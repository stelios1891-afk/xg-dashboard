# -*- coding: utf-8 -*-
"""xi_age_totals_eval.py — 21/10/2026 (Στελιος: «τρεξτο (αξια με διορθωση ηλικιας) και μαζι πιθανους τροπους για τα συνολα»).
ΜΕΡΟΣ Α — ΗΛΙΚΙΑ: η αξια ευνοει τους νεους (ο Πεπε €6m στα 31, ο Σαλιμπα €9m στα 22). Αν για την ιδια αξια μια ΝΕΟΤΕΡΗ ενδεκαδα αποδιδει λιγοτερο,
  η αναλυση πρεπει να δωσει θετικο βαρος στη Δ ηλικιας. Εκδοχες (LOSO, ιδιοι στοχοι με τον αγωνα μετρων):
  αναφορα = Δαξια + Δεμπιστοσυνη(10) · +Δηλικια · +Δηλικια + Δ(ηλικια−27)² (κορυφη ηλικιας)
ΜΕΡΟΣ Β — ΣΥΝΟΛΑ: λαθος μοντελου στο ΣΥΝΟΛΟ xG και στο ΣΥΝΟΛΟ γκολ ~ αλλαγες ενδεκαδας (αξια + εμπιστοσυνη):
  Σ1 «πιο αδυναμες ομαδες συνολικα»: (Δ γηπ + Δ φιλ)  · Σ2 ΑΝΑ ΘΕΣΗ: επιθεση/μεσοι (Δ γηπ + Δ φιλ) και αμυνα/τερμ. (Δ γηπ + Δ φιλ) χωριστα
  Σ3 ΑΝΑ ΠΛΕΥΡΑ: γκολ που βαζει καθε ομαδα ~ δικη της επιθεση + αμυνα αντιπαλου (εκτιμηση στις πλευρες, συνολο = αθροισμα)
  Σ4 rotation και των δυο (αθροισμα Δεμπιστοσυνης μονο)
ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ): μια εκδοχη κρατιεται μονο αν η εκτος δειγματος βελτιωση ειναι θετικη σε ≥3/4 σεζον ΚΑΙ στο xG ΚΑΙ στα γκολ,
  και το διαστημα 90% (bootstrap ανα αγωνιστικη εβδομαδα) της βελτιωσης ειναι πανω απο 0 σε τουλαχιστον ενα απο τα δυο."""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NL = chr(10)
V = pd.read_csv('xi_variants_rows.csv', dtype={'mid': str})
E = pd.read_csv('xi_measure_eval_rows.csv', dtype={'mid': str, 'season': str},
                usecols=['mid', 'season', 'league', 'date_x', 'r_xgd', 'r_gd', 'r_xh', 'r_xa', 'axh', 'axa', 'xg_h', 'xg_a', 'gd'])
D = E.merge(V.drop(columns=['date', 'lg', 'sea'], errors='ignore'), on='mid', how='inner')
gl = pd.read_csv('core7_mech_preds_bl_0.6.csv', dtype={'mid': str}, usecols=['mid'])
import json, glob, re
TG = {}
for f in glob.glob('data_*_*.json'):
    if not re.search(r'data_(EPL|LaLiga|SerieA|Bundesliga|Ligue1|Eredivisie|PrimeiraLiga)_\d{4}\.json$', f): continue
    for k, v in json.load(open(f, encoding='utf-8')).items():
        try: TG[str(k)] = (int(v['hs']), int(v['as']))
        except Exception: pass
D['hg'] = D.mid.map(lambda k: TG.get(k, (np.nan, np.nan))[0]); D['ag'] = D.mid.map(lambda k: TG.get(k, (np.nan, np.nan))[1])
D['r_tx'] = (D.axh + D.axa) - (D.xg_h + D.xg_a); D['r_tg'] = (D.hg + D.ag) - (D.xg_h + D.xg_a)
D['r_gh'] = D.hg - D.xg_h; D['r_ga'] = D.ag - D.xg_a
SE = sorted(D.season.unique())
D['blk'] = D.league + '_' + pd.to_datetime(D.date_x).dt.strftime('%G%V')
for c in ('Vlog', 'Tm10', 'Age', 'Age2'): D[f'x_{c}'] = D[f'{c}_h'] - D[f'{c}_a']
def gains(cols, y, data=D):
    g = pd.Series(np.nan, index=data.index)
    for s in SE:
        tr = data[(data.season != s) & data[y].notna()]; te = data[(data.season == s) & data[y].notna()]
        X = np.column_stack([np.ones(len(tr))] + [tr[c].fillna(0).values for c in cols]); b = np.linalg.lstsq(X, tr[y].values, rcond=None)[0]
        p = np.column_stack([np.ones(len(te))] + [te[c].fillna(0).values for c in cols]) @ b
        g[te.index] = (te[y].values - tr[y].mean()) ** 2 - (te[y].values - p) ** 2
    return g
