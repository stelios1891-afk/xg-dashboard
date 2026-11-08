# -*- coding: utf-8 -*-
"""t64_totals_value_combos.py — ΣΥΝΟΛΑ NBA: ΠΟΙΟΣ ΔΕΙΚΤΗΣ / ΣΥΝΔΥΑΣΜΟΣ ΓΙΑ ΤΗΝ ΕΠΙΘΕΤΙΚΗ (o) / ΑΜΥΝΤΙΚΗ (d) ΑΞΙΑ ΑΠΟΝΤΑ (23/10/2026).
Ιδιο ερωτημα με το t62 (χαντικαπ) αλλα για τα ΣΥΝΟΛΑ.
Σημερα (live/t35): o/d = ΑΠΛΟΣ μεσος περσινων DARKO o_dpm/d_dpm · O/D-LEBRON · OBPM/DBPM (bbref) × λεπτα/(λεπτα+500), αγνωστος −0.5/−0.5.
ΔΙΟΡΘΩΣΗ OBPM/DBPM (μονο μεσα στο τεστ): το regex αποτυγχανει οταν obpm/dbpm ειναι σε <strong> (πρωτος λιγκας) → κρατιεται η γραμμη
  των PLAYOFFS (advanced_post). ΣΩΣΤΟ = μονο html ΠΡΙΝ το 'id="advanced_post"', αφαιρεση <strong>/</strong>, πολλες γραμμες → η με τα περισσοτερα mp.
ΕΚΔΟΧΕΣ (ετος s−1, μεσος ΔΙΑΘΕΣΙΜΩΝ δεικτων της εκδοχης × mp/(mp+500), κανενας → −0.5/−0.5):
  1 DARKO · 2 LEBRON · 3 BPM(σωστο) · 4 DARKO+LEBRON · 5 DARKO+BPM · 6 LEBRON+BPM · 7 ολοι (σωστο BPM) · ref = σημερινο (λαθος BPM).
ΑΠΟΝΤΕΣ = ακριβως οι ιδιοι με το t35 στο ΑΝΟΙΓΜΑ (επισημη αναφορα ≤ τ, ρολος ≥20′, επαιξε φετος για την ομαδα, ιδιες πιθανοτητες/λεπτα).
  LO = Σ w·(o + 0.5)·λεπτα/48 · LD = Σ w·(d + 0.5)·λεπτα/48 (w = πιθανοτητα· «μονο Out» → w = 1 για Out, 0 αλλιως).
  ΕΛΕΓΧΟΣ: ref αναπαραγει lo/ld/lop/ldp του _t35_totals.csv (αλλιως ΣΤΟΠ).
(Ι) LIVE ΤΥΠΟΣ: συνολο = tt + Φ3 + cO·LO + cD·LD (LO/LD με πιθανοτητες = live απο 22/10 «official»· δευτερευον «μονο Out»).
  α) σταθερα live cO −0.5, cD +1.0 · β) cO/cD ΕΠΑΝΕΚΤΙΜΗΜΕΝΑ LOSO (OLS (πραγμ − tt − Φ3) ~ 1 + LO + LD στις αλλες 4, εφαρμογη ΧΩΡΙΣ σταθερα).
  Picks ανοιγμα edge ≥8% (TOT_MIN), σ 18. ΕΛΕΓΧΟΣ: ref «μονο Out» σταθερα → +110.6μ, 2519 picks (t36 Δ0).
(ΙΙ) ΣΚΙΑ Μ2δ (t39): (πραγμ − δικαιο αγορας) = ridge λ50 [μ−αγορα, LO, LD, LOp−LO, LDp−LD, Οκτ-Δεκ, Μαρ-Απρ, γραμμη−225, αγων≤10, Απρ],
  μ = tt + Φ3 − 0.5·LO + 1.0·LD (μονο Out, οπως t36/t39), LOSO ανα σεζον, ξανα-fit ανα εκδοχη. Picks edge ≥6%, σ 18.
  ΕΛΕΓΧΟΣ: ref → +128.7μ, 1042 picks (t39 «ολη 6%»).
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (γραφτηκαν ΠΡΙΝ το τρεξιμο), ΧΩΡΙΣΤΑ για (Ι)β και (ΙΙ):
  (1) Μια εκδοχη ΑΝΤΙΚΑΘΙΣΤΑ την «7 ολοι» αν: RMSE συνολου καλυτερο απο το 7 σε ≥4/5 σεζον ΚΑΙ μοναδες picks ≥ του 7 ΚΑΙ θετικες σεζον ≥4/5.
  (2) Αν καμια → μενει το 7.
  (3) LOSO επιλογη εκδοχης (1-7) με RMSE στις αλλες 4 σεζον (στο fit των 4) → ποσο συχνα ιδια, αποτελεσμα στη σεζον-τεστ.
  Περιγραφικα: RMSE, ΔRMSE ανα σεζον vs 7, cO/cD (ή coef LO/LD) ανα εκδοχη με προσημα ανα σεζον, ROI/n/μοναδες/ανα σεζον, θετικες σεζον,
  Δμοναδες vs 7 ±ΤΣ (ζευγαρωτα ανα ματς), χωριστα over / under, εγγραφες στο −0.5 ανα εκδοχη.
ΕΛΕΓΧΟΣ ΠΑΡΑΔΕΙΓΜΑΤΩΝ: Jokić (s−1 = 2024 ή 2025), καλος αμυντικος (Gobert/Wembanyama), ενας χωρις LEBRON.
Εξοδος: t64_totals_value_combos_out.txt (stdout)."""
import os, sys, io, re, json, pickle, contextlib, collections, warnings
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from scipy.special import ndtr
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
CACHE = os.environ.get('T64_CACHE', os.path.join(os.environ.get('TEMP', SC), 't64_abs_cache.pkl'))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
PR = {'star': {'Out': 1.0, 'Doubtful': .965, 'Questionable': .42, 'Probable': .04}, 'starter': {'Out': 1.0, 'Doubtful': .963, 'Questionable': .46, 'Probable': .07}}
# ================= ΦΑΣΗ Α: απουσιες στο ανοιγμα (ιδιο με t35) =================
if os.path.exists(CACHE):
    C = pickle.load(open(CACHE, 'rb'))
