# -*- coding: utf-8 -*-
"""lineup_dual_calc.py — Διπλος υπολογισμος ΧΩΡΙΣ vs ΜΕ projected ενδεκαδες (σεζον 26/27).

ΠΑΙΓΜΕΝΑ ματς (LaLiga/EPL/SerieA): προβλεψεις FutbolFantasy απο το αρχειο του site
(predicted11_history_2627.jsonl — κλειδωνουν ~2h προ σεντρας, αρα τιμια pre-match πληροφορια).
xg μοντελου ΧΩΡΙΣ ενδεκαδες: walk-forward με το ΙΔΙΟ live engine (ραμπα χαρακα, warm-start K=8,
τιμιες νεοφωτιστες) — μονο ματς ΠΡΙΝ τη σεντρα. Αποδοσεις: odds_history.jsonl snapshot ~−24h.
Ενδεκαδες: abilities του lineup_lab (χτισμενες μεχρι τελος 25/26 — κανενα 26/27 leak).

ΜΕ = shift SLOPE*(dh−da)/2 στο xg (ιδιο με Lineup Lab / forward log).
Εξοδος: πινακες δίπλα-δίπλα + αποσυνθεση κοινα/καινουργια/κομμενα.
"""
import sys, os, json, re, datetime, unicodedata
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard'))
import picks
import build_data

LGS = ['LaLiga', 'EPL', 'SerieA']
SLOPE = 0.9
LAB = json.load(open('lineup_lab.json', encoding='utf-8'))


def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return set(re.findall(r'[a-z]{2,}', s))


def player_lookup(tid, site_name):
    toks = norm(site_name)
    best, bs = None, 0
    for p in LAB['teams'][tid]['players']:
        ov = len(toks & norm(p['nm']))
        if ov > bs:
            best, bs = p['id'], ov
    return best if bs >= 1 else None


# ---- 1. FF preds 26/27: team_id -> δικο μας tid (βαση ΡΟΣΤΕΡ hits) + pids ανα (team, jornada) ----
recs = []
for line in open('predicted11_history_2627.jsonl', encoding='utf-8'):
    try:
        r = json.loads(line)
    except ValueError:
        continue
    if r.get('pred'):
        recs.append(r)

ff_names = {}
for r in recs:
    ff_names.setdefault((r['lg'], r['team_id']), {'team': r['team'], 'names': set()})
    ff_names[(r['lg'], r['team_id'])]['names'] |= {p['nm'] for p in r['pred'] if p.get('nm')}

ff2tid = {}
for (lg, ftid), v in ff_names.items():
    best, bs = None, -1
    for tid, t in LAB['teams'].items():
        if t['lg'] != lg:
            continue
        hits = sum(1 for nm in v['names'] if player_lookup(tid, nm))
        score = hits + 0.5 * len(norm(v['team']) & norm(t['name']))
        if score > bs:
            best, bs = tid, score
    ff2tid[(lg, ftid)] = best

# pids ανα (tid, jornada) + ημερομηνια ματς του FF
pred_xi = {}
for r in recs:
    tid = ff2tid.get((r['lg'], r['team_id']))
    if not tid:
        continue
    pids = [player_lookup(tid, p['nm']) for p in r['pred'] if p.get('nm')]
    pids = [p for p in pids if p]
    dres = (r.get('date_resultado') or '')[:10]
    pred_xi[(tid, r['jornada'])] = dict(pids=pids, date=dres, team=r['team'])

ok8 = sum(1 for v in pred_xi.values() if len(v['pids']) >= 8)
print(f'FF προβλεψεις 26/27: {len(pred_xi)} πλευρες-αγωνιστικες · με >=8 ταιριασμενους: {ok8}')


def delta(tid, pids):
    t = LAB['teams'].get(tid)
    if not t or len(pids) < 8:
        return None
    pmap = {p['id']: p['rt'] for p in t['players']}
    vals = [pmap[i] for i in pids if i in pmap]
    if len(vals) < 8 or t.get('base') is None:
        return None
    return sum(vals) / len(vals) - t['base']


# ---- 2. Walk-forward xg ΧΩΡΙΣ ενδεκαδες (live engine, μονο ματς πριν τη σεντρα) ----
Mp, id2name = picks.load_matches(LGS, ['2526'])
Mc, id2c = picks.load_matches(LGS, ['2627'])
id2name.update(id2c)

