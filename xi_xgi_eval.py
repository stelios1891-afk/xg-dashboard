# -*- coding: utf-8 -*-
"""xi_xgi_eval.py — 21/10/2026: προσθετει το xGI παικτη (xi_xgi_rows.csv) κατι στα ΣΥΝΟΛΑ και στο ΧΑΝΤΙΚΑΠ; LOSO 4 σεζον, bootstrap ανα εβδομαδα.
ΣΥΝΟΛΑ — αναφορα = Σ2 (εμπιστοσυνη & αξια επιθεσης/μεσων και αμυνας, αθροισμα 2 ομαδων — ο μονος τροπος που περασε)
  vs: xGI 11αδας (αθροισμα 2 ομαδων) · xG-μονο · xA-μονο · xGI μονο μεσοι/επιθεση · αναφορα + xGI
ΧΑΝΤΙΚΑΠ — αναφορα = αξια + εμπιστοσυνη (διαφορα) vs + διαφορα xGI
ΑΝΑ ΠΛΕΥΡΑ — γκολ/xG που βαζει καθε ομαδα ~ Δ xGI της (επιθεση) [+ εμπιστοσυνη αμυνας αντιπαλου]
ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ): το xGI κρατιεται μονο αν βελτιωνει την αναφορα εκτος δειγματος σε ≥3/4 σεζον ΚΑΙ στο xG ΚΑΙ στα γκολ
  και το 90% της διαφορας απο την αναφορα ειναι πανω απο 0 σε τουλαχιστον ενα."""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NL = chr(10)
src = open('xi_age_totals_eval.py', encoding='utf-8').read()
exec(src[:src.index("print(f'ματς {len(D)}')")])                     # D (στοχοι + αξια/εμπιστοσυνη), gains, boot, show, SE
for c in ('Vlog', 'Tm10'):
    D[f's_{c}'] = D[f'{c}_h'] + D[f'{c}_a']
    for g in ('gk', 'df', 'md', 'at'): D[f's_{c}{g}'] = D[f'{c}{g}_h'].fillna(0) + D[f'{c}{g}_a'].fillna(0)
    D[f's_{c}O'] = D[f's_{c}md'] + D[f's_{c}at']; D[f's_{c}D'] = D[f's_{c}gk'] + D[f's_{c}df']
Xg = pd.read_csv('xi_xgi_rows.csv', dtype={'mid': str})
D = D.merge(Xg, on='mid', how='left')
for me in ('XGI', 'XG', 'XA', 'XGIat'):
    D[f's_{me}'] = D[f'{me}_h'] + D[f'{me}_a']; D[f'x_{me}'] = D[f'{me}_h'] - D[f'{me}_a']
_defs = src[src.index('def gains('):src.index("print(f'ματς {len(D)}')")]
exec(_defs)                                                            # ξαναοριζω gains/boot/show πανω στο νεο D (με xGI)
print(f'ματς {len(D)} · με xGI {D.s_XGI.notna().sum()}')
print(f'κατανομη Δ xGI ενδεκαδας (ανα ομαδα): sd {D.XGI_h.std():.3f} · 5% {D.XGI_h.quantile(.05):+.3f} · 95% {D.XGI_h.quantile(.95):+.3f}')
YT = [('r_tx', 'xG'), ('r_tg', 'γκολ')]
REF_T = ['s_VlogO', 's_VlogD', 's_Tm10O', 's_Tm10D']
print(f'{NL}{"=" * 150}{NL}Α. ΣΥΝΟΛΑ — λαθος μοντελου στο ΣΥΝΟΛΟ xG / ΣΥΝΟΛΟ γκολ (βελτιωση ×1000 εκτος δειγματος [90%], ανα σεζον)')
show('αναφορα Σ2 (εμπιστ.+αξια ανα θεση)', REF_T, YT)
show('xGI ενδεκαδας (και οι 2)', ['s_XGI'], YT, REF_T)
show('xG-μονο', ['s_XG'], YT, REF_T)
show('xA-μονο', ['s_XA'], YT, REF_T)
show('xGI μονο μεσοι/επιθεση', ['s_XGIat'], YT, REF_T)
show('αναφορα + xGI', REF_T + ['s_XGI'], YT, REF_T)
print(f'{NL}{"=" * 150}{NL}Β. ΧΑΝΤΙΚΑΠ — διαφορα xG / διαφορα γκολ')
REF_H = ['x_Vlog', 'x_Tm10']; YD = [('r_xgd', 'xG'), ('r_gd', 'γκολ')]
show('αναφορα αξια + εμπιστοσυνη', REF_H, YD)
show('μονο διαφορα xGI', ['x_XGI'], YD, REF_H)
show('αναφορα + διαφορα xGI', REF_H + ['x_XGI'], YD, REF_H)
print(f'{NL}{"=" * 150}{NL}Γ. ΑΝΑ ΠΛΕΥΡΑ — xG / γκολ που βαζει ο ΓΗΠΕΔΟΥΧΟΣ ~ Δ xGI του (και ιδια για φιλοξενουμενο) — μεγεθος')
for side, ry, rg in (('h', 'r_xh', 'r_gh'), ('a', 'r_xa', 'r_ga')):
    q = D[D[f'XGI_{side}'].notna()]
    for lab, msk in (('xGI 11αδας ΠΟΛΥ κατω (5%)', q[f'XGI_{side}'] <= q[f'XGI_{side}'].quantile(.05)), ('ουδετερο', q[f'XGI_{side}'].abs() <= q[f'XGI_{side}'].abs().quantile(.5)),
                     ('xGI 11αδας ΠΟΛΥ πανω (5%)', q[f'XGI_{side}'] >= q[f'XGI_{side}'].quantile(.95))):
        z = q[msk]
        print(f'   {"γηπεδουχος" if side == "h" else "φιλοξενουμενος":14s} {lab:28s} n {len(z):4d} · Δ xGI {z[f"XGI_{side}"].mean():+.2f} · xG − μοντελο {z[ry].mean():+.2f} · γκολ − μοντελο {z[rg].mean():+.2f}')
