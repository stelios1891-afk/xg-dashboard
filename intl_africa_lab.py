"""
intl_africa_lab.py — ΕΡΓΑΣΤΗΡΙΟ ΑΦΡΙΚΗΣ (25/9/2026, εντολη Στελιου: «τρεξε ολα τα τεστ, ολους τους πιθανους μηχανισμους, βρες τι ταιριαζει
αποκλειστικα για την Αφρικη· τα Μ2/Μ3 που ειναι;»).

ΔΕΔΟΜΕΝΑ: ολα τα αφρικανικα αγωνιστικα (AFCONQ, AFCON, WCQ_CAF) με γραμμες Nowgoal (Crown 3 / SBOBET 31), 5 κυκλοι:
  2015-17 · 2017-19 · 2019-22 · 2022-24 · 2024-26 (ορισμος κυκλου απο ημερομηνια).
  Ratings: ΙΔΙΑ μηχανη H3 με το live (intl_rating2_hist: Elo+xElo, seed CAF τελος 2010, walk απο 2011) — ξανατρεχει εδω με ρυθμιζομενες
  παραμετρους· ΕΛΕΓΧΟΣ: με τις live παραμετρους αναπαραγει το intl_preds_H.csv (αλλιως σταματα).
  Αγκυρα (για Μ2/Μ3 Αφρικης): μετα απο καθε ματς με closing AH Crown τα ratings κινουνται λ·(d_αγορας − d)/2 (ιδιος κανονας με intl_mkt_anchor)·
  closing: intl_close_hist.json (μη αφρικανικα) + τελευταια pre-match γραμμη Crown των αφρικανικων (Nowgoal).

ΜΟΝΤΕΛΟ-ΒΑΣΗ (= live Αφρικης σημερα): diff = H3 (HFA CAF 80, υψομετρο 110) + αξια ELO_LN·ln(V_full) · T = 0.29+0.33|diff|/100+0.26·KO+0.49·[|ΔElo|<150]+0.10·μεσο Elo/100 ·
  υπεροχη 0.491·diff · Poisson (DRAW_BOOST 1.13) · σωστα τεταρτα.

ΠΡΟ-ΔΗΛΩΣΗ (γραφτηκε ΠΡΙΝ τρεξει· ΜΙΑ εκτελεση· ολες οι παραμετροι LOSO ανα κυκλο: επιλογη ΜΟΝΟ απο τους αλλους 4 κυκλους, με ακριβεια αποτελεσματων —
ΠΟΤΕ με ROI):
  Μηχανισμοι με τη σειρα (καθε ενας πανω στους αποδεκτους προηγουμενους):
    Μ-1 εδρα CAF ∈ {40,60,80,100,120,140} (ξανατρεχει ratings)          κριτηριο: log-lik διαφορας γκολ
    Μ-2 υψομετρο ∈ {0,55,110,165}                                          log-lik διαφορας γκολ
    Μ-3 βαρος αξιας ροστερ ×{0,0.5,1,1.5}                                  log-lik διαφορας γκολ
    Μ-4 κλιση υπεροχης (OLS gd~diff)                                       log-lik διαφορας γκολ
    Μ-5 μετατοπιση συνολου γκολ Αφρικης (μεσος υπολοιπου)                  log-lik συνολου γκολ (Poisson)
    Μ-6 σχημα: κοινα γκολ λ3 ∈ {0..0.4}                                   log-lik διαφορας γκολ
    Μ-7 αγκυρα λ ∈ {0.1,0.2,0.3,0.5} (Μ2 = αγκυρα, Μ3 = αγκυρα+αξια)     log-lik διαφορας γκολ
  ΑΠΟΔΟΧΗ μηχανισμου: καλυτερος απο το προηγουμενο βημα σε ≥4/5 κυκλους (LOSO) ΚΑΙ στο συνολο.
  ΤΕΛΙΚΟ (αναφορα + αποφαση): παραθυρο 72ω (και closing), live κανονες (AH |γρ|≥0.5, 1.70-2.10, edge≥10% · OVER edge≥8% ΚΑΙ (κοντινο ή KO))·
    Μ1 βαση vs Μ1 διορθωμενο · Μ2 · Μ3 · συναινεση ≥2/3 · και Σχεδιο Β / βαθια φαβορι πανω στο διορθωμενο.
    Ενα ROI = μεσος Crown/SBOBET (σημειωση αν διαφωνουν). Κριτηριο για live: ROI 72ω > 0 ΚΑΙ ≥3/5 κυκλοι θετικοι ΚΑΙ και στα 2 βιβλια > 0.
Εξοδος: intl_africa_lab_out.txt, intl_africa_lab_bets.csv
"""
import sys, json, math, ast, time
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
import picks
T0 = time.time()
out = []
def P_(s=''):
    print(s, flush=True); out.append(str(s))

