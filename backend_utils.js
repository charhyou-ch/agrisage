'use strict';

/**
 * AgriSage — Utilitaires de parsing des données ONSSA
 */

/**
 * Parse une valeur DAR brute en entier (jours)
 * Gère les formats : "7", "07", "7 j", "7jrs", "7 jours", "-", "NR", ""
 */
function parseDar(raw) {
  if (!raw || typeof raw !== 'string') return null;
  const s = raw.trim();
  if (['-', '--', '---', 'NR', 'nr', 'N/A', ''].includes(s)) return null;
  const m = s.match(/^(\d+)/);
  return m ? parseInt(m[1], 10) : null;
}

/**
 * Normalise une catégorie ONSSA vers le type_produit API
 */
function normalizeCategorie(cat) {
  if (!cat) return 'autre';
  const c = cat.toLowerCase();
  if (c.includes('fongicide') && c.includes('bact'))       return 'fongicide-bactericide';
  if (c.includes('insecticide') && c.includes('acaricide')) return 'insecticide-acaricide';
  if (c.includes('insecticide') && c.includes('fongicide')) return 'insecticide-fongicide';
  if (c.includes('insecticide') && c.includes('fumigant'))  return 'insecticide-fumigant';
  if (c.includes('insecticide') && c.includes('acridicide'))return 'insecticide-acridicide';
  if (c.includes('nématicide') && c.includes('fumigant'))   return 'nematicide-fumigant';
  if (c.includes('herbicide') && c.includes('régulateur'))  return 'herbicide-regulateur';
  if (c.includes('fongicide'))                              return 'fongicide';
  if (c.includes('insecticide'))                            return 'insecticide';
  if (c.includes('herbicide'))                              return 'herbicide';
  if (c.includes('acaricide'))                              return 'acaricide';
  if (c.includes('nématicide'))                             return 'nematicide';
  if (c.includes('molluscicide'))                           return 'molluscicide';
  if (c.includes('acridicide'))                             return 'acridicide';
  if (c.includes('régulateur'))                             return 'regulateur-croissance';
  if (c.includes('adjuvant'))                               return 'adjuvant';
  if (c.includes('phéromone'))                              return 'pheromone';
  if (c.includes('rodenticide'))                            return 'rodenticide';
  if (c.includes('virucide'))                               return 'virucide';
  if (c.includes('bactéricide'))                            return 'bactericide';
  return 'autre';
}

/**
 * Normalise un nom de culture pour la recherche (insensible à la casse/accents)
 */
function normalizeCulture(name) {
  return name
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();
}

/**
 * Extrait le nom de base d'une matière active (sans teneur/concentration)
 * Ex: "Azoxystrobine(250 g/l)" → "Azoxystrobine"
 */
function extractMaBase(maComplet) {
  if (!maComplet) return '';
  return maComplet
    .replace(/\s*[\(\[]\d[^\)\]]*[\)\]]/g, '')
    .replace(/\s*-\s*\d.*$/, '')
    .replace(/\s*\(\d.*\)$/, '')
    .trim();
}

/**
 * Parse une date au format DD/MM/YYYY → YYYY-MM-DD
 */
function parseDate(str) {
  if (!str || !str.includes('/')) return null;
  const parts = str.split('/');
  if (parts.length !== 3) return null;
  return `${parts[2]}-${parts[1].padStart(2,'0')}-${parts[0].padStart(2,'0')}`;
}

/**
 * Génère un conseil_id unique
 */
function generateConseilId() {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  const rand  = Array.from({length: 8}, () => chars[Math.floor(Math.random() * chars.length)]).join('');
  return `c_${rand}`;
}

module.exports = {
  parseDar,
  normalizeCategorie,
  normalizeCulture,
  extractMaBase,
  parseDate,
  generateConseilId,
};
