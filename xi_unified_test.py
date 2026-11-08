# -*- coding: utf-8 -*-
"""xi_unified_test.py — 21/10/2026 (Στελιος: «τρεξε το ενιαιο τεστ, αλλα και αλλα τεστ — πως μειωνεται το λαθος, την κλιση κτλπ»).
Α. ΕΝΙΑΙΟ ΤΕΣΤ ΠΟΝΤΑΡΙΣΜΑΤΟΣ (ΠΡΟ-ΔΗΛΩΜΕΝΟ, κανενα διαλεγμα): ΟΛΟΙ οι κανονες στο ΣΤΑΘΕΡΟ κατωφλι τους:
   αουτσαιντερ 7+ ≥10% (p_cover) · φαβορι 15+ ≥10% (live: αγκυρα .7, σωστα τεταρτα) · over 7+ ≥10% · under 7+ ≥10% (αγκυρα συνολων)
   στις στιγμες 55′ (επισημη ενδεκαδα) και 6ω (απουσιες). ΕΝΑ νουμερο: μοναδες «με ενδεκαδα» − «μονο μοντελο» (μεσος Crown/Bet365),
   ανα σεζον + διαστημα 90% (bootstrap ανα αγωνιστικη εβδομαδα λιγκας). ΚΡΙΤΗΡΙΟ: διαφορα > 0 σε ≥3/4 σεζον ΚΑΙ 90% πανω απο 0.
Β. ΑΚΡΙΒΕΙΑ στην τιμη της ιδιας στιγμης (Crown), μοντελο ΧΩΡΙΣ vs ΜΕ ενδεκαδα:
   (1) τετραγωνικο λαθος (διαφορα γκολ / συνολο)  (2) ΚΛΙΣΗ «πληροφοριας περα απο την αγορα»: (αποτελεσμα − αγορα) = a + b·(μοντελο − αγορα)
       — b = ποσο απο τη διαφωνια μας με την αγορα βγαινει αληθινο (0 θορυβος, 1 ολο)  (3) Brier της καλυψης χαντικαπ / over στη γραμμη της αγορας."""
import sys, json, glob, re, io, contextlib, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
NL = chr(10)
A = pd.read_csv('xi_model_overlay_rows.csv', dtype={'mid': str, 'season': str}); A = A[A.role == 'dog'].assign(kind='dog')
B = pd.read_csv('xi_fav_totals_overlay_rows.csv', dtype={'mid': str, 'season': str})
R = pd.concat([A[['mid', 'kind', 'tp', 'bk', 'season', 'md', 'e0', 'e1', 'pnl']], B[['mid', 'kind', 'tp', 'bk', 'season', 'md', 'e0', 'e1', 'pnl']]], ignore_index=True)
RULES = [('αουτσαιντερ 7+ ≥10%', 'dog', 6, .10), ('φαβορι 15+ ≥10% (live)', 'fav', 14, .10), ('over 7+ ≥10%', 'over', 6, .10), ('under 7+ ≥10%', 'under', 6, .10)]
KO, LGM = {}, {}
for f in glob.glob('data_*_*.json'):
    m = re.search(r'data_(EPL|LaLiga|SerieA|Bundesliga|Ligue1|Eredivisie|PrimeiraLiga)_\d{4}\.json$', f)
    if not m: continue
    for k, v in json.load(open(f, encoding='utf-8')).items():
        try: KO[str(k)] = dt.datetime.strptime(v['date'], '%a, %b %d, %Y, %H:%M UTC'); LGM[str(k)] = m.group(1)
        except Exception: pass
