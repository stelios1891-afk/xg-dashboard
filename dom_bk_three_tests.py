# -*- coding: utf-8 -*-
"""dom_bk_three_tests.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ: 3 ΤΕΣΤ ΑΠΟ ΤΗΝ ΑΝΑΛΥΣΗ «ΠΟΥ ΠΕΦΤΟΥΜΕ ΕΞΩ» (7/10/2026, Στελιος «ναι ξεκινα»).
Προβλεψεις = τελικη βαση dom_bk_mech_v2. Ομαδα Ευρωπης = παιζει φετος EL/EC/BCL/FEC (γνωστο απο την αρχη της σεζον).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ την εκτελεση):
 Α. ΜΠΟΝΟΥΣ ΟΜΑΔΑΣ ΕΥΡΩΠΗΣ: προβλεψη + β·(γηπ Ευρ − φιλοξ Ευρ) [«ισο»] ή + β·(γηπ Ευρ & φιλοξ οχι) [«μονο εντος»], β {0,.5,1,1.5,2,3}.
    LOSO 2021-26 ανα πρωταθλημα (RMSE ολων) → ΠΕΡΝΑ αν καλυτερο απο β=0 σε ≥4/5 σεζον.
 Β. ΤΕΝΤΩΜΑ: k·προβλεψη, k {.9…1.4}· ιδιο κριτηριο· και Α+Β μαζι.
 Γ. ΑΓΟΡΑ (ολα τα πρωταθληματα μαζι): Γ1 γηπ ≥3 μερες πιο ξεκουραστος → γηπεδουχος· Γ2 φιλοξ εχει ευρωπαικο ≤3.5 μερες ΜΕΤΑ (γηπ οχι) → γηπεδουχος.
    ΠΕΡΝΑ αν (i) υπολοιπο κλεισιματος θετικο σε ≥4/5 σεζον 2021-26 ΚΑΙ (ii) θετικο στη 2020-21 (ΕΚΤΟΣ του δειγματος που τα βρηκε)
    ΚΑΙ (iii) ROI γηπεδουχου στο ΚΛΕΙΣΙΜΟ (Crown, αλλιως Bet365) θετικο σε ≥4/5 σεζον 2021-26.
Εξοδος: dom_bk_three_tests_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, contextlib, math, json, collections, bisect
import numpy as np, pandas as pd
LGS = ['ACB', 'LBA', 'GBL', 'TBL', 'LNB', 'BBL']
class _Buf(io.StringIO):
    def reconfigure(self, **k): pass
_src = open('dom_bk_outrights_test_4lg.py', encoding='utf-8').read()
_src = _src.replace("ARGS = ['GBL', 'TBL', 'LNB', 'BBL']", f"ARGS = {LGS!r}", 1).replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass').split("KX = (0, 1, 2, 3, 4, 6)")[0]
with contextlib.redirect_stdout(_Buf()):
    exec(_src, globals())
FINAL = {'ACB': (.7, 12, 9999, .5, False, -8, 2), 'LBA': (1.0, 12, 120, None, False, 0, 0), 'GBL': (1.0, 4, 9999, None, True, 0, 0),
         'TBL': (1.0, 4, 60, .5, True, -8, 1), 'LNB': (1.0, 8, 9999, .5, True, 0, 0), 'BBL': (.85, 8, 9999, .5, False, -4, 0)}
EUC = ('EL', 'EC', 'BCL', 'FEC')

def _job(lg):
    pr, gn, new, fin = run(lg, *FINAL[lg]); return lg, pr

def main():
    from multiprocessing import Pool
    sys.stdout.reconfigure(encoding='utf-8')
    O = []
    def W(s=''): print(s, flush=True); O.append(str(s))
    with Pool(6) as pool: res = pool.map(_job, LGS)
    pred = np.full(len(G), np.nan)
    for lg, pr in res: m = G.lg.values == lg; pred[m] = pr[m]
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    SCH = collections.defaultdict(list); EUTEAM = set()
    for key, L in FG.items():
        comp = key.split('_')[0]; y = int(key.split('_')[1])
        for e in L:
            if not (e.get('ts') and e.get('hid') and e.get('aid')): continue
            for t in (e['hid'], e['aid']):
                SCH[t].append((e['ts'], comp in EUC))
                if comp in EUC: EUTEAM.add((t, y))
    for v in SCH.values(): v.sort()
    def sched(t, ts):
        v = SCH.get(t, []); k = bisect.bisect_left(v, (ts - 3600, False))
        prev = v[k - 1] if k > 0 else None; nxt = next((x for x in v[k:] if x[0] > ts + 3600), None)
        return dict(rest=(ts - prev[0]) / 86400 if prev else 9.0, next_eu=bool(nxt and nxt[1] and (nxt[0] - ts) / 86400 <= 3.5))
    rows = []
    for i in MK:
        y = int(G.y.values[i])
        if y not in [2020] + EV or not np.isfinite(pred[i]): continue
        ts = G.t.values[i].astype('datetime64[s]').astype(int); h, a = sched(G.hid.values[i], ts), sched(G.aid.values[i], ts)
        rows.append(dict(lg=G.lg.values[i], y=y, act=act[i], pr=pred[i], mc=MK[i]['mc'], op=MK[i]['op'], cl=MK[i]['cl'],
                         heu=(G.hid.values[i], y) in EUTEAM, aeu=(G.aid.values[i], y) in EUTEAM, rest_d=min(h['rest'], 9) - min(a['rest'], 9),
                         h_next=h['next_eu'], a_next=a['next_eu']))
    R = pd.DataFrame(rows)
    W(f'ματς με αγορα: {len(R)} (2020-21: {(R.y == 2020).sum()})')
    # ---------------- Α & Β ----------------
    BETAS = [0, .5, 1, 1.5, 2, 3]; KS = list(np.round(np.arange(.9, 1.41, .05), 2))
    def loso(s, f, grid, base):
        rmy = lambda p, ys: float(np.sqrt(np.mean((s.act[s.y.isin(ys)] - p[s.y.isin(ys)]) ** 2)))
        ch, dd = [], []; P_ = {g: f(g) for g in grid}
        for Y in EV:
            tr = [x for x in EV if x != Y]; g = min(grid, key=lambda g: rmy(P_[g], tr)); ch.append(g); dd.append(rmy(P_[g], [Y]) - rmy(P_[base], [Y]))
        held = np.sqrt(np.mean([rmy(P_[g], [Y]) ** 2 for g, Y in zip(ch, EV)]))
        return ch, dd, rmy(P_[base], EV), held
    W(''); W('######## Α. ΜΠΟΝΟΥΣ ΟΜΑΔΑΣ ΕΥΡΩΠΗΣ · Β. ΤΕΝΤΩΜΑ · Α+Β (LOSO 2021-26, RMSE ολων, ≥4/5) ########')
    for lg in LGS:
        s = R[(R.lg == lg) & R.y.isin(EV)].reset_index(drop=True); W(f'  -- {NAME[lg]} (n {len(s)}, ματς με διαφορετικη Ευρωπη {(s.heu != s.aeu).sum()})')
        tests = [('Α ισο   β', lambda b: s.pr + b * (s.heu.astype(int) - s.aeu.astype(int)), BETAS, 0),
                 ('Α εντος β', lambda b: s.pr + b * (s.heu & ~s.aeu).astype(int), BETAS, 0),
                 ('Β τεντωμα k', lambda k: k * s.pr, KS, 1.0),
                 ('Α+Β (ισο β, k)', lambda bk: bk[1] * s.pr + bk[0] * (s.heu.astype(int) - s.aeu.astype(int)), [(b, k) for b in BETAS for k in KS], (0, 1.0))]
        for lab, f, grid, base in tests:
            ch, dd, r0, r1 = loso(s, f, grid, base); ok = sum(x < 0 for x in dd) >= 4
            W(f'    {lab:16s} LOSO {ch} · {r0:.3f} → {r1:.3f} · ' + ' '.join(f'{x:+.3f}' for x in dd) + f' → {sum(x < 0 for x in dd)}/5' + ('  ✓ ΠΕΡΝΑ' if ok else '  ✗'))
    # ---------------- Γ ----------------
    W(''); W('######## Γ. ΑΓΟΡΑ: υπολοιπο κλεισιματος (πραγμ − κλεισ, γηπ) & ROI γηπεδουχου ########')
    def roi(s, when):
        u = []
        for _, r in s.iterrows():
            L, o1, o2 = r[when]; v = r.act + L
            u.append((o1 - 1) if v > 0 else (0 if v == 0 else -1))
        return np.array(u)
    for lab, m in (('Γ1 γηπ ≥3 μερες πιο ξεκουραστος', R.rest_d >= 3), ('   (καθρεφτης: φιλοξ ≥3 πιο ξεκουραστος)', R.rest_d <= -3),
                   ('Γ2 φιλοξ ευρωπαικο ΜΕΤΑ (γηπ οχι)', R.a_next & ~R.h_next), ('   (καθρεφτης: γηπ ευρωπαικο ΜΕΤΑ)', R.h_next & ~R.a_next)):
        s = R[m]; ins = s[s.y.isin(EV)]; oos = s[s.y == 2020]
        res_y = {Y: (s[s.y == Y].act - s[s.y == Y].mc).mean() for Y in [2020] + EV if (s.y == Y).sum() >= 5}
        ry = {Y: roi(s[s.y == Y], 'cl').mean() for Y in EV if (s.y == Y).sum() >= 5}
        ro = {Y: roi(s[s.y == Y], 'op').mean() for Y in EV if (s.y == Y).sum() >= 5}
        e = ins.act - ins.mc; t = e.mean() / (e.std() / math.sqrt(len(e)))
        c1 = sum(1 for Y in EV if res_y.get(Y, 0) > 0) >= 4; c2 = res_y.get(2020, -1) > 0; c3 = sum(1 for Y in EV if ry.get(Y, -1) > 0) >= 4
        W(f'  {lab:42s} n {len(ins)} (+2020-21: {len(oos)}) · υπολοιπο {e.mean():+.2f} (t {t:+.1f}) · ανα σεζον ' + ' '.join(f'{Y % 100}:{v:+.1f}' for Y, v in res_y.items()))
        W(f'      ROI γηπ κλεισιμο {roi(ins, "cl").mean()*100:+.1f}% ({sum(1 for v in ry.values() if v > 0)}/{len(ry)}) · ανοιγμα {roi(ins, "op").mean()*100:+.1f}% ({sum(1 for v in ro.values() if v > 0)}/{len(ro)})'
          + (f' · 2020-21 κλεισιμο {roi(oos, "cl").mean()*100:+.1f}%' if len(oos) else '')
          + ('' if lab.strip().startswith('(') else f' · ΚΡΙΣΗ (i){"✓" if c1 else "✗"} (ii){"✓" if c2 else "✗"} (iii){"✓" if c3 else "✗"} → ' + ('ΠΕΡΝΑ' if c1 and c2 and c3 else '✗')))
    open('dom_bk_three_tests_out.txt', 'w', encoding='utf-8').write(chr(10).join(O))

if __name__ == '__main__':
    main()
