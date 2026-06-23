'use strict';

// ─────────────────────────────────────────────────────────────────────────────
// AgriSage SDK — Node.js
// Version : 1.0.0
// Docs    : https://docs.agrisage.ma
// Support : api@agrisage.ma
// ─────────────────────────────────────────────────────────────────────────────

const https = require('https');
const http  = require('http');
const { URL } = require('url');

// ── Constantes ────────────────────────────────────────────────────────────────

const SDK_VERSION      = '1.0.0';
const DEFAULT_BASE_URL = 'https://api.agrisage.ma/v1';
const SANDBOX_BASE_URL = 'https://api-sandbox.agrisage.ma/v1';
const DEFAULT_TIMEOUT  = 30_000; // ms
const DEFAULT_RETRIES  = 2;
const RETRY_DELAY_MS   = 500;

// ── Erreurs personnalisées ────────────────────────────────────────────────────

class AgriSageError extends Error {
  constructor(message, code, statusCode, requestId, suggestion) {
    super(message);
    this.name        = 'AgriSageError';
    this.code        = code        || 'UNKNOWN_ERROR';
    this.statusCode  = statusCode  || null;
    this.requestId   = requestId   || null;
    this.suggestion  = suggestion  || null;
  }
}

class AuthenticationError extends AgriSageError {
  constructor(message, requestId) {
    super(message, 'UNAUTHORIZED', 401, requestId);
    this.name = 'AuthenticationError';
  }
}

class PlanLimitError extends AgriSageError {
  constructor(message, requestId, suggestion) {
    super(message, 'PLAN_LIMIT', 403, requestId, suggestion);
    this.name = 'PlanLimitError';
  }
}

class QuotaExceededError extends AgriSageError {
  constructor(message, requestId, resetAt) {
    super(message, 'QUOTA_EXCEEDED', 429, requestId);
    this.name   = 'QuotaExceededError';
    this.resetAt = resetAt || null;
  }
}

class NotFoundError extends AgriSageError {
  constructor(message, requestId, suggestion) {
    super(message, 'NOT_FOUND', 404, requestId, suggestion);
    this.name = 'NotFoundError';
  }
}

class ValidationError extends AgriSageError {
  constructor(message, requestId, suggestion) {
    super(message, 'INVALID_PARAM', 400, requestId, suggestion);
    this.name = 'ValidationError';
  }
}

class NetworkError extends AgriSageError {
  constructor(message, originalError) {
    super(message, 'NETWORK_ERROR');
    this.name          = 'NetworkError';
    this.originalError = originalError || null;
  }
}

// ── Utilitaires internes ──────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function buildQueryString(params) {
  if (!params || Object.keys(params).length === 0) return '';
  const parts = [];
  for (const [key, val] of Object.entries(params)) {
    if (val === undefined || val === null) continue;
    if (Array.isArray(val)) {
      val.forEach(v => parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(v)}`));
    } else {
      parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(val)}`);
    }
  }
  return parts.length > 0 ? '?' + parts.join('&') : '';
}

function parseErrorBody(body, statusCode) {
  try {
    const parsed = JSON.parse(body);
    const err    = parsed.error || {};
    return {
      message    : err.message    || `Erreur HTTP ${statusCode}`,
      code       : err.code       || 'UNKNOWN_ERROR',
      requestId  : err.request_id || null,
      suggestion : err.suggestion || null,
    };
  } catch {
    return {
      message   : `Erreur HTTP ${statusCode}`,
      code      : 'UNKNOWN_ERROR',
      requestId : null,
      suggestion: null,
    };
  }
}

function throwForStatus(statusCode, body, headers) {
  const { message, code, requestId, suggestion } = parseErrorBody(body, statusCode);
  switch (statusCode) {
    case 400: throw new ValidationError(message, requestId, suggestion);
    case 401: throw new AuthenticationError(message, requestId);
    case 403: throw new PlanLimitError(message, requestId, suggestion);
    case 404: throw new NotFoundError(message, requestId, suggestion);
    case 429: {
      const resetAt = headers['x-ratelimit-reset'] || null;
      throw new QuotaExceededError(message, requestId, resetAt);
    }
    default:  throw new AgriSageError(message, code, statusCode, requestId, suggestion);
  }
}

