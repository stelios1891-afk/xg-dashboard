# -*- coding: utf-8 -*-
"""el_live_experts_backtest.py — ΙΣΤΟΡΙΚΟ ΤΗΣ LIVE ΡΥΘΜΙΣΗΣ ΕΙΔΙΚΩΝ στο χαντικαπ (25/9/2026, αιτημα Στελιου «ξεκινα με το 1»).
Live (el_refresh v3): αρχικο net = (w_team/0.7)·(v1 αρχικο) + w_exp·E(θεση BasketNews), μετα το v1 συνεχιζει κανονικα (βαρος 8, HL 120).
Εδω ΑΚΡΙΒΩΣ το ιδιο, σεζον 2021-2025, ΤΙΜΙΑ: για καθε σεζον-τεστ Y
  · w_team, w_exp απο τη στατικη παλινδρομηση του τεστ Γ ΧΩΡΙΣ τη Y (y = εδρα + w_team·ομαδα περσι + w_exp·ειδικοι)
  · E(θεση) απο την κατανομη ratings ομαδων των ΑΛΛΩΝ σεζον (ridge λ2, οπως live)
Συγκριση με v1 (χωρις ειδικους) στα ιδια ματς: ακριβεια, b, ROI χαντικαπ (Pinnacle closing, κανονικη περιοδος), ανα περιοδο/ρολο.
ΚΡΙΤΗΡΙΟ ΕΠΙΒΕΒΑΙΩΣΗΣ (προ-δηλωμενο): edge ≥8% ROI οχι χειροτερο απο v1 ΚΑΙ κερδοφορες σεζον οχι λιγοτερες.
Εξοδος: el_live_experts_backtest_out.txt"""
import sys, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
_o4 = []
ex = open('el_expert_prior_test.py', encoding='utf-8').read()
src = ex.split('base, ENDS = run_x(0.0)')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out = _o4
def P(s=''):
    print(s, flush=True); out.append(str(s))
gv = {}
exec(open('el_player_value2b.py', encoding='utf-8').read().split('rows = []')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), gv)
team_end, GG, DD = gv['team_end'], gv['G'], gv['D']
SE5 = list(RANK)
TE = {s: team_end(s) for s in gv['SEAS']}
def q2r(q, excl):
    ends = [np.sort(np.array(list(TE[s].values())))[::-1] for s in gv['SEAS'] if s >= 'E2018' and s != excl]
    return float(np.mean([np.interp(q, (np.arange(len(e)) + .5) / len(e), e) for e in ends]))
# ---- βαρη ανα fold (στατικη παλινδρομηση οπως τεστ Γ) ----
rows = []
for Y in SE5:
    prev = gv['SEAS'][gv['SEAS'].index(Y) - 1]; N = len(RANK[Y])
    E = {t: q2r((r - .5) / N, Y) for t, r in RANK[Y].items()}
    g = GG[(GG.season == Y) & (GG.phase == 'RS')]
    for k in g.index:
        h, a = DD.loc[k, 'home'], DD.loc[k, 'away']
        rows.append(dict(season=Y, y=g.loc[k, 'y'], home=float(not g.loc[k, 'neu']), team=TE[prev].get(h, 0) - TE[prev].get(a, 0), exp=E.get(h, np.nan) - E.get(a, np.nan)))
Qs = pd.DataFrame(rows).dropna()
W = {}
for Y in SE5:
    tr = Qs[Qs.season != Y]; c = np.linalg.lstsq(tr[['home', 'team', 'exp']].values, tr.y.values, rcond=None)[0]; W[Y] = (c[1], c[2])
P('βαρη ανα σεζον-τεστ (απο τις αλλες): ' + ' · '.join(f'{Y[-2:]}: ομαδα {w[0]:.2f} ειδικοι {w[1]:.2f}' for Y, w in W.items()) + '  (live: 0.32 / 0.42)')

