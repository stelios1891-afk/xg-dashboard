"""intl_nl_shadow.py — NL 2026-27 MD1-2 (24-29/9): προβολες (intl_projections.csv: rating H + αξια ροστερ + logit + Poisson, T ανα τυπο) ΔΙΠΛΑ σε τρεχουσες
γραμμες Nowgoal (Crown 3 / SBOBET 31, intl_ng_now.json), fair odds, edge, και ΧΑΡΤΙΝΟ pick (κλασικο dog>=0.5 1.70-2.10 edge>=10%· φαβορι ιδιο· 1Χ2 φαβορι>=75%).
Εξοδος intl_nl_shadow_2627.csv (χαρτινο ledger, ΟΧΙ live). 21/9/2026.
25/9: τρεις εκδοχες διπλα-διπλα — H (PICK_χαρτι: AH + 1Χ2 φαβ), A αγκυρα χωρις αξια (PICK_αγκυρα: μονο AH, οπως απο 21/9), AV αγκυρα+αξια (PICK_αγκυρα_αξια: AH + 1Χ2 φαβ)."""
import sys, json, re, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
import picks
import intl_pricing   # 25/9: σωστα τεταρτα AH/over
P = pd.read_csv('intl_projections.csv'); NG = json.load(open('intl_ng_now.json', encoding='utf-8')); NAMES = json.load(open('nowgoal_intl_team_names.json', encoding='utf-8'))
# 21/9: σημαιες κλησης — πηγη πλεον TRANSFERMARKT (intl_callups_tm.py v2 -> intl_vcall_tm.json).
# Το FotMob squad ηταν ΜΠΑΓΙΑΤΙΚΟ (προηγουμενη αποστολη — διορθωση Στελιου)· το TM kader
# επικυρωθηκε: Ελλαδα = μονο Κωνσταντελιας εκτος (Καρετσας/Ιωαννιδης μεσα), Γαλλια χωρις
# ψευδο-απουσιες Mbappe/Olise. Ομαδες με υποπτο μεγεθος κλησης (Γερμανια) δεν εχουν σημαια.
CALL_FLAGS_ON = True
try:
    if not CALL_FLAGS_ON:
        raise RuntimeError('flags off')
    _VC = json.load(open('intl_vcall_tm.json', encoding='utf-8'))
    _M2 = pd.read_csv('intl_matches.csv', dtype={'mid': str})
    _N2T = {}
    for _r in _M2.itertuples():
        _N2T[str(_r.hn)] = int(_r.hid); _N2T[str(_r.an)] = int(_r.aid)
    def call_flag(team):
        v = _VC.get(str(_N2T.get(str(team), '')))
        if not v or not v.get('missing'):
            return ''
        return ', '.join(f"{m['nm']}({m['mv']}M{', χειρ.' if m.get('manual') else ''})" for m in v['missing'][:2])      # 25/9: χειροκινητες απουσιες σημειωνονται
except Exception:
    def call_flag(team):
        return ''
def toks(s):
    s = re.sub(r'[^a-z ]', ' ', str(s).lower().replace('ü', 'u').replace('ö', 'o').replace('ç', 'c')); return set(w for w in s.split() if len(w) > 2)
ALIAS = {'Turkiye': 'Turkey', 'Czechia': 'Czech Republic', 'Bosnia and Herzegovina': 'Bosnia', 'Ireland': 'Republic of Ireland', 'North Macedonia': 'Macedonia', 'Faroe Islands': 'Faroe'}
ng_by_key = {}
for ng, o in NG.items():
    ng_by_key.setdefault((NAMES.get(str(o['hid']), ''), NAMES.get(str(o['aid']), '')), []).append((ng, o))   # 25/9: λιστα (ιδιο ζευγος σε 2 αγωνιστικες)
import intl_dedupe
def resolve(fm):
    cands = list(ng_by_key.keys()); t = toks(ALIAS.get(fm, fm)) | toks(fm)
    best = None; bs = 0
    for k in cands:
        for nm in k:
            ov = len(t & toks(nm))
            if ov > bs: bs = ov; best = nm
    return best
def line_of(s):
    if s in (None, ''): return np.nan
    s = str(s)
    if '/' in s:
        a, b = s.split('/'); return (float(a) + float(b)) / 2
    return float(s)
