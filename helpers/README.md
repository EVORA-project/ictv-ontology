# Programmatic access to official taxonomy of viruses with **ICTV Ontology API** – Helper Libraries & Direct API Access

## 🌍 What is the ICTV OLS API?

The EVORA project (European Viral Outbreak Response Alliance) in collaboration with the ICTV (International Committee on Taxonomy of Viruses) have developed a **public programmatic access to the official taxonomy of viruses** by transforming ICTV releases into the **ICTV ontology** and serving it through the **Ontology Lookup Service (OLS) API**. 

OLS API is a REST-based web service that provides programmatic access to latest versions of biomedical ontologies including the developed ICTV ontology. OLS API is hosted and maintained by the European Bioinformatics Institute (EBI) and allows to retrieve semantic information of the ICTV ontology. This is essential for:
- Automated virus taxon identification pipelines
- Integration into bioinformatics workflows
- Ensuring consistent taxonomy across applications
- Tracking historical and current virus classifications
  
 With the ICTV OLS API, you can:
- **Query taxonomic entities** by taxon name, identifier, or IRI
- **Resolve historical and obsolete taxa** to their current replacements using former taxon names, virus names, synonyms, ICTV identifiers, or NCBI taxonomy identifiers
- **Retrieve lineage information of a taxon** within a specific ICTV release
- **Access synonyms and historical names** for virus taxonomy
- **Map NCBI Taxon identifiers** to ICTV entities via a complementary SSSOM file
- **Retrieve complete ICTV releases** in structured, machine-readable format

### 📖 API Documentation
👉 **Official OLS API Documentation**: https://www.ebi.ac.uk/ols4/api-docs

👉 **ICTV Ontology on OLS**: https://www.ebi.ac.uk/ols4/api/ontologies/ictv

The ICTV OLS API follows REST principles and returns JSON-formatted responses, making it accessible from any programming language or environment that can make HTTP requests.

---

## 🎯 Two Approaches to Access the ICTV OLS API

The ICTV ontology data can be accessed in **two complementary ways**:
### ✅ **Approach 1: Helper Libraries (Recommended for Most Users)**
Lightweight client libraries that **encapsulate the complexity** of direct OLS queries and provide a simple, domain-friendly interface for common use cases.

**Use this if you:**
- Want quick integration with minimal code
- Need standard ICTV resolution workflows
- Prefer simplified, language-specific APIs
- Work in JavaScript, Python, or PHP

### 🔧 **Approach 2: Direct OLS API Access (For Advanced Users)**
Direct HTTP access to the OLS API endpoints, providing **full control and flexibility** for custom queries and advanced workflows.

**Use this if you:**
- Need fine-grained control over API parameters
- Have custom or non-standard query patterns
- Want to build your own abstractions
- Are integrating into systems where helper libraries aren't available
- Need to understand the raw OLS response structure

---

## 📘 Helper Libraries Overview

This directory provides lightweight client libraries that make it easy to query the **ICTV Ontology API**, as served through  the OLS API service. 

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
**Note:** Requires a module-compatible environment. Use in HTML with <script type="module"> or in modern Node.js projects with "type": "module" in package.json.

**Features:**

- Resolving ICTV IDs, IRIs, taxon or virus labels, synonyms
- Mapping NCBI Taxon IDs ↔ ICTV IDs
- Replacement chains and obsolete term resolution
- Historical lineage retrieval across releases

**No dependencies** — pure ES6.

**Note:** Optimized for single-taxon resolution workflows. For bulk data export or complete release extraction, use Python or PHP helpers.

👉 **Full JS helper API library reference & Advanced Examples:** See [`helpers/js/README.md`](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/js/README.md)
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

- Full term resolution (all input types)
- ICTV ↔ NCBI mapping
- **Complete release export** with automatic pagination handling (`getAllFromRelease()`)
- **Release-specific taxon queries** (`getTaxonByRelease()`)
- Individual/isolate queries
- Synonym, history, and obsolescence reason retrieval

Ideal for building local caches or comprehensive data analysis

**Use Case:** Export entire MSL40 release for downstream processing, data validation, or archival.

👉 **Full Python helper API library reference & Configuration Options:** See [`helpers/python/README.md`](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/python/README.md)

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

**Features:** All features equivalent to Python helper

Ideal for backend systems needing bulk data access

**Use Case:** CMS/backend system importing/updating to latest ICTV release for website taxonomy database.

