# -*- coding: utf-8 -*-
"""el_loso_totals.py — LOSO μονο για τα ΣΥΝΟΛΑ ΠΟΝΤΩΝ Ευρωλιγκας (24/9/2026, αιτημα Στελιου).

Το κοινο LOSO (el_loso_tests) εδωσε για τα συνολα χειροτερη επιλογη απο το v1 (.235 vs .272). Εδω πλεγμα με μηχανισμους που
αφορουν ΚΥΡΙΩΣ το επιπεδο πονταρισματος:
  luck_w  {0.25, 0.5, 0.75} : βαρος του 3P%/FT% ΤΟΥ ΜΑΤΣ (υπολοιπο = μεσος λιγκας περσι)· v1 = 0.5
  HL      {60, 120, 9999}   : ημιζωη (μερες)· v1 = 120
  carry   {0.5, 0.7, 1.0}   : περσινη εικονα· v1 = 0.7
  mu_w    {0.5, 5, 50}      : ποσο «κολλαει» το επιπεδο της λιγκας στο περσινο (ισοδυναμες παρατηρησεις)· v1 = 5
  trend   {0, 0.5, 1.0}     : + trend × (περσινη αυξηση μεσου συνολου λιγκας) στην προβλεψη συνολου· v1 = 0
ΣΤΑΘΕΡΑ: ρυθμος ανα ομαδα, βαρος περσινης 8, διορθωση αντιπαλου, εδρα 6, ουδετερο εκτος πολης.
ΜΕΤΡΟ: b συνολου = κλιση (πραγματικο − closing) πανω στο (μοντελο − closing)· + μεση μεροληψια (αναφορα).
ΠΡΟ-ΔΗΛΩΜΕΝΟΣ ΚΑΝΟΝΑΣ (ΜΙΑ εκτελεση): η LOSO-επιλογη ΥΙΟΘΕΤΕΙΤΑΙ για τα συνολα αν στις 6 σεζον-εξω εχει μεγαλυτερο b απο
το v1 ΣΤΟ ΣΥΝΟΛΟ ΚΑΙ σε ≥4/6 σεζον. Αλλιως μενει το v1.
Εξοδος: el_loso_totals_out.txt
"""
import sys, itertools, math
from collections import Counter
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))

src = open('el_mech_tests.py', encoding='utf-8').read().split('VARIANTS = [')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
SS = [s for s in EVAL if (SE == s).sum() >= 30]
LG = ns['LG']; lg_prev = ns['lg_prev']

def luck_pts(w):
    res = []
    for side in ('h', 'a'):
        p3l = np.array([lg_prev(s)['p3'] for s in D.season]); ftl = np.array([lg_prev(s)['ft'] for s in D.season])
        m3, a3, mf, af = (D[f'{side}_{c}'].values.astype(float) for c in ('fgm3', 'fga3', 'ftm', 'fta'))
        p3g = np.where(a3 > 0, m3 / np.maximum(a3, 1), p3l); ftg = np.where(af > 0, mf / np.maximum(af, 1), ftl)
        res.append(D[f'{side}_pts'].values - 3 * m3 + 3 * a3 * (w * p3g + (1 - w) * p3l) - mf + af * (w * ftg + (1 - w) * ftl))
    return 100 * res[0] / D.poss.values, 100 * res[1] / D.poss.values

def fit_eff_mu(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0, mu_w):
    nG = len(hi); sw = np.sqrt(w)
    A = np.zeros((2 * nG + 2 * n + 1, 1 + 2 * n)); y = np.zeros(2 * nG + 2 * n + 1)
    r0 = np.arange(nG); r1 = nG + r0
    A[r0, 0] = sw; A[r0, 1 + hi] = sw; A[r0, 1 + n + ai] = sw; y[r0] = sw * (eh - hb)
    A[r1, 0] = sw; A[r1, 1 + ai] = sw; A[r1, 1 + n + hi] = sw; y[r1] = sw * (ea + hb)
    sl = math.sqrt(lam); k = np.arange(n)
    A[2 * nG + k, 1 + k] = sl; y[2 * nG + k] = sl * o0; A[2 * nG + n + k, 1 + n + k] = sl; y[2 * nG + n + k] = sl * d0
    A[-1, 0] = math.sqrt(mu_w); y[-1] = math.sqrt(mu_w) * mu0
    x = np.linalg.lstsq(A, y, rcond=None)[0]
    return x[0], x[1:1 + n], x[1 + n:]

# μεσο συνολο λιγκας ανα σεζον (κανονικη περιοδος) -> περσινη αυξηση
RSm = D.phase.values == 'RS'
TOTS = {s: float((D.hs + D.as_).values[RSm & (D.season.values == s)].mean()) for s in SEAS}
def delta(s):
    i = SEAS.index(s)
    return TOTS[SEAS[i - 1]] - TOTS[SEAS[i - 2]] if i >= 2 else 0.0

