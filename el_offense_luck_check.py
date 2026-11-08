# -*- coding: utf-8 -*-
"""el_offense_luck_check.py (απο el_luck_split_check.py) — ΕΥΡΩΛΙΓΚΑ: επιθεση {.25,.5,.75} × αμυνα {.25,0} vs LIVE (.25/.25) (25/10/2026, Στελιος «ναι»).
ΠΑΛΙΑ ΠΕΡΙΓΡΑΦΗ: el_luck_split_check.py — ΕΠΙΒΕΒΑΙΩΣΗ ΣΤΗΝ ΕΥΡΩΛΙΓΚΑ (τροπος 8 του t86): «τυχη» χωριστα για επιθεση και αμυνα στα συνολα (25/10/2026).
NBA t85: 3P%/FT% αντιπαλων ≈ τυχη → λιγοτερη τυχη στην ΑΜΥΝΑ. Εδω ιδια ιδεα στη μηχανη συνολων Ευρωλιγκας (ENG_TOTAL του live:
τυχη .25, χωρις φθορα, περσι 70%, επιπεδο λιγκας 50, εδρα 6) — ΧΩΡΙΣ ξαναρυθμιση: συγκρινουμε (επ .25 / αμ .25) = LIVE με
(επ .25 / αμ 0) και, για συγκριση με το NBA, (επ .5 / αμ .5) vs (επ .5 / αμ .25).
Προελεγχος: επαναληψη 3P%/FT% επιθεσης vs αντιπαλων (1ο → 2ο μισο σεζον, el_box).
ΜΕΤΡΑ (ιδια με el_loso_totals): b = κλιση (πραγματικο − closing) πανω στο (μοντελο − closing) ανα σεζον (E2020-25) · RMSE · ζευγαρωτη.
ΕΠΙΒΕΒΑΙΩΝΕΤΑΙ αν b καλυτερο σε ≥4/6 σεζον ΚΑΙ στο συνολο ΚΑΙ ζευγαρωτη διαφορα σφαλματος υπερ (t > 0).
Εξοδος: el_luck_split_check_out.txt"""
import sys, io, json, math, contextlib, collections
import numpy as np
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open('el_loso_totals.py', encoding='utf-8').read().split('GRID = list(itertools.product')[0]
ns = {}
with contextlib.redirect_stdout(_B()): exec(src, ns)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
D, SEAS, IDX, MT, TOT, SE, SS = ns['D'], ns['SEAS'], ns['IDX'], ns['MT'], ns['TOT'], ns['SE'], ns['SS']
luck_pts, fit_eff_mu, fit_pace = ns['luck_pts'], ns['fit_eff_mu'], ns['fit_pace']
# ---- προελεγχος επαναληψης ----
B = json.load(open('el_box.json', encoding='utf-8'))
by = collections.defaultdict(list)
for b in B.values():
    if not b.get('h') or b['season'] < 'E2018': continue
    for me, op, code in (('h', 'a', b['hcode']), ('a', 'h', b['acode'])): by[(b['season'], code)].append((b['utc'], b[me], b[op]))
A = []
for k, L in by.items():
    L.sort(key=lambda x: x[0]); h = len(L) // 2
    if h < 8: continue
    f = lambda X, s, m, a: sum(x[s][m] for x in X) / max(1, sum(x[s][a] for x in X))
    A.append([f(L[:h], 1, 'fgm3', 'fga3'), f(L[h:], 1, 'fgm3', 'fga3'), f(L[:h], 2, 'fgm3', 'fga3'), f(L[h:], 2, 'fgm3', 'fga3'),
              f(L[:h], 1, 'ftm', 'fta'), f(L[h:], 1, 'ftm', 'fta'), f(L[:h], 2, 'ftm', 'fta'), f(L[h:], 2, 'ftm', 'fta')])