else:
    src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
    g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
    cwd = os.getcwd()
    with contextlib.redirect_stdout(_B()): exec(src, g)
    os.chdir(cwd)
    nt = g['nt']; G, SEAS_G, dD, EV, SER, SHIFT = g['G'], g['SEAS_G'], g['dD'], g['EV'], g['SER'], g['SHIFT']
    status_at, K2P, mins, REP_SEASONS = g['status_at'], g['K2P'], g['mins'], g['REP_SEASONS']
    TT = np.asarray(nt['TT'], float); odval = nt['odval']
    recs = []
    for i, (sw, tip, r21, r23) in SER.items():
        s = int(SEAS_G[i])
        if s not in EV or s not in REP_SEASONS or not np.isfinite(TT[i]) or not r23: continue
        rr = [[x[0] + SHIFT] + list(x[1:]) for x in r23]; rr = [x for x in rr if x[0] <= tip + 900]
        if not rr: continue
        tau = rr[0][0]; d = dD[i]
        for t in (G.home.values[i], G.away.values[i]):
            for k, stt in status_at(t, d, tau).items():
                pid = K2P.get((k, t, s))
                if pid is None: continue
                m = mins(pid, t, s, d)
                if m is None or m < 20: continue
                o_, d_ = odval(pid, s - 1); w = PR['star' if m >= 30 else 'starter'].get(stt, 0.0)
                recs.append((i, t, k, pid, s - 1, float(m), stt, w, o_, d_, str(d)))
    NS = nt['NS']; A = g['A']
    C = dict(recs=recs, MPT=dict(NS['MPT']), NAME2PID=dict(NS['NAME2PID']), OD_={k: (list(v[0]), list(v[1])) for k, v in nt['OD_'].items()},
             NAMES={p: n for p, n in A[['pid', 'PLAYER_NAME']].drop_duplicates('pid').itertuples(index=False)})
    pickle.dump(C, open(CACHE, 'wb'))
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True)
MPT, NAME2PID, OD_, NAMES = C['MPT'], C['NAME2PID'], C['OD_'], C['NAMES']
R = pd.DataFrame(C['recs'], columns=['i', 'team', 'key', 'pid', 'y', 'm', 'stt', 'w', 'o_ref', 'd_ref', 'date'])
# nk ιδιο με nba_roster_adj
import unicodedata
def nk(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s); return ' '.join(re.findall(r'[a-z]+', s))
# ================= ΔΕΙΚΤΕΣ ανα (pid, ετος) =================
IDX = {'DARKO': collections.defaultdict(list), 'LEBRON': collections.defaultdict(list), 'BPM': {}, 'BPMold': collections.defaultdict(list)}
for r in json.load(open(os.path.join(ROOT, 'nba_rapm/DARKO.json'), encoding='utf-8')):
    if r.get('o_dpm') is not None and r.get('d_dpm') is not None: IDX['DARKO'][(str(r['nba_id']), int(r['season']))].append((r['o_dpm'], r['d_dpm']))
for r in json.load(open(os.path.join(ROOT, 'nba_rapm/lebron.json'), encoding='utf-8')):
    if r.get('O-LEBRON') is not None and r.get('D-LEBRON') is not None and r.get('nba_id'):
        IDX['LEBRON'][(str(r['nba_id']), int(r['year']))].append((r['O-LEBRON'], r['D-LEBRON']))
