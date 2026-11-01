"""
intl_africa_window_test.py — ΤΕΣΤ ΤΩΝ ΔΥΟ ΔΙΟΡΘΩΣΕΩΝ HANDICAP ΣΤΗΝ ΑΦΡΙΚΗ (25/9/2026, εντολη Στελιου «οτι αλλαγη καναμε τεσταρε τη και στην Αφρικη»).
Διορθωσεις (live στις εθνικες UEFA απο 25/9): (Β) dog +x.25 με τον παλιο τροπο · (Γ) σωστη υπεροχη για φαβορι −2 και βαθυτερα.

ΔΕΙΓΜΑ: ολα τα αφρικανικα αγωνιστικα με ιστορικο γραμμων Nowgoal (Crown 3 / SBOBET 31, pre-match κινησεις με χρονοσφραγιδα):
  AFCONQ + AFCON (Nowgoal c93: 2017-2019*, 2019-2022*, 2022-2024, 2024-2026) · WCQ CAF (c651: 2015-2017*, 2019-2021, 2023-2025) — *κατεβηκαν 25/9.
  Αντιστοιχιση με intl_matches.csv: ονοματα (nowgoal_intl_team_names + alias) + ημερομηνια ±36ω (Nowgoal = UTC+8), και ανεστραμμενα.
ΜΟΝΤΕΛΟ = το LIVE της Αφρικης (intl_afconq_shadow_v): Μ1 μονο (χωρις αγκυρα CAF) — diff = H3 walk-forward (intl_preds_H) + αξια ροστερ
  ELO_LN·ln(V_full_h/V_full_a) (V_full walk-forward, intl_callup_test_events)· T = 0.29 + 0.33·|diff|/100 + 0.26·[KO] + 0.49·[|ΔElo|<150] + 0.10·μεσο Elo/100
  (επιπεδα Elo walk-forward E0 οπως intl_afconq_eval)· υπεροχη a·diff, a = κλιση gd~diff σε ΟΛΑ τα αγωνιστικα 2020+ (οπως το live).
ΚΑΝΟΝΕΣ (live): AH |γραμμη| ≥0.5, τιμη 1.70-2.10, edge ≥10% (με 3% μειωση κερδους)· bet στην ΠΡΩΤΗ κινηση των τελευταιων 72ω που περναει.
ΠΡΟ-ΔΗΛΩΣΗ (πριν τρεξει, ΜΙΑ εκτελεση):
  Εκδοχες: 0 = σημερινη (σωστα τεταρτα) · Β = dog +x.25 παλιος τροπος · Γ = φαβορι ≤−2 με κλιση a_deep (fit LOSO ανα κυκλο στα αφρικανικα αγωνιστικα
  με το ιδιο diff) · Β+Γ.
  ΠΕΡΝΑ η Β αν: ROI ολων των AH οχι χειροτερο ΚΑΙ ROI dogs καλυτερο, στον μεσο ορο Crown/SBOBET ΚΑΙ σε καθε βιβλιο.
  ΠΕΡΝΑ η Γ αν: ROI ολων οχι χειροτερο ΚΑΙ ROI βαθιων φαβορι (≤−2) καλυτερο, στον μεσο ορο ΚΑΙ σε καθε βιβλιο.
  Αναφορα: ανα κυκλο, closing για συγκριση, διαγνωση κατανομης (νικη με 1 / με 3+) οπως στις UEFA.
Εξοδος: intl_africa_window_test_out.txt
"""
import sys, json, math, ast
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
import picks, intl_pricing
out = []
def P_(s=''):
    print(s, flush=True); out.append(str(s))

M = pd.read_csv('intl_matches.csv', dtype={'mid': str, 'season': str}, parse_dates=['date'])
import intl_dedupe
M = intl_dedupe.dedupe(M, where='africa_window')
AFR = M[M.comp.isin(['AFCONQ', 'AFCON', 'WCQ_CAF'])].copy()
NAMES = json.load(open('nowgoal_intl_team_names.json', encoding='utf-8'))
ALIAS = {'Democratic Rep Congo': 'DR Congo', 'Republic of the Congo': 'Congo', 'Guinea Bissau': 'Guinea-Bissau', "Cote d'Ivoire": 'Ivory Coast',
         "Côte d'Ivoire": 'Ivory Coast', 'Cabo Verde': 'Cape Verde', 'Swaziland': 'Eswatini', 'Sao Tome': 'Sao Tome and Principe', 'Sao Tome & Principe': 'Sao Tome and Principe',
         'Central Africa': 'Central African Republic', 'Equatorial Guinea': 'Equatorial Guinea', 'Gambia': 'Gambia', 'Tanzania': 'Tanzania'}
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

