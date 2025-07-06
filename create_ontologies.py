

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
IDENTIFIER = "http://purl.org/dc/terms/identifier"
RANK = "http://purl.obolibrary.org/obo/TAXRANK_1000000"


# taxnode_id: Taxon within a specific release
# ictv_id: Taxon across releases
# 
# All ictv_ids are taxnode_ids but not all taxnode_ids are ictv_ids
# 

def main():

    common_graph = rdflib.Graph()
    common_graph.parse('imported_terms.ttl', format='ttl')
    
    nodes = pd.read_csv('data/taxonomy_node_export.utf8.txt', sep='\t', on_bad_lines=lambda x: x[:-1], engine='python', dtype=str)
    delta = pd.read_csv('data/taxonomy_node_delta.utf8.txt', sep='\t', dtype=str)
    isolates = pd.read_csv('data/species_isolates.utf8.txt', sep='\t', dtype=str)

    releases = nodes[(nodes['level_id'] == '100') & (nodes['name'] != 'empty_tree')]
  
    ontologies = []

    taxnode_id_to_ictv_id = {}
    for node in nodes.itertuples():
        if node.taxnode_id in taxnode_id_to_ictv_id:
            raise Exception(f'Taxnode ID {node.ictv_id} already exists')
        taxnode_id_to_ictv_id[node.taxnode_id] = node.ictv_id

    latest_release = releases['msl_release_num'].max()

    for release in releases.itertuples():

        #if int(release.msl_release_num) < 39:
            #continue

        print(f'Creating ontology for ICTV release {release.name}')

        msl_id = 'MSL' + release.msl_release_num
        ontology_iri = f'http://ictv.global/id/{msl_id}'

        nodes_in_release = nodes[(nodes['msl_release_num'] == release.msl_release_num) & (nodes['level_id'] != '100')]

        g = rdflib.Graph()
        ontologies.append(g)

        g.add((URIRef(ontology_iri), RDF.type, OWL.Ontology))
        g.add((URIRef(ontology_iri), RDFS.label, Literal("ICTV Taxonomy (" + release.name + ")")))
        g.add((URIRef(ontology_iri), RDFS.comment, Literal("International Committee on Taxonomy of Viruses (ICTV)")))
        g.add((URIRef(ontology_iri), FOAF.homepage, URIRef("http://ictv.global/")))
        g.add((URIRef(ontology_iri), OWL.versionInfo, Literal(str(release.msl_release_num))))

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

                g.add((class_iri, OWL.deprecated, Literal('true', datatype=URIRef('http://www.w3.org/2001/XMLSchema#boolean'))))

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
                    g.add((class_iri, URIRef(TERM_REPLACED_BY), URIRef(replacement_iri)))
                    g.add((class_iri, URIRef(REPLACED_BY), URIRef(replacement_iri)))

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

            if node.rank == "realm":
                # "Viruses" from NCBITaxon used as the root for the ontology
                g.add((class_iri, RDFS.subClassOf, URIRef('http://purl.obolibrary.org/obo/NCBITaxon_10239')))

            if node.parent_id != release.ictv_id:
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


    g_all = rdflib.Graph()
    for g in ontologies:
        g_all += g

    # For all classes that aren't deprecated yet
    # If they are not from the latest ICTV version, add a replaced_by to their latest version
    # and mark them as deprecated
    for g in ontologies:
        ontology = g.value(predicate=RDF.type, object=OWL.Ontology)
        ontology_id = ontology.split('/')[-1]
        if ontology_id == 'MSL' + latest_release:
            continue
        for c in g.subjects(predicate=RDF.type, object=OWL.Class):
            if len(list(g.triples((c, OWL.deprecated, Literal('true', datatype=URIRef('http://www.w3.org/2001/XMLSchema#boolean')))))) == 0:
                ictv_id = g.value(subject=c, predicate=URIRef(IDENTIFIER))
                latest_version = sorted(list(g_all.subjects(predicate=URIRef(IDENTIFIER), object=ictv_id)))[-1]
                if latest_version != c:
                    g.add((URIRef(c), OWL.deprecated, Literal('true', datatype=URIRef('http://www.w3.org/2001/XMLSchema#boolean'))))
                    g.add((URIRef(c), URIRef(REPLACED_BY), latest_version))
                    g.add((URIRef(c), URIRef(TERM_REPLACED_BY), latest_version))

    # For all of the replaced_by, add the inverse triple "replaces"
    for g in ontologies:
        for c in g.subjects(predicate=RDF.type, object=OWL.Class):
            for replaces in g_all.subjects(predicate=URIRef(REPLACED_BY), object=c):
                g.add((URIRef(c), URIRef(REPLACES), replaces))

    all_g_merged = rdflib.Graph()

    for g_orig in ontologies:
        g = rdflib.Graph()
        g += g_orig
        ontology = g.value(predicate=RDF.type, object=OWL.Ontology)
        ontology_id = ontology.split('/')[-1]
        version = g.value(subject=ontology, predicate=OWL.versionInfo)
        print(f'Building final ontology for {ontology_id} (version = {version})')
        for other_g in ontologies:
            other_ontology = other_g.value(predicate=RDF.type, object=OWL.Ontology)
            other_version = other_g.value(subject=other_ontology, predicate=OWL.versionInfo)
            if other_version < version:
                print(f'- merging {other_version} into {version}')
                for c in g.subjects(predicate=RDF.type, object=OWL.Class):
                    ictv_id = g.value(subject=c, predicate=URIRef(IDENTIFIER))
                    prev_versions = list(other_g.subjects(predicate=URIRef(IDENTIFIER), object=ictv_id))
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
                                # g.add((stmt, RDFS.isDefinedBy, other_ontology))
                                g.add((stmt, OWL.versionInfo, Literal( other_ontology.split('/')[-1])))
        g += common_graph
        all_g_merged += g

    all_g_merged.bind('owl', OWL)
    all_g_merged.bind('iao', 'http://purl.obolibrary.org/obo/IAO_')
    all_g_merged.bind('oio', 'http://www.geneontology.org/formats/oboInOwl#')
    all_g_merged.bind('omo', 'http://purl.obolibrary.org/obo/OMO_')
    all_g_merged.bind('dcterms', 'http://purl.org/dc/terms/')
    all_g_merged.bind('rdfs', RDFS)
    all_g_merged.bind('taxrank', 'http://purl.obolibrary.org/obo/TAXRANK_')
    all_g_merged.serialize('out/ictv_all_versions.owl.ttl', format="ttl")

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
            'preferred_root_term': ['http://purl.obolibrary.org/obo/NCBITaxon_10239'],
            'base_uri': list(map(lambda f: 'http://ictv.global/id/' + f.split('.')[0] + '/', owl_files))
        }]
    }

    with open('ols_config_combined.json', 'w') as f:
        f.write(json.dumps(ols_config_combined, indent=2))

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






main()