rows = []
for y in range(2020, 2027):
    fn = os.path.join(ROOT, 'bbref_cache', f'NBA_{y}_advanced.html')
    if not os.path.exists(fn): continue
    t0 = open(fn, encoding='utf-8', errors='ignore').read()
    seen = set()                                    # ΣΗΜΕΡΙΝΗ (λαθος) αναγνωση — ιδια με od_totals_test
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t0, re.S):
        nm = re.search(r'data-stat="name_display"[^>]*>(?:<a[^>]*>)?([^<]+)', tr)
        o = re.search(r'data-stat="obpm"[^>]*>([-\d.]+)<', tr); d = re.search(r'data-stat="dbpm"[^>]*>([-\d.]+)<', tr)
        if nm and o and d:
            k_ = nk(nm.group(1))
            if k_ in NAME2PID and (k_, y) not in seen:
                seen.add((k_, y)); IDX['BPMold'][(NAME2PID[k_], y)].append((float(o.group(1)), float(d.group(1))))
    k = t0.find('id="advanced_post"'); t = t0[:k] if k >= 0 else t0
    t = t.replace('<strong>', '').replace('</strong>', '')
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
        nm = re.search(r'data-stat="name_display"[^>]*>(?:<a[^>]*>)?([^<]+)', tr)
        o = re.search(r'data-stat="obpm"[^>]*>([-\d.]+)<', tr); d = re.search(r'data-stat="dbpm"[^>]*>([-\d.]+)<', tr)
        b = re.search(r'data-stat="bpm"[^>]*>([-\d.]+)<', tr); mp = re.search(r'data-stat="mp"[^>]*>(\d+)<', tr)
        if nm and o and d and mp: rows.append((nk(nm.group(1)), y, float(o.group(1)), float(d.group(1)), float(b.group(1)) if b else np.nan, int(mp.group(1))))
br = pd.DataFrame(rows, columns=['k', 'y', 'o', 'd', 'b', 'mp']).sort_values('mp', ascending=False).drop_duplicates(['k', 'y'])
for k_, y, o, d in zip(br.k, br.y, br.o, br.d):
    if k_ in NAME2PID: IDX['BPM'][(NAME2PID[k_], y)] = [(o, d)]
BPM_B = {(NAME2PID[k_], y): b for k_, y, b in zip(br.k, br.y, br.b) if k_ in NAME2PID}
P('t64 — ΣΥΝΟΛΑ NBA · επιθετικη/αμυντικη αξια αποντα: ποιος δεικτης/συνδυασμος (σεζον 2022-2026 = 2021-22 … 2025-26 · ανοιγμα Crown)')
P(''); P('ΕΛΕΓΧΟΣ ΔΙΟΡΘΩΣΗΣ OBPM/DBPM (bbref, κανονικη περιοδος· σωστο: OBPM + DBPM ≈ BPM):')
def raw(p, y, i):
    v = IDX[i].get((p, y)); return v if v else None
for name, y in (('Nikola Jokić', 2021), ('Nikola Jokić', 2022), ('Nikola Jokić', 2024), ('Nikola Jokić', 2025), ('Julius Randle', 2021), ('Rudy Gobert', 2024), ('Victor Wembanyama', 2025)):
    p = NAME2PID.get(nk(name)); c = raw(p, y, 'BPM'); o_ = raw(p, y, 'BPMold')
    P(f'  {name} {y}: σωστο OBPM/DBPM {c[0] if c else "—"} (BPM {BPM_B.get((p, y))}) · σημερινο (λαθος) {o_[0] if o_ else "—"}')
cm = [k_ for k_ in IDX['BPM'] if k_ in IDX['BPMold']]
dif = [k_ for k_ in cm if any(abs(a - b) > 1e-9 for a, b in zip(IDX['BPM'][k_][0], IDX['BPMold'][k_][0]))]
P(f'  ζευγαρια (παικτης, ετος) με OBPM/DBPM: σωστο {len(IDX["BPM"])} · σημερινο {len(IDX["BPMold"])} · κοινα {len(cm)} · με διαφορετικη τιμη {len(dif)}'
  f' · μονο στο σωστο {len(set(IDX["BPM"]) - set(IDX["BPMold"]))} · μονο στο σημερινο {len(set(IDX["BPMold"]) - set(IDX["BPM"]))}')
