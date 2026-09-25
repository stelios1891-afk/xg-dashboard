# -*- coding: utf-8 -*-
"""el_clv_nowgoal_test.py — CLV ΤΕΣΤ ρυθμισεων χαντικαπ με ιστορικο γραμμων Nowgoal (Crown), 2021-2025 (25/9/2026).
Γιατι: το ROI 5 σεζον εχει θορυβο μεγαλυτερο απο τις διαφορες που ψαχνουμε· το CLV (αν η γραμμη κινηθηκε υπερ μας ως το
κλεισιμο) εχει πολυ λιγοτερο θορυβο.
ΕΙΣΟΔΟΣ: γραμμη/αποδοση Crown ~12ω πριν το τζαμπολ (η τελευταια ≤ −12ω· αν δεν υπαρχει, η πρωτη διαθεσιμη εφοσον ≤ −3ω).
ΚΛΕΙΣΙΜΟ: η τελευταια pre-match γραμμη Crown. Αποδοσεις Nowgoal = HK (0.90 → δεκαδικη 1.90).
PICK: edge ≥ 8% στη γραμμη εισοδου με το μοντελο της ρυθμισης (N(margin, 11.5), ακεραιες γραμμες ±0.5).
ΜΕΤΡΑ CLV (ανα pick): (1) ποντοι που κινηθηκε η γραμμη υπερ μας· (2) EV στο κλεισιμο = P(καλυψη στη γραμμη εισοδου | μεσος
  της αγορας στο κλεισιμο, μετα αφαιρεση γκανιοτας) × αποδοση εισοδου − 1· (3) % picks με θετικο CLV.
ΡΥΘΜΙΣΕΙΣ: live (0.32/0.42/K8/HL120/εδρα6/τυχη.5/×1.0) · v1 χωρις ειδικους · «καλυτερη ακριβεια» (0.5/0.42/K12/HL60/εδρα5/.5/×1.1)
  · live με ανοιγμα ×1.1. Bootstrap (ματς, 2000): πιθανοτητα η καθε μια να εχει μεγαλυτερο EV-στο-κλεισιμο απο το live.
Εξοδος: el_clv_nowgoal_test_out.txt"""
import sys, json, math, re, unicodedata
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
_o7 = []
src = open('el_hcap_big_test.py', encoding='utf-8').read().split('ENG = list(')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out = _o7
def P(s=''):
    print(s, flush=True); out.append(str(s))
CONF = {'live': (0.32, 0.42, 8, 120, 6.0, 0.5, 1.0), 'v1 χωρις ειδικους': (0.7, 0.0, 8, 120, 6.0, 0.5, 1.0),
        'καλυτερη ακριβεια': (0.5, 0.42, 12, 60, 5.0, 0.5, 1.1), 'live + ανοιγμα ×1.1': (0.32, 0.42, 8, 120, 6.0, 0.5, 1.1)}
PREDS = {}
cache_end = {}
for nm, (wt, we, lam, HL, h, lw, sf) in CONF.items():
    k = (HL, h, lw, lam)
    if k not in cache_end: cache_end[k] = ends_for(HL, h, lw, lam)
    v = np.full(len(D), np.nan)
    for Y in SE5:
        sidx, pr = run_season(Y, cache_end[k][Y], wt, we, EM[Y], lam, HL, h, lw); v[sidx] = pr
    PREDS[nm] = np.where(GN >= 7, v * sf, v)
    print(f'  {nm} ετοιμο', flush=True)

# ---- Nowgoal: προγραμμα + ιστορικο Crown χαντικαπ ----
NGS = {'20-21': 'E2020', '21-22': 'E2021', '22-23': 'E2022', '23-24': 'E2023', '24-25': 'E2024', '25-26': 'E2025'}
sched = []
for sea, es in NGS.items():
    try:
        for g in json.load(open(f'nowgoal_el/sched_{sea}.json', encoding='utf-8')):
            g['es'] = es; g['utc'] = (pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)).tz_localize('UTC'); sched.append(g)
    except FileNotFoundError:
        pass
