# -*- coding: utf-8 -*-
"""el_index_build_test.py — ΕΥΡΩΛΙΓΚΑ ΒΗΜΑΤΑ 2-3: δικος μας δεικτης παικτη (box + «διορθωμενο» on/off), ΕΠΙΘΕΣΗ (O) / ΑΜΥΝΑ (D),
walk-forward, και τεστ στα ΣΥΝΟΛΑ (23/10/2026). Δεν αγγιζει κανενα live αρχειο.

ΔΕΔΟΜΕΝΑ: el_pbp_stints.pkl (απο el_rapm_build.py: κομματια πενταδων + box ανα παικτη/ματς, E2016-E2026), el_players.json (ωρες/αγωνιστικες).
ΒΗΜΑ 2 — BOX ΔΕΙΚΤΗΣ:
  15 ρυθμοι ανα 100 κατοχες «ομαδας-στο-γηπεδο» (κατοχες μεσα = (κατ. δικες + κατ. αντιπαλου)/2 στα κομματια που ειναι μεσα):
  ευστ.2, αστ.2, ευστ.3, αστ.3, ευστ.βολες, αστ.βολες, επιθ.ριμπ, αμυντ.ριμπ, ασιστ, κλεψ, λαθη, κοψ., κοψ.που δεχτηκε, φαουλ, φαουλ που κερδισε.
  Στοχος = RAPM 3 σεζον μαζι (παραθυρο s-2..s, λ 8000, χωρις prior), O και D χωριστα, γραμμικη παλινδρομηση με σταθερο, βαρος λεπτα,
  δειγμα παικτες ≥300′ στο παραθυρο. Για τη σεζον S οι συντελεστες (C_S) εκτιμωνται ΜΟΝΟ απο παραθυρα που τελειωνουν ≤ S−1.
  Στην εφαρμογη ο ρυθμος μαζευεται προς τον μεσο: (Σ στατ + 300·μεσος)/(Σ κατοχες + 300) (300 κατοχες ψευδο-δειγμα).
ΒΗΜΑ 3 — ΣΥΝΔΥΑΣΜΟΣ: ridge RAPM με prior = box: λυση για δ = β − box με y' = y − X·box (η εδρα με prior 0).
  Δεδομενα = περσινη σεζον (βαρος w_prev ∈ {0.3, 0.6}) + φετινη ΜΟΝΟ πριν το σημειο υπολογισμου, λ ∈ {1000, 3000, 8000}.
  Το box του prior υπολογιζεται απο τα ιδια δεδομενα (περσι×w_prev + φετος ως τωρα) με C_S.
  Walk-forward: σημεια υπολογισμου καθε 28 μερες (00:00 UTC) απο την ημερα του 1ου ματς· ματς μετα το σημειο k παιρνει τις τιμες του k.
  Στην αρχη (καμια φετινη) = περσινα + box. Παικτης χωρις κανενα κομματι Ευρωλιγκας στα δεδομενα → 0 (καμια καλυψη).
  Πληροφοριακα: «box μονο» (w_prev 0.3/0.6) και «RAPM χωρις box» (w_prev 0.6, λ 8000).
ΣΤΑΘΕΡΟΤΗΤΑ (πριν απο το στοιχημα): τελικη τιμη S ↔ S+1, παικτες ≥500′ και στις δυο, ζευγαρια E2017→18 … E2024→25:
  O, D, καθαρο (O − D) για box, συνδυασμο (και «μονο φετινα», w_prev 0, για να μην υπαρχει επικαλυψη δεδομενων S στις δυο τιμες).
  Αναφορα (ιδια ζευγαρια): PIR/40, απλο on/off, RAPM λ8000 μιας σεζον.
  Προβλεψη: τιμη στην ΑΡΧΗ της S+1 → RAPM λ8000 ολοκληρης της S+1 (συσχετιση) για box / συνδυασμο / PIR / απλο on/off / RAPM S.
ΤΕΣΤ ΣΤΑ ΣΥΝΟΛΑ: ιδιο στησιμο με el_absence_onoff_test.py W4 (εκτελειται ο κωδικας του ως εχει, με μονη προσθηκη το pid του αποντα
  και τα κλειδια του ματς)· ΠΡΩΤΑ αναπαραγωγη R0 = 511 picks, +59.0μ, ROI +11.5%, RMSE 16.523 — αλλιως STOP.
  Αλλαζουν ΜΟΝΟ τα (onO, onD) των αποντων: onO := O του δεικτη, onD := D (+ = δεχεται περισσοτερα) απο το τελευταιο σημειο υπολογισμου
  ΠΡΙΝ το ματς· διαιρεση με την τυπ. αποκλιση του δικου μας (στις απουσιες με καλυψη), χωρις καλυψη = 0. Απουσια/τακτικος/g(k) ιδια.
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (γραφτηκαν ΠΡΙΝ απο το τρεξιμο):
  (1) ΣΤΑΘΕΡΟΤΗΤΑ: συνδυασμος (εκδοχη LOSO) S→S+1 καθαρο ≥ PIR/40 (ιδια ζευγαρια) Ή τουλαχιστον D ≥ 0.36·
      αλλιως σημειωνεται «δεν περνα σταθεροτητα», αλλα το τεστ τρεχει για πληροφορια.
  (2) ΑΝΤΙΚΑΘΙΣΤΑ το live (R0) αν: LOSO RMSE συνολου καλυτερο απο R0 σε ≥4/5 σεζον ΚΑΙ μοναδες ≥ R0 ΚΑΙ θετικες σεζον ≥4/5.
      w_prev και λ επιλεγονται LOSO με RMSE (για την κρατημενη σεζον Y: η εκδοχη με το μικροτερο RMSE στις αλλες 4).
Εξοδος: el_index_build_test_out.txt · el_onoff_variants_beta.pkl (εκδοχη → DataFrame ανα ματς)."""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ[_v] = '1'   # αλλιως ο BLAS «πνιγεται» (10 δευτ. ανα λυση)
import sys, io, json, pickle, collections, contextlib, time, math
import numpy as np, pandas as pd
from scipy.sparse import coo_matrix
import scipy.linalg as SL
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
sys.stdout.reconfigure(encoding='utf-8')
T0 = time.time()
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open(os.path.join(ROOT, 'el_index_build_test_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))

# ================= ΔΕΔΟΜΕΝΑ =================
C = pickle.load(open('el_pbp_stints.pkl', 'rb'))
PL = json.load(open('el_players.json', encoding='utf-8'))
FE = ['ευστ2', 'αστ2', 'ευστ3', 'αστ3', 'ευστΒ', 'αστΒ', 'επιθΡ', 'αμυνΡ', 'ασιστ', 'κλεψ', 'λαθη', 'κοψ', 'κοψΔεχ', 'φαουλ', 'φαουλΚερδ']
NF = len(FE)
PID = {}; PIDS = []
def gid(p):
    if p not in PID: PID[p] = len(PIDS); PIDS.append(p)
    return PID[p]
NAME = {}
GD = {}
for k, g in C.items():
    NAME.update(g['name'])
    off, dff, hm, yy, ww = [], [], [], [], []
    pon = collections.Counter()
    for h5, a5, ph, pa, qh, qa, sec in g['stints']:
        for o, d_, pts, poss, ih in ((h5, a5, ph, qh, 1), (a5, h5, pa, qa, 0)):
            if poss <= 0: continue
            off.append([gid(p) for p in o]); dff.append([gid(p) for p in d_]); hm.append(ih); yy.append(100 * pts / poss); ww.append(poss)
        av = (qh + qa) / 2
        for p in h5 + a5: pon[p] += av
    ps = {}
    for pid, v in g['box'].items():
        if pon.get(pid, 0) <= 0: continue
        vec = np.array([v['FieldGoalsMade2'], v['FieldGoalsAttempted2'] - v['FieldGoalsMade2'], v['FieldGoalsMade3'], v['FieldGoalsAttempted3'] - v['FieldGoalsMade3'],
                        v['FreeThrowsMade'], v['FreeThrowsAttempted'] - v['FreeThrowsMade'], v['OffensiveRebounds'], v['DefensiveRebounds'], v['Assistances'],
                        v['Steals'], v['Turnovers'], v['BlocksFavour'], v['BlocksAgainst'], v['FoulsCommited'], v['FoulsReceived'],
                        pon[pid], v['sec'] / 60, v['val']], float)
        ps[gid(pid)] = (vec, v['team'])
    pk = PL.get(k)
    ts = pd.Timestamp(pk['utc']).tz_localize(None).timestamp() if pk else None
    GD[k] = dict(season=g['season'], ts=ts, H=g['H'], A=g['A'], off=np.array(off, int).reshape(-1, 5), dff=np.array(dff, int).reshape(-1, 5),
                 home=np.array(hm, float), y=np.array(yy), w=np.array(ww), ps=ps, stints=g['stints'])
SEAS = sorted({g['season'] for g in GD.values()})
BYS = {s: sorted([k for k, g in GD.items() if g['season'] == s], key=lambda k: (GD[k]['ts'] or 0, k)) for s in SEAS}
prevS = {s: SEAS[i - 1] for i, s in enumerate(SEAS) if i > 0}
P(f'ματς {len(GD)} · παικτες {len(PIDS)} · σεζον {SEAS}')

# ================= RAPM (κανονικες εξισωσεις) =================
def rapm(gw, lam, prior=None):
    """gw: λιστα (κλειδι ματς, πολλαπλασιαστης βαρους). prior: συναρτηση gid -> (O, D) ή None. Επιστρεφει dict gid -> (O, D), εδρα."""
    gw = [(k, m) for k, m in gw if m > 0 and len(GD[k]['y'])]
    if not gw: return {}, 0.0
    off = np.concatenate([GD[k]['off'] for k, _ in gw]); dff = np.concatenate([GD[k]['dff'] for k, _ in gw])
    hm = np.concatenate([GD[k]['home'] for k, _ in gw]); y = np.concatenate([GD[k]['y'] for k, _ in gw])
    w = np.concatenate([GD[k]['w'] * m for k, m in gw])
    mu = np.average(y, weights=w)
    pl = np.unique(np.concatenate([off.ravel(), dff.ravel()])); n = len(pl)
    loc = {p: i for i, p in enumerate(pl)}
    lo = np.vectorize(loc.get)(off); ld = np.vectorize(loc.get)(dff) + n
    r = len(y); R = np.repeat(np.arange(r), 5)
    rows = np.concatenate([R, R, np.arange(r)[hm > 0]]); cols = np.concatenate([lo.ravel(), ld.ravel(), np.full(int((hm > 0).sum()), 2 * n)])
    X = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(r, 2 * n + 1)).tocsr()
    A = (X.T @ X.multiply(w[:, None])).toarray(); b = X.T @ (w * (y - mu))
    p0 = np.zeros(2 * n + 1)
    if prior is not None:
        for i, p in enumerate(pl): p0[i], p0[n + i] = prior(p)
        b = b - A @ p0
    delta = SL.cho_solve(SL.cho_factor(A + lam * np.eye(2 * n + 1)), b); beta = p0 + delta
    return {p: (beta[i], beta[n + i]) for i, p in enumerate(pl)}, beta[2 * n]
def agg(gw):
    """αθροισμα box ανα παικτη: gid -> [15 στατ, κατοχες μεσα, λεπτα, PIR]."""
    S = {}
    for k, m in gw:
        if m <= 0: continue
        for p, (vec, tm) in GD[k]['ps'].items():
            if p in S: S[p] += vec * m
            else: S[p] = vec * m
    return S
def team_last(keys):
    T = {}
    for k in keys:
        for p, (vec, tm) in GD[k]['ps'].items(): T[p] = tm
    return T

# ================= ΒΗΜΑ 2: box συντελεστες =================
WIN = {}
P(''); P('ΒΗΜΑ 2 — RAPM 3 σεζον (λ 8000) ανα παραθυρο-στοχο:')
for i, s in enumerate(SEAS[:-2]):            # παραθυρα που τελειωνουν E2016 … E2024 (E2025 δεν χρειαζεται: test ως E2025)
    ss = SEAS[max(0, i - 2): i + 1]
    gw = [(k, 1.0) for x in ss for k in BYS[x]]
    R, h = rapm(gw, 8000); A_ = agg(gw)
    WIN[s] = (R, A_)
    P(f'  παραθυρο {ss[0]}–{s}: ματς {len(gw)} · παικτες {len(R)} · εδρα {h:+.2f}')
def train_box(S):
    """C_S: απο παραθυρα με τελος < S."""
    Xs, yO, yD, wt = [], [], [], []
    for s, (R, A_) in WIN.items():
        if s >= S: continue
        for p, v in A_.items():
            if v[16] < 300 or v[15] <= 0 or p not in R: continue
            Xs.append(100 * v[:NF] / v[15]); yO.append(R[p][0]); yD.append(R[p][1]); wt.append(v[16])
    X = np.c_[np.ones(len(Xs)), np.array(Xs)]; wt = np.array(wt); sw = np.sqrt(wt)
    bO = np.linalg.lstsq(X * sw[:, None], np.array(yO) * sw, rcond=None)[0]; bD = np.linalg.lstsq(X * sw[:, None], np.array(yD) * sw, rcond=None)[0]
    tot = np.sum([WIN[s][1][p] for s in WIN if s < S for p in WIN[s][1]], axis=0)
    lg = tot[:NF] / tot[15]                                   # μεσος ρυθμος ανα κατοχη
    fO = X @ bO; fD = X @ bD
    r2O = 1 - np.average((np.array(yO) - fO) ** 2, weights=wt) / np.average((np.array(yO) - np.average(yO, weights=wt)) ** 2, weights=wt)
    r2D = 1 - np.average((np.array(yD) - fD) ** 2, weights=wt) / np.average((np.array(yD) - np.average(yD, weights=wt)) ** 2, weights=wt)
    return dict(bO=bO, bD=bD, lg=lg, n=len(Xs), r2O=r2O, r2D=r2D)
KBOX = 300.0
COEF = {S: train_box(S) for S in SEAS[1:-1]}       # E2017 … E2025
def boxval(v, cf):
    rate = 100 * (v[:NF] + KBOX * cf['lg']) / (v[15] + KBOX)
    return float(cf['bO'][0] + rate @ cf['bO'][1:]), float(cf['bD'][0] + rate @ cf['bD'][1:])
P(''); P('ΣΥΝΤΕΛΕΣΤΕΣ BOX (C_E2025 = εκπαιδευση σε παραθυρα ως E2024): ποντοι/100 κατοχες RAPM ανα +1 γεγονος ανα 100 κατοχες μεσα')
P('  (O + = η ομαδα σκοραρει περισσοτερο · D + = ο αντιπαλος σκοραρει περισσοτερο = ΚΑΚΗ αμυνα) · «ιδιο προσημο» = στα 9 folds C_E2017…C_E2025')
cf = COEF['E2025']
P(f'  {"στατιστικο":12s} {"O":>7s} {"D":>7s}   ιδιο προσ. O · D   μεσος ρυθμος/100')
for j, nm in enumerate(FE):
    sO = sum(np.sign(COEF[S]['bO'][j + 1]) == np.sign(cf['bO'][j + 1]) for S in COEF); sD = sum(np.sign(COEF[S]['bD'][j + 1]) == np.sign(cf['bD'][j + 1]) for S in COEF)
    P(f'  {nm:12s} {cf["bO"][j + 1]:+7.3f} {cf["bD"][j + 1]:+7.3f}   {sO}/9 · {sD}/9         {100 * cf["lg"][j]:5.1f}')
P(f'  σταθερος     {cf["bO"][0]:+7.2f} {cf["bD"][0]:+7.2f}')
P('  R² (σταθμ. λεπτα, εντος δειγματος) ανα fold: ' + ' · '.join(f'{S[-2:]}: O {COEF[S]["r2O"]:.2f} D {COEF[S]["r2D"]:.2f} (n {COEF[S]["n"]})' for S in COEF))
save()

# ================= ΒΗΜΑ 3: walk-forward =================
WPREV = (0.3, 0.6); LAMS = (1000, 3000, 8000)
CVARS = [f'Σ w{w} λ{l}' for w in WPREV for l in LAMS]
XVARS = CVARS + ['box μονο w0.3', 'box μονο w0.6', 'RAPM χωρις box w0.6 λ8000']
def estimate(S, cut, var):
    """τιμες στο σημειο cut (timestamp, None = ολη η σεζον) για σεζον S. gid -> (O, D)."""
    cur = [k for k in BYS[S] if cut is None or (GD[k]['ts'] is not None and GD[k]['ts'] < cut)]
    cf = COEF[S]
    if var.startswith('Σ'):
        w = float(var.split('w')[1].split()[0]); lam = float(var.split('λ')[1])
    elif var.startswith('box'):
        w = float(var.split('w')[1]); lam = None
    elif var.startswith('RAPM'):
        w, lam = 0.6, 8000.0
    elif var.startswith('φετ'):                       # «μονο φετινα» (σταθεροτητα χωρις επικαλυψη)
        w = 0.0; lam = float(var.split('λ')[1])
    gw = ([(k, w) for k in BYS[prevS[S]]] if w > 0 else []) + [(k, 1.0) for k in cur]
    A_ = agg(gw)
    if var.startswith('box'):
        return {p: boxval(v, cf) for p, v in A_.items() if v[15] > 0}
    if var.startswith('RAPM'):
        return rapm(gw, lam)[0]
    BX = {p: boxval(v, cf) for p, v in A_.items() if v[15] > 0}
    return rapm(gw, lam, prior=lambda p: BX.get(p, (0.0, 0.0)))[0]
# σημεια υπολογισμου
CPS = {}
for S in SEAS[1:-1]:
    tss = [GD[k]['ts'] for k in BYS[S] if GD[k]['ts'] is not None]
    d0 = pd.Timestamp(min(tss), unit='s').normalize().timestamp(); cps = []
    while d0 <= max(tss): cps.append(d0); d0 += 28 * 86400
    CPS[S] = cps
TEST = ['E2021', 'E2022', 'E2023', 'E2024', 'E2025']
P(''); P('ΣΗΜΕΙΑ ΥΠΟΛΟΓΙΣΜΟΥ (καθε 28 μερες): ' + ' · '.join(f'{S}: {len(CPS[S])}' for S in TEST))
VAL = {}                     # (var, S, k) -> dict
for S in TEST:
    for var in XVARS:
        for k, cp in enumerate(CPS[S]): VAL[(var, S, k)] = estimate(S, cp, var)
    P(f'  walk-forward {S} ετοιμο ({time.time() - T0:.0f} δευτ.)')
save()

# ================= ΣΤΑΘΕΡΟΤΗΤΑ =================
def season_ref(S):
    keys = BYS[S]; A_ = agg([(k, 1.0) for k in keys]); TM = team_last(keys)
    mins = {p: v[16] for p, v in A_.items()}; pir = {p: v[17] / v[16] * 40 for p, v in A_.items() if v[16] > 0}
    onp = collections.defaultdict(lambda: np.zeros(4)); tt = collections.defaultdict(lambda: np.zeros(4))
    for k in keys:
        g = GD[k]
        for h5, a5, ph, pa, qh, qa, sec in g['stints']:
            for p in h5: onp[gid(p)] += (ph, qh, pa, qa)
            for p in a5: onp[gid(p)] += (pa, qa, ph, qh)
            tt[g['H']] += (ph, qh, pa, qa); tt[g['A']] += (pa, qa, ph, qh)
    oo = {}
    for p, o in onp.items():
        t = tt[TM.get(p)]; f = t - o
        if o[1] > 50 and f[1] > 50: oo[p] = (100 * o[0] / o[1] - 100 * o[2] / o[3]) - (100 * f[0] / f[1] - 100 * f[2] / f[3])
    R8 = rapm([(k, 1.0) for k in keys], 8000)[0]
    return dict(mins=mins, pir=pir, onoff=oo, R8=R8, team=TM)
REF = {S: season_ref(S) for S in SEAS[:-1]}
FINAL = {}; START = {}
SVARS = CVARS + ['box μονο w0.3', 'box μονο w0.6', 'φετινα μονο λ1000', 'φετινα μονο λ3000', 'φετινα μονο λ8000', 'box φετινα μονο']
for S in SEAS[1:-1]:
    for var in SVARS:
        if var == 'box φετινα μονο':
            A_ = agg([(k, 1.0) for k in BYS[S]]); FINAL[(var, S)] = {p: boxval(v, COEF[S]) for p, v in A_.items() if v[15] > 0}
        else: FINAL[(var, S)] = estimate(S, None, var)
    for var in CVARS + ['box μονο w0.3', 'box μονο w0.6']:
        START[(var, S)] = estimate(S, CPS[S][0], var)
P(f'  τελικες/αρχικες τιμες ετοιμες ({time.time() - T0:.0f} δευτ.)')
PAIRS = [(SEAS[i], SEAS[i + 1]) for i in range(1, len(SEAS) - 2)]          # E2017→18 … E2024→25
def corr(u, v):
    m = [i for i in range(len(u)) if u[i] is not None and v[i] is not None]
    return np.corrcoef([u[i] for i in m], [v[i] for i in m])[0, 1] if len(m) > 10 else np.nan
def ppl(a, b): return [p for p in REF[a]['mins'] if REF[a]['mins'][p] >= 500 and REF[b]['mins'].get(p, 0) >= 500]
P(''); P('################ ΣΤΑΘΕΡΟΤΗΤΑ: συσχετιση τελικης τιμης σεζον S ↔ S+1 (παικτες ≥500′ και στις δυο) ################')
P('  ζευγαρια: ' + ' '.join(f'{a[-2:]}→{b[-2:]}' for a, b in PAIRS) + ' · n παικτες: ' + ' '.join(str(len(ppl(a, b))) for a, b in PAIRS))
def stab(getter):
    cs = [corr([getter(a, p) for p in ppl(a, b)], [getter(b, p) for p in ppl(a, b)]) for a, b in PAIRS]
    return np.nanmean(cs), cs
STAB = {}
def g_ref(f): return lambda S, p: REF[S][f].get(PID_OF(p))
PID_OF = lambda p: p
P(f'  {"δεικτης":32s} {"μεσος":>6s} · ανα ζευγαρι')
for lab, gtr in (('PIR/40 (καθαρο)', lambda S, p: REF[S]['pir'].get(p)), ('απλο on/off (καθαρο)', lambda S, p: REF[S]['onoff'].get(p)),
                 ('RAPM λ8000 1 σεζον — καθαρο', lambda S, p: (lambda r: r[0] - r[1] if r else None)(REF[S]['R8'].get(p))),
                 ('RAPM λ8000 1 σεζον — O', lambda S, p: (lambda r: r[0] if r else None)(REF[S]['R8'].get(p))),
                 ('RAPM λ8000 1 σεζον — D', lambda S, p: (lambda r: r[1] if r else None)(REF[S]['R8'].get(p)))):
    m, cs = stab(gtr); STAB[lab] = m
    P(f'  {lab:32s} {m:+6.2f} · ' + ' '.join(f'{c:+.2f}' for c in cs))
for var in SVARS:
    for part, fn in (('O', lambda r: r[0]), ('D', lambda r: r[1]), ('καθαρο', lambda r: r[0] - r[1])):
        m, cs = stab(lambda S, p, var=var, fn=fn: (lambda r: fn(r) if r else None)(FINAL[(var, S)].get(p)))
        STAB[(var, part)] = m
        P(f'  {var + " — " + part:32s} {m:+6.2f} · ' + ' '.join(f'{c:+.2f}' for c in cs))
P('  ΣΗΜ.: στις εκδοχες με w_prev η τελικη τιμη της S+1 περιεχει τα δεδομενα της S (×w_prev) → μερος της συσχετισης ειναι μηχανικο· τα «φετινα μονο» δεν εχουν επικαλυψη.')
P(''); P('################ ΠΡΟΒΛΕΨΗ: τιμη στην ΑΡΧΗ της S+1 → RAPM λ8000 ολοκληρης της S+1 (συσχετιση, παικτες ≥500′ σε S και S+1) ################')
P(f'  {"δεικτης στην αρχη της S+1":36s} {"O":>6s} {"D":>6s} {"καθαρο":>7s} · καθαρο ανα S+1 (' + ' '.join(b[-2:] for a, b in PAIRS) + ')')
def pred_row(lab, getter):
    res = {}
    for part, fn in (('O', lambda r: r[0]), ('D', lambda r: r[1]), ('N', lambda r: r[0] - r[1])):
        cs = []
        for a, b in PAIRS:
            ps = ppl(a, b); tgt = [(lambda r: fn(r) if r else None)(REF[b]['R8'].get(p)) for p in ps]
            u = [getter(a, b, p) for p in ps]
            u = [(fn(x) if isinstance(x, tuple) else (x if part == 'N' else None)) if x is not None else None for x in u]
            cs.append(corr(u, tgt))
        res[part] = (np.nanmean(cs) if not all(np.isnan(cs)) else np.nan, cs)
    P(f'  {lab:36s} ' + ' '.join(f'{res[x][0]:+6.2f}' if not np.isnan(res[x][0]) else '     —' for x in ('O', 'D')) + f' {res["N"][0]:+7.2f} · ' + ' '.join(f'{c:+.2f}' for c in res['N'][1]))
    return res
PRED = {}
PRED['PIR/40 S'] = pred_row('PIR/40 της S', lambda a, b, p: REF[a]['pir'].get(p))
PRED['onoff S'] = pred_row('απλο on/off της S', lambda a, b, p: REF[a]['onoff'].get(p))
PRED['RAPM S'] = pred_row('RAPM λ8000 της S', lambda a, b, p: REF[a]['R8'].get(p))
for var in ['box μονο w0.3', 'box μονο w0.6'] + CVARS:
    PRED[var] = pred_row(var, lambda a, b, p, var=var: START[(var, b)].get(p))
save()

# ================= ΤΕΣΤ ΣΤΑ ΣΥΝΟΛΑ =================
P(''); P('################ ΤΕΣΤ ΣΤΑ ΣΥΝΟΛΑ (στησιμο el_absence_onoff_test.py W4) ################')
src = open('el_absence_onoff_test.py', encoding='utf-8').read().split('# ---- ΧΑΝΤΙΚΑΠ ----')[0]
a1 = "res.append(dict(w=w, **(pr or dict(onO=0.0, onD=0.0, usg=None))))"; a2 = "rows.append(dict(y=sea,"
assert src.count(a1) == 1 and src.count(a2) == 1
src = src.replace(a1, "res.append(dict(w=w, pid=pid, **(pr or dict(onO=0.0, onD=0.0, usg=None))))").replace(a2, "rows.append(dict(hc=hc, ac=ac, ts=ts, y=sea,")
class _B(io.StringIO):
    def reconfigure(self, **k): pass
NS = {}
with contextlib.redirect_stdout(_B()):
    exec(src, NS)
sys.stdout.reconfigure(encoding='utf-8')
rows, SE, ys, YT, YH, YA = NS['rows'], NS['SE'], NS['ys'], NS['YT'], NS['YH'], NS['YA']
rmse, tp, ALL = NS['rmse'], NS['tp'], NS['ALL']
H_R0 = NS['HELD']['W4 μονο on/off']
u_chk, s_chk = NS['tpicks'](H_R0)
P(f'ΑΝΑΠΑΡΑΓΩΓΗ R0 (W4 live): ματς {len(rows)} · RMSE {rmse(YT - H_R0, ALL):.3f} · {s_chk}')
ok_rep = len(rows) == 1563 and abs(rmse(YT - H_R0, ALL) - 16.523) < 0.0006 and abs(u_chk - 59.0) < 0.06 and s_chk.strip().startswith('511 picks')
if not ok_rep:
    P('  !!! ΔΕΝ αναπαραγεται το R0 — STOP'); save(); sys.exit(1)
P('  ✓ αναπαραγεται (1563 ματς, 511 picks, +59.0μ, RMSE 16.523)')
# στοιχεια ματς: code/αγωνιστικη
PLIDX = collections.defaultdict(list)
for k, g in PL.items(): PLIDX[(g['season'], g['hcode'], g['acode'])].append((pd.Timestamp(g['utc']).tz_localize(None).timestamp(), g['code'], g.get('rnd')))
for r in rows:
    c = [x for x in PLIDX[(r['y'], r['hc'], r['ac'])] if abs(x[0] - r['ts']) < 86400]
    r['code'], r['rnd'] = (c[0][1], c[0][2]) if c else (None, None)
P(f'  ματς με code/αγωνιστικη: {sum(r["code"] is not None for r in rows)}/{len(rows)}')
def cp_of(S, ts):
    k = max([i for i, c in enumerate(CPS[S]) if c <= ts], default=0); return k
def our(var, r, p):
    v = VAL[(var, r['y'], cp_of(r['y'], r['ts']))].get(PID.get(p['pid'], -1)); return v
# καλυψη + sd
COV = {}; SDV = {}
allabs = [(r, p) for r in rows for p in r['ah'] + r['aa']]
for var in XVARS:
    vals = [our(var, r, p) for r, p in allabs]
    cv = [v for v in vals if v is not None]; COV[var] = len(cv) / len(vals)
    SDV[var] = (float(np.std([v[0] for v in cv])), float(np.std([v[1] for v in cv])))
P(f'  απουσιες (παικτης-ματς) {len(allabs)} · καλυψη R0 (περσινο προφιλ 3StepsBasket) {np.mean([p["usg"] is not None for r, p in allabs]):.0%}')
P(f'  R0 τυπ. αποκλιση (ποντοι/100 κατοχες): onO {NS["SD"]["onO"]:.2f} · onD {NS["SD"]["onD"]:.2f}')
for var in XVARS: P(f'  {var:28s} καλυψη {COV[var]:.0%} · τυπ. αποκλιση O {SDV[var][0]:.2f} · D {SDV[var][1]:.2f}')
def feats(var):
    sO, sD = SDV[var]; XH = np.zeros((len(rows), 2)); XA = np.zeros((len(rows), 2))
    for i, r in enumerate(rows):
        def side(own, opp):
            o = sum(p['w'] * ((our(var, r, p) or (0.0, 0.0))[0] / sO) for p in own)
            d = sum(p['w'] * ((our(var, r, p) or (0.0, 0.0))[1] / sD) for p in opp)
            return o, d
        XH[i] = side(r['ah'], r['aa']); XA[i] = side(r['aa'], r['ah'])
    return XH, XA
def fit2(XH, XA, tr):
    X = np.r_[XH[tr], XA[tr]]; y = np.r_[YH[tr], YA[tr]]
    return np.linalg.solve(X.T @ X + 1.0 * np.eye(2), X.T @ y)
FX = {'R0 live (W4 3StepsBasket)': (NS['XH'][:, [2, 3]], NS['XA'][:, [2, 3]])}
for var in XVARS: FX[var] = feats(var)
HELDV = {}; TRAIN_RMSE = {}
for nm, (XH, XA) in FX.items():
    h = np.zeros(len(rows))
    for Y in SE:
        b = fit2(XH, XA, ys != Y); m = ys == Y; h[m] = XH[m] @ b + XA[m] @ b
        tr = ys != Y; TRAIN_RMSE[(nm, Y)] = rmse(YT - (XH @ b + XA @ b), tr)
    HELDV[nm] = h
# LOSO επιλογη w_prev/λ
hsel = np.zeros(len(rows)); CHOICE = {}
for Y in SE:
    best = min(CVARS, key=lambda v: TRAIN_RMSE[(v, Y)]); CHOICE[Y] = best; m = ys == Y; hsel[m] = HELDV[best][m]
HELDV['Σ LOSO-επιλογη'] = hsel
P('  LOSO επιλογη (w_prev, λ) ανα κρατημενη σεζον: ' + ' · '.join(f'{Y[-2:]}: {CHOICE[Y]}' for Y in SE))
# ---- picks (ιδια λογικη με tpicks του W4) ----
def picks_df(adj):
    L = []
    for r, a in zip(rows, adj):
        o = r['op']; T_, oo, ou = o[2], o[3], o[4]; po, pp, pu = tp(r['T'] + a, T_); eo, eu = po * oo + pp - 1, pu * ou + pp - 1
        sd, e, od = (1, eo, oo) if eo >= eu else (-1, eu, ou)
        act = r['hs'] + r['as_']; side = None; u = np.nan; clv = np.nan
        if e >= .08:
            x = (act - T_) * sd; u = (od - 1) if x > 0 else (0 if x == 0 else -1); side = 'over' if sd == 1 else 'under'; clv = (r['cl'][1] - o[1]) * sd
        L.append(dict(season=r['y'], code=r['code'], rnd=r['rnd'], home=r['hc'], away=r['ac'], ts=r['ts'], model_total=r['T'], pred_total=r['T'] + a,
                      adj=a, actual_total=act, line=T_, odds_over=oo, odds_under=ou, edge=e, pick=side, units=u, clv=clv))
    return pd.DataFrame(L)
DF = {nm: picks_df(h) for nm, h in HELDV.items()}
DF['χωρις διορθωση'] = picks_df(np.zeros(len(rows)))
def summ(df):
    q = df[df.pick.notna()]; U = {s: q[q.season == s].units for s in SE}
    return len(q), q.units.sum(), q.units.mean() * 100, sum(1 for s in SE if len(U[s]) and U[s].mean() > 0), {s: U[s].sum() for s in SE}, q.clv.mean()
assert abs(summ(DF['R0 live (W4 3StepsBasket)'])[1] - u_chk) < 1e-6
ORDER = ['χωρις διορθωση', 'R0 live (W4 3StepsBasket)', 'Σ LOSO-επιλογη'] + XVARS
P(''); P('## RMSE συνολου (LOSO, ποντοι) ανα σεζον και ΔRMSE vs R0 (− = καλυτερο απο το live)')
P(f'  {"εκδοχη":28s} {"RMSE ολα":>8s} · RMSE ανα σεζον (' + ' '.join(s[-2:] for s in SE) + ') · ΔRMSE vs R0 ανα σεζον · καλυτερο σε')
R0n = 'R0 live (W4 3StepsBasket)'
for nm in ORDER:
    h = HELDV.get(nm, np.zeros(len(rows))); rr = [rmse(YT - h, ys == s) for s in SE]; r0 = [rmse(YT - HELDV[R0n], ys == s) for s in SE]
    d = [a - b for a, b in zip(rr, r0)]
    P(f'  {nm:28s} {rmse(YT - h, ALL):8.3f} · ' + ' '.join(f'{x:.3f}' for x in rr) + ' · ' + ' '.join(f'{x:+.3f}' for x in d) + f' · {sum(x < 0 for x in d)}/5')
P(''); P('## ΣΥΝΤΕΛΕΣΤΕΣ bO (δικοι αποντες × z(O)) / bD (αντιπ. αποντες × z(D)) — ποντοι ομαδας ανα 40′ απουσιας ανα 1 τυπ. αποκλιση· αναμενομενα < 0')
for nm in [R0n] + XVARS:
    XH, XA = FX[nm]; b = fit2(XH, XA, ALL); per = {s: fit2(XH, XA, ys == s) for s in SE}
    P(f'  {nm:28s} bO {b[0]:+.2f} (' + ' '.join(f'{s[-2:]}:{per[s][0]:+.2f}' for s in SE) + f'; <0 σε {sum(per[s][0] < 0 for s in SE)}/5) · '
      f'bD {b[1]:+.2f} (' + ' '.join(f'{s[-2:]}:{per[s][1]:+.2f}' for s in SE) + f'; <0 σε {sum(per[s][1] < 0 for s in SE)}/5)')
P(''); P('## PICKS συνολων ≥8% στο ανοιγμα (Crown) — n · μοναδες · ROI · θετικες σεζον · ανα σεζον · CLV (ποντοι γραμμης προς εμας)')
for nm in ORDER:
    n, u, roi, pos, us, clv = summ(DF[nm])
    P(f'  {nm:28s} {n:4d} picks · {u:+6.1f}μ · ROI {roi:+5.1f}% · θετ {pos}/5 · ' + ' '.join(f'{s[-2:]}:{us[s]:+.1f}' for s in SE) + f' · CLV {clv:+.2f}')
P(''); P('## OVER / UNDER χωριστα (n · μοναδες · ROI)')
for nm in ORDER:
    q = DF[nm]; q = q[q.pick.notna()]
    P(f'  {nm:28s} ' + ' · '.join(f'{sd}: {len(q[q.pick == sd]):3d} · {q[q.pick == sd].units.sum():+6.1f}μ · ROI {q[q.pick == sd].units.mean() * 100:+5.1f}%' for sd in ('over', 'under')))
P(''); P('## ΑΓΩΝΙΣΤΙΚΕΣ 1-10 vs 11+ (n · μοναδες · ROI)')
for nm in ORDER:
    q = DF[nm]; q = q[q.pick.notna()]; e = q[q.rnd.fillna(99) <= 10]; l = q[q.rnd.fillna(99) > 10]
    P(f'  {nm:28s} 1-10: {len(e):3d} · {e.units.sum():+6.1f}μ · ROI {e.units.mean() * 100:+5.1f}% · 11+: {len(l):3d} · {l.units.sum():+6.1f}μ · ROI {l.units.mean() * 100:+5.1f}%')
P(''); P('## ΚΑΛΥΨΗ ΑΠΟΝΤΩΝ (μεριδιο παικτη-ματς απουσιων με τιμη δεικτη) ανα σεζον')
P(f'  {"R0 live":28s} ' + ' · '.join(f'{s[-2:]}: {np.mean([p["usg"] is not None for r, p in allabs if r["y"] == s]):.0%}' for s in SE))
for var in ['Σ w0.6 λ3000', 'box μονο w0.6']:
    P(f'  {var:28s} ' + ' · '.join(f'{s[-2:]}: {np.mean([our(var, r, p) is not None for r, p in allabs if r["y"] == s]):.0%}' for s in SE))
# ---- αποφαση ----
P(''); P('################ ΑΠΟΦΑΣΗ (προ-δηλωμενα κριτηρια) ################')
modal = collections.Counter(CHOICE.values()).most_common(1)[0][0]
sN, sD = STAB[(modal, 'καθαρο')], STAB[(modal, 'D')]
c1 = sN >= STAB['PIR/40 (καθαρο)'] or sD >= 0.36
P(f'  (1) σταθεροτητα εκδοχης LOSO (συχνοτερη: {modal}): καθαρο {sN:+.2f} vs PIR/40 {STAB["PIR/40 (καθαρο)"]:+.2f} · D {sD:+.2f} vs 0.36 → ' + ('ΠΕΡΝΑ' if c1 else 'ΔΕΝ ΠΕΡΝΑ ΣΤΑΘΕΡΟΤΗΤΑ'))
rr = [rmse(YT - hsel, ys == s) - rmse(YT - HELDV[R0n], ys == s) for s in SE]; n, u, roi, pos, us, clv = summ(DF['Σ LOSO-επιλογη']); n0, u0 = summ(DF[R0n])[:2]
c2 = sum(x < 0 for x in rr) >= 4 and u >= u0 and pos >= 4
P(f'  (2) Σ LOSO-επιλογη: RMSE καλυτερο απο R0 σε {sum(x < 0 for x in rr)}/5 · μοναδες {u:+.1f} vs R0 {u0:+.1f} · θετικες {pos}/5 → ' + ('ΚΡΙΤΗΡΙΟ ΑΝΤΙΚΑΤΑΣΤΑΣΗΣ ΠΛΗΡΟΥΤΑΙ' if c2 else 'ΚΡΙΤΗΡΙΟ ΑΝΤΙΚΑΤΑΣΤΑΣΗΣ ΔΕΝ ΠΛΗΡΟΥΤΑΙ'))
save()
pickle.dump(DF, open('el_onoff_variants_beta.pkl', 'wb'))
# ================= ΕΛΕΓΧΟΣ ΠΑΡΑΔΕΙΓΜΑΤΩΝ =================
P(''); P(f'################ ΕΛΕΓΧΟΣ ΠΑΡΑΔΕΙΓΜΑΤΩΝ — 2025-26 (E2025), τελικη τιμη, παικτες ≥500′, εκδοχη {modal} ################')
F = FINAL[(modal, 'E2025')]; FB = FINAL[('box φετινα μονο', 'E2025')]; RF = REF['E2025']
ps = [p for p in F if RF['mins'].get(p, 0) >= 500]
def lab(p): return f"{NAME.get(PIDS[p], PIDS[p])} ({RF['team'].get(p)})"
P('  ΚΟΡΥΦΑΙΟΙ 10 ΕΠΙΘΕΣΗ (O υψηλο = η ομαδα σκοραρει περισσοτερο):')
for p in sorted(ps, key=lambda p: -F[p][0])[:10]:
    P(f'    {lab(p):40s} O {F[p][0]:+.2f} · D {F[p][1]:+.2f} · box O {FB.get(p, (np.nan,)*2)[0]:+.2f} · RAPM1σ O {RF["R8"].get(p, (np.nan,)*2)[0]:+.2f} · PIR/40 {RF["pir"].get(p, np.nan):.1f} · λεπτα {RF["mins"][p]:.0f}')
P('  ΚΟΡΥΦΑΙΟΙ 10 ΑΜΥΝΑ (D χαμηλο = ο αντιπαλος σκοραρει λιγοτερο):')
for p in sorted(ps, key=lambda p: F[p][1])[:10]:
    P(f'    {lab(p):40s} D {F[p][1]:+.2f} · O {F[p][0]:+.2f} · box D {FB.get(p, (np.nan,)*2)[1]:+.2f} · RAPM1σ D {RF["R8"].get(p, (np.nan,)*2)[1]:+.2f} · PIR/40 {RF["pir"].get(p, np.nan):.1f} · λεπτα {RF["mins"][p]:.0f}')
P('  ΧΕΙΡΟΤΕΡΟΙ 5 ΑΜΥΝΑ (D υψηλο):')
for p in sorted(ps, key=lambda p: -F[p][1])[:5]:
    P(f'    {lab(p):40s} D {F[p][1]:+.2f} · box D {FB.get(p, (np.nan,)*2)[1]:+.2f} · RAPM1σ D {RF["R8"].get(p, (np.nan,)*2)[1]:+.2f}')
# 2 αποντες
P(''); P('  ΑΠΟΝΤΕΣ — τιμες καθε εκδοχης την ημερα του ματς (R0 = 3StepsBasket περσινο on/off μετα το μαζεμα· δικες = O/D στο σημειο υπολογισμου):')
cand = sorted([(r, p) for r, p in allabs if r['y'] in ('E2024', 'E2025') and PID.get(p['pid']) is not None], key=lambda x: -x[1]['w'])
seen = set(); ex = []
for want in ('TAVARES', 'VEZENKOV', 'NUNN', 'LESSORT', 'HEZONJA'):
    for r, p in cand:
        if want in NAME.get(p['pid'], '') and want not in seen: ex.append((r, p)); seen.add(want); break
    if len(ex) >= 2: break
for r, p in ex:
    P(f'    {NAME.get(p["pid"])} — απων στο {r["hc"]}-{r["ac"]} {pd.Timestamp(r["ts"], unit="s"):%Y-%m-%d} ({r["y"]}, αγων. {r["rnd"]}) · βαρος w {p["w"]:.2f}')
    P(f'      R0: onO {p["onO"]:+.2f} · onD {p["onD"]:+.2f}' + (' (χωρις προφιλ → 0)' if p['usg'] is None else ''))
    for var in XVARS:
        v = our(var, r, p)
        P(f'      {var:28s} ' + (f'O {v[0]:+.2f} · D {v[1]:+.2f} · z(O) {v[0] / SDV[var][0]:+.2f} · z(D) {v[1] / SDV[var][1]:+.2f}' if v else 'χωρις τιμη → 0'))
P(''); P(f'χρονος {time.time() - T0:.0f} δευτ.')
save()
