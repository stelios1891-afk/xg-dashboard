# -*- coding: utf-8 -*-
"""bcl_small_start_test.py — BCL: ΑΦΕΤΗΡΙΑ ομαδων των 9 ΜΙΚΡΩΝ πρωταθληματων (7/10/2026, Στελιος «δοκιμασε τα ναι»).
Ευρημα (bcl_small_versions_out): στα ματς 1-3 τις υπερεκτιμαμε −6 σε ΚΑΘΕ εκδοχη → φταιει η αφετηρια (ξεκινουν κοντα στη «μεση» ολων).
Βαση = live κοινη κλιμακα ΧΩΡΙΣ εγχωρια μικρων (σημερα). Μικρα = CZE FIN BUL POR SUI CYP DEN GEO SVK (το πρωταθλημα της ομαδας απο fs_bk_extra/extra2).
 (α) ΠΟΙΝΗ αφετηριας δ {−2,−4,−6,−8,−10} σε καθε ομαδα μικρου πρωταθληματος καθε σεζον (μετατοπιση αφετηριας· σβηνει με τα ματς, βαρος ~1.5 ματς).
 (γ) ΑΦΕΤΗΡΙΑ = ΕΠΙΠΕΔΟ ΠΡΩΤΑΘΛΗΜΑΤΟΣ: ομαδα ΧΩΡΙΣ περσινο rating ξεκινα απο τον μεσο ορο (τελος σεζον) των ομαδων του ιδιου πρωταθληματος τις 3
     προηγουμενες σεζον (μονο ευρωπαικα ματς, οπως σημερα)· + δ {0,−2,−4}.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): LOSO 2021-26 (επιλογη με λαθος στα ματς-στοχο των αλλων σεζον) → ΠΕΡΝΑ αν το λαθος στον στοχο πεφτει σε ≥4/5 σεζον
  ΚΑΙ τα υπολοιπα ματς BCL δεν χειροτερευουν > 0.01. Αναφορα: μεροληψια ανα ζωνη ματς BCL (1-3/4-6/7-10/11+). Εξοδος: bcl_small_start_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, pickle, collections
import numpy as np
SMALL = {'CZE', 'FIN', 'BUL', 'POR', 'SUI', 'CYP', 'DEN', 'GEO', 'SVK'}

def small_teams():
    import bcl_common as B
    rows = B.load(pre=False, extra2=True, include=('CZE', 'FIN')); by = collections.defaultdict(list)
    for r in rows: by[r[0]].append(r)
    MC = {y: B._main_comp(v) for y, v in by.items()}
    lg = {}
    for y in MC:
        for t, c in MC[y].items():
            if c in SMALL: lg[(y, t)] = c
    return lg, MC

def _job(a):
    import bcl_common as B
    name, adj = a
    rows = B.load(pre=True)
    return name, B.run(rows, 1.3, 1.5, 9999.0, 25.0, kf=0.5, wo=1.5, prior_adj=adj, want_state=True)

def main():
    from multiprocessing import Pool
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    LG, MC = small_teams()
    years = sorted({y for (y, t) in LG})
    def team_lg(y, t): return LG.get((y, t)) or LG.get((y - 1, t))
    # ---- βαση (για τα επιπεδα της (γ)) ----
    with Pool(1) as pool: (nm0, (pr0, st0)), = pool.map(_job, [('base', None)])
    import bcl_common as B
    rows_all = B.load(pre=True); teams_y = collections.defaultdict(set)
    for r in rows_all: teams_y[r[0]] |= {r[3], r[4]}
    def lvl(y, c):
        v = [st0[yy]['r'][t] for yy in range(y - 3, y) if yy in st0 for t in st0[yy]['r'] if team_lg(yy, t) == c]
        return float(np.mean(v)) if len(v) >= 2 else None
    ADJ = {}
    for d in (-2, -4, -6, -8, -10):
        ADJ[f'α δ{d}'] = {y: {t: float(d) for t in teams_y[y] if team_lg(y, t)} for y in teams_y}
    for d in (0, -2, -4):
        A_ = {}
        for y in teams_y:
            A_[y] = {}
            for t in teams_y[y]:
                c = team_lg(y, t)
                if not c: continue
                has_prior = (y - 1) in st0 and t in st0[y - 1]['r']
                if not has_prior:
                    L = lvl(y, c)
                    if L is not None: A_[y][t] = L
                A_[y][t] = A_[y].get(t, 0.0) + d
        ADJ[f'γ επιπεδο δ{d}'] = A_
    P('επιπεδα πρωταθληματων (μεσος ομαδων τους, 3 προηγ. σεζον, μονο ευρωπαικα) — 2025: ' + ' '.join(f'{c}:{lvl(2025, c):+.1f}' for c in sorted(SMALL) if lvl(2025, c) is not None))
    with Pool(len(ADJ)) as pool: R = dict((n, v[0]) for n, v in pool.map(_job, list(ADJ.items())))
    R['σημερα'] = pr0
    D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); ids, ys = D['id'], D['y']; pos = {i: k for k, i in enumerate(ids)}
    def arr(pr):
        v = np.full(len(ids), np.nan)
        for mid, (p, y) in pr.items():
            if mid in pos: v[pos[mid]] = p
        return v
    A0 = arr(pr0); M1 = (D['FIN'] - .75 * A0) / .25
    H = {k: .25 * M1 + .75 * arr(v) for k, v in R.items()}
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
    cnt = collections.Counter(); GN = {}
    for k, L in FG.items():
        if not k.startswith('BCL_'): continue
        y = int(k.split('_')[1])
        for e in sorted([x for x in L if x.get('hs') not in (None, '')], key=lambda x: x['ts']):
            h, a = B.ALIAS.get(e['hid'], e['hid']), B.ALIAS.get(e['aid'], e['aid']); cnt[(y, h)] += 1; cnt[(y, a)] += 1; GN[e['id']] = (cnt[(y, h)], cnt[(y, a)])
    act = np.array([(int(E[i]['hs']) - int(E[i]['as_'])) if i in E else np.nan for i in ids], float)
    sgn = np.zeros(len(ids)); gsm = np.zeros(len(ids), int); tgt = np.zeros(len(ids), bool)
    for k, i in enumerate(ids):
        if i not in E: continue
        y = int(ys[k]); h, a = B.ALIAS.get(E[i]['hid'], E[i]['hid']), B.ALIAS.get(E[i]['aid'], E[i]['aid'])
        sh, sa = bool(team_lg(y, h)), bool(team_lg(y, a))
        if sh or sa: tgt[k] = True
        if sh != sa: sgn[k] = 1 if sh else -1; gsm[k] = GN[i][0] if sh else GN[i][1]
    EV = [2021, 2022, 2023, 2024, 2025]; ev = np.isin(ys, EV)
    def rm(v, m): m = m & np.isfinite(v) & np.isfinite(act); return float(np.sqrt(np.mean((act - v)[m] ** 2)))
    BINS = [('1-3', 1, 3), ('4-6', 4, 6), ('7-10', 7, 10), ('11+', 11, 99)]
    P(f'ματς-στοχος {int((tgt & ev).sum())} · μεροληψια (πραγμ − προβλ, − = υπερεκτιμηση) ανα ζωνη · λαθος στοχου · υπολοιπων')
    for k in ['σημερα'] + list(ADJ):
        v = H[k]; cells = []
        for lab, a, b in BINS:
            m = ev & (sgn != 0) & (gsm >= a) & (gsm <= b); cells.append(f'{np.mean((act - v)[m] * sgn[m]):+6.2f}')
        P(f'  {k:16s} ' + ' '.join(cells) + f'  · {rm(v, tgt & ev):.3f} · {rm(v, ~tgt & ev):.3f}')
    base = H['σημερα']; P(''); P('ΚΡΙΣΗ (LOSO, στοχος ≥4/5, υπολοιπα ≤ +0.01)')
    for fam in ('α', 'γ'):
        ks = [x for x in ADJ if x.startswith(fam)]
        held = np.full(len(ids), np.nan); ch = []
        for Y in EV:
            kb = min(ks, key=lambda k: rm(H[k], tgt & ev & (ys != Y))); ch.append(kb); m = ys == Y; held[m] = H[kb][m]
        d = [rm(held, tgt & (ys == Y)) - rm(base, tgt & (ys == Y)) for Y in EV]; dr = rm(held, ~tgt & ev) - rm(base, ~tgt & ev)
        ok = sum(x < 0 for x in d) >= 4 and dr <= .01
        P(f'  ({fam}) LOSO {ch} · στοχος {rm(base, tgt & ev):.3f} → {rm(held, tgt & ev):.3f} · ' + ' '.join(f'{x:+.2f}' for x in d) + f' → {sum(x < 0 for x in d)}/5 · υπολοιπα {dr:+.3f}'
          + ('  <- ΠΕΡΝΑ' if ok else '  ✗'))
    open('bcl_small_start_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

if __name__ == '__main__':
    main()