# ================= 1. μηχανη ratings (αντιγραφο του intl_rating2_hist, με παραμετρους) =================
_s = open('intl_rating2_hist.py', encoding='utf-8').read()
G = {'__name__': 'lab'}
exec(_s[:_s.index('def run(mode):')], G)
M, SEED, CAF_IDS, HFA_CONF, home_elev, CUTOFF = G['M'], G['SEED'], G['CAF_IDS'], G['HFA_CONF'], G['home_elev'], G['CUTOFF']
adj_xg, exp_score, margin_mult, FAV_D, K_TYPE = G['adj_xg'], G['exp_score'], G['margin_mult'], G['FAV_D'], G['K_TYPE']
AFR_COMPS = {'AFCONQ', 'AFCON', 'WCQ_CAF'}
_raw = _adj = 0.0
for r in M[M.has_xg].itertuples():
    a_, b_ = adj_xg(r.shots, 0, 'gs'); _raw += r.xg_h + r.xg_a; _adj += a_ + b_
SCALE = _raw / _adj
XS = {}
ROWS_M = list(M.itertuples())


def walk(hfa_caf=None, alt=110, lam=0.0, close=None):
    """ιδιο με run('H3')· hfa_caf = εδρα για ΤΑ ΑΦΡΙΚΑΝΙΚΑ ματς (None = οπως το live: CAF 80 / AFCONQ 'OTHER' 80)· lam = αγκυρα."""
    R = dict(SEED); rec = {}
    for r in ROWS_M:
        is_early = r.date < CUTOFF; h_caf = r.hid in CAF_IDS; a_caf = r.aid in CAF_IDS
        if is_early and not h_caf and not a_caf:
            continue
        uh = (not is_early) or h_caf; ua = (not is_early) or a_caf
        rh = R.get(r.hid, 1500.0); ra = R.get(r.aid, 1500.0)
        base = HFA_CONF.get(r.conf, 80)
        if hfa_caf is not None and r.comp in AFR_COMPS:
            base = hfa_caf
        h = base * r.hsign
        if r.hsign == 1 and pd.notna(r.elev) and r.elev >= 1500 and home_elev.get(r.aid, 0) < 1000:
            h += (alt if r.comp in AFR_COMPS else 110)
        d = rh + h - ra; E = 1 / (1 + 10 ** (-d / 400)); gd = int(r.hs) - int(r.ag)
        rec[r.mid] = (d, rh, ra)
        S_res = 1.0 if gd > 0 else (0.5 if gd == 0 else 0.0)
        if r.has_xg:
            fav = 1 if d >= FAV_D else (-1 if d <= -FAV_D else 0)
            k_ = (r.mid, fav)
            if k_ not in XS:
                xh, xa = adj_xg(r.shots, fav, 'gs'); XS[k_] = (xh * SCALE, xa * SCALE)
            xh, xa = XS[k_]
            S = 0.5 * S_res + 0.5 * exp_score(xh, xa); mm = margin_mult(round(0.5 * gd + 0.5 * (xh - xa)))
        else:
            S = S_res; mm = margin_mult(gd)
        K = K_TYPE.get(r.ctype, 30) * mm
        if uh: R[r.hid] = rh + K * (S - E)
        if ua: R[r.aid] = ra - K * (S - E)
        if lam > 0 and close is not None and r.mid in close:
            sh = lam * (close[r.mid] - d) / 2
            if uh: R[r.hid] += sh
            if ua: R[r.aid] -= sh
    return rec


base_rec = walk()
PH = pd.read_csv('intl_preds_H.csv', dtype={'mid': str})
chk = PH[PH.mid.isin(base_rec.keys())]
dev = np.abs(chk['diff'].values - np.array([base_rec[m][0] for m in chk.mid])).max()
P_(f'ΕΛΕΓΧΟΣ αναπαραγωγης live H3: {len(chk)} ματς, μεγιστη αποκλιση diff {dev:.2e}')
assert dev < 1e-6, 'η μηχανη του εργαστηριου ΔΕΝ αναπαραγει το live H3 — σταματω'

# ================= 2. γραμμες Nowgoal Αφρικης + closing για αγκυρα =================
NAMES = json.load(open('nowgoal_intl_team_names.json', encoding='utf-8'))
ALIAS = {'Democratic Rep Congo': 'DR Congo', 'Republic of the Congo': 'Congo', 'Guinea Bissau': 'Guinea-Bissau', "Cote d'Ivoire": 'Ivory Coast',
         "Côte d'Ivoire": 'Ivory Coast', 'Cabo Verde': 'Cape Verde', 'Swaziland': 'Eswatini', 'Sao Tome': 'Sao Tome and Principe', 'Sao Tome & Principe': 'Sao Tome and Principe',
         'Central Africa': 'Central African Republic'}
