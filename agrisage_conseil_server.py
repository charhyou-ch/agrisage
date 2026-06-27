#!/usr/bin/env python3
"""
AgriSage API â€” Serveur Python stdlib uniquement
Endpoints :
  POST /v1/conseil       â€” Conseil phytosanitaire
  GET  /v1/produits      â€” Liste produits ONSSA (filtres + pagination)
  GET  /v1/produits/{id} â€” Detail produit ONSSA
  GET  /v1/cultures      â€” Liste cultures disponibles
  GET  /health           â€” Statut serveur

Usage : python agrisage_conseil_server.py --port 3000 --db onssa_index.db
"""
import json, os, random, re, sqlite3, string, sys, argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

SDK_VERSION  = '1.0.0'
API_VERSION  = 'v1'
DEFAULT_PORT = int(os.environ.get('PORT', 3000))
DB_PATH      = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'onssa_index.db')

# â”€â”€ FRAC / IRAC / ToxicitÃ© â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
FRAC_GROUPS = {
    'azoxystrobine':    {'groupe':'11','risque':'Ã©levÃ©',     'mecanisme':'Inhibiteurs complexes III (Qo)'},
    'trifloxystrobine': {'groupe':'11','risque':'Ã©levÃ©',     'mecanisme':'Inhibiteurs complexes III (Qo)'},
    'pyraclostrobine':  {'groupe':'11','risque':'Ã©levÃ©',     'mecanisme':'Inhibiteurs complexes III (Qo)'},
    'cyprodinil':       {'groupe':'9', 'risque':'modÃ©rÃ©',    'mecanisme':'Inhibiteurs biosynthÃ¨se acides aminÃ©s'},
    'pyrimethanil':     {'groupe':'9', 'risque':'modÃ©rÃ©',    'mecanisme':'Inhibiteurs biosynthÃ¨se acides aminÃ©s'},
    'fludioxonil':      {'groupe':'12','risque':'faible',    'mecanisme':'Inhibiteurs transduction signal'},
    'difÃ©noconazole':   {'groupe':'3', 'risque':'modÃ©rÃ©',    'mecanisme':'Inhibiteurs dÃ©mÃ©thylation (DMI)'},
    'tebuconazole':     {'groupe':'3', 'risque':'modÃ©rÃ©',    'mecanisme':'Inhibiteurs dÃ©mÃ©thylation (DMI)'},
    'penconazole':      {'groupe':'3', 'risque':'modÃ©rÃ©',    'mecanisme':'Inhibiteurs dÃ©mÃ©thylation (DMI)'},
    'fluopyram':        {'groupe':'7', 'risque':'modÃ©rÃ©',    'mecanisme':'Inhibiteurs succinate dÃ©shydrogÃ©nase'},
    'boscalid':         {'groupe':'7', 'risque':'modÃ©rÃ©',    'mecanisme':'Inhibiteurs succinate dÃ©shydrogÃ©nase'},
    'mancozebe':        {'groupe':'M3','risque':'faible',    'mecanisme':'Contact multi-site'},
    'mancozÃ¨be':        {'groupe':'M3','risque':'faible',    'mecanisme':'Contact multi-site'},
    'folpel':           {'groupe':'M4','risque':'faible',    'mecanisme':'Contact multi-site'},
    'cymoxanil':        {'groupe':'27','risque':'modÃ©rÃ©',    'mecanisme':'Inhibiteurs acides nuclÃ©iques'},
    'dimÃ©thomorphe':    {'groupe':'40','risque':'modÃ©rÃ©',    'mecanisme':'Inhibiteurs paroi cellulaire'},
    'dimethomorphe':    {'groupe':'40','risque':'modÃ©rÃ©',    'mecanisme':'Inhibiteurs paroi cellulaire'},
    'mÃ©talaxyl':        {'groupe':'4', 'risque':'trÃ¨s Ã©levÃ©','mecanisme':'Inhibiteurs polymÃ©rase ARN'},
    'metalaxyl':        {'groupe':'4', 'risque':'trÃ¨s Ã©levÃ©','mecanisme':'Inhibiteurs polymÃ©rase ARN'},
    'cyflufÃ©namide':    {'groupe':'U6','risque':'faible',    'mecanisme':'Inhibiteurs cÃ©tol-rÃ©ductases'},
    'iprodione':        {'groupe':'2', 'risque':'faible',    'mecanisme':'Inhibiteurs transduction signal'},
    'spiroxamine':      {'groupe':'5', 'risque':'modÃ©rÃ©',    'mecanisme':'Inhibiteurs biosynthÃ¨se stÃ©rols'},
}
IRAC_GROUPS = {
    'abamectine':           {'groupe':'6',  'risque':'modÃ©rÃ©','mecanisme':'Modulateurs canaux Cl glutamate'},
    'lambda cyhalothrine':  {'groupe':'3A', 'risque':'Ã©levÃ©', 'mecanisme':'Modulateurs canaux Na'},
    'cypermÃ©thrine':        {'groupe':'3A', 'risque':'Ã©levÃ©', 'mecanisme':'Modulateurs canaux Na'},
    'deltamethrine':        {'groupe':'3B', 'risque':'Ã©levÃ©', 'mecanisme':'Modulateurs canaux Na'},
    'chlorantraniliprole':  {'groupe':'28', 'risque':'faible','mecanisme':'Modulateurs rÃ©cepteurs ryanodine'},
    'chloranthraniliprole': {'groupe':'28', 'risque':'faible','mecanisme':'Modulateurs rÃ©cepteurs ryanodine'},
    'spinosad':             {'groupe':'5',  'risque':'faible','mecanisme':'Modulateurs rÃ©cepteurs nAChR'},
    'spinetoram':           {'groupe':'5',  'risque':'faible','mecanisme':'Modulateurs rÃ©cepteurs nAChR'},
    'imidaclopride':        {'groupe':'4A', 'risque':'Ã©levÃ©', 'mecanisme':'Agonistes nAChR'},
    'thiamÃ©toxame':         {'groupe':'4A', 'risque':'Ã©levÃ©', 'mecanisme':'Agonistes nAChR'},
    'acetamipride':         {'groupe':'4A', 'risque':'Ã©levÃ©', 'mecanisme':'Agonistes nAChR'},
    'pyriproxyfÃ¨ne':        {'groupe':'7C', 'risque':'faible','mecanisme':'MimÃ©tiques hormone juvÃ©nile'},
    'spirotÃ©tramat':        {'groupe':'23', 'risque':'faible','mecanisme':'Inhibiteurs ACCase'},
    'etoxazole':            {'groupe':'10B','risque':'faible','mecanisme':'Inhibiteurs biosynthÃ¨se chitine'},
}
TOXICITE_ABEILLES = {
    'lambda cyhalothrine':'Ã©levÃ©', 'cypermÃ©thrine':'Ã©levÃ©', 'deltamethrine':'Ã©levÃ©',
    'imidaclopride':'Ã©levÃ©',       'thiamÃ©toxame':'Ã©levÃ©',  'clothianidine':'Ã©levÃ©',
    'acetamipride':'modÃ©rÃ©',       'spinosad':'modÃ©rÃ©',     'abamectine':'modÃ©rÃ©',
    'spirotÃ©tramat':'modÃ©rÃ©',
    'azoxystrobine':'faible',      'cyprodinil':'faible',   'fludioxonil':'faible',
    'difÃ©noconazole':'faible',     'mancozÃ¨be':'faible',    'mancozebe':'faible',
    'pyriproxyfÃ¨ne':'faible',      'etoxazole':'faible',    'boscalid':'faible',
    'cymoxanil':'faible',          'fluopyram':'faible',
    'chlorantraniliprole':'trÃ¨s faible', 'chloranthraniliprole':'trÃ¨s faible',
}
ROTATION_NOTES = {
    '3' :'Alterner avec FRAC 7, 9 ou 27. Max 2 applications/saison.',
    '7' :'Alterner avec FRAC 3 ou 11. Max 2 applications/saison.',
    '9' :'Alterner avec FRAC 3 ou 40. Max 2 applications/saison.',
    '11':'Risque Ã©levÃ©. Max 1 application consÃ©cutive. Alterner avec FRAC 3 ou 7.',
    '4' :'Risque TRES ELEVE. Max 1 application/saison. Toujours en mÃ©lange.',
    '27':'Bon choix anti-rÃ©sistance strobilurines. Alterner avec FRAC 40.',
    '40':'Alterner avec FRAC 27 ou M3.',
    'M3':'Contact multi-site. Rotation libre. Excellent tank-mix.',
    '28':'Bon choix anti-rÃ©sistance. Max 2 applications/saison.',
    '3A':'Risque Ã©levÃ© pyrethrinoides. Alterner avec IRAC 5, 6 ou 28.',
    '4A':'Risque trÃ¨s Ã©levÃ© neonicotinoides. Alterner avec IRAC 5 ou 28.',
    '6' :'Alterner avec IRAC 28 ou 5. Max 2 applications/saison.',
}
STADES_VALIDES   = {'germination','levee','vegetation','floraison','fructification','recolte','post-recolte'}
VALID_KEY_PREFIXES = ('as_test_', 'as_live_')
PAGE_SIZE = 50

