'use strict';

/**
 * AgriSage — Moteur de conseil phytosanitaire
 *
 * Croise en une seule passe :
 *   1. Index ONSSA  → produits homologués pour culture + ravageur
 *   2. Filtre DAR   → produits dont le DAR ≤ dar_max demandé
 *   3. Anti-résistance IRAC/FRAC → exclut les groupes déjà utilisés
 *   4. Faune utile  → alerte si risque abeilles élevé en floraison
 *   5. GlobalGAP    → filtre produits non conformes si demandé
 *   6. Sélection    → meilleur produit + alternatives
 */

const { getDb }          = require('../db/database');
const { generateConseilId, normalizeCulture } = require('../utils/parseDar');

// ── Données IRAC/FRAC/HRAC (à enrichir progressivement) ──────────────────
// Mapping matière active → groupe de résistance
// Source : classifications officielles IRAC 2024 / FRAC 2024 / HRAC 2024
const FRAC_GROUPS = {
  'azoxystrobine':         { groupe: '11', risque: 'élevé',   mecanisme: 'Inhibiteurs de la succinate déshydrogénase' },
  'cyprodinil':            { groupe: '9',  risque: 'modéré',  mecanisme: 'Inhibiteurs de la biosynthèse des acides aminés' },
  'fludioxonil':           { groupe: '12', risque: 'faible',  mecanisme: 'Inhibiteurs de la transduction du signal' },
  'difénoconazole':        { groupe: '3',  risque: 'modéré',  mecanisme: 'Inhibiteurs de la déméthylation (DMI)' },
  'tebuconazole':          { groupe: '3',  risque: 'modéré',  mecanisme: 'Inhibiteurs de la déméthylation (DMI)' },
  'penconazole':           { groupe: '3',  risque: 'modéré',  mecanisme: 'Inhibiteurs de la déméthylation (DMI)' },
  'fluopyram':             { groupe: '7',  risque: 'modéré',  mecanisme: 'Inhibiteurs de la succinate déshydrogénase' },
  'boscalid':              { groupe: '7',  risque: 'modéré',  mecanisme: 'Inhibiteurs de la succinate déshydrogénase' },
  'pyrimethanil':          { groupe: '9',  risque: 'modéré',  mecanisme: 'Inhibiteurs de la biosynthèse des acides aminés' },
  'iprodione':             { groupe: '2',  risque: 'faible',  mecanisme: 'Inhibiteurs de la transduction du signal' },
  'mancozèbe':             { groupe: 'M3', risque: 'faible',  mecanisme: 'Contact multi-site' },
  'chlorothalonil':        { groupe: 'M5', risque: 'faible',  mecanisme: 'Contact multi-site' },
  'diméthomorphe':         { groupe: '40', risque: 'modéré',  mecanisme: 'Inhibiteurs de la synthèse des parois cellulaires' },
  'cymoxanil':             { groupe: '27', risque: 'modéré',  mecanisme: 'Inhibiteurs des acides nucléiques' },
  'métalaxyl':             { groupe: '4',  risque: 'très élevé', mecanisme: 'Inhibiteurs de la polymérase ARN' },
  'spiroxamine':           { groupe: '5',  risque: 'modéré',  mecanisme: 'Inhibiteurs de la biosynthèse des stérols' },
  'trifloxystrobine':      { groupe: '11', risque: 'élevé',   mecanisme: 'Inhibiteurs de la succinate déshydrogénase' },
  'cyflufénamide':         { groupe: 'U6', risque: 'faible',  mecanisme: 'Inhibiteurs des cétol-réductases' },
};

