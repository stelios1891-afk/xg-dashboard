# -*- coding: utf-8 -*-
"""ucl_away3_penalty_test.py — CHAMPIONS LEAGUE: ΠΟΙΝΗ «3ο+ ΣΥΝΕΧΟΜΕΝΟ ΕΚΤΟΣ» στον φιλοξενουμενο, ως διορθωση μοντελου
(16/10/2026, Στελιος: «βαλε την ποινη οπως στο ταξιδι της Ευρωλιγκας»). Προτυπο: el_travel_shape_test.py / el_travel.py.
Βαση: ucl_away_streak_deep.py (ημερολογιο ομαδας εγχωρια+Ευρωπη, σερι εκτος, ξεκουραση) + αλυσιδα ucl_bb_timing (LH/LA live, W2 συνολα,
κανονες live). ΜΟΝΟ UCL, 2223-2526 (4 σεζον με live μοντελο), FotMob+FotMob για χαντικαπ (ως live)· over και με μια ομαδα χωρις FotMob.
ΜΟΡΦΗ ΠΟΙΝΗΣ (η πιο απλη): ΜΙΑ μετατοπιση υπεροχης δ (γκολ, + = υπερ γηπεδουχου) μοιρασμενη ισα: λ_γηπ += δ/2, λ_φιλ −= δ/2
(το συνολο γκολ μενει ιδιο → τα συνολα σχεδον δεν αλλαζουν). Ιδια μετατοπιση και στη μηχανη συνολων (OH/OA).
ΕΚΔΟΧΕΣ (f = βαρος ποινης στο ματς):
  A ΣΚΑΛΙ: σερι εκτος φιλοξ. ≥3 → f=1
  B ΣΚΑΛΙ + ξεκουραση: σερι ≥3 ΚΑΙ ξεκουραση φιλοξ. ≤3.5 μερες → f=1
  C ΔΙΑΒΑΘΜΙΣΜΕΝΗ: σερι 2 → f=½ · σερι ≥3 → f=1
  (γειτονικα για την A: συγκρατηση K=0 και K=50)
Παραμετρος LOSO (εκπαιδευση στις 3 αλλες σεζον), υπολοιπο r = διαφορα γκολ − (LH−LA), με συγκρατηση προς το 0 (οπως EL):
  δ = Σ f·r / (Σ f² + K), K = 25 ματς. Ματς με ελλιπες ημερολογιο (καμια εγχωρια ±14μ) ή τελικος → f=0.
ΜΕΤΡΗΣΕΙΣ: (1) ΔRMSE διαφορας γκολ & Δlog-loss 1Χ2 / AH-καλυψης (γραμμη κλεισιματος Crown, αλλιως SBOBET) ανα σεζον, ολα τα ματς UCL
  FotMob+FotMob της σεζον · (2) picks live κανονων (φαβ ≥10% σωστα τεταρτα, dog ≥4% p_cover, |γραμμη|≥0.5, 1.70-2.10, over ≥4%, under ≥10%)
  στην τιμη 72ω (επιλογη+τιμη στη στιγμη 72ω) ΚΑΙ στο κλεισιμο (επιλογη+τιμη κλεισιματος), + αναφορα: alert ≤72ω (πρωτη στιγμη) ·
  μεσος Crown/SBOBET · ΜΟΝΟ στα ματς που αγγιζει η ποινη (τα υπολοιπα μενουν ιδια) · (3) συνολα: αλλαζουν τα over/under;
ΠΡΟ-ΔΗΛΩΜΕΝΟ (γραφτηκε ΠΡΙΝ το τρεξιμο, ανα εκδοχη): ΠΕΡΝΑ αν ΟΛΑ:
  (1) LOSO RMSE καλυτερο σε ≥3/4 σεζον (ή, αν οχι, log-loss 1Χ2 καλυτερο σε ≥3/4)
  (2) μοναδες picks (χαντικαπ+συνολα, επηρεαζομενα ματς) ΜΕ ποινη ≥ ΧΩΡΙΣ, και στις 72ω ΚΑΙ στο κλεισιμο
  (3) οχι απο μια σεζον: διαφορα ανα σεζον > 0 σε ≥3/4 Η το συνολο μενει > 0 χωρις την καλυτερη σεζον (72ω ΚΑΙ κλεισιμο)
  Αλλιως ✗.
ΠΡΟΣΘΗΚΗ (Στελιος, ιδιο τρεξιμο): ΕΓΧΩΡΙΑ CORE7 2223-2526 (μοντελο europe_test_preds md≥6, Crown κλεισιμο/72ω Nowgoal), φιλοξ. σε 3ο+ συνεχομενο
  εκτος (εγχ. Χ → Ευρωπη Χ → εγχ. Χ, εγχ. Χ ×3, αλλα). ΔΕΝ εχουμε εγχωρια κυπελλα → σερι μπορει να ειναι λαθος (ενδιαμεσο κυπελλο εντος).
  ΔΕΝ υπαρχει σε αυτο το harness πιστο αντιγραφο των εγχωριων live κανονων → αντι για (2)/(3) picks: ΤΥΦΛΟ AH υπερ γηπεδουχου στα σημαδεμενα.
  ΠΡΟ-ΔΗΛΩΜΕΝΟ ΕΓΧΩΡΙΑ: (1) ιδιο · (2') τυφλο AH γηπ. > 0 στις 72ω ΚΑΙ στο κλεισιμο · (3') > 0 σε ≥3/4 σεζον Η συνολο > 0 χωρις την καλυτερη.
  ΚΟΙΝΗ ποινη UCL+εγχ. (LOSO): δ απο ενωμενο δειγμα· ιδια κριση (1) χωριστα σε UCL και εγχωρια + ποσες σεζον κοινη ≤ χωριστη (RMSE).
ΣΗΜΕΡΑ: Sabah–Dortmund, Porto–PSV, PSG–Barcelona, Como–Man United (20-21/10/2026): euro_projections xgh/xga, γραμμες euro_odds_latest (Pinnacle).
Εξοδος: ucl_away3_penalty_test_out.txt"""
import sys, io, os, json, math, pickle, contextlib
import numpy as np, pandas as pd
sys.path.insert(0, os.getcwd())
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open('ucl_away_streak_deep.py', encoding='utf-8').read()
src = src[:src.index('# ---------------- 2. ΑΓΟΡΑ & ΓΡΑΜΜΕΣ')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
D = {'__name__': 'deep'}
with contextlib.redirect_stdout(_B()): exec(src, D)
sys.stdout.reconfigure(encoding='utf-8')
g = D['g']
MIDS, COMP, FM, SEA = list(map(str, g['MIDS'])), np.asarray(g['COMP']), np.asarray(g['FM'], bool), np.asarray(g['SEA'])
LH, LA, GD = np.asarray(g['LH'], float), np.asarray(g['LA'], float), np.asarray(g['GD'], float)
GH, GA, OH, OA = np.asarray(g['GH'], float), np.asarray(g['GA'], float), np.asarray(g['OH'], float), np.asarray(g['OA'], float)
KO, TRAJ, TOU = g['KO'], g['TRAJ'], g['TOU']
sdist, cover_q, edge, picks, window, settle_ou, ES, DS = g['sdist'], g['cover_q'], g['edge'], g['picks'], g['window'], g['settle_ou'], g['ES'], g['DRAW_SCALE']
G, feats, build_cal = D['G'], D['feats'], D['build_cal']
THR = dict(fav=0.10, dog=0.04, over=0.04, under=0.10)
SEAS = ['2223', '2324', '2425', '2526']; K0 = 25
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
# ---- ονοματα ----
NM = {}
for fn in ('europe_fixtures.json', 'europe_fixtures_2627.json'):
    for L in json.load(open(fn, encoding='utf-8')).values():
        for m in L: NM[int(m['hid'])] = m.get('hname', ''); NM[int(m['aid'])] = m.get('aname', '')
# ---- πηγες για over με μια ομαδα χωρις FotMob ----
_V = pickle.load(open('euro_v6_preds.pkl', 'rb')); _VI = {str(m): j for j, m in enumerate(_V['mids'])}
_LAB = {'shots': 'F', 'griffis': 'B', 'goals': 'G'}
def srcs(i):
    j = _VI.get(MIDS[i]); return (_LAB.get(_V['src_h'][j], '?'), _LAB.get(_V['src_a'][j], '?')) if j is not None else ('?', '?')
# ---- χαρακτηριστικα φιλοξενουμενου ανα ματς ----
N = len(MIDS); STR = np.zeros(N, int); REST = np.full(N, np.nan); OK = np.zeros(N, bool); NF1 = np.zeros(N, bool)
UCL = (COMP == 'ChampionsLeague') & np.isin(SEA, SEAS)
for i, mid in enumerate(MIDS):
    if not UCL[i]: continue
    x = G.get(mid)
    if x is None or x['rnd'] == 'final': continue
    Fh, Fa = feats(x['h'], mid), feats(x['a'], mid)
    if Fh is None or Fa is None: continue
    STR[i], REST[i], OK[i] = Fa['streak'], Fa['rest'], bool(Fh['ok'] and Fa['ok'])
    if not FM[i]:
        sh, sa = srcs(i); NF1[i] = (sh == 'F') != (sa == 'F')
VER = {'A σερι≥3': lambda s, r: (s >= 3).astype(float),
       'B σερι≥3 & ξεκ≤3.5': lambda s, r: ((s >= 3) & (np.nan_to_num(r, nan=99) <= 3.5)).astype(float),
       'C σερι2=½ · ≥3=1': lambda s, r: np.where(s >= 3, 1.0, np.where(s == 2, 0.5, 0.0))}
F = {k: np.where(OK, fn(STR, REST), 0.0) for k, fn in VER.items()}
RES = GD - (LH - LA)
FIT = UCL & FM & OK
def fit(f, mask, K):
    return float((f[mask] * RES[mask]).sum() / ((f[mask] ** 2).sum() + K))
# ---- μετρα ακριβειας ----
OUT3 = np.where(GD > 0, 0, np.where(GD == 0, 1, 2))
def cl_line(mid):
    for bk in ('Crown', 'SBOBET'):
        seq = [x for x in (TRAJ.get((mid, bk)) or []) if KO.get(mid) and x[0] <= KO[mid] + 900]
        if seq: return seq[-1][1]
    return None
CLL = [cl_line(m) if UCL[i] and FM[i] else None for i, m in enumerate(MIDS)]
def ll_match(i, lh, la):
    d = sdist(lh, la); p3 = [sum(v for k, v in d.items() if k > 0), d.get(0, 0.0), sum(v for k, v in d.items() if k < 0)]
    l1 = -math.log(max(p3[OUT3[i]], 1e-9)); L = CLL[i]; la_ = 0.0
    if L is not None:
        parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]
        for q in parts:
            m_ = GD[i] + q
            if abs(m_) < .01: continue
            pw = sum(v for k, v in d.items() if k + q > .01); pl = sum(v for k, v in d.items() if k + q < -.01)
            p = pw / max(pw + pl, 1e-9); la_ += -math.log(max(p if m_ > 0 else 1 - p, 1e-9)) / len(parts)
    return l1, la_
