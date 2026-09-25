"""
intl_project.py — ΠΡΟΒΟΛΕΣ ΕΘΝΙΚΩΝ (σκια, 19/9/2026) για τα επερχομενα ματς Nations League A-D 2026/27 (FotMob).
Rating: H3 απο intl_rating2.py (Elo+xElo ενιαιο, πραγματικες εδρες, HFA ανα ομοσπονδια, υψομετρο) — intl_ratings_h.csv· προβλεψη NL με HFA 60,
        + στρωμα αξιας ροστερ: ELO_LN * ln(V_full_h / V_full_a) (intl_team_vfull.json, απο intl_value2 — ΠΕΡΑΣΕ 5/6).
Χαρτογραφηση:
  1Χ2: ordered logit diff -> (home, draw, away), fit σε ΟΛΑ τα αγωνιστικα ματς 2021+ (intl_preds_B.csv).
  Γκολ: supremacy s = a * diff (γραμμικη παλινδρομηση gd ~ diff, χωρις σταθερα — η εδρα ειναι μεσα στο diff)·
        συνολο T = μεσος γκολ ανα τυπο αγωνα (nl) · λ_h = (T+s)/2, λ_a = (T-s)/2 -> Poisson (picks.gd_dist) -> fair AH.
Εξοδος: intl_projections.csv + εκτυπωση. ΟΧΙ picks — μονο fair τιμες για συγκριση με την αγορα (σκια).
Τρεις εκδοχες (25/9): H = rating H3 + αξια ροστερ (στηλες χωρις καταληξη) · A = αγκυρα αγορας ΧΩΡΙΣ αξια (_A) · AV = αγκυρα + αξια (_AV, ιδιος logit/T με την A).
"""
import sys, json, gzip, urllib.request, math
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
import picks

_src = open('intl_rating.py', encoding='utf-8').read(); _ns = {'np': np}
exec(_src[_src.index('def sig(x):'):_src.index("EVAL_SEASONS = ")], _ns)
sig, fit_ol, probs = _ns['sig'], _ns['fit_ol'], _ns['probs']
HFA = 60      # 19/9 intl_hfa.py: μετρημενη εδρα εθνικων ~62 Elo (NL 49, προκριματικα 77, 2425/2526 75-88)· RPS αδιαφορο 50-80
COMPS = {'NationsLeagueA': 9806, 'NationsLeagueB': 9807, 'NationsLeagueC': 9808, 'NationsLeagueD': 9809}
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36', 'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}


def get(u):
    raw = urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=25).read()
    return gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw


# ---- ratings & χαρτογραφησεις ----
R = pd.read_csv('intl_ratings_h.csv', index_col=0).rename(columns={'R': 'B'})
RA = pd.read_csv('intl_ratings_anchor.csv', index_col=0)['R']          # 21/9: rating με αγκυρα αγορας (λ=0.3, intl_mkt_anchor.py) — ΧΩΡΙΣ στρωμα αξιας
PA = pd.read_csv('intl_preds_anchor.csv', dtype={'mid': str}).merge(pd.read_csv('intl_preds_H.csv', dtype={'season': str, 'mid': str})[['mid', 'ctype', 'date', 'gd']], on='mid')
PA = PA[PA.ctype.isin(['nl', 'qual', 'tourn']) & (pd.to_datetime(PA.date) >= '2020-07-01')]; PA['y'] = np.where(PA.gd > 0, 2, np.where(PA.gd == 0, 1, 0))     # 19/9: H3 (πραγματικες εδρες + HFA ομοσπονδιας + υψομετρο)
VF = json.load(open('intl_team_vfull.json', encoding='utf-8')); VFULL = {int(k): v for k, v in VF['vfull'].items()}; ELO_LN = VF['elo_per_ln']
# ---- 25/9/2026 ΑΠΟΦΑΣΗ ΣΤΕΛΙΟΥ: στρωμα αξιας = ΑΞΙΑ ΤΗΣ ΚΛΗΣΗΣ (αποστολη που θα παιξει), οχι «δυνατη ενδεκαδα 2 ετων» ----
# V_call = αθροισμα 11 μεγαλυτερων αξιων SciSports της τρεχουσας κλησης Transfermarkt (intl_callups_tm.py → intl_vcall_tm.json)·
# συντελεστης απο το τεστ intl_callup_test.py (K1o, Μ1 H3: RPS .16755 → .16694, 4/6) → intl_vcall_config.json.
# Ομαδα χωρις εγκυρη κληση (π.χ. Γερμανια: λιστα TM 43 ονοματα) ή κληση παλαιοτερη απο 10 ημερες πριν το ματς → V_full × (διαμεσος V_call/V_full
# της ιδιας ληψης), ωστε να ειναι στην ιδια κλιμακα με τις υπολοιπες.
import os as _os, datetime as _dtm
CALL_CFG = json.load(open('intl_vcall_config.json', encoding='utf-8')); ELO_LN_CALL = CALL_CFG['elo_per_ln']
_VC = json.load(open('intl_vcall_tm.json', encoding='utf-8')) if _os.path.exists('intl_vcall_tm.json') else {}
VCALL = {int(k): (v['v_call_sci'], v.get('asof')) for k, v in _VC.items() if v.get('v_call_sci')}
_sc = [VCALL[t][0] / VFULL[t] for t in VCALL if VFULL.get(t)]
CALL_SCALE = float(np.median(_sc)) if len(_sc) >= 10 else CALL_CFG['r_scale']


