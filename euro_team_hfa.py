"""
euro_team_hfa.py — 9/10/2026 (Στελιος: «μηπως υποτιμαμε την εδρα ομαδων εκτος μεγαλων πρωταθληματων που στηριζονται στην εδρα τους —
Ολυμπιακος, Ντιναμο Ζαγκρεμπ, Ερυθρος Αστερας;»). Ευρωπαικα 2223-2526, σημερινη ευρωπαικη αλυσιδα (κοινη εδρα 1.144 για ολους).
1. Ανα ΧΩΡΑ γηπεδουχου (εκτος top-5): γηπεδουχος πραγματικο − μοντελο (διαφορα γκολ) ΕΝΤΟΣ, και οι ιδιες ομαδες ΕΚΤΟΣ · − αγορα.
2. Ανα ΟΜΑΔΑ (≥6 ευρωπαικα εντος): ιδια μετρα.
3. ΕΠΙΜΟΝΗ: η «εξτρα εδρα» μιας ομαδας σε μια σεζον προβλεπει την επομενη; (αλλιως = τυχη)
4. ΕΓΧΩΡΙΑ ΕΔΡΑ (ex-ante): (εντος − εκτος διαφορα γκολ)/2 της ομαδας στα 2 προηγουμενα εγχωρια πρωταθληματα, μειον τον μεσο της λιγκας
   → προβλεπει την ευρωπαικη εδρα;
5. ΔΙΟΡΘΩΣΗ (LOSO, μονο ομαδες εκτος top-5): (α) ανα χωρα (β) ανα ομαδα απο ευρωπαικα αλλων σεζον (γ) απο εγχωρια εδρα.
ΠΡΟ-ΔΗΛΩΣΗ 5: περνα αν πιθανοφανεια γκολ εκτος δειγματος καλυτερη σε ≥3/4 σεζον ΚΑΙ picks (μεσος Crown/SBOBET, κλεισιμο, ολες οι
διοργανωσεις μαζι) καλυτερα απο σημερα σε ≥3/4 σεζον ΚΑΙ καμια διοργανωση δεν χειροτερευει >3 μοναδες.
"""
import sys, io, os, json, math, contextlib, datetime
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('uel_home_why.py', encoding='utf-8').read(); src = src[:src.index("print('1. ΕΔΡΑ")].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'thfa'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
MIDS, COMP, SEA, GD, GH, GA, LH_N, LA_N, SM, LGH, LGA, TEAMS, XH, XA = (g[k] for k in (
    'MIDS', 'COMP', 'SEA', 'GD', 'GH', 'GA', 'LH_N', 'LA_N', 'SM', 'LGH', 'LGA', 'TEAMS', 'XH', 'XA'))
B = g['g']; make_picks, fm, P_LIVE = B['make_picks'], B['fm'], B['P0']
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
N = len(MIDS); SMOD = LH_N - LA_N
NAMES = {}
for k_, lst in json.load(open('europe_fixtures.json', encoding='utf-8')).items():
    for m in lst: NAMES[m['hid']] = m['hname']; NAMES[m['aid']] = m['aname']
HID = np.array([TEAMS[m][0] if m in TEAMS else -1 for m in MIDS]); AID = np.array([TEAMS[m][1] if m in TEAMS else -1 for m in MIDS])
R = GD - SMOD                       # σκοπια γηπεδουχου: πραγματικο − μοντελο
RK = GD - SM                        # − αγορα
RX = (XH - XA) - SMOD
def stat(v):
    v = v[np.isfinite(v)]; return (v.mean(), v.std() / np.sqrt(len(v)) if len(v) > 1 else np.nan, len(v))
# 1. ανα χωρα
print('1. ΑΝΑ ΧΩΡΑ (εκτος top-5) — ΕΝΤΟΣ: πραγμ − μοντελο · xG − μοντελο · πραγμ − αγορα ‖ ΟΙ ΙΔΙΕΣ ΕΚΤΟΣ (σκοπια ομαδας): πραγμ − μοντελο')
rows = []
for lg in sorted(set(LGH) | set(LGA)):
    h = LGH == lg; a = LGA == lg
    if h.sum() < 12 or lg in TOP5: continue
    m1, s1, n1 = stat(R[h]); mx, _, _ = stat(RX[h]); mk, sk, _ = stat(RK[h]); m2, s2, n2 = stat(-R[a])
    rows.append((lg, n1, m1, s1, mx, mk, sk, n2, m2, s2))
for r in sorted(rows, key=lambda z: -z[2]):
    print(f'   {r[0]:24s} εντος n{r[1]:3d} {r[2]:+.2f}±{r[3]:.2f} · xG {r[4]:+.2f} · −αγορα {r[5]:+.2f}±{r[6]:.2f} ‖ εκτος n{r[7]:3d} {r[8]:+.2f}±{r[9]:.2f}')
