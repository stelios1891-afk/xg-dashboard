"""x12_implied.py — 16/10/2026: αναμενομενα γκολ γηπ/φιλ απο ΜΟΝΟ 1Χ2 (αντιστροφη Poisson με το εγχωριο μητρωο σκορ picks.score_matrix_dom,
χωρις γκανιοτα αναλογικα). Χρηση: lam_from_1x2(o1, ox, o2) → (λh, λa). Επικυρωση (main): CORE7 2223-2526, Nowgoal Crown κλεισιμο — συνολο απο
1Χ2 vs συνολο απο τη γραμμη over/under (mtot) και διαφορα απο 1Χ2 vs απο χαντικαπ."""
import numpy as np, picks
_CACHE = {}
def _probs(h, a):
    M = np.asarray(picks.score_matrix_dom(max(h, .05), max(a, .05)))
    i = np.arange(M.shape[0])[:, None]; j = np.arange(M.shape[1])[None, :]
    return M[i > j].sum(), M[i == j].sum(), M[i < j].sum()
def lam_from_1x2(o1, ox, o2):
    q = np.array([1 / o1, 1 / ox, 1 / o2]); q = q / q.sum()
    key = tuple(np.round(q, 3))
    if key in _CACHE: return _CACHE[key]
    best = None
    for T in np.arange(1.6, 4.61, 0.1):                      # πλεγμα συνολο × διαφορα, μετα τοπικη βελτιωση
        for d in np.arange(-3.0, 3.01, 0.1):
            h, a = (T + d) / 2, (T - d) / 2
            if h <= .05 or a <= .05: continue
            p = _probs(h, a); e = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
            if best is None or e < best[0]: best = (e, T, d)
    _, T, d = best
    for st in (0.05, 0.02, 0.01):
        for _ in range(8):
            moved = False
            for dT, dd in ((st, 0), (-st, 0), (0, st), (0, -st)):
                h, a = (T + dT + d + dd) / 2, (T + dT - d - dd) / 2
                if h <= .05 or a <= .05: continue
                p = _probs(h, a); e = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
                if e < best[0]: best = (e, T + dT, d + dd); T, d = T + dT, d + dd; moved = True
            if not moved: break
    r = ((T + d) / 2, (T - d) / 2); _CACHE[key] = r
    return r
if __name__ == '__main__':
    import sys, os, json, glob
    sys.stdout.reconfigure(encoding='utf-8')
    _s = open('ucl_away_streak_deep.py', encoding='utf-8').read(); _s = _s[:_s.index('def at(seq, t):')]
    _TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _TO
    sys.stdout.reconfigure(encoding='utf-8')
    rows = []
    for f in glob.glob('nowgoal_odds/2[2-5]*_*.jsonl'):
        if any(x in f for x in ('_UCL', '_UEL', '_UECL', 'deep')) or not any(c in f for c in CORE7): continue
        for line in open(f, encoding='utf-8'):
            r = json.loads(line)
            if r['cid'] != 3 or not r.get('op'): continue
            mid = str(r['mid']); x = G.get(mid)
            if not x or x['hs'] is None: continue
            ko = int(x['t'].tz_localize('UTC').timestamp())
            op = sorted((int(e[0]), float(e[1]) + 0, float(e[2]), float(e[3])) for e in r['op'] if e[0] and int(e[0]) <= ko + 900)
            tou = [e for e in TOUD.get((mid, 'Crown'), []) if e[0] <= ko + 900]; ah = [e for e in AHD.get((mid, 'Crown'), []) if e[0] <= ko + 900]
            if not op or not tou or not ah: continue
            o1, ox, o2 = op[-1][1:]
            if min(o1, ox, o2) <= 1: continue
            Tm = mtot(*tou[-1][1:]); c = msup(ah[-1][1], ah[-1][2], ah[-1][3], Tm)
            h, a = lam_from_1x2(o1, ox, o2)
            rows.append((Tm, h + a, c, h - a, x['hs'] + x['as_'], x['hs'] - x['as_']))
            if len(rows) >= 2500: break
        if len(rows) >= 2500: break
    R = np.array(rows)
    print(f'CORE7 ματς με 1Χ2 + συνολα + χαντικαπ (Crown κλεισιμο): {len(R)}')
    print(f'  ΣΥΝΟΛΟ: απο γραμμη συνολων {R[:, 0].mean():.2f} · απο 1Χ2 {R[:, 1].mean():.2f} · συσχετιση {np.corrcoef(R[:, 0], R[:, 1])[0, 1]:.2f} · μεση |διαφορα| {np.abs(R[:, 0] - R[:, 1]).mean():.2f}')
    print(f'  ΔΙΑΦΟΡΑ: απο χαντικαπ {R[:, 2].mean():+.2f} · απο 1Χ2 {R[:, 3].mean():+.2f} · συσχετιση {np.corrcoef(R[:, 2], R[:, 3])[0, 1]:.2f} · μεση |διαφορα| {np.abs(R[:, 2] - R[:, 3]).mean():.2f}')
    print(f'  ακριβεια vs πραγματικα (MAE): συνολο γραμμη {np.abs(R[:, 4] - R[:, 0]).mean():.3f} / 1Χ2 {np.abs(R[:, 4] - R[:, 1]).mean():.3f} · διαφορα χαντικαπ {np.abs(R[:, 5] - R[:, 2]).mean():.3f} / 1Χ2 {np.abs(R[:, 5] - R[:, 3]).mean():.3f}')