P('  διαφορετικα: ' + ', '.join(f'{NAMES.get(p_, p_)} {y_}' for p_, y_ in sorted(dif, key=lambda x: (x[1], str(NAMES.get(x[0]))))))
dup = {i: sum(1 for v in IDX[i].values() if len(v) > 1) for i in ('DARKO', 'LEBRON')}
P(f'  διπλες εγγραφες (ιδιος παικτης-ετος): DARKO {dup["DARKO"]} · LEBRON {dup["LEBRON"]} (στις εκδοχες: μεσος ΑΝΑ δεικτη, μετα μεσος δεικτων)')
# ================= ΕΚΔΟΧΕΣ =================
VER = collections.OrderedDict([('1 DARKO', ['DARKO']), ('2 LEBRON', ['LEBRON']), ('3 BPM', ['BPM']), ('4 DARKO+LEBRON', ['DARKO', 'LEBRON']),
                               ('5 DARKO+BPM', ['DARKO', 'BPM']), ('6 LEBRON+BPM', ['LEBRON', 'BPM']), ('7 ολοι', ['DARKO', 'LEBRON', 'BPM']),
                               ('ref (σημερινο)', None)])
V7 = list(VER)[:7]
def od_ver(p, y, idx):
    mp = MPT.get((p, y), 0.0); sh = mp / (mp + 500)
    if idx is None:                                   # ref: ακριβως οπως odval (συνενωση λιστων, λαθος BPM)
        L = IDX['DARKO'].get((p, y), []) + IDX['LEBRON'].get((p, y), []) + IDX['BPMold'].get((p, y), [])
        if not L: return -0.5, -0.5, False
        return float(np.mean([a for a, _ in L])) * sh, float(np.mean([b for _, b in L])) * sh, True
    vs = [(np.mean([a for a, _ in IDX[i][(p, y)]]), np.mean([b for _, b in IDX[i][(p, y)]])) for i in idx if IDX[i].get((p, y))]
    if not vs: return -0.5, -0.5, False
    return float(np.mean([a for a, _ in vs])) * sh, float(np.mean([b for _, b in vs])) * sh, True
X = pd.read_csv(os.path.join(SC, '_t35_totals.csv'))
X['per'] = X.mon.map({10: 'Οκτ-Δεκ', 11: 'Οκτ-Δεκ', 12: 'Οκτ-Δεκ', 1: 'Ιαν-Φεβ', 2: 'Ιαν-Φεβ', 3: 'Μαρ-Απρ', 4: 'Μαρ-Απρ'})
D = X[X.tau == 'ανοιγμα'].reset_index(drop=True)
# ΣΗΜ.: ο δεικτης i του σημερινου G ΔΕΝ ταυτιζεται με το i του _t35_totals.csv (το G ξαναχτιστηκε μετα το CSV) → αντιστοιχιση με (ημερα, ομαδα)
POS = {}
for q, (dte, h, a) in enumerate(zip(D.date.astype(str), D.home, D.away)): POS[(dte, h)] = q; POS[(dte, a)] = q
R['q'] = [POS.get((dte, t)) for dte, t in zip(R.date.astype(str), R.team)]
P(f'αντιστοιχιση εγγραφων αποντων σε ματς του CSV με (ημερα, ομαδα): χωρις ματς {int(R.q.isna().sum())} απο {len(R)}')
R = R[R.q.notna()].reset_index(drop=True); R['q'] = R.q.astype(int); R['out'] = (R.stt == 'Out').astype(float)
OV, DV, KN = {}, {}, {}
for v, idx in VER.items():
    r = [od_ver(p, y, idx) for p, y in zip(R.pid, R.y)]
    OV[v] = np.array([a for a, _, _ in r]); DV[v] = np.array([b for _, b, _ in r]); KN[v] = np.array([c for _, _, c in r])
nq = len(D)
def agg(v, wcol):
    w = R[wcol].values; m = R.m.values; q = R.q.values
    lo = np.zeros(nq); ld = np.zeros(nq)
    np.add.at(lo, q, w * (OV[v] + 0.5) * m / 48); np.add.at(ld, q, w * (DV[v] + 0.5) * m / 48)
    return lo, ld
LOo, LDo, LOp, LDp = {}, {}, {}, {}
for v in VER: LOo[v], LDo[v] = agg(v, 'out'); LOp[v], LDp[v] = agg(v, 'w')
e1 = max(np.max(np.abs(R.o_ref.values - OV['ref (σημερινο)'])), np.max(np.abs(R.d_ref.values - DV['ref (σημερινο)'])))
e2 = max(np.max(np.abs(LOo['ref (σημερινο)'] - D.lo.values)), np.max(np.abs(LDo['ref (σημερινο)'] - D.ld.values)),
         np.max(np.abs(LOp['ref (σημερινο)'] - D.lop.values)), np.max(np.abs(LDp['ref (σημερινο)'] - D.ldp.values)))
