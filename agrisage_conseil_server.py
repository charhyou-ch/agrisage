#!/usr/bin/env python3
"""
AgriSage API — Serveur Python stdlib uniquement
Endpoints :
  POST /v1/conseil       — Conseil phytosanitaire
  GET  /v1/produits      — Liste produits ONSSA (filtres + pagination)
  GET  /v1/produits/{id} — Detail produit ONSSA
  GET  /v1/cultures      — Liste cultures disponibles
  GET  /v1/groupes       — Référentiel IRAC / FRAC / HRAC
  GET  /health           — Statut serveur

Usage : python agrisage_conseil_server.py --port 3000 --db onssa_index.db
"""
import json, os, random, re, sqlite3, string, sys, argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

SDK_VERSION  = '1.0.0'
API_VERSION  = 'v1'
DEFAULT_PORT = 3000
DB_PATH      = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'onssa_index.db')

# ── FRAC 2025 — Fongicides ────────────────────────────────────────────────────
FRAC_DB = {
    '1': {
        'groupe': '1', 'type': 'frac',
        'nom': 'MBC fungicides — Méthyl Benzimidazole Carbamates',
        'mecanisme': 'Inhibition de la polymérisation de la tubuline (B1)',
        'risque_resistance': 'élevé',
        'classes_chimiques': ['benzimidazoles', 'thiophanates'],
        'matieres_actives': ['benomyl','carbendazim','fuberidazole','thiabendazole','thiophanate-methyl','thiophanate'],
        'recommandation': 'Max 2 applications/saison. Alterner avec groupes 2, 9, 12. Résistance très répandue sur Botrytis.',
    },
    '2': {
        'groupe': '2', 'type': 'frac',
        'nom': 'Dicarboximides',
        'mecanisme': 'Inhibition de la transduction du signal osmotique (E3)',
        'risque_resistance': 'modéré',
        'classes_chimiques': ['dicarboximides'],
        'matieres_actives': ['iprodione','procymidone','vinclozolin','chlozolinate','dimethachlone'],
        'recommandation': 'Max 2 applications/saison. Alterner avec groupes 9, 11, 12.',
    },
    '3': {
        'groupe': '3', 'type': 'frac',
        'nom': 'DMI — Inhibiteurs de la déméthylation (SBI Classe I)',
        'mecanisme': 'Inhibition de la C14-déméthylase dans la biosynthèse des stérols (G1)',
        'risque_resistance': 'modéré',
        'classes_chimiques': ['triazoles','imidazoles','pyrimidines','piperazines','pyridines'],
        'matieres_actives': ['tebuconazole','difenoconazole','propiconazole','cyproconazole',
                             'penconazole','myclobutanil','metconazole','flusilazole','flutriafol',
                             'hexaconazole','bitertanol','triadimefon','triadimenol','triticonazole',
                             'epoxiconazole','fenbuconazole','fluquinconazole','imibenconazole',
                             'mefentrifluconazole','ipconazole','simeconazole','tetraconazole',
                             'diniconazole','bromuconazole','azaconazole','etaconazole',
                             'prothioconazole','triforine','fenarimol','nuarimol',
                             'imazalil','prochloraz','triflumizole','pefurazoate',
                             'oxpoconazole','pyrifenox','pyrisoxazole'],
        'recommandation': 'Max 2 applications consécutives. Alterner avec groupes 7, 9, 11. Efficacité préventive et curative.',
    },
    '4': {
        'groupe': '4', 'type': 'frac',
        'nom': 'PA-fungicides — Phényl-Amides',
        'mecanisme': 'Inhibition de la polymérase ARN I (A1)',
        'risque_resistance': 'très élevé',
        'classes_chimiques': ['acylalanines','butyrolactones','oxazolidinones'],
        'matieres_actives': ['metalaxyl','metalaxyl-m','benalaxyl','benalaxyl-m','furalaxyl','ofurace','oxadixyl'],
        'recommandation': 'RISQUE TRÈS ÉLEVÉ. Max 1 application/saison. Toujours en mélange avec un multi-site (M3, M5). Ne jamais utiliser seul.',
    },
    '5': {
        'groupe': '5', 'type': 'frac',
        'nom': 'Morpholines / Amines (SBI Classe II)',
        'mecanisme': 'Inhibition de la ∆14-réductase et ∆8→∆7-isomérase dans la biosynthèse des stérols (G2)',
        'risque_resistance': 'modéré',
        'classes_chimiques': ['morpholines','piperidines','spiroketal-amines'],
        'matieres_actives': ['fenpropimorph','tridemorph','aldimorph','dodemorph','fenpropidin','spiroxamine'],
        'recommandation': 'Alterner avec groupes 3 ou 7. Max 3 applications/saison.',
    },
    '7': {
        'groupe': '7', 'type': 'frac',
        'nom': 'SDHI — Inhibiteurs de la Succinate Déshydrogénase',
        'mecanisme': 'Inhibition du complexe II de la chaîne respiratoire mitochondriale (C2)',
        'risque_resistance': 'modéré',
        'classes_chimiques': ['pyrazole-4-carboxamides','pyridinecarboxamides','pyrazinecarboxamides','phenyl-benzamides','oxathiin-carboxamides'],
        'matieres_actives': ['boscalid','fluopyram','fluxapyroxad','bixafen','isopyrazam','penflufen',
                             'penthiopyrad','sedaxane','benzovindiflupyr','fluindapyr','furametpyr',
                             'inpyrfluxam','isoflucypram','pydiflumetofen','pyraziflumid',
                             'thifluzamide','cyclobutrifluram','isofetamid','carboxin','oxycarboxin',
                             'fenfuram','flutolanil','mepronil','benodanil'],
        'recommandation': 'Max 2 applications/saison. Alterner avec groupes 3, 11. Résistance en progression sur Botrytis et Alternaria.',
    },
    '9': {
        'groupe': '9', 'type': 'frac',
        'nom': 'AP-fungicides — Anilino-Pyrimidines',
        'mecanisme': 'Inhibition de la biosynthèse de la méthionine (gène cgs) (D1)',
        'risque_resistance': 'modéré',
        'classes_chimiques': ['anilino-pyrimidines'],
        'matieres_actives': ['cyprodinil','pyrimethanil','mepanipyrim'],
        'recommandation': 'Max 2 applications/saison. Alterner avec groupes 2, 7, 12. Efficace contre Botrytis et Monilinia.',
    },
    '11': {
        'groupe': '11', 'type': 'frac',
        'nom': 'QoI — Inhibiteurs du Quinone outside (Strobilurines)',
        'mecanisme': 'Inhibition du complexe III cytochrome bc1 au site Qo (C3)',
        'risque_resistance': 'élevé',
        'classes_chimiques': ['methoxy-acrylates','oximino-acetamides','oximino-acetates','methoxy-carbamates','oxazolidinediones','dihydrodioxazines'],
        'matieres_actives': ['azoxystrobine','trifloxystrobine','pyraclostrobine','kresoxim-methyl',
                             'picoxystrobine','dimoxystrobine','fluoxastrobin','orysastrobin',
                             'metominostrobin','fenaminstrobin','coumoxystrobin','bifemetstrobin',
                             'enoxastrobin','flufenoxystrobin','pyraoxystrobin','famoxadone','pyribencarb'],
        'recommandation': 'RISQUE ÉLEVÉ. Max 1-2 applications/saison. Alterner avec groupes 3, 7, 9. Résistance très répandue.',
    },
    '11A': {
        'groupe': '11A', 'type': 'frac',
        'nom': 'QoI Subgroup A — Méthyltétraprole',
        'mecanisme': 'Inhibition du complexe III cytochrome bc1 au site Qo, sous-groupe A (C3)',
        'risque_resistance': 'élevé',
        'classes_chimiques': ['triazolopyrimidine'],
        'matieres_actives': ['metyltetraprole'],
        'recommandation': 'Nouveau mode d\'action QoI. Alterner avec groupes 7, 9.',
    },
    '12': {
        'groupe': '12', 'type': 'frac',
        'nom': 'PP-fungicides — Phénylpyrroles',
        'mecanisme': 'Inhibition de la transduction du signal osmotique MAP/histidine-kinase os-2 (E2)',
        'risque_resistance': 'faible',
        'classes_chimiques': ['phenylpyrroles'],
        'matieres_actives': ['fludioxonil','fenpiclonil'],
        'recommandation': 'Faible risque de résistance. Max 2 applications/saison. Excellent partenaire en mélange.',
    },
    '17': {
        'groupe': '17', 'type': 'frac',
        'nom': 'KRI — Inhibiteurs de la Kétoréductase (SBI Classe III)',
        'mecanisme': 'Inhibition de la 3-kéto-réductase dans la C4-déméthylation (G3)',
        'risque_resistance': 'faible',
        'classes_chimiques': ['hydroxyanilides','amino-pyrazolinones'],
        'matieres_actives': ['fenhexamid','fenpyrazamine'],
        'recommandation': 'Spécifique Botrytis et Monilinia. Max 2 applications/saison.',
    },
    '27': {
        'groupe': '27', 'type': 'frac',
        'nom': 'Cyanoacétamide-oximes',
        'mecanisme': 'Mécanisme inconnu (U)',
        'risque_resistance': 'modéré',
        'classes_chimiques': ['cyanoacetamide-oximes'],
        'matieres_actives': ['cymoxanil'],
        'recommandation': 'Toujours utilisé en mélange. Bon partenaire anti-résistance pour les strobilurines et phénylamides.',
    },
    '40': {
        'groupe': '40', 'type': 'frac',
        'nom': 'CAA — Acides Carboxyliques Amides',
        'mecanisme': 'Inhibition de la cellulose synthase CesA3 (H5)',
        'risque_resistance': 'modéré',
        'classes_chimiques': ['cinnamic acid amides','mandelic acid amides','valinamide carbamates'],
        'matieres_actives': ['dimethomorph','flumorph','mandipropamid','iprovalicarb',
                             'benthiavalicarb','pyrimorph','valifenalate'],
        'recommandation': 'Spécifique Oomycètes (Mildiou, Phytophthora). Alterner avec groupes 4, 27, M3.',
    },
    '49': {
        'groupe': '49', 'type': 'frac',
        'nom': 'OSBPI — Inhibiteurs de la protéine homologue de liaison aux oxystérols',
        'mecanisme': 'Inhibition du transport et stockage des lipides (F9)',
        'risque_resistance': 'faible',
        'classes_chimiques': ['piperidyl-thiazole-isoxazoline'],
        'matieres_actives': ['oxathiapiprolin','fluoxapiproline'],
        'recommandation': 'Nouveau mode d\'action anti-Oomycètes. Excellent choix en rotation.',
    },
    'M3': {
        'groupe': 'M3', 'type': 'frac',
        'nom': 'Dithiocarbamates & relatifs',
        'mecanisme': 'Activité multi-site — inhibition de plusieurs enzymes par liaisons electrophiles',
        'risque_resistance': 'faible',
        'classes_chimiques': ['dithiocarbamates','thiurams'],
        'matieres_actives': ['mancozebe','maneb','zineb','propineb','thiram','metiram','ziram','amobam','ferbam'],
        'recommandation': 'Contact multi-site. Rotation libre. Excellent partenaire en tank-mix. Préventif uniquement.',
    },
    'M4': {
        'groupe': 'M4', 'type': 'frac',
        'nom': 'Phthalimides',
        'mecanisme': 'Activité multi-site — inhibition de la respiration cellulaire (électrophile)',
        'risque_resistance': 'faible',
        'classes_chimiques': ['phthalimides'],
        'matieres_actives': ['captan','folpet','captafol'],
        'recommandation': 'Contact multi-site. Rotation libre. Préventif uniquement.',
    },
    'M5': {
        'groupe': 'M5', 'type': 'frac',
        'nom': 'Chloronitriles',
        'mecanisme': 'Activité multi-site non spécifiée',
        'risque_resistance': 'faible',
        'classes_chimiques': ['chloronitriles'],
        'matieres_actives': ['chlorothalonil'],
        'recommandation': 'Contact multi-site. Rotation libre. Préventif uniquement.',
    },
    'U6': {
        'groupe': 'U6', 'type': 'frac',
        'nom': 'Phényl-acétamides (mode d\'action inconnu)',
        'mecanisme': 'Mécanisme inconnu — probablement inhibiteurs des cétol-réductases',
        'risque_resistance': 'faible',
        'classes_chimiques': ['phenyl-acetamides'],
        'matieres_actives': ['cyflufenamid'],
        'recommandation': 'Spécifique oïdium. Alterner avec groupe 3.',
    },
}