xg_map = {}   # mid -> (xg_h, xg_a, md_home)
for lg in LGS:
    G = Mc[Mc.league == lg].sort_values(['date', 'mid']).reset_index(drop=True)
    if len(G) == 0:
        continue
    histp, p_shots, p_xgps, hf = picks.league_state(Mp, lg, '2526')
    teams27 = set(G.home) | set(G.away)
    newcomers = sorted(t for t in teams27 if t not in histp)
    for tid, (nm, synth) in build_data.promoted_priors(lg, newcomers, p_shots, p_xgps, id2name).items():
        histp[tid] = synth
    histp = build_data.flatten_warmstart(histp, lg)
    prior_r = {tid: build_data._rating(h) for tid, h in histp.items() if h.get('sf')}
    for date, dg in G.groupby('date', sort=True):
        cut = Mc[(Mc.league == lg) & (Mc.date < date)]
        histc, cur_shots, cur_xgps, _ = picks.league_state(cut, lg, '2627')
        lg_shots, lg_xgps = p_shots, p_xgps
        nc = sum(len(h['sf']) for h in histc.values())
        if nc and cur_shots and cur_xgps:
            w = nc / (nc + build_data.KN_NORM)
            lg_shots = lg_shots * (cur_shots / lg_shots) ** w
            lg_xgps = lg_xgps * (cur_xgps / lg_xgps) ** w
        blended, ns = build_data.blend_league(prior_r, histc)
        if picks.SOS:
            blended = {tid: picks.sos_adjust(r, histc.get(tid, {}).get('opp', []),
                                             blended, lg_shots, lg_xgps)
                       for tid, r in blended.items()}
        for _, m in dg.iterrows():
            rh = blended.get(m['home']); ra = blended.get(m['away'])
            if rh and ra:
                pf = build_data._predict_ratings(rh, ra, lg_shots, lg_xgps, hf)
                nH = len((histc.get(m['home']) or {}).get('sf', []))
                xg_map[m['mid']] = (pf['home_adj_xg'], pf['away_adj_xg'], nH + 1)

print(f'walk-forward xg για {len(xg_map)} παιγμενα ματς')

# ---- 3. Αποδοσεις ~−24h: odds_history (scanner) + fallback nowgoal 2627 (Crown/Bet365) ----
hist = {}
for line in open('odds_history.jsonl', encoding='utf-8'):
    try:
        r = json.loads(line)
    except ValueError:
        continue
    hist.setdefault((r.get('hid'), r.get('aid')), []).append(r)

try:
    from nowgoal_merged import load_traj
    NG3 = load_traj('2627', 3); NG8 = load_traj('2627', 8)
except Exception:
    NG3, NG8 = {}, {}


def odds_24h(hid, aid, mid=None):
    best = None
    for s in hist.get((hid, aid)) or []:
        try:
            ko = datetime.datetime.fromisoformat(s['ko'])
            t = datetime.datetime.fromisoformat(s['t'][:16])
        except Exception:
            continue
        if s.get('line') is None or s.get('oh') is None or s.get('oa') is None:
            continue
        d = abs((t - (ko - datetime.timedelta(hours=24))).total_seconds())
        if best is None or d < best[0]:
            best = (d, float(s['line']), float(s['oh']), float(s['oa']))
    if best and best[0] < 12 * 3600:
        return best[1], best[2], best[3]
    # fallback: nowgoal traj (Crown πρωτα, μετα Bet365) — τελευταιο snapshot <= τελος−24h
    for src in (NG3, NG8):
        tr = src.get(str(mid)) or src.get(mid)
        if tr:
            cm = tr[-1][0]
            past = [x for x in tr if x[0] <= cm - 24 * 3600]
            if past:
                e = past[-1]
                return e[1], e[2], e[3]
    return None


# ---- 4. Ζευγαρωμα ματς <-> FF jornada (ημερομηνια ±2 μερες) + διπλος υπολογισμος ----
def find_pred(tid, date):
    d0 = datetime.date.fromisoformat(date)
    best = None
    for (t, j), v in pred_xi.items():
        if t != tid or not v['date']:
            continue
        try:
            dd = abs((datetime.date.fromisoformat(v['date']) - d0).days)
        except ValueError:
            continue
        if dd <= 2 and (best is None or dd < best[0]):
            best = (dd, j, v)
    return best


