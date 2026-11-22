# -*- coding: utf-8 -*-
"""ec_totals_prior.py — ΦΙΛΙΚΑ ΣΤΑ ΣΥΝΟΛΑ EuroCup (5/10/2026, αποφαση Στελιου «βαλε τη μηχανη live»· ec_totals_deep_test Ν3 4/5).
Ιδια μεθοδος με το τεστ: τ = ταση ποντων ανα ομαδα στην ΠΕΡΣΙΝΗ σεζον (ridge στα ΣΥΝΟΛΑ ολων των ματς fs_bk_games, επιπεδο ανα διοργανωση)·
φιλικα/Super Cups 1 Αυγ … πρεμιερα EuroCup οπου και οι 2 ομαδες εχουν τ: υπολοιπο = συνολο − τ_γηπ − τ_φιλ, μ_φιλικων = μεσος ολων·
r_T(ομαδα) = Σ(υπολοιπο − μ_φιλικων)/(n + 4). Στο ec_refresh: συνολο += κT·(r_T γηπ + r_T φιλ) στους αγωνες 1-10 (κT .25).
Γραφει rT/nT/kT στο ec_prior.json (χρειαζεται το 'fs' = Flashscore κωδικοι ομαδων απο το ec_prior_build.py).
Χρηση: python ec_totals_prior.py   (το καλει και το ec_prior_build.py στο τελος)"""
import sys, json, math, datetime as dt
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
KT = 0.25

def tau_prev(FG, y):
    rows = []
    for k, L in FG.items():
        lg, yy = k.split('_')
        if int(yy) != y: continue
        for e in L:
            try: tt = int(e['hs']) + int(e['as_'])
            except Exception: continue
            if e.get('hid') and e.get('aid'): rows.append((e['hid'], e['aid'], lg, tt))
    if not rows: return {}
    teams = sorted({r[0] for r in rows} | {r[1] for r in rows}); ix = {t: i for i, t in enumerate(teams)}
    lgs = sorted({r[2] for r in rows}); il = {l: i for i, l in enumerate(lgs)}
    n, nl, k = len(teams), len(lgs), len(rows)
    A = np.zeros((k + n, n + nl)); b = np.zeros(k + n); r_ = np.arange(k)
    A[r_, [ix[r[0]] for r in rows]] = 1; A[r_, [ix[r[1]] for r in rows]] = 1; A[r_, [n + il[r[2]] for r in rows]] = 1; b[:k] = [r[3] for r in rows]
    A[k + np.arange(n), np.arange(n)] = math.sqrt(3)
    x = np.linalg.lstsq(A, b, rcond=None)[0]
    return {t: float(x[ix[t]]) for t in teams}

def main(path='ec_prior.json'):
    P = json.load(open(path, encoding='utf-8'))
    Y = int(P['season'][1:]); FS = P.get('fs') or {}
    S = json.load(open('ec_sched.json', encoding='utf-8')).get(P['season'], [])
    start = min(dt.datetime.fromisoformat(x['utc'].replace('Z', '+00:00')).timestamp() for x in S) if S else dt.datetime(Y, 10, 1).timestamp()
    FG = json.load(open('fs_bk_games.json', encoding='utf-8')); PS = json.load(open('fs_bk_preseason.json', encoding='utf-8'))
    C = tau_prev(FG, Y - 1); lo = dt.datetime(Y, 8, 1, tzinfo=dt.timezone.utc).timestamp()
    rev = {fs: c for c, fs in FS.items()}
    res, mine = [], {}
    for k, L in PS.items():
        for e in L:
            if not e.get('ts') or not (lo <= e['ts'] < start): continue
            try: tt = int(e['hs']) + int(e['as_'])
            except Exception: continue
            h, a = e.get('hid'), e.get('aid')
            if h not in C or a not in C: continue
            r0 = tt - C[h] - C[a]; res.append(r0)
            for me in (h, a):
                if me in rev: mine.setdefault(rev[me], []).append(r0)
    if len(res) < 20:
        print(f'ΠΡΟΣΟΧΗ: λιγα φιλικα με τ ({len(res)}) — rT κενο'); P.update(rT={}, nT={}, kT=KT); json.dump(P, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); return
    mu = float(np.mean(res))
    P['rT'] = {c: round(sum(x - mu for x in L) / (len(L) + 4), 2) for c, L in mine.items()}
    P['nT'] = {c: len(L) for c, L in mine.items()}; P['kT'] = KT; P['mu_pre_T'] = round(mu, 2)
    json.dump(P, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{P["season"]}: φιλικα στα συνολα — {len(res)} ματς με τ, μ {mu:+.1f} · ομαδες με r_T {len(P["rT"])}/{len(FS)}')
    for c in sorted(P['rT'], key=lambda c: -P['rT'][c]): print(f'  {c} r_T {P["rT"][c]:+.1f} ({P["nT"][c]} ματς) → συνολο {KT * P["rT"][c]:+.1f} π. ανα ματς (αγων 1-10)')

if __name__ == '__main__':
    main()