def run_live(target, wt, we, Emap, carry=0.7, lam=8, HL=120, h=6.0):
    if 'L' not in _PTS:
        ph, pa = points(D, 'L'); _PTS['L'] = (100 * ph / D.poss.values, 100 * pa / D.poss.values)
    EH, EA = _PTS['L']; preds = np.full(len(D), np.nan); prior = {}
    mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean())
    dnum = np.array([(d - D.date.iloc[0]).days for d in D.date])
    for s in SEAS:
        sidx = np.where(D.season.values == s)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        o0 = np.array([carry * prior.get(t, (0, 0, 0))[0] for t in teams]); d0 = np.array([carry * prior.get(t, (0, 0, 0))[1] for t in teams])
        p0 = np.array([carry * prior.get(t, (0, 0, 0))[2] for t in teams])
        if s == target:
            for t, i in ix.items():
                if t not in Emap: continue
                cur = o0[i] - d0[i]; new = wt / carry * cur + we * Emap[t]
                o0[i] += (new - cur) / 2; d0[i] -= (new - cur) / 2
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        neu = D.ff.values[sidx] | D.relocated.values[sidx]
        hb = np.where(neu, 0.0, h / 2); dn = dnum[sidx]; eh = EH[sidx]; ea = EA[sidx]; pc = D.pace.values[sidx]
        for d in np.unique(dn):
            past = dn < d; cur_ = np.where(dn == d)[0]
            if past.any():
                w = 0.5 ** ((d - dn[past]) / HL)
                mu, O, Dd = fit_eff(hi[past], ai[past], eh[past], ea[past], hb[past], w, n, o0, d0, lam, mu0)
                pm, Pc = fit_pace(hi[past], ai[past], pc[past], w, n, p0, lam, pm0)
            else:
                mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
            hh, aa, hbb = hi[cur_], ai[cur_], hb[cur_]
            e_h = mu + O[hh] + Dd[aa] + hbb; e_a = mu + O[aa] + Dd[hh] - hbb
            preds[sidx[cur_]] = (pm + Pc[hh] + Pc[aa]) * (e_h - e_a) / 100
        w = 0.5 ** ((dn.max() - dn) / HL)
        mu, O, Dd = fit_eff(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0)
        pm, Pc = fit_pace(hi, ai, pc, w, n, p0, lam, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return preds

M_LIVE = np.array(M_V1, float)
for Y in SE5:
    N = len(RANK[Y]); Emap = {t: q2r((r - .5) / N, Y) for t, r in RANK[Y].items()}
    pr = run_live(Y, W[Y][0], W[Y][1], Emap)[IDX]
    M_LIVE[SE == Y] = pr[SE == Y]
    print(f'  {Y} ετοιμο', flush=True)
assert np.allclose(run_live('none', 0.32, 0.42, {})[IDX], M_V1), 'χωρις ειδικους πρεπει να ειναι ακριβως v1'

rs_all = D[D.phase == 'RS'].sort_values('date'); cnt, gno = {}, {}
for i, r in rs_all.iterrows():
    for t in (r.home, r.away): cnt[(r.season, t)] = cnt.get((r.season, t), 0) + 1
    gno[i] = max(cnt[(r.season, r.home)], cnt[(r.season, r.away)])
RND = np.array([gno.get(i, 99) for i in IDX])
m5 = RS & np.isin(SE, SE5)
P('')
P('=== ΑΚΡΙΒΕΙΑ (κανονικη περιοδος 2021-2025, ματς με closing) ===')
for lab, mm in (('v1 χωρις ειδικους', M_V1), ('LIVE με ειδικους', M_LIVE)):
    e = ACT - mm
    P(f'  {lab:18s} RMSE αγων 1-10 {np.sqrt(np.mean(e[m5 & (RND <= 10)] ** 2)):.2f} · 11+ {np.sqrt(np.mean(e[m5 & (RND > 10)] ** 2)):.2f} · ολη {np.sqrt(np.mean(e[m5] ** 2)):.2f}'
      f' · κλιση b {np.polyfit((mm - MM)[m5], (ACT - MM)[m5], 1)[0]:+.3f} · μεση |διαφωνια με αγορα| 1-10 {np.mean(np.abs(mm - MM)[m5 & (RND <= 10)]):.1f} π.')
P(f'  (αγορα: RMSE αγων 1-10 {np.sqrt(np.mean((ACT - MM)[m5 & (RND <= 10)] ** 2)):.2f} · ολη {np.sqrt(np.mean((ACT - MM)[m5] ** 2)):.2f})')

def spb(mm):
    b = bets(mm, T_LO); b = b[(b.mkt == 'sp') & b.season.isin(SE5)].copy()
    jj = [j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0])]
    b['rnd'] = [r for r, s in zip(RND[jj], SE[jj]) if s in SE5]; return b
B1, BL = spb(M_V1), spb(M_LIVE)
cell = lambda x: f'{x.p.mean()*100:+5.1f}% ({len(x)}, {x.p.sum():+.1f}u)' if len(x) else '—'
P('')
P('=== ROI ΧΑΝΤΙΚΑΠ (Pinnacle closing, 2021-2025) ===')
okk = None
for thr in (0.05, 0.08, 0.10, 0.15):
    a, b = B1[B1.edge >= thr], BL[BL.edge >= thr]
    pa = sum(1 for s in SE5 if len(a[a.season == s]) and a[a.season == s].p.mean() > 0); pb = sum(1 for s in SE5 if len(b[b.season == s]) and b[b.season == s].p.mean() > 0)
    P(f'  edge ≥{thr*100:2.0f}%: v1 {cell(a)} {pa}/5 · LIVE {cell(b)} {pb}/5')
    if thr == 0.08: okk = (b.p.mean() >= a.p.mean()) and pb >= pa
P('')
P('=== edge ≥8% ανα σεζον / περιοδο / ρολο ===')
a, b = B1[B1.edge >= 0.08], BL[BL.edge >= 0.08]
P('  σεζον: ' + ' · '.join(f'{s[-2:]}: v1 {a[a.season == s].p.mean()*100:+.0f}% ({len(a[a.season == s])}) → LIVE {b[b.season == s].p.mean()*100:+.0f}% ({len(b[b.season == s])})' for s in SE5))
for lab, lo, hi in (('αγων 1-6', 1, 6), ('αγων 7-10', 7, 10), ('αγων 11+', 11, 99)):
    P(f'  {lab:9s}: v1 {cell(a[(a.rnd >= lo) & (a.rnd <= hi)])} · LIVE {cell(b[(b.rnd >= lo) & (b.rnd <= hi)])}')
for role in ('φαβορι', 'αουτσαιντερ'):
    P(f'  {role:11s}: v1 {cell(a[a.role == role])} · LIVE {cell(b[b.role == role])}')
P('')
P(f'ΚΡΙΤΗΡΙΟ ΕΠΙΒΕΒΑΙΩΣΗΣ (≥8%: ROI οχι χειροτερο & σεζον οχι λιγοτερες): {"✓ ΕΠΙΒΕΒΑΙΩΝΕΤΑΙ" if okk else "✗ ΔΕΝ ΕΠΙΒΕΒΑΙΩΝΕΤΑΙ — για επανεξεταση"}')
open('el_live_experts_backtest_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