def shift(i, dl): return max(LH[i] + dl / 2, .05), max(LA[i] - dl / 2, .05)
def accuracy(f, K):
    """ανα σεζον: ΔRMSE, Δlog-loss 1Χ2, Δlog-loss AH (με − χωρις), δ, n σημαδεμενα στην εκπαιδευση/τεστ"""
    R = {}
    for s in SEAS:
        tr = FIT & (SEA != s); dl = fit(f, tr, K); te = UCL & FM & (SEA == s)
        idx = np.where(te)[0]; r0 = RES[idx]; r1 = r0 - f[idx] * dl
        d1 = d2 = 0.0
        for i in idx[f[idx] != 0]:
            a0, b0 = ll_match(i, LH[i], LA[i]); a1, b1 = ll_match(i, *shift(i, f[i] * dl)); d1 += a1 - a0; d2 += b1 - b0
        R[s] = dict(dl=dl, drmse=math.sqrt((r1 ** 2).mean()) - math.sqrt((r0 ** 2).mean()), d1=d1, d2=d2,
                    ntr=int((tr & (f != 0)).sum()), nte=int((te & (f != 0)).sum()))
    return R
# ---- picks live κανονων ----
def picks_match(i, lh, la, oh, oa):
    """λιστα (στιγμη, βιβλιο, αγορα, πλευρα, pnl) · στιγμες: '72' (επιλογη+τιμη 72ω), 'cl' (κλεισιμο), 'al' (πρωτο alert ≤72ω)"""
    mid = MIDS[i]; ko = KO.get(mid); res = []
    if not ko: return res
    if FM[i]:
        dist = sdist(lh, la)
        for bk in ('Crown', 'SBOBET'):
            ser, cl = window(TRAJ.get((mid, bk)), ko)
            if not ser or not cl: continue
            for side in (1, -1):
                def ev(row):
                    _, L, h_, a_ = row; ln = L if side == 1 else -L; o = h_ if side == 1 else a_
                    role = 'fav' if ln <= -0.5 else ('dog' if ln >= 0.5 else None)
                    if role is None or not (1.70 <= o <= 2.10): return None
                    pw, pp = cover_q(dist, side, ln) if role == 'fav' else picks.p_cover(dist, side, ln)
                    return picks.settle(GD[i], side, ln, o) if edge(pw, pp, o) >= THR[role] else None
                for tag, row in (('72', ser[0]), ('cl', cl)):
                    v = ev(row)
                    if v is not None: res.append((tag, bk, 'ah', side, v))
                for row in ser:
                    v = ev(row)
                    if v is not None: res.append(('al', bk, 'ah', side, v)); break
    if FM[i] or NF1[i]:
        oh_, oa_ = oh, oa
        if NF1[i]:
            sh, _ = srcs(i)
            if sh == 'F': oh_ *= 1.22
            else: oa_ *= 1.22
        td = ES.tot_dist(max(oh_, .05), max(oa_, .05), DS); tot = GH[i] + GA[i]
        for bk in ('Crown', 'SBOBET'):
            ser, cl = window(TOU.get((mid, bk)), ko)
            if not ser or not cl: continue
            for side in (('over', 'under') if FM[i] else ('over',)):
                def ev(row):
                    _, L, o, un = row; od = o if side == 'over' else un
                    if not (1.70 <= od <= 2.10): return None
                    po, pu = ES.p_over(td, L); pw_, pl_ = (po, pu) if side == 'over' else (pu, po)
                    return settle_ou(tot, L, od, side == 'over') if pw_ * (od - 1) * (1 - picks.MARGIN) - pl_ >= THR[side] else None
                for tag, row in (('72', ser[0]), ('cl', cl)):
                    v = ev(row)
                    if v is not None: res.append((tag, bk, 'ou', side, v))
                for row in ser:
                    v = ev(row)
                    if v is not None: res.append(('al', bk, 'ou', side, v)); break
    return res
