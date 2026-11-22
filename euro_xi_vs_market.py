"""euro_xi_vs_market.py — 14/10/2026. Συμπληρωμα euro_transfer_mechanism: η αξια ενδεκαδας (ln γηπ/φιλ) εξηγει κατι που η ΑΓΟΡΑ (κλεισιμο) δεν εχει;
και το σεναριο «κορυφαια μη-top5 vs μετρια top-5» — τι λεει η αγορα; Κατηγορια Α, διαφορα γκολ γηπεδουχου (γραμμικα): (xG − αγορα) = c + k·ln(αξια γηπ/φιλ).
"""
import sys, os, pickle
_XOUT = sys.stdout
exec(open('uel_home_away_fav_diag.py', encoding='utf-8').read().split("print('1) ΑΝΑΛΥΣΗ ΛΑΘΟΥΣ")[0])
sys.stdout = _XOUT; sys.stdout.reconfigure(encoding='utf-8')
XA = pickle.load(open('euro_xi_abs.pkl', 'rb'))
C['mid'] = [str(MIDS[i]) for i in C.i]
C['V'] = [np.log(XA[m][0] / XA[m][1]) if m in XA else np.nan for m in C.mid]
X = C.dropna(subset=['V'])
def ols(x, y):
    Xm = np.c_[np.ones(len(x)), x]; b, *_ = np.linalg.lstsq(Xm, y, rcond=None); e = y - Xm @ b
    se = np.sqrt(np.diag(np.linalg.inv(Xm.T @ Xm) * (e @ e) / (len(x) - Xm.shape[1]))); return b, se
print('(xG διαφορα − ΑΓΟΡΑ κλεισιμο) = c + k·ln(αξια ενδεκαδας γηπ/φιλ) · k>0 = η αξια λεει κατι που η αγορα ΔΕΝ εχει · και ιδιο με (xG − ΜΟΝΤΕΛΟ)')
for cm, lab in ((('EuropaLeague',), 'EUROPA'), (('ConferenceLeague',), 'CONFERENCE'), (('ChampionsLeague',), 'CHAMPIONS'), (('EuropaLeague', 'ConferenceLeague'), 'EUROPA+CONF')):
    x = X[X.comp.isin(cm)]
    b1, s1 = ols(x.V.values, (x.xgd - x.kgd).values); b2, s2 = ols(x.V.values, (x.xgd - x.mgd).values); b3, s3 = ols(x.V.values, (x.gd - x.kgd).values)
    print(f'   {lab:12s} n{len(x):4d} · vs ΑΓΟΡΑ (xG) k {b1[1]:+.3f}±{s1[1]:.3f} · vs ΑΓΟΡΑ (γκολ) k {b3[1]:+.3f}±{s3[1]:.3f} · vs ΜΟΝΤΕΛΟ (xG) k {b2[1]:+.3f}±{s2[1]:.3f}')
SCN = pickle.load(open('euro_scenario_mids.pkl', 'rb')); Ci = C.set_index('mid')
print(NL + 'ΣΕΝΑΡΙΟ «κορυφαια μη-top5 vs μετρια top-5» (απο τη σκοπια της μη-top5): ΑΓΟΡΑ vs ΜΟΝΤΕΛΟ vs xG')
for cm, lab in ((('EuropaLeague', 'ConferenceLeague'), 'EUROPA + CONFERENCE'), (('ChampionsLeague',), 'CHAMPIONS')):
    rows = [(sg * Ci.loc[m, 'kgd'], sg * Ci.loc[m, 'mgd'], sg * Ci.loc[m, 'xgd'], sg * Ci.loc[m, 'gd']) for m, sg in SCN if m in Ci.index and Ci.loc[m, 'comp'] in cm]
    R_ = np.array(rows)
    if len(R_) < 5: print(f'   {lab}: λιγα'); continue
    print(f'   {lab}: n{len(R_)} · ΑΓΟΡΑ {R_[:, 0].mean():+.2f} · ΜΟΝΤΕΛΟ {R_[:, 1].mean():+.2f} · xG {R_[:, 2].mean():+.2f} · γκολ {R_[:, 3].mean():+.2f}'
          f' → αγορα − xG {(R_[:, 0] - R_[:, 2]).mean():+.2f} ±{(R_[:, 0] - R_[:, 2]).std() / np.sqrt(len(R_)):.2f}')
