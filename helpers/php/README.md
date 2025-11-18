# ICTV PHP API Helper (`ictv-api.php`)

Lightweight PHP helper to query the **ICTV Ontology API** (served via the [Ontology Lookup Service](https://www.ebi.ac.uk/ols4/ontologies/ictv)) and resolve virus taxon names, historical ICTV identifiers, and NCBI Taxon IDs to the corresponding current ICTV taxon.

- Ontology & API: ICTV Ontology via OLS4
- Data © International Committee on Taxonomy of Viruses (ICTV), CC BY 4.0
- Helper code © EVORA Project — MIT License

This PHP helper exposes 2 classes:

- `ICTVOLSClient` — main client for OLS / ICTV ontology
- `ICTVtoNCBImapping` — helper for ICTV ↔ NCBI Taxon mappings based on SSSOM

---

## 1. Requirements

- PHP 7+ (or any version with):
  - `curl` extension enabled
  - `allow_url_fopen` enabled (for reading the SSSOM file via `file()`)
- Network access to:
  - `https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv`
  - `https://raw.githubusercontent.com/EVORA-project/virus-taxonomy-mappings/...` (default SSSOM mapping)

---

## 2. Installation

Copy the helper file into your project, then include it in your PHP code:

```php
require_once __DIR__ . '/helpers/php/ictv-api.php';

$client = new ICTVOLSClient();
```

If you prefer a different mapping file (e.g. local mirror), you can change it via:

```php
$mapper = new ICTVtoNCBImapping();
$mapper->setDifferentSssomUrl('https://example.org/my-ictv-ncbi.sssom.tsv');

// ICTVOLSClient currently creates its own mapper internally, but you can
// extend the class to inject your own mapper if needed.
```

---

## 3. Constructor

```php
$client = new ICTVOLSClient(string $baseUrl = 'https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv');
```

- **$baseUrl** (optional): base OLS4 endpoint for the ICTV ontology.  
  For most users, the default is fine.

Internally, the client:

- uses `curl` to query OLS4  
- uses `ICTVtoNCBImapping` to connect ICTV taxa to NCBI Taxon IDs  
- caches OLS responses in memory for the duration of the request

---

## 4. Main concepts

Most methods return either:

- **Normalized ICTV entities** (associative arrays) similar to the JS `IctvEntity` type, or  
- **Resolution results** with a `status` field (`current`, `obsolete`, `not-found`), plus additional data.

### 4.1 Normalized ICTV entity

A normalized ICTV entity looks like:

```php
$entity = [
    'msl'        => 'MSL33',
    'ictv_id'    => 'ICTV20040588',
    'ictv_curie' => 'ictv:MSL33/ICTV20040588',
    'iri'        => 'http://ictv.global/id/MSL33/ICTV20040588',

    'label'      => 'Zika virus',
    'synonyms'   => ['Zika virus isolate XYZ', /* ... */],

    'is_obsolete'         => false,
    'obsolescence_reason' => null,    // "MERGED" / "SPLIT" / null
    'reason_iri'          => null,

    'direct_parent_iri'   => 'http://ictv.global/id/MSL33/ICTV20040587',
    'ancestors_iris'      => [/* ... */],

    'rank' => [
        'iri'   => 'http://purl.obolibrary.org/obo/NCBITaxon_species',
        'label' => 'species',
    ],

    'replaced_by'     => null,        // string|string[]|null
    'was_revision_of' => null,        // IRI of previous revision
    'had_revision'    => null,        // IRI of next revision

    'narrow_match'    => [
        // raw list of SKOS narrowMatch values as returned by OLS
    ],
];
```

Some helpers (like `enrichLineage`) add:

- `direct_parent_label` — label of the direct parent taxon  
- `lineage` — array of ancestor labels, root → parent

---

## 5. Public API (ICTVOLSClient)

### 5.1 `resolveToLatest($inputRaw, array $options = [...])`

Resolve any input (ICTV ID, IRI, label, synonym, NCBI taxid, individual) to the latest ICTV taxon.

```php
$result = $client->resolveToLatest('Zika virus');
```

**Options:**

```php
[
    'replacements'   => true,   // follow replacement chains when obsolete
    'enrichLineage'  => true,   // add parent and lineage labels to mapped entities
    'suggestions'    => true,   // return suggestions when not found
]
```

**Return structure:**

```php
// status: "current"
[
    'status'  => 'current',
    'input'   => 'Zika virus',
    'current' => $entity,       // normalized ICTV entity
    'ncbi'    => [
        ['ncbiCurie' => 'ncbitaxon:64320', 'label' => 'Zika virus'],
        // ...
    ],
];
```

```php
// status: "obsolete"
[
    'status'       => 'obsolete',
    'input'        => 'ICTV1999xxxxx',
    'obsolete'     => $obsoleteEntity,
    'reason'       => 'MERGED',      // or "SPLIT" or null
    'replacements' => [$entity1, $entity2, /* ... */], // final replacement taxa
    'final'        => $entity1,      // best replacement (latest MSL), if any
];
```

```php
// status: "not-found"
[
    'status'      => 'not-found',
    'input'       => 'Some name',
    'reason'      => 'empty input',  // optional extra reason
    'suggestions' => ['Possible virus 1', 'Possible virus 2', /* ... */],
];
```

#### Input formats supported

- ICTV ID: `"ICTV19990695"`  
- ICTV IRI: `"http://ictv.global/id/MSL22/ICTV20040588"`  
- Label / former taxon name / virus name: `"Tehran virus"`  
- NCBI taxid: `"64320"` or `"ncbitaxon:64320"`  

---

### 5.2 `getTaxonByIRI($iri)`

Fetch and map an ICTV entity directly by its IRI.

```php
$entity = $client->getTaxonByIRI('http://ictv.global/id/MSL33/ICTV20040588');
```

Returns either a normalized entity array or `null` if not found.

---

### 5.3 `getCurrentReplacements($idOrLabelOrEntity)`

Return the **current entity/entities** for an input that might be obsolete.

```php
$current = $client->getCurrentReplacements('ICTV19990862');

foreach ($current as $e) {
    echo $e['label'] . ' ' . $e['ictv_curie'] . PHP_EOL;
}
```

- If the input resolves to a current entity → returns an array with that single entity.  
- If obsolete with replacements → returns final replacement entities.  
- If no clear resolution → returns an empty array.

---

### 5.4 `findCandidates($idOrLabel)`

Return raw OLS candidates (before mapping) for a label or ICTV ID.

```php
$candidates = $client->findCandidates('Zika virus');
```

Useful for debugging or custom selection.

---

### 5.5 `findLatest($idOrLabel)`

Return the best (latest) mapped entity for a label or ICTV ID.

```php
$entity = $client->findLatest('Zika virus');
```

---

### 5.6 `getSynonyms($idOrLabelOrEntity)`

Return a deduplicated list of synonyms for a taxon.

```php
$synonyms = $client->getSynonyms('Zika virus');
```

---

### 5.7 `getIndividuals($idOrLabelOrEntity)` / `getIndividualsNames($idOrLabelOrEntity)`

Get individuals under a class, or just their names.

```php
$data  = $client->getIndividuals('Zika virus');
$names = $client->getIndividualsNames('Zika virus');
```

---

### 5.8 `getAllFromRelease(string $release)`

Fetch all taxa for a specific MSL release.

```php
$all = $client->getAllFromRelease('MSL33');
```

Returns an array of mapped entities.

---

### 5.9 `getTaxonByRelease($ictvId, $release)`

Fetch a specific taxon by ICTV ID and MSL.

```php
$entity = $client->getTaxonByRelease('ICTV20040588', 'MSL33');
```

---

### 5.10 `getHistory($idOrLabelOrEntity)`

Get the full history (revision chain) for a taxon across MSLs.

```php
$history = $client->getHistory('Zika virus');

foreach ($history as $h) {
    echo $h['msl'] . ': ' . $h['label'] . ' [' . $h['ictv_id'] . ']' . PHP_EOL;
}
```

Sorted from latest MSL to earliest.

---

### 5.11 `getHistoricalParent($idOrLabelOrEntity)`

Return the previous or next revision in the history chain, if any.

---

### 5.12 `getObsolescenceReason($idOrLabelOrEntity)` / `getTextualObsolescenceReason($idOrLabelOrEntity)`

```php
$reasonIri  = $client->getObsolescenceReason('Some old virus');
$reasonText = $client->getTextualObsolescenceReason('Some old virus'); // "SPLIT", "MERGED", or null
```

---

## 6. ICTV ↔ NCBI mapping (ICTVtoNCBImapping)

The `ICTVtoNCBImapping` class is used internally by `ICTVOLSClient` but can also be used directly.

### 6.1 `setDifferentSssomUrl($sssomUrl)`

Use a different mapping file (for example, a local copy):

```php
$mapping = new ICTVtoNCBImapping();
$mapping->setDifferentSssomUrl('/path/to/ictv_ncbitaxon_exact.sssom.tsv');
```

---

### 6.2 `getNcbiTaxon($ictvId, $msl)`

ICTV → NCBI mapping for a given ICTV ID + release.

```php
$ncbi = $mapping->getNcbiTaxon('ICTV20040588', 'MSL33');
// e.g. [['ncbiCurie' => 'ncbitaxon:64320', 'label' => 'Zika virus'], /* ... */]
```

---

### 6.3 `getIctvFromNcbi($ncbiId)`

NCBI → ICTV mapping; returns only the best (latest MSL) entry per ICTV ID.

```php
$ictvHits = $mapping->getIctvFromNcbi('64320');
// or
$ictvHits = $mapping->getIctvFromNcbi('ncbitaxon:64320');
```

Each result:

```php
[
  'ictv_curie' => 'ictv:MSL33/ICTV20040588',
  'msl'        => 'MSL33',
  'ictv_id'    => 'ICTV20040588',
  'label'      => 'Zika virus',
];
```

---

## 7. Error handling

- Network / HTTP errors throw `Exception` (e.g. OLS down, mapping file unavailable).  
- “Not found” cases are returned as arrays with `status => 'not-found'`.  

Wrap calls with `try/catch` if you need to handle network failures:

```php
try {
    $res = $client->resolveToLatest('Some virus name');
} catch (Exception $e) {
    error_log('ICTV API error: ' . $e->getMessage());
}
```

---

## 8. Licensing

- ICTV data as included in the ICTV ontology: ICTV CC BY 4.0  
- SSSOM mapping: CC0 (see the `virus-taxonomy-mappings` repository)  
- Helper code (`ictv-api.php`): © EVORA Project — MIT License

If you build a public interface using this helper, please acknowledge both ICTV and the EVORA Project in your documentation or About page.