BASE = {}
def base(i):
    if i not in BASE: BASE[i] = picks_match(i, LH[i], LA[i], OH[i], OA[i])
    return BASE[i]
def picks_eval(f, K):
    """σε σημαδεμενα ματς ανα σεζον (δ LOSO): picks χωρις/με, ανα στιγμη & αγορα· και αλλαγες (εμφ./εξαφ./αντιστρ.)"""
    rows, chg = [], []
    for s in SEAS:
        dl = fit(f, FIT & (SEA != s), K)
        for i in np.where(UCL & (FM | NF1) & (SEA == s) & (f != 0))[0]:
            d = f[i] * dl; lh, la = shift(i, d)
            p0, p1 = base(i), picks_match(i, lh, la, OH[i] + d / 2, OA[i] - d / 2)
            for w, P_ in ((0, p0), (1, p1)):
                for tag, bk, mk, side, v in P_: rows.append(dict(sea=s, i=i, w=w, tag=tag, bk=bk, mk=mk, side=side, v=v))
            for t in ('72', 'cl'):                              # λιστα αλλαγων: Crown μονο (να μη διπλομετραμε)
                for m in ('ah', 'ou'):
                    a = {sd: v for tt, b, mm, sd, v in p0 if tt == t and b == 'Crown' and mm == m}
                    b_ = {sd: v for tt, b, mm, sd, v in p1 if tt == t and b == 'Crown' and mm == m}
                    new, lost = set(b_) - set(a), set(a) - set(b_)
                    if new and lost:
                        for sd in new: chg.append(dict(sea=s, i=i, tag=t, mk=m, side=sd, kind='αντιστρ.', v=b_[sd]))
                    else:
                        for sd in new: chg.append(dict(sea=s, i=i, tag=t, mk=m, side=sd, kind='νεο', v=b_[sd]))
                        for sd in lost: chg.append(dict(sea=s, i=i, tag=t, mk=m, side=sd, kind='χαθηκε', v=a[sd]))
    return pd.DataFrame(rows), pd.DataFrame(chg)
