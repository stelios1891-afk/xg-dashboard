"""
intl_ratings_fetch.py — FotMob RATING ΠΑΙΚΤΩΝ + ΑΡΧΗΓΟΣ ανα ματς εθνικων (25/9/2026, για το τεστ «σημασια παικτη» — Στελιος: «ο Xhaka ειναι
ο αρχηγος και ισως ο πιο σημαντικος, με μονο την αξια δεν θα τον νιωσει το μοντελο»).
Για καθε ματς του intl_squads.json (ματς με ενδεκαδες): matchDetails → ανα πλευρα {pid: [rating, αρχηγος(0/1), βασικος(0/1)]}.
Resumable (οσα υπαρχουν δεν ξανακατεβαινουν). → intl_player_ratings.json {mid: {h: {...}, a: {...}}}
"""
import sys, os, json, gzip, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.stdout.reconfigure(encoding='utf-8')
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36', 'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}
OUT_F = 'intl_player_ratings.json'
SQ = json.load(open('intl_squads.json', encoding='utf-8'))
out = json.load(open(OUT_F, encoding='utf-8')) if os.path.exists(OUT_F) else {}
todo = [m for m in SQ if m not in out]
print(f'ματς με ενδεκαδες {len(SQ)} · ηδη {len(out)} · νεα {len(todo)}', flush=True)


def get(mid):
    for i in range(3):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}', headers=HDR), timeout=25).read()
            return json.loads(gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw)
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None


def work(mid):
    d = get(mid)
    if not d:
        return mid, None
    lu = (d.get('content') or {}).get('lineup') or {}; rec = {}
    for side, k in (('homeTeam', 'h'), ('awayTeam', 'a')):
        t = lu.get(side) or {}; pl = {}
        for grp, st in (('starters', 1), ('subs', 0)):
            for p in (t.get(grp) or []):
                if not p.get('id'):
                    continue
                rt = (p.get('performance') or {}).get('rating')
                pl[str(p['id'])] = [float(rt) if rt not in (None, '') else None, 1 if p.get('isCaptain') else 0, st]
        rec[k] = pl
    return mid, rec


t0 = time.time(); n = 0
with ThreadPoolExecutor(max_workers=4) as ex:
    for mid, rec in ex.map(work, todo):
        if rec is not None:
            out[mid] = rec; n += 1
        if n and n % 200 == 0:
            json.dump(out, open(OUT_F, 'w', encoding='utf-8')); print(f'  {n}/{len(todo)} · {(time.time() - t0) / 60:.1f} min', flush=True)
json.dump(out, open(OUT_F, 'w', encoding='utf-8'))
print(f'ΤΕΛΟΣ: {n} νεα σε {(time.time() - t0) / 60:.1f} min · συνολο {len(out)}', flush=True)