# â”€â”€ Utilitaires â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_ma_base(ma):
    if not ma: return ''
    ma = re.sub(r'\s*[\(\[]\d[^\)\]]*[\)\]]', '', ma)
    ma = re.sub(r'\s*\(.*?\)', '', ma)
    return ma.strip().lower()

def get_frac(ma):
    base = get_ma_base(ma)
    for k, v in FRAC_GROUPS.items():
        if k in base: return v
    return None

def get_irac(ma):
    base = get_ma_base(ma)
    for k, v in IRAC_GROUPS.items():
        if k in base: return v
    return None

def get_risque_abeilles(ma):
    base = get_ma_base(ma)
    for k, v in TOXICITE_ABEILLES.items():
        if k in base: return v
    return 'faible'

def conseil_id():
    return 'c_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def enrich_produit(p):
    """Ajoute groupe_frac, groupe_irac, risque_abeilles Ã  un dict produit."""
    ma   = p.get('matiere_active', '')
    frac = get_frac(ma)
    irac = get_irac(ma)
    p['groupe_frac']      = frac['groupe'] if frac else None
    p['groupe_irac']      = irac['groupe'] if irac else None
    p['risque_abeilles']  = get_risque_abeilles(ma)
    p['risque_resistance']= (frac or irac or {}).get('risque')
    return p

