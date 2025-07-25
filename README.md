

# ICTV Ontology

**The ICTV ontologies can be accessed via OLS at **[https://www.ebi.ac.uk/ols4/ontologies/ictv](https://www.ebi.ac.uk/ols4/ontologies/ictv)**.

Ontology representation of the [International Committee on Taxonomy of Viruses (ICTV)](https://ictv.global/) for the [EVORA project](https://evora-project.eu/)

Uses data from: https://github.com/ICTV-Virus-Knowledgebase/ICTVdatabase

# Running a local OLS

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