# ── IRAC 2021 — Insecticides / Acaricides ─────────────────────────────────────
IRAC_DB = {
    '1A': {
        'groupe': '1A', 'type': 'irac',
        'nom': 'Inhibiteurs de l\'Acétylcholinestérase — Carbamates',
        'mecanisme': 'Inhibition de l\'AChE (acétylcholinestérase)',
        'risque_resistance': 'élevé',
        'classes_chimiques': ['carbamates'],
        'matieres_actives': ['carbofuran','methomyl','carbosulfan','pirimicarb','carbaryl','thiodicarb'],
        'recommandation': 'Alterner avec groupes 3A, 4A, 28. Résistance fréquente.',
    },
    '1B': {
        'groupe': '1B', 'type': 'irac',
        'nom': 'Inhibiteurs de l\'Acétylcholinestérase — Organophosphorés',
        'mecanisme': 'Inhibition de l\'AChE (acétylcholinestérase)',
        'risque_resistance': 'élevé',
        'classes_chimiques': ['organophosphores'],
        'matieres_actives': ['chlorpyrifos','acephate','dimethoate','malathion','phorate','profenofos','triazophos'],
        'recommandation': 'Alterner avec groupes 3A, 4A, 28. Résistance très fréquente. Usage restreint en Europe.',
    },
    '3A': {
        'groupe': '3A', 'type': 'irac',
        'nom': 'Pyréthrines & Pyréthrinoïdes',
        'mecanisme': 'Modulation des canaux sodiques voltage-dépendants',
        'risque_resistance': 'élevé',
        'classes_chimiques': ['pyrethrinoïdes','pyréthrines naturelles'],
        'matieres_actives': ['deltamethrine','lambda-cyhalothrine','alpha-cypermethrine','cypermethrine',
                             'bifenthrine','esfenvalerate','tefluthrine','permethrine','etofenprox'],
        'recommandation': 'RISQUE ÉLEVÉ. Max 1-2 applications/saison. Alterner avec groupes 4A, 5, 28. Très dangereux pour abeilles.',
    },
    '4A': {
        'groupe': '4A', 'type': 'irac',
        'nom': 'Néonicotinoïdes',
        'mecanisme': 'Agonistes compétitifs des récepteurs nicotiniques de l\'acétylcholine (nAChR)',
        'risque_resistance': 'élevé',
        'classes_chimiques': ['neonicotinoïdes'],
        'matieres_actives': ['imidaclopride','thiaméthoxame','acetamipride','clothianidine',
                             'nitenpyrame','thiaclopride','dinotefurane'],
        'recommandation': 'RISQUE TRÈS ÉLEVÉ. Max 1 application/saison. Alterner avec groupes 1B, 3A, 5. Très dangereux abeilles. Restrictions UE.',
    },
    '4C': {
        'groupe': '4C', 'type': 'irac',
        'nom': 'Sulfoximines',
        'mecanisme': 'Agonistes compétitifs des récepteurs nicotiniques de l\'acétylcholine (nAChR)',
        'risque_resistance': 'modéré',
        'classes_chimiques': ['sulfoximines'],
        'matieres_actives': ['sulfoxaflor'],
        'recommandation': 'Alterner avec groupes 3A, 5, 28. Risque modéré pour abeilles.',
    },
    '4D': {
        'groupe': '4D', 'type': 'irac',
        'nom': 'Buténolides',
        'mecanisme': 'Agonistes des récepteurs nicotiniques de l\'acétylcholine (nAChR)',
        'risque_resistance': 'modéré',
        'classes_chimiques': ['buténolides'],
        'matieres_actives': ['flupyradifurone'],
        'recommandation': 'Alternative aux néonicotinoïdes. Alterner avec groupes 3A, 5, 28.',
    },
    '5': {
        'groupe': '5', 'type': 'irac',
        'nom': 'Spinosynes',
        'mecanisme': 'Modulateurs allostériques des récepteurs nAChR (site I)',
        'risque_resistance': 'faible',
        'classes_chimiques': ['spinosynes'],
        'matieres_actives': ['spinosad','spinetoram'],
        'recommandation': 'Faible risque. Max 2 applications/saison. Alterner avec groupes 3A, 4A, 28. Risque modéré pour abeilles.',
    },
    '6': {
        'groupe': '6', 'type': 'irac',
        'nom': 'Avermectines & Milbémycines',
        'mecanisme': 'Activation allostérique des canaux chlorure glutamate-dépendants (GluCl)',
        'risque_resistance': 'modéré',
        'classes_chimiques': ['avermectines','milbemycines'],
        'matieres_actives': ['abamectine','emamectine','milbemectine','lepimectine'],
        'recommandation': 'Max 2 applications/saison. Alterner avec groupes 5, 23, 28. Risque modéré pour abeilles.',
    },
    '7C': {
        'groupe': '7C', 'type': 'irac',
        'nom': 'Pyriproxyfène — Mimétique de l\'hormone juvénile',
        'mecanisme': 'Mimétique de l\'hormone juvénile',
        'risque_resistance': 'faible',
        'classes_chimiques': ['analogues hormone juvénile'],
        'matieres_actives': ['pyriproxyfene'],
        'recommandation': 'Faible risque. Efficace sur aleurodes, cochenilles. Rotation libre.',
    },
    '10B': {
        'groupe': '10B', 'type': 'irac',
        'nom': 'Etoxazole — Inhibiteur de biosynthèse de chitine acariens',
        'mecanisme': 'Inhibition de CHS1 (chitine synthase 1)',
        'risque_resistance': 'faible',
        'classes_chimiques': ['diphenyl oxazoline'],
        'matieres_actives': ['etoxazole'],
        'recommandation': 'Spécifique acariens. Max 1 application/saison. Rotation libre entre saisons.',
    },
    '23': {
        'groupe': '23', 'type': 'irac',
        'nom': 'Inhibiteurs de l\'Acetyl-CoA carboxylase — Tétroniques & Tétramiques',
        'mecanisme': 'Inhibition de l\'Acetyl-CoA carboxylase (ACCase)',
        'risque_resistance': 'faible',
        'classes_chimiques': ['acides tétroniques','acides tétramiques'],
        'matieres_actives': ['spirodiclofen','spiromesifen','spirotetramat','spiropidion'],
        'recommandation': 'Faible risque. Efficace sur acariens et pucerons. Max 1-2 applications/saison.',
    },
    '28': {
        'groupe': '28', 'type': 'irac',
        'nom': 'Diamides — Modulateurs du Récepteur Ryanodine',
        'mecanisme': 'Modulation des récepteurs ryanodine (canaux calcium)',
        'risque_resistance': 'faible',
        'classes_chimiques': ['diamides anthranilamides','diamides phthalamides'],
        'matieres_actives': ['chlorantraniliprole','cyantraniliprole','flubendiamide',
                             'cyclaniliprole','tetraniliprole'],
        'recommandation': 'EXCELLENT CHOIX anti-résistance. Max 2 applications/saison. Très faible toxicité abeilles. Efficace sur Lépidoptères.',
    },
    '29': {
        'groupe': '29', 'type': 'irac',
        'nom': 'Flonicamide — Modulateur organes chordotonaux',
        'mecanisme': 'Modulation des organes chordotonaux (site cible non confirmé)',
        'risque_resistance': 'faible',
        'classes_chimiques': ['acides tétroniques fluorés'],
        'matieres_actives': ['flonicamide'],
        'recommandation': 'Spécifique pucerons et aleurodes. Faible risque. Rotation libre.',
    },
}

