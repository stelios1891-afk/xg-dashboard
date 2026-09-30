# -*- coding: utf-8 -*-
"""ec_expert_map.py — αντιστοιχιση ονοματων ειδικων (power rankings Eurohoops / Taking The Charge) & outrights → κωδικοι ομαδων EuroCup (el_players 'U').
Εξοδος: ec_expert.json {season 'U2022': {code: {'EH': rank, 'EH_n': N, 'TTC': rank, 'TTC_n': N, 'odds': δεκαδικη}}}"""
import json, re, unicodedata, sys
sys.stdout.reconfigure(encoding='utf-8')
B = {k: v for k, v in json.load(open('el_players.json', encoding='utf-8')).items() if v.get('comp') == 'U'}
TEAMS = {}
for g in B.values():
    for c, n in ((g['hcode'], g['home']), (g['acode'], g['away'])): TEAMS.setdefault(g['season'], {}).setdefault(c, set()).add(n)
PR = json.load(open('ec_power_rankings.json', encoding='utf-8')); OR = json.load(open('ec_outrights.json', encoding='utf-8'))
STOP = {'bc', 'kk', 'basket', 'basketball', 'club', 'de', 'the', 'bk', 'sk', 'pbc', 'cb', 'ss', 'fc', 'as', 'sp', 'en', 'sa', 'bkt', 'mne', 'ita', 'ltu',
        'ger', 'fra', 'esp', 'tur', 'gre', 'isr', 'slo', 'rou', 'pol', 'gbr', 'lat', 'bul', 'bih', 'group'}
ALIAS = {}
for canon, words in {
    'bursaspor': 'bursaspor frutti', 'tofas': 'tofas', 'jerusalem': 'jerusalem', 'telaviv': 'tel aviv', 'lokomotiv': 'lokomotiv kuban',
    'venezia': 'reyer venice venezia umana', 'cedevita': 'olimpija ljubljana cedevita zagreb', 'joventut': 'badalona joventut',
    'tenerife': 'tenerife laguna iberostar lenovo', 'malaga': 'unicaja malaga', 'gdynia': 'gdynia gydnia arka', 'zenit': 'zenit', 'kazan': 'unics kazan',
    'virtus': 'segafredo bologna virtus', 'mornar': 'mornar bar', 'levallois': 'levallois metropolitans boulogne', 'hamburg': 'hamburg towers veolia',
    'ulm': 'ulm ratiopahm ratiopharm', 'promitheas': 'patras promitheas', 'sopot': 'sopot trefl', 'bahcesehir': 'bahcesehir bahceshir', 'turin': 'turin fiat torino auxilium', 'besiktas': 'besiktas',
    'slask': 'wroclaw slask', 'lietkabelis': 'lietkabelis panevezys paneverzys', 'bourg': 'bourg bresse jl', 'cluj': 'cluj napoca',
    'telekom': 'telekom turk ankara', 'buducnost': 'buducnost podgorica voli', 'prometey': 'prometey kamianske', 'canaria': 'gran canaria herbalife dreamland',
    'valencia': 'valencia', 'partizan': 'partizan', 'andorra': 'andorra morabanc', 'trento': 'trento aquila dolomiti', 'brescia': 'brescia germani leonessa',
    'london': 'london lions', 'paris': 'paris', 'aris': 'aris', 'manresa': 'manresa baxi', 'chemnitz': 'chemnitz niners', 'panionios': 'panionios',
    'neptunas': 'neptunas klaipeda', 'tortona': 'tortona derthona', 'monaco': 'monaco', 'darussafaka': 'darussafaka', 'galatasaray': 'galatasaray',
    'rytas': 'rytas vilnius lietuvos', 'zvezda': 'crvena zvezda', 'nanterre': 'nanterre', 'limoges': 'limoges', 'asvel': 'asvel villeurbanne lyon',
    'bilbao': 'bilbao', 'budivelnyk': 'budivelnyk kyiv', 'karsiyaka': 'karsiyaka pinar', 'sassari': 'dinamo sassari banco', 'lemans': 'mans sarthe',
    'rostock': 'rostock seawolves', 'frankfurt': 'frankfurt skyliners', 'riga': 'riga zelli vef', 'siauliai': 'siauliai', 'botevgrad': 'botevgrad balkan',
    'bosna': 'sarajevo bosna', 'napoli': 'napoli', 'roma': 'roma', 'burgos': 'burgos', 'paok': 'paok', 'nizhny': 'nizhny novgorod', 'rishon': 'rishon',
    'antwerp': 'antwerp giants', 'oldenburg': 'oldenburg ewe', 'bayern': 'bayern', 'alba': 'alba berlin', 'fuenlabrada': 'fuenlabrada', 'kalev': 'kalev tallinn',
    'gipuzkoa': 'gipuzkoa', 'lietuvos': 'lietuvos', 'wolves': 'wolves', 'ludwigsburg': 'ludwigsburg', 'murcia': 'murcia ucam', 'reggio': 'reggio emilia reggiana',
    'cantu': 'cantu', 'mega': 'mega', 'igokea': 'igokea', 'zielona': 'zielona gora', 'bonn': 'bonn telekom-baskets', 'lokomotiv': 'lokomotiv kuban',
    'saratov': 'avtodor saratov', 'khimki': 'khimki', 'gran': 'gran'}.items():
    for w in words.split(): ALIAS.setdefault(w, canon)