rows = []; miss = dict(no_xg=0, no_pred=0, no_delta=0, no_odds=0)
for _, m in Mc.sort_values(['date', 'mid']).iterrows():
    mid = m['mid']
    if mid not in xg_map:
        miss['no_xg'] += 1; continue
    xh0, xa0, mdH = xg_map[mid]
    ph = find_pred(str(m['home']), m['date'])
    pa = find_pred(str(m['away']), m['date'])
    if not ph or not pa:
        miss['no_pred'] += 1; continue
    dh = delta(str(m['home']), ph[2]['pids'])
    da = delta(str(m['away']), pa[2]['pids'])
    if dh is None or da is None:
        miss['no_delta'] += 1; continue
    o = odds_24h(m['home'], m['away'], mid)
    if not o:
        miss['no_odds'] += 1; continue
    line, oh, oa = o
    gd = m['hg'] - m['ag']
    sh = SLOPE * (dh - da) / 2
    xh1, xa1 = max(xh0 + sh, 0.05), max(xa0 - sh, 0.05)
    for mode, (xh, xa) in (('ΧΩΡΙΣ', (xh0, xa0)), ('ΜΕ', (xh1, xa1))):
        for b in picks.evaluate_bet(xh, xa, line, oh, oa):
            rows.append(dict(mid=mid, lg=m['league'], date=m['date'],
                             home=id2name.get(m['home'], m['home']), away=id2name.get(m['away'], m['away']),
                             md=mdH, mode=mode, side=b['side'], hcap=b['hcap'], odds=b['odds'],
                             edge=b['edge'], gd=gd, dh=dh, da=da, xh=round(xh, 2), xa=round(xa, 2),
                             pnl=picks.settle(gd, b['side'], b['hcap'], b['odds'])))
    rows.append(dict(mid=mid, lg=m['league'], date=m['date'],
                     home=id2name.get(m['home'], m['home']), away=id2name.get(m['away'], m['away']),
                     md=mdH, mode='xg', side='', hcap=line, odds=0.0,
                     edge=0.0, gd=gd, dh=dh, da=da,
                     xh=round(xh0, 2), xa=round(xa0, 2), pnl=0.0))

print('χαμενα:', miss)
B = pd.DataFrame([r for r in rows if r['mode'] != 'xg'])
X = pd.DataFrame([r for r in rows if r['mode'] == 'xg'])
print(f'ματς με ΠΛΗΡΗ στοιχεια (xg+11αδες+odds): {len(X)}')

if len(X):
    print()
    print('=== ΠΑΙΓΜΕΝΑ ΜΑΤΣ: xg ΧΩΡΙΣ (και Δ 11αδων) ===')
    for _, r in X.iterrows():
        s = SLOPE * (r.dh - r.da) / 2
        print(f"  {r.date} {r.lg:7s} {r.home[:18]:18s}-{r.away[:18]:18s} "
              f"xg {r.xh:.2f}-{r.xa:.2f} -> ΜΕ {max(r.xh+s,0.05):.2f}-{max(r.xa-s,0.05):.2f} "
              f"(shift {s:+.3f}) gd={int(r.gd):+d}")

def cell(g):
    return '%2d bets %+7.2f%% %+6.2fu' % (len(g), g.pnl.mean() * 100, g.pnl.sum()) \
        if len(g) else '  -'

if len(B):
    print()
    print('=== PICKS (edge>=10%, 1.70-2.10, γραμμη>=0.5) ===')
    print('%-8s | %-24s | %-24s' % ('', 'ΧΩΡΙΣ ενδεκαδες', 'ΜΕ projected'))
    for lg in LGS + ['ΣΥΝΟΛΟ']:
        a = B[B['mode'] == 'ΧΩΡΙΣ']; b = B[B['mode'] == 'ΜΕ']
        if lg != 'ΣΥΝΟΛΟ':
            a = a[a.lg == lg]; b = b[b.lg == lg]
        print('%-8s | %-24s | %-24s' % (lg, cell(a), cell(b)))
    print()
    print('--- αναλυτικα picks ---')
    for _, r in B.sort_values(['date', 'mid', 'mode']).iterrows():
        print(f"  {r.date} {r.lg:7s} {r.home[:16]:16s}-{r.away[:16]:16s} [{r['mode']:5s}] "
              f"{r.side} {r.hcap:+.2f} @{r.odds:.2f} edge {r.edge*100:.1f}% -> {r.pnl:+.2f}u")
    # αποσυνθεση κοινα/καινουργια/κομμενα
    A = {(r.mid, r.side) for r in B[B['mode'] == 'ΧΩΡΙΣ'].itertuples()}
    Bm = {(r.mid, r.side) for r in B[B['mode'] == 'ΜΕ'].itertuples()}
    com = A & Bm; new = Bm - A; cutb = A - Bm
    print()
    for nm, ss, mode in (('ΚΟΙΝΑ', com, 'ΧΩΡΙΣ'), ('ΚΑΙΝΟΥΡΓΙΑ (μονο ΜΕ)', new, 'ΜΕ'),
                         ('ΚΟΜΜΕΝΑ (μονο ΧΩΡΙΣ)', cutb, 'ΧΩΡΙΣ')):
        g = B[(B['mode'] == mode) & B.apply(lambda r: (r.mid, r.side) in ss, axis=1)] if ss else B.iloc[0:0]
        print(f'  {nm:22s}: {cell(g)}')