N2ID = {}
for r in M.itertuples():
    N2ID[str(r.hn)] = int(r.hid); N2ID[str(r.an)] = int(r.aid)
def tid(ng):
    nm = NAMES.get(str(ng), ''); return N2ID.get(ALIAS.get(nm, nm))
def hk(x):
    v = float(x); return v + 1 if v < 1.5 else v
def line_of(s):
    s = str(s)
    if '/' in s:
        a_, b_ = s.split('/'); return (float(a_) + float(b_)) / 2
    return float(s)
AFR = M[M.comp.isin(AFR_COMPS)].copy()
AFI = {}
for r in AFR.itertuples():
    AFI.setdefault((int(r.hid), int(r.aid)), []).append((r.date, r.mid))
KOT = {r.mid: pd.Timestamp(r.date).tz_localize('UTC').timestamp() for r in AFR.itertuples()}
ROWS = {}; OU = {}; unm = 0; nng = 0
for f in ('intl_ng_hist_afconq.json', 'intl_ng_hist_wcqcaf.json'):
    for ng, v in json.load(open(f, encoding='utf-8')).items():
        nng += 1; h_, a_ = tid(v['hid']), tid(v['aid']); dt = pd.to_datetime(v['dt']) - pd.Timedelta(hours=8); mid = None; flip = False
        for (x, y, fl) in ((h_, a_, False), (a_, h_, True)):
            c = [m for d_, m in AFI.get((x, y), []) if abs((d_ - dt).total_seconds()) <= 36 * 3600] if (x and y) else []
            if c:
                mid, flip = c[0], fl; break
        if mid is None:
            unm += 1; continue
        books = v['books'] if isinstance(v['books'], dict) else ast.literal_eval(v['books']); ko = KOT[mid]
        for cid in ('3', '31'):
            b = books.get(cid) or {}; rec = []; ou = []
            for x in (b.get('ah') or []):
                try:
                    if x[0] and x[0] < ko and x[1] not in (None, '') and x[2] not in (None, '', '0') and x[3] not in (None, '', '0'):
                        L, oh, oa = -line_of(x[1]), hk(x[2]), hk(x[3])
                        if flip: L, oh, oa = -L, oa, oh
                        rec.append(((ko - x[0]) / 3600, L, oh, oa))
                except Exception:
                    pass
            for x in (b.get('ou') or []):
                try:
                    if x[0] and x[0] < ko and x[1] not in (None, '') and x[2] not in (None, '', '0'):
                        ou.append(((ko - x[0]) / 3600, line_of(x[1]), hk(x[2]), hk(x[3])))
                except Exception:
                    pass
            if rec: ROWS[(mid, cid)] = sorted(rec, key=lambda z: -z[0])
            if ou: OU[(mid, cid)] = sorted(ou, key=lambda z: -z[0])
P_(f'Nowgoal Αφρικης: {nng} εγγραφες · αταιριαστες {unm} · ματς με AH Crown {sum(1 for k in ROWS if k[1] == "3")} / SBOBET {sum(1 for k in ROWS if k[1] == "31")} · O/U Crown {sum(1 for k in OU if k[1] == "3")}')


def sup_from_line(line, oh, oa, T=2.6):
    kk = 1 / oh + 1 / oa; tgt = (1 / oh) / kk; lo, hi = -4.0, 4.0
    for _ in range(30):
        mid_ = (lo + hi) / 2; lh_ = max((T + mid_) / 2, 0.15); la_ = max((T - mid_) / 2, 0.15)
        pw, pp_ = picks.p_cover(picks.gd_dist(lh_, la_), 1, line); p_eff = pw / max(1 - pp_, 1e-9)
        lo, hi = (mid_, hi) if p_eff < tgt else (lo, mid_)
    return (lo + hi) / 2
CL = json.load(open('intl_close_hist.json', encoding='utf-8'))
CLOSE = {}
for m, v in CL.items():
    if v.get('ah_line') is not None and v.get('ah_h') and v.get('ah_a'):
        try: CLOSE[m] = sup_from_line(float(v['ah_line']), float(v['ah_h']), float(v['ah_a'])) / 0.0049
        except Exception: pass
n0 = len(CLOSE)
for (m, cid), rec in ROWS.items():
    if cid == '3' and m not in CLOSE:
        _, L, oh, oa = rec[-1]; CLOSE[m] = sup_from_line(L, oh, oa) / 0.0049
