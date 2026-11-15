# -*- coding: utf-8 -*-
"""el_onoff_hybrid_test.py — ΕΥΡΩΛΙΓΚΑ ΣΥΝΟΛΑ: ΥΒΡΙΔΙΚΟ on/off απουσιων (23/10/2026, εγκριση Στελιου μεσω συντονιστη).
Στησιμο: ιδιο με el_index_build_test.py / el_absence_onoff_test.py W4 (1563 ματς E2021-25, picks συνολων ≥8% στο ανοιγμα Crown,
LOSO bO/bD, ridge 1.0, απουσια/τακτικος/g(k) ιδια με το live). Τιποτα live δεν αλλαζει.
ΑΦΕΤΗΡΙΕΣ:
  R0        = W4 ως εχει (περσινο προφιλ 3StepsBasket, αντιστοιχιση «επωνυμο + αρχικο»). Πρεπει: 511 picks, +59.0μ, RMSE 16.523.
  R0+alias  = R0 + el_onoff_alias.json (ιδια λογικη με el_absence.onoff_of: αν το ονομα box ειναι στο alias και το κλειδι εχει
              περσινο προφιλ → αυτο, αλλιως η κανονικη αντιστοιχιση). Αυτο ειναι πλεον το LIVE.
ΥΒΡΙΔΙΚΟ (πανω σε καθε αφετηρια): για καθε αποντα — αν εχει περσινο προφιλ 3StepsBasket → αυτο (ακριβως οπως η αφετηρια)·
  αν ΔΕΝ εχει → ο δεικτης Σ (O, D) απο el_index_build_test.py, τελευταιο σημειο υπολογισμου ΠΡΙΝ το ματς, μετατρεπομενος στην
  κλιμακα 3StepsBasket: onO^ = aO + cO·O_Σ, onD^ = aD + cD·D_Σ (OLS στους αποντες που εχουν ΚΑΙ τα δυο, ΜΟΝΟ σε σεζον
  εκπαιδευσης LOSO). Χωρις κανενα απο τα δυο → 0. Διαιρεση με την τυπ. αποκλιση της αφετηριας (ιδια z με την αφετηρια).
  Παραμετροι Σ (w_prev ∈ {0.3, 0.6}, λ ∈ {1000, 3000, 8000}) επιλεγονται LOSO με RMSE (κρατημενη σεζον Y: η εκδοχη με το
  μικροτερο RMSE στις αλλες 4, με αντιστοιχιση και bO/bD εκτιμημενα στις αλλες 4).
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ το τρεξιμο):
  το ΥΒΡΙΔΙΚΟ πανω στο R0+alias ΑΝΤΙΚΑΘΙΣΤΑ το live (R0+alias) αν: LOSO RMSE συνολου καλυτερο σε ≥4/5 σεζον
  ΚΑΙ μοναδες picks ≥ R0+alias ΚΑΙ θετικες σεζον ≥4/5.
Εξοδος: el_onoff_hybrid_test_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, json, collections, contextlib, time
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
T0 = time.time()
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open(os.path.join(ROOT, 'el_onoff_hybrid_test_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
# ---- 1. δεικτης Σ (walk-forward) απο el_index_build_test.py, ως εχει ----
src = open('el_index_build_test.py', encoding='utf-8').read().split('# ================= ΣΤΑΘΕΡΟΤΗΤΑ')[0]
r1 = "def save(): open("; r2 = "    for var in XVARS:\n        for k, cp in enumerate(CPS[S]): VAL"
assert src.count(r1) == 1 and src.count(r2) == 1
src = src.replace(r1, "def save(): return; open(").replace(r2, "    for var in CVARS:\n        for k, cp in enumerate(CPS[S]): VAL")
IX = {'__file__': os.path.join(ROOT, 'el_index_build_test.py'), '__name__': 'idx'}
with contextlib.redirect_stdout(_B()): exec(src, IX)
sys.stdout.reconfigure(encoding='utf-8')
VAL, CPS, PIDX, CVARS, IXNAME, GD, BYS, prevS = IX['VAL'], IX['CPS'], IX['PID'], IX['CVARS'], IX['NAME'], IX['GD'], IX['BYS'], IX['prevS']
P(f'δεικτης Σ ετοιμος ({time.time() - T0:.0f} δευτ.) · εκδοχες {CVARS}')
# ---- 2. W4 με/χωρις alias ----
ALIAS = {n: (tuple(v[0]), v[1]) for n, v in json.load(open('el_onoff_alias.json', encoding='utf-8'))['alias'].items()}
base = open('el_absence_onoff_test.py', encoding='utf-8').read().split('# ---- ΧΑΝΤΙΚΑΠ ----')[0]
a1 = "res.append(dict(w=w, **(pr or dict(onO=0.0, onD=0.0, usg=None))))"; a2 = "rows.append(dict(y=sea,"
a3 = "def profile(name, yr):\n    k = key_of(name)\n"
for a in (a1, a2, a3): assert base.count(a) == 1, a
base = base.replace(a1, "res.append(dict(w=w, pid=pid, **(pr or dict(onO=0.0, onD=0.0, usg=None))))").replace(a2, "rows.append(dict(hc=hc, ac=ac, ts=ts, y=sea,")
base = base.replace(a3, a3 + "    _a = ALIAS.get(str(name))\n    if _a is not None and _a in PROF and PROF[_a].get(yr - 1) is not None and PROF[_a][yr - 1][2] > 0: k = _a\n")
RUN = {}
for nm, al in (('R0', {}), ('R0+alias', ALIAS)):
    NS = {'ALIAS': al}
    with contextlib.redirect_stdout(_B()): exec(base, NS)
    sys.stdout.reconfigure(encoding='utf-8')
    RUN[nm] = NS
    P(f'{nm}: εκτελεστηκε ({time.time() - T0:.0f} δευτ.)')
N0 = RUN['R0']; rows, SE, ys, YT, YH, YA = N0['rows'], N0['SE'], N0['ys'], N0['YT'], N0['YH'], N0['YA']
rmse, tp, ALL = N0['rmse'], N0['tp'], N0['ALL']
assert len(RUN['R0+alias']['rows']) == len(rows) and all(a['ts'] == b['ts'] and a['hc'] == b['hc'] for a, b in zip(rows, RUN['R0+alias']['rows']))
h0 = N0['HELD']['W4 μονο on/off']; u_chk, s_chk = N0['tpicks'](h0)
P(''); P(f'ΑΝΑΠΑΡΑΓΩΓΗ R0: ματς {len(rows)} · RMSE {rmse(YT - h0, ALL):.3f} · {s_chk.strip()}')
if not (len(rows) == 1563 and abs(rmse(YT - h0, ALL) - 16.523) < 0.0006 and abs(u_chk - 59.0) < 0.06 and s_chk.strip().startswith('511 picks')):
    P('!!! ΔΕΝ αναπαραγεται το R0 — STOP'); save(); sys.exit(1)
P('  ✓ αναπαραγεται')
PLD = json.load(open('el_players.json', encoding='utf-8'))
PLIDX = collections.defaultdict(list)
for k, g in PLD.items(): PLIDX[(g['season'], g['hcode'], g['acode'])].append((pd.Timestamp(g['utc']).tz_localize(None).timestamp(), g['code'], g.get('rnd')))
for r in rows:
    c = [x for x in PLIDX[(r['y'], r['hc'], r['ac'])] if abs(x[0] - r['ts']) < 86400]
    r['code'], r['rnd'] = (c[0][1], c[0][2]) if c else (None, None)
def cp_of(S, ts): return max([i for i, c in enumerate(CPS[S]) if c <= ts], default=0)
def sig(var, r, p): return VAL[(var, r['y'], cp_of(r['y'], r['ts']))].get(PIDX.get(p['pid'], -1))
# ---- 3. χαρακτηριστικα ----
def feats_base(B):
    XH, XA = RUN[B]['XH'][:, [2, 3]], RUN[B]['XA'][:, [2, 3]]; return XH, XA
def mapfit(B, var, tr_seasons):
    o, so, d, sd = [], [], [], []
    for r, rb in zip(rows, RUN[B]['rows']):
        if r['y'] not in tr_seasons: continue
        for p in rb['ah'] + rb['aa']:
            if p['usg'] is None: continue
            v = sig(var, r, p)
            if v is None: continue
            o.append(p['onO']); so.append(v[0]); d.append(p['onD']); sd.append(v[1])
    cO = np.polyfit(so, o, 1); cD = np.polyfit(sd, d, 1)
    return dict(cO=cO, cD=cD, n=len(o), rO=np.corrcoef(so, o)[0, 1], rD=np.corrcoef(sd, d)[0, 1])
def feats_hyb(B, var, mp):
    SDb = RUN[B]['SD']; XH = np.zeros((len(rows), 2)); XA = np.zeros((len(rows), 2))
    def val(r, p):
        if p['usg'] is not None: return p['onO'], p['onD']
        v = sig(var, r, p)
        if v is None: return 0.0, 0.0
        return float(np.polyval(mp['cO'], v[0])), float(np.polyval(mp['cD'], v[1]))
    for i, (r, rb) in enumerate(zip(rows, RUN[B]['rows'])):
        def side(own, opp):
            return sum(p['w'] * val(r, p)[0] / SDb['onO'] for p in own), sum(p['w'] * val(r, p)[1] / SDb['onD'] for p in opp)
        XH[i] = side(rb['ah'], rb['aa']); XA[i] = side(rb['aa'], rb['ah'])
    return XH, XA
def fit2(XH, XA, tr):
    X = np.r_[XH[tr], XA[tr]]; y = np.r_[YH[tr], YA[tr]]
    return np.linalg.solve(X.T @ X + 1.0 * np.eye(2), X.T @ y)
# ---- 4. LOSO ----
HELD, BCOEF, CHOICE, MAPS = {}, {}, {}, {}
for B in ('R0', 'R0+alias'):
    XH, XA = feats_base(B); h = np.zeros(len(rows))
    for Y in SE:
        b = fit2(XH, XA, ys != Y); m = ys == Y; h[m] = XH[m] @ b + XA[m] @ b; BCOEF[(B, Y)] = b
    HELD[B] = h
    hy = {var: np.zeros(len(rows)) for var in CVARS}; trr = {}
    for Y in SE:
        tr_s = [s for s in SE if s != Y]
        for var in CVARS:
            mp = mapfit(B, var, tr_s); MAPS[(B, var, Y)] = mp
            XH, XA = feats_hyb(B, var, mp); b = fit2(XH, XA, ys != Y); m = ys == Y
            hy[var][m] = XH[m] @ b + XA[m] @ b; trr[(var, Y)] = rmse(YT - (XH @ b + XA @ b), ys != Y); BCOEF[(f'Υ[{B}] {var}', Y)] = b
        best = min(CVARS, key=lambda v: trr[(v, Y)]); CHOICE[(B, Y)] = best
    hs = np.zeros(len(rows))
    for Y in SE: hs[ys == Y] = hy[CHOICE[(B, Y)]][ys == Y]
    HELD[f'ΥΒΡΙΔΙΚΟ[{B}] LOSO'] = hs
    for var in CVARS: HELD[f'Υ[{B}] {var}'] = hy[var]
    P(f'  LOSO {B} ετοιμο ({time.time() - T0:.0f} δευτ.)')
assert abs(N0['tpicks'](HELD['R0'])[0] - 59.0) < 0.06
# ---- 5. picks ----
def picks_df(adj):
    L = []
    for r, a in zip(rows, adj):
        o = r['op']; T_, oo, ou = o[2], o[3], o[4]; po, pp, pu = tp(r['T'] + a, T_); eo, eu = po * oo + pp - 1, pu * ou + pp - 1
        sd, e, od = (1, eo, oo) if eo >= eu else (-1, eu, ou)
        act = r['hs'] + r['as_']; side = None; u = np.nan; clv = np.nan
        if e >= .08:
            x = (act - T_) * sd; u = (od - 1) if x > 0 else (0 if x == 0 else -1); side = 'over' if sd == 1 else 'under'; clv = (r['cl'][1] - o[1]) * sd
        L.append(dict(season=r['y'], rnd=r['rnd'], pick=side, units=u, clv=clv, adj=a))
    return pd.DataFrame(L)
ORDER = ['χωρις διορθωση', 'R0', 'R0+alias', 'ΥΒΡΙΔΙΚΟ[R0] LOSO', 'ΥΒΡΙΔΙΚΟ[R0+alias] LOSO'] + [f'Υ[R0+alias] {v}' for v in CVARS]
HELD['χωρις διορθωση'] = np.zeros(len(rows))
DF = {nm: picks_df(HELD[nm]) for nm in ORDER}
def summ(df):
    q = df[df.pick.notna()]; U = {s: q[q.season == s].units for s in SE}
    return len(q), q.units.sum(), q.units.mean() * 100, sum(1 for s in SE if len(U[s]) and U[s].mean() > 0), {s: U[s].sum() for s in SE}, q.clv.mean()
# ================= ΠΙΝΑΚΕΣ =================
P(''); P('## ΚΑΛΥΨΗ ΑΠΟΝΤΩΝ (παικτης-ματς απουσιων) — ποσοι εχουν προφιλ 3StepsBasket, ποσους συμπληρωνει το Σ, συνολικη καλυψη')
P(f'  {"σεζον":6s} {"αποντες":>7s} · R0: 3Steps · +Σ · καλυψη · R0+alias: 3Steps · +Σ · καλυψη  (Σ = w0.6 λ3000· ιδια καλυψη σε ολες τις εκδοχες Σ)')
tot = collections.Counter()
for s in SE + ['ολα']:
    c = collections.Counter()
    for r, ra in zip(rows, RUN['R0+alias']['rows']):
        if s != 'ολα' and r['y'] != s: continue
        rb = r
        for p0, pa in zip(rb['ah'] + rb['aa'], ra['ah'] + ra['aa']):
            c['n'] += 1; sg = sig('Σ w0.6 λ3000', r, p0) is not None
            c['b0'] += p0['usg'] is not None; c['s0'] += (p0['usg'] is None) and sg
            c['ba'] += pa['usg'] is not None; c['sa'] += (pa['usg'] is None) and sg
    P(f'  {s:6s} {c["n"]:7d} · {c["b0"]:5d} ({c["b0"] / c["n"]:.0%}) · +{c["s0"]:4d} · {(c["b0"] + c["s0"]) / c["n"]:.0%} · '
      f'{c["ba"]:5d} ({c["ba"] / c["n"]:.0%}) · +{c["sa"]:4d} · {(c["ba"] + c["sa"]) / c["n"]:.0%}')
nal = sum(1 for r, ra in zip(rows, RUN['R0+alias']['rows']) for p0, pa in zip(r['ah'] + r['aa'], ra['ah'] + ra['aa']) if p0['usg'] is None and pa['usg'] is not None)
alp = collections.Counter(IXNAME.get(p0['pid'], p0['pid']) for r, ra in zip(rows, RUN['R0+alias']['rows']) for p0, pa in zip(r['ah'] + r['aa'], ra['ah'] + ra['aa']) if p0['usg'] is None and pa['usg'] is not None)
P(f'  το alias προσθετει {nal} απουσιες με προφιλ: ' + ' · '.join(f'{k} {v}' for k, v in alp.most_common()))
P(f'  τυπ. αποκλιση αφετηριας (ποντοι/100 κατοχες): R0 onO {RUN["R0"]["SD"]["onO"]:.2f} / onD {RUN["R0"]["SD"]["onD"]:.2f} · R0+alias onO {RUN["R0+alias"]["SD"]["onO"]:.2f} / onD {RUN["R0+alias"]["SD"]["onD"]:.2f}')
P(''); P('## ΑΝΤΙΣΤΟΙΧΙΣΗ Σ → κλιμακα 3StepsBasket (R0+alias, εκτιμηση σε ολες τις σεζον — μονο για προβολη· στο LOSO εκτιμαται χωρις τη σεζον-τεστ)')
for var in CVARS:
    mp = mapfit('R0+alias', var, SE)
    P(f'  {var:14s} n {mp["n"]} · onO = {mp["cO"][1]:+.2f} + {mp["cO"][0]:.2f}·O_Σ (r {mp["rO"]:+.2f}) · onD = {mp["cD"][1]:+.2f} + {mp["cD"][0]:.2f}·D_Σ (r {mp["rD"]:+.2f})')
P('  LOSO επιλογη Σ ανα κρατημενη σεζον: ' + ' · '.join(f'{B}: ' + ' '.join(f'{Y[-2:]}:{CHOICE[(B, Y)][2:]}' for Y in SE) for B in ('R0', 'R0+alias')))
P(''); P('## RMSE συνολου (LOSO, ποντοι συνολου ματς) · ΔRMSE vs R0+alias (− = καλυτερο απο το live)')
ref = 'R0+alias'
for nm in ORDER:
    h = HELD[nm]; rr = [rmse(YT - h, ys == s) for s in SE]; d = [rmse(YT - h, ys == s) - rmse(YT - HELD[ref], ys == s) for s in SE]
    P(f'  {nm:26s} RMSE {rmse(YT - h, ALL):.3f} · ανα σεζον ' + ' '.join(f'{x:.3f}' for x in rr) + ' · Δ ' + ' '.join(f'{x:+.3f}' for x in d) + f' · καλυτερο {sum(x < 0 for x in d)}/5')
P(''); P('## ΣΥΝΤΕΛΕΣΤΕΣ bO (δικοι αποντες × z(onO)) / bD (αντιπ. αποντες × z(onD)) — ποντοι ομαδας ανα 40′ απουσιας ανα 1 τυπ. αποκλιση · LOSO (εκπαιδευση χωρις τη σεζον) · αναμενομενα < 0')
for nm in ['R0', 'R0+alias'] + [f'Υ[R0+alias] {v}' for v in CVARS]:
    bs = {Y: BCOEF[(nm, Y)] for Y in SE}
    P(f'  {nm:26s} bO ' + ' '.join(f'{Y[-2:]}:{bs[Y][0]:+.2f}' for Y in SE) + f' (<0 {sum(bs[Y][0] < 0 for Y in SE)}/5) · bD ' + ' '.join(f'{Y[-2:]}:{bs[Y][1]:+.2f}' for Y in SE) + f' (<0 {sum(bs[Y][1] < 0 for Y in SE)}/5)')
P(''); P('## PICKS συνολων ≥8% στο ανοιγμα (Crown) — n · μοναδες · ROI · θετικες σεζον · ανα σεζον · CLV (ποντοι γραμμης προς εμας)')
for nm in ORDER:
    n, u, roi, pos, us, clv = summ(DF[nm])
    P(f'  {nm:26s} {n:4d} picks · {u:+6.1f}μ · ROI {roi:+5.1f}% · θετ {pos}/5 · ' + ' '.join(f'{s[-2:]}:{us[s]:+.1f}' for s in SE) + f' · CLV {clv:+.2f}')
P(''); P('## OVER / UNDER (n · μοναδες · ROI)')
for nm in ORDER:
    q = DF[nm]; q = q[q.pick.notna()]
    P(f'  {nm:26s} ' + ' · '.join(f'{sd}: {len(q[q.pick == sd]):3d} · {q[q.pick == sd].units.sum():+6.1f}μ · ROI {q[q.pick == sd].units.mean() * 100:+5.1f}%' for sd in ('over', 'under')))
P(''); P('## ΑΓΩΝΙΣΤΙΚΕΣ 1-10 vs 11+ (n · μοναδες · ROI)')
for nm in ORDER:
    q = DF[nm]; q = q[q.pick.notna()]; e = q[q.rnd.fillna(99) <= 10]; l = q[q.rnd.fillna(99) > 10]
    P(f'  {nm:26s} 1-10: {len(e):3d} · {e.units.sum():+6.1f}μ · ROI {e.units.mean() * 100:+5.1f}% · 11+: {len(l):3d} · {l.units.sum():+6.1f}μ · ROI {l.units.mean() * 100:+5.1f}%')
P(''); P('################ ΑΠΟΦΑΣΗ (προ-δηλωμενο κριτηριο) ################')
hn = 'ΥΒΡΙΔΙΚΟ[R0+alias] LOSO'
d = [rmse(YT - HELD[hn], ys == s) - rmse(YT - HELD[ref], ys == s) for s in SE]; n, u, roi, pos, us, clv = summ(DF[hn]); u0 = summ(DF[ref])[1]
ok = sum(x < 0 for x in d) >= 4 and u >= u0 and pos >= 4
P(f'  {hn}: RMSE καλυτερο σε {sum(x < 0 for x in d)}/5 · μοναδες {u:+.1f} vs R0+alias {u0:+.1f} · θετικες {pos}/5 → ' + ('ΚΡΙΤΗΡΙΟ ΑΝΤΙΚΑΤΑΣΤΑΣΗΣ ΠΛΗΡΟΥΤΑΙ' if ok else 'ΚΡΙΤΗΡΙΟ ΑΝΤΙΚΑΤΑΣΤΑΣΗΣ ΔΕΝ ΠΛΗΡΟΥΤΑΙ'))
save()
# ================= ΠΑΡΑΔΕΙΓΜΑΤΑ =================
P(''); P('################ ΕΛΕΓΧΟΣ — 3 αποντες που συμπληρωνει το Σ (R0+alias, 2025-26, εκδοχη LOSO της σεζον) ################')
B = 'R0+alias'; Y = 'E2025'; var = CHOICE[(B, Y)]; mp = MAPS[(B, var, Y)]; b = BCOEF[(f'Υ[{B}] {var}', Y)]; SDb = RUN[B]['SD']
cand = []
for i, (r, rb) in enumerate(zip(rows, RUN[B]['rows'])):
    if r['y'] != Y: continue
    for side, L in (('γηπ', rb['ah']), ('φιλ', rb['aa'])):
        for p in L:
            if p['usg'] is not None: continue
            v = sig(var, r, p)
            if v is None: continue
            mO, mD = float(np.polyval(mp['cO'], v[0])), float(np.polyval(mp['cD'], v[1]))
            eff = p['w'] * (b[0] * mO / SDb['onO'] + b[1] * mD / SDb['onD'])
            cand.append((abs(eff), i, side, p, v, mO, mD, eff))
cand.sort(key=lambda x: -x[0]); seen = set(); shown = 0
gid_of = IX['PID']
def origin(pid, season):
    g = gid_of.get(pid)
    pv = prevS.get(season)
    tm_prev = {GD[k]['ps'][g][1] for k in BYS.get(pv, []) if g is not None and g in GD[k]['ps']}
    n_cur = None
    return (f'περσι στην Ευρωλιγκα με {"/".join(sorted(tm_prev))}' if tm_prev else 'ΚΑΙΝΟΥΡΓΙΟΣ στην Ευρωλιγκα (περσι εκτος EL ή χωρις 3Steps)')
for ab, i, side, p, v, mO, mD, eff in cand:
    if p['pid'] in seen: continue
    seen.add(p['pid']); r = rows[i]
    ncur = sum(1 for k in BYS[Y] if GD[k]['ts'] is not None and GD[k]['ts'] < IX['CPS'][Y][cp_of(Y, r['ts'])] and gid_of.get(p['pid']) in GD[k]['ps'])
    P(f'  {IXNAME.get(p["pid"], p["pid"])} — απων ({side}) {r["hc"]}-{r["ac"]} {pd.Timestamp(r["ts"], unit="s"):%Y-%m-%d} αγων. {r["rnd"]} · βαρος w {p["w"]:.2f}')
    P(f'    απο πού: {origin(p["pid"], Y)} · φετινα ματς EL στα δεδομενα του Σ: {ncur} · 3StepsBasket περσινο προφιλ: ΟΧΙ')
    P(f'    Σ ({var}): O {v[0]:+.2f} · D {v[1]:+.2f} → κλιμακα 3Steps: onO {mO:+.2f} · onD {mD:+.2f} → z {mO / SDb["onO"]:+.2f} / {mD / SDb["onD"]:+.2f}')
    P(f'    επιδραση στο συνολο (LOSO b {Y[-2:]}: bO {b[0]:+.2f}, bD {b[1]:+.2f}): {eff:+.2f} ποντοι · διορθωση ματς: live {HELD[ref][i]:+.2f} → υβριδικο {HELD[hn][i]:+.2f} '
      f'· γραμμη {r["op"][2]} · μοντελο {r["T"]:.1f} · πραγματικο {r["hs"] + r["as_"]:.0f} · pick live {DF[ref].pick[i]} / υβριδικο {DF[hn].pick[i]}')
    shown += 1
    if shown >= 3: break
P(''); P(f'χρονος {time.time() - T0:.0f} δευτ.')
save()