// ── Transport HTTP ────────────────────────────────────────────────────────────

function rawRequest(options, body, timeout) {
  return new Promise((resolve, reject) => {
    const lib = options.protocol === 'http:' ? http : https;
    const req = lib.request(options, (res) => {
      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => {
        resolve({ statusCode: res.statusCode, headers: res.headers, body: data });
      });
    });
    req.setTimeout(timeout, () => {
      req.destroy();
      reject(new NetworkError(`Délai dépassé (${timeout}ms)`, null));
    });
    req.on('error', (err) => {
      reject(new NetworkError(`Erreur réseau : ${err.message}`, err));
    });
    if (body) req.write(body);
    req.end();
  });
}

// ── Client principal ──────────────────────────────────────────────────────────

class AgriSageClient {
  /**
   * @param {object} config
   * @param {string}  config.apiKey        - Clé API (as_test_… ou as_live_…)
   * @param {string}  [config.baseUrl]     - URL de base (défaut : production)
   * @param {boolean} [config.sandbox]     - Utiliser l'environnement sandbox
   * @param {string}  [config.lang]        - Langue par défaut : 'fr' | 'ar'
   * @param {number}  [config.timeout]     - Timeout en ms (défaut : 30 000)
   * @param {number}  [config.maxRetries]  - Nombre de tentatives (défaut : 2)
   * @param {boolean} [config.debug]       - Logs de debug
   */
  constructor(config = {}) {
    if (!config.apiKey) {
      throw new AgriSageError(
        'apiKey est requis. Obtenez votre clé sur agrisage.ma/dashboard',
        'MISSING_API_KEY'
      );
    }

    this._apiKey     = config.apiKey;
    this._baseUrl    = config.baseUrl
      || (config.sandbox ? SANDBOX_BASE_URL : DEFAULT_BASE_URL);
    this._lang       = config.lang       || 'fr';
    this._timeout    = config.timeout    || DEFAULT_TIMEOUT;
    this._maxRetries = config.maxRetries ?? DEFAULT_RETRIES;
    this._debug      = config.debug      || false;

    // Sous-clients (namespacing style Stripe)
    this.conseil    = new ConseilResource(this);
    this.produits   = new ProduitsResource(this);
    this.traitement = new TraitementResource(this);
    this.carnet     = new CarnetResource(this);
    this.groupes    = new GroupesResource(this);
    this.alertes    = new AlertesResource(this);
    this.cultures   = new CulturesResource(this);

    this._log(`AgriSage SDK v${SDK_VERSION} initialisé — ${this._baseUrl}`);
  }

  _log(...args) {
    if (this._debug) console.log('[AgriSage]', ...args);
  }

