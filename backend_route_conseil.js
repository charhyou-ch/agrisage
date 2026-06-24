'use strict';

/**
 * AgriSage — Route POST /conseil
 * Génère un conseil phytosanitaire complet
 */

const express        = require('express');
const router         = express.Router();
const { genererConseil } = require('../services/conseilService');

// Valeurs autorisées
const STADES_VALIDES = [
  'germination','levee','vegetation','floraison',
  'fructification','recolte','post-recolte',
];
const REGIONS_VALIDES = [
  'souss-massa','gharb-chrarda','marrakech-safi','fes-meknes',
  'tanger-tetouan','oriental','rabat-sale-kenitra',
  'beni-mellal-khenifra','draa-tafilalet','laayoune-sakia',
];

/**
 * Validation des paramètres d'entrée
 */
function validerParams(body) {
  const errors = [];

  if (!body.culture || typeof body.culture !== 'string' || !body.culture.trim()) {
    errors.push({ champ: 'culture', message: 'Le champ culture est requis.' });
  }
  if (!body.ravageur || typeof body.ravageur !== 'string' || !body.ravageur.trim()) {
    errors.push({ champ: 'ravageur', message: 'Le champ ravageur est requis.' });
  }
  if (!body.stade || typeof body.stade !== 'string') {
    errors.push({ champ: 'stade', message: 'Le champ stade est requis.' });
  } else if (!STADES_VALIDES.includes(body.stade.toLowerCase())) {
    errors.push({
      champ: 'stade',
      message: `Stade invalide. Valeurs acceptées : ${STADES_VALIDES.join(', ')}`,
    });
  }
  if (body.dar_max !== undefined) {
    const d = parseInt(body.dar_max, 10);
    if (isNaN(d) || d < 0 || d > 365) {
      errors.push({ champ: 'dar_max', message: 'dar_max doit être un entier entre 0 et 365.' });
    }
  }
  if (body.nb_alternatives !== undefined) {
    const n = parseInt(body.nb_alternatives, 10);
    if (isNaN(n) || n < 0 || n > 5) {
      errors.push({ champ: 'nb_alternatives', message: 'nb_alternatives doit être entre 0 et 5.' });
    }
  }
  if (body.historique_frac && !Array.isArray(body.historique_frac)) {
    errors.push({ champ: 'historique_frac', message: 'historique_frac doit être un tableau.' });
  }
  if (body.historique_irac && !Array.isArray(body.historique_irac)) {
    errors.push({ champ: 'historique_irac', message: 'historique_irac doit être un tableau.' });
  }

  return errors;
}

/**
 * POST /conseil
 *
 * Body JSON :
 *   culture          string  requis
 *   ravageur         string  requis
 *   stade            string  requis  (germination|levee|vegetation|floraison|...)
 *   region           string  optionnel
 *   dar_max          integer optionnel  DAR max en jours
 *   globalgap        boolean optionnel
 *   export_ue        boolean optionnel
 *   historique_frac  string[] optionnel  ex: ["3","11"]
 *   historique_irac  string[] optionnel  ex: ["3A","4A"]
 *   nb_alternatives  integer optionnel  (0-5, défaut 2)
 *   lang             string  optionnel  "fr"|"ar"
 */
router.post('/', (req, res) => {
  const startTime = Date.now();

  // ── Validation ──────────────────────────────────────────────────────
  const errors = validerParams(req.body);
  if (errors.length > 0) {
    return res.status(400).json({
      error: {
        code:       'INVALID_PARAM',
        message:    'Paramètre(s) invalide(s) ou manquant(s).',
        details:    errors,
        request_id: req.requestId,
        suggestion: 'Consultez https://docs.agrisage.ma pour les paramètres requis.',
      },
    });
  }

  // ── Appel moteur ─────────────────────────────────────────────────────
  try {
    const params = {
      culture:          req.body.culture.trim(),
      ravageur:         req.body.ravageur.trim(),
      stade:            req.body.stade.toLowerCase().trim(),
      region:           req.body.region || null,
      dar_max:          req.body.dar_max != null ? parseInt(req.body.dar_max, 10) : null,
      globalgap:        req.body.globalgap === true,
      export_ue:        req.body.export_ue === true,
      historique_frac:  Array.isArray(req.body.historique_frac) ? req.body.historique_frac : [],
      historique_irac:  Array.isArray(req.body.historique_irac) ? req.body.historique_irac : [],
      nb_alternatives:  req.body.nb_alternatives != null ? parseInt(req.body.nb_alternatives, 10) : 2,
      lang:             req.body.lang || 'fr',
    };

    const conseil = genererConseil(params);
    const elapsed = Date.now() - startTime;

    // Headers rate-limit (simulés — brancher sur le vrai compteur en production)
    res.set({
      'X-Response-Time':      `${elapsed}ms`,
      'X-RateLimit-Remaining': String(req.rateLimitRemaining || 9999),
    });

    return res.status(200).json(conseil);

  } catch (err) {
    const elapsed = Date.now() - startTime;
    console.error(`[POST /conseil] Erreur après ${elapsed}ms :`, err.message);

    // Erreur métier (culture non trouvée, etc.)
    if (err.code === 'CULTURE_NOT_FOUND') {
      return res.status(404).json({
        error: {
          code:       'CULTURE_NOT_FOUND',
          message:    err.message,
          suggestion: err.suggestion,
          request_id: req.requestId,
        },
      });
    }

    // Erreur inattendue
    return res.status(500).json({
      error: {
        code:       'SERVER_ERROR',
        message:    'Erreur interne du serveur. Réessayez dans quelques instants.',
        request_id: req.requestId,
      },
    });
  }
});

module.exports = router;