P(''); P(f'ΕΛΕΓΧΟΣ ref: |o/d ref ξαναυπολογ. − odval του t35| μεγ. {e1:.2e} · |LO/LD/LOp/LDp ref − _t35_totals.csv| μεγ. {e2:.2e} (πρεπει ≈0)')
if e1 > 1e-6 or e2 > 1e-4: P('  ✗ ΣΤΟΠ — η ref δεν αναπαραγει το t35'); sys.exit(1)
P(f'ματς (ανοιγμα) {nq} · εγγραφες αποντων ρολου (καθε κατασταση) {len(R)} · με w>0 {int((R.w > 0).sum())} · Out {int(R.out.sum())}')
# ---- πινακας 0 ----
P(''); P('ΠΙΝΑΚΑΣ 0 — εγγραφες αποντων (w>0) στο −0.5/−0.5 (λειπει ΚΑΘΕ δεικτης της εκδοχης για τη σεζον s−1):')
wp = R.w.values > 0; any7 = KN['7 ολοι']
for v in VER:
    k_ = KN[v]
    P(f'  {v:16s}: στο −0.5 {int((~k_ & wp).sum()):5d} απο {int(wp.sum())} ({100 * (~k_ & wp).sum() / wp.sum():4.1f}%) · εκ των οποιων εχουν αλλο δεικτη {int((~k_ & wp & any7).sum()):4d}'
      f' · Out στο −0.5 {int((~k_ & (R.out.values > 0)).sum())}')
fb = np.array([(p, y) not in MPT and (p, y - 1) in MPT for p, y in zip(R.pid, R.y)])
z0 = np.array([MPT.get((p, y), 0.0) == 0 for p, y in zip(R.pid, R.y)])
P(f'  σημειωση: εγγραφες (w>0) με περσινα λεπτα 0 → ×0 = o/d 0 (αν εχουν δεικτη) ή −0.5: {int((z0 & wp).sum())} · εκ των οποιων επαιξαν ΠΡΟΠΕΡΣΙ'
  f' (το live build παιρνει τις προπερσινες· το t35/τεστ ΟΧΙ): {int((fb & wp).sum())}')
# ================= ΚΟΙΝΑ =================
SIG = 18.0; SE = sorted(D.sea.unique()); ys = D.sea.values; TOT = D.tot.values; FAIR = D.fair.values; CF = D.cfair.values
Tl = D['T'].values; OO = D.oo.values; OU = D.ou.values; INT = np.abs(Tl - np.round(Tl)) < 1e-9
def pk(mu, thr):
    po = np.where(INT, ndtr((mu - Tl - 0.5) / SIG), ndtr((mu - Tl) / SIG)); pu = np.where(INT, ndtr((Tl - mu - 0.5) / SIG), 1 - po)
    pp = np.where(INT, 1 - po - pu, 0.0); eo = po * OO + pp - 1; eu = pu * OU + pp - 1
    sd = np.where(eo >= eu, 1, -1); e = np.maximum(eo, eu); od = np.where(sd == 1, OO, OU); hit = e >= thr
    x = (TOT - Tl) * sd; res = np.where(x > 0, od - 1, np.where(x == 0, 0.0, -1.0)); res = np.where(hit, res, 0.0)
    return dict(res=res, hit=hit, sd=sd, clv=sd * (CF - FAIR))
def st(p, side=None):
    h = p['hit'] if side is None else (p['hit'] & (p['sd'] == side)); u = p['res'][h]
    per = {s: float(p['res'][h & (ys == s)].sum()) for s in SE}
    return dict(n=int(h.sum()), u=float(u.sum()), roi=100 * u.mean() if len(u) else np.nan, se=100 * u.std(ddof=1) / np.sqrt(len(u)) if len(u) > 1 else np.nan,
                per=per, pos=sum(per[s] > 0 for s in SE), clv=float(p['clv'][h].mean()) if len(u) else np.nan, vec=np.where(h, p['res'], 0.0))
def rm(pred, mk): return float(np.sqrt(np.mean((TOT[mk] - pred[mk]) ** 2)))
ALL = np.ones(nq, bool)
def fmt_st(s_, s7=None):
    t = f'ROI {s_["roi"]:+5.1f}% ± {s_["se"]:.1f} · n {s_["n"]:4d} · μοναδες {s_["u"]:+6.1f} · θετικες {s_["pos"]}/5 · CLV {s_["clv"]:+.2f}π · ανα σεζον ' + ' '.join(f'{s % 100}:{s_["per"][s]:+.1f}' for s in SE)
    if s7 is not None: dg = s_['vec'] - s7['vec']; t += f' · Δμοναδες vs 7 {dg.sum():+.1f} ± {dg.std(ddof=1) * np.sqrt(len(dg)):.1f}'
    return t