# â”€â”€ Moteur conseil â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def generer_conseil(params):
    culture   = params.get('culture', '').strip()
    ravageur  = params.get('ravageur', '').strip()
    stade     = params.get('stade', '').strip().lower()
    dar_max   = params.get('dar_max')
    hist_frac = params.get('historique_frac') or []
    hist_irac = params.get('historique_irac') or []
    nb_alt    = int(params.get('nb_alternatives', 2))

    cl = culture.lower()
    rl = ravageur.lower() if ravageur else None

    conn = db()
    cur  = conn.cursor()

    sql  = '''SELECT p.id, p.nom_commercial, p.numero_homologation, p.detenteur,
                     p.categorie, p.type_produit, p.formulation, p.matiere_active,
                     p.valable_jusquau, p.tableau_toxicologique,
                     u.usage_desc, u.culture AS usage_culture,
                     u.dose, u.dar_raw, u.dar_jours, u.nb_applications
              FROM produits p JOIN usages u ON p.id = u.produit_id
              WHERE LOWER(u.culture) LIKE ?'''
    args = ['%' + cl + '%']
    if rl:
        sql += ' AND LOWER(u.usage_desc) LIKE ?'
        args.append('%' + rl + '%')
    if dar_max is not None:
        sql += ' AND (u.dar_jours IS NULL OR u.dar_jours <= ?)'
        args.append(int(dar_max))
    sql += ' ORDER BY u.dar_jours ASC NULLS LAST LIMIT 80'
    rows = [dict(r) for r in cur.execute(sql, args).fetchall()]

    if not rows and rl:
        sql2  = sql.replace(' AND LOWER(u.usage_desc) LIKE ?', '').replace('LIMIT 80','LIMIT 20')
        args2 = ['%' + cl + '%']
        if dar_max is not None:
            args2.append(int(dar_max))
        rows = [dict(r) for r in cur.execute(sql2, args2).fetchall()]
    conn.close()

    if not rows:
        raise ValueError("Aucun produit homologue ONSSA pour '" + culture + "'")

    for r in rows:
        ma    = r.get('matiere_active', '')
        frac  = get_frac(ma); irac = get_irac(ma); ra = get_risque_abeilles(ma)
        tox   = r.get('tableau_toxicologique', '')
        score = 100
        if frac and frac['groupe'] in hist_frac: score -= 60
        if irac and irac['groupe'] in hist_irac: score -= 60
        if ra == 'Ã©levÃ©'  and stade == 'floraison': score -= 45
        if ra == 'modÃ©rÃ©' and stade == 'floraison': score -= 20
        if tox == 'Ia': score -= 30
        if tox == 'Ib': score -= 15
        if frac and frac['groupe'] not in hist_frac: score += 10
        if ra == 'trÃ¨s faible': score += 12
        elif ra == 'faible':    score += 6
        d = r.get('dar_jours')
        if d and d <= 3: score += 5
        r.update({'_s':score,'_f':frac,'_i':irac,'_ra':ra})

    rows.sort(key=lambda x: -x['_s'])
    best = rows[0]

    alertes = []
    if stade == 'floraison':
        ra = best['_ra']
        if   ra == 'Ã©levÃ©':  alertes.append('DANGEREUX abeilles. Application interdite en floraison.')
        elif ra == 'modÃ©rÃ©': alertes.append('Risque modÃ©rÃ© pollinisateurs. Appliquer aprÃ¨s 19h ou avant 6h.')
        else:                alertes.append('Floraison : appliquer de prÃ©fÃ©rence aprÃ¨s 19h.')
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

    rot = None
    if best['_f']: rot = ROTATION_NOTES.get(best['_f']['groupe'])
    elif best['_i']: rot = ROTATION_NOTES.get(best['_i']['groupe'])

    return {
        'conseil_id':          conseil_id(),
        'produit':             best['nom_commercial'],
        'matiere_active':      best['matiere_active'],
        'numero_amm':          best.get('numero_homologation'),
        'detenteur':           best.get('detenteur'),
        'dose':                best.get('dose'),
        'dar':                 best.get('dar_jours'),
        'dar_raw':             best.get('dar_raw'),
        'nb_applications':     best.get('nb_applications'),
        'formulation':         best.get('formulation'),
        'categorie':           best.get('categorie'),
        'type_produit':        best.get('type_produit'),
        'usage_homologue':     best.get('usage_desc'),
        'culture_homologuee':  best.get('usage_culture'),
        'groupe_frac':         best['_f']['groupe'] if best['_f'] else None,
        'groupe_irac':         best['_i']['groupe'] if best['_i'] else None,
        'groupe_hrac':         None,
        'risque_resistance':   (best['_f'] or best['_i'] or {}).get('risque'),
        'mecanisme_action':    (best['_f'] or best['_i'] or {}).get('mecanisme'),
        'rotation_note':       rot,
        'homologue_onssa':     True,
        'valable_jusquau':     best.get('valable_jusquau'),
        'tableau_toxicologique': best.get('tableau_toxicologique'),
        'conforme_globalgap':  None,
        'lmr_ue_respectee':    None,
        'risque_abeilles':     best['_ra'],
        'risque_auxiliaires':  'faible',
        'alertes':             alertes,
        'alternatives':        alts,
        'meta': {'culture_demandee':culture,'ravageur_demande':ravageur,'stade':stade,
                 'dar_max_demande':dar_max,'nb_produits_trouves':len(rows),'score_principal':best['_s']},
        'timestamp': datetime.now().isoformat(),
    }

