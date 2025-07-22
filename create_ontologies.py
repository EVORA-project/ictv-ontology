

import rdflib
from rdflib import URIRef, BNode, Literal
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDFS, RDF, PROV, FOAF, SKOS
import pandas as pd
import os
import json
import re
from concurrent.futures import ProcessPoolExecutor, as_completed

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
IDENTIFIER = "http://purl.org/dc/terms/identifier"
RANK = "http://purl.obolibrary.org/obo/TAXRANK_1000000"
WAS_REVISION_OF = "http://www.w3.org/ns/prov#wasRevisionOf"
HAD_REVISION = "http://www.w3.org/ns/prov#hadRevision"


ontology_iri = f'http://ictv.global/'

# taxnode_id: Taxon within a specific release
# ictv_id: Taxon across releases
# 
# All ictv_ids are taxnode_ids but not all taxnode_ids are ictv_ids
# 

def main():

    common_graph = rdflib.Graph()
    common_graph.parse('imported_terms.ttl', format='ttl')
    
    nodes = pd.read_csv('data/taxonomy_node_export.utf8.txt', sep='\t', on_bad_lines=lambda x: x[:-1], engine='python', dtype=str)

    releases = nodes[(nodes['level_id'] == '100') & (nodes['name'] != 'empty_tree')]

    # for testing pretend there are only latest 3 releases
    # releases = releases.sort_values(by='msl_release_num', ascending=False).head(3)


    taxnode_id_to_ictv_id = {}
    for node in nodes.itertuples():
        if node.taxnode_id in taxnode_id_to_ictv_id:
            raise Exception(f'Taxnode ID {node.ictv_id} already exists')
        taxnode_id_to_ictv_id[node.taxnode_id] = node.ictv_id

    latest_release = str(releases['msl_release_num'].astype(int).max())

    print(f'Latest release: MSL{latest_release}')

    ontologies = []

    with ProcessPoolExecutor() as executor:
        futures = [
            executor.submit(build_ontology_for_release, release.to_dict())
            for _, release in releases.iterrows()
        ]
        ontologies = []
        for future in as_completed(futures):
            rdfxml = future.result()
            g = rdflib.Graph()
            g.parse(data=rdfxml, format="xml")
            ontologies.append(g)

    print(f'Built {len(ontologies)} ontologies, merging into one graph ...')

    g_all = rdflib.Graph()
    for g in ontologies:
        g_all += g

    print('Marking deprecated terms ...')

    # For all classes that aren't deprecated yet
    # If they are not from the latest ICTV version mark them as deprecated
    for c in g_all.subjects(predicate=RDF.type, object=OWL.Class):
        version = g_all.value(subject=c, predicate=OWL.versionInfo)
        if version and str(version) != 'MSL'+latest_release:
            g_all.add((c, OWL.deprecated, Literal(True)))

    print('Annotating terms with their final replacement(s) ...')

    for cl in g_all.subjects(predicate=RDF.type, object=OWL.Class):
        working_set = set([cl])
        while True:
            new_set = set()
            for c in working_set:
                replacements = list(g_all.objects(subject=c, predicate=URIRef(HAD_REVISION)))
                if len(replacements) > 0:
                    new_set.update(replacements)
                else:
                    new_set.add(c)
            if new_set == working_set:
                break
            working_set = new_set
        if working_set != set([cl]):
            for c in working_set:
                g_all.add((cl, URIRef(TERM_REPLACED_BY), c))

    print('Annotating former names ...')

    for cl in g_all.subjects(predicate=RDF.type, object=OWL.Class):
        cur_name = g_all.value(subject=cl, predicate=RDFS.label)
        other_versions = list(g_all.subjects(predicate=URIRef(IDENTIFIER), object=g_all.value(subject=cl, predicate=URIRef(IDENTIFIER))))
        for other_term in other_versions:
            other_version = str(g_all.value(subject=other_term, predicate=OWL.versionInfo))
            # if older version
            if other_version and int(other_version.split('MSL')[1]) < int(str(g_all.value(subject=cl, predicate=OWL.versionInfo)).split('MSL')[1]):
                older_name = g_all.value(subject=other_term, predicate=RDFS.label)
                if older_name and older_name != cur_name:
                    if len(list(g_all.triples((cl, URIRef(SYNONYM), Literal(older_name))))) == 0:
                        g_all.add((cl, URIRef(SYNONYM), Literal(older_name)))
                        stmt = BNode()
                        g_all.add((stmt, RDF.type, OWL.Axiom))
                        g_all.add((stmt, OWL.annotatedSource, cl))
                        g_all.add((stmt, OWL.annotatedProperty, URIRef(SYNONYM)))
                        g_all.add((stmt, OWL.annotatedTarget, Literal(older_name)))
                        g_all.add((stmt, URIRef(SYNONYM_TYPE), URIRef(PREVIOUS_NAME)))
                        g_all.add((stmt, OWL.versionInfo, Literal(other_version)))
        

    print('Building the final output ontology ...')

    g_all += common_graph

    g_all.add((URIRef(ontology_iri), RDF.type, OWL.Ontology))
    g_all.add((URIRef(ontology_iri), RDFS.label, Literal("ICTV Taxonomy")))
    g_all.add((URIRef(ontology_iri), RDFS.comment, Literal("International Committee on Taxonomy of Viruses (ICTV)")))
    g_all.add((URIRef(ontology_iri), FOAF.homepage, URIRef("http://ictv.global/")))
    g_all.add((URIRef(ontology_iri), URIRef('http://purl.obolibrary.org/obo/IAO_0000700'), URIRef('http://purl.obolibrary.org/obo/NCBITaxon_10239')))

    g_all.bind('owl', OWL)
    g_all.bind('iao', 'http://purl.obolibrary.org/obo/IAO_')
    g_all.bind('oio', 'http://www.geneontology.org/formats/oboInOwl#')
    g_all.bind('omo', 'http://purl.obolibrary.org/obo/OMO_')
    g_all.bind('dcterms', 'http://purl.org/dc/terms/')
    g_all.bind('rdfs', RDFS)
    g_all.bind('taxrank', 'http://purl.obolibrary.org/obo/TAXRANK_')
    g_all.bind('prov', 'http://www.w3.org/ns/prov#')
    g_all.serialize('out/ictv_all_versions.owl.ttl', format="ttl")

    owl_files = [f for f in os.listdir('out') if f.startswith('MSL') and f.endswith('.owl.ttl')]
    ols_config = {
        'ontologies': json.load(open('supporting_ontologies.json'))['ontologies'] + list(map(lambda f: {
            'id': f.split('.')[0],
            'ontology_purl': 'file:///opt/dataload/out/' + f,
            'preferredPrefix': "ICTV",
            'base_uri': ['http://ictv.global/id/' + f.split('.')[0] + '/']
        }, owl_files))
    }
    with open('ols_config.json', 'w') as f:
        f.write(json.dumps(ols_config, indent=2))

    ols_config_combined = {
         'ontologies': json.load(open('supporting_ontologies.json'))['ontologies'] + [{
            'id': 'ictv',
            'ontology_purl': 'file:///opt/dataload/out/ictv_all_versions.owl.ttl',
            'preferredPrefix': "ICTV",
            'base_uri': list(map(lambda f: 'http://ictv.global/id/' + f.split('.')[0] + '/', owl_files))
        }]
    }

    with open('ols_config_combined.json', 'w') as f:
        f.write(json.dumps(ols_config_combined, indent=2))