P_(f'closing για αγκυρα: {n0} μη αφρικανικα + {len(CLOSE) - n0} αφρικανικα')

# ================= 3. δειγμα αξιολογησης =================
EV = pd.read_csv('intl_callup_test_events.csv', dtype={'mid': str})[['mid', 'vf_h', 'vf_a']]
ELO_LN = json.load(open('intl_team_vfull.json', encoding='utf-8'))['elo_per_ln']
KO_R = {}
for f in ('data_AFCON_2017.json', 'data_AFCON_2019.json', 'data_AFCON_2021.json', 'data_AFCON_2023.json', 'data_AFCON_2025.json'):
    try:
        for mid, v in json.load(open(f, encoding='utf-8')).items():
            KO_R[str(mid)] = not str(v.get('round')).isdigit()
    except Exception:
        pass
A = AFR[AFR.mid.isin({k[0] for k in ROWS})].merge(EV, on='mid', how='left').copy()
A['gd'] = A.hs - A.ag; A['tot'] = A.hs + A.ag
A['lv'] = np.where((A.vf_h > 0) & (A.vf_a > 0), np.log(A.vf_h / A.vf_a), 0.0); A['has_v'] = (A.vf_h > 0) & (A.vf_a > 0)
A['KO'] = A.mid.map(lambda m: KO_R.get(m, False)).astype(float)
A['cyc'] = np.select([A.date < '2017-12-31', A.date < '2019-08-01', A.date < '2022-03-31', A.date < '2024-03-01'], ['2015-17', '2017-19', '2019-22', '2022-24'], '2024-26')
A = A[A.mid.isin(base_rec.keys())].reset_index(drop=True)
CYC = sorted(A.cyc.unique())
P_(f'ΔΕΙΓΜΑ: {len(A)} αφρικανικα ματς με γραμμες · ανα κυκλο {A.cyc.value_counts().sort_index().to_dict()} · ανα διοργανωση {A.comp.value_counts().to_dict()} · '
   f'με αξια ροστερ και στις 2: {int(A.has_v.sum())} ({A.groupby("cyc").has_v.mean().round(2).to_dict()})')
A_LIVE = 0.00491


def frame(rec, vmult=1.0):
    d = np.array([rec[m][0] for m in A.mid]); rh = np.array([rec[m][1] for m in A.mid]); ra = np.array([rec[m][2] for m in A.mid])
    return d + vmult * ELO_LN * A.lv.values, rh, ra


def Tof(diff, rh, ra, toff=0.0):
    return 0.29 + 0.33 * np.abs(diff) / 100 + 0.26 * A.KO.values + 0.49 * (np.abs(rh - ra) < 150) + 0.10 * (rh + ra) / 2 / 100 + toff


def dist_of(T, s, l3=0.0):
    return picks.gd_dist(max((T + s) / 2 - l3, .08), max((T - s) / 2 - l3, .08))


def ll_gd(diff, rh, ra, a=A_LIVE, toff=0.0, l3=0.0, idx=None):
    T = Tof(diff, rh, ra, toff); s = a * diff; gd = A.gd.values; o = np.zeros(len(A))
    for i in (range(len(A)) if idx is None else idx):
        o[i] = math.log(max(dist_of(T[i], s[i], l3).get(int(gd[i]), 1e-9), 1e-9))
    return o


def ll_tot(T):
    t = A.tot.values
    return np.array([-T[i] + t[i] * math.log(T[i]) - math.lgamma(t[i] + 1) for i in range(len(A))])


def by_cyc(v):
    return {c: float(v[(A.cyc == c).values].mean()) for c in CYC}


def accept(name, ll_old, ll_new):
    o, n = by_cyc(ll_old), by_cyc(ll_new); better = sum(1 for c in CYC if n[c] > o[c] + 1e-12)
    ok = better >= 4 and ll_new.mean() > ll_old.mean()
    P_(f'  → {name}: συνολο {ll_old.mean():.4f} → {ll_new.mean():.4f} · καλυτερο σε {better}/5 κυκλους · {"ΑΠΟΔΕΚΤΟ ✓" if ok else "ΑΠΟΡΡΙΠΤΕΤΑΙ ✗"} · '
       + ' '.join(f'{c}:{o[c]:.3f}→{n[c]:.3f}' for c in CYC))
    return ok


