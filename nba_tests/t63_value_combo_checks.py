# -*- coding: utf-8 -*-
"""t63_value_combo_checks.py — 3 ΕΠΙΠΛΕΟΝ ΕΛΕΓΧΟΙ ΓΙΑ ΤΙΣ ΕΚΔΟΧΕΣ ΠΕΡΣΙΝΗΣ ΑΞΙΑΣ ΑΠΟΝΤΑ (23/10/2026, Στελιος).
Συνεχεια του t62_value_combos.py: ιδιες εκδοχες βασης (ετος s−1, μεσος ΔΙΑΘΕΣΙΜΩΝ δεικτων × mp/(mp+500), κανενας → −1, ΣΩΣΤΟ BPM):
  1 DARKO · 2 LEBRON · 3 BPM · 4 DARKO+LEBRON · 5 DARKO+BPM · 6 LEBRON+BPM · 7 ολοι (σωστο BPM) · ref = σημερινο value() (λαθος BPM).
  Μιξη (live τυπος): v = (λεπτα_φετος·v_box + 500·βαση)/(λεπτα_φετος + 500), v_box = φετινη box αξια (FIT του t59, εκπαιδευση s′ < s, ΑΜΕΤΑΒΛΗΤΟ).

ΤΕΣΤ Α — ΣΥΜΦΩΝΙΑ ΜΕ ΤΗΝ ΑΓΟΡΑ ΣΤΙΣ ΕΙΔΗΣΕΙΣ ΑΠΟΥΣΙΑΣ. Ειδησεις NBC 5 σεζον απο t50_news_5s.py (exec ως "KS = (-15", οπως t53):
  kind='out', ολα τα st0 (εκτος του ηδη Out, που το t50 πεταει), παικτης ρολου ≥20′ (λεπτα = mins του t50, φετινα).
  Κινηση = δικαιη γραμμη Crown (αναμενομενη διαφορα γηπ.) (α) στο t0+15′ (μονο αν ≤ τζαμπολ) και (β) στο τζαμπολ ΜΕΙΟΝ δικαιη γραμμη στο t0−1′,
  προς την πλευρα της ειδησης (+ = η αγορα κινηθηκε ΚΟΝΤΡΑ στην ομαδα του αποντα).
  Κοστος εκδοχης = 0.75·(v+2)·λεπτα/48 με v = (i) μονο βαση, (ii) μιξη με φετινη box ως τη μερα της ειδησης (box με ημερομηνια < ημερα ειδησης, ωρα ΗΠΑ UTC−5).
  Μετρα: Pearson συσχετιση (κινηση, κοστος) και κλιση OLS κινηση = a + b·κοστος, συνολικα και ανα σεζον, ΤΣ με bootstrap (2000, ζευγαρωτα για ολες τις εκδοχες).
TEST Β — CLV ΤΩΝ PICKS: ιδιο στησιμο picks με t62 (ανοιγμα Crown, edge ≥8%, σ 13.5, μιξη M=500). CLV = (δικαιη κλεισιματος − δικαιη ανοιγματος)
  προς την πλευρα του pick (ποντοι χαντικαπ). cfair απο _t29_games.csv (tau=='ανοιγμα', αντιστοιχιση (ημερομηνια, γηπεδουχος)).
  Μεσος CLV ± ΤΣ, % picks CLV > 0, ανα σεζον, ζευγαρωτη διαφορα μεσου CLV vs 7 (bootstrap ανα ματς) και ΣCLV διαφορα vs 7.
ΤΕΣΤ Γ — ΣΤΑΡ: OLS (act − m0) = a + b_σταρ·καθαρο_κοστος_σταρ + b_αλλοι·καθαρο_κοστος_υπολοιπων (ολα τα ματς του t59/t62, m0 χωρις απουσιες).
  Σταρ = μεσος ΔΙΑΘΕΣΙΜΩΝ (DARKO, LEBRON) ακατεργαστων της s−1 ≥ 3 (και 2ο οριο ≥ 2) — ΙΔΙΟΣ ορισμος για ολες τις εκδοχες.
  Μιξη M=500 και μονο βαση. Πιο κοντα στο 1 = καλυτερο. Και μεσο κοστος (w·0.75·(v+2)·λεπτα/48) εγγραφης σταρ ανα εκδοχη.

ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ το τρεξιμο): η 4 (DARKO+LEBRON) ΕΠΙΒΕΒΑΙΩΝΕΤΑΙ αν ειναι καλυτερη απο την 7 (ολοι, σωστο BPM)
  σε Α (μεγαλυτερη συσχετιση με την κινηση στο ΤΖΑΜΠΟΛ, μιξη) ΚΑΙ Β (μεγαλυτερος μεσος CLV) ΚΑΙ Γ (b_σταρ για σταρ ≥3, μιξη, πιο κοντα στο 1).
  3/3 = «επιβεβαιωνεται» · 2/3 = «αναμεικτο» · ≤1/3 = «δεν επιβεβαιωνεται». Δειχνονται ολες οι εκδοχες.
ΕΛΕΓΧΟΙ: αναπαραγωγη t62 (ref M=500 → +164.6 μοναδες, 2996 picks) · ref βαση στις ειδησεις == value() του t50 · ειδησεις με φετινο box.
ΕΛΕΓΧΟΣ ΠΑΡΑΔΕΙΓΜΑΤΩΝ: 3 πραγματικες ειδησεις απουσιας σταρ (ονομα, ημερομηνια, κινηση αγορας, κοστος καθε εκδοχης).
Εξοδος: t63_value_combo_checks_out.txt"""
import os, sys, io, re, contextlib, collections, pickle, datetime as dt
import numpy as np, pandas as pd
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
# ---- t59 ως vmix (cache) ----
src = open(os.path.join(SC, 't59_inseason_value.py'), encoding='utf-8').read().split('def vmix(M):')[0]
g = {'__file__': os.path.join(SC, 't59_inseason_value.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
AB_, D, NM, feats, FIT, MU_BY = g['AB_'], g['D'], g['NM'], g['feats'], g['FIT'], g['MU_BY']
# ---- nba_roster_adj ----
cwd = os.getcwd(); os.chdir(ROOT)
rsrc = open(os.path.join(ROOT, 'nba_roster_adj.py'), encoding='utf-8').read().split('OUT, ABS = {}, {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
R = {}
with contextlib.redirect_stdout(_B()): exec(rsrc, R)
VM, MPT, value, nk, NAME2PID = R['M'], R['MPT'], R['value'], R['nk'], R['NAME2PID']
# ---- ΣΩΣΤΟ BPM (ιδιο με t62) ----
rows = []
for y in range(2020, 2026):
    fn = os.path.join(ROOT, 'bbref_cache', f'NBA_{y}_advanced.html')
    if not os.path.exists(fn): continue
    t = open(fn, encoding='utf-8', errors='ignore').read()
    k = t.find('id="advanced_post"'); t = t[:k] if k >= 0 else t
    t = t.replace('<strong>', '').replace('</strong>', '')
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
        nm = re.search(r'data-stat="name_display"[^>]*>(?:<a[^>]*>)?([^<]+)', tr)
        b = re.search(r'data-stat="bpm"[^>]*>([-\d.]+)<', tr); mp = re.search(r'data-stat="mp"[^>]*>(\d+)<', tr)
        if nm and b and mp: rows.append((nk(nm.group(1)), y, float(b.group(1)), int(mp.group(1)), nm.group(1)))
os.chdir(cwd)
br = pd.DataFrame(rows, columns=['k', 'y', 'bpm', 'mp', 'nm']).sort_values('mp', ascending=False).drop_duplicates(['k', 'y'])
BPMC = {(NAME2PID[k], y): v for k, y, v in zip(br.k, br.y, br.bpm) if k in NAME2PID}
IDX = {'DARKO': VM['DARKO'], 'LEBRON': VM['LEBRON'], 'BPM': BPMC, 'BPMold': VM['BPM']}
VER = collections.OrderedDict([('1 DARKO', ['DARKO']), ('2 LEBRON', ['LEBRON']), ('3 BPM', ['BPM']), ('4 DARKO+LEBRON', ['DARKO', 'LEBRON']),
                               ('5 DARKO+BPM', ['DARKO', 'BPM']), ('6 LEBRON+BPM', ['LEBRON', 'BPM']), ('7 ολοι', ['DARKO', 'LEBRON', 'BPM']),
                               ('ref (σημερινο)', ['DARKO', 'LEBRON', 'BPMold'])])
def vver(p, y, idx):
    vs = [IDX[i][(p, y)] for i in idx if (p, y) in IDX[i]]
    if not vs: return -1.0
    mp = MPT.get((p, y), 0.0); return float(np.mean(vs)) * mp / (mp + 500)
def starv(p, y):
    vs = [IDX[i][(p, y)] for i in ('DARKO', 'LEBRON') if (p, y) in IDX[i]]
    return float(np.mean(vs)) if vs else np.nan
# ---- ειδησεις t50 (cache) ----
NC = os.environ.get('T63_NEWS_CACHE')
if NC and os.path.exists(NC):
    NEWSR = pickle.load(open(NC, 'rb'))
else:
    s50 = open(os.path.join(SC, 't50_news_5s.py'), encoding='utf-8').read().split("KS = (-15")[0]
    s50 = s50.replace("N.append(dict(i=i, S=S, t0=t0, src=src or 'NBC',", "N.append(dict(i=i, S=S, t0=t0, k=k, d=d, pid=pid, m=m, src=src or 'NBC',")
    g50 = {'__file__': os.path.join(SC, 't50_news_5s.py'), '__name__': 'x'}
    with contextlib.redirect_stdout(_B()): exec(s50, g50)
    D50, at_h, ACT50 = g50['D'], g50['at_h'], g50['ACT']; G50 = g50['G']
    NEWSR = []
    for r in D50.itertuples(index=False):
        if r.kind != 'out': continue
        b0 = at_h(r.i, r.t0 - 60); c = at_h(r.i, r.tip); f15 = at_h(r.i, r.t0 + 900) if r.t0 + 900 <= r.tip else None
        NEWSR.append(dict(i=int(r.i), S=int(r.S), t0=float(r.t0), tip=float(r.tip), pid=r.pid, m=float(r.m), team=r.team, home=bool(r.home), st0=r.st0,
                          hc=float(r.hc), hrs=float(r.hrs), d=str(r.d)[:10], hm=G50.home.values[r.i], aw=G50.away.values[r.i],
                          f0=(b0['fair'] if b0 else np.nan), f15=(f15['fair'] if f15 else np.nan), fc=(c['fair'] if c else np.nan), act=float(ACT50[r.i])))
    if NC: pickle.dump(NEWSR, open(NC, 'wb'))
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open(os.path.join(SC, 't63_value_combo_checks_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
P('t63 — 3 επιπλεον ελεγχοι εκδοχων περσινης αξιας αποντα (NBA, σεζον 2022-2026 = 2021-22 … 2025-26)')
INF = float('inf'); RNG = np.random.default_rng(63); BOOT = 2000
# =========================== κοινο: προβλεψεις t62 ===========================
BASE = {nm_: np.array([vver(p, s - 1, idx) for p, s in zip(AB_.pid, AB_.s)]) for nm_, idx in VER.items()}
def vmix(base, M):
    if M == INF: return base
    vn = np.where(AB_.ng.values > 0, AB_.vnow.values, base); mn = AB_.minnow.values
    return (mn * vn + M * base) / (mn + M)
PRED, COST = {}, {}
for nm_ in VER:
    for M in (500, INF):
        v = vmix(BASE[nm_], M); cost = AB_.w.values * 0.75 * (v + 2.0) * AB_.m.values / 48
        adj = np.zeros(len(D)); np.add.at(adj, AB_.q.values, AB_.sg.values * cost)
        PRED[(nm_, M)] = D.m0.values + adj; COST[(nm_, M)] = cost
from statistics import NormalDist
N_ = NormalDist(); SIG = 13.5
def cover(m, L):
    if abs(L - round(L)) < 1e-9: pw = 1 - N_.cdf((-L + .5 - m) / SIG); pl = N_.cdf((-L - .5 - m) / SIG); return pw, 1 - pw - pl, pl
    pw = 1 - N_.cdf((-L - m) / SIG); return pw, 0.0, 1 - pw
def per_game(pred):
    res = np.zeros(len(D)); side = np.zeros(len(D))
    for q, (r, mp) in enumerate(zip(D.itertuples(index=False), pred)):
        pw, pp, pl = cover(mp, r.L); e1, e2 = pw * r.oh + pp - 1, pl * r.oa + pp - 1
        sd, e, od = (1, e1, r.oh) if e1 >= e2 else (-1, e2, r.oa)
        if e < .08: continue
        x = (r.act + r.L) * sd; res[q] = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0); side[q] = sd
    return res, side
PG = {nm_: per_game(PRED[(nm_, 500)]) for nm_ in VER}
res_ref, sd_ref = PG['ref (σημερινο)']
ok = abs(res_ref.sum() - 164.6) < 0.05 and int((sd_ref != 0).sum()) == 2996
P(f'ΕΛΕΓΧΟΣ ΑΝΑΠΑΡΑΓΩΓΗΣ t62: ref M=500 → μοναδες {res_ref.sum():+.1f} · picks {int((sd_ref != 0).sum())} (στοχος +164.6 · 2996) {"✓" if ok else "✗ ΣΤΟΠ"}')
if not ok: save(); sys.exit(1)
SE = sorted(D.sea.unique()); ys = D.sea.values
def boot_se(f, n, B=BOOT):
    vals = [f(RNG.integers(0, n, n)) for _ in range(B)]; return float(np.std(vals, ddof=1))
# =========================== ΤΕΣΤ Α ===========================
E = pd.DataFrame(NEWSR)
P(''); P('=' * 110); P('ΤΕΣΤ Α — ΣΥΜΦΩΝΙΑ ΚΟΣΤΟΥΣ ΕΚΔΟΧΗΣ ΜΕ ΤΗΝ ΚΙΝΗΣΗ ΤΗΣ ΑΓΟΡΑΣ ΣΤΙΣ ΕΙΔΗΣΕΙΣ «ΕΚΤΟΣ» (NBC, Crown δικαιη γραμμη)')
n_all = len(E); E = E[np.isfinite(E.f0) & np.isfinite(E.fc)].reset_index(drop=True)
P(f'ειδησεις «εκτος» (ρολου ≥20′, οχι ηδη Out): {n_all} · με γραμμη στο t0−1′ και στο τζαμπολ: {len(E)} · ανα σεζον ' + ' · '.join(f'{s}: {(E.S == s).sum()}' for s in sorted(E.S.unique())))
P('  κατασταση πριν την ειδηση: ' + ' · '.join(f'{k} {v}' for k, v in E.st0.value_counts().items()))
dirn = np.where(E.home.values, -1.0, 1.0)
E['mv_tip'] = dirn * (E.fc.values - E.f0.values); E['mv15'] = dirn * (E.f15.values - E.f0.values)
# φετινη box ως τη μερα της ειδησης (ημερα ΗΠΑ ≈ UTC−5)
dnews = np.array([np.datetime64(dt.datetime.fromtimestamp(t0 - 5 * 3600, dt.timezone.utc).date()).astype('datetime64[D]').astype(np.int64) for t0 in E.t0])
VN, MN, NGv = [], [], []
for p, s, d in zip(E.pid, E.S, dnews):
    if s not in FIT: VN.append(np.nan); MN.append(0.0); NGv.append(0); continue
    ft, mn, ng, last = feats(p, s, int(d), MU_BY[s]); c_ = FIT[s]
    VN.append(c_[0] + ft @ c_[1:] if ng else np.nan); MN.append(mn); NGv.append(ng)
E['vnow'], E['minnow'], E['ng'] = VN, MN, NGv
E['star'] = [starv(p, s - 1) for p, s in zip(E.pid, E.S)]
for nm_, idx in VER.items():
    b = np.array([vver(p, s - 1, idx) for p, s in zip(E.pid, E.S)])
    vn = np.where(E.ng.values > 0, E.vnow.values, b); vmx = (E.minnow.values * vn + 500 * b) / (E.minnow.values + 500)
    E[f'b_{nm_}'] = b; E[f'x_{nm_}'] = vmx
    E[f'cb_{nm_}'] = 0.75 * (b + 2) * E.m.values / 48; E[f'cx_{nm_}'] = 0.75 * (vmx + 2) * E.m.values / 48
chk = np.max(np.abs(E['cb_ref (σημερινο)'].values - E.hc.values))
P(f'ΕΛΕΓΧΟΣ: |κοστος ref (βαση) − αξια t50 (value())| μεγιστη {chk:.2e} (πρεπει 0) · ειδησεις με φετινο box πριν την ημερα: {int((E.ng > 0).sum())}/{len(E)}'
  f' · διαμεσα φετινα λεπτα ως τη μερα {np.median(E.minnow):.0f}′')
P(f'  μεση κινηση αγορας (ποντοι, + = κοντρα στην ομαδα του αποντα): t0+15′ {np.nanmean(E.mv15):+.2f} (n {int(np.isfinite(E.mv15).sum())}) · τζαμπολ {E.mv_tip.mean():+.2f} (n {len(E)})')
def corr_slope(x, y):
    xm, ym = x - x.mean(), y - y.mean(); sxx = (xm * xm).sum()
    return float((xm * ym).sum() / np.sqrt(sxx * (ym * ym).sum())), float((xm * ym).sum() / sxx)
BI = RNG.integers(0, len(E), (BOOT, len(E)))
def boot_cs(X, Y, bi):
    xb, yb = X[bi], Y[bi]; xm = xb - xb.mean(1, keepdims=True); ym = yb - yb.mean(1, keepdims=True)
    sxy = (xm * ym).sum(1); sxx = (xm * xm).sum(1); syy = (ym * ym).sum(1); return sxy / np.sqrt(sxx * syy), sxy / sxx
RESA = {}
for mvc, mlab in (('mv_tip', 'τζαμπολ'), ('mv15', 't0+15′')):
    mk = np.isfinite(E[mvc].values); Y = E[mvc].values[mk]; Ek = E[mk].reset_index(drop=True); n = len(Y)
    bi = RNG.integers(0, n, (BOOT, n)); S_ = Ek.S.values
    for cpre, clab in (('cx', 'ΜΙΞΗ M=500 (κυρια)'), ('cb', 'ΜΟΝΟ ΒΑΣΗ')):
        P(''); P(f'ΠΙΝΑΚΑΣ Α · κινηση ως {mlab} · κοστος {clab} · n ειδησεων {n} · συσχετιση r ± ΤΣ (bootstrap) · κλιση b (ποντοι κινησης ανα ποντο κοστους) ± ΤΣ · '
                 f'Δr vs 7 ± ΤΣ (ζευγαρωτο) · r ανα σεζον (ΤΣ)')
        bc7, _ = boot_cs(Ek[f'{cpre}_7 ολοι'].values, Y, bi)
        for nm_ in VER:
            X = Ek[f'{cpre}_{nm_}'].values; r, b = corr_slope(X, Y); bc, bs = boot_cs(X, Y, bi)
            r7 = corr_slope(Ek[f'{cpre}_7 ολοι'].values, Y)[0]; RESA[(mvc, cpre, nm_)] = r
            pers = []
            for s in sorted(set(S_)):
                m_ = S_ == s; xs, ysn = X[m_], Y[m_]; rs, _ = corr_slope(xs, ysn)
                bis = RNG.integers(0, m_.sum(), (500, m_.sum())); rb, _ = boot_cs(xs, ysn, bis); pers.append(f'{s % 100}:{rs:.3f}({np.std(rb, ddof=1):.3f})')
            P(f'  {nm_:16s}: r {r:.4f} ± {np.std(bc, ddof=1):.4f} · b {b:.3f} ± {np.std(bs, ddof=1):.3f} · Δr vs 7 {r - r7:+.4f} ± {np.std(bc - bc7, ddof=1):.4f} · '
              f'μεσο κοστος {X.mean():.2f} π. · ανα σεζον ' + ' '.join(pers))
# =========================== ΤΕΣΤ Β ===========================
P(''); P('=' * 110); P('ΤΕΣΤ Β — CLV ΤΩΝ PICKS (χαντικαπ ανοιγμα Crown, edge ≥8%, μιξη M=500) · CLV = δικαιη κλεισιματος − δικαιη ανοιγματος προς το pick (ποντοι)')
X29 = pd.read_csv(os.path.join(SC, '_t29_games.csv')); X29 = X29[X29.tau == 'ανοιγμα']
dup = X29.duplicated(['date', 'home']).sum()
CF = {(str(a)[:10], h): (c, f) for a, h, c, f in zip(X29.date, X29.home, X29.cfair, X29.fair)}
cf = np.array([CF.get((str(a)[:10], h), (np.nan, np.nan))[0] for a, h in zip(D.date, D.home)])
fo = np.array([CF.get((str(a)[:10], h), (np.nan, np.nan))[1] for a, h in zip(D.date, D.home)])
P(f'ΕΛΕΓΧΟΣ αντιστοιχισης: διπλα (ημερομηνια, γηπ.) στο _t29 {dup} · ματς χωρις cfair {int(np.isnan(cf).sum())}/{len(D)} · '
  f'μεγιστη |fair _t29 − fair D| {np.nanmax(np.abs(fo - D.fair.values)):.2e} (πρεπει 0) · μεση |κλεισιμο − ανοιγμα| {np.nanmean(np.abs(cf - D.fair.values)):.2f} π.')
CLV = {nm_: np.where(PG[nm_][1] != 0, PG[nm_][1] * (cf - D.fair.values), 0.0) for nm_ in VER}
HIT = {nm_: PG[nm_][1] != 0 for nm_ in VER}
BG = RNG.integers(0, len(D), (BOOT, len(D)))
def bmean(cl, h, bi):
    return (cl[bi] * h[bi]).sum(1) / h[bi].sum(1)
b7 = bmean(CLV['7 ολοι'], HIT['7 ολοι'], BG); m7 = CLV['7 ολοι'][HIT['7 ολοι']].mean()
RESB = {}
P('  εκδοχη          : μεσος CLV ± ΤΣ (π.) · % CLV>0 · % CLV<0 · n picks · ΣCLV (π.) · ανα σεζον μεσος CLV (n) · Δμεσου CLV vs 7 ± ΤΣ (bootstrap ματς) · ΔΣCLV vs 7 ± ΤΣ')
for nm_ in VER:
    h = HIT[nm_]; c = CLV[nm_][h]; RESB[nm_] = c.mean(); bm = bmean(CLV[nm_], h, BG)
    dsum = CLV[nm_] - CLV['7 ολοι']
    P(f'  {nm_:16s}: {c.mean():+.3f} ± {c.std(ddof=1) / np.sqrt(len(c)):.3f} · {100 * (c > 0).mean():4.1f}% · {100 * (c < 0).mean():4.1f}% · n {len(c)} · Σ {c.sum():+7.1f} · ανα σεζον '
      + ' '.join(f'{s % 100}:{CLV[nm_][h & (ys == s)].mean():+.3f}({int((h & (ys == s)).sum())})' for s in SE)
      + f' · Δ {c.mean() - m7:+.4f} ± {np.std(bm - b7, ddof=1):.4f} · ΔΣ {dsum.sum():+.1f} ± {dsum.std(ddof=1) * np.sqrt(len(dsum)):.1f}')
P(f'  (για αναφορα: CLV ολων των ματς αν παιζαμε παντα γηπεδουχο: {np.nanmean(cf - D.fair.values):+.3f} π.)')
# =========================== ΤΕΣΤ Γ ===========================
P(''); P('=' * 110); P('ΤΕΣΤ Γ — ΣΤΑΡ: OLS (act − m0) = a + b_σταρ·καθαρο κοστος σταρ + b_αλλοι·καθαρο κοστος υπολοιπων (ολα τα ματς, b=1 σωστο μεγεθος)')
SV = np.array([starv(p, s - 1) for p, s in zip(AB_.pid, AB_.s)])
YV = D.act.values - D.m0.values
RESC = {}
for thr in (3.0, 2.0):
    st = np.nan_to_num(SV, nan=-99) >= thr
    gst = np.unique(AB_.q.values[st])
    P(''); P(f'ΟΡΙΟ σταρ: μεσος (DARKO, LEBRON) s−1 ≥ {thr:.0f} · εγγραφες αποντων σταρ {int(st.sum())} (Out {int((st & (AB_.stt.values == "Out")).sum())}) · '
             f'διαφορετικοι παικτες-σεζον {len(set(zip(AB_.pid.values[st], AB_.s.values[st])))} · ματς με σταρ απον {len(gst)}')
    for M, tag in ((500, 'ΜΙΞΗ M=500'), (INF, 'ΜΟΝΟ ΒΑΣΗ')):
        P(f'  [{tag}] εκδοχη: b_σταρ ± ΤΣ · |b_σταρ − 1| · b_αλλοι ± ΤΣ · μεσο κοστος εγγραφης σταρ (π., με βαρος w) · μεσο κοστος σταρ Out (π.) · b_σταρ ανα σεζον')
        for nm_ in VER:
            cost = COST[(nm_, M)]
            a1 = np.zeros(len(D)); a2 = np.zeros(len(D))
            np.add.at(a1, AB_.q.values[st], AB_.sg.values[st] * cost[st]); np.add.at(a2, AB_.q.values[~st], AB_.sg.values[~st] * cost[~st])
            Xr = np.c_[np.ones(len(D)), a1, a2]; bb = np.linalg.lstsq(Xr, YV, rcond=None)[0]; e = YV - Xr @ bb
            cov = np.linalg.inv(Xr.T @ Xr) * (e @ e) / (len(YV) - 3)
            pers = []
            for s in SE:
                m_ = ys == s; bs_ = np.linalg.lstsq(Xr[m_], YV[m_], rcond=None)[0]; es = YV[m_] - Xr[m_] @ bs_
                cs = np.linalg.inv(Xr[m_].T @ Xr[m_]) * (es @ es) / (m_.sum() - 3); pers.append(f'{s % 100}:{bs_[1]:.2f}({np.sqrt(cs[1, 1]):.2f})')
            RESC[(thr, M, nm_)] = bb[1]
            P(f'    {nm_:16s}: b_σταρ {bb[1]:.3f} ± {np.sqrt(cov[1, 1]):.3f} · |b−1| {abs(bb[1] - 1):.3f} · b_αλλοι {bb[2]:.3f} ± {np.sqrt(cov[2, 2]):.3f} · '
              f'κοστος σταρ {cost[st].mean():.2f} · σταρ Out {cost[st & (AB_.stt.values == "Out")].mean():.2f} · ανα σεζον ' + ' '.join(pers))
# =========================== ΚΡΙΤΗΡΙΟ ===========================
P(''); P('=' * 110); P('ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ: 4 (DARKO+LEBRON) vs 7 (ολοι, σωστο BPM)')
cA = RESA[('mv_tip', 'cx', '4 DARKO+LEBRON')] > RESA[('mv_tip', 'cx', '7 ολοι')]
cB = RESB['4 DARKO+LEBRON'] > RESB['7 ολοι']
cC = abs(RESC[(3.0, 500, '4 DARKO+LEBRON')] - 1) < abs(RESC[(3.0, 500, '7 ολοι')] - 1)
P(f"  Α r(κινηση τζαμπολ, κοστος μιξη): 4 {RESA[('mv_tip', 'cx', '4 DARKO+LEBRON')]:.4f} vs 7 {RESA[('mv_tip', 'cx', '7 ολοι')]:.4f} → {'✓' if cA else '✗'}")
P(f"  Β μεσος CLV: 4 {RESB['4 DARKO+LEBRON']:+.3f} vs 7 {RESB['7 ολοι']:+.3f} π. → {'✓' if cB else '✗'}")
P(f"  Γ b_σταρ (≥3, μιξη): 4 {RESC[(3.0, 500, '4 DARKO+LEBRON')]:.3f} vs 7 {RESC[(3.0, 500, '7 ολοι')]:.3f} (πιο κοντα στο 1) → {'✓' if cC else '✗'}")
k = int(cA) + int(cB) + int(cC)
P(f"  → {k}/3: {'ΕΠΙΒΕΒΑΙΩΝΕΤΑΙ' if k == 3 else ('ΑΝΑΜΕΙΚΤΟ' if k == 2 else 'ΔΕΝ ΕΠΙΒΕΒΑΙΩΝΕΤΑΙ')}")
# =========================== ΠΑΡΑΔΕΙΓΜΑΤΑ ===========================
P(''); P('=' * 110); P('ΕΛΕΓΧΟΣ ΠΑΡΑΔΕΙΓΜΑΤΩΝ — 3 πραγματικες ειδησεις «εκτος» σταρ (μεσος DARKO/LEBRON s−1 ≥ 3), διαφορετικοι παικτες, μεγαλυτερος δεικτης σταρ:')
cand = E[E.star >= 3].sort_values('star', ascending=False); seen = set(); kk = 0
for _, r in cand.iterrows():
    if r.pid in seen: continue
    seen.add(r.pid); kk += 1
    p, y = r.pid, int(r.S) - 1; mp = MPT.get((p, y), 0.0)
    tl = dt.datetime.fromtimestamp(r.t0, dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    P(f'  [{kk}] {NM.get(p)} [pid {p}] · {r.team} ({"γηπ." if r.home else "φιλοξ."}) στο {r.aw}@{r.hm} {r.d} · ειδηση {tl} ({r.hrs:.1f}ω πριν) · πριν: {r.st0} · '
      f'λεπτα {r.m:.1f}′ · τελικο σκορ γηπ−φιλ {r.act:+.0f}')
    P(f'      δικαιη γραμμη γηπ. (αναμ. διαφορα): t0−1′ {r.f0:+.2f} · t0+15′ {r.f15:+.2f} · τζαμπολ {r.fc:+.2f} → κινηση κοντρα στην ομαδα του: +15′ {r.mv15:+.2f} π. · τζαμπολ {r.mv_tip:+.2f} π.')
    P(f'      ακατεργαστοι s−1: DARKO {IDX["DARKO"].get((p, y), "—")} · LEBRON {IDX["LEBRON"].get((p, y), "—")} · BPM σωστο {IDX["BPM"].get((p, y), "—")} · BPM σημερινο {IDX["BPMold"].get((p, y), "—")}'
      f' · περσινα λεπτα {mp:.0f} (×{mp / (mp + 500):.3f}) · φετινη box {r.vnow:+.2f} με {r.minnow:.0f}′')
    for nm_ in VER:
        P(f'      {nm_:16s}: βαση {r[f"b_{nm_}"]:+.2f} → κοστος {r[f"cb_{nm_}"]:.2f} π. · μιξη {r[f"x_{nm_}"]:+.2f} → κοστος {r[f"cx_{nm_}"]:.2f} π.')
    if kk == 3: break
save()