  /**
   * Requête interne avec retry automatique sur 429 / 5xx.
   */
  async _request(method, path, { query = {}, body = null } = {}) {
    const qs      = buildQueryString({ lang: this._lang, ...query });
    const fullUrl = new URL(this._baseUrl + path + qs);
    const payload = body ? JSON.stringify(body) : null;

    const options = {
      hostname : fullUrl.hostname,
      port     : fullUrl.port || (fullUrl.protocol === 'https:' ? 443 : 80),
      path     : fullUrl.pathname + fullUrl.search,
      method   : method.toUpperCase(),
      protocol : fullUrl.protocol,
      headers  : {
        'Authorization' : `Bearer ${this._apiKey}`,
        'Content-Type'  : 'application/json',
        'Accept'        : 'application/json',
        'User-Agent'    : `agrisage-node/${SDK_VERSION}`,
        ...(payload ? { 'Content-Length': Buffer.byteLength(payload) } : {}),
      },
    };

    let attempt = 0;

    while (attempt <= this._maxRetries) {
      this._log(`${method.toUpperCase()} ${path} (tentative ${attempt + 1})`);

      try {
        const { statusCode, headers, body: resBody } = await rawRequest(
          options, payload, this._timeout
        );

        // Extraire les métadonnées de quota depuis les headers
        const rateLimit = {
          limit    : parseInt(headers['x-ratelimit-limit'])     || null,
          remaining: parseInt(headers['x-ratelimit-remaining']) || null,
          reset    : headers['x-ratelimit-reset']               || null,
        };
        this._log(`← ${statusCode} · quota restant: ${rateLimit.remaining}`);

        if (statusCode >= 200 && statusCode < 300) {
          // Réponse PDF : retourner le buffer brut
          if (headers['content-type']?.includes('application/pdf')) {
            return { data: Buffer.from(resBody), rateLimit, contentType: 'application/pdf' };
          }
          const data = resBody ? JSON.parse(resBody) : null;
          return { data, rateLimit };
        }

        // Retry sur 429 et 5xx
        const shouldRetry = (statusCode === 429 || statusCode >= 500) && attempt < this._maxRetries;
        if (shouldRetry) {
          const delay = RETRY_DELAY_MS * Math.pow(2, attempt);
          this._log(`Retry dans ${delay}ms...`);
          await sleep(delay);
          attempt++;
          continue;
        }

        throwForStatus(statusCode, resBody, headers);

      } catch (err) {
        if (err instanceof AgriSageError) throw err;
        // Erreur réseau : retry
        if (attempt < this._maxRetries) {
          const delay = RETRY_DELAY_MS * Math.pow(2, attempt);
          this._log(`Erreur réseau, retry dans ${delay}ms...`);
          await sleep(delay);
          attempt++;
          continue;
        }
        throw new NetworkError(err.message, err);
      }
    }
  }
}

// ── Ressource : Conseil ───────────────────────────────────────────────────────

class ConseilResource {
  constructor(client) { this._client = client; }

  /**
   * Génère un conseil phytosanitaire.
   *
   * @param {object}   params
   * @param {string}   params.culture            - Culture cible (ex: "tomate")
   * @param {string}   params.ravageur           - Organisme nuisible (ex: "botrytis")
   * @param {string}   params.stade              - Stade phénologique
   * @param {string}   [params.region]           - Code région marocaine
   * @param {number}   [params.darMax]           - DAR maximum acceptable (jours)
   * @param {boolean}  [params.globalgap]        - Filtrer sur conformité GlobalGAP v6
   * @param {boolean}  [params.exportUe]         - Appliquer LMR UE 396/2005 (plan Pro+)
   * @param {string[]} [params.historiqueFrac]   - Groupes FRAC déjà utilisés ce cycle
   * @param {string[]} [params.historiqueIrac]   - Groupes IRAC déjà utilisés ce cycle
   * @param {number}   [params.nbAlternatives]   - Nombre d'alternatives (0–5, défaut 2)
   * @param {string}   [params.lang]             - 'fr' | 'ar'
   * @returns {Promise<{data: Conseil, rateLimit: RateLimit}>}
   */
  async generer(params = {}) {
    _requireFields(params, ['culture', 'ravageur', 'stade'], 'conseil.generer');
    const body = {
      culture           : params.culture,
      ravageur          : params.ravageur,
      stade             : params.stade,
      region            : params.region,
      dar_max           : params.darMax,
      globalgap         : params.globalgap,
      export_ue         : params.exportUe,
      historique_frac   : params.historiqueFrac,
      historique_irac   : params.historiqueIrac,
      nb_alternatives   : params.nbAlternatives,
      lang              : params.lang || this._client._lang,
    };
    return this._client._request('POST', '/conseil', { body: _clean(body) });
  }
}

// ── Ressource : Produits ──────────────────────────────────────────────────────

class ProduitsResource {
  constructor(client) { this._client = client; }

