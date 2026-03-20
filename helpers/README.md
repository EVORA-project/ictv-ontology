> Resolve virus taxa across ICTV releases programmatically.
<p align="center">
  <img src="https://ictv.global/sites/default/files/inline-images/ictvLogo-head.png" alt="ICTV Logo" height="100" style="vertical-align: middle; margin: 0 30px;" />
  <img src="https://raw.githubusercontent.com/EVORA-project/ictv-resolver/main/assets/images/logo/logo.svg" alt="EVORA Project Logo" height="80" style="vertical-align: middle; margin: 0 30px;" />
</p>

<p align="center">
  <a href="https://github.com/EVORA-project/ictv-ontology/tree/main/helpers">
    <img src="https://img.shields.io/badge/View%20on-GitHub-black?logo=github&style=for-the-badge">
  </a>
</p>

# Programmatic access to the official taxonomy of viruses with **ICTV Ontology API** – Helper Libraries & Direct API Access
## 📑 Quick Navigation

- [What is the ICTV OLS API?](#-what-is-the-ictv-ols-api)
- [Two approaches](#-two-approaches-to-access-the-ictv-ols-api)
- [Helper libraries overview](#-helper-libraries-overview)
- [Quick start with helper libraries](#-quick-start-with-helper-libraries)
- [Choose your helper](#-choose-your-helper)
- [Direct OLS API access](#-advanced-direct-ols-api-access)
- [Common use cases](#-common-use-cases-with-examples)
- [Response structure](#-response-structure-and-navigation)
- [Related resources](#-related-resources)
- [Support & feedback](#-support--feedback)

## 🌍 What is the ICTV OLS API?

The EVORA project (European Viral Outbreak Response Alliance) in collaboration with the ICTV (International Committee on Taxonomy of Viruses) has developed a **public programmatic access to the official taxonomy of viruses** by transforming ICTV releases into the **ICTV ontology** and serving it through the **Ontology Lookup Service (OLS)** API. 

OLS is a REST-based web service hosted by EMBL-EBI that provides programmatic access to biomedical ontologies, including the ICTV ontology. This makes it possible to retrieve structured semantic information about virus taxa and their relationships across ICTV releases.

This is useful for:

- automated virus taxon identification pipelines
- integration into bioinformatics workflows
- ensuring consistent taxonomy across applications
- tracking historical and current virus classifications
  
 With the ICTV OLS API, you can:
 
- **query taxonomic entities** by taxon name, identifier, or IRI
- **resolve historical and obsolete taxa** to their current replacements using former taxon names, virus names, synonyms, ICTV identifiers, or NCBI taxonomy identifiers
- **retrieve lineage information of a taxon** within a specific ICTV release
- **access synonyms and historical names** for virus taxonomy
- **map NCBI Taxon identifiers** to ICTV entities via a complementary SSSOM mapping
- **retrieve complete ICTV releases** in structured, machine-readable format

### 📖 API Documentation

- **OLS API documentation:** [https://www.ebi.ac.uk/ols4/api-docs](https://www.ebi.ac.uk/ols4/api-docs)
- **ICTV ontology browser page on OLS:** [https://www.ebi.ac.uk/ols4/ontologies/ictv](https://www.ebi.ac.uk/ols4/ontologies/ictv)
- **ICTV ontology API metadata endpoint:** [https://www.ebi.ac.uk/ols4/api/ontologies/ictv](https://www.ebi.ac.uk/ols4/api/ontologies/ictv)

The ICTV OLS API follows REST principles and returns JSON responses, making it accessible from any programming language or environment that can make HTTP requests.

---

## 🎯 Two Approaches to Access the ICTV OLS API

The ICTV ontology data can be accessed in **two complementary ways**:

### ✅ **Approach 1: Helper Libraries (recommended for most users)**

Lightweight client libraries that **encapsulate the complexity** of direct OLS queries and provide a simple, domain-friendly interface for common use cases.

**Use this if you:**

- want quick integration with minimal code
- need standard ICTV resolution workflows
- prefer simplified language-specific APIs
- work in JavaScript, Python, or PHP

### 🔧 **Approach 2: Direct OLS API access**
Direct HTTP access to the OLS API endpoints, giving you full control and flexibility for custom queries and advanced workflows.

**Use this if you:**

- need fine-grained control over API parameters
- have custom or non-standard query patterns
- want to build your own abstractions
- are integrating into systems where helper libraries are not available
- need to understand the raw OLS response structure

---

## 📘 Helper Libraries Overview

This directory provides lightweight client libraries that make it easy to query the **ICTV Ontology API**, as served through the OLS API. 

These helpers allow you to resolve ICTV taxon names, historical ICTV identifiers, IRIs, virus names and NCBI Taxon IDs to the **current ICTV taxon**, including lineage and replacement history.


### 📦 Available Implementations

Helpers are available in three languages:


- **JavaScript** ([`js/ictv-api.js`](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/js/ictv-api.js))
- **Python** ([`python/ictv-api.py`](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/python/ictv-api.py))
- **PHP** ([`php/ictv-api.php`](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/php/ictv-api.php))

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

## 🚀 Quick Start with Helper Libraries

### 🔹 JavaScript (`js/ictv-api.js`)

ES module suitable for browsers, Node.js, and static sites.

**Installation:** Simply import from CDN or local file.

```javascript
import { ICTVApi } from 'https://cdn.jsdelivr.net/gh/EVORA-project/ictv-ontology/helpers/js/ictv-api.js';

const api = new ICTVApi();
const result = await api.resolveToLatest("SARS-CoV-2");
console.log(result);
```
**Note:** Requires a module-compatible environment. Use in HTML with `script type="module">` or in modern Node.js projects with `"type": "module"` in package.json.

**Features:**

- resolution of ICTV IDs, IRIs, taxon or virus labels, and synonyms
- ICTV ↔ NCBI Taxon mapping
- replacement chains and obsolete term resolution
- taxon history retrieval
- individual/isolate resolution through their parent class

**No dependencies** — pure ES module.

👉 **Full JS helper documentation:** See [`helpers/js/README.md`](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/js/README.md)

---

### 🔹 Python (`python/ictv-api.py`)

**Best for:** Data pipelines, scripts, Jupyter notebooks, ETL workflows

Lightweight client using the `requests` library.

**Installation:** Copy `python/ictv-api.py` to your project.

```python
from ictv_api import ICTVOLSClient

client = ICTVOLSClient()
result = client.resolveToLatest("Zika virus")
print(result)
```

**Features:**

- full term resolution (all input types)
- ICTV ↔ NCBI mapping
- **complete release export** with pagination handling (`getAllFromRelease()`)
- **release-specific taxon queries** (`getTaxonByRelease()`)
- individual/isolate queries
- synonym, history, and obsolescence reason retrieval

👉 **Full Python helper documentation:** See [`helpers/python/README.md`](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/python/README.md)

---

### 🔹 PHP (`php/ictv-api.php`)

**Best for:** Server-side integrations, CMS backends, database imports

Standalone PHP helper using cURL (built-in).

**Installation:** Copy `php/ictv-api.php` to your project.

```php
require_once "ictv-api.php";

$api = new ICTVOLSClient();
$result = $api->resolveToLatest("Tehran virus");
print_r($result);
```

**Features:** 

- full term resolution (all input types)
- ICTV ↔ NCBI mapping
- **complete release export** with pagination handling (`getAllFromRelease()`)
- **release-specific taxon queries** (`getTaxonByRelease()`)
- individual/isolate queries
- synonym, history, and obsolescence reason retrieval


👉 **Full PHP helper documentation:** See [`helpers/php/README.md`](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/php/README.md)

---

## 📚 Choose Your Helper

| Feature | JavaScript | Python | PHP |
|---------|:---:|:---:|:---:|
| **Basic resolution** | ✅ | ✅ | ✅ |
| **Bulk export (`getAllFromRelease`)** | ❌ | ✅ | ✅ |
| **Release-specific queries** | ❌ | ✅ | ✅ |
| **Dependencies** | None | `requests` | `curl` (built-in) |
| **Best for** | 🌐 Web | 📊 Data pipelines | 🖥️ Server-side |
| **Full Docs** | [js/README](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/js/README.md) | [python/README](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/python/README.md) | [php/README](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/php/README.md) |


---

## 📚 Helper Library Architecture

### Common Resolution Strategy

All three helper implementations follow the same general resolution strategy:

1. recognize ICTV IRIs and identifiers
2. optionally map NCBI Taxon identifiers to ICTV taxa
3. search classes by label and synonym
4. search individuals when needed and resolve them upward through their parent class
5. follow replacement chains when an entity is obsolete until final non-obsolete taxa are reached

### Normalized Output

The helper libraries return a **normalized ICTV taxon object** containing:

- Identifiers and IRI
- Label and synonyms
- Rank and lineage
- Obsolescence status
- Revision links
- NCBI mappings (where available)

This abstraction allows developers to focus on domain logic rather than on raw OLS API response handling.

---

## 🌐 Live Implementation Example

👉 **ICTV Taxon Resolver**  
[https://evora-project.github.io/ictv-resolver/](https://evora-project.github.io/ictv-resolver/)

A browser-based demonstration of the helper logic. It accepts:

- historical or current viral taxa from any rank
- virus names
- ICTV identifiers
- IRIs
- NCBI Taxon identifiers

and returns the latest accepted ICTV taxon with lineage and mapping information.

**Source code:** [https://github.com/EVORA-project/ictv-resolver](https://github.com/EVORA-project/ictv-resolver)


---

# 🔧 Advanced: Direct OLS API Access

For users who need direct access to the ICTV Ontology Lookup Service API without using helper libraries, this section provides guidance on constructing and executing OLS API queries.

👉 **Official OLS Documentation**: [https://www.ebi.ac.uk/ols4/api-docs](https://www.ebi.ac.uk/ols4/api-docs)

## 📡 OLS API Endpoints Overview

The ICTV Ontology is exposed through two main sets of OLS endpoints:

### v1 Endpoints (legacy)

[https://www.ebi.ac.uk/ols4/api/ontologies/ictv](https://www.ebi.ac.uk/ols4/api/ontologies/ictv)


- **Use case:** Legacy integrations, access to features like `/api/suggest`
- **Features:** Still include useful search and suggestion features
- **Response format:** Original OLS v1 structure

**Examples:**
- List all terms: [https://www.ebi.ac.uk/ols4/api/ontologies/ictv/terms?page=0&size=1000](https://www.ebi.ac.uk/ols4/api/ontologies/ictv/terms?page=0&size=1000)
- Search: [https://www.ebi.ac.uk/ols4/api/search?ontology=ictv&q=Sarbecovirus](https://www.ebi.ac.uk/ols4/api/search?ontology=ictv&q=Sarbecovirus)

---

### v2 endpoints (recommended)

[https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv](https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv)


- **Use case:** integrations requiring richer metadata
- **Features:** Enhanced entity linking, better obsolescence handling
- **Response format:** Extended JSON with linked entity details

**Examples:**
- List current classes: `GET /api/v2/ontologies/ictv/classes`
- Get specific class: `GET /api/v2/ontologies/ictv/classes/{DOUBLE_URL_ENCODED_IRI}`
- Get specific entity by IRI: `GET /api/v2/ontologies/ictv/entities/{DOUBLE_URL_ENCODED_IRI}`

---

## 🎯 Common Use Cases with Examples

### Use Case 1: Building a Local Cache of a former release

If you want to retrieve all classes for one ICTV release, your code can query the `classes` endpoint while filtering by the release value stored in `owl:versionInfo`, with pagination and the includeObsoleteEntities set to true as all former releases terms are marked as obsolete.

Example pattern:

```
GET /api/v2/ontologies/ictv/classes?http%3A%2F%2Fwww.w3.org%2F2002%2F07%2Fowl%23versionInfo=MSL39&page=0&size=10&includeObsoleteEntities=true
```

**Parameters:**
- `page`: Page number (0-indexed)
- `size`: Number of items per page (up to 1000)
- `http%3A%2F%2Fwww.w3.org%2F2002%2F07%2Fowl%23versionInfo`: version info corresponding to the MSL number in the ICTV ontology
- `includeObsoleteEntities`: boolean set to `true` to include obsolete terms

**An iteration loop can simply handle paginated results to retrieve all terms**

**Response structure:** JSON array of classes objects with IRIs, labels, synonyms, and metadata.

### Use Case 2: Building a Local Cache of the latest release
**Note:** As the ICTV ontology is a unified ontology of all ICTV releases (made available online on OLS typically 24H after a new ICTV release), as all the previous releases terms are marked as obsolete and as the classes endpoint has false for default value of the includeObsoleteEntities parameter,  omitting the versionInfo and the includeObsoleteEntities will automatically return the taxonomic terms of the most recent ICTV release.

example: [https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv/classes?page=0&size=1000](https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv/classes?page=0&size=1000)

**Example response fragment:**
```json
{
  "page" : 0,
  "numElements" : 1000,
  "totalPages" : 21,
  "totalElements" : 20845,
  "elements" : [ {
    "appearsIn" : [ "ictv" ],
    "curie" : "ICTV19710003",
    "directAncestor" : [ "http://ictv.global/id/MSL40/ICTV20080005", "http://ictv.global/id/MSL40/ICTV201857095", "http://ictv.global/id/MSL40/ICTV201907198", "http://ictv.global/id/MSL40/ICTV201907209", "http://ictv.global/id/MSL40/ICTV201907210", "http://purl.obolibrary.org/obo/NCBITaxon_10239" ],
    "directParent" : [ "http://ictv.global/id/MSL40/ICTV20080005" ],
    "hasDirectChildren" : true,
    "hasDirectParents" : true,
    "hasHierarchicalChildren" : true,
    "hasHierarchicalParents" : true,
    "hierarchicalAncestor" : [ "http://ictv.global/id/MSL40/ICTV20080005", "http://ictv.global/id/MSL40/ICTV201857095", "http://ictv.global/id/MSL40/ICTV201907198", "http://ictv.global/id/MSL40/ICTV201907209", "http://ictv.global/id/MSL40/ICTV201907210", "http://purl.obolibrary.org/obo/NCBITaxon_10239" ],
    "hierarchicalParent" : [ "http://ictv.global/id/MSL40/ICTV20080005" ],
    "hierarchicalProperty" : "http://www.w3.org/2000/01/rdf-schema#subClassOf",
    "imported" : false,
    "iri" : "http://ictv.global/id/MSL40/ICTV19710003",
    "isDefiningOntology" : false,
    "isObsolete" : false,
    "isPreferredRoot" : false,
    "label" : [ "Picornaviridae" ],
    "linkedEntities" : {
      "http://ictv.global/id/MSL39/ICTV19710003" : {
        "numAppearsIn" : 1.0,
        "hasLocalDefinition" : true,
        "label" : [ "Picornaviridae" ],
        "curie" : "ICTV19710003",
        "type" : [ "class", "entity" ]
      },
    ...

}
```

---

### Use Case 3: Resolving Historical References

**Objective:** Find the current accepted ICTV taxon for a viral taxon that may be known by a historical or obsolete taxon name.

#### Step 1: Search for the Historical Name (Including Obsolete Terms)

```
https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv/classes?label=severe%20acute%20respiratory%20syndrome%20coronavirus&includeObsoleteEntities=true
```

**Parameters:**
- `label`: The taxon name to search for (URL-encoded)
- `includeObsoleteEntities`: Set to `true` to include obsolete terms

**Response:** List of matching classes, including obsolete ones.

**Note:** Except in case where it is already known that the searched term is obsolete, it is a good practice to run a first search with `includeObsoleteEntities=false` to seek in the most recent ICTV release first.

---

#### Step 2: Follow the Replacement Chain

When an obsolete entity is found, it typically includes a reference using the **IAO:0100001** property (term_replaced_by), which links to the current/replacement taxon.

**Key metadata fields:**

- `term_replaced_by` ([IAO:0100001](http://purl.obolibrary.org/obo/IAO_0100001)): Points to the current replacement taxon IRI
- `identifier` (from dcterms): correspond to the ICTV ID of the current class taxon, this ID is persistent across ICTV releases except special events like split, merged, or abolished terms.   
- `hasExactSynonym` (from oboInOwl): Historical names and synonyms
- `has_rank` ([TAXRANK_1000000](http://purl.obolibrary.org/obo/TAXRANK_1000000)): indicate the rank of the current taxon
- `iri`: the current term IRI that is, in the ICTV ontology, made of the ontology IRI, the MSL release, and the identifier

**Example workflow:**

```
1. Search: "Severe acute respiratory syndrome coronavirus"
2. Find obsolete entity with IRI: http://ictv.global/id/MSL22/ICTV20040588
3. Check for "term_replaced_by" relationship → points to:
   http://ictv.global/id/MSL40/ICTV20040588
4. Fetch the replacement entity (see Use Case 4 below)
5. Return as the current accepted taxon
```

---

### Use Case 4: Resolving ICTV IDs

**Objective:** Query the ICTV API using stable ICTV IDs, which remain consistent across releases.

ICTV IDs (e.g., `ICTV20040588`) are **stable identifiers** provided by ICTV specifically for use with the ICTV ontology and API.

#### Pattern for ICTV ID Resolution

The API endpoint pattern for resolving by ICTV ID is:

```
https://ebi.ac.uk/ols4/api/v2/ontologies/{ONTOLOGY}/classes/{DOUBLE_URL_ENCODED_IRI}
```

#### Step-by-Step Example: Resolving SARS-CoV-2

**1. Construct the IRI:**
```
http://ictv.global/id/MSL40/ICTV20040588
```

- `MSL40`: ICTV release identifier (Master Species List, version 40)
- `ICTV20040588`: The stable ICTV ID for SARS-CoV-2

**2. Double URL-Encode the IRI:**

The IRI must be double URL-encoded to embed it safely in the API path:

```
Original:  http://ictv.global/id/MSL40/ICTV20040588
Encoded:   http%253A%252F%252Fictv.global%252Fid%252FMSL40%252FICTV20040588
```

Encoding breakdown:
- `:` → `%3A` → `%253A` (double-encoded)
- `/` → `%2F` → `%252F` (double-encoded)

**3. Construct the full API URL:**

```
https://ebi.ac.uk/ols4/api/v2/ontologies/ictv/classes/http%253A%252F%252Fictv.global%252Fid%252FMSL40%252FICTV20040588
```

**4. Fetch the entity:**

```bash
curl "https://ebi.ac.uk/ols4/api/v2/ontologies/ictv/classes/http%253A%252F%252Fictv.global%252Fid%252FMSL40%252FICTV20040588"
```

**Response:** Full JSON object for the species of SARS-CoV-2 including:
- Current label and synonyms
- Lineage (parents, ancestors)
- Links to previous/next releases
- Additional metadata and annotations

---

#### General IRI Encoding Pattern

For any ICTV IRI, follow this pattern:

```
1. IRI Format:        http://ictv.global/id/{RELEASE}/{ICTV_ID}
2. Step 1 Encoding:   http%3A%2F%2Fictv.global%2Fid%2F{RELEASE}%2F{ICTV_ID}
3. Step 2 Encoding:   http%253A%252F%252Fictv.global%252Fid%252F{RELEASE}%252F{ICTV_ID}
4. API URL:           https://ebi.ac.uk/ols4/api/v2/ontologies/ictv/classes/{STEP_2_ENCODING}
```

---

## 📋 Direct API Quick Reference

### Essential v2 Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v2/ontologies/ictv/classes` | List all current ICTV classes/taxa |
| `GET /api/v2/ontologies/ictv/classes?label={LABEL}` | Search classes by taxon name |
| `GET /api/v2/ontologies/ictv/classes?label={LABEL}&includeObsoleteEntities=true` | Search classes by name including obsolete taxa |
| `GET /api/v2/ontologies/ictv/classes/{ENCODED_IRI}` | Retrieve a specific class by IRI |
| `GET /api/v2/ontologies/ictv/entities` | List all entities, including classes and individuals |
| `GET /api/v2/ontologies/ictv/entities?label={LABEL}` |  Search by name across all entity types|
| `GET /api/v2/ontologies/ictv/entities/{ENCODED_IRI}` | Retrieve a specific entity by IRI |
| `GET /api/v2/ontologies/ictv/individuals` | List isolates and strains |
| `GET /api/v2/ontologies/ictv/properties` | List ontology properties |

### Common Query Parameters

| Parameter | Values | Purpose |
|-----------|--------|---------|
| `label` | string (URL-encoded) | Search by entity label/name |
| `includeObsoleteEntities` | true/false | Include obsolete terms in results |
| `page` | integer | Page number (0-indexed) |
| `size` | integer (1-1000) | Results per page |

---

## 🔍 Response Structure and Navigation

### Typical v2 Class Response

```json
{
  "iri": "http://ictv.global/id/MSL38/ICTV20040588",
  "label": "Severe acute respiratory syndrome-related coronavirus",
  "synonym": [
    "SARS-CoV",
    {
      "type": [
        "reification"
      ],
      "value": "Severe acute respiratory syndrome coronavirus",
      "axioms": [
        {
          "http://www.geneontology.org/formats/oboInOwl#hasSynonymType": "http://purl.obolibrary.org/obo/OMO_0003008",
          "http://www.w3.org/2002/07/owl#versionInfo": "MSL22",
          "oboSynonymTypeName": "previous name"
        }
      ]
    }
  ],
  "isObsolete": true,
  "hierarchicalParent": [ "http://ictv.global/id/MSL38/ICTV20186129" ],
  "hierarchicalAncestor": [ "http://ictv.global/id/MSL38/ICTV19750006", "http://ictv.global/id/MSL38/ICTV19960002", "http://ictv.global/id/MSL38/ICTV20090624", "http://ictv.global/id/MSL38/ICTV20091082", "http://ictv.global/id/MSL38/ICTV201857095", "http://ictv.global/id/MSL38/ICTV20186105", "http://ictv.global/id/MSL38/ICTV20186129", "http://ictv.global/id/MSL38/ICTV201907198", "http://ictv.global/id/MSL38/ICTV201907209", "http://ictv.global/id/MSL38/ICTV201907210", "http://purl.obolibrary.org/obo/NCBITaxon_10239" ],
  "http://purl.obolibrary.org/obo/IAO_0100001" : "http://ictv.global/id/MSL40/ICTV20040588",
  "http://purl.obolibrary.org/obo/TAXRANK_1000000" : "http://purl.obolibrary.org/obo/TAXRANK_0000006",
  "http://purl.org/dc/terms/identifier" : "ICTV20040588"
  }
```

### Key Fields

- **`iri`**: Unique identifier for the taxon
- **`label`**: Current accepted name
- **`synonym`**: Known alternative names
- **`isObsolete`**: Boolean indicating if the taxon is deprecated
- **`hierarchicalParent`**: Direct parent taxon
- **`hierarchicalAncestor`**: Taxonomic ancestors (lineage)
- **`annotation`**: Additional metadata including replacement chains
- **`http://purl.obolibrary.org/obo/IAO_0100001`**: Link to the replacement term if exists and if the current term is obsolete
- **`http://purl.obolibrary.org/obo/TAXRANK_1000000`**: Taxonomic rank information according to the TAXRANK ontology
- **`http://purl.org/dc/terms/identifier`**: The ICTV ID of the current taxon

---

## 🛠️ Working with Replacement Chains

When resolving historical taxa, you may encounter the **term_replaced_by** relationship (IAO:0100001):

```
Original Request:
  GET /api/v2/ontologies/ictv/classes?label=old%20name&includeObsoleteEntities=true

Response includes:
  {
    "iri": "http://ictv.global/id/OLD_RELEASE/ICTV123456",
    "label": ["Old taxon name"],
    "isObsolete": true,
    "http://purl.obolibrary.org/obo/IAO_0100001": "http://ictv.global/id/MSL40/ICTV789012"
    }
  }

Follow-up Request:
  GET /api/v2/ontologies/ictv/classes/http%253A%252F%252Fictv.global%252Fid%252FMSL40%252FICTV789012

Response:
  {
    "iri": "http://ictv.global/id/MSL40/ICTV789012",
    "label": "Current taxon name",
    "isObsolete": false,
    ...
  }
```
**Real example request URL of ICTV ID ICTV20040588 on MSL38 with API V2**: https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv/classes/http%253A%252F%252Fictv.global%252Fid%252FMSL38%252FICTV20040588


---

## 📖 Additional Resources

### Official OLS Documentation
- **OLS4 API Docs:** [https://www.ebi.ac.uk/ols4/api-docs](https://www.ebi.ac.uk/ols4/api-docs)
- **OLS GitHub Repository:** [https://github.com/EBISPOT/ols4](https://github.com/EBISPOT/ols4)
  - Includes source code, deployment materials (Docker), and examples
  - Supports external contributions via pull requests

### ICTV Ontology Resources
- **ICTV Taxonomy:** [https://ictv.global/taxonomy](https://ictv.global/taxonomy)
- **EVORA Project's ICTV ontology repository:** [https://github.com/EVORA-project/ictv-ontology](https://github.com/EVORA-project/ictv-ontology)
  - OWL files for ICTV releases
  - Configuration and deployment materials
  - Executable Jupyter notebook with example workflows: [https://github.com/EVORA-project/ictv-ontology/blob/main/notebooks/ictv.ipynb](https://github.com/EVORA-project/ictv-ontology/blob/main/notebooks/ictv.ipynb)

### Jupyter Notebook Example
The repository includes a comprehensive Jupyter notebook illustrating typical workflows:
- Querying taxa by label or ICTV identifier
- Following obsolescence relationships
- Reconstructing full taxon history across releases
- Integrating into computational pipelines

---

## 🌐 When to Use Direct API vs. Helper Libraries

### Use Direct API Access When:
- ✅ You need custom query logic beyond standard resolution
- ✅ You want to understand the raw OLS response structure
- ✅ You're working in an environment where helper libraries aren't available
- ✅ You need to implement your own abstraction layer
- ✅ You require specific OLS v1 features (e.g., suggestions)

### Use Helper Libraries When:
- ✅ You need standard ICTV resolution workflows
- ✅ You want simplified domain-specific APIs
- ✅ You prefer working in JavaScript, Python, or PHP
- ✅ You want to minimize dependency management
- ✅ You need consistent behavior across programming languages

---

## 🔗 Related Resources

- ICTV ontology browser on OLS: [https://www.ebi.ac.uk/ols4/ontologies/ictv](https://www.ebi.ac.uk/ols4/ontologies/ictv)
- ICTV ontology API metadata: [https://www.ebi.ac.uk/ols4/api/ontologies/ictv](https://www.ebi.ac.uk/ols4/api/ontologies/ictv)
- OLS API documentation: [https://www.ebi.ac.uk/ols4/api-docs](https://www.ebi.ac.uk/ols4/api-docs)
- ICTV taxonomy: [https://ictv.global/taxonomy](https://ictv.global/taxonomy)
- EVORA ICTV ontology repository: [https://github.com/EVORA-project/ictv-ontology](https://github.com/EVORA-project/ictv-ontology)
- ICTV taxon resolver demo: [https://evora-project.github.io/ictv-resolver/](https://evora-project.github.io/ictv-resolver/)
- ICTV taxon resolver source: [https://github.com/EVORA-project/ictv-resolver](https://github.com/EVORA-project/ictv-resolver)
- Example notebook in this repository: [https://github.com/EVORA-project/ictv-ontology/blob/main/notebooks/ictv.ipynb](https://github.com/EVORA-project/ictv-ontology/blob/main/notebooks/ictv.ipynb)

---
## 🤝 Support & Feedback

- **Issues or questions?** Open an issue on our [GitHub repository](https://github.com/EVORA-project/ictv-ontology/issues)
- **Found an error in this documentation?** Submit a PR to improve it
- **Need OLS-specific help?** Check [OLS4 Documentation](https://www.ebi.ac.uk/ols4/api-docs)

---


## ⚖️ License

- **ICTV data:** CC BY 4.0 — © International Committee on Taxonomy of Viruses (ICTV)
- **SSSOM mapping:** CC0
- **Helpers code:** MIT License — © EVORA Project