# ---- γραμμες Nowgoal ----
ROWS = {}; n_ng = 0; unm = 0
AFI = {}
for r in AFR.itertuples():
    AFI.setdefault((int(r.hid), int(r.aid)), []).append((r.date, r.mid))
for f in ('intl_ng_hist_afconq.json', 'intl_ng_hist_wcqcaf.json'):
    for ng, v in json.load(open(f, encoding='utf-8')).items():
        n_ng += 1; h, a = tid(v['hid']), tid(v['aid']); dt = pd.to_datetime(v['dt']) - pd.Timedelta(hours=8); mid = None; flip = False
        for (x, y, fl) in ((h, a, False), (a, h, True)):
            c = [m for d, m in AFI.get((x, y), []) if abs((d - dt).total_seconds()) <= 36 * 3600] if (x and y) else []
            if c:
                mid, flip = c[0], fl; break
        if mid is None:
            unm += 1; continue
        books = v['books'] if isinstance(v['books'], dict) else ast.literal_eval(v['books'])
        ko = AFR.set_index('mid').date[mid].timestamp() if False else pd.Timestamp(AFR[AFR.mid == mid].date.iloc[0]).tz_localize('UTC').timestamp()
        for cid in ('3', '31'):
            b = books.get(cid) or {}; rec = []
            for x in (b.get('ah') or []):
                try:
                    if x[0] and x[0] < ko and x[1] not in (None, '') and x[2] not in (None, '', '0') and x[3] not in (None, '', '0'):
                        L, oh, oa = -line_of(x[1]), hk(x[2]), hk(x[3])
                        if flip: L, oh, oa = -L, oa, oh
                        rec.append(((ko - x[0]) / 3600, L, oh, oa))
                except Exception:
                    pass
            if rec:
                ROWS[(mid, cid)] = sorted(rec, key=lambda z: -z[0])
P_(f'Nowgoal εγγραφες {n_ng} · αταιριαστες {unm} · ματς με γραμμες Crown {sum(1 for k in ROWS if k[1] == "3")} / SBOBET {sum(1 for k in ROWS if k[1] == "31")}')

# ---- μοντελο (live Αφρικης) ----
PH = pd.read_csv('intl_preds_H.csv', dtype={'mid': str, 'season': str})
EV = pd.read_csv('intl_callup_test_events.csv', dtype={'mid': str})[['mid', 'vf_h', 'vf_a']]
VF = json.load(open('intl_team_vfull.json', encoding='utf-8')); ELO_LN = VF['elo_per_ln']
_src = open('intl_rating.py', encoding='utf-8').read(); n4 = {}
exec(_src[:_src.index('def run2(mode)')].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), n4)
SEED, K_TYPE, HFA0, MALL = n4['SEED'], n4['K_TYPE'], n4['HFA'], n4['M']
def margin_mult(gd):
    gd = abs(gd); return 1.0 if gd <= 1 else (1.5 if gd == 2 else 1.75 + 0.125 * (gd - 3))
R = dict(SEED); lvl = {}
for r in MALL.itertuples():
    rh = R.get(r.hid, 1500.0); ra = R.get(r.aid, 1500.0); d = rh + (0 if r.neutral else HFA0) - ra; lvl[r.mid] = (rh, ra)
    E = 1 / (1 + 10 ** (-d / 400)); gd = int(r.hs) - int(r.ag); S = 1.0 if gd > 0 else (0.5 if gd == 0 else 0.0); k = K_TYPE.get(r.ctype, 30) * margin_mult(gd)
    R[r.hid] = rh + k * (S - E); R[r.aid] = ra - k * (S - E)
C0 = PH[PH.ctype.isin(['nl', 'qual', 'tourn'])].copy(); C0['date'] = pd.to_datetime(C0.date); C0 = C0[C0.date >= '2020-07-01']
A_LIVE = float(np.sum(C0['diff'] * C0.gd) / np.sum(C0['diff'] ** 2))
D = AFR.merge(PH[['mid', 'diff']], on='mid').merge(EV, on='mid', how='left')
D['vadj'] = np.where(D.vf_h.notna() & D.vf_a.notna() & (D.vf_h > 0) & (D.vf_a > 0), ELO_LN * np.log(D.vf_h / D.vf_a), 0.0)
D['d'] = D['diff'] + D.vadj; D['gd'] = D.hs - D['as']
D['R_h'] = D.mid.map(lambda m: lvl.get(m, (np.nan, np.nan))[0]); D['R_a'] = D.mid.map(lambda m: lvl.get(m, (np.nan, np.nan))[1])
D['KO'] = (D.ctype == 'tourn') & ~D.mid.isin([])      # (ανα γυρο δεν ξερουμε εδω — KO = τελικη φαση: αναφορα)
KO_R = {}
for f in ('data_AFCON_2019.json', 'data_AFCON_2021.json', 'data_AFCON_2023.json', 'data_AFCON_2025.json'):
    try:
        for mid, v in json.load(open(f, encoding='utf-8')).items():
            KO_R[str(mid)] = not str(v.get('round')).isdigit()
    except Exception:
        pass