# â”€â”€ GET /produits â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_produits(qs):
    """
    ParamÃ¨tres query string :
      culture    â€” filtre par culture homologuÃ©e (LIKE)
      usage      â€” type : fongicide|insecticide|herbicide|acaricide|nematicide|...
      ma         â€” recherche matiÃ¨re active (LIKE)
      statut     â€” homologue (dÃ©faut) | tous
      groupe_fracâ€” filtre par groupe FRAC
      groupe_iracâ€” filtre par groupe IRAC
      q          â€” recherche libre sur nom_commercial + matiere_active
      page       â€” numÃ©ro de page (dÃ©faut 1)
    """
    culture     = qs.get('culture',     [None])[0]
    usage       = qs.get('usage',       [None])[0]
    ma          = qs.get('ma',          [None])[0]
    statut      = qs.get('statut',      ['homologue'])[0]
    groupe_frac = qs.get('groupe_frac', [None])[0]
    groupe_irac = qs.get('groupe_irac', [None])[0]
    q           = qs.get('q',           [None])[0]
    try:
        page = max(1, int(qs.get('page', ['1'])[0]))
    except ValueError:
        page = 1

    conn = db()
    cur  = conn.cursor()

    # RequÃªte de base â€” on joint usages pour avoir les cultures
    sql_select = '''
        SELECT DISTINCT p.id, p.nom_commercial, p.detenteur, p.fournisseur,
               p.numero_homologation, p.valable_jusquau, p.tableau_toxicologique,
               p.categorie, p.type_produit, p.formulation, p.matiere_active, p.teneur
        FROM produits p
    '''
    sql_where = 'WHERE 1=1'
    args = []

    needs_usage_join = bool(culture or groupe_frac or groupe_irac)

    if needs_usage_join:
        sql_select += ' LEFT JOIN usages u ON p.id = u.produit_id'

    if culture:
        sql_where += ' AND LOWER(u.culture) LIKE ?'
        args.append('%' + culture.lower() + '%')

    if usage:
        sql_where += ' AND p.type_produit LIKE ?'
        args.append('%' + usage.lower() + '%')

    if ma:
        sql_where += ' AND LOWER(p.matiere_active) LIKE ?'
        args.append('%' + ma.lower() + '%')

    if q:
        sql_where += ' AND (LOWER(p.nom_commercial) LIKE ? OR LOWER(p.matiere_active) LIKE ?)'
        args.extend(['%' + q.lower() + '%', '%' + q.lower() + '%'])

    if groupe_frac:
        # Filtrer par groupe FRAC via la matiÃ¨re active
        ma_keys = [k for k, v in FRAC_GROUPS.items() if v['groupe'] == groupe_frac]
        if ma_keys:
            placeholders = ' OR '.join(['LOWER(p.matiere_active) LIKE ?' for _ in ma_keys])
            sql_where += ' AND (' + placeholders + ')'
            args.extend(['%' + k + '%' for k in ma_keys])

    if groupe_irac:
        ma_keys = [k for k, v in IRAC_GROUPS.items() if v['groupe'] == groupe_irac]
        if ma_keys:
            placeholders = ' OR '.join(['LOWER(p.matiere_active) LIKE ?' for _ in ma_keys])
            sql_where += ' AND (' + placeholders + ')'
            args.extend(['%' + k + '%' for k in ma_keys])

    # Compter le total
    sql_count = 'SELECT COUNT(DISTINCT p.id) FROM produits p'
    if needs_usage_join:
        sql_count += ' LEFT JOIN usages u ON p.id = u.produit_id'
    sql_count += ' ' + sql_where
    total = cur.execute(sql_count, args).fetchone()[0]

    # DonnÃ©es paginÃ©es
    offset = (page - 1) * PAGE_SIZE
    sql_data = sql_select + ' ' + sql_where + ' ORDER BY p.nom_commercial ASC LIMIT ? OFFSET ?'
    rows = [dict(r) for r in cur.execute(sql_data, args + [PAGE_SIZE, offset]).fetchall()]

    # Enrichir avec cultures homologuÃ©es et groupes FRAC/IRAC
    for p in rows:
        enrich_produit(p)
        cultures_r = cur.execute(
            'SELECT DISTINCT culture FROM usages WHERE produit_id=? AND culture != "" ORDER BY culture LIMIT 20',
            (p['id'],)
        ).fetchall()
        p['cultures_homologuees'] = [r['culture'] for r in cultures_r]

        # DAR min/max
        dar_r = cur.execute(
            'SELECT MIN(dar_jours) dar_min, MAX(dar_jours) dar_max FROM usages WHERE produit_id=? AND dar_jours IS NOT NULL',
            (p['id'],)
        ).fetchone()
        p['dar_min'] = dar_r['dar_min'] if dar_r else None
        p['dar_max'] = dar_r['dar_max'] if dar_r else None

    conn.close()

    pages_total = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return {
        'data': rows,
        'pagination': {
            'page':        page,
            'par_page':    PAGE_SIZE,
            'total':       total,
            'pages_total': pages_total,
        }
    }