def units(R, **kw):
    d = R
    for k, v in kw.items(): d = d[d[k] == v] if not isinstance(v, (list, tuple)) else d[d[k].isin(v)]
    return d.v.sum() / 2, len(d) / 2
# ============================ ΤΡΕΞΙΜΟ ============================
P('UCL · ποινη «3ο+ συνεχομενο εκτος» στον φιλοξ. · δ = μετατοπιση υπεροχης (γκολ, + υπερ γηπ.), ½ σε καθε λ · LOSO 2223-2526 · συγκρατηση K=25')
nfl = {k: int((FIT & (f != 0)).sum()) for k, f in F.items()}
P(f'δειγμα: UCL FotMob+FotMob με πληρες ημερολογιο {int(FIT.sum())} ματς · σημαδεμενα A {nfl["A σερι≥3"]} · B {nfl["B σερι≥3 & ξεκ≤3.5"]} · '
  f'C {int((FIT & (F["C σερι2=½ · ≥3=1"] == 1)).sum())} (≥3) + {int((FIT & (F["C σερι2=½ · ≥3=1"] == .5)).sum())} (σερι 2) · '
  f'μεσο υπολοιπο σερι≥3 {RES[FIT & (STR >= 3)].mean():+.2f} (n {int((FIT & (STR >= 3)).sum())}), σερι 2 {RES[FIT & (STR == 2)].mean():+.2f} (n {int((FIT & (STR == 2)).sum())})')
