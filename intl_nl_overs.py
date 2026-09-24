"""intl_nl_overs.py — OVER με ΚΑΤΑΣΤΑΣΗ στο NL 2026-27 (22/9): T = 0.29 + 0.33·|diff|/100 + 0.26·[KO] + 0.49·[|ΔElo|<150] + 0.10·(R_h+R_a)/2/100 − 0.05·[NL] (intl_xg_totals, 22/9), Poisson με s=0.49·diff/100,
συγκριση με τρεχουσες γραμμες O/U Crown(3)/SBOBET(31) απο intl_ng_now.json· pick = over edge>=8%. ΧΑΡΤΙΝΟ.
25/9: το ιδιο T και για τις εκδοχες αγκυρας (T_A με diff_A, T_AV με diff_AV· ratings/ΔElo αγκυρας) → Crown/SBOBET_edge_A/_AV, PICK_over_A/_AV."""
import sys, json, re, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
P = pd.read_csv('intl_projections.csv'); AD = json.load(open('intl_xg_attdef.json', encoding='utf-8')); MU = 1.231; HF = 1.15; NG = json.load(open('intl_ng_now.json', encoding='utf-8')); NAMES = json.load(open('nowgoal_intl_team_names.json', encoding='utf-8'))
def toks(s): s = re.sub(r'[^a-z ]', ' ', str(s).lower()); return set(w for w in s.split() if len(w) > 2)
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
def line_of(s):
    if s in (None, ''): return np.nan
    s = str(s)
    if '/' in s: a, b = s.split('/'); return (float(a) + float(b)) / 2
    return float(s)
def p_over(T, line):
    kmax = int(math.floor(line)); p = 1 - sum(math.exp(-T) * T ** k / math.factorial(k) for k in range(kmax + 1))
    if float(line).is_integer(): p_push = math.exp(-T) * T ** int(line) / math.factorial(int(line)); return p, p_push
    return p, 0.0
