"""intl_dashboard_build.py — 🌐 INTERNATIONAL tab (25/9/2026, εντολη Στελιου): μαζευει σε ΕΝΑ json τις προβολες εθνικων
(NL A-D 2026-27 + προκριματικα AFCON 2027) με τις ΤΡΕΙΣ εκδοχες μοντελου ΞΕΧΩΡΙΣΤΑ και διπλα την αγορα (Nowgoal Crown/SBOBET).
  H  = rating H3 + στρωμα αξιας ροστερ (intl_project.py στηλες χωρις καταληξη)
  A  = αγκυρα αγορας λ=0.3 ΧΩΡΙΣ αξια (_A)          AV = αγκυρα + αξια (_AV, ιδιος logit/T με την A)
Πηγες (ολα τοπικα, ΔΕΝ τρεχει στο Actions): intl_projections.csv, intl_nl_shadow_2627.csv, intl_nl_overs_2627.csv (picks χαρτινου ledger
ανα εκδοχη + κλησεις TM + νεκρη), intl_ng_now.json / intl_ng_now_afconq.json (γραμμες), intl_afconq_shadow_2627.csv + intl_afconq_overs_2627.csv
(AFCONQ: ΜΟΝΟ εκδοχη H — αγκυρα μη διαθεσιμη για CAF). fair/edge AH ανα εκδοχη ξαναϋπολογιζονται εδω (picks.gd_dist/p_cover, ιδια λ με τα CSV)·
over edges = απο τα CSV (ιδιο p_over ανα script). ΔΕΝ κανει fetch. Εξοδος: intl_projections_dashboard.json (σκια, χαρτινο — ΟΧΙ live)."""
import sys, os, json, re, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
import picks

OUT = 'intl_projections_dashboard.json'
VERS = ('H', 'A', 'AV')
BOOKS = (('3', 'crown'), ('31', 'sbobet'))
RULES = {'ah': 'AH: dog/φαβορι ≥0.5, τιμη 1.70-2.10, edge ≥10% (Crown πρωτα, μετα SBOBET)',
         'x12': '1Χ2: φαβορι με P ≥75% (και 1/τιμη <0.95)', 'dead': 'νεκρη ομαδα (αδιαφορη για 1η/υποβιβασμο) = κανενα pick',
         'over': 'OVER: edge ≥8% ΚΑΙ (νοκ-αουτ ή |ΔElo| <150 = «κοντινο»)· αλλιως «εκτος κανονα»',
         'hfa': {'NL': 60, 'AFCONQ': 80}, 'T': 'T = 0.29 + 0.33·|diff|/100 + 0.26·[KO] + 0.49·[κοντινο] + 0.10·(R_h+R_a)/2/100 − 0.05·[NL]',
         'A_note': 'Η εκδοχη Α (αγκυρα χωρις αξια) δινει ΜΟΝΟ AH picks (οπως τρεχει απο 21/9)· H και AV δινουν AH + 1Χ2 φαβορι.',
         'afconq_note': 'AFCONQ: αγκυρα μη διαθεσιμη για CAF (δεν εχει τρεξει intl_mkt_anchor) — μονο εκδοχη H, HFA 80.'}
NAMES = json.load(open('nowgoal_intl_team_names.json', encoding='utf-8'))
M = pd.read_csv('intl_matches.csv', dtype={'mid': str}); N2ID = {}
for r in M.itertuples(): N2ID[str(r.hn)] = int(r.hid); N2ID[str(r.an)] = int(r.aid)


def jf(x, nd=2):
    """float για json (NaN -> None)."""
    try:
        return None if x is None or (isinstance(x, float) and np.isnan(x)) or pd.isna(x) else round(float(x), nd)
    except Exception:
        return None


def pct(s):
    """'+12%' -> 12.0, '' -> None."""
    try:
        return float(str(s).replace('%', '').replace('+', '')) if s not in (None, '') and str(s) != 'nan' else None
    except Exception:
        return None


def line_of(s):
    if s in (None, ''): return np.nan
    s = str(s)
    if '/' in s:
        a, b = s.split('/'); return (float(a) + float(b)) / 2
    return float(s)


def hk(x):
    v = float(x); return v + 1 if v < 1.5 else v