const IRAC_GROUPS = {
  'abamectine':            { groupe: '6',   risque: 'modéré',  mecanisme: 'Modulateurs des canaux chlorure glutamate' },
  'lambda cyhalothrine':   { groupe: '3A',  risque: 'élevé',   mecanisme: 'Modulateurs des canaux sodium voltage-dépendants' },
  'chlorantraniliprole':   { groupe: '28',  risque: 'faible',  mecanisme: 'Modulateurs des récepteurs ryanodine' },
  'spinosad':              { groupe: '5',   risque: 'faible',  mecanisme: 'Modulateurs des récepteurs nicotiniques acétylcholine' },
  'imidaclopride':         { groupe: '4A',  risque: 'élevé',   mecanisme: 'Agonistes des récepteurs nicotiniques acétylcholine' },
  'thiamétoxame':          { groupe: '4A',  risque: 'élevé',   mecanisme: 'Agonistes des récepteurs nicotiniques acétylcholine' },
  'acetamipride':          { groupe: '4A',  risque: 'élevé',   mecanisme: 'Agonistes des récepteurs nicotiniques acétylcholine' },
  'pyriproxyfène':         { groupe: '7C',  risque: 'faible',  mecanisme: 'Mimétiques de l\'hormone juvénile' },
  'spirotétramat':         { groupe: '23',  risque: 'faible',  mecanisme: 'Inhibiteurs de l\'acétyl-CoA carboxylase' },
  'bifénazate':            { groupe: 'UN',  risque: 'faible',  mecanisme: 'Inhibiteurs de la respiration mitochondriale' },
  'cyflumétofen':          { groupe: '25A', risque: 'faible',  mecanisme: 'Inhibiteurs de la succinate déshydrogénase' },
};

// Toxicité faune utile par matière active
// Source : PPDB (Pesticide Properties DataBase, Univ. Hertfordshire)
const TOXICITE_ABEILLES = {
  // Très dangereux
  'lambda cyhalothrine':   'élevé',
  'imidaclopride':         'élevé',
  'thiamétoxame':          'élevé',
  'clothianidine':         'élevé',
  'deltamethrine':         'élevé',
  'alpha-cyperméthrine':   'élevé',
  'cyperméthrine':         'élevé',
  // Dangereux
  'acetamipride':          'modéré',
  'spinosad':              'modéré',
  'spirotétramat':         'modéré',
  'abamectine':            'modéré',
  // Peu dangereux
  'azoxystrobine':         'faible',
  'cyprodinil':            'faible',
  'fludioxonil':           'faible',
  'difénoconazole':        'faible',
  'mancozèbe':             'faible',
  'chloranthraniliprole':  'très faible',
  'chlorantraniliprole':   'très faible',
  'pyriproxyfène':         'faible',
  'cyflufénamide':         'faible',
  'bifénazate':            'faible',
};

const TOXICITE_AUXILIAIRES = {
  'lambda cyhalothrine':   'élevé',
  'imidaclopride':         'élevé',
  'thiamétoxame':          'élevé',
  'abamectine':            'modéré',
  'spinosad':              'faible',
  'azoxystrobine':         'faible',
  'cyprodinil':            'faible',
  'chlorantraniliprole':   'faible',
  'pyriproxyfène':         'faible',
};

// Recommandations de rotation FRAC
const ROTATION_RECOMMANDATIONS = {
  '3':  'Alterner avec FRAC 7, 9 ou 11. Max 2 applications/saison.',
  '7':  'Alterner avec FRAC 3 ou 11. Max 2 applications/saison.',
  '9':  'Alterner avec FRAC 3 ou 12. Max 2 applications/saison.',
  '11': 'Alterner avec FRAC 3 ou 7. Max 1 application consécutive.',
  '4':  'Risque TRÈS ÉLEVÉ. Max 1 application/saison. Ne jamais utiliser seul.',
  'M3': 'Contact multi-site. Rotation libre mais préférer des produits spécifiques.',
};

// ── Fonctions utilitaires ────────────────────────────────────────────────

function getMaBase(maComplet) {
  if (!maComplet) return '';
  return maComplet
    .replace(/\s*[\(\[]\d[^\)\]]*[\)\]]/g, '')
    .replace(/\s*-\s*\d.*$/g, '')
    .trim()
    .toLowerCase();
}

function getGroupeFrac(maComplet) {
  const base = getMaBase(maComplet);
  for (const [ma, info] of Object.entries(FRAC_GROUPS)) {
    if (base.includes(ma.toLowerCase())) return info;
  }
  return null;
}

