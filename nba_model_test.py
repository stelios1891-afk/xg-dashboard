# -*- coding: utf-8 -*-
"""nba_model_test.py — ΤΟ ΙΔΙΟ ΜΟΝΤΕΛΟ ΜΕ ΤΗΝ ΕΥΡΩΛΙΓΚΑ ΣΤΟ NBA (27/9/2026, αιτημα Στελιου).
Δεδομενα: nba_gamelogs.csv (Basketball-Reference, κανονικη περιοδος 2020-21…2025-26) · nowgoal_nba/ (Crown closing χαντικαπ/συνολο).
Μοντελο (οπως Ευρωλιγκα v4/B1, χωρις ειδικους): ratings επιθεσης/αμυνας/ρυθμου (ridge, walk-forward καθε μερα), διορθωση τυχης
  3P%/FT% (50% προς τον περσινο μεσο), αφετηρια = carry × περσινο τελος με βαρος K ματς, φθορα HL μερες, εδρα h/100.
  Κατοχες = FGA + 0.44·FTA − ORB + TOV (μεσος των 2 ομαδων)· ρυθμος ανα 48′ (παρατασεις = +5′ η καθε μια).
ΤΕΣΤ (σεζον 2021-22 … 2025-26· η 2020-21 μονο ως αφετηρια):
  ακριβεια (RMSE διαφορας) μοντελο vs Crown closing · κλιση b (διαφωνια μας με closing → εχει πληροφορια;) · ROI χαντικαπ σε edge ≥5/8/10%
  στις closing τιμες Crown· μικρο πλεγμα (εδρα, K, HL, carry) με LOSO. Εξοδος: nba_model_test_out.txt"""
import sys, json, math, itertools
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))

# ---------------- παιχνιδια ----------------
L = pd.read_csv('nba_gamelogs.csv', low_memory=False)
L = L[L.table == 'team_game_log_reg'].copy()
for c in ['team_game_score', 'opp_team_game_score', 'fga', 'fta', 'orb', 'tov', 'fg3', 'fg3a', 'ft', 'opp_fga', 'opp_fta', 'opp_orb', 'opp_tov', 'opp_fg3', 'opp_fg3a', 'opp_ft']:
    L[c] = pd.to_numeric(L[c], errors='coerce')
