# -*- coding: utf-8 -*-
"""el_scorer_timeline_test.py — EUROLEAGUE ΣΥΝΟΛΑ: ΤΟ ΜΟΝΤΕΛΟ «ΞΕΡΕΙ ΤΙ ΙΣΧΥΕΙ» ΣΕ ΚΑΘΕ ΣΤΙΓΜΗ; (27/10/2026, Στελιος «ναι»).
Στοχος (Στελιος): σε ΟΛΟΥΣ τους χρονους το μοντελο να καταλαβαινει τι γινεται — στο ανοιγμα αμφιβολοι με πιθανοτητα (οπως NBA), καθε ξαφνικη
απουσια μπαινει μολις βγει η ειδηση. Η βαση ΔΕΝ αλλαζει: διορθωση μονο για ΝΕΟΥΣ (1-3 ματς) παικτες ≥10 π/μ (μηχανες Α / Β / Ν2-10 του
el_scorer_engine_test).
ΓΝΩΣΗ ΤΗ ΣΤΙΓΜΗ τ ∈ {ανοιγμα, −12ω, −6ω, −3ω, −1ω, τζαμπολ}: σελιδα RotoWire ξαναχτισμενη στο τ (news_state του el_gtd_model_test):
  OUT ×1 · αμφιβολος (i ειδηση αμφιβολος/μαλλον παιζει · ii δεν επαιξε στο προηγουμενο χωρις νεα · iii ειδηση τραυματισμου) × p
  (p = πιθανοτητα να ΛΕΙΨΕΙ, LOSO ανα πηγη × ρολο = PPAGE, οπως το live χαντικαπ απο 23/10) · ΠΑΙΖΕΙ / καμια ενδειξη ×0.
ΜΕΓΕΘΟΣ («φυσικη» της απουσιας): συντελεστης c απο οσους ΠΡΑΓΜΑΤΙ ελειψαν (box), LOSO ανα σεζον· διορθωση τ = c × Σ βαρος_τ × χαρακτηριστικο.
ΜΕΤΡΗΣΕΙΣ ανα τ (ματς με ≥1 νεο σκορερ 10+ με βαρος > 0): μεροληψια = πραγματικο − (μοντελο + διορθωση) · κλιση (πραγμ − μοντελο) πανω
  στη διορθωση (ολα τα ματς, με σταθερα) + θετικη ανα σεζον · αγορα: κινηση Crown ανοιγμα→τ πανω στη μεταβολη της διορθωσης μας, και
  (γραμμη τ − μοντελο) πανω στη διορθωση τ. PICKS ΑΝΟΙΓΜΑΤΟΣ ≥8% (εκει που πονταρουμε): OUT μονο vs OUT + αμφιβολοι×p vs live (OUT + on/off):
  LOSO, walk-forward (c απο προηγουμενες σεζον), placebo (ανακατεμα μεταξυ ματς ιδιας σεζον, 200).
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (γραφτηκαν ΠΡΙΝ το τρεξιμο), ανα μηχανη με αμφιβολους×p: (1) κλιση 0.7-1.3 σε ΟΛΕΣ τις στιγμες ΚΑΙ θετικη ≥4/5 σεζον
  σε ολες · (2) |μεροληψια| ≤ 1 ποντος σε ολες · (3) picks ανοιγματος: walk-forward ≥ live ΚΑΙ placebo < 10%.
Εξοδος: el_scorer_timeline_test_out.txt"""
import os, sys, io, contextlib, time
import numpy as np, pandas as pd
ROOT = r'C:\Users\steli\My Drive\Betting Model'; os.chdir(ROOT)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
T00 = time.time()
src = open('el_scorer_engine_test.py', encoding='utf-8').read().split("VERD = {}")[0]
src = src.replace("def P(s=''): print(s, flush=True); out.append(str(s))", "def P(s=''): pass").replace("def save(): open('el_scorer_engine_test_out.txt'", "def save_(): open('x'")
S = {}
with contextlib.redirect_stdout(_B()): exec(src, S)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open('el_scorer_timeline_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
G = S['G']; rows, ys, YT, YH, YA, SE, HELD_B = S['rows'], S['ys'], S['YT'], S['YH'], S['YA'], S['SE'], S['HELD_B']
recent, onoffO, pts40, LG, picks, fit, apply, loso, wf = (S[k] for k in ('recent', 'onoffO', 'pts40', 'LG', 'picks', 'fit', 'apply', 'loso', 'wf'))
news_state, PPAGE, rolek, PSRC, REC = G['news_state'], G['PPAGE'], G['rolek'], G['PSRC'], G['REC']
N = len(rows); TOT, T0 = S['TOT'], S['T0']; WF4 = np.isin(ys, SE[1:]); rng = np.random.default_rng(7)
ENG = ['Α χαμενοι−αντικαταστατης', 'Β επιθεση με/χωρις', 'Ν2-10']
TAUS = [('ανοιγμα', None), ('−12ω', 12), ('−6ω', 6), ('−3ω', 3), ('−1ω', 1), ('τζαμπολ', 0)]
P(f'el_scorer_timeline_test · Ευρωλιγκα 2021-25 · ματς {N} · φορτωμα {time.time() - T00:.0f} δευτ.')
P('πιθανοτητα να ΛΕΙΨΕΙ (ολες οι σεζον): ' + ' · '.join(f'{src_}/{rk} {PPAGE[("ολα", src_, rk)]:.2f}' for src_ in PSRC for rk in ('βασικος', 'ρολιστας')))
# ---- υποψηφιοι: νεοι (k ≤ 3) με ≥10 π/μ ----
CAND = []                                                      # ανα ματς: [(πλευρα 0/1, ομαδα, p, χαρακτηριστικα [Α, Β, Ν])]
for r in rows:
    L = []
    for si, (own, team) in enumerate(((r['CH'], r['hc']), (r['CA'], r['ac']))):
        for p in own:
            if p['k'] > 3: continue
            rc = recent(r['y'], team, p['pid'], r['ts'])
            if rc is None or rc['ppg'] < 10: continue
            L.append((si, team, p, np.array([max(rc['ppg'] - rc['mpg'] * rc['br'], 0.0), p['w'] * onoffO(p['pid'], r['y'], r['ts']), p['w'] * (pts40(p['pid'], r['ts']) - LG)])))
    CAND.append(L)
P(f'νεοι υποψηφιοι 10+ (τακτικοι): {sum(len(c) for c in CAND)} σε {sum(1 for c in CAND if c)} ματς · χρονος {time.time() - T00:.0f} δευτ.')
def tau_of(r, h):
    return r['op'][0] if h is None else r['ts'] - h * 3600
def weights(r, L, tau, gtd=True):
    st = {}
    for si, team, p, f in L:
        if team not in st: st[team] = news_state(r['y'], team, r['ts'], tau)[1]
    res = []
    for si, team, p, f in L:
        pg_ = st[team].get(p['pid']); ps = pg_[0] if pg_ else (None if p['pprev'] else 'ii')
        w = 1.0 if ps == 'OUT' else ((PPAGE[(r['y'], ps, rolek(p))] if gtd else 0.0) if ps in PSRC else 0.0)
        res.append(w)
    return res
def feat_mat(Wl):                                              # → XH, XA [N × 3]
    XH, XA = np.zeros((N, 3)), np.zeros((N, 3))
    for j, (L, W_) in enumerate(zip(CAND, Wl)):
        for (si, team, p, f), w in zip(L, W_):
            (XH if si == 0 else XA)[j] += w * f
    return XH, XA
BOX = [[0.0 if p['played'] else 1.0 for si, team, p, f in L] for L in CAND]
XBH, XBA = feat_mat(BOX)
WT = {lab: [weights(r, L, tau_of(r, h)) if L else [] for r, L in zip(rows, CAND)] for lab, h in TAUS}
WO = [weights(r, L, tau_of(r, None), gtd=False) if L else [] for r, L in zip(rows, CAND)]
P(f'σελιδες ξαναχτιστηκαν σε 6 στιγμες · χρονος {time.time() - T00:.0f} δευτ.')
# συντελεστες απο box: LOSO (για καθε σεζον) & walk-forward
CL = {e: {s: float(fit(XBH[:, j], XBA[:, j], ys != s)[0]) for s in SE} for j, e in enumerate(ENG)}
CW = {e: {s: float(fit(XBH[:, j], XBA[:, j], np.isin(ys, SE[:i]))[0]) for i, s in enumerate(SE[1:], 1)} for j, e in enumerate(ENG)}
P('συντελεστες απο οσους ΠΡΑΓΜΑΤΙ ελειψαν (LOSO ανα σεζον-τεστ): ' + ' │ '.join(f"{e} " + ' '.join(f'{s[-2:]}:{CL[e][s]:+.3f}' for s in SE) for e in ENG))
def corr(XH, XA, j, C):
    c = np.array([C.get(s, np.nan) for s in ys]); return c * (XH[:, j] + XA[:, j])
Y = TOT - T0
def mkt(r, h):
    d = REC[23].get(r['pos'])
    if d is None: return np.nan, np.nan
    x = d['open'] if h is None else (d.get(h) or d['open'])
    return x[1], d['open'][1]
MK = {lab: np.array([mkt(r, h) for r in rows]) for lab, h in TAUS}
P(f'\n## ΑΝΑ ΣΤΙΓΜΗ (αμφιβολοι × p): ματς με βαρος > 0 · πραγμ − μοντελο · διορθωση · μεροληψια (πραγμ − μοντελο − διορθ.) · κλιση (θετ. σεζον) · αγορα')
RES = {e: {} for e in ENG}; CORR0 = {}
for lab, h in TAUS:
    XH, XA = feat_mat(WT[lab]); m = (XH.sum(1) + XA.sum(1)) != 0
    m = np.array([any(w > 0 for w in W_) for W_ in WT[lab]])
    nout = sum(1 for W_ in WT[lab] for w in W_ if w == 1.0); ngtd = sum(1 for W_ in WT[lab] for w in W_ if 0 < w < 1)
    P(f'\n  {lab:8s}: ματς {int(m.sum()):4d} (OUT παικτες {nout}, αμφιβολοι {ngtd}) · πραγμ − μοντελο {np.mean(Y[m]):+5.2f} · '
      f'κινηση αγορας ανοιγμα→τ {np.nanmean((MK[lab][:, 0] - MK[lab][:, 1])[m]):+5.2f} (υπολοιπα ματς {np.nanmean((MK[lab][:, 0] - MK[lab][:, 1])[~m]):+5.2f})')
    for j, e in enumerate(ENG):
        c = corr(XH, XA, j, CL[e]);
        if lab == 'ανοιγμα': CORR0[e] = c
        A_ = np.c_[np.ones(N), c]; b = np.linalg.lstsq(A_, Y, rcond=None)[0][1]
        bs = [np.linalg.lstsq(A_[ys == s], Y[ys == s], rcond=None)[0][1] for s in SE]
        bias = float(np.mean(Y[m] - c[m]))
        dm = MK[lab][:, 0] - MK[lab][:, 1]; dc = c - CORR0[e]; ok = ~np.isnan(dm) & (np.abs(dc) > 1e-9)
        km = np.polyfit(dc[ok], dm[ok], 1)[0] if ok.sum() > 10 else np.nan
        lv = MK[lab][:, 0] - T0; ok2 = ~np.isnan(lv); kl = np.linalg.lstsq(np.c_[np.ones(ok2.sum()), c[ok2]], lv[ok2], rcond=None)[0][1]
        RES[e][lab] = dict(b=b, pos=sum(x > 0 for x in bs), bias=bias)
        P(f'     {e:26s} διορθ. {np.mean(c[m]):+5.2f} · μεροληψια {bias:+5.2f} · κλιση {b:4.2f} (' + ' '.join(f'{x:+.1f}' for x in bs) + f', θετ {sum(x > 0 for x in bs)}/5)'
          f' · αγορα: γραμμη τ πανω στη διορθ. {kl:4.2f} · κινηση ανοιγμα→τ πανω στη μεταβολη διορθ. {km:4.2f} ({int(ok.sum())} ματς)')
save()
# ---- picks ανοιγματος ----
P(f'\n## PICKS ΑΝΟΙΓΜΑΤΟΣ ≥8% (Crown) — LOSO / walk-forward 2022-25 / placebo')
F4 = [G['featB'](r, 'N', 'G0') for r in rows]; X4H = np.array([f[0] for f in F4]); X4A = np.array([f[1] for f in F4])
live_l, live_w = HELD_B[('N', 'G0')], wf(X4H, X4A)
XoH, XoA = feat_mat(WO); XgH, XgA = feat_mat(WT['ανοιγμα'])
def line(lab, hl, hw):
    sd, u = picks(hl); sw, uw = picks(hw); ps = pd.Series(u[sd != 0]).groupby(ys[sd != 0]).sum()
    P(f'  {lab:40s} picks {int((sd != 0).sum()):4d} · LOSO {u.sum():+6.1f}μ ({int((ps > 0).sum())}/5: ' + ' '.join(f'{s[-2:]}:{ps.get(s, 0):+.1f}' for s in SE)
      + f') · walk-forward {uw[WF4].sum():+6.1f}μ')
    return u.sum(), uw[WF4].sum()
line('χωρις διορθωση', np.zeros(N), np.zeros(N)); LV = line('live: OUT + on/off', live_l, live_w)
PK = {}
for j, e in enumerate(ENG):
    line(f'{e} · μονο OUT', corr(XoH, XoA, j, CL[e]), np.nan_to_num(corr(XoH, XoA, j, CW[e])))
    hl = corr(XgH, XgA, j, CL[e]); u_l, u_w = line(f'{e} · OUT + αμφιβολοι×p', hl, np.nan_to_num(corr(XgH, XgA, j, CW[e])))
    a, b = XgH[:, j].copy(), XgA[:, j].copy(); vals = []
    for _ in range(200):
        pa, pb = a.copy(), b.copy()
        for s in SE:
            idx = np.where(ys == s)[0]; pm = rng.permutation(idx); pa[idx] = a[pm]; pb[idx] = b[pm]
        c = np.array([CL[e][s] for s in ys]); vals.append(picks(c * (pa + pb))[1].sum())
    PK[e] = dict(u=u_l, wf=u_w, plc=float(np.mean(np.array(vals) >= u_l)))
    P(f'  {"":40s} placebo μεσος {np.mean(vals):+.1f} (95% {np.percentile(vals, 95):+.1f}) · P {100 * PK[e]["plc"]:.1f}%')
P(f'\n## ΚΡΙΣΗ (προ-δηλωμενη, αμφιβολοι × p)')
for e in ENG:
    t = {'κλιση 0.7-1.3 παντου': all(0.7 <= RES[e][l]['b'] <= 1.3 for l, _ in TAUS), 'θετικη ≥4/5 παντου': all(RES[e][l]['pos'] >= 4 for l, _ in TAUS),
         '|μεροληψια| ≤ 1 παντου': all(abs(RES[e][l]['bias']) <= 1 for l, _ in TAUS), 'WF ≥ live': PK[e]['wf'] >= LV[1], 'placebo < 10%': PK[e]['plc'] < .10}
    P(f'  {e:26s} ' + ' · '.join(f"{k} {'✓' if v else '✗'}" for k, v in t.items()) + f" → {'ΠΕΡΝΑ' if all(t.values()) else 'δεν περνα'}")
P(f'\nχρονος {time.time() - T00:.0f} δευτ.'); save()
