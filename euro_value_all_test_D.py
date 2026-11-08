"""
euro_value_all_test_D.py — 10/10/2026 (ΠΑΡΑΛΛΑΓΗ μετα το αποτελεσμα: το υπολοιπο αξιας και ως προς τη ΔΙΑΦΟΡΑ ΛΙΓΚΑΣ — το αρχικο εδειξε νεα μεροληψια CORE7 ±0.16 = διπλομετρημα λιγκας· POST-HOC). euro_value_all_test.py — 10/10/2026 (επεκταση σε ΟΛΕΣ τις ευρωπαικες ομαδες: euro_squads.json + euro_player_values.json). ΒΑΣΗ: euro_value_elo_test.py — 10/10/2026 (Στελιος: «τρεξε την αξια ροστερ, οπως και το team Elo»). Απολυτη ποιοτητα ομαδας στο ευρωπαικο μοντελο.
Σημερινη αλυσιδα (2223-2526). Δυο ανεξαρτητα στρωματα, το καθενα με την πληροφορια που ΔΕΝ εχει ηδη το μοντελο (υπολοιπο):
  ΑΞΙΑ: V = 80ο εκατοστημοριο αξιας βασικης ενδεκαδας (FotMob/SciSports, core7_squads + core7_player_values) στα εγχωρια ματς 365 ημερων ΠΡΙΝ
        → lv = ln(V_γηπ/V_φιλ)· ΜΟΝΟ ματς με 2 ομαδες CORE7 (εκει υπαρχουν δεδομενα). z = lv − (a + b·ln(λγ/λφ)) (a,b απο train).
  ELO:  ClubElo πριν το ματς (clubelo_europe.csv) → ΔElo/100· z ομοιως. Ολα τα ματς με Elo.
  Διορθωση: λγ × e^(c·z/2), λφ × e^(−c·z/2)· c απο LOSO (πιθανοφανεια γκολ στις 3 αλλες σεζον), grid 0..0.6.
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (ανα στρωμα): (1) RPS των επηρεαζομενων ματς καλυτερο σε ≥3/4 σεζον ΚΑΙ pooled · (2) ROI (σημερινη τιμολογηση,
μεσος Crown/Pinnacle) ΟΛΑ & UCL ≥ σημερα − 1SE · αναφερεται και πριν/μετα για PSG, Real, City, Bayern (πραγματικο − μοντελο).
"""
import sys, io, json, math, bisect, contextlib, glob, os
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
g = {'__name__': 've'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('euro_oppadj_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
G = g['g']
MIDS, SEA, COMP, GD, GH, GA, HID, AID, DATES, N = (G[k] for k in ('MIDS', 'SEA', 'COMP', 'GD', 'GH', 'GA', 'HID', 'AID', 'DATES', 'N'))
SEA = np.asarray(SEA); BASE = g['BASE']; rps_arr, dse, gen, roi, FLT, CROWN, PIN = (g[k] for k in ('rps_arr', 'dse', 'gen', 'roi', 'FLT', 'CROWN', 'PIN'))
LGH, LGA = G['LGH'], G['LGA']; eh, ea = G['eh'], G['ea']
CORE7 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie'}
SEAS = ['2223', '2324', '2425', '2526']
# ---------------- αξια ενδεκαδας ανα εγχωριο ματς ----------------
sys.path.insert(0, '.')
from euro_engine import kodt
DATE = {}
for lg in CORE7:
    for f in glob.glob(f'data_{lg}_*.json'):
        for mid, m in json.load(open(f, encoding='utf-8')).items():
            d = kodt(m['date'])
            if d is not None: DATE[str(mid)] = d
SQ = json.load(open('core7_squads.json', encoding='utf-8')); PV = json.load(open('core7_player_values.json', encoding='utf-8'))
SQ.update({k: v for k, v in json.load(open('euro_squads.json', encoding='utf-8')).items() if v})
PV.update(json.load(open('euro_player_values.json', encoding='utf-8')))
# ημερομηνιες για ΟΛΑ τα ματς (εγχωρια ολων των λιγκων + ευρωπαικα)
for f in glob.glob('data_*.json'):
    if any(x in f for x in ('Nations', 'Brazil', 'MLS')): continue
    try:
        for mid, m in json.load(open(f, encoding='utf-8')).items():
            if str(mid) in DATE: continue
            d = kodt(m.get('date'))
            if d is not None: DATE[str(mid)] = d
    except Exception:
        pass
H = {}
for pid, v in PV.items():
    h = sorted((d, float(x)) for d, x in (v.get('hist') or []) if d and x)
    if h: H[int(pid)] = ([d for d, _ in h], [x for _, x in h])
    elif v.get('mv_now') and str(v['mv_now']) != 'None': H[int(pid)] = (['2026-09-20'], [float(v['mv_now'])])
def value_at(pid, ds):
    h = H.get(pid)
    if not h: return None
    i = bisect.bisect_right(h[0], ds) - 1
    return h[1][i] if i >= 0 else h[1][0]
TEAMXI = {}
for mid, s in SQ.items():
    d = DATE.get(str(mid))
    if d is None: continue
    ds = d.strftime('%Y-%m-%d')
    for side in ('h', 'a'):
        x = s.get(side) or {}; st = x.get('st') or []
        if len(st) < 8 or not x.get('t'): continue
        got = [v for v in (value_at(int(p), ds) for p in st) if v]
        if len(got) >= len(st) - 3:
            TEAMXI.setdefault(int(x['t']), []).append((d, sum(got) * len(st) / len(got)))
for t in TEAMXI: TEAMXI[t].sort()
def vfull(tid, d):
    xs = [v for dd, v in TEAMXI.get(int(tid), []) if d - pd.Timedelta(days=365) <= dd < d]
    return float(np.percentile(xs, 80)) if len(xs) >= 3 else np.nan
LV = np.full(N, np.nan)
for i in range(N):
    if True:
        vh, va = vfull(HID[i], DATES[i]), vfull(AID[i], DATES[i])
        if np.isfinite(vh) and np.isfinite(va) and vh > 0 and va > 0: LV[i] = math.log(vh / va)
LE = np.where(np.isfinite(eh) & np.isfinite(ea), (eh - ea) / 100.0, np.nan)
print(f'ματς με αξια (ΟΛΕΣ οι λιγκες): {int(np.isfinite(LV).sum())} · με Elo: {int(np.isfinite(LE).sum())} / {N}')
LR = np.log(BASE[0] / BASE[1]); R0 = rps_arr(*BASE)
DD = np.asarray(G['D_ARR'])
def corr_lam(x, c, ab):
    z = np.where(np.isfinite(x), x - (ab[0] + ab[1] * LR + ab[2] * DD), 0.0)
    return BASE[0] * np.exp(c * z / 2), BASE[1] * np.exp(-c * z / 2)
def ll(lh, la, m): return float(np.sum(GH[m] * np.log(lh[m]) - lh[m] + GA[m] * np.log(la[m]) - la[m]))
CG = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
TEAMS = {'Paris Saint-Germain', 'Real Madrid', 'Manchester City', 'Bayern München', 'Liverpool', 'Barcelona', 'Inter', 'Arsenal'}
SN = G['S']
def team_resid(lh, la):
    out = {}
    for t in TEAMS:
        r = []
        for i in range(N):
            if SN.hname.values[i] == t: r.append(GD[i] - (lh[i] - la[i]))
            elif SN.aname.values[i] == t: r.append(-(GD[i] - (lh[i] - la[i])))
        out[t] = (np.mean(r) if r else np.nan, len(r))
    return out
def roi_tab(L):
    GG = [gen(L, OD) for OD in (CROWN, PIN)]; out = {}
    for lab, flt in FLT:
        v = [roi([r for r in x.values() if flt(r)]) for x in GG]
        out[lab] = ((v[0][0] + v[1][0]) / 2, np.nanmean([v[0][1], v[1][1]]), np.nanmean([v[0][2], v[1][2]]))
    return out
RB = roi_tab(BASE); TB = team_resid(*BASE)
print('ROI σημερα: ' + ' · '.join(f'{l} {v[0]:.0f} {100 * v[1]:+.1f}%' for l, v in RB.items()))
for name, X in (('ΑΞΙΑ ΡΟΣΤΕΡ (υπολοιπο ως προς μοντελο ΚΑΙ λιγκα)', LV), ('ELO (υπολοιπο ως προς μοντελο ΚΑΙ λιγκα)', LE)):
    aff = np.isfinite(X)
    print(f'\n===== {name} (επηρεαζομενα {int(aff.sum())}) =====')
    LH = BASE[0].copy(); LA = BASE[1].copy(); ch = {}
    for te in SEAS:
        tr = aff & (SEA != te)
        A_ = np.c_[np.ones(tr.sum()), LR[tr], DD[tr]]; ab = tuple(np.linalg.lstsq(A_, X[tr], rcond=None)[0])
        c = max(CG, key=lambda c: ll(*corr_lam(X, c, ab), tr)); ch[te] = (c, ab)
        m = SEA == te; L = corr_lam(X, c, ab); LH[m] = L[0][m]; LA[m] = L[1][m]
    R1 = rps_arr(LH, LA)
    cs = [dse(R1[aff & (SEA == s)] - R0[aff & (SEA == s)])[0] for s in SEAS]; d_, se_ = dse(R1[aff] - R0[aff])
    print('   c ανα σεζον: ' + ' '.join(f'{s}:{v[0]}' for s, v in ch.items()) + f' · κλιση {name} πανω στο μοντελο b ≈ {np.mean([v[1][1] for v in ch.values()]):.2f}')
    print(f'   ΔRPS επηρεαζομενων ×10⁻³: ' + ' '.join(f'{s}:{1000 * c:+.2f}' for s, c in zip(SEAS, cs)) + f' · pooled {1000 * d_:+.2f}±{1000 * se_:.2f}')
    LLd = [ll(LH, LA, aff & (SEA == s)) - ll(*BASE, aff & (SEA == s)) for s in SEAS]
    print(f'   Δπιθανοφανεια γκολ: ' + ' '.join(f'{s}:{v:+.1f}' for s, v in zip(SEAS, LLd)))
    RT = roi_tab((LH, LA))
    print('   ROI: ' + ' · '.join(f'{l} {v[0]:.0f} {100 * v[1]:+.1f}%' for l, v in RT.items()))
    T1 = team_resid(LH, LA)
    print('   πραγματικο − μοντελο (διαφορα γκολ) σημερα → με στρωμα: ' + ' · '.join(f'{t.split()[0]} {TB[t][0]:+.2f}→{T1[t][0]:+.2f}' for t in sorted(TEAMS)))
    cross = aff & (np.array([a != b for a, b in zip(LGH, LGA)]))
    nonc7 = aff & np.array([(a not in CORE7) or (b not in CORE7) for a, b in zip(LGH, LGA)])
    for lab, mm in (('διαφορετικες λιγκες', cross), ('με ομαδα εκτος CORE7', nonc7), ('CORE7-CORE7', aff & ~nonc7)):
        if mm.sum() > 30:
            dd, ss = dse(R1[mm] - R0[mm]); cc = [dse(R1[mm & (SEA == s)] - R0[mm & (SEA == s)])[0] for s in SEAS]
            print(f'   {lab:22s} n{int(mm.sum()):4d} · ΔRPS ×10⁻³ pooled {1000 * dd:+.2f}±{1000 * ss:.2f} ({sum(c < 0 for c in cc)}/4)')
    def grp_bias(L, m):
        e = GD - (L[0] - L[1]); return float(e[m].mean())
    for lab, mm in (('γηπ CORE7 vs φιλ αλλη', aff & np.isin(LGH, list(CORE7)) & ~np.isin(LGA, list(CORE7))),
                    ('γηπ αλλη vs φιλ CORE7', aff & ~np.isin(LGH, list(CORE7)) & np.isin(LGA, list(CORE7)))):
        if mm.sum() > 30: print(f'   μεροληψια {lab:24s} n{int(mm.sum())}: σημερα {grp_bias(BASE, mm):+.2f} → {grp_bias((LH, LA), mm):+.2f}')
    PB0 = {(bk, m, s): r['pnl'] for bk, OD in (('C', CROWN), ('P', PIN)) for (m, s), r in gen(BASE, OD).items()}
    PB1 = {(bk, m, s): r['pnl'] for bk, OD in (('C', CROWN), ('P', PIN)) for (m, s), r in gen((LH, LA), OD).items()}
    gone = [v for k, v in PB0.items() if k not in PB1]; new = [v for k, v in PB1.items() if k not in PB0]
    print(f'   picks: φευγουν {len(gone) / 2:.0f} ({100 * np.mean(gone) if gone else float("nan"):+.1f}%) · μπαινουν {len(new) / 2:.0f} ({100 * np.mean(new) if new else float("nan"):+.1f}%)')
    k1 = d_ < 0 and sum(c < 0 for c in cs) >= 3; k2 = all(RT[l][1] >= RB[l][1] - RB[l][2] for l in ('ΟΛΑ', 'UCL'))
    print(f'   ΚΡΙΣΗ: (1) RPS {"✓" if k1 else "✗"} ({sum(c < 0 for c in cs)}/4) · (2) ROI {"✓" if k2 else "✗"} → {"ΠΕΡΝΑ" if k1 and k2 else "ΔΕΝ ΠΕΡΝΑ"}')