# ── HRAC 2026 — Herbicides ─────────────────────────────────────────────────────
HRAC_DB = {
    '1': {
        'groupe': '1', 'type': 'hrac', 'legacy': 'A',
        'nom': 'Inhibiteurs de l\'Acetyl-CoA Carboxylase (ACCase)',
        'mecanisme': 'Inhibition de l\'ACCase — blocage de la biosynthèse des acides gras',
        'risque_resistance': 'élevé',
        'classes_chimiques': ['cyclohexanediones (DIMs)','aryloxyphenoxypropionates (FOPs)','phényl-pyrazoline'],
        'matieres_actives': ['clethodim','cycloxydim','sethoxydim','tralkoxydim','profoxydim',
                             'clodinafop-propargyl','cyhalofop-butyl','diclofop-methyl',
                             'fenoxaprop-ethyl','fluazifop-butyl','haloxyfop-methyl','quizalofop-ethyl',
                             'pinoxaden'],
        'recommandation': 'Spécifique graminées. Alterner avec groupe 2. Résistance fréquente sur ray-grass.',
    },
    '2': {
        'groupe': '2', 'type': 'hrac', 'legacy': 'B',
        'nom': 'Inhibiteurs de l\'Acétolactate Synthase (ALS)',
        'mecanisme': 'Inhibition de l\'ALS — blocage de la biosynthèse des acides aminés ramifiés',
        'risque_resistance': 'élevé',
        'classes_chimiques': ['sulfonylurées','imidazolinones','triazolopyrimidines','pyrimidinylbenzoates','sulfonanilides'],
        'matieres_actives': ['metsulfuron-methyl','chlorsulfuron','tribenuron-methyl','nicosulfuron',
                             'rimsulfuron','mesosulfuron-methyl','florasulam','pyroxsulam',
                             'penoxsulam','imazamox','imazethapyr','imazapyr','imazapic',
                             'flumetsulam','diclosulam','cloransulam-methyl','flucarbazone-na'],
        'recommandation': 'RISQUE ÉLEVÉ. Max 1 application/saison sur même culture. Alterner avec groupes 1, 10, 15. Résistances multiples répandues.',
    },
    '3': {
        'groupe': '3', 'type': 'hrac', 'legacy': 'K1',
        'nom': 'Inhibiteurs de l\'Assemblage des Microtubules (α-Tubuline)',
        'mecanisme': 'Inhibition de la polymérisation de la tubuline alpha',
        'risque_resistance': 'modéré',
        'classes_chimiques': ['dinitroanilines','phosphoroamidates','pyridines'],
        'matieres_actives': ['trifluralin','pendimethalin','ethalfluralin','benefin','prodiamine',
                             'butralin','dithiopyr','oryzalin'],
        'recommandation': 'Préemergence uniquement. Alterner avec groupes 15, 9. Incorporer au sol.',
    },
    '4': {
        'groupe': '4', 'type': 'hrac', 'legacy': 'O',
        'nom': 'Auxin Mimics — Herbicides Auxiniques',
        'mecanisme': 'Mimétisme de l\'auxine — perturbation de la croissance cellulaire',
        'risque_resistance': 'modéré',
        'classes_chimiques': ['phenoxycarboxylates','pyridyloxycarboxylates','6-arylpicolinates','benzoates','quinolinecarboxylates'],
        'matieres_actives': ['2,4-D','MCPA','dichlorprop','mecoprop','2,4-DB','MCPB',
                             'triclopyr','fluroxypyr','clopyralid','picloram','aminopyralid',
                             'halauxifen','florpyrauxifen','dicamba','quinclorac','quinmerac'],
        'recommandation': 'Spécifique dicotylédones. Attention dérive sur cultures sensibles (vigne, tournesol).',
    },
    '5': {
        'groupe': '5', 'type': 'hrac', 'legacy': 'C1,2',
        'nom': 'Inhibiteurs de la Photosynthèse au PS II — Sérine 264',
        'mecanisme': 'Blocage du transfert d\'électrons au niveau de la protéine D1 (liaison sérine 264)',
        'risque_resistance': 'élevé',
        'classes_chimiques': ['triazines','urées','triazinones','phénylcarbamates','amides','uraciles'],
        'matieres_actives': ['atrazine','simazine','terbuthylazine','propazine','ametryne',
                             'diuron','linuron','isoproturon','chlorotoluron','fluometuron',
                             'metribuzin','metamitron','hexazinone','desmedipham','phenmedipham'],
        'recommandation': 'Résistance très répandue. Alterner avec groupes 4, 9, 15. Atrazine interdite dans de nombreux pays.',
    },
    '9': {
        'groupe': '9', 'type': 'hrac', 'legacy': 'G',
        'nom': 'Inhibiteurs de l\'EPSPS (Glyphosate)',
        'mecanisme': 'Inhibition de l\'énolpyruvyl shikimate phosphate synthase — blocage voie shikimate',
        'risque_resistance': 'élevé',
        'classes_chimiques': ['acides phosphoniques'],
        'matieres_actives': ['glyphosate'],
        'recommandation': 'Herbicide total. Résistances en forte progression mondiale. Max 1-2 applications/saison. Pas de rotation possible (mode unique).',
    },
    '14': {
        'groupe': '14', 'type': 'hrac', 'legacy': 'E',
        'nom': 'Inhibiteurs de la Protoporphyrinogène Oxydase (PPO)',
        'mecanisme': 'Inhibition de la PPO — accumulation de protoporphyrine IX, génération de ROS',
        'risque_resistance': 'modéré',
        'classes_chimiques': ['N-phénylimides','diphényl-éthers','N-phényltriazolinones','N-phényloxadiazolones'],
        'matieres_actives': ['fomesafen','acifluorfen','lactofen','oxyfluorfen','bifenox',
                             'carfentrazone-ethyl','sulfentrazone','flumiclorac-pentyl','flumioxazin',
                             'saflufenacil','tiafenacil','epyrifenacil','trifludimoxazin',
                             'oxadiargyl','oxadiazon'],
        'recommandation': 'Alterner avec groupes 2, 5, 9. Contact rapide. Application préemergence ou post-précoce.',
    },
    '15': {
        'groupe': '15', 'type': 'hrac', 'legacy': 'K3',
        'nom': 'Inhibiteurs de la Synthèse des Acides Gras à Très Longue Chaîne (VLCFA)',
        'mecanisme': 'Inhibition de l\'élongase — blocage de la biosynthèse des VLCFA',
        'risque_resistance': 'modéré',
        'classes_chimiques': ['α-chloroacétamides','α-thioacétamides','α-oxyacétamides','thiocarbamates','isoxazolines','benzofuranes'],
        'matieres_actives': ['metolachlor','acetochlor','alachlor','dimethenamid','pretilachlor',
                             'butachlor','dimethachlor','pethoxamid','flufenacet','pyroxasulfone',
                             'fenoxasulfone','mefenacet','prosulfocarb','thiobencarb','triallate',
                             'EPTC','molinate','benfuresate','cafenstrole'],
        'recommandation': 'Préemergence principalement. Efficace graminées et certaines dicotylédones. Alterner avec groupes 2, 9.',
    },
    '27': {
        'groupe': '27', 'type': 'hrac', 'legacy': 'F2',
        'nom': 'Inhibiteurs de l\'HPPD — Hydroxyphénylpyruvate Dioxygénase',
        'mecanisme': 'Inhibition de l\'HPPD — blocage de la biosynthèse du tocophérol et plastoquinone',
        'risque_resistance': 'faible',
        'classes_chimiques': ['triketones','pyrazoles','isoxazoles'],
        'matieres_actives': ['mesotrione','tembotrione','sulcotrione','tefuryltrione','bicyclopyrone',
                             'fenquinotrione','benzobicyclon','pyrasulfotole','topramezone',
                             'pyrazolynate','tolpyralate','isoxaflutole'],
        'recommandation': 'Faible risque de résistance. Bon choix en rotation. Efficace sur graminées et dicotylédones.',
    },
}

