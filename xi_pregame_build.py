# -*- coding: utf-8 -*-
"""xi_pregame_build.py — 21/10/2026 (Στελιος: «το πρωι, πριν τις ενδεκαδες, με καλο ρεπορταζ και 2-3 επιβεβαιωμενες απουσιες, πως αλλαζουν οι
προβλεψεις μας; σημερα δεν εχουμε καμια προσαρμογη»).
ΑΝΑΜΕΝΟΜΕΝΗ ενδεκαδα πριν το ματς = η συνηθισμενη (11 με τα περισσοτερα λεπτα, abs_build) ΧΩΡΙΣ τους απουσες της λιστας Sofascore (missing),
συμπληρωμενη με τους επομενους (avail) · και εκδοχη που βγαζει ΚΑΙ τους αμφιβολους (availd).
Ιδια μετρα με τη φορμουλα (μονο πληροφορια ΠΡΙΝ το ματς): αξια (μεσος ln) · εμπιστοσυνη (10 ματς, λεπτα) ανα θεση · xGI (αθροισμα).
Δ_πριν = αναμενομενη − συνηθισμενη (ιδια λογικη με το Δ της επισημης ενδεκαδας).  ΕΞΟΔΟΣ: xi_pregame_rows.csv"""
import sys, json, glob, collections, datetime as dt, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
LG = ('EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'Eredivisie', 'PrimeiraLiga')
FM = {}
for lg in LG:
    for f in glob.glob(f'data_{lg}_*.json'):
        for k, v in json.load(open(f, encoding='utf-8')).items():
            try: d = dt.datetime.strptime(v['date'], '%a, %b %d, %Y, %H:%M UTC')
            except Exception: continue
            FM[str(k)] = dict(date=d, hid=v['home']['id'], aid=v['away']['id'])
SQ = json.load(open('core7_squads.json', encoding='utf-8'))
PM = json.load(open('player_matches.json', encoding='utf-8'))
X = {}
for l in open('player_xgi.jsonl', encoding='utf-8'):
    r = json.loads(l); X[r['mid']] = r['p']
VAL = {}
for f in ('core7_player_values.json', 'euro_player_values.json'):
    for k, v in json.load(open(f, encoding='utf-8')).items():
        if v.get('hist') and str(k) not in VAL: VAL[str(k)] = [(h[0], h[1]) for h in v['hist'] if h[1]]
AB = pd.read_csv('abs_sides.csv', dtype={'mid': str})
AB = AB[AB.sofa_list.astype(bool)]
LIST = {(r.mid, r.side): (str(r.full_ids).split('|'), str(r.avail_ids).split('|'), str(r.availd_ids).split('|'), r.n_miss, r.n_miss_reg)
        for r in AB.itertuples() if isinstance(r.full_ids, str)}
PRED = {k: [str(x) for x in v] for k, v in json.load(open('pred_pids_2526.json', encoding='utf-8')).items()}   # 21/10: ΠΡΟΒΛΕΠΟΜΕΝΕΣ 11αδες predicted11 (2526, ~25ω πριν)
ORDER = sorted([k for k in FM if k in SQ and SQ[k].get('h') and SQ[k].get('a')], key=lambda k: FM[k]['date'])
POS = {}
for k in ORDER:
    for s in ('h', 'a'):
        for e in ((PM.get(k) or {}).get(s) or {}).get('p', []) or []:
            POS[str(e[0])] = e[3] if e[3] in (0, 1, 2, 3) else 2
acc = collections.defaultdict(lambda: [0.0, 0.0])
for k in ORDER:
    for pid, (mn, xg, xa) in (X.get(k) or {}).items():
        if mn and mn > 0: a = acc[POS.get(pid, 2)]; a[0] += xg + xa; a[1] += mn / 90.0
MU = {p: v[0] / v[1] for p, v in acc.items() if v[1] > 0}
def value_at(pid, ds):
    h = VAL.get(pid)
    if not h: return None
    v = None
    for t, x in h:
        if t <= ds: v = x
        else: break
    return v if v is not None else h[0][1]
TEAM_HIST = collections.defaultdict(list); STX = {}
OUT = []
for k in ORDER:
    m = FM[k]; ds = m['date'].strftime('%Y-%m-%d'); rec = dict(mid=k)
    for fs, tid in (('h', m['hid']), ('a', m['aid'])):
        L = LIST.get((k, fs))
        if not L: continue
        full, avail, availd, nm, nr = L
        hist = TEAM_HIST[tid][-10:]
        def trust(p):
            ins = [mn[p] for mn in hist if p in mn]
            return sum(ins) / (90.0 * len(ins)) if ins else 0.3
        def lv(p):
            v = value_at(p, ds); return math.log(v) if v else None
        def xgi(p):
            s = STX.get(p); mu = MU.get(POS.get(p, 2), 0.25)
            return (s[0] + 5 * mu) / (s[1] + 5) if s else mu
        def feats(xi):
            vs = [lv(p) for p in xi]; kn = [x for x in vs if x is not None]
            V = float(np.mean(kn)) if kn else np.nan
            T = float(np.mean([trust(p) for p in xi])); TO = float(np.mean([trust(p) for p in xi if POS.get(p, 2) in (2, 3)] or [np.nan]))
            TD = float(np.mean([trust(p) for p in xi if POS.get(p, 2) in (0, 1)] or [np.nan]))
            VO = float(np.mean([x for p, x in zip(xi, vs) if x is not None and POS.get(p, 2) in (2, 3)] or [np.nan]))
            VD = float(np.mean([x for p, x in zip(xi, vs) if x is not None and POS.get(p, 2) in (0, 1)] or [np.nan]))
            return dict(V=V, T=T, TO=TO, TD=TD, VO=VO, VD=VD, XGI=sum(xgi(p) for p in xi))
        F, A, Ad = feats(full), feats(avail), feats(availd)
        ACT = feats([str(p) for p in SQ[k][fs]['st']])                                   # ΠΡΑΓΜΑΤΙΚΗ 11αδα, ιδιος ορισμος (vs συνηθισμενη)
        PR = PRED.get(f'{k}_{fs}'); PRf = feats(PR) if PR and len(PR) >= 9 else None      # ΠΡΟΒΛΕΠΟΜΕΝΗ (predicted11)
        for key in F:
            rec[f'p{key}_{fs}'] = A[key] - F[key]; rec[f'pd{key}_{fs}'] = Ad[key] - F[key]
            rec[f'a{key}_{fs}'] = ACT[key] - F[key]
            rec[f'r{key}_{fs}'] = (PRf[key] - F[key]) if PRf else np.nan
        rec[f'r_ok_{fs}'] = bool(PRf)
        rec[f'nmiss_{fs}'] = nm; rec[f'nreg_{fs}'] = nr
    OUT.append(rec)
    for fs, tid in (('h', m['hid']), ('a', m['aid'])):
        TEAM_HIST[tid].append({str(p): mn for p, mn in SQ[k][fs]['p'].items()})
    for pid, (mn, xg, xa) in (X.get(k) or {}).items():
        if mn and mn > 0:
            s = STX.get(pid, [0.0, 0.0]); STX[pid] = [s[0] * 0.95 + xg + xa, s[1] * 0.95 + mn / 90.0]
P = pd.DataFrame(OUT); P.to_csv('xi_pregame_rows.csv', index=False)
print('ετοιμο xi_pregame_rows.csv', len(P), '· με λιστα και στις 2:', int((P.filter(like='pV_h').notna().iloc[:, 0] & P.filter(like='pV_a').notna().iloc[:, 0]).sum()))
