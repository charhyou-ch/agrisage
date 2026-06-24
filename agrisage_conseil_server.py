#!/usr/bin/env python3
"""
AgriSage API — Serveur Python stdlib uniquement
Version complète avec gestion des clés API, dashboard, documentation

Endpoints publics :
  GET  /health               — Statut serveur
  GET  /docs                 — Documentation interactive HTML

Endpoints API (Bearer token requis) :
  POST /v1/conseil           — Conseil phytosanitaire
  GET  /v1/produits          — Liste produits ONSSA
  GET  /v1/produits/{id}     — Détail produit
  GET  /v1/cultures          — Liste cultures
  GET  /v1/groupes           — Référentiels IRAC/FRAC/HRAC

Endpoints admin (clé admin requise) :
  POST /admin/keys           — Créer une clé API client
  GET  /admin/keys           — Lister toutes les clés
  GET  /admin/stats          — Statistiques d'utilisation
  POST /admin/keys/{id}/revoke — Révoquer une clé

Usage : python agrisage_conseil_server.py --port 3000 --db onssa_index.db
"""
import json, os, random, re, secrets, hashlib, sqlite3, string, sys, argparse
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

SDK_VERSION  = '1.0.0'
API_VERSION  = 'v1'
DEFAULT_PORT = 3000
DB_PATH      = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'onssa_index.db')

# Clé admin — à changer en production via variable d'environnement
ADMIN_KEY = os.environ.get('AGRISAGE_ADMIN_KEY', 'admin_agrisage_2025_changez_moi')

# ── FRAC / IRAC / HRAC ───────────────────────────────────────────────────────

FRAC_DB = {
    '1':  {'groupe':'1',  'type':'frac','nom':'MBC — Méthyl Benzimidazole Carbamates','mecanisme':'Inhibition de la polymérisation de la tubuline (B1)','risque_resistance':'élevé','classes_chimiques':['benzimidazoles','thiophanates'],'matieres_actives':['benomyl','carbendazim','fuberidazole','thiabendazole','thiophanate-methyl'],'recommandation':'Max 2 applications/saison. Alterner avec groupes 2, 9, 12.'},
    '2':  {'groupe':'2',  'type':'frac','nom':'Dicarboximides','mecanisme':'Inhibition transduction signal osmotique (E3)','risque_resistance':'modéré','classes_chimiques':['dicarboximides'],'matieres_actives':['iprodione','procymidone','vinclozolin','chlozolinate','dimethachlone'],'recommandation':'Max 2 applications/saison. Alterner avec groupes 9, 11, 12.'},
    '3':  {'groupe':'3',  'type':'frac','nom':'DMI — Inhibiteurs de la Déméthylation (SBI Classe I)','mecanisme':'Inhibition C14-déméthylase dans biosynthèse stérols (G1)','risque_resistance':'modéré','classes_chimiques':['triazoles','imidazoles','pyrimidines','piperazines'],'matieres_actives':['tebuconazole','difenoconazole','propiconazole','cyproconazole','penconazole','myclobutanil','metconazole','flusilazole','flutriafol','hexaconazole','bitertanol','triadimefon','triadimenol','triticonazole','epoxiconazole','fenbuconazole','fluquinconazole','mefentrifluconazole','prothioconazole','imazalil','prochloraz','triflumizole'],'recommandation':'Max 2 applications consécutives. Alterner avec groupes 7, 9, 11.'},
    '4':  {'groupe':'4',  'type':'frac','nom':'PA-fungicides — Phényl-Amides','mecanisme':'Inhibition polymérase ARN I (A1)','risque_resistance':'très élevé','classes_chimiques':['acylalanines','butyrolactones','oxazolidinones'],'matieres_actives':['metalaxyl','metalaxyl-m','benalaxyl','benalaxyl-m','furalaxyl','ofurace','oxadixyl'],'recommandation':'RISQUE TRÈS ÉLEVÉ. Max 1 application/saison. Toujours en mélange avec M3 ou M5.'},
    '5':  {'groupe':'5',  'type':'frac','nom':'Morpholines / Amines (SBI Classe II)','mecanisme':'Inhibition Δ14-réductase et Δ8→Δ7-isomérase biosynthèse stérols (G2)','risque_resistance':'modéré','classes_chimiques':['morpholines','piperidines','spiroketal-amines'],'matieres_actives':['fenpropimorph','tridemorph','aldimorph','dodemorph','fenpropidin','spiroxamine'],'recommandation':'Alterner avec groupes 3 ou 7. Max 3 applications/saison.'},
    '7':  {'groupe':'7',  'type':'frac','nom':'SDHI — Inhibiteurs de la Succinate Déshydrogénase','mecanisme':'Inhibition complexe II chaîne respiratoire mitochondriale (C2)','risque_resistance':'modéré','classes_chimiques':['pyrazole-4-carboxamides','pyridinecarboxamides','phenyl-benzamides','oxathiin-carboxamides'],'matieres_actives':['boscalid','fluopyram','fluxapyroxad','bixafen','isopyrazam','penflufen','penthiopyrad','sedaxane','benzovindiflupyr','fluindapyr','furametpyr','inpyrfluxam','isoflucypram','pydiflumetofen','pyraziflumid','thifluzamide','cyclobutrifluram','isofetamid','carboxin','oxycarboxin','fenfuram','flutolanil','mepronil','benodanil'],'recommandation':'Max 2 applications/saison. Alterner avec groupes 3, 11.'},
    '9':  {'groupe':'9',  'type':'frac','nom':'AP-fungicides — Anilino-Pyrimidines','mecanisme':'Inhibition biosynthèse méthionine (gène cgs) (D1)','risque_resistance':'modéré','classes_chimiques':['anilino-pyrimidines'],'matieres_actives':['cyprodinil','pyrimethanil','mepanipyrim'],'recommandation':'Max 2 applications/saison. Alterner avec groupes 2, 7, 12.'},
    '11': {'groupe':'11', 'type':'frac','nom':'QoI — Strobilurines','mecanisme':'Inhibition complexe III cytochrome bc1 site Qo (C3)','risque_resistance':'élevé','classes_chimiques':['methoxy-acrylates','oximino-acetamides','methoxy-carbamates'],'matieres_actives':['azoxystrobine','trifloxystrobine','pyraclostrobine','kresoxim-methyl','picoxystrobine','dimoxystrobine','fluoxastrobin','orysastrobin','metominostrobin','famoxadone','pyribencarb'],'recommandation':'RISQUE ÉLEVÉ. Max 1-2 applications/saison. Alterner avec groupes 3, 7, 9.'},
    '12': {'groupe':'12', 'type':'frac','nom':'PP-fungicides — Phénylpyrroles','mecanisme':'Inhibition transduction signal osmotique MAP/histidine-kinase os-2 (E2)','risque_resistance':'faible','classes_chimiques':['phenylpyrroles'],'matieres_actives':['fludioxonil','fenpiclonil'],'recommandation':'Faible risque. Max 2 applications/saison.'},
    '17': {'groupe':'17', 'type':'frac','nom':'KRI — Inhibiteurs de la Kétoréductase (SBI Classe III)','mecanisme':'Inhibition 3-kéto-réductase dans C4-déméthylation (G3)','risque_resistance':'faible','classes_chimiques':['hydroxyanilides','amino-pyrazolinones'],'matieres_actives':['fenhexamid','fenpyrazamine'],'recommandation':'Spécifique Botrytis et Monilinia. Max 2 applications/saison.'},
    '27': {'groupe':'27', 'type':'frac','nom':'Cyanoacétamide-oximes','mecanisme':'Mécanisme inconnu (U)','risque_resistance':'modéré','classes_chimiques':['cyanoacetamide-oximes'],'matieres_actives':['cymoxanil'],'recommandation':'Toujours utilisé en mélange. Bon partenaire anti-résistance.'},
    '40': {'groupe':'40', 'type':'frac','nom':'CAA — Acides Carboxyliques Amides','mecanisme':'Inhibition cellulose synthase CesA3 (H5)','risque_resistance':'modéré','classes_chimiques':['cinnamic acid amides','mandelic acid amides','valinamide carbamates'],'matieres_actives':['dimethomorph','flumorph','mandipropamid','iprovalicarb','benthiavalicarb','pyrimorph','valifenalate'],'recommandation':'Spécifique Oomycètes. Alterner avec groupes 4, 27, M3.'},
    '49': {'groupe':'49', 'type':'frac','nom':'OSBPI — Inhibiteurs homologue liaison oxystérols','mecanisme':'Inhibition transport et stockage lipides (F9)','risque_resistance':'faible','classes_chimiques':['piperidyl-thiazole-isoxazoline'],'matieres_actives':['oxathiapiprolin','fluoxapiproline'],'recommandation':'Nouveau mode action anti-Oomycètes. Excellent choix en rotation.'},
    'M3': {'groupe':'M3','type':'frac','nom':'Dithiocarbamates & relatifs','mecanisme':'Activité multi-site — inhibition enzymes par liaisons electrophiles','risque_resistance':'faible','classes_chimiques':['dithiocarbamates','thiurams'],'matieres_actives':['mancozebe','maneb','zineb','propineb','thiram','metiram','ziram'],'recommandation':'Contact multi-site. Rotation libre. Excellent partenaire tank-mix.'},
    'M4': {'groupe':'M4','type':'frac','nom':'Phthalimides','mecanisme':'Activité multi-site — inhibition respiration cellulaire (électrophile)','risque_resistance':'faible','classes_chimiques':['phthalimides'],'matieres_actives':['captan','folpet','captafol'],'recommandation':'Contact multi-site. Rotation libre. Préventif uniquement.'},
    'M5': {'groupe':'M5','type':'frac','nom':'Chloronitriles','mecanisme':'Activité multi-site non spécifiée','risque_resistance':'faible','classes_chimiques':['chloronitriles'],'matieres_actives':['chlorothalonil'],'recommandation':'Contact multi-site. Rotation libre. Préventif uniquement.'},
    'U6': {'groupe':'U6','type':'frac','nom':'Phényl-acétamides','mecanisme':'Mécanisme inconnu — probablement inhibiteurs cétol-réductases','risque_resistance':'faible','classes_chimiques':['phenyl-acetamides'],'matieres_actives':['cyflufenamid'],'recommandation':'Spécifique oïdium. Alterner avec groupe 3.'},
}

