# -*- coding: utf-8 -*-
"""
xi_v2_test.py — Η «πυλη» των ενδεκαδων ΞΑΝΑ, με career-seeding για τους
πρωτοεμφανιζομενους των 2425/2526 (αυστηρα χρονολογημενο: μονο σεζον που ειχαν
ΤΕΛΕΙΩΣΕΙ πριν το ντεμπουτο, χωρις φιλικα).

v1 = οπως το xi_strength.py (νεοι ξεκινουν στον μεσο θεσης)
v2 = νεοι ξεκινουν με prior απο την καριερα τους (αθροισματα με την ιδια δομη decay)

Συγκριση: κλιση/t της πυλης (Δdiff -> r_gd) συνολικα + σε υποομαδες.
"""
import sys, json, datetime
import numpy as np, pandas as pd
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

PM = json.load(open('player_matches.json', encoding='utf-8'))
SQ = json.load(open('squads_all.json', encoding='utf-8'))
ESQ = json.load(open('europe_squads.json', encoding='utf-8'))
TG = pd.read_csv('teamgame_inputs_5s.csv')
TG['season'] = TG['season'].astype(str); TG['mid'] = TG['mid'].astype(str)
EU = json.load(open('europe_fixtures.json', encoding='utf-8'))

dom_dates = TG.groupby('mid').date.first().to_dict()
eu_dates = {m['mid']: m['utc'][:10] for rows in EU.values() for m in rows}
all_matches = sorted([(d, mid, 'dom') for mid, d in dom_dates.items()] +
                     [(d, mid, 'eu') for mid, d in eu_dates.items()])

def mins_of(mid, kind):
    src = SQ if kind == 'dom' else ESQ
    rec = src.get(mid) or {}
    out = {}
    for sk in ('h', 'a'):
        s = rec.get(sk)
        if s:
            for pid, mn in s['p'].items():
                out[int(pid)] = mn
    return out

pos_sum = defaultdict(float); pos_n = defaultdict(int)
for rec in PM.values():
    if not rec: continue
    for sk in ('h', 'a'):
        for p in (rec.get(sk, {}).get('p') or []):
            if p[1] is not None:
                pos_sum[p[3]] += p[1]; pos_n[p[3]] += 1
POS_MU = {k: pos_sum[k] / pos_n[k] for k in pos_n if pos_n[k] >= 200}
GMU = sum(pos_sum.values()) / sum(pos_n.values())

# ---- career seeds ----
CAREER = {}
for line in open('player_career_debuts.jsonl', encoding='utf-8'):
    r = json.loads(line)
    CAREER[int(r['pid'])] = r['s']

def season_end(sn):
    """'2023/2024' -> 2024-06-30 · '2024' -> 2024-12-15"""
    try:
        if '/' in str(sn):
            return datetime.date(int(str(sn).split('/')[1]), 6, 30)
        return datetime.date(int(sn), 12, 15)
    except (ValueError, IndexError):
        return None

def seed_of(pid, debut_date):
    """(psum, pw) απο ολοκληρωμενες σεζον πριν το ντεμπουτο — ιδια δομη decay (0.95/εμφ)."""
    entries = []
    for sn, lgid, lg, apps, rt, fr in CAREER.get(pid, []):
        if fr or rt is None or not apps:
            continue
        end = season_end(sn)
        if end is None or end >= debut_date:
            continue
        entries.append((end, apps, rt))
    entries.sort()
    ps = pw = 0.0
    for end, apps, rt in entries:
        apps = min(int(apps), 45)
        dec = 0.95 ** apps
        W = (1 - dec) / 0.05
        ps = ps * dec + rt * W
        pw = pw * dec + W
    return ps, pw

DEC, KSH = 0.95, 5.0

def run_pass(use_seed):
    psum = defaultdict(float); pw = defaultdict(float)
    seeded = set(); seen = set()
    team_xi_hist = defaultdict(list)
    XI = {}
    xi_has_debut = {}
    for d, mid, kind in all_matches:
        rec = PM.get(mid)
        if not rec: continue
        dd = datetime.date.fromisoformat(d)
        mm = mins_of(mid, kind)
        for sk in ('h', 'a'):
            side = rec.get(sk)
            if not side: continue
            tid = side.get('t')
            # seed πρωτοεμφανιζομενων ΠΡΙΝ υπολογιστει η 11αδα
            if use_seed:
                for p in side['p']:
                    pid = p[0]
                    if pid not in seen and pid not in seeded and pid in CAREER:
                        ps, w = seed_of(pid, dd)
                        if w > 0:
                            psum[pid] += ps; pw[pid] += w
                        seeded.add(pid)
            starters = [p for p in side['p'] if p[4] == 1]
            if len(starters) >= 10:
                vals = []
                ndeb = 0
                for pid, rt, mv, pos, st in starters:
                    mu = POS_MU.get(pos, GMU)
                    vals.append((psum[pid] + KSH * mu) / (pw[pid] + KSH))
                    if pid in CAREER and pid not in seen:
                        ndeb += 1
                xi = float(np.mean(vals))
                hist = team_xi_hist[tid]
                avg = float(np.mean(hist[-15:])) if len(hist) >= 5 else np.nan
                if kind == 'dom':
                    XI[(mid, sk)] = (xi, xi - avg if not np.isnan(avg) else np.nan)
                    xi_has_debut[(mid, sk)] = ndeb
                hist.append(xi)
        for sk in ('h', 'a'):
            side = rec.get(sk)
            if not side: continue
            for pid, rt, mv, pos, st in side['p']:
                seen.add(pid)
                if rt is None: continue
                w = mm.get(pid, 60) / 90.0
                psum[pid] = psum[pid] * DEC + rt * w
                pw[pid] = pw[pid] * DEC + w
    return XI, xi_has_debut

