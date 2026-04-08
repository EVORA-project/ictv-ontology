<?php
/**
 * ICTV PHP API Helper (ictv-api.php)
 *
 * Lightweight helper to query the ICTV Ontology via the Ontology Lookup Service (OLS4)
 * and to resolve ICTV taxon names, identifiers, and NCBI Taxon IDs to current ICTV taxa.
 *
 * Implementation initially inspired by notebook script created by @jamesamcl:
 * https://github.com/EVORA-project/ictv-ontology/blob/main/notebooks/ictv_ols.py
 *
 * This file provides two classes:
 *  - ICTVOLSClient      : main client for OLS / ICTV ontology
 *  - ICTVtoNCBImapping  : ICTV ↔ NCBI Taxon mapping helper based on SSSOM
 *
 * PHP version: 7.4+
 *
 * @author  EVORA Project - Angatar (d3fk)
 * @license MIT
 * @link    https://github.com/EVORA-project/ictv-ontology
 */

/* ====================================================================== */
/*                           ICTV OLS API Helper                          */
/* ====================================================================== */

class ICTVOLSClient {
    private $baseUrl;
    private $headers;
    private $ncbiMapper;

    /** @var array<string, mixed> IRI -> raw OLS entity */
    private $iriCache = [];
    /** @var array<string, array> OLS endpoint+query key -> OLS response */
    private $classCache = [];

    public function __construct($baseUrl = 'https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv') {
        $this->baseUrl = rtrim($baseUrl, '/');
        $this->headers = ["Accept: application/json"];
        $this->ncbiMapper = new ICTVtoNCBImapping();
    }

    /* -------------------- tiny utils -------------------- */
    private function normalizeValue($value) {
        return is_array($value) ? ($value[0] ?? null) : $value;
    }

    private function toArray($x) {
        if ($x === null) return [];
        return is_array($x) ? $x : [$x];
    }

    private function parseMsl($msl) {
        return preg_match('/MSL(\d+)/i', $msl ?? '', $m) ? (int)$m[1] : -1;
    }

    private function isIctvId($s) {
        return preg_match('/^ICTV\d{5,}$/i', trim($s));
    }

    private function isIctvIri($s) {
        return preg_match('#^https?://ictv\.global/id/MSL\d+/ICTV\d+#i', trim($s));
    }

    private function buildUrl($base, $params = []) {
        $query = http_build_query(array_filter($params, fn($v) => $v !== null && $v !== ''));
        return $query ? "$base?$query" : $base;
    }

