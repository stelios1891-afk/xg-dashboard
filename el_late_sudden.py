# -*- coding: utf-8 -*-
"""el_late_sudden.py — ΕΥΡΩΛΙΓΚΑ ΧΑΝΤΙΚΑΠ: τα picks «ξαφνικης κινησης» (Β) — ειναι λογω απουσιας; (29/10/2026, Στελιος: «η ξαφνικη κινηση ειναι
λογω απουσιας και θεωρουμε οτι η αγορα υπερτιμα την απουσια;»).
Ιδια σαρωση με el_late_groups (σημερινη μηχανη PIR + αμυνα, χωρις κανονες αποφυγης). Για καθε pick Β (κοντρα ≥1 π. σε 1ω) και Γ (σταδιακη, συγκριση):
  ειδησεις RotoWire τις 2 ωρες πριν (για την ομαδα που ΠΑΙΖΟΥΜΕ / την ΑΝΤΙΠΑΛΗ) · αν αλλαξε και η ΔΙΚΗ μας διορθωση απουσιων τις 3 ωρες πριν
  (+ = η αλλαγη πηγε υπερ της πλευρας μας) · ποιος ηταν τελικα εκτος (box) απο την ομαδα μας / την αντιπαλη χωρις να το ξερουμε (αιφνιδια).
Εξοδος: el_late_sudden_out.txt"""
import os, sys, io, contextlib, bisect, time
import numpy as np
ROOT = r'C:\Users\steli\My Drive\Betting Model'; os.chdir(ROOT); sys.path.insert(0, ROOT)
T00 = time.time()
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open('el_pird_tests.py', encoding='utf-8').read().split('# ---- σαρωση σαν scanner ----')[0]
s0 = "def save(): open('el_pird_tests_out.txt', 'w', encoding='utf-8').write('" + chr(92) + "n'.join(out))"
assert src.count(s0) == 1
TH = {'__name__': 'pird'}
with contextlib.redirect_stdout(_B()): exec(src.replace(s0, 'def save(): return'), TH)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open('el_late_sudden_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
S = TH['S']; SE = S['SE']
rows, NT, REC, edge_pick, settle, featsPD, BPD, CAND, wts = (S['rows'], S['NT'], S['REC'], S['edge_pick'], S['settle'], TH['featsPD'], TH['BPD'], S['CAND'], S['wts'])
def mu_at(ser, t):
    i = bisect.bisect_right([x[0] for x in ser], t) - 1; return ser[max(i, 0)]
L = []
for i, r in enumerate(rows):
    b = BPD[('loso', r['y'])]
    d_ = REC[21][r['pos']]; tip = d_['tip']; ser = [x for x in d_['ser'] if x[0] < tip]
    if not ser or b is None: continue
    t0 = ser[0][0]; tl = [x[0] for x in ser]
    nts = set(t + 900 for team in (r['hc'], r['ac']) for t in NT.get((r['sea'], team), []) if t0 < t + 900 < tip)
    prev_a = None
    for j, e in enumerate(sorted(set(tl) | nts)):
        row = ser[bisect.bisect_right(tl, e) - 1]; a = float(featsPD(i, e) @ b)
        sd, ed, od = edge_pick(r['m'] + a, row[2], row[3], row[4])
        if ed >= .08:
            if j == 0: break
            if prev_a is not None and abs(a - prev_a) > 1e-9:
                sd0, ed0, _ = edge_pick(r['m'] + prev_a, row[2], row[3], row[4])
                if not (ed0 >= .08 and sd0 == sd): break                      # γκρουπ Α (απουσια) — εκτος
            m1 = (row[1] - mu_at(ser, e - 3600)[1]) * sd
            m36 = min((row[1] - mu_at(ser, e - 3 * 3600)[1]) * sd, (row[1] - mu_at(ser, e - 6 * 3600)[1]) * sd)
            grp = 'Β ΞΑΦΝΙΚΗ' if m1 <= -1.0 else ('Γ ΣΤΑΔΙΑΚΗ' if m36 <= -0.5 else None)
            if grp is None: break
            own = r['hc'] if sd == 1 else r['ac']; opp = r['ac'] if sd == 1 else r['hc']
            def nnews(team): return sum(1 for t in NT.get((r['sea'], team), []) if e - 900 - 2 * 3600 <= t <= e - 900 + 1e-6)
            a3 = float(featsPD(i, e - 3 * 3600) @ b) if e - 3 * 3600 > t0 else float(featsPD(i, t0) @ b)
            # αιφνιδια: τακτικοι που ΤΕΛΙΚΑ δεν επαιξαν αλλα η RotoWire τη στιγμη e δεν τους ειχε OUT/GTD
            surp = {}
            for team, (s_, lst, W, ZP, ZS) in CAND[i].items():
                w_rw = wts(r, lst, S['news_state'](r['sea'], team, r['ts'], e)[1], 'rw'); w_box = wts(r, lst, None, 'box')
                surp[team] = float(((w_box > 0) & (w_rw == 0)).astype(float) @ W)
            L.append(dict(grp=grp, sea=r['y'], hrs=(tip - e) / 3600, dog=(row[2] > 0) if sd == 1 else (row[2] < 0), u=settle(r['act'], row[2], sd, od),
                          n_own=nnews(own), n_opp=nnews(opp), dadj=(a - a3) * sd, s_own=surp.get(own, 0.0), s_opp=surp.get(opp, 0.0), move=m1))
            break
        prev_a = a
P(f'picks Β/Γ: {len(L)} · {time.time() - T00:.0f} δευτ.')
def st(X):
    if not X: return '—'
    u = np.array([x['u'] for x in X]); ps = {s: sum(x['u'] for x in X if x['sea'] == s) for s in SE}
    return f'{len(X):3d} picks · {u.sum():+6.1f}μ · ROI {u.mean() * 100:+6.1f}% · θετ {sum(v > 0 for v in ps.values())}/5'
for g in ('Β ΞΑΦΝΙΚΗ', 'Γ ΣΤΑΔΙΑΚΗ'):
    G = [x for x in L if x['grp'] == g]
    P(''); P(f'## {g}: {st(G)}')
    P(f'  ειδηση RotoWire τις 2ω πριν: για ΤΗΝ ΟΜΑΔΑ ΜΑΣ {st([x for x in G if x["n_own"] > 0])}')
    P(f'                                για την ΑΝΤΙΠΑΛΗ  {st([x for x in G if x["n_opp"] > 0 and x["n_own"] == 0])}')
    P(f'                                καμια ειδηση      {st([x for x in G if x["n_own"] == 0 and x["n_opp"] == 0])}')
    P(f'  η ΔΙΚΗ μας διορθωση αλλαξε τις 3ω πριν (≥0.3 π.): υπερ μας {st([x for x in G if x["dadj"] >= 0.3])} · κοντρα {st([x for x in G if x["dadj"] <= -0.3])} · σχεδον ιδια {st([x for x in G if abs(x["dadj"]) < 0.3])}')
    P(f'  ΑΙΦΝΙΔΙΑ απουσια (τακτικος που ΔΕΝ επαιξε, η RotoWire δεν το ειχε): στην ΟΜΑΔΑ ΜΑΣ {st([x for x in G if x["s_own"] >= 0.3])} · στην αντιπαλη {st([x for x in G if x["s_opp"] >= 0.3 and x["s_own"] < 0.3])} · καμια {st([x for x in G if x["s_own"] < 0.3 and x["s_opp"] < 0.3])}')
    P(f'  αουτσ. {st([x for x in G if x["dog"]])} · φαβορι {st([x for x in G if not x["dog"]])} · <2ω {st([x for x in G if x["hrs"] <= 2])} · >2ω {st([x for x in G if x["hrs"] > 2])}')
    P(f'  μεγεθος αλματος: 1-1.5 π. {st([x for x in G if -1.5 < x["move"] <= -1.0])} · ≥1.5 π. {st([x for x in G if x["move"] <= -1.5])}' if g.startswith('Β') else '')
P(f'\nχρονος {time.time() - T00:.0f} δευτ.'); save()