L['ot'] = pd.to_numeric(L.overtimes.astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
L.loc[L.overtimes.astype(str).str.strip() == 'OT', 'ot'] = 1
H = L[L.game_location.fillna('') != '@'].copy()          # μια γραμμη ανα ματς (ο γηπεδουχος)
G = pd.DataFrame(dict(season=H.season_end.astype(int), date=pd.to_datetime(H.date), home=H.team, away=H.opp_name_abbr,
                      hs=H.team_game_score, as_=H.opp_team_game_score, ot=H.ot,
                      h_fga=H.fga, h_fta=H.fta, h_orb=H.orb, h_tov=H.tov, h_3m=H.fg3, h_3a=H.fg3a, h_ftm=H.ft,
                      a_fga=H.opp_fga, a_fta=H.opp_fta, a_orb=H.opp_orb, a_tov=H.opp_tov, a_3m=H.opp_fg3, a_3a=H.opp_fg3a, a_ftm=H.opp_ft))
G['neutral'] = H.game_location.fillna('').str.upper().eq('N').values
G = G.dropna(subset=['hs', 'as_', 'h_fga', 'a_fga']).sort_values('date').reset_index(drop=True)
ph = G.h_fga + 0.44 * G.h_fta - G.h_orb + G.h_tov; pa = G.a_fga + 0.44 * G.a_fta - G.a_orb + G.a_tov
G['poss'] = (ph + pa) / 2; G['mins'] = 48 + 5 * G.ot; G['pace'] = G.poss * 48 / G.mins
SEAS = sorted(G.season.unique())
P(f'ματς κανονικης περιοδου: {len(G)} · σεζον {SEAS} · μεσος ρυθμος {G.pace.mean():.1f}/48′ · ποντοι/100 {100 * (G.hs + G.as_).sum() / (2 * G.poss.sum()):.1f}')

def luck_eff(w=0.5):
    """ποντοι/100 με 3P%/FT% w προς τον περσινο μεσο της λιγκας (1η σεζον: ιδιας σεζον)."""
    lg = {}
    for s in SEAS:
        g = G[G.season == s]
        lg[s] = dict(p3=(g.h_3m.sum() + g.a_3m.sum()) / (g.h_3a.sum() + g.a_3a.sum()), ft=(g.h_ftm.sum() + g.a_ftm.sum()) / (g.h_fta.sum() + g.a_fta.sum()))
    prev = {s: lg[SEAS[max(0, SEAS.index(s) - 1)]] for s in SEAS}
    res = []
    for side, pts in (('h', G.hs), ('a', G.as_)):
        p3l = G.season.map(lambda s: prev[s]['p3']).values; ftl = G.season.map(lambda s: prev[s]['ft']).values
        m3, a3, mf, af = G[f'{side}_3m'].values, G[f'{side}_3a'].values, G[f'{side}_ftm'].values, G[f'{side}_fta'].values
        p3g = np.where(a3 > 0, m3 / np.maximum(a3, 1), p3l); ftg = np.where(af > 0, mf / np.maximum(af, 1), ftl)
        adj = pts.values - 3 * m3 + 3 * a3 * (w * p3g + (1 - w) * p3l) - mf + af * (w * ftg + (1 - w) * ftl)
        res.append(100 * adj / G.poss.values)
    return res[0], res[1]

def fit_eff(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0):
    nG = len(hi); sw = np.sqrt(w)
    A = np.zeros((2 * nG + 2 * n + 1, 1 + 2 * n)); y = np.zeros(2 * nG + 2 * n + 1)
    r0 = np.arange(nG); r1 = nG + r0
    A[r0, 0] = sw; A[r0, 1 + hi] = sw; A[r0, 1 + n + ai] = sw; y[r0] = sw * (eh - hb)
    A[r1, 0] = sw; A[r1, 1 + ai] = sw; A[r1, 1 + n + hi] = sw; y[r1] = sw * (ea + hb)
    sl = math.sqrt(lam); k = np.arange(n)
    A[2 * nG + k, 1 + k] = sl; y[2 * nG + k] = sl * o0; A[2 * nG + n + k, 1 + n + k] = sl; y[2 * nG + n + k] = sl * d0
    A[-1, 0] = math.sqrt(5.0); y[-1] = math.sqrt(5.0) * mu0
    x = np.linalg.lstsq(A, y, rcond=None)[0]
    return x[0], x[1:1 + n], x[1 + n:]
def fit_pace(hi, ai, pc, w, n, p0, lam, pm0):
    nG = len(hi); sw = np.sqrt(w)
    A = np.zeros((nG + n + 1, 1 + n)); y = np.zeros(nG + n + 1); r0 = np.arange(nG)
    A[r0, 0] = sw; A[r0, 1 + hi] += sw; A[r0, 1 + ai] += sw; y[r0] = sw * pc
    sl = math.sqrt(lam); k = np.arange(n)
    A[nG + k, 1 + k] = sl; y[nG + k] = sl * p0
    A[-1, 0] = math.sqrt(5.0); y[-1] = math.sqrt(5.0) * pm0
    x = np.linalg.lstsq(A, y, rcond=None)[0]
    return x[0], x[1:]
EHA = {}
dnum = np.array([(d - G.date.iloc[0]).days for d in G.date])
def run(h=3.0, lam=8, HL=120, carry=0.7, lw=0.5, step=1):
    """walk-forward: προβλεψη διαφορας & συνολου για καθε ματς με οτι ηταν γνωστο ΠΡΙΝ τη μερα του (step = ανανεωση καθε Χ μερες)."""
    if lw not in EHA: EHA[lw] = luck_eff(lw)
    EH, EA = EHA[lw]
    pm_ = np.full(len(G), np.nan); pt_ = np.full(len(G), np.nan); prior = {}
    mu0 = float((EH.mean() + EA.mean()) / 2); pm0 = float(G.pace.mean())
    for s in SEAS:
        sidx = np.where(G.season.values == s)[0]
        teams = sorted(set(G.home.values[sidx]) | set(G.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        o0 = np.array([carry * prior.get(t, (0, 0, 0))[0] for t in teams]); d0 = np.array([carry * prior.get(t, (0, 0, 0))[1] for t in teams])
        p0 = np.array([carry * prior.get(t, (0, 0, 0))[2] for t in teams])
        hi = np.array([ix[t] for t in G.home.values[sidx]]); ai = np.array([ix[t] for t in G.away.values[sidx]])
        hb = np.where(G.neutral.values[sidx], 0.0, h / 2); dn = dnum[sidx]; eh = EH[sidx]; ea = EA[sidx]; pc = G.pace.values[sidx]
        days = np.unique(dn); last = None
        for d in days:
            past = dn < d; cur = np.where(dn == d)[0]
            if last is None or d - last >= step or not past.any():
                if past.any():
                    w = 0.5 ** ((d - dn[past]) / HL)
                    mu, O, Dd = fit_eff(hi[past], ai[past], eh[past], ea[past], hb[past], w, n, o0, d0, lam, mu0)
                    pm, Pc = fit_pace(hi[past], ai[past], pc[past], w, n, p0, lam, pm0)
                else:
                    mu, O, Dd, pm, Pc = mu0, o0, d0, pm0, p0
                last = d
            hh, aa, hbb = hi[cur], ai[cur], hb[cur]
            eh_ = mu + O[hh] + Dd[aa] + hbb; ea_ = mu + O[aa] + Dd[hh] - hbb; poss = pm + Pc[hh] + Pc[aa]
            pm_[sidx[cur]] = poss * (eh_ - ea_) / 100; pt_[sidx[cur]] = poss * (eh_ + ea_) / 100
        w = 0.5 ** ((dn.max() - dn) / HL)
        mu, O, Dd = fit_eff(hi, ai, eh, ea, hb, w, n, o0, d0, lam, mu0)
        pm, Pc = fit_pace(hi, ai, pc, w, n, p0, lam, pm0)
        prior = {t: (O[i], Dd[i], Pc[i]) for t, i in ix.items()}; mu0 = mu; pm0 = pm
    return pm_, pt_

# ---------------- αγορα: Crown closing απο Nowgoal (αντιστοιχιση με ημερομηνια ±1 & ΤΕΛΙΚΟ ΣΚΟΡ) ----------------
NGS = {'20-21': 2021, '21-22': 2022, '22-23': 2023, '23-24': 2024, '24-25': 2025, '25-26': 2026}
ODDS = {}
for ln in open('nowgoal_nba/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln); ODDS[(r['ngid'], r['t'])] = r['rows']
key = {}
for i, r in G.iterrows():
    key.setdefault((r.season, int(r.hs), int(r.as_)), []).append(i)
MK = {}
for sea, se in NGS.items():
    try: S = json.load(open(f'nowgoal_nba/sched_{sea}.json', encoding='utf-8'))
    except FileNotFoundError: continue
    for g in S:
        if g['hs'] is None: continue
        us = (pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)).tz_localize('UTC').tz_convert('America/New_York').tz_localize(None).normalize()
        cand = [i for i in key.get((se, g['hs'], g['as_']), []) if abs((G.date[i] - us).days) <= 1]
        swap = False
        if not cand:
            cand = [i for i in key.get((se, g['as_'], g['hs']), []) if abs((G.date[i] - us).days) <= 1]; swap = True
        if len(cand) != 1: continue
        i = cand[0]; rec = {}
        for t, nm in ((21, 'sp'), (23, 'tot')):
            rows = sorted([x for x in ODDS.get((g['ngid'], t), []) if x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
            if not rows: continue
            c = rows[-1]
            if nm == 'sp':
                Lh = -c[1] * (-1 if swap else 1)           # Nowgoal g: + = γηπεδουχος δινει ποντους → γραμμη γηπ = −g
                oh, oa = (1 + c[2], 1 + c[3]) if not swap else (1 + c[3], 1 + c[2])
                rec.update(L=Lh, oh=oh, oa=oa)
            else:
                rec.update(T=c[1], ov=1 + c[2], un=1 + c[3])
        if 'L' in rec: MK[i] = rec
P(f'ματς με Crown closing χαντικαπ: {len(MK)} · ανα σεζον ' + ', '.join(f'{s}: {sum(1 for i in MK if G.season[i] == s)}' for s in SEAS))
IDX = np.array(sorted(MK)); SE = G.season.values[IDX]
ACT = (G.hs - G.as_).values[IDX].astype(float); MM = np.array([-MK[i]['L'] for i in IDX])
EVAL = [s for s in SEAS[1:] if (SE == s).sum() >= 200]
if not EVAL:
    P('δεν υπαρχουν ακομα αρκετες αποδοσεις — ξανατρεξε αργοτερα'); open('nba_model_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out)); sys.exit()
SIG = float(np.std((ACT - MM)[np.isin(SE, EVAL)]))
P(f'σεζον-τεστ: {EVAL} · διασπορα (πραγματικο − closing) = {SIG:.2f} π. → σ για τις πιθανοτητες')
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
def roi(m, thr, seasons):
    rows = []
    for j, i in enumerate(IDX):
        if SE[j] not in seasons: continue
        r = MK[i]; Lh = r['L']; mu = m[i]
        if abs(Lh - round(Lh)) < 1e-9:
            pw = Phi((mu + Lh - 0.5) / SIG); pl = Phi((-mu - Lh - 0.5) / SIG)
        else:
            pw = Phi((mu + Lh) / SIG); pl = 1 - pw
        pp = 1 - pw - pl
        eh, ea = pw * r['oh'] + pp - 1, pl * r['oa'] + pp - 1
        side, e, od = (1, eh, r['oh']) if eh >= ea else (-1, ea, r['oa'])
        if e < thr: continue
        v = (ACT[j] + Lh) * side
        rows.append(dict(season=SE[j], p=(od - 1) if v > 0 else (0 if v == 0 else -1), fav=(Lh < 0) == (side == 1)))
    return pd.DataFrame(rows)
def report(lab, m):
    mm = np.isin(SE, EVAL); e = ACT - m[IDX]
    b = np.polyfit((m[IDX] - MM)[mm], (ACT - MM)[mm], 1)[0]
    cells = []
    for thr in (0.05, 0.08, 0.10):
        R = roi(m, thr, EVAL)
        pos = sum(1 for s in EVAL if len(R[R.season == s]) and R[R.season == s].p.mean() > 0)
        cells.append(f'≥{thr*100:.0f}%: {R.p.mean()*100:+.1f}% ({len(R)}) {pos}/{len(EVAL)}' if len(R) else f'≥{thr*100:.0f}%: —')
    P(f'  {lab:34s} RMSE {np.sqrt(np.mean(e[mm] ** 2)):.2f} (αγορα {np.sqrt(np.mean((ACT - MM)[mm] ** 2)):.2f}) · b {b:+.3f} | ' + ' | '.join(cells))
P('')
P('=== ΒΑΣΙΚΟ ΜΟΝΤΕΛΟ (ιδιο με Ευρωλιγκα) — προβλεψη πριν απο καθε μερα ===')
base = run(h=3.0, lam=8, HL=120, carry=0.7)[0]
report('εδρα 3/100 · K8 · HL120 · περσι 0.7', base)
P('')
P('=== ΜΙΚΡΟ ΠΛΕΓΜΑ (εδρα × K × HL × περσι) ===')
GRID = list(itertools.product([2.0, 3.0, 4.0], [8, 20], [60, 120], [0.5, 0.7]))
PR = {}
for c in GRID:
    PR[c] = run(h=c[0], lam=c[1], HL=c[2], carry=c[3])[0]
def rmse(m, ss):
    mm = np.isin(G.season.values, ss); return np.sqrt(np.mean(((G.hs - G.as_).values - m)[mm] ** 2))
held = np.full(len(G), np.nan); picks = []
for Y in EVAL:
    best = min(GRID, key=lambda c: rmse(PR[c], [s for s in EVAL if s != Y])); picks.append(best)
    held[G.season.values == Y] = PR[best][G.season.values == Y]
    P(f'  {Y} εξω: [εδρα {best[0]} · K {best[1]} · HL {best[2]} · περσι {best[3]}]')
report('LOSO επιλογη ακριβειας', held)
open('nba_model_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
