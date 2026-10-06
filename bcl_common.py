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

def load(pre=False):
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    if pre:   # 6/10: φιλικα/Super Cups (fs_bk_preseason.json) ως comp 'PRE' — βαρος kf στο run, ουδετερη εδρα
        try:
            for k, v in json.load(open('fs_bk_preseason.json', encoding='utf-8')).items(): FG['PRE_' + k.rsplit('_', 1)[1] + '_' + k] = v
        except Exception: pass
    try:
        XT = json.load(open('fs_bk_extra.json', encoding='utf-8'))
        for k, v in XT.items(): FG.setdefault(k, v)
    except Exception: pass
    rows = []
    for key, L in FG.items():
        if key.startswith('PRE_'): comp, y = 'PRE', int(key.split('_')[1])
        else: comp, y = key.rsplit('_', 1); y = int(y)
        for e in L:
            if not e.get('hid') or not e.get('aid') or not e.get('ts'): continue
            try: hs, as_ = int(e['hs']), int(e['as_'])
            except Exception: hs = as_ = None
            rows.append((y, comp, e['ts'], e['hid'], e['aid'], hs, as_, e['id']))
    rows.sort(key=lambda r: r[2])
    return rows

def run(rows, carry=.7, lam=10.0, HL=120.0, clip=25.0, kf=0.0, wo=1.0, comp='BCL', years=None, today_ts=None, want_state=False, prior_adj=None):
    by_y = collections.defaultdict(list)
    for r in rows:
        if r[1] == 'PRE' and kf <= 0: continue
        by_y[r[0]].append(r)
    prior = {}; preds = {}; states = {}
    for y in sorted(by_y):
        R = by_y[y]
        teams = sorted({r[3] for r in R} | {r[4] for r in R}); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        m0 = np.array([carry * prior.get(t, 0.0) for t in teams])
        if prior_adj and y in prior_adj:            # ειδικοι/αποδοσεις: μετατοπιση αφετηριας (ποντοι)
            m0 = m0 + np.array([prior_adj[y].get(t, 0.0) for t in teams])
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
                wt = kf if r[1] == 'PRE' else (1.0 if r[1] == comp else wo)   # wo = βαρος ματς αλλων διοργανωσεων (εγχωρια/Ευρωπη)
                v = np.zeros(n + 1); v[i] = 1; v[j] = -1; v[n] = 0 if r[1] == 'PRE' else 1
                nz = (i, j, n)
                for a_ in nz:
                    for c_ in nz: M[a_, c_] += wt * v[a_] * v[c_]
                    b[a_] += wt * v[a_] * yv
        rr, h = solve()
        prior = {t: float(rr[ix[t]]) for t in teams}
        if want_state: states[y] = dict(r=dict(prior), h=float(h))
    return (preds, states) if want_state else preds