rows = []
for r in P.itertuples():
    if pd.isna(r.diff): continue
    gap = abs(r.R_home - r.R_away); close = gap < 150; T = 0.29 + 0.33 * abs(r.diff) / 100 + 0.49 * close + 0.10 * (r.R_home + r.R_away) / 2 / 100 - 0.05      # 22/9: T με επιπεδο (intl_xg_totals)
    # εκδοχη «ΜΑΖΙ» (σκια): T_mix = 0.28 + 0.72·T_xg + 0.26·|diff|/100 + 0.27·[KO] + 0.41·[κοντινο], T_xg απο xG επιθεση/αμυνα ομαδων
    ah_ = AD.get(str(r.hid), {}); aa_ = AD.get(str(r.aid), {})
    if ah_ and aa_:
        lhx = MU * (ah_['att'] / MU) * (aa_['dfn'] / MU) * HF; lax = MU * (aa_['att'] / MU) * (ah_['dfn'] / MU) / HF; T_mix = 0.28 + 0.72 * (lhx + lax) + 0.26 * abs(r.diff) / 100 + 0.41 * close
    else:
        T_mix = np.nan
    h, a = resolve(r.home), resolve(r.away); o = ng_by_key.get((h, a)) or ng_by_key.get((a, h))
    rec = dict(comp=r.comp, utc=r.utc[:16], ματς=f'{r.home} - {r.away}', ΔElo=int(gap), κοντινο='ναι' if close else '', T_μοντ=round(T, 2), T_μαζι=(round(T_mix, 2) if pd.notna(T_mix) else np.nan), T_παλιο=round(2.41 + 0.14 * abs(r.diff) / 100, 2))
    # 25/9: ιδιο T με ratings αγκυρας — εκδοχη A (diff_A) και AV (diff_AV = diff_A + αξια)· κοντινο με ΔElo αγκυρας
    TV = {}
    if pd.notna(getattr(r, 'diff_A', np.nan)) and pd.notna(getattr(r, 'R_home_A', np.nan)):
        gapA = abs(r.R_home_A - r.R_away_A); closeA = gapA < 150; lvlA = 0.10 * (r.R_home_A + r.R_away_A) / 2 / 100
        TV['A'] = (0.29 + 0.33 * abs(r.diff_A) / 100 + 0.49 * closeA + lvlA - 0.05, closeA)
        if pd.notna(getattr(r, 'diff_AV', np.nan)): TV['AV'] = (0.29 + 0.33 * abs(r.diff_AV) / 100 + 0.49 * closeA + lvlA - 0.05, closeA)
        rec['ΔElo_A'] = int(gapA)
    for v_, (Tv, _) in TV.items(): rec[f'T_{v_}'] = round(Tv, 2)
    bestV = {v_: '' for v_ in TV}
    best = ''
    if o:
        for cid, lab in (('3', 'Crown'), ('31', 'SBOBET')):
            ou = (o['books'].get(cid) or {}).get('ou') or []
            if not ou: rec[lab] = '—'; continue
            mt, g, u, d, _ = ou[-1]
            try: line = line_of(g); oo = float(u) + 1; ou_ = float(d) + 1
            except Exception: rec[lab] = '—'; continue
            po, pp = p_over(T, line); e = po * oo - 1 + 0 * pp; rec[lab] = f'{line:g} {oo:.2f}/{ou_:.2f}'; rec[f'{lab}_p_over'] = f'{po*100:.0f}%'; rec[f'{lab}_edge'] = f'{e*100:+.0f}%'
            if pd.notna(T_mix): pm, _ = p_over(T_mix, line); rec[f'{lab}_edge_μαζι'] = f'{(pm*oo-1)*100:+.0f}%'
            if e >= .08 and not best: best = (f'OVER {line:g} @{oo:.2f} ({lab}, {e*100:+.0f}%)' if close else f'(εκτος κανονα: αναντιστοιχια, edge {e*100:+.0f}% {lab})')
            for v_, (Tv, closeV) in TV.items():
                pv, _ = p_over(Tv, line); ev_ = pv * oo - 1; rec[f'{lab}_edge_{v_}'] = f'{ev_*100:+.0f}%'
                if ev_ >= .08 and not bestV[v_]: bestV[v_] = (f'OVER {line:g} @{oo:.2f} ({lab}, {ev_*100:+.0f}%)' if closeV else f'(εκτος κανονα: αναντιστοιχια, edge {ev_*100:+.0f}% {lab})')
        ia = line_of(o.get('init_ou')); rec['αρχικη_OU'] = f'{ia:g}' if pd.notna(ia) else '—'
    rec['PICK_over'] = best
    for v_ in ('A', 'AV'): rec[f'PICK_over_{v_}'] = bestV.get(v_, '')
    rows.append(rec)
T = pd.DataFrame(rows); pd.set_option('display.width', 300); pd.set_option('display.max_columns', 30)
cols = [c for c in ['comp', 'utc', 'ματς', 'ΔElo', 'κοντινο', 'T_παλιο', 'T_μοντ', 'T_μαζι', 'αρχικη_OU', 'Crown', 'Crown_p_over', 'Crown_edge', 'Crown_edge_μαζι', 'SBOBET', 'SBOBET_edge', 'PICK_over', 'T_A', 'Crown_edge_A', 'PICK_over_A', 'T_AV', 'Crown_edge_AV', 'PICK_over_AV'] if c in T.columns]
print(T[cols].fillna('').to_string(index=False)); print(f'\nκοντινα ματς: {int((T.κοντινο=="ναι").sum())}/{len(T)} · με γραμμη O/U: {int(T.Crown.fillna("—").ne("—").sum()) if "Crown" in T else 0} · picks over: {int((T.PICK_over!="").sum())} · A: {int((T.PICK_over_A!="").sum())} · AV: {int((T.PICK_over_AV!="").sum())}')
T.to_csv('intl_nl_overs_2627.csv', index=False)
