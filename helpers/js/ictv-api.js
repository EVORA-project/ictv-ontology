/* ============================================================================
   ICTV Ontology API JavaScript Helper
   ----------------------------------------------------------------------------
   Lightweight helper for resolving ICTV taxon names, identifiers, and NCBI
   Taxon IDs using the ICTV Ontology served via the OLS4 API.

   Implementation initially inspired by notebook script created by @jamesamcl:
   https://github.com/EVORA-project/ictv-ontology/blob/main/notebooks/ictv_ols.py

   Data © ICTV (CC BY 4.0) — https://ictv.global/
   Code © EVORA Project / Angatar (d3fk) — MIT License
   Source ontology via OLS4: https://www.ebi.ac.uk/ols4/ontologies/ictv
   ========================================================================== */

export class ICTVApi {
  constructor(
    base = 'https://www.ebi.ac.uk/ols4/api/v2/ontologies/ictv',
    sssomUrl = 'https://raw.githubusercontent.com/EVORA-project/virus-taxonomy-mappings/refs/heads/dev/mappings/ictv_ncbitaxon_exact.sssom.tsv'
  ) {
    this.base = base;
    this.sssomUrl = sssomUrl;
    this._ncbiMap = null;
    this._entityCache = new Map();
  }

  /* -------------------- tiny utils -------------------- */
  _toArray(x) { return x == null ? [] : Array.isArray(x) ? x : [x]; }
  _firstOrNull(x) { return Array.isArray(x) ? x[0] ?? null : x ?? null; }
  _toIriArray(x) {
    return this._toArray(x)
      .flatMap(v => String(v).split(','))
      .map(v => v.trim())
      .filter(Boolean);
  }
  _isUrlLike(v) { return typeof v === 'string' && /^https?:\/\//i.test(v); }
  _parseMslNum(msl) { const m = /MSL(\d+)/i.exec(msl || ''); return m ? parseInt(m[1], 10) : -1; }
  _isIctvId(s) { return /^ICTV\d{5,}$/i.test(String(s).trim()); }
  _isIctvIri(s) { return /^https?:\/\/ictv\.global\/id\/MSL\d+\/ICTV\d+/i.test(String(s).trim()); }
  _asIctvIriFromCurie(curie) {
    const m = /^ictv:([^/]+)\/([^/]+)$/i.exec(curie || '');
    return m ? `http://ictv.global/id/${m[1]}/${m[2]}` : null;
  }
  _buildUrl(base, params = {}) {
    const u = new URL(base);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') u.searchParams.set(k, v);
    });
    return u.toString();
  }
  async _fetchJSON(url) {
    const res = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!res.ok) throw new Error(`Fetch failed ${res.status} for ${url}`);
    return res.json();
  }

  /* -------------------- NCBI mapping (SSSOM) -------------------- */
  async _loadNcbiMap() {
    if (this._ncbiMap) return this._ncbiMap;
    const txt = await (await fetch(this.sssomUrl)).text();
    const rows = txt.split(/\r?\n/).filter(Boolean);
    rows.shift(); // header
    const forward = Object.create(null); // ictv:MSLx/ICTVyyyy -> [{ncbiCurie,label}]
    const reverse = Object.create(null); // ncbitaxon:#### -> [{ictv_curie,msl,ictv_id,label}]
    for (const line of rows) {
      const cols = line.split('\t');
      if (cols.length < 5) continue;
      const ictvCurie = cols[0];
      const ncbiCurie = cols[3].toLowerCase();
      const label = cols[4];

      (forward[ictvCurie] ||= []).push({ ncbiCurie, label });

      const m = /^ictv:([^/]+)\/([^/]+)$/i.exec(ictvCurie);
      const msl = m ? m[1] : null;
      const ictvId = m ? m[2] : null;
      (reverse[ncbiCurie] ||= []).push({ ictv_curie: ictvCurie, msl, ictv_id: ictvId, label });
    }
    this._ncbiMap = { forward, reverse };
    return this._ncbiMap;
  }

  async getNcbiForIctvCurie(ictvCurie) {
    const map = await this._loadNcbiMap();
    return map.forward[ictvCurie] || [];
  }

  async getIctvFromNcbi(ncbiId) {
    const map = await this._loadNcbiMap();
    let k = String(ncbiId).trim().toLowerCase();
    if (!k.startsWith('ncbitaxon:')) k = 'ncbitaxon:' + k;
    const hits = map.reverse[k] || [];
    const best = {};
    for (const h of hits) {
      const n = this._parseMslNum(h.msl);
      const prev = best[h.ictv_id];
      if (!prev || n > prev._n) best[h.ictv_id] = { ...h, _n: n };
    }
    return Object.values(best).map(({ _n, ...rest }) => rest);
  }

  /* -------------------- OLS helpers -------------------- */
  async _ols(endpoint, params) {
    return this._fetchJSON(this._buildUrl(`${this.base}/${endpoint}`, { size: 1000, ...params }));
  }

  async getEntityByIri(iri) {
    if (this._entityCache.has(iri)) return this._entityCache.get(iri);
    const enc = encodeURIComponent(encodeURIComponent(iri));
    const request = this._fetchJSON(`${this.base}/entities/${enc}`).catch(err => {
      this._entityCache.delete(iri);
      throw err;
    });
    this._entityCache.set(iri, request);
    return request;
  }

  async _dedupeByIri(entities) {
    const seen = new Set();
    const out = [];
    for (const e of entities || []) {
      const iri = e.iri || e['iri'] || null;
      const id  = e['http://purl.org/dc/terms/identifier'];
      const msl = e['http://www.w3.org/2002/07/owl#versionInfo'];
      const key = iri || (id ? `${id}|${msl || ''}` : null) || JSON.stringify(e);
      if (!seen.has(key)) { seen.add(key); out.push(e); }
    }
    return out;
  }

  async _getSuggestions(query) {
    const collect = (docs) => {
      const cleaned = this._normText(query);
      const out = [];
      const seen = new Set();
      for (const d of docs || []) {
        const v = this._firstOrNull(d.autosuggest ?? d.label);
        const s = typeof v === 'string' ? v.trim() : '';
        const key = this._normText(s);
        if (s && key !== cleaned && !seen.has(key)) {
          seen.add(key);
          out.push(s);
        }
      }
      return out.slice(0, 5);
    };

    try {
      const url = `https://www.ebi.ac.uk/ols4/api/suggest?ontology=ictv&q=${encodeURIComponent(query)}`;
      const res = await this._fetchJSON(url);
      const suggestions = collect(res?.response?.docs);
      if (suggestions.length) return suggestions;
    } catch { /* ignore */ }

    try {
      const url = `https://www.ebi.ac.uk/ols4/api/search?ontology=ictv&q=${encodeURIComponent(query)}&rows=10`;
      const res = await this._fetchJSON(url);
      return collect(res?.response?.docs);
    } catch { /* ignore */ }

    return [];
  }

  /* -------- conservative class/individual lookups -------- */
  _normText(v) {
    return String(v ?? '').trim().replace(/\s+/g, ' ').toLowerCase();
  }

  _entityTextValues(e) {
    const values = [];
    for (const v of this._toArray(e.label ?? e['http://www.w3.org/2000/01/rdf-schema#label'])) {
      if (typeof v === 'string') values.push(v);
    }
    for (const key of ['synonym', 'synonyms', 'http://www.geneontology.org/formats/oboInOwl#hasExactSynonym']) {
      for (const s of this._toArray(e[key])) {
        if (typeof s === 'string') values.push(s);
        else if (s && typeof s === 'object' && typeof s.value === 'string') values.push(s.value);
      }
    }
    return values;
  }

  _entityMatchesTextExactly(e, query) {
    const wanted = this._normText(query);
    return this._entityTextValues(e).some(v => this._normText(v) === wanted);
  }

  _entityMatchesIctvId(e, ictvId) {
    const wanted = String(ictvId ?? '').trim().toUpperCase();
    if (!wanted) return false;
    const rawValues = [
      e['http://purl.org/dc/terms/identifier'],
      e.shortForm,
      e.curie,
      e.ictv_id,
      e.iri
    ];
    return rawValues.some(v => {
      const text = String(v ?? '').trim().toUpperCase();
      return text === wanted || text.endsWith(`/${wanted}`);
    });
  }

  async _olsElementsOrEmpty(endpoint, params, filter = null) {
    try {
      const res = await this._ols(endpoint, params);
      const elements = res.elements || [];
      return filter ? elements.filter(filter) : elements;
    } catch {
      return [];
    }
  }

  async _findClassesByExactFields(label, includeObsoleteEntities) {
    const baseParams = {
      search: label,
      exactMatch: 'true',
      includeObsoleteEntities,
      size: 20
    };
    const filter = e => this._entityMatchesTextExactly(e, label);
    const [byLabel, bySynonyms] = await Promise.all([
      this._olsElementsOrEmpty('classes', { ...baseParams, searchFields: 'label' }, filter),
      this._olsElementsOrEmpty('classes', { ...baseParams, searchFields: 'synonyms' }, filter)
    ]);
    return [...byLabel, ...bySynonyms];
  }

  async _findClassesByLabelConservative(label) {
    const exactCurrent = await this._findClassesByExactFields(label, 'false');

    let all = [...exactCurrent];

    if (all.length === 0) {
      const exactAny = await this._findClassesByExactFields(label, 'true');
      all = [...exactAny];
    }

    if (all.length === 0) {
      all = await this._uniqueRelaxedClassSearch(label);
    }

    // Deduplicate
    const uniq = await this._dedupeByIri(all);

    return uniq;
  }

  async _uniqueRelaxedClassSearch(label) {
    const raw = String(label).trim();
    if (raw.split(/\s+/).length < 2) return [];
    const variants = [];
    const withoutVirus = raw.replace(/\s+virus$/i, '').trim();
    if (withoutVirus && withoutVirus !== raw) {
      variants.push(withoutVirus.toLowerCase(), withoutVirus);
    } else {
      variants.push(raw.toLowerCase());
    }
    for (const search of Array.from(new Set(variants))) {
      try {
        const res = await this._ols('classes', {
          search,
          exactMatch: 'false',
          includeObsoleteEntities: 'false',
          size: 2
        });
        if (Number(res.totalElements || 0) === 1) return res.elements || [];
      } catch { /* ignore fallback query failures */ }
    }
    return [];
  }

  async _getClassesByIdentifier(ictvId) {
    const filter = e => this._entityMatchesIctvId(e, ictvId);
    const baseParams = {
      search: ictvId,
      searchFields: 'shortForm',
      exactMatch: 'true',
      size: 100
    };
    const [current, all] = await Promise.all([
      this._olsElementsOrEmpty('classes', {
        ...baseParams,
        includeObsoleteEntities: 'false'
      }, filter),
      this._olsElementsOrEmpty('classes', {
        ...baseParams,
        includeObsoleteEntities: 'true'
      }, filter)
    ]);
    const obsolete = all.filter(e => e.isObsolete === true);
    return this._dedupeByIri([...current, ...obsolete]);
  }

  async _findIndividualsAndResolveParents(labelOrSynonym) {
    const baseParams = {
      search: labelOrSynonym,
      exactMatch: 'true',
      includeObsoleteEntities: 'false',
      size: 20
    };
    const [byLabel, bySynonyms] = await Promise.all([
      this._olsElementsOrEmpty('individuals', { ...baseParams, searchFields: 'label' }),
      this._olsElementsOrEmpty('individuals', { ...baseParams, searchFields: 'synonyms' })
    ]);
    const allInds = [...byLabel, ...bySynonyms];

    const parentIris = Array.from(new Set(
      allInds.map(ind => this._firstOrNull(ind.directParent)).filter(Boolean)
    ));
    if (parentIris.length !== 1) return [];

    try {
      const parent = await this.getEntityByIri(parentIris[0]);
      return parent && parent['http://purl.org/dc/terms/identifier'] ? [parent] : [];
    } catch {
      return [];
    }
  }

  /* -------------------- mapping to normalized object -------------------- */
  _mapEntity(e) {
    const label = this._firstOrNull(e.label ?? e['http://www.w3.org/2000/01/rdf-schema#label']);

    // synonyms
    const syns = [];
    for (const key of ['synonym','http://www.geneontology.org/formats/oboInOwl#hasExactSynonym']) {
      for (const s of this._toArray(e[key])) {
        if (s && typeof s === 'object') {
          if ('value' in s) syns.push(s.value);
          else syns.push(this._firstOrNull(s));
        } else if (typeof s === 'string') {
          syns.push(s);
        }
      }
    }

    // rank
    const rankIri =
      e['http://purl.obolibrary.org/obo/TAXRANK_1000000'] ||
      (e.rank && e.rank.iri) || null;
    let rankLabel = (e.rank && e.rank.label) || null;
    if (rankIri && e.linkedEntities?.[rankIri]?.label) {
      rankLabel = this._firstOrNull(e.linkedEntities[rankIri].label);
    }

    // obsolescence reason (IAO terms → friendly text)
    const reasonIri = e['http://purl.obolibrary.org/obo/IAO_0000225'] || e['oboInOwl:hasObsolescenceReason'] || null;
    let reasonText = null;
    if (reasonIri === 'http://purl.obolibrary.org/obo/IAO_0000229') reasonText = 'SPLIT';
    else if (reasonIri === 'http://purl.obolibrary.org/obo/IAO_0000227') reasonText = 'MERGED';

    const msl = e['http://www.w3.org/2002/07/owl#versionInfo'] || e.msl || null;
    const ictv_id = e['http://purl.org/dc/terms/identifier'] || e.ictv_id || e.curie || null;
    const directParentIri = this._firstOrNull(e.directParent || e.direct_parent) || null;
    const ancestorIris = e.ancestors || e.hierarchicalAncestor || [];
    const linkedEntities = e.linkedEntities || {};
    const linkedLabelFor = iri => this._firstOrNull(linkedEntities?.[iri]?.label) || null;
    const linkedLineage = this._toArray(ancestorIris).map(linkedLabelFor).filter(Boolean);

    return {
      // identity
      msl,
      ictv_id,
      ictv_curie: msl && ictv_id ? `ictv:${msl}/${ictv_id}` : null,
      iri: e.iri || null,

      // names
      label,
      synonyms: Array.from(new Set(syns)),

      // status
      is_obsolete: e.isObsolete ?? e.is_obsolete ?? false,
      obsolescence_reason: reasonText,
      reason_iri: reasonIri || null,

      // parents/lineage
      direct_parent_iri: directParentIri,
      direct_parent_label: directParentIri ? linkedLabelFor(directParentIri) : null,
      ancestors_iris: ancestorIris,
      lineage: linkedLineage,

      // rank
      rank_label: rankLabel,
      rank_iri: rankIri,

      // revision links
      replaced_by:      e['http://purl.obolibrary.org/obo/IAO_0100001'] || e.replaced_by || null,
      was_revision_of:  e['http://www.w3.org/ns/prov#wasRevisionOf']       || e.was_revision_of || null,
      had_revision:     e['http://www.w3.org/ns/prov#hadRevision']          || e.had_revision    || null,

      // external xrefs → friendly URLs where possible
      narrow_match: this._toArray(e['http://www.w3.org/2004/02/skos/core#narrowMatch']).map(x => {
        const v = typeof x === 'string' ? x : (x?.value || String(x));
        let url = null;
        if (/^genbank:/i.test(v)) url = `https://www.ncbi.nlm.nih.gov/nuccore/${v.split(':')[1]}`;
        else if (/^refseq:/i.test(v)) url = `https://www.ncbi.nlm.nih.gov/nuccore/${v.split(':')[1]}`;
        else if (this._isUrlLike(v)) url = v;
        return { value: v, url };
      }),
    };
  }

  async _enrichParentAndLineage(mapped) {
    // direct parent label
    if (mapped.direct_parent_iri) {
      try {
        const p = await this.getEntityByIri(mapped.direct_parent_iri);
        mapped.direct_parent_label = this._firstOrNull(
          p?.label ?? p?.['http://www.w3.org/2000/01/rdf-schema#label']
        );
      } catch { /* ignore */ }
    }

    // ordered lineage reconstructed from parent chain
    const lineageLabels = [];
    const lineageIris = [];
    const seen = new Set();
    let currentIri = mapped.direct_parent_iri || null;

    while (currentIri && !seen.has(currentIri)) {
      seen.add(currentIri);

      try {
        const parentRaw = await this.getEntityByIri(currentIri);
        if (!parentRaw) break;

        const parentLabel = this._firstOrNull(
          parentRaw?.label ?? parentRaw?.['http://www.w3.org/2000/01/rdf-schema#label']
        );
        if (parentLabel) {
          lineageLabels.push(parentLabel);
          lineageIris.push(currentIri);
        }

        currentIri = this._firstOrNull(
          parentRaw?.directParent ?? parentRaw?.direct_parent
        ) || null;
      } catch {
        break;
      }
    }

  mapped.lineage = lineageLabels.reverse();
  mapped.ancestors_iris = lineageIris.reverse();
  return mapped;
}

  /* -------------------- entity selection -------------------- */
  async _findBestEntityForInput(input) {
    const trimmed = String(input).trim();
    let suggestions = [];
    let base = null;

    // 1) direct IRI
    if (this._isIctvIri(trimmed)) {
      base = await this.getEntityByIri(trimmed);
      return { base, suggestions };
    }

    // 2) ICTV ID (e.g., ICTV19990862)
    if (this._isIctvId(trimmed)) {
      const cs = await this._getClassesByIdentifier(trimmed);
      if (cs.length) {
        base = cs.sort(
          (a, b) =>
            this._parseMslNum(b['http://www.w3.org/2002/07/owl#versionInfo']) -
            this._parseMslNum(a['http://www.w3.org/2002/07/owl#versionInfo'])
        )[0];
        return { base, suggestions };
      }
    }

    // 3) NCBI taxid or ncbitaxon:####
    if (/^\d+$/.test(trimmed) || /^ncbitaxon:\d+$/i.test(trimmed)) {
      const hits = await this.getIctvFromNcbi(trimmed);
      if (hits.length) {
        const best = hits.reduce((acc, h) => {
          const n = this._parseMslNum(h.msl);
          return !acc || n > acc.n ? { h, n } : acc;
        }, null).h;
        const iri = this._asIctvIriFromCurie(best.ictv_curie);
        if (iri) {
          base = await this.getEntityByIri(iri);
          return { base, suggestions };
        }
      }
    }
     
    // 4) individuals -> parent class
    const parents = await this._findIndividualsAndResolveParents(trimmed);
    if (parents.length) {
      base = parents.sort(
        (a, b) =>
          this._parseMslNum(b['http://www.w3.org/2002/07/owl#versionInfo']) -
          this._parseMslNum(a['http://www.w3.org/2002/07/owl#versionInfo'])
      )[0];
      return { base, suggestions };
    }

    // 5) label/synonym classes
    const classes = await this._findClassesByLabelConservative(trimmed);
    if (classes.length) {
      base = classes.sort(
        (a, b) =>
          this._parseMslNum(b['http://www.w3.org/2002/07/owl#versionInfo']) -
          this._parseMslNum(a['http://www.w3.org/2002/07/owl#versionInfo'])
      )[0];
      return { base, suggestions };
    }

    // 6) nothing → suggest terms
    suggestions = await this._getSuggestions(trimmed);
    return { base: null, suggestions };
  }

  async _followReplacements(entity) {
    const queue = this._toIriArray(entity.replaced_by);
    const seen = new Set();
    const results = [];

    while (queue.length) {
      const iri = queue.shift();
      if (!iri || seen.has(iri)) continue;
      seen.add(iri);

      const ent = await this.getEntityByIri(iri);
      if (!ent) continue;

      let mapped = this._mapEntity(ent);
      mapped = await this._enrichParentAndLineage(mapped);

      if (mapped.is_obsolete && mapped.replaced_by) {
        queue.push(...this._toIriArray(mapped.replaced_by));
      } else {
        results.push(mapped);
      }
    }

    return results.sort((a, b) => this._parseMslNum(b.msl) - this._parseMslNum(a.msl));
  }

  /* -------------------- public API -------------------- */
  async resolveToLatest(inputRaw) {
    const input = String(inputRaw).trim();
    const { base, suggestions } = await this._findBestEntityForInput(input);

    if (!base) {
      const extra = suggestions?.length ? suggestions : await this._getSuggestions(input);
      return { status: 'not-found', input, suggestions: extra };
    }

    // If we somehow got an individual, move to parent class
    let entity = base;
    if (!entity['http://purl.org/dc/terms/identifier']) {
      const p = this._firstOrNull(entity.directParent);
      if (p) entity = await this.getEntityByIri(p);
    }

    // Map & enrich
    let mapped = this._mapEntity(entity);
    mapped = await this._enrichParentAndLineage(mapped);

    if (!mapped.is_obsolete) {
      const ncbi = await this.getNcbiForIctvCurie(mapped.ictv_curie);
      return { status: 'current', input, current: mapped, ncbi };
    }

    // obsolete → try replacements chain
    const replacements = await this._followReplacements(mapped);
    if (replacements.length > 0) {
      return {
        status: 'obsolete',
        input,
        obsolete: mapped,
        reason: mapped.obsolescence_reason || null,
        replacements,
        final: replacements[0]
      };
    }

    // still obsolete, no replacements
    return {
      status: 'obsolete',
      input,
      obsolete: mapped,
      reason: mapped.obsolescence_reason || null,
      replacements: []
    };
  }

  async getHistory(inputRaw) {
    const input = String(inputRaw).trim();
    const { base, suggestions } = await this._findBestEntityForInput(input);

    if (!base) {
      const extra = suggestions?.length ? suggestions : await this._getSuggestions(input);
      return { status: 'not-found', input, suggestions: extra };
    }

    // If individual → go to parent class
    let entity = base;
    if (!entity['http://purl.org/dc/terms/identifier']) {
      const p = this._firstOrNull(entity.directParent);
      if (p) entity = await this.getEntityByIri(p);
    }

    const seen = new Set();
    const history = [];

    const walk = async (ent) => {
      let m = this._mapEntity(ent);
      if (!m.msl || !m.ictv_id) return;
      const seenKey = m.iri || `${m.msl}|${m.ictv_id}`;
      if (seen.has(seenKey)) return;
      seen.add(seenKey);
      m = await this._enrichParentAndLineage(m);
      history.push(m);

      for (const key of ['was_revision_of', 'had_revision']) {
        for (const iri of this._toIriArray(m[key])) {
          const nxt = await this.getEntityByIri(iri);
          if (nxt) await walk(nxt);
        }
      }
    };

    await walk(entity);
    history.sort((a, b) => this._parseMslNum(b.msl) - this._parseMslNum(a.msl));
    return { status: 'ok', input, history };
  }
}
