# @agrisage/sdk

SDK Node.js officiel pour l'[API AgriSage](https://docs.agrisage.ma) — conseil phytosanitaire pour l'agriculture marocaine.

> Croise l'index ONSSA, les groupes IRAC/FRAC/HRAC, GlobalGAP v6 et les LMR export UE en une seule requête.

## Installation

```bash
npm install @agrisage/sdk
# ou
yarn add @agrisage/sdk
```

Aucune dépendance externe. Node.js ≥ 16 requis.

## Démarrage rapide

```js
const { AgriSageClient, STADES, REGIONS } = require('@agrisage/sdk');

const agrisage = new AgriSageClient({
  apiKey: process.env.AGRISAGE_API_KEY,
});

const { data: conseil } = await agrisage.conseil.generer({
  culture  : 'tomate',
  ravageur : 'botrytis',
  stade    : STADES.FLORAISON,
  region   : REGIONS.SOUSS_MASSA,
  darMax   : 7,
  globalgap: true,
});

console.log(conseil.produit);          // "Switch 62.5 WG"
console.log(conseil.dar);             // 3
console.log(conseil.groupe_frac);     // "9 + 12"
console.log(conseil.risque_abeilles); // "faible"
console.log(conseil.alertes);         // ["Stade floraison : appliquer après 19h"]
```

## Configuration

```js
const agrisage = new AgriSageClient({
  apiKey    : 'as_live_xxxxxxxxxxxx', // requis
  lang      : 'fr',                  // 'fr' (défaut) | 'ar'
  sandbox   : false,                 // true = données fictives, quota illimité
  timeout   : 30_000,               // ms (défaut : 30 000)
  maxRetries: 2,                     // tentatives auto sur erreur réseau / 5xx
  debug     : false,                 // logs de debug dans la console
});
```

### Variables d'environnement recommandées

```bash
AGRISAGE_API_KEY=as_live_xxxxxxxxxxxx
```

---

## Référence complète

### `agrisage.conseil.generer(params)`

Génère un conseil phytosanitaire validé.

```js
const { data } = await agrisage.conseil.generer({
  culture          : 'tomate',          // requis
  ravageur         : 'botrytis',        // requis
  stade            : 'floraison',       // requis
  region           : 'souss-massa',
  darMax           : 7,
  globalgap        : true,
  exportUe         : true,              // plan Pro+
  historiqueFrac   : ['1', '9'],        // rotation anti-résistance
  historiqueIrac   : ['3A'],
  nbAlternatives   : 3,                 // 0–5, défaut 2
  lang             : 'fr',
});

// data.produit          → nom commercial
// data.matiere_active   → MA(s)
// data.dose             → { valeur: 0.8, unite: 'kg/ha' }
// data.dar              → DAR en jours
// data.groupe_frac      → groupe(s) FRAC
// data.risque_abeilles  → 'faible' | 'modéré' | 'élevé'
// data.conforme_globalgap → boolean
// data.alertes          → string[]
// data.alternatives     → AlternativeProduit[]
```

---

### `agrisage.produits.lister(params?)`

```js
const { data } = await agrisage.produits.lister({
  culture   : 'tomate',
  usage     : 'fongicide',
  ma        : 'cyprodinil',    // correspondance partielle
  statut    : 'homologue',     // défaut
  groupeFrac: '9',
  page      : 1,
});
// data.data       → ProduitONSSA[]
// data.pagination → { page, par_page, total, pages_total }
```

### `agrisage.produits.obtenir(id, lang?)`

```js
const { data } = await agrisage.produits.obtenir('prod_onssa_00412');
// data.nom_commercial       → "Switch 62.5 WG"
// data.cultures_homologuees → ["tomate", "poivron", ...]
// data.statut               → "homologué"
```

---

### `agrisage.traitement.enregistrer(params)` _(plan Pro+)_