P(''); P('## (1) ΑΚΡΙΒΕΙΑ LOSO (με − χωρις· − = καλυτερα) · δ ανα fold (n σημαδ. εκπαιδ./τεστ) · RMSE ×1000 · log-loss αθροισμα σεζον')
ACC = {}
runs = [(k, F[k], K0) for k in VER] + [('A  K=0 (γειτ.)', F['A σερι≥3'], 0), ('A  K=50 (γειτ.)', F['A σερι≥3'], 50)]
for nm, f, K in runs:
    R = accuracy(f, K); ACC[nm] = R
    w1 = sum(R[s]['drmse'] < 0 for s in SEAS); w2 = sum(R[s]['d1'] < 0 for s in SEAS); w3 = sum(R[s]['d2'] < 0 for s in SEAS)
    P(f'  {nm:20s} δ ' + ' '.join(f'{R[s]["dl"]:+.2f}({R[s]["ntr"]}/{R[s]["nte"]})' for s in SEAS))
    P(f'  {"":20s} RMSE ' + ' '.join(f'{1000 * R[s]["drmse"]:+.1f}' for s in SEAS) + f' → {w1}/4 · 1Χ2 ' + ' '.join(f'{R[s]["d1"]:+.2f}' for s in SEAS)
      + f' → {w2}/4 · AH ' + ' '.join(f'{R[s]["d2"]:+.2f}' for s in SEAS) + f' → {w3}/4')
P(''); P('## (2) PICKS live κανονων ΣΤΑ ΣΗΜΑΔΕΜΕΝΑ ΜΑΤΣ (μεσος Crown/SBOBET· picks/βιβλιο, μοναδες) · χωρις → με · διαφορα ανα σεζον 22/23/24/25')
PE = {}; VERD = {}
for nm in VER:
    R, C = picks_eval(F[nm], K0); PE[nm] = (R, C); tests = {}
    for tag, lab in (('72', '72ω '), ('cl', 'κλεισ'), ('al', 'alert')):
        u0, n0 = units(R, tag=tag, w=0); u1, n1 = units(R, tag=tag, w=1)
        ah0, _ = units(R, tag=tag, w=0, mk='ah'); ah1, _ = units(R, tag=tag, w=1, mk='ah')
        ps = [units(R, tag=tag, w=1, sea=s)[0] - units(R, tag=tag, w=0, sea=s)[0] for s in SEAS]
        drop = sum(ps) - max(ps)
        tests[tag] = (u1 >= u0, sum(p > 1e-9 for p in ps) >= 3 or drop > 0)
        roi = lambda u, n: f'{100 * u / n:+.0f}%' if n else '—'
        P(f'  {nm[:1]} {lab} {n0:4.1f} π {u0:+5.2f}μ ({roi(u0, n0)}) → {n1:4.1f} π {u1:+5.2f}μ ({roi(u1, n1)}) · εκ των οποιων AH {ah0:+.2f}→{ah1:+.2f} · '
          f'ανα σεζον ' + '/'.join(f'{p:+.1f}' for p in ps) + f' · χωρις καλυτερη {drop:+.2f}')
    acc = ACC[nm]; c1 = sum(acc[s]['drmse'] < 0 for s in SEAS) >= 3 or sum(acc[s]['d1'] < 0 for s in SEAS) >= 3
    c2 = tests['72'][0] and tests['cl'][0]; c3 = tests['72'][1] and tests['cl'][1]
    VERD[nm] = (c1, c2, c3)
    if len(C):
        C = C.sort_values(['tag', 'sea'])
        for tag in ('72', 'cl'):
            c = C[C.tag == tag]
            if len(c):
                P(f'     αλλαγες Crown {tag}: ' + ' · '.join(
                    f'{r.sea[:2]} {NM.get(G[MIDS[r.i]]["h"], "?")[:10]}–{NM.get(G[MIDS[r.i]]["a"], "?")[:10]} {r.kind} '
                    f'{("γηπ" if r.side == 1 else "φιλ") if r.mk == "ah" else r.side} {r.v:+.2f}' for r in c.itertuples()))
