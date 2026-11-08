# -*- coding: utf-8 -*-
"""el_scorer_pos_known_test.py — ΙΔΙΟ με el_scorer_pos_gtdtime_test.py (κανονες: ποντοι πανω απο 9, εξτρα γκαρντ, σεντερ· αμφιβολοι × p ανα
στιγμη) αλλα οι ΣΥΝΤΕΛΕΣΤΕΣ μετρανται απο ΟΤΙ ΗΤΑΝ ΓΝΩΣΤΟ (σελιδα RotoWire στο ΤΖΑΜΠΟΛ: OUT ×1 + αμφιβολοι × p), ΟΧΙ απο «ποιος δεν επαιξε»
(28/10/2026, Στελιος «τρεξε ολα τα τεστ»). Αφορμη: οι γνωστες απουσιες κοστιζουν λιγοτερο απο τις αιφνιδιες → η φυσικη απο box φουσκωνει.
Εφαρμογη σε ολες τις στιγμες. ΚΡΙΤΗΡΙΑ ΙΔΙΑ (κλιση 0.7-1.3 & θετικη ≥4/5 παντου · |μεροληψια| ≤ 1 · WF ≥ live · placebo < 10%).
Εξοδος: el_scorer_pos_known_test_out.txt"""
import os, sys, io, contextlib, collections, re, unicodedata, time, json, glob
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
def save(): open('el_scorer_pos_known_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
G = S['G']; rows, ys, YT, YH, YA, SE, HELD_B, NAME = S['rows'], S['ys'], S['YT'], S['YH'], S['YA'], S['SE'], S['HELD_B'], S['NAME']
picks, fit, apply, loso, wf, PL = (S[k] for k in ('picks', 'fit', 'apply', 'loso', 'wf', 'PL'))
news_state, PPAGE, rolek, PSRC, REC = G['news_state'], G['PPAGE'], G['rolek'], G['PSRC'], G['REC']
N = len(rows); TOT, T0 = S['TOT'], S['T0']; WF4 = np.isin(ys, SE[1:]); rng = np.random.default_rng(7)
# ---- ποντοι/ματς: φετος (10 τελευταια με την ομαδα) + περσι ----
TGx = S['TGx']
SEAS = collections.defaultdict(lambda: [0.0, 0])                  # (pid, ετος) → [Σποντοι, ματς]  (E + U)
for k, g in PL.items():
    if 'ph' not in g or 'pa' not in g or g.get('hs') is None: continue
    for side in ('ph', 'pa'):
        for p in g[side]:
            if (p[3] or 0) > 0: v = SEAS[(p[0], int(g['season'][1:]))]; v[0] += float(p[4] or 0); v[1] += 1
KW = 8.0
def ppg_blend(sea, team, pid, ts):
    prev = [gd for t, gd in TGx.get((sea, team), []) if t < ts - 3600]
    ap = [gd[pid] for gd in prev if pid in gd][-10:]
    if len(ap) < 3: return None
    cur = float(np.mean([a[2] for a in ap])); n = len(ap); ps = SEAS.get((pid, int(sea[1:]) - 1))
    if not ps or ps[1] < 5: return cur, float(np.mean([a[1] for a in ap]))
    return (n * cur + KW * ps[0] / ps[1]) / (n + KW), float(np.mean([a[1] for a in ap]))
# ---- θεσεις ----
def tok(s): return [w for w in re.split(r'[^a-z]+', unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()) if w]
D3 = pd.read_csv('el_onoff_3s.csv'); POS = collections.defaultdict(dict); BYS = collections.defaultdict(set)
for _, x in D3.iterrows():
    if not isinstance(x.position, str): continue
    k = (tuple(tok(x.surname)), (tok(x.firstname) or [''])[0][:1]); POS[k][int(str(x.season)[:4])] = x.position.capitalize(); BYS[k[0]].add(k)
def pos_name(nm, y):
    sur, fst = (nm.split(',', 1) + [''])[:2]; k = (tuple(tok(sur)), (tok(fst) or [''])[0][:1])
    if k not in POS:
        c = list(BYS.get(k[0], []))
        if len(c) != 1: return None
        k = c[0]
    d = POS[k]
    for yy in (y, y - 1, y + 1, y - 2, y + 2):
        if yy in d: return d[yy]
    return next(iter(d.values()))
# ---- υποψηφιοι: νεοι τακτικοι με π/μ > 9 Ή σεντερ ----
CAND = []; NPOS = collections.Counter()
for r in rows:
    L = []
    for si, (own, team) in enumerate(((r['CH'], r['hc']), (r['CA'], r['ac']))):
        for p in own:
            if p['k'] > 3: continue
            pb = ppg_blend(r['y'], team, p['pid'], r['ts'])
            if pb is None: continue
            ps = pos_name(NAME.get(p['pid'], ''), int(r['y'][1:])); NPOS[ps] += 1
            ex = max(pb[0] - 9.0, 0.0); cen = p['w'] if ps == 'Center' else 0.0
            if ex <= 0 and cen <= 0: continue
            L.append((si, team, p, np.array([ex, ex if ps == 'Guard' else 0.0, cen])))
    CAND.append(L)
P(f'el_scorer_pos_known_test · Ευρωλιγκα 2021-25 · ματς {N} · νεοι τακτικοι: θεσεις {dict(NPOS)} · υποψηφιοι (π/μ>9 ή σεντερ) {sum(len(c) for c in CAND)} · {time.time() - T00:.0f} δευτ.')
def tau_of(r, h): return r['op'][0] if h is None else r['ts'] - h * 3600
def weights(r, L, tau, gtd=True):
    st = {}
    for si, team, p, f in L:
        if team not in st: st[team] = news_state(r['y'], team, r['ts'], tau)[1]
    res = []
    for si, team, p, f in L:
        pg_ = st[team].get(p['pid']); ps = pg_[0] if pg_ else (None if p['pprev'] else 'ii')
        res.append(1.0 if ps == 'OUT' else ((PPAGE[(r['y'], ps, rolek(p))] if gtd else 0.0) if ps in PSRC else 0.0))
    return res
def feat_mat(Wl):                                             # στηλες: [επιθεση ex, γκαρντ ex, σεντερ αντιπαλου] για ΤΟΥΣ ΠΟΝΤΟΥΣ της ομαδας-γραμμης
    XH, XA = np.zeros((N, 3)), np.zeros((N, 3))
    for j, (L, W_) in enumerate(zip(CAND, Wl)):
        for (si, team, p, f), w in zip(L, W_):
            own, opp = (XH, XA) if si == 0 else (XA, XH)
            own[j, 0] += w * f[0]; own[j, 1] += w * f[1]; opp[j, 2] += w * f[2]
    return XH, XA
BOX = [[0.0 if p['played'] else 1.0 for si, team, p, f in L] for L in CAND]
XBH, XBA = feat_mat(BOX)
TAUS = [('ανοιγμα', None), ('−12ω', 12), ('−6ω', 6), ('−3ω', 3), ('−1ω', 1), ('τζαμπολ', 0)]
def states(r, L, tau):
    st = {}
    for si, team, p, f in L:
        if team not in st: st[team] = news_state(r['y'], team, r['ts'], tau)[1]
    return [(st[team].get(p['pid']) or [None if p['pprev'] else 'ii'])[0] for si, team, p, f in L]
STT = {lab: [states(r, L, tau_of(r, h)) if L else [] for r, L in zip(rows, CAND)] for lab, h in TAUS}
RP = pd.DataFrame([(lab, r['y'], s_, rolek(p), 0 if p['played'] else 1) for lab, _ in TAUS for r, L, SS in zip(rows, CAND, STT[lab])
                   for (si, team, p, f), s_ in zip(L, SS) if s_ in PSRC or s_ == 'OUT'], columns=['lab', 'sea', 'src', 'role', 'miss'])
PT = {}
for lab, _ in TAUS:
    for s in SE + ['ολα']:
        tr = RP[(RP.lab == lab) & (RP.sea != s)]
        for src_ in PSRC:
            t2 = tr[tr.src == src_]; base = float(t2.miss.mean()) if len(t2) else 0.5
            for rk in ('βασικος', 'ρολιστας', 'αλλο'):
                x = t2[t2.role == rk]; PT[(lab, s, src_, rk)] = float(x.miss.mean()) if len(x) >= 20 else base
P(chr(10) + 'πιθανοτητα να ΛΕΙΨΕΙ ανα στιγμη (ολες οι σεζον· πλήθος) — βασικος / ρολιστας:')
for src_, nm_ in (('i', 'i ειδηση αμφιβολος'), ('ii', 'ii δεν επαιξε προηγ., χωρις νεα'), ('iii', 'iii ειδηση τραυματισμου'), ('OUT', 'OUT (ελεγχος)')):
    P(f'  {nm_:32s} ' + ' · '.join(f"{lab} {RP[(RP.lab == lab) & (RP.src == src_)].miss.mean():.2f} ({int(((RP.lab == lab) & (RP.src == src_)).sum())})" for lab, _ in TAUS))
WT = {lab: [[1.0 if s_ == 'OUT' else (PT[(lab, r['y'], s_, rolek(p))] if s_ in PSRC else 0.0) for (si, team, p, f), s_ in zip(L, SS)]
            for r, L, SS in zip(rows, CAND, STT[lab])] for lab, _ in TAUS}
P(f'σελιδες σε 6 στιγμες · {time.time() - T00:.0f} δευτ.')
VER = {'V1 [a, b]': [0, 2], 'V2 [a, a_γκ, b]': [0, 1, 2]}
XKH, XKA = feat_mat(WT['τζαμπολ'])
CL = {v: {s: fit(XKH[:, c], XKA[:, c], ys != s) for s in SE} for v, c in VER.items()}
CW = {v: {s: fit(XKH[:, c], XKA[:, c], np.isin(ys, SE[:i])) for i, s in enumerate(SE[1:], 1)} for v, c in VER.items()}
CA = {v: fit(XKH[:, c], XKA[:, c], ys != '') for v, c in VER.items()}
for v, c in VER.items():
    nm = ['a', 'a_γκ', 'b'] if len(c) == 3 else ['a', 'b']
    P(f'  {v}: ολα τα ματς ' + ' · '.join(f'{n} {x:+.3f}' for n, x in zip(nm, CA[v])) + ' │ LOSO ανα σεζον-τεστ: ' + ' '.join(f'{s[-2:]}:(' + ', '.join(f'{x:+.2f}' for x in CL[v][s]) + ')' for s in SE))
def corr(XH, XA, cols, C):
    h = np.full(N, np.nan)
    for s, b in C.items():
        m = ys == s; h[m] = XH[m][:, cols] @ b + XA[m][:, cols] @ b
    return h
Y = TOT - T0
def mkt(r, h):
    d = REC[23].get(r['pos'])
    if d is None: return np.nan, np.nan
    x = d['open'] if h is None else (d.get(h) or d['open']); return x[1], d['open'][1]
MK = {lab: np.array([mkt(r, h) for r in rows]) for lab, h in TAUS}
RES = {v: {} for v in VER}; C0 = {}
P('\n## ΑΝΑ ΣΤΙΓΜΗ (αμφιβολοι × p) · ματς με βαρος > 0 · πραγμ − μοντελο · διορθωση · μεροληψια · κλιση (ανα σεζον) · αγορα (γραμμη τ πανω στη διορθωση)')
for lab, h in TAUS:
    XH, XA = feat_mat(WT[lab]); m = np.array([any(w > 0 for w in W_) for W_ in WT[lab]])
    P(f'\n  {lab:8s}: ματς {int(m.sum()):4d} · πραγμ − μοντελο {np.mean(Y[m]):+5.2f}')
    for v, cols in VER.items():
        c = corr(XH, XA, cols, CL[v])
        if lab == 'ανοιγμα': C0[v] = c
        A_ = np.c_[np.ones(N), c]; b = np.linalg.lstsq(A_, Y, rcond=None)[0][1]
        bs = [np.linalg.lstsq(A_[ys == s], Y[ys == s], rcond=None)[0][1] for s in SE]; bias = float(np.mean(Y[m] - c[m]))
        lv = MK[lab][:, 0] - T0; ok = ~np.isnan(lv); kl = np.linalg.lstsq(np.c_[np.ones(ok.sum()), c[ok]], lv[ok], rcond=None)[0][1]
        RES[v][lab] = dict(b=b, pos=sum(x > 0 for x in bs), bias=bias)
        P(f'     {v:16s} διορθ. {np.mean(c[m]):+5.2f} · μεροληψια {bias:+5.2f} · κλιση {b:4.2f} (' + ' '.join(f'{x:+.1f}' for x in bs) + f', θετ {sum(x > 0 for x in bs)}/5) · αγορα {kl:4.2f}')
save()
# ---- αθροισιμοτητα (box) ----
P('\n## ΑΘΡΟΙΣΙΜΟΤΗΤΑ (box, LOSO V1): ομαδα-ματς με 1 vs 2 vs 3+ νεους αποντες με π/μ > 9 → πραγματικο (ποντοι ομαδας − μοντελο) / προβλεψη επιθεσης')
cnt = np.zeros((N, 2))
for j, (L, W_) in enumerate(zip(CAND, BOX)):
    for (si, team, p, f), w in zip(L, W_):
        if w > 0 and f[0] > 0: cnt[j, si] += 1
predH = corr(XBH, XBA, [0, 2], CL['V1 [a, b]']); bA = np.array([CL['V1 [a, b]'][s][0] for s in ys])
ownH, ownA = bA * XBH[:, 0], bA * XBA[:, 0]
for lab, sel in (('1', lambda c: c == 1), ('2', lambda c: c == 2), ('3+', lambda c: c >= 3)):
    mh, ma = sel(cnt[:, 0]), sel(cnt[:, 1]); yv = np.r_[YH[mh], YA[ma]]; pv = np.r_[ownH[mh], ownA[ma]]
    if len(yv): P(f'  {lab:3s} αποντες: ομαδα-ματς {len(yv):4d} · πραγματικο {np.mean(yv):+5.2f} · προβλεψη επιθεσης {np.mean(pv):+5.2f} · λογος {np.mean(yv) / np.mean(pv) if np.mean(pv) else float("nan"):.2f}')
# ---- picks ανοιγματος ----
P('\n## PICKS ΑΝΟΙΓΜΑΤΟΣ ≥8% (Crown, αμφιβολοι × p) — LOSO / walk-forward 2022-25 / placebo')
F4 = [G['featB'](r, 'N', 'G0') for r in rows]; X4H = np.array([f[0] for f in F4]); X4A = np.array([f[1] for f in F4])
def line(lab, hl, hw):
    sd, u = picks(hl); sw, uw = picks(hw); ps = pd.Series(u[sd != 0]).groupby(ys[sd != 0]).sum()
    P(f'  {lab:28s} picks {int((sd != 0).sum()):4d} · LOSO {u.sum():+6.1f}μ ({int((ps > 0).sum())}/5: ' + ' '.join(f'{s[-2:]}:{ps.get(s, 0):+.1f}' for s in SE) + f') · walk-forward {uw[WF4].sum():+6.1f}μ')
    return u.sum(), uw[WF4].sum()
line('χωρις διορθωση', np.zeros(N), np.zeros(N)); LV = line('live: OUT + on/off', HELD_B[('N', 'G0')], wf(X4H, X4A))
XgH, XgA = feat_mat(WT['ανοιγμα']); PK = {}
for v, cols in VER.items():
    hl = corr(XgH, XgA, cols, CL[v]); hw = np.nan_to_num(corr(XgH, XgA, cols, CW[v])); u_l, u_w = line(v, hl, hw); vals = []
    for _ in range(200):
        pa, pb = XgH.copy(), XgA.copy()
        for s in SE:
            idx = np.where(ys == s)[0]; pm = rng.permutation(idx); pa[idx] = XgH[pm]; pb[idx] = XgA[pm]
        vals.append(picks(corr(pa, pb, cols, CL[v]))[1].sum())
    PK[v] = dict(u=u_l, wf=u_w, plc=float(np.mean(np.array(vals) >= u_l)))
    P(f'  {"":28s} placebo μεσος {np.mean(vals):+.1f} (95% {np.percentile(vals, 95):+.1f}) · P {100 * PK[v]["plc"]:.1f}%')
P('\n## ΚΡΙΣΗ (προ-δηλωμενη)')
PASS = {}
for v in VER:
    t = {'κλιση 0.7-1.3 παντου': all(0.7 <= RES[v][l]['b'] <= 1.3 for l, _ in TAUS), 'θετικη ≥4/5 παντου': all(RES[v][l]['pos'] >= 4 for l, _ in TAUS),
         '|μεροληψια| ≤ 1': all(abs(RES[v][l]['bias']) <= 1 for l, _ in TAUS), 'WF ≥ live': PK[v]['wf'] >= LV[1], 'placebo < 10%': PK[v]['plc'] < .10}
    PASS[v] = all(t.values())
    P(f'  {v:16s} ' + ' · '.join(f"{k} {'✓' if x else '✗'}" for k, x in t.items()) + f" → {'ΠΕΡΝΑ' if PASS[v] else 'δεν περνα'}")
P(f"  V2 (ξεχωριστο a γκαρντ) κρατιεται: {'ΝΑΙ' if PASS['V2 [a, a_γκ, b]'] and PK['V2 [a, a_γκ, b]']['wf'] > PK['V1 [a, b]']['wf'] else 'ΟΧΙ'}")
# ---- Ολυμπιακος 28/10 ----
P('\n## ΟΛΥΜΠΙΑΚΟΣ (Μπεσικτας − Ολυμπιακος 28/10, OUT: Μοντερο, Ντορσει, Φουρνιε, Μιλουτινοφ) — συντελεστες ολων των ματς')
import urllib.request
B = json.load(open('el_box.json', encoding='utf-8')); have = {int(f.split('_')[-1][:-5]) for f in glob.glob('el_pbp/E2026_*.json')}
games = sorted([v for k, v in B.items() if k.startswith('E2026') and 'OLY' in (v['hcode'], v['acode']) and v.get('ph')], key=lambda v: v['utc'])
st = collections.defaultdict(list)
for v in games:
    c = v['code']
    b = json.load(open(f'el_pbp/E2026_{c}.json', encoding='utf-8'))['box'] if c in have else json.loads(urllib.request.urlopen(urllib.request.Request(
        f'https://live.euroleague.net/api/Boxscore?gamecode={c}&seasoncode=E2026', headers={'User-Agent': 'Mozilla/5.0'}), timeout=40).read())
    t = b['Stats'][0 if v['hcode'] == 'OLY' else 1]
    for p in t['PlayersStats']:
        try: m_, s_ = str(p.get('Minutes') or '0:0').split(':'); m = int(m_) + int(s_) / 60
        except Exception: m = 0
        if m > 0: st[str(p.get('Player_ID', '')).strip()].append((m, p['Points'], p['Player']))
tot = {v: 0.0 for v in VER}
for nm_ in ('MONTERO, JEAN', 'DORSEY, TYLER', 'FOURNIER, EVAN', 'MILUTINOV, NIKOLA'):
    pid = next(k for k, L in st.items() if L[0][2] == nm_); L = st[pid][-10:]; n = len(L); cur = np.mean([x[1] for x in L]); mpg = np.mean([x[0] for x in L])
    ps_ = SEAS.get((pid, 2025)); pb = (n * cur + KW * ps_[0] / ps_[1]) / (n + KW) if ps_ and ps_[1] >= 5 else cur
    pos = pos_name(nm_, 2026); ex = max(pb - 9, 0); cen = mpg / 40 if pos == 'Center' else 0.0
    parts = []
    for v, cols in VER.items():
        f = np.array([ex, ex if pos == 'Guard' else 0.0, cen])[cols]; bb = CA[v]; e = float(f @ bb); tot[v] += e; parts.append(f'{v[:2]} {e:+.2f}')
    P(f'  {nm_:20s} {pos or "?":8s} φετος {cur:4.1f} π/μ ({n} ματς, {mpg:4.1f}′) · περσι {ps_[0] / ps_[1] if ps_ and ps_[1] else float("nan"):4.1f} → μιξη {pb:4.1f} · ' + ' · '.join(parts))
P('  ΣΥΝΟΛΟ ματς: ' + ' · '.join(f'{v} {x:+.2f}' for v, x in tot.items()) + ' (μοντελο χωρις απουσιες 175.7)')
P(f'\nχρονος {time.time() - T00:.0f} δευτ.'); save()