R['blk'] = R.mid.map(lambda k: f"{LGM.get(k, '')}_{KO[k].strftime('%G%V')}" if k in KO else 'x')
SE = sorted(R.season.unique()); rng = np.random.default_rng(11)
print(f'{"=" * 140}{NL}Α. ΕΝΙΑΙΟ ΤΕΣΤ — μοναδες «μονο μοντελο» → «με ενδεκαδα» (μεσος Crown/Bet365), ΣΤΑΘΕΡΑ κατωφλια')
for tp, lab in (('55′', '55′ πριν (επισημη ενδεκαδα)'), ('6ω', '6ω πριν (απουσιες)')):
    print(f'{NL}   {lab}')
    tot_rows = []
    for nm, kd, mm, T in RULES:
        q = R[(R.tp == tp) & (R.kind == kd) & (R.md >= mm)]
        a, b = q[q.e0 >= T], q[q.e1 >= T]
        ua, ub = a.pnl.sum() / 2, b.pnl.sum() / 2
        per = [(b[b.season == s].pnl.sum() - a[a.season == s].pnl.sum()) / 2 for s in SE]
        print(f'      {nm:26s} │ picks {len(a) / 2:5.0f} → {len(b) / 2:5.0f} │ ROI {100 * a.pnl.mean():+5.1f}% → {100 * b.pnl.mean():+5.1f}% │ μοναδες {ua:+6.1f} → {ub:+6.1f} '
              f'(διαφ. {ub - ua:+5.1f}) │ ανα σεζον ' + ' '.join(f'{v:+.1f}' for v in per) + f' ({sum(v > 0 for v in per)}/4)')
        d = pd.concat([b.assign(w=1.0), a.assign(w=-1.0)]); d['g'] = d.pnl * d.w / 2; tot_rows.append(d)
    D = pd.concat(tot_rows); g = D.groupby('blk').g.sum(); blocks = g.index.values; vals = g.values
    bs = [vals[rng.integers(0, len(vals), len(vals))].sum() for _ in range(3000)]
    per = [D[D.season == s].g.sum() for s in SE]
    print(f'      {"ΣΥΝΟΛΟ 4 κανονων":26s} │ διαφορα μοναδων {vals.sum():+6.1f} · 90% [{np.percentile(bs, 5):+.1f}, {np.percentile(bs, 95):+.1f}] · ανα σεζον '
          + ' '.join(f'{v:+.1f}' for v in per) + f' ({sum(v > 0 for v in per)}/4) → {"ΠΕΡΝΑ" if (sum(v > 0 for v in per) >= 3 and np.percentile(bs, 5) > 0) else "ΔΕΝ περνα"}')
