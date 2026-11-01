# -*- coding: utf-8 -*-
"""dom_bk_mech_v2.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ: ΚΑΘΕ ΒΑΣΙΚΟΣ ΜΗΧΑΝΙΣΜΟΣ ΞΑΝΑ, ΜΕ ΤΙΣ ΑΠΟΔΟΣΕΙΣ ΝΙΚΗΤΗ ΜΕΣΑ (7/10/2026, Στελιος: «τρεξε καθε μηχανισμο
και μην κολλας στη μιξη για αρχη»). 6 πρωταθληματα: ACB LBA GBL TBL LNB BBL.
Σειρα (καθε βημα πανω στη βαση με οσα περασαν πριν): 1 αποδοσεις νικητη κx {0,1,2,3,4} → 2 περσινο {0,.2,.35,.5,.7,.85,1} → 3 λ {2,4,8,12,16}
→ 4 μνημη HL {30,60,120,∞} → 5 τυχη {ωμο,.5,.25} → 6 εδρα ανα ομαδα {οχι,ναι} → 7 νεοφερμενες δ {0,−2,−4,−6,−8,−10}.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): LOSO 2021-26 ανα πρωταθλημα (επιλογη με RMSE διαφορας στις αλλες 4 σεζον) → ΑΛΛΑΓΗ αν το RMSE ΟΛΩΝ των ματς
  της κρατημενης σεζον πεφτει σε ≥4/5 σεζον. Για το κx: πεφτει το RMSE αγων 1-10 σε ≥80% των σεζον ΜΕ αποδοσεις ΚΑΙ ολα δεν χειροτερευουν (οπως πριν).
  ΑΓΟΡΑ: μονο αναφορα στο τελος (αρχικη vs τελικη βαση), ΟΧΙ κριτηριο. Εξοδος: dom_bk_mech_v2_out.txt
Αρχικη βαση = ο,τι περασε ως τωρα (βημα 1 μηχανη, νεοφερμενες, αποδοσεις ACB/TBL)."""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, contextlib, math
import numpy as np
LGS = ['ACB', 'LBA', 'GBL', 'TBL', 'LNB', 'BBL']
_src = open('dom_bk_outrights_test_4lg.py', encoding='utf-8').read()
_src = _src.replace("ARGS = ['GBL', 'TBL', 'LNB', 'BBL']", f"ARGS = {LGS!r}", 1).replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass').split("KX = (0, 1, 2, 3, 4, 6)")[0]
class _Buf(io.StringIO):
    def reconfigure(self, **k): pass
_buf = _Buf()
with contextlib.redirect_stdout(_buf):
    exec(_src, globals())
MATCH_LOG = _buf.getvalue()
# (περσι, λ, HL, τυχη, εδρα ανα ομαδα, δ νεοφερμενων, κx)
BASE0 = {'ACB': (.7, 8, 9999, .5, False, -8, 2), 'LBA': (1.0, 12, 120, None, False, 0, 0), 'GBL': (1.0, 4, 9999, None, True, 0, 0),
         'TBL': (1.0, 4, 60, .5, True, -8, 2), 'LNB': (.7, 8, 9999, .5, False, 0, 0), 'BBL': (.7, 8, 9999, .5, False, -4, 0)}
STEPS = [('αποδοσεις νικητη κx', 6, [0, 1, 2, 3, 4]), ('περσινο', 0, [0, .2, .35, .5, .7, .85, 1.0]), ('λ (τραβηγμα)', 1, [2, 4, 8, 12, 16]),
         ('μνημη HL', 2, [30, 60, 120, 9999]), ('τυχη', 3, [None, .5, .25]), ('εδρα ανα ομαδα', 4, [False, True]), ('νεοφερμενες δ', 5, [0, -2, -4, -6, -8, -10])]

def _job(a):
    lg, b = a
    pr, gn, new, fin = run(lg, b[0], b[1], b[2], b[3], b[4], b[5], b[6])
    return a, (pr, gn)

