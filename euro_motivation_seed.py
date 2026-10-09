"""
euro_motivation_seed.py — 10/10/2026 (Στελιος: «οι μεγαλες που εχουν προκριθει δεν ειχαν κινητρο για καλυτερη θεση;»). ΒΑΣΗ: euro_motivation.py — 9/10/2026 (Στελιος: «κινητρο στις τελευταιες αγωνιστικες της League Phase — και ποσα γκολ χρειαζεται μια ομαδα»).
Τελευταιες 2 αγωνιστικες League Phase (νεα μορφη 2425/2526: UCL/UEL md7-8, UECL md5-6) και ομιλων (παλια 2223/2324: md5-6), UCL/UEL/UECL.
ΠΡΟΣΟΜΟΙΩΣΗ (4.000) των αγωνων που μενουν με τις προβλεψεις του μοντελου (σημερινη αλυσιδα· Elo οπου λειπει) + ισοβαθμιες
(νεα: ποντοι, διαφορα, γκολ · ομιλοι: ποντοι, μεταξυ τους ποντοι/διαφορα/γκολ, συνολικη διαφορα/γκολ). Για καθε ομαδα:
  ΚΙΝΗΤΡΟ ΝΙΚΗΣ = max στοχου [P(στοχος | νικη) − P(στοχος | ηττα)]  (στοχοι νεα: 8αδα, 24αδα · ομιλοι: 1η, 2αδα, 3αδα)
  ΑΝΑΓΚΗ ΓΚΟΛ   = max στοχου [P(στοχος | νικη 3+) − P(στοχος | νικη 1)]
  ΝΕΚΡΗ = κινητρο < 0.05 (τιποτα δεν αλλαζει)· ΧΑΜΗΛΟ 0.05-0.20· ΥΨΗΛΟ ≥ 0.20.
ΕΡΩΤΗΜΑΤΑ: (1) παιζει η νεκρη χειροτερα απο το μοντελο (γκολ, xG); (2) το ξερει η αγορα (σκορ vs κλεισιμο Crown/SBOBET);
(3) λεφτα: τα picks μας + τυφλα (υπερ/κατα νεκρης, over οταν καποιος θελει γκολ).
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ: διορθωση μοντελου (λ νεκρης ×e^a, λ ομαδας με αναγκη γκολ ×e^b) μονο αν LOSO πιθανοφανεια γκολ καλυτερη σε ≥3/4 σεζον·
κανονας picks μονο αν θετικος ΚΑΙ στα 2 βιβλια ΚΑΙ σε ≥3/4 σεζον· αλλιως μονο ενδειξη στο dashboard.
"""
import sys, io, json, glob, math, contextlib, collections
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
g = {'__name__': 'mot'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('euro_oppadj_test.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
G = g['g']; picks = g['picks']
MIDS, BASE, SEAS = G['MIDS'], g['BASE'], g['SEAS']
LAM = {m: (float(BASE[0][i]), float(BASE[1][i])) for i, m in enumerate(MIDS)}
RNG = np.random.default_rng(7)
NSIM = 4000
# ---------------- Elo για ματς χωρις προβλεψη ----------------
ce = pd.read_csv('clubelo_europe.csv'); ce['mid'] = ce.mid.astype(str)
ELO = {r.mid: (r.home_elo, r.away_elo) for r in ce.itertuples()}
xs, yh, ya = [], [], []
for m, (lh, la) in LAM.items():
    e = ELO.get(m)
    if e and np.isfinite(e[0]) and np.isfinite(e[1]):
        xs.append((e[0] - e[1]) / 100); yh.append(math.log(lh)); ya.append(math.log(la))
xs = np.array(xs); bh = np.polyfit(xs, yh, 1); ba = np.polyfit(xs, ya, 1)
def lam_of(mid):
    if mid in LAM: return LAM[mid], 'model'
    e = ELO.get(mid)
    if e and np.isfinite(e[0]) and np.isfinite(e[1]):
        x = (e[0] - e[1]) / 100; return (math.exp(np.polyval(bh, x)), math.exp(np.polyval(ba, x))), 'elo'
    return (1.45, 1.15), 'μεσος'
# ---------------- αγωνες League Phase ----------------
ef = json.load(open('europe_fixtures.json', encoding='utf-8'))
def sc(s):
    a, b = [int(x) for x in s.replace(' ', '').split('-')]; return a, b
NEWF = {'2425', '2526'}
def rank_new(P, GDv, GF):
    key = P * 1e6 + GDv * 1e3 + GF + RNG.random(P.shape) * 0.5
    order = np.argsort(-key, axis=1); rk = np.empty_like(order); n = P.shape[1]
    rk[np.arange(P.shape[0])[:, None], order] = np.arange(n)[None, :]
    return rk + 1
def rank_group(teams, results):
    """teams: λιστα 4· results: λιστα (h, a, gh, ga). Επιστρεφει dict ομαδα->θεση (κανονες UEFA ομιλων, μεταξυ τους πρωτα)."""
    st = {t: [0, 0, 0] for t in teams}
    for h, a, x, y in results:
        st[h][1] += x - y; st[a][1] += y - x; st[h][2] += x; st[a][2] += y
        if x > y: st[h][0] += 3
        elif x < y: st[a][0] += 3
        else: st[h][0] += 1; st[a][0] += 1
    def resolve(group):
        if len(group) == 1: return group
        sub = {t: [0, 0, 0] for t in group}
        for h, a, x, y in results:
            if h in sub and a in sub:
                sub[h][1] += x - y; sub[a][1] += y - x; sub[h][2] += x; sub[a][2] += y
                if x > y: sub[h][0] += 3
                elif x < y: sub[a][0] += 3
                else: sub[h][0] += 1; sub[a][0] += 1
        return sorted(group, key=lambda t: (sub[t][0], sub[t][1], sub[t][2], st[t][1], st[t][2], RNG.random()), reverse=True)
    byp = collections.defaultdict(list)
    for t in teams: byp[st[t][0]].append(t)
    out = []
    for p in sorted(byp, reverse=True): out += resolve(byp[p])
    return {t: i + 1 for i, t in enumerate(out)}
def thresholds(new, comp):
    return (('2αδα', 2), ('4αδα', 4), ('8αδα', 8), ('16αδα', 16), ('24αδα', 24)) if new else (('1η', 1), ('2αδα', 2), ('3αδα', 3))
MAIN_NEW = ('8αδα', '24αδα')
ROWS = []
nsrc = collections.Counter()
for key, rows in ef.items():
    comp, sea = key.rsplit('_', 1)
    if sea not in SEAS: continue
    lp = [m for m in rows if str(m['round']).isdigit() and m.get('score')]
    new = sea in NEWF
    rmax = max(int(m['round']) for m in lp)
    if new:
        units = [sorted({m['hid'] for m in lp} | {m['aid'] for m in lp})]
    else:   # ομιλοι = συνεκτικες συνιστωσες
        adj = collections.defaultdict(set)
        for m in lp: adj[m['hid']].add(m['aid']); adj[m['aid']].add(m['hid'])
        seen, units = set(), []
        for t in adj:
            if t in seen: continue
            comp_, stack = set(), [t]
            while stack:
                x = stack.pop()
                if x in comp_: continue
                comp_.add(x); stack += list(adj[x] - comp_)
            seen |= comp_; units.append(sorted(comp_))
    for r0 in (rmax - 1, rmax):
        for unit in units:
            us = set(unit)
            um = [m for m in lp if m['hid'] in us]
            played = [m for m in um if int(m['round']) < r0]; rem = [m for m in um if int(m['round']) >= r0]
            idx = {t: i for i, t in enumerate(unit)}
            lams = []
            for m in rem:
                (lh, la), s_ = lam_of(str(m['mid'])); lams.append((lh, la)); nsrc[s_] += 1
            GH = RNG.poisson([l[0] for l in lams], size=(NSIM, len(rem))); GA = RNG.poisson([l[1] for l in lams], size=(NSIM, len(rem)))
            if new:
                P0 = np.zeros(len(unit)); D0 = np.zeros(len(unit)); F0 = np.zeros(len(unit))
                for m in played:
                    x, y = sc(m['score']); h, a = idx[m['hid']], idx[m['aid']]
                    D0[h] += x - y; D0[a] += y - x; F0[h] += x; F0[a] += y
                    P0[h] += 3 if x > y else (1 if x == y else 0); P0[a] += 3 if y > x else (1 if x == y else 0)
                P = np.tile(P0, (NSIM, 1)); Dg = np.tile(D0, (NSIM, 1)); Fg = np.tile(F0, (NSIM, 1))
                for j, m in enumerate(rem):
                    h, a = idx[m['hid']], idx[m['aid']]; x, y = GH[:, j], GA[:, j]
                    P[:, h] += np.where(x > y, 3, np.where(x == y, 1, 0)); P[:, a] += np.where(y > x, 3, np.where(x == y, 1, 0))
                    Dg[:, h] += x - y; Dg[:, a] += y - x; Fg[:, h] += x; Fg[:, a] += y
                RK = rank_new(P, Dg, Fg)
            else:
                base_res = [(m['hid'], m['aid']) + sc(m['score']) for m in played]
                RK = np.zeros((NSIM, len(unit)), int)
                for s in range(NSIM):
                    res = base_res + [(m['hid'], m['aid'], int(GH[s, j]), int(GA[s, j])) for j, m in enumerate(rem)]
                    rk = rank_group(unit, res)
                    for t, p in rk.items(): RK[s, idx[t]] = p
            for j, m in enumerate(rem):
                if int(m['round']) != r0: continue
                for side, t in ((1, m['hid']), (-1, m['aid'])):
                    mg = (GH[:, j] - GA[:, j]) * side; rk = RK[:, idx[t]]
                    cats = {'L': mg < 0, 'D': mg == 0, 'W': mg > 0, 'W1': mg == 1, 'W3': mg >= 3, 'W2': mg >= 2}
                    best_ws, best_gn, probs, wsd = 0.0, 0.0, {}, {}
                    for lab, k in thresholds(new, comp):
                        p = {c: (rk[msk] <= k).mean() if msk.sum() >= 30 else np.nan for c, msk in cats.items()}
                        probs[lab] = p
                        ws = p['W'] - p['L'] if np.isfinite(p['W']) and np.isfinite(p['L']) else np.nan
                        w3 = p['W3'] if np.isfinite(p['W3']) else p['W2']
                        gn = w3 - p['W1'] if np.isfinite(w3) and np.isfinite(p['W1']) else 0.0
                        wsd[lab] = ws if np.isfinite(ws) else 0.0
                        if (not new) or lab in MAIN_NEW:
                            best_ws = max(best_ws, ws if np.isfinite(ws) else 0.0); best_gn = max(best_gn, gn)
                    ROWS.append(dict(mid=str(m['mid']), sea=sea, comp=comp, new=new, rnd=r0, side=side, team=m['hname'] if side == 1 else m['aname'],
                                     ws=best_ws, gn=best_gn, score=m['score'], probs=probs, wsd=wsd))
M = pd.DataFrame(ROWS)
M['ws_seed'] = [max([v for k, v in d.items() if k in ('2αδα', '4αδα', '16αδα')] or [0.0]) if n else 0.0 for d, n in zip(M.wsd, M.new)]
M['status'] = np.where(M.ws < 0.05, 'νεκρη', np.where(M.ws < 0.20, 'χαμηλο', 'υψηλο'))
M['needg'] = M.gn >= 0.10
print(f'προβλεψεις για προσομοιωση: {dict(nsrc)}')
print(f'ομαδα-ματς τελευταιων 2 αγωνιστικων: {len(M)} · ' + ', '.join(f'{k}: {v}' for k, v in M.status.value_counts().items()) + f' · θελει γκολ (≥10%): {int(M.needg.sum())}')
print('   ανα μορφη/αγωνιστικη: ' + ' · '.join(f'{"νεα" if n else "ομιλοι"} {"τελευταια" if r == "last" else "προτελευταια"}: ' + ', '.join(f'{k} {v}' for k, v in x.status.value_counts().items())
      for (n, r), x in M.assign(r=np.where(M.groupby(['sea', 'comp']).rnd.transform('max') == M.rnd, 'last', 'prev')).groupby(['new', 'r'])))
# ---------------- ενωση με μοντελο / αγορα / xG ----------------
XG = {}
for sea in SEAS:
    for mid, mm in json.load(open(f'data_Europe_{sea}.json', encoding='utf-8')).items():
        if not mm.get('shots'): continue
        h, a = int(mm['home']['id']), int(mm['away']['id']); agg = {h: 0.0, a: 0.0}
        for s in mm['shots']:
            if s.get('xg') is not None and s.get('tid') in agg: agg[s['tid']] += 0.25 if s.get('sit') == 'Penalty' else s['xg']
        XG[str(mid)] = (agg[h], agg[a])
def parse_line(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception:
        return None
KO = {str(m['mid']): int(pd.Timestamp(m['utc']).timestamp()) for v in ef.values() for m in v if m.get('utc')}
CL = {}   # (mid, book) -> dict(ah=(home line, oh, oa), ou=(line, over, under))
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for line in open(f, encoding='utf-8'):
        r = json.loads(line)
        bk = {3: 'Crown', 31: 'SBOBET'}.get(r['cid'])
        mid = str(r['mid']); ko = KO.get(mid)
        if bk is None or ko is None: continue
        d = {}
        ah = sorted((int(mt), -parse_line(gg), float(u) + 1, float(dn) + 1) for mt, u, gg, dn in (r.get('ah') or [])
                    if mt and parse_line(gg) is not None and int(mt) <= ko + 900)
        ou = sorted((int(mt), parse_line(gg), float(o) + 1, float(un) + 1) for mt, o, gg, un in (r.get('ou') or [])
                    if mt and parse_line(gg) is not None and int(mt) <= ko + 900)
        if ah: d['ah'] = ah[-1][1:]
        if ou: d['ou'] = ou[-1][1:]
        if d: CL[(mid, bk)] = d
def msup(L, oh, oa, T):
    tq = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -4.5, 4.5
    for _ in range(24):
        s = (lo + hi) / 2; d = picks.gd_dist(max((T + s) / 2, .05), max((T - s) / 2, .05)); w, p = picks.p_cover(d, 1, L)
        if w / max(1 - p, 1e-9) < tq: lo = s
        else: hi = s
    return (lo + hi) / 2
def settle_ou(tot, L, o, over=True):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; r = 0.0
    for p in parts:
        d = (tot - p) if over else (p - tot)
        r += ((o - 1) if d > 0 else (0 if d == 0 else -1)) / len(parts)
    return r
rec = []
for r in M.itertuples():
    lam = LAM.get(r.mid)
    gh, ga = sc(r.score); gf, gaa = (gh, ga) if r.side == 1 else (ga, gh)
    x = XG.get(r.mid); xf, xa = ((x[0], x[1]) if r.side == 1 else (x[1], x[0])) if x else (np.nan, np.nan)
    lf, la = ((lam[0], lam[1]) if r.side == 1 else (lam[1], lam[0])) if lam else (np.nan, np.nan)
    row = dict(mid=r.mid, sea=r.sea, comp=r.comp, new=r.new, side=r.side, team=r.team, status=r.status, needg=r.needg, ws=r.ws, gn=r.gn, ws_seed=r.ws_seed, wsd=r.wsd, rnd=r.rnd,
               gf=gf, ga=gaa, xf=xf, xa=xa, lf=lf, la=la, tot=gh + ga)
    for bk in ('Crown', 'SBOBET'):
        c = CL.get((r.mid, bk), {})
        if 'ah' in c and lam:
            L, oh, oa = c['ah']; ms = msup(L, oh, oa, lam[0] + lam[1]) * r.side
            Lt, ot = (L, oh) if r.side == 1 else (-L, oa)
            row[f'mkt_{bk}'] = ms; row[f'ah_{bk}'] = picks.settle(gh - ga, r.side, Lt, ot) if 1.5 <= ot <= 2.6 else np.nan
            row[f'ahL_{bk}'] = Lt
        if 'ou' in c:
            L, o, u = c['ou']; row[f'ov_{bk}'] = settle_ou(gh + ga, L, o, True); row[f'un_{bk}'] = settle_ou(gh + ga, L, u, False); row[f'ouL_{bk}'] = L
    rec.append(row)
R = pd.DataFrame(rec)
R['mkt'] = R[['mkt_Crown', 'mkt_SBOBET']].mean(axis=1)
OPP = R.set_index(['mid', 'side'])
R['opp_status'] = [OPP.loc[(m, -s), 'status'] if (m, -s) in OPP.index else '?' for m, s in zip(R.mid, R.side)]
R['opp_needg'] = [bool(OPP.loc[(m, -s), 'needg']) if (m, -s) in OPP.index else False for m, s in zip(R.mid, R.side)]
def se(x): x = x.dropna(); return x.std() / math.sqrt(len(x)) if len(x) > 1 else np.nan
D = R[R.status == 'νεκρη'].copy()
D['kind'] = np.where(~D.new, 'ομιλοι (παλια) — ολα κλειδωμενα', np.where(D.ws_seed >= 0.05, 'νεα — ΚΙΝΗΤΡΟ ΘΕΣΗΣ (1-2/1-4/9-16)', 'νεα — εντελως νεκρη'))
print('«ΝΕΚΡΕΣ» (κινητρο 8αδας/24αδας < 0.05) — χωρισμα κατα κινητρο ΘΕΣΗΣ στη νεα μορφη:')
print(f'   {"":40s} {"n":>4s} | γκολ υπερ−λ   xG υπερ−λ  | διαφορα−μοντ  διαφορα−αγορα | τυφλο χαντικαπ υπερ')
for k in sorted(D.kind.unique()):
    x = D[D.kind == k]; dm = (x.gf - x.ga) - (x.lf - x.la); dk = (x.gf - x.ga) - x.mkt; v = x[['ah_Crown', 'ah_SBOBET']].stack()
    print(f'   {k:40s} {len(x):4d} | {(x.gf - x.lf).mean():+.2f}±{se(x.gf - x.lf):.2f} {(x.xf - x.lf).mean():+.2f}±{se(x.xf - x.lf):.2f} | {dm.mean():+.2f}±{se(dm):.2f}  {dk.mean():+.2f}±{se(dk):.2f} | {100 * v.mean():+.1f}% (n{len(v) // 2})')
print(chr(10) + 'ΝΕΑ ΜΟΡΦΗ — ποιο κινητρο θεσης ειχαν οι «νεκρες» (P(στοχος|νικη) − P(στοχος|ηττα)):')
X = D[D.new]
for r in X.sort_values('ws_seed', ascending=False).itertuples():
    w = r.wsd
    print(f'   {r.sea} {r.comp[:4]} αγ.{r.rnd} {r.team[:20]:20s} σκορ ομαδας {r.gf}-{r.ga} · 2αδα {w.get("2αδα", 0):.2f} · 4αδα {w.get("4αδα", 0):.2f} · 8αδα {w.get("8αδα", 0):.2f} · 16αδα {w.get("16αδα", 0):.2f} · 24αδα {w.get("24αδα", 0):.2f}')
R.to_pickle('euro_motivation_seed_rows.pkl')