function getGroupeIrac(maComplet) {
  const base = getMaBase(maComplet);
  for (const [ma, info] of Object.entries(IRAC_GROUPS)) {
    if (base.includes(ma.toLowerCase())) return info;
  }
  return null;
}

function getRisqueAbeilles(maComplet) {
  const base = getMaBase(maComplet);
  for (const [ma, risque] of Object.entries(TOXICITE_ABEILLES)) {
    if (base.includes(ma.toLowerCase())) return risque;
  }
  return 'faible'; // défaut conservateur
}

function getRisqueAuxiliaires(maComplet) {
  const base = getMaBase(maComplet);
  for (const [ma, risque] of Object.entries(TOXICITE_AUXILIAIRES)) {
    if (base.includes(ma.toLowerCase())) return risque;
  }
  return 'faible';
}

function isGroupeDejaUtilise(maComplet, historiqueFrac, historiqueIrac) {
  const fracInfo = getGroupeFrac(maComplet);
  const iracInfo = getGroupeIrac(maComplet);

  if (fracInfo && historiqueFrac && historiqueFrac.includes(fracInfo.groupe)) {
    return { utilise: true, type: 'FRAC', groupe: fracInfo.groupe };
  }
  if (iracInfo && historiqueIrac && historiqueIrac.includes(iracInfo.groupe)) {
    return { utilise: true, type: 'IRAC', groupe: iracInfo.groupe };
  }
  return { utilise: false };
}

// Génère les alertes pour un produit
function genererAlertes(produit, usage, params) {
  const alertes = [];
  const stade   = params.stade || '';
  const ma      = produit.matiere_active || '';
  const risqueA = getRisqueAbeilles(ma);

  // Alerte floraison + abeilles
  if (stade === 'floraison') {
    if (risqueA === 'élevé') {
      alertes.push('⚠️ Stade floraison : ce produit est DANGEREUX pour les abeilles. Application strictement interdite pendant la floraison et la présence de butineuses.');
    } else if (risqueA === 'modéré') {
      alertes.push('🌿 Stade floraison : risque modéré pour les pollinisateurs. Appliquer impérativement après 19h ou avant 6h du matin.');
    } else {
      alertes.push('Stade floraison détecté : appliquer de préférence après 19h pour limiter l\'exposition des pollinisateurs.');
    }
  }

  // Alerte rotation anti-résistance
  const dejaUtilise = isGroupeDejaUtilise(ma, params.historique_frac, params.historique_irac);
  if (dejaUtilise.utilise) {
    alertes.push(`⚠️ Résistance : groupe ${dejaUtilise.type} ${dejaUtilise.groupe} déjà utilisé ce cycle. Ce produit est déconseillé — choisir une alternative.`);
  }

  // Alerte DAR proche récolte
  if (usage.dar_jours && params.dar_max && usage.dar_jours === params.dar_max) {
    alertes.push(`DAR limite atteint (${usage.dar_jours} jours). Respecter strictement la date de récolte.`);
  }

  // Alerte toxicologie
  const tox = produit.tableau_toxicologique;
  if (tox === 'Ia' || tox === 'Ib') {
    alertes.push(`⚠️ Toxicité : classe ${tox} (extrêmement/très dangereux). EPI complets obligatoires. Délai de réentrée à respecter.`);
  }

  return alertes;
}

// Formater dose en objet
function parseDoseObj(doseStr) {
  if (!doseStr) return { valeur: null, unite: null, raw: '' };
  const match = doseStr.match(/^([\d,\.]+)\s*(.+)$/);
  if (!match) return { valeur: null, unite: null, raw: doseStr };
  return {
    valeur: parseFloat(match[1].replace(',', '.')),
    unite:  match[2].trim(),
    raw:    doseStr,
  };
}

// ── MOTEUR PRINCIPAL ─────────────────────────────────────────────────────