IRAC_DB = {
    '1A': {'groupe':'1A','type':'irac','nom':'Inhibiteurs AChE — Carbamates','mecanisme':'Inhibition acétylcholinestérase','risque_resistance':'élevé','classes_chimiques':['carbamates'],'matieres_actives':['carbofuran','methomyl','carbosulfan','pirimicarb','carbaryl','thiodicarb'],'recommandation':'Alterner avec groupes 3A, 4A, 28.'},
    '1B': {'groupe':'1B','type':'irac','nom':'Inhibiteurs AChE — Organophosphorés','mecanisme':'Inhibition acétylcholinestérase','risque_resistance':'élevé','classes_chimiques':['organophosphores'],'matieres_actives':['chlorpyrifos','acephate','dimethoate','malathion','profenofos'],'recommandation':'Alterner avec groupes 3A, 4A, 28.'},
    '3A': {'groupe':'3A','type':'irac','nom':'Pyréthrines & Pyréthrinoïdes','mecanisme':'Modulation canaux sodiques voltage-dépendants','risque_resistance':'élevé','classes_chimiques':['pyrethrinoïdes','pyréthrines naturelles'],'matieres_actives':['deltamethrine','lambda-cyhalothrine','alpha-cypermethrine','cypermethrine','bifenthrine','esfenvalerate','tefluthrine','permethrine','etofenprox'],'recommandation':'RISQUE ÉLEVÉ. Max 1-2 applications/saison. Alterner avec 4A, 5, 28. Très dangereux abeilles.'},
    '4A': {'groupe':'4A','type':'irac','nom':'Néonicotinoïdes','mecanisme':'Agonistes compétitifs récepteurs nicotiniques acétylcholine (nAChR)','risque_resistance':'élevé','classes_chimiques':['neonicotinoïdes'],'matieres_actives':['imidaclopride','thiaméthoxame','acetamipride','clothianidine','nitenpyrame','thiaclopride','dinotefurane'],'recommandation':'RISQUE TRÈS ÉLEVÉ. Max 1 application/saison. Très dangereux abeilles.'},
    '4C': {'groupe':'4C','type':'irac','nom':'Sulfoximines','mecanisme':'Agonistes compétitifs récepteurs nAChR','risque_resistance':'modéré','classes_chimiques':['sulfoximines'],'matieres_actives':['sulfoxaflor'],'recommandation':'Alterner avec groupes 3A, 5, 28.'},
    '4D': {'groupe':'4D','type':'irac','nom':'Buténolides','mecanisme':'Agonistes récepteurs nAChR','risque_resistance':'modéré','classes_chimiques':['butenolides'],'matieres_actives':['flupyradifurone'],'recommandation':'Alternative néonicotinoïdes. Alterner avec 3A, 5, 28.'},
    '5':  {'groupe':'5', 'type':'irac','nom':'Spinosynes','mecanisme':'Modulateurs allostériques récepteurs nAChR (site I)','risque_resistance':'faible','classes_chimiques':['spinosynes'],'matieres_actives':['spinosad','spinetoram'],'recommandation':'Faible risque. Max 2 applications/saison. Risque modéré abeilles.'},
    '6':  {'groupe':'6', 'type':'irac','nom':'Avermectines & Milbémycines','mecanisme':'Activation allostérique canaux chlorure glutamate-dépendants (GluCl)','risque_resistance':'modéré','classes_chimiques':['avermectines','milbemycines'],'matieres_actives':['abamectine','emamectine','milbemectine','lepimectine'],'recommandation':'Max 2 applications/saison. Alterner avec 5, 23, 28.'},
    '7C': {'groupe':'7C','type':'irac','nom':'Pyriproxyfène — Mimétique hormone juvénile','mecanisme':'Mimétique hormone juvénile','risque_resistance':'faible','classes_chimiques':['analogues hormone juvénile'],'matieres_actives':['pyriproxyfene'],'recommandation':'Faible risque. Efficace aleurodes, cochenilles. Rotation libre.'},
    '10B':{'groupe':'10B','type':'irac','nom':'Etoxazole — Inhibiteur biosynthèse chitine acariens','mecanisme':'Inhibition CHS1 (chitine synthase 1)','risque_resistance':'faible','classes_chimiques':['diphenyl oxazoline'],'matieres_actives':['etoxazole'],'recommandation':'Spécifique acariens. Max 1 application/saison.'},
    '23': {'groupe':'23','type':'irac','nom':'Inhibiteurs Acetyl-CoA carboxylase — Tétroniques & Tétramiques','mecanisme':'Inhibition Acetyl-CoA carboxylase (ACCase)','risque_resistance':'faible','classes_chimiques':['acides tétroniques','acides tétramiques'],'matieres_actives':['spirodiclofen','spiromesifen','spirotetramat','spiropidion'],'recommandation':'Faible risque. Efficace acariens et pucerons.'},
    '28': {'groupe':'28','type':'irac','nom':'Diamides — Modulateurs Récepteur Ryanodine','mecanisme':'Modulation récepteurs ryanodine (canaux calcium)','risque_resistance':'faible','classes_chimiques':['diamides anthranilamides','diamides phthalamides'],'matieres_actives':['chlorantraniliprole','cyantraniliprole','flubendiamide','cyclaniliprole','tetraniliprole'],'recommandation':'EXCELLENT CHOIX anti-résistance. Max 2 applications/saison. Très faible toxicité abeilles.'},
    '29': {'groupe':'29','type':'irac','nom':'Flonicamide — Modulateur organes chordotonaux','mecanisme':'Modulation organes chordotonaux','risque_resistance':'faible','classes_chimiques':['acides tétroniques fluorés'],'matieres_actives':['flonicamide'],'recommandation':'Spécifique pucerons et aleurodes. Faible risque.'},
}

