

import rdflib
from rdflib import URIRef, BNode, Literal
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDFS, RDF, PROV, FOAF, SKOS
import pandas as pd
import os
import json
import re

TERM_REPLACED_BY = "http://purl.obolibrary.org/obo/IAO_0100001"
OBSOLESCENCE_REASON = "http://purl.obolibrary.org/obo/IAO_0000225"
TERM_SPLIT = "http://purl.obolibrary.org/obo/IAO_0000229"
TERMS_MERGED = "http://purl.obolibrary.org/obo/IAO_0000227"
SYNONYM = "http://www.geneontology.org/formats/oboInOwl#hasExactSynonym"
SYNONYM_TYPE = "http://www.geneontology.org/formats/oboInOwl#hasSynonymType"
PREVIOUS_NAME = "http://purl.obolibrary.org/obo/OMO_0003008"
XREF = "http://www.geneontology.org/formats/oboInOwl#hasDbXref"
SOURCE = "http://purl.org/dc/terms/source"
REPLACES = "http://purl.org/dc/terms/replaces"
REPLACED_BY = "http://purl.org/dc/terms/isReplacedBy"
EDITOR_NOTE = "http://purl.obolibrary.org/obo/IAO_0000116"

def main():

    common_graph = rdflib.Graph()
    common_graph.parse(location='ictv_molecules.owl')
    
    nodes = pd.read_csv('data/taxonomy_node_export.utf8.txt', sep='\t', on_bad_lines=lambda x: x[:-1], engine='python', dtype=str)
    delta = pd.read_csv('data/taxonomy_node_delta.utf8.txt', sep='\t', dtype=str)
    isolates = pd.read_csv('data/species_isolates.utf8.txt', sep='\t', dtype=str)

    releases = nodes[(nodes['level_id'] == '100') & (nodes['name'] != 'empty_tree')]

    prefix = 'https://ictv.global/taxonomy/taxondetails?taxnode_id='
  
    ontologies = []

    for release in releases.itertuples():

        if release.name != '2023' and release.name != '2022':
            continue

        print(f'Creating ontology for ICTV release {release.name}')

        taxnode_id_to_ictv_id = {}

        id = 'ictv_' + release.name
        release_num = release.msl_release_num
        ontology_iri = f'{prefix}{id}'

        nodes_in_release = nodes[(nodes['msl_release_num'] == release_num) & (nodes['level_id'] != '100')]

        g = rdflib.Graph()
        ontologies.append(g)

        g.add((URIRef(ontology_iri), RDF.type, OWL.Ontology))
        g.add((URIRef(ontology_iri), RDFS.label, Literal("ICTV Taxonomy (" + release.name + ")")))
        g.add((URIRef(ontology_iri), RDFS.comment, Literal("International Committee on Taxonomy of Viruses (ICTV)")))
        g.add((URIRef(ontology_iri), FOAF.homepage, URIRef("https://ictv.global/")))
        g.add((URIRef(ontology_iri), OWL.versionInfo, Literal(str(release_num))))

        for node in nodes_in_release.itertuples():
            class_iri = URIRef(prefix + node.ictv_id)

            if node.taxnode_id in taxnode_id_to_ictv_id:
                raise Exception(f'Taxnode ID {node.ictv_id} already exists')
            taxnode_id_to_ictv_id[node.taxnode_id] = node.ictv_id
            # print(class_iri)

            replacements = delta[delta['prev_taxid'] == node.taxnode_id]

            if not replacements.empty:
                is_merged = replacements['is_merged'].value_counts().get('1', 0) > 0
                is_split = replacements['is_split'].value_counts().get('1', 0) > 0
                is_moved = replacements['is_moved'].value_counts().get('1', 0) > 0
                is_promoted = replacements['is_promoted'].value_counts().get('1', 0) > 0
                is_demoted = replacements['is_demoted'].value_counts().get('1', 0) > 0
                is_renamed = replacements['is_renamed'].value_counts().get('1', 0) > 0
                is_new = replacements['is_new'].value_counts().get('1', 0) > 0
                is_deleted = replacements['is_deleted'].value_counts().get('1', 0) > 0

                # g.add((class_iri, OWL.deprecated, Literal('true', datatype=URIRef('http://www.w3.org/2001/XMLSchema#boolean'))))

                for replacement in replacements.itertuples():
                    if not pd.isna(replacement.new_taxid):
                        g.add((class_iri, URIRef(TERM_REPLACED_BY), URIRef(prefix+replacement.new_taxid)))
                        g.add((class_iri, URIRef(REPLACED_BY), URIRef(prefix+replacement.new_taxid)))
                        g.add((URIRef(prefix+replacement.new_taxid), URIRef(REPLACES), class_iri))

                if is_new:
                    year = replacements['new_taxid'][:4]
                    g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"New in " + year)))
                elif is_merged:
                    g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"Merged into {', '.join(replacements['new_taxid'].values)}")))
                    g.add((class_iri, URIRef(OBSOLESCENCE_REASON), URIRef(TERMS_MERGED)))
                elif is_split:
                    g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"Split into {', '.join(replacements['new_taxid'].values)}")))
                    g.add((class_iri, URIRef(OBSOLESCENCE_REASON), URIRef(TERM_SPLIT)))
                elif is_moved:
                    g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"Moved to {', '.join(replacements['new_taxid'].values)}")))
                elif is_promoted:
                    g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"Promoted, see {', '.join(replacements['new_taxid'].values)}")))
                elif is_demoted:
                    g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"Demoted, see {', '.join(replacements['new_taxid'].values)}")))
                elif is_renamed:
                    g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"Renamed, see {', '.join(replacements['new_taxid'].values)}")))
                elif is_deleted:
                    g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"Deleted")))

            g.add((class_iri, RDF.type, OWL.Class))
            g.add((class_iri, RDFS.label, Literal(node.name)))
            g.add((class_iri, URIRef("http://ictv.global/ictv_id"), Literal(node.ictv_id)))
            g.add((class_iri, OWL.versionInfo, Literal(str(release_num))))

            if node.parent_id != release.ictv_id:
                if node.parent_id in taxnode_id_to_ictv_id:
                    g.add((class_iri, RDFS.subClassOf, URIRef(f'{prefix}{taxnode_id_to_ictv_id[node.parent_id]}')))
            g.add((class_iri, RDFS.isDefinedBy, URIRef(ontology_iri)))

            if not pd.isna(node.abbrev_csv):
                g.add((class_iri, URIRef(SYNONYM), Literal(node.abbrev_csv)))

            # if not pd.isna(node.genbank_accession_csv):
            #     add_xrefs(g, class_iri, node.genbank_accession_csv, 'genbank:')
            # if not pd.isna(node.refseq_accession_csv):
            #     add_xrefs(g, class_iri, node.refseq_accession_csv, 'refseq:')

            taxnode_isolates = isolates[isolates['taxnode_id'] == node.taxnode_id]

            for isolate in taxnode_isolates.itertuples():
                isolate_iri = f'https://ictv.global/isolates#isolate_{isolate.isolate_id}'
                g.add((URIRef(isolate_iri), RDF.type, OWL.NamedIndividual))
                g.add((URIRef(isolate_iri), RDF.type, class_iri))
                g.add((URIRef(isolate_iri), RDFS.isDefinedBy, URIRef(ontology_iri)))
                if not pd.isna(isolate.isolate_names):
                    for name in re.split(';|,', isolate.isolate_names):
                        g.add((URIRef(isolate_iri), RDFS.label, Literal(name.strip())))
                if not pd.isna(isolate.isolate_abbrevs):
                    for abbrev in re.split(';|,', isolate.isolate_abbrevs):
                        g.add((URIRef(isolate_iri), URIRef(SYNONYM), Literal(abbrev.strip())))
                if not pd.isna(isolate.genbank_accessions):
                    for xref in re.split(';|,', isolate.genbank_accessions):
                        g.add((URIRef(isolate_iri), SKOS.exactMatch, Literal("genbank:" + xref.strip())))
                        g.add((class_iri, SKOS.narrowMatch, Literal("genbank:" + xref.strip())))
                if not pd.isna(isolate.refseq_accessions):
                    for xref in re.split(';|,', isolate.refseq_accessions):
                        g.add((URIRef(isolate_iri), SKOS.exactMatch, Literal("refseq:" + xref.strip())))
                        g.add((class_iri, SKOS.narrowMatch, Literal("refseq:" + xref.strip())))


    for g_orig in ontologies:
        g = rdflib.Graph()
        g += g_orig
        ontology = g.value(predicate=RDF.type, object=OWL.Ontology)
        ontology_id = ontology.split('=')[-1]
        version = g.value(subject=ontology, predicate=OWL.versionInfo)
        print(f'Building final ontology for {ontology_id} (version = {version})')
        for other_g in ontologies:
            other_ontology = other_g.value(predicate=RDF.type, object=OWL.Ontology)
            other_version = other_g.value(subject=other_ontology, predicate=OWL.versionInfo)
            if other_version < version:
                print(f'- merging {other_version} into {version}')
                for c in g.subjects(predicate=RDF.type, object=OWL.Class):
                    ictv_id = g.value(subject=c, predicate=URIRef("http://ictv.global/ictv_id"))
                    prev_versions = list(other_g.subjects(predicate=URIRef("http://ictv.global/ictv_id"), object=ictv_id))
                    cur_name = g.value(subject=c, predicate=RDFS.label)
                    for prev_version in prev_versions:
                        prev_name = other_g.value(subject=prev_version, predicate=RDFS.label)
                        if prev_name and prev_name != cur_name:
                            if len(list(g.triples((c, URIRef(SYNONYM), Literal(prev_name))))) == 0:
                                g.add((c, URIRef(SYNONYM), Literal(prev_name)))
                                stmt = BNode()
                                g.add((stmt, RDF.type, OWL.Axiom))
                                g.add((stmt, OWL.annotatedSource, c))
                                g.add((stmt, OWL.annotatedProperty, URIRef(SYNONYM)))
                                g.add((stmt, OWL.annotatedTarget, Literal(name)))
                                g.add((stmt, URIRef(SYNONYM_TYPE), URIRef(PREVIOUS_NAME)))
                                g.add((stmt, RDFS.isDefinedBy, other_ontology))
                other_g_copy = rdflib.Graph()
                other_g_copy += other_g
                other_g_copy.remove((URIRef(ontology_iri), RDF.type, OWL.Ontology))
                other_g_copy.remove((next(other_g_copy.subjects(RDF.type, OWL.Ontology), None), None, None))
                g += other_g_copy

        owl_filename = 'out/' + ontology_id + '.owl.ttl'
        print(f'Saving OWL file ' + owl_filename)
        g += common_graph
        g.bind('owl', OWL)
        g.bind('iao', 'http://purl.obolibrary.org/obo/IAO_')
        g.bind('oio', 'http://www.geneontology.org/formats/oboInOwl#')
        g.bind('omo', 'http://purl.obolibrary.org/obo/OMO_')
        g.bind('dcterms', 'http://purl.org/dc/terms/')
        g.bind('ictv', prefix)
        g.serialize(owl_filename, format="ttl")

    owl_files = [f for f in os.listdir('out') if f.endswith('.owl.ttl')]
    ols_config = {
        'ontologies':[
            {
                "id": "evora",
                "ontology_purl": "https://raw.githubusercontent.com/EVORA-project/evora-ontology/refs/heads/main/models/owl/evora_ontology.owl.ttl"
            }
         ] + json.load(open('supporting_ontologies.json'))['ontologies'] + list(map(lambda f: {
            'id': f.split('.')[0],
            'ontology_purl': 'file:///opt/dataload/out/' + f,
            'preferredPrefix': prefix,
            'base_uri': ["https://ictv.global/taxonomy/taxondetails?taxnode_id=","https://ictv.global/isolates#"]
        }, owl_files))
    }
    with open('ols_config.json', 'w') as f:
        f.write(json.dumps(ols_config, indent=2))

def add_xrefs(g, class_iri, field, prefix):
    entries = re.split(';|,', field)
    for entry in entries:
        if ':' in entry:
            k = entry.split(':')[0].strip()
            v = entry.split(':')[1].strip()
            g.add((class_iri, URIRef(XREF), Literal(prefix + v)))
            stmt = BNode()
            g.add((stmt, RDF.type, OWL.Axiom))
            g.add((stmt, OWL.annotatedSource, class_iri))
            g.add((stmt, OWL.annotatedProperty, URIRef(XREF)))
            g.add((stmt, OWL.annotatedTarget, Literal(prefix + v)))
            g.add((stmt, RDFS.label, Literal(k)))
        else:
            g.add((class_iri, URIRef(XREF), Literal(prefix + entry)))



main()
