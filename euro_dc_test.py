"""
euro_dc_test.py — 28/9/2026 (Στελιος: «μετρα το Dixon-Coles και στα υπολοιπα μοντελα, με τον ιδιο ακριβως τροπο»). ΜΟΝΟ τεστ.
ΕΥΡΩΠΗ χωρις Europa League (UCL + UECL), 2223-2526. λ = live ευρωπαικο stack (euro_inseason_eu_preds.pkl, live['base']:
V4 + prior-EU w=2 + γ −0.47 + UCL_FAV_SCALE 1.16). Σκορ/ημερομηνιες: data_Europe_<sea>.json.
ΕΚΔΟΧΕΣ: ΣΗΜΕΡΑ = DRAW_BOOST 1.13 σε ολα τα ισοπαλα + P(X)×0.85 (οπως euro_shadow_scan.eu_dist)
         DC = κανονικο Dixon-Coles (μονο 0-0/1-0/0-1/1-1), ρ LOSO (log-lik σκορ απο τις αλλες σεζον)
         DC×0.85 = DC + P(X)×0.85 (πληροφοριακα: χρειαζεται ακομα το 0.85;)
ΠΡΟ-ΔΗΛΩΣΗ (ιδια με τα εγχωρια): ΠΕΡΝΑ αν (1) RPS 1Χ2 καλυτερο απο ΣΗΜΕΡΑ σε ≥3/4 σεζον ΚΑΙ (2) picks (κανονες live euro_shadow_scan:
  FotMob+FotMob, 1.70-2.10, UCL fav@10 dog@4, UECL fav@4 dog@10, p_cover, MARGIN) ROI ≥ ΣΗΜΕΡΑ ΚΑΙ μοναδες ≥ ΣΗΜΕΡΑ
  (μεσος ορος Crown/Pinnacle closing).
"""
import sys, json, glob, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
E = pd.read_pickle('euro_inseason_eu_preds.pkl')
lh_all, la_all = E['live']['base']
D = pd.DataFrame(dict(mid=[str(m) for m in E['mids']], season=E['sea'], comp=E['comp'], gd=[int(x) for x in E['gd']],
                      src_h=E['src_h'], src_a=E['src_a'], lh=np.clip(lh_all, .05, 8), la=np.clip(la_all, .05, 8)))
SC = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        if m.get('hs') is not None and m.get('as') is not None:
            SC[str(mid)] = (int(m['hs']), int(m['as']), m.get('date') or m.get('utc'))
D['hg'] = D.mid.map(lambda m: SC.get(m, (np.nan,) * 3)[0]); D['ag'] = D.mid.map(lambda m: SC.get(m, (np.nan,) * 3)[1])
D['date'] = D.mid.map(lambda m: SC.get(m, (None,) * 3)[2])
D = D[D.comp.isin(['ChampionsLeague', 'ConferenceLeague']) & D.hg.notna()].reset_index(drop=True)
SEAS = sorted(D.season.unique()); y = np.where(D.gd > 0, 2, np.where(D.gd == 0, 1, 0))
print(f'ματς UCL+UECL με σκορ: {len(D)} ({D.comp.value_counts().to_dict()}) · πραγματικες ισοπαλιες {100*(D.gd == 0).mean():.1f}%')
F = [math.factorial(i) for i in range(13)]
def mat(lh, la, kind, par):
    ph = np.array([math.exp(-lh) * lh ** i / F[i] for i in range(13)]); pa = np.array([math.exp(-la) * la ** j / F[j] for j in range(13)])
    M = np.outer(ph, pa)
    if kind == 'DB':
        for i in range(13): M[i, i] *= par
    else:
        M[0, 0] *= 1 - lh * la * par; M[0, 1] *= 1 + lh * par; M[1, 0] *= 1 + la * par; M[1, 1] *= 1 - par
    return M / M.sum()
def to_gd(M, xscale):
    d = {}
    for i in range(13):
        for j in range(13): d[i - j] = d.get(i - j, 0) + M[i, j]
    if xscale != 1.0:
        px = d.get(0, 0); k = (1 - xscale * px) / (1 - px); d = {g: (p * xscale if g == 0 else p * k) for g, p in d.items()}
    return d
def p3(d):
    return np.array([sum(v for k, v in d.items() if k > 0), d.get(0, 0), sum(v for k, v in d.items() if k < 0)])
def rps(pm, yy):
    o = np.zeros_like(pm); o[np.arange(len(yy)), 2 - yy] = 1
    return float(np.mean(((np.cumsum(pm, 1) - np.cumsum(o, 1)) ** 2)[:, :2].sum(1) / 2))
RHOS = [0.0, -0.03, -0.06, -0.09, -0.12, -0.15]
LL = {r: np.array([math.log(max(mat(a, b, 'DC', r)[min(int(h), 12), min(int(g_), 12)], 1e-12)) for a, b, h, g_ in zip(D.lh, D.la, D.hg, D.ag)]) for r in RHOS}
RHO = {s_: max(RHOS, key=lambda r: LL[r][(D.season != s_).values].mean()) for s_ in SEAS}
print('ρ LOSO: ' + ' · '.join(f'{s}: {r}' for s, r in RHO.items()) + ' · log-lik ανα ρ: ' + ' · '.join(f'{r}: {LL[r].mean():.4f}' for r in RHOS))
ARMS = {'ΣΗΜΕΡΑ (×1.13 ολα + Χ×0.85)': lambda r: to_gd(mat(r.lh, r.la, 'DB', 1.13), 0.85),
        'DC (ρ LOSO)': lambda r: to_gd(mat(r.lh, r.la, 'DC', RHO[r.season]), 1.0),
        'DC×0.85 (πληροφοριακα)': lambda r: to_gd(mat(r.lh, r.la, 'DC', RHO[r.season]), 0.85)}