P = pd.read_csv('europe_test_preds.csv'); P['mid'] = P['mid'].astype(str); P['season'] = P.season.astype(str)
gx = TG.set_index(['mid', 'team'])
P['axg_h'] = [gx.xg_model.get((m, t), np.nan) for m, t in zip(P.mid, P.home)]
P['axg_a'] = [gx.xg_model.get((m, t), np.nan) for m, t in zip(P.mid, P.away)]
P['r_gd'] = P.gd - (P.xg_h - P.xg_a)
P['r_xg'] = (P.axg_h - P.axg_a) - (P.xg_h - P.xg_a)

# νεοφωτιστες ανα σεζον (ομαδα που δεν υπηρχε στην ιδια λιγκα την προηγουμενη σεζον)
SEAS = ['2122', '2223', '2324', '2425', '2526']
teams_by = TG.groupby(['league', 'season']).team.apply(set).to_dict()
promoted = set()
for (lg, sea), ts in teams_by.items():
    i = SEAS.index(sea)
    if i == 0: continue
    prev = teams_by.get((lg, SEAS[i - 1]), set())
    for t in ts - prev:
        promoted.add((sea, t))

def gate(P2, label):
    out = {}
    for nm, mask in (('ΟΛΑ (md6+, 2425+2526)', P2.season.isin(['2425', '2526'])),
                     ('αρχη σεζον md6-15', P2.season.isin(['2425', '2526']) & (P2.md <= 15)),
                     ('md16+', P2.season.isin(['2425', '2526']) & (P2.md > 15)),
                     ('ματς ΝΕΟΦΩΤΙΣΤΗΣ', P2.season.isin(['2425', '2526']) & P2.promo),
                     ('11αδα με ντεμπουτο', P2.season.isin(['2425', '2526']) & (P2.ndeb > 0))):
        d = P2[mask].dropna(subset=['dd', 'r_gd'])
        if len(d) < 50:
            out[nm] = (len(d), np.nan, np.nan); continue
        x = d.dd.values; y = d.r_gd.values
        b = np.cov(x, y)[0, 1] / np.var(x)
        res = y - b * x - (y.mean() - b * x.mean())
        se = np.sqrt((res @ res) / (len(y) - 2) / (np.var(x) * len(y)))
        out[nm] = (len(d), b * 0.10, b / se)
    return out

results = {}
for use_seed, label in ((False, 'v1 (χωρις seed)'), (True, 'v2 (career seed)')):
    XI, ndeb = run_pass(use_seed)
    xh = {m: v for (m, s), v in XI.items() if s == 'h'}
    xa = {m: v for (m, s), v in XI.items() if s == 'a'}
    P2 = P.copy()
    P2['d_h'] = P2.mid.map(lambda m: xh.get(m, (np.nan, np.nan))[1])
    P2['d_a'] = P2.mid.map(lambda m: xa.get(m, (np.nan, np.nan))[1])
    P2['dd'] = P2.d_h - P2.d_a
    P2['ndeb'] = P2.mid.map(lambda m: (ndeb.get((m, 'h'), 0) + ndeb.get((m, 'a'), 0)))
    P2['promo'] = [((sea, h) in promoted) or ((sea, a) in promoted)
                   for sea, h, a in zip(P2.season, P2.home, P2.away)]
    P2 = P2[P2.md >= 6]
    results[label] = gate(P2, label)
    print(f'{label}: ετοιμο', flush=True)

print()
print('Η ΠΥΛΗ: προβλεπει το Δdiff ενδεκαδων το «υπολοιπο» του μοντελου (γκολ ανα +0.10 Δ · t-stat)')
print('%-26s %28s %28s' % ('', 'v1 (χωρις seed)', 'v2 (career seed)'))
for nm in results['v1 (χωρις seed)']:
    n1, b1, t1 = results['v1 (χωρις seed)'][nm]
    n2, b2, t2 = results['v2 (career seed)'][nm]
    print('%-26s n=%5d  %+.3f (t=%+.1f)    n=%5d  %+.3f (t=%+.1f)' % (nm, n1, b1, t1, n2, b2, t2))