rng = np.random.default_rng(7); UB = D.blk.unique(); IDX = {b: np.where(D.blk.values == b)[0] for b in UB}
def boot(series, n=1500):
    s = series.values; out = []
    for _ in range(n):
        pick = rng.choice(UB, len(UB)); ii = np.concatenate([IDX[b] for b in pick]); out.append(np.nanmean(s[ii]))
    return 1000 * np.nanmean(s), 1000 * np.percentile(out, 5), 1000 * np.percentile(out, 95)
def coefs(cols, y):
    ok = D[y].notna(); X = np.column_stack([np.ones(ok.sum())] + [D.loc[ok, c].fillna(0).values for c in cols])
    return np.linalg.lstsq(X, D.loc[ok, y].values, rcond=None)[0][1:]
def show(nm, cols, ys, ref=None):
    parts = []
    for y, lab in ys:
        g = gains(cols, y); per = [1000 * g[D.season == s].mean() for s in SE]; m, lo, hi = boot(g)
        txt = f'{lab} {m:+6.2f} [{lo:+.1f}, {hi:+.1f}] ' + ' '.join(f'{v:+.1f}' for v in per) + f' {sum(v > 0 for v in per)}/4'
        if ref is not None:
            gr = gains(ref, y); dm, dlo, dhi = boot(g - gr); txt += f' · vs αναφορα {dm:+.2f} [{dlo:+.1f}, {dhi:+.1f}]'
        parts.append(txt)
    cf = coefs(cols, ys[0][0])
    print(f'   {nm:40s} │ ' + ' │ '.join(parts) + ' │ βαρη ' + ' '.join(f'{c.replace("x_", "").replace("s_", "")}:{v:+.3f}' for c, v in zip(cols, cf)))
print(f'ματς {len(D)}')
print(f'{NL}{"=" * 140}{NL}Α. ΗΛΙΚΙΑ — διαφορα xG / διαφορα γκολ (βελτιωση ×1000 εκτος δειγματος, [90%], ανα σεζον)')
REF = ['x_Vlog', 'x_Tm10']; YD = [('r_xgd', 'xG'), ('r_gd', 'γκολ')]
show('αναφορα: αξια + εμπιστοσυνη', REF, YD)
show('+ ηλικια', REF + ['x_Age'], YD, REF)
show('+ ηλικια + (ηλικια−27)²', REF + ['x_Age', 'x_Age2'], YD, REF)
show('μονο ηλικια', ['x_Age'], YD)
# ---------------- ΣΥΝΟΛΑ ----------------
for c in ('Vlog', 'Tm10'):
    D[f's_{c}'] = D[f'{c}_h'] + D[f'{c}_a']
    for g in ('gk', 'df', 'md', 'at'): D[f's_{c}{g}'] = D[f'{c}{g}_h'].fillna(0) + D[f'{c}{g}_a'].fillna(0)
    D[f's_{c}O'] = D[f's_{c}md'] + D[f's_{c}at']; D[f's_{c}D'] = D[f's_{c}gk'] + D[f's_{c}df']
