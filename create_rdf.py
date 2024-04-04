
import rdflib
from rdflib import URIRef, BNode, Literal
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDFS, RDF, PROV
import pandas as pd
import os

TERM_REPLACED_BY = "http://purl.obolibrary.org/obo/IAO_0100001"
OBSOLESCENCE_REASON = "http://purl.obolibrary.org/obo/IAO_0000225"
TERM_SPLIT = "http://purl.obolibrary.org/obo/IAO_0000229"
TERMS_MERGED = "http://purl.obolibrary.org/obo/IAO_0000227"

prefix = 'http://ictv.global/'


def main():

    molecules = pd.read_csv('data/taxonomy_molecule.tsv', sep='\t', dtype=str)
# id	abbrev	name	balt_group	balt_roman	description	left_idx	right_idx

    common_graph = rdflib.Graph()

    molecule_superclass_iri = prefix + 'molecule'
    common_graph.add((URIRef(molecule_superclass_iri), RDF.type, OWL.Class))
    common_graph.add((URIRef(molecule_superclass_iri), RDFS.label, Literal("Molecule")))
    common_graph.add((URIRef(molecule_superclass_iri), RDFS.subClassOf, OWL.Thing))

    for molecule in molecules.itertuples():
        molecule_iri = prefix + 'molecule_' + molecule.id
        common_graph.add((URIRef(molecule_iri), RDF.type, OWL.Class))
        common_graph.add((URIRef(molecule_iri), RDFS.subClassOf, URIRef(molecule_superclass_iri)))
        common_graph.add((URIRef(molecule_iri), RDFS.label, Literal(molecule.abbrev)))
        common_graph.add((URIRef(molecule_iri), RDFS.comment, Literal(molecule.name)))

    nodes = pd.read_csv('data/taxonomy_node.tsv', sep='\t', on_bad_lines=lambda x: x[:-1], engine='python', dtype=str)
    delta = pd.read_csv('data/taxonomy_node_delta.tsv', sep='\t', dtype=str)

    # releases = nodes[(nodes['level_id'] == '100') & (nodes['name'] != 'empty_tree') & (nodes['name'] == '2014')]
    releases = nodes[(nodes['level_id'] == '100') & (nodes['name'] != 'empty_tree')]

    for release in releases.itertuples():
        print(f'Processing release {release.name}')
        id = 'ictv_' + release.name
        release_num = release.msl_release_num
        owl_filename = 'out/' + id + '.owl'
        ontology_iri = f'{prefix}{id}'

        nodes_in_release = nodes[(nodes['msl_release_num'] == release_num) & (nodes['level_id'] != '100')]

        g = rdflib.Graph() + common_graph
        g.add((URIRef(ontology_iri), RDF.type, OWL.Ontology))

        for node in nodes_in_release.itertuples():
            class_iri = f'{prefix}{node.taxnode_id}'
            # print(class_iri)

            replacements = delta[delta['prev_taxid'] == node.taxnode_id]

            if not replacements.empty:
                is_merged = replacements['is_merged'].value_counts().get('1', 0) > 0
                is_split = replacements['is_split'].value_counts().get('1', 0) > 0
                # is_moved = replacements['is_moved'].value_counts().get('1', 0) > 0
                # is_promoted = replacements['is_promoted'].value_counts().get('1', 0) > 0
                # is_demoted = replacements['is_demoted'].value_counts().get('1', 0) > 0
                # is_renamed = replacements['is_renamed'].value_counts().get('1', 0) > 0
                # is_new = replacements['is_new'].value_counts().get('1', 0) > 0
                # is_deleted = replacements['is_deleted'].value_counts().get('1', 0) > 0

                for replacement in replacements.itertuples():
                    if not pd.isna(replacement.new_taxid):
                        g.add((URIRef(class_iri), URIRef(TERM_REPLACED_BY), URIRef(prefix+replacement.new_taxid)))

                if is_merged:
                    g.add((URIRef(class_iri), URIRef(OBSOLESCENCE_REASON), URIRef(TERMS_MERGED)))
                if is_split:
                    g.add((URIRef(class_iri), URIRef(OBSOLESCENCE_REASON), URIRef(TERM_SPLIT)))

            g.add((URIRef(class_iri), RDF.type, OWL.Class))
            g.add((URIRef(class_iri), RDFS.label, Literal(node.name)))
            if node.parent_id != release.taxnode_id:
                g.add((URIRef(class_iri), RDFS.subClassOf, URIRef(f'{prefix}{node.parent_id}')))

            # g.add((URIRef(class_iri), RDFS.isDefinedBy, URIRef(ontology_iri)))

            if not pd.isna(node.molecule_id):
                g.add((URIRef(class_iri), RDFS.subClassOf, URIRef(f'{prefix}molecule_{node.molecule_id}')))

            molecule_iri = prefix + 'molecule_' + molecule.id

        g.bind('owl', OWL)
        g.bind('iao', 'http://purl.obolibrary.org/obo/IAO_')
        g.serialize(owl_filename, format='pretty-xml')






# def create_merge_source(g, merges):
#     source = BNode()
#     g.add((source, RDF.type, OWL.Class))

#     list = make_rdf_list(g, [URIRef(f'http://ictv.global/{taxid}') for taxid in merges['prev_taxid']])
#     g.add((source, OWL.oneOf, list))

#     return source

# def make_rdf_list(g, list):
#     if len(list) == 0:
#         return None
#     head = BNode()
#     g.add((head, RDF.first, list[0]))
#     if len(list) > 1:
#         g.add((head, RDF.rest, make_rdf_list(g, list[1:])))
#     return head

main()