  /**
   * Liste les produits ONSSA avec filtres.
   *
   * @param {object}  [params]
   * @param {string}  [params.culture]    - Filtre par culture homologuée
   * @param {string}  [params.usage]      - 'fongicide' | 'insecticide' | 'herbicide' | ...
   * @param {string}  [params.ma]         - Recherche par matière active
   * @param {string}  [params.statut]     - 'homologue' | 'retire' | 'tous'
   * @param {string}  [params.groupeFrac] - Filtre par groupe FRAC
   * @param {string}  [params.groupeIrac] - Filtre par groupe IRAC
   * @param {number}  [params.page]       - Numéro de page
   * @param {string}  [params.lang]
   * @returns {Promise<{data: {data: ProduitONSSA[], pagination: Pagination}, rateLimit: RateLimit}>}
   */
  async lister(params = {}) {
    return this._client._request('GET', '/produits', {
      query: _clean({
        culture     : params.culture,
        usage       : params.usage,
        ma          : params.ma,
        statut      : params.statut,
        groupe_frac : params.groupeFrac,
        groupe_irac : params.groupeIrac,
        page        : params.page,
        lang        : params.lang,
      }),
    });
  }

  /**
   * Détail d'un produit ONSSA par son identifiant.
   *
   * @param {string} id       - Identifiant du produit (ex: "prod_onssa_00412")
   * @param {string} [lang]
   * @returns {Promise<{data: ProduitONSSA, rateLimit: RateLimit}>}
   */
  async obtenir(id, lang) {
    if (!id) throw new ValidationError('id est requis pour produits.obtenir');
    return this._client._request('GET', `/produits/${encodeURIComponent(id)}`, {
      query: _clean({ lang }),
    });
  }
}

// ── Ressource : Traitement ────────────────────────────────────────────────────

class TraitementResource {
  constructor(client) { this._client = client; }

  /**
   * Enregistre un traitement dans le carnet (plan Pro+).
   *
   * @param {object}  params
   * @param {string}  params.parcelleId         - Identifiant parcelle
   * @param {string}  params.produitNom         - Nom commercial du produit
   * @param {object}  params.doseAppliquee      - { valeur: number, unite: string }
   * @param {string}  params.dateTraitement     - ISO 8601 (ex: "2025-03-15")
   * @param {string}  [params.conseilId]        - ID du conseil AgriSage associé
   * @param {string}  [params.culture]
   * @param {string}  [params.numeroAmm]        - Numéro AMM ONSSA
   * @param {number}  [params.surfaceTraitee]   - Surface en hectares
   * @param {string}  [params.dateRecoltePrevue]- Déclenche alerte DAR si dépassé
   * @param {string}  [params.operateur]        - Nom de l'opérateur
   * @param {string[]}[params.epiPortes]        - Équipements de protection portés
   * @param {object}  [params.conditionsMeteo]  - { temperatureC, ventKmh, hygrometriePct }
   * @param {string}  [params.notes]
   * @returns {Promise<{data: TraitementResponse, rateLimit: RateLimit}>}
   */
  async enregistrer(params = {}) {
    _requireFields(params, ['parcelleId', 'produitNom', 'doseAppliquee', 'dateTraitement'], 'traitement.enregistrer');
    const body = {
      conseil_id         : params.conseilId,
      parcelle_id        : params.parcelleId,
      culture            : params.culture,
      produit_nom        : params.produitNom,
      numero_amm         : params.numeroAmm,
      dose_appliquee     : params.doseAppliquee,
      surface_traitee    : params.surfaceTraitee,
      date_traitement    : params.dateTraitement,
      date_recolte_prevue: params.dateRecoltePrevue,
      operateur          : params.operateur,
      epi_portes         : params.epiPortes,
      conditions_meteo   : params.conditionsMeteo ? {
        temperature_c   : params.conditionsMeteo.temperatureC,
        vent_kmh        : params.conditionsMeteo.ventKmh,
        hygrometrie_pct : params.conditionsMeteo.hygrometriePct,
      } : undefined,
      notes              : params.notes,
    };
    return this._client._request('POST', '/traitement', { body: _clean(body) });
  }
}

