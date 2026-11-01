# -*- coding: utf-8 -*-
"""el_mech_tests.py — ΕΥΡΩΛΙΓΚΑ: ΚΑΘΕ μηχανισμος του μοντελου περναει απο τεστ, σε ΟΛΕΣ τις σεζον με closing (24/9/2026,
αιτημα Στελιου: «οταν εχουμε ολες τις σεζον, καθε μηχανισμος που χρησιμοποιειται θα πρεπει να περασει απο τεστ»).

ΒΑΣΗ = το v1 που τρεχει live: διορθωση αντιπαλου ON, τυχη 3P/FT (L), ημιζωη 120 μερες, prior 70% περσι με βαρος λ=8,
εδρα 6/100, ουδετερο οταν «εντος» >300 χλμ απο το σπιτι (και Final Four), ρυθμος ανα ομαδα, νεες ομαδες = 0.
ΚΑΘΕ ΠΑΡΑΛΛΑΓΗ αλλαζει ΕΝΑ πραγμα. Walk-forward (καθε ματς μονο με οτι ειχε παιχτει πριν).

ΚΡΙΣΗ απεναντι στο closing Pinnacle (fallback διαμεσος) σε ΟΛΕΣ τις σεζον E2020-E2025:
  b = κλιση του (πραγματικο − αγορα) πανω στο (μοντελο − αγορα) — ποσο απο τη διαφωνια μας επαληθευεται —
  χωριστα για διαφορα (χαντικαπ) και συνολο· + RMSE απεναντι στα αποτελεσματα (αναφορα).
ΠΡΟ-ΔΗΛΩΜΕΝΟΣ ΚΑΝΟΝΑΣ (γραφτηκε ΠΡΙΝ το τρεξιμο· ΜΙΑ εκτελεση):
  Μια παραλλαγη ΝΙΚΑ τη βαση αν σε μια αγορα (διαφορα ή συνολο) εχει μεγαλυτερο b ΣΤΟ ΣΥΝΟΛΟ των σεζον ΚΑΙ σε ≥4/6 σεζον (≥2/3 των σεζον με closing),
  χωρις να ριχνει το b της αλλης αγορας συνολικα πανω απο 0.05.
  Μηχανισμος της βασης ΠΕΡΝΑ = καμια εναλλακτικη του δεν τον νικα ΚΑΙ η αφαιρεση του (οπου εχει νοημα) δεν τον νικα.
  Σημειωση: οι παραμετροι του v1 ρυθμιστηκαν στα ΑΠΟΤΕΛΕΣΜΑΤΑ 2021-23 — το b απεναντι στην αγορα δεν επηρεαζεται απο αυτο.
Εξοδος: el_mech_tests_out.txt
"""
import sys, json, math, unicodedata, re
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))

src = open('el_model_test.py', encoding='utf-8').read()
ns = {}
exec(src[:src.index('# ---------------- walk-forward ----------------')].replace("sys.stdout.reconfigure(encoding='utf-8')", '').replace('P(f', 'pass  # P(f'), ns)
exec(src[src.index('def fit_eff'):src.index('_PTS = {}')], ns)
D, points, fit_eff, fit_pace = ns['D'], ns['points'], ns['fit_eff'], ns['fit_pace']
SEAS = sorted(D.season.unique())

# ---- ουδετερα γηπεδα (ιδιος κανονας με el_refresh) ----
S = json.load(open('el_sched.json', encoding='utf-8'))
_ft = open('el_fatigue_travel.py', encoding='utf-8').read(); _c = {'math': math, 'np': np}
exec(_ft[_ft.index('CITY = {'):_ft.index('D = pd.read_csv')], _c); ll, km = _c['ll'], _c['km']
TRUE_HOME = {'TEL': (32.05, 34.79), 'HTA': (32.05, 34.79), 'DUB': (25.21, 55.27), 'BES': (41.04, 29.00), 'PRS': (48.89, 2.36)}
for s in sorted(S):
    for x in S[s]:
        if s <= 'E2022' and x['phase'] == 'RS' and x['hcode'] not in TRUE_HOME and ll(x.get('vname')):
            TRUE_HOME.setdefault(x['hcode'], ll(x['vname']))