def v_call_of(tid, utc):
    """(αξια, πηγη) για την ομαδα στο ματς: κληση TM αν υπαρχει και ειναι φρεσκια (≤10 ημερες πριν το ματς), αλλιως V_full × CALL_SCALE."""
    vc = VCALL.get(tid)
    if vc and vc[1]:
        try:
            age = (_dtm.datetime.fromisoformat(str(utc)[:16]) - _dtm.datetime.fromisoformat(vc[1][:16])).days
        except Exception:
            age = 99
        if -1 <= age <= 10:
            return vc[0], 'κληση'
    return (VFULL[tid] * CALL_SCALE, 'V_full') if VFULL.get(tid) else (None, '—')


print(f"στρωμα αξιας ΚΛΗΣΗΣ: {len(VCALL)} ομαδες με κληση TM · {CALL_CFG['elo_per_doubling']:+.0f} Elo ανα διπλασιασμο · κλιμακα fallback V_full ×{CALL_SCALE:.3f}")
print(f"στρωμα αξιας: {len(VFULL)} ομαδες, {VF['elo_per_doubling']:+.0f} Elo ανα διπλασιασμο (V1, intl_value2)")
P = pd.read_csv('intl_preds_H.csv', dtype={'season': str, 'mid': str}, parse_dates=['date'])
C = P[P.ctype.isin(['nl', 'qual', 'tourn']) & (P.date >= '2020-07-01')].copy()
C['y'] = np.where(C.gd > 0, 2, np.where(C.gd == 0, 1, 0))
ol = fit_ol(C['diff'].values, C['y'].values)
olA = fit_ol(PA['diff_lam0.3'].values, PA['y'].values); aA = float(np.sum(PA['diff_lam0.3'] * PA['gd']) / np.sum(PA['diff_lam0.3'] ** 2))
a = float(np.sum(C['diff'] * C['gd']) / np.sum(C['diff'] ** 2))          # gd ~ a*diff
M = pd.read_csv('intl_matches.csv', dtype={'season': str, 'mid': str})
import intl_dedupe
M = intl_dedupe.dedupe(M, where='intl_project')   # 25/9: κλειδι ασφαλειας — διπλα ματς δεν μετρανε
T_nl = float((M[(M.ctype == 'nl') & (M.season >= '2223')].hs + M[(M.ctype == 'nl') & (M.season >= '2223')]['as']).mean())
print(f'ordered logit: beta {ol[0]:.4f}/Elo, c1 {ol[1]:.3f}, c2 {ol[2]:.3f} · supremacy a = {a*100:.3f} γκολ ανα 100 Elo · μεσο συνολο NL {T_nl:.2f}')

# ---- fixtures ----
rows = []
for comp, lid in COMPS.items():
    d = json.loads(get(f'https://www.fotmob.com/api/data/leagues?id={lid}&season=2026%2F2027'))
    for m in d.get('fixtures', {}).get('allMatches', []):
        st = m.get('status', {})
        if st.get('finished') or st.get('cancelled'):
            continue
        rows.append(dict(comp=comp, utc=st.get('utcTime', '')[:16], mid=str(m['id']), hid=int(m['home']['id']), aid=int(m['away']['id']),
                         home=m['home']['name'], away=m['away']['name'], rnd=m.get('round')))