HRAC_DB = {
    '1':  {'groupe':'1', 'type':'hrac','legacy':'A', 'nom':'Inhibiteurs ACCase','mecanisme':'Inhibition Acetyl-CoA Carboxylase — blocage biosynthèse acides gras','risque_resistance':'élevé','classes_chimiques':['cyclohexanediones (DIMs)','aryloxyphenoxypropionates (FOPs)'],'matieres_actives':['clethodim','cycloxydim','sethoxydim','clodinafop-propargyl','cyhalofop-butyl','fenoxaprop-ethyl','fluazifop-butyl','haloxyfop-methyl','quizalofop-ethyl','pinoxaden'],'recommandation':'Spécifique graminées. Alterner avec groupe 2. Résistance fréquente.'},
    '2':  {'groupe':'2', 'type':'hrac','legacy':'B', 'nom':'Inhibiteurs ALS','mecanisme':'Inhibition Acétolactate Synthase — blocage biosynthèse acides aminés ramifiés','risque_resistance':'élevé','classes_chimiques':['sulfonylurées','imidazolinones','triazolopyrimidines'],'matieres_actives':['metsulfuron-methyl','chlorsulfuron','nicosulfuron','rimsulfuron','mesosulfuron-methyl','florasulam','imazamox','imazethapyr','imazapyr'],'recommandation':'RISQUE ÉLEVÉ. Max 1 application/saison. Alterner avec groupes 1, 10, 15.'},
    '3':  {'groupe':'3', 'type':'hrac','legacy':'K1','nom':'Inhibiteurs assemblage microtubules (α-Tubuline)','mecanisme':'Inhibition polymérisation tubuline alpha','risque_resistance':'modéré','classes_chimiques':['dinitroanilines','phosphoroamidates'],'matieres_actives':['trifluralin','pendimethalin','ethalfluralin','benefin','prodiamine','dithiopyr'],'recommandation':'Préemergence uniquement. Alterner avec groupes 15, 9.'},
    '4':  {'groupe':'4', 'type':'hrac','legacy':'O', 'nom':'Auxin Mimics — Herbicides Auxiniques','mecanisme':'Mimétisme auxine — perturbation croissance cellulaire','risque_resistance':'modéré','classes_chimiques':['phenoxycarboxylates','pyridyloxycarboxylates','6-arylpicolinates','benzoates'],'matieres_actives':['2,4-D','MCPA','dichlorprop','mecoprop','triclopyr','fluroxypyr','clopyralid','picloram','aminopyralid','halauxifen','dicamba','quinclorac'],'recommandation':'Spécifique dicotylédones. Attention dérive sur cultures sensibles.'},
    '5':  {'groupe':'5', 'type':'hrac','legacy':'C1,2','nom':'Inhibiteurs photosynthèse PS II — Sérine 264','mecanisme':'Blocage transfert électrons au niveau protéine D1 (liaison sérine 264)','risque_resistance':'élevé','classes_chimiques':['triazines','urées','triazinones'],'matieres_actives':['atrazine','simazine','terbuthylazine','diuron','linuron','isoproturon','chlorotoluron','metribuzin','metamitron','hexazinone'],'recommandation':'Résistance très répandue. Alterner avec groupes 4, 9, 15.'},
    '9':  {'groupe':'9', 'type':'hrac','legacy':'G', 'nom':'Inhibiteurs EPSPS (Glyphosate)','mecanisme':'Inhibition énolpyruvyl shikimate phosphate synthase — blocage voie shikimate','risque_resistance':'élevé','classes_chimiques':['acides phosphoniques'],'matieres_actives':['glyphosate'],'recommandation':'Herbicide total. Résistances en forte progression mondiale.'},
    '14': {'groupe':'14','type':'hrac','legacy':'E', 'nom':'Inhibiteurs PPO','mecanisme':'Inhibition Protoporphyrinogène Oxydase — accumulation protoporphyrine IX, génération ROS','risque_resistance':'modéré','classes_chimiques':['N-phénylimides','diphényl-éthers','N-phényltriazolinones'],'matieres_actives':['fomesafen','acifluorfen','lactofen','oxyfluorfen','carfentrazone-ethyl','sulfentrazone','flumioxazin','saflufenacil','tiafenacil','oxadiargyl','oxadiazon'],'recommandation':'Alterner avec groupes 2, 5, 9.'},
    '15': {'groupe':'15','type':'hrac','legacy':'K3','nom':'Inhibiteurs VLCFA','mecanisme':'Inhibition élongase — blocage biosynthèse acides gras très longue chaîne','risque_resistance':'modéré','classes_chimiques':['α-chloroacétamides','α-thioacétamides','thiocarbamates'],'matieres_actives':['metolachlor','acetochlor','alachlor','dimethenamid','pretilachlor','butachlor','flufenacet','pyroxasulfone','prosulfocarb','thiobencarb','triallate','EPTC','molinate'],'recommandation':'Préemergence principalement. Alterner avec groupes 2, 9.'},
    '27': {'groupe':'27','type':'hrac','legacy':'F2','nom':'Inhibiteurs HPPD','mecanisme':'Inhibition HPPD — blocage biosynthèse tocophérol et plastoquinone','risque_resistance':'faible','classes_chimiques':['triketones','pyrazoles','isoxazoles'],'matieres_actives':['mesotrione','tembotrione','sulcotrione','tefuryltrione','bicyclopyrone','pyrasulfotole','topramezone','isoxaflutole'],'recommandation':'Faible risque de résistance. Bon choix en rotation.'},
}

# ── Utilitaires conseil ──────────────────────────────────────────────────────

def get_ma_base(ma):
    if not ma: return ''
    ma = re.sub(r'\s*[\(\[]\d[^\)\]]*[\)\]]', '', ma)
    ma = re.sub(r'\s*\(.*?\)', '', ma)
    return ma.strip().lower()

def get_frac(ma):
    base = get_ma_base(ma)
    for g, info in FRAC_DB.items():
        for active in info['matieres_actives']:
            if active.lower() in base or base in active.lower():
                return {'groupe': g, 'risque_resistance': info['risque_resistance'],
                        'mecanisme': info['mecanisme'], 'recommandation': info['recommandation']}
    return None

def get_irac(ma):
    base = get_ma_base(ma)
    for g, info in IRAC_DB.items():
        for active in info['matieres_actives']:
            if active.lower() in base or base in active.lower():
                return {'groupe': g, 'risque_resistance': info['risque_resistance'],
                        'mecanisme': info['mecanisme'], 'recommandation': info['recommandation']}
    return None

def get_risque_abeilles(ma):
    base = get_ma_base(ma)
    TOXICITE = {
        'lambda cyhalothrine':'élevé','cyperméthrine':'élevé','deltamethrine':'élevé',
        'alpha-cyperméthrine':'élevé','bifenthrine':'élevé',
        'imidaclopride':'élevé','thiamétoxame':'élevé','clothianidine':'élevé',
        'acetamipride':'modéré','spinosad':'modéré','abamectine':'modéré','spirotétramat':'modéré',
        'chlorantraniliprole':'très faible','chloranthraniliprole':'très faible',
        'pyriproxyfène':'faible','etoxazole':'faible','flonicamide':'faible',
        'azoxystrobine':'faible','cyprodinil':'faible','fludioxonil':'faible',
        'difénoconazole':'faible','tebuconazole':'faible','mancozebe':'faible','mancozèbe':'faible',
        'boscalid':'faible','fluopyram':'faible','cymoxanil':'faible',
    }
    for k, v in TOXICITE.items():
        if k in base: return v
    return 'faible'

def conseil_id():
    return 'c_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def enrich_produit(p):
    ma   = p.get('matiere_active', '')
    frac = get_frac(ma); irac = get_irac(ma)
    p['groupe_frac']       = frac['groupe'] if frac else None
    p['groupe_irac']       = irac['groupe'] if irac else None
    p['risque_abeilles']   = get_risque_abeilles(ma)
    p['risque_resistance'] = (frac or irac or {}).get('risque_resistance')
    return p

PAGE_SIZE = 50
STADES_VALIDES = {'germination','levee','vegetation','floraison','fructification','recolte','post-recolte'}

# ── Gestion des clés API ─────────────────────────────────────────────────────

def init_keys_db():
    """Crée la table api_keys dans la base principale si elle n'existe pas."""
    conn = db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash    TEXT UNIQUE NOT NULL,
            key_prefix  TEXT NOT NULL,
            client_name TEXT NOT NULL,
            client_email TEXT,
            plan        TEXT DEFAULT 'starter',
            quota_mensuel INTEGER DEFAULT 500,
            requetes_mois INTEGER DEFAULT 0,
            mois_courant  TEXT,
            actif       INTEGER DEFAULT 1,
            date_creation TEXT,
            derniere_utilisation TEXT,
            notes       TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS request_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash    TEXT,
            endpoint    TEXT,
            methode     TEXT,
            status_code INTEGER,
            response_ms INTEGER,
            date_heure  TEXT
        )
    ''')
    conn.commit()
    conn.close()

def generate_api_key(prefix='as_live'):
    """Génère une clé API sécurisée et retourne (clé_en_clair, hash_sha256)."""
    raw = secrets.token_urlsafe(32)
    key = f"{prefix}_{raw}"
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key, key_hash

def create_key(client_name, client_email='', plan='starter', notes=''):
    """Crée une nouvelle clé API pour un client."""
    quotas = {'starter': 500, 'growth': 10000, 'pro': 50000, 'scale': 300000}
    quota  = quotas.get(plan, 500)
    key_clear, key_hash = generate_api_key()
    prefix = key_clear[:15] + '...'  # Affichage sécurisé
    conn = db()
    conn.execute('''
        INSERT INTO api_keys (key_hash, key_prefix, client_name, client_email,
                              plan, quota_mensuel, date_creation, mois_courant, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (key_hash, prefix, client_name, client_email, plan, quota,
          datetime.now().isoformat(), datetime.now().strftime('%Y-%m'), notes))
    conn.commit()
    key_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    return {'id': key_id, 'key': key_clear, 'prefix': prefix, 'plan': plan,
            'quota_mensuel': quota, 'client': client_name}