def build_ontology_for_release(release):

    print(f'Creating ontology for ICTV release {release['name']}')

    nodes = pd.read_csv('data/taxonomy_node_export.utf8.txt', sep='\t', on_bad_lines=lambda x: x[:-1], engine='python', dtype=str)
    delta = pd.read_csv('data/taxonomy_node_delta.utf8.txt', sep='\t', dtype=str)
    isolates = pd.read_csv('data/species_isolates.utf8.txt', sep='\t', dtype=str)

    taxnode_id_to_ictv_id = {}
    for node in nodes.itertuples():
        if node.taxnode_id in taxnode_id_to_ictv_id:
            raise Exception(f'Taxnode ID {node.ictv_id} already exists')
        taxnode_id_to_ictv_id[node.taxnode_id] = node.ictv_id

    msl_id = 'MSL' + release['msl_release_num']

    nodes_in_release = nodes[(nodes['msl_release_num'] == release['msl_release_num']) & (nodes['level_id'] != '100')]

    g = rdflib.Graph()

    for node in nodes_in_release.itertuples():
        class_iri = URIRef(f'http://ictv.global/id/{msl_id}/ICTV{node.ictv_id}')

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

            # an ancestor changed but I didn't necessarily change
            is_lineage_updated = replacements['is_lineage_updated'].value_counts().get('1', 0) > 0

            replacement_iris = []

            for replacement in replacements.itertuples():
                if pd.isna(replacement.new_taxid):
                    continue
                if replacement.new_taxid in taxnode_id_to_ictv_id:
                    replacement_iris.append(f'http://ictv.global/id/MSL{replacement.msl}/ICTV'+taxnode_id_to_ictv_id[replacement.new_taxid])
                else:
                    print('Warning: replacement taxid ' + replacement.new_taxid + ' not found in release ' + replacement.msl)
                    replacement_iris.append(f'http://ictv.global/id/MSL{replacement.msl}/ICTV'+replacement.new_taxid)

            for replacement_iri in replacement_iris:
                g.add((class_iri, URIRef(HAD_REVISION), URIRef(replacement_iri)))
                g.add((URIRef(replacement_iri), URIRef(WAS_REVISION_OF), class_iri))

            if is_new:
                year = replacements['new_taxid'][:4]
                g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"New in " + year)))
            elif is_merged:
                g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"Merged into {', '.join(replacement_iris)}")))
                g.add((class_iri, URIRef(OBSOLESCENCE_REASON), URIRef(TERMS_MERGED)))
            elif is_split:
                g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"Split into {', '.join(replacement_iris)}")))
                g.add((class_iri, URIRef(OBSOLESCENCE_REASON), URIRef(TERM_SPLIT)))
            elif is_moved:
                g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"Moved to {', '.join(replacement_iris)}")))
            elif is_promoted:
                g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"Promoted, see {', '.join(replacement_iris)}")))
            elif is_demoted:
                g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"Demoted, see {', '.join(replacement_iris)}")))
            elif is_renamed:
                g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"Renamed, see {', '.join(replacement_iris)}")))
            elif is_deleted:
                g.add((class_iri, URIRef(EDITOR_NOTE), Literal(f"Deleted")))

        g.add((class_iri, RDF.type, OWL.Class))
        g.add((class_iri, RDFS.label, Literal(node.name)))
        g.add((class_iri, URIRef(IDENTIFIER), Literal("ICTV" + node.ictv_id)))
        g.add((class_iri, OWL.versionInfo, Literal(str(msl_id))))
        g.add((class_iri, URIRef(RANK), URIRef(map_rank(node.rank))))

        if node.parent_id == release['taxnode_id']:
            # "Viruses" from NCBITaxon used as the root for the ontology
            g.add((class_iri, RDFS.subClassOf, URIRef('http://purl.obolibrary.org/obo/NCBITaxon_10239')))
        else:
            if node.parent_id in taxnode_id_to_ictv_id:
                g.add((class_iri, RDFS.subClassOf, URIRef(f'http://ictv.global/id/{msl_id}/ICTV{taxnode_id_to_ictv_id[node.parent_id]}')))
        g.add((class_iri, RDFS.isDefinedBy, URIRef(ontology_iri)))

        if not pd.isna(node.abbrev_csv):
            g.add((class_iri, URIRef(SYNONYM), Literal(node.abbrev_csv)))

        # if not pd.isna(node.genbank_accession_csv):
        #     add_xrefs(g, class_iri, node.genbank_accession_csv, 'genbank:')
        # if not pd.isna(node.refseq_accession_csv):
        #     add_xrefs(g, class_iri, node.refseq_accession_csv, 'refseq:')

        taxnode_isolates = isolates[isolates['taxnode_id'] == node.taxnode_id]

        for isolate in taxnode_isolates.itertuples():
            isolate_iri = f'http://ictv.global/id/VMR{isolate.isolate_id}'
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

    return g.serialize(format='xml')


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

