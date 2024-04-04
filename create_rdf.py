
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

def main():
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

        g = rdflib.Graph()
        g.add((URIRef(ontology_iri), RDF.type, OWL.Ontology))

        for node in nodes_in_release.itertuples():
            class_iri = f'{prefix}{node.taxnode_id}'
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

        g.bind('owl', OWL)
        g.bind('iao', 'http://purl.obolibrary.org/obo/IAO_')
        g.serialize(owl_filename, format='pretty-xml')



def map_molecule(mol_id):
    if mol_id == '0':
        return None
    elif mol_id == '1': # dsDNA	Double-stranded DNA	1	I	NULL	20	30
        return "http://purl.obolibrary.org/obo/SO_0001198" # ds_DNA_viral_sequence

    elif mol_id == '2':	# ssDNA	Single-stranded DNA	2	II	NULL	100	800
        print("todo")
        exit(1)
        return 

    elif mol_id == '3':	# dsRNA	Double-stranded RNA	3	III	NULL	NULL	NULL
        return "http://purl.obolibrary.org/obo/SO_0001169" # ds_RNA_viral_sequence

    elif mol_id == '4':	# ssRNA(+)	Single-stranded RNA - Positive-sense	4	IV	NULL	1300	1400
        return "http://purl.obolibrary.org/obo/SO_0001201" # positive_sense_ssRNA_viral_sequence

    elif mol_id == '5':	# ssRNA(-)	Single-stranded RNA - Negative-sense	5	V	NULL	1500	1600
        return "http://purl.obolibrary.org/obo/SO_0001200" # negative_sense_ssRNA_viral_sequence

    elif mol_id == '6':	# ssRNA-RT	Single-stranded RNA - Positive-sense - replicates through a DNA intermediate	6	VI	NULL	NULL	NULL
    elif mol_id == '7':	# dsDNA-RT	Double-stranded DNA - replicates through a single-strand RNA intermediate	7	VII	NULL	NULL	NULL
    elif mol_id == '8':	# Viroid	Circular Single-stranded RNA	NULL	NULL	NULL	NULL	NULL
    elif mol_id == '9':	# ssDNA(-)	Single-stranded DNA - Negative-sense	NULL	NULL	NULL	500	600
    elif mol_id == '10': # ssDNA(+)	Single-stranded DNA - Positive-sense	NULL	NULL	NULL	300	400
    elif mol_id == '11': # ssDNA(+/-)	Single-stranded DNA - Ambi-sense	NULL	NULL	NULL	200	700

    elif mol_id == '12': # ssRNA(+/-)	Single-stranded RNA - Ambi-sense	NULL	NULL	NULL	1200	1700
        return "http://purl.obolibrary.org/obo/SO_0001202" # ambisense_ssRNA_viral_sequence

    elif mol_id == '13': # dsDNA; ssDNA	DNA - some taxa double stranded, some taxa single standed	NULL	NULL	NULL	10	900
    elif mol_id == '14': # ssRNA	Single-stranded RNA	NULL	NULL	Introduced in MSL33 for the viroids	1100	1800



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




