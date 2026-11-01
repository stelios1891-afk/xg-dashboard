# -*- coding: utf-8 -*-
"""t22_report_timing.py — ΠΟΤΕ ΝΑ ΜΠΑΙΝΟΥΜΕ: ΤΙΜΗ ΚΑΙ ΑΠΟΥΣΙΕΣ ΤΗΝ ΙΔΙΑ ΣΤΙΓΜΗ (21/10/2026, Στελιος: «πρεπει να τσεκαρουμε ακριβως ποια τιμη
υπηρχε οταν βγηκε το ρεπορτ — οχι τιμες ανοιγματος με ρεπορτ 8 ωρες μετα»).
Για καθε ματς και καθε ΣΤΙΓΜΗ ΑΠΟΦΑΣΗΣ τ (ανοιγμα · Τ−12ω · Τ−6ω · Τ−2ω · Τ−30′):
  ΤΙΜΗ = η γραμμη Crown που ισχυε στο τ (τελευταια αλλαγη ≤ τ) · ΑΠΟΥΣΙΕΣ = η τελευταια ΕΠΙΣΗΜΗ αναφορα NBA με ωρα ≤ τ (ποτε μεταγενεστερη).
  Για καθε παικτη: η πιο προσφατη κατασταση του (αναφορες της ομαδας για ματς των τελευταιων 3 ημερων, ωρα ≤ τ).
ΜΟΝΤΕΛΟ = αντιγραφο live (t15 core: production + carry ανα ομαδα + B2B + ζωνη ωρας + μεταγραφες) ΧΩΡΙΣ τον κανονα «εχασε 2 ματς»,
  + απουσιες απο την αναφορα: κοστος 0.75·(αξια+2)·λεπτα/48 × βαρος, μονο παικτες που επαιξαν φετος για την ομαδα με μ.ο. ≥20′ (οπως το live).
  Α «ΟΠΩΣ ΤΟ LIVE»: βαρος 1 μονο για Out.
  Β «ΜΕ ΠΙΘΑΝΟΤΗΤΕΣ» (απο t21): Out 1 · Doubtful 0.97 · Questionable 0.45 · Probable 0.07.
PICK = edge ≥8% στην τιμη του τ · αποτελεσμα στην τιμη του τ · CLV = κινηση της γραμμης απο το τ ως το κλεισιμο προς το pick.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (πριν το τρεξιμο): το Β «κερδιζει» το Α σε μια στιγμη αν ROI υψηλοτερο συνολικα ΚΑΙ σε ≥ (σεζον−1) σεζον.
Εξοδος: t22_report_timing_out.txt"""
import os, sys, io, re, contextlib, collections, unicodedata, datetime as dt
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
# --- 1) αντιγραφο live (t15 core) ---
src = open(os.path.join(SC, 't15_trades.py'), encoding='utf-8').read().split('# ---------- (Α) περιγραφικο ----------')[0]
ns = {'__file__': os.path.join(SC, 't15_trades.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, ns)
# --- 2) γραμμες Crown με ωρα (news_test) ---
nt = {'__file__': os.path.join(SC, 'news_test.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()):
    exec(open(os.path.join(SC, 'news_test.py'), encoding='utf-8').read().split("def reg(y, X, m):")[0], nt)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; pd = ns['pd'] if 'pd' in ns else __import__('pandas'); G = ns['G']; SEAS_G = ns['SEAS_G']; dD = ns['dD']; EV = ns['EV']; ACT = ns['ACT']
assert len(nt['G']) == len(G) and (nt['G'].home.values == G.home.values).all() and (nt['G'].date.values == G.date.values).all()
LH, LA = ns['LH'], ns['LA']
VNO = ns['BASE'] + ns['adj'](1.0, -2.0, None) - 0.75 * (LH - LA)          # live χωρις τον κανονα «εχασε 2»
SER, SHIFT = nt['SER'], nt['SHIFT']; inner = ns['ns']; cover_, SIG_ = inner['cover'], inner['SIG']; value = ns['value']; A = ns['A']
from zoneinfo import ZoneInfo
NY = ZoneInfo('America/New_York')
SUF = re.compile(r'\b(jr|sr|ii|iii|iv)\b\.?', re.I)
def nkey(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return re.sub(r'[^a-z]', '', SUF.sub('', s))
# παικτες: key → pid ανα (ομαδα, σεζον) · λεπτα φετος ανα (pid, ομαδα, σεζον)
A2 = A[A.MIN > 0].copy(); A2['k'] = A2.PLAYER_NAME.map(nkey); A2['dd'] = A2.d.values.astype('datetime64[D]')
K2P = {(r.k, r.team, int(r.s)): r.pid for r in A2.drop_duplicates(['k', 'team', 's']).itertuples(index=False)}
HM = collections.defaultdict(list)
for r in A2.sort_values('dd').itertuples(index=False): HM[(r.pid, r.team, int(r.s))].append((r.dd, r.MIN))
def mins(pid, t, s, d):
    h = [m for dd_, m in HM.get((pid, t, s), []) if dd_ < d][-10:]
    return float(np.mean(h)) if h else None
# --- 3) αναφορες ---
R = []
for s in (2022, 2023, 2024, 2025, 2026):
    fn = os.path.join(ROOT, f'nba_injrep/rows_{s}.csv')
    if os.path.exists(fn):
        x = pd.read_csv(fn, dtype=str).dropna(subset=['rep_ts', 'game_date', 'team', 'key', 'status']); R.append(x)
R = pd.concat(R, ignore_index=True)
R = R[~R.reason.fillna('').str.replace(' ', '').str.contains('GLeague', case=False)]
rep = pd.to_datetime(R.rep_ts, format='%m/%d/%y %I:%M %p', errors='coerce')
R = R[rep.notna()].copy(); rep = rep[rep.notna()]
R['ep'] = [int(t.replace(tzinfo=NY).timestamp()) for t in rep]
R['gd'] = pd.to_datetime(R.game_date, format='%m/%d/%Y', errors='coerce').values.astype('datetime64[D]')
REP_BY = collections.defaultdict(list)                     # (ομαδα, ημερα αγωνα) → [(ep, key, status)]
for r in R.itertuples(index=False): REP_BY[(r.team, r.gd)].append((r.ep, r.key, r.status))
for k in REP_BY: REP_BY[k].sort()
REP_SEASONS = sorted({int(str(x)[:4]) + (1 if int(str(x)[5:7]) >= 7 else 0) for x in R.gd.unique()})
W_A = {'Out': 1.0}; W_B = {'Out': 1.0, 'Doubtful': 0.97, 'Questionable': 0.45, 'Probable': 0.07}
def status_at(t, d, tau):
    """{key: κατασταση} για την ομαδα t στο ματς της ημερας d, οπως ηταν γνωστα στο τ."""
    st = {}
    for back in (3, 2, 1, 0):                              # παλιοτερα πρωτα → τα νεοτερα γραφουν απο πανω
        for ep, k, s in REP_BY.get((t, d - np.timedelta64(back, 'D')), ()):
            if ep <= tau: st[k] = (ep, s)
    return {k: v[1] for k, v in st.items()}
def abs_cost(t, d, s, tau, W):
    c = 0.0; det = []
    for k, stt in status_at(t, d, tau).items():
        w = W.get(stt)
        if not w: continue
        pid = K2P.get((k, t, s))
        if pid is None: continue
        m = mins(pid, t, s, d)
        if m is None or m < 20: continue                    # οπως το live: επαιξε φετος για την ομαδα, ≥20′
        cc = w * 0.75 * (value(pid, s - 1) + 2.0) * m / 48; c += cc; det.append((k, stt, round(cc, 2)))
    return c, det
def line_at(rows, tau, sw):
    pre = [x for x in rows if x[0] <= tau]
    if not pre: return None
    x = pre[-1]; L = -x[1] * (-1 if sw else 1); oh, oa = (1 + x[2], 1 + x[3]) if not sw else (1 + x[3], 1 + x[2])
    ph = (1 / oh) / (1 / oh + 1 / oa)
    from statistics import NormalDist
    fair = -L + SIG_ * NormalDist().inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
    return float(L), float(oh), float(oa), fair, x[0]
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
if os.environ.get('T22_AUDIT'):                           # ελεγχος: σταρ Questionable → Out μεσα στη μερα, γραμμη πριν/μετα
    SG = pd.read_csv(os.path.join(ROOT, 'nba_injrep/status_games.csv'))
    c = SG[(SG.role >= 30) & (SG['s_Τ−24ω'] == 'Questionable') & (SG['s_τελευταια'] == 'Out') & (SG.sea == 2025)].head(3)
    GI = {(G.home.values[i], str(dD[i])): i for i in range(len(G))}; GI.update({(G.away.values[i], str(dD[i])): i for i in range(len(G))})
    ATH = ZoneInfo('Europe/Athens')
    for _, r in c.iterrows():
        i = GI.get((r['t'], r['d']));
        if i is None or i not in SER: continue
        sw, tip, r21, _ = SER[i]; rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
        P(f"== {r['name']} ({r['t']}, {r['role']:.0f}′) · {G.home.values[i]}-{G.away.values[i]} {r['d']} · τζαμπολ {dt.datetime.fromtimestamp(tip, ATH):%d/%m %H:%M} Ελλαδα")
        d = dD[i]
        for ep, k, st in sorted(REP_BY.get((r['t'], d), ())):
            if k == r['k']: P(f"   αναφορα {dt.datetime.fromtimestamp(ep, ATH):%d/%m %H:%M}: {st}")
        for x in rows[:1] + rows[-12:]:
            ln = line_at(rows, x[0], sw); P(f"   γραμμη {dt.datetime.fromtimestamp(x[0], ATH):%d/%m %H:%M}: γηπ {ln[0]:+g} (δικαιη {ln[3]:+.1f})")
        c0, det = abs_cost(r['t'], d, int(SEAS_G[i]), rows[0][0], W_B); c1, det1 = abs_cost(r['t'], d, int(SEAS_G[i]), tip - 1800, W_B)
        P(f"   κοστος απουσιων {r['t']} στο ανοιγμα {c0:.2f} {det} · στο Τ−30′ {c1:.2f} {det1}")
    open(os.path.join(SC, 't22_audit_out.txt'), 'w', encoding='utf-8').write(chr(10).join(out)); sys.exit()
TAUS = (('ανοιγμα', None), ('Τ−12ω', 12), ('Τ−6ω', 6), ('Τ−2ω', 2), ('Τ−30′', 0.5))
recs = []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]): continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if len(rows) < 1: continue
    close = line_at(rows, tip, sw); h, a, d = G.home.values[i], G.away.values[i], dD[i]
    for lab, hrs in TAUS:
        tau = rows[0][0] if hrs is None else tip - hrs * 3600
        if hrs is not None and tau < rows[0][0]: continue    # η γραμμη δεν ειχε ανοιξει ακομα
        ln = line_at(rows, tau, sw)
        if not ln: continue
        L, oh, oa, fair, _ = ln
        for vname, W in (('Α', W_A), ('Β', W_B)):
            ch, dh = abs_cost(h, d, s, tau, W); ca, da = abs_cost(a, d, s, tau, W)
            m = VNO[i] - ch + ca
            pw, pp, pl = cover_(m, L, SIG_); e1, e2 = pw * oh + pp - 1, pl * oa + pp - 1
            sd, e, od_ = (1, e1, oh) if e1 >= e2 else (-1, e2, oa)
            if e < .08: continue
            x = (ACT[i] + L) * sd; res = (od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0)
            recs.append(dict(i=i, sea=s, tau=lab, v=vname, res=res, clv=sd * (close[3] - fair), hrs=(tip - tau) / 3600, mon=int(G.date.dt.month.values[i])))
X = pd.DataFrame(recs)
def cell(d):
    if not len(d): return '      —'
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+6.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, {int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f}π'
P(f'NBA · ΣΤΙΓΜΗ ΑΠΟΦΑΣΗΣ: ΤΙΜΗ ΚΑΙ ΑΠΟΥΣΙΕΣ ΤΗΝ ΙΔΙΑ ΩΡΑ · σεζον με αναφορες {[x for x in REP_SEASONS if x in EV]} · αντιγραφο live')
P('κελι = ROI στην τιμη της στιγμης (picks, μοναδες, θετικες σεζον) · CLV = κινηση ως το κλεισιμο προς εμας')
P(f'{"στιγμη":10s} | {"Α: οπως το live (μονο Out)":52s} | {"Β: με πιθανοτητες (D .97 · Q .45 · P .07)":52s}')
for lab, _ in TAUS:
    a = X[(X.tau == lab) & (X.v == 'Α')]; b = X[(X.tau == lab) & (X.v == 'Β')]
    P(f'{lab:10s} | {cell(a):52s} | {cell(b):52s}')
P('');  P('-- μονο Ιαν-Φεβ --')
for lab, _ in TAUS:
    a = X[(X.tau == lab) & (X.v == 'Α') & X.mon.isin([1, 2])]; b = X[(X.tau == lab) & (X.v == 'Β') & X.mon.isin([1, 2])]
    P(f'{lab:10s} | {cell(a):52s} | {cell(b):52s}')
open(os.path.join(SC, 't22_report_timing_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
X.to_csv(os.path.join(ROOT, 'nba_injrep', 't22_picks.csv'), index=False)
