# -*- coding: utf-8 -*-
"""ec_favdog_split.py — EuroCup χαντικαπ: ΦΑΒΟΡΙ vs ΑΟΥΤΣΑΪΝΤΕΡ στους κανονες που δοκιμαστηκαν οταν μπηκε το live (13/10/2026, Στελιος «ηταν τα ιδια
αποτελεσματα ή κανεις λαθος;»). ec_fresh_market.pkl (ιδιο αρχειο με ec_late_picks_test / ec_sigma_edge), Crown U2020-25, pick στο ΑΝΟΙΓΜΑ.
Κανονες: LIVE = μοντελο μονο του (σ 11.5, edge ≥8%) · ΜΙΞΗ = 50/50 με την αγορα (σ 12.3, ≥6%, ec_hcap_mix_nested «προτεινομενος»).
Προβλεψεις: 'held' (οπως τα παλια τεστ) και 'live'. Εξοδος: ec_favdog_split_out.txt"""
import sys, pickle, collections
import numpy as np
from statistics import NormalDist
Phi = NormalDist().cdf
sys.stdout.reconfigure(encoding='utf-8')
EVM = ['U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']
D = pickle.load(open('ec_fresh_market.pkl', 'rb')); S = np.asarray(D['seasn']); GN = np.asarray(D['GN']); ACT = D['act']
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
res = lambda x, o: (o - 1) if x > 0 else (0 if x == 0 else -1)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(R):
    u = [x for v in R.values() for x in v]
    if not u: return '—'
    return f'{np.mean(u)*100:+6.1f}% ({len(u):3d}, {sum(u):+5.1f}u, θετ {sum(1 for Y in EVM if R.get(Y) and np.mean(R[Y]) > 0)}/{sum(1 for Y in EVM if R.get(Y))})'
for pk in ('held', 'live'):
    if pk not in D: continue
    M = D[pk]
    for rule, w, sg, thr in (('LIVE (μοντελο, σ11.5, ≥8%)', 1.0, 11.5, .08), ('ΜΙΞΗ 50/50 (σ12.3, ≥6%)', .5, 12.3, .06)):
        R = collections.defaultdict(lambda: collections.defaultdict(list))
        for i in D['MK']:
            if S[i] not in EVM or not np.isfinite(M[i]): continue
            L, mk, o1, o2 = D['MK'][i]['o']; Lc, _, c1, c2 = D['MK'][i]['c']
            m = (-L) + w * (M[i] - (-L))
            pw, pp, pl = cover(m, L, sg); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
            s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
            if e < thr: continue
            role = 'ΦΑΒΟΡΙ' if L * s_ < 0 else ('ΑΟΥΤΣ.' if L * s_ > 0 else 'PK')
            z = '1-6' if GN[i] <= 5 else '7+'
            ua = res((ACT[i] + L) * s_, od); uc = res((ACT[i] + Lc) * s_, c1 if s_ == 1 else c2)
            for k in ((role, 'ΟΛΑ'), (role, z), ('ΟΛΑ', 'ΟΛΑ')):
                R[k + ('o',)][S[i]].append(ua); R[k + ('c',)][S[i]].append(uc)
        P(''); P(f'=== {rule} · προβλεψεις {pk} ===')
        for role in ('ΟΛΑ', 'ΦΑΒΟΡΙ', 'ΑΟΥΤΣ.'):
            for z in (('ΟΛΑ',) if role == 'ΟΛΑ' else ('ΟΛΑ', '1-6', '7+')):
                P(f'  {role:7s} {z:4s} ανοιγμα {cell(R[(role, z, "o")])} · κλεισιμο {cell(R[(role, z, "c")])}')
open('ec_favdog_split_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