def market_of(o, flipped=False, conv=None):
    """γραμμες ανα book απο εγγραφη Nowgoal (τελευταια σειρα ah/ou/op)· conv = μετατροπη HK -> δεκαδικη."""
    conv = conv or (lambda v: float(v) + 1)
    out = {}
    for cid, lab in BOOKS:
        b = (o.get('books') or {}).get(cid) or {}; rec = {}
        ah = b.get('ah') or []
        if ah:
            try:
                _, g, u, d, _ = ah[-1]; line = -line_of(g); oh = conv(u); oa = conv(d)
                if flipped: line, oh, oa = -line, oa, oh
                rec.update(ah_line=round(line, 2), oh=round(oh, 2), oa=round(oa, 2))
            except Exception: pass
        ou = b.get('ou') or []
        if ou:
            try:
                _, g, u, d, _ = ou[-1]; rec.update(ou_line=round(line_of(g), 2), over=round(conv(u), 2), under=round(conv(d), 2))
            except Exception: pass
        op = b.get('op') or []
        if op:
            try:
                _, gx, g1, g2, _ = op[-1]; o1, ox, o2 = float(g1), float(gx), float(g2)      # op: g=ισοπαλια, u=γηπ, d=εκτος
                if flipped: o1, o2 = o2, o1
                rec.update(o1=round(o1, 2), ox=round(ox, 2), o2=round(o2, 2))
            except Exception: pass
        out[lab] = rec or None
    return out


def ah_edges(xg_h, xg_a, mk):
    """fair/edge στη γραμμη καθε book για γηπεδουχο (H) και φιλοξενουμενο (A) — ιδιος τυπος με intl_nl_shadow.py."""
    if xg_h is None or xg_a is None: return {}
    dist = picks.gd_dist(max(xg_h, .05), max(xg_a, .05)); out = {}
    for _, lab in BOOKS:
        b = mk.get(lab) or {}
        if b.get('ah_line') is None: out[lab] = None; continue
        line, oh, oa = b['ah_line'], b['oh'], b['oa']; rec = {}
        for side, ud, odds, tag in ((1, line, oh, 'home'), (-1, -line, oa, 'away')):
            pw, pp = picks.p_cover(dist, side, ud); e = pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
            rec[f'ah_{tag}'] = round(e * 100, 1); rec[f'fair_{tag[0]}'] = round((1 - pp) / pw, 2) if pw > 0 else None
        out[lab] = rec
    return out


def version(Rh, Ra, vadj, diff, xg_h, xg_a, p1, px, p2, T=None):
    if diff is None or pd.isna(diff): return None
    p1, px, p2 = float(p1), float(px), float(p2)
    return dict(R_h=jf(Rh, 0), R_a=jf(Ra, 0), vadj=jf(vadj, 0), diff=jf(diff, 0), xg_h=jf(xg_h), xg_a=jf(xg_a), T=jf(T),
                p1=round(p1), px=round(px), p2=round(p2),
                fair_1=(round(100 / p1, 2) if p1 > 0 else None), fair_x=(round(100 / px, 2) if px > 0 else None), fair_2=(round(100 / p2, 2) if p2 > 0 else None))


def sget(row, col, default=''):
    if row is None or col not in row.index: return default
    v = row[col]; return default if (v is None or (isinstance(v, float) and np.isnan(v))) else v


# ============================ NATIONS LEAGUE ============================
P = pd.read_csv('intl_projections.csv'); NG = json.load(open('intl_ng_now.json', encoding='utf-8'))
SH = pd.read_csv('intl_nl_shadow_2627.csv'); OV = pd.read_csv('intl_nl_overs_2627.csv')
SHD = {k: SH.iloc[i] for i, k in enumerate(zip(SH.comp, SH.utc.str[:16], SH['ματς']))}; OVD = {k: OV.iloc[i] for i, k in enumerate(zip(OV.comp, OV.utc.str[:16], OV['ματς']))}


def toks(s):
    s = re.sub(r'[^a-z ]', ' ', str(s).lower().replace('ü', 'u').replace('ö', 'o').replace('ç', 'c')); return set(w for w in s.split() if len(w) > 2)


ALIAS = {'Turkiye': 'Turkey', 'Czechia': 'Czech Republic', 'Bosnia and Herzegovina': 'Bosnia', 'Ireland': 'Republic of Ireland', 'North Macedonia': 'Macedonia', 'Faroe Islands': 'Faroe'}
ng_by_key = {}
for ng, o in NG.items(): ng_by_key[(NAMES.get(str(o['hid']), ''), NAMES.get(str(o['aid']), ''))] = o


def resolve(fm):
    t = toks(ALIAS.get(fm, fm)) | toks(fm); best = None; bs = 0
    for k in ng_by_key:
        for nm in k:
            ov = len(t & toks(nm))
            if ov > bs: bs = ov; best = nm
    return best