def main():
    from multiprocessing import Pool
    sys.stdout.reconfigure(encoding='utf-8')
    out.clear()
    P('ΑΝΤΙΣΤΟΙΧΙΣΗ ΑΠΟΔΟΣΕΩΝ:'); [P(l) for l in MATCH_LOG.splitlines() if 'αντιστοιχιση' in l or 'ΛΙΓΕΣ' in l]
    base = dict(BASE0); cache = {}
    crit = {lg: sorted({y for (y, t) in Z if y in EV and ((G.lg.values == lg) & (G.hid.values == t)).any()}) for lg in LGS}
    with Pool(20) as pool:
        for name, pos, grid in STEPS:
            jobs = []
            for lg in LGS:
                for v in grid:
                    b = list(base[lg]); b[pos] = v; b = tuple(b)
                    if (lg, b) not in cache: jobs.append((lg, b))
            for k, r in pool.map(_job, jobs): cache[k] = r
            P(''); P(f'======== {name} ========')
            for lg in LGS:
                rmm = lambda v, ys, msk=None: rm(v, lg, ys, msk)
                PR = {}
                for v in grid:
                    b = list(base[lg]); b[pos] = v; PR[v] = cache[(lg, tuple(b))]
                cur = base[lg][pos]; gn = PR[cur][1]
                held = np.full(len(G), np.nan); ch = []
                for Y in EV:
                    tr = [x for x in EV if x != Y]
                    k = min(grid, key=lambda v: rmm(PR[v][0], tr, gn <= 10) if pos == 6 else rmm(PR[v][0], tr)); ch.append(k)
                    mm = (G.lg.values == lg) & (G.y.values == Y); held[mm] = PR[k][0][mm]
                bp = PR[cur][0]
                dA = [rmm(held, [Y]) - rmm(bp, [Y]) for Y in EV]
                d10 = [rmm(held, [Y], gn <= 10) - rmm(bp, [Y], gn <= 10) for Y in EV]
                if pos == 6:
                    cy = crit[lg]; need = math.ceil(.8 * len(cy)) if cy else 99
                    w10 = sum(rmm(held, [Y], gn <= 10) < rmm(bp, [Y], gn <= 10) for Y in cy)
                    ok = bool(cy) and w10 >= need and rmm(held, EV) <= rmm(bp, EV); rule = f'αγων 1-10 {w10}/{len(cy)} (χρειαζεται {need})'
                else:
                    ok = sum(x < 0 for x in dA) >= 4; rule = f'ολα {sum(x < 0 for x in dA)}/5'
                insample = ' '.join(f'{v if v is not None else "ωμο"}:{rmm(PR[v][0], EV):.3f}' for v in grid)
                newv = cur
                if ok:
                    vals = [c for c in ch]; newv = max(set(vals), key=vals.count)          # η τιμη που διαλεγεται πιο συχνα
                    if newv == cur: ok = False
                P(f'  {NAME[lg]:9s} σημερα {cur if cur is not None else "ωμο"} · LOSO {[c if c is not None else "ωμο" for c in ch]} · '
                  f'ολα {rmm(bp, EV):.3f}→{rmm(held, EV):.3f} ({" ".join(f"{x:+.3f}" for x in dA)}) · αγων 1-10 {rmm(bp, EV, gn <= 10):.3f}→{rmm(held, EV, gn <= 10):.3f} '
                  f'({sum(x < 0 for x in d10)}/5) · {rule} → ' + (f'ΑΛΛΑΓΗ σε {newv if newv is not None else "ωμο"}' if ok else 'μενει'))
                P(f'            in-sample ολα: {insample}')
                if ok:
                    b = list(base[lg]); b[pos] = newv; base[lg] = tuple(b)
        P(''); P('======== ΤΕΛΙΚΗ ΒΑΣΗ (περσι, λ, HL, τυχη, εδρα ομαδας, δ, κx) & ΑΓΟΡΑ (μονο αναφορα) ========')
        jobs = [(lg, base[lg]) for lg in LGS if (lg, base[lg]) not in cache]
        for k, r in pool.map(_job, jobs): cache[k] = r
    for lg in LGS:
        rmm = lambda v, ys, msk=None: rm(v, lg, ys, msk)
        a, b = cache[(lg, BASE0[lg])], cache[(lg, base[lg])]
        P(f'  {NAME[lg]}: {BASE0[lg]} → {base[lg]} · ολα {rmm(a[0], EV):.3f} → {rmm(b[0], EV):.3f} · αγων 1-10 {rmm(a[0], EV, a[1] <= 10):.3f} → {rmm(b[0], EV, b[1] <= 10):.3f}')
        market_report(a[0], lg, 'αρχικη'); market_report(b[0], lg, 'τελικη')
    open('dom_bk_mech_v2_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))

if __name__ == '__main__':
    main()
