'use strict';

require('dotenv').config();

const express    = require('express');
const cors       = require('cors');
const helmet     = require('helmet');
const rateLimit  = require('express-rate-limit');
const { v4: uuidv4 } = require('uuid');
const { closeDb } = require('./db/database');

const app  = express();
const PORT = process.env.PORT || 3000;
const ENV  = process.env.NODE_ENV || 'development';

// ── Sécurité & headers ─────────────────────────────────────────────────────
app.use(helmet());
app.use(cors({
  origin: process.env.CORS_ORIGIN || '*',
  methods: ['GET', 'POST', 'PATCH', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));

// ── Body parser ────────────────────────────────────────────────────────────
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: false }));

// ── Request ID ────────────────────────────────────────────────────────────
app.use((req, res, next) => {
  req.requestId = `req_${uuidv4().replace(/-/g,'').slice(0,12)}`;
  res.set('X-Request-Id', req.requestId);
  next();
});

// ── Logging ───────────────────────────────────────────────────────────────
app.use((req, _res, next) => {
  if (ENV !== 'test') {
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  }
  next();
});

// ── Rate limiting ─────────────────────────────────────────────────────────
const limiter = rateLimit({
  windowMs:         60 * 1000,      // 1 minute
  max:              120,            // 120 req/min en dev
  standardHeaders:  true,
  legacyHeaders:    false,
  handler: (req, res) => {
    res.status(429).json({
      error: {
        code:       'QUOTA_EXCEEDED',
        message:    'Trop de requêtes. Attendez avant de réessayer.',
        request_id: req.requestId,
      },
    });
  },
});
app.use('/v1/', limiter);

// ── Auth middleware (simplifié — à brancher sur JWT en prod) ──────────────
app.use('/v1/', (req, res, next) => {
  const auth = req.headers.authorization;
  if (!auth || !auth.startsWith('Bearer ')) {
    return res.status(401).json({
      error: {
        code:       'UNAUTHORIZED',
        message:    'Clé API manquante. Ajoutez : Authorization: Bearer as_live_XXXX',
        suggestion: 'Obtenez votre clé sur agrisage.ma/dashboard',
        request_id: req.requestId,
      },
    });
  }
  const key = auth.replace('Bearer ', '').trim();
  // En dev, accepter toutes les clés as_test_ et as_live_
  if (!key.startsWith('as_test_') && !key.startsWith('as_live_')) {
    return res.status(401).json({
      error: {
        code:       'UNAUTHORIZED',
        message:    'Clé API invalide. Les clés doivent commencer par as_test_ ou as_live_.',
        request_id: req.requestId,
      },
    });
  }
  req.isSandbox = key.startsWith('as_test_');
  req.rateLimitRemaining = 9999; // Brancher sur la BDD en production
  next();
});

// ── Routes ────────────────────────────────────────────────────────────────
app.use('/v1/conseil',   require('./routes/conseil'));

// Route santé (pas d'auth)
app.get('/health', (_req, res) => {
  res.json({
    status:  'ok',
    service: 'AgriSage API',
    version: '1.0.0',
    env:     ENV,
    time:    new Date().toISOString(),
  });
});

// Route racine
app.get('/', (_req, res) => {
  res.json({
    name:    'AgriSage API',
    version: '1.0.0',
    docs:    'https://docs.agrisage.ma',
    base_url: '/v1',
    endpoints: [
      'POST /v1/conseil',
      'GET  /v1/produits',
      'GET  /v1/produits/:id',
      'POST /v1/traitement',
      'GET  /v1/carnet',
      'GET  /v1/groupes',
      'GET  /v1/alertes',
      'GET  /v1/cultures',
    ],
  });
});

// 404
app.use((_req, res) => {
  res.status(404).json({
    error: {
      code:    'NOT_FOUND',
      message: 'Endpoint introuvable.',
      docs:    'https://docs.agrisage.ma',
    },
  });
});

// Erreur globale
app.use((err, _req, res, _next) => {
  console.error('[ERROR]', err);
  res.status(500).json({
    error: {
      code:    'SERVER_ERROR',
      message: 'Erreur interne du serveur.',
    },
  });
});

// ── Démarrage ─────────────────────────────────────────────────────────────
const server = app.listen(PORT, () => {
  console.log(`\n🌿 AgriSage API démarré`);
  console.log(`   URL     : http://localhost:${PORT}`);
  console.log(`   Env     : ${ENV}`);
  console.log(`   Version : 1.0.0\n`);
});

// Arrêt propre
process.on('SIGTERM', () => {
  server.close(() => {
    closeDb();
    process.exit(0);
  });
});

module.exports = app;