comps = {c: [] for c in ('NL A', 'NL B', 'NL C', 'NL D', 'AFCONQ')}
n_chk = 0; chk_bad = []
for r in P.itertuples():
    if pd.isna(r.diff): continue
    key = (r.comp, r.utc[:16], f'{r.home} - {r.away}'); sh = SHD.get(key); ov = OVD.get(key)
    h, a = resolve(r.home), resolve(r.away); o = ng_by_key.get((h, a)); flipped = False
    if o is None and ng_by_key.get((a, h)) is not None: o = ng_by_key[(a, h)]; flipped = True
    mk = market_of(o, flipped) if o else {'crown': None, 'sbobet': None}
    vers = {'H': version(r.R_home, r.R_away, r.val_adj, r.diff, r.xg_h, r.xg_a, r.P1, r.PX, r.P2, sget(ov, 'T_μοντ', None)),
            'A': version(getattr(r, 'R_home_A', np.nan), getattr(r, 'R_away_A', np.nan), 0, r.diff_A, r.xg_h_A, r.xg_a_A, r.P1_A, r.PX_A, r.P2_A, sget(ov, 'T_A', None)) if pd.notna(r.diff_A) else None,
            'AV': version(getattr(r, 'R_home_A', np.nan), getattr(r, 'R_away_A', np.nan), r.val_adj, r.diff_AV, r.xg_h_AV, r.xg_a_AV, r.P1_AV, r.PX_AV, r.P2_AV, sget(ov, 'T_AV', None)) if pd.notna(getattr(r, 'diff_AV', np.nan)) else None}
    edges = {}
    for v, suf in (('H', ''), ('A', '_A'), ('AV', '_AV')):
        V = vers[v]
        if V is None: edges[v] = None; continue
        e = ah_edges(V['xg_h'], V['xg_a'], mk)
        for _, lab in BOOKS:
            if e.get(lab) is not None:
                e[lab]['over'] = pct(sget(ov, f'{"Crown" if lab == "crown" else "SBOBET"}_edge{suf}')); e[lab]['p_over'] = pct(sget(ov, f'{"Crown" if lab == "crown" else "SBOBET"}_p_over')) if v == 'H' else None
            elif (mk.get(lab) or {}).get('ou_line') is not None:
                e[lab] = {'over': pct(sget(ov, f'{"Crown" if lab == "crown" else "SBOBET"}_edge{suf}'))}
        edges[v] = e
        # ελεγχος συνεπειας με το CSV της σκιας (εκδοχη H: fair/edge Crown)
        if v == 'H' and e.get('crown') and sh is not None and sget(sh, 'Crown_fair_H', None) is not None:
            n_chk += 1
            if abs(float(sh['Crown_fair_H']) - (e['crown']['fair_h'] or 0)) > 0.011 or abs(pct(sh['Crown_edge_H']) - e['crown']['ah_home']) > 0.6:
                chk_bad.append((key[2], sh['Crown_fair_H'], e['crown']['fair_h'], sh['Crown_edge_H'], e['crown']['ah_home']))
    dead = str(getattr(r, 'νεκρη', '') or ''); dead = '' if dead == 'nan' else dead
    comps[r.comp].append(dict(utc=r.utc[:16].replace('T', ' '), home=r.home, away=r.away, hid=int(r.hid), aid=int(r.aid), dead=dead,
                              callups=str(sget(sh, 'απουσιες_κλησης', '')), init_ah=str(sget(sh, 'αρχικη_AH', '')), init_ou=str(sget(ov, 'αρχικη_OU', '')),
                              versions=vers, market=mk, edges=edges,
                              picks=dict(H=str(sget(sh, 'PICK_χαρτι', '')), A=str(sget(sh, 'PICK_αγκυρα', '')), AV=str(sget(sh, 'PICK_αγκυρα_αξια', '')),
                                         over=str(sget(ov, 'PICK_over', '')), over_A=str(sget(ov, 'PICK_over_A', '')), over_AV=str(sget(ov, 'PICK_over_AV', '')))))
print(f'NL: ελεγχος fair/edge H vs intl_nl_shadow: {n_chk} ματς, αποκλισεις {len(chk_bad)}' + (f' -> {chk_bad[:3]}' if chk_bad else ''))