ALIAS.pop('gran', None); ALIAS['gran'] = 'canaria'
def keys(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower()
    toks = [t for t in re.split(r'[^a-z]+', n) if t and t not in STOP]
    ks = {ALIAS[t] for t in toks if t in ALIAS}
    if 'hapoel' in toks and ('tel' in toks or 'aviv' in toks): ks.discard('jerusalem'); ks.add('telaviv')
    if 'telekom' in ks and 'bonn' in toks: ks.discard('telekom')
    return ks
def match(season, name):
    best, bs = None, 0
    kn = keys(name)
    for c, ns in TEAMS.get(season, {}).items():
        ok = set().union(*[keys(x) for x in ns])
        sc = len(kn & ok)
        if sc > bs: best, bs = c, sc
    return best
SMAP = lambda s: 'U' + s[:4]            # '2022-23' → 'U2022'
EX, miss = {}, []
for src, seas in PR.items():
    if src.startswith('_'): continue
    tag = 'EH' if src.lower().startswith('euro') else 'TTC'
    for s, v in seas.items():
        S = SMAP(s); N = len(v['ranking'])
        for r, n in enumerate(v['ranking'], 1):
            c = match(S, n)
            if c is None: miss.append((tag, S, n)); continue
            if tag in EX.get(S, {}).get(c, {}): miss.append((tag, S, n, 'ΔΙΠΛΟ→' + c)); continue
            EX.setdefault(S, {}).setdefault(c, {})[tag] = r; EX[S][c][tag + '_n'] = N
for S, v in OR.items():
    for n, o in v['odds'].items():
        c = match(S, n)
        if c is None: miss.append(('ODDS', S, n)); continue
        if 'odds' in EX.get(S, {}).get(c, {}): miss.append(('ODDS', S, n, 'ΔΙΠΛΟ→' + c)); continue
        EX.setdefault(S, {}).setdefault(c, {})['odds'] = o
json.dump(EX, open('ec_expert.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ΧΩΡΙΣ ΑΝΤΙΣΤΟΙΧΙΣΗ / ΔΙΠΛΑ:')
for m in miss: print('  ', m)
for S in sorted(EX):
    tm = TEAMS.get(S, {})
    print(S, f'EuroCup ομαδες {len(tm)} · EH {sum("EH" in d for d in EX[S].values())} · TTC {sum("TTC" in d for d in EX[S].values())} · odds {sum("odds" in d for d in EX[S].values())}'
          + ' · χωρις τιποτα: ' + ','.join(f'{c}({"/".join(sorted(tm[c]))[:25]})' for c in sorted(set(tm) - set(EX[S]))))
