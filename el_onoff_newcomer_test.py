# -*- coding: utf-8 -*-
"""el_onoff_newcomer_test.py — EUROLEAGUE ΣΥΝΟΛΑ: τιμη on/off για απουσες ΧΩΡΙΣ περσινο προφιλ (23/10/2026, Στελιος «τεσταρε τελευταια
διαθεσιμα δεδομενα απο προηγουμενες σεζον, φετινα μονο για αυτους, μια μιξη των 2» — ορισμος εγκριθηκε «ναι»).
Βαση: el_onoff_mix_test.py / W4 (ιδιος ορισμος απουσιας, w, τυπος [δικα×z(onO), αντιπ.×z(onD)], ridge 1, LOSO E2021-25, picks ≥8% ανοιγμα).
Για απουσες ΜΕ περσινο προφιλ 3StepsBasket: ΤΙΠΟΤΑ δεν αλλαζει (ιδια τιμη A0, ιδια κλιμακα z = SD του A0). Αλλαζουν ΜΟΝΟ οσοι σημερα = 0:
  N0 = live (0) · N1 = πιο προσφατη ΠΑΛΙΟΤΕΡΗ σεζον EL/EuroCup στο 3StepsBasket (πριν την περσινη· ιδιος υπολογισμος με το live)
  N2 = μονο φετινα: on/off απο πενταδες (el_pbp_stints, EL) ως 1ω πριν το ματς · N3 = N1 + N2 μαζι, βαρος κατοχες (n), μαζεμα στο συνολο.
  Μαζεμα παντου × n/(n+1500).
ΠΡΟ-ΔΗΛΩΜΕΝΑ: περνα αν RMSE συνολου καλυτερο απο N0 ≥4/5 σεζον ΚΑΙ μοναδες ≥ N0 ΚΑΙ θετικες σεζον ≥4/5.
Εξοδος: el_onoff_newcomer_test_out.txt"""
import sys, io, contextlib, collections, math
import numpy as np, pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
M = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_onoff_mix_test.py', encoding='utf-8').read().split("VARS = {")[0], M)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
G = M['G']; rows, segs, NAME, PTEAMS, SE, Phi, K_SHR = M['rows'], M['segs'], M['NAME'], M['PTEAMS'], M['SE'], M['Phi'], 1500.0
PROF, BYSUR, key_of, tok, S3 = G['PROF'], G['BYSUR'], G['key_of'], G['tok'], G['S3']
# ---- ωμα (μη μαζεμενα) τμηματα 3StepsBasket ανα παικτη-ετος: [(diffO, diffD, n)] — για τη μιξη N3 ----
RAW = collections.defaultdict(lambda: collections.defaultdict(list))
for cid, d in S3.items():
    yr = int(cid.split('-')[1]) - 1
    TT = {t['clubId']: t for t in d.get('teams', [])}
    for club, ps in (d.get('players') or {}).items():
        t = TT.get(club)
        if not t or not ps: continue
        pf = 2 * t['madeTwo'] + 3 * t['madeThree'] + t['madeFt']; pa = 2 * t['oppMadeTwo'] + 3 * t['oppMadeThree'] + t['oppMadeFt']
        op, dp = t['offPossessions'], t['defPossessions']; tg = t.get('games') or 1
        for p in ps.get('players') or []:
            g = p.get('gamesPlayed') or 0
            if g <= 0 or not p.get('teamPossessionsNet'): continue
            sc = tg / max(g, tg)
            ton, tpo = p['teamPoints'] * g * sc, p['teamPossessionsNet'] * g * sc
            oon, opo = p['oppPoints'] * g * sc, p['oppPossessionsNet'] * g * sc
            if op - tpo < 50 or dp - opo < 50 or tpo < 50: continue
            onO = 100 * ton / tpo - 100 * (pf - ton) / (op - tpo); onD = 100 * oon / opo - 100 * (pa - oon) / (dp - opo)
            n = 1 / (1 / tpo + 1 / (op - tpo))
            RAW[(tuple(tok(p.get('surname'))), (tok(p.get('firstname')) or [''])[0])][yr].append((onO, onD, n))
def pkey(name):
    k = key_of(name)
    if k in PROF: return k
    c = [x for x in BYSUR.get(k[0], []) if x[1][:1] == k[1][:1]]
    return c[0] if len(c) == 1 else None