# ================= 4. ΔΙΑΓΝΩΣΗ ΒΑΣΗΣ =================
d0, rh0, ra0 = frame(base_rec)
T0_ = Tof(d0, rh0, ra0); s0 = A_LIVE * d0
sg = np.sign(s0); sg[sg == 0] = 1; gdf = A.gd.values * sg
pred1 = np.array([dist_of(T0_[i], s0[i]).get(int(sg[i]), 0) for i in range(len(A))]); pred3 = np.array([sum(p for k, p in dist_of(T0_[i], s0[i]).items() if k * sg[i] >= 3) for i in range(len(A))])
P_(f'\nΔΙΑΓΝΩΣΗ ΒΑΣΗΣ (φαβορι-σκοπια): μεσο GD {np.mean(np.abs(s0)):+.2f} vs {gdf.mean():+.2f} · νικη με 1 {pred1.mean() * 100:.1f} vs {(gdf == 1).mean() * 100:.1f}% · '
   f'3+ {pred3.mean() * 100:.1f} vs {(gdf >= 3).mean() * 100:.1f}% · συνολο γκολ μοντελο {T0_.mean():.2f} vs πραγματικο {A.tot.mean():.2f} · ισοπαλιες {np.mean([dist_of(T0_[i], s0[i]).get(0, 0) for i in range(len(A))]) * 100:.1f} vs {(A.gd == 0).mean() * 100:.1f}%')
P_('ανα κυκλο: ' + ' · '.join(f'{c}: GD {np.mean(np.abs(s0[(A.cyc == c).values])):+.2f}/{gdf[(A.cyc == c).values].mean():+.2f} γκολ {T0_[(A.cyc == c).values].mean():.2f}/{A.tot[A.cyc == c].mean():.2f}' for c in CYC))

# ================= 5. ΜΗΧΑΝΙΣΜΟΙ (LOSO ανα κυκλο) =================
P_('\n' + '=' * 110); P_('ΜΗΧΑΝΙΣΜΟΙ — παραμετρος καθε κυκλου απο τους ΑΛΛΟΥΣ 4 (log-lik αποτελεσματων), αποδοχη ≥4/5 κυκλοι + συνολο'); P_('=' * 110)
cur = dict(hfa=None, alt=110, vmult=1.0, a=None, toff=None, l3=None)
ll_cur = ll_gd(d0, rh0, ra0)


def loso_pick(grid, llfun):
    """για καθε κυκλο: η τιμη του grid με το καλυτερο μεσο log-lik στους ΑΛΛΟΥΣ κυκλους → log-lik ανα ματς με την επιλογη του κυκλου του."""
    lls = {g: llfun(g) for g in grid}; outv = np.zeros(len(A)); chosen = {}
    for c in CYC:
        tr = (A.cyc != c).values; te = (A.cyc == c).values
        g = max(grid, key=lambda z: lls[z][tr].mean()); chosen[c] = g; outv[te] = lls[g][te]
    gall = max(grid, key=lambda z: lls[z].mean())
    return outv, chosen, gall, lls


# Μ-1 εδρα CAF
REC = {}
def rec_for(hfa, alt):
    k = (hfa, alt)
    if k not in REC: REC[k] = walk(hfa_caf=hfa, alt=alt)
    return REC[k]
P_('Μ-1 ΕΔΡΑ ΑΦΡΙΚΗΣ (live 80)')
v1, ch1, g1, L1 = loso_pick([40, 60, 80, 100, 120, 140], lambda h: ll_gd(*frame(rec_for(h, 110))))
P_('  επιλογες LOSO: ' + ' · '.join(f'{c}:{v}' for c, v in ch1.items()) + f' · ολο το δειγμα: {g1}')
if accept('εδρα', ll_cur, v1): cur['hfa'] = g1; ll_cur = L1[g1]
# Μ-2 υψομετρο
P_('Μ-2 ΥΨΟΜΕΤΡΟ (live 110)')
hf = cur['hfa'] if cur['hfa'] is not None else 80
v2, ch2, g2, L2 = loso_pick([0, 55, 110, 165], lambda al: ll_gd(*frame(rec_for(hf if cur['hfa'] is not None else None, al))))
P_('  επιλογες LOSO: ' + ' · '.join(f'{c}:{v}' for c, v in ch2.items()) + f' · ολο: {g2}')
if accept('υψομετρο', ll_cur, v2): cur['alt'] = g2; ll_cur = L2[g2]
RB = rec_for(cur['hfa'], cur['alt'])
# Μ-3 βαρος αξιας
P_('Μ-3 ΒΑΡΟΣ ΑΞΙΑΣ ΡΟΣΤΕΡ (live ×1)')
v3, ch3, g3, L3 = loso_pick([0.0, 0.5, 1.0, 1.5], lambda vm: ll_gd(*frame(RB, vm)))
P_('  επιλογες LOSO: ' + ' · '.join(f'{c}:{v}' for c, v in ch3.items()) + f' · ολο: {g3}')
if accept('αξια', ll_cur, v3): cur['vmult'] = g3; ll_cur = L3[g3]
dB, rhB, raB = frame(RB, cur['vmult'])
# Μ-4 κλιση
P_('Μ-4 ΚΛΙΣΗ ΥΠΕΡΟΧΗΣ (live 0.491)')
v4 = np.zeros(len(A)); ch4 = {}
for c in CYC:
    tr = (A.cyc != c).values; te = np.where((A.cyc == c).values)[0]
    a_c = float(np.sum(dB[tr] * A.gd.values[tr]) / np.sum(dB[tr] ** 2)); ch4[c] = a_c
    v4[te] = ll_gd(dB, rhB, raB, a=a_c, idx=te)[te]