T5h = np.isin(LGH, list(TOP5)); m1, s1, n1 = stat(R[~T5h]); mk, sk, _ = stat(RK[~T5h]); m2, s2, _ = stat(R[T5h]); mk2, _, _ = stat(RK[T5h])
print(f'   ΣΥΝΟΛΟ γηπεδουχοι εκτος top-5 n{n1}: {m1:+.3f}±{s1:.3f} · −αγορα {mk:+.3f}±{sk:.3f} ‖ γηπεδουχοι top-5: {m2:+.3f} · −αγορα {mk2:+.3f}')
# 2. ανα ομαδα
print('\n2. ΑΝΑ ΟΜΑΔΑ (εκτος top-5, ≥6 ευρωπαικα εντος) — εντος: πραγμ − μοντελο · −αγορα ‖ εκτος: πραγμ − μοντελο (σκοπια ομαδας)')
tr = []
for t in set(HID[~T5h]):
    h = HID == t; a = AID == t
    if h.sum() < 6: continue
    tr.append((NAMES.get(t, t), LGH[h][0], h.sum(), R[h].mean(), np.nanmean(RK[h]), a.sum(), (-R[a]).mean() if a.sum() else np.nan))
for r in sorted(tr, key=lambda z: -z[3]):
    print(f'   {str(r[0]):24s} {r[1]:20s} εντος n{r[2]:2d} {r[3]:+.2f} · −αγορα {r[4]:+.2f} ‖ εκτος n{r[5]:2d} {r[6]:+.2f}')
# 3. επιμονη
print('\n3. ΕΠΙΜΟΝΗ — εξτρα εδρα ομαδας (εντος πραγμ − μοντελο) σε σεζον t vs ΑΛΛΕΣ σεζον της ιδιας ομαδας (≥3 εντος ανα σεζον)')
TS = pd.DataFrame(dict(t=HID, sea=SEA, r=R, rk=RK, out=~T5h)).groupby(['t', 'sea']).agg(r=('r', 'mean'), rk=('rk', 'mean'), n=('r', 'size'), out=('out', 'first')).reset_index()
TS = TS[TS.n >= 3]
pairs = []
for t, d in TS.groupby('t'):
    for i in range(len(d)):
        oth = d.drop(d.index[i])
        if len(oth): pairs.append((d.r.iloc[i], oth.r.mean(), d.rk.iloc[i], oth.rk.mean(), d.out.iloc[i]))
P = np.array(pairs, float)
for lab, msk in (('ολες', np.ones(len(P), bool)), ('εκτος top-5', P[:, 4] == 1)):
    q = P[msk]; print(f'   {lab}: corr(σεζον, αλλες σεζον) μοντελο {np.corrcoef(q[:, 0], q[:, 1])[0, 1]:+.2f} · αγορα {np.corrcoef(q[:, 2], q[:, 3])[0, 1]:+.2f} (ζευγη {len(q)})')
# 4. εγχωρια εδρα (ex-ante)
CAL = {'2223': '2022', '2324': '2023', '2425': '2024', '2526': '2025'}
def dom_file(lg, sea):
    for s in (sea, CAL.get(sea)):
        if s and os.path.exists(f'data_{lg}_{s}.json'): return f'data_{lg}_{s}.json'
    return None
def prevs(sea):
    a = f'{int(sea[:2]) - 1:02d}{int(sea[2:]) - 1:02d}'; b = f'{int(sea[:2]) - 2:02d}{int(sea[2:]) - 2:02d}'; return [a, b]
DHFA = {}; _cache = {}
def team_hfa(lg, sea):
    key = (lg, sea)
    if key in _cache: return _cache[key]
    hs, as_ = {}, {}
    for s in prevs(sea):
        f = dom_file(lg, s)
        if not f: continue
        for m in json.load(open(f, encoding='utf-8')).values():
            if m.get('hs') is None: continue
            d_ = m['hs'] - m['as']; hs.setdefault(m['home']['id'], []).append(d_); as_.setdefault(m['away']['id'], []).append(-d_)
    out = {}
    if hs:
        lgm = np.mean([np.mean(v) for v in hs.values()]) - np.mean([np.mean(v) for v in as_.values()])
        for t in hs:
            if t in as_ and len(hs[t]) >= 10 and len(as_[t]) >= 10:
                n = min(len(hs[t]), len(as_[t])); raw = (np.mean(hs[t]) - np.mean(as_[t]) - lgm) / 2
                out[t] = raw * n / (n + 15)          # συρρικνωση
    _cache[key] = out; return out
