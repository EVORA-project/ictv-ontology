# ICTV Python API Helper (`ictv-api.py`)

Lightweight Python helper to query the **ICTV Ontology API** (via OLS4) and resolve virus taxon names, historical ICTV identifiers, and NCBI Taxon IDs to the corresponding current ICTV taxon.

This is the Python counterpart of:

- `ictv-api.js`
- `ictv-api.php`
- `ictv-api.py` (this file)

It provides:

- `ICTVOLSClient` — main client for ICTV Ontology / OLS  
- `ICTVtoNCBImapping` — SSSOM-based ICTV ↔ NCBI Taxon mapping helper

---

## 1. Requirements

- Python **3.8+**
- `requests` library

Install:

```bash
pip install requests
```

---

## 2. Installation

Place the file as:

```
helpers/python/ictv-api.py
```

Use it as follows:

```python
from helpers.python.ictv_api import ICTVOLSClient

client = ICTVOLSClient()
res = client.resolveToLatest("Zika virus")

if res["status"] == "current":
    print(res["current"]["label"], res["current"]["ictv_curie"])
```

---

## 3. Constructor

```python
client = ICTVOLSClient(
    baseUrl="https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv"
)
```

The default endpoint is recommended.

---

## 4. Normalized ICTV entities

The client returns mapped objects like:

```python
{
    "msl": "MSL33",
    "ictv_id": "ICTV20040588",
    "ictv_curie": "ictv:MSL33/ICTV20040588",
    "iri": "http://ictv.global/id/MSL33/ICTV20040588",
    "label": "Zika virus",
    "synonyms": [...],
    "is_obsolete": False,
    "obsolescence_reason": None,
    "rank": {"iri": "...", "label": "species"},
    ...
}
```

When lineage enrichment is enabled:

- `direct_parent_label`
- `lineage`

are added.

---

## 5. Public API (ICTVOLSClient)

### 5.1 resolveToLatest()

```python
res = client.resolveToLatest("Tehran virus")
```

Possible results:

#### Current
```python
{"status": "current", "current": {...}, "ncbi": [...]}
```

#### Obsolete
```python
{
  "status": "obsolete",
  "obsolete": {...},
  "reason": "MERGED",
  "replacements": [...],
  "final": {...}
}
```

#### Not found
```python
{"status": "not-found", "suggestions": [...]}
```

---

### 5.2 getTaxonByIRI()

```python
entity = client.getTaxonByIRI("http://ictv.global/id/MSL33/ICTV20040588")
```

---

### 5.3 getCurrentReplacements()

```python
client.getCurrentReplacements("ICTV19990862")
```

---

### 5.4 findCandidates()

```python
client.findCandidates("Zika virus")
```

---

### 5.5 findLatest()

```python
client.findLatest("Zika virus")
```

---

### 5.6 Synonym helpers

```python
client.getSynonyms("Zika virus")
```

---

### 5.7 Individuals

```python
client.getIndividuals("Zika virus")
client.getIndividualsNames("Zika virus")
```

---

### 5.8 getAllFromRelease()

```python
client.getAllFromRelease("MSL33")
```

---

### 5.9 getTaxonByRelease()

```python
client.getTaxonByRelease("ICTV20040588", "MSL33")
```

---

### 5.10 getHistory()

```python
history = client.getHistory("Zika virus")
```

---

### 5.11 getHistoricalParent()

```python
parent = client.getHistoricalParent("Zika virus")
```

---

### 5.12 Obsolescence utilities

```python
client.getObsolescenceReason("Some virus")
client.getTextualObsolescenceReason("Some virus")
```

---

## 6. ICTV ↔ NCBI mapping

### Change mapping file

```python
mapper = ICTVtoNCBImapping()
mapper.setDifferentSssomUrl("local.sssom.tsv")
```

### ICTV → NCBI

```python
mapper.getNcbiTaxon("ICTV20040588", "MSL33")
```

### NCBI → ICTV

```python
mapper.getIctvFromNcbi("64320")
```

---

## 7. Error handling

Network errors → `Exception`  
Not-found cases → dict with `"status": "not-found"`

---

## 8. Licensing

- ICTV Ontology data: **CC BY 4.0**
- SSSOM mapping: **CC0**
- Python helper code: **MIT License**

If you publish a service using this helper, acknowledge ICTV & EVORA Project.