// ── Ressource : Carnet ────────────────────────────────────────────────────────

class CarnetResource {
  constructor(client) { this._client = client; }

  /**
   * Consulte l'historique des traitements (plan Pro+).
   *
   * @param {object} [params]
   * @param {string} [params.parcelleId] - Filtre par parcelle
   * @param {string} [params.du]         - Date début ISO 8601
   * @param {string} [params.au]         - Date fin ISO 8601
   * @param {string} [params.format]     - 'json' (défaut) | 'pdf'
   * @param {number} [params.page]
   * @returns {Promise<{data: object|Buffer, rateLimit: RateLimit, contentType?: string}>}
   */
  async obtenir(params = {}) {
    return this._client._request('GET', '/carnet', {
      query: _clean({
        parcelle_id : params.parcelleId,
        du          : params.du,
        au          : params.au,
        format      : params.format,
        page        : params.page,
      }),
    });
  }

  /**
   * Raccourci — exporte le carnet au format PDF GlobalGAP.
   *
   * @param {object} [params]
   * @param {string} [params.parcelleId]
   * @param {string} [params.du]
   * @param {string} [params.au]
   * @returns {Promise<Buffer>} Buffer du PDF
   */
  async exporterPdf(params = {}) {
    const res = await this.obtenir({ ...params, format: 'pdf' });
    return res.data;
  }
}

// ── Ressource : Groupes ───────────────────────────────────────────────────────

class GroupesResource {
  constructor(client) { this._client = client; }

  /**
   * Liste les groupes de résistance IRAC / FRAC / HRAC.
   *
   * @param {object} params
   * @param {string} params.type           - 'irac' | 'frac' | 'hrac' (requis)
   * @param {string} [params.groupe]       - Numéro de groupe
   * @param {string} [params.ma]           - Recherche par matière active
   * @param {string} [params.risque]       - 'faible' | 'modéré' | 'élevé' | 'très élevé'
   * @param {string} [params.lang]
   * @returns {Promise<{data: {data: GroupeResistance[], total: number}, rateLimit: RateLimit}>}
   */
  async lister(params = {}) {
    _requireFields(params, ['type'], 'groupes.lister');
    return this._client._request('GET', '/groupes', {
      query: _clean({
        type   : params.type,
        groupe : params.groupe,
        ma     : params.ma,
        risque : params.risque,
        lang   : params.lang,
      }),
    });
  }

  /**
   * Raccourcis par type
   */
  async irac(params = {}) { return this.lister({ ...params, type: 'irac' }); }
  async frac(params = {}) { return this.lister({ ...params, type: 'frac' }); }
  async hrac(params = {}) { return this.lister({ ...params, type: 'hrac' }); }
}

// ── Ressource : Alertes ───────────────────────────────────────────────────────

class AlertesResource {
  constructor(client) { this._client = client; }

  /**
   * Consulte les alertes actives.
   *
   * @param {object}  [params]
   * @param {string}  [params.type]       - 'DAR_DEPASSE' | 'PRODUIT_RETIRE' | 'LMR_MODIFIEE' | ...
   * @param {string}  [params.urgence]    - 'critique' | 'élevée' | 'modérée' | 'information'
   * @param {boolean} [params.lue]        - Filtre par statut de lecture
   * @param {string}  [params.parcelleId]
   * @param {number}  [params.page]
   * @returns {Promise<{data: {data: Alerte[], non_lues: number, pagination: Pagination}, rateLimit: RateLimit}>}
   */
  async lister(params = {}) {
    return this._client._request('GET', '/alertes', {
      query: _clean({
        type        : params.type,
        urgence     : params.urgence,
        lue         : params.lue,
        parcelle_id : params.parcelleId,
        page        : params.page,
      }),
    });
  }

