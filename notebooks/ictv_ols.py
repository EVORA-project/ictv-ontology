"""Compatibility helpers for the ICTV OLS notebook examples.

The notebook keeps the historical example API from this module, while the
implementation delegates normal lookup work to the maintained Python helper in
``helpers/python/ictv-api.py``.
"""

from __future__ import annotations

import gzip
import re
from importlib import util
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

VERSION_INFO = "http://www.w3.org/2002/07/owl#versionInfo"
IDENTIFIER = "http://purl.org/dc/terms/identifier"
SUBCLASS_OF = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
WAS_REVISION_OF = "http://www.w3.org/ns/prov#wasRevisionOf"
HAD_REVISION = "http://www.w3.org/ns/prov#hadRevision"
REPLACED_BY = "http://purl.obolibrary.org/obo/IAO_0100001"
OBSOLESCENCE_REASON = "http://purl.obolibrary.org/obo/IAO_0000225"
LATEST_ONTOLOGY_METADATA = "https://www.ebi.ac.uk/ols4/api/ontologies/ictv"


def _helper_path() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parent, *here.parents):
        path = candidate / "helpers" / "python" / "ictv-api.py"
        if path.exists():
            return path
    raise FileNotFoundError("Cannot locate helpers/python/ictv-api.py")


def _load_helper():
    path = _helper_path()
    spec = util.spec_from_file_location("ictv_api_helper", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load ICTV helper from {path}")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_helper = _load_helper()


class ICTVOLSClient(_helper.ICTVOLSClient):
    """Notebook-facing client preserving the original example method names."""

    def __init__(self, base_url: str = "https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv"):
        super().__init__(base_url)
        self._release_entities: Optional[List[Dict[str, Any]]] = None
        self._release_entities_by_iri: Dict[str, Dict[str, Any]] = {}

    def _validate_release(self, release: str) -> None:
        if not isinstance(release, str):
            raise ValueError(f"Release must be a string, got {type(release)}")
        if not re.match(r"^MSL\d+$", release, flags=re.IGNORECASE):
            raise ValueError(f"MSL must look like 'MSL7', got {release}")

    def get_all_taxa_by_release(self, release: str) -> List[Dict[str, Any]]:
        """Return all taxa for one ICTV release.

        OLS v2 class responses contain ``owl:versionInfo``, but the live v2
        endpoint currently does not reliably filter on that property as a query
        parameter. We try the OLS filter first and fall back to the ontology file
        advertised by the OLS metadata endpoint when needed.
        """
        self._validate_release(release)
        items = self._get_all_from_ols_release_filter(release)
        if not items:
            wanted = release.upper()
            items = [e for e in self._load_release_entities() if str(e.get(VERSION_INFO, "")).upper() == wanted]
        return sorted((self._map_entity(e) for e in items), key=lambda x: x.get("ictv_id") or "")

    def get_taxon_by_release(self, id_or_label: str, release: str) -> Dict[str, Any]:
        self._validate_release(release)
        candidates = self._find_release_candidates(id_or_label, release)
        if not candidates:
            raise ValueError(f"Taxon with identifier/label {id_or_label} not found in release {release}")
        if len(candidates) > 1:
            raise ValueError(f"Multiple taxa found with identifier/label {id_or_label} in release {release}")
        return self._map_entity(candidates[0])

    def get_current_replacements(self, id_or_label: str, release: Optional[str] = None) -> List[Dict[str, Any]]:
        if release is not None:
            taxon = self.get_taxon_by_release(id_or_label, release)
            replacements = self._resolve_iris(taxon["current_replacements"])
            return [r for r in replacements if not r["is_obsolete"]]

        mapped = self._current_replacements_without_release(id_or_label)
        return [self._legacy_from_mapped(m) for m in mapped]

    def get_historical_parents(self, id_or_label: str, release: str) -> List[Dict[str, Any]]:
        taxon = self.get_taxon_by_release(id_or_label, release)
        return self._resolve_iris(taxon["replaces"])

    def get_taxonomic_parents(self, id_or_label: str, release: str) -> List[Dict[str, Any]]:
        taxon = self.get_taxon_by_release(id_or_label, release)
        return self._resolve_iris(taxon["taxonomic_parents"])

    def _get_all_from_ols_release_filter(self, release: str) -> List[Dict[str, Any]]:
        page = 0
        size = 1000
        out: List[Dict[str, Any]] = []
        while True:
            data = self.ols("classes", {
                VERSION_INFO: release,
                "includeObsoleteEntities": "true",
                "page": page,
                "size": size,
            })
            batch = data.get("elements") or []
            if not batch:
                return []
            if any(str(e.get(VERSION_INFO, "")).upper() != release.upper() for e in batch):
                return []
            out.extend(batch)
            page += 1
            if page >= int(data.get("totalPages") or 0):
                return out

    def _find_release_candidates(self, id_or_label: str, release: str) -> List[Dict[str, Any]]:
        value = str(id_or_label).strip()
        wanted_release = release.upper()
        wanted_text = self.normText(value)
        candidates: List[Dict[str, Any]] = []

        if self.isIctvId(value):
            iri = f"http://ictv.global/id/{release.upper()}/{value.upper()}"
            direct = self.retrieveTaxonByIRI(iri)
            if direct and self._entity_release(direct) == wanted_release and self.entityMatchesIctvId(direct, value):
                candidates.append(direct)
            for e in self.seekOntologyTaxonByClassId(value):
                full = self._full_entity(e)
                if self._entity_release(full) == wanted_release and self.entityMatchesIctvId(full, value):
                    candidates.append(full)
        else:
            for e in self._seek_exact_label(value, include_obsolete="true"):
                full = self._full_entity(e)
                if self._entity_release(full) == wanted_release and self.normText(self.normalizeValue(full.get("label"))) == wanted_text:
                    candidates.append(full)

        if not candidates:
            for e in self._load_release_entities():
                if self._entity_release(e) != wanted_release:
                    continue
                if self.isIctvId(value) and self.entityMatchesIctvId(e, value):
                    candidates.append(e)
                elif self.normText(self.normalizeValue(e.get("label"))) == wanted_text:
                    candidates.append(e)

        return self._dedupe_raw_by_iri(candidates)

    def _current_replacements_without_release(self, id_or_label: str) -> List[Dict[str, Any]]:
        for candidates in self._exact_candidate_groups(str(id_or_label)):
            mapped = self._resolve_candidate_group_to_current(candidates)
            if mapped:
                return mapped

        res = self.resolveToLatest(id_or_label, {
            "replacements": True,
            "enrichLineage": False,
            "suggestions": False,
        })
        mapped = self._mapped_replacements_from_result(res)
        if mapped:
            return [m for m in mapped if not m.get("is_obsolete")]

        return []

    def _exact_candidate_groups(self, value: str) -> List[List[Dict[str, Any]]]:
        if self.isIctvId(value):
            return [self._seek_exact_id(value), self._seek_exact_id_from_release_file(value)]
        return [
            self._seek_exact_label(value, include_obsolete="false"),
            self._seek_exact_label(value, include_obsolete="true"),
            self._seek_exact_synonym(value),
        ]

    def _resolve_candidate_group_to_current(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        candidates = [self._full_entity(c) for c in self._dedupe_raw_by_iri(candidates)]
        if not candidates:
            return []

        current = [self.mapEntity(c) for c in candidates if not c.get("isObsolete")]
        if current:
            return sorted(current, key=lambda x: self.parseMsl(x.get("msl")), reverse=True)

        for candidate in self.sortCandidates(candidates):
            mapped = self.mapEntity(candidate)
            replacements = self.followReplacements(mapped, {"replacements": True, "enrichLineage": False})
            replacements = [r for r in replacements if not r.get("is_obsolete")]
            if replacements:
                return replacements
            direct = [r for r in self._resolve_iris(self._legacy_from_mapped(mapped, raw=candidate)["current_replacements"]) if not r["is_obsolete"]]
            if direct:
                return [self._mapped_from_legacy(r) for r in direct]
        return []

    def _seek_exact_id(self, value: str) -> List[Dict[str, Any]]:
        return [self._full_entity(e) for e in self.seekOntologyTaxonByClassId(value) if self.entityMatchesIctvId(e, value)]

    def _seek_exact_id_from_release_file(self, value: str) -> List[Dict[str, Any]]:
        return [e for e in self._load_release_entities() if self.entityMatchesIctvId(e, value)]

    def _seek_exact_label(self, value: str, include_obsolete: str) -> List[Dict[str, Any]]:
        wanted = self.normText(value)
        return [
            self._full_entity(e)
            for e in (self.seekOntologyTaxon("classes", {
                "search": value,
                "searchFields": "label",
                "exactMatch": "true",
                "includeObsoleteEntities": include_obsolete,
                "size": 100,
            }) or [])
            if self.normText(self.normalizeValue(e.get("label"))) == wanted
        ]

    def _seek_exact_synonym(self, value: str) -> List[Dict[str, Any]]:
        return [self._full_entity(e) for e in self.seekOntologyTaxonBySynonym(value)]

    def _mapped_replacements_from_result(self, res: Dict[str, Any]) -> List[Dict[str, Any]]:
        if res.get("status") == "current" and res.get("current"):
            return [res["current"]]
        if res.get("status") == "obsolete":
            if res.get("replacements"):
                return res["replacements"]
            if res.get("final"):
                return [res["final"]]
        return []

    def _resolve_iris(self, iris: List[str]) -> List[Dict[str, Any]]:
        resolved: List[Dict[str, Any]] = []
        for iri in iris:
            raw = self.retrieveTaxonByIRI(iri) or self._load_release_entities_by_iri().get(iri)
            if raw:
                resolved.append(self._map_entity(raw))
        return resolved

    def _full_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        iri = entity.get("iri")
        return self.retrieveTaxonByIRI(iri) or entity if iri else entity

    def _mapped_from_legacy(self, legacy: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "msl": legacy.get("msl"),
            "ictv_id": legacy.get("ictv_id"),
            "label": legacy.get("label"),
            "is_obsolete": legacy.get("is_obsolete", False),
            "obsolescence_reason": legacy.get("obsolescence_reason"),
            "direct_parent_iri": (legacy.get("taxonomic_parents") or [None])[0],
            "was_revision_of": legacy.get("replaces"),
            "had_revision": legacy.get("replaced_by"),
            "replaced_by": legacy.get("current_replacements"),
        }

    def _map_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        mapped = self.mapEntity(entity)
        return self._legacy_from_mapped(mapped, raw=entity)

    def _legacy_from_mapped(self, mapped: Dict[str, Any], raw: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raw = raw or {}
        direct_parent = mapped.get("direct_parent_iri") or self.normalizeValue(raw.get(SUBCLASS_OF))
        return {
            "msl": mapped.get("msl"),
            "ictv_id": mapped.get("ictv_id"),
            "label": mapped.get("label"),
            "is_obsolete": bool(mapped.get("is_obsolete")),
            "obsolescence_reason": mapped.get("obsolescence_reason"),
            "taxonomic_parents": self.toIriArray(direct_parent),
            "replaces": self.toIriArray(mapped.get("was_revision_of") or raw.get(WAS_REVISION_OF)),
            "replaced_by": self.toIriArray(mapped.get("had_revision") or raw.get(HAD_REVISION)),
            "current_replacements": self.toIriArray(mapped.get("replaced_by") or raw.get(REPLACED_BY)),
        }

    def _entity_release(self, entity: Dict[str, Any]) -> str:
        return str(entity.get(VERSION_INFO, "")).upper()

    def _dedupe_raw_by_iri(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        out = []
        for entity in entities:
            iri = entity.get("iri")
            if iri and iri in seen:
                continue
            if iri:
                seen.add(iri)
            out.append(entity)
        return out

    def _load_release_entities_by_iri(self) -> Dict[str, Dict[str, Any]]:
        self._load_release_entities()
        return self._release_entities_by_iri

    def _load_release_entities(self) -> List[Dict[str, Any]]:
        if self._release_entities is not None:
            return self._release_entities

        metadata = requests.get(LATEST_ONTOLOGY_METADATA, headers=self.headers, timeout=30).json()
        file_url = (metadata.get("config") or {}).get("fileLocation")
        if not file_url:
            raise RuntimeError("OLS metadata does not expose an ontology fileLocation")

        response = requests.get(file_url, headers=self.headers, timeout=120)
        response.raise_for_status()
        text = gzip.decompress(response.content).decode("utf-8")

        entities = []
        for match in re.finditer(r"(?:^|\n)<([^>]+)> a owl:Class ;\n(.*?)(?=\n\n<|\Z)", text, flags=re.S):
            iri, block = match.groups()
            entity = self._parse_turtle_class_block(iri, block)
            if entity:
                entities.append(entity)

        self._release_entities = entities
        self._release_entities_by_iri = {e["iri"]: e for e in entities if e.get("iri")}
        return entities

    def _parse_turtle_class_block(self, iri: str, block: str) -> Optional[Dict[str, Any]]:
        label = self._ttl_literal(block, "rdfs:label")
        ictv_id = self._ttl_literal(block, "dcterms:identifier")
        release = self._ttl_literal(block, "owl:versionInfo")
        if not (label and ictv_id and release):
            return None

        parent_iris = self._ttl_iris(block, "rdfs:subClassOf")
        was_revision_of = self._ttl_iris(block, "prov:wasRevisionOf")
        had_revision = self._ttl_iris(block, "prov:hadRevision")
        current_replacements = self._ttl_iris(block, "iao:0100001")
        reason = self._ttl_prefixed_iri(block, "iao:0000225")

        return {
            "iri": iri,
            "label": label,
            IDENTIFIER: ictv_id,
            VERSION_INFO: release,
            "isObsolete": "owl:deprecated true" in block,
            SUBCLASS_OF: parent_iris,
            "directParent": parent_iris[0] if parent_iris else None,
            WAS_REVISION_OF: was_revision_of,
            HAD_REVISION: had_revision,
            REPLACED_BY: current_replacements,
            OBSOLESCENCE_REASON: reason,
        }

    def _ttl_literal(self, block: str, predicate: str) -> Optional[str]:
        match = re.search(rf"{re.escape(predicate)}\s+\"((?:[^\"\\]|\\.)*)\"", block)
        if not match:
            return None
        return match.group(1).replace('\\"', '"')

    def _ttl_iris(self, block: str, predicate: str) -> List[str]:
        match = re.search(rf"{re.escape(predicate)}\s+(.+?)\s*;", block, flags=re.S)
        if not match:
            return []
        return re.findall(r"<([^>]+)>", match.group(1))

    def _ttl_prefixed_iri(self, block: str, predicate: str) -> Optional[str]:
        match = re.search(rf"{re.escape(predicate)}\s+([a-z]+):(\d+)", block)
        if not match:
            return None
        prefix, local = match.groups()
        if prefix == "iao":
            return f"http://purl.obolibrary.org/obo/IAO_{local}"
        return f"{prefix}:{local}"


ICTVtoNCBImapping = _helper.ICTVtoNCBImapping

__all__ = ["ICTVOLSClient", "ICTVtoNCBImapping"]
