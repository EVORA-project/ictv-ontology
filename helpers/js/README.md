
# ICTV JavaScript API Helper (`ictv-api.js`)

Lightweight ES module to query the **ICTV Ontology API** (served via the [Ontology Lookup Service](https://www.ebi.ac.uk/ols4/ontologies/ictv)) and resolve virus taxon names, historical ICTV identifiers, and NCBI Taxon IDs to the corresponding current ICTV taxon.

- Ontology & API: ICTV Ontology via OLS4  
- Data © International Committee on Taxonomy of Viruses (ICTV), CC BY 4.0  
- Helper code © EVORA Project — MIT License

This helper is the same one used by the public ICTV Taxon Resolver demo:  
https://github.com/EVORA-project/ictv-resolver

## 1. Quick start (browser, via CDN)

Load the helper as an ES module and use the `ICTVApi` class:

```html
<script type="module">
  import { ICTVApi } from "https://cdn.jsdelivr.net/gh/EVORA-project/ictv-ontology/helpers/js/ictv-api.js";

  const api = new ICTVApi();

  const result = await api.resolveToLatest("Zika virus");
  console.log(result);
</script>
```
Why this syntax?

* ictv-api.js is an ES module, so the `<script>` tag must use type="module".

* The helper exposes a named export: `{ ICTVApi }` (no default export).
 
* Modern browsers allow top-level `await` inside module scripts.

## 2. Installation & loading

You can simply use the jsdelivr CDN (recommended), or import a local copy into your project:

```js
import { ICTVApi } from "https://cdn.jsdelivr.net/gh/EVORA-project/ictv-ontology/helpers/js/ictv-api.js";
```

Note: the helper uses the standard `fetch` API. In Node.js, ensure your runtime includes it.

## 3. Constructor

```js
const api = new ICTVApi(base?, sssomUrl?);
```
Arguments:
- base (optional): Ontology Lookup Service (OLS) endpoint. Current default set to OLS API v2: https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv
- sssomUrl (optional): ICTV–NCBI mapping file used to map between ICTV taxa and NCBI Taxon IDs. You can provide your own mapping, but our default file is rebuilt at each ICTV release:
  https://raw.githubusercontent.com/EVORA-project/virus-taxonomy-mappings/refs/heads/dev/mappings/ictv_ncbitaxon_exact.sssom.tsv

## 4. Main concepts
Several methods return a normalized ICTV entity, with the following key fields:
```ts

type IctvEntity = {
  // identity
  msl: string | null;                // e.g. "MSL22"
  ictv_id: string | null;            // e.g. "ICTV20040588"
  ictv_curie: string | null;         // e.g. "ictv:MSL22/ICTV20040588"
  iri: string | null;                // e.g. "http://ictv.global/id/MSL22/ICTV20040588"

  // names
  label: string | null;              // main ICTV label
  synonyms: string[];                // exact synonyms (if any)

  // status / obsolescence
  is_obsolete: boolean;
  obsolescence_reason: "SPLIT" | "MERGED" | null;  // if known
  reason_iri: string | null;         // IAO term for obsolescence reason

  // hierarchy
  direct_parent_iri: string | null;
  direct_parent_label: string | null;
  ancestors_iris: string[];          // ancestor IRIs from ontology
  lineage: string[];                 // ancestor labels (root → parent)

  // rank
  rank_label: string | null;         // e.g. "species", "genus", ...
  rank_iri: string | null;

  // revision links (provenance)
  replaced_by: string | string[] | null;     // IRI(s) of replacement taxa
  was_revision_of: string | null;           // IRI of previous revision (if any)
  had_revision: string | null;              // IRI of next revision (if any)

  // external cross-references
  narrow_match: {
    value: string;                  // e.g. "GenBank:AY274119"
    url: string | null;             // helper URL if recognized (NCBI links, etc.)
  }[];
};
```

All async methods below return Promises and may throw network errors if the API is unavailable.

## 5. Public API methods

### 5.1 resolveToLatest(input)

Resolves any ICTV ID, label, synonym, virus name, NCBI taxid, or IRI, to the current ICTV taxon, following replacement chains if necessary.

Possible return structures include:
- current ICTV taxon
- obsolete with replacement history
- not-found with suggestions

```js
const res = await api.resolveToLatest("Zika virus");

```
#### Input formats supported

* ICTV ID: e.g. "ICTV19990695"

* ICTV IRI: e.g. "http://ictv.global/id/MSL22/ICTV20040588"

* Label / former taxon name / virus name: e.g. "Tehran virus"

* NCBI taxid: "64320" or "ncbitaxon:64320"

#### Return shape

````ts
type ResolveResult =
  | {
      status: "current";
      input: string;
      current: IctvEntity;          // current accepted ICTV taxon
      ncbi: {                       // NCBI mappings (if available)
        ncbiCurie: string;          // e.g. "ncbitaxon:2901879"
        label: string;              // NCBI label
      }[];
    }
  | {
      status: "obsolete";
      input: string;
      obsolete: IctvEntity;         // obsolete ICTV taxon
      reason: string | null;        // high-level reason (e.g. "MERGED", "SPLIT")
      replacements: IctvEntity[];   // all final replacement taxa (possibly several)
      final?: IctvEntity;           // best final replacement (latest MSL), if any
    }
  | {
      status: "not-found";
      input: string;
      suggestions: string[];        // candidate labels suggested by OLS
    };
````

#### Example:

````js
const res = await api.resolveToLatest("Tehran virus");

if (res.status === "current") {
  console.log("Current ICTV species:", res.current.label, res.current.ictv_curie);
} else if (res.status === "obsolete") {
  console.log("Obsolete taxon:", res.obsolete.label, "reason:", res.reason);
  console.log("Replaced by:", res.replacements.map(r => r.label).join(", "));
} else {
  console.warn("Not found. Maybe try:", res.suggestions.join(", "));
}

````

### 5.2 getHistory(input)

Retrieve the full ICTV history across MSL releases for a given term (past → present, or present → past).
````js
const res = await api.getHistory("ICTV19990862");
````

#### Return shape
````ts
type HistoryResult =
  | {
      status: "ok";
      input: string;
      history: IctvEntity[];    // sorted by MSL (latest first)
    }
  | {
      status: "not-found";
      input: string;
      suggestions: string[];
    };

````
Each history[i] is a full IctvEntity enriched with lineage and revision links.

#### Example:
````js
const res = await api.getHistory("Zika virus");

if (res.status === "ok") {
  for (const h of res.history) {
    console.log(`${h.msl}: ${h.label} [${h.ictv_id}] obsolete=${h.is_obsolete}`);
  }
}

````

### 5.3 getNcbiForIctvCurie(ictvCurie)

Look up NCBI Taxon mappings for a given ICTV CURIE using the SSSOM mapping.

````js

const mappings = await api.getNcbiForIctvCurie("ictv:MSL33/ICTV20040588");

````

#### Returns
````ts
type NcbiMapping = {
  ncbiCurie: string;       // e.g. "ncbitaxon:2901879"
  label: string;           // NCBI label
};

NcbiMapping[];

````

### 5.4 getIctvFromNcbi(ncbiId)

Resolve an NCBI Taxon ID (or ncbitaxon:#### CURIE) back to the best corresponding ICTV taxon.

````js
const hits = await api.getIctvFromNcbi("2901879");
// or
const hits = await api.getIctvFromNcbi("ncbitaxon:2901879");
````

####Returns

An array of the best ICTV mappings per ICTV ID, always choosing the latest MSL when there are multiple entries:

````ts
type IctvFromNcbiHit = {
  ictv_curie: string;    // e.g. "ictv:MSL33/ICTV20040588"
  msl: string;           // e.g. "MSL33"
  ictv_id: string;       // e.g. "ICTV20040588"
  label: string;         // ICTV label
};

IctvFromNcbiHit[];
````


### 5.5 getEntityByIri(iri)

Low-level helper: fetch the raw OLS entity JSON for an ICTV IRI.
This is mostly useful if you need fields not included in the normalized IctvEntity.

````js
const raw = await api.getEntityByIri("http://ictv.global/id/MSL40/ICTV20040588");
console.log(raw);
````

## 6. Behaviour and selection strategy

resolveToLatest() and getHistory() use a conservative resolution strategy:

1. Direct ICTV IRI: if the input looks like an ICTV IRI, it is resolved directly.  
2. ICTV ID: if it matches ICTV\d+, the helper queries classes by identifier.
3. NCBI Taxon ID: if it looks like a taxid (1234 or ncbitaxon:1234), it resolves via SSSOM mappings.
4. Individuals → parent class: some virus names exist as individuals; in that case, the helper resolves the parent taxon.  
5. Class label / synonym: the helper searches current + obsolete classes by label and synonym (with some relaxed matching as a fallback).
6. Suggestions: if nothing is found, the helper uses the OLS suggest API to propose alternative labels.

## 7. Error handling

* Network or server errors (e.g. OLS unavailable) will cause the underlying fetch calls to throw.
   OLS is a public service and may encounter short maitenance periods, triggering network errors on API requests. Retrying after a short delay usually resolves the issue.

* Logical "not found" cases are represented as { status: "not-found", ... }.

* Always wrap calls in try/catch if you need to handle network failures gracefully:

````js
try {
  const res = await api.resolveToLatest("Some virus name");
  // ...inspect res.status...
} catch (err) {
  console.error("ICTV API error:", err);
}
````


## 8. Licensing

- ICTV data as included in the ICTV ontology: ICTV CC BY 4.0  
- SSSOM mapping: [CC0](https://github.com/EVORA-project/virus-taxonomy-mappings/blob/dev/LICENSE)
- Helper code (ictv-api.js): © EVORA Project - MIT License

If you build a public interface using this helper, please acknowledge both ICTV and the EVORA Project in your documentation or About page.
