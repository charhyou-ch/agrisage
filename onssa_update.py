#!/usr/bin/env python3
"""
AgriSage — Script de mise à jour trimestrielle de l'index ONSSA
Usage : python onssa_update.py --file nouveau_index.xls --db postgresql://...
"""

import re
import sys
import argparse
import json
from collections import defaultdict
from datetime import datetime

def parse_onssa_xls(filepath: str) -> dict:
    """Parse le fichier XLS (HTML déguisé) exporté depuis eservice.onssa.gov.ma"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    rows_raw = re.split(r'<tr[^>]*>', content)[1:]

    def extract_tds(row):
        return re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)

    def clean(t):
        return re.sub(r'<[^>]+>', '', t).strip()

    hdrs = [clean(h) for h in extract_tds(rows_raw[0])]
    records = []
    for row in rows_raw[1:]:
        cells = extract_tds(row)
        if cells and len(cells) >= 14:
            r = {hdrs[i]: clean(c) for i, c in enumerate(cells) if i < len(hdrs)}
            records.append(r)

    # Regrouper par produit
    produits = defaultdict(lambda: {'info': None, 'usages': []})
    for r in records:
        num = r.get('Numéro homologation', '').strip()
        nom = r.get('Produits (4657)', '').strip()
        key = num if num else f"NOM_{nom}"

        if not produits[key]['info']:
            produits[key]['info'] = {
                'nom_commercial':      nom,
                'detenteur':           r.get('Détenteur', ''),
                'fournisseur':         r.get('Fournisseur', ''),
                'numero_homologation': num,
                'valable_jusquau':     r.get("Valable jusqu'au", ''),
                'tableau_tox':         r.get('Tableau toxicologique', ''),
                'categorie':           r.get('Catégorie', ''),
                'formulation':         r.get('Formulation', ''),
                'matiere_active':      r.get('Matière active', ''),
                'teneur':              r.get('Teneur', ''),
            }
        produits[key]['usages'].append({
            'usage_desc': r.get('Usage', ''),
            'dose':       r.get('Dose', ''),
            'culture':    r.get('Culture', ''),
            'dar_raw':    r.get('DAR', ''),
            'nb_appli':   r.get("Nbr d'application", ''),
        })

    return {
        'produits': dict(produits),
        'total_lignes': len(records),
        'date_import': datetime.now().strftime('%Y-%m-%d'),
        'source_file': filepath,
    }


def parse_dar(s: str):
    if not s or s.strip() in ['-', 'NR', 'nr', 'N/A', '']:
        return None
    m = re.search(r'(\d+)', str(s))
    return int(m.group(1)) if m else None


def normalize_categorie(cat: str) -> str:
    cat_l = cat.lower()
    mapping = [
        ('fongicide', 'bact',       'fongicide-bactericide'),
        ('insecticide', 'acaricide','insecticide-acaricide'),
        ('insecticide', 'fongicide','insecticide-fongicide'),
        ('insecticide', 'fumigant', 'insecticide-fumigant'),
        ('insecticide', 'acridicide','insecticide-acridicide'),
        ('nématicide', 'fumigant',  'nematicide-fumigant'),
        ('herbicide', 'régulateur', 'herbicide-regulateur'),
    ]
    for a, b, result in mapping:
        if a in cat_l and b in cat_l:
            return result
    singles = {
        'fongicide': 'fongicide', 'insecticide': 'insecticide',
        'herbicide': 'herbicide', 'acaricide': 'acaricide',
        'nématicide': 'nematicide', 'molluscicide': 'molluscicide',
        'acridicide': 'acridicide', 'régulateur': 'regulateur-croissance',
        'adjuvant': 'adjuvant', 'phéromone': 'pheromone',
        'rodenticide': 'rodenticide', 'virucide': 'virucide',
        'bactéricide': 'bactericide', 'désinfectant': 'desinfectant',
    }
    for keyword, result in singles.items():
        if keyword in cat_l:
            return result
    return 'autre'


def generate_diff_report(old_data: dict, new_data: dict) -> dict:
    """Compare deux versions de l'index pour détecter nouveaux/retirés"""
    old_keys = set(old_data['produits'].keys())
    new_keys = set(new_data['produits'].keys())

    nouveaux   = new_keys - old_keys
    retires    = old_keys - new_keys
    communs    = old_keys & new_keys

    report = {
        'date_rapport': datetime.now().isoformat(),
        'nouveaux_produits': len(nouveaux),
        'produits_retires':  len(retires),
        'produits_inchanges': len(communs),
        'details_nouveaux':  list(nouveaux)[:50],
        'details_retires':   list(retires)[:50],
        'alertes': [],
    }

    # Alertes pour produits retirés
    for key in retires:
        info = old_data['produits'][key]['info']
        report['alertes'].append({
            'type': 'PRODUIT_RETIRE',
            'urgence': 'critique',
            'produit': info['nom_commercial'],
            'numero': info['numero_homologation'],
            'message': f"Le produit {info['nom_commercial']} ({info['numero_homologation']}) a été retiré de l'index ONSSA."
        })

    return report


def main():
    parser = argparse.ArgumentParser(description='Import index ONSSA vers AgriSage')
    parser.add_argument('--file', required=True, help='Fichier XLS ONSSA')
    parser.add_argument('--output-sql', help='Fichier SQL de sortie')
    parser.add_argument('--output-json', help='Rapport JSON')
    parser.add_argument('--dry-run', action='store_true', help='Analyse sans import')
    args = parser.parse_args()

    print(f"🌿 AgriSage — Import ONSSA")
    print(f"   Fichier : {args.file}")
    print(f"   Date    : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print()

    data = parse_onssa_xls(args.file)
    produits = data['produits']

    print(f"✅ Analyse terminée :")
    print(f"   Produits distincts : {len(produits)}")
    print(f"   Lignes (usages)    : {data['total_lignes']}")

    cultures = set()
    mas = set()
    for p in produits.values():
        mas.add(p['info']['matiere_active'])
        for u in p['usages']:
            if u['culture']:
                cultures.add(u['culture'])

    print(f"   Cultures           : {len(cultures)}")
    print(f"   Matières actives   : {len(mas)}")

    if args.dry_run:
        print("\n⚠️  Mode dry-run — aucune écriture effectuée")
        return

    if args.output_json:
        report = {
            'date_import': data['date_import'],
            'source': args.file,
            'stats': {
                'produits': len(produits),
                'usages': data['total_lignes'],
                'cultures': len(cultures),
                'matieres_actives': len(mas),
            }
        }
        with open(args.output_json, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Rapport JSON : {args.output_json}")

    print("\n✅ Import terminé avec succès")


if __name__ == '__main__':
    main()