P(''); P('## (3) ΣΥΝΟΛΑ στα σημαδεμενα: over/under picks χωρις → με (μοναδες, 72ω | κλεισ) · και over με μια ομαδα χωρις FotMob')
for nm in VER:
    R, _ = PE[nm]; cells = []
    for side in ('over', 'under'):
        for tag in ('72', 'cl'):
            u0, n0 = units(R, tag=tag, w=0, side=side); u1, n1 = units(R, tag=tag, w=1, side=side); cells.append(f'{side[:2]} {tag} {n0:.1f}π {u0:+.2f}→{n1:.1f}π {u1:+.2f}')
    nf = R[R.i.map(lambda i: bool(NF1[i]))]; u0, n0 = units(nf, tag='cl', w=0); u1, n1 = units(nf, tag='cl', w=1)
    P(f'  {nm[:1]} ' + ' · '.join(cells) + f' · μη-FM over κλεισ {n0:.1f}π {u0:+.2f}→{n1:.1f}π {u1:+.2f}')
P(''); P('## ΠΡΟ-ΔΗΛΩΜΕΝΟ: (1) RMSE ή 1Χ2 ≥3/4 · (2) μοναδες με ≥ χωρις 72ω & κλεισ · (3) οχι απο μια σεζον (72ω & κλεισ)')
for nm in VER:
    c1, c2, c3 = VERD[nm]; ok = c1 and c2 and c3
    P(f'  {nm:20s} (1) {"✓" if c1 else "✗"} · (2) {"✓" if c2 else "✗"} · (3) {"✓" if c3 else "✗"} → {"ΠΕΡΝΑ" if ok else "✗"}')
# ============================ ΕΓΧΩΡΙΑ CORE7 ============================
s2 = open('ucl_away_streak_deep.py', encoding='utf-8').read()
s2 = s2[s2.index('# ---------------- 2. ΑΓΟΡΑ & ΓΡΑΜΜΕΣ'):s2.index('# ---------------- 3. ΓΡΑΜΜΕΣ ΟΜΑΔΑΣ-ΜΑΤΣ')]
with contextlib.redirect_stdout(_B()): exec(s2, D)
AHD, TOUD, at_, msup_, mtot_ = D['AHD'], D['TOUD'], D['at'], g['msup'], g['mtot']
EP = pd.read_csv('europe_test_preds.csv'); EP['mid'] = EP.mid.astype(str)
drows = []
for r in EP.itertuples():
    x = G.get(r.mid)
    if x is None or x['kind'] != 'dom': continue
    a = int(x['a']); Lc = D['CAL'].get(a); j = D['POS'].get(a, {}).get(r.mid)
    if j is None: continue
    Fa = feats(a, r.mid); ko = int(x['t'].tz_localize('UTC').timestamp())
    seq = [y for y in (AHD.get((r.mid, 'Crown')) or []) if y[0] < ko]
    if not seq: continue
    ts = [y for y in (TOUD.get((r.mid, 'Crown')) or []) if y[0] < ko]
    T = mtot_(*ts[-1][1:]) if ts else r.xg_h + r.xg_a
    cl = seq[-1]; op = at_(seq, ko - 72 * 3600) or seq[0]
    drows.append(dict(mid=r.mid, sea=str(r.season), gd=float(r.gd), lh=float(r.xg_h), la=float(r.xg_a), st=Fa['streak'], rest=Fa['rest'],
                      p3=''.join('E' if e[4] == 'eu' else 'L' for e in Lc[max(0, j - 2):j + 1]),
                      mc=msup_(cl[1], cl[2], cl[3], T), mo=msup_(op[1], op[2], op[3], T),
                      pc=picks.settle(r.gd, 1, cl[1], cl[2]), po=picks.settle(r.gd, 1, op[1], op[2])))
DM = pd.DataFrame(drows); DM['rm'] = DM.gd - (DM.lh - DM.la); DM['rc'] = DM.gd - DM.mc; DM['ro'] = DM.gd - DM.mo
DOUT = np.where(DM.gd > 0, 0, np.where(DM.gd == 0, 1, 2))
DF = {'A σερι≥3': (DM.st >= 3).astype(float).values,
      'B σερι≥3 & ξεκ≤3.5': ((DM.st >= 3) & (DM.rest.fillna(99) <= 3.5)).astype(float).values,
      'C σερι2=½ · ≥3=1': np.where(DM.st >= 3, 1.0, np.where(DM.st == 2, .5, 0.)).astype(float)}
P(''); P(f'## ΕΓΧΩΡΙΑ CORE7 2223-2526 · Crown · μοντελο europe_test_preds (md≥6) · {len(DM)} ματς · ΧΩΡΙΣ κυπελλα (σερι πιθανον λαθος)')
P('  ομαδα (φιλοξ.)            n   · πραγμ−κλεισ ±SE (t) · −72ω · −μοντ · τυφλο AH γηπ. κλεισ | 72ω · σεζον ιδια φορα (κλεισ)  [+ = φιλοξ. χειροτερα]')
def drow(lab, d):
    if len(d) < 5: P(f'  {lab:24s} n {len(d):5d}'); return
    mu, se = d.rc.mean(), d.rc.std() / math.sqrt(len(d)); ps = d.groupby('sea').rc.mean()
    P(f'  {lab:24s} n {len(d):5d} · {mu:+.3f}±{se:.3f} (t {mu / se:+.1f}) · {d.ro.mean():+.3f} · {d.rm.mean():+.3f} · {100 * d.pc.mean():+5.1f}% | {100 * d.po.mean():+5.1f}%'
      f' · {int((np.sign(ps) == np.sign(mu)).sum())}/{len(ps)} [' + ' '.join(f'{v:+.2f}' for v in ps) + ']')