D['KO'] = D.mid.map(lambda m: KO_R.get(m, False))
D['Tg'] = 0.29 + 0.33 * D.d.abs() / 100 + 0.26 * D.KO.astype(float) + 0.49 * ((D.R_h - D.R_a).abs() < 150).astype(float) + 0.10 * (D.R_h + D.R_a) / 2 / 100
D['cyc'] = np.where(D.date < '2017-12-31', '2015-17', np.where(D.date < '2019-08-01', '2017-19', np.where(D.date < '2022-03-31', '2019-22', np.where(D.date < '2024-03-01', '2022-24', '2024-26'))))
D = D[D.mid.isin({k[0] for k in ROWS}) & D.d.notna() & D.Tg.notna() & D.gd.notna()].copy()
P_(f'δειγμα: {len(D)} αφρικανικα ματς με γραμμες και rating · ανα κυκλο {D.cyc.value_counts().sort_index().to_dict()} · ανα διοργανωση {D.comp.value_counts().to_dict()}')
P_(f'κλιση live a = {A_LIVE * 100:.3f} γκολ/100 Elo (ολα τα αγωνιστικα 2020+)')
CYC = sorted(D.cyc.unique())
A_DEEP = {c: float(np.sum(D[D.cyc != c].d * D[D.cyc != c].gd) / np.sum(D[D.cyc != c].d ** 2)) for c in CYC}
P_('κλιση a_deep LOSO (αφρικανικα, αλλοι κυκλοι): ' + ' · '.join(f'{c}: {v * 100:.3f}' for c, v in A_DEEP.items())
   + f' · ολο το δειγμα {float(np.sum(D.d * D.gd) / np.sum(D.d ** 2)) * 100:.3f}')

# ---- διαγνωση κατανομης (φαβορι-σκοπια) ----
rows = []
for r in D.itertuples():
    s = A_LIVE * r.d; dist = picks.gd_dist(max((r.Tg + s) / 2, .15), max((r.Tg - s) / 2, .15)); sg = 1 if s >= 0 else -1
    f = {k * sg: p for k, p in dist.items()}; g = int(r.gd) * sg
    rows.append(dict(s=abs(s), gd=g, mp=sum(k * p for k, p in f.items()), p1=f.get(1, 0), p3=sum(p for k, p in f.items() if k >= 3)))
Q = pd.DataFrame(rows)
P_(f'ΔΙΑΓΝΩΣΗ (φαβορι-σκοπια, προβλ. vs πραγμ.): μεσο GD {Q.mp.mean():+.2f} vs {Q.gd.mean():+.2f} · νικη με 1 {Q.p1.mean() * 100:.1f} vs {(Q.gd == 1).mean() * 100:.1f}% · '
   f'με 3+ {Q.p3.mean() * 100:.1f} vs {(Q.gd >= 3).mean() * 100:.1f}% · μεγαλα φαβορι (υπεροχη ≥1.5, n={int((Q.s >= 1.5).sum())}): 3+ {Q[Q.s >= 1.5].p3.mean() * 100:.1f} vs {(Q[Q.s >= 1.5].gd >= 3).mean() * 100:.1f}%')

# ---- bets ----
def ev(dist, side, ud, odds, planB):
    parts = [ud] if (ud * 4) % 2 == 0 else [ud - .25, ud + .25]
    if planB and ud > 0 and abs(ud % 1 - .25) < 1e-9:
        parts = [ud]
    e = 0.0
    for L in parts:
        pw, pp = picks.p_cover(dist, side, L); e += (pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp)) / len(parts)
    return e
