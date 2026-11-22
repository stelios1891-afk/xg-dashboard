# -*- coding: utf-8 -*-
"""psg_deep_picks.py — 19/10/2026. Κοστισε η υποτιμηση της Παρι σε picks; + ΓΕΝΙΚΟ τεστ φιλτρου (οχι μονο Παρι):
«ομαδα που η αγορα την εβλεπε ΠΕΡΣΙ σταθερα καλυτερη απο το μοντελο» (μεσο αγορα−μοντελο περσινης σεζον ≥ +0.25, ≥6 ματς).
Απλοποιημενα picks στο ΚΛΕΙΣΙΜΟ (Crown & SBOBET χωριστα, μεσος): |γραμμη| ≥0.5, 1.70-2.10, φαβ σωστα τεταρτα / dog p_cover, edge ≥4% ή ≥10%,
ολες οι διοργανωσεις. Περιγραφικο (οχι ο ακριβης live κανονας ανα διοργανωση)."""
import sys, os
_s = open('uel_full_review.py', encoding='utf-8').read().split("print('=' * 100 + NL + '1. ΣΥΝΟΛΑ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
D = pd.read_pickle('psg_deep_rows.pkl'); D['km'] = D.kgd - D.mgd
IDX = {str(m): i for i, m in enumerate(MIDS)}
TS = D.groupby(['team', 'sea']).agg(km=('km', 'mean'), n=('km', 'size'))
SS = sorted(D.sea.unique()); PREV = {SS[k]: SS[k - 1] for k in range(1, len(SS))}
def prev_km(t, s):
    p = PREV.get(s)
    if p is None or (t, p) not in TS.index: return np.nan
    r = TS.loc[(t, p)]; return r.km if r.n >= 6 else np.nan
H = D[D.home].set_index('mid')
rows = []
for mid, r in H.iterrows():
    i = IDX[mid]; dist = sdist(LH_N[i], LA_N[i])
    for bk in ('Crown', 'SBOBET'):
        s = snap_ah(mid, bk, 0)
        if not s: continue
        L, oh, oa = s
        for side, ln, o in ((1, L, oh), (-1, -L, oa)):
            if not (1.70 <= o <= 2.10) or abs(ln) < 0.5: continue
            pw, pp = cover_q(dist, side, ln) if ln < 0 else picks.p_cover(dist, side, ln)
            e = edge(pw, pp, o)
            if e < 0.04: continue
            tm, op = (r.team, r.opp) if side == 1 else (r.opp, r.team)
            rows.append(dict(mid=mid, bk=bk, sea=r.sea, comp=r.comp, team=tm, opp=op, e=e, role='φαβ' if ln < 0 else 'dog',
                             pnl=picks.settle(GD[i], side, ln, o), pk_t=prev_km(tm, r.sea), pk_o=prev_km(op, r.sea)))
B = pd.DataFrame(rows)
def cc(y):
    if not len(y): return '—'
    m = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean(); se = y.pnl.std() / np.sqrt(max(n, 1))
    return f'{n:4.0f} picks · ROI {100 * m.mean():+6.1f}% ±{100 * se:.0f} · μοναδες {m.mean() * n:+5.1f}'
PSG = 'Paris Saint-Germain'
print('Ε9. PICKS ΣΤΑ ΜΑΤΣ ΤΗΣ ΠΑΡΙ (κλεισιμο, edge ≥4%, 2022-26)')
for lab, y in (('ΚΟΝΤΡΑ στην Παρι', B[B.opp == PSG]), ('ΥΠΕΡ της Παρι', B[B.team == PSG])):
    for th in (.04, .10):
        z = y[y.e >= th]; print(f'   {lab:18s} ≥{int(th * 100):2d}%: {cc(z)} · ανα σεζον ' + ' '.join(f'{s}:{len(v) / max(v.bk.nunique(), 1):.0f}/{100 * v.pnl.mean():+.0f}%' for s, v in z.groupby('sea')))
print('\nΕ10. ΓΕΝΙΚΟ ΦΙΛΤΡΟ — picks ΚΟΝΤΡΑ σε ομαδα που περσι η αγορα την εβλεπε καλυτερη απο το μοντελο (περσινο αγορα−μοντ)')
for th in (.04, .10):
    z = B[B.e >= th]
    print(f'   edge ≥{int(th * 100)}%  ολα: {cc(z)}')
    for lab, f in (('αντιπαλος περσι ≥+0.25 (η αγορα τον «ηξερε»)', z.pk_o >= .25), ('αντιπαλος περσι 0…+0.25', (z.pk_o >= 0) & (z.pk_o < .25)),
                   ('αντιπαλος περσι <0', z.pk_o < 0), ('αντιπαλος χωρις περσινα', z.pk_o.isna()),
                   ('ΥΠΕΡ ομαδας με περσι ≥+0.25', z.pk_t >= .25), ('ΥΠΕΡ ομαδας με περσι ≤−0.25', z.pk_t <= -.25)):
        y = z[f]; print(f'      {lab:44s} {cc(y)} · ανα σεζον ' + ' '.join(f'{s}:{100 * v.pnl.mean():+.0f}%' for s, v in y.groupby('sea')))
print('   ποιες ομαδες ειχαν περσι ≥+0.25 (ομαδα-σεζον): ' + ', '.join(sorted({f'{t[:14]} {s}' for (t, s) in TS.index if prev_km(t, s) >= .25})))
