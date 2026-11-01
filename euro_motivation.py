"""
euro_motivation.py — 9/10/2026 (Στελιος: «κινητρο στις τελευταιες αγωνιστικες της League Phase — και ποσα γκολ χρειαζεται μια ομαδα»).
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
    return (('8αδα', 8), ('24αδα', 24)) if new else (('1η', 1), ('2αδα', 2), ('3αδα', 3))
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
                    best_ws, best_gn, probs = 0.0, 0.0, {}
                    for lab, k in thresholds(new, comp):
                        p = {c: (rk[msk] <= k).mean() if msk.sum() >= 30 else np.nan for c, msk in cats.items()}
                        probs[lab] = p
                        ws = p['W'] - p['L'] if np.isfinite(p['W']) and np.isfinite(p['L']) else np.nan
                        w3 = p['W3'] if np.isfinite(p['W3']) else p['W2']
                        gn = w3 - p['W1'] if np.isfinite(w3) and np.isfinite(p['W1']) else 0.0
                        best_ws = max(best_ws, ws if np.isfinite(ws) else 0.0); best_gn = max(best_gn, gn)
                    ROWS.append(dict(mid=str(m['mid']), sea=sea, comp=comp, new=new, rnd=r0, side=side, team=m['hname'] if side == 1 else m['aname'],
                                     ws=best_ws, gn=best_gn, score=m['score'], probs=probs))
M = pd.DataFrame(ROWS)
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
    row = dict(mid=r.mid, sea=r.sea, comp=r.comp, new=r.new, side=r.side, team=r.team, status=r.status, needg=r.needg, ws=r.ws, gn=r.gn,
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
print('\n1. ΠΑΙΖΕΙ ΧΕΙΡΟΤΕΡΑ; (οπτικη ομαδας — πραγματικο − μοντελο, και πραγματικη διαφορα − αγορα)')
print(f'   {"κατασταση ομαδας":30s} {"n":>4s} | γκολ υπερ−λ    κατα−λ   | xG υπερ−λ   κατα−λ  | διαφορα−μοντ  διαφορα−αγορα')
for lab, msk in (('ΝΕΚΡΗ', R.status == 'νεκρη'), ('χαμηλο κινητρο', R.status == 'χαμηλο'), ('ΥΨΗΛΟ κινητρο', R.status == 'υψηλο'),
                 ('νεκρη vs ζωντανη (υψηλο)', (R.status == 'νεκρη') & (R.opp_status == 'υψηλο')),
                 ('νεκρη vs νεκρη', (R.status == 'νεκρη') & (R.opp_status == 'νεκρη')),
                 ('ΘΕΛΕΙ ΓΚΟΛ (≥10%)', R.needg)):
    x = R[msk]; dm = (x.gf - x.ga) - (x.lf - x.la); dk = (x.gf - x.ga) - x.mkt
    print(f'   {lab:30s} {len(x):4d} | {(x.gf - x.lf).mean():+.2f}±{se(x.gf - x.lf):.2f} {(x.ga - x.la).mean():+.2f}±{se(x.ga - x.la):.2f} | '
          f'{(x.xf - x.lf).mean():+.2f}±{se(x.xf - x.lf):.2f} {(x.xa - x.la).mean():+.2f}±{se(x.xa - x.la):.2f} | {dm.mean():+.2f}±{se(dm):.2f}  {dk.mean():+.2f}±{se(dk):.2f}')
print('\n   ΣΥΝΟΛΑ ΓΚΟΛ ματς οπου καποια ομαδα θελει γκολ vs οχι (πραγματικο − μοντελο · − γραμμη Crown/SBOBET):')
Mm = R.groupby('mid').agg(tot=('tot', 'first'), ltot=('lf', 'sum'), needg=('needg', 'max'), ouC=('ouL_Crown', 'first'), ouS=('ouL_SBOBET', 'first'),
                          ovC=('ov_Crown', 'first'), ovS=('ov_SBOBET', 'first'), unC=('un_Crown', 'first'), unS=('un_SBOBET', 'first'), sea=('sea', 'first'),
                          dead=('status', lambda s: (s == 'νεκρη').sum()))
for lab, msk in (('καποιος θελει γκολ', Mm.needg), ('κανεις', ~Mm.needg), ('2 νεκρες', Mm.dead == 2), ('1 νεκρη', Mm.dead == 1), ('0 νεκρες', Mm.dead == 0)):
    x = Mm[msk]; ln = x[['ouC', 'ouS']].mean(axis=1)
    ov = x[['ovC', 'ovS']].mean(axis=1); un = x[['unC', 'unS']].mean(axis=1); ps = x.assign(o=ov).groupby('sea').o.mean()
    print(f'   {lab:20s} n{len(x):4d} · γκολ {x.tot.mean():.2f} · μοντελο {x.ltot.mean():.2f} · γραμμη {ln.mean():.2f} · OVER {100 * ov.mean():+.1f}% ({int((ps > 0).sum())}/{ps.size}) · UNDER {100 * un.mean():+.1f}%')
print('\n2. ΤΥΦΛΑ ΧΑΝΤΙΚΑΠ (μεσος Crown/SBOBET, 1.50-2.60): υπερ της ομαδας')
for lab, msk in (('νεκρη (ολες)', R.status == 'νεκρη'), ('νεκρη vs υψηλο', (R.status == 'νεκρη') & (R.opp_status == 'υψηλο')),
                 ('νεκρη ως αουτσαιντερ (γραμμη ≥ +0.5)', (R.status == 'νεκρη') & (R.ahL_Crown >= .5)),
                 ('νεκρη ως φαβορι (γραμμη ≤ −0.5)', (R.status == 'νεκρη') & (R.ahL_Crown <= -.5)),
                 ('υψηλο vs νεκρη', (R.status == 'υψηλο') & (R.opp_status == 'νεκρη')), ('θελει γκολ', R.needg),
                 ('θελει γκολ & φαβορι', R.needg & (R.ahL_Crown <= -.5))):
    x = R[msk]; v = x[['ah_Crown', 'ah_SBOBET']]; ps = x.assign(p=v.mean(axis=1)).groupby('sea').p.mean()
    print(f'   {lab:38s} n{v.notna().any(axis=1).sum():4d} · ROI {100 * v.stack().mean():+6.1f}% (C {100 * v.ah_Crown.mean():+.1f} / S {100 * v.ah_SBOBET.mean():+.1f}) · σεζον {int((ps > 0).sum())}/{ps.size}')
# ---------------- 3. τα picks μας σε αυτα τα ματς ----------------
P = []
for bk, OD in (('Crown', g['CROWN']), ('Pin', g['PIN'])):
    for (mid, side), rr in g['gen'](BASE, OD).items():
        P.append(dict(mid=mid, side=side, bk=bk, role=rr['role'], pnl=rr['pnl'], sea=rr['sea']))
P = pd.DataFrame(P).merge(R[['mid', 'side', 'status', 'opp_status', 'needg']], on=['mid', 'side'], how='inner')
print('\n3. ΤΑ PICKS ΜΑΣ (σημερινοι κανονες, κλεισιμο, μεσος Crown/Pinnacle) στις τελευταιες 2 αγωνιστικες, ανα κατασταση ΤΗΣ ΟΜΑΔΑΣ ΤΟΥ PICK')
for lab, msk in (('ολα', P.status.notna()), ('pick σε νεκρη', P.status == 'νεκρη'), ('pick κατα νεκρης', P.opp_status == 'νεκρη'),
                 ('pick σε υψηλο κινητρο', P.status == 'υψηλο'), ('pick σε ομαδα που θελει γκολ', P.needg)):
    x = P[msk]; m_ = x.groupby('bk').pnl.agg(['mean', 'size'])
    print(f'   {lab:30s} n{m_["size"].mean() if len(m_) else 0:4.0f} · ROI {100 * m_["mean"].mean() if len(m_) else float("nan"):+.1f}%')
# ---------------- 4. LOSO διορθωση μοντελου ----------------
print('\n4. LOSO ΔΙΟΡΘΩΣΗ ΜΟΝΤΕΛΟΥ (πιθανοφανεια γκολ στις τελευταιες 2 αγωνιστικες): λ νεκρης επιθ ×e^a, αμυνας ×e^d · λ «θελει γκολ» ×e^b')
X = R.dropna(subset=['lf'])
def ll(x, a, d, b):
    lf = x.lf * np.exp(np.where(x.status == 'νεκρη', a, 0) + np.where(x.needg, b, 0))
    la = x.la * np.exp(np.where(x.status == 'νεκρη', d, 0))
    return float(np.sum(x.gf * np.log(lf) - lf + x.ga * np.log(la) - la))
GR = np.round(np.arange(-0.4, 0.41, 0.05), 2)
out = {}
for te in SEAS:
    tr = X[X.sea != te]; ts = X[X.sea == te]
    a = max(GR, key=lambda v: ll(tr, v, 0, 0)); d = max(GR, key=lambda v: ll(tr, a, v, 0)); b = max(GR, key=lambda v: ll(tr, a, d, v))
    out[te] = (a, d, b, ll(ts, a, d, b) - ll(ts, 0, 0, 0))
    print(f'   εκτος {te}: a {a:+.2f} d {d:+.2f} b {b:+.2f} → Δπιθ {out[te][3]:+.2f}')
npos = sum(v[3] > 0 for v in out.values())
print(f'   → {"ΠΕΡΝΑ" if npos >= 3 else "ΔΕΝ ΠΕΡΝΑ"} ({npos}/4)')
print('\n5. ΠΑΡΑΔΕΙΓΜΑΤΑ «θελει γκολ» (2526):')
for r in M[(M.sea == '2526') & M.needg].sort_values('gn', ascending=False).head(10).itertuples():
    pr = {k: v for k, v in r.probs.items()}
    print(f'   {r.comp[:4]} αγων.{r.rnd} {r.team[:20]:20s} σκορ {r.score} · κινητρο νικης {r.ws:.2f} · αναγκη γκολ {r.gn:.2f} · ' +
          ' '.join(f'{k}: Η {v["L"]:.2f} / Ν1 {v["W1"]:.2f} / Ν3+ {v["W3"] if np.isfinite(v["W3"]) else v["W2"]:.2f}' for k, v in pr.items()))
R.drop(columns=[]).to_pickle('euro_motivation_rows.pkl')