DH = np.array([team_hfa(LGH[i], SEA[i]).get(HID[i], np.nan) if LGH[i] not in TOP5 else np.nan for i in range(N)])
ok = np.isfinite(DH)
b = np.polyfit(DH[ok], R[ok], 1); bk = np.polyfit(DH[ok][np.isfinite(RK[ok])], RK[ok][np.isfinite(RK[ok])], 1)
print(f'\n4. ΕΓΧΩΡΙΑ ΕΞΤΡΑ ΕΔΡΑ (2 προηγουμενα πρωταθληματα, συρρικνωμενη) → ευρωπαικη εδρα (εκτος top-5, n{ok.sum()}):')
print(f'   corr με πραγμ−μοντελο {np.corrcoef(DH[ok], R[ok])[0, 1]:+.3f} (κλιση {b[0]:+.2f}) · με πραγμ−αγορα {np.corrcoef(DH[ok][np.isfinite(RK[ok])], RK[ok][np.isfinite(RK[ok])])[0, 1]:+.3f} · sd εγχωριας {np.nanstd(DH):.3f}')
q = np.nanpercentile(DH[ok], [25, 75])
for lab, msk in (('χαμηλη εγχωρια εδρα (κατω 25%)', ok & (DH <= q[0])), ('μεσαια', ok & (DH > q[0]) & (DH < q[1])), ('ΨΗΛΗ εγχωρια εδρα (πανω 25%)', ok & (DH >= q[1]))):
    m1, s1, n1 = stat(R[msk]); mk, _, _ = stat(RK[msk]); print(f'   {lab:32s} n{n1:3d} · πραγμ−μοντελο {m1:+.2f}±{s1:.2f} · −αγορα {mk:+.2f}')
# 5. διορθωσεις LOSO
SEAS = ('2223', '2324', '2425', '2526')
OUT = ~T5h
def apply(delta):
    d = np.nan_to_num(delta); return np.maximum(LH_N + d / 2, .05), np.maximum(LA_N - d / 2, .05)
def ll(LH, LA, m): return float(np.sum(GH[m] * np.log(LH[m]) - LH[m] + GA[m] * np.log(LA[m]) - LA[m]))
def variants():
    yield 'α ανα χωρα', lambda te: np.array([(lambda v: v.sum() / (len(v) + 20))(R[(LGH == LGH[i]) & (SEA != te) & OUT]) if OUT[i] else 0 for i in range(N)])
    yield 'β ανα ομαδα', lambda te: np.array([(lambda v: v.sum() / (len(v) + 10))(R[(HID == HID[i]) & (SEA != te)]) if OUT[i] else 0 for i in range(N)])
    def gam(te):
        trm = ok & (SEA != te); k_ = np.polyfit(DH[trm], R[trm], 1)[0]
        return np.where(ok, k_ * np.nan_to_num(DH), 0.0)
    yield 'γ απο εγχωρια εδρα', gam
print('\n5. ΔΙΟΡΘΩΣΕΙΣ (LOSO) — Δπιθανοφανεια γκολ ανα σεζον · picks ολων των διοργανωσεων')
for name, fn in variants():
    dll = {}; LHa, LAa = LH_N.copy(), LA_N.copy()
    for te in SEAS:
        tm = SEA == te; d = fn(te); lh, la = apply(d)
        dll[te] = ll(lh, la, tm) - ll(LH_N, LA_N, tm); LHa[tm] = lh[tm]; LAa[tm] = la[tm]
    Pn = make_picks(LHa, LAa)
    ps = Pn.groupby('sea').pnl.mean(); p0 = P_LIVE.groupby('sea').pnl.mean()
    worst = min(Pn[Pn.comp == c].pnl.sum() / 2 - P_LIVE[P_LIVE.comp == c].pnl.sum() / 2 for c in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'))
    c1 = sum(v > 0 for v in dll.values()) >= 3; c2 = int((ps > p0.reindex(ps.index)).sum()) >= 3; c3 = worst > -3
    print(f'   {name:20s} Δπιθ. ' + ' '.join(f'{s}:{v:+.1f}' for s, v in dll.items()) + f' · picks ολα {fm(Pn)} vs σημερα {fm(P_LIVE)[:24]}')
    print(f'   {"":20s} ' + ' · '.join(f'{c[:6]} {fm(Pn[Pn.comp == c])[:24]}' for c in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'))
          + f' → (1){"✓" if c1 else "✗"} (2){"✓" if c2 else "✗"} (3){"✓" if c3 else "✗"} {"ΠΕΡΝΑ" if c1 and c2 and c3 else "ΔΕΝ ΠΕΡΝΑ"}')