def run_tot(rows, carry=.8, lam=5.0, kf=0.0, wo=1.0, lam_mu=20.0, comp='BCL', want_state=False, tmap=None):
    """6/10/2026 — ΚΟΙΝΗ ΚΛΙΜΑΚΑ ΣΥΝΟΛΩΝ: συνολο = μ_διοργανωσης + s_γηπ + s_φιλ (s = «ταση συνολου» ομαδας: επιθεση + αμυνα που δεχεται).
    Ενα s ανα ομαδα απο ΟΛΑ τα ματς (καθε διοργανωση με δικο της επιπεδο μ — τα πρωταθληματα σκοραρουν διαφορετικα), walk-forward καθε μερα.
    Ridge: s → carry × περσινο (νεες 0)· μ → περσινο μ της διοργανωσης (βαρος lam_mu). Φιλικα (comp 'PRE') βαρος kf, αλλες διοργανωσεις wo."""
    by_y = collections.defaultdict(list)
    for r in rows:
        if r[1] == 'PRE' and kf <= 0: continue
        by_y[r[0]].append(r)
    prior, pmu = {}, {}; preds = {}; states = {}
    for y in sorted(by_y):
        R = by_y[y]
        teams = sorted({r[3] for r in R} | {r[4] for r in R}); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        comps = sorted({r[1] for r in R}); cx = {c: n + k for k, c in enumerate(comps)}; N = n + len(comps)
        done = [r[5] + r[6] for r in R if r[5] is not None]; gmean = float(np.mean(done)) if done else 160.0
        m0 = np.array([carry * prior.get(t, 0.0) for t in teams] + [pmu.get(c, gmean) for c in comps])
        M = np.zeros((N, N)); b = np.zeros(N)
        days = collections.defaultdict(list)
        for r in R: days[int(r[2] // 86400)].append(r)
        def solve():
            A = M.copy(); A[np.arange(n), np.arange(n)] += lam
            for c in comps: A[cx[c], cx[c]] += lam_mu if c in pmu else 1.0
            rhs = b.copy(); rhs[:n] += lam * m0[:n]
            for c in comps: rhs[cx[c]] += (lam_mu if c in pmu else 1.0) * m0[cx[c]]
            return np.linalg.solve(A, rhs)
        for d in sorted(days):
            todays = days[d]
            need = [r for r in todays if r[1] == comp]
            if need:
                x = solve()
                for r in need: preds[r[7]] = (float(x[cx[comp]] + x[ix[r[3]]] + x[ix[r[4]]]), y)
            for r in todays:
                if r[5] is None: continue
                i, j, c = ix[r[3]], ix[r[4]], cx[r[1]]; yv = float(tmap.get(r[7], r[5] + r[6])) if tmap else float(r[5] + r[6])   # tmap: συνολο «χωρις τυχη» (luck_totals)
                wt = kf if r[1] == 'PRE' else (1.0 if r[1] == comp else wo)
                for a_ in (i, j, c):
                    for c_ in (i, j, c): M[a_, c_] += wt
                    b[a_] += wt * yv
        x = solve()
        prior = {t: float(x[ix[t]]) for t in teams}; pmu = {c: float(x[cx[c]]) for c in comps}
        if want_state: states[y] = dict(s=dict(prior), mu=dict(pmu))
    return (preds, states) if want_state else preds


def luck_totals(w):
    """6/10/2026 — ΣΥΝΟΛΟ ΧΩΡΙΣ ΤΥΧΗ (ιδια λογικη με Ευρωλιγκα/EuroCup/dom_bk_screen.effs): ποσοστα τριποντων & βολων καθε ομαδας
    κρατιουνται κατα w και κατα (1 − w) γινονται ο μεσος της διοργανωσης-σεζον. Μονο ματς με box score (fs_bk_stats.jsonl: 12 διοργανωσεις).
    Επιστρεφει {match id: διορθωμενο συνολο}."""
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    sc = {e['id']: int(e['hs']) + int(e['as_']) for L in FG.values() for e in L if e.get('hs') not in (None, '')}
    def num(x):
        try: return float(str(x).replace('%', ''))
        except Exception: return None
    rec = collections.defaultdict(list)
    for ln in open('fs_bk_stats.jsonl', encoding='utf-8'):
        try: r = json.loads(ln)
        except Exception: continue
        st = r.get('stats') or {}
        try:
            v = [(num(st['3-point field goals made'][k]), num(st['3-point field goals attempts'][k]), num(st['Free throws made'][k]), num(st['Free throws attempts'][k])) for k in (0, 1)]
        except Exception: continue
        if r['id'] in sc and all(None not in t for t in v): rec[r['lg']].append((r['id'], v))
    out = {}
    for lg, L in rec.items():
        p3 = sum(t[0] for _, v in L for t in v) / max(1, sum(t[1] for _, v in L for t in v))
        pf = sum(t[2] for _, v in L for t in v) / max(1, sum(t[3] for _, v in L for t in v))
        for mid, v in L:
            adj = 0.0
            for m3, a3, mf, af in v:
                g3 = m3 / a3 if a3 else p3; gf = mf / af if af else pf
                adj += -3 * m3 + 3 * a3 * (w * g3 + (1 - w) * p3) - mf + af * (w * gf + (1 - w) * pf)
            out[mid] = sc[mid] + adj
    return out
