# -*- coding: utf-8 -*-
"""xi_pred2627.py — 21/10/2026 (Στελιος: «τρεξε και τις φετινες»). ΦΕΤΙΝΕΣ ΠΡΟΒΛΕΠΟΜΕΝΕΣ ενδεκαδες (2026-27, CORE7 εκτος NL/PT):
  predicted11 (EPL/LaLiga/SerieA, projected_lineups.jsonl) · ligainsider (Bundesliga) & fantasy-coach (Ligue 1) (projected_fc.jsonl, ανα ομαδα)
  → η ΤΕΛΕΥΤΑΙΑ εκδοχη που υπηρχε 24ω και 6ω πριν τη σεντρα (χρονοσφραγιδα snapshot).
ΙΔΙΑ ΦΟΡΜΟΥΛΑ / ΟΡΙΣΜΟΣ με xi_predicted_eval: ενδεκαδα vs ΣΥΝΗΘΙΣΜΕΝΗ (11 με τα περισσοτερα λεπτα στα 10 τελευταια ματς πρωταθληματος:
  1 τερματοφυλακας + 10) — αξια (μεσος ln), εμπιστοσυνη (10 ματς, λεπτα), θεσεις, xGI. Συντελεστες απο 2223-2526 (πραγματικη vs συνηθισμενη).
ΜΟΝΤΕΛΟ: match_projections_archive (παγωμενη προ-αγωνα live προβλεψη) · ΑΓΟΡΑ: Pinnacle (odds_history.jsonl) 24ω / 6ω / 55′ / κλεισιμο."""
import sys, io, json, glob, re, math, bisect, contextlib, collections, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks, euro_shadow_scan as ES
NL = chr(10); UTC = dt.timezone.utc
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
# ---------- συντελεστες απο τις προηγουμενες σεζον (πραγματικη vs συνηθισμενη) ----------
src = open('xi_xgi_eval.py', encoding='utf-8').read(); g0 = {'__name__': 'x0'}
with contextlib.redirect_stdout(_Q()): exec(src[:src.index("print(f'ματς {len(D)} · με xGI")], g0)
D0 = g0['D'].merge(pd.read_csv('xi_pregame_rows.csv', dtype={'mid': str}), on='mid', how='left')
D0['g_V'] = D0.aV_h - D0.aV_a; D0['g_T'] = D0.aT_h - D0.aT_a
for k in ('VO', 'VD', 'TO', 'TD', 'XGI'): D0[f't_{k}'] = D0[f'a{k}_h'] + D0[f'a{k}_a']
def coef(cols, y):
    q = D0[D0[y].notna() & D0.g_V.notna()]; X = np.column_stack([np.ones(len(q))] + [q[c].fillna(0).values for c in cols]); return np.linalg.lstsq(X, q[y].values, rcond=None)[0][1:]