# ============================ AFCONQ (μονο H) ============================
try:
    AQ = pd.read_csv('intl_afconq_shadow_2627.csv', dtype={'ng': str}); AQO = pd.read_csv('intl_afconq_overs_2627.csv'); NGQ = json.load(open('intl_ng_now_afconq.json', encoding='utf-8'))
    AQOD = {}
    for i, k in enumerate(AQO['ματς']): AQOD.setdefault(k, AQO.iloc[i])
    ALIAS_Q = {'Democratic Rep Congo': 'DR Congo', 'Republic of the Congo': 'Congo', 'Guinea Bissau': 'Guinea-Bissau', "Cote d'Ivoire": 'Ivory Coast', 'Cabo Verde': 'Cape Verde', 'Swaziland': 'Eswatini', 'Sao Tome': 'Sao Tome and Principe'}
    n_q = 0
    for r in AQ.itertuples():
        if pd.isna(r.diff): continue
        o = NGQ.get(str(r.ng)) or {}; hn_, an_ = str(r.ματς).split(' - ', 1)
        hid = N2ID.get(ALIAS_Q.get(NAMES.get(str(o.get('hid')), ''), NAMES.get(str(o.get('hid')), '')) or hn_) or N2ID.get(hn_)
        aid = N2ID.get(ALIAS_Q.get(NAMES.get(str(o.get('aid')), ''), NAMES.get(str(o.get('aid')), '')) or an_) or N2ID.get(an_)
        lh, la = [float(x) for x in str(r.λ).split('-')]; p1, px, p2 = [float(x) for x in str(r.p1X2).split('/')]
        ov = AQOD.get(r.ματς); srow = AQ.iloc[r.Index]
        mk = market_of(o, False, hk) if o else {'crown': None, 'sbobet': None}
        V = version(r.R_h, r.R_a, r.vadj, r.diff, lh, la, p1, px, p2, sget(ov, 'T_μοντ', None))
        e = ah_edges(lh, la, mk)
        for _, lab in BOOKS:
            L = 'Crown' if lab == 'crown' else 'SBOBET'
            if e.get(lab) is not None: e[lab]['over'] = pct(sget(ov, f'{L}_edge')); e[lab]['p_over'] = pct(sget(ov, f'{L}_p_over'))
            elif (mk.get(lab) or {}).get('ou_line') is not None: e[lab] = {'over': pct(sget(ov, f'{L}_edge'))}
        comps['AFCONQ'].append(dict(utc=str(r.utc)[:16].replace('T', ' '), home=hn_, away=an_, hid=hid, aid=aid, dead='', callups='',
                                    init_ah=str(sget(srow, 'αρχικη_AH', '')), init_ou=str(sget(ov, 'αρχικη_OU', '')),
                                    versions={'H': V, 'A': None, 'AV': None}, market=mk, edges={'H': e, 'A': None, 'AV': None},
                                    picks=dict(H=str(sget(srow, 'PICK_χαρτι', '')), A='', AV='', over=str(sget(ov, 'PICK_over', '')), over_A='', over_AV='')))
        n_q += 1
    print(f'AFCONQ: {n_q} ματς (μονο H)')
except FileNotFoundError as ex:
    print(f'AFCONQ: παραλειπεται ({ex})')

for c in comps: comps[c].sort(key=lambda m: m['utc'])
ng_m = dt.datetime.fromtimestamp(os.path.getmtime('intl_ng_now.json'), dt.timezone.utc)
out = dict(generated=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M'), ng_snapshot=ng_m.strftime('%Y-%m-%d %H:%M'),
           ng_snapshot_afconq=(dt.datetime.fromtimestamp(os.path.getmtime('intl_ng_now_afconq.json'), dt.timezone.utc).strftime('%Y-%m-%d %H:%M') if os.path.exists('intl_ng_now_afconq.json') else None),
           comps=[dict(comp=c, matches=ms) for c, ms in comps.items()], rules=RULES, versions={'H': 'Rating H3 + αξια ροστερ', 'A': 'Αγκυρα αγορας (λ=0.3) χωρις αξια', 'AV': 'Αγκυρα + αξια ροστερ'})
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def _real(p):
    return bool(p) and not p.startswith('ΟΧΙ') and not p.startswith('(')


for c, ms in comps.items():
    n_pick = {v: sum(_real(m['picks'][v]) for m in ms) for v in VERS}
    n_over = {v: sum(_real(m['picks'][k]) for m in ms) for v, k in (('H', 'over'), ('A', 'over_A'), ('AV', 'over_AV'))}
    print(f"{c}: {len(ms)} ματς · με Crown AH {sum(1 for m in ms if (m['market'].get('crown') or {}).get('ah_line') is not None)} · picks AH/1Χ2 H {n_pick['H']} A {n_pick['A']} AV {n_pick['AV']} · over H {n_over['H']} A {n_over['A']} AV {n_over['AV']}")
print(f'-> {OUT} · generated {out["generated"]} UTC · Nowgoal snapshot {out["ng_snapshot"]} UTC')
