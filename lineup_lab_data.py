# -*- coding: utf-8 -*-
"""
lineup_lab_data.py — ΦΑΣΗ 1 του Lineup Lab: βαση παικτων ανα ομαδα CORE7 (σεζον 26/27).

Για καθε ομαδα: τρεχον ροστερ (FotMob squad API) + rating καθε παικτη απο το
2σεζονο ιστορικο μας (φθινων 0.95/εμφ., ζυγισμενος στα λεπτα, συρρικνωση K=5x90'
προς μεσο θεσης — η μεθοδος του xi_strength.py που εδωσε t=5 στην πυλη) +
προσφατες συμμετοχες βασικου (για την «αναμενομενη ενδεκαδα») + baseline ομαδας
(μεσος των τελευταιων 15 πραγματικων ενδεκαδων της).

Εξοδος: lineup_lab.json  — το διαβαζει η σελιδα του dashboard.
Ξανατρεξιμο = πληρης ανανεωση (τα squads κρατιουνται σε cache 3 ημερων).
"""
import sys, os, json, time, datetime
import numpy as np
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard'))
import build_data

DEC, KSH = 0.95, 5.0
SLOPE_GD_PER_RATING = 0.9          # μετρημενη ζυγαρια: +0.10 Δ ενδεκαδας ≈ +0.09 γκολ στη διαφορα
POS_NAME = {0: 'GK', 1: 'DEF', 2: 'MID', 3: 'ATT'}
SQUAD_CACHE = 'lineup_lab_squads.json'
OUT = 'lineup_lab.json'

print('φορτωση ιστορικου παικτων...', flush=True)
PM = json.load(open('player_matches.json', encoding='utf-8'))
SQ = json.load(open('squads_all.json', encoding='utf-8'))
ESQ = json.load(open('europe_squads.json', encoding='utf-8'))
EU = json.load(open('europe_fixtures.json', encoding='utf-8'))
import pandas as pd
TG = pd.read_csv('teamgame_inputs_5s.csv')
TG['season'] = TG['season'].astype(str); TG['mid'] = TG['mid'].astype(str)

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


# μεσοι ανα θεση (prior)
pos_sum = defaultdict(float); pos_n = defaultdict(int)
for rec in PM.values():
    if not rec:
        continue
    for sk in ('h', 'a'):
        for p in (rec.get(sk, {}).get('p') or []):
            if p[1] is not None:
                pos_sum[p[3]] += p[1]; pos_n[p[3]] += 1
POS_MU = {k: pos_sum[k] / pos_n[k] for k in pos_n if pos_n[k] >= 200}
GMU = sum(pos_sum.values()) / sum(pos_n.values())

# walk-forward: τελικα αθροισματα παικτων + XI ιστορικο ομαδων + συμμετοχες
psum = defaultdict(float); pw = defaultdict(float); papp = defaultdict(int)
ppos = {}
team_xi_hist = defaultdict(list)
team_starts = defaultdict(lambda: defaultdict(list))   # tid -> pid -> [1/0 ανα ματς της ομαδας]
for d, mid, kind in all_matches:
    rec = PM.get(mid)
    if not rec:
        continue
    mm = mins_of(mid, kind)
    for sk in ('h', 'a'):
        side = rec.get(sk)
        if not side:
            continue
        tid = side.get('t')
        starters = [p for p in side['p'] if p[4] == 1]
        if len(starters) >= 10:
            vals = []
            for pid, rt, mv, pos, st in starters:
                mu = POS_MU.get(pos, GMU)
                vals.append((psum[pid] + KSH * mu) / (pw[pid] + KSH))
            team_xi_hist[tid].append(float(np.mean(vals)))
        started = {p[0] for p in starters}
        for pid, rt, mv, pos, st in side['p']:
            team_starts[tid][pid].append(1 if pid in started else 0)
        for pid, rt, mv, pos, st in side['p']:
            ppos[pid] = pos if pos is not None else ppos.get(pid)
            if rt is None:
                continue
            w = mm.get(pid, 60) / 90.0
            psum[pid] = psum[pid] * DEC + rt * w
            pw[pid] = pw[pid] * DEC + w
            papp[pid] += 1