# â”€â”€ GET /produits/{id} â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_produit_by_id(produit_id):
    conn = db()
    cur  = conn.cursor()

    row = cur.execute('SELECT * FROM produits WHERE id = ?', (produit_id,)).fetchone()
    if not row:
        conn.close()
        return None

    p = dict(row)
    enrich_produit(p)

    # Tous les usages
    usages = [dict(r) for r in cur.execute(
        'SELECT culture, usage_desc, dose, dar_raw, dar_jours, nb_applications FROM usages WHERE produit_id=? ORDER BY culture',
        (produit_id,)
    ).fetchall()]
    p['usages'] = usages
    p['cultures_homologuees'] = list({u['culture'] for u in usages if u['culture']})
    p['cultures_homologuees'].sort()

    # Infos FRAC/IRAC complÃ¨tes
    frac = get_frac(p.get('matiere_active',''))
    irac = get_irac(p.get('matiere_active',''))
    if frac:
        p['frac_info'] = {**frac, 'rotation_note': ROTATION_NOTES.get(frac['groupe'])}
    if irac:
        p['irac_info'] = {**irac, 'rotation_note': ROTATION_NOTES.get(irac['groupe'])}

    conn.close()
    return p

# â”€â”€ GET /cultures â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_cultures(qs):
    """
    ParamÃ¨tres :
      q    â€” recherche partielle sur nom_fr
      page â€” numÃ©ro de page
    """
    q = qs.get('q', [None])[0]
    try:
        page = max(1, int(qs.get('page', ['1'])[0]))
    except ValueError:
        page = 1

    conn = db()
    cur  = conn.cursor()

    sql_where = "WHERE nom_fr != ''"
    args = []
    if q:
        sql_where += ' AND LOWER(nom_fr) LIKE ?'
        args.append('%' + q.lower() + '%')

    total = cur.execute('SELECT COUNT(*) FROM cultures ' + sql_where, args).fetchone()[0]

    offset = (page - 1) * PAGE_SIZE
    rows = [dict(r) for r in cur.execute(
        'SELECT id, nom_fr, nb_produits FROM cultures ' + sql_where +
        ' ORDER BY nb_produits DESC, nom_fr ASC LIMIT ? OFFSET ?',
        args + [PAGE_SIZE, offset]
    ).fetchall()]

    conn.close()
    pages_total = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return {
        'data': rows,
        'total': total,
        'pagination': {'page':page,'par_page':PAGE_SIZE,'total':total,'pages_total':pages_total}
    }

