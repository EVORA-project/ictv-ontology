
import rdflib
from rdflib import URIRef, BNode, Literal
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDFS, RDF, PROV, FOAF
import pandas as pd
import os
import json
import re
import gzip

TERM_REPLACED_BY = "http://purl.obolibrary.org/obo/IAO_0100001"
OBSOLESCENCE_REASON = "http://purl.obolibrary.org/obo/IAO_0000225"
TERM_SPLIT = "http://purl.obolibrary.org/obo/IAO_0000229"
TERMS_MERGED = "http://purl.obolibrary.org/obo/IAO_0000227"
SYNONYM = "http://www.geneontology.org/formats/oboInOwl#hasExactSynonym"
XREF = "http://www.geneontology.org/formats/oboInOwl#hasDbXref"

def main():

    common_graph = rdflib.Graph()
    common_graph.parse(location='ictv_molecules.owl')
    
    nodes = pd.read_csv('data/taxonomy_node.tsv', sep='\t', on_bad_lines=lambda x: x[:-1], engine='python', dtype=str)
    delta = pd.read_csv('data/taxonomy_node_delta.tsv', sep='\t', dtype=str)

    releases = nodes[(nodes['level_id'] == '100') & (nodes['name'] != 'empty_tree')]

    prefix = 'http://ictv.global/'

    for release in releases.itertuples():
        print(f'Processing release {release.name}')
        id = 'ictv_' + release.name
        release_num = release.msl_release_num
        owl_filename = 'out/' + id + '.owl'
        ontology_iri = f'{prefix}{id}'

        nodes_in_release = nodes[(nodes['msl_release_num'] == release_num) & (nodes['level_id'] != '100')]

        g = rdflib.Graph() + common_graph
        g.add((URIRef(ontology_iri), RDF.type, OWL.Ontology))
        g.add((URIRef(ontology_iri), RDFS.label, Literal("ICTV Taxonomy (" + release.name + ")")))
        g.add((URIRef(ontology_iri), RDFS.comment, Literal("International Committee on Taxonomy of Viruses (ICTV)")))
        g.add((URIRef(ontology_iri), FOAF.homepage, URIRef("https://ictv.global/")))
        g.add((URIRef(ontology_iri), OWL.versionInfo, Literal(str(release_num))))

        for node in nodes_in_release.itertuples():
            class_iri = f'{prefix}ictv_{node.taxnode_id}'
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

                for replacement in replacements.itertuples():
                    if not pd.isna(replacement.new_taxid):
                        g.add((URIRef(class_iri), URIRef(TERM_REPLACED_BY), URIRef(prefix+replacement.new_taxid)))

                if is_merged:
                    g.add((URIRef(class_iri), URIRef(OBSOLESCENCE_REASON), URIRef(TERMS_MERGED)))
                if is_split:
                    g.add((URIRef(class_iri), URIRef(OBSOLESCENCE_REASON), URIRef(TERM_SPLIT)))

            g.add((URIRef(class_iri), RDF.type, OWL.Class))
            g.add((URIRef(class_iri), RDFS.label, Literal(node.name)))
            if node.parent_id != release.ictv_id:
                g.add((URIRef(class_iri), RDFS.subClassOf, URIRef(f'{prefix}ictv_{node.parent_id}')))
            g.add((URIRef(class_iri), RDFS.isDefinedBy, URIRef(ontology_iri)))

            if not pd.isna(node.abbrev_csv):
                g.add((URIRef(class_iri), URIRef(SYNONYM), Literal(node.abbrev_csv)))

            if not pd.isna(node.genbank_accession_csv):
                add_xrefs(g, class_iri, node.genbank_accession_csv, 'genbank:')
            if not pd.isna(node.refseq_accession_csv):
                add_xrefs(g, class_iri, node.refseq_accession_csv, 'refseq:')

        g.bind('owl', OWL)
        g.bind('iao', 'http://purl.obolibrary.org/obo/IAO_')
        g.bind('oio', 'http://www.geneontology.org/formats/oboInOwl#')

        g.serialize(owl_filename, format='pretty-xml')

    owl_files = [f for f in os.listdir('out') if f.endswith('.owl')]
    ols_config = {
        'ontologies': list(map(lambda f: {
            'id': f.split('.')[0],
            'ontology_purl': './out/' + f
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
            g.add((URIRef(class_iri), URIRef(XREF), Literal(prefix + v)))
            stmt = BNode()
            g.add((stmt, RDF.type, OWL.Axiom))
            g.add((stmt, OWL.annotatedSource, URIRef(class_iri)))
            g.add((stmt, OWL.annotatedProperty, URIRef(XREF)))
            g.add((stmt, OWL.annotatedTarget, Literal(prefix + v)))
            g.add((stmt, RDFS.label, Literal(k)))
        else:
            g.add((URIRef(class_iri), URIRef(XREF), Literal(prefix + entry)))



main()
