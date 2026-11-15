# -*- coding: utf-8 -*-
"""bcl_move_against.py — BCL: PICKS ΧΑΝΤΙΚΑΠ ΟΠΟΥ Η ΑΓΟΡΑ ΚΙΝΗΘΗΚΕ ΚΟΝΤΡΑ ΑΠΟ ΤΟ ΑΝΟΙΓΜΑ ΩΣ ΤΟ ΚΛΕΙΣΙΜΟ (13/10/2026, Στελιος: Rytas & Περιστερι «εχουν φαει
κοντρα απο οταν ανοιξαν — ποσους ποντους και συγκριση με ιστορικα δειγματα BCL»). Live φορμουλα (bcl_engine_preds_live.pkl, χωρις αποδοσεις νικητη),
σ 12, pick στο ΑΝΟΙΓΜΑ με edge ≥8%, Crown & Bet365 (Nowgoal, μεσος), 2021-26. Κινηση = (γραμμη κλεισιματος − γραμμη ανοιγματος) στην πλευρα του pick
(− = κοντρα). ROI στην τιμη ανοιγματος και αν το επαιζες στο κλεισιμο. Ανα αγων 1-3 / 4+ και φαβορι/αουτσαιντερ. ΠΕΡΙΓΡΑΦΙΚΟ. Εξοδος: bcl_move_against_out.txt"""
import sys, json, pickle, collections
import numpy as np
from statistics import NormalDist
Phi = NormalDist().cdf
sys.stdout.reconfigure(encoding='utf-8')
D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); MK = pickle.load(open('bcl_mk.pkl', 'rb'))
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
E = {e['id']: e for k, L in FG.items() if k.startswith('BCL_') for e in L if e.get('hs') not in (None, '')}
cnt = collections.Counter(); GN = {}
for k, L in FG.items():
    if not k.startswith('BCL_'): continue
    y = int(k.split('_')[1])
    for e in sorted([x for x in L if x.get('hs') not in (None, '')], key=lambda x: x['ts']):
        cnt[(y, e['hid'])] += 1; cnt[(y, e['aid'])] += 1; GN[e['id']] = max(cnt[(y, e['hid'])], cnt[(y, e['aid'])])
def cover(m_, L, s=12.0):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
res = lambda x, o: (o - 1) if x > 0 else (0 if x == 0 else -1)
rows = []
for k, i in enumerate(D['id']):
    if i not in E or i not in MK or not np.isfinite(D['FIN'][k]): continue
    act = int(E[i]['hs']) - int(E[i]['as_']); m = float(D['FIN'][k]); z = '1-3' if GN.get(i, 0) <= 3 else '4+'
    for b in (3, 8):
        o = MK[i].get(b, {}).get('o'); c = MK[i].get(b, {}).get('c')
        if not o or not c: continue
        L, _, o1, o2 = o; pw, pp, pl = cover(m, L); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e < .08: continue
        Lc = c[0]; oc = c[2] if side == 1 else c[3]
        mv = (Lc - L) * side                       # + = η γραμμη της πλευρας μας μεγαλωσε (καλυτερη για εμας στο κλεισιμο) = η αγορα πηγε ΚΟΝΤΡΑ
        ln = L * side                              # γραμμη της πλευρας μας στο ανοιγμα (+ = παιρνουμε ποντους)
        rows.append(dict(y=int(D['y'][k]), z=z, bk=b, mv=mv, role='dog' if ln > 0 else 'fav', gap=abs(m + L),
                         pa=res((act + L) * side, od), pc=res((act + Lc) * side, oc)))
import pandas as pd
X = pd.DataFrame(rows)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d, col='pa'):
    if not len(d): return f'{"—":>24}'
    g = d.groupby('bk')[col]; ps = d.groupby('y')[col].mean()
    return f'{100*g.mean().mean():+6.1f}% ({g.size().mean():3.0f}, {int((ps > 0).sum())}/{ps.size})'
B = [('προς εμας (γραμμη μικρυνε)', -99, -0.25), ('καμια κινηση', -0.25, 0.25), ('κοντρα 0.5-1.5', 0.25, 1.75), ('κοντρα 2-2.5', 1.75, 2.75), ('κοντρα ≥3', 2.75, 99)]
P('BCL ΧΑΝΤΙΚΑΠ · pick στο ΑΝΟΙΓΜΑ (live φορμουλα, edge ≥8%) · κινηση ανοιγμα→κλεισιμο · μεσος Crown/Bet365 · ROI (picks, θετικες σεζον)')
P('«κοντρα Χ» = η αγορα κινηθηκε Χ ποντους μακρια απο το pick (π.χ. Rytas +1.5 → +4.5 = κοντρα 3)')
for lab, msk in (('ΟΛΑ', X.z.notna()), ('αγων 1-3', X.z == '1-3'), ('αγων 4+', X.z == '4+'), ('ΑΟΥΤΣΑΪΝΤΕΡ', X.role == 'dog'), ('αουτσαιντερ αγων 1-3', (X.role == 'dog') & (X.z == '1-3'))):
    d0 = X[msk]; P(''); P(f'=== {lab} ===')
    for bl, lo, hi in B:
        d = d0[(d0.mv > lo) & (d0.mv <= hi)]
        P(f'  {bl:28s} στο ανοιγμα {cell(d)} · αν επαιζα στο κλεισιμο {cell(d, "pc")}')
open('bcl_move_against_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