# â”€â”€ GET /matieres-actives â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_matieres_actives(qs):
    """
    ParamÃ¨tres :
      q    â€” recherche partielle sur nom
      page â€” numÃ©ro de page
    """
    q = qs.get('q', [None])[0]
    try:
        page = max(1, int(qs.get('page', ['1'])[0]))
    except ValueError:
        page = 1

    conn = db()
    cur  = conn.cursor()

    # Essayer la table matieres_actives si elle existe, sinon dÃ©river des produits
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

    if 'matieres_actives' in tables:
        sql_where = "WHERE 1=1"
        args = []
        if q:
            sql_where += ' AND LOWER(nom) LIKE ?'
            args.append('%' + q.lower() + '%')
        total = cur.execute('SELECT COUNT(*) FROM matieres_actives ' + sql_where, args).fetchone()[0]
        offset = (page - 1) * PAGE_SIZE
        rows = [dict(r) for r in cur.execute(
            'SELECT * FROM matieres_actives ' + sql_where +
            ' ORDER BY nom ASC LIMIT ? OFFSET ?',
            args + [PAGE_SIZE, offset]
        ).fetchall()]
    else:
        # DÃ©river depuis la colonne matiere_active de produits
        sql_where = "WHERE matiere_active IS NOT NULL AND matiere_active != ''"
        args = []
        if q:
            sql_where += ' AND LOWER(matiere_active) LIKE ?'
            args.append('%' + q.lower() + '%')
        total = cur.execute(
            'SELECT COUNT(DISTINCT matiere_active) FROM produits ' + sql_where, args
        ).fetchone()[0]
        offset = (page - 1) * PAGE_SIZE
        raw = cur.execute(
            'SELECT matiere_active, COUNT(*) as nb_produits FROM produits ' + sql_where +
            ' GROUP BY matiere_active ORDER BY matiere_active ASC LIMIT ? OFFSET ?',
            args + [PAGE_SIZE, offset]
        ).fetchall()
        rows = []
        for r in raw:
            ma = r[0]
            frac = get_frac(ma)
            irac = get_irac(ma)
            rows.append({
                'nom': ma,
                'nb_produits': r[1],
                'groupe_frac': frac['groupe'] if frac else None,
                'groupe_irac': irac['groupe'] if irac else None,
                'risque_resistance': frac['risque'] if frac else (irac['risque'] if irac else None),
            })

    conn.close()
    pages_total = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return {
        'data': rows,
        'total': total,
        'pagination': {'page': page, 'par_page': PAGE_SIZE, 'total': total, 'pages_total': pages_total}
    }