drow('σερι 1 [βαση]', DM[DM.st == 1]); drow('σερι 2', DM[DM.st == 2]); drow('σερι ≥3', DM[DM.st >= 3])
drow('  εγχ.Χ→Ευρ.Χ→εγχ.Χ', DM[(DM.st >= 3) & (DM.p3 == 'LEL')]); drow('  εγχ.Χ ×3', DM[(DM.st >= 3) & (DM.p3 == 'LLL')])
drow('  αλλο (π.χ. Ε→Ε→Χ)', DM[(DM.st >= 3) & ~DM.p3.isin(['LEL', 'LLL'])]); drow('  σερι≥3 & ξεκ≤3.5', DM[(DM.st >= 3) & (DM.rest <= 3.5)])
def dll(i, lh, la):
    d = picks.gd_dist(max(lh, .05), max(la, .05)); p3 = [sum(v for k, v in d.items() if k > 0), d.get(0, 0.), sum(v for k, v in d.items() if k < 0)]
    return -math.log(max(p3[DOUT[i]], 1e-9))
DSEA = DM.sea.values; RM = DM.rm.values
def dfit(f, m, K): return float((f[m] * RM[m]).sum() / ((f[m] ** 2).sum() + K))
P('  LOSO (K=25): δ ανα fold · ΔRMSE×1000 ανα σεζον · Δlog-loss 1Χ2 (Poisson) · τυφλο AH γηπ. στα σημαδεμενα (μον.) κλεισ | 72ω ανα σεζον')
DVER = {}
for nm, f in DF.items():
    ds, dr, dl_, uc, uo = [], [], [], [], []
    for s in SEAS:
        dl = dfit(f, DSEA != s, K0); ds.append(dl); te = DSEA == s; r0 = RM[te]; r1 = r0 - f[te] * dl
        dr.append(math.sqrt((r1 ** 2).mean()) - math.sqrt((r0 ** 2).mean()))
        dl_.append(sum(dll(i, DM.lh.iat[i] + f[i] * dl / 2, DM.la.iat[i] - f[i] * dl / 2) - dll(i, DM.lh.iat[i], DM.la.iat[i]) for i in np.where(te & (f != 0))[0]))
        m = te & (f >= 1); uc.append(DM.pc.values[m].sum()); uo.append(DM.po.values[m].sum())
    w1, w2 = sum(v < 0 for v in dr), sum(v < 0 for v in dl_)
    c1 = w1 >= 3 or w2 >= 3
    c2 = sum(uc) > 0 and sum(uo) > 0
    c3 = all(sum(p > 0 for p in u) >= 3 or sum(u) - max(u) > 0 for u in (uc, uo))
    DVER[nm] = (c1, c2, c3)
    P(f'  {nm[:1]} δ ' + ' '.join(f'{v:+.2f}' for v in ds) + ' · RMSE ' + ' '.join(f'{1000 * v:+.1f}' for v in dr) + f' → {w1}/4 · 1Χ2 '
      + ' '.join(f'{v:+.1f}' for v in dl_) + f' → {w2}/4 · AH(f=1) ' + '/'.join(f'{v:+.1f}' for v in uc) + f' = {sum(uc):+.1f}μ | ' + '/'.join(f'{v:+.1f}' for v in uo) + f' = {sum(uo):+.1f}μ')
P("  ΠΡΟ-ΔΗΛΩΜΕΝΟ ΕΓΧΩΡΙΑ (1) RMSE ή 1Χ2 ≥3/4 · (2') τυφλο AH>0 72ω & κλεισ · (3') οχι απο μια σεζον: " + ' · '.join(
    f'{nm[:1]} {"✓" if a else "✗"}{"✓" if b else "✗"}{"✓" if c else "✗"} → {"ΠΕΡΝΑ" if a and b and c else "✗"}' for nm, (a, b, c) in DVER.items()))
