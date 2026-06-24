'use strict';

/**
 * AgriSage — Couche base de données
 * Utilise better-sqlite3 (synchrone, performant, zéro config)
 * En production : remplacer par pg (PostgreSQL)
 */

const Database = require('better-sqlite3');
const path     = require('path');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, '../../../onssa_index.db');

let _db = null;

function getDb() {
  if (!_db) {
    _db = new Database(DB_PATH, {
      readonly: false,
      fileMustExist: true,
    });
    // Optimisations SQLite
    _db.pragma('journal_mode = WAL');
    _db.pragma('synchronous = NORMAL');
    _db.pragma('cache_size = -64000'); // 64 MB cache
    _db.pragma('temp_store = MEMORY');
    console.log(`[DB] Connecté : ${DB_PATH}`);
  }
  return _db;
}

function closeDb() {
  if (_db) {
    _db.close();
    _db = null;
  }
}

module.exports = { getDb, closeDb };