```js
const { data } = await agrisage.traitement.enregistrer({
  parcelleId        : 'parcelle_nord_003',  // requis
  produitNom        : 'Switch 62.5 WG',    // requis
  doseAppliquee     : { valeur: 0.8, unite: 'kg/ha' }, // requis
  dateTraitement    : '2025-03-15',         // requis
  conseilId         : 'c_8f2a1d3e',
  culture           : 'tomate',
  surfaceTraitee    : 2.5,
  dateRecoltePrevue : '2025-03-25',        // déclenche alerte si DAR dépassé
  operateur         : 'Ahmed Benali',
  epiPortes         : ['gants nitrile', 'masque FFP2'],
  conditionsMeteo   : { temperatureC: 22, ventKmh: 8, hygrometriePct: 65 },
  notes             : 'Application en début de matinée',
});
// data.traitement_id → "tr_9c3b1f2a"
// data.statut        → "enregistré" | "alerte_dar" | "alerte_produit"
// data.dar_restant   → jours restants avant DAR
```

---

### `agrisage.carnet.obtenir(params?)` _(plan Pro+)_

```js
const { data } = await agrisage.carnet.obtenir({
  parcelleId : 'parcelle_nord_003',
  du         : '2025-01-01',
  au         : '2025-03-31',
  page       : 1,
});
```

### `agrisage.carnet.exporterPdf(params?)` _(plan Pro+)_

```js
const fs = require('fs');

const pdfBuffer = await agrisage.carnet.exporterPdf({
  parcelleId: 'parcelle_nord_003',
  du        : '2025-01-01',
  au        : '2025-12-31',
});

fs.writeFileSync('./audit-globalgap-2025.pdf', pdfBuffer);
console.log('Rapport PDF GlobalGAP exporté.');
```

---

### `agrisage.groupes.lister(params)` / `.irac()` / `.frac()` / `.hrac()`

```js
// Via le type explicite
const { data } = await agrisage.groupes.lister({ type: 'frac', ma: 'cyprodinil' });

// Raccourcis
const frac = await agrisage.groupes.frac({ ma: 'cyprodinil' });
const irac = await agrisage.groupes.irac({ risque: 'élevé' });
const hrac = await agrisage.groupes.hrac();

// data.data[0].numero                   → "9"
// data.data[0].risque_resistance        → "modéré"
// data.data[0].recommandation_rotation  → "Ne pas appliquer plus de 2 fois..."
```

---

### `agrisage.alertes.lister(params?)` / `.nonLues()` / `.critiques()`

```js
const { data } = await agrisage.alertes.lister({
  type      : 'DAR_DEPASSE',
  urgence   : 'critique',
  parcelleId: 'parcelle_nord_003',
  lue       : false,
});
// data.non_lues → nombre d'alertes non lues

// Raccourcis
const nonLues  = await agrisage.alertes.nonLues();
const critiques = await agrisage.alertes.critiques();
```

### `agrisage.alertes.marquerLue(id)`

```js
await agrisage.alertes.marquerLue('al_7d4e2f1b');
```

---

### `agrisage.cultures.lister()` / `.rechercher(terme)`

```js
const { data } = await agrisage.cultures.rechercher('tom');
// data.data[0] → { id: 'tomate', nom_fr: 'Tomate', nom_ar: 'الطماطم', ... }
```

---

## Gestion des erreurs

Chaque erreur étend `AgriSageError` avec `code`, `statusCode`, `requestId` et `suggestion`.

```js
const {
  AgriSageError,
  AuthenticationError,
  PlanLimitError,
  QuotaExceededError,
  NotFoundError,
  ValidationError,
  NetworkError,
} = require('@agrisage/sdk');

try {
  const { data } = await agrisage.conseil.generer({ culture: 'tomate', ravageur: 'botrytis', stade: 'floraison' });
} catch (err) {
  if (err instanceof AuthenticationError) {
    console.error('Clé API invalide :', err.message);
  } else if (err instanceof PlanLimitError) {
    console.error('Plan insuffisant :', err.message);
    console.log('Suggestion :', err.suggestion);
  } else if (err instanceof QuotaExceededError) {
    console.error('Quota épuisé. Renouvellement :', err.resetAt);
  } else if (err instanceof ValidationError) {
    console.error('Paramètre invalide :', err.message);
  } else if (err instanceof NetworkError) {
    console.error('Erreur réseau :', err.message);
  } else {
    throw err;
  }
}
```

---

## Utilisation avec TypeScript

Le SDK inclut les déclarations TypeScript complètes.

