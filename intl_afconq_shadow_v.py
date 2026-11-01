"""
intl_afconq_shadow_v.py — ΑΝΤΙΓΡΑΦΟ του intl_afconq_shadow.py (24/9/2026) για το ΒΗΜΑ 5 του intl_afconq_value_test.py:
ξανατρεχει τη σκια του παραθυρου 24/9-2/10/2026 με το ΕΝΗΜΕΡΩΜΕΝΟ intl_team_vfull.json (αξιες CAF συμπληρωμενες).
ΜΟΝΕΣ διαφορες απο το πρωτοτυπο (ολα μεσω env, προεπιλογες = πρωτοτυπο):
  AFQ_HFA   (προεπιλογη 80)  : HFA CAF στις προβλεψεις (αλλαζει ΜΟΝΟ αν περασε το ΒΗΜΑ 3)
  AFQ_TADD  (προεπιλογη 0.0) : προσθετος ορος στο T (c_CAF, ΜΟΝΟ αν περασε το ΒΗΜΑ 4)
  AFQ_VFULL (προεπιλογη intl_team_vfull.json) : αρχειο V_full · AFQ_SUFFIX (προεπιλογη '') : καταληξη αρχειων εξοδου (για το «πριν»)
Εξοδος: intl_afconq_shadow_2627.csv, intl_afconq_overs_2627.csv (ιδια ονοματα — το «πριν» σωθηκε ως intl_afconq_shadow_2627_before_values.csv).
"""
import sys, json, math, os
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
import picks
_src = open('intl_rating.py', encoding='utf-8').read(); _ns = {'np': np}
exec(_src[_src.index('def sig(x):'):_src.index("EVAL_SEASONS = ")], _ns); fit_ol, probs = _ns['fit_ol'], _ns['probs']
HFA = float(os.environ.get('AFQ_HFA', '80')); ALT = 110; TADD = float(os.environ.get('AFQ_TADD', '0'))
R = pd.read_csv('intl_ratings_h.csv', index_col=0)['R']
CFG = json.load(open('intl_hfa_config.json', encoding='utf-8')); ELEV = {int(k): v for k, v in CFG['home_elev'].items()}
VF = json.load(open(os.environ.get('AFQ_VFULL', 'intl_team_vfull.json'), encoding='utf-8')); SUF = os.environ.get('AFQ_SUFFIX', ''); VFULL = {int(k): v for k, v in VF['vfull'].items()}; ELO_LN = VF['elo_per_ln']
PH = pd.read_csv('intl_preds_H.csv', dtype={'season': str, 'mid': str}, parse_dates=['date'])
Cc = PH[PH.ctype.isin(['nl', 'qual', 'tourn']) & (PH.date >= '2020-07-01')].copy(); Cc['y'] = np.where(Cc.gd > 0, 2, np.where(Cc.gd == 0, 1, 0))
ol = fit_ol(Cc['diff'].values, Cc.y.values); a = float(np.sum(Cc['diff'] * Cc.gd) / np.sum(Cc['diff'] ** 2))
print(f'ordered logit (ολα αγωνιστικα 2020+, n={len(Cc)}): beta {ol[0]:.4f} c1 {ol[1]:.3f} c2 {ol[2]:.3f} · a = {a*100:.3f} γκολ/100 Elo · HFA {HFA:g} (CAF) · ALT {ALT} · T+{TADD:+.2f} · V_full ομαδες {len(VFULL)} (ELO_LN {ELO_LN:.1f})')
NAMES = json.load(open('nowgoal_intl_team_names.json', encoding='utf-8')); NG = json.load(open('intl_ng_now_afconq.json', encoding='utf-8'))
M = pd.read_csv('intl_matches.csv', dtype={'mid': str}); N2ID = {}
import intl_dedupe
M = intl_dedupe.dedupe(M, where='intl_afconq_shadow_v')   # 25/9: κλειδι ασφαλειας — διπλα ματς δεν μετρανε
for r in M.itertuples(): N2ID[str(r.hn)] = int(r.hid); N2ID[str(r.an)] = int(r.aid)
ALIAS = {'Democratic Rep Congo': 'DR Congo', 'Republic of the Congo': 'Congo', 'Guinea Bissau': 'Guinea-Bissau', "Cote d'Ivoire": 'Ivory Coast', 'Cabo Verde': 'Cape Verde', 'Swaziland': 'Eswatini', 'Sao Tome': 'Sao Tome and Principe'}
def team(ngid):
    nm = NAMES.get(str(ngid), f'ng{ngid}'); nm = ALIAS.get(nm, nm); return nm, N2ID.get(nm)
def hk(x):
    v = float(x); return v + 1 if v < 1.5 else v