# â”€â”€ POST /conseil/batch â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def generer_conseil_batch(items):
    """
    Accepte une liste de requÃªtes conseil et retourne une liste de rÃ©sultats.
    Chaque item doit avoir : culture, ravageur, stade
    Optionnel : dar_max, historique_frac, historique_irac, nb_alternatives, ref
    """
    if not isinstance(items, list):
        raise ValueError('Le champ "items" doit Ãªtre une liste.')
    if len(items) == 0:
        raise ValueError('La liste "items" est vide.')
    if len(items) > 20:
        raise ValueError('Maximum 20 items par requÃªte batch.')

    results = []
    for i, item in enumerate(items):
        ref = item.get('ref', str(i + 1))
        errors = []
        if not item.get('culture'):  errors.append({'champ': 'culture', 'message': 'Requis.'})
        if not item.get('ravageur'): errors.append({'champ': 'ravageur', 'message': 'Requis.'})
        stade = str(item.get('stade', '')).lower().strip()
        if not stade:
            errors.append({'champ': 'stade', 'message': 'Requis.'})
        elif stade not in STADES_VALIDES:
            errors.append({'champ': 'stade', 'message': 'Valeurs: ' + ', '.join(sorted(STADES_VALIDES))})

        if errors:
            results.append({'ref': ref, 'status': 'error', 'errors': errors})
            continue

        try:
            params = {
                'culture':         item['culture'].strip(),
                'ravageur':        item['ravageur'].strip(),
                'stade':           stade,
                'dar_max':         item.get('dar_max'),
                'historique_frac': item.get('historique_frac') or [],
                'historique_irac': item.get('historique_irac') or [],
                'nb_alternatives': item.get('nb_alternatives', 2),
            }
            conseil = generer_conseil(params)
            results.append({'ref': ref, 'status': 'ok', 'conseil': conseil})
        except ValueError as e:
            results.append({'ref': ref, 'status': 'not_found', 'message': str(e)})
        except Exception as e:
            results.append({'ref': ref, 'status': 'error', 'message': str(e)})

    return {
        'total': len(items),
        'ok': sum(1 for r in results if r['status'] == 'ok'),
        'errors': sum(1 for r in results if r['status'] in ('error', 'not_found')),
        'results': results,
    }