👉 **Full PHP helper API library reference & Error Handling Guide:** See [`helpers/php/README.md`](https://github.com/EVORA-project/ictv-ontology/blob/main/helpers/php/README.md)

---

## 📚 Choose Your Helper

| Feature | JavaScript | Python | PHP |
|---------|:---:|:---:|:---:|
| **Basic resolution** | ✅ | ✅ | ✅ |
| **Bulk export (`getAllFromRelease`)** | ❌ | ✅ | ✅ |
| **Release-specific queries** | ❌ | ✅ | ✅ |
| **Dependencies** | None | `requests` | `curl` (built-in) |
| **Best for** | 🌐 Web | 📊 Data pipelines | 🖥️ Server-side |
| **Full Docs** | [js/README](helpers/js/README.md) | [python/README](helpers/python/README.md) | [php/README](helpers/php/README.md) |


---

## 📚 Helper Library Architecture

### Common Resolution Strategy

All three helper implementations follow the same general resolution strategy:

1. **Recognize ICTV IRIs and identifiers**
2. **Optionally map NCBI Taxon identifiers** to ICTV taxa
3. **Treat individuals** (e.g., isolates) as entry points and resolve them to the corresponding species
4. **Fall back to labels and synonyms** where needed
5. **Follow the replacement chain** when an entity is obsolete until final non-obsolete taxa are reached

### Normalized Output

The libraries return a **normalized ICTV taxon object** containing:

- Identifiers and IRI
- Label and synonyms
- Rank and lineage
- Obsolescence status
- Revision links
- NCBI mappings (where available)

This abstraction allows developers to focus on domain logic rather than the details of the OLS API.

---

## 🌐 Live Implementation Example

👉 **ICTV Taxon Resolver**  
https://evora-project.github.io/ictv-resolver/

A reference browser-based implementation that demonstrates the helper library logic. It accepts:
- Historical or current viral taxon from any rank
- Virus names
- ICTV identifiers
- IRIs
- NCBI Taxon identifiers

And returns the latest accepted ICTV taxon with lineage and mapping information.

**Source code:** https://github.com/EVORA-project/ictv-resolver

---

## 🧠 Dependencies Comparison

| Language  | Dependencies | Best For |
|-----------|--------------|----------|
| JavaScript | None (pure ES6) | Web applications, browsers, Node.js |
| Python | `requests` | Scripts, pipelines, Jupyter notebooks |
| PHP | cURL (built-in) | Server-side, CMS integrations |

---

---

# 🔧 Advanced: Direct OLS API Access

For users who need direct access to the ICTV Ontology Lookup Service API without using helper libraries, this section provides guidance on constructing and executing OLS API queries.

👉 **Official OLS Documentation**: https://www.ebi.ac.uk/ols4/api-docs

## 📡 OLS API Endpoints Overview

The ICTV Ontology is exposed through two main sets of OLS endpoints:

### v1 Endpoints (Legacy but Stable)
```
https://www.ebi.ac.uk/ols4/api/ontologies/ictv
```

- **Use case:** Legacy integrations, access to features like `/api/suggest`
- **Features:** Still include useful search and suggestion features
- **Response format:** Original OLS v1 structure

**Examples:**
- List all terms: `https://www.ebi.ac.uk/ols4/api/ontologies/ictv/terms?page=0&size=1000`
- Search: `https://www.ebi.ac.uk/ols4/api/ontologies/ictv/terms?q=coronavirus`

---

### v2 Endpoints (Modern and Recommended)
```
https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv
```

- **Use case:** Modern integrations requiring richer metadata
- **Features:** Enhanced entity linking, better obsolescence handling
- **Response format:** Extended JSON with linked entity details

**Examples:**
- List current classes: `https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv/classes`
- Get specific class: `https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv/classes/{ENCODED_IRI}`

---

## 🎯 Common Use Cases with Examples

### Use Case 1: Building a Local Cache

**Objective:** Retrieve the entire ICTV taxonomy, including historical terms, for local caching or offline use.

#### Option A: Using v1 `/terms` Endpoint (All Terms Including Historical)

Retrieve all terms across all ICTV releases:

```
https://www.ebi.ac.uk/ols4/api/ontologies/ictv/terms?page=0&size=1000
```

**Parameters:**
- `page`: Page number (0-indexed)
- `size`: Number of items per page (up to 1000)

**An iteration loop can simply handle paginated results to retreive all terms**

**Response structure:** JSON array of term objects with IRIs, labels, synonyms, and metadata.

---

#### Option B: Using v2 `/classes` Endpoint (Current Taxa Only)

Retrieve only current taxa from the latest ICTV release with richer metadata:

```
https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv/classes
```

**Advantages of v2:**
- Returns more detailed linked entity information
- Better suited for understanding taxon relationships
- Includes direct references to parent/child taxa

**Example response fragment:**
```json
{
  "iri": "http://ictv.global/id/MSL40/ICTV20040588",
  "label": "Severe acute respiratory syndrome coronavirus 2",
  "description": ["..."],
  "synonyms": ["SARS-CoV-2", "..."],
  "isObsolete": false,
  "parents": [...]
}
```

---

### Use Case 2: Resolving Historical References

**Objective:** Find the current accepted ICTV taxon for a virus that may be known by a historical or obsolete name.

#### Step 1: Search for the Historical Name (Including Obsolete Terms)

```
https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv/classes?label=severe%20acute%20respiratory%20syndrome%20coronavirus&includeObsoleteEntities=true
```

**Parameters:**
- `label`: The virus name to search for (URL-encoded)
- `includeObsoleteEntities`: Set to `true` to include obsolete terms

**Response:** List of matching classes, including obsolete ones.

---

#### Step 2: Follow the Replacement Chain

When an obsolete entity is found, it typically includes a reference using the **IAO:0100001** property (term_replaced_by), which links to the current/replacement taxon.

**Key metadata fields:**
- `hasExactSynonym` (from oboInOwl): Historical names and synonyms
- `term_replaced_by` (IAO:0100001): Points to the current replacement taxon IRI

**Example workflow:**

```
1. Search: "Severe acute respiratory syndrome coronavirus"
2. Find obsolete entity with IRI: http://ictv.global/id/OLD_RELEASE/ICTV20040587
3. Check for "term_replaced_by" relationship → points to:
   http://ictv.global/id/MSL40/ICTV20040588
4. Fetch the replacement entity (see Use Case 3 below)
5. Return as the current accepted taxon
```

---

### Use Case 3: Resolving ICTV IDs

**Objective:** Query the ICTV API using stable ICTV IDs, which remain consistent across releases.

ICTV IDs (e.g., `ICTV20040588`) are **stable identifiers** provided by ICTV specifically for use with the ICTV ontology and API.

#### Pattern for ICTV ID Resolution

The API endpoint pattern for resolving by ICTV ID is:

```
https://ebi.ac.uk/ols4/api/v2/ontologies/{ONTOLOGY}/classes/{ENCODED_IRI}
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

**Response:** Full JSON object for SARS-CoV-2 including:
- Current label and synonyms
- Lineage (parents, ancestors)
- Links to previous/next releases
- Metadata and annotations

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
| `GET /api/v2/ontologies/ictv/classes?label={LABEL}` | Search by taxon name |
| `GET /api/v2/ontologies/ictv/classes?label={LABEL}&includeObsoleteEntities=true` | Search including obsolete taxa |
| `GET /api/v2/ontologies/ictv/classes/{ENCODED_IRI}` | Get specific taxon by IRI |
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
  "description": ["The causative agent of COVID-19..."],
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
  "hierarchicalAncestor" : [ "http://ictv.global/id/MSL38/ICTV19750006", "http://ictv.global/id/MSL38/ICTV19960002", "http://ictv.global/id/MSL38/ICTV20090624", "http://ictv.global/id/MSL38/ICTV20091082", "http://ictv.global/id/MSL38/ICTV201857095", "http://ictv.global/id/MSL38/ICTV20186105", "http://ictv.global/id/MSL38/ICTV20186129", "http://ictv.global/id/MSL38/ICTV201907198", "http://ictv.global/id/MSL38/ICTV201907209", "http://ictv.global/id/MSL38/ICTV201907210", "http://purl.obolibrary.org/obo/NCBITaxon_10239" ],
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

When resolving historical taxa, you may encounter the **term_replaced_by** relationship:

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
    "label": "Current virus name",
    "isObsolete": false,
    ...
  }
```
**Real example request URL on API V2**: https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv/classes/http%253A%252F%252Fictv.global%252Fid%252FMSL38%252FICTV20040588

---

## 💡 Practical Example: Querying for a Virus by Name

### Scenario: Find information about "Zika virus"

#### Step 1: Search for the term
```bash
curl "https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv/classes?label=zika%20virus"
```

#### Step 2: Parse the response
```json
{
  "_embedded": {
    "classes": [
      {
        "iri": "http://ictv.global/id/MSL40/ICTV20040123",
        "label": "Zika virus",
        "isObsolete": false
      }
    ]
  }
}
```

#### Step 3: Fetch full details
```bash
curl "https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv/classes/http%253A%252F%252Fictv.global%252Fid%252FMSL40%252FICTV20040123"
```

#### Step 4: Extract useful information
- Label, synonyms, description
- Lineage (hierarchicalParents)
- NCBI mappings (if available in annotations)
- Release history

---

## 📖 Additional Resources

### Official OLS Documentation
- **OLS4 API Docs:** https://www.ebi.ac.uk/ols4/docs/
- **OLS GitHub Repository:** https://github.com/EMBL-EBI/OLS
  - Includes source code, deployment materials (Docker), and examples
  - Supports external contributions via pull requests

### ICTV Ontology Resources
- **ICTV Taxonomy:** https://ictv.global/taxonomy
- **EVORA Project Repository:** https://github.com/EVORA-project/ictv-ontology
  - OWL files for ICTV releases
  - Configuration and deployment materials
  - Executable Jupyter notebook with example workflows: https://github.com/EVORA-project/ictv-ontology/blob/main/notebooks/ictv.ipynb

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

- ICTV Ontology on OLS: https://www.ebi.ac.uk/ols4/ontologies/ictv
- ICTV Taxonomy: https://ictv.global/taxonomy
- EVORA Project ICTV Ontology Repository: https://github.com/EVORA-project/ictv-ontology
- ICTV Taxon Resolver Demo: https://evora-project.github.io/ictv-resolver/
- OLS API Documentation: https://www.ebi.ac.uk/ols4/docs/

---

## ⚖️ License

- **ICTV data:** CC BY 4.0 — © International Committee on Taxonomy of Viruses (ICTV)
- **SSSOM mapping:** CC0
- **Helpers code:** MIT License — © EVORA Project