# ── Utilitaires ──────────────────────────────────────────────────────────────

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
                return {'groupe': g, **{k:v for k,v in info.items() if k not in ('matieres_actives','classes_chimiques')}}
    return None

def get_irac(ma):
    base = get_ma_base(ma)
    for g, info in IRAC_DB.items():
        for active in info['matieres_actives']:
            if active.lower() in base or base in active.lower():
                return {'groupe': g, **{k:v for k,v in info.items() if k not in ('matieres_actives','classes_chimiques')}}
    return None

def get_risque_abeilles(ma):
    base = get_ma_base(ma)
    TOXICITE = {
        'lambda cyhalothrine':'élevé','cyperméthrine':'élevé','deltamethrine':'élevé',
        'alpha-cyperméthrine':'élevé','bifenthrine':'élevé',
        'imidaclopride':'élevé','thiamétoxame':'élevé','clothianidine':'élevé','acetamipride':'modéré',
        'spinosad':'modéré','abamectine':'modéré','spirotétramat':'modéré','spinetoram':'modéré',
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
    frac = get_frac(ma)
    irac = get_irac(ma)
    p['groupe_frac']      = frac['groupe'] if frac else None
    p['groupe_irac']      = irac['groupe'] if irac else None
    p['risque_abeilles']  = get_risque_abeilles(ma)
    p['risque_resistance']= (frac or irac or {}).get('risque_resistance')
    return p

PAGE_SIZE = 50
STADES_VALIDES   = {'germination','levee','vegetation','floraison','fructification','recolte','post-recolte'}
VALID_KEY_PREFIXES = ('as_test_', 'as_live_')

# ── Moteur conseil ────────────────────────────────────────────────────────────

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
        if dar_max is not None: args2.append(int(dar_max))
        rows = [dict(r) for r in cur.execute(sql2, args2).fetchall()]
    conn.close()

    if not rows:
        raise ValueError("Aucun produit homologue ONSSA pour '" + culture + "'")

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
        '3A':'Risque élevé pyrethrinoides. Alterner avec IRAC 5, 6 ou 28.',
        '4A':'Risque très élevé neonicotinoides. Alterner avec IRAC 5 ou 28.',
        '6':'Alterner avec IRAC 28 ou 5. Max 2 applications/saison.',
    }

    for r in rows:
        ma = r.get('matiere_active','')
        frac = get_frac(ma); irac = get_irac(ma); ra = get_risque_abeilles(ma)
        tox  = r.get('tableau_toxicologique','')
        score = 100
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
        r.update({'_score':score,'_frac':frac,'_irac':irac,'_ra':ra})

    rows.sort(key=lambda x: -x['_score'])
    best = rows[0]

    alertes = []
    if stade == 'floraison':
        ra = best['_ra']
        if   ra == 'élevé':  alertes.append('DANGEREUX abeilles. Application interdite en floraison.')
        elif ra == 'modéré': alertes.append('Risque modéré pollinisateurs. Appliquer après 19h.')
        else:                alertes.append('Floraison : appliquer de préférence après 19h.')
    if best['_frac'] and best['_frac']['groupe'] in hist_frac:
        alertes.append('FRAC ' + best['_frac']['groupe'] + ' deja utilise. Risque resistance.')
    if best['_irac'] and best['_irac']['groupe'] in hist_irac:
        alertes.append('IRAC ' + best['_irac']['groupe'] + ' deja utilise. Risque resistance.')
    if best.get('tableau_toxicologique') in ('Ia','Ib'):
        alertes.append('Toxicite classe ' + str(best.get('tableau_toxicologique')) + ' - EPI obligatoires.')

    best_fg = best['_frac']['groupe'] if best['_frac'] else None
    best_ig = best['_irac']['groupe'] if best['_irac'] else None
    seen = {best['id']}; alts = []
    for r in rows[1:]:
        if r['id'] in seen or len(alts) >= nb_alt: break
        r_fg = r['_frac']['groupe'] if r['_frac'] else None
        r_ig = r['_irac']['groupe'] if r['_irac'] else None
        if r_fg != best_fg or r_ig != best_ig:
            alts.append({'produit':r['nom_commercial'],'matiere_active':r['matiere_active'],
                         'groupe_frac':r_fg,'groupe_irac':r_ig,'dar':r.get('dar_jours'),'dose':r.get('dose')})
            seen.add(r['id'])

    rot = ROTATION_NOTES.get(best['_frac']['groupe'] if best['_frac'] else '') or \
          ROTATION_NOTES.get(best['_irac']['groupe'] if best['_irac'] else '')

    return {
        'conseil_id':         conseil_id(),
        'produit':            best['nom_commercial'],
        'matiere_active':     best['matiere_active'],
        'numero_amm':         best.get('numero_homologation'),
        'detenteur':          best.get('detenteur'),
        'dose':               best.get('dose'),
        'dar':                best.get('dar_jours'),
        'dar_raw':            best.get('dar_raw'),
        'nb_applications':    best.get('nb_applications'),
        'formulation':        best.get('formulation'),
        'categorie':          best.get('categorie'),
        'type_produit':       best.get('type_produit'),
        'usage_homologue':    best.get('usage_desc'),
        'culture_homologuee': best.get('usage_culture'),
        'groupe_frac':        best['_frac']['groupe'] if best['_frac'] else None,
        'groupe_irac':        best['_irac']['groupe'] if best['_irac'] else None,
        'groupe_hrac':        None,
        'risque_resistance':  (best['_frac'] or best['_irac'] or {}).get('risque_resistance'),
        'mecanisme_action':   (best['_frac'] or best['_irac'] or {}).get('mecanisme'),
        'rotation_note':      rot,
        'homologue_onssa':    True,
        'valable_jusquau':    best.get('valable_jusquau'),
        'tableau_toxicologique': best.get('tableau_toxicologique'),
        'risque_abeilles':    best['_ra'],
        'risque_auxiliaires': 'faible',
        'alertes':            alertes,
        'alternatives':       alts,
        'meta': {'culture_demandee':culture,'ravageur_demande':ravageur,'stade':stade,
                 'dar_max_demande':dar_max,'nb_produits_trouves':len(rows),'score_principal':best['_score']},
        'timestamp': datetime.now().isoformat(),
    }