F = pd.DataFrame(rows).sort_values('utc')
# ---- ΝΕΚΡΑ ΜΑΤΣ (21/9): ομιλοι απο ολο το προγραμμα, βαθμολογια απο τελειωμενα, ζωντανη = μπορει να πιασει 1η ή να πεσει τελευταια (D: μονο 1η) ----
import collections
alive = {}
for comp, lid in COMPS.items():
    dj = json.loads(get(f'https://www.fotmob.com/api/data/leagues?id={lid}&season=2026%2F2027')); allm = dj.get('fixtures', {}).get('allMatches', [])
    grp = [m for m in allm if str(m.get('round', '')).isdigit()]
    par = {}
    def find(x):
        while par.setdefault(x, x) != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for m in grp: par[find(int(m['home']['id']))] = find(int(m['away']['id']))
    groups = collections.defaultdict(set)
    for m in grp: groups[find(int(m['home']['id']))].update([int(m['home']['id']), int(m['away']['id'])])
    for teams in groups.values():
        teams = sorted(teams); n = len(teams); pts = collections.Counter(); rem = collections.Counter({tt: 0 for tt in teams})
        for m in grp:
            h, ta = int(m['home']['id']), int(m['away']['id'])
            if h not in teams: continue
            st = m.get('status', {})
            if st.get('finished'):
                try:
                    hs, as_ = [int(x) for x in st.get('scoreStr', '0 - 0').split(' - ')]
                except Exception:
                    continue
                pts[h] += 3 if hs > as_ else (1 if hs == as_ else 0); pts[ta] += 3 if as_ > hs else (1 if hs == as_ else 0)
            elif not st.get('cancelled'):
                rem[h] += 1; rem[ta] += 1
        order = sorted(teams, key=lambda tt: -pts[tt]); bottom = not comp.endswith('D')
        for tt in teams:
            rank = order.index(tt) + 1; ok = False
            if rank == 1 and n > 1 and pts[order[1]] + 3 * rem[order[1]] >= pts[tt]: ok = True
            if rank > 1 and pts[tt] + 3 * rem[tt] >= pts[order[0]]: ok = True
            if bottom and rank == n and pts[tt] + 3 * rem[tt] >= pts[order[n - 2]]: ok = True
            if bottom and rank < n and pts[order[n - 1]] + 3 * rem[order[n - 1]] >= pts[tt]: ok = True
            if rem[tt] == 0: ok = False
            alive[tt] = ok