  /**
   * Marque une alerte comme lue.
   *
   * @param {string} id - Identifiant de l'alerte
   * @returns {Promise<{data: {alerte_id: string, lue: true}, rateLimit: RateLimit}>}
   */
  async marquerLue(id) {
    if (!id) throw new ValidationError('id est requis pour alertes.marquerLue');
    return this._client._request('PATCH', `/alertes/${encodeURIComponent(id)}/lue`);
  }

  /**
   * Raccourcis filtrés
   */
  async nonLues(params = {})   { return this.lister({ ...params, lue: false }); }
  async critiques(params = {}) { return this.lister({ ...params, urgence: 'critique' }); }
}

// ── Ressource : Cultures ──────────────────────────────────────────────────────

class CulturesResource {
  constructor(client) { this._client = client; }

  /**
   * Liste les cultures disponibles dans l'index ONSSA.
   *
   * @param {object} [params]
   * @param {string} [params.q]    - Recherche par nom (correspondance partielle)
   * @param {string} [params.lang]
   * @returns {Promise<{data: {data: Culture[], total: number}, rateLimit: RateLimit}>}
   */
  async lister(params = {}) {
    return this._client._request('GET', '/cultures', {
      query: _clean({ q: params.q, lang: params.lang }),
    });
  }

  /**
   * Recherche rapide par nom (alias de lister avec q)
   */
  async rechercher(terme, lang) {
    return this.lister({ q: terme, lang });
  }
}

// ── Helpers internes ──────────────────────────────────────────────────────────

function _requireFields(obj, fields, method) {
  for (const f of fields) {
    if (obj[f] === undefined || obj[f] === null || obj[f] === '') {
      throw new ValidationError(
        `Le champ '${f}' est requis pour ${method}`,
        null,
        `Consultez la doc : https://docs.agrisage.ma#${method.replace('.', '-')}`
      );
    }
  }
}

function _clean(obj) {
  const out = {};
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined && v !== null) out[k] = v;
  }
  return out;
}

// ── Exports ───────────────────────────────────────────────────────────────────

module.exports = {
  AgriSageClient,
  // Erreurs
  AgriSageError,
  AuthenticationError,
  PlanLimitError,
  QuotaExceededError,
  NotFoundError,
  ValidationError,
  NetworkError,
  // Constantes utiles
  STADES: Object.freeze({
    GERMINATION    : 'germination',
    LEVEE          : 'levee',
    VEGETATION     : 'vegetation',
    FLORAISON      : 'floraison',
    FRUCTIFICATION : 'fructification',
    RECOLTE        : 'recolte',
    POST_RECOLTE   : 'post-recolte',
  }),
  REGIONS: Object.freeze({
    SOUSS_MASSA         : 'souss-massa',
    GHARB_CHRARDA       : 'gharb-chrarda',
    MARRAKECH_SAFI      : 'marrakech-safi',
    FES_MEKNES          : 'fes-meknes',
    TANGER_TETOUAN      : 'tanger-tetouan',
    ORIENTAL            : 'oriental',
    RABAT_SALE_KENITRA  : 'rabat-sale-kenitra',
    BENI_MELLAL         : 'beni-mellal-khenifra',
    DRAA_TAFILALET      : 'draa-tafilalet',
    LAAYOUNE            : 'laayoune-sakia',
  }),
  USAGES: Object.freeze({
    FONGICIDE   : 'fongicide',
    INSECTICIDE : 'insecticide',
    HERBICIDE   : 'herbicide',
    NEMATICIDE  : 'nematicide',
    ACARICIDE   : 'acaricide',
    MOLLUSCICIDE: 'molluscicide',
  }),
  ALERTES_TYPES: Object.freeze({
    DAR_DEPASSE     : 'DAR_DEPASSE',
    PRODUIT_RETIRE  : 'PRODUIT_RETIRE',
    LMR_MODIFIEE    : 'LMR_MODIFIEE',
    ROTATION_REQUISE: 'ROTATION_REQUISE',
    ZNT_VIOLATION   : 'ZNT_VIOLATION',
  }),
};