# ── GET /produits ─────────────────────────────────────────────────────────────

def get_produits(qs):
    culture     = qs.get('culture',     [None])[0]
    usage       = qs.get('usage',       [None])[0]
    ma          = qs.get('ma',          [None])[0]
    groupe_frac = qs.get('groupe_frac', [None])[0]
    groupe_irac = qs.get('groupe_irac', [None])[0]
    q           = qs.get('q',           [None])[0]
    try: page = max(1, int(qs.get('page', ['1'])[0]))
    except ValueError: page = 1

    conn = db(); cur = conn.cursor()
    sql_select = 'SELECT DISTINCT p.id, p.nom_commercial, p.detenteur, p.fournisseur, p.numero_homologation, p.valable_jusquau, p.tableau_toxicologique, p.categorie, p.type_produit, p.formulation, p.matiere_active, p.teneur FROM produits p'
    sql_where = 'WHERE 1=1'; args = []
    needs_join = bool(culture or groupe_frac or groupe_irac)
    if needs_join: sql_select += ' LEFT JOIN usages u ON p.id = u.produit_id'
    if culture: sql_where += ' AND LOWER(u.culture) LIKE ?'; args.append('%' + culture.lower() + '%')
    if usage:   sql_where += ' AND p.type_produit LIKE ?'; args.append('%' + usage.lower() + '%')
    if ma:      sql_where += ' AND LOWER(p.matiere_active) LIKE ?'; args.append('%' + ma.lower() + '%')
    if q:
        sql_where += ' AND (LOWER(p.nom_commercial) LIKE ? OR LOWER(p.matiere_active) LIKE ?)'
        args.extend(['%' + q.lower() + '%', '%' + q.lower() + '%'])
    if groupe_frac:
        ma_keys = []
        if groupe_frac in FRAC_DB: ma_keys = FRAC_DB[groupe_frac]['matieres_actives']
        if ma_keys:
            placeholders = ' OR '.join(['LOWER(p.matiere_active) LIKE ?' for _ in ma_keys])
            sql_where += ' AND (' + placeholders + ')'; args.extend(['%' + k + '%' for k in ma_keys])
    if groupe_irac:
        ma_keys = []
        if groupe_irac in IRAC_DB: ma_keys = IRAC_DB[groupe_irac]['matieres_actives']
        if ma_keys:
            placeholders = ' OR '.join(['LOWER(p.matiere_active) LIKE ?' for _ in ma_keys])
            sql_where += ' AND (' + placeholders + ')'; args.extend(['%' + k + '%' for k in ma_keys])
    sql_count = 'SELECT COUNT(DISTINCT p.id) FROM produits p'
    if needs_join: sql_count += ' LEFT JOIN usages u ON p.id = u.produit_id'
    sql_count += ' ' + sql_where
    total = cur.execute(sql_count, args).fetchone()[0]
    offset = (page - 1) * PAGE_SIZE
    rows = [dict(r) for r in cur.execute(sql_select + ' ' + sql_where + ' ORDER BY p.nom_commercial ASC LIMIT ? OFFSET ?', args + [PAGE_SIZE, offset]).fetchall()]
    for p in rows:
        enrich_produit(p)
        cr = cur.execute('SELECT DISTINCT culture FROM usages WHERE produit_id=? AND culture != "" ORDER BY culture LIMIT 20', (p['id'],)).fetchall()
        p['cultures_homologuees'] = [r['culture'] for r in cr]
        dr = cur.execute('SELECT MIN(dar_jours) dar_min, MAX(dar_jours) dar_max FROM usages WHERE produit_id=? AND dar_jours IS NOT NULL', (p['id'],)).fetchone()
        p['dar_min'] = dr['dar_min'] if dr else None; p['dar_max'] = dr['dar_max'] if dr else None
    conn.close()
    pages_total = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return {'data': rows, 'pagination': {'page':page,'par_page':PAGE_SIZE,'total':total,'pages_total':pages_total}}

