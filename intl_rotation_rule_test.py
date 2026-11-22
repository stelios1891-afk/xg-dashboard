"""
intl_rotation_rule_test.py — ΤΕΣΤ 28/9/2026 (Στελιος: «γιατι εμεις την ριξαμε λιγο και η αγορα πολυ, οταν ειδαμε οτι σε τετοιο ροτεισον η αγορα εχει δικιο;»).
ΜΟΝΟ ΑΚΡΑΙΕΣ ΠΕΡΙΠΤΩΣΕΙΣ: ομαδα με ΣΤΑΡ (top-3 αξιας της συνηθισμενης 11αδας, μονο επισημα) στον ΠΑΓΚΟ ή 5+ βασικους στον ΠΑΓΚΟ.
ΕΚΔΟΧΕΣ (αξια στις −60′):  ΣΗΜΕΡΑ = top-11 των 23 για ολους ·
   ΚΑΝΟΝΑΣ w=0 = για την ομαδα με την ακραια αλλαγη μετρα η ΒΑΣΙΚΗ 11αδα (αλλες ομαδες: οι 23) · ΚΑΝΟΝΑΣ w=0.5 = μισο βαρος στον παγκο.
Μοντελο: Elo H3 + ln(αξια_h/αξια_a), ordered logit, LOSO ανα σεζον (fit σε ΟΛΑ τα ματς).
ΠΡΟ-ΔΗΛΩΣΗ: ο κανονας ΠΕΡΝΑ αν (1) RPS στα ακραια ματς < ΣΗΜΕΡΑ, (2) καλυτερος σε ≥4/6 σεζον εκει, (3) RPS σε ΟΛΑ δεν χειροτερευει.
Πληροφοριακα: αποσταση απο closing (RMSE / μεροληψια για την ομαδα με την αλλαγη) και μεροληψια vs πραγματικο γκολ.
"""
import sys, json
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
_src = open('intl_rating.py', encoding='utf-8').read(); _ns = {'np': np}
exec(_src[_src.index('def sig(x):'):_src.index("EVAL_SEASONS = ")], _ns)
sig, nelder_mead, rps, logloss = _ns['sig'], _ns['nelder_mead'], _ns['rps'], _ns['logloss']
_v = open('intl_value.py', encoding='utf-8').read(); _n2 = {'np': np, 'sig': sig, 'nelder_mead': nelder_mead}
exec(_v[_v.index('def fit_ol_multi'):_v.index('FEATS = ')], _n2)
fit_ol_multi, probs_multi = _n2['fit_ol_multi'], _n2['probs_multi']

X = pd.read_csv('intl_xi60_rows.csv', dtype={'mid': str, 'season': str})
Bm = pd.read_csv('intl_lineup_bigmoves_rows.csv', dtype={'mid': str})[['mid', 'key_bench_h', 'key_bench_a', 'bench_h', 'bench_a']]
D = X.merge(Bm, on='mid', how='left')
for sd in ('h', 'a'):
    D[f'flag_{sd}'] = ((D[f'key_bench_{sd}'] == 1) | (D[f'bench_{sd}'] >= 5)).fillna(False)
D['flag'] = D.flag_h | D.flag_a
def Lrule(w):
    vh = np.where(D.flag_h, D.xi_h + w * (D.v23_h - D.xi_h), D.v23_h)
    va = np.where(D.flag_a, D.xi_a + w * (D.v23_a - D.xi_a), D.v23_a)
    return np.log(vh / va)
D['L_today'] = np.log(D.v23_h / D.v23_a); D['L_r0'] = Lrule(0.0); D['L_r5'] = Lrule(0.5)
SEAS = ['2021', '2122', '2223', '2324', '2425', '2526']
D = D[D.season.isin(SEAS)].reset_index(drop=True)
F = D.flag.values
print(f'ματς: {len(D)} · ΑΚΡΑΙΑ (σταρ στον παγκο ή 5+ παγκος σε μια ομαδα): {F.sum()} · με closing {int(D[F].s_mkt.notna().sum())}')
print(f'  στα ακραια: αξια 11αδας / 23 για την ομαδα με την αλλαγη = {np.nanmean(np.where(D.flag_h, D.xi_h / D.v23_h, D.xi_a / D.v23_a)[F]):.2f} (μεσο)')