def validate_key(key_string):
    """Valide une clé API. Retourne le record client ou None."""
    if not key_string:
        return None
    key_hash = hashlib.sha256(key_string.encode()).hexdigest()
    conn = db()
    row = conn.execute(
        'SELECT * FROM api_keys WHERE key_hash=? AND actif=1', (key_hash,)
    ).fetchone()
    if not row:
        conn.close()
        return None
    client = dict(row)

    # Vérifier et réinitialiser le quota mensuel
    mois_now = datetime.now().strftime('%Y-%m')
    if client['mois_courant'] != mois_now:
        conn.execute('UPDATE api_keys SET requetes_mois=0, mois_courant=? WHERE key_hash=?',
                     (mois_now, key_hash))
        client['requetes_mois'] = 0

    # Vérifier quota
    if client['requetes_mois'] >= client['quota_mensuel']:
        conn.close()
        return 'QUOTA_EXCEEDED'

    # Incrémenter compteur
    conn.execute('''
        UPDATE api_keys SET requetes_mois=requetes_mois+1,
        derniere_utilisation=? WHERE key_hash=?
    ''', (datetime.now().isoformat(), key_hash))
    conn.commit()
    conn.close()
    return client

def log_request(key_hash, endpoint, methode, status_code, response_ms):
    """Enregistre un appel API pour les statistiques."""
    try:
        conn = db()
        conn.execute('''
            INSERT INTO request_logs (key_hash, endpoint, methode, status_code, response_ms, date_heure)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (key_hash or 'anonymous', endpoint, methode, status_code,
              response_ms, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception:
        pass  # Ne pas bloquer sur erreur de log

def get_stats():
    """Statistiques d'utilisation globales."""
    conn = db()
    stats = {}
    stats['total_clients']  = conn.execute('SELECT COUNT(*) FROM api_keys WHERE actif=1').fetchone()[0]
    stats['total_requetes'] = conn.execute('SELECT COUNT(*) FROM request_logs').fetchone()[0]
    stats['requetes_aujourd_hui'] = conn.execute(
        "SELECT COUNT(*) FROM request_logs WHERE date_heure LIKE ?",
        (datetime.now().strftime('%Y-%m-%d') + '%',)
    ).fetchone()[0]
    stats['endpoints_populaires'] = [dict(r) for r in conn.execute(
        'SELECT endpoint, COUNT(*) n FROM request_logs GROUP BY endpoint ORDER BY n DESC LIMIT 5'
    ).fetchall()]
    stats['clients'] = [dict(r) for r in conn.execute(
        'SELECT id, key_prefix, client_name, client_email, plan, quota_mensuel, requetes_mois, actif, date_creation, derniere_utilisation FROM api_keys ORDER BY id DESC'
    ).fetchall()]
    conn.close()
    return stats

# ── Moteur conseil ────────────────────────────────────────────────────────────

ROTATION_NOTES = {
    '3':'Alterner avec FRAC 7, 9 ou 27. Max 2 applications/saison.',
    '7':'Alterner avec FRAC 3 ou 11. Max 2 applications/saison.',
    '9':'Alterner avec FRAC 3 ou 40. Max 2 applications/saison.',
    '11':'Risque élevé. Max 1 application consécutive. Alterner avec FRAC 3 ou 7.',
    '4':'Risque TRES ELEVE. Max 1 application/saison. Toujours en mélange.',
    '27':'Bon choix anti-résistance strobilurines. Alterner avec FRAC 40.',
    '40':'Alterner avec FRAC 27 ou M3.',
    'M3':'Contact multi-site. Rotation libre. Excellent tank-mix.',
    '28':'Bon choix anti-résistance. Max 2 applications/saison.',
    '3A':'Risque élevé. Alterner avec IRAC 5, 6 ou 28.',
    '4A':'Risque très élevé. Alterner avec IRAC 5 ou 28.',
    '6':'Alterner avec IRAC 28 ou 5. Max 2 applications/saison.',
}

def generer_conseil(params):
    culture   = params.get('culture', '').strip()
    ravageur  = params.get('ravageur', '').strip()
    stade     = params.get('stade', '').strip().lower()
    dar_max   = params.get('dar_max')
    hist_frac = params.get('historique_frac') or []
    hist_irac = params.get('historique_irac') or []
    nb_alt    = int(params.get('nb_alternatives', 2))
    cl = culture.lower(); rl = ravageur.lower() if ravageur else None
    conn = db(); cur = conn.cursor()
    sql  = '''SELECT p.id, p.nom_commercial, p.numero_homologation, p.detenteur,
                     p.categorie, p.type_produit, p.formulation, p.matiere_active,
                     p.valable_jusquau, p.tableau_toxicologique,
                     u.usage_desc, u.culture AS usage_culture,
                     u.dose, u.dar_raw, u.dar_jours, u.nb_applications
              FROM produits p JOIN usages u ON p.id = u.produit_id
              WHERE LOWER(u.culture) LIKE ?'''
    args = ['%' + cl + '%']
    if rl: sql += ' AND LOWER(u.usage_desc) LIKE ?'; args.append('%' + rl + '%')
    if dar_max is not None: sql += ' AND (u.dar_jours IS NULL OR u.dar_jours <= ?)'; args.append(int(dar_max))
    sql += ' ORDER BY u.dar_jours ASC NULLS LAST LIMIT 80'
    rows = [dict(r) for r in cur.execute(sql, args).fetchall()]
    if not rows and rl:
        sql2 = sql.replace(' AND LOWER(u.usage_desc) LIKE ?', '').replace('LIMIT 80','LIMIT 20')
        args2 = ['%' + cl + '%']
        if dar_max is not None: args2.append(int(dar_max))
        rows = [dict(r) for r in cur.execute(sql2, args2).fetchall()]
    conn.close()
    if not rows: raise ValueError("Aucun produit homologue ONSSA pour '" + culture + "'")
    for r in rows:
        ma = r.get('matiere_active',''); frac = get_frac(ma); irac = get_irac(ma); ra = get_risque_abeilles(ma)
        tox = r.get('tableau_toxicologique',''); score = 100
        if frac and frac['groupe'] in hist_frac: score -= 60
        if irac and irac['groupe'] in hist_irac: score -= 60
        if ra == 'élevé'  and stade == 'floraison': score -= 45
        if ra == 'modéré' and stade == 'floraison': score -= 20
        if tox == 'Ia': score -= 30
        if tox == 'Ib': score -= 15
        if frac and frac['groupe'] not in hist_frac: score += 10
        if ra == 'très faible': score += 12
        elif ra == 'faible': score += 6
        d = r.get('dar_jours')
        if d and d <= 3: score += 5
        r.update({'_s':score,'_f':frac,'_i':irac,'_ra':ra})
    rows.sort(key=lambda x: -x['_s']); best = rows[0]
    alertes = []
    if stade == 'floraison':
        ra = best['_ra']
        if   ra == 'élevé':  alertes.append('DANGEREUX abeilles. Application interdite en floraison.')
        elif ra == 'modéré': alertes.append('Risque modéré pollinisateurs. Appliquer après 19h.')
        else:                alertes.append('Floraison : appliquer de préférence après 19h.')
    if best['_f'] and best['_f']['groupe'] in hist_frac:
        alertes.append('FRAC ' + best['_f']['groupe'] + ' deja utilise. Risque resistance.')
    if best['_i'] and best['_i']['groupe'] in hist_irac:
        alertes.append('IRAC ' + best['_i']['groupe'] + ' deja utilise. Risque resistance.')
    if best.get('tableau_toxicologique') in ('Ia','Ib'):
        alertes.append('Toxicite classe ' + str(best.get('tableau_toxicologique')) + ' - EPI obligatoires.')
    best_fg = best['_f']['groupe'] if best['_f'] else None
    best_ig = best['_i']['groupe'] if best['_i'] else None
    seen = {best['id']}; alts = []
    for r in rows[1:]:
        if r['id'] in seen or len(alts) >= nb_alt: break
        r_fg = r['_f']['groupe'] if r['_f'] else None
        r_ig = r['_i']['groupe'] if r['_i'] else None
        if r_fg != best_fg or r_ig != best_ig:
            alts.append({'produit':r['nom_commercial'],'matiere_active':r['matiere_active'],
                         'groupe_frac':r_fg,'groupe_irac':r_ig,'dar':r.get('dar_jours'),'dose':r.get('dose')})
            seen.add(r['id'])
    rot = ROTATION_NOTES.get(best['_f']['groupe'] if best['_f'] else '') or \
          ROTATION_NOTES.get(best['_i']['groupe'] if best['_i'] else '')
    return {
        'conseil_id': conseil_id(), 'produit': best['nom_commercial'],
        'matiere_active': best['matiere_active'], 'numero_amm': best.get('numero_homologation'),
        'detenteur': best.get('detenteur'), 'dose': best.get('dose'), 'dar': best.get('dar_jours'),
        'dar_raw': best.get('dar_raw'), 'nb_applications': best.get('nb_applications'),
        'formulation': best.get('formulation'), 'categorie': best.get('categorie'),
        'type_produit': best.get('type_produit'), 'usage_homologue': best.get('usage_desc'),
        'culture_homologuee': best.get('usage_culture'),
        'groupe_frac': best['_f']['groupe'] if best['_f'] else None,
        'groupe_irac': best['_i']['groupe'] if best['_i'] else None,
        'groupe_hrac': None,
        'risque_resistance': (best['_f'] or best['_i'] or {}).get('risque_resistance'),
        'mecanisme_action':  (best['_f'] or best['_i'] or {}).get('mecanisme'),
        'rotation_note': rot, 'homologue_onssa': True,
        'valable_jusquau': best.get('valable_jusquau'),
        'tableau_toxicologique': best.get('tableau_toxicologique'),
        'risque_abeilles': best['_ra'], 'risque_auxiliaires': 'faible',
        'alertes': alertes, 'alternatives': alts,
        'meta': {'culture_demandee':culture,'ravageur_demande':ravageur,'stade':stade,
                 'dar_max_demande':dar_max,'nb_produits_trouves':len(rows),'score_principal':best['_s']},
        'timestamp': datetime.now().isoformat(),
    }

# ── GET /produits ─────────────────────────────────────────────────────────────

def get_produits(qs):
    culture=qs.get('culture',[None])[0]; usage=qs.get('usage',[None])[0]
    ma=qs.get('ma',[None])[0]; groupe_frac=qs.get('groupe_frac',[None])[0]
    groupe_irac=qs.get('groupe_irac',[None])[0]; q=qs.get('q',[None])[0]
    try: page=max(1,int(qs.get('page',['1'])[0]))
    except: page=1
    conn=db(); cur=conn.cursor()
    sql_select='SELECT DISTINCT p.id, p.nom_commercial, p.detenteur, p.fournisseur, p.numero_homologation, p.valable_jusquau, p.tableau_toxicologique, p.categorie, p.type_produit, p.formulation, p.matiere_active, p.teneur FROM produits p'
    sql_where='WHERE 1=1'; args=[]
    needs_join=bool(culture or groupe_frac or groupe_irac)
    if needs_join: sql_select+=' LEFT JOIN usages u ON p.id = u.produit_id'
    if culture: sql_where+=' AND LOWER(u.culture) LIKE ?'; args.append('%'+culture.lower()+'%')
    if usage:   sql_where+=' AND p.type_produit LIKE ?'; args.append('%'+usage.lower()+'%')
    if ma:      sql_where+=' AND LOWER(p.matiere_active) LIKE ?'; args.append('%'+ma.lower()+'%')
    if q:
        sql_where+=' AND (LOWER(p.nom_commercial) LIKE ? OR LOWER(p.matiere_active) LIKE ?)'
        args.extend(['%'+q.lower()+'%','%'+q.lower()+'%'])
    if groupe_frac and groupe_frac in FRAC_DB:
        ma_keys=FRAC_DB[groupe_frac]['matieres_actives']
        if ma_keys:
            sql_where+=' AND ('+' OR '.join(['LOWER(p.matiere_active) LIKE ?']*len(ma_keys))+')'
            args.extend(['%'+k+'%' for k in ma_keys])
    if groupe_irac and groupe_irac in IRAC_DB:
        ma_keys=IRAC_DB[groupe_irac]['matieres_actives']
        if ma_keys:
            sql_where+=' AND ('+' OR '.join(['LOWER(p.matiere_active) LIKE ?']*len(ma_keys))+')'
            args.extend(['%'+k+'%' for k in ma_keys])
    sql_count='SELECT COUNT(DISTINCT p.id) FROM produits p'
    if needs_join: sql_count+=' LEFT JOIN usages u ON p.id = u.produit_id'
    sql_count+=' '+sql_where
    total=cur.execute(sql_count,args).fetchone()[0]
    offset=(page-1)*PAGE_SIZE
    rows=[dict(r) for r in cur.execute(sql_select+' '+sql_where+' ORDER BY p.nom_commercial ASC LIMIT ? OFFSET ?',args+[PAGE_SIZE,offset]).fetchall()]
    for p in rows:
        enrich_produit(p)
        cr=cur.execute('SELECT DISTINCT culture FROM usages WHERE produit_id=? AND culture != "" ORDER BY culture LIMIT 20',(p['id'],)).fetchall()
        p['cultures_homologuees']=[r['culture'] for r in cr]
        dr=cur.execute('SELECT MIN(dar_jours) dar_min, MAX(dar_jours) dar_max FROM usages WHERE produit_id=? AND dar_jours IS NOT NULL',(p['id'],)).fetchone()
        p['dar_min']=dr['dar_min'] if dr else None; p['dar_max']=dr['dar_max'] if dr else None
    conn.close()
    pages_total=max(1,(total+PAGE_SIZE-1)//PAGE_SIZE)
    return {'data':rows,'pagination':{'page':page,'par_page':PAGE_SIZE,'total':total,'pages_total':pages_total}}

def get_produit_by_id(produit_id):
    conn=db(); cur=conn.cursor()
    row=cur.execute('SELECT * FROM produits WHERE id = ?',(produit_id,)).fetchone()
    if not row: conn.close(); return None
    p=dict(row); enrich_produit(p)
    usages=[dict(r) for r in cur.execute('SELECT culture, usage_desc, dose, dar_raw, dar_jours, nb_applications FROM usages WHERE produit_id=? ORDER BY culture',(produit_id,)).fetchall()]
    p['usages']=usages; p['cultures_homologuees']=sorted({u['culture'] for u in usages if u['culture']})
    frac=get_frac(p.get('matiere_active','')); irac=get_irac(p.get('matiere_active',''))
    if frac: p['frac_info']=frac
    if irac: p['irac_info']=irac
    conn.close(); return p

def get_cultures(qs):
    q=qs.get('q',[None])[0]
    try: page=max(1,int(qs.get('page',['1'])[0]))
    except: page=1
    conn=db(); cur=conn.cursor()
    sql_where="WHERE nom_fr != ''"; args=[]
    if q: sql_where+=' AND LOWER(nom_fr) LIKE ?'; args.append('%'+q.lower()+'%')
    total=cur.execute('SELECT COUNT(*) FROM cultures '+sql_where,args).fetchone()[0]
    offset=(page-1)*PAGE_SIZE
    rows=[dict(r) for r in cur.execute('SELECT id, nom_fr, nb_produits FROM cultures '+sql_where+' ORDER BY nb_produits DESC, nom_fr ASC LIMIT ? OFFSET ?',args+[PAGE_SIZE,offset]).fetchall()]
    conn.close()
    pages_total=max(1,(total+PAGE_SIZE-1)//PAGE_SIZE)
    return {'data':rows,'total':total,'pagination':{'page':page,'par_page':PAGE_SIZE,'total':total,'pages_total':pages_total}}

def get_groupes(qs):
    type_g=qs.get('type',[None])[0]; groupe=qs.get('groupe',[None])[0]
    ma=qs.get('ma',[None])[0]; risque=qs.get('risque',[None])[0]
    if not type_g or type_g.lower() not in ('frac','irac','hrac'):
        raise ValueError("Parametre 'type' requis : frac | irac | hrac")
    type_g=type_g.lower()
    source={'frac':FRAC_DB,'irac':IRAC_DB,'hrac':HRAC_DB}[type_g]
    results=[]
    for g_id, info in source.items():
        if groupe and g_id.upper()!=groupe.upper(): continue
        if risque and info.get('risque_resistance','').lower()!=risque.lower(): continue
        if ma:
            ml=ma.lower()
            if not any(ml in a.lower() or a.lower() in ml for a in info.get('matieres_actives',[])): continue
        item={k:v for k,v in info.items()}
        results.append(item)
    return {'type':type_g,'data':results,'total':len(results)}

# ── Documentation HTML ────────────────────────────────────────────────────────

DOCS_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgriSage API — Documentation</title>
<style>
:root{--green:#27500A;--green-mid:#4A8C2A;--green-light:#6DB842;--cream:#F7FAF3;--amber:#D4820A;--gray:#4A5568}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--cream);color:#1A1A1A}
header{background:var(--green);color:white;padding:24px 40px;display:flex;align-items:center;gap:16px}
header h1{font-size:28px;font-weight:700}
header .badge{background:var(--green-light);color:var(--green);padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600}
.container{max-width:960px;margin:0 auto;padding:40px 24px}
.intro{background:white;border-radius:12px;padding:24px;margin-bottom:32px;border:1px solid #E8F0E0;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.intro p{color:var(--gray);line-height:1.7;margin-bottom:8px}
.base-url{background:var(--green);color:#fff;padding:10px 16px;border-radius:8px;font-family:monospace;font-size:14px;display:inline-block;margin-top:8px}
.section-title{font-size:20px;font-weight:700;color:var(--green);margin:32px 0 16px;border-bottom:2px solid #E8F0E0;padding-bottom:8px}
.endpoint{background:white;border-radius:12px;padding:20px;margin-bottom:16px;border:1px solid #E8F0E0;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.endpoint-header{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.method{padding:4px 10px;border-radius:6px;font-size:12px;font-weight:700;font-family:monospace}
.method.post{background:#FEF3C7;color:#92400E}
.method.get{background:#D1FAE5;color:#065F46}
.path{font-family:monospace;font-size:15px;font-weight:600;color:var(--green)}
.desc{color:var(--gray);font-size:14px;line-height:1.6;margin-bottom:12px}
.params{background:#F8FAFC;border-radius:8px;padding:12px;margin-bottom:12px}
.param-row{display:grid;grid-template-columns:120px 80px 1fr;gap:8px;padding:4px 0;font-size:13px;border-bottom:1px solid #EEF2F7}
.param-row:last-child{border:none}
.param-name{font-family:monospace;color:var(--green-mid);font-weight:600}
.param-type{color:var(--amber);font-size:12px;align-self:center}
.param-desc{color:var(--gray)}
.required{color:#DC2626;font-size:10px;font-weight:700;margin-left:4px}
.try-btn{background:var(--green-light);color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;margin-top:8px}
.try-btn:hover{background:var(--green-mid)}
.try-panel{display:none;background:#1E1E1E;border-radius:8px;padding:16px;margin-top:12px}
.try-panel.open{display:block}
.try-panel label{color:#9CA3AF;font-size:12px;display:block;margin-bottom:4px;margin-top:8px}
.try-panel input,.try-panel textarea,.try-panel select{width:100%;background:#2D2D2D;border:1px solid #444;color:#E5E7EB;padding:8px;border-radius:6px;font-family:monospace;font-size:13px}
.try-panel textarea{min-height:120px;resize:vertical}
.run-btn{background:var(--amber);color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:700;margin-top:12px}
.response-area{background:#0D1117;color:#7EE787;font-family:monospace;font-size:12px;padding:12px;border-radius:6px;max-height:400px;overflow:auto;margin-top:8px;white-space:pre;display:none}
.alert-box{background:#FEF3C7;border:1px solid #FCD34D;border-radius:8px;padding:16px;margin-bottom:16px}
.alert-box p{color:#92400E;font-size:14px}
code{background:#E8F0E0;padding:2px 6px;border-radius:4px;font-family:monospace;font-size:13px;color:var(--green)}
</style>
</head>
<body>
<header>
  <div>
    <h1>🌿 AgriSage API</h1>
    <p style="font-size:13px;opacity:.8;margin-top:4px">Conseil phytosanitaire pour l'agriculture marocaine</p>
  </div>
  <span class="badge">v1.0.0</span>
</header>

<div class="container">
  <div class="intro">
    <p><strong>Base URL :</strong></p>
    <div class="base-url">https://web-production-0e1ad.up.railway.app</div>
    <p style="margin-top:16px">Toutes les requêtes nécessitent un header d'authentification :</p>
    <div class="base-url" style="margin-top:8px">Authorization: Bearer as_test_VOTRE_CLE</div>
    <p style="margin-top:12px">Pour obtenir une clé de production, contactez <strong>api@agrisage.ma</strong></p>
  </div>

  <div class="alert-box">
    <p>⚠️ <strong>Phase beta :</strong> Les clés <code>as_test_demo</code> sont acceptées pour tester. Contactez-nous pour une clé de production.</p>
  </div>

  <div class="section-title">🌱 Conseil phytosanitaire</div>

  <div class="endpoint">
    <div class="endpoint-header">
      <span class="method post">POST</span>
      <span class="path">/v1/conseil</span>
    </div>
    <div class="desc">Génère un conseil phytosanitaire complet. Croise l'index ONSSA, les groupes FRAC/IRAC, la toxicité pour les abeilles et le DAR.</div>
    <div class="params">
      <div class="param-row"><span class="param-name">culture<span class="required">*</span></span><span class="param-type">string</span><span class="param-desc">Culture cible (ex: "tomate", "vigne", "agrumes")</span></div>
      <div class="param-row"><span class="param-name">ravageur<span class="required">*</span></span><span class="param-type">string</span><span class="param-desc">Maladie ou ravageur (ex: "botrytis", "mildiou", "tuta absoluta")</span></div>
      <div class="param-row"><span class="param-name">stade<span class="required">*</span></span><span class="param-type">string</span><span class="param-desc">Stade phénologique : germination | levee | vegetation | floraison | fructification | recolte</span></div>
      <div class="param-row"><span class="param-name">dar_max</span><span class="param-type">integer</span><span class="param-desc">DAR maximum en jours (ex: 7). Filtre les produits trop persistants.</span></div>
      <div class="param-row"><span class="param-name">historique_frac</span><span class="param-type">array</span><span class="param-desc">Groupes FRAC déjà utilisés ce cycle (ex: ["11","3"]). Active la rotation anti-résistance.</span></div>
      <div class="param-row"><span class="param-name">nb_alternatives</span><span class="param-type">integer</span><span class="param-desc">Nombre de produits alternatifs à inclure (0-5, défaut: 2)</span></div>
    </div>
    <button class="try-btn" onclick="toggle('conseil')">▶ Essayer</button>
    <div class="try-panel" id="panel-conseil">
      <label>Body JSON</label>
      <textarea id="body-conseil">{"culture": "tomate", "ravageur": "botrytis", "stade": "floraison", "dar_max": 7, "historique_frac": []}</textarea>
      <label>Clé API</label>
      <input id="key-conseil" value="as_test_demo">
      <button class="run-btn" onclick="run('POST','conseil',null,'conseil')">Envoyer ▶</button>
      <div class="response-area" id="resp-conseil"></div>
    </div>
  </div>

  <div class="section-title">📦 Produits ONSSA</div>

  <div class="endpoint">
    <div class="endpoint-header">
      <span class="method get">GET</span>
      <span class="path">/v1/produits</span>
    </div>
    <div class="desc">Liste les 1 355 produits homologués par l'ONSSA avec filtres et pagination (50 par page).</div>
    <div class="params">
      <div class="param-row"><span class="param-name">culture</span><span class="param-type">string</span><span class="param-desc">Filtre par culture homologuée (ex: "tomate")</span></div>
      <div class="param-row"><span class="param-name">usage</span><span class="param-type">string</span><span class="param-desc">Type de produit : fongicide | insecticide | herbicide | acaricide</span></div>
      <div class="param-row"><span class="param-name">q</span><span class="param-type">string</span><span class="param-desc">Recherche libre sur nom commercial ou matière active</span></div>
      <div class="param-row"><span class="param-name">groupe_frac</span><span class="param-type">string</span><span class="param-desc">Filtrer par groupe FRAC (ex: "11", "9", "M3")</span></div>
      <div class="param-row"><span class="param-name">page</span><span class="param-type">integer</span><span class="param-desc">Numéro de page (défaut: 1)</span></div>
    </div>
    <button class="try-btn" onclick="toggle('produits')">▶ Essayer</button>
    <div class="try-panel" id="panel-produits">
      <label>Paramètres (query string)</label>
      <input id="qs-produits" value="culture=tomate&usage=fongicide">
      <label>Clé API</label>
      <input id="key-produits" value="as_test_demo">
      <button class="run-btn" onclick="run('GET','produits','qs-produits','produits')">Envoyer ▶</button>
      <div class="response-area" id="resp-produits"></div>
    </div>
  </div>

  <div class="endpoint">
    <div class="endpoint-header">
      <span class="method get">GET</span>
      <span class="path">/v1/produits/{id}</span>
    </div>
    <div class="desc">Détail complet d'un produit : tous ses usages homologués, cultures, doses, DAR et informations FRAC/IRAC.</div>
    <button class="try-btn" onclick="toggle('produit-id')">▶ Essayer</button>
    <div class="try-panel" id="panel-produit-id">
      <label>ID du produit</label>
      <input id="qs-produit-id" value="1">
      <label>Clé API</label>
      <input id="key-produit-id" value="as_test_demo">
      <button class="run-btn" onclick="runId()">Envoyer ▶</button>
      <div class="response-area" id="resp-produit-id"></div>
    </div>
  </div>

  <div class="section-title">🌾 Cultures & Référentiels</div>

  <div class="endpoint">
    <div class="endpoint-header">
      <span class="method get">GET</span>
      <span class="path">/v1/cultures</span>
    </div>
    <div class="desc">Liste les 179 cultures présentes dans l'index ONSSA, triées par nombre de produits homologués.</div>
    <button class="try-btn" onclick="toggle('cultures')">▶ Essayer</button>
    <div class="try-panel" id="panel-cultures">
      <label>Paramètres (optionnel)</label>
      <input id="qs-cultures" value="q=tom">
      <label>Clé API</label>
      <input id="key-cultures" value="as_test_demo">
      <button class="run-btn" onclick="run('GET','cultures','qs-cultures','cultures')">Envoyer ▶</button>
      <div class="response-area" id="resp-cultures"></div>
    </div>
  </div>

  <div class="endpoint">
    <div class="endpoint-header">
      <span class="method get">GET</span>
      <span class="path">/v1/groupes</span>
    </div>
    <div class="desc">Référentiels officiels de résistance FRAC 2025 (fongicides), IRAC 2021 (insecticides), HRAC 2026 (herbicides).</div>
    <div class="params">
      <div class="param-row"><span class="param-name">type<span class="required">*</span></span><span class="param-type">string</span><span class="param-desc">Type de classification : frac | irac | hrac</span></div>
      <div class="param-row"><span class="param-name">groupe</span><span class="param-type">string</span><span class="param-desc">Numéro de groupe (ex: "11", "28", "M3")</span></div>
      <div class="param-row"><span class="param-name">risque</span><span class="param-type">string</span><span class="param-desc">Niveau de risque : faible | modéré | élevé | très élevé</span></div>
      <div class="param-row"><span class="param-name">ma</span><span class="param-type">string</span><span class="param-desc">Recherche par matière active (ex: "cyprodinil")</span></div>
    </div>
    <button class="try-btn" onclick="toggle('groupes')">▶ Essayer</button>
    <div class="try-panel" id="panel-groupes">
      <label>Paramètres</label>
      <input id="qs-groupes" value="type=frac&groupe=11">
      <label>Clé API</label>
      <input id="key-groupes" value="as_test_demo">
      <button class="run-btn" onclick="run('GET','groupes','qs-groupes','groupes')">Envoyer ▶</button>
      <div class="response-area" id="resp-groupes"></div>
    </div>
  </div>

</div>

<script>
const BASE = window.location.origin;

function toggle(id) {
  const panel = document.getElementById('panel-' + id);
  panel.classList.toggle('open');
}

async function run(method, endpoint, qsId, respId) {
  const keyEl = document.getElementById('key-' + respId);
  const respEl = document.getElementById('resp-' + respId);
  const key = keyEl ? keyEl.value : 'as_test_demo';
  let url = BASE + '/v1/' + endpoint;
  if (qsId) {
    const qs = document.getElementById(qsId)?.value;
    if (qs) url += '?' + qs;
  }
  respEl.style.display = 'block';
  respEl.textContent = 'Chargement...';
  try {
    const opts = { headers: { 'Authorization': 'Bearer ' + key } };
    if (method === 'POST') {
      opts.method = 'POST';
      opts.headers['Content-Type'] = 'application/json';
      opts.body = document.getElementById('body-' + respId)?.value || '{}';
    }
    const r = await fetch(url, opts);
    const data = await r.json();
    respEl.textContent = JSON.stringify(data, null, 2);
  } catch(e) {
    respEl.textContent = 'Erreur : ' + e.message;
  }
}

async function runId() {
  const id = document.getElementById('qs-produit-id').value;
  const key = document.getElementById('key-produit-id').value;
  const respEl = document.getElementById('resp-produit-id');
  respEl.style.display = 'block';
  respEl.textContent = 'Chargement...';
  try {
    const r = await fetch(BASE + '/v1/produits/' + id, {
      headers: { 'Authorization': 'Bearer ' + key }
    });
    const data = await r.json();
    respEl.textContent = JSON.stringify(data, null, 2);
  } catch(e) {
    respEl.textContent = 'Erreur : ' + e.message;
  }
}
</script>
</body>
</html>'''

# ── HTTP Handler ──────────────────────────────────────────────────────────────

class AgriSageHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        ts = datetime.now().strftime('%H:%M:%S')
        print('[' + ts + '] ' + self.address_string() + ' ' + (fmt % args))

    def send_json(self, code, data, extra_headers=None):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type',   'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.send_header('X-Powered-By',   'AgriSage/' + SDK_VERSION)
        if extra_headers:
            for k, v in extra_headers.items(): self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html):
        body = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type',   'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.end_headers()

    def check_auth(self):
        """Valide la clé API. Retourne le client ou None."""
        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            self.send_json(401, {'error':{'code':'UNAUTHORIZED','message':'Header requis : Authorization: Bearer as_test_XXXX'}})
            return None
        key = auth.replace('Bearer ', '').strip()

        # Mode de compatibilité : as_test_demo accepté sans DB
        if key == 'as_test_demo':
            return {'id': 0, 'client_name': 'demo', 'plan': 'starter',
                    'quota_mensuel': 500, 'requetes_mois': 0, 'key_hash': 'demo'}

        # Vérifier dans la DB des clés
        try:
            result = validate_key(key)
            if result is None:
                self.send_json(401, {'error':{'code':'UNAUTHORIZED','message':'Cle API invalide ou revoquee.'}})
                return None
            if result == 'QUOTA_EXCEEDED':
                self.send_json(429, {'error':{'code':'QUOTA_EXCEEDED',
                    'message':'Quota mensuel atteint. Passez au plan superieur sur agrisage.ma/tarifs.'}})
                return None
            return result
        except Exception:
            # Si la table n'existe pas encore, accepter les préfixes standards
            if key.startswith(('as_test_', 'as_live_')):
                return {'id': 0, 'client_name': 'client', 'plan': 'starter',
                        'quota_mensuel': 9999, 'requetes_mois': 0, 'key_hash': key[:20]}
            self.send_json(401, {'error':{'code':'UNAUTHORIZED','message':'Cle invalide.'}})
            return None

    def check_admin(self):
        auth = self.headers.get('Authorization', '')
        key  = auth.replace('Bearer ', '').strip()
        if key != ADMIN_KEY:
            self.send_json(403, {'error':{'code':'FORBIDDEN','message':'Acces admin requis.'}})
            return False
        return True

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip('/')
        qs     = parse_qs(parsed.query)

        # ── Routes publiques (sans auth) ─────────────────────────────────
        if path in ('/health', ''):
            return self.send_json(200, {
                'status':'ok', 'service':'AgriSage API', 'version':SDK_VERSION,
                'endpoints':['POST /v1/conseil','GET /v1/produits','GET /v1/produits/{id}',
                             'GET /v1/cultures','GET /v1/groupes','GET /docs'],
                'time': datetime.now().isoformat(),
            })

        if path == '/docs':
            return self.send_html(DOCS_HTML)

        # ── Routes admin ─────────────────────────────────────────────────
        if path == '/admin/keys':
            if not self.check_admin(): return
            try:
                init_keys_db()
                stats = get_stats()
                return self.send_json(200, stats)
            except Exception as e:
                return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        if path == '/admin/stats':
            if not self.check_admin(): return
            try:
                init_keys_db()
                return self.send_json(200, get_stats())
            except Exception as e:
                return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        # ── Routes API (auth requise) ─────────────────────────────────────
        client = self.check_auth()
        if not client: return
        start  = datetime.now()

        m = re.match(r'^/' + API_VERSION + r'/produits/(\d+)$', path)
        if m:
            pid = int(m.group(1))
            try:
                result = get_produit_by_id(pid)
                if result is None:
                    elapsed = int((datetime.now()-start).total_seconds()*1000)
                    log_request(client.get('key_hash'), path, 'GET', 404, elapsed)
                    return self.send_json(404, {'error':{'code':'NOT_FOUND','message':'Produit ' + str(pid) + ' introuvable.'}})
                elapsed = int((datetime.now()-start).total_seconds()*1000)
                log_request(client.get('key_hash'), '/v1/produits/{id}', 'GET', 200, elapsed)
                return self.send_json(200, result, {'X-Response-Time':str(elapsed)+'ms',
                    'X-RateLimit-Remaining':str(client.get('quota_mensuel',9999)-client.get('requetes_mois',0))})
            except Exception as e:
                return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        if path == '/' + API_VERSION + '/produits':
            try:
                result  = get_produits(qs)
                elapsed = int((datetime.now()-start).total_seconds()*1000)
                log_request(client.get('key_hash'), '/v1/produits', 'GET', 200, elapsed)
                return self.send_json(200, result, {'X-Response-Time':str(elapsed)+'ms'})
            except Exception as e:
                return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        if path == '/' + API_VERSION + '/cultures':
            try:
                result  = get_cultures(qs)
                elapsed = int((datetime.now()-start).total_seconds()*1000)
                log_request(client.get('key_hash'), '/v1/cultures', 'GET', 200, elapsed)
                return self.send_json(200, result, {'X-Response-Time':str(elapsed)+'ms'})
            except Exception as e:
                return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        if path == '/' + API_VERSION + '/groupes':
            try:
                result  = get_groupes(qs)
                elapsed = int((datetime.now()-start).total_seconds()*1000)
                log_request(client.get('key_hash'), '/v1/groupes', 'GET', 200, elapsed)
                return self.send_json(200, result, {'X-Response-Time':str(elapsed)+'ms'})
            except ValueError as e:
                return self.send_json(400, {'error':{'code':'INVALID_PARAM','message':str(e)}})
            except Exception as e:
                return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        self.send_json(404, {'error':{'code':'NOT_FOUND','message':'Endpoint introuvable. Consultez /docs'}})

    def do_POST(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip('/')
        start  = datetime.now()

        # ── Admin : créer une clé ────────────────────────────────────────
        if path == '/admin/keys':
            if not self.check_admin(): return
            length = int(self.headers.get('Content-Length', 0))
            try:
                body = json.loads(self.rfile.read(length).decode('utf-8')) if length else {}
            except Exception:
                return self.send_json(400, {'error':{'code':'INVALID_JSON','message':'Body JSON invalide.'}})
            if not body.get('client_name'):
                return self.send_json(400, {'error':{'code':'INVALID_PARAM','message':'client_name requis.'}})
            try:
                init_keys_db()
                result = create_key(
                    client_name=body['client_name'],
                    client_email=body.get('client_email',''),
                    plan=body.get('plan','starter'),
                    notes=body.get('notes','')
                )
                print(f"[ADMIN] Nouvelle cle creee pour {result['client']} (plan:{result['plan']})")
                return self.send_json(201, {
                    'message': 'Cle API creee avec succes.',
                    'key': result['key'],
                    'key_id': result['id'],
                    'client': result['client'],
                    'plan': result['plan'],
                    'quota_mensuel': result['quota_mensuel'],
                    'warning': 'Sauvegardez cette cle maintenant — elle ne sera plus affichee.'
                })
            except Exception as e:
                return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        if path == '/admin/keys/revoke':
            if not self.check_admin(): return
            length = int(self.headers.get('Content-Length', 0))
            try:
                body = json.loads(self.rfile.read(length).decode('utf-8')) if length else {}
                key_id = body.get('key_id')
                if not key_id:
                    return self.send_json(400, {'error':{'code':'INVALID_PARAM','message':'key_id requis.'}})
                init_keys_db()
                conn = db()
                conn.execute('UPDATE api_keys SET actif=0 WHERE id=?', (key_id,))
                conn.commit(); conn.close()
                return self.send_json(200, {'message': 'Cle ' + str(key_id) + ' revoquee.'})
            except Exception as e:
                return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        # ── API conseil ──────────────────────────────────────────────────
        client = self.check_auth()
        if not client: return

        length = int(self.headers.get('Content-Length', 0))
        try:
            raw  = self.rfile.read(length).decode('utf-8') if length else '{}'
            body = json.loads(raw)
        except Exception:
            return self.send_json(400, {'error':{'code':'INVALID_JSON','message':'Body JSON invalide.'}})

        if path == '/' + API_VERSION + '/conseil':
            return self._handle_conseil(body, start, client)

        self.send_json(404, {'error':{'code':'NOT_FOUND','message':'Endpoint introuvable. Consultez /docs'}})

    def _handle_conseil(self, body, start, client):
        errors = []
        if not body.get('culture'):  errors.append({'champ':'culture','message':'Requis.'})
        if not body.get('ravageur'): errors.append({'champ':'ravageur','message':'Requis.'})
        stade = str(body.get('stade','')).lower().strip()
        if not stade: errors.append({'champ':'stade','message':'Requis.'})
        elif stade not in STADES_VALIDES:
            errors.append({'champ':'stade','message':'Valeurs: ' + ', '.join(sorted(STADES_VALIDES))})
        if errors:
            return self.send_json(400, {'error':{'code':'INVALID_PARAM','message':'Parametre(s) invalide(s).','details':errors}})
        try:
            params = {
                'culture':         body['culture'].strip(),
                'ravageur':        body['ravageur'].strip(),
                'stade':           stade,
                'dar_max':         body.get('dar_max'),
                'historique_frac': body.get('historique_frac') or [],
                'historique_irac': body.get('historique_irac') or [],
                'nb_alternatives': body.get('nb_alternatives', 2),
            }
            conseil = generer_conseil(params)
            elapsed = int((datetime.now() - start).total_seconds() * 1000)
            log_request(client.get('key_hash'), '/v1/conseil', 'POST', 200, elapsed)
            body_bytes = json.dumps(conseil, ensure_ascii=False, indent=2).encode('utf-8')
            remaining  = client.get('quota_mensuel', 9999) - client.get('requetes_mois', 0)
            self.send_response(200)
            self.send_header('Content-Type',   'application/json; charset=utf-8')
            self.send_header('Content-Length',  str(len(body_bytes)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('X-Response-Time', str(elapsed) + 'ms')
            self.send_header('X-RateLimit-Remaining', str(max(0, remaining)))
            self.end_headers()
            self.wfile.write(body_bytes)
        except ValueError as e:
            self.send_json(404, {'error':{'code':'CULTURE_NOT_FOUND','message':str(e)}})
        except Exception as e:
            print('[ERROR]', e)
            self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    global DB_PATH
    parser = argparse.ArgumentParser(description='AgriSage API Server')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--db',   type=str, default=DB_PATH)
    parser.add_argument('--host', type=str, default='0.0.0.0')
    args = parser.parse_args()
    DB_PATH = os.path.abspath(args.db)

    if not os.path.exists(DB_PATH):
        print('ERREUR : Base de donnees introuvable : ' + DB_PATH)
        sys.exit(1)

    # Initialiser les tables de gestion des clés
    try:
        init_keys_db()
        print('Systeme de cles API initialise')
    except Exception as e:
        print('Warning: init cles:', e)

    server = HTTPServer((args.host, args.port), AgriSageHandler)
    print('')
    print('AgriSage API demarree — v' + SDK_VERSION)
    print('  URL      : http://localhost:' + str(args.port))
    print('  Docs     : http://localhost:' + str(args.port) + '/docs')
    print('  Base DB  : ' + DB_PATH)
    print('  Admin    : Authorization: Bearer ' + ADMIN_KEY)
    print('')
    print('  Endpoints :')
    print('    GET  /docs                          Documentation interactive')
    print('    POST /v1/conseil                    Conseil phytosanitaire')
    print('    GET  /v1/produits                   Liste produits ONSSA')
    print('    GET  /v1/produits/{id}              Detail produit')
    print('    GET  /v1/cultures                   Liste cultures')
    print('    GET  /v1/groupes?type=frac|irac|hrac Referentiels resistance')
    print('    POST /admin/keys                    Creer une cle client')
    print('    GET  /admin/keys                    Lister les cles')
    print('    GET  /admin/stats                   Statistiques')
    print('')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Serveur arrete.')
        server.server_close()

if __name__ == '__main__':
    main()
