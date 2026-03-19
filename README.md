<p align="center">
  <img src="https://ictv.global/sites/default/files/inline-images/ictvLogo-head.png" alt="ICTV Logo" height="100" style="vertical-align: middle; margin: 0 30px;" />
  <img src="https://raw.githubusercontent.com/EVORA-project/ictv-resolver/main/assets/images/logo/logo.svg" alt="EVORA Project Logo" height="80" style="vertical-align: middle; margin: 0 30px;" />
</p>

<p align="center">
  <a href="https://github.com/EVORA-project/ictv-ontology">
    <img src="https://img.shields.io/badge/View%20on-GitHub-black?logo=github&style=for-the-badge">
  </a>
</p>

# ICTV Ontology & API

> Resolve virus taxa across ICTV releases programmatically.

The **ICTV Ontology & API** provides a machine-readable representation of the official virus taxonomy maintained by the [International Committee on Taxonomy of Viruses (ICTV)](https://ictv.global/), together with programmatic access through the Ontology Lookup Service (OLS) API.

The ontology integrates all ICTV releases into a unified model, enabling:

- resolution of virus names and ICTV identifiers  
- tracking of taxonomy changes across releases  
- interoperability with external resources such as NCBI Taxonomy  

The ontology is publicly accessible via the Ontology Lookup Service (OLS):  
[https://www.ebi.ac.uk/ols4/ontologies/ictv](https://www.ebi.ac.uk/ols4/ontologies/ictv)

---

## 🔎 Using the ICTV API

While OLS provides ontology access through standardised REST API, this repository also provides documentation on how to use the ICTV OLS API directly for taxonomic term resolution, and **ready-to-use helper libraries for practical API usage** (name resolution, obsolete taxa handling, lineage, ICTV ↔ NCBI mapping, etc.).

👉 **See the ICTV API dedictated help documentation:**  

➡️ [`ICTV API documentation (GitHub Pages)`](https://evora-project.github.io/ictv-ontology/helpers/)

➡️ [`Source on GitHub (/helpers)`](https://github.com/EVORA-project/ictv-ontology/tree/main/helpers)

---


# ICTV Ontology


The ontology representation of the [International Committee on Taxonomy of Viruses (ICTV)](https://ictv.global/) developed within the [EVORA project](https://evora-project.eu/) in collaboration with ICTV, uses data from: [https://github.com/ICTV-Virus-Knowledgebase/ICTVdatabase](https://github.com/ICTV-Virus-Knowledgebase/ICTVdatabase)

Complementary SSSOM mappings to NCBITaxon is also made available in a distinct repository: [https://github.com/EVORA-project/virus-taxonomy-mappings](https://github.com/EVORA-project/virus-taxonomy-mappings)

# Running a local OLS
Cloning this repository allows you to run a local version of OLS.

To start an [Ontology Lookup Service (OLS)](https://github.com/EBISPOT/ols4) instance with all versions of ICTV 1971-present:

    docker compose up

# Querying with the Jupyter notebook

To install a minimal environment for the Jupyter notebook:

    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install pandas requests networkx matplotlib tabulate

# Building the ontologies from ICTV data

To rebuild the ontologies from the ICTV TSV files, you will need to install some Python dependencies:

    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install rdflib pandas 

Then run the `create_ontologies.py` script:

    python3 create_ontologies.py

## License

This repository uses separate licenses for code and data:

- **Code:** Licensed under the [Apache License 2.0](./LICENSE). See the LICENSE file for full terms.
- **Data:** See [DATA_LICENSE](./DATA_LICENSE) for detailed information on data licensing, provenance, and attribution requirements.

Please review both files to understand the licensing terms when using this repository.