def line_of(s):
    if s in (None, ''): return np.nan
    s = str(s)
    if '/' in s:
        a_, b_ = s.split('/'); return (float(a_) + float(b_)) / 2
    return float(s)
import intl_pricing   # 25/9 (Στελιος): σωστο edge over (push/μισα)
def p_over(T, line):
    parts = [line] if (line * 4) % 2 == 0 else [line - 0.25, line + 0.25]; pw = pp = 0.0
    pk = [math.exp(-T) * T ** k / math.factorial(k) for k in range(30)]
    for L in parts:
        for k, p in enumerate(pk):
            m = k - L
            if m > 0.01: pw += p / len(parts)
            elif abs(m) < 0.01: pp += p / len(parts)
    return pw, pp
import datetime as _dt; _d0 = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=1)).strftime('%Y-%m-%d'); _d1 = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(days=10)).strftime('%Y-%m-%d')
W = sorted([(k, v) for k, v in NG.items() if _d0 <= v['dt'][:10] <= _d1], key=lambda kv: kv[1]['dt'])   # 25/9: παραθυρο τρεχον −1/+10 ημερες (ηταν σταθερο 24/9-2/10)
print(f'ματς παραθυρου (Nowgoal 24/9-2/10): {len(W)}')
rows = []; orows = []; n_v = 0; n_nor = 0
for ng, o in W:
    hn, hid = team(o['hid']); an, aid = team(o['aid']); utc = (pd.to_datetime(o['dt']) - pd.Timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')
    rec = dict(comp='AFCONQ', utc=utc, ng=ng, ματς=f'{hn} - {an}')
    if hid is None or aid is None or hid not in R.index or aid not in R.index:
        n_nor += 1; rec['diff'] = np.nan; rec['σημ'] = 'χωρις rating'; rows.append(rec); continue
    rh, ra = float(R[hid]), float(R[aid]); vh, va = VFULL.get(hid), VFULL.get(aid); vadj = ELO_LN * math.log(vh / va) if (vh and va) else 0.0; n_v += bool(vh and va)
    alt = ALT if (ELEV.get(hid, 0) > 1500 and ELEV.get(aid, 0) < 1000) else 0
    diff = rh + HFA + alt - ra + vadj; ph, pdr, pa = probs(np.array([diff]), ol)[0]; ph60 = probs(np.array([diff - (HFA - 60)]), ol)[0][0]
    gap = abs(rh - ra); close = gap < 150; T = 0.29 + 0.33 * abs(diff) / 100 + 0.49 * close + 0.10 * (rh + ra) / 2 / 100 + TADD; s = a * diff; lh = max((T + s) / 2, .15); la = max((T - s) / 2, .15)
    dist = picks.gd_dist(lh, la)
    rec.update(R_h=round(rh), R_a=round(ra), υψομ=alt, vadj=round(vadj), diff=int(round(diff)), λ=f'{lh:.2f}-{la:.2f}', p1X2=f'{ph*100:.0f}/{pdr*100:.0f}/{pa*100:.0f}', P1_HFA60=f'{ph60*100:.0f}')
    fair = {}
    for line in (-1.5, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.5):
        fair[line] = intl_pricing.ah_fair(dist, 1, line)
    best = min(fair.items(), key=lambda kv: abs((kv[1] or 9) - 2.0)); rec['fair_line'] = f'{best[0]:+.2f} @{best[1]}'
    ia = line_of(o.get('init_ah')); rec['αρχικη_AH'] = (f'{-ia:+.2f}' if pd.notna(ia) else '—')
    pick = ''
    for cid, lab in (('3', 'Crown'), ('31', 'SBOBET')):
        b = (o['books'].get(cid) or {}); ah = b.get('ah') or []
        if not ah: rec[lab] = '—'
        else:
            try:
                mt, g, u, d, _ = ah[-1]; line = -line_of(g); oh = hk(u); oa = hk(d); rec[lab] = f'{line:+.2f} {oh:.2f}/{oa:.2f}'
                for side, ud, odds in ((1, line, oh), (-1, -line, oa)):
                    e = intl_pricing.ah_ev(dist, side, ud, odds, picks.MARGIN); fo = intl_pricing.ah_fair(dist, side, ud) or 99
                    tag = 'H' if side == 1 else 'A'; rec[f'{lab}_fair_{tag}'] = round(fo, 2); rec[f'{lab}_edge_{tag}'] = f'{e*100:+.0f}%'
                    if not pick and 1.70 <= odds <= 2.10 and e >= .10:
                        if ud >= 0.5: pick = f"DOG {'1' if side==1 else '2'} {ud:+.2f} @{odds:.2f} ({lab}, {e*100:+.0f}%)"
                        elif ud <= -0.5: pick = f"FAV {'1' if side==1 else '2'} {ud:+.2f} @{odds:.2f} ({lab}, {e*100:+.0f}%)"
            except Exception: rec[lab] = '—'
        op = b.get('op') or []
        if op:
            try:
                _, gx, g1, g2, _ = op[-1]; o1, ox, o2 = float(g1), float(gx), float(g2); rec[f'{lab}_1X2'] = f'{o1:.2f}/{ox:.2f}/{o2:.2f}'
                if lab == 'Crown':
                    rec['1X2_edge_1'] = f'{(ph*o1-1)*100:+.0f}%'; rec['1X2_edge_2'] = f'{(pa*o2-1)*100:+.0f}%'
                    if ph >= .75 and 1 / o1 < .95: pick = (pick + ' · ' if pick else '') + f'1Χ2 φαβ γηπ ≥75% @{o1:.2f}'
                    if pa >= .75 and 1 / o2 < .95: pick = (pick + ' · ' if pick else '') + f'1Χ2 φαβ εκτος ≥75% @{o2:.2f}'
            except Exception: pass
        ou = b.get('ou') or []
        if ou or lab == 'Crown':
            orec = dict(utc=utc, ματς=f'{hn} - {an}', ΔElo=int(gap), κοντινο=('ναι' if close else ''), T_μοντ=round(T, 2))
            if ou:
                try:
                    mt, g, u, d, _ = ou[-1]; ol_ = line_of(g); oo = hk(u); ou_ = hk(d); e = intl_pricing.over_ev(T, ol_, oo); po = intl_pricing.over_p_equiv(T, ol_, oo)
                    orec.update({lab: f'{ol_:g} {oo:.2f}/{ou_:.2f}', f'{lab}_p_over': f'{po*100:.0f}%', f'{lab}_edge': f'{e*100:+.0f}%'})
                    orec['PICK_over'] = (f'OVER {ol_:g} @{oo:.2f} ({lab}, {e*100:+.0f}%)' if (e >= .08 and close) else (f'(εκτος κανονα: οχι κοντινο, edge {e*100:+.0f}%)' if e >= .08 else ''))
                except Exception: orec[lab] = '—'
            else: orec[lab] = '—'
            io = line_of(o.get('init_ou')); orec['αρχικη_OU'] = f'{io:g}' if pd.notna(io) else '—'
            ex = [x for x in orows if x['ματς'] == orec['ματς']]
            if ex: ex[0].update({k: v for k, v in orec.items() if k not in ex[0] or v not in ('', '—')})
            else: orows.append(orec)
    rec['νεκρη'] = ''; rec['PICK_χαρτι'] = pick; rows.append(rec)
T = pd.DataFrame(rows); pd.set_option('display.width', 320); pd.set_option('display.max_columns', 40)
cols = [c for c in ['utc', 'ματς', 'R_h', 'R_a', 'υψομ', 'vadj', 'diff', 'λ', 'p1X2', 'P1_HFA60', 'fair_line', 'αρχικη_AH', 'Crown', 'Crown_fair_H', 'Crown_fair_A', 'Crown_edge_H', 'Crown_edge_A', 'SBOBET', 'SBOBET_edge_H', 'SBOBET_edge_A', 'Crown_1X2', '1X2_edge_1', '1X2_edge_2', 'νεκρη', 'PICK_χαρτι', 'σημ'] if c in T.columns]
print(T[cols].fillna('').to_string(index=False))
print(f'\nματς {len(T)} · χωρις rating {n_nor} · με στρωμα αξιας (V και στις 2) {n_v} (υπολοιπα vadj=0) · με Crown AH {int((T.get("Crown", pd.Series(["—"]*len(T))) != "—").sum())} · με Crown 1Χ2 {int(T.get("Crown_1X2", pd.Series()).notna().sum())} · χαρτινα picks: {int((T.PICK_χαρτι.fillna("") != "").sum())}')
T.to_csv(f'intl_afconq_shadow_2627{SUF}.csv', index=False)
O = pd.DataFrame(orows)
if len(O):
    oc = [c for c in ['utc', 'ματς', 'ΔElo', 'κοντινο', 'T_μοντ', 'αρχικη_OU', 'Crown', 'Crown_p_over', 'Crown_edge', 'SBOBET', 'SBOBET_p_over', 'SBOBET_edge', 'PICK_over'] if c in O.columns]
    print('\n--- O/U ---'); print(O[oc].fillna('').to_string(index=False)); print(f'με γραμμη O/U: {int((O.Crown.fillna("—") != "—").sum())} Crown · picks over: {int((O.get("PICK_over", pd.Series()).fillna("").str.startswith("OVER")).sum())}')
    O.to_csv(f'intl_afconq_overs_2627{SUF}.csv', index=False)
