# -*- coding: utf-8 -*-
"""bcl_expert_test.py — BCL: ΓΝΩΜΗ ΕΙΔΙΚΩΝ / ΑΠΟΔΟΣΕΙΣ ΝΙΚΗΤΗ στην αφετηρια σεζον (6/10/2026, Στελιος «ειδικοι/αποδοσεις που ειδαμε οτι βοηθανε»).
Ιδια λογικη με EuroCup (ec_prior_build): z ομαδας = μεσος γνωμων (θεση power ranking → Φ⁻¹(1 − (θεση − .5)/N) · αποδοση νικητη → τυποποιημενο ln p).
Μπαινει στην κοινη κλιμακα ως μετατοπιση αφετηριας: αφετηρια = περσι × περσινο + κx · z (ποντοι). κx {0, 1.5, 3, 4.5, 6}.
Βαση: οι LOSO επιλογες του bcl_engine_test2 (Μ1, Μ2, a ανα σεζον) — αλλαζει ΜΟΝΟ το Μ2 κομματι.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): κx επιλεγεται LOSO· μπαινει αν καλυτερο απο κx=0 σε ≥ 75% των σεζον ΜΕ γνωμες (στρογγ. προς τα πανω).
Εξοδος: bcl_expert_test_out.txt · bcl_engine_preds3.pkl · bcl_expert_z.json (z ανα σεζον/ομαδα, για live)"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, math, re, pickle, unicodedata, collections
import numpy as np
from statistics import NormalDist
from multiprocessing import Pool
KX = (1.5, 3.0, 4.5, 6.0)

def toks(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return {w for w in re.split(r'[^a-z0-9]+', s) if len(w) >= 3 and w not in {'basket', 'basketball', 'club', 'the', 'bc', 'bk', 'kk', 'cb', 'sc', 'fc'}}

def build_z():
    nd = NormalDist()
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    PR = json.load(open('bcl_power_rankings.json', encoding='utf-8'))
    OR = json.load(open('bcl_outrights.json', encoding='utf-8')) if os.path.exists('bcl_outrights.json') else {}
    Z = collections.defaultdict(lambda: collections.defaultdict(list)); miss = []; srcs = collections.defaultdict(list)
    def teams_of(y):
        nm = {}
        for e in FG.get(f'BCL_{y}', []):
            for t, n in ((e['hid'], e['home']), (e['aid'], e['away'])): nm.setdefault(t, set()).add(n)
        return nm
    def code(name, nm):
        tn = toks(name); best = (0, None)
        for t, ns in nm.items():
            for n in ns:
                tt = toks(n)
                if tt and tn:
                    sc = len(tn & tt) / min(len(tn), len(tt))
                    if sc > best[0]: best = (sc, t)
        return best[1] if best[0] >= .5 else None
    for src, D in list(PR.items()) + [('αποδοσεις ' + k, {f'{k[1:5]}-xx': v}) for k, v in OR.items() if k.startswith('U')]:
        if src.startswith('_'): continue
        for lbl, v in D.items():
            y = int(lbl[:4]); nm = teams_of(y)
            if 'ranking' in v:
                L = v['ranking']
                for r, n in enumerate(L, 1):
                    c = code(n, nm)
                    if c: Z[y][c].append(nd.inv_cdf(1 - (r - .5) / len(L)))
                    else: miss.append((lbl, src[:20], n))
            elif 'odds' in v:
                p = {n: 1 / o for n, o in v['odds'].items() if o and o > 1}; s = sum(p.values())
                lp = {n: math.log(x / s) for n, x in p.items()}; mu = np.mean(list(lp.values())); sd = np.std(list(lp.values())) or 1
                for n, x in lp.items():
                    c = code(n, nm)
                    if c: Z[y][c].append((x - mu) / sd)
                    else: miss.append((lbl, src[:20], n))
            srcs[y].append(src.split(' (')[0])
    z = {y: {t: float(np.mean(v)) for t, v in d.items()} for y, d in Z.items()}
    return z, miss, srcs

def _m2(args):
    cfg, kx, z = args
    import bcl_common as B
    rows = B.load(pre=True)
    adj = {y: {t: kx * v for t, v in d.items()} for y, d in z.items()}
    return (cfg, kx), B.run(rows, *cfg[:4], kf=cfg[4], prior_adj=adj)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    z, miss, srcs = build_z()
    P('ΓΝΩΜΕΣ: ' + ' · '.join(f'{y}-{(y+1)%100:02d}: {len(z[y])} ομαδες ({", ".join(sorted(set(srcs[y])))})' for y in sorted(z)))
    if miss: P(f'  χωρις ταιριασμα ({len(miss)}): ' + '; '.join(f'{a} {c}' for a, b, c in miss[:25]))
    json.dump({str(y): d for y, d in z.items()}, open('bcl_expert_z.json', 'w', encoding='utf-8'), ensure_ascii=False)
    D = pickle.load(open('bcl_engine_preds2f.pkl', 'rb'))   # με φιλικα (ζευγαρωτο τεστ 21/24 ρυθμισεις ≥4/5)
    ids, ys, act, FIN, cb = D['id'], D['y'], D['act'], D['FIN'], D['cb']
    EV = sorted(cb)
    M2raw = pickle.load(open('bcl_m2_cache2.pkl', 'rb'))
    need = sorted({cb[Y][1] for Y in EV if cb[Y][2] > 0})
    P('Μ2 ρυθμισεις LOSO: ' + ' · '.join(map(str, need)))
    jobs = [(c, kx, z) for c in need for kx in KX]
    with Pool(min(8, len(jobs))) as pool: R = dict(pool.map(_m2, jobs))
    pos = {i: k for k, i in enumerate(ids)}
    def arr(pr):
        v = np.full(len(ids), np.nan)
        for mid, (p, y) in pr.items():
            if mid in pos: v[pos[mid]] = p
        return v
    base = {c: arr(M2raw[c]) for c in need}
    VAR = {0.0: FIN.copy()}
    for kx in KX:
        v = FIN.copy()
        for Y in EV:
            k1, k2, a = cb[Y]
            if a == 0: continue
            m = ys == Y; d = arr(R[(k2, kx)]) - base[k2]; v[m] = FIN[m] + a * np.nan_to_num(d[m])
        VAR[kx] = v
    def rm(v, yy, extra=None):
        m = np.isin(ys, yy) & np.isfinite(v)
        if extra is not None: m &= extra
        return float(np.sqrt(np.mean((act - v)[m] ** 2)))
    gno = np.zeros(len(ids), int); cnt = collections.Counter()
    for i in np.argsort(D['t']): cnt[(ys[i], D['hid'][i])] += 1; gno[i] = cnt[(ys[i], D['hid'][i])]
    P(''); P('in-sample λαθος ανα κx (ολα | 1-3 ματς ομαδας γηπ.):')
    for kx, v in VAR.items(): P(f'  κx {kx}: ' + ' '.join(f'{Y}: {rm(v, [Y]):.3f}' for Y in EV) + f' · ΟΛΑ {rm(v, EV):.3f} | 1-3 {rm(v, EV, gno <= 3):.3f}')
    held = np.full(len(ids), np.nan); ch = {}
    for Y in EV:
        tr = [x for x in EV if x != Y]; k = min(VAR, key=lambda k: rm(VAR[k], tr)); ch[Y] = k; held[ys == Y] = VAR[k][ys == Y]
    WY = [Y for Y in EV if Y in z]
    d = [rm(held, [Y]) - rm(FIN, [Y]) for Y in WY]; need_n = math.ceil(.75 * len(WY)) if WY else 99
    ok = sum(x < 0 for x in d) >= need_n
    P(''); P('LOSO κx: ' + ' '.join(f'{Y}: {ch[Y]}' for Y in EV))
    P(f'  σεζον με γνωμες {WY}: ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/{len(WY)} (χρειαζεται {need_n})' + ('  <- ΜΠΑΙΝΕΙ' if ok else '  <- ✗'))
    P(f'  ΟΛΑ {rm(FIN, EV):.3f} → {rm(held, EV):.3f} · 1-3 ματς {rm(FIN, EV, gno <= 3):.3f} → {rm(held, EV, gno <= 3):.3f}')
    D2 = dict(D); D2['FIN'] = held if ok else FIN; D2['HB'] = D2['FIN']; D2['kx'] = ch; D2['ok_exp'] = ok
    pickle.dump(D2, open('bcl_engine_preds3.pkl', 'wb'))
    open('bcl_expert_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))

if __name__ == '__main__':
    main()