    private function fetchit($url, $params = []) {
        $ch = curl_init();
        $url = $this->buildUrl($url, $params);
        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FAILONERROR => true,
            CURLOPT_HTTPHEADER => $this->headers
        ]);
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);

        if ($response === false || $httpCode >= 400) {
            throw new Exception("Fetch failed ($httpCode) for $url: " . curl_error($ch));
        }
        curl_close($ch);
        return json_decode($response, true);
    }

    private function ols($endpoint, $params = []) {
        $cacheKey = $endpoint . '|' . http_build_query($params);
        if (isset($this->classCache[$cacheKey])) {
            return $this->classCache[$cacheKey];
        }
        $result = $this->fetchit("{$this->baseUrl}/$endpoint", array_merge(["size" => 1000], $params));
        $this->classCache[$cacheKey] = $result;
        return $result;
    }

    /**
     * Fetch an entity by IRI with in-memory caching.
     */
    private function retrieveTaxonByIRI($iri) {
        if (!$iri) return null;
        if (isset($this->iriCache[$iri])) {
            return $this->iriCache[$iri];
        }
        // OLS expects double-encoded entity IRIs
        $enc = rawurlencode(rawurlencode($iri));
        $res = $this->fetchit("{$this->baseUrl}/entities/$enc");
        $this->iriCache[$iri] = $res;
        return $res;
    }

    public function getTaxonByIRI($iri) {
        $e = $this->retrieveTaxonByIRI($iri);
        return $e ? $this->mapEntity($e) : null;
    }

    /* -------------------- Suggestions (OLS autosuggest) -------------------- */
    public function getSuggestions($query) {
        $url = "https://www.ebi.ac.uk/ols4/api/suggest";
        $data = $this->fetchit($url, ["ontology" => "ictv", "q" => $query]);
        $docs = $data['response']['docs'] ?? [];
        $sugs = [];
        foreach ($docs as $d) {
            if (!empty($d['autosuggest'])) {
                $v = trim($d['autosuggest']);
                if (strcasecmp($v, $query) !== 0) {
                    $sugs[$v] = true;
                }
            }
        }
        return array_values(array_keys($sugs));
    }

    /* -------------------- Input resolution (tunable) -------------------- */
    /**
     * Resolve any input (IRI, ICTV ID, NCBI TaxID, label/synonym, individual) to current/obsolete entity.
     * Options:
     *  - replacements (bool): follow replacement chains when obsolete (default true)
     *  - enrichLineage (bool): fetch parent & ancestor labels (default true)
     *  - suggestions (bool): include suggestions when not found (default true)
     */
    public function resolveToLatest($inputRaw, array $options = [
        'replacements'   => true,
        'enrichLineage'  => true,
        'suggestions'    => true
    ]) {
        $input = is_string($inputRaw) ? trim($inputRaw) : $inputRaw;
        if (empty($input)) {
            return [
                'status' => 'not-found',
                'input'  => null,
                'reason' => 'empty input'
            ];
        }

        // 1) direct IRI
        if ($this->isIctvIri($input)) {
            return $this->resolveEntityByIri($input, $options);
        }

        // 2) ICTV ID
        if ($this->isIctvId($input)) {
            return $this->resolveEntityById($input, $options);
        }

        // 3) NCBI TaxID
        if (ctype_digit($input) || preg_match('/^ncbitaxon:\d+$/i', $input)) {
            $hits = $this->ncbiMapper->getIctvFromNcbi($input);
            if (!empty($hits)) {
                $best = array_reduce($hits, function ($acc, $h) {
                    $n = $this->parseMsl($h['msl']);
                    if (!$acc || $n > $acc['n']) return ['h' => $h, 'n' => $n];
                    return $acc;
                });
                $iri = "http://ictv.global/id/{$best['h']['msl']}/{$best['h']['ictv_id']}";
                return $this->resolveEntityByIri($iri, $options);
            }
        }
        // 4) individuals → parent class
        $ind = $this->seekOntologyTaxon('individuals', ['label' => $input])
            ?: $this->seekOntologyTaxon('individuals', ['synonym' => $input]);
        if ($ind) {
            foreach ($ind as $e) {
                $pIri = $this->normalizeValue($e['directParent'] ?? null);
                if ($pIri) return $this->resolveEntityByIri($pIri, $options);
            }
        }
        // 5) label / synonym
        $found = $this->seekOntologyTaxon('classes', ['label' => $input, 'isObsolete' => 'false'])
            ?: $this->seekOntologyTaxon('classes', ['label' => $input, 'isObsolete' => 'true'])
            ?: $this->seekOntologyTaxon('classes', ['synonym' => $input]);

        if (!$found) {
            // relaxed query
            $rel = $this->seekOntologyTaxon('classes', ['q' => $input, 'isObsolete' => 'false']) ?: [];
            if (!empty($rel)) $found = $rel;
        }

        if ($found) {
            $sorted = $this->sortCandidates($found);
            return $this->resolveEntityByIri($sorted[0]['iri'], $options);
        }



        // 6) suggestions fallback
        return [
            'status' => 'not-found',
            'input' => $input,
            'suggestions' => $options['suggestions'] ? $this->getSuggestions($input) : []
        ];
    }

    private function resolveEntityByIri($iri, array $options) {
        $e = $this->retrieveTaxonByIRI($iri);
        if (!$e) return ['status' => 'not-found', 'input' => $iri];

        // If we somehow got an individual, move to parent class
        if (empty($e['http://purl.org/dc/terms/identifier'])) {
            $p = $this->normalizeValue($e['directParent'] ?? null);
            if ($p) $e = $this->retrieveTaxonByIRI($p);
        }
        if (!$e) return ['status' => 'not-found', 'input' => $iri];

        $mapped = $this->mapEntity($e);
        if ($options['enrichLineage']) {
            $mapped = $this->enrichLineage($mapped);
        }

        if (!$mapped['is_obsolete']) {
            $ncbi = $this->ncbiMapper->getNcbiTaxon($mapped['ictv_id'], $mapped['msl']);
            return ['status' => 'current', 'input' => $iri, 'current' => $mapped, 'ncbi' => $ncbi];
        }

        $replacements = $options['replacements'] ? $this->followReplacements($mapped, $options) : [];
        return [
            'status' => 'obsolete',
            'input' => $iri,
            'obsolete' => $mapped,
            'reason' => $mapped['obsolescence_reason'] ?? null,
            'replacements' => $replacements,
            'final' => $replacements[0] ?? null
        ];
    }

    private function resolveEntityById($ictvId, array $options) {
        $candidates = $this->seekOntologyTaxonByClassId($ictvId);
        if (empty($candidates)) return ['status' => 'not-found', 'input' => $ictvId];
        $sorted = $this->sortCandidates($candidates);
        return $this->resolveEntityByIri($sorted[0]['iri'], $options);
    }

    /* -------------------- Replacement chain -------------------- */
    private function followReplacements($entity, array $options) {
        $queue = $this->toArray($entity['replaced_by']);
        $seen = [];
        $results = [];

        while (!empty($queue)) {
            $iri = array_shift($queue);
            if (!$iri || isset($seen[$iri])) continue;
            $seen[$iri] = true;

            $e = $this->retrieveTaxonByIRI($iri);
            if (!$e) continue;

            $mapped = $this->mapEntity($e);
            if ($options['enrichLineage']) {
                $mapped = $this->enrichLineage($mapped);
            }

            if ($mapped['is_obsolete'] && $mapped['replaced_by']) {
                foreach ($this->toArray($mapped['replaced_by']) as $r) $queue[] = $r;
            } else {
                $results[] = $mapped;
            }
        }

        usort($results, fn($a, $b) => $this->parseMsl($b['msl']) <=> $this->parseMsl($a['msl']));
        return $results;
    }

    /* -------------------- Lineage enrichment -------------------- */
    private function enrichLineage($mapped) {
        // direct parent label
        $mapped['direct_parent_label'] = null;
        if (!empty($mapped['direct_parent_iri'])) {
            $p = $this->retrieveTaxonByIRI($mapped['direct_parent_iri']);
            if ($p) {
                $mapped['direct_parent_label'] = $this->normalizeValue(
                    $p['label'] ?? $p["http://www.w3.org/2000/01/rdf-schema#label"] ?? null
                );
            }
        }

        // ordered lineage reconstructed from parent chain
        $lineageLabels = [];
        $lineageIris = [];

        $seen = [];
        $currentIri = $mapped['direct_parent_iri'] ?? null;

        while ($currentIri && !isset($seen[$currentIri])) {
            $seen[$currentIri] = true;

            $parentRaw = $this->retrieveTaxonByIRI($currentIri);
            if (!$parentRaw) {
                break;
            }

            $parentLabel = $this->normalizeValue(
                $parentRaw['label'] ?? $parentRaw["http://www.w3.org/2000/01/rdf-schema#label"] ?? null
            );
            if ($parentLabel) {
                $lineageLabels[] = $parentLabel;
                $lineageIris[] = $currentIri;
            }

            $currentIri = $this->normalizeValue(
                $parentRaw['directParent'] ?? $parentRaw['direct_parent'] ?? null
            );
        }

        $mapped['lineage'] = array_reverse($lineageLabels);
        $mapped['ancestors_iris'] = array_reverse($lineageIris);
        return $mapped;
    }

    /* -------------------- Mapping (with rank restored) -------------------- */
    private function mapEntity($e) {
        $label = $this->normalizeValue($e['label'] ?? $e["http://www.w3.org/2000/01/rdf-schema#label"] ?? null);

        // synonyms
        $synonyms = [];
        foreach (["synonym", "http://www.geneontology.org/formats/oboInOwl#hasExactSynonym"] as $key) {
            foreach ($this->toArray($e[$key] ?? []) as $s) {
                if (is_array($s) && isset($s['value'])) $synonyms[] = $s['value'];
                elseif (is_string($s)) $synonyms[] = $s;
                elseif (is_array($s)) $synonyms[] = $this->normalizeValue($s);
            }
        }

        // rank (iri + label), including linkedEntities fallback
        $rankIri = $e["http://purl.obolibrary.org/obo/TAXRANK_1000000"] ?? ($e['rank']['iri'] ?? null);
        $rankLabel = $e['rank']['label'] ?? null;
        if ($rankIri && isset($e['linkedEntities'][$rankIri]['label'])) {
            $rankLabel = $this->normalizeValue($e['linkedEntities'][$rankIri]['label']);
        }

        // obsolescence reason
        $reasonIri  = $e["http://purl.obolibrary.org/obo/IAO_0000225"] ?? $e["oboInOwl:hasObsolescenceReason"] ?? null;
        $reasonText = $this->mapReasonIriToText($reasonIri);

        $msl     = $e["http://www.w3.org/2002/07/owl#versionInfo"] ?? null;
        $ictv_id = $e["http://purl.org/dc/terms/identifier"] ?? null;

        return [
            // identity
            'msl'        => $msl,
            'ictv_id'    => $ictv_id,
            'ictv_curie' => ($msl && $ictv_id) ? "ictv:$msl/$ictv_id" : null,
            'iri'        => $e["iri"] ?? null,

            // names
            'label'      => $label,
            'synonyms'   => array_values(array_unique($synonyms)),

            // status
            'is_obsolete'         => $e["isObsolete"] ?? false,
            'obsolescence_reason' => $reasonText,
            'reason_iri'          => $reasonIri,

            // parents / lineage
            'direct_parent_iri' => $this->normalizeValue($e["directParent"] ?? $e["direct_parent"] ?? null),
            'ancestors_iris'    => $e["ancestors"] ?? $e["hierarchicalAncestor"] ?? [],

            // rank
            'rank' => [
                'iri'   => $rankIri,
                'label' => $rankLabel
            ],

            // revision links
            'replaced_by'     => $e["http://purl.obolibrary.org/obo/IAO_0100001"] ?? null,
            'was_revision_of' => $e["http://www.w3.org/ns/prov#wasRevisionOf"] ?? null,
            'had_revision'    => $e["http://www.w3.org/ns/prov#hadRevision"] ?? null,

            // external matches (raw list; transform in caller if needed)
            'narrow_match'    => $this->toArray($e["http://www.w3.org/2004/02/skos/core#narrowMatch"] ?? [])
        ];
    }

    private function mapReasonIriToText($reasonIri) {
        if ($reasonIri === "http://purl.obolibrary.org/obo/IAO_0000229") return "SPLIT";
        if ($reasonIri === "http://purl.obolibrary.org/obo/IAO_0000227") return "MERGED";
        return null;
    }

    /* -------------------- Seekers -------------------- */
    private function seekOntologyTaxon($endpoint, $params) {
        $data = $this->ols($endpoint, $params);
        return $data['elements'] ?? null;
    }

    private function seekOntologyTaxonByClassId($id) {
        $curr = $this->seekOntologyTaxon('classes', [
            "http://purl.org/dc/terms/identifier" => $id,
            "isObsolete" => "false"
        ]) ?: [];
        $obs  = $this->seekOntologyTaxon('classes', [
            "http://purl.org/dc/terms/identifier" => $id,
            "isObsolete" => "true"
        ]) ?: [];
        return array_merge($curr, $obs);
    }

    private function seekOntologyTaxonByClassLabel($label) {
        $curr = $this->seekOntologyTaxon('classes', ["label" => $label, "isObsolete" => "false"]) ?: [];
        $obs  = $this->seekOntologyTaxon('classes', ["label" => $label, "isObsolete" => "true"]) ?: [];
        return array_merge($curr, $obs);
    }

    private function seekOntologyTaxonBySynonym($synonym) {
        return $this->seekOntologyTaxon('classes', ["synonym" => $synonym]) ?: [];
    }

    private function seekOntologyTaxonByIndividual($labelOrSyn) {
        $indsLabel = $this->seekOntologyTaxon('individuals', ['label' => $labelOrSyn]) ?: [];
        $indsSyn   = $this->seekOntologyTaxon('individuals', ['synonym' => $labelOrSyn]) ?: [];
        $all = array_merge($indsLabel, $indsSyn);
        $parents = [];
        $seen = [];
        foreach ($all as $ind) {
            $pIri = $this->normalizeValue($ind['directParent'] ?? null);
            if ($pIri && !isset($seen[$pIri])) {
                $seen[$pIri] = true;
                $p = $this->retrieveTaxonByIRI($pIri);
                if ($p && !empty($p["http://purl.org/dc/terms/identifier"])) {
                    $parents[] = $p;
                }
            }
        }
        return $parents;
    }

    private function sortCandidates($arr) {
        usort($arr, fn($a, $b) =>
            $this->parseMsl($b["http://www.w3.org/2002/07/owl#versionInfo"] ?? '') <=>
            $this->parseMsl($a["http://www.w3.org/2002/07/owl#versionInfo"] ?? '')
        );
        return $arr;
    }

    /* -------------------- Extras / Public helpers -------------------- */

    /**
     * Return the current entity/entities for a given input.
     * - If the input resolves to a current entity → returns [entity]
     * - If obsolete → returns replacement chain final(s)
     */
    public function getCurrentReplacements($idOrLabelOrEntity) {
        $res = $this->resolveToLatest($idOrLabelOrEntity, [
            'replacements'  => true,
            'enrichLineage' => false,
            'suggestions'   => false
        ]);

        if (($res['status'] ?? null) === 'current') {
            return [$res['current']];
        }

        if (($res['status'] ?? null) === 'obsolete') {
            // if we already have explicit replacements, return them
            if (!empty($res['replacements'])) {
                return $res['replacements'];
            }

            // --- fallback by label (important for old ICTV IDs without replaced_by) ---
            $obsolete = $res['obsolete'] ?? null;
            $label    = is_array($obsolete ?? null) ? ($obsolete['label'] ?? null) : null;
            if ($label) {
                $res2 = $this->resolveToLatest($label, [
                    'replacements'  => true,
                    'enrichLineage' => false,
                    'suggestions'   => false
                ]);

                if (($res2['status'] ?? null) === 'current' && isset($res2['current'])) {
                    return [$res2['current']];
                }
                if (($res2['status'] ?? null) === 'obsolete' && !empty($res2['replacements'])) {
                    return $res2['replacements'];
                }
            }
        }

        return [];
    }

    /** Thin wrapper to expose candidates, keeping backwards compatibility. */
    public function findCandidates($idOrLabel) {
        if (strpos($idOrLabel, 'ICTV') !== false) {
            $candidates = $this->seekOntologyTaxonByClassId($idOrLabel);
        } else {
            $candidates = $this->seekOntologyTaxonByClassLabel($idOrLabel);
            if (empty($candidates)) $candidates = $this->seekOntologyTaxonBySynonym($idOrLabel);
            if (empty($candidates)) $candidates = $this->seekOntologyTaxonByIndividual($idOrLabel);
        }
        if (empty($candidates)) return [];
        $candidates = $this->sortCandidates($candidates);
        foreach ($candidates as &$el) {
            $el['_msl_number'] = $this->parseMsl($el["http://www.w3.org/2002/07/owl#versionInfo"] ?? '');
        }
        return $candidates;
    }

    /** Thin wrapper returning the latest mapped entity for a given label/ID. */
    public function findLatest($idOrLabel) {
        $res = $this->resolveToLatest($idOrLabel, [
            'replacements'  => false,
            'enrichLineage' => false,
            'suggestions'   => false
        ]);

        return $res['current'] ?? $res['final']?? $res['obsolete'] ?? null;
    }

    /** Get synonyms of a class/entity (deduped). */
    public function getSynonyms($idOrLabelOrEntity) {
        $entity = $this->resolveAsEntity($idOrLabelOrEntity);
        return $entity ? array_values(array_unique($entity['synonyms'] ?? [])) : [];
    }

    /** Get (unique) individuals under a class. */
    public function getIndividuals($idOrLabelOrEntity) {
        $entity = $this->resolveAsEntity($idOrLabelOrEntity);
        if (!$entity || empty($entity['iri'])) return [];
        // OLS expects double-encoded entity IRIs here
        $enc = rawurlencode(rawurlencode($entity['iri']));
        $data = $this->fetchit("{$this->baseUrl}/classes/$enc/individuals", ["size" => 1000]);
        return $data;
    }

    /** Get (unique) individuals' names under a class. */
    public function getIndividualsNames($idOrLabelOrEntity) {
        $data = $this->getIndividuals($idOrLabelOrEntity);
        $names = [];
        foreach ($data['elements'] ?? [] as $ind) {
            $label = $ind['label'] ?? $ind["http://www.w3.org/2000/01/rdf-schema#label"] ?? null;
            $label = $this->normalizeValue($label);
            if ($label) $names[$label] = true;
        }
        return array_keys($names);
    }

    /** Get all taxa for a specific MSL release (paged). */
    public function getAllFromRelease(string $release): array {
        $page = 0;
        $size = 1000;
        $all = [];

        do {
            $data = $this->fetchit("{$this->baseUrl}/classes", [
                "http://www.w3.org/2002/07/owl#versionInfo" => $release,
                "size" => $size,
                "page" => $page
            ]);
            $batch = $data['elements'] ?? [];
            foreach ($batch as $el) {
                $all[] = $this->mapEntity($el);
            }
            $page++;
            $hasMore = !empty($batch);
        } while ($hasMore);

        return $all;
    }

    /** Fetch a specific taxon by ICTV ID + MSL (release). */
    public function getTaxonByRelease($ictvId, $release) {
        $data = $this->ols('classes', [
            "http://www.w3.org/2002/07/owl#versionInfo" => $release,
            "http://purl.org/dc/terms/identifier" => $ictvId
        ]);
        $el = $data['elements'][0] ?? null;
        return $el ? $this->mapEntity($el) : null;
    }

    /** Full history across revisions (linear chain), newest first. */
    public function getHistory($idOrLabelOrEntity) {
        $entityRaw = $this->resolveAsEntity($idOrLabelOrEntity);
        if (!$entityRaw) return [];

        // Ensure we traverse from a raw OLS entity
        $entity = $this->retrieveTaxonByIRI($entityRaw['iri']) ?? $entityRaw;

        $seen = [];
        $history = [];

        $walk = function ($ent) use (&$walk, &$seen, &$history) {
            $mapped = $this->mapEntity($ent);
            if (!$mapped['msl'] || !$mapped['ictv_id']) return;
            $mslKey = $mapped['msl'];
            if (isset($seen[$mslKey])) return;
            $seen[$mslKey] = true;

            $mapped = $this->enrichLineage($mapped);
            $history[] = $mapped;

            foreach (['was_revision_of', 'had_revision'] as $key) {
                if (!empty($mapped[$key])) {
                    $next = $this->retrieveTaxonByIRI($mapped[$key]);
                    if ($next) return $walk($next);
                }
            }
        };

        $walk($entity);
        usort($history, fn($a, $b) => $this->parseMsl($b['msl']) <=> $this->parseMsl($a['msl']));
        return $history;
    }

    /** Returns the (single) historical parent if present (linear only). */
    public function getHistoricalParent($idOrLabelOrEntity) {
        $entity = $this->resolveAsEntity($idOrLabelOrEntity);
        if (!$entity) return null;

        foreach (['was_revision_of', 'had_revision'] as $key) {
            if (!empty($entity[$key])) {
                $parent = $this->retrieveTaxonByIRI($entity[$key]);
                return $parent ? $this->mapEntity($parent) : null;
            }
        }
        return null;
    }

    /** Raw obsolescence reason IRI (if obsolete). */
    public function getObsolescenceReason($idOrLabelOrEntity): ?string {
        $entity = $this->resolveAsEntity($idOrLabelOrEntity);
        if (!$entity || !($entity['is_obsolete'] ?? false)) return null;
        return $entity['reason_iri'] ?? null;
    }

    /** Friendly obsolescence reason (SPLIT / MERGED), if applicable. */
    public function getTextualObsolescenceReason($idOrLabelOrEntity): ?string {
        $iri = $this->getObsolescenceReason($idOrLabelOrEntity);
        return $this->mapReasonIriToText($iri);
    }

    /** Internal: resolve input or entity to a mapped entity array. */
    private function resolveAsEntity($idOrLabelOrEntity) {
        if (is_array($idOrLabelOrEntity) && isset($idOrLabelOrEntity['iri'])) {
            return $idOrLabelOrEntity;
        }
        $res = $this->resolveToLatest($idOrLabelOrEntity, [
            'replacements'  => true,
            'enrichLineage' => false,
            'suggestions'   => false
        ]);
        if (($res['status'] ?? null) === 'current') return $res['current'];
        if (($res['status'] ?? null) === 'obsolete' && isset($res['obsolete'])) return $res['obsolete'];
        return null;
    }
}