rows = []
for r in P.itertuples():
    if pd.isna(getattr(r, 'diff', np.nan)): continue
    h, a = resolve(r.home), resolve(r.away); key = (h, a); hit = intl_dedupe.ng_pick(ng_by_key.get(key), r.utc, lambda x: x[1].get('dt')); flipped = False   # 25/9: ιδια ημερομηνια
    if not hit:
        hit = intl_dedupe.ng_pick(ng_by_key.get((a, h)), r.utc, lambda x: x[1].get('dt')); flipped = bool(hit)   # 25/9: ηταν «key != (h, a)» = παντα False
    rec = dict(comp=r.comp, utc=r.utc[:16], ματς=f'{r.home} - {r.away}', diff=int(r.diff), λ=f'{r.xg_h:.2f}-{r.xg_a:.2f}', p1X2=f'{r.P1}/{r.PX}/{r.P2}', diff_A=(int(r.diff_A) if pd.notna(r.diff_A) else np.nan), λ_A=(f'{r.xg_h_A:.2f}-{r.xg_a_A:.2f}' if pd.notna(r.xg_h_A) else '—'), p1X2_A=(f'{r.P1_A:.0f}/{r.PX_A:.0f}/{r.P2_A:.0f}' if pd.notna(r.P1_A) else '—'),
               diff_AV=(int(r.diff_AV) if pd.notna(r.diff_AV) else np.nan), λ_AV=(f'{r.xg_h_AV:.2f}-{r.xg_a_AV:.2f}' if pd.notna(r.xg_h_AV) else '—'), p1X2_AV=(f'{r.P1_AV:.0f}/{r.PX_AV:.0f}/{r.P2_AV:.0f}' if pd.notna(r.P1_AV) else '—'))
    distA = picks.gd_dist(max(r.xg_h_A, .05), max(r.xg_a_A, .05)) if pd.notna(r.xg_h_A) else None; pickA = ''
    _dg = lambda h, a: picks.gd_dist(max(h, .05), max(a, .05)) if (pd.notna(h) and pd.notna(a)) else None      # 25/9 (γ) βαθια φαβορι ≤ −2
    ddH, ddA, ddAV = _dg(getattr(r, 'xg_h_D', np.nan), getattr(r, 'xg_a_D', np.nan)), _dg(getattr(r, 'xg_h_A_D', np.nan), getattr(r, 'xg_a_A_D', np.nan)), _dg(getattr(r, 'xg_h_AV_D', np.nan), getattr(r, 'xg_a_AV_D', np.nan))
    distAV = picks.gd_dist(max(r.xg_h_AV, .05), max(r.xg_a_AV, .05)) if pd.notna(r.xg_h_AV) else None; pickAV = ''          # 25/9: εκδοχη AV = αγκυρα + αξια ροστερ (ιδιοι κανονες)
    fh_, fa_ = call_flag(r.home), call_flag(r.away)
    if fh_ or fa_:
        rec['απουσιες_κλησης'] = (f'{r.home}: {fh_}' if fh_ else '') + (' | ' if fh_ and fa_ else '') + (f'{r.away}: {fa_}' if fa_ else '')
    if not hit:
        rec['Crown'] = '—'; rows.append(rec); continue
    ng, o = hit
    ia = line_of(o.get('init_ah')); rec['αρχικη_AH'] = (f'{(-ia if not flipped else ia):+.2f}' if pd.notna(ia) else '—')
    dist = picks.gd_dist(max(r.xg_h, .05), max(r.xg_a, .05)); pick = ''
    for cid, lab in (('3', 'Crown'), ('31', 'SBOBET')):
        b = (o['books'].get(cid) or {}); ah = b.get('ah') or []
        if not ah: rec[lab] = '—'; continue
        mt, g, u, d, _ = ah[-1]
        try: line = -line_of(g); oh = float(u) + 1; oa = float(d) + 1
        except Exception: rec[lab] = '—'; continue
        if flipped: line, oh, oa = -line, oa, oh
        rec[lab] = f'{line:+.2f} {oh:.2f}/{oa:.2f}'
        if distA is not None:
            for side, ud, odds in ((1, line, oh), (-1, -line, oa)):
                e = intl_pricing.ah_ev(intl_pricing.dist_for(distA, ddA, ud), side, ud, odds, picks.MARGIN)
                rec[f'{lab}_edgeA_{"H" if side == 1 else "A"}'] = f'{e*100:+.0f}%'
                if not pickA and 1.70 <= odds <= 2.10 and e >= .10 and abs(ud) >= 0.5:
                    pickA = f"{'DOG' if ud >= 0.5 else 'FAV'} {'1' if side==1 else '2'} {ud:+.2f} @{odds:.2f} ({lab}, {e*100:+.0f}%)"
        if distAV is not None:
            for side, ud, odds in ((1, line, oh), (-1, -line, oa)):
                e = intl_pricing.ah_ev(intl_pricing.dist_for(distAV, ddAV, ud), side, ud, odds, picks.MARGIN)
                rec[f'{lab}_edgeAV_{"H" if side == 1 else "A"}'] = f'{e*100:+.0f}%'
                if not pickAV and 1.70 <= odds <= 2.10 and e >= .10 and abs(ud) >= 0.5:
                    pickAV = f"{'DOG' if ud >= 0.5 else 'FAV'} {'1' if side==1 else '2'} {ud:+.2f} @{odds:.2f} ({lab}, {e*100:+.0f}%)"
        for side, ud, odds in ((1, line, oh), (-1, -line, oa)):
            dx = intl_pricing.dist_for(dist, ddH, ud); e = intl_pricing.ah_ev(dx, side, ud, odds, picks.MARGIN); fo = intl_pricing.ah_fair(dx, side, ud) or 99
            tag = 'H' if side == 1 else 'A'; rec[f'{lab}_fair_{tag}'] = round(fo, 2); rec[f'{lab}_edge_{tag}'] = f'{e*100:+.0f}%'
            if not pick and 1.70 <= odds <= 2.10 and e >= .10:
                if ud >= 0.5: pick = f"DOG {'1' if side==1 else '2'} {ud:+.2f} @{odds:.2f} ({lab}, {e*100:+.0f}%)"
                elif ud <= -0.5: pick = f"FAV {'1' if side==1 else '2'} {ud:+.2f} @{odds:.2f} ({lab}, {e*100:+.0f}%)"
        op = b.get('op') or []
        if op and lab == 'Crown':
            try:
                _, gx, g1, g2, _ = op[-1]; o1, ox, o2 = float(g1), float(gx), float(g2)      # op: g=ισοπαλια, u=γηπ, d=εκτος
                if flipped: o1, o2 = o2, o1
                rec['Crown_1X2'] = f'{o1:.2f}/{ox:.2f}/{o2:.2f}'
                if r.P1 >= 75 and 1 / o1 < .95: pick = (pick + ' · ' if pick else '') + f'1Χ2 φαβ γηπ ≥75% @{o1:.2f}'
                if r.P2 >= 75 and 1 / o2 < .95: pick = (pick + ' · ' if pick else '') + f'1Χ2 φαβ εκτος ≥75% @{o2:.2f}'
                if pd.notna(r.P1_AV) and r.P1_AV >= 75 and 1 / o1 < .95: pickAV = (pickAV + ' · ' if pickAV else '') + f'1Χ2 φαβ γηπ ≥75% @{o1:.2f}'
                if pd.notna(r.P2_AV) and r.P2_AV >= 75 and 1 / o2 < .95: pickAV = (pickAV + ' · ' if pickAV else '') + f'1Χ2 φαβ εκτος ≥75% @{o2:.2f}'
            except Exception: pass
    dead = str(getattr(r, 'νεκρη', '') or '') if str(getattr(r, 'νεκρη', '')) != 'nan' else ''
    rec['νεκρη'] = dead
    if dead: pick = 'ΟΧΙ (νεκρη ' + dead + ')'          # κανονας 21/9 Στελιος: κανενα pick σε ματς με αδιαφορη ομαδα
    if dead: pickA = 'ΟΧΙ (νεκρη)'; pickAV = 'ΟΧΙ (νεκρη)'
    rec['PICK_χαρτι'] = pick; rec['PICK_αγκυρα'] = pickA; rec['PICK_αγκυρα_αξια'] = pickAV; rows.append(rec)
T = pd.DataFrame(rows); pd.set_option('display.width', 300); pd.set_option('display.max_columns', 30)
cols = [c for c in ['comp', 'utc', 'ματς', 'diff', 'λ', 'p1X2', 'αρχικη_AH', 'Crown', 'Crown_fair_H', 'Crown_fair_A', 'Crown_edge_H', 'Crown_edge_A', 'SBOBET', 'Crown_1X2', 'νεκρη', 'PICK_χαρτι', 'p1X2_A', 'Crown_edgeA_H', 'Crown_edgeA_A', 'PICK_αγκυρα', 'p1X2_AV', 'Crown_edgeAV_H', 'Crown_edgeAV_A', 'PICK_αγκυρα_αξια'] if c in T.columns]
print(T[cols].to_string(index=False)); print(f'\nματς με γραμμη Crown: {int((T.Crown != "—").sum())}/{len(T)} · χαρτινα picks: {int((T.PICK_χαρτι != "").sum())} · αγκυρα: {int((T.PICK_αγκυρα != "").sum())} · αγκυρα+αξια: {int((T.PICK_αγκυρα_αξια != "").sum())}')
T.to_csv('intl_nl_shadow_2627.csv', index=False)