A = np.array(A); c = lambda i, j: np.corrcoef(A[:, i], A[:, j])[0, 1]
P(f'ΠΡΟΕΛΕΓΧΟΣ ({len(A)} ομαδα-σεζον, 1ο → 2ο μισο): 3P% επιθεσης r {c(0, 1):.2f} · 3P% ΑΝΤΙΠΑΛΩΝ r {c(2, 3):.2f} · FT% επιθεσης r {c(4, 5):.2f} · FT% ΑΝΤΙΠΑΛΩΝ r {c(6, 7):.2f}')
_LP = {}
def run_split(w_off, w_def, HL=9999, carry=0.7, mu_w=50.0, lam=8, h=6.0):
    for w in (w_off, w_def):
        if w not in _LP: _LP[w] = luck_pts(w)
    EHo, EAo = _LP[w_off]; EHd, EAd = _LP[w_def]
    tot = np.full(len(D), np.nan); prO, prD, prP = {}, {}, {}
    m0o = float((EHo.mean() + EAo.mean()) / 2); m0d = float((EHd.mean() + EAd.mean()) / 2); pm0 = float(D.pace.mean())
    dnum = np.array([(d - D.date.iloc[0]).days for d in D.date])
    for s in SEAS:
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        g = lambda pr, j: np.array([carry * pr.get(t, (0, 0))[j] for t in teams])
        o0, d0o, o0d, d0 = g(prO, 0), g(prO, 1), g(prD, 0), g(prD, 1); p0 = np.array([carry * prP.get(t, 0.0) for t in teams])
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        neu = D.ff.values[sidx] | D.relocated.values[sidx]; hb = np.where(neu, 0.0, h / 2); dn = dnum[sidx]; pc = D.pace.values[sidx]
        eho, eao, ehd, ead = EHo[sidx], EAo[sidx], EHd[sidx], EAd[sidx]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                w = 0.5 ** ((d - dn[past]) / HL)
                mA, O, _ = fit_eff_mu(hi[past], ai[past], eho[past], eao[past], hb[past], w, n, o0, d0o, lam, m0o, mu_w)
                mB, _, Dd = fit_eff_mu(hi[past], ai[past], ehd[past], ead[past], hb[past], w, n, o0d, d0, lam, m0d, mu_w)
                pm, Pc = fit_pace(hi[past], ai[past], pc[past], w, n, p0, lam, pm0)
            else:
                mA, mB, O, Dd, pm, Pc = m0o, m0d, o0, d0, pm0, p0
            mu = (mA + mB) / 2; hh, aa, hbb = hi[cur], ai[cur], hb[cur]
            tot[sidx[cur]] = (pm + Pc[hh] + Pc[aa]) * (2 * mu + O[hh] + Dd[aa] + O[aa] + Dd[hh]) / 100
        w = 0.5 ** ((dn.max() - dn) / HL)
        mA, O, Do = fit_eff_mu(hi, ai, eho, eao, hb, w, n, o0, d0o, lam, m0o, mu_w)
        mB, Od, Dd = fit_eff_mu(hi, ai, ehd, ead, hb, w, n, o0d, d0, lam, m0d, mu_w)
        pm, Pc = fit_pace(hi, ai, pc, w, n, p0, lam, pm0)
        prO = {t: (O[i], Do[i]) for t, i in ix.items()}; prD = {t: (Od[i], Dd[i]) for t, i in ix.items()}; prP = {t: Pc[i] for t, i in ix.items()}
        m0o, m0d, pm0 = mA, mB, pm
    return tot[IDX]

K = [(0.25, 0.25), (0.5, 0.25), (0.75, 0.25), (0.25, 0.0), (0.5, 0.0), (0.75, 0.0)]
R = {k: run_split(*k) for k in K}
chk = ns['run_t'](0.25, 9999, 0.7, 50.0, 0.0)
P(f'ελεγχος: (.25/.25) = μηχανη συνολων live (μεγ. διαφορα {np.nanmax(np.abs(R[(0.25, 0.25)] - chk)):.2e})')
m = np.isin(SE, SS); LIVE = (0.25, 0.25)
b_of = lambda t, mk: np.polyfit((t - MT)[mk], (TOT - MT)[mk], 1)[0]
rm = lambda t, mk: float(np.sqrt(np.mean((TOT - t)[mk] ** 2)))
dts = D.date.values[IDX].astype('datetime64[D]'); wk = (dts - dts.min()).astype(int) // 7
rng = np.random.default_rng(5)
P('\n=== ΑΝΑ ΕΚΔΟΧΗ: b (ποσο απο τη διαφωνια μας με το κλεισιμο επαληθευεται) · RMSE συνολου ===')
for k in K:
    P(f"  επ {k[0]}/αμ {k[1]}{' (LIVE)' if k == LIVE else ''}: b {b_of(R[k], m):+.3f} (" + ' '.join(f'{s[1:]}:{b_of(R[k], SE == s):+.2f}' for s in SS)
      + f') · RMSE {rm(R[k], m):.3f}')
P('\n=== vs LIVE: σεζον με καλυτερο b · ζευγαρωτη t · bootstrap (εβδομαδες) P(πιο κοντα) ===')
for k in K[1:]:
    wins = sum(b_of(R[k], SE == s) > b_of(R[LIVE], SE == s) for s in SS)
    d = ((TOT - R[LIVE]) ** 2 - (TOT - R[k]) ** 2)[m]; w_ = wk[m]
    import pandas as pd
    dd = pd.Series(d).groupby(w_).sum(); t = dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd)))
    v = dd.values; bs = np.array([v[rng.integers(0, len(v), len(v))].sum() for _ in range(3000)])
    P(f'  επ {k[0]}/αμ {k[1]}: b καλυτερο {wins}/{len(SS)} · ζευγαρωτη t {t:+.2f} · P(πιο κοντα) {100 * (bs > 0).mean():.0f}%')
P('\n=== WALK-FORWARD: επιλογη με b απο τις προηγουμενες σεζον ===')
hx, hy, lx, ly = [], [], [], []
for i, s in enumerate(SS[2:], 2):
    prev = np.isin(SE, SS[:i]); cur = SE == s; b = max(K, key=lambda k: b_of(R[k], prev))
    hx.append((R[b] - MT)[cur]); hy.append((TOT - MT)[cur]); lx.append((R[LIVE] - MT)[cur]); ly.append((TOT - MT)[cur])
    P(f'  {s}: διαλεγει επ {b[0]}/αμ {b[1]} · b {b_of(R[b], cur):+.2f} vs live {b_of(R[LIVE], cur):+.2f}')
P(f'  ΣΥΝΟΛΟ: b {np.polyfit(np.concatenate(hx), np.concatenate(hy), 1)[0]:+.3f} vs live {np.polyfit(np.concatenate(lx), np.concatenate(ly), 1)[0]:+.3f}')
open('el_offense_luck_check_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