/**
 * genererConseil — Moteur de décision AgriSage
 *
 * @param {object} params
 * @param {string}   params.culture           — Culture cible
 * @param {string}   params.ravageur          — Organisme nuisible
 * @param {string}   params.stade             — Stade phénologique
 * @param {number}   [params.dar_max]         — DAR maximum en jours
 * @param {boolean}  [params.globalgap]       — Filtrer GlobalGAP
 * @param {boolean}  [params.export_ue]       — Appliquer LMR UE
 * @param {string[]} [params.historique_frac] — Groupes FRAC déjà utilisés
 * @param {string[]} [params.historique_irac] — Groupes IRAC déjà utilisés
 * @param {number}   [params.nb_alternatives] — Nombre d'alternatives (défaut 2)
 * @param {string}   [params.lang]            — 'fr' | 'ar'
 * @returns {object} Conseil complet
 */
function genererConseil(params) {
  const db = getDb();
  const {
    culture,
    ravageur,
    stade,
    dar_max,
    globalgap    = false,
    historique_frac = [],
    historique_irac = [],
    nb_alternatives = 2,
  } = params;

  // ── 1. Construire la requête ONSSA ─────────────────────────────────────
  // Recherche dans usage_desc (contient "Culture / Ravageur")
  // et dans culture (nom seul)
  const cultureLower   = normalizeCulture(culture);
  const ravageurLower  = ravageur
    ? normalizeCulture(ravageur)
    : null;

  // Déterminer le type de produit attendu selon le ravageur
  // (heuristique basée sur la description de l'usage)
  let typeFilter = null;
  if (ravageurLower) {
    const maladiesMots = ['mildiou','oidium','oïdium','botrytis','alternariose',
      'fusariose','cladosporiose','septoriose','sclerotinia','rouille',
      'anthracnose','fonte','bactériose','virucide'];
    const insectesMots = ['mouche','puceron','acarien','thrips','tuta','mineuse',
      'cochenille','aleurode','leafminer','chenille','noctuelles'];
    const herbesMots   = ['adventice','mauvaise','graminée','dicotylédone'];

    if (maladiesMots.some(m => ravageurLower.includes(m)))
      typeFilter = 'fongicide';
    else if (insectesMots.some(m => ravageurLower.includes(m)))
      typeFilter = ['insecticide','insecticide-acaricide','acaricide'];
    else if (herbesMots.some(m => ravageurLower.includes(m)))
      typeFilter = 'herbicide';
  }

  // ── 2. Requête SQLite ──────────────────────────────────────────────────
  let sql = `
    SELECT
      p.id,
      p.nom_commercial,
      p.numero_homologation,
      p.detenteur,
      p.categorie,
      p.type_produit,
      p.formulation,
      p.matiere_active,
      p.teneur,
      p.valable_jusquau,
      p.tableau_toxicologique,
      p.statut,
      u.id         AS usage_id,
      u.culture    AS usage_culture,
      u.usage_desc,
      u.dose,
      u.dar_raw,
      u.dar_jours,
      u.nb_applications
    FROM produits p
    JOIN usages u ON p.id = u.produit_id
    WHERE 1=1
  `;
  const sqlParams = [];

  // Filtre culture (insensible à la casse)
  sql += ` AND LOWER(u.culture) LIKE ?`;
  sqlParams.push(`%${cultureLower}%`);

  // Filtre ravageur dans usage_desc
  if (ravageurLower) {
    sql += ` AND LOWER(u.usage_desc) LIKE ?`;
    sqlParams.push(`%${ravageurLower}%`);
  }

  // Filtre DAR
  if (dar_max != null && !isNaN(dar_max)) {
    sql += ` AND (u.dar_jours IS NULL OR u.dar_jours <= ?)`;
    sqlParams.push(parseInt(dar_max, 10));
  }

  // Filtre type produit
  if (typeFilter) {
    if (Array.isArray(typeFilter)) {
      sql += ` AND p.type_produit IN (${typeFilter.map(() => '?').join(',')})`;
      sqlParams.push(...typeFilter);
    } else {
      sql += ` AND p.type_produit = ?`;
      sqlParams.push(typeFilter);
    }
  }

  sql += ` ORDER BY u.dar_jours ASC NULLS LAST, p.nom_commercial ASC`;
  sql += ` LIMIT 50`;

  const rows = db.prepare(sql).all(...sqlParams);

  if (!rows || rows.length === 0) {
    // Tentative plus souple : sans ravageur
    return genererConseilSansRavageur(params);
  }

  // ── 3. Scoring et sélection ────────────────────────────────────────────
  // Score chaque produit selon les critères de qualité
  const scored = rows.map(row => {
    let score = 100;

    const ma          = row.matiere_active || '';
    const fracInfo    = getGroupeFrac(ma);
    const iracInfo    = getGroupeIrac(ma);
    const risqueA     = getRisqueAbeilles(ma);
    const dejaUtilise = isGroupeDejaUtilise(ma, historique_frac, historique_irac);

    // Pénalités
    if (dejaUtilise.utilise) score -= 60; // forte pénalité anti-résistance
    if (risqueA === 'élevé' && stade === 'floraison') score -= 40;
    if (risqueA === 'modéré' && stade === 'floraison') score -= 15;
    if (row.tableau_toxicologique === 'Ia') score -= 25;
    if (row.tableau_toxicologique === 'Ib') score -= 15;
    if (!row.dar_jours) score -= 5; // DAR inconnu = moins fiable

    // Bonus
    if (fracInfo && !dejaUtilise.utilise) score += 10;
    if (risqueA === 'très faible') score += 10;
    if (risqueA === 'faible') score += 5;
    if (row.dar_jours && row.dar_jours <= 3) score += 5; // DAR court = flexible

    return { ...row, score, fracInfo, iracInfo, risqueA };
  });

  // Trier par score desc
  scored.sort((a, b) => b.score - a.score);

  // Produit principal
  const best = scored[0];

  // Alternatives : produits de groupe FRAC/IRAC différent
  const bestFracGroupe = best.fracInfo?.groupe;
  const bestIracGroupe = best.iracInfo?.groupe;

  const alternatives = scored
    .slice(1)
    .filter(r => {
      if (r.id === best.id) return false;
      // Préférer groupes différents du principal
      const fracDiff = !bestFracGroupe || r.fracInfo?.groupe !== bestFracGroupe;
      const iracDiff = !bestIracGroupe || r.iracInfo?.groupe !== bestIracGroupe;
      return fracDiff || iracDiff;
    })
    .slice(0, nb_alternatives)
    .map(r => ({
      produit:       r.nom_commercial,
      matiere_active: r.matiere_active,
      groupe_frac:   r.fracInfo?.groupe || null,
      groupe_irac:   r.iracInfo?.groupe || null,
      dar:           r.dar_jours,
      dose:          parseDoseObj(r.dose),
    }));

  // ── 4. Construire la réponse ───────────────────────────────────────────
  const fracInfo = getGroupeFrac(best.matiere_active);
  const iracInfo = getGroupeIrac(best.matiere_active);
  const risqueA  = getRisqueAbeilles(best.matiere_active);
  const risqueAux = getRisqueAuxiliaires(best.matiere_active);
  const alertes  = genererAlertes(best, best, params);

  // Rotation recommandée
  let rotationNote = null;
  if (fracInfo?.groupe && ROTATION_RECOMMANDATIONS[fracInfo.groupe]) {
    rotationNote = ROTATION_RECOMMANDATIONS[fracInfo.groupe];
  }

  const conseil = {
    conseil_id:          generateConseilId(),
    produit:             best.nom_commercial,
    matiere_active:      best.matiere_active,
    numero_amm:          best.numero_homologation || null,
    detenteur:           best.detenteur || null,
    dose:                parseDoseObj(best.dose),
    dar:                 best.dar_jours,
    dar_raw:             best.dar_raw || null,
    nb_applications:     best.nb_applications || null,
    formulation:         best.formulation || null,
    categorie:           best.categorie,
    type_produit:        best.type_produit,
    usage_homologue:     best.usage_desc,
    culture_homologuee:  best.usage_culture,
    groupe_frac:         fracInfo ? fracInfo.groupe : null,
    groupe_irac:         iracInfo ? iracInfo.groupe : null,
    groupe_hrac:         null,
    risque_resistance:   fracInfo?.risque || iracInfo?.risque || null,
    mecanisme_action:    fracInfo?.mecanisme || iracInfo?.mecanisme || null,
    rotation_note:       rotationNote,
    homologue_onssa:     true,
    valable_jusquau:     best.valable_jusquau || null,
    tableau_toxicologique: best.tableau_toxicologique || null,
    conforme_globalgap:  globalgap ? null : null, // À enrichir
    lmr_ue_respectee:    params.export_ue ? null : null, // À enrichir
    risque_abeilles:     risqueA,
    risque_auxiliaires:  risqueAux,
    alertes,
    alternatives,
    meta: {
      culture_demandee:  culture,
      ravageur_demande:  ravageur || null,
      stade:             stade || null,
      dar_max_demande:   dar_max || null,
      nb_produits_trouves: rows.length,
      score_principal:   best.score,
    },
    timestamp: new Date().toISOString(),
  };

  return conseil;
}