```ts
import { AgriSageClient, ConseilParams, Conseil, STADES } from '@agrisage/sdk';

const agrisage = new AgriSageClient({ apiKey: process.env.AGRISAGE_API_KEY! });

const params: ConseilParams = {
  culture : 'tomate',
  ravageur: 'botrytis',
  stade   : STADES.FLORAISON,
  darMax  : 7,
};

const { data }: { data: Conseil } = await agrisage.conseil.generer(params);
```

---

## Exemples complets

### Application Node.js — conseil quotidien automatisé

```js
const { AgriSageClient, STADES, REGIONS, QuotaExceededError } = require('@agrisage/sdk');

const agrisage = new AgriSageClient({
  apiKey: process.env.AGRISAGE_API_KEY,
  lang  : 'fr',
  debug : process.env.NODE_ENV === 'development',
});

async function conseillerParcelle(parcelle) {
  try {
    const { data: conseil, rateLimit } = await agrisage.conseil.generer({
      culture   : parcelle.culture,
      ravageur  : parcelle.ravageurDetecte,
      stade     : parcelle.stade,
      region    : parcelle.region,
      darMax    : parcelle.joursAvantRecolte,
      globalgap : parcelle.certifieeGlobalGap,
      exportUe  : parcelle.exporteVersUe,
    });

    // Vérifier les alertes critiques
    if (conseil.risque_abeilles === 'élevé') {
      await envoyerAlerteSMS(parcelle.technicien, `⚠️ ${conseil.produit} — risque élevé abeilles`);
    }

    // Enregistrer le traitement
    if (parcelle.traitementPlanifie) {
      await agrisage.traitement.enregistrer({
        conseilId        : conseil.conseil_id,
        parcelleId       : parcelle.id,
        produitNom       : conseil.produit,
        doseAppliquee    : conseil.dose,
        dateTraitement   : new Date().toISOString().slice(0, 10),
        dateRecoltePrevue: parcelle.dateRecolte,
        operateur        : parcelle.operateur,
      });
    }

    console.log(`✅ ${parcelle.id} → ${conseil.produit} (DAR ${conseil.dar}j) | quota restant: ${rateLimit.remaining}`);
    return conseil;

  } catch (err) {
    if (err instanceof QuotaExceededError) {
      console.warn(`Quota épuisé jusqu'au ${err.resetAt}. Mise en file d'attente.`);
      await mettreEnFile(parcelle);
    } else {
      throw err;
    }
  }
}
```

### Export PDF mensuel GlobalGAP

```js
const fs   = require('fs');
const path = require('path');

async function exporterBilanMensuel(parcelleId, annee, mois) {
  const du = `${annee}-${String(mois).padStart(2, '0')}-01`;
  const au = new Date(annee, mois, 0).toISOString().slice(0, 10);

  const pdfBuffer = await agrisage.carnet.exporterPdf({ parcelleId, du, au });

  const fichier = path.join('./rapports', `globalgap_${parcelleId}_${annee}-${mois}.pdf`);
  fs.mkdirSync('./rapports', { recursive: true });
  fs.writeFileSync(fichier, pdfBuffer);

  console.log(`📄 Rapport GlobalGAP exporté : ${fichier} (${(pdfBuffer.length / 1024).toFixed(1)} Ko)`);
  return fichier;
}
```

---

## Rate limiting

Chaque réponse expose les headers de quota dans `rateLimit` :

```js
const { data, rateLimit } = await agrisage.conseil.generer({ ... });

console.log(rateLimit.limit);     // quota total du plan
console.log(rateLimit.remaining); // requêtes restantes ce mois
console.log(rateLimit.reset);     // date de renouvellement ISO 8601
```

Le SDK gère automatiquement les retries avec backoff exponentiel sur les erreurs 5xx et réseau.

---

## Sandbox

```js
const agrisage = new AgriSageClient({
  apiKey : 'as_test_xxxxxxxxxxxx', // clé sandbox
  sandbox: true,
});
// Quota illimité, données fictives — idéal pour CI/CD et développement
```

---

## Support & ressources

- Documentation : [docs.agrisage.ma](https://docs.agrisage.ma)
- Statut API : [status.agrisage.ma](https://status.agrisage.ma)
- Email : api@agrisage.ma
- GitHub Issues : [github.com/agrisage/sdk-node/issues](https://github.com/agrisage/sdk-node/issues)

---

## Licence

MIT © [AgriSage](https://agrisage.ma)