VN = {f"{s}_{x['code']}": x.get('vname') for s in S for x in S[s]}
def reloc(k, h):
    th, v = TRUE_HOME.get(h), ll(VN.get(k))
    return bool(th and v and km(th, v) > 300)
D['relocated'] = [reloc(k, h) for k, h in zip(D.key, D.home)]
D['ff'] = (D.phase == 'FF').values

def fit_eff_noadj(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0):
    """χωρις διορθωση αντιπαλου: επιθεση = μεσος ποντων που βαζει, αμυνα = μεσος που δεχεται (+ ιδιο prior)."""
    nG = len(hi); sw = np.sqrt(w)
    A = np.zeros((4 * nG + 2 * n + 1, 1 + 2 * n)); y = np.zeros(A.shape[0]); r = np.arange(nG)
    for blk, (team, col, val) in enumerate(((hi, 0, eh - hb), (ai, 0, ea + hb), (ai, 1, eh - hb), (hi, 1, ea + hb))):
        rr = blk * nG + r; A[rr, 0] = sw; A[rr, 1 + col * n + team] = sw; y[rr] = sw * val
    sl = math.sqrt(lam); k = np.arange(n); b0 = 4 * nG
    A[b0 + k, 1 + k] = sl; y[b0 + k] = sl * o0; A[b0 + n + k, 1 + n + k] = sl; y[b0 + n + k] = sl * d0
    A[-1, 0] = math.sqrt(5.0); y[-1] = math.sqrt(5.0) * mu0
    x = np.linalg.lstsq(A, y, rcond=None)[0]
    return x[0], x[1:1 + n], x[1 + n:]

_PTS = {}
def run(adj=True, var='L', HL=120, lam=8, carry=0.7, h=6.0, neutral=True, newc=0.0, pace=True, h_roll=False):
    if var not in _PTS:
        ph, pa = points(D, var); _PTS[var] = (100 * ph / D.poss.values, 100 * pa / D.poss.values)
    EH, EA = _PTS[var]
    fe = fit_eff if adj else fit_eff_noadj
    preds = np.full((len(D), 2), np.nan); prior = {}
    mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(D.pace.mean())
    dnum = np.array([(d - D.date.iloc[0]).days for d in D.date])
    for si, s in enumerate(SEAS):
        sidx = np.where(D.season.values == s)[0]
        hs = h
        if h_roll and si >= 1:   # εδρα απο τις 2 προηγουμενες σεζον (μεση διαφορα αποδοτικοτητας εντος-εκτος, χωρις ουδετερα)
            prv = D.season.isin(SEAS[max(0, si - 2):si]).values & ~D.ff.values & ~D.relocated.values
            hs = float(np.mean(EH[prv] - EA[prv]))
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        newt = {t for t in teams if prior and t not in prior}
        o0 = np.array([(-newc / 2 if t in newt else carry * prior.get(t, (0, 0, 0))[0]) for t in teams])
        d0 = np.array([(newc / 2 if t in newt else carry * prior.get(t, (0, 0, 0))[1]) for t in teams])
        p0 = np.array([carry * prior.get(t, (0, 0, 0))[2] for t in teams])
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        neu = D.ff.values[sidx] | (D.relocated.values[sidx] if neutral else False)
        hb = np.where(neu, 0.0, hs / 2); dn = dnum[sidx]; eh = EH[sidx]; ea = EA[sidx]; pc = D.pace.values[sidx]
        for d in np.unique(dn):
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                w = 0.5 ** ((d - dn[past]) / HL)
                mu, O, Dd = fe(hi[past], ai[past], eh[past], ea[past], hb[past], w, n, o0, d0, lam, mu0)
                pm, Pc = fit_pace(hi[past], ai[past], pc[past], w, n, p0, lam, pm0) if pace else (float(np.average(pc[past], weights=w)), np.zeros(n))
            else:
                mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, (p0 if pace else np.zeros(n))
            hh, aa, hbb = hi[cur], ai[cur], hb[cur]
            e_h = mu + O[hh] + Dd[aa] + hbb; e_a = mu + O[aa] + Dd[hh] - hbb
            poss = pm + Pc[hh] + Pc[aa]
            preds[sidx[cur], 0] = poss * (e_h - e_a) / 100; preds[sidx[cur], 1] = poss * (e_h + e_a) / 100
        w = 0.5 ** ((dn.max() - dn) / HL)
        mu, O, Dd = fe(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0)
        pm, Pc = fit_pace(hi, ai, pc, w, n, p0, lam, pm0) if pace else (float(pc.mean()), np.zeros(n))
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return preds

