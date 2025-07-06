

# ICTV Ontology

**The ICTV ontologies can be accessed via OLS at **[https://www.ebi.ac.uk/ols4/ontologies/ictv](https://www.ebi.ac.uk/ols4/ontologies/ictv)**.

Ontology representation of the [International Committee on Taxonomy of Viruses (ICTV)](https://ictv.global/) for the [EVORA project](https://evora-project.eu/)

Uses data from: https://github.com/ICTV-Virus-Knowledgebase/ICTVonlineDbLoad

To start an [Ontology Lookup Service (OLS)](https://github.com/EBISPOT/ols4) instance with all versions of ICTV 1971-present:

    docker compose up

To rebuild the ontologies from the ICTV TSV files:

    python3 create_ontologies.py