# ---- κοινη ποινη UCL + εγχωρια ----
P(''); P('## ΚΟΙΝΗ ΠΟΙΝΗ UCL+ΕΓΧΩΡΙΑ (LOSO, K=25): δ κοινο · ΔRMSE×1000 UCL | εγχ. ανα σεζον · κοινη ≤ χωριστη (σεζον)')
for nm in VER:
    fu, fd = F[nm], DF[nm]; dc, ru, rd, cu, cd = [], [], [], 0, 0
    for s in SEAS:
        mu_, md_ = FIT & (SEA != s), DSEA != s
        d = float(((fu[mu_] * RES[mu_]).sum() + (fd[md_] * RM[md_]).sum()) / ((fu[mu_] ** 2).sum() + (fd[md_] ** 2).sum() + K0)); dc.append(d)
        tu = UCL & FM & (SEA == s); r0 = RES[tu]; td_ = DSEA == s; q0 = RM[td_]
        rmse = lambda r: math.sqrt((r ** 2).mean())
        ru.append(rmse(r0 - fu[tu] * d) - rmse(r0)); rd.append(rmse(q0 - fd[td_] * d) - rmse(q0))
        cu += rmse(r0 - fu[tu] * d) <= rmse(r0 - fu[tu] * fit(fu, mu_, K0)) + 1e-12
        cd += rmse(q0 - fd[td_] * d) <= rmse(q0 - fd[td_] * dfit(fd, md_, K0)) + 1e-12
    P(f'  {nm[:1]} δ ' + ' '.join(f'{v:+.2f}' for v in dc) + ' · UCL ' + ' '.join(f'{1000 * v:+.1f}' for v in ru) + f' → {sum(v < 0 for v in ru)}/4 · εγχ. '
      + ' '.join(f'{1000 * v:+.1f}' for v in rd) + f' → {sum(v < 0 for v in rd)}/4 · κοινη ≤ χωριστη: UCL {cu}/4, εγχ. {cd}/4')
D['CAL'], D['POS'] = build_cal(G)
# ---- ΣΗΜΕΡΑ ----
G0 = D['G0']; D['CAL'], D['POS'] = build_cal(G0)
PJ = {m['mid']: m for m in json.load(open('euro_projections.json', encoding='utf-8'))['matches']}
OD = json.load(open('euro_odds_latest.json', encoding='utf-8'))
DALL = {nm: fit(F[nm], FIT, K0) for nm in VER}
P(''); P(f'## ΣΗΜΕΡΑ (δ ολων των σεζον: ' + ' · '.join(f'{nm[:1]} {v:+.2f}' for nm, v in DALL.items())
  + f') · Pinnacle {OD["scanned_at"]} UTC · υπεροχη μοντελου xgh−xga · edge γηπ | φιλοξ στη γραμμη')
for mid in ('6106422', '6106287', '6106234', '6106410'):
    m = PJ[mid]; o = OD['odds'].get(mid); x = next((v for k, v in G0.items() if str(k) == mid), None)
    Fa = feats(int(m['aid']), mid) if x is not None else None
    st, rs = (Fa['streak'], Fa['rest']) if Fa else (0, float('nan'))
    def edges(lh, la):
        dist = sdist(lh, la); L = o['line']; e = []
        for side, ln, od in ((1, L, o['oh']), (-1, -L, o['oa'])):
            pw, pp = cover_q(dist, side, ln) if ln <= -0.5 else picks.p_cover(dist, side, ln); e.append(edge(pw, pp, od))
        return e
    lh, la = m['xgh'], m['xga']; e0 = edges(lh, la); cells = []
    for nm, fn in VER.items():
        f = float(fn(np.array([st]), np.array([rs]))[0]); d = f * DALL[nm]
        e1 = edges(max(lh + d / 2, .05), max(la - d / 2, .05)); cells.append(f'{nm[:1]} {d:+.2f} → {100 * e1[0]:+.0f}|{100 * e1[1]:+.0f}%')
    fmx = 'FM' if m['src_h'] == 'FotMob' and m['src_a'] == 'FotMob' else 'μη-FM'
    P(f'  {m["home"][:11]}–{m["away"][:11]} ({fmx}, σερι {st}, ξεκ {rs:.1f}μ) γρ {o["line"]:+.2f} {o["oh"]:.2f}/{o["oa"]:.2f} · υπερ. {lh - la:+.2f} · '
      f'edge τωρα {100 * e0[0]:+.0f}|{100 * e0[1]:+.0f}% · ' + ' · '.join(cells))
P('σημ.: |γραμμη|<0.5 (PSG 0, Como −0.25) εκτος κανονα χαντικαπ· Sabah μη-FotMob → χαντικαπ δεν παιζεται live· edge φαβ = σωστα τεταρτα, dog = p_cover.')
open('ucl_away3_penalty_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
