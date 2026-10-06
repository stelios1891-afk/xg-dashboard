# -*- coding: utf-8 -*-
"""bcl_refresh.py — ΚΑΘΗΜΕΡΙΝΗ ενημερωση Basketball Champions League (6/10/2026, Στελιος «BCL σημερα»).
1. Flashscore: αποτελεσματα τρεχουσας σεζον (BCL + box, flashscore_bcl_stats.py· εγχωρια/Ευρωπη, flashscore_bk_domestic.py --current· extra, flashscore_bk_extra.py)
2. Μηχανη (bcl_engine_test.py — ρυθμισεις παρακατω): Μ1 = μονο BCL (box, κατοχες, τυχη) · Μ2 = ΚΟΙΝΗ ΚΛΙΜΑΚΑ απο ΟΛΑ τα ματς (bcl_common)
   προβλεψη = (1 − A)·Μ1 + A·Μ2 (Μ1 λειπει → μονο Μ2).
3. bcl_state.json: ratings σημερα ανα κωδικο Flashscore + ονοματα (για ταιριασμα με Pinnacle στο bcl_odds_scan.py).
Χρηση: python bcl_refresh.py [--no-fetch]"""
import sys, os, json, subprocess, datetime as dt, io, contextlib
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
from el_season import Y as CUR
M1_CFG = dict(carry=1.4, lam=8, HL=9999, w=0.5)      # bcl_engine_test2: επιλογη σε ολες τις 5 σεζον (με φιλικα), 6/10
M2_CFG = (1.3, 1.5, 9999.0, 25.0, 0.5)                # (περσι, λ, HL, ψαλιδισμα, βαρος φιλικων) — bcl_engine_test2 (φιλικα: 21/24 ρυθμισεις καλυτερες ≥4/5)
KX = 4.5                                               # ειδικοι/αποδοσεις: αφετηρια += KX · z (bcl_expert_z.json, bcl_expert_test.py) — 6/10 Στελιος: μονο αποδοσεις νικητη (ιστορικο δεν υπαρχει, κx απο 2024-25 ειδικους)
A = 0.75                                               # μιξη Μ1/Μ2 (bcl_engine_test2)
SIGMA = 12.0                                           # sd (πραγματικο − κλεισιμο) 2024-26
if '--no-fetch' not in sys.argv:
    for cmd in (['python', 'flashscore_bcl_stats.py'], ['python', 'flashscore_bk_domestic.py', '--current'], ['python', 'flashscore_bk_extra.py', '--current']):
        if not os.path.exists(cmd[1]): continue
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        print(f'{cmd[1]}: exit {r.returncode} · ' + (r.stdout.strip().splitlines() or [''])[-1][:120])
# ---- Μ2 κοινη κλιμακα ----
import bcl_common as B
rows = B.load(pre=M2_CFG[4] > 0)
ADJ = None
if KX > 0:
    try: ADJ = {int(y): {t: KX * v for t, v in d.items()} for y, d in json.load(open('bcl_expert_z.json', encoding='utf-8')).items()}
    except Exception as e: print('ΠΡΟΣΟΧΗ: bcl_expert_z.json —', e); ADJ = {}
    try:
        import math, re, unicodedata
        def _tk(x):
            x = unicodedata.normalize('NFKD', x or '').encode('ascii', 'ignore').decode().lower()
            return {w for w in re.split(r'[^a-z0-9]+', x) if len(w) >= 3 and w not in {'basket', 'basketball', 'club', 'the', 'bc', 'bk', 'kk', 'cb', 'sc', 'fc', 'baskets'}}
        _FG = json.load(open('fs_bk_games.json', encoding='utf-8')); _nm = {}
        for _k, _L in _FG.items():
            if int(_k.rsplit('_', 1)[1]) < CUR - 1: continue
            for _e in _L:
                for _t, _n in ((_e.get('hid'), _e.get('home')), (_e.get('aid'), _e.get('away'))):
                    if _t and _n: _nm.setdefault(_t, set()).add(_n)
        _OR = json.load(open('bcl_outrights.json', encoding='utf-8')); _Z = {}
        for _k, _v in _OR.items():
            if not _k.startswith(f'U{CUR}'): continue
            _p = {n: 1 / o for n, o in _v['odds'].items() if o and o > 1}; _s = sum(_p.values())
            _lp = {n: math.log(x / _s) for n, x in _p.items()}; _mu = np.mean(list(_lp.values())); _sd = np.std(list(_lp.values())) or 1
            for n, x in _lp.items():
                tn = _tk(n); best = (0, None)
                for t, ns in _nm.items():
                    for nn in ns:
                        tt = _tk(nn)
                        if tt and tn and len(tn & tt) / min(len(tn), len(tt)) > best[0]: best = (len(tn & tt) / min(len(tn), len(tt)), t)
                if best[0] >= .5: _Z.setdefault(best[1], []).append((x - _mu) / _sd)
        if _Z: ADJ[CUR] = {t: KX * float(np.mean(v)) for t, v in _Z.items()}; print(f'αποδοσεις νικητη {CUR}: {len(_Z)} ομαδες στην αφετηρια (κx {KX})')
    except Exception as e: print('ΠΡΟΣΟΧΗ: bcl_outrights.json —', e)