F['alive_h'] = F.hid.map(alive); F['alive_a'] = F.aid.map(alive)
import datetime as _dt
_lim = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(days=10)).strftime('%Y-%m-%dT%H:%M')
F = F[F.utc <= _lim]          # 25/9: τρεχον παραθυρο = ματς των επομενων 10 ημερων (ηταν σταθερο '2026-10-01' → το αυτοματο refresh πιανει και τα επομενα παραθυρα)
out = []
for r in F.itertuples():
    if r.hid not in R.index or r.aid not in R.index:
        out.append(dict(comp=r.comp, utc=r.utc, home=r.home, away=r.away, note='χωρις rating')); continue
    rh, ra = float(R.loc[r.hid, 'B']), float(R.loc[r.aid, 'B'])
    (vh, srch), (va, srca) = v_call_of(r.hid, r.utc), v_call_of(r.aid, r.utc)
    vadj = ELO_LN_CALL * math.log(vh / va) if (vh and va) else 0.0          # 25/9: στρωμα αξιας ΚΛΗΣΗΣ (ηταν V_full)
    diff = rh + HFA - ra + vadj
    ph, pdr, pa = probs(np.array([diff]), ol)[0]
    # ---- εκδοχη ΑΓΚΥΡΑΣ (χωρις αξια) ----
    if r.hid in RA.index and r.aid in RA.index:
        rhA, raA = float(RA.loc[r.hid]), float(RA.loc[r.aid])
        dA = rhA + HFA - raA; phA, pdA, paA = probs(np.array([dA]), olA)[0]
        TA = 0.29 + 0.33 * abs(dA) / 100 + 0.49 * (abs(rhA - raA) < 150) + 0.10 * (rhA + raA) / 2 / 100 - 0.05; sA = aA * dA; lhA = max((TA + sA) / 2, 0.15); laA = max((TA - sA) / 2, 0.15)
        # ---- 25/9: εκδοχη AV = αγκυρα + στρωμα αξιας (ιδιος logit olA, ιδιο T με diff_AV) ----
        dAV = dA + vadj; phAV, pdAV, paAV = probs(np.array([dAV]), olA)[0]
        TAV = 0.29 + 0.33 * abs(dAV) / 100 + 0.49 * (abs(rhA - raA) < 150) + 0.10 * (rhA + raA) / 2 / 100 - 0.05; sAV = aA * dAV; lhAV = max((TAV + sAV) / 2, 0.15); laAV = max((TAV - sAV) / 2, 0.15)
    else:
        rhA = raA = dA = np.nan; phA = pdA = paA = np.nan; lhA = laA = np.nan
        dAV = np.nan; phAV = pdAV = paAV = np.nan; lhAV = laAV = np.nan
    # 22/9 (Στελιος «βαλτο»): συνολο γκολ ΜΕ ΚΑΤΑΣΤΑΣΗ + ΕΠΙΠΕΔΟ (intl_xg_totals, LOSO): T = 0.29 + 0.33·|diff|/100 + 0.26·[KO] + 0.49·[|ΔElo|<150] + 0.10·(R_h+R_a)/2/100 − 0.05·[NL]
    close_m = abs(rh - ra) < 150; T_m = 0.29 + 0.33 * abs(diff) / 100 + 0.49 * close_m + 0.10 * (rh + ra) / 2 / 100 - 0.05
    s = a * diff; lh = max((T_m + s) / 2, 0.15); la = max((T_m - s) / 2, 0.15)
    dist = picks.gd_dist(lh, la)
    fair = {}
    for line in (-1.5, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.5):
        pw, pp = picks.p_cover(dist, 1, line)          # γηπεδουχος με χαντικαπ line (αρνητικο = δινει)
        # fair δεκαδικη (με push): (1-pp)/pw
        fair[line] = round((1 - pp) / pw, 2) if pw > 0 else None
    # γραμμη οπου ο γηπεδουχος ~ 50%: η πλησιεστερη σε fair 2.00
    best = min(fair.items(), key=lambda kv: abs((kv[1] or 9) - 2.0))
    out.append(dict(comp=r.comp.replace('NationsLeague', 'NL '), utc=r.utc, home=r.home, away=r.away, hid=r.hid, aid=r.aid, νεκρη=('' if (r.alive_h is not False and r.alive_a is not False) else ('γηπ' if r.alive_h is False else '') + ('εκτος' if r.alive_a is False else '')),
                    R_home=round(rh), R_away=round(ra), val_adj=round(vadj), val_src=f'{srch}/{srca}', V_h=(round(vh / 1e6, 1) if vh else np.nan), V_a=(round(va / 1e6, 1) if va else np.nan), diff=round(diff), xg_h=round(lh, 2), xg_a=round(la, 2),
                    P1=round(ph * 100), PX=round(pdr * 100), P2=round(pa * 100),
                    fair_1=round(1 / ph, 2), fair_X=round(1 / pdr, 2), fair_2=round(1 / pa, 2),
                    fair_line=f'{best[0]:+.2f} @{best[1]}', fair_m05=fair[-0.5], fair_p05=fair[0.5],
                    diff_A=(round(dA) if pd.notna(dA) else np.nan), xg_h_A=(round(lhA, 2) if pd.notna(lhA) else np.nan), xg_a_A=(round(laA, 2) if pd.notna(laA) else np.nan), P1_A=(round(phA * 100) if pd.notna(phA) else np.nan), PX_A=(round(pdA * 100) if pd.notna(pdA) else np.nan), P2_A=(round(paA * 100) if pd.notna(paA) else np.nan),
                    R_home_A=(round(rhA) if pd.notna(rhA) else np.nan), R_away_A=(round(raA) if pd.notna(raA) else np.nan),
                    diff_AV=(round(dAV) if pd.notna(dAV) else np.nan), xg_h_AV=(round(lhAV, 2) if pd.notna(lhAV) else np.nan), xg_a_AV=(round(laAV, 2) if pd.notna(laAV) else np.nan), P1_AV=(round(phAV * 100) if pd.notna(phAV) else np.nan), PX_AV=(round(pdAV * 100) if pd.notna(pdAV) else np.nan), P2_AV=(round(paAV * 100) if pd.notna(paAV) else np.nan)))
O = pd.DataFrame(out)
O.to_csv('intl_projections.csv', index=False)
pd.set_option('display.width', 250)
print(O.to_string(index=False))
