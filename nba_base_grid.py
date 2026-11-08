# -*- coding: utf-8 -*-
"""nba_base_grid.py — NBA «ΚΑΛΗ ΒΑΣΗ» ΤΟΥ ΜΟΝΤΕΛΟΥ ΟΜΑΔΩΝ (28/9/2026, αιτημα Στελιου: πρωτα καλη βαση για τους πρωτους μηνες).
Τρεχουσα: εδρα 2/100 · K 8 · HL 60 · περσι 0.7 · τυχη 0.5 (τα 4 πρωτα απο μικρο πλεγμα με νικητη ΣΤΗΝ ΑΚΡΗ, η τυχη αντιγραφη EL).
ΣΤΑΔΙΟ 1 (3.750): περσι {.5,.6,.7,.8,.9,1} × K {2,4,6,8,12} × HL {20,30,45,60,∞} × τυχη {0,.25,.5,.75,1} × εδρα {1,1.5,2,2.5,3}.
ΣΤΑΔΙΟ 2: με HL/τυχη/εδρα του καλυτερου σταδιου 1 → περσι (6) × K (5) × εδρα ανα ομαδα lam_u {κοινη,80,40,20,10} × ρόστερ beta {0,.5,1,1.5}.
ΚΡΙΣΗ (προ-δηλωμενη): LOSO σε 5 σεζον (2021-22…2025-26) — ρυθμιση διαλεγεται ΜΟΝΟ απο τις αλλες σεζον (ελαχιστο RMSE διαφορας
  στα ματς με closing). ΚΥΡΙΑ: Οκτ-Δεκ · δευτερη: ολη η σεζον. Αλλαγη ΠΕΡΝΑ αν το εκτος-δειγματος RMSE ειναι καλυτερο σε ≥4/5 σεζον.
  Συγκρισεις: (1) πλεγμα vs τρεχουσα · (2) +εδρα ανα ομαδα vs χωρις · (3) +ρόστερ vs χωρις · (4) ολα vs τρεχουσα.
Επισης: RMSE vs αγορα (Crown closing) και κλιση b. Εξοδος: nba_base_grid_out.txt · nba_base_grid_cache.npz"""
import sys, itertools, os
import numpy as np
from multiprocessing import Pool

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    import nba_base_core as C
    out = []
    def P(s=''):
        print(s, flush=True); out.append(str(s))
    IDX, ACT, MM, SE, G = C.IDX, C.ACT, C.MM, C.SE, C.G
    EV = [int(s) for s in C.EVAL]
    MON = G.date.dt.month.values[IDX]
    OCTDEC = np.isin(MON, [10, 11, 12])
    CACHE = 'nba_base_grid_cache.npz'
    PRED = {}
    if os.path.exists(CACHE):
        z = np.load(CACHE, allow_pickle=True); PRED = dict(zip([tuple(k) for k in z['keys']], z['vals']))
    def key(c): return (c['h'], c['lam'], c['HL'], c['carry'], c['lw'], c.get('lam_u') or 0, c.get('beta', 0.0))
    def runall(cfgs):
        todo = [c for c in cfgs if key(c) not in PRED]
        P(f'  τρεξιμο {len(todo)} ρυθμισεων (απο {len(cfgs)}) σε 20 πυρηνες…')
        with Pool(16) as pool:
            for k, (c, pr) in enumerate(pool.imap_unordered(C.job, todo, chunksize=4)):
                PRED[key(c)] = pr
                if (k + 1) % 250 == 0: P(f'    {k + 1}/{len(todo)}')
        np.savez(CACHE, keys=np.array(list(PRED.keys()), dtype=float), vals=np.array(list(PRED.values())))
    def score(k):
        e = ACT - PRED[k][IDX]
        return {(s, per): float(np.sqrt(np.mean(e[(SE == s) & (OCTDEC if per == 'od' else True)] ** 2))) for s in EV for per in ('od', 'all')}
    CUR = (2.0, 8, 60, 0.7, 0.5, 0, 0.0)
    def loso(keys, per):
        SC = {k: score(k) for k in keys}; held = {}; chosen = []
        for Y in EV:
            best = min(keys, key=lambda k: np.mean([SC[k][(s, per)] for s in EV if s != Y]))
            chosen.append(best); held[Y] = best
        return held, chosen, SC
    def heldpred(held):
        p = np.full(len(G), np.nan)
        for Y, k in held.items(): p[G.season.values == Y] = PRED[k][G.season.values == Y]
        return p
    def rep(lab, p):
        mm = np.isin(SE, EV)
        cells = []
        for nm, msk in (('Οκτ-Δεκ', OCTDEC), ('ολη', np.ones(len(IDX), bool))):
            k = mm & msk; e = ACT - p[IDX]
            b = np.polyfit((p[IDX] - MM)[k], (ACT - MM)[k], 1)[0]
            cells.append(f'{nm}: RMSE {np.sqrt(np.mean(e[k] ** 2)):.3f} (αγορα {np.sqrt(np.mean((ACT - MM)[k] ** 2)):.3f}) b {b:+.3f}')
        P(f'  {lab:40s} ' + ' | '.join(cells))
    def compare(lab, pa, pb):
        for nm, msk in (('Οκτ-Δεκ', OCTDEC), ('ολη', np.ones(len(IDX), bool))):
            wins, cells = 0, []
            for s in EV:
                k = (SE == s) & msk
                ra, rb = np.sqrt(np.mean((ACT - pa[IDX])[k] ** 2)), np.sqrt(np.mean((ACT - pb[IDX])[k] ** 2))
                wins += ra < rb; cells.append(f'{s}:{ra - rb:+.3f}')
            P(f'  {lab} [{nm}]: διαφορα RMSE ανα σεζον ' + ' '.join(cells) + f' → καλυτερο σε {wins}/{len(EV)} → {"ΠΕΡΝΑ" if wins >= 4 else "✗"}')

    # ---------------- ΣΤΑΔΙΟ 1 ----------------
    P('=== ΣΤΑΔΙΟ 1: πλεγμα βασικων ρυθμισεων ===')
    G1 = [dict(h=h, lam=l, HL=hl, carry=c, lw=w) for c in (.5, .6, .7, .8, .9, 1.0) for l in (2, 4, 6, 8, 12)
          for hl in (20, 30, 45, 60, 9999) for w in (0.0, 0.25, 0.5, 0.75, 1.0) for h in (1.0, 1.5, 2.0, 2.5, 3.0)]
    runall(G1)
    K1 = [key(c) for c in G1]
    SC1 = {k: score(k) for k in K1}
    names = ['εδρα', 'K', 'HL', 'περσι', 'τυχη']
    for per, pl in (('od', 'Οκτ-Δεκ'), ('all', 'ολη σεζον')):
        P(f'  προφιλ ({pl}, μεσο RMSE 5 σεζον, καλυτερο για καθε τιμη):')
        for j, nm in enumerate(names):
            vals = sorted({k[j] for k in K1})
            P(f'    {nm:6s} ' + ' · '.join(f'{v:g}: {min(np.mean([SC1[k][(s, per)] for s in EV]) for k in K1 if k[j] == v):.3f}' for v in vals))
        bestall = min(K1, key=lambda k: np.mean([SC1[k][(s, per)] for s in EV]))
        P(f'    καλυτερο συνολικα: εδρα {bestall[0]} · K {bestall[1]} · HL {bestall[2]} · περσι {bestall[3]} · τυχη {bestall[4]} '
          f'({np.mean([SC1[bestall][(s, per)] for s in EV]):.3f} vs τρεχουσα {np.mean([SC1[CUR][(s, per)] for s in EV]):.3f})')
    P('')
    held1, ch1, _ = loso(K1, 'od'); held1a, ch1a, _ = loso(K1, 'all')
    P('  LOSO επιλογες (Οκτ-Δεκ): ' + ' | '.join(f'{Y}: εδρα {k[0]} K {k[1]} HL {k[2]} περσι {k[3]} τυχη {k[4]}' for Y, k in held1.items()))
    P('  LOSO επιλογες (ολη):     ' + ' | '.join(f'{Y}: εδρα {k[0]} K {k[1]} HL {k[2]} περσι {k[3]} τυχη {k[4]}' for Y, k in held1a.items()))
    pcur = PRED[CUR]; p1 = heldpred(held1); p1a = heldpred(held1a)
    rep('τρεχουσα (2/8/60/0.7/0.5)', pcur); rep('ΣΤΑΔΙΟ 1 LOSO (κριση Οκτ-Δεκ)', p1); rep('ΣΤΑΔΙΟ 1 LOSO (κριση ολη)', p1a)
    compare('(1) πλεγμα vs τρεχουσα, επιλογη Οκτ-Δεκ', p1, pcur)
    compare('(1β) πλεγμα vs τρεχουσα, επιλογη ολη', p1a, pcur)
    P('')

    # ---------------- ΣΤΑΔΙΟ 2 ----------------
    b1 = min(K1, key=lambda k: np.mean([SC1[k][(s, 'od')] for s in EV]))
    P(f'=== ΣΤΑΔΙΟ 2: εδρα ανα ομαδα & ρόστερ (σταθερα απο σταδιο 1: εδρα {b1[0]} · HL {b1[2]} · τυχη {b1[4]}) ===')
    G2 = [dict(h=b1[0], lam=l, HL=b1[2], carry=c, lw=b1[4], lam_u=u, beta=bt) for c in (.5, .6, .7, .8, .9, 1.0) for l in (2, 4, 6, 8, 12)
          for u in (None, 80, 40, 20, 10) for bt in (0.0, 0.5, 1.0, 1.5)]
    runall(G2)
    K2 = [key(c) for c in G2]
    SC2 = {k: score(k) for k in K2}
    P('  προφιλ (Οκτ-Δεκ / ολη):')
    for j, nm, vals in ((5, 'εδρα ανα ομαδα lam_u (0=κοινη)', (0, 80, 40, 20, 10)), (6, 'ρόστερ beta', (0.0, 0.5, 1.0, 1.5)), (3, 'περσι', (.5, .6, .7, .8, .9, 1.0)), (1, 'K', (2, 4, 6, 8, 12))):
        P(f'    {nm:30s} ' + ' · '.join(f'{v:g}: {min(np.mean([SC2[k][(s, "od")] for s in EV]) for k in K2 if k[j] == v):.3f}/'
                                        f'{min(np.mean([SC2[k][(s, "all")] for s in EV]) for k in K2 if k[j] == v):.3f}' for v in vals))
    sub = lambda f: [k for k in K2 if f(k)]
    for per, pl in (('od', 'Οκτ-Δεκ'), ('all', 'ολη')):
        P(f'  --- επιλογη με κριση {pl} ---')
        base_ = heldpred(loso(sub(lambda k: k[5] == 0 and k[6] == 0), per)[0])
        home_ = heldpred(loso(sub(lambda k: k[6] == 0), per)[0])
        ros_h, _, _ = loso(sub(lambda k: k[5] == 0), per); ros_ = heldpred(ros_h)
        all_h, _, _ = loso(K2, per); all_ = heldpred(all_h)
        P('    επιλογες «ολα»: ' + ' | '.join(f'{Y}: K {k[1]} περσι {k[3]} lam_u {k[5]:g} beta {k[6]:g}' for Y, k in all_h.items()))
        P('    επιλογες «ρόστερ»: ' + ' | '.join(f'{Y}: K {k[1]} περσι {k[3]} beta {k[6]:g}' for Y, k in ros_h.items()))
        rep('χωρις επεκτασεις', base_); rep('+ εδρα ανα ομαδα', home_); rep('+ ρόστερ', ros_); rep('+ ολα', all_)
        compare('(2) εδρα ανα ομαδα vs κοινη', home_, base_)
        compare('(3) ρόστερ vs χωρις', ros_, base_)
        compare('(4) ολα vs ΤΡΕΧΟΥΣΑ', all_, pcur)
    open('nba_base_grid_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

if __name__ == '__main__':
    main()
