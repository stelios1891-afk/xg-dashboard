# -*- coding: utf-8 -*-
"""
player_fetch_2627.py — Φετινα (26/27) player ratings + λεπτα, incremental.

Ματς: οσα υπαρχουν στα data_{lg}_2627.json (παιγμενα, απο το καθημερινο refresh).
Ενα request/ματς (FotMob matchDetails) δινει και τα δυο:
  player_matches_2627.json  {mid: {"h":{"t","p":[[pid,rt,mv,pos,starter],...]},"a":...}}
  squads_2627.json          {mid: {"h":{"t","p":{pid:minutes}},"a":...}}
Resumable: κατεβαζει μονο νεα mids. Τρεχει και στο data-refresh (καθημερινα).
"""
import sys, os, json, time, gzip, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.stdout.reconfigure(encoding='utf-8')
HDR = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}
OUT_PM, OUT_SQ = 'player_matches_2627.json', 'squads_2627.json'
LEAGUES = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']


def minutes_map(j):
    out = {}
    ps = (j.get('content') or {}).get('playerStats') or {}
    if not isinstance(ps, dict):
        return out
    for pid, v in ps.items():
        if not isinstance(v, dict):
            continue
        mins = None
        st = v.get('stats')
        blocks = st if isinstance(st, list) else [st]
        for blk in blocks:
            if not isinstance(blk, dict):
                continue
            sk = blk.get('stats') if isinstance(blk.get('stats'), dict) else blk
            mp = sk.get('Minutes played') if isinstance(sk, dict) else None
            if isinstance(mp, dict):
                s = mp.get('stat')
                mins = s.get('value') if isinstance(s, dict) else s
            elif isinstance(mp, (int, float)):
                mins = mp
            if mins is not None:
                break
        try:
            out[int(pid)] = int(mins) if mins is not None else 0
        except Exception:
            pass
    return out


def one(mid):
    for i in range(3):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(
                f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}', headers=HDR), timeout=25).read()
            if raw[:2] == b'\x1f\x8b':
                raw = gzip.decompress(raw)
            j = json.loads(raw)
            lu = (j.get('content') or {}).get('lineup') or {}
            rec = {}
            for side, k in (('homeTeam', 'h'), ('awayTeam', 'a')):
                t = lu.get(side) or {}
                pl = []
                for grp, is_st in (('starters', 1), ('subs', 0)):
                    for p in (t.get(grp) or []):
                        if not p.get('id'):
                            continue
                        perf = p.get('performance') or {}
                        rt = perf.get('rating')
                        try:
                            rt = float(rt) if rt is not None else None
                        except Exception:
                            rt = None
                        pl.append([int(p['id']), rt, p.get('marketValue'),
                                   p.get('usualPlayingPositionId', p.get('positionId')), is_st])
                if pl:
                    rec[k] = {'t': t.get('id'), 'p': pl}
            mm = minutes_map(j)
            sq = {}
            for k in ('h', 'a'):
                if k in rec:
                    ids = {p[0] for p in rec[k]['p']}
                    sq[k] = {'t': rec[k]['t'], 'p': {str(pid): mn for pid, mn in mm.items() if pid in ids}}
            return mid, (rec or None), (sq or None)
        except Exception:
            time.sleep(0.8 * (i + 1))
    return mid, None, None


mids = []
for lg in LEAGUES:
    try:
        d = json.load(open(f'data_{lg}_2627.json', encoding='utf-8'))
        mids += [str(k) for k in d]
    except FileNotFoundError:
        pass
PM = json.load(open(OUT_PM, encoding='utf-8')) if os.path.exists(OUT_PM) else {}
SQ = json.load(open(OUT_SQ, encoding='utf-8')) if os.path.exists(OUT_SQ) else {}
todo = [m for m in sorted(set(mids)) if m not in PM]
print(f'φετινα ματς: {len(set(mids))} · ηδη: {len(PM)} · νεα: {len(todo)}', flush=True)
if todo:
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(one, m): m for m in todo}
        for f in as_completed(futs):
            mid, rec, sq = f.result()
            if rec:
                PM[mid] = rec
            if sq:
                SQ[mid] = sq
    json.dump(PM, open(OUT_PM, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(SQ, open(OUT_SQ, 'w', encoding='utf-8'), ensure_ascii=False)
wr = sum(1 for v in PM.values() if v and any(x[1] is not None for x in (v.get('h', {}).get('p') or [])))
print(f'ΤΕΛΟΣ 2627: {len(PM)} ματς αποθηκευμενα · με ratings {wr}')