_LP = {}
def run_t(luck_w=0.5, HL=120, carry=0.7, mu_w=5.0, trend=0.0, lam=8, h=6.0):
    if luck_w not in _LP: _LP[luck_w] = luck_pts(luck_w)
    EH, EA = _LP[luck_w]
    tot = np.full(len(D), np.nan); prior = {}
    mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean())
    dnum = np.array([(d - D.date.iloc[0]).days for d in D.date])
    for s in SEAS:
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        o0 = np.array([carry * prior.get(t, (0, 0, 0))[0] for t in teams]); d0 = np.array([carry * prior.get(t, (0, 0, 0))[1] for t in teams])
        p0 = np.array([carry * prior.get(t, (0, 0, 0))[2] for t in teams])
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        neu = D.ff.values[sidx] | D.relocated.values[sidx]
        hb = np.where(neu, 0.0, h / 2); dn = dnum[sidx]; eh = EH[sidx]; ea = EA[sidx]; pc = D.pace.values[sidx]
        add = trend * delta(s)
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                w = 0.5 ** ((d - dn[past]) / HL)
                mu, O, Dd = fit_eff_mu(hi[past], ai[past], eh[past], ea[past], hb[past], w, n, o0, d0, lam, mu0, mu_w)
                pm, Pc = fit_pace(hi[past], ai[past], pc[past], w, n, p0, lam, pm0)
            else:
                mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
            hh, aa, hbb = hi[cur], ai[cur], hb[cur]
            e_h = mu + O[hh] + Dd[aa] + hbb; e_a = mu + O[aa] + Dd[hh] - hbb
            tot[sidx[cur]] = (pm + Pc[hh] + Pc[aa]) * (e_h + e_a) / 100 + add
        w = 0.5 ** ((dn.max() - dn) / HL)
        mu, O, Dd = fit_eff_mu(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0, mu_w)
        pm, Pc = fit_pace(hi, ai, pc, w, n, p0, lam, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return tot[IDX]

GRID = list(itertools.product([0.25, 0.5, 0.75], [60, 120, 9999], [0.5, 0.7, 1.0], [0.5, 5.0, 50.0], [0.0, 0.5, 1.0]))
V1 = (0.5, 120, 0.7, 5.0, 0.0)
P(f'πλεγμα {len(GRID)} · σεζον {SS} · ματς {len(IDX)}')
PR = {}
for i, c in enumerate(GRID):
    PR[c] = run_t(*c)
    if (i + 1) % 27 == 0: P(f'  {i + 1}/{len(GRID)}')
chk = run(); P(f'ελεγχος: v1 εδω = v1 του el_mech_tests (μεγ. διαφορα συνολου {np.max(np.abs(PR[V1] - chk[IDX, 1])):.2e})')

def b_of(t, mask):
    return np.polyfit((t - MT)[mask], (TOT - MT)[mask], 1)[0]
def lab(c):
    return f'τυχη {c[0]} · φθορα {"καμια" if c[1] == 9999 else c[1]} · περσι {int(c[2]*100)}% · επιπεδο λιγκας {c[3]} · ταση {c[4]}'

hx, hy, vx, vy, wins, picks = [], [], [], [], 0, []
for s in SS:
    tr = (SE != s) & np.isin(SE, SS); te = SE == s
    best = max(GRID, key=lambda c: b_of(PR[c], tr)); picks.append(best)
    bb, b1 = b_of(PR[best], te), b_of(PR[V1], te); wins += bb > b1
    hx.append((PR[best] - MT)[te]); hy.append((TOT - MT)[te]); vx.append((PR[V1] - MT)[te]); vy.append((TOT - MT)[te])
    P(f'  {s[1:]} εξω: [{lab(best)}] → b {bb:+.2f} · v1 {b1:+.2f} · μεροληψια (πραγμ − μοντ) {np.mean((TOT - PR[best])[te]):+.1f} vs v1 {np.mean((TOT - PR[V1])[te]):+.1f}')
bL = np.polyfit(np.concatenate(hx), np.concatenate(hy), 1)[0]; b1 = np.polyfit(np.concatenate(vx), np.concatenate(vy), 1)[0]
ok = bL > b1 and wins >= 4
P(f'\nΣΥΝΟΛΟ 6 σεζον-εξω: LOSO b {bL:+.3f} · v1 b {b1:+.3f} · καλυτερο σε {wins}/{len(SS)} → {"ΥΙΟΘΕΤΕΙΤΑΙ" if ok else "ΜΕΝΕΙ ΤΟ v1"}')
for j, nm in enumerate(('τυχη', 'φθορα', 'περσινη εικονα', 'επιπεδο λιγκας', 'ταση')):
    P(f'  σταθεροτητα — {nm}: ' + ', '.join(f'{k}×{v}' for k, v in Counter(str(p[j]) for p in picks).most_common()))
ba = max(GRID, key=lambda c: b_of(PR[c], np.isin(SE, SS)))
P(f'(αναφορα) καλυτερο σε ολες μαζι: [{lab(ba)}] b {b_of(PR[ba], np.isin(SE, SS)):+.3f} · μεροληψια {np.mean(TOT - PR[ba]):+.1f} (v1 {np.mean(TOT - PR[V1]):+.1f})')
open('el_loso_totals_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