def map_rank(rank):
    if rank == "realm":
        return "http://purl.obolibrary.org/obo/TAXRANK_0001004" # clade
    if rank == "kingdom":
        return "http://purl.obolibrary.org/obo/TAXRANK_0000017"
    if rank == "subkingdom":
        return "http://purl.obolibrary.org/obo/TAXRANK_0000029"
    if rank == "phylum":
        return "http://purl.obolibrary.org/obo/TAXRANK_0000001"
    if rank == "subphylum":
        return "http://purl.obolibrary.org/obo/TAXRANK_0000008"
    if rank == "class":
        return "http://purl.obolibrary.org/obo/TAXRANK_0000002"
    if rank == "subclass":
        return "http://purl.obolibrary.org/obo/TAXRANK_0000007"
    if rank == "order":
        return "http://purl.obolibrary.org/obo/TAXRANK_0000003"
    if rank == "suborder":
        return "http://purl.obolibrary.org/obo/TAXRANK_0000014"
    if rank == "family":
        return "http://purl.obolibrary.org/obo/TAXRANK_0000004"
    if rank == "subfamily":
        return "http://purl.obolibrary.org/obo/TAXRANK_0000024"
    if rank == "genus":
        return "http://purl.obolibrary.org/obo/TAXRANK_0000005"
    if rank == "subgenus":
        return "http://purl.obolibrary.org/obo/TAXRANK_0000009"
    if rank == "species":
        return "http://purl.obolibrary.org/obo/TAXRANK_0000006"

if __name__ == "__main__":
    main()