def older(name, yr):
    """πιο προσφατο ετος < yr-1 με προφιλ → (ετος, μαζεμενη τιμη οπως το live, ωμα τμηματα)"""
    k = pkey(name)
    if k is None: return None
    ys_ = [y for y, v in PROF[k].items() if y < yr - 1 and v[2] > 0]
    if not ys_: return None
    y = max(ys_); v = PROF[k][y]
    return y, (v[0] / v[2], v[1] / v[2]), RAW[k].get(y, [])
def shrunk(L):
    N = sum(x[2] for x in L)
    if N <= 0: return (0.0, 0.0), False
    sh = N / (N + K_SHR); return (sh * sum(a * n for a, _, n in L) / N, sh * sum(b * n for _, b, n in L) / N), True
VN = ['N0', 'N1', 'N2', 'N3']
for r in rows:
    for p in r['ah'] + r['aa']:
        if p['A0has']: p['V'] = {nm: (p['A0'], True) for nm in VN}; p['new'] = False; continue
        yr = int(p['sea'][1:]); o = older(NAME[p['pid']], yr); cur = segs(p['pid'], p['sea'], p['ts'] - 3600)
        p['old_yr'] = o[0] if o else None; p['new'] = True
        p['V'] = {'N0': ((0.0, 0.0), False), 'N1': ((o[1], True) if o else ((0.0, 0.0), False)),
                  'N2': shrunk(cur), 'N3': shrunk((o[2] if o else []) + cur)}
allp = [p for r in rows for p in r['ah'] + r['aa']]
hasA0 = [p['A0'] for p in allp if p['A0has'] and p['A0'] != (0.0, 0.0)]
SD = (np.std([x[0] for x in hasA0]), np.std([x[1] for x in hasA0]))
newp = [p for p in allp if p['new']]
P(f'Ευρωλιγκα 2021-25: ματς {len(rows)} · απουσιες-ματς {len(allp)} · ΧΩΡΙΣ περσινο προφιλ {len(newp)} ({len(newp) / len(allp):.0%})')
P(f'κλιμακα z (SD του live A0, ιδια για ολες): onO {SD[0]:.2f} · onD {SD[1]:.2f} ποντοι/100 κατοχες')
P(''); P('## ΚΑΛΥΨΗ: απουσες χωρις περσινο προφιλ που παιρνουν τιμη ≠0 (απουσιες-ματς)')
for nm in VN[1:]:
    c = [p for p in newp if p['V'][nm][1] and p['V'][nm][0] != (0.0, 0.0)]
    P(f'  {nm}: {len(c):4d} απο {len(newp)} ({len(c) / len(newp):.0%}) · μεσο |onO| {np.mean([abs(p["V"][nm][0][0]) for p in c]):.2f} · '
      f'|onD| {np.mean([abs(p["V"][nm][0][1]) for p in c]):.2f} (ποντοι/100 κατ. μετα το μαζεμα)' if c else f'  {nm}: 0')
ago = collections.Counter(int(p['sea'][1:]) - p['old_yr'] for p in newp if p.get('old_yr') is not None)
P('  N1: ποσα χρονια πισω η παλιοτερη σεζον: ' + ' · '.join(f'{k} χρον.: {v}' for k, v in sorted(ago.items())))
YH = np.array([r['hs'] - (r['T'] + r['M']) / 2 for r in rows]); YA = np.array([r['as_'] - (r['T'] - r['M']) / 2 for r in rows]); YT = YH + YA
ys = np.array([r['y'] for r in rows]); ALL = np.ones(len(rows), bool)
def feats(nm):
    f = lambda own, opp: [sum(p['w'] * p['V'][nm][0][0] / SD[0] for p in own), sum(p['w'] * p['V'][nm][0][1] / SD[1] for p in opp)]
    return np.array([f(r['ah'], r['aa']) for r in rows]), np.array([f(r['aa'], r['ah']) for r in rows])
X = {nm: feats(nm) for nm in VN}
def fit(nm, tr):
    XH, XA = X[nm]; Xm = np.r_[XH[tr], XA[tr]]; y = np.r_[YH[tr], YA[tr]]
    return np.linalg.solve(Xm.T @ Xm + 1.0 * np.eye(2), Xm.T @ y)