a_all = float(np.sum(dB * A.gd.values) / np.sum(dB ** 2))
P_('  επιλογες LOSO: ' + ' · '.join(f'{c}:{v * 100:.3f}' for c, v in ch4.items()) + f' · ολο: {a_all * 100:.3f}')
if accept('κλιση', ll_cur, v4): cur['a'] = a_all; ll_cur = ll_gd(dB, rhB, raB, a=a_all)
aC = cur['a'] or A_LIVE
# Μ-5 συνολο γκολ
P_('Μ-5 ΣΥΝΟΛΟ ΓΚΟΛ ΑΦΡΙΚΗΣ (μετατοπιση T)')
Tb = Tof(dB, rhB, raB); llT0 = ll_tot(Tb); v5 = np.zeros(len(A)); ch5 = {}
for c in CYC:
    tr = (A.cyc != c).values; te = (A.cyc == c).values; off = float((A.tot.values[tr] - Tb[tr]).mean()); ch5[c] = off
    v5[te] = ll_tot(np.maximum(Tb + off, .3))[te]
off_all = float((A.tot.values - Tb).mean())
P_('  επιλογες LOSO: ' + ' · '.join(f'{c}:{v:+.2f}' for c, v in ch5.items()) + f' · ολο: {off_all:+.2f} γκολ')
if accept('συνολο γκολ (log-lik συνολου)', llT0, v5):
    cur['toff'] = off_all; ll_cur = ll_gd(dB, rhB, raB, a=aC, toff=off_all)
tO = cur['toff'] or 0.0
# Μ-6 σχημα
P_('Μ-6 ΣΧΗΜΑ (κοινα γκολ λ3)')
v6, ch6, g6, L6 = loso_pick([0.0, 0.1, 0.2, 0.3, 0.4], lambda l3: ll_gd(dB, rhB, raB, a=aC, toff=tO, l3=l3))
P_('  επιλογες LOSO: ' + ' · '.join(f'{c}:{v}' for c, v in ch6.items()) + f' · ολο: {g6}')
if accept('σχημα', ll_cur, v6): cur['l3'] = g6; ll_cur = L6[g6]
l3C = cur['l3'] or 0.0
# Μ-7 αγκυρα
P_('Μ-7 ΑΓΚΥΡΑ ΑΓΟΡΑΣ (Μ2 = χωρις αξια, Μ3 = με αξια)')
ANC = {lam: walk(hfa_caf=cur['hfa'], alt=cur['alt'], lam=lam, close=CLOSE) for lam in (0.1, 0.2, 0.3, 0.5)}
v7, ch7, g7, L7 = loso_pick([0.1, 0.2, 0.3, 0.5], lambda lam: ll_gd(*frame(ANC[lam], cur['vmult']), a=aC, toff=tO, l3=l3C))
P_('  (Μ3) επιλογες LOSO: ' + ' · '.join(f'{c}:{v}' for c, v in ch7.items()) + f' · ολο: {g7}')
accept('αγκυρα+αξια (Μ3) vs Μ1', ll_cur, v7)
v7b, ch7b, g7b, L7b = loso_pick([0.1, 0.2, 0.3, 0.5], lambda lam: ll_gd(*frame(ANC[lam], 0.0), a=aC, toff=tO, l3=l3C))
P_('  (Μ2) επιλογες LOSO: ' + ' · '.join(f'{c}:{v}' for c, v in ch7b.items()) + f' · ολο: {g7b}')
accept('αγκυρα χωρις αξια (Μ2) vs Μ1', ll_cur, v7b)
P_(f'\nΤΕΛΙΚΕΣ ΠΑΡΑΜΕΤΡΟΙ ΑΦΡΙΚΗΣ: εδρα {cur["hfa"] if cur["hfa"] is not None else "80 (live)"} · υψομετρο {cur["alt"]} · αξια ×{cur["vmult"]} · κλιση {aC * 100:.3f} · '
   f'συνολο {tO:+.2f} · λ3 {l3C} · αγκυρα Μ2 λ={g7b} / Μ3 λ={g7}   [{(time.time() - T0) / 60:.1f} λεπτα]')

