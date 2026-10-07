# -*- coding: utf-8 -*-
"""bcl_league_level_test.py — BCL: ΕΠΙΠΕΔΟ ΠΡΩΤΑΘΛΗΜΑΤΟΣ αντι για «ολοι προς το 0» (7/10/2026, Στελιος: «δεν μπορουμε να χρησιμοποιουμε
εγχωρια για καποιες ομαδες και για αλλες οχι — να προσαρμοσουμε τη δυναμικοτητα των πρωταθληματων, οπως το Elo στο ποδοσφαιρο»).
ΜΙΚΡΑ πρωταθληματα = Τσεχια, Φινλανδια (ηδη κατεβασμενα, σημερα ΕΚΤΟΣ) + Βουλγαρια, Πορτογαλια, Ελβετια, Κυπρος, Δανια, Γεωργια, Σλοβακια (fs_bk_extra2).
Εκδοχες (χαντικαπ, live μηχανη: 0.25·μονο BCL + 0.75·κοινη κλιμακα [περσι 1.3, λ 1.5, φιλικα .5, εγχωρια ×1.5]):
  Α σημερα (χωρις μικρα) · Β ολα τα μικρα, χωρις προσαρμογη · Γ ολα τα μικρα + ΕΠΙΠΕΔΟ ΠΡΩΤΑΘΛΗΜΑΤΟΣ (lamL {1,3,10}, LOSO) ·
  Δ επιπεδο πρωταθληματος ΧΩΡΙΣ μικρα (βοηθα γενικα;)
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): στοχος = ματς BCL 2021-26 με ομαδα μικρου πρωταθληματος (φετος ή περσι). Εκδοχη ΚΕΡΔΙΖΕΙ την Α αν το λαθος
  στον στοχο πεφτει σε ≥4/5 σεζον ΚΑΙ τα υπολοιπα ματς δεν χειροτερευουν > 0.01. Εξοδος: bcl_league_level_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, pickle, collections
import numpy as np
SMALL = {'CZE', 'FIN', 'BUL', 'POR', 'SUI', 'CYP', 'DEN', 'GEO', 'SVK'}

def _job(a):
    import bcl_common as B
    name, allsmall, lgl, lamL = a
    rows = B.load(pre=True, extra2=allsmall, include=('CZE', 'FIN') if allsmall else ())
    return a, B.run(rows, 1.3, 1.5, 9999.0, 25.0, kf=0.5, wo=1.5, lglevel=lgl, lamL=lamL)

def main():
    from multiprocessing import Pool
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    jobs = [('Α', False, False, 0), ('Β', True, False, 0)] + [('Γ', True, True, l) for l in (1.0, 3.0, 10.0)] + [('Δ', False, True, l) for l in (1.0, 3.0, 10.0)]
    with Pool(len(jobs)) as pool: R = dict(pool.map(_job, jobs))
    import bcl_common as B
    D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); ids, ys = D['id'], D['y']
    pos = {i: k for k, i in enumerate(ids)}
    def arr(pr):
        v = np.full(len(ids), np.nan)
        for mid, (p, y) in pr.items():
            if mid in pos: v[pos[mid]] = p
        return v
    A0 = arr(R[jobs[0]]); M1 = (D['FIN'] - .75 * A0) / .25
    H = {k: .25 * M1 + .75 * arr(v) for k, v in R.items()}
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
    act = np.array([(int(E[i]['hs']) - int(E[i]['as_'])) if i in E else np.nan for i in ids], float)
    rows = B.load(pre=False, extra2=True, include=('CZE', 'FIN')); by_y = collections.defaultdict(list)
    for r in rows: by_y[r[0]].append(r)
    MC = {y: B._main_comp(v) for y, v in by_y.items()}
    tgt = np.zeros(len(ids), bool)
    for k, i in enumerate(ids):
        if i not in E: continue
        y = int(ys[k]); a_ = B.ALIAS.get(E[i]['hid'], E[i]['hid']); b_ = B.ALIAS.get(E[i]['aid'], E[i]['aid'])
        if any((MC.get(y, {}).get(t) or MC.get(y - 1, {}).get(t)) in SMALL for t in (a_, b_)): tgt[k] = True
    EV = [2021, 2022, 2023, 2024, 2025]; ev = np.isin(ys, EV)
    def rm(v, m): m = m & np.isfinite(v) & np.isfinite(act); return float(np.sqrt(np.mean((act - v)[m] ** 2))) if m.any() else np.nan
    P(f'ματς BCL 2021-26: {int(ev.sum())} · με ομαδα μικρου πρωταθληματος: {int((tgt & ev).sum())} (' + ' '.join(f'{Y}:{int((tgt & (ys == Y)).sum())}' for Y in EV) + ')')
    cnt = collections.Counter(c for y in MC for c in MC[y].values() if c in SMALL); P('ομαδες-σεζον ανα μικρο πρωταθλημα: ' + str(dict(cnt)))
    base = H[jobs[0]]
    def show(lab, v):
        d = [rm(v, tgt & (ys == Y)) - rm(base, tgt & (ys == Y)) for Y in EV]; dr = rm(v, ~tgt & ev) - rm(base, ~tgt & ev)
        ok = sum(x < 0 for x in d) >= 4 and dr <= .01
        P(f'  {lab:34s} στοχος {rm(base, tgt & ev):.3f} → {rm(v, tgt & ev):.3f} · ' + ' '.join(f'{x:+.2f}' for x in d) + f' → {sum(x < 0 for x in d)}/5 · υπολοιπα {dr:+.3f} · ολα {rm(v, ev):.3f}'
          + ('  <- ΚΕΡΔΙΖΕΙ' if ok else '  ✗'))
    P(''); P(f'  Α σημερα: στοχος {rm(base, tgt & ev):.3f} · υπολοιπα {rm(base, ~tgt & ev):.3f} · ολα {rm(base, ev):.3f}')
    show('Β ολα τα μικρα, χωρις προσαρμογη', H[jobs[1]])
    for nm in ('Γ', 'Δ'):
        ks = [k for k in jobs if k[0] == nm]
        for k in ks: show(f'{nm} lamL {k[3]:g} (in-sample)', H[k])
        held = np.full(len(ids), np.nan); ch = []
        for Y in EV:
            tr = tgt & ev & (ys != Y) if nm == 'Γ' else ev & (ys != Y)
            kb = min(ks, key=lambda k: rm(H[k], tr)); ch.append(kb[3]); m = ys == Y; held[m] = H[kb][m]
        show(f'{nm} LOSO lamL {ch}', held)
    open('bcl_league_level_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

if __name__ == '__main__':
    main()