print(f'{NL}{"=" * 140}{NL}Β. ΣΥΝΟΛΑ — λαθος μοντελου στο ΣΥΝΟΛΟ xG / ΣΥΝΟΛΟ γκολ')
YT = [('r_tx', 'xG'), ('r_tg', 'γκολ')]
show('Σ1 πιο αδυναμες συνολικα (αξια+εμπιστ.)', ['s_Vlog', 's_Tm10'], YT)
show('Σ2 ανα θεση: επιθεση/μεσοι vs αμυνα/τερμ.', ['s_VlogO', 's_VlogD', 's_Tm10O', 's_Tm10D'], YT)
show('Σ4 rotation και των δυο (μονο εμπιστ.)', ['s_Tm10'], YT)
# Σ3 ανα πλευρα: στοιβαζουμε (γκολ γηπ ~ επιθ. γηπ + αμυνα φιλ) και (γκολ φιλ ~ επιθ. φιλ + αμυνα γηπ)
def side_stack():
    rows = []
    for side, opp, ry, rg in (('h', 'a', 'r_xh', 'r_gh'), ('a', 'h', 'r_xa', 'r_ga')):
        q = pd.DataFrame({'mid': D.mid, 'season': D.season, 'blk': D.blk, 'ry': D[ry], 'rg': D[rg],
                          'oV': D[f'Vlogmd_{side}'].fillna(0) + D[f'Vlogat_{side}'].fillna(0), 'oT': D[f'Tm10md_{side}'].fillna(0) + D[f'Tm10at_{side}'].fillna(0),
                          'dV': D[f'Vloggk_{opp}'].fillna(0) + D[f'Vlogdf_{opp}'].fillna(0), 'dT': D[f'Tm10gk_{opp}'].fillna(0) + D[f'Tm10df_{opp}'].fillna(0)})
        rows.append(q)
    return pd.concat(rows, ignore_index=True)
S = side_stack(); cols = ['oV', 'oT', 'dV', 'dT']
out = {}
for y, yt in (('ry', 'r_tx'), ('rg', 'r_tg')):
    pred = pd.Series(np.nan, index=S.index)
    for s in SE:
        tr = S[(S.season != s) & S[y].notna()]; te = S[(S.season == s)]
        X = np.column_stack([np.ones(len(tr))] + [tr[c].values for c in cols]); b = np.linalg.lstsq(X, tr[y].values, rcond=None)[0]
        pred[te.index] = np.column_stack([np.zeros(len(te))] + [te[c].values for c in cols]) @ b
    tot = pred.groupby(S.mid).sum()
    base = {s: D[(D.season != s)][yt].mean() for s in SE}
    yv = D[yt].values; pv = D.mid.map(tot).values; bv = D.season.map(base).values
    g = pd.Series((yv - bv) ** 2 - (yv - bv - pv) ** 2, index=D.index)
    per = [1000 * g[D.season == s].mean() for s in SE]; m, lo, hi = boot(g); out[yt] = (m, lo, hi, per)
    ok = S[y].notna(); X = np.column_stack([np.ones(ok.sum())] + [S.loc[ok, c].values for c in cols]); bb = np.linalg.lstsq(X, S.loc[ok, y].values, rcond=None)[0]
    if y == 'ry': B3 = bb[1:]
print(f'   {"Σ3 ανα πλευρα (επιθ. ομαδας + αμυνα αντιπ.)":40s} │ ' + ' │ '.join(f'{lab} {out[yt][0]:+6.2f} [{out[yt][1]:+.1f}, {out[yt][2]:+.1f}] ' + ' '.join(f'{v:+.1f}' for v in out[yt][3]) + f' {sum(v > 0 for v in out[yt][3])}/4' for yt, lab in (('r_tx', 'xG'), ('r_tg', 'γκολ')))
      + ' │ βαρη (xG ανα πλευρα) ' + ' '.join(f'{c}:{v:+.3f}' for c, v in zip(cols, B3)) + '  (αναμενεται επιθεση +, αμυνα αντιπαλου −)')
print(f'{NL}Γ. ΜΕΓΕΘΟΣ — ακραια 5% στο Σ1 (και οι δυο πολυ αδυναμες / πολυ δυνατες): μεσο λαθος μοντελου στο συνολο')
x = D.s_Vlog * 0 + D.s_Tm10
for lab, msk in (('και οι δυο ΠΟΛΥ αδυναμες (5%)', x <= x.quantile(.05)), ('ουδετερο', x.abs() <= x.abs().quantile(.5)), ('και οι δυο πληρεις/δυνατες (5%)', x >= x.quantile(.95))):
    q = D[msk]
    print(f'   {lab:34s} n {len(q):4d} · συνολο xG − μοντελο {q.r_tx.mean():+.2f} · συνολο γκολ − μοντελο {q.r_tg.mean():+.2f}')