def block(tag, PRED, thr, show_rmse=True):
    if show_rmse:
        P(f'  RMSE συνολου (πραγμ − προβλ., ποντοι, {nq} ματς) · ΔRMSE ανα σεζον vs «7 ολοι» (αρνητικο = καλυτερο):')
        r7 = {s: rm(PRED['7 ολοι'], ys == s) for s in SE}
        for v in VER:
            dd = [rm(PRED[v], ys == s) - r7[s] for s in SE]
            P(f'    {v:16s}: RMSE {rm(PRED[v], ALL):.4f} · ΔRMSE ' + ' '.join(f'{s % 100}:{x:+.4f}' for s, x in zip(SE, dd)) + f' · καλυτερο απο 7 σε {sum(x < 0 for x in dd)}/5')
    PK = {v: pk(PRED[v], thr) for v in VER}
    for side, lab in ((None, 'ΟΛΑ'), (1, 'OVER'), (-1, 'UNDER')):
        P(f'  PICKS {lab} (ανοιγμα edge ≥{int(thr * 100)}%, 1 μοναδα/pick, μοναδες ανα σεζον 22…26):')
        s7 = st(PK['7 ολοι'], side)
        for v in VER: P(f'    {v:16s}: ' + fmt_st(st(PK[v], side), s7))
    return PK
def criterion(tag, PRED, PK):
    P(f'  ΚΡΙΤΗΡΙΟ (1) {tag}: RMSE καλυτερο απο 7 σε ≥4/5 ΚΑΙ μοναδες ≥ 7 ΚΑΙ θετικες ≥4/5')
    s7 = st(PK['7 ολοι']); r7 = {s: rm(PRED['7 ολοι'], ys == s) for s in SE}; rep = []
    for v in list(VER)[:6] + ['ref (σημερινο)']:
        s_ = st(PK[v]); nb = sum(rm(PRED[v], ys == s) < r7[s] for s in SE); c1, c2, c3 = nb >= 4, s_['u'] >= s7['u'], s_['pos'] >= 4
        P(f'    {v:16s}: RMSE {nb}/5 {"✓" if c1 else "✗"} · μοναδες {s_["u"]:+.1f} vs {s7["u"]:+.1f} {"✓" if c2 else "✗"} · θετικες {s_["pos"]}/5 {"✓" if c3 else "✗"} → {"ΑΝΤΙΚΑΘΙΣΤΑ" if (c1 and c2 and c3) else "οχι"}')
        if c1 and c2 and c3 and v != 'ref (σημερινο)': rep.append(v)
    P(f'    → εκδοχες 1-6 που περνουν: {", ".join(rep) if rep else "καμια (μενει το 7)"}')
def loso_select(tag, PRED, TRM, thr):
    held = np.zeros(nq); ch = []
    for s in SE:
        best = min(V7, key=lambda v: TRM[(v, s)]); ch.append(best); held[ys == s] = PRED[best][ys == s]
    cnt = collections.Counter(ch); r7 = {s: rm(PRED['7 ολοι'], ys == s) for s in SE}
    P(f'  LOSO ΕΠΙΛΟΓΗ ΕΚΔΟΧΗΣ {tag} (μικροτερο RMSE στο fit των αλλων 4): ' + ' · '.join(f'{s % 100}:{c}' for s, c in zip(SE, ch)) + f' · ιδια επιλογη {cnt.most_common(1)[0][1]}/5')
    P('    RMSE σεζον-τεστ LOSO − 7 ολοι: ' + ' '.join(f'{s % 100}:{rm(held, ys == s) - r7[s]:+.4f}' for s in SE))
    p7 = pk(PRED['7 ολοι'], thr); ph = pk(held, thr)
    P('    LOSO picks: ' + fmt_st(st(ph), st(p7)))