bG = coef(['g_V', 'g_T'], 'r_xgd'); TK = ('VO', 'VD', 'TO', 'TD', 'XGI'); bT = coef([f't_{k}' for k in TK], 'r_tx')
print(f'συντελεστες (2223-2526): χαντικαπ αξια {bG[0]:+.3f} εμπιστ. {bG[1]:+.3f} │ συνολα ' + ' '.join(f'{k} {v:+.3f}' for k, v in zip(TK, bT)))
# ---------- ματς (ολες οι σεζον, για το ιστορικο) ----------
LG = ('EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'Eredivisie', 'PrimeiraLiga')
FM = {}
for lg in LG:
    for f in glob.glob(f'data_{lg}_*.json'):
        sea = re.search(r'_(\d{4})\.json$', f).group(1)
        for k, v in json.load(open(f, encoding='utf-8')).items():
            try: d = dt.datetime.strptime(v['date'], '%a, %b %d, %Y, %H:%M UTC').replace(tzinfo=UTC)
            except Exception: continue
            FM[str(k)] = dict(lg=lg, sea=sea, date=d, hid=v['home']['id'], aid=v['away']['id'], hs=v.get('hs'), as_=v.get('as'))
SQ = json.load(open('core7_squads.json', encoding='utf-8')); PM = json.load(open('player_matches.json', encoding='utf-8'))
PM.update(json.load(open('player_matches_2627.json', encoding='utf-8')))
for k, v in json.load(open('squads_2627.json', encoding='utf-8')).items():
    for fs in ('h', 'a'):
        if v.get(fs) and 'st' not in v[fs]:
            v[fs]['st'] = [e[0] for e in ((PM.get(k) or {}).get(fs) or {}).get('p', []) or [] if len(e) > 4 and e[4] == 1]
    SQ.setdefault(k, v)
X = {}
for l in open('player_xgi.jsonl', encoding='utf-8'):
    r = json.loads(l); X[r['mid']] = r['p']
VAL = {}
for f in ('core7_player_values.json', 'euro_player_values.json'):
    for k, v in json.load(open(f, encoding='utf-8')).items():
        if v.get('hist') and str(k) not in VAL: VAL[str(k)] = [(h[0], h[1]) for h in v['hist'] if h[1]]
CURV = {}                                                        # φετινες αξιες απο τις ενδεκαδες FotMob (για νεους παικτες)
for k, v in PM.items():
    for fs in ('h', 'a'):
        for e in ((v or {}).get(fs) or {}).get('p', []) or []:
            if len(e) > 2 and e[2]: CURV[str(e[0])] = e[2]
def value_at(pid, ds):
    h = VAL.get(pid)
    if not h: return CURV.get(pid)
    v = None
    for t, x in h:
        if t <= ds: v = x
        else: break
    return v if v is not None else h[0][1]
ORDER = sorted([k for k in FM if k in SQ and SQ[k].get('h') and SQ[k].get('a')], key=lambda k: FM[k]['date'])
POS = {}
for k in ORDER:
    for s in ('h', 'a'):
        for e in ((PM.get(k) or {}).get(s) or {}).get('p', []) or []:
            POS[str(e[0])] = e[3] if e[3] in (0, 1, 2, 3) else 2
acc = collections.defaultdict(lambda: [0.0, 0.0])
for k in ORDER:
    for pid, (mn, xg, xa) in (X.get(k) or {}).items():
        if mn and mn > 0: a = acc[POS.get(pid, 2)]; a[0] += xg + xa; a[1] += mn / 90.0
MU = {p: v[0] / v[1] for p, v in acc.items() if v[1] > 0}
# ---------- φετινες προβλεπομενες ----------
PL = [json.loads(l) for l in open('projected_lineups.jsonl', encoding='utf-8')]
P11 = collections.defaultdict(list)          # (home_tid, away_tid, ko date) -> [(ts, xi_h, xi_a)]
for r in PL:
    try: ts = dt.datetime.fromisoformat(r['ts'].replace('Z', '+00:00'))
    except Exception: continue
    xh = [str(p['pid']) for p in r.get('xi_home') or [] if p.get('pid')]; xa = [str(p['pid']) for p in r.get('xi_away') or [] if p.get('pid')]
    P11[(str(r.get('home_tid')), str(r.get('away_tid')), str(r.get('ko'))[:10])].append((ts, xh, xa))
FC = collections.defaultdict(list)           # tid -> [(ts, xi)]
for l in open('projected_fc.jsonl', encoding='utf-8'):
    r = json.loads(l)
    try: ts = dt.datetime.fromisoformat(r['ts'].replace('Z', '+00:00'))
    except Exception: continue
    FC[str(r.get('tid'))].append((ts, [str(p['pid']) for p in r.get('xi') or [] if p.get('pid')]))
def pred_at(m, hrs):
    cut = m['date'] - dt.timedelta(hours=hrs)
    c = [x for x in P11.get((str(m['hid']), str(m['aid']), m['date'].strftime('%Y-%m-%d')), []) if x[0] <= cut]
    if c:
        c.sort(key=lambda x: x[0]); return c[-1][1], c[-1][2], 'predicted11'
    out = []
    for tid in (m['hid'], m['aid']):
        z = [x for x in FC.get(str(tid), []) if x[0] <= cut and x[0] >= m['date'] - dt.timedelta(days=6)]
        z.sort(key=lambda x: x[0]); out.append(z[-1][1] if z else None)
    if out[0] and out[1]: return out[0], out[1], 'ligainsider/fantasy-coach'
    return None, None, None
# ---------- walk-forward ----------
TEAM_HIST = collections.defaultdict(list); STX = {}
ROWS = []
for k in ORDER:
    m = FM[k]; ds = m['date'].strftime('%Y-%m-%d')
    if m['sea'] == '2627' and m['lg'] not in ('Eredivisie', 'PrimeiraLiga'):
        rec = dict(mid=k, lg=m['lg'], date=ds)
        p24 = pred_at(m, 24); p6 = pred_at(m, 6); rec['src'] = p24[2] or p6[2]
        for fs, tid, i in (('h', m['hid'], 0), ('a', m['aid'], 1)):
            hist = TEAM_HIST[tid][-10:]
            if len(hist) < 4: rec['skip'] = True; continue
            mins = collections.Counter()
            for h in hist:
                for p, mn in h.items(): mins[p] += mn
            pool = [p for p, mn in mins.most_common() if mn > 0]
            usual = [p for p in pool if POS.get(p, 2) == 0][:1] + [p for p in pool if POS.get(p, 2) != 0][:10]
            def trust(p):
                ins = [h[p] for h in hist if p in h]; return sum(ins) / (90.0 * len(ins)) if ins else 0.3
            def lv(p):
                v = value_at(p, ds); return math.log(v) if v else None
            def xgi(p):
                s = STX.get(p); mu = MU.get(POS.get(p, 2), 0.25); return (s[0] + 5 * mu) / (s[1] + 5) if s else mu
            def feats(xi):
                vs = [lv(p) for p in xi]; kn = [x for x in vs if x is not None]
                f = dict(V=float(np.mean(kn)) if kn else np.nan, T=float(np.mean([trust(p) for p in xi])), XGI=sum(xgi(p) for p in xi))
                f['TO'] = float(np.mean([trust(p) for p in xi if POS.get(p, 2) in (2, 3)] or [np.nan])); f['TD'] = float(np.mean([trust(p) for p in xi if POS.get(p, 2) in (0, 1)] or [np.nan]))
                f['VO'] = float(np.mean([x for p, x in zip(xi, vs) if x is not None and POS.get(p, 2) in (2, 3)] or [np.nan]))
                f['VD'] = float(np.mean([x for p, x in zip(xi, vs) if x is not None and POS.get(p, 2) in (0, 1)] or [np.nan]))
                return f
            F = feats(usual)
            for lab, xi in (('act', [str(p) for p in SQ[k][fs]['st']]), ('p24', p24[i]), ('p6', p6[i])):
                if xi and len(xi) >= 9:
                    G = feats(xi)
                    for key in F: rec[f'{lab}_{key}_{fs}'] = G[key] - F[key]
        ROWS.append(rec)
    for fs, tid in (('h', m['hid']), ('a', m['aid'])):
        TEAM_HIST[tid].append({str(p): mn for p, mn in SQ[k][fs]['p'].items()})
    for pid, (mn, xg, xa) in (X.get(k) or {}).items():
        if mn and mn > 0:
            s = STX.get(pid, [0.0, 0.0]); STX[pid] = [s[0] * 0.95 + xg + xa, s[1] * 0.95 + mn / 90.0]
R = pd.DataFrame(ROWS); R = R[R.get('skip', pd.Series(False, index=R.index)).isna() | (R.get('skip') != True)] if 'skip' in R else R
for lab in ('act', 'p24', 'p6'):
    if f'{lab}_V_h' not in R: continue
    R[f'fg_{lab}'] = bG[0] * (R[f'{lab}_V_h'] - R[f'{lab}_V_a']).fillna(0) + bG[1] * (R[f'{lab}_T_h'] - R[f'{lab}_T_a'])
    R[f'ft_{lab}'] = sum(b * (R[f'{lab}_{k}_h'].fillna(0) + R[f'{lab}_{k}_a'].fillna(0)) for b, k in zip(bT, TK))
# ---------- μοντελο, αποτελεσμα, αγορα ----------
A = json.load(open('match_projections_archive.json', encoding='utf-8'))
R['xh'] = R.mid.map(lambda k: (A.get(k) or {}).get('home_adj_xg')); R['xa'] = R.mid.map(lambda k: (A.get(k) or {}).get('away_adj_xg'))
R['gd'] = R.mid.map(lambda k: (FM[k]['hs'] - FM[k]['as_']) if FM[k]['hs'] is not None else np.nan); R['tg'] = R.mid.map(lambda k: (FM[k]['hs'] + FM[k]['as_']) if FM[k]['hs'] is not None else np.nan)
OH = collections.defaultdict(list)
for l in open('odds_history.jsonl', encoding='utf-8'):
    r = json.loads(l)
    if r.get('inplay'): continue
    try: t = dt.datetime.fromisoformat(r['t'].replace('Z', '+00:00')).timestamp()
    except Exception: continue
    OH[(int(r['hid']), int(r['aid']), str(r['ko'])[:10])].append((t, r.get('line'), r.get('oh'), r.get('oa'), r.get('ou')))
for v in OH.values(): v.sort(key=lambda x: x[0])
S_GRID = np.round(np.arange(-4.0, 4.001, 0.02), 3); QH = {}
for L in np.round(np.arange(-4.0, 4.001, 0.25), 2):
    q = []
    for s in S_GRID:
        d = picks.gd_dist(max((2.7 + s) / 2, .05), max((2.7 - s) / 2, .05)); pw, pp = picks.p_cover(d, 1, L); q.append(pw / max(pw + (1 - pw - pp), 1e-9))
    QH[L] = np.array(q)
T_GRID = np.round(np.arange(0.8, 6.0, 0.02), 3); IDXT = np.add.outer(np.arange(13), np.arange(13)); KS = np.arange(25); QO = {}
for L in np.round(np.arange(0.5, 6.01, 0.25), 2):
    q = []
    for T in T_GRID:
        Mx = picks.score_matrix_dom(T / 2, T / 2); tt = np.bincount(IDXT.ravel(), weights=np.asarray(Mx).ravel(), minlength=25)
        parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; po = pu = 0
        for x in parts: po += tt[KS > x + .01].sum() / len(parts); pu += tt[KS < x - .01].sum() / len(parts)
        q.append(po / max(po + pu, 1e-9))
    QO[L] = np.array(q)
def sup(lh, oh, oa):
    L = round(round(lh * 4) / 4, 2)
    if L not in QH or not oh or not oa: return np.nan
    q = (1 / oh) / (1 / oh + 1 / oa); arr = QH[L]
    return float(np.interp(q, arr[::-1], S_GRID[::-1])) if arr[0] > arr[-1] else float(np.interp(q, arr, S_GRID))
def tot(ou):
    if not ou: return np.nan
    L, o, u = ou; L = round(round(float(L) * 4) / 4, 2)
    if L not in QO: return np.nan
    q = (1 / o) / (1 / o + 1 / u); return float(np.interp(q, QO[L], T_GRID))
TPS = (('24ω', 1440), ('6ω', 360), ('55′', 55), ('κλεισ.', 0))
for lab, _ in TPS:
    for c in ('s', 'T', 'L', 'oh', 'oa', 'OL', 'oo', 'ou'): R[f'{c}_{lab}'] = np.nan
for i, r in R.iterrows():
    m = FM[r.mid]; seq = OH.get((int(m['hid']), int(m['aid']), m['date'].strftime('%Y-%m-%d')))
    if not seq: continue
    ts = [x[0] for x in seq]; ko = m['date'].timestamp()
    for lab, mins in TPS:
        j = bisect.bisect_right(ts, ko - mins * 60) - 1
        if j < 0: continue
        _, L, oh, oa, ou = seq[j]
        if L is not None and oh and oa:
            R.at[i, f's_{lab}'] = sup(L, oh, oa); R.at[i, f'L_{lab}'] = L; R.at[i, f'oh_{lab}'] = oh; R.at[i, f'oa_{lab}'] = oa
        if ou:
            R.at[i, f'T_{lab}'] = tot(ou); R.at[i, f'OL_{lab}'] = ou[0]; R.at[i, f'oo_{lab}'] = ou[1]; R.at[i, f'ou_{lab}'] = ou[2]
c = np.corrcoef(R['s_κλεισ.'].fillna(0), R.gd.fillna(0))[0, 1]
if c < 0:
    for lab, _ in TPS: R[f's_{lab}'] = -R[f's_{lab}']
R.to_csv('xi_pred2627_rows.csv', index=False)
Q = R[R.xh.notna() & R.gd.notna() & R['s_24ω'].notna()]
print(f'ματς 2026-27 (5 λιγκες): {len(R)} · με προβλεπομενη 24ω: {R.fg_p24.notna().sum() if "fg_p24" in R else 0} · 6ω: {R.fg_p6.notna().sum() if "fg_p6" in R else 0} · με τιμες & αποτελεσμα: {len(Q)}')
print('πηγες:', R.src.value_counts().to_dict())
print(f'ομοιοτητα διορθωσης με την επισημη: 24ω {Q[["fg_p24", "fg_act"]].corr().iloc[0, 1]:.2f} · 6ω {Q[["fg_p6", "fg_act"]].corr().iloc[0, 1]:.2f}')
def slope(x, y):
    m = np.isfinite(x) & np.isfinite(y); x, y = x[m], y[m]
    if len(x) < 30: return np.nan, np.nan, len(x)
    Xm = np.column_stack([np.ones(len(x)), x]); b = np.linalg.lstsq(Xm, y, rcond=None)[0]; res = y - Xm @ b
    return b[1], np.sqrt((res ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum()), len(x)
print(f'{NL}{"=" * 130}{NL}Α. ΧΑΝΤΙΚΑΠ — λαθος² & ΚΛΙΣΗ περα απο την αγορα (Pinnacle)')
for v, lab in (('none', 'σκετο μοντελο'), ('p24', 'ΠΡΟΒΛΕΠΟΜΕΝΗ 24ω'), ('p6', 'ΠΡΟΒΛΕΠΟΜΕΝΗ 6ω'), ('act', 'ΕΠΙΣΗΜΗ')):
    q = Q if v == 'none' else Q[Q[f'fg_{v}'].notna()]
    m = (q.xh - q.xa) + (0 if v == 'none' else q[f'fg_{v}'])
    parts = [f'{tp} {slope((m - q[f"s_{tp}"]).values, (q.gd - q[f"s_{tp}"]).values)[0]:+.2f}±{slope((m - q[f"s_{tp}"]).values, (q.gd - q[f"s_{tp}"]).values)[1]:.2f}' for tp in ('24ω', '6ω', '55′')]
    print(f'   {lab:20s} n {len(q):4d} │ λαθος² {((q.gd - m) ** 2).mean():.4f} │ κλιση ' + ' · '.join(parts))
print(f'{NL}Β. ΚΙΝΗΣΗ ΑΓΟΡΑΣ (Pinnacle) προς τη διορθωση της προβλεπομενης 24ω')
for kind, f, pre in (('χαντικαπ', 'fg_p24', 's'), ('συνολα', 'ft_p24', 'T')):
    q = Q[Q[f].notna()]
    print(f'   {kind:9s}: ' + ' · '.join(f'{a}→{b} {slope(q[f].values, (q[f"{pre}_{b}"] - q[f"{pre}_{a}"]).values)[0]:+.2f}±{slope(q[f].values, (q[f"{pre}_{b}"] - q[f"{pre}_{a}"]).values)[1]:.2f}'
                                  for a, b in (('24ω', '6ω'), ('6ω', '55′'), ('55′', 'κλεισ.'))))
q = Q[Q.fg_p24.notna()]; thr = q.fg_p24.abs().quantile(.80); top = q[q.fg_p24.abs() >= thr]; sg = np.sign(top.fg_p24)
print(f'   TOP 20% |διορθωσης| (n {len(top)}, μεση {top.fg_p24.abs().mean():.2f}): κινηση χαντικαπ προς τη μερια της απο 24ω: '
      + ' · '.join(f'{t} {((top[f"s_{t}"] - top["s_24ω"]) * sg).mean():+.3f}' for t in ('6ω', '55′', 'κλεισ.')))
