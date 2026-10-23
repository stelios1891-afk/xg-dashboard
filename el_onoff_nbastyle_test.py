# -*- coding: utf-8 -*-
"""el_onoff_nbastyle_test.py — ΕΥΡΩΛΙΓΚΑ ΣΥΝΟΛΑ: ΜΙΞΗ «τυπου NBA» περσινης βασης + φετινου δεικτη (23/10/2026, εγκριση Στελιου μεσω συντονιστη).
Στησιμο: ιδιο με el_absence_onoff_test.py W4 / el_onoff_hybrid_test.py (1563 ματς E2021-25, picks συνολων ≥8% στο ανοιγμα Crown,
LOSO bO/bD με ridge 1.0, απουσια/τακτικος/g(k) ιδια με το live). Τιποτα live δεν αλλαζει.
LIVE = R0+alias: περσινο προφιλ 3StepsBasket με el_onoff_alias.json (ιδια λογικη με el_absence.onoff_of). Πρεπει: 516 picks, +55.9μ.
ΜΙΞΗ για καθε αποντα, την ημερα του ματς, χωριστα για O (onO) και D (onD):
  τιμη = (n·Σφ + K·βαση) / (n + K)
  βαση = περσινο προφιλ 3StepsBasket με alias (χωρις προφιλ → 0)
  Σφ   = δεικτης Σ ΜΟΝΟ με ΦΕΤΙΝΑ ματς πριν το σημειο υπολογισμου (box-prior RAPM, w_prev = 0, box συντελεστες C_S απο σεζον < S),
         σε κλιμακα 3Steps με γραμμικη αντιστοιχιση onO = a + c·O_Σφ (OLS στους αποντες με βαση ΚΑΙ Σφ, ΜΟΝΟ σεζον εκπαιδευσης LOSO)
  n    = ΦΕΤΙΝΕΣ ΚΑΤΟΧΕΣ του παικτη μεσα στο γηπεδο (μεσος δικων/αντιπαλου) ως το σημειο υπολογισμου (0 στην αρχη → τιμη = βαση)
  K ∈ {500, 1000, 2000, 4000} κατοχες · λ του Σφ ∈ {1000, 3000, 8000} → 12 εκδοχες· επιλογη LOSO με RMSE (κρατημενη σεζον Y:
  η εκδοχη με το μικροτερο RMSE στις αλλες 4, με αντιστοιχιση και bO/bD απο τις αλλες 4). Διαιρεση με την τυπ. αποκλιση της βασης.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ το τρεξιμο): η ΜΙΞΗ (LOSO) ΑΝΤΙΚΑΘΙΣΤΑ το live αν LOSO RMSE συνολου καλυτερο απο το live
  σε ≥4/5 σεζον ΚΑΙ μοναδες ≥ live ΚΑΙ θετικες σεζον ≥4/5.
ΠΕΡΙΓΡΑΦΙΚΑ: αποντες που ΑΛΛΑΞΑΝ ΟΜΑΔΑ απο περσι (εχουν βαση και η φετινη ομαδα ≠ περσινη ομαδα Ευρωλιγκας, ή περσι δεν επαιζαν
  Ευρωλιγκα = ερχονται απο EuroCup): πληθος, και κλιση (ποντοι ομαδας − μοντελο) πανω στη διαφορα (μιξη − βαση) τους.
ΠΡΟΣΘΗΚΗ (ζητηση Στελιου, γραφτηκε ΑΦΟΥ ειχε δει αποτελεσματα μονο η σταδιακη μιξη, ΠΡΙΝ απο οποιοδηποτε αποτελεσμα της νεας εκδοχης):
  ΕΚΔΟΧΗ «ΣΗΜΕΙΟ ΑΛΛΑΓΗΣ»: μιξη οπως παραπανω μεχρι ο παικτης να εχει παιξει X φετινα ματς Ευρωλιγκας (μετρημενα στο σημειο υπολογισμου,
  ματς με χρονο στο γηπεδο), απο εκει και περα τιμη = 100% Σφ (σε κλιμακα 3Steps), καθολου βαση. X ∈ {10, 15, 20}· επιλογη LOSO μαζι με K/λ.
  ΙΔΙΟ κριτηριο αντικαταστασης (RMSE ≥4/5 ΚΑΙ μοναδες ≥ live ΚΑΙ θετικες ≥4/5).
  ΠΛΗΡΟΦΟΡΙΑΚΑ (ΟΧΙ για αποφαση): η αντιστοιχιση OLS βγηκε σχεδον επιπεδη (r ≈ 0.05 στο πρωτο τρεξιμο) → και οι δυο εκδοχες
  τρεχουν ΚΑΙ με κλιμακα «ταιριασμα μεσου/τυπ. αποκλισης» (onO = μ_3S + (σ_3S/σ_Σφ)·(O − μ_Σφ), στους ιδιους αποντες εκπαιδευσης).
Εξοδος: el_onoff_nbastyle_test_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, json, collections, contextlib, time
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
T0 = time.time()
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open(os.path.join(ROOT, 'el_onoff_nbastyle_test_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
LAMS = (1000, 3000, 8000); KS = (500, 1000, 2000, 4000)
FV = [f'φετινα μονο λ{l}' for l in LAMS]
# ---- 1. δεικτης Σφ (μονο φετινα) απο el_index_build_test.py ----
src = open('el_index_build_test.py', encoding='utf-8').read().split('# ================= ΣΤΑΘΕΡΟΤΗΤΑ')[0]
r1 = "def save(): open("; r2 = "    for var in XVARS:\n        for k, cp in enumerate(CPS[S]): VAL"
assert src.count(r1) == 1 and src.count(r2) == 1
src = src.replace(r1, "def save(): return; open(").replace(r2, f"    for var in {FV!r}:\n        for k, cp in enumerate(CPS[S]): VAL")
IX = {'__file__': os.path.join(ROOT, 'el_index_build_test.py'), '__name__': 'idx'}
with contextlib.redirect_stdout(_B()): exec(src, IX)
sys.stdout.reconfigure(encoding='utf-8')
VAL, CPS, PIDX, IXNAME, GD, BYS, prevS, agg = IX['VAL'], IX['CPS'], IX['PID'], IX['NAME'], IX['GD'], IX['BYS'], IX['prevS'], IX['agg']
TEST = IX['TEST']
NCUR = {}; NGAM = {}                                       # (S, k) -> gid -> φετινες κατοχες πριν το σημειο k
for S in TEST:
    for k, cp in enumerate(CPS[S]):
        A_ = agg([(g, 1.0) for g in BYS[S] if GD[g]['ts'] is not None and GD[g]['ts'] < cp]); NCUR[(S, k)] = {p: v[15] for p, v in A_.items()}
        NGAM[(S, k)] = collections.Counter(p for g in BYS[S] if GD[g]['ts'] is not None and GD[g]['ts'] < cp for p in GD[g]['ps'])
P(f'δεικτης Σφ ετοιμος ({time.time() - T0:.0f} δευτ.)')
# ---- 2. W4 με alias (= live) ----
ALIAS = {n: (tuple(v[0]), v[1]) for n, v in json.load(open('el_onoff_alias.json', encoding='utf-8'))['alias'].items()}
base = open('el_absence_onoff_test.py', encoding='utf-8').read().split('# ---- ΧΑΝΤΙΚΑΠ ----')[0]
a1 = "res.append(dict(w=w, **(pr or dict(onO=0.0, onD=0.0, usg=None))))"; a2 = "rows.append(dict(y=sea,"
a3 = "def profile(name, yr):\n    k = key_of(name)\n"
for a in (a1, a2, a3): assert base.count(a) == 1, a
base = base.replace(a1, "res.append(dict(w=w, pid=pid, **(pr or dict(onO=0.0, onD=0.0, usg=None))))").replace(a2, "rows.append(dict(hc=hc, ac=ac, ts=ts, y=sea,")
base = base.replace(a3, a3 + "    _a = ALIAS.get(str(name))\n    if _a is not None and _a in PROF and PROF[_a].get(yr - 1) is not None and PROF[_a][yr - 1][2] > 0: k = _a\n")
NS = {'ALIAS': ALIAS}
with contextlib.redirect_stdout(_B()): exec(base, NS)
sys.stdout.reconfigure(encoding='utf-8')
rows, SE, ys, YT, YH, YA = NS['rows'], NS['SE'], NS['ys'], NS['YT'], NS['YH'], NS['YA']
rmse, tp, ALL, SDb = NS['rmse'], NS['tp'], NS['ALL'], NS['SD']
hL = NS['HELD']['W4 μονο on/off']; uL, sL = NS['tpicks'](hL)
P(f'LIVE (R0+alias) αναπαραγωγη: ματς {len(rows)} · RMSE {rmse(YT - hL, ALL):.3f} · {sL.strip()}')
if not (len(rows) == 1563 and abs(uL - 55.9) < 0.06 and sL.strip().startswith('516 picks')):
    P('!!! ΔΕΝ αναπαραγεται το live (516 picks, +55.9μ) — STOP'); save(); sys.exit(1)
P('  ✓ αναπαραγεται (516 picks, +55.9μ)')
PLD = json.load(open('el_players.json', encoding='utf-8'))
PLIDX = collections.defaultdict(list)
for k, g in PLD.items(): PLIDX[(g['season'], g['hcode'], g['acode'])].append((pd.Timestamp(g['utc']).tz_localize(None).timestamp(), g['code'], g.get('rnd')))
for r in rows:
    c = [x for x in PLIDX[(r['y'], r['hc'], r['ac'])] if abs(x[0] - r['ts']) < 86400]
    r['code'], r['rnd'] = (c[0][1], c[0][2]) if c else (None, None)
def cp_of(S, ts): return max([i for i, c in enumerate(CPS[S]) if c <= ts], default=0)
PREVTEAMS = {}
def prev_teams(pid, S):
    g = PIDX.get(pid)
    if (pid, S) not in PREVTEAMS:
        PREVTEAMS[(pid, S)] = {GD[k]['ps'][g][1] for k in BYS.get(prevS.get(S), []) if g is not None and g in GD[k]['ps']}
    return PREVTEAMS[(pid, S)]
# ---- 3. πινακας περιστατικων απουσιας ----
INST = []                                       # i, ρολος (0 = γηπ αποντας, 1 = φιλ), w, βαση O/D, εχει βαση, Σφ ανα λ, n, αλλαξε ομαδα
for i, r in enumerate(rows):
    k = cp_of(r['y'], r['ts'])
    for side, L, team in ((0, r['ah'], r['hc']), (1, r['aa'], r['ac'])):
        for p in L:
            g = PIDX.get(p['pid'], -1)
            sv = {l: VAL[(f'φετινα μονο λ{l}', r['y'], k)].get(g) for l in LAMS}
            hb = p['usg'] is not None; pt = prev_teams(p['pid'], r['y'])
            ch = 'EL→αλλη ομαδα EL' if hb and pt and team not in pt else ('EuroCup/αλλου→EL' if hb and not pt else ('ιδια ομαδα' if hb else 'χωρις βαση'))
            INST.append(dict(i=i, side=side, w=p['w'], bO=p['onO'], bD=p['onD'], hb=hb, sv=sv, n=NCUR[(r['y'], k)].get(g, 0.0), ng=NGAM[(r['y'], k)].get(g, 0), ch=ch, pid=p['pid'], team=team))
II = np.array([x['i'] for x in INST]); SIDE = np.array([x['side'] for x in INST]); W = np.array([x['w'] for x in INST])
BO = np.array([x['bO'] for x in INST]); BD = np.array([x['bD'] for x in INST]); HB = np.array([x['hb'] for x in INST])
NN = np.array([x['n'] for x in INST]); NG = np.array([x['ng'] for x in INST]); YI = ys[II]; CH = np.array([x['ch'] for x in INST])
SV = {l: (np.array([x['sv'][l][0] if x['sv'][l] else np.nan for x in INST]), np.array([x['sv'][l][1] if x['sv'][l] else np.nan for x in INST])) for l in LAMS}
P(f'περιστατικα απουσιας {len(INST)} · με βαση {HB.mean():.0%} · με Σφ (n > 0) {np.mean(NN > 0):.0%} · μεσες φετινες κατοχες στη στιγμη του ματς {NN.mean():.0f}')
def mapfit(l, trmask, kind='ols'):
    m = trmask & HB & ~np.isnan(SV[l][0])
    if kind == 'ols': cO, cD = np.polyfit(SV[l][0][m], BO[m], 1), np.polyfit(SV[l][1][m], BD[m], 1)
    else:
        def sdm(x, y): c = np.std(y) / np.std(x); return np.array([c, np.mean(y) - c * np.mean(x)])
        cO, cD = sdm(SV[l][0][m], BO[m]), sdm(SV[l][1][m], BD[m])
    return cO, cD, int(m.sum()), np.corrcoef(SV[l][0][m], BO[m])[0, 1], np.corrcoef(SV[l][1][m], BD[m])[0, 1]
def mixvals(l, K, mp, X=None):
    sO = np.where(np.isnan(SV[l][0]), 0.0, np.polyval(mp[0], np.nan_to_num(SV[l][0]))); sD = np.where(np.isnan(SV[l][1]), 0.0, np.polyval(mp[1], np.nan_to_num(SV[l][1])))
    n = np.where(np.isnan(SV[l][0]), 0.0, NN)
    mO, mD = (n * sO + K * BO) / (n + K), (n * sD + K * BD) / (n + K)
    if X is not None:
        sw = (NG >= X) & ~np.isnan(SV[l][0]); mO = np.where(sw, sO, mO); mD = np.where(sw, sD, mD)
    return mO, mD
def feats(mO, mD, extra_mask=None):
    """XH: [γηπ αποντες × z(O), φιλ αποντες × z(D)] (ποντοι γηπεδουχου) · XA αναλογα"""
    zO = W * mO / SDb['onO']; zD = W * mD / SDb['onD']
    if extra_mask is not None: zO = zO * extra_mask; zD = zD * extra_mask
    XH = np.zeros((len(rows), 2)); XA = np.zeros((len(rows), 2))
    np.add.at(XH[:, 0], II[SIDE == 0], zO[SIDE == 0]); np.add.at(XH[:, 1], II[SIDE == 1], zD[SIDE == 1])
    np.add.at(XA[:, 0], II[SIDE == 1], zO[SIDE == 1]); np.add.at(XA[:, 1], II[SIDE == 0], zD[SIDE == 0])
    return XH, XA
def fit2(XH, XA, tr):
    X = np.r_[XH[tr], XA[tr]]; y = np.r_[YH[tr], YA[tr]]
    return np.linalg.solve(X.T @ X + 1.0 * np.eye(2), X.T @ y)
XHb, XAb = feats(BO, BD)
assert np.allclose(XHb, NS['XH'][:, [2, 3]]) and np.allclose(XAb, NS['XA'][:, [2, 3]]), 'τα χαρακτηριστικα βασης ≠ live'
# ---- 4. LOSO ----
XS = (10, 15, 20)
FAM = {'ΜΙΞΗ': ('ols', [(l, K, None) for l in LAMS for K in KS]), 'ΣΗΜΕΙΟ ΑΛΛΑΓΗΣ': ('ols', [(l, K, X) for l in LAMS for K in KS for X in XS]),
       'ΜΙΞΗ [κλιμ. σ]': ('sd', [(l, K, None) for l in LAMS for K in KS]), 'ΣΗΜ. ΑΛΛΑΓΗΣ [κλιμ. σ]': ('sd', [(l, K, X) for l in LAMS for K in KS for X in XS])}
def vn(l, K, X=None): return f'λ{l} K{K}' + (f' X{X}' if X else '')
HELD = {'live (R0+alias)': hL, 'χωρις διορθωση': np.zeros(len(rows))}; BC = {}; TRR = {}; MAPS = {}; CHF = {}
for fam, (kind, VV) in FAM.items():
    hv = {v: np.zeros(len(rows)) for v in VV}
    for Y in SE:
        tr = YI != Y
        for l in LAMS:
            if (kind, l, Y) not in MAPS: MAPS[(kind, l, Y)] = mapfit(l, tr, kind)
        for v in VV:
            l, K, X = v; XH, XA = feats(*mixvals(l, K, MAPS[(kind, l, Y)], X)); b = fit2(XH, XA, ys != Y); m = ys == Y
            hv[v][m] = XH[m] @ b + XA[m] @ b; TRR[(fam, v, Y)] = rmse(YT - (XH @ b + XA @ b), ys != Y); BC[(fam, v, Y)] = b
    CHF[fam] = {Y: min(VV, key=lambda v: TRR[(fam, v, Y)]) for Y in SE}
    hs_ = np.zeros(len(rows))
    for Y in SE: hs_[ys == Y] = hv[CHF[fam][Y]][ys == Y]
    HELD[f'{fam} LOSO'] = hs_
    for v in VV: HELD[f'{fam} {vn(*v)}'] = hv[v]
for Y in SE: BC[('live', None, Y)] = fit2(XHb, XAb, ys != Y)
def picks_df(adj):
    L = []
    for r, a in zip(rows, adj):
        o = r['op']; T_, oo, ou = o[2], o[3], o[4]; po, pp, pu = tp(r['T'] + a, T_); eo, eu = po * oo + pp - 1, pu * ou + pp - 1
        sd, e, od = (1, eo, oo) if eo >= eu else (-1, eu, ou)
        act = r['hs'] + r['as_']; side = None; u = np.nan; clv = np.nan
        if e >= .08:
            x = (act - T_) * sd; u = (od - 1) if x > 0 else (0 if x == 0 else -1); side = 'over' if sd == 1 else 'under'; clv = (r['cl'][1] - o[1]) * sd
        L.append(dict(season=r['y'], rnd=r['rnd'], pick=side, units=u, clv=clv))
    return pd.DataFrame(L)
MAIN = ['χωρις διορθωση', 'live (R0+alias)', 'ΜΙΞΗ LOSO', 'ΣΗΜΕΙΟ ΑΛΛΑΓΗΣ LOSO', 'ΜΙΞΗ [κλιμ. σ] LOSO', 'ΣΗΜ. ΑΛΛΑΓΗΣ [κλιμ. σ] LOSO']
ORDER = MAIN + [f'{fam} {vn(*v)}' for fam in ('ΜΙΞΗ', 'ΣΗΜΕΙΟ ΑΛΛΑΓΗΣ') for v in FAM[fam][1]]
DF = {nm: picks_df(HELD[nm]) for nm in ORDER}
assert abs(DF['live (R0+alias)'].units.sum() - uL) < 1e-6
def summ(df):
    q = df[df.pick.notna()]; U = {s: q[q.season == s].units for s in SE}
    return len(q), q.units.sum(), q.units.mean() * 100, sum(1 for s in SE if len(U[s]) and U[s].mean() > 0), {s: U[s].sum() for s in SE}, q.clv.mean()
# ================= ΠΙΝΑΚΕΣ =================
FAMS = ['ΜΙΞΗ', 'ΣΗΜΕΙΟ ΑΛΛΑΓΗΣ', 'ΜΙΞΗ [κλιμ. σ]', 'ΣΗΜ. ΑΛΛΑΓΗΣ [κλιμ. σ]']
MOD = {f: collections.Counter(CHF[f].values()).most_common(1)[0][0] for f in FAMS}
P(''); P('## ΑΝΤΙΣΤΟΙΧΙΣΗ Σφ → κλιμακα 3Steps (fold χωρις 2025-26)')
for kind in ('ols', 'sd'):
    for l in LAMS:
        mp = MAPS[(kind, l, 'E2025')]
        P(f'  [{"OLS" if kind == "ols" else "κλιμ. σ"}] Σφ λ{l}: n {mp[2]} · onO = {mp[0][1]:+.2f} + {mp[0][0]:.2f}·O · onD = {mp[1][1]:+.2f} + {mp[1][0]:.2f}·D · r O {mp[3]:+.2f} / D {mp[4]:+.2f}')
P(''); P('## ΕΠΙΛΟΓΗ LOSO ανα κρατημενη σεζον (λ του Σφ, K κατοχες, X ματς για το σημειο αλλαγης)')
for f in FAMS: P(f'  {f:24s} ' + ' · '.join(f'{Y[-2:]}: {vn(*CHF[f][Y])}' for Y in SE) + f'  (συχνοτερη: {vn(*MOD[f])})')
for f in ('ΜΙΞΗ', 'ΣΗΜΕΙΟ ΑΛΛΑΓΗΣ'):
    for Y in SE:
        l = CHF[f][Y][0]; X = CHF[f][Y][2]
        P(f'    {f} {Y}: RMSE εκπαιδευσης ανα K (λ{l}' + (f', X{X}' if X else '') + '): ' + ' · '.join(f'K{K} {TRR[(f, (l, K, X), Y)]:.4f}' for K in KS)
          + f' · live {rmse(YT - (XHb @ BC[("live", None, Y)] + XAb @ BC[("live", None, Y)]), ys != Y):.4f}')
P(''); P('## RMSE συνολου (LOSO, ποντοι συνολου ματς) · ΔRMSE vs live (− = καλυτερο)')
def rmse_line(nm, mask=None):
    h = HELD[nm]; mk = (lambda s: (ys == s) & (mask if mask is not None else True))
    rr = [rmse(YT - h, mk(s)) for s in SE]; d = [rmse(YT - h, mk(s)) - rmse(YT - hL, mk(s)) for s in SE]
    allm = mask if mask is not None else ALL
    return f'RMSE {rmse(YT - h, allm):.3f} · ανα σεζον ' + ' '.join(f'{x:.3f}' for x in rr) + ' · Δ ' + ' '.join(f'{x:+.3f}' for x in d) + f' · καλυτερο {sum(x < 0 for x in d)}/5'
for nm in ORDER: P(f'  {nm:34s} ' + rmse_line(nm))
P(''); P('## bO (δικοι αποντες × z(onO)) / bD (αντιπ. αποντες × z(onD)) — ποντοι ομαδας ανα 40′ απουσιας ανα 1 τυπ. αποκλιση · LOSO fold · αναμενομενα < 0')
def bline(nm, getb):
    bs = {Y: getb(Y) for Y in SE}
    P(f'  {nm:34s} bO ' + ' '.join(f'{Y[-2:]}:{bs[Y][0]:+.2f}' for Y in SE) + f' (<0 {sum(bs[Y][0] < 0 for Y in SE)}/5) · bD ' + ' '.join(f'{Y[-2:]}:{bs[Y][1]:+.2f}' for Y in SE) + f' (<0 {sum(bs[Y][1] < 0 for Y in SE)}/5)')
bline('live (R0+alias)', lambda Y: BC[('live', None, Y)])
for f in FAMS:
    bline(f'{f} LOSO (επιλογη fold)', lambda Y, f=f: BC[(f, CHF[f][Y], Y)])
    bline(f'{f} {vn(*MOD[f])} (συχνοτερη)', lambda Y, f=f: BC[(f, MOD[f], Y)])
P(''); P('## PICKS συνολων ≥8% στο ανοιγμα (Crown) — n · μοναδες · ROI · θετικες σεζον · ανα σεζον · CLV (ποντοι γραμμης προς εμας)')
def pline(nm, df):
    n, u, roi, pos, us, clv = summ(df)
    return f'{n:4d} picks · {u:+6.1f}μ · ROI {roi:+5.1f}% · θετ {pos}/5 · ' + ' '.join(f'{s[-2:]}:{us[s]:+.1f}' for s in SE) + f' · CLV {clv:+.2f}'
for nm in ORDER: P(f'  {nm:34s} ' + pline(nm, DF[nm]))
P(''); P('## OVER / UNDER (n · μοναδες · ROI)')
for nm in MAIN:
    q = DF[nm]; q = q[q.pick.notna()]
    P(f'  {nm:34s} ' + ' · '.join(f'{sd}: {len(q[q.pick == sd]):3d} · {q[q.pick == sd].units.sum():+6.1f}μ · ROI {q[q.pick == sd].units.mean() * 100:+5.1f}%' for sd in ('over', 'under')))
P(''); P('## ΑΓΩΝΙΣΤΙΚΕΣ 1-10 vs 11+ (n · μοναδες · ROI)')
for nm in MAIN:
    q = DF[nm]; q = q[q.pick.notna()]; e = q[q.rnd.fillna(99) <= 10]; l_ = q[q.rnd.fillna(99) > 10]
    P(f'  {nm:34s} 1-10: {len(e):3d} · {e.units.sum():+6.1f}μ · ROI {e.units.mean() * 100:+5.1f}% · 11+: {len(l_):3d} · {l_.units.sum():+6.1f}μ · ROI {l_.units.mean() * 100:+5.1f}%')
P(''); P('################ ΑΠΟΦΑΣΗ (προ-δηλωμενο κριτηριο· μονο οι δυο εκδοχες OLS) ################')
for f in ('ΜΙΞΗ', 'ΣΗΜΕΙΟ ΑΛΛΑΓΗΣ'):
    h = HELD[f'{f} LOSO']; d = [rmse(YT - h, ys == s) - rmse(YT - hL, ys == s) for s in SE]; n, u, roi, pos, us, clv = summ(DF[f'{f} LOSO'])
    ok = sum(x < 0 for x in d) >= 4 and u >= uL and pos >= 4
    P(f'  {f} LOSO: RMSE καλυτερο σε {sum(x < 0 for x in d)}/5 · μοναδες {u:+.1f} vs live {uL:+.1f} · θετικες {pos}/5 → ' + ('ΚΡΙΤΗΡΙΟ ΑΝΤΙΚΑΤΑΣΤΑΣΗΣ ΠΛΗΡΟΥΤΑΙ' if ok else 'ΚΡΙΤΗΡΙΟ ΑΝΤΙΚΑΤΑΣΤΑΣΗΣ ΔΕΝ ΠΛΗΡΟΥΤΑΙ'))
save()
# ================= ΠΕΡΙΓΡΑΦΙΚΑ: αλλαξαν ομαδα =================
P(''); P('################ ΑΠΟΝΤΕΣ ΠΟΥ ΑΛΛΑΞΑΝ ΟΜΑΔΑ απο περσι ################')
P(f'  {"κατηγορια":20s} περιστατικα · διαφορετικοι παικτες · ανα σεζον (' + ' '.join(s[-2:] for s in SE) + ') · μεσα φετινα ματς / κατοχες στο ματς')
for c in ('ιδια ομαδα', 'EL→αλλη ομαδα EL', 'EuroCup/αλλου→EL', 'χωρις βαση'):
    m = CH == c
    P(f'  {c:20s} {m.sum():6d} · {len({INST[j]["pid"] for j in np.where(m)[0]}):5d} · ' + ' '.join(f'{(m & (YI == s)).sum()}' for s in SE) + f' · {NG[m].mean():.1f} / {NN[m].mean():.0f}')
chm = np.isin(CH, ['EL→αλλη ομαδα EL', 'EuroCup/αλλου→EL']).astype(float)
CHROW = np.zeros(len(rows), bool); CHROW[II[chm > 0]] = True
P(f'  ματς με ≥1 αποντα που αλλαξε ομαδα: {CHROW.sum()} απο {len(rows)}')
P(''); P('  RMSE συνολου ΜΟΝΟ στα ματς με ≥1 αποντα που αλλαξε ομαδα (LOSO, Δ vs live):')
for nm in MAIN: P(f'    {nm:34s} ' + rmse_line(nm, CHROW))
P(''); P('  PICKS ΜΟΝΟ στα ματς με ≥1 αποντα που αλλαξε ομαδα:')
for nm in MAIN: P(f'    {nm:34s} ' + pline(nm, DF[nm][CHROW]))
P(''); P('  ΚΛΙΣΗ (ποντοι ομαδας − μοντελο) πανω στη διαφορα (τιμη − βαση) ΜΟΝΟ των αποντων που αλλαξαν ομαδα (EL→EL + EuroCup→EL)')
P('  (OLS σε ομαδα-ματς· ελεγχος: χαρακτηριστικα βασης ολων των αποντων· Δ = Σ w·(τιμη − βαση)/τυπ.αποκλ.· αν η νεα τιμη ειναι σωστοτερη: κλιση Δ ≈ bO/bD < 0)')
for f in FAMS:
    kind = FAM[f][0]; l, K, X = MOD[f]
    for Y in ['ολα'] + SE:
        tr = (YI != Y) if Y != 'ολα' else np.ones(len(INST), bool)
        mp = mapfit(l, tr, kind); mO, mD = mixvals(l, K, mp, X)
        dH, dA = feats(mO - BO, mD - BD, extra_mask=chm)
        m = (ys == Y) if Y != 'ολα' else ALL
        Xm = np.r_[np.c_[np.ones(m.sum()), XHb[m], dH[m]], np.c_[np.ones(m.sum()), XAb[m], dA[m]]]; y = np.r_[YH[m], YA[m]]
        b = np.linalg.lstsq(Xm, y, rcond=None)[0]; res = y - Xm @ b
        se = np.sqrt(np.diag(res @ res / (len(y) - Xm.shape[1]) * np.linalg.pinv(Xm.T @ Xm)))
        nz = int(((np.abs(np.r_[dH[m], dA[m]]).sum(1)) > 1e-9).sum())
        P(f'    {f + " " + vn(l, K, X):38s} {Y:5s} ομαδα-ματς με Δ≠0 {nz:4d} · Δ δικα O {b[3]:+.2f} (t {b[3] / se[3]:+.1f}) · Δ αντιπ. D {b[4]:+.2f} (t {b[4] / se[4]:+.1f})'
          + (f' · βαση: δικα×onO {b[1]:+.2f} (t {b[1] / se[1]:+.1f}) αντιπ.×onD {b[2]:+.2f} (t {b[2] / se[2]:+.1f})' if Y == 'ολα' else ''))
    mp = mapfit(l, np.ones(len(INST), bool), kind); mO, mD = mixvals(l, K, mp, X)
    P(f'    {"":38s} μεση |τιμη − βαση| (ποντοι/100 κατοχες): ' + ' · '.join(f'{c}: O {np.mean(np.abs(mO[CH == c] - BO[CH == c])):.2f} D {np.mean(np.abs(mD[CH == c] - BD[CH == c])):.2f}' for c in ('EL→αλλη ομαδα EL', 'EuroCup/αλλου→EL', 'ιδια ομαδα')))
save()
# ================= ΠΑΡΑΔΕΙΓΜΑΤΑ =================
Y = 'E2025'; prof = NS['profile']; NAMEPL = NS['NAME']
P(''); P('################ ΕΛΕΓΧΟΣ ΠΑΡΑΔΕΙΓΜΑΤΩΝ — 2025-26 (συχνοτερες εκδοχες, αντιστοιχιση χωρις 2025-26) ################')
P('  ' + ' · '.join(f'{f}: {vn(*MOD[f])}' for f in FAMS))
def show(pid, label):
    nm = NAMEPL.get(pid, IXNAME.get(pid, pid)); g = PIDX.get(pid); pr = prof(nm, 2025)
    bO, bD = (pr['onO'], pr['onD']) if pr else (0.0, 0.0)
    cur = sorted({GD[k]['ps'][g][1] for k in BYS[Y] if g in GD[k]['ps']})
    P(f'  [{label}] {nm} · περσι (EL) {"/".join(sorted(prev_teams(pid, Y))) or "—"} → φετος {"/".join(cur) or "—"} · βαση 3Steps: ' + (f'onO {bO:+.2f} / onD {bD:+.2f}' if pr else 'ΚΑΜΙΑ (→ 0)'))
    nc = len(CPS[Y])
    for k in (1, nc // 2, nc - 2):
        n = NCUR[(Y, k)].get(g, 0.0); ngm = NGAM[(Y, k)].get(g, 0); parts = []
        for f in FAMS:
            kind = FAM[f][0]; l, K, X = MOD[f]; mp = MAPS[(kind, l, Y)]; v = VAL[(f'φετινα μονο λ{l}', Y, k)].get(g)
            if v is None: parts.append(f'{f}: = βαση {bO:+.2f}/{bD:+.2f}'); continue
            sO, sD = float(np.polyval(mp[0], v[0])), float(np.polyval(mp[1], v[1]))
            if X is not None and ngm >= X: mO, mD = sO, sD
            else: mO, mD = (n * sO + K * bO) / (n + K), (n * sD + K * bD) / (n + K)
            parts.append(f'{f}: Σφ(λ{l}) {v[0]:+.2f}/{v[1]:+.2f} → 3S {sO:+.2f}/{sD:+.2f} → τιμη {mO:+.2f}/{mD:+.2f}')
        P(f'      {pd.Timestamp(CPS[Y][k], unit="s"):%d/%m/%Y} · φετινα ματς {ngm} · κατοχες {n:.0f}')
        for x in parts: P(f'          {x}')
def find(sub):
    c = [p for p, nm in IXNAME.items() if sub in nm]; return c[0] if c else None
pv = find('VILDOZA')
if pv: show(pv, 'αλλαξε ομαδα')
y25 = [x for j, x in enumerate(INST) if YI[j] == Y]
st = collections.Counter(x['pid'] for x in y25 if x['ch'] == 'ιδια ομαδα').most_common(1)
if st: show(st[0][0], 'σταθερος (ιδια ομαδα, οι περισσοτερες απουσιες)')
nb = collections.Counter(x['pid'] for x in y25 if x['ch'] == 'χωρις βαση').most_common(1)
if nb: show(nb[0][0], 'χωρις βαση (οι περισσοτερες απουσιες)')
P(''); P(f'χρονος {time.time() - T0:.0f} δευτ.')
save()
