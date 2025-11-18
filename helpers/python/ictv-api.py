# ======================================================================
#                   ICTV Python API Helper (ictv-api.py)
#
# Lightweight helper to query the ICTV Ontology via the Ontology
# Lookup Service (OLS4) API and to resolve ICTV taxon names, identifiers,
# and NCBI Taxon IDs to current ICTV taxa.
#
# Implementation initially inspired by notebook script created by @jamesamcl
# https://github.com/EVORA-project/ictv-ontology/blob/main/notebooks/ictv_ols.py
#
# This file provides two classes:
#   - ICTVOLSClient     : main client for OLS / ICTV ontology
#   - ICTVtoNCBImapping : ICTV ↔ NCBI Taxon mapping helper based on SSSOM
#
# Python version: 3.8+
#
# @author  EVORA Project - Angatar (d3fk)
# @license MIT
# @link    https://github.com/EVORA-project/ictv-ontology


# ======================================================================
#                           ICTV OLS API Helper
# ======================================================================

from __future__ import annotations
import re
import json
from typing import Any, Dict, List, Optional
from urllib.parse import quote
import requests


class ICTVOLSClient:
    def __init__(self, baseUrl: str = 'https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv'):
        self.baseUrl: str = baseUrl.rstrip('/')
        self.headers: Dict[str, str] = {"Accept": "application/json"}
        self.ncbiMapper: ICTVtoNCBImapping = ICTVtoNCBImapping()

        # IRI -> raw OLS entity
        self.iriCache: Dict[str, Dict[str, Any]] = {}
        # OLS endpoint+query key -> OLS response
        self.classCache: Dict[str, Dict[str, Any]] = {}

    # -------------------- tiny utils --------------------
    def normalizeValue(self, value: Any) -> Any:
        if isinstance(value, list):
            return value[0] if value else None
        return value

    def toArray(self, x: Any) -> List[Any]:
        if x is None:
            return []
        return x if isinstance(x, list) else [x]

    def parseMsl(self, msl: Optional[str]) -> int:
        if not msl:
            return -1
        m = re.search(r'MSL(\d+)', msl, flags=re.IGNORECASE)
        return int(m.group(1)) if m else -1

    def isIctvId(self, s: str) -> bool:
        return bool(re.match(r'^ICTV\d{5,}$', s.strip(), flags=re.IGNORECASE))

    def isIctvIri(self, s: str) -> bool:
        return bool(re.match(r'^https?://ictv\.global/id/MSL\d+/ICTV\d+', s.strip(), flags=re.IGNORECASE))

    def _cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        # stable key independent of param order
        items = sorted((k, str(v)) for k, v in params.items())
        return endpoint + '|' + '&'.join(f'{k}={v}' for k, v in items)

    def fetchit(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}
        try:
            r = requests.get(url, params=params, headers=self.headers, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            status = getattr(e.response, 'status_code', 'N/A')
            raise Exception(f"Fetch failed ({status}) for {r.url if 'r' in locals() else url}: {e}")

    def ols(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params.copy() if params else {}
        params.setdefault("size", 1000)
        cacheKey = self._cache_key(endpoint, params)
        if cacheKey in self.classCache:
            return self.classCache[cacheKey]
        result = self.fetchit(f"{self.baseUrl}/{endpoint}", params)
        self.classCache[cacheKey] = result
        return result

    # -------------------- entity fetch (with cache) --------------------
    def retrieveTaxonByIRI(self, iri: Optional[str]) -> Optional[Dict[str, Any]]:
        if not iri:
            return None
        if iri in self.iriCache:
            return self.iriCache[iri]
        # OLS expects double-encoded entity IRIs
        enc = quote(quote(iri, safe=''), safe='')
        res = self.fetchit(f"{self.baseUrl}/entities/{enc}")
        self.iriCache[iri] = res
        return res

    def getTaxonByIRI(self, iri: str) -> Optional[Dict[str, Any]]:
        e = self.retrieveTaxonByIRI(iri)
        return self.mapEntity(e) if e else None

    # -------------------- Suggestions (OLS autosuggest) --------------------
    def getSuggestions(self, query: str) -> List[str]:
        url = "https://www.ebi.ac.uk/ols4/api/suggest"
        data = self.fetchit(url, {"ontology": "ictv", "q": query})
        docs = (data.get('response') or {}).get('docs', [])
        sugs = {}
        for d in docs:
            v = (d.get('autosuggest') or '').strip()
            if v and v.lower() != query.strip().lower():
                sugs[v] = True
        return list(sugs.keys())

    # -------------------- Input resolution (tunable) --------------------
    def resolveToLatest(self, inputRaw: Any, options: Dict[str, bool] = None) -> Dict[str, Any]:
        if options is None:
            options = {'replacements': True, 'enrichLineage': True, 'suggestions': True}

        input_val = inputRaw.strip() if isinstance(inputRaw, str) else inputRaw
        if not input_val:
            return {'status': 'not-found', 'input': None, 'reason': 'empty input'}

        # 1) direct IRI
        if isinstance(input_val, str) and self.isIctvIri(input_val):
            return self._resolveEntityByIri(input_val, options)

        # 2) ICTV ID
        if isinstance(input_val, str) and self.isIctvId(input_val):
            return self._resolveEntityById(input_val, options)

        # 3) NCBI TaxID
        if isinstance(input_val, str) and (input_val.isdigit() or re.match(r'^ncbitaxon:\d+$', input_val, re.I)):
            hits = self.ncbiMapper.getIctvFromNcbi(input_val)
            if hits:
                best = None
                for h in hits:
                    n = self.parseMsl(h.get('msl'))
                    if best is None or n > best['n']:
                        best = {'h': h, 'n': n}
                iri = f"http://ictv.global/id/{best['h']['msl']}/{best['h']['ictv_id']}"
                return self._resolveEntityByIri(iri, options)

        # 4) individuals → parent class
        ind = self.seekOntologyTaxon('individuals', {'label': input_val}) or \
              self.seekOntologyTaxon('individuals', {'synonym': input_val})
        if ind:
            for e in ind:
                pIri = self.normalizeValue(e.get('directParent'))
                if pIri:
                    return self._resolveEntityByIri(pIri, options)

        # 5) label / synonym
        found = (self.seekOntologyTaxon('classes', {'label': input_val, 'isObsolete': 'false'}) or
                 self.seekOntologyTaxon('classes', {'label': input_val, 'isObsolete': 'true'}) or
                 self.seekOntologyTaxon('classes', {'synonym': input_val}))

        if not found:
            rel = self.seekOntologyTaxon('classes', {'q': input_val, 'isObsolete': 'false'}) or []
            if rel:
                found = rel

        if found:
            sorted_cands = self.sortCandidates(found)
            return self._resolveEntityByIri(sorted_cands[0]['iri'], options)

        # 6) suggestions fallback
        return {
            'status': 'not-found',
            'input': input_val,
            'suggestions': self.getSuggestions(input_val) if options.get('suggestions') else []
        }

    def _resolveEntityByIri(self, iri: str, options: Dict[str, bool]) -> Dict[str, Any]:
        e = self.retrieveTaxonByIRI(iri)
        if not e:
            return {'status': 'not-found', 'input': iri}

        # If we somehow got an individual, move to parent class
        if not e.get('http://purl.org/dc/terms/identifier'):
            p = self.normalizeValue(e.get('directParent'))
            if p:
                e = self.retrieveTaxonByIRI(p)

        if not e:
            return {'status': 'not-found', 'input': iri}

        mapped = self.mapEntity(e)
        if options.get('enrichLineage'):
            mapped = self.enrichLineage(mapped)

        if not mapped['is_obsolete']:
            ncbi = self.ncbiMapper.getNcbiTaxon(mapped['ictv_id'], mapped['msl'])
            return {'status': 'current', 'input': iri, 'current': mapped, 'ncbi': ncbi}

        replacements = self.followReplacements(mapped, options) if options.get('replacements') else []
        return {
            'status': 'obsolete',
            'input': iri,
            'obsolete': mapped,
            'reason': mapped.get('obsolescence_reason'),
            'replacements': replacements,
            'final': (replacements[0] if replacements else None)
        }

    def _resolveEntityById(self, ictvId: str, options: Dict[str, bool]) -> Dict[str, Any]:
        candidates = self.seekOntologyTaxonByClassId(ictvId)
        if not candidates:
            return {'status': 'not-found', 'input': ictvId}
        sorted_cands = self.sortCandidates(candidates)
        return self._resolveEntityByIri(sorted_cands[0]['iri'], options)

    # -------------------- Replacement chain --------------------
    def followReplacements(self, entity: Dict[str, Any], options: Dict[str, bool]) -> List[Dict[str, Any]]:
        queue = self.toArray(entity.get('replaced_by'))
        seen = set()
        results: List[Dict[str, Any]] = []

        while queue:
            iri = queue.pop(0)
            if not iri or iri in seen:
                continue
            seen.add(iri)

            e = self.retrieveTaxonByIRI(iri)
            if not e:
                continue

            mapped = self.mapEntity(e)
            if options.get('enrichLineage'):
                mapped = self.enrichLineage(mapped)

            if mapped['is_obsolete'] and mapped.get('replaced_by'):
                for r in self.toArray(mapped['replaced_by']):
                    queue.append(r)
            else:
                results.append(mapped)

        results.sort(key=lambda a: self.parseMsl(a.get('msl')), reverse=True)
        return results

    # -------------------- Lineage enrichment --------------------
    def enrichLineage(self, mapped: Dict[str, Any]) -> Dict[str, Any]:
        # direct parent label
        mapped['direct_parent_label'] = None
        if mapped.get('direct_parent_iri'):
            p = self.retrieveTaxonByIRI(mapped['direct_parent_iri'])
            if p:
                mapped['direct_parent_label'] = self.normalizeValue(
                    p.get('label') or p.get("http://www.w3.org/2000/01/rdf-schema#label")
                )

        # lineage labels from ancestor IRIs
        mapped['lineage'] = []
        for iri in self.toArray(mapped.get('ancestors_iris') or []):
            a = self.retrieveTaxonByIRI(iri)
            if a:
                l = self.normalizeValue(a.get('label') or a.get("http://www.w3.org/2000/01/rdf-schema#label"))
                if l:
                    mapped['lineage'].append(l)
        return mapped

    # -------------------- Mapping (with rank restored) --------------------
    def mapEntity(self, e: Dict[str, Any]) -> Dict[str, Any]:
        label = self.normalizeValue(e.get('label') or e.get("http://www.w3.org/2000/01/rdf-schema#label"))

        # synonyms
        synonyms: List[str] = []
        for key in ["synonym", "http://www.geneontology.org/formats/oboInOwl#hasExactSynonym"]:
            for s in self.toArray(e.get(key) or []):
                if isinstance(s, dict) and 'value' in s:
                    synonyms.append(s['value'])
                elif isinstance(s, str):
                    synonyms.append(s)
                elif isinstance(s, list):
                    synonyms.append(self.normalizeValue(s))

        # rank (iri + label), including linkedEntities fallback
        rankIri = e.get("http://purl.obolibrary.org/obo/TAXRANK_1000000") or (e.get('rank', {}) or {}).get('iri')
        rankLabel = (e.get('rank', {}) or {}).get('label')
        if rankIri and 'linkedEntities' in e and rankIri in e['linkedEntities'] and 'label' in e['linkedEntities'][rankIri]:
            rankLabel = self.normalizeValue(e['linkedEntities'][rankIri]['label'])

        # obsolescence reason
        reasonIri = e.get("http://purl.obolibrary.org/obo/IAO_0000225") or e.get("oboInOwl:hasObsolescenceReason")
        reasonText = self.mapReasonIriToText(reasonIri)

        msl = e.get("http://www.w3.org/2002/07/owl#versionInfo")
        ictv_id = e.get("http://purl.org/dc/terms/identifier")

        mapped = {
            # identity
            'msl': msl,
            'ictv_id': ictv_id,
            'ictv_curie': f"ictv:{msl}/{ictv_id}" if (msl and ictv_id) else None,
            'iri': e.get("iri"),

            # names
            'label': label,
            'synonyms': list(dict.fromkeys(synonyms)),  # dedupe, keep order

            # status
            'is_obsolete': e.get("isObsolete", False),
            'obsolescence_reason': reasonText,
            'reason_iri': reasonIri,

            # parents / lineage
            'direct_parent_iri': self.normalizeValue(e.get("directParent") or e.get("direct_parent")),
            'ancestors_iris': e.get("ancestors") or e.get("hierarchicalAncestor") or [],

            # rank
            'rank': {
                'iri': rankIri,
                'label': rankLabel
            },

            # revision links
            'replaced_by': e.get("http://purl.obolibrary.org/obo/IAO_0100001"),
            'was_revision_of': e.get("http://www.w3.org/ns/prov#wasRevisionOf"),
            'had_revision': e.get("http://www.w3.org/ns/prov#hadRevision"),

            # external matches (raw list)
            'narrow_match': self.toArray(e.get("http://www.w3.org/2004/02/skos/core#narrowMatch") or [])
        }
        return mapped

    def mapReasonIriToText(self, reasonIri: Optional[str]) -> Optional[str]:
        if reasonIri == "http://purl.obolibrary.org/obo/IAO_0000229":
            return "SPLIT"
        if reasonIri == "http://purl.obolibrary.org/obo/IAO_0000227":
            return "MERGED"
        return None

    # -------------------- Seekers --------------------
    def seekOntologyTaxon(self, endpoint: str, params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        data = self.ols(endpoint, params)
        return data.get('elements')

    def seekOntologyTaxonByClassId(self, id_: str) -> List[Dict[str, Any]]:
        curr = self.seekOntologyTaxon('classes', {
            "http://purl.org/dc/terms/identifier": id_, "isObsolete": "false"
        }) or []
        obs = self.seekOntologyTaxon('classes', {
            "http://purl.org/dc/terms/identifier": id_, "isObsolete": "true"
        }) or []
        return curr + obs

    def seekOntologyTaxonByClassLabel(self, label: str) -> List[Dict[str, Any]]:
        curr = self.seekOntologyTaxon('classes', {"label": label, "isObsolete": "false"}) or []
        obs = self.seekOntologyTaxon('classes', {"label": label, "isObsolete": "true"}) or []
        return curr + obs

    def seekOntologyTaxonBySynonym(self, synonym: str) -> List[Dict[str, Any]]:
        return self.seekOntologyTaxon('classes', {"synonym": synonym}) or []

    def seekOntologyTaxonByIndividual(self, labelOrSyn: str) -> List[Dict[str, Any]]:
        indsLabel = self.seekOntologyTaxon('individuals', {'label': labelOrSyn}) or []
        indsSyn = self.seekOntologyTaxon('individuals', {'synonym': labelOrSyn}) or []
        all_inds = indsLabel + indsSyn
        parents = []
        seen = set()
        for ind in all_inds:
            pIri = self.normalizeValue(ind.get('directParent'))
            if pIri and pIri not in seen:
                seen.add(pIri)
                p = self.retrieveTaxonByIRI(pIri)
                if p and p.get("http://purl.org/dc/terms/identifier"):
                    parents.append(p)
        return parents

    def sortCandidates(self, arr: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def msl_num(el: Dict[str, Any]) -> int:
            return self.parseMsl(el.get("http://www.w3.org/2002/07/owl#versionInfo", ''))
        return sorted(arr, key=msl_num, reverse=True)

    # -------------------- Extras / Public helpers --------------------
    def getCurrentReplacements(self, idOrLabelOrEntity: Any) -> List[Dict[str, Any]]:
        res = self.resolveToLatest(idOrLabelOrEntity, {
            'replacements': True, 'enrichLineage': False, 'suggestions': False
        })

        if res.get('status') == 'current':
            return [res['current']]

        if res.get('status') == 'obsolete':
            if res.get('replacements'):
                return res['replacements']

            # fallback by label if no replaced_by
            obsolete = res.get('obsolete') or {}
            label = obsolete.get('label')
            if label:
                res2 = self.resolveToLatest(label, {
                    'replacements': True, 'enrichLineage': False, 'suggestions': False
                })
                if res2.get('status') == 'current' and res2.get('current'):
                    return [res2['current']]
                if res2.get('status') == 'obsolete' and res2.get('replacements'):
                    return res2['replacements']

        return []

    def findCandidates(self, idOrLabel: str) -> List[Dict[str, Any]]:
        if 'ICTV' in idOrLabel:
            candidates = self.seekOntologyTaxonByClassId(idOrLabel)
        else:
            candidates = self.seekOntologyTaxonByClassLabel(idOrLabel)
            if not candidates:
                candidates = self.seekOntologyTaxonBySynonym(idOrLabel)
            if not candidates:
                candidates = self.seekOntologyTaxonByIndividual(idOrLabel)
        if not candidates:
            return []
        candidates = self.sortCandidates(candidates)
        for el in candidates:
            el['_msl_number'] = self.parseMsl(el.get("http://www.w3.org/2002/07/owl#versionInfo", ''))
        return candidates

    def findLatest(self, idOrLabel: str) -> Optional[Dict[str, Any]]:
        res = self.resolveToLatest(idOrLabel, {
            'replacements': False, 'enrichLineage': False, 'suggestions': False
        })
        return res.get('current') or res.get('final') or res.get('obsolete')

    def getSynonyms(self, idOrLabelOrEntity: Any) -> List[str]:
        entity = self._resolveAsEntity(idOrLabelOrEntity)
        return list(dict.fromkeys(entity.get('synonyms', []))) if entity else []

    def getIndividuals(self, idOrLabelOrEntity: Any) -> Dict[str, Any]:
        entity = self._resolveAsEntity(idOrLabelOrEntity)
        if not entity or not entity.get('iri'):
            return {}
        enc = quote(quote(entity['iri'], safe=''), safe='')
        data = self.fetchit(f"{self.baseUrl}/classes/{enc}/individuals", {"size": 1000})
        return data

    def getIndividualsNames(self, idOrLabelOrEntity: Any) -> List[str]:
        data = self.getIndividuals(idOrLabelOrEntity)
        names = {}
        for ind in (data.get('elements') or []):
            label = ind.get('label') or ind.get("http://www.w3.org/2000/01/rdf-schema#label")
            label = self.normalizeValue(label)
            if label:
                names[label] = True
        return list(names.keys())

    def getAllFromRelease(self, release: str) -> List[Dict[str, Any]]:
        page = 0
        size = 1000
        all_items: List[Dict[str, Any]] = []
        while True:
            data = self.fetchit(f"{self.baseUrl}/classes", {
                "http://www.w3.org/2002/07/owl#versionInfo": release,
                "size": size,
                "page": page
            })
            batch = data.get('elements') or []
            for el in batch:
                all_items.append(self.mapEntity(el))
            page += 1
            if not batch:
                break
        return all_items

    def getTaxonByRelease(self, ictvId: str, release: str) -> Optional[Dict[str, Any]]:
        data = self.ols('classes', {
            "http://www.w3.org/2002/07/owl#versionInfo": release,
            "http://purl.org/dc/terms/identifier": ictvId
        })
        el = (data.get('elements') or [None])[0]
        return self.mapEntity(el) if el else None

    def getHistory(self, idOrLabelOrEntity: Any) -> List[Dict[str, Any]]:
        entityRaw = self._resolveAsEntity(idOrLabelOrEntity)
        if not entityRaw:
            return []

        # Ensure we traverse from a raw OLS entity
        entity = self.retrieveTaxonByIRI(entityRaw['iri']) or entityRaw

        seen = set()
        history: List[Dict[str, Any]] = []

        def walk(ent: Dict[str, Any]):
            mapped = self.mapEntity(ent)
            if not mapped.get('msl') or not mapped.get('ictv_id'):
                return
            mslKey = mapped['msl']
            if mslKey in seen:
                return
            seen.add(mslKey)

            mapped_enriched = self.enrichLineage(mapped)
            history.append(mapped_enriched)

            for key in ['was_revision_of', 'had_revision']:
                if mapped_enriched.get(key):
                    nxt = self.retrieveTaxonByIRI(mapped_enriched[key])
                    if nxt:
                        return walk(nxt)

        walk(entity)
        history.sort(key=lambda a: self.parseMsl(a.get('msl')), reverse=True)
        return history

    def getHistoricalParent(self, idOrLabelOrEntity: Any) -> Optional[Dict[str, Any]]:
        entity = self._resolveAsEntity(idOrLabelOrEntity)
        if not entity:
            return None
        for key in ['was_revision_of', 'had_revision']:
            if entity.get(key):
                parent = self.retrieveTaxonByIRI(entity[key])
                return self.mapEntity(parent) if parent else None
        return None

    def getObsolescenceReason(self, idOrLabelOrEntity: Any) -> Optional[str]:
        entity = self._resolveAsEntity(idOrLabelOrEntity)
        if not entity or not entity.get('is_obsolete', False):
            return None
        return entity.get('reason_iri')

    def getTextualObsolescenceReason(self, idOrLabelOrEntity: Any) -> Optional[str]:
        iri = self.getObsolescenceReason(idOrLabelOrEntity)
        return self.mapReasonIriToText(iri)

    # Internal: resolve input or entity to a mapped entity array.
    def _resolveAsEntity(self, idOrLabelOrEntity: Any) -> Optional[Dict[str, Any]]:
        if isinstance(idOrLabelOrEntity, dict) and 'iri' in idOrLabelOrEntity:
            return idOrLabelOrEntity
        res = self.resolveToLatest(idOrLabelOrEntity, {
            'replacements': True, 'enrichLineage': False, 'suggestions': False
        })
        if res.get('status') == 'current':
            return res.get('current')
        if res.get('status') == 'obsolete' and res.get('obsolete'):
            return res.get('obsolete')
        return None


# ======================================================================
#                           ICTV/NCBI Mapping
# ======================================================================

class ICTVtoNCBImapping:
    def __init__(self):
        self.sssomUrl: str = ('https://raw.githubusercontent.com/EVORA-project/virus-taxonomy-mappings/'
                              'refs/heads/dev/mappings/ictv_ncbitaxon_exact.sssom.tsv')
        self.ncbiMap: Optional[Dict[str, Dict[str, List[Dict[str, Any]]]]] = None  # {'forward': {}, 'reverse': {}}

    def setDifferentSssomUrl(self, sssomUrl: str) -> None:
        self.sssomUrl = sssomUrl

    def loadNcbiMap(self) -> None:
        if self.ncbiMap is not None:
            return
        try:
            r = requests.get(self.sssomUrl, timeout=30)
            r.raise_for_status()
            text = r.text
        except requests.RequestException as e:
            raise Exception("Failed to fetch mapping file") from e

        self.ncbiMap = {'forward': {}, 'reverse': {}}
        rows = [line for line in text.splitlines() if line.strip()]
        if rows:
            rows = rows[1:]  # skip header

        for line in rows:
            cols = line.split('\t')
            if len(cols) < 5:
                continue
            ictvCurie = cols[0]
            ncbiCurie = cols[3].lower()
            label = cols[4]

            # forward
            self.ncbiMap['forward'].setdefault(ictvCurie, []).append({'ncbiCurie': ncbiCurie, 'label': label})

            # reverse
            m = re.match(r'^ictv:([^/]+)/([^/]+)$', ictvCurie, flags=re.IGNORECASE)
            if m:
                self.ncbiMap['reverse'].setdefault(ncbiCurie, []).append({
                    'ictv_curie': ictvCurie,
                    'msl': m.group(1),
                    'ictv_id': m.group(2),
                    'label': label
                })

    # ICTV → NCBI (same MSL).
    def getNcbiTaxon(self, ictvId: str, msl: str) -> List[Dict[str, Any]]:
        self.loadNcbiMap()
        curie = f"ictv:{msl}/{ictvId}"
        return self.ncbiMap['forward'].get(curie, [])

    # NCBI → ICTV (keep only highest MSL per ICTV ID).
    def getIctvFromNcbi(self, ncbiId: str) -> List[Dict[str, Any]]:
        self.loadNcbiMap()
        key = (ncbiId or '').strip().lower()
        if not key.startswith('ncbitaxon:'):
            key = 'ncbitaxon:' + key
        hits = self.ncbiMap['reverse'].get(key, [])
        best: Dict[str, Dict[str, Any]] = {}

        for h in hits:
            m = re.search(r'MSL(\d+)', h.get('msl', ''), flags=re.IGNORECASE)
            mslNum = int(m.group(1)) if m else 0
            ictv_id = h.get('ictv_id')
            if ictv_id and (ictv_id not in best or mslNum > best[ictv_id]['_msl']):
                best[ictv_id] = dict(h)
                best[ictv_id]['_msl'] = mslNum

        for v in best.values():
            v.pop('_msl', None)
        return list(best.values())