# ---------------- Β. ΑΚΡΙΒΕΙΑ ----------------
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
M = pd.read_csv('xi_market_timing_rows.csv', dtype={'mid': str, 'season': str}); M = M[M.bk == 'Crown']
Pm = pd.read_csv('core7_mech_preds_bl_0.6.csv', dtype={'mid': str})[['mid', 'xg_h', 'xg_a', 'md']]
gT = {'__name__': 'xt'}; s2 = open('core7_totals_anchor_md1_test.py', encoding='utf-8').read()
with contextlib.redirect_stdout(_Q()): exec(s2[:s2.index('rows = []; prestale = []')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), gT)
TOT = pd.DataFrame({'mid': gT['P'].mid.astype(str).values, 'Ta': gT['anchored'](6)})
gP = {'__name__': 'xp'}; s3 = open('xi_pregame_eval.py', encoding='utf-8').read()
with contextlib.redirect_stdout(_Q()): exec(s3[:s3.index("M = pd.read_csv('xi_market_timing_rows.csv'")], gP)
M = M.merge(Pm, on='mid').merge(TOT, on='mid', how='left').merge(gP['D'][['mid', 'g_gd', 'g_t']], on='mid', how='left')
M = M[M.md >= 6]
def slope(x, y):
    m = np.isfinite(x) & np.isfinite(y); x, y = x[m], y[m]
    X = np.column_stack([np.ones(len(x)), x]); b = np.linalg.lstsq(X, y, rcond=None)[0]; res = y - X @ b
    se = np.sqrt((res ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum()); return b[1], se, len(x)
def brier_ah(xh, xa, L_ng, gd):
    """P(γηπεδουχος καλυπτει) απο το μοντελο στη γραμμη της αγορας vs αποτελεσμα (ισοπαλιες γραμμης εξω, μισα αποτελεσματα = 0.5)."""
    d = picks.gd_dist(max(xh, .05), max(xa, .05)); pw, pp = picks.p_cover(d, 1, -L_ng); p = pw / max(pw + (1 - pw - pp), 1e-9)
    r = picks.settle(gd, 1, -L_ng, 2.0)
    if r == 0: return None
    y = 1.0 if r >= 1 else (0.75 if r > 0 else (0.25 if r > -1 else 0.0))
    return (p - y) ** 2
print(f'{NL}{"=" * 140}{NL}Β. ΑΚΡΙΒΕΙΑ (Crown, αγωνιστικες 7+) — μοντελο ΧΩΡΙΣ vs ΜΕ ενδεκαδα, στην τιμη της ιδιας στιγμης')
for tp, adj_gd, adj_t, lab in (('55′', 'f_gd', 'f_t', '55′ πριν — επισημη ενδεκαδα'), ('6ω', 'g_gd', 'g_t', '6ω πριν — απουσιες')):
    q = M[M[f's_{tp}'].notna() & M[adj_gd].notna()].copy()
    q['m0'] = q.xg_h - q.xg_a; q['m1'] = q.m0 + q[adj_gd]; sm = q[f's_{tp}']
    print(f'{NL}   {lab} — ΧΑΝΤΙΚΑΠ (n {len(q)})')
    for k, kl in (('m0', 'μονο μοντελο'), ('m1', 'ΜΕ ενδεκαδα')):
        mse = ((q.gd - q[k]) ** 2).mean(); b, se, n = slope((q[k] - sm).values, (q.gd - sm).values)
        per = [slope((z[k] - z[f's_{tp}']).values, (z.gd - z[f's_{tp}']).values)[0] for _, z in q.groupby('season')]
        br = [brier_ah(r.xg_h + (r[adj_gd] / 2 if k == 'm1' else 0), r.xg_a - (r[adj_gd] / 2 if k == 'm1' else 0), r[f'L_{tp}'], r.gd) for _, r in q.iterrows()]
        br = np.mean([x for x in br if x is not None])
        print(f'      {kl:14s} │ λαθος² {mse:.4f} │ ΚΛΙΣΗ περα απο αγορα {b:+.2f} (±{se:.2f}) · ανα σεζον ' + ' '.join(f'{v:+.2f}' for v in per) + f' │ Brier καλυψης {br:.4f}')
    pm = []
    for _, r in q.iterrows():
        if r[f'oh_{tp}'] != r[f'oh_{tp}']: continue
        res = picks.settle(r.gd, 1, -r[f'L_{tp}'], 2.0)
        if res == 0: continue
        y = 1.0 if res >= 1 else (0.75 if res > 0 else (0.25 if res > -1 else 0.0)); p = (1 / r[f'oh_{tp}']) / (1 / r[f'oh_{tp}'] + 1 / r[f'oa_{tp}']); pm.append((p - y) ** 2)
    print(f'      {"η αγορα (αναφορα)":14s} │ Brier καλυψης {np.mean(pm):.4f}')
    q = M[M[f'T_{tp}'].notna() & M[adj_t].notna() & M.Ta.notna() & M.tg.notna()].copy()
    q['t0'] = q.Ta; q['t1'] = q.Ta + q[adj_t]; tm = q[f'T_{tp}']
    print(f'   {lab} — ΣΥΝΟΛΑ (n {len(q)})')
    for k, kl in (('t0', 'μονο μοντελο'), ('t1', 'ΜΕ ενδεκαδα')):
        mse = ((q.tg - q[k]) ** 2).mean(); b, se, n = slope((q[k] - tm).values, (q.tg - tm).values)
        per = [slope((z[k] - z[f'T_{tp}']).values, (z.tg - z[f'T_{tp}']).values)[0] for _, z in q.groupby('season')]
        print(f'      {kl:14s} │ λαθος² {mse:.4f} │ ΚΛΙΣΗ περα απο αγορα {b:+.2f} (±{se:.2f}) · ανα σεζον ' + ' '.join(f'{v:+.2f}' for v in per))
    print(f'      {"η αγορα":14s} │ λαθος² {((q.tg - tm) ** 2).mean():.4f}')
