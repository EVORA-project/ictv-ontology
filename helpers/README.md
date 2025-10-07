# ICTV Ontology – Helpers

This folder provides a lightweight helper classes to access the **ICTV Ontology API** as served through the [Ontology Lookup Service (OLS4)](https://www.ebi.ac.uk/ols4/ontologies/ictv).

---

## 📘 Overview

The js subfolder contains `ictv-api.js` helper that makes it easy to query ICTV taxonomic data from JavaScript environments, whether you are:
- Building a browser-based tool (e.g., ICTV Resolver),
- Embedding taxonomic lookups in web applications,
- Writing scripts to test ontology term resolution.

It handles:
- Querying by ICTV identifiers, NCBI Taxon IDs, or synonyms,  
- Finding historical taxa and resolving to the latest ICTV term,  
- Returning clean JSON responses from the OLS API.

---

## 📦 File

| File | Description |
|------|--------------|
|[`ictv-api.js`](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/js/ictv-api.js) | Helper class for interacting with the ICTV ontology API (ES6 module). |

---

## 🚀 Usage

### Import directly from GitHub (recommended)

```html
<script type="module">
  import { ICTVApi } from 'https://raw.githubusercontent.com/EVORA-project/ictv-ontology/main/helpers/js/ictv-api.js';

  const api = new ICTVApi();

  // Example: resolve a term by label or ICTV ID
  api.resolveToLatest('SARS-CoV')
    .then(result => console.log(result))
    .catch(err => console.error(err));
</script>