AH = {}
for ln in open('nowgoal_el/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['ot'] == 6 and r.get('t', 21) == 21 and r['cid'] == 3: AH[r['ngid']] = r['rows']
def tok(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return set(w for w in re.findall(r'[a-z]{3,}', s) if w not in ('basketball', 'basket', 'club', 'the', 'sport', 'bc', 'kk', 'fc'))
Dt = D.t
mapping = {}
for g in sched:
    c = D[(D.season == g['es']) & ((Dt - g['utc']).abs() <= pd.Timedelta(hours=3))]
    if not len(c): continue
    th, ta = tok(g['home']), tok(g['away'])
    sc = sorted([(len(th & tok(r.hname)) + len(ta & tok(r.aname)), i) for i, r in c.iterrows()], reverse=True)
    if sc[0][0] == 0 and len(c) > 1: continue
    i = sc[0][1]
    if abs((D.loc[i, 'hs'] or 0) - (g['hs'] or -99)) > 0 and D.loc[i, 'hs'] != g['hs']:
        # επιβεβαιωση με σκορ (αν διαφερει, πιθανη αντιστροφη ή λαθος)
        if not (D.loc[i, 'hs'] == g['as_'] and D.loc[i, 'as_'] == g['hs']): continue
        swap = True
    else:
        swap = False
    mapping[g['ngid']] = (i, swap)
P(f'αντιστοιχιση Nowgoal → δικα μας: {len(mapping)} ματς (απο {len(sched)})· με ιστορικο Crown χαντικαπ: {sum(1 for k in mapping if k in AH)}')

Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
def cover(mu, L, sig=11.5):
    if abs(L - round(L)) < 1e-9:
        pw = Phi((mu + L - 0.5) / sig); pl = Phi((-mu - L - 0.5) / sig); return pw, 1 - pw - pl
    return Phi((mu + L) / sig), 0.0
def implied_mu(L, oh, oa, sig=11.5):
    """μεσος (γηπ − φιλ) που βαζει η αγορα: χωρις γκανιοτα P(γηπ καλυπτει) = (1/oh)/((1/oh)+(1/oa))."""
    ph = (1 / oh) / ((1 / oh) + (1 / oa)); lo, hi = -60.0, 60.0
    for _ in range(60):
        mid = (lo + hi) / 2; pw, pp = cover(mid, L, sig); p = pw / (1 - pp) if pp < 1 else 0.5
        lo, hi = (mid, hi) if p < ph else (lo, mid)
    return (lo + hi) / 2
RSMASK = D.phase.values == 'RS'
rows = []
for ng, (i, swap) in mapping.items():
    if ng not in AH or not RSMASK[D.index.get_loc(i)] or D.loc[i, 'season'] not in SE5: continue
    tip = int(pd.Timestamp(D.loc[i, 't']).timestamp())
    pre = sorted([r for r in AH[ng] if r[4] == 2 and r[0] < tip and r[1] is not None and r[2] and r[3]], key=lambda r: r[0])
    if len(pre) < 2: continue
    ent = [r for r in pre if r[0] <= tip - 12 * 3600]
    e = ent[-1] if ent else (pre[0] if pre[0][0] <= tip - 3 * 3600 else None)
    if e is None: continue
    c = pre[-1]
    sgn = -1 if swap else 1                          # Nowgoal g: + = γηπεδουχος δινει ποντους → γραμμη γηπ L = −g
    Le, ohe, oae = -e[1] * sgn, 1 + (e[2] if not swap else e[3]), 1 + (e[3] if not swap else e[2])
    Lc, ohc, oac = -c[1] * sgn, 1 + (c[2] if not swap else c[3]), 1 + (c[3] if not swap else c[2])
    rows.append(dict(i=D.index.get_loc(i), season=D.loc[i, 'season'], Le=Le, ohe=ohe, oae=oae, Lc=Lc, ohc=ohc, oac=oac,
                     hrs=(tip - e[0]) / 3600, act=float(D.loc[i, 'hs'] - D.loc[i, 'as_'])))
Z = pd.DataFrame(rows)
Z['mu_c'] = [implied_mu(r.Lc, r.ohc, r.oac) for r in Z.itertuples()]
P(f'ματς με εισοδο & κλεισιμο: {len(Z)} · μεση ωρα εισοδου {Z.hrs.mean():.1f}ω πριν · μεση κινηση γραμμης |Lc − Le| {np.mean(np.abs(Z.Lc - Z.Le)):.2f} π.')
P('')
RES = {}
for nm, v in PREDS.items():
    m = v[Z.i.values]; recs = []
    for r, mm in zip(Z.itertuples(), m):
        pw, pp = cover(mm, r.Le); pl = 1 - pw - pp
        eh, ea = pw * r.ohe + pp - 1, pl * r.oae + pp - 1
        side, ed, od = (1, eh, r.ohe) if eh >= ea else (-1, ea, r.oae)
        if ed < 0.08: continue
        cw, cp = cover(r.mu_c, r.Le); cl = 1 - cw - cp
        ev_close = (cw if side == 1 else cl) * od + cp - 1
        move = (r.Lc - r.Le) * (-side)                # + = η γραμμη κινηθηκε υπερ μας (π.χ. πηραμε +6, κλεισε +4)
        v_ = (r.act + r.Le) * side; pnl = (od - 1) if v_ > 0 else (0 if v_ == 0 else -1)
        recs.append(dict(season=r.season, ev=ev_close, move=move, pnl=pnl, edge=ed))
    RES[nm] = pd.DataFrame(recs)
P('=== CLV ανα ρυθμιση (picks edge ≥8% στη γραμμη Crown ~12ω πριν, 2021-2025) ===')
P(f'{"":24s} {"picks":>6s} {"EV στο κλεισιμο":>16s} {"κινηση γραμμης":>15s} {"% θετικο CLV":>13s} | {"ROI (αποτελεσμα)":>17s}')
for nm, R in RES.items():
    P(f'{nm:24s} {len(R):6d} {R.ev.mean()*100:+15.2f}% {R.move.mean():+14.2f}π {np.mean(R.ev > 0)*100:12.0f}% | {R.pnl.mean()*100:+16.1f}%')
P('')
P('ανα σεζον — EV στο κλεισιμο:')
for nm, R in RES.items():
    P(f'  {nm:24s} ' + ' · '.join(f'{s[-2:]}: {R[R.season == s].ev.mean()*100:+.1f}% ({len(R[R.season == s])})' for s in SE5))
P('')
rng = np.random.default_rng(11)
seasons = np.array(SE5)
base = RES['live']
for nm, R in RES.items():
    if nm == 'live': continue
    diffs = []
    for _ in range(2000):
        ss = rng.choice(seasons, len(seasons))           # bootstrap σεζον (συσχετιση μεσα στη σεζον)
        a = pd.concat([R[R.season == s] for s in ss]); b = pd.concat([base[base.season == s] for s in ss])
        diffs.append(a.ev.mean() - b.ev.mean())
    P(f'  πιθανοτητα «{nm}» να εχει μεγαλυτερο EV-στο-κλεισιμο απο το live: {np.mean(np.array(diffs) > 0)*100:.0f}%')
open('el_clv_nowgoal_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
