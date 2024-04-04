
import rdflib
from rdflib import URIRef
from rdflib.namespace import OWL, RDFS, RDF, PROV
import pandas as pd
import os

nodes = pd.read_csv('data/taxonomy_node.tsv', sep='\t', on_bad_lines=lambda x: x[:-1], engine='python', dtype=str)
delta = pd.read_csv('data/taxonomy_node_delta.tsv', sep='\t', dtype=str)

releases = nodes[(nodes['level_id'] == '100') & (nodes['name'] != 'empty_tree')]

prefix = 'http://ictv.global/'

for release in releases.itertuples():
    print(f'Processing release {release.name}')
    id = 'ictv_' + release.name
    release_num = release.msl_release_num
    template_filename = 'out/templates/' + id + '.robot.tsv'
    owl_filename = 'out/owl/' + id + '.owl'
    ontology_iri = f'{prefix}{id}'

    release_merge_splits = merge_split[merge_split['dist'] == release.msl_release_num]

    nodes_in_release = nodes[(nodes['msl_release_num'] == release_num) & (nodes['level_id'] != '100')]

    g = rdflib.Graph()
    g.add((URIRef(ontology_iri), RDF.type, OWL.Ontology))

    for node in nodes_in_release.itertuples():
        deltas = delta[delta['new_taxid'] == node.taxnode_id]

        if not merge_splits.empty:
            is_merged = merge_splits['is_merged'].unique().item()
            is_split = merge_splits['is_split'].unique().item()

        class_iri = f'{prefix}{node.taxnode_id}'
        g.add((URIRef(class_iri), RDF.type, OWL.Class))
        g.add((URIRef(class_iri), RDFS.label, rdflib.Literal(node.name)))
        if node.parent_id != release.ictv_id:
            g.add((URIRef(class_iri), RDFS.subClassOf, URIRef(f'{prefix}ictv_{node.parent_id}')))
        g.add((URIRef(class_iri), RDFS.isDefinedBy, URIRef(ontology_iri)))

    g.bind('owl', OWL)
    g.serialize(owl_filename, format='pretty-xml')