DIST = {k: [f(r) for r in D.itertuples()] for k, f in ARMS.items()}
# closing: Crown (Nowgoal cid 3, <= KO+15′) & Pinnacle (toa_pin_hist)
import datetime as _dt
def _ts(d):
    try:
        return int(_dt.datetime.strptime(str(d).replace(' UTC', ''), '%a, %b %d, %Y, %H:%M').replace(tzinfo=_dt.timezone.utc).timestamp())
    except Exception:
        try:
            return int(pd.Timestamp(str(d)[:19]).tz_localize('UTC').timestamp())
        except Exception:
            return None
KO = {m: _ts(d) for m, d in zip(D.mid, D.date) if d and _ts(d)}
def pl(g):
    try:
        s = str(g)
        if '/' in s:
            a, b = s.split('/'); return (float(a) + float(b)) / 2
        return float(s)
    except Exception:
        return None
CROWN = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        r = json.loads(ln)
        if r.get('cid') != 3 or str(r['mid']) not in KO: continue
        rows = []
        for x in r.get('ah') or []:
            try:
                gl = pl(x[2]); rows.append((int(x[0]), -gl, float(x[1]) + 1, float(x[3]) + 1))
            except Exception:
                pass
        rows = sorted(z for z in rows if z[0] <= KO[str(r['mid'])] + 900)
        if rows: CROWN[str(r['mid'])] = rows[-1][1:]
PIN = {}
for ln in open('toa_pin_hist.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r.get('line') is not None and r.get('oh') and r.get('oa'): PIN[str(r['mid'])] = (float(r['line']), float(r['oh']), float(r['oa']))
print(f'closing: Crown {sum(m in CROWN for m in D.mid)} · Pinnacle {sum(m in PIN for m in D.mid)} / {len(D)}')
res = {}
for k in ARMS:
    pm = np.array([p3(d) for d in DIST[k]])
    row = {'ισοπ%': round(100 * pm[:, 1].mean(), 1), 'RPS': round(rps(pm, y), 5)}
    for s_ in SEAS: m = (D.season == s_).values; row[s_] = rps(pm[m], y[m])
    B = []
    for i, r in enumerate(D.itertuples()):
        if not (r.src_h == 'shots' and r.src_a == 'shots'): continue
        ucl = r.comp == 'ChampionsLeague'; tf, td = (0.10, 0.04) if ucl else (0.04, 0.10)
        for book, src in (('Crown', CROWN), ('Pinnacle', PIN)):
            o = src.get(r.mid)
            if not o: continue
            L, oh, oa = o
            for side, ud, odds in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= odds <= 2.10) or abs(ud) < 0.5: continue
                pw, pp = picks.p_cover(DIST[k][i], side, ud); e = pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
                role = 'fav' if ud < 0 else 'dog'
                if e >= (tf if role == 'fav' else td):
                    B.append((book, r.comp, role, r.season, picks.settle(r.gd, side, ud, odds)))
    B = pd.DataFrame(B, columns=['book', 'comp', 'role', 'season', 'pnl'])
    row['_roi'] = np.mean([B[B.book == b].pnl.mean() for b in ('Crown', 'Pinnacle')]); row['_u'] = np.mean([B[B.book == b].pnl.sum() for b in ('Crown', 'Pinnacle')])
    for lab, m in (('ΟΛΑ', np.ones(len(B), bool)), ('UCL φαβ', (B.comp == 'ChampionsLeague') & (B.role == 'fav')), ('UCL dog', (B.comp == 'ChampionsLeague') & (B.role == 'dog')),
                   ('UECL φαβ', (B.comp == 'ConferenceLeague') & (B.role == 'fav')), ('UECL dog', (B.comp == 'ConferenceLeague') & (B.role == 'dog'))):
        d = B[m]
        if not len(d): row[lab] = '—'; continue
        roi = np.mean([d[d.book == b].pnl.mean() for b in ('Crown', 'Pinnacle') if (d.book == b).any()]); u = np.mean([d[d.book == b].pnl.sum() for b in ('Crown', 'Pinnacle')])
        ps = d.groupby('season').pnl.mean()
        row[lab] = f'{len(d)//2} / {100*roi:+.1f}% / {u:+.1f}u / {int((ps > 0).sum())}/{len(ps)}'
    res[k] = row
T = pd.DataFrame(res).T; pd.set_option('display.width', 260)
print(f'\nΑΚΡΙΒΕΙΑ (πραγματικες ισοπαλιες {100*(D.gd == 0).mean():.1f}%)'); print(T[['ισοπ%', 'RPS'] + SEAS].to_string())
print('\nPICKS (≈n ανα βιβλιο / ROI μεσος Crown-Pinnacle / μοναδες / θετικες σεζον)'); print(T[['ΟΛΑ', 'UCL φαβ', 'UCL dog', 'UECL φαβ', 'UECL dog']].to_string())
b = res['ΣΗΜΕΡΑ (×1.13 ολα + Χ×0.85)']; r = res['DC (ρ LOSO)']
w = sum(r[s_] < b[s_] for s_ in SEAS); c1 = w >= 3; c2 = r['_roi'] >= b['_roi'] and r['_u'] >= b['_u']
print(f"\nΚΡΙΣΗ DC: RPS {w}/4 {'✓' if c1 else '✗'} · picks {100*r['_roi']:+.1f}%/{r['_u']:+.1f}u vs {100*b['_roi']:+.1f}%/{b['_u']:+.1f}u {'✓' if c2 else '✗'} → {'ΠΕΡΝΑ' if c1 and c2 else 'ΔΕΝ ΠΕΡΝΑ'}")