/**
 * Repli : recherche uniquement par culture si ravageur non trouvé
 */
function genererConseilSansRavageur(params) {
  const db = getDb();
  const cultureLower = normalizeCulture(params.culture);

  let sql = `
    SELECT p.id, p.nom_commercial, p.numero_homologation, p.detenteur,
           p.categorie, p.type_produit, p.formulation, p.matiere_active,
           p.teneur, p.valable_jusquau, p.tableau_toxicologique,
           u.usage_desc, u.culture AS usage_culture, u.dose,
           u.dar_raw, u.dar_jours, u.nb_applications
    FROM produits p JOIN usages u ON p.id = u.produit_id
    WHERE LOWER(u.culture) LIKE ?
  `;
  const sqlParams = [cultureLower + '%'];

  if (params.dar_max != null) {
    sql += ` AND (u.dar_jours IS NULL OR u.dar_jours <= ?)`;
    sqlParams.push(parseInt(params.dar_max, 10));
  }

  sql += ` ORDER BY u.dar_jours ASC NULLS LAST LIMIT 20`;

  const rows = db.prepare(sql).all(...sqlParams);

  if (!rows || rows.length === 0) {
    const error = new Error(`Aucun produit homologué trouvé pour la culture "${params.culture}"`);
    error.code  = 'CULTURE_NOT_FOUND';
    error.suggestion = 'Vérifiez le nom de la culture ou consultez GET /cultures';
    throw error;
  }

  const best = rows[0];
  const fracInfo = getGroupeFrac(best.matiere_active);
  const iracInfo = getGroupeIrac(best.matiere_active);

  return {
    conseil_id:      generateConseilId(),
    produit:         best.nom_commercial,
    matiere_active:  best.matiere_active,
    numero_amm:      best.numero_homologation || null,
    dose:            parseDoseObj(best.dose),
    dar:             best.dar_jours,
    formulation:     best.formulation || null,
    categorie:       best.categorie,
    usage_homologue: best.usage_desc,
    groupe_frac:     fracInfo?.groupe || null,
    groupe_irac:     iracInfo?.groupe || null,
    risque_abeilles: getRisqueAbeilles(best.matiere_active),
    risque_auxiliaires: getRisqueAuxiliaires(best.matiere_active),
    homologue_onssa: true,
    alertes:         genererAlertes(best, best, params),
    alternatives:    rows.slice(1, 1 + (params.nb_alternatives || 2)).map(r => ({
      produit:       r.nom_commercial,
      matiere_active: r.matiere_active,
      groupe_frac:   getGroupeFrac(r.matiere_active)?.groupe || null,
      dar:           r.dar_jours,
      dose:          parseDoseObj(r.dose),
    })),
    meta: {
      culture_demandee: params.culture,
      ravageur_demande: params.ravageur || null,
      note: 'Ravageur non trouvé — conseil basé sur la culture uniquement',
      nb_produits_trouves: rows.length,
    },
    timestamp: new Date().toISOString(),
  };
}

module.exports = { genererConseil };