# â”€â”€ HTTP Handler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.end_headers()

    def check_auth(self):
        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            self.send_json(401, {'error':{'code':'UNAUTHORIZED',
                'message':'Header requis : Authorization: Bearer as_test_XXXX'}})
            return False
        key = auth.replace('Bearer ', '').strip()
        if not any(key.startswith(p) for p in VALID_KEY_PREFIXES):
            self.send_json(401, {'error':{'code':'UNAUTHORIZED',
                'message':'Cle invalide. Prefixe requis : as_test_ ou as_live_'}})
            return False
        return True

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip('/')
        qs     = parse_qs(parsed.query)

        # Health â€” sans auth
        if path in ('/health', ''):
            return self.send_json(200, {
                'status':'ok', 'service':'AgriSage API', 'version':SDK_VERSION,
                'endpoints':['POST /v1/conseil','GET /v1/produits',
                             'GET /v1/produits/{id}','GET /v1/cultures'],
                'time': datetime.now().isoformat(),
            })

        if not self.check_auth():
            return

        start = datetime.now()

        # GET /v1/produits/{id}
        m = re.match(r'^/' + API_VERSION + r'/produits/(\d+)$', path)
        if m:
            produit_id = int(m.group(1))
            try:
                result = get_produit_by_id(produit_id)
                if result is None:
                    return self.send_json(404, {'error':{
                        'code':'NOT_FOUND',
                        'message':'Produit ' + str(produit_id) + ' introuvable.',
                        'suggestion':'Consultez GET /v1/produits pour la liste complÃ¨te.',
                    }})
                elapsed = (datetime.now() - start).total_seconds() * 1000
                return self.send_json(200, result, {'X-Response-Time':'{:.0f}ms'.format(elapsed)})
            except Exception as e:
                return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        # GET /v1/produits
        if path == '/' + API_VERSION + '/produits':
            try:
                result  = get_produits(qs)
                elapsed = (datetime.now() - start).total_seconds() * 1000
                return self.send_json(200, result, {'X-Response-Time':'{:.0f}ms'.format(elapsed)})
            except Exception as e:
                return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        # GET /v1/cultures
        if path == '/' + API_VERSION + '/cultures':
            try:
                result  = get_cultures(qs)
                elapsed = (datetime.now() - start).total_seconds() * 1000
                return self.send_json(200, result, {'X-Response-Time':'{:.0f}ms'.format(elapsed)})
            except Exception as e:
                return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        # GET /v1/matieres-actives
        if path == '/' + API_VERSION + '/matieres-actives':
            try:
                result  = get_matieres_actives(qs)
                elapsed = (datetime.now() - start).total_seconds() * 1000
                return self.send_json(200, result, {'X-Response-Time':'{:.0f}ms'.format(elapsed)})
            except Exception as e:
                return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        self.send_json(404, {'error':{'code':'NOT_FOUND','message':'Endpoint introuvable.'}})

    def do_POST(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip('/')
        start  = datetime.now()

        if not self.check_auth():
            return

        length = int(self.headers.get('Content-Length', 0))
        try:
            raw  = self.rfile.read(length).decode('utf-8') if length else '{}'
            body = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.send_json(400, {'error':{'code':'INVALID_JSON','message':'Body JSON invalide.'}})

        if path == '/' + API_VERSION + '/conseil':
            return self._handle_conseil(body, start)

        if path == '/' + API_VERSION + '/conseil/batch':
            return self._handle_conseil_batch(body, start)

        self.send_json(404, {'error':{'code':'NOT_FOUND','message':'Endpoint introuvable.'}})

    def _handle_conseil(self, body, start):
        errors = []
        if not body.get('culture'):  errors.append({'champ':'culture', 'message':'Requis.'})
        if not body.get('ravageur'): errors.append({'champ':'ravageur','message':'Requis.'})
        stade = str(body.get('stade','')).lower().strip()
        if not stade:
            errors.append({'champ':'stade','message':'Requis.'})
        elif stade not in STADES_VALIDES:
            errors.append({'champ':'stade','message':'Valeurs: ' + ', '.join(sorted(STADES_VALIDES))})
        if errors:
            return self.send_json(400,{'error':{'code':'INVALID_PARAM',
                'message':'Parametre(s) invalide(s).','details':errors}})
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
            elapsed = (datetime.now() - start).total_seconds() * 1000
            body_bytes = json.dumps(conseil, ensure_ascii=False, indent=2).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type',          'application/json; charset=utf-8')
            self.send_header('Content-Length',         str(len(body_bytes)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('X-Response-Time',        '{:.0f}ms'.format(elapsed))
            self.send_header('X-RateLimit-Remaining', '9999')
            self.end_headers()
            self.wfile.write(body_bytes)
        except ValueError as e:
            self.send_json(404,{'error':{'code':'CULTURE_NOT_FOUND','message':str(e)}})
        except Exception as e:
            print('[ERROR]', e)
            self.send_json(500,{'error':{'code':'SERVER_ERROR','message':str(e)}})

    def _handle_conseil_batch(self, body, start):
        items = body.get('items')
        if not items:
            return self.send_json(400, {'error':{'code':'INVALID_PARAM',
                'message':'Champ requis : "items" (liste de requÃªtes conseil).'}})
        try:
            result  = generer_conseil_batch(items)
            elapsed = (datetime.now() - start).total_seconds() * 1000
            return self.send_json(200, result, {'X-Response-Time':'{:.0f}ms'.format(elapsed)})
        except ValueError as e:
            return self.send_json(400, {'error':{'code':'INVALID_PARAM','message':str(e)}})
        except Exception as e:
            print('[ERROR]', e)
            return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

# â”€â”€ Main â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main():
    global DB_PATH
    parser = argparse.ArgumentParser(description='AgriSage API Server')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--db',   type=str, default=DB_PATH)
    parser.add_argument('--host', type=str, default='0.0.0.0')
    args   = parser.parse_args()
    DB_PATH = os.path.abspath(args.db)

    if not os.path.exists(DB_PATH):
        print('ERREUR : Base de donnees introuvable : ' + DB_PATH)
        sys.exit(1)

    server = HTTPServer((args.host, args.port), AgriSageHandler)
    print('')
    print('AgriSage API demarree â€” v' + SDK_VERSION)
    print('  URL     : http://localhost:' + str(args.port))
    print('  Base DB : ' + DB_PATH)
    print('')
    print('  Endpoints disponibles :')
    print('    POST http://localhost:' + str(args.port) + '/v1/conseil')
    print('    GET  http://localhost:' + str(args.port) + '/v1/produits')
    print('    GET  http://localhost:' + str(args.port) + '/v1/produits/1')
    print('    GET  http://localhost:' + str(args.port) + '/v1/cultures')
    print('    GET  http://localhost:' + str(args.port) + '/health')
    print('')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Serveur arrete.')
        server.server_close()

if __name__ == '__main__':
    main()