# ================= (Ι) LIVE ΤΥΠΟΣ =================
B0 = (D.tt + D.lev).values; Y1 = TOT - B0
COEF_I = {}
for wtag, LOx, LDx in (('με πιθανοτητες (live 22/10)', LOp, LDp), ('μονο Out', LOo, LDo)):
    P(''); P(f'================ (Ι) LIVE ΤΥΠΟΣ · LO/LD {wtag} ================')
    PF = {v: B0 - 0.5 * LOx[v] + 1.0 * LDx[v] for v in VER}
    PL = {v: np.zeros(nq) for v in VER}; TRM = {}; CO = {}
    for v in VER:
        for s in SE:
            tr = ys != s; A_ = np.c_[np.ones(tr.sum()), LOx[v][tr], LDx[v][tr]]; b = np.linalg.lstsq(A_, Y1[tr], rcond=None)[0]
            CO[(v, s)] = b; PL[v][ys == s] = B0[ys == s] + b[1] * LOx[v][ys == s] + b[2] * LDx[v][ys == s]
            TRM[(v, s)] = float(np.sqrt(np.mean((Y1[tr] - b[1] * LOx[v][tr] - b[2] * LDx[v][tr]) ** 2)))
    if wtag.startswith('μονο'):
        pr = pk(PF['ref (σημερινο)'], .08); sr = st(pr)
        ok = abs(sr['u'] - 110.6) < 0.05 and sr['n'] == 2519
        P(f'  ΕΛΕΓΧΟΣ ΑΝΑΠΑΡΑΓΩΓΗΣ t36 Δ0: ref σταθερα, μονο Out → μοναδες {sr["u"]:+.1f} · picks {sr["n"]} (στοχος +110.6 · 2519) {"✓" if ok else "✗ ΣΤΟΠ"}')
        if not ok: sys.exit(1)
    P(''); P(f'  --- (Ι)α ΣΤΑΘΕΡΑ live cO −0.5 · cD +1.0 ---')
    PKF = block('Ια', PF, .08)
    P(''); P(f'  --- (Ι)β cO/cD ΕΠΑΝΕΚΤΙΜΗΜΕΝΑ LOSO (OLS με σταθερα στις 4, εφαρμογη χωρις σταθερα) ---')
    P('  ΣΥΝΤΕΛΕΣΤΕΣ ανα σεζον-τεστ (fit στις αλλες 4)· ολο το δειγμα ± ΤΣ:')
    for v in VER:
        A_ = np.c_[np.ones(nq), LOx[v], LDx[v]]; b = np.linalg.lstsq(A_, Y1, rcond=None)[0]; e = Y1 - A_ @ b
        se = np.sqrt(np.diag(np.linalg.inv(A_.T @ A_) * (e @ e) / (nq - 3)))
        P(f'    {v:16s}: cO ' + ' '.join(f'{s % 100}:{CO[(v, s)][1]:+.2f}' for s in SE) + f' (αρνητικο {sum(CO[(v, s)][1] < 0 for s in SE)}/5) · ολο {b[1]:+.2f} ± {se[1]:.2f}'
          + f' | cD ' + ' '.join(f'{s % 100}:{CO[(v, s)][2]:+.2f}' for s in SE) + f' (θετικο {sum(CO[(v, s)][2] > 0 for s in SE)}/5) · ολο {b[2]:+.2f} ± {se[2]:.2f}'
          + f' | σταθερα ολο {b[0]:+.2f}')
    if wtag.startswith('με'): COEF_I = {v: np.mean([CO[(v, s)] for s in SE], axis=0) for v in VER}
    PKL = block('Ιβ', PL, .08)
    criterion(f'(Ι)β {wtag}', PL, PKL)
    loso_select(f'(Ι)β {wtag}', PL, TRM, .08)
# ================= (ΙΙ) Μ2δ =================
P(''); P('================ (ΙΙ) ΣΚΙΑ Μ2δ (ridge λ50 LOSO, edge ≥6%, σ 18) ================')
YF = TOT - FAIR; NAMES_F = ['σταθερα', 'mu−mkt', 'LO', 'LD', 'LOp−LO', 'LDp−LD', 'oct_dec', 'mar_apr', 'T−225', 'gn≤10', 'apr']
def fx(v):
    mu = D.tt.values + D.lev.values - 0.5 * LOo[v] + 1.0 * LDo[v]
    return np.c_[mu - FAIR, LOo[v], LDo[v], LOp[v] - LOo[v], LDp[v] - LDo[v], (D.per == 'Οκτ-Δεκ').astype(float), (D.per == 'Μαρ-Απρ').astype(float),
                 Tl - 225, (D.gn <= 10).astype(float), (D.mon == 4).astype(float)]
P2 = {}; TRM2 = {}; CO2 = {}
for v in VER:
    Xf = fx(v); P2[v] = np.zeros(nq)
    for s in SE:
        tr = ys != s; A_ = np.c_[np.ones(tr.sum()), Xf[tr]]; b = np.linalg.solve(A_.T @ A_ + 50 * np.eye(A_.shape[1]), A_.T @ YF[tr])
        CO2[(v, s)] = b; P2[v][ys == s] = FAIR[ys == s] + np.c_[np.ones((ys == s).sum()), Xf[ys == s]] @ b
        TRM2[(v, s)] = float(np.sqrt(np.mean((YF[tr] - A_ @ b) ** 2)))
sr = st(pk(P2['ref (σημερινο)'], .06)); ok = abs(sr['u'] - 128.7) < 0.05 and sr['n'] == 1042
P(f'  ΕΛΕΓΧΟΣ ΑΝΑΠΑΡΑΓΩΓΗΣ t39: ref → μοναδες {sr["u"]:+.1f} · picks {sr["n"]} · ROI {sr["roi"]:+.1f}% (στοχος +128.7 · 1042 · +12.3%) {"✓" if ok else "✗ ΣΤΟΠ"}')
if not ok: sys.exit(1)
P(f'  RMSE αγορας (δικαιο ανοιγματος) {rm(FAIR, ALL):.4f} · ανα σεζον ' + ' '.join(f'{s % 100}:{rm(FAIR, ys == s):.3f}' for s in SE))
P('  ΣΥΝΤΕΛΕΣΤΕΣ coef LO / LD / mu−mkt ανα σεζον-τεστ (fit στις αλλες 4):')
for v in VER:
    P(f'    {v:16s}: LO ' + ' '.join(f'{s % 100}:{CO2[(v, s)][2]:+.2f}' for s in SE) + f' (αρνητικο {sum(CO2[(v, s)][2] < 0 for s in SE)}/5)'
      + ' | LD ' + ' '.join(f'{s % 100}:{CO2[(v, s)][3]:+.2f}' for s in SE) + f' (θετικο {sum(CO2[(v, s)][3] > 0 for s in SE)}/5)'
      + ' | mu−mkt ' + ' '.join(f'{s % 100}:{CO2[(v, s)][1]:+.2f}' for s in SE))