VAR = {'ΣΗΜΕΡΑ (23)': 'L_today', 'ΚΑΝΟΝΑΣ w=0.5': 'L_r5', 'ΚΑΝΟΝΑΣ w=0 (11αδα)': 'L_r0'}
P = {}
D['y'] = np.where(D.gd > 0, 2, np.where(D.gd == 0, 1, 0))
res = {}
for name, L in VAR.items():
    Pm = np.zeros((len(D), 3))
    for s_ in SEAS:
        tr = (D.season != s_).values; te = (D.season == s_).values
        b, c1, c2 = fit_ol_multi(D.loc[tr, ['diff', L]].values.astype(float), D.y.values[tr])
        Pm[te] = probs_multi(D.loc[te, ['diff', L]].values.astype(float), b, c1, c2)
    P[name] = Pm
    res[name] = dict(ALL=rps(Pm, D.y.values), ΑΚΡΑΙΑ=rps(Pm[F], D.y.values[F]),
                     **{s_: rps(Pm[F & (D.season == s_).values], D.y.values[F & (D.season == s_).values]) for s_ in SEAS})
T = pd.DataFrame(res).T
print('\nRPS (χαμηλοτερο = καλυτερο)')
print(T[['ALL', 'ΑΚΡΑΙΑ'] + SEAS].round(5).to_string())
b0 = res['ΣΗΜΕΡΑ (23)']
for name in list(VAR)[1:]:
    better = sum(res[name][s_] < b0[s_] for s_ in SEAS)
    ok = res[name]['ΑΚΡΑΙΑ'] < b0['ΑΚΡΑΙΑ'] and better >= 4 and res[name]['ALL'] <= b0['ALL'] + 1e-6
    print(f"  {name}: ακραια ΔRPS {res[name]['ΑΚΡΑΙΑ'] - b0['ΑΚΡΑΙΑ']:+.5f} ({better}/6 σεζον) · ολα ΔRPS {res[name]['ALL'] - b0['ALL']:+.5f} → {'ΠΕΡΝΑ' if ok else 'δεν περνα'}")

# υπεροχη σε γκολ (OLS LOSO) → μεροληψια για την ομαδα με την αλλαγη: vs αποτελεσμα και vs closing
print('\nΜΕΡΟΛΗΨΙΑ για την ομαδα με την ακραια αλλαγη (+ = την υπερεκτιμουμε), στα ακραια ματς όπου ΜΟΝΟ μια ομαδα εχει σημαια:')
one = (D.flag_h ^ D.flag_a).values
sgn = np.where(D.flag_h, 1, -1)
for name, L in VAR.items():
    sm = np.zeros(len(D))
    for s_ in SEAS:
        tr = (D.season != s_).values; te = (D.season == s_).values
        b = np.linalg.lstsq(np.column_stack([D['diff'][tr], D[L][tr]]), D.gd.values[tr], rcond=None)[0]
        sm[te] = D['diff'].values[te] * b[0] + D[L].values[te] * b[1]
    m = one; mk = one & D.s_mkt.notna().values
    vr = sgn[m] * (sm[m] - D.gd.values[m]); vm = sgn[mk] * (sm[mk] - D.s_mkt.values[mk])
    print(f"  {name:22s} vs ΑΠΟΤΕΛΕΣΜΑ {vr.mean():+.3f} γκολ (±{vr.std()/np.sqrt(len(vr)):.3f}, n={m.sum()}) · vs CLOSING {vm.mean():+.3f} (±{vm.std()/np.sqrt(len(vm)):.3f}, n={mk.sum()}) · "
          f"RMSE vs closing {np.sqrt(np.mean((sm[mk] - D.s_mkt.values[mk])**2)):.3f}")
mk = one & D.s_mkt.notna().values
vm = sgn[mk] * (D.s_mkt.values[mk] - D.gd.values[mk])
print(f"  {'ΑΓΟΡΑ (closing)':22s} vs ΑΠΟΤΕΛΕΣΜΑ {vm.mean():+.3f} γκολ (±{vm.std()/np.sqrt(len(vm)):.3f}, n={mk.sum()})")
