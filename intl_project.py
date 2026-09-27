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
try:      # 27/9: μη διαθεσιμοι FotMob (τραυματισμος/τιμωρια) + προβλεπομενη 11αδα — intl_unavailable.py
    _UJ = json.load(open('intl_unavailable.json', encoding='utf-8'))
    UNAV = {k: v for k, v in _UJ.items() if not k.startswith('_')}
    XI = _UJ.get('_xi') or {}
except Exception:
    UNAV, XI = {}, {}
try:      # 27/9: ΧΕΙΡΟΚΙΝΗΤΕΣ απουσιες και εδω (ισχυουν και για κλησεις απο αποστολες FotMob, π.χ. Γερμανια/Havertz)
    MANUAL = {k: v for k, v in json.load(open('intl_absences_manual.json', encoding='utf-8')).items() if not k.startswith('_')}
except Exception:
    MANUAL = {}
try:      # 27/9: αξιες SciSports (συμπαγες) για παικτες της 11αδας που δεν ειναι στη λιστα TM
    PVN = json.load(open('intl_player_values_now.json', encoding='utf-8'))
except Exception:
    PVN = {}
try:      # 27/9: ΕΠΙΣΗΜΕΣ αποστολες (~60′ πριν, intl_lineups_check.py) → αξια των 23 που ντυθηκαν για ΑΥΤΟ το ματς
    LUP = {}
    for _k, _L in json.load(open('intl_lineups.json', encoding='utf-8')).items():
        _c, _h, _a, _u = _k.split('|')
        LUP[(_h, _a, _u.replace(' ', 'T')[:16])] = _L
except Exception:
    LUP = {}


try:      # 27/9: αποστολες FotMob των ματς του τρεχοντος παραθυρου (για «ντυθηκε αλλα δεν υπηρξε ΠΟΤΕ στη λιστα TM»)
    _SQ = json.load(open('intl_squads.json', encoding='utf-8'))
    _MW = pd.read_csv('intl_matches.csv', dtype={'mid': str})
    _MW = _MW[_MW.date >= (_dtm.datetime.now() - _dtm.timedelta(days=10)).strftime('%Y-%m-%d')].sort_values('date')
    LAST_SQ = {}
    for _r in _MW.itertuples():
        for _sk, _t in (('h', _r.hid), ('a', _r.aid)):
            _p = ((_SQ.get(_r.mid) or {}).get(_sk) or {}).get('p') or {}
            if len(_p) >= 16:
                LAST_SQ[int(_t)] = (str(_r.date)[:16], [int(x) for x in _p])      # η ΤΕΛΕΥΤΑΙΑ (ταξινομηση κατα ημερομηνια)
except Exception:
    LAST_SQ = {}


import intl_value_rule as VR      # 27/9: κανονας τερματοφυλακα


def _nm(s):
    import unicodedata
    return ' '.join(unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower().replace('-', ' ').split())


def _same_person(a, b):
    a, b = _nm(a).split(), _nm(b).split()
    return bool(a and b) and a[-1] == b[-1] and a[0][:1] == b[0][:1]
VCALL = {int(k): (v['v_call_sci'], v.get('asof')) for k, v in _VC.items() if v.get('v_call_sci')}
_sc = [VCALL[t][0] / VFULL[t] for t in VCALL if VFULL.get(t)]
CALL_SCALE = float(np.median(_sc)) if len(_sc) >= 10 else CALL_CFG['r_scale']