# ================= 6. ΣΤΟΙΧΗΜΑΤΑ (72ω + closing) =================
def ev_ah(dist, side, ud, odds, planB):
    parts = [ud] if (ud * 4) % 2 == 0 else [ud - .25, ud + .25]
    if planB and ud > 0 and abs(ud % 1 - .25) < 1e-9: parts = [ud]
    e = 0.0
    for L in parts:
        pw, pp = picks.p_cover(dist, side, L); e += (pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp)) / len(parts)
    return e
def pk(T, k):
    return math.exp(-T) * T ** k / math.factorial(k)
def ev_over(T, line, odds):
    q = round(line * 4) / 4
    if abs(q * 2 - round(q * 2)) > 1e-9: return 0.5 * ev_over(T, q - .25, odds) + 0.5 * ev_over(T, q + .25, odds)
    pw = 1 - sum(pk(T, k) for k in range(int(math.floor(q)) + 1)); pp = pk(T, int(q)) if float(q).is_integer() else 0.0
    return pw * (odds - 1) - (1 - pw - pp)
def settle_over(tot, line, odds):
    q = round(line * 4) / 4
    if abs(q * 2 - round(q * 2)) > 1e-9: return 0.5 * settle_over(tot, q - .25, odds) + 0.5 * settle_over(tot, q + .25, odds)
    return odds - 1 if tot > q else (0.0 if abs(tot - q) < 1e-9 else -1.0)
VERS = {}
VERS['Μ1 βαση'] = dict(frame=(d0, rh0, ra0), a=A_LIVE, toff=0.0, l3=0.0)
VERS['Μ1 διορθ.'] = dict(frame=(dB, rhB, raB), a=aC, toff=tO, l3=l3C)
VERS['Μ2 αγκυρα'] = dict(frame=frame(ANC[g7b], 0.0), a=aC, toff=tO, l3=l3C)
VERS['Μ3 αγκ+αξια'] = dict(frame=frame(ANC[g7], cur['vmult']), a=aC, toff=tO, l3=l3C)
DEEP_A = {c: ch4.get(c, aC) for c in CYC}
bets = []
for vn, V in VERS.items():
    dd, rr_h, rr_a = V['frame']; T = Tof(dd, rr_h, rr_a, V['toff']); s = V['a'] * dd
    close_f = np.abs(rr_h - rr_a) < 150
    for i, r in enumerate(A.itertuples()):
        dist = dist_of(T[i], s[i], V['l3'])
        for cid, book in (('3', 'Crown'), ('31', 'SBOBET')):
            rec = ROWS.get((r.mid, cid))
            if rec:
                for win, cand in (('72ω', [z for z in rec if z[0] <= 72]), ('closing', rec[-1:])):
                    for planB in (False, True):
                        for h, L, oh, oa in cand:
                            q = None
                            for side, ud, odds in ((1, L, oh), (-1, -L, oa)):
                                e = ev_ah(dist, side, ud, odds, planB)
                                if 1.70 <= odds <= 2.10 and e >= .10 and abs(ud) >= .5: q = (side, ud, odds, e); break
                            if q:
                                side, ud, odds, e = q
                                bets.append(dict(ver=vn, planB=planB, mid=r.mid, cyc=r.cyc, book=book, win=win, mkt='AH', side=side, line=ud, odds=odds, edge=e,
                                                 seg=('dog' if ud > 0 else ('βαθυ φαβ' if ud <= -2 + 1e-9 else 'φαβ')), pnl=picks.settle(int(r.gd), side, ud, odds)))
                                break
            orec = OU.get((r.mid, cid))
            if orec and (close_f[i] or r.KO):
                for win, cand in (('72ω', [z for z in orec if z[0] <= 72]), ('closing', orec[-1:])):
                    for h, L, oo, uu in cand:
                        e = ev_over(T[i], L, oo)
                        if e >= .08:
                            for planB in (False, True):
                                bets.append(dict(ver=vn, planB=planB, mid=r.mid, cyc=r.cyc, book=book, win=win, mkt='OVER', side=0, line=L, odds=oo, edge=e, seg='over',
                                                 pnl=settle_over(int(r.tot), L, oo)))
                            break
