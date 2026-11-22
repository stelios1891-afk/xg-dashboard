"""
core7_nocomp_714.py — 9/10/2026 (Στελιος: «η συμπιεση ειναι απο τα compressed shots; αν ναι, βοηθα να το βγαλουμε στις 6-14;»).
LIVE (Caley συμπιεση μεγαλων ευκαιριων) vs ΧΩΡΙΣ ΣΥΜΠΙΕΣΗ (np_raw), ιδια κατα τα αλλα (σωστο SoS 0.75, DC, κοκκινες emps, K=8).
(1) Κλιμακα: ομαδοποιηση (α) κατα την αγορα (οπως στο core7_early_weakness) και (β) κατα το ΙΔΙΟ το μοντελο (χωρις μεροληψια επιλογης)·
    κλιση πραγματικου πανω στην υπεροχη του μοντελου (1 = σωστη κλιμακα, >1 = συμπιεσμενο).
(2) Ακριβεια: RMSE & πληροφορια πανω απο αγορα (β) ανα παραθυρο.
(3) Picks αγων 6-14 (dogs + κοντα φαβορι) και 15+ — ιδιοι live κανονες, Pinnacle/Crown/Bet365 κλεισιμο.
ΠΡΟ-ΔΗΛΩΣΗ «βγαζω τη συμπιεση στις 6-14»: (Α) RMSE 6-14 καλυτερο σε ≥3/4 σεζον ΚΑΙ (Β) picks 6-14 ROI (μεσος 3 βιβλιων) > live σε ≥3/4 σεζον
ΚΑΙ θετικο συνολο ΚΑΙ καλυτερο σε ≥2/3 βιβλια.
"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
s = open('core7_sos15_final.py', encoding='utf-8').read(); s = s[:s.index('RES = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'nc'}
with contextlib.redirect_stdout(_Q()): exec(s, g)
D, NG, picks = g['D'], g['NG'], g['picks']
SEAS = ['2223', '2324', '2425', '2526']
def preds(v):
    P = pd.read_csv(f'core7_mech_preds_{v}.csv', dtype={'season': str, 'mid': str}); return P[P.season.isin(SEAS)].set_index('mid')
VS = {'LIVE': preds('cur_0.75_6_13~emps'), 'ΧΩΡΙΣ ΣΥΜΠΙΕΣΗ': preds('cur_0.75_6_13~emps@nocomp')}
M = VS['LIVE'][['league', 'season', 'md', 'gd']].copy()
Dm = D.set_index('mid')
for c in ('L', 'ah', 'aa', 's_mkt'): M[f'pin_{c}'] = Dm[c].reindex(M.index)
for bk, ab in (('Crown', 'cr'), ('Bet365', 'b3')):
    q = [NG.get((m, bk)) for m in M.index]
    for i, c in enumerate(('L', 'oh', 'oa')): M[f'{ab}_{c}'] = [x[1][i] if x else np.nan for x in q]
for k, P in VS.items():
    M[f'xh_{k}'] = P.xg_h; M[f'xa_{k}'] = P.xg_a; M[f's_{k}'] = P.xg_h - P.xg_a
M['w'] = np.where(M.md.between(5, 13), '6-14', np.where(M.md >= 14, '15+', '1-5'))
A = M[M.pin_s_mkt.notna()]
def ols(y, X):
    X = np.c_[np.ones(len(y)), X]; b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    return b, np.sqrt(np.diag(np.linalg.inv(X.T @ X)) * (e @ e) / (len(y) - X.shape[1]))
print('(1) ΚΛΙΜΑΚΑ — (α) ομαδες κατα ΑΓΟΡΑ (|υπεροχη αγορας| ≥1.2) · (β) ομαδες κατα ΜΟΝΤΕΛΟ (|υπεροχη μοντελου| ≥1.0) · κλιση πραγμ. πανω στο μοντελο')
for w in ('6-14', '15+'):
    x = A[A.w == w]
    for k in VS:
        sm = x[f's_{k}']; sg = np.sign(x.pin_s_mkt); a_ = x.pin_s_mkt.abs() >= 1.2
        sg2 = np.sign(sm); b_ = sm.abs() >= 1.0
        bb, se = ols(x.gd.values.astype(float), sm.values)
        print(f'   [{w:4s}] {k:15s} (α) αγορα {(x.pin_s_mkt * sg)[a_].mean():.2f} / μοντελο {(sm * sg)[a_].mean():.2f} / πραγμ {(x.gd * sg)[a_].mean():.2f} (n{a_.sum()})'
              f' · (β) μοντελο {(sm * sg2)[b_].mean():.2f} / αγορα {(x.pin_s_mkt * sg2)[b_].mean():.2f} / πραγμ {(x.gd * sg2)[b_].mean():.2f} (n{b_.sum()})'
              f' · κλιση {bb[1]:.2f} ±{se[1]:.2f}')
print('\n(2) ΑΚΡΙΒΕΙΑ — RMSE (πραγμ. − υπεροχη) · β = πληροφορια πανω απο αγορα · RMSE ανα σεζον')
acc = {}
for w in ('6-14', '15+'):
    x = A[A.w == w]; y = x.gd.values.astype(float)
    print(f'   [{w}] αγορα RMSE {np.sqrt(np.mean((y - x.pin_s_mkt) ** 2)):.4f}')
    for k in VS:
        b, se = ols(y - x.pin_s_mkt.values, (x[f's_{k}'] - x.pin_s_mkt).values)
        ps = x.groupby('season').apply(lambda v: np.sqrt(np.mean((v.gd - v[f's_{k}']) ** 2)))
        acc[(w, k)] = ps
        print(f'      {k:15s} RMSE {np.sqrt(np.mean((y - x[f"s_{k}"]) ** 2)):.4f} · β {b[1]:+.2f} (t {b[1] / se[1]:+.1f}) · ανα σεζον ' + ' '.join(f'{v:.3f}' for v in ps.values))
for w in ('6-14', '15+'):
    d_ = acc[(w, 'ΧΩΡΙΣ ΣΥΜΠΙΕΣΗ')] - acc[(w, 'LIVE')]
    print(f'   [{w}] χωρις συμπιεση καλυτερο RMSE σε {int((d_ < 0).sum())}/4 σεζον (Δ μεσος {d_.mean():+.4f})')
print('\n(3) PICKS — ιδιοι live κανονες (dogs 6-14 χωρις αγκυρα· 15+ dogs με αγκυρα κοντων δεν εφαρμοζεται εδω → συγκριση ΙΔΙΑΣ μεταχειρισης)')
rows = []
for mid, r in M[M.md >= 5].iterrows():
    for bk, (L, oh, oa) in (('Pinnacle', (r.pin_L, r.pin_ah, r.pin_aa)), ('Crown', (r.cr_L, r.cr_oh, r.cr_oa)), ('Bet365', (r.b3_L, r.b3_oh, r.b3_oa))):
        if not (L == L and oh == oh): continue
        for k in VS:
            xh_, xa_ = r[f'xh_{k}'], r[f'xa_{k}']
            for b in picks.evaluate_bet(xh_, xa_, L, oh, oa):
                rows.append(dict(v=k, w=r.w, season=r.season, book=bk, role='dog', dep='βαθια' if abs(b['hcap']) >= 1.5 else ('μεση' if abs(b['hcap']) >= 1 else 'κοντη'),
                                 pnl=picks.settle(r.gd, b['side'], b['hcap'], b['odds'])))
            if r.md <= 13 and abs(L) in (0.5, 0.75):
                side = 1 if L < 0 else -1; o = oh if side == 1 else oa
                if 1.70 <= o <= 2.10 and picks.fav_edge_q(xh_, xa_, side, -abs(L), o) >= 0:
                    rows.append(dict(v=k, w=r.w, season=r.season, book=bk, role='fav', dep='κοντη', pnl=picks.settle(r.gd, side, -abs(L), o)))
B = pd.DataFrame(rows)
def fm(d):
    if len(d) < 6: return f'n{len(d) / 3:5.0f}' + ' ' * 30
    ps = d.groupby('season').pnl.mean()
    return f'n{len(d) / d.book.nunique():5.0f} {100 * d.pnl.mean():+6.1f}% {d.pnl.sum() / d.book.nunique():+6.1f}u σεζ {int((ps > 0).sum())}/{ps.size}'
for w in ('6-14', '15+'):
    for role in ('dog', 'fav'):
        if w == '15+' and role == 'fav': continue
        print(f'   [{w} {role}]')
        for k in VS:
            x = B[(B.w == w) & (B.role == role) & (B.v == k)]
            print(f'      {k:15s} ολα {fm(x)} · ' + ' · '.join(f'{dp} {fm(x[x.dep == dp])}' for dp in ('κοντη', 'μεση', 'βαθια') if (x.dep == dp).any()))
x = B[B.w == '6-14']
L_ = x[x.v == 'LIVE']; N_ = x[x.v == 'ΧΩΡΙΣ ΣΥΜΠΙΕΣΗ']
psl = L_.groupby('season').pnl.mean(); psn = N_.groupby('season').pnl.mean()
pbl = L_.groupby('book').pnl.mean(); pbn = N_.groupby('book').pnl.mean()
cA = int((acc[('6-14', 'ΧΩΡΙΣ ΣΥΜΠΙΕΣΗ')] < acc[('6-14', 'LIVE')]).sum()) >= 3
cB = int((psn > psl).sum()) >= 3 and N_.pnl.mean() > 0 and int((pbn > pbl).sum()) >= 2
print(f'\nΚΡΙΣΗ «χωρις συμπιεση στις 6-14» (ολα τα picks 6-14): LIVE {fm(L_)} · ΧΩΡΙΣ {fm(N_)} → (Α) {"✓" if cA else "✗"} (Β) {"✓" if cB else "✗"} → {"ΠΕΡΝΑ" if cA and cB else "ΔΕΝ ΠΕΡΝΑ"}')
