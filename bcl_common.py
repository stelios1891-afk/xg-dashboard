# -*- coding: utf-8 -*-
"""bcl_common.py — «ΚΟΙΝΗ ΚΛΙΜΑΚΑ» για το Basketball Champions League (6/10/2026, Στελιος «BCL σημερα»).
Ενα rating ανα ομαδα απο ΟΛΑ τα ματς της σεζον (εγχωρια + BCL + FIBA Europe Cup + EuroCup + Ευρωλιγκα), walk-forward καθε μερα:
  διαφορα γηπ = r_γηπ − r_φιλ + εδρα (κοινη)· ridge προς αφετηρια = carry × περσινο τελος (νεες ομαδες 0)· φθορα HL μερες (εκθετικη)·
  διαφορα ψαλιδισμενη στο ±clip (κοινη κλιμακα ειναι ευαισθητη στα «μπλοουτ» μικρων λιγκων).
Πηγες: fs_bk_games.json (14 διοργανωσεις: ACB GBL TBL LBA ISR LNB BBL LKL ABA VTB EL EC BCL FEC) + fs_bk_extra.json (PLK ROM GBR BNX LEL UKR).
Ομαδες με τον ΙΔΙΟ κωδικο Flashscore σε ολες τις διοργανωσεις (PX/PY).
run(carry, lam, HL, clip, comp='BCL') → {match id: προβλεψη διαφορας γηπ} για καθε ματς της comp, με οτι ηταν γνωστο ΠΡΙΝ τη μερα του.
state(...) → ratings σημερα (για live)."""
import json, math, collections
import numpy as np

def load():
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    try:
        XT = json.load(open('fs_bk_extra.json', encoding='utf-8'))
        for k, v in XT.items(): FG.setdefault(k, v)
    except Exception: pass
    rows = []
    for key, L in FG.items():
        comp, y = key.rsplit('_', 1); y = int(y)
        for e in L:
            if not e.get('hid') or not e.get('aid') or not e.get('ts'): continue
            try: hs, as_ = int(e['hs']), int(e['as_'])
            except Exception: hs = as_ = None
            rows.append((y, comp, e['ts'], e['hid'], e['aid'], hs, as_, e['id']))
    rows.sort(key=lambda r: r[2])
    return rows

def run(rows, carry=.7, lam=10.0, HL=120.0, clip=25.0, comp='BCL', years=None, today_ts=None, want_state=False):
    by_y = collections.defaultdict(list)
    for r in rows: by_y[r[0]].append(r)
    prior = {}; preds = {}; states = {}
    for y in sorted(by_y):
        R = by_y[y]
        teams = sorted({r[3] for r in R} | {r[4] for r in R}); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        m0 = np.array([carry * prior.get(t, 0.0) for t in teams])
        M = np.zeros((n + 1, n + 1)); b = np.zeros(n + 1)       # τελευταια στηλη = εδρα
        last_day = None
        days = collections.defaultdict(list)
        for r in R: days[int(r[2] // 86400)].append(r)
        def solve():
            A = M.copy(); A[:n, :n] += lam * np.eye(n); A[n, n] += 50.0
            rhs = b.copy(); rhs[:n] += lam * m0; rhs[n] += 50.0 * 2.5
            x = np.linalg.solve(A, rhs); return x[:n], x[n]
        for d in sorted(days):
            if last_day is not None and HL < 9000:
                f = 0.5 ** ((d - last_day) / HL); M *= f; b *= f
            last_day = d
            todays = days[d]
            need = [r for r in todays if r[1] == comp]
            if need:
                rr, h = solve()
                for r in need:
                    if r[3] in ix and r[4] in ix: preds[r[7]] = (float(rr[ix[r[3]]] - rr[ix[r[4]]] + h), y)
            for r in todays:
                if r[5] is None: continue
                i, j = ix[r[3]], ix[r[4]]; yv = float(np.clip(r[5] - r[6], -clip, clip))
                v = np.zeros(n + 1); v[i] = 1; v[j] = -1; v[n] = 1
                nz = (i, j, n)
                for a_ in nz:
                    for c_ in nz: M[a_, c_] += v[a_] * v[c_]
                    b[a_] += v[a_] * yv
        rr, h = solve()
        prior = {t: float(rr[ix[t]]) for t in teams}
        if want_state: states[y] = dict(r=dict(prior), h=float(h))
    return (preds, states) if want_state else preds
