

import pandas as pd
import os

nodes = pd.read_csv('data/taxonomy_node.tsv', sep='\t', on_bad_lines=lambda x: x[:-1], engine='python', dtype=str)
merge_split = pd.read_csv('data/taxonomy_node_merge_split.tsv', sep='\t', dtype=str)

releases = nodes[(nodes['level_id'] == '100') & (nodes['name'] != 'empty_tree')]

for release in releases.itertuples():
    print(f'Processing release {release.name}')
    id = 'ictv_' + release.name
    release_num = release.msl_release_num
    template_filename = 'out/templates/' + id + '.robot.tsv'
    owl_filename = 'out/owl/' + id + '.owl'
    ontology_iri = f'http://ictv.global/{id}'

    nodes_in_release = nodes[(nodes['msl_release_num'] == release_num) & (nodes['level_id'] != '100')]

    columns = ['id', 'label', 'type', 'parent', 'is_defined_by']

    out_template = pd.DataFrame(columns=columns)
    out_template['id'] = 'ICTV:' + nodes_in_release['taxnode_id'].astype(str)
    out_template['label'] = nodes_in_release['name']
    out_template['type'] = 'owl:Class'
    out_template['parent'] = 'ICTV:' + nodes_in_release['parent_id'].astype(str)
    out_template['is_defined_by'] = ontology_iri

    print("Release id is " + str(release.ictv_id))
    out_template['parent'] = out_template['parent'].replace('ICTV:' + str(release.ictv_id), 'owl:Thing')

    out_template = pd.concat([
          pd.DataFrame([['ID','LABEL','TYPE','SC %','AI rdfs:isDefinedBy']], columns=columns), out_template])

    out_template.to_csv(template_filename, sep='\t', index=False)

    os.system(f'robot template --add-prefix \'ICTV: http://ictv.global/\' --template {template_filename} --ontology-iri {ontology_iri} --output {owl_filename}')


