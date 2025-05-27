
import requests
import urllib.parse
import networkx as nx
import matplotlib.pyplot as plt

VERSION_INFO = urllib.parse.quote("http://www.w3.org/2002/07/owl#versionInfo")
IDENTIFIER = urllib.parse.quote("http://purl.org/dc/terms/identifier")

class ICTVOLSClient:

    def __init__(self, base_url):
        self.cache = {}
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Accept": "application/json"
        }

    def _validate_release(self, release):
        if not isinstance(release, str):
            raise ValueError(f"Release must be a string, got {type(release)}")
        if not release.startswith("MSL"):
            raise ValueError("MSL must start with 'MSL'")

    def get_all_taxa_by_release(self, release):
        self._validate_release(release)
        return list(map(self._map_entity, self._get_all_merged([
            f"{self.base_url}/classes?{VERSION_INFO}={release}&isObsolete=false",
            f"{self.base_url}/classes?{VERSION_INFO}={release}&isObsolete=true",
        ])))

    def get_taxon_by_release(self, release, id_or_label):
        self._validate_release(release)
        res = self._get_all_merged([
            f"{self.base_url}/classes?{VERSION_INFO}={release}&isObsolete=false&{IDENTIFIER}={id_or_label}",
            f"{self.base_url}/classes?{VERSION_INFO}={release}&isObsolete=false&label={id_or_label}",
            f"{self.base_url}/classes?{VERSION_INFO}={release}&isObsolete=true&{IDENTIFIER}={id_or_label}",
            f"{self.base_url}/classes?{VERSION_INFO}={release}&isObsolete=true&label={id_or_label}",
        ])
        if not res:
            raise ValueError(f"Taxon with identifier/label {id_or_label} not found in release {release}")
        if len(res) > 1:
            raise ValueError(f"Multiple taxa found with identifier/label {id_or_label} in release {release}")
        return self._map_entity( res[0] )

    def get_replacements(self, release, id_or_label):
        taxon = self.get_taxon_by_release(release, id_or_label)
        return self._resolve_iris(taxon['replacements'])

    def get_historical_parents(self, release, id_or_label):
        taxon = self.get_taxon_by_release(release, id_or_label)
        return self._resolve_iris(taxon['historical_parents'])

    def get_taxonomic_parents(self, release, id_or_label):
        taxon = self.get_taxon_by_release(release, id_or_label)
        return self._resolve_iris(taxon['taxonomic_parents'])

    def get_history_graph(self, release, id_or_label):
        taxon = self.get_taxon_by_release(release, id_or_label)
        if not taxon:
            raise ValueError(f"Taxon with identifier/label {id_or_label} not found in release {release}")
        return self._get_history_graph(release, id_or_label)

    def _get_history_graph(self, release, id_or_label, _visited=None):
        if _visited is None:
            _visited = set()
        taxon = self.get_taxon_by_release(release, id_or_label)
        if not taxon:
            raise ValueError(f"Taxon with identifier/label {id_or_label} not found in release {release}")
        
        G = nx.DiGraph()
        G.add_node(taxon['ictv_id'], label=taxon['label'])

        parents = self.get_historical_parents(release, id_or_label)
        for parent in parents:
            if parent['ictv_id'] not in _visited:
                _visited.add(parent['ictv_id'])
                G.add_edge(taxon['ictv_id'], parent['ictv_id'])
                G = nx.compose(G, self._get_history_graph(release, parent['ictv_id'], _visited))

        replacements = self.get_replacements(release, id_or_label)
        for replacement in replacements:
            if replacement['ictv_id'] not in _visited:
                _visited.add(replacement['ictv_id'])
                G.add_edge(taxon['ictv_id'], replacement['ictv_id'])
                G = nx.compose(G, self._get_history_graph(release, replacement['ictv_id'], _visited))

        return G

                




        





    def _get_all_merged(self, urls):
        results = []
        for url in urls:
            results.extend(self._get_all(url))
        return results

    def _get_all(self, url): 
        if url in self.cache:
            return self.cache[url]
        else:
            results = []
            page = 0
            while True:
                response = requests.get(url, params={"page": page, "size": 1000})
                if response.status_code != 200:
                    raise Exception(f"Failed to retrieve data: {response.status_code}")
                data = response.json()
                elements = data.get("elements", [])
                results.extend(elements)
                page += 1
                if page > data.get("totalPages", 0):
                    break
            self.cache[url] = results
            return results

    def _map_entity(self, entity):
        return {
            "msl": entity["http://www.w3.org/2002/07/owl#versionInfo"],
            "ictv_id": entity["http://purl.org/dc/terms/identifier"],
            "label": self._ensure_list(entity, "label")[0],
            "obsolescence_reason": self._map_obsolescence_reason( entity.get("http://purl.obolibrary.org/obo/IAO_0000225", None) ),
            "taxonomic_parents": self._ensure_list(entity, "http://www.w3.org/2000/01/rdf-schema#subClassOf"),
            "historical_parents": self._ensure_list(entity, "http://purl.org/dc/terms/replaces"),
            "replacements" : self._ensure_list(entity, "http://purl.org/dc/terms/isReplacedBy"),
        }

    def _map_obsolescence_reason(self, reason):
        if reason == 'http://purl.obolibrary.org/obo/IAO_0000229':
            return 'SPLIT'
        elif reason == 'http://purl.obolibrary.org/obo/IAO_0000227':
            return 'MERGED'
        else:
            return None

    def _double_encode(self, value):
        return urllib.parse.quote(urllib.parse.quote(value))

    def _split_iri(self, iri):
        parts = iri.split('/')
        msl = parts[-2:][0]
        ictv_id = parts[-1:][0]
        return msl, ictv_id

    def _ensure_list(self, obj, key):
        if key in obj:
            value = obj[key]
            if isinstance(value, list):
                return value
            elif isinstance(value, str):
                return [value]
            else:
                return [str(value)]
        else:
            return []
    
    def _resolve_iris(self, iris):
        res = []
        for parent in iris:
            parent_msl, parent_ictv_id = self._split_iri(parent)
            parent = self.get_taxon_by_release(parent_msl, parent_ictv_id)
            res.append(parent)
        return res

if __name__ == "__main__":
    client = ICTVOLSClient("http://localhost:8080/api/v2/ontologies/ictv_all_versions")

    G = client.get_history_graph('MSL6', 'Bovine adenovirus')
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=2000, edge_color='gray', font_size=14, font_weight='bold', labels=nx.get_node_attributes(G, 'label'))
    plt.title("Graph Visualization")
    plt.show()

    
    #print(client.get_replacements('MSL7', 'Cardiovirus'))