_, states = B.run(rows, *M2_CFG[:4], kf=M2_CFG[4], want_state=True, prior_adj=ADJ)
st2 = states.get(CUR) or states[max(states)]
# ομαδες χωρις ματς φετος: περσινο × carry (οπως στο τεστ, οπου η αφετηρια ειναι carry × περσινο τελος)
if CUR in states and CUR - 1 in states:
    st2 = dict(r={**{t: M2_CFG[0] * v + (ADJ or {}).get(CUR, {}).get(t, 0.0) for t, v in states[CUR - 1]['r'].items()}, **states[CUR]['r']}, h=states[CUR]['h'])
# ---- Μ1 μονο BCL ----
src = open('dom_bk_engine_test.py', encoding='utf-8').read().split("LIVE = (.7, 8, 9999, .5, False)")[0]
src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1).replace("ARGS = [a for a in sys.argv[1:] if not a.startswith('--')] or ['ACB', 'LBA']", "ARGS = ['BCL']")
dsrc = open('dom_bk_screen.py', encoding='utf-8').read()
NS = {'__name__': 'r'}
with contextlib.redirect_stdout(io.StringIO()):
    # η σεζον της βασης (dom_bk_screen) σταματα στο 2025 → επεκταση ως την τρεχουσα
    exec(src.replace("src = open('dom_bk_screen.py', encoding='utf-8').read()", "src = open('dom_bk_screen.py', encoding='utf-8').read().replace('YRS = range(2020, 2026)', 'YRS = range(2020, %d)')" % (CUR + 1)), NS)
G, EFF, fit = NS['G'], NS['EFF'], NS['fit']
m1 = None
try:
    EH, EA, PC = EFF[M1_CFG['w']]
    idx_all = np.where(G.lg.values == 'BCL')[0]
    prior, h0, mu0 = {}, 4.0, float(np.mean(np.r_[EH[idx_all], EA[idx_all]]))
    for y in sorted(set(G.y.values[idx_all])):
        sidx = idx_all[G.y.values[idx_all] == y]
        teams = sorted(set(G.hid.values[sidx]) | set(G.aid.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        hi = np.array([ix[t] for t in G.hid.values[sidx]]); ai = np.array([ix[t] for t in G.aid.values[sidx]])
        o0 = np.array([M1_CFG['carry'] * prior.get(t, (0, 0))[0] for t in teams]); d0 = np.array([M1_CFG['carry'] * prior.get(t, (0, 0))[1] for t in teams])
        dn = G.d.values[sidx]; w = 0.5 ** ((dn.max() - dn) / M1_CFG['HL'])
        mu, h, O, D, _ = fit(hi, ai, EH[sidx], EA[sidx], w, n, o0, d0, h0, mu0, M1_CFG['lam'], False)
        prev_prior = dict(prior)
        prior = {t: (O[i], D[i]) for t, i in ix.items()}; h0, mu0 = h, mu
        if y == CUR:
            m1 = dict(O={t: float(O[i]) for t, i in ix.items()}, D={t: float(D[i]) for t, i in ix.items()}, h=float(h), pace=float(np.mean(PC[sidx])), n=int(len(sidx)))
            for t, v in prev_prior.items():           # ομαδες BCL περσι χωρις ματς φετος: carry × περσινο
                if t not in m1['O']: m1['O'][t] = M1_CFG['carry'] * float(v[0]); m1['D'][t] = M1_CFG['carry'] * float(v[1])
    if m1 is None:   # η σεζον δεν εχει ακομα ματς BCL → περσινο × carry
        m1 = dict(O={t: M1_CFG['carry'] * v[0] for t, v in prior.items()}, D={t: M1_CFG['carry'] * v[1] for t, v in prior.items()}, h=float(h0), pace=float(np.mean(PC[idx_all])), n=0)
except Exception as e:
    print('ΠΡΟΣΟΧΗ: Μ1 απενεργη —', e)
# ---- ονοματα ----
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
try: FG.update({k: v for k, v in json.load(open('fs_bk_extra.json', encoding='utf-8')).items() if k not in FG})
except Exception: pass
names, bcl_now = {}, set()
for key, L in FG.items():
    comp, y = key.rsplit('_', 1)
    if int(y) < CUR - 1: continue
    for e in L:
        for t, nm in ((e.get('hid'), e.get('home')), (e.get('aid'), e.get('away'))):
            if t and nm: names.setdefault(t, set()).add(nm)
            if t and comp == 'BCL' and int(y) == CUR: bcl_now.add(t)
json.dump(dict(built=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes'), season=CUR, A=A, sigma=SIGMA, m1_cfg=M1_CFG, m2_cfg=list(M2_CFG),
               m2=dict(r=st2['r'], h=st2['h']), m1=m1, names={t: sorted(v) for t, v in names.items()}, bcl_teams=sorted(bcl_now),
               model=f'BCL: (1−{A})·μονο BCL (περσι {M1_CFG["carry"]}, λ {M1_CFG["lam"]}, HL {M1_CFG["HL"]}, τυχη {M1_CFG["w"]}) + {A}·κοινη κλιμακα (ολα τα ματς, περσι {M2_CFG[0]}, λ {M2_CFG[1]}, φιλικα {M2_CFG[4]}, ειδικοι {KX})'),
          open('bcl_state.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(f'bcl_state.json: Μ2 {len(st2["r"])} ομαδες · Μ1 {len(m1["O"]) if m1 else 0} (ματς φετος {m1["n"] if m1 else 0}) · ομαδες BCL φετος {len(bcl_now)}')
