# -*- coding: utf-8 -*-
"""xi_variants_build.py — 21/10/2026 (Στελιος «οκ ελεγξε τα ολα»): ΠΑΡΑΛΛΑΓΕΣ του νικητη (αξια + εμπιστοσυνη προπονητη).
ΕΜΠΙΣΤΟΣΥΝΗ: παραθυρο 5 / 10 / 20 ματς × (λεπτα | εκκινησεις) — «οταν ηταν στην αποστολη, ποσα λεπτα επαιξε / ποσες φορες ξεκινησε»
ΑΞΙΑ: (α) μεσος ln(αξιας) των 11 [σημερινη] · (β) ln(αθροισμα αξιων) · (γ) ln(αξια) ως μεριδιο της ομαδας (αξια παικτη / μεση αξια ροστερ, ανα σεζον)
ΘΕΣΕΙΣ: για καθε μετρο και ξεχωριστα για τερματοφυλακα / αμυνα / μεσους / επιθεση.
Ολα με πραγματικες ενδεκαδες, μονο πληροφορια ΠΡΙΝ το ματς· Δ = ενδεκαδα σημερα − φθινων (0.9) μεσος προηγουμενων (ανα ομαδα, ανα μετρο/θεση).
ΕΞΟΔΟΣ: xi_variants_rows.csv"""
import sys, json, glob, re, collections, datetime as dt, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
LG = ('EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'Eredivisie', 'PrimeiraLiga')
FM = {}
for lg in LG:
    for f in glob.glob(f'data_{lg}_*.json'):
        sea = re.search(r'_(\d{4})\.json$', f).group(1)
        for k, v in json.load(open(f, encoding='utf-8')).items():
            try: d = dt.datetime.strptime(v['date'], '%a, %b %d, %Y, %H:%M UTC')
            except Exception: continue
            FM[str(k)] = dict(lg=lg, sea=sea, date=d, hid=v['home']['id'], aid=v['away']['id'])
SQ = json.load(open('core7_squads.json', encoding='utf-8'))
PM = json.load(open('player_matches.json', encoding='utf-8'))
VAL = {}
for f in ('core7_player_values.json', 'euro_player_values.json'):
    for k, v in json.load(open(f, encoding='utf-8')).items():
        if v.get('hist') and str(k) not in VAL: VAL[str(k)] = [(h[0], h[1]) for h in v['hist'] if h[1]]
ORDER = sorted([k for k in FM if k in SQ and SQ[k].get('h') and SQ[k].get('a')], key=lambda k: FM[k]['date'])
PL_POS = {}
for k in ORDER:
    for s in ('h', 'a'):
        for e in ((PM.get(k) or {}).get(s) or {}).get('p', []) or []:
            PL_POS[str(e[0])] = e[3] if e[3] in (0, 1, 2, 3) else 2
def value_at(pid, ds):
    h = VAL.get(pid)
    if not h: return None
    v = None
    for t, x in h:
        if t <= ds: v = x
        else: break
    return v if v is not None else h[0][1]
TEAM_HIST = collections.defaultdict(list)            # team -> [(mins dict, starters set)]
SQUAD_VAL = collections.defaultdict(dict)            # (team, sea) -> pid -> ln value (ροστερ οσων εχουν παιξει)
BASE = collections.defaultdict(dict)
GRP = {0: 'gk', 1: 'df', 2: 'md', 3: 'at'}
OUT = []
for k in ORDER:
    m = FM[k]; sq = SQ[k]; ds = m['date'].strftime('%Y-%m-%d'); rec = dict(mid=k, lg=m['lg'], sea=m['sea'], date=ds)
    for fs, tid in (('h', m['hid']), ('a', m['aid'])):
        st = [str(p) for p in sq[fs]['st']]
        feats = {}
        for N in (5, 10, 20):
            hist = TEAM_HIST[tid][-N:]
            def tm(p):
                ins = [mn[p] for mn, _ in hist if p in mn]
                return sum(ins) / (90.0 * len(ins)) if ins else 0.3
            def ts(p):
                ins = [(p in s0) for mn, s0 in hist if p in mn]
                return sum(ins) / len(ins) if ins else 0.3
            feats[f'Tm{N}'] = [tm(p) for p in st]; feats[f'Ts{N}'] = [ts(p) for p in st]
        lv = [value_at(p, ds) for p in st]; lv = [math.log(v) if v else None for v in lv]
        known = [x for x in lv if x is not None]; med = float(np.median(known)) if known else np.nan
        lv = [x if x is not None else med for x in lv]
        feats['Vlog'] = lv
        sv = SQUAD_VAL[(tid, m['sea'])]; smu = float(np.mean(list(sv.values()))) if len(sv) >= 11 else np.nan
        feats['Vrel'] = [x - smu if np.isfinite(smu) else np.nan for x in lv]
        for me, xs in feats.items():
            S = float(np.nanmean(xs)) if len(xs) else np.nan
            b = BASE[tid].get(me); rec[f'{me}_{fs}'] = S - b if (b is not None and np.isfinite(b) and np.isfinite(S)) else np.nan
            BASE[tid][me] = S if (b is None or not np.isfinite(b)) else (0.9 * b + 0.1 * S if np.isfinite(S) else b)
            for pos, g in GRP.items():
                ys = [x for p, x in zip(st, xs) if PL_POS.get(p, 2) == pos and np.isfinite(x)]
                Sg = float(np.mean(ys)) if ys else np.nan; key = f'{me}{g}'; bg = BASE[tid].get(key)
                rec[f'{key}_{fs}'] = Sg - bg if (bg is not None and np.isfinite(bg) and np.isfinite(Sg)) else np.nan
                BASE[tid][key] = Sg if (bg is None or not np.isfinite(bg)) else (0.9 * bg + 0.1 * Sg if np.isfinite(Sg) else bg)
        vs = [math.exp(x) for x in lv if np.isfinite(x)]
        S = math.log(sum(vs)) if len(vs) >= 9 else np.nan
        b = BASE[tid].get('Vsum'); rec[f'Vsum_{fs}'] = S - b if (b is not None and np.isfinite(S)) else np.nan
        BASE[tid]['Vsum'] = S if b is None else (0.9 * b + 0.1 * S if np.isfinite(S) else b)
    OUT.append(rec)
    for fs, tid in (('h', m['hid']), ('a', m['aid'])):
        mins = {str(p): mn for p, mn in sq[fs]['p'].items()}
        TEAM_HIST[tid].append((mins, set(str(p) for p in sq[fs]['st'])))
        for p, mn in mins.items():
            if mn > 0:
                v = value_at(p, ds)
                if v: SQUAD_VAL[(tid, m['sea'])][p] = math.log(v)
pd.DataFrame(OUT).to_csv('xi_variants_rows.csv', index=False)
print('ετοιμο xi_variants_rows.csv', len(OUT))
