'use strict';

// Tests du SDK AgriSage (sans dépendances externes)

const {
  AgriSageClient,
  AgriSageError,
  AuthenticationError,
  ValidationError,
  STADES,
  REGIONS,
  USAGES,
  ALERTES_TYPES,
} = require('../src/index.js');

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✅  ${name}`);
    passed++;
  } catch (err) {
    console.log(`  ❌  ${name}`);
    console.log(`       ${err.message}`);
    failed++;
  }
}

function assert(condition, msg) {
  if (!condition) throw new Error(msg || 'Assertion échouée');
}

function assertThrows(fn, ErrorClass, msg) {
  let threw = false;
  try { fn(); } catch (err) {
    threw = true;
    if (ErrorClass && !(err instanceof ErrorClass)) {
      throw new Error(`Attendu ${ErrorClass.name}, reçu ${err.constructor.name} : ${err.message}`);
    }
  }
  if (!threw) throw new Error(msg || 'Aucune erreur levée');
}

// ── Tests ─────────────────────────────────────────────────────────────────────

console.log('\nAgriSage SDK — Tests unitaires\n');

console.log('1. Initialisation du client');

test('Lance une erreur si apiKey absent', () => {
  assertThrows(() => new AgriSageClient({}), AgriSageError);
});

test('Crée un client avec apiKey valide', () => {
  const c = new AgriSageClient({ apiKey: 'as_test_abc123' });
  assert(c.conseil,    'conseil resource manquant');
  assert(c.produits,   'produits resource manquant');
  assert(c.traitement, 'traitement resource manquant');
  assert(c.carnet,     'carnet resource manquant');
  assert(c.groupes,    'groupes resource manquant');
  assert(c.alertes,    'alertes resource manquant');
  assert(c.cultures,   'cultures resource manquant');
});

test('Utilise le sandbox URL si sandbox=true', () => {
  const c = new AgriSageClient({ apiKey: 'as_test_abc', sandbox: true });
  assert(c._baseUrl.includes('sandbox'), 'URL sandbox incorrecte');
});

test('Utilise baseUrl personnalisée', () => {
  const c = new AgriSageClient({ apiKey: 'as_test_abc', baseUrl: 'http://localhost:3000' });
  assert(c._baseUrl === 'http://localhost:3000', 'baseUrl non appliquée');
});

test('Applique la langue par défaut fr', () => {
  const c = new AgriSageClient({ apiKey: 'as_test_abc' });
  assert(c._lang === 'fr', 'Langue par défaut incorrecte');
});

test('Accepte lang ar', () => {
  const c = new AgriSageClient({ apiKey: 'as_test_abc', lang: 'ar' });
  assert(c._lang === 'ar', 'Langue ar non appliquée');
});

console.log('\n2. Validation des paramètres');

test('conseil.generer — valide les champs requis', async () => {
  const c = new AgriSageClient({ apiKey: 'as_test_abc' });
  try {
    await c.conseil.generer({ culture: 'tomate' });
    assert(false, 'Aurait dû lever une erreur');
  } catch (err) {
    assert(err instanceof ValidationError, `Attendu ValidationError, reçu ${err.constructor.name}`);
    assert(err.code === 'INVALID_PARAM', `code incorrect: ${err.code}`);
  }
});

test('traitement.enregistrer — valide les champs requis', async () => {
  const c = new AgriSageClient({ apiKey: 'as_test_abc' });
  try {
    await c.traitement.enregistrer({ parcelleId: 'p1' });
    assert(false, 'Aurait dû lever une erreur');
  } catch (err) {
    assert(err instanceof ValidationError);
  }
});

test('alertes.marquerLue — valide id requis', async () => {
  const c = new AgriSageClient({ apiKey: 'as_test_abc' });
  try {
    await c.alertes.marquerLue(null);
    assert(false, 'Aurait dû lever une erreur');
  } catch (err) {
    assert(err instanceof ValidationError);
  }
});

test('produits.obtenir — valide id requis', async () => {
  const c = new AgriSageClient({ apiKey: 'as_test_abc' });
  try {
    await c.produits.obtenir('');
    assert(false, 'Aurait dû lever une erreur');
  } catch (err) {
    assert(err instanceof ValidationError);
  }
});

test('groupes.lister — valide type requis', async () => {
  const c = new AgriSageClient({ apiKey: 'as_test_abc' });
  try {
    await c.groupes.lister({});
    assert(false, 'Aurait dû lever une erreur');
  } catch (err) {
    assert(err instanceof ValidationError);
  }
});

console.log('\n3. Constantes exportées');

test('STADES contient tous les stades attendus', () => {
  const attendus = ['GERMINATION', 'LEVEE', 'VEGETATION', 'FLORAISON', 'FRUCTIFICATION', 'RECOLTE', 'POST_RECOLTE'];
  for (const s of attendus) {
    assert(STADES[s], `STADES.${s} manquant`);
  }
  assert(STADES.FLORAISON === 'floraison');
});

test('REGIONS contient les régions marocaines', () => {
  assert(REGIONS.SOUSS_MASSA   === 'souss-massa');
  assert(REGIONS.GHARB_CHRARDA === 'gharb-chrarda');
  assert(REGIONS.TANGER_TETOUAN === 'tanger-tetouan');
});

test('USAGES contient les types de traitement', () => {
  assert(USAGES.FONGICIDE   === 'fongicide');
  assert(USAGES.INSECTICIDE === 'insecticide');
  assert(USAGES.HERBICIDE   === 'herbicide');
});

test('ALERTES_TYPES contient les types d\'alertes', () => {
  assert(ALERTES_TYPES.DAR_DEPASSE    === 'DAR_DEPASSE');
  assert(ALERTES_TYPES.PRODUIT_RETIRE === 'PRODUIT_RETIRE');
  assert(ALERTES_TYPES.LMR_MODIFIEE  === 'LMR_MODIFIEE');
});

test('Les constantes sont gelées (immutables)', () => {
  let erreur = false;
  try {
    STADES.NOUVEAU = 'nouveau'; // doit échouer en strict mode
  } catch {
    erreur = true;
  }
  // En strict mode, modification d'objet gelé lève une TypeError
  // En mode non-strict, ça échoue silencieusement — on vérifie que la valeur est inchangée
  assert(STADES.NOUVEAU === undefined || erreur, 'STADES devrait être immutable');
});

console.log('\n4. Hiérarchie des erreurs');

test('AgriSageError est une instance de Error', () => {
  const e = new AgriSageError('test', 'CODE', 500);
  assert(e instanceof Error);
  assert(e instanceof AgriSageError);
  assert(e.code === 'CODE');
  assert(e.statusCode === 500);
});

test('AuthenticationError hérite de AgriSageError', () => {
  const e = new AuthenticationError('Non autorisé', 'req_123');
  assert(e instanceof AgriSageError);
  assert(e.statusCode === 401);
  assert(e.requestId === 'req_123');
});

test('ValidationError a code INVALID_PARAM', () => {
  const e = new ValidationError('Champ manquant');
  assert(e.code === 'INVALID_PARAM');
  assert(e.statusCode === 400);
});

console.log('\n5. Raccourcis des ressources');

test('groupes.irac() appelle lister avec type=irac', async () => {
  const c = new AgriSageClient({ apiKey: 'as_test_abc' });
  let capturedQuery = null;
  c._request = async (method, path, opts) => {
    capturedQuery = opts?.query;
    return { data: { data: [], total: 0 }, rateLimit: {} };
  };
  await c.groupes.irac({ ma: 'abamectine' });
  assert(capturedQuery?.type === 'irac', 'type=irac non transmis');
  assert(capturedQuery?.ma === 'abamectine', 'ma non transmis');
});

test('alertes.nonLues() appelle lister avec lue=false', async () => {
  const c = new AgriSageClient({ apiKey: 'as_test_abc' });
  let capturedQuery = null;
  c._request = async (method, path, opts) => {
    capturedQuery = opts?.query;
    return { data: { data: [], non_lues: 0, pagination: {} }, rateLimit: {} };
  };
  await c.alertes.nonLues();
  assert(capturedQuery?.lue === false, 'lue=false non transmis');
});

test('cultures.rechercher(terme) passe q=terme', async () => {
  const c = new AgriSageClient({ apiKey: 'as_test_abc' });
  let capturedQuery = null;
  c._request = async (method, path, opts) => {
    capturedQuery = opts?.query;
    return { data: { data: [], total: 0 }, rateLimit: {} };
  };
  await c.cultures.rechercher('tom');
  assert(capturedQuery?.q === 'tom', 'q=tom non transmis');
});

// ── Résumé ────────────────────────────────────────────────────────────────────

console.log(`\n${'─'.repeat(40)}`);
console.log(`Résultat : ${passed} passés · ${failed} échoués`);

if (failed > 0) {
  process.exit(1);
} else {
  console.log('Tous les tests sont passés ✅\n');
}