# ── GET /produits/{id} ────────────────────────────────────────────────────────

def get_produit_by_id(produit_id):
    conn = db(); cur = conn.cursor()
    row = cur.execute('SELECT * FROM produits WHERE id = ?', (produit_id,)).fetchone()
    if not row: conn.close(); return None
    p = dict(row); enrich_produit(p)
    usages = [dict(r) for r in cur.execute('SELECT culture, usage_desc, dose, dar_raw, dar_jours, nb_applications FROM usages WHERE produit_id=? ORDER BY culture', (produit_id,)).fetchall()]
    p['usages'] = usages
    p['cultures_homologuees'] = sorted({u['culture'] for u in usages if u['culture']})
    frac = get_frac(p.get('matiere_active','')); irac = get_irac(p.get('matiere_active',''))
    if frac: p['frac_info'] = frac
    if irac: p['irac_info'] = irac
    conn.close(); return p

# ── GET /cultures ─────────────────────────────────────────────────────────────

def get_cultures(qs):
    q = qs.get('q', [None])[0]
    try: page = max(1, int(qs.get('page', ['1'])[0]))
    except ValueError: page = 1
    conn = db(); cur = conn.cursor()
    sql_where = "WHERE nom_fr != ''"; args = []
    if q: sql_where += ' AND LOWER(nom_fr) LIKE ?'; args.append('%' + q.lower() + '%')
    total = cur.execute('SELECT COUNT(*) FROM cultures ' + sql_where, args).fetchone()[0]
    offset = (page - 1) * PAGE_SIZE
    rows = [dict(r) for r in cur.execute('SELECT id, nom_fr, nb_produits FROM cultures ' + sql_where + ' ORDER BY nb_produits DESC, nom_fr ASC LIMIT ? OFFSET ?', args + [PAGE_SIZE, offset]).fetchall()]
    conn.close()
    pages_total = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return {'data': rows, 'total': total, 'pagination': {'page':page,'par_page':PAGE_SIZE,'total':total,'pages_total':pages_total}}

