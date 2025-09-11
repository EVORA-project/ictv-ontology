
import requests
import urllib.parse

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
            raise ValueError(f"MSL must start with 'MSL', got {release}")

    def get_all_taxa_by_release(self, release):
        self._validate_release(release)
        return list(map(self._map_entity, self._get_all_merged([
            f"{self.base_url}/classes?{VERSION_INFO}={release}&isObsolete=false",
            f"{self.base_url}/classes?{VERSION_INFO}={release}&isObsolete=true",
        ])))

    def get_taxon_by_release(self, id_or_label, release):
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

    def get_current_replacements(self, id_or_label, release=None):
        if release != None:
            taxon = self.get_taxon_by_release(id_or_label, release)
            return self._resolve_iris(taxon['current_replacements'])
        else:
            not_obsolete = self._get_all_merged([
                f"{self.base_url}/classes?isObsolete=false&{IDENTIFIER}={id_or_label}",
                f"{self.base_url}/classes?isObsolete=false&label={id_or_label}",
            ])
            if len(not_obsolete) > 0:
                return [self._map_entity( not_obsolete[0] )]
            obsolete = self._get_all_merged([
                f"{self.base_url}/classes?isObsolete=true&{IDENTIFIER}={id_or_label}",
                f"{self.base_url}/classes?isObsolete=true&label={id_or_label}",
            ])
            if len(obsolete) > 0:
                replacement_iris = self._map_entity(obsolete[0])['current_replacements']
                replacements = self._resolve_iris(replacement_iris)
                replacements = [r for r in replacements if r['is_obsolete'] != True]
                return replacements
            return []

    def get_historical_parents(self, id_or_label, release=None):
        taxon = self.get_taxon_by_release(id_or_label, release)
        return self._resolve_iris(taxon['replaces'])

    def get_taxonomic_parents(self, id_or_label, release=None):
        taxon = self.get_taxon_by_release(id_or_label, release)
        return self._resolve_iris(taxon['taxonomic_parents'])





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
            "is_obsolete": entity.get("isObsolete", False),
            "obsolescence_reason": self._map_obsolescence_reason( entity.get("http://purl.obolibrary.org/obo/IAO_0000225", None) ),
            "taxonomic_parents": self._ensure_list(entity, "http://www.w3.org/2000/01/rdf-schema#subClassOf"),
            "replaces": self._ensure_list(entity, "http://www.w3.org/ns/prov#wasRevisionOf"),
            "replaced_by": self._ensure_list(entity, "http://www.w3.org/ns/prov#hadRevision"),
            "current_replacements" : self._ensure_list(entity, "http://purl.obolibrary.org/obo/IAO_0100001"),
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
            parent = self.get_taxon_by_release(parent_ictv_id, parent_msl)
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