/* ====================================================================== */
/*                           ICTV/NCBI Mapping                            */
/* ====================================================================== */
class ICTVtoNCBImapping {
    private $sssomUrl = 'https://raw.githubusercontent.com/EVORA-project/virus-taxonomy-mappings/refs/heads/dev/mappings/ictv_ncbitaxon_exact.sssom.tsv';
    private $ncbiMap = null; // ['forward' => [], 'reverse' => []]

    public function __construct() {}

    public function setDifferentSssomUrl($sssomUrl) {
        $this->sssomUrl = $sssomUrl;
    }

    private function loadNcbiMap() {
        if ($this->ncbiMap !== null) return;
        $rows = @file($this->sssomUrl, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        if ($rows === false) throw new Exception("Failed to fetch mapping file");

        $this->ncbiMap = ['forward' => [], 'reverse' => []];
        array_shift($rows); // header

        foreach ($rows as $line) {
            $cols = explode("\t", $line);
            if (count($cols) < 5) continue;
            $ictvCurie = $cols[0];
            $ncbiCurie = strtolower($cols[3]);
            $label = $cols[4];

            // forward
            $this->ncbiMap['forward'][$ictvCurie][] = ['ncbiCurie' => $ncbiCurie, 'label' => $label];

            // reverse
            if (preg_match('~^ictv:([^/]+)/([^/]+)$~i', $ictvCurie, $mm)) {
                $this->ncbiMap['reverse'][$ncbiCurie][] = [
                    'ictv_curie' => $ictvCurie,
                    'msl'        => $mm[1],
                    'ictv_id'    => $mm[2],
                    'label'      => $label
                ];
            }
        }
    }

    /** ICTV → NCBI (same MSL). */
    public function getNcbiTaxon($ictvId, $msl) {
        $this->loadNcbiMap();
        $curie = "ictv:$msl/$ictvId";
        return $this->ncbiMap['forward'][$curie] ?? [];
    }

    /** NCBI → ICTV (keep only highest MSL per ICTV ID). */
    public function getIctvFromNcbi($ncbiId) {
        $this->loadNcbiMap();
        $key = strtolower(trim($ncbiId));
        if (strpos($key, 'ncbitaxon:') !== 0) {
            $key = 'ncbitaxon:' . $key;
        }
        $hits = $this->ncbiMap['reverse'][$key] ?? [];
        $best = [];

        foreach ($hits as $h) {
            $mslNum = preg_match('/MSL(\d+)/i', $h['msl'], $m) ? (int)$m[1] : 0;
            if (!isset($best[$h['ictv_id']]) || $mslNum > $best[$h['ictv_id']]['_msl']) {
                $best[$h['ictv_id']] = $h + ['_msl' => $mslNum];
            }
        }

        foreach ($best as &$b) unset($b['_msl']);
        return array_values($best);
    }
}