# ---- αγορα: ολες οι σεζον με closing ----
def tok(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return set(w for w in re.findall(r'[a-z]{3,}', s) if w not in ('basketball', 'basket', 'club', 'the', 'sport'))
byid = {}
for l in open('toa_el_closing.jsonl', encoding='utf-8'):
    o = json.loads(l); byid[o['id']] = o
EVAL = [s for s in SEAS if 'E2020' <= s <= 'E2025']
EV = D[D.season.isin(EVAL)]
mk = {}
for o in byid.values():
    ct = pd.Timestamp(o['commence']); c = EV[(EV.t - ct).abs() <= pd.Timedelta(minutes=25)]
    if not len(c): continue
    th, ta = tok(o['home']), tok(o['away'])
    sc = sorted([(len(th & tok(r.hname)) + len(ta & tok(r.aname)) - 0.5 * (len(th & tok(r.aname)) + len(ta & tok(r.hname))), i) for i, r in c.iterrows()], reverse=True)
    if len(c) > 1 and sc[0][0] <= 0: continue
    i = sc[0][1]; r = D.loc[i]
    flip = len(th & tok(r.aname)) > len(th & tok(r.hname))
    hn, an = (o['away'], o['home']) if flip else (o['home'], o['away'])
    def line(bk):
        sp = tt = None
        for m in bk['markets']:
            if m['key'] == 'spreads':
                a_ = [x for x in m['outcomes'] if x['name'] == hn]; b_ = [x for x in m['outcomes'] if x['name'] == an]
                if a_ and b_ and a_[0].get('point') is not None: sp = float(a_[0]['point'])
            if m['key'] == 'totals':
                ov = [x for x in m['outcomes'] if x['name'] == 'Over']
                if ov: tt = float(ov[0]['point'])
        return sp, tt
    pin = [b for b in o['bookmakers'] if b['key'] == 'pinnacle']
    sp, tt = line(pin[0]) if pin else (None, None)
    if sp is None or tt is None:
        al = [line(b) for b in o['bookmakers']]
        if sp is None and any(x[0] is not None for x in al): sp = float(np.median([x[0] for x in al if x[0] is not None]))
        if tt is None and any(x[1] is not None for x in al): tt = float(np.median([x[1] for x in al if x[1] is not None]))
    if sp is not None and tt is not None:
        mk[i] = (-sp, tt, bool(pin))
IDX = np.array(sorted(mk)); MM = np.array([mk[i][0] for i in IDX]); MT = np.array([mk[i][1] for i in IDX])
ACT = (D.hs - D.as_).values[IDX].astype(float); TOT = (D.hs + D.as_).values[IDX].astype(float); SE = D.season.values[IDX]
RS = D.phase.values[IDX] == 'RS'
P(f'Ματς με closing ανα σεζον: ' + ' · '.join(f'{s[1:]} {int((SE == s).sum())}' for s in EVAL) + f' · συνολο {len(IDX)} (Pinnacle {sum(mk[i][2] for i in IDX)})')

def slope(x, y):
    b = np.polyfit(x, y, 1)[0]; r = y - np.poly1d(np.polyfit(x, y, 1))(x)
    return b, b / (r.std(ddof=2) / (x.std() * math.sqrt(len(x))))

def evaluate(pr):
    m, t = pr[IDX, 0], pr[IDX, 1]; res = {}
    for lab, mo, mkv, a in (('m', m, MM, ACT), ('t', t, MT, TOT)):
        b, tt = slope(mo - mkv, a - mkv); per = {s: slope((mo - mkv)[SE == s], (a - mkv)[SE == s])[0] for s in EVAL if (SE == s).sum() >= 30}
        res[lab] = dict(b=b, t=tt, per=per, rmse=math.sqrt(np.mean((a - mo) ** 2)))
    return res

VARIANTS = [
    ('BASE v1', {}),
    ('Α. χωρις διορθωση αντιπαλου', dict(adj=False)),
    ('Β. χωρις διορθωση τυχης (ωμοι ποντοι)', dict(var='raw')),
    ('Γ. ημιζωη 60 μερες', dict(HL=60)), ('Γ. χωρις φθορα (ολα ισα)', dict(HL=9999)),
    ('Δ. περσινη εικονα 100%', dict(carry=1.0)), ('Δ. περσινη εικονα 50%', dict(carry=0.5)), ('Δ. χωρις περσινη (0%)', dict(carry=0.0)),
    ('Ε. βαρος περσινης 4 ματς', dict(lam=4)), ('Ε. βαρος περσινης 14 ματς', dict(lam=14)),
    ('ΣΤ. εδρα 4/100', dict(h=4.0)), ('ΣΤ. εδρα 5/100', dict(h=5.0)), ('ΣΤ. εδρα απο 2 προηγ. σεζον', dict(h_roll=True)),
    ('Ζ. χωρις κανονα ουδετερου (εκτος πολης)', dict(neutral=False)),
    ('Η. νεες ομαδες −2/100', dict(newc=-2.0)),
    ('Θ. χωρις ρυθμο ανα ομαδα', dict(pace=False)),
]
R = {}
for lab, kw in VARIANTS:
    R[lab] = evaluate(run(**kw))
base = R['BASE v1']
P('\nb = ποσο απο τη διαφωνια μας με το closing επαληθευεται (0 = τιποτα, 1 = ολη) · RMSE = λαθος vs αποτελεσματα (ποντοι)')
P(f'{"παραλλαγη":42s} {"b διαφ":>7s} {"t":>5s} {"b συνολ":>8s} {"t":>5s} {"RMSE δ":>7s} {"RMSE σ":>7s}  νικα; (σεζον καλυτερες διαφ/συνολ)')
verdict = {}
for lab, _ in VARIANTS:
    r = R[lab]
    if lab == 'BASE v1':
        win = ''
    else:
        SS = list(base['m']['per']); need = math.ceil(2 * len(SS) / 3)
        wm = sum(r['m']['per'][s] > base['m']['per'][s] for s in SS); wt = sum(r['t']['per'][s] > base['t']['per'][s] for s in SS)
        beat_m = r['m']['b'] > base['m']['b'] and wm >= need and r['t']['b'] >= base['t']['b'] - 0.05
        beat_t = r['t']['b'] > base['t']['b'] and wt >= need and r['m']['b'] >= base['m']['b'] - 0.05
        verdict[lab] = beat_m or beat_t
        win = f'{"ΝΙΚΑ ΤΗ ΒΑΣΗ" if verdict[lab] else "οχι"} ({wm}/{len(SS)} · {wt}/{len(SS)})'
    P(f'{lab:42s} {r["m"]["b"]:+7.3f} {r["m"]["t"]:5.1f} {r["t"]["b"]:+8.3f} {r["t"]["t"]:5.1f} {r["m"]["rmse"]:7.2f} {r["t"]["rmse"]:7.2f}  {win}')
P('\nΑΝΑ ΣΕΖΟΝ — b διαφορας / b συνολου (βαση):')
P('  ' + ' · '.join(f'{s[1:]} {base["m"]["per"][s]:+.2f}/{base["t"]["per"][s]:+.2f}' for s in base['m']['per']))
P('\nΕΤΥΜΗΓΟΡΙΑ ανα μηχανισμο (κανονας: περνα αν ΚΑΜΙΑ εναλλακτικη/αφαιρεση του δεν νικα τη βαση):')
groups = {}
for lab in verdict:
    groups.setdefault(lab.split('.')[0], []).append(lab)
names = {'Α': 'διορθωση αντιπαλου', 'Β': 'διορθωση τυχης 3P/FT', 'Γ': 'ημιζωη 120 μερες', 'Δ': 'περσινη εικονα 70%', 'Ε': 'βαρος περσινης 8 ματς',
         'ΣΤ': 'εδρα 6/100', 'Ζ': 'κανονας ουδετερου εκτος πολης', 'Η': 'νεες ομαδες = 0 (η βαση)', 'Θ': 'ρυθμος ανα ομαδα'}
for g, labs in groups.items():
    lost = [l for l in labs if verdict[l]]
    P(f'  {names[g]:32s} ' + ('ΠΕΡΝΑ' if not lost else 'ΔΕΝ ΠΕΡΝΑ — καλυτερο: ' + '; '.join(l.split('. ', 1)[1] for l in lost)))
open('el_mech_tests_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