def player_rating(pid, pos):
    mu = POS_MU.get(pos, GMU)
    return (psum[pid] + KSH * mu) / (pw[pid] + KSH)

# ---------- τρεχοντα ροστερ (FotMob) ----------
id2name = {}; id2lg = {}
for lg in build_data.LEAGUE_FOTMOB:
    try:
        d = json.load(open(f'data_{lg}_2627.json', encoding='utf-8'))
    except FileNotFoundError:
        continue
    for m in d.values():
        for s in ('home', 'away'):
            id2name[int(m[s]['id'])] = m[s]['name']; id2lg[int(m[s]['id'])] = lg
print(f'ομαδες CORE7 26/27: {len(id2name)}', flush=True)

cache = {}
if os.path.exists(SQUAD_CACHE):
    try:
        c = json.load(open(SQUAD_CACHE, encoding='utf-8'))
        if time.time() - c.get('at', 0) < 3 * 86400:
            cache = c.get('squads', {})
    except Exception:
        pass
squads = {}
n_fetch = 0
for tid in sorted(id2name):
    k = str(tid)
    if k in cache:
        squads[k] = cache[k]; continue
    try:
        j = build_data._fotmob(f'https://www.fotmob.com/api/data/teams?id={tid}')
        groups = (j.get('squad') or {}).get('squad') or []
        members = []
        for g in groups:
            if g.get('title') == 'coach':
                continue
            for m in (g.get('members') or []):
                if m.get('id') and m.get('name'):
                    members.append(dict(id=int(m['id']), nm=m['name'],
                                        pos=m.get('positionId'), desc=m.get('positionIdsDesc', '')))
        squads[k] = members
        n_fetch += 1
        time.sleep(0.5)
    except Exception as e:
        print(f'  {id2name[tid]}: ΣΦΑΛΜΑ squad {type(e).__name__}', flush=True)
        squads[k] = []
    if n_fetch and n_fetch % 20 == 0:
        print(f'  ...{n_fetch} squads', flush=True)
json.dump(dict(at=time.time(), squads=squads), open(SQUAD_CACHE, 'w', encoding='utf-8'))
print(f'squads: {len(squads)} ομαδες ({n_fetch} φρεσκα)', flush=True)

# ---------- συνθεση εξοδου ----------
out_teams = {}
for tid, name in id2name.items():
    members = squads.get(str(tid)) or []
    ts = team_starts.get(tid, {})
    players = []
    for m in members:
        pid = m['id']
        pos = m['pos'] if m['pos'] is not None else ppos.get(pid, 2)
        known = pw.get(pid, 0) > 0.5
        st15 = sum(ts.get(pid, [])[-15:])
        players.append(dict(id=pid, nm=m['nm'], pos=int(pos), desc=m.get('desc', ''),
                            rt=round(float(player_rating(pid, pos)), 3),
                            ap=int(papp.get(pid, 0)), st15=int(st15), new=(not known)))
    # αναμενομενη ενδεκαδα: 1 GK + 10 αλλοι, με σειρα προσφατες συμμετοχες βασικου -> rating
    gks = sorted([p for p in players if p['pos'] == 0], key=lambda p: (-p['st15'], -p['rt']))
    rest = sorted([p for p in players if p['pos'] != 0], key=lambda p: (-p['st15'], -p['rt']))
    xi = ([gks[0]['id']] if gks else []) + [p['id'] for p in rest[:11 - (1 if gks else 0)]]
    hist = team_xi_hist.get(tid, [])
    base = round(float(np.mean(hist[-15:])), 3) if len(hist) >= 5 else None
    out_teams[str(tid)] = dict(name=name, lg=id2lg[tid], players=players, xi=xi, base=base)

json.dump(dict(built=datetime.date.today().isoformat(), slope_gd=SLOPE_GD_PER_RATING,
               pos_mu={str(k): round(v, 3) for k, v in POS_MU.items()},
               pos_name=POS_NAME, teams=out_teams),
          open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
n_known = sum(1 for t in out_teams.values() for p in t['players'] if not p['new'])
n_all = sum(len(t['players']) for t in out_teams.values())
print(f'ΕΤΟΙΜΟ: {OUT} · {len(out_teams)} ομαδες · {n_all} παικτες ({n_known} με ιστορικο, {n_all-n_known} νεοι)')
