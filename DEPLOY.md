# AgriSage — Guide déploiement Railway

## Pré-requis
- Compte Railway : https://railway.app (gratuit)
- Repo GitHub : https://github.com/charhyou-ch/agrisage

## Étapes (5 minutes)

### 1. Créer un projet Railway
1. Aller sur https://railway.app
2. "New Project" → "Deploy from GitHub repo"
3. Sélectionner `charhyou-ch/agrisage`
4. Railway détecte Python automatiquement ✅

### 2. Uploader la base de données ONSSA
Railway ne persiste pas les fichiers entre déploiements.
**Solution** : utiliser Railway Volumes (disque persistant).

Dans le dashboard Railway :
- "Add Volume" → monter sur `/app/data`
- Modifier la commande de démarrage :
  `python agrisage_conseil_server.py --port $PORT --db /app/data/onssa_index.db`

Puis uploader onssa_index.db via la CLI Railway :
```bash
npm install -g @railway/cli
railway login
railway run -- python -c "import shutil; shutil.copy('onssa_index.db', '/app/data/onssa_index.db')"
```

### 3. Variables d'environnement
Dans Railway Dashboard → Variables :
```
PORT=3000          (auto-injecté par Railway)
PYTHON_VERSION=3.12
```

### 4. Domaine
Railway génère automatiquement : `agrisage-production.up.railway.app`
Pour agrisage.ma : Settings → Custom Domain

## Tarifs Railway
- Hobby plan : 5$/mois — 512 MB RAM, suffisant pour l'API
- Pro plan : 20$/mois — pour la production

## Alternative : Render.com
Si Railway ne convient pas, Render est identique avec plan gratuit (cold start 30s).
