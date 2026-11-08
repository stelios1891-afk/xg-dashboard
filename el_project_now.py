# -*- coding: utf-8 -*-
"""el_project_now.py — προβλεψεις Ευρωλιγκας με το ΠΑΓΩΜΕΝΟ μοντελο του el_model_test (24/9/2026).
Παραμετροι: HL=120 λ=8 carry=0.7 h=6 παραλλαγη L. Τρεχει ολες τις σεζον ως E2025, κραταει το τελικο
rating καθε ομαδας, και προβλεπει τα ματς της E2026 που δεν εχουν παιχτει (οσο δεν υπαρχουν φετινα ματς
= μονο prior: 0.7 × περσινο, νεες ομαδες 0). Εξοδος: el_projections_now.csv + αναλυση ενος ματς."""
import sys, json, math, urllib.request
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('el_model_test.py', encoding='utf-8').read()
src = src[:src.index('# ---------------- ρυθμιση (χωρις αποδοσεις) ----------------')]
src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", '')
ns = {}
exec(src, ns)
D, points, fit_eff, fit_pace, SEAS = ns['D'], ns['points'], ns['fit_eff'], ns['fit_pace'], ns['SEAS']
HL, LAM, CARRY, H, VAR = 120, 8, 0.7, 6, 'L'

ph, pa = points(D, VAR); EH = 100 * ph / D.poss.values; EA = 100 * pa / D.poss.values
prior = {}; mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean())
dnum = np.array([(d - D.date.iloc[0]).days for d in D.date])
for s in SEAS:
    sidx = np.where(D.season.values == s)[0]
    teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
    hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
    hb = np.where(D.neutral.values[sidx] == 1, 0.0, H / 2)
    o0 = np.array([CARRY * prior.get(t, (0, 0, 0))[0] for t in teams]); d0 = np.array([CARRY * prior.get(t, (0, 0, 0))[1] for t in teams])
    p0 = np.array([CARRY * prior.get(t, (0, 0, 0))[2] for t in teams]); dn = dnum[sidx]
    w = 0.5 ** ((dn.max() - dn) / HL)
    mu, O, Dd = fit_eff(hi, ai, EH[sidx], EA[sidx], hb, w, n, o0, d0, LAM, mu0)
    pm, Pc = fit_pace(hi, ai, D.pace.values[sidx], w, n, p0, LAM, pm0)
    prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
names = dict(zip(D.home, D.hname)); names.update(dict(zip(D.away, D.aname)))

print(f'ΤΕΛΟΣ 2025-26: μεσος ποντοι/100 κατοχες mu = {mu0:.1f} · μεσος ρυθμος pm = {pm0:.1f} (αθροισμα 2 ομαδων: pace = pm + P_h + P_a)')
print('\nΚΑΤΑΤΑΞΗ τελος 2025-26 (O = επιθεση πανω απο μεσο, D = ποντοι που δεχεται πανω απο μεσο → αρνητικο = καλη αμυνα, net = O − D):')
R = sorted(prior.items(), key=lambda kv: -(kv[1][0] - kv[1][1]))
for t, (o, d, p) in R:
    print(f'  {names.get(t, t)[:30]:30s} O {o:+5.1f} · D {d:+5.1f} · net {o-d:+5.1f} · ρυθμος {p:+4.1f}')

H_ = {'User-Agent': 'Mozilla/5.0 Chrome/120.0', 'Accept': 'application/json'}
g = json.loads(urllib.request.urlopen(urllib.request.Request('https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games', headers=H_), timeout=60).read())['data']
g = sorted([x for x in g if not x.get('played')], key=lambda x: x['utcDate'])
rows = []
for x in g:
    hc, ac = x['local']['club']['code'], x['road']['club']['code']
    oh, dh, pch = [CARRY * v for v in prior.get(hc, (0, 0, 0))]
    oa, da, pca = [CARRY * v for v in prior.get(ac, (0, 0, 0))]
    neu = x['phaseType']['code'] == 'FF'; hb = 0 if neu else H / 2
    eh = mu0 + oh + da + hb; ea = mu0 + oa + dh - hb; poss = pm0 + pch + pca
    rows.append(dict(rnd=x['round'], utc=x['utcDate'], home=x['local']['club']['name'], away=x['road']['club']['name'],
                     new_h=hc not in prior, new_a=ac not in prior, oh=oh, dh=dh, oa=oa, da=da, eh=eh, ea=ea, poss=poss,
                     pts_h=poss * eh / 100, pts_a=poss * ea / 100, margin=poss * (eh - ea) / 100, total=poss * (eh + ea) / 100))
P = pd.DataFrame(rows); P.to_csv('el_projections_now.csv', index=False)
print('\nΑΓΩΝΙΣΤΙΚΗ 1 (μονο prior — δεν εχει παιχτει φετινο ματς):')
for r in P[P.rnd == P.rnd.min()].itertuples():
    tag = (' [ΝΕΑ γηπ.]' if r.new_h else '') + (' [ΝΕΑ φιλοξ.]' if r.new_a else '')
    print(f'  {r.utc[:16]} {r.home[:24]:24s} - {r.away[:24]:24s} {r.pts_h:5.1f}-{r.pts_a:5.1f} · γραμμη γηπ {-r.margin:+5.1f} · συνολο {r.total:5.1f}{tag}')
r = P.iloc[0]
print(f"\nΑΝΑΛΥΣΗ: {r.home} - {r.away}")
print(f"  επιθεση γηπ. {r.oh:+.1f} · αμυνα φιλοξ. {r.da:+.1f} · εδρα +{H/2:.0f} → ποντοι/100 γηπ = {mu0:.1f} {r.oh:+.1f} {r.da:+.1f} +{H/2:.0f} = {r.eh:.1f}")
print(f"  επιθεση φιλοξ. {r.oa:+.1f} · αμυνα γηπ. {r.dh:+.1f} · εδρα −{H/2:.0f} → ποντοι/100 φιλοξ = {mu0:.1f} {r.oa:+.1f} {r.dh:+.1f} −{H/2:.0f} = {r.ea:.1f}")
print(f"  κατοχες = {r.poss:.1f} → σκορ {r.pts_h:.1f} - {r.pts_a:.1f} · διαφορα {r.margin:+.1f} · συνολο {r.total:.1f}")