def v_call_of(tid, utc, home=None, away=None, side=None):
    """(αξια, πηγη) για την ομαδα στο ματς: κληση TM αν υπαρχει και ειναι φρεσκια (≤10 ημερες πριν το ματς), αλλιως V_full × CALL_SCALE.
    27/9: (1) ΕΠΙΣΗΜΗ αποστολη του ματς αν εχει βγει (~60′ πριν) → αξια των 23· (2) αλλιως κληση + παικτες της προβλεπομενης 11αδας
    που λειπουν απο τη λιστα TM − μη διαθεσιμοι FotMob."""
    L = LUP.get((str(home), str(away), str(utc).replace(' ', 'T')[:16])) if home else None
    if L and side:
        t_ = (L.get('teams') or {}).get(side) or {}
        if t_.get('v1'):
            return float(t_['v1']), 'αποστολη'
    vc = VCALL.get(tid)
    if vc and vc[1]:
        try:
            age = (_dtm.datetime.fromisoformat(str(utc)[:16]) - _dtm.datetime.fromisoformat(vc[1][:16])).days
        except Exception:
            age = 99
        if -1 <= age <= 10:
            # 27/9 (Στελιος): ΑΠΟΥΣΙΕΣ FotMob πριν την αποστολη (intl_unavailable.json: injury/suspension, οχι «Doubtful»)
            out_ = {int(p_) for p_, u_ in (UNAV.get(str(tid)) or {}).items()
                    if u_.get('type') in ('injury', 'suspension') and not u_.get('doubtful')
                    and u_.get('until') and str(utc)[:10] < u_['until']}      # μονο αν το ματς ειναι ΠΡΙΝ την επιστροφη
            pl_ = [p_ for p_ in (_VC.get(str(tid)) or {}).get('players', []) if p_.get('v')]
            have_ = {int(p_['pid']) for p_ in pl_ if p_.get('pid')}
            add_ = []
            seen_map_ = (_VC.get(str(tid)) or {}).get('seen') or {}
            seen_ = list(seen_map_.keys()) + list((_VC.get(str(tid)) or {}).get('called') or [])
            first_tm_ = min([x for x in seen_map_.values() if x] or ['9999'])      # πρωτο «στιγμιοτυπο» λιστας TM που εχουμε
            xi_ = XI.get(str(tid)) or {}
            last_d_, last_p_ = LAST_SQ.get(int(tid), ('', []))
            # «ΠΑΛΙΟ» ματς (αποστολη του τελευταιου ματς ή lastStarting11): προσθηκη ΜΟΝΟ αν εχουμε λιστα TM ΑΠΟ ΠΡΙΝ εκεινο το ματς και ο παικτης
            # ΔΕΝ υπηρξε ποτε μεσα (λιστα ελλιπης, π.χ. Hancko)· αν ΗΤΑΝ και βγηκε (Brobbey) ή δεν ξερουμε (λιστα μετα το ματς) → οχι
            can_old_ = bool(last_d_) and first_tm_ < last_d_
            cand_ = [(x_['pid'], x_.get('name', ''), 'xi' if xi_.get('type') in ('predicted', 'standard') else 'old')
                     for x_ in (xi_.get('players') or [])]
            cand_ += [(p_, (PVN.get(str(p_)) or [''])[0], 'old') for p_ in last_p_]
            added_ = set()
            # 27/9: οι ΧΕΙΡΟΚΙΝΗΤΑ εκτος (intl_absences_manual → manual_out) ΔΕΝ ξαναμπαινουν ποτε (π.χ. Isak: ντυθηκε 25/9, λειπει)
            man_ = [m_.get('nm') or '' for m_ in ((_VC.get(str(tid)) or {}).get('manual_out') or [])] +                    [m_.get('tm') or '' for m_ in ((_VC.get(str(tid)) or {}).get('manual_out') or [])]
            _mt = MANUAL.get((_VC.get(str(tid)) or {}).get('nm', '')) or {}
            if not _mt.get('until') or str(utc)[:10] <= _mt['until']:
                man_ += list(_mt.get('out') or [])
            pl_ = [p_ for p_ in pl_ if not any(m_ and _same_person(m_, p_.get('tm', '')) for m_ in man_)]      # εκτος και απο την ιδια την κληση
            for pid_, name_, why_ in cand_:
                if pid_ in have_ or pid_ in added_ or pid_ in out_:
                    continue
                if any(m_ and _same_person(m_, name_) for m_ in man_):
                    continue
                if any(not p_.get('pid') and _same_person(p_['tm'], name_) for p_ in pl_):
                    continue
                if why_ == 'old' and (not can_old_ or any(_same_person(s_, name_) for s_ in seen_)):
                    continue
                v_ = (PVN.get(str(pid_)) or [None, None])[1]
                if v_:
                    add_.append((pid_, v_)); added_.add(pid_)
            items_ = [(p_.get('pid'), p_['v']) for p_ in pl_ if not (p_.get('pid') and int(p_['pid']) in out_)] + add_
            # 27/9: κανονας τερματοφυλακα (intl_value_rule, διακοπτης gk_rule) — προτιμηση στον τερματοφυλακα της 11αδας FotMob
            gk_xi_ = next((x_['pid'] for x_ in (xi_.get('players') or []) if int(x_['pid']) in VR.GK), None)
            V_ = VR.top11(items_, tid, utc, gk_xi_)
            if V_ and abs(V_ - vc[0]) > 1:
                return V_, 'κληση' + ('+11αδα' if add_ else '') + ('−FotMob' if out_ else '') + ('·ΤΦ' if VR.enabled() else '')
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
# 25/9 (γ) ΒΑΘΙΑ ΦΑΒΟΡΙ: υπεροχη με a_deep (intl_deepfav_config.json) → στηλες xg_*_D· το intl_pricing.dist_for τις χρησιμοποιει ΜΟΝΟ για φαβορι ≤ −2
ADEEP = json.load(open('intl_deepfav_config.json', encoding='utf-8'))['a_deep']
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
    (vh, srch), (va, srca) = v_call_of(r.hid, r.utc, r.home, r.away, 'h'), v_call_of(r.aid, r.utc, r.home, r.away, 'a')
    vadj = ELO_LN_CALL * math.log(vh / va) if (vh and va) else 0.0          # 25/9: στρωμα αξιας ΚΛΗΣΗΣ (ηταν V_full)
    diff = rh + HFA - ra + vadj
    ph, pdr, pa = probs(np.array([diff]), ol)[0]
    # ---- εκδοχη ΑΓΚΥΡΑΣ (χωρις αξια) ----
    if r.hid in RA.index and r.aid in RA.index:
        rhA, raA = float(RA.loc[r.hid]), float(RA.loc[r.aid])
        dA = rhA + HFA - raA; phA, pdA, paA = probs(np.array([dA]), olA)[0]
        TA = 0.29 + 0.33 * abs(dA) / 100 + 0.49 * (abs(rhA - raA) < 150) + 0.10 * (rhA + raA) / 2 / 100 - 0.05; sA = aA * dA; lhA = max((TA + sA) / 2, 0.15); laA = max((TA - sA) / 2, 0.15)
        lhA_D = max((TA + ADEEP['A'] * dA) / 2, 0.15); laA_D = max((TA - ADEEP['A'] * dA) / 2, 0.15)
        # ---- 25/9: εκδοχη AV = αγκυρα + στρωμα αξιας (ιδιος logit olA, ιδιο T με diff_AV) ----
        dAV = dA + vadj; phAV, pdAV, paAV = probs(np.array([dAV]), olA)[0]
        TAV = 0.29 + 0.33 * abs(dAV) / 100 + 0.49 * (abs(rhA - raA) < 150) + 0.10 * (rhA + raA) / 2 / 100 - 0.05; sAV = aA * dAV; lhAV = max((TAV + sAV) / 2, 0.15); laAV = max((TAV - sAV) / 2, 0.15)
        lhAV_D = max((TAV + ADEEP['AV'] * dAV) / 2, 0.15); laAV_D = max((TAV - ADEEP['AV'] * dAV) / 2, 0.15)
    else:
        rhA = raA = dA = np.nan; phA = pdA = paA = np.nan; lhA = laA = np.nan; lhA_D = laA_D = np.nan
        dAV = np.nan; phAV = pdAV = paAV = np.nan; lhAV = laAV = np.nan; lhAV_D = laAV_D = np.nan
    # 22/9 (Στελιος «βαλτο»): συνολο γκολ ΜΕ ΚΑΤΑΣΤΑΣΗ + ΕΠΙΠΕΔΟ (intl_xg_totals, LOSO): T = 0.29 + 0.33·|diff|/100 + 0.26·[KO] + 0.49·[|ΔElo|<150] + 0.10·(R_h+R_a)/2/100 − 0.05·[NL]
    close_m = abs(rh - ra) < 150; T_m = 0.29 + 0.33 * abs(diff) / 100 + 0.49 * close_m + 0.10 * (rh + ra) / 2 / 100 - 0.05
    s = a * diff; lh = max((T_m + s) / 2, 0.15); la = max((T_m - s) / 2, 0.15)
    lh_D = max((T_m + ADEEP['H'] * diff) / 2, 0.15); la_D = max((T_m - ADEEP['H'] * diff) / 2, 0.15)
    dist = picks.gd_dist(lh, la)
    fair = {}
    for line in (-1.5, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.5):
        pw, pp = picks.p_cover(dist, 1, line)          # γηπεδουχος με χαντικαπ line (αρνητικο = δινει)
        # fair δεκαδικη (με push): (1-pp)/pw
        fair[line] = round((1 - pp) / pw, 2) if pw > 0 else None
    # γραμμη οπου ο γηπεδουχος ~ 50%: η πλησιεστερη σε fair 2.00
    best = min(fair.items(), key=lambda kv: abs((kv[1] or 9) - 2.0))
    out.append(dict(comp=r.comp.replace('NationsLeague', 'NL '), utc=r.utc, home=r.home, away=r.away, hid=r.hid, aid=r.aid, νεκρη=('' if (r.alive_h is not False and r.alive_a is not False) else ('γηπ' if r.alive_h is False else '') + ('εκτος' if r.alive_a is False else '')),
                    R_home=round(rh), R_away=round(ra), val_adj=round(vadj), xg_h_D=round(lh_D, 3), xg_a_D=round(la_D, 3), xg_h_A_D=(round(lhA_D, 3) if pd.notna(lhA_D) else np.nan), xg_a_A_D=(round(laA_D, 3) if pd.notna(laA_D) else np.nan), xg_h_AV_D=(round(lhAV_D, 3) if pd.notna(lhAV_D) else np.nan), xg_a_AV_D=(round(laAV_D, 3) if pd.notna(laAV_D) else np.nan), val_src=f'{srch}/{srca}', V_h=(round(vh / 1e6, 1) if vh else np.nan), V_a=(round(va / 1e6, 1) if va else np.nan), Vh_raw=(round(vh) if vh else np.nan), Va_raw=(round(va) if va else np.nan), diff=round(diff), xg_h=round(lh, 2), xg_a=round(la, 2),
                    P1=round(ph * 100), PX=round(pdr * 100), P2=round(pa * 100),
                    fair_1=round(1 / ph, 2), fair_X=round(1 / pdr, 2), fair_2=round(1 / pa, 2),
                    fair_line=f'{best[0]:+.2f} @{best[1]}', fair_m05=fair[-0.5], fair_p05=fair[0.5],
                    diff_A=(round(dA) if pd.notna(dA) else np.nan), xg_h_A=(round(lhA, 2) if pd.notna(lhA) else np.nan), xg_a_A=(round(laA, 2) if pd.notna(laA) else np.nan), P1_A=(round(phA * 100) if pd.notna(phA) else np.nan), PX_A=(round(pdA * 100) if pd.notna(pdA) else np.nan), P2_A=(round(paA * 100) if pd.notna(paA) else np.nan),
                    R_home_A=(round(rhA) if pd.notna(rhA) else np.nan), R_away_A=(round(raA) if pd.notna(raA) else np.nan),
                    diff_AV=(round(dAV) if pd.notna(dAV) else np.nan), xg_h_AV=(round(lhAV, 2) if pd.notna(lhAV) else np.nan), xg_a_AV=(round(laAV, 2) if pd.notna(laAV) else np.nan), P1_AV=(round(phAV * 100) if pd.notna(phAV) else np.nan), PX_AV=(round(pdAV * 100) if pd.notna(pdAV) else np.nan), P2_AV=(round(paAV * 100) if pd.notna(paAV) else np.nan)))
O = pd.DataFrame(out)
O.to_csv('intl_projections.csv', index=False)
# 26/9: συντελεστες για τον ελεγχο ενδεκαδων πριν το ματς (intl_lineups_check.py ξαναβγαζει Μ1/Μ3 με την αξια της πραγματικης αποστολης)
json.dump(dict(a=a, aA=aA, adeep=ADEEP, elo_per_ln=ELO_LN_CALL, hfa=HFA), open('intl_project_coefs.json', 'w', encoding='utf-8'), indent=1)
pd.set_option('display.width', 250)
print(O.to_string(index=False))
