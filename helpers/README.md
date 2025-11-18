# ICTV Ontology – Helper Libraries

This directory provides lightweight client libraries that make it easy to query the **ICTV Ontology API**, as served through the  
👉 **Ontology Lookup Service (OLS)**: https://www.ebi.ac.uk/ols4/ontologies/ictv

These helpers allow you to resolve ICTV taxon names, historical ICTV identifiers, IRIs, and NCBI Taxon IDs to the **current ICTV taxon**, including lineage and replacement history.


---

## 📘 Contents

Helpers are available in:

- **JavaScript** ([`js/ictv-api.js`](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/js/ictv-api.js))
- **Python** ([`python/ictv-api.py`](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/python/ictv-api.py))
- **PHP** ([`php/ictv-api.php`](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/js/ictv-api.php))

```
helpers/
 ├── js/
 │    └── ictv-api.js
 ├── python/
 │    └── ictv-api.py
 └── php/
      └── ictv-api.php
```

---

## 📚 Helper Implementations

### 🔹 JavaScript (`js/ictv-api.js`)

ES module suitable for browsers, Node.js, and static sites.

Handles:

- Resolving ICTV IDs, IRIs, labels, synonyms
- Mapping NCBI Taxon IDs ↔ ICTV IDs
- Replacement chains and obsolete terms
- Fetching history across releases

No dependencies — pure ES6.

---

### 🔹 Python (`python/ictv-api.py`)

Lightweight client using `requests`.

Features:

- Full term resolution
- ICTV ↔ NCBI mapping
- Fetching releases, history, lineage
- Mirrors JS helper behaviour

---

### 🔹 PHP (`php/ictv-api.php`)

Standalone PHP helper using cURL.

Ideal for:

- Server-side integrations
- CMS modules and backends

Equivalent API to JS & Python helpers.

---

## 🚀 Quick Start Examples

### JavaScript

```html
<script type="module">
  import { ICTVApi } from 'https://cdn.jsdelivr.net/gh/EVORA-project/ictv-ontology/helpers/js/ictv-api.js';

  const api = new ICTVApi();
  const result = await api.resolveToLatest("SARS-CoV-2");
  console.log(result);
</script>
```

### Python

```python
from ictv_api import ICTVOLSClient

client = ICTVOLSClient()
res = client.resolveToLatest("Zika virus")
print(res)
```

### PHP

```php
require_once "ictv-api.php";

$api = new ICTVOLSClient();
$res = $api->resolveToLatest("Tehran virus");
print_r($res);
```

---

## 🌐 Live Showcase

👉 **ICTV Taxon Resolver**  
https://evora-project.github.io/ictv-resolver/

Source code:  
https://github.com/EVORA-project/ictv-resolver

---

## 🧠 Dependencies

| Language  | Dependencies |
|----------|--------------|
| JavaScript | None |
| Python | requests |
| PHP | cURL |

---

## 🔗 Related Resources

- ICTV Ontology on OLS: https://www.ebi.ac.uk/ols4/ontologies/ictv  
- ICTV Taxonomy: https://ictv.global/taxonomy  
- EVORA Project ICTV Ontology Repository: https://github.com/EVORA-project/ictv-ontology  
- ICTV Resolver Demo: https://evora-project.github.io/ictv-resolver/

---

## ⚖️ License

- ICTV data: CC BY 4.0  
- SSSOM mapping: CC0  
- Helpers code: MIT License — © EVORA Project
