# -*- coding: utf-8 -*-
"""
lineup_lab_data.py — Βαση παικτων του Lineup Lab (v2: ικανοτητα + συντελεστης λιγκας).

Ρειτινγκ παικτη = «καθαρη ικανοτητα» (καθε βαθμολογια αναγεται σε κλιμακα EPL με τον
συντελεστη της λιγκας που παιχτηκε — league_offsets.json, επικυρωμενο out-of-sample:
μεροληψια +0.24 -> +0.00) προβεβλημενη στη λιγκα της τωρινης ομαδας.

Πηγες ανα παικτη (χρονολογικα, decay 0.95/εμφανιση, συρρικνωση K=5x90' προς μεσο θεσης):
  1. δικο μας αρχειο (CORE7 + ευρωπαικα, ανα ματς)
  2. backfill 12μηνου (ανα ματς, ολες οι λιγκες, χωρις φιλικα)
  3. career σεζον-μπλοκ (για οσους δεν φταναν τα παραπανω, χωρις φιλικα)

Εξοδος: lineup_lab.json — το διαβαζει η σελιδα του dashboard.
"""
import sys, os, json, time, datetime
import numpy as np
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard'))
import build_data

DEC, KSH = 0.95, 5.0
SLOPE_GD_PER_RATING = 0.9
POS_NAME = {0: 'GK', 1: 'DEF', 2: 'MID', 3: 'ATT'}
SQUAD_CACHE = 'lineup_lab_squads.json'
OUT = 'lineup_lab.json'
DEFAULT_OFF = 0.50            # αγνωστη λιγκα: συντηρητικα «κατωτερη»

OFF = json.load(open('league_offsets.json', encoding='utf-8'))
def off_of(key):
    return OFF.get(key, DEFAULT_OFF)

print('φορτωση ιστορικου...', flush=True)
PM = json.load(open('player_matches.json', encoding='utf-8'))
SQ = json.load(open('squads_all.json', encoding='utf-8'))
ESQ = json.load(open('europe_squads.json', encoding='utf-8'))
EU = json.load(open('europe_fixtures.json', encoding='utf-8'))
import pandas as pd
TG = pd.read_csv('teamgame_inputs_5s.csv')
TG['season'] = TG['season'].astype(str); TG['mid'] = TG['mid'].astype(str)
mid_lg = TG.groupby('mid').league.first().to_dict()
dom_dates = TG.groupby('mid').date.first().to_dict()
eu_dates = {m['mid']: m['utc'][:10] for rows in EU.values() for m in rows}
eu_comp = {m['mid']: comp for comp, rows in EU.items() for m in rows}
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

# ---- μοναδες βαθμολογιας ανα παικτη: (date, rating_ability, weight_90s) ----
units = defaultdict(list)
ppos = {}; papp = defaultdict(int)
team_starts = defaultdict(lambda: defaultdict(list))
# 1. δικο μας αρχειο
pos_sum = defaultdict(float); pos_n = defaultdict(int)
for d, mid, kind in all_matches:
    rec = PM.get(mid)
    if not rec:
        continue
    lgkey = mid_lg.get(mid) if kind == 'dom' else 'EU_' + eu_comp.get(mid, '')
    o = off_of(lgkey)
    mm = mins_of(mid, kind)
    for sk in ('h', 'a'):
        side = rec.get(sk)
        if not side:
            continue
        tid = side.get('t')
        started = {p[0] for p in side['p'] if p[4] == 1}
        for pid, rt, mv, pos, st in side['p']:
            team_starts[tid][pid].append(1 if pid in started else 0)
            if pos is not None:
                ppos[pid] = pos
            if rt is None:
                continue
            w = mm.get(pid, 60) / 90.0
            units[pid].append((d, rt - o, w))
            papp[pid] += 1
            if pos is not None:
                pos_sum[pos] += rt - o; pos_n[pos] += 1
POS_MU = {k: pos_sum[k] / pos_n[k] for k in pos_n if pos_n[k] >= 200}
GMU = sum(pos_sum.values()) / sum(pos_n.values())

# 2. backfill 12μηνου (ανα ματς)
n_bf = 0
for line in open('player_backfill.jsonl', encoding='utf-8'):
    r = json.loads(line)
    for d, lgid, lg, mins, rt in r['m']:
        if rt is None or not d or (lg or '').lower().startswith('club friendl'):
            continue
        key = f'{lg}#{lgid}'
        units[r['pid']].append((d, rt - off_of(key), (mins or 60) / 90.0))
        papp[r['pid']] += 1
        n_bf += 1
# 3. career μπλοκ (μονο οσοι εχουν λιγες μοναδες ως εδω, και μονο παλιες σεζον)
def season_end_date(sn):
    s = str(sn)
    try:
        if '/' in s:
            return f"{int(s.split('/')[1])}-06-30"
        return f"{int(s)}-12-15"
    except (ValueError, IndexError):
        return None