PK2 = block('ΙΙ', P2, .06)
criterion('(ΙΙ) Μ2δ', P2, PK2)
loso_select('(ΙΙ) Μ2δ', P2, TRM2, .06)
COEF_II = {v: np.mean([CO2[(v, s)] for s in SE], axis=0) for v in VER}
# ================= ΠΑΡΑΔΕΙΓΜΑΤΑ =================
P(''); P('ΕΛΕΓΧΟΣ ΠΑΡΑΔΕΙΓΜΑΤΩΝ (απων Out στο ανοιγμα · δεικτες ακατεργαστοι (o, d) ετους s−1 · εκδοχες μετα το × mp/(mp+500) · επιδραση στο συνολο σε ποντους):')
P('  επιδραση = Δσυνολου απο ΑΥΤΟΝ τον απoντα: (Ι)α −0.5·LOi + 1.0·LDi · (Ι)β μεσο LOSO cO·LOi + cD·LDi (με πιθαν.) · (ΙΙ) coef_mu·(−0.5·LOi + LDi) + coefLO·LOi + coefLD·LDi')
def show(tag, j):
    r = R.iloc[j]; p, y = r.pid, int(r.y); mp = MPT.get((p, y), 0.0); rr = D.iloc[int(r.q)]
    P(f'  [{tag}] {r.date} {rr.away}@{rr.home} · {r.team} {NAMES.get(p, p)} [pid {p}] · {r.stt} (w {r.w:.2f}) · λεπτα (μ.ο. 10 τελευταιων) {r.m:.1f}′'
      f' · περσινα λεπτα {mp:.0f} (×{mp / (mp + 500):.3f}) · γραμμη {rr["T"]} · πραγματικο {rr.tot:.0f}')
    P('      δεικτες (o, d): ' + ' · '.join(f'{i_} {tuple(round(x, 2) for x in raw(p, y, i_)[0]) if raw(p, y, i_) else "—"}' for i_ in ('DARKO', 'LEBRON', 'BPM', 'BPMold'))
      + f' · BPM σωστο {BPM_B.get((p, y))}')
    for v in VER:
        o, d = OV[v][j], DV[v][j]; LOi = (o + 0.5) * r.m / 48; LDi = (d + 0.5) * r.m / 48
        ci = COEF_I[v]; cii = COEF_II[v]
        P(f'      {v:16s}: o {o:+.2f} · d {d:+.2f}{"" if KN[v][j] else " (−0.5)"} · LOi {LOi:+.2f} · LDi {LDi:+.2f} · επιδραση (Ι)α {-0.5 * LOi + LDi:+.2f} · (Ι)β {ci[1] * LOi + ci[2] * LDi:+.2f}'
          f' (cO {ci[1]:+.2f}, cD {ci[2]:+.2f}) · (ΙΙ) {cii[1] * (-0.5 * LOi + LDi) + cii[2] * LOi + cii[3] * LDi:+.2f}')
OUT = (R.stt == 'Out').values
nmv = np.array([str(NAMES.get(p, '')) for p in R.pid])
jk = [j for j in range(len(R)) if OUT[j] and 'Joki' in nmv[j] and R.y.values[j] in (2024, 2025)]
jk2 = [j for j in jk if (R.pid.values[j], int(R.y.values[j])) in set(dif)]
if jk2 or jk: show('Jokić', (jk2 or jk)[0])
else: P('  Jokić: καμια εγγραφη Out με s−1 2024/2025')
for nm_ in ('Gobert', 'Wembanyama'):
    jj = [j for j in range(len(R)) if OUT[j] and nm_ in nmv[j]]
    if jj: show(f'αμυντικος {nm_}', jj[0]); break
nl = [(MPT.get((R.pid.values[j], int(R.y.values[j])), 0), j) for j in range(len(R)) if OUT[j]
      and raw(R.pid.values[j], int(R.y.values[j]), 'LEBRON') is None and raw(R.pid.values[j], int(R.y.values[j]), 'DARKO') is not None]
nl.sort(reverse=True)
if nl: show('χωρις LEBRON', nl[0][1])
P(f'  σημειωση: εγγραφες Out χωρις LEBRON αλλα με DARKO: {len(nl)} · με περσινα λεπτα 0: {sum(1 for m_, _ in nl if m_ == 0)}')