B = pd.DataFrame(bets)
def cons(b):
    rows = []
    for (bk, win, pb, mid, mkt, side), g in b.groupby(['book', 'win', 'planB', 'mid', 'mkt', 'side']):
        if g.ver.nunique() >= 2: rows.append(g.iloc[0].to_dict() | dict(ver='ΣΥΝΑΙΝΕΣΗ'))
    return pd.DataFrame(rows)
C3 = cons(B[B.ver.isin(['Μ1 διορθ.', 'Μ2 αγκυρα', 'Μ3 αγκ+αξια'])])
ALL = pd.concat([B, C3], ignore_index=True)
def cell(g):
    if len(g) == 0: return None
    s_ = g.groupby('cyc').pnl.mean(); return dict(n=len(g), roi=g.pnl.mean() * 100, pos=int((s_ > 0).sum()), ns=s_.size, u=g.pnl.sum())
def line_(g):
    c, s_ = cell(g[g.book == 'Crown']), cell(g[g.book == 'SBOBET'])
    if not c or not s_: return '—'
    avg = (c['roi'] + s_['roi']) / 2; warn = ' ⚠ διαφωνουν' if (c['roi'] > 0) != (s_['roi'] > 0) else ''
    return f"{avg:+6.1f}%  (n~{(c['n'] + s_['n']) // 2}, θετικοι κυκλοι {c['pos']}/{c['ns']}, μοναδες ~{(c['u'] + s_['u']) / 2:+.1f}){warn}"
for win in ('72ω', 'closing'):
    P_('\n' + '=' * 110); P_(f'ΣΤΟΙΧΗΜΑΤΑ {win} — ενα ROI = μεσος Crown/SBOBET'); P_('=' * 110)
    for seg, fl in (('ΟΛΑ (AH+OVER)', lambda x: x.mkt.notna()), ('handicap ολα', lambda x: x.mkt == 'AH'), ('  dogs', lambda x: x.seg == 'dog'),
                    ('  φαβορι ως −1.75', lambda x: x.seg == 'φαβ'), ('  βαθια φαβορι ≤−2', lambda x: x.seg == 'βαθυ φαβ'), ('over (κοντινα/KO)', lambda x: x.mkt == 'OVER')):
        P_(f'--- {seg} ---')
        for vn in list(VERS) + ['ΣΥΝΑΙΝΕΣΗ']:
            for pb in (False, True):
                if pb and seg in ('over (κοντινα/KO)',): continue
                g = ALL[(ALL.win == win) & (ALL.ver == vn) & (ALL.planB == pb)]; g = g[fl(g)]
                P_(f"  {vn:12s}{' +Σχ.Β' if pb else '       '}  {line_(g)}")
P_('\n' + '=' * 110); P_('ΚΡΙΤΗΡΙΟ LIVE (72ω, ΟΛΑ AH+OVER, χωρις Σχ.Β): ROI > 0 ΚΑΙ ≥3/5 κυκλοι ΚΑΙ και στα 2 βιβλια > 0'); P_('=' * 110)
for vn in list(VERS) + ['ΣΥΝΑΙΝΕΣΗ']:
    g = ALL[(ALL.win == '72ω') & (ALL.ver == vn) & (~ALL.planB)]
    c, s_ = cell(g[g.book == 'Crown']), cell(g[g.book == 'SBOBET'])
    if c and s_:
        ok = c['roi'] > 0 and s_['roi'] > 0 and c['pos'] >= 3 and s_['pos'] >= 3
        P_(f"  {vn:12s} Crown {c['roi']:+.1f}% {c['pos']}/{c['ns']} · SBOBET {s_['roi']:+.1f}% {s_['pos']}/{s_['ns']} → {'ΠΕΡΝΑ' if ok else '—'}")
    for mk in ('AH', 'OVER'):
        gm = g[g.mkt == mk]; c, s_ = cell(gm[gm.book == 'Crown']), cell(gm[gm.book == 'SBOBET'])
        if c and s_:
            ok = c['roi'] > 0 and s_['roi'] > 0 and c['pos'] >= 3 and s_['pos'] >= 3
            P_(f"     {mk:5s} Crown {c['roi']:+.1f}% {c['pos']}/{c['ns']} · SBOBET {s_['roi']:+.1f}% {s_['pos']}/{s_['ns']} → {'ΠΕΡΝΑ' if ok else '—'}")
ALL.to_csv('intl_africa_lab_bets.csv', index=False)
json.dump(dict(params={k: (None if v is None else float(v)) for k, v in cur.items()}, a=aC, toff=tO, l3=l3C, anchor_M2=g7b, anchor_M3=g7),
          open('intl_africa_lab_params.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
P_(f'\nΤΕΛΟΣ [{(time.time() - T0) / 60:.1f} λεπτα]')
open('intl_africa_lab_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