def adj(nm, b, m): XH, XA = X[nm]; return XH[m] @ b + XA[m] @ b
def rmse(v, m): return float(np.sqrt(np.mean(v[m] ** 2)))
HELD, COEF = {}, {}
for nm in VN:
    h = np.zeros(len(rows))
    for Yr in SE: m = ys == Yr; h[m] = adj(nm, fit(nm, ~m), m)
    HELD[nm] = h; COEF[nm] = fit(nm, ALL)
P(''); P('## ΣΥΝΤΕΛΕΣΤΕΣ (ολες οι σεζον): bO δικα×z(onO) · bD αντιπ.×z(onD) — ποντοι ομαδας ανα 40′ απουσιας ανα 1 SD')
for nm in VN: P(f'  {nm}: bO {COEF[nm][0]:+.2f} · bD {COEF[nm][1]:+.2f}')
chg = {nm: np.abs(HELD[nm] - HELD['N0']) > 1e-9 for nm in VN}
P(''); P(f'## LOSO RMSE συνολου (ποντοι, μικροτερο = καλυτερο) · ΔRMSE vs N0 ανα σεζον (− = καλυτερο)')
P('  εκδοχη | RMSE ολα | ' + ' | '.join(f'{s} (Δ)' for s in SE) + ' | καλυτερο απο N0')
BETTER = {}
for nm in VN:
    d = [rmse(YT - HELD[nm], ys == s) - rmse(YT - HELD['N0'], ys == s) for s in SE]; BETTER[nm] = sum(x < 0 for x in d)
    P(f'  {nm}     | {rmse(YT - HELD[nm], ALL):.4f}  | ' + ' | '.join(f'{rmse(YT - HELD[nm], ys == s):.3f} ({x:+.4f})' for s, x in zip(SE, d))
      + f' | {BETTER[nm]}/5')
def tp(t, T_):
    if abs(T_ - round(T_)) < 1e-9: po = 1 - Phi((T_ + .5 - t) / 16.7); pu = Phi((T_ - .5 - t) / 16.7); return po, 1 - po - pu, pu
    po = 1 - Phi((T_ - t) / 16.7); return po, 0.0, 1 - po
def picks_df(a):
    R = []
    for r, x_ in zip(rows, a):
        o = r['op']; T_, oo, ou = o[2], o[3], o[4]; po, pp, pu = tp(r['T'] + x_, T_); eo, eu = po * oo + pp - 1, pu * ou + pp - 1
        sd, e, od = (1, eo, oo) if eo >= eu else (-1, eu, ou)
        pk = e >= .08; x = (r['hs'] + r['as_'] - T_) * sd
        R.append(dict(season=r['y'], pick=('over' if sd == 1 else 'under') if pk else None,
                      units=(((od - 1) if x > 0 else (0 if x == 0 else -1)) if pk else 0.0)))
    return pd.DataFrame(R)
DF = {nm: picks_df(HELD[nm]) for nm in VN}
P(''); P('## PICKS ΣΥΝΟΛΩΝ ≥8% στο ανοιγμα (1 μοναδα/pick)')
P('  εκδοχη | picks | μοναδες | ROI    | θετ. σεζον | ' + ' | '.join(f'{s} n/μ' for s in SE))
RES = {}
for nm in VN:
    q = DF[nm][DF[nm].pick.notna()]; U_ = {s: q[q.season == s].units for s in SE}; pos = sum(1 for s in SE if len(U_[s]) and U_[s].mean() > 0)
    RES[nm] = (len(q), q.units.sum(), pos)
    P(f'  {nm}     | {len(q):5d} | {q.units.sum():+7.1f} | {q.units.mean() * 100:+5.1f}% | {pos}/5        | '
      + ' | '.join(f'{len(U_[s])}/{U_[s].sum():+.1f}' for s in SE))