n_car = 0
try:
    for line in open('player_career.jsonl', encoding='utf-8'):
        r = json.loads(line)
        if len(units.get(r['pid'], [])) >= 10:
            continue
        for sn, lgid, lg, apps, rt, fr in r['s']:
            if fr or rt is None or not apps:
                continue
            if str(sn) in ('2025/2026', '2026/2027', '2026'):
                continue                      # καλυπτεται απο το 12μηνο
            d = season_end_date(sn)
            if d is None:
                continue
            key = f'{lg}#{lgid}'
            units[r['pid']].append((d, rt - off_of(key), min(int(apps), 45) * 1.0))
            n_car += 1
except FileNotFoundError:
    pass
print(f'μοναδες: αρχειο + {n_bf} backfill ματς + {n_car} career μπλοκ', flush=True)

def ability(pid, pos):
    """fold χρονολογικα με decay 0.95 ανα ισοδυναμο 90λεπτο, μετα συρρικνωση."""
    mu = POS_MU.get(pos, GMU)
    us = sorted(units.get(pid, []))
    ps = pw = 0.0
    for d, r, w in us:
        dec = DEC ** w
        ps = ps * dec + r * w
        pw = pw * dec + w
    return (ps + KSH * mu) / (pw + KSH), pw

# ---- ροστερ & εξοδος ----
id2name = {}; id2lg = {}
for lg in build_data.LEAGUE_FOTMOB:
    try:
        d = json.load(open(f'data_{lg}_2627.json', encoding='utf-8'))
    except FileNotFoundError:
        continue
    for m in d.values():
        for s in ('home', 'away'):
            id2name[int(m[s]['id'])] = m[s]['name']; id2lg[int(m[s]['id'])] = lg

cache = {}
if os.path.exists(SQUAD_CACHE):
    try:
        c = json.load(open(SQUAD_CACHE, encoding='utf-8'))
        if time.time() - c.get('at', 0) < 3 * 86400:
            cache = c.get('squads', {})
    except Exception:
        pass
squads = {}; n_fetch = 0
for tid in sorted(id2name):
    k = str(tid)
    if k in cache:
        squads[k] = cache[k]; continue
    try:
        j = build_data._fotmob(f'https://www.fotmob.com/api/data/teams?id={tid}')
        members = []
        for g in ((j.get('squad') or {}).get('squad') or []):
            if g.get('title') == 'coach':
                continue
            for m in (g.get('members') or []):
                if m.get('id') and m.get('name'):
                    members.append(dict(id=int(m['id']), nm=m['name'],
                                        pos=m.get('positionId'), desc=m.get('positionIdsDesc', '')))
        squads[k] = members; n_fetch += 1
        time.sleep(0.5)
    except Exception as e:
        print(f'  {id2name[tid]}: squad ΣΦΑΛΜΑ {type(e).__name__}', flush=True)
        squads[k] = []
json.dump(dict(at=time.time(), squads=squads), open(SQUAD_CACHE, 'w', encoding='utf-8'))

out_teams = {}
for tid, name in id2name.items():
    lg = id2lg[tid]
    o_lg = off_of(lg)
    members = squads.get(str(tid)) or []
    ts = team_starts.get(tid, {})
    players = []
    for m in members:
        pid = m['id']
        pos = m['pos'] if m['pos'] is not None else ppos.get(pid, 2)
        ab, w = ability(pid, pos)
        players.append(dict(id=pid, nm=m['nm'], pos=int(pos), desc=m.get('desc', ''),
                            rt=round(float(ab + o_lg), 3),
                            ap=int(papp.get(pid, 0)), st15=int(sum(ts.get(pid, [])[-15:])),
                            new=(w < 2.0)))
    gks = sorted([p for p in players if p['pos'] == 0], key=lambda p: (-p['st15'], -p['rt']))
    rest = sorted([p for p in players if p['pos'] != 0], key=lambda p: (-p['st15'], -p['rt']))
    xi = ([gks[0]['id']] if gks else []) + [p['id'] for p in rest[:11 - (1 if gks else 0)]]
    pmap = {p['id']: p for p in players}
    base = round(float(np.mean([pmap[i]['rt'] for i in xi])), 3) if len(xi) == 11 else None
    out_teams[str(tid)] = dict(name=name, lg=lg, players=players, xi=xi, base=base)

json.dump(dict(built=datetime.date.today().isoformat(), slope_gd=SLOPE_GD_PER_RATING,
               pos_mu={str(k): round(v, 3) for k, v in POS_MU.items()}, pos_name=POS_NAME,
               teams=out_teams), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
n_known = sum(1 for t in out_teams.values() for p in t['players'] if not p['new'])
n_all = sum(len(t['players']) for t in out_teams.values())
print(f'ΕΤΟΙΜΟ v2: {len(out_teams)} ομαδες · {n_all} παικτες ({n_known} με ουσιωδες ιστορικο)')