VAR = {'0 σημερα': (False, False), 'Β': (True, False), 'Γ': (False, True), 'Β+Γ': (True, True)}
bets = []
for r in D.itertuples():
    s = A_LIVE * r.d; dist = picks.gd_dist(max((r.Tg + s) / 2, .15), max((r.Tg - s) / 2, .15))
    sd = A_DEEP[r.cyc] * r.d; ddist = picks.gd_dist(max((r.Tg + sd) / 2, .15), max((r.Tg - sd) / 2, .15))
    for cid, book in (('3', 'Crown'), ('31', 'SBOBET')):
        rec = ROWS.get((r.mid, cid))
        if not rec:
            continue
        for win, cand in (('72ω', [z for z in rec if z[0] <= 72]), ('closing', rec[-1:])):
            for vname, (pb, deep) in VAR.items():
                for h, L, oh, oa in cand:
                    q = None
                    for side, ud, odds in ((1, L, oh), (-1, -L, oa)):
                        dx = ddist if (deep and ud <= -2 + 1e-9) else dist
                        e = ev(dx, side, ud, odds, pb)
                        if 1.70 <= odds <= 2.10 and e >= .10 and abs(ud) >= .5:
                            q = (side, ud, odds, e); break
                    if q:
                        side, ud, odds, e = q
                        bets.append(dict(mid=r.mid, cyc=r.cyc, comp=r.comp, book=book, win=win, var=vname, side=side, line=ud, odds=odds, edge=e,
                                         seg=('dog' if ud > 0 else ('βαθυ φαβ' if ud <= -2 + 1e-9 else 'φαβ')), pnl=picks.settle(int(r.gd), side, ud, odds)))
                        break
B = pd.DataFrame(bets)
def st(g):
    if len(g) == 0:
        return dict(n=0, roi=np.nan, pos='—', u=0.0)
    s = g.groupby('cyc').pnl.mean(); return dict(n=len(g), roi=g.pnl.mean() * 100, pos=f'{int((s > 0).sum())}/{s.size}', u=g.pnl.sum())
def fmt(d):
    return '—' if d['n'] == 0 else f"n{d['n']:3d} {d['roi']:+6.1f}% {d['pos']} {d['u']:+5.1f}u"
for win in ('72ω', 'closing'):
    P_(f'\n======== {win} — Μ1 Αφρικης (μεσος Crown/SBOBET ROI · ανα βιβλιο n/ROI/θετικοι κυκλοι/μοναδες) ========')
    for seg, fl in (('ΟΛΑ AH', lambda x: x.seg.notna()), ('dogs', lambda x: x.seg == 'dog'), ('φαβορι (ως −1.75)', lambda x: x.seg == 'φαβ'), ('βαθια φαβορι ≤−2', lambda x: x.seg == 'βαθυ φαβ'),
                    ('   από αυτα dog +x.25', lambda x: (x.seg == 'dog') & ((x.line % 1).round(2) == 0.25))):
        P_(f'--- {seg} ---')
        for v in VAR:
            g = B[(B.win == win) & (B['var'] == v)]; g = g[fl(g)]
            c, s_ = st(g[g.book == 'Crown']), st(g[g.book == 'SBOBET'])
            avg = np.nanmean([c['roi'], s_['roi']]) if (c['n'] or s_['n']) else np.nan
            P_(f"  {v:9s} μεσος {avg:+6.1f}%  |  Crown {fmt(c)}  |  SBOBET {fmt(s_)}")
P_('\n======== ΚΡΙΤΗΡΙΑ (72ω) ========')
def roi(v, bk, fl):
    g = B[(B.win == '72ω') & (B['var'] == v) & (B.book == bk)]; g = g[fl(g)]; return g.pnl.mean() * 100 if len(g) else np.nan
for v, segname, fl in (('Β', 'dogs', lambda x: x.seg == 'dog'), ('Γ', 'βαθια φαβορι', lambda x: x.seg == 'βαθυ φαβ')):
    checks = []
    for bk in ('Crown', 'SBOBET'):
        a0, a1 = roi('0 σημερα', bk, lambda x: x.seg.notna()), roi(v, bk, lambda x: x.seg.notna())
        s0, s1 = roi('0 σημερα', bk, fl), roi(v, bk, fl)
        checks.append((bk, a1 >= a0 - 1e-9, s1 > s0 if not (np.isnan(s0) and np.isnan(s1)) else False, a0, a1, s0, s1))
    avg_ok = np.mean([c[3] for c in checks]) <= np.mean([c[4] for c in checks]) + 1e-9 and np.nanmean([c[5] for c in checks]) < np.nanmean([c[6] for c in checks])
    ok = avg_ok and all(c[1] and c[2] for c in checks)
    P_(f'  {v}: ' + ' · '.join(f"{c[0]}: ολα {c[3]:+.1f}→{c[4]:+.1f} {'✓' if c[1] else '✗'} · {segname} {c[5]:+.1f}→{c[6]:+.1f} {'✓' if c[2] else '✗'}" for c in checks)
       + f'  →  {"ΠΕΡΝΑ" if ok else "ΔΕΝ ΠΕΡΝΑ"}')
B.to_csv('intl_africa_window_test_bets.csv', index=False)
open('intl_africa_window_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