n0, u0, _ = RES['N0']
if not (n0 == 511 and abs(u0 - 59.0) < 0.05):
    P(f'!!! N0 ΔΕΝ αναπαραγει το live W4 (511 / +59.0): {n0} / {u0:+.1f} — STOP'); open('el_onoff_newcomer_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out)); sys.exit(1)
P('  (N0 αναπαραγει το live W4: 511 picks / +59.0μ ✓)')
P(''); P('## ΖΕΥΓΑΡΩΤΗ ΔΙΑΦΟΡΑ vs N0 (ολα τα ματς): μοναδες ± τυπ. σφαλμα · ματς με αλλο pick · ΔMSE (ποντοι²) ± τυπ. σφαλμα')
e0 = (YT - HELD['N0']) ** 2
for nm in VN[1:]:
    du = DF[nm].units.values - DF['N0'].units.values; de = (YT - HELD[nm]) ** 2 - e0
    P(f'  {nm}: Δμοναδες {du.sum():+6.1f} ± {du.std(ddof=1) * math.sqrt(len(du)):.1f} · ματς με αλλο pick '
      f'{int((DF[nm].pick.fillna("-") != DF["N0"].pick.fillna("-")).sum())} · ΔMSE {de.mean():+.3f} ± {de.std(ddof=1) / math.sqrt(len(de)):.3f}'
      f' · ματς που αλλαξε η προβλεψη {int(chg[nm].sum())} (εκει: RMSE N0 {rmse(YT - HELD["N0"], chg[nm]):.3f} → {rmse(YT - HELD[nm], chg[nm]):.3f})')
P(''); P('## ΚΡΙΤΗΡΙΑ (προ-δηλωμενα): RMSE καλυτερο απο N0 ≥4/5 · μοναδες ≥ N0 · θετικες σεζον ≥4/5')
for nm in VN[1:]:
    n, u, pos = RES[nm]; c1, c2, c3 = BETTER[nm] >= 4, u >= u0, pos >= 4
    P(f'  {nm}: RMSE {BETTER[nm]}/5 {"✓" if c1 else "✗"} · μοναδες {u:+.1f} vs {u0:+.1f} {"✓" if c2 else "✗"} · θετικες {pos}/5 {"✓" if c3 else "✗"} → '
      + ('ΠΕΡΝΑ' if c1 and c2 and c3 else 'ΔΕΝ περνα'))
P(''); P('## ΠΑΡΑΔΕΙΓΜΑΤΑ (onO/onD ποντοι/100 κατ. μετα το μαζεμα · επιδραση = ποντοι στο συνολο του ματς με τους συντελεστες ολων των σεζον)')
def effect(p, nm): b = COEF[nm]; v = p['V'][nm][0]; return p['w'] * (b[0] * v[0] / SD[0] + b[1] * v[1] / SD[1])
cand = [(p, r) for r in rows for p in r['ah'] + r['aa'] if p['new'] and p['w'] >= .5 and r['y'] in ('E2023', 'E2024', 'E2025')]
ex1 = max([c for c in cand if c[0].get('old_yr') is not None], key=lambda c: c[0]['w'] + abs(effect(c[0], 'N3')), default=None)
ex2 = max([c for c in cand if c[0].get('old_yr') is None and c[0]['V']['N2'][1]], key=lambda c: c[0]['w'] + abs(effect(c[0], 'N2')), default=None)
for lab, c in (('επεστρεψε στην Ευρωπη (εχει παλιοτερη σεζον)', ex1), ('νεος (ποτε EL/EC)', ex2)):
    if c is None: continue
    p, r = c
    P(f'  [{lab}] {NAME.get(p["pid"])} ({p["team"]}) · {r["y"]} {r["hc"]}-{r["ac"]} {r["t"]:%Y-%m-%d} (αγων. {r["phase"]} {r["rnd"]}) · w {p["w"]:.2f}'
      f' · παλιοτερη σεζον 3Steps: {p["old_yr"] if p.get("old_yr") is not None else "—"}')
    for nm in VN:
        v = p['V'][nm][0]; P(f'      {nm}: onO {v[0]:+6.2f} · onD {v[1]:+6.2f} · επιδραση στο συνολο {effect(p, nm):+5.2f} ποντοι')
    cs = segs(p['pid'], p['sea'], p['ts'] - 3600)
    P('      φετινα ως το ματς: ' + ('; '.join(f'diffO {a:+.1f} diffD {b:+.1f} n {n:.0f}' for a, b, n in cs) or '—'))
open('el_onoff_newcomer_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