# ── GET /groupes ──────────────────────────────────────────────────────────────

def get_groupes(qs):
    """
    Paramètres :
      type   — 'frac' | 'irac' | 'hrac' (requis)
      groupe — numéro de groupe (optionnel)
      ma     — recherche par matière active (optionnel)
      risque — filtre par niveau de risque (optionnel)
    """
    type_g  = qs.get('type',   [None])[0]
    groupe  = qs.get('groupe', [None])[0]
    ma      = qs.get('ma',     [None])[0]
    risque  = qs.get('risque', [None])[0]

    if not type_g or type_g.lower() not in ('frac','irac','hrac'):
        raise ValueError("Paramètre 'type' requis : frac | irac | hrac")

    type_g = type_g.lower()
    db_map = {'frac': FRAC_DB, 'irac': IRAC_DB, 'hrac': HRAC_DB}
    source = db_map[type_g]

    results = []
    for g_id, info in source.items():
        item = {
            'type':               type_g,
            'groupe':             g_id,
            'nom':                info.get('nom',''),
            'mecanisme':          info.get('mecanisme',''),
            'risque_resistance':  info.get('risque_resistance',''),
            'classes_chimiques':  info.get('classes_chimiques',[]),
            'matieres_actives':   info.get('matieres_actives',[]),
            'recommandation':     info.get('recommandation',''),
        }
        if type_g == 'hrac':
            item['legacy_hrac'] = info.get('legacy','')

        # Filtres
        if groupe and g_id.upper() != groupe.upper():
            continue
        if risque and info.get('risque_resistance','').lower() != risque.lower():
            continue
        if ma:
            ma_lower = ma.lower()
            found = any(ma_lower in active.lower() or active.lower() in ma_lower
                       for active in info.get('matieres_actives',[]))
            if not found:
                continue

        results.append(item)

    return {'type': type_g, 'data': results, 'total': len(results)}

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

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.end_headers()

    def check_auth(self):
        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            self.send_json(401, {'error':{'code':'UNAUTHORIZED','message':'Header requis : Authorization: Bearer as_test_XXXX'}})
            return False
        key = auth.replace('Bearer ', '').strip()
        if not any(key.startswith(p) for p in VALID_KEY_PREFIXES):
            self.send_json(401, {'error':{'code':'UNAUTHORIZED','message':'Cle invalide. Prefixe requis : as_test_ ou as_live_'}})
            return False
        return True

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip('/')
        qs     = parse_qs(parsed.query)

        if path in ('/health', ''):
            return self.send_json(200, {
                'status':'ok', 'service':'AgriSage API', 'version':SDK_VERSION,
                'endpoints':['POST /v1/conseil','GET /v1/produits','GET /v1/produits/{id}',
                             'GET /v1/cultures','GET /v1/groupes'],
                'time': datetime.now().isoformat(),
            })

        if not self.check_auth(): return
        start = datetime.now()

        m = re.match(r'^/' + API_VERSION + r'/produits/(\d+)$', path)
        if m:
            pid = int(m.group(1))
            try:
                result = get_produit_by_id(pid)
                if result is None:
                    return self.send_json(404, {'error':{'code':'NOT_FOUND','message':'Produit ' + str(pid) + ' introuvable.'}})
                elapsed = (datetime.now() - start).total_seconds() * 1000
                return self.send_json(200, result, {'X-Response-Time':'{:.0f}ms'.format(elapsed)})
            except Exception as e: return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        if path == '/' + API_VERSION + '/produits':
            try:
                result  = get_produits(qs)
                elapsed = (datetime.now() - start).total_seconds() * 1000
                return self.send_json(200, result, {'X-Response-Time':'{:.0f}ms'.format(elapsed)})
            except Exception as e: return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        if path == '/' + API_VERSION + '/cultures':
            try:
                result  = get_cultures(qs)
                elapsed = (datetime.now() - start).total_seconds() * 1000
                return self.send_json(200, result, {'X-Response-Time':'{:.0f}ms'.format(elapsed)})
            except Exception as e: return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        if path == '/' + API_VERSION + '/groupes':
            try:
                result  = get_groupes(qs)
                elapsed = (datetime.now() - start).total_seconds() * 1000
                return self.send_json(200, result, {'X-Response-Time':'{:.0f}ms'.format(elapsed)})
            except ValueError as e:
                return self.send_json(400, {'error':{'code':'INVALID_PARAM','message':str(e),'suggestion':"Utilisez ?type=frac, ?type=irac ou ?type=hrac"}})
            except Exception as e: return self.send_json(500, {'error':{'code':'SERVER_ERROR','message':str(e)}})

        self.send_json(404, {'error':{'code':'NOT_FOUND','message':'Endpoint introuvable.'}})

    def do_POST(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip('/')
        start  = datetime.now()
        if not self.check_auth(): return
        length = int(self.headers.get('Content-Length', 0))
        try:
            raw  = self.rfile.read(length).decode('utf-8') if length else '{}'
            body = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.send_json(400, {'error':{'code':'INVALID_JSON','message':'Body JSON invalide.'}})

        if path == '/' + API_VERSION + '/conseil':
            return self._handle_conseil(body, start)
        self.send_json(404, {'error':{'code':'NOT_FOUND','message':'Endpoint introuvable.'}})

    def _handle_conseil(self, body, start):
        errors = []
        if not body.get('culture'):  errors.append({'champ':'culture', 'message':'Requis.'})
        if not body.get('ravageur'): errors.append({'champ':'ravageur','message':'Requis.'})
        stade = str(body.get('stade','')).lower().strip()
        if not stade: errors.append({'champ':'stade','message':'Requis.'})
        elif stade not in STADES_VALIDES:
            errors.append({'champ':'stade','message':'Valeurs: ' + ', '.join(sorted(STADES_VALIDES))})
        if errors:
            return self.send_json(400,{'error':{'code':'INVALID_PARAM','message':'Parametre(s) invalide(s).','details':errors}})
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
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body_bytes)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('X-Response-Time', '{:.0f}ms'.format(elapsed))
            self.send_header('X-RateLimit-Remaining', '9999')
            self.end_headers()
            self.wfile.write(body_bytes)
        except ValueError as e:
            self.send_json(404,{'error':{'code':'CULTURE_NOT_FOUND','message':str(e)}})
        except Exception as e:
            print('[ERROR]', e)
            self.send_json(500,{'error':{'code':'SERVER_ERROR','message':str(e)}})

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

    server = HTTPServer((args.host, args.port), AgriSageHandler)
    print('')
    print('AgriSage API demarree — v' + SDK_VERSION)
    print('  URL     : http://localhost:' + str(args.port))
    print('  Base DB : ' + DB_PATH)
    print('')
    print('  Endpoints :')
    print('    POST http://localhost:' + str(args.port) + '/v1/conseil')
    print('    GET  http://localhost:' + str(args.port) + '/v1/produits')
    print('    GET  http://localhost:' + str(args.port) + '/v1/produits/1')
    print('    GET  http://localhost:' + str(args.port) + '/v1/cultures')
    print('    GET  http://localhost:' + str(args.port) + '/v1/groupes?type=frac')
    print('    GET  http://localhost:' + str(args.port) + '/v1/groupes?type=irac')
    print('    GET  http://localhost:' + str(args.port) + '/v1/groupes?type=hrac')
    print('    GET  http://localhost:' + str(args.port) + '/health')
    print('')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Serveur arrete.')
        server.server_close()

if __name__ == '__main__':
    main()
