"""
intl_values_refresh.py — ΑΥΤΟΜΑΤΗ ανανεωση αξιων παικτων εθνικων (26/9/2026, εντολη Στελιου — ηταν χειροκινητα ~1×/μηνα).

Πηγη: FotMob playerData → «Market value» (SciSports) — ιδια κλιμακα με την οποια μετρηθηκε η ζυγαριa του μοντελου (56 Elo/ln).
Ποιοι: οσοι ειναι στις τρεχουσες κλησεις (intl_vcall_tm.json, με pid FotMob) + οσοι ντυθηκαν σε ματς εθνικων τις τελευταιες 60 ημερες
(~1.500 παικτες, οχι ολοι οι 12.7k). Γραφει στο συμπαγες intl_player_values_now.json {pid: [ονομα, αξια]} — αυτο διαβαζουν το
Actions ΚΑΙ (απο 26/9) το laptop πανω απο το μεγαλο ιστορικο αρχειο.
Τρεχει στο GitHub (intl-values.yml): καθε Δευτερα και Πεμπτη + χειροκινητα. Προστασια: αν αποτυχει >30% → τιποτα δεν γραφεται.
"""
import os, sys, json, time, gzip, datetime as dt, urllib.request
from concurrent.futures import ThreadPoolExecutor
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
import pandas as pd

OUT = 'intl_player_values_now.json'
META = 'intl_player_values_now_meta.json'
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
       'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}


def get(u, tries=3):
    for i in range(tries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=25).read()
            return json.loads(gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw)
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def one(pid):
    try:
        d = get(f'https://www.fotmob.com/api/data/playerData?id={pid}')
        info = {it.get('title'): it.get('value') for it in (d.get('playerInformation') or []) if isinstance(it, dict)}
        return pid, d.get('name'), (info.get('Market value') or {}).get('numberValue'), True
    except Exception:
        return pid, None, None, False


def main():
    pids = set()
    for v in (json.load(open('intl_vcall_tm.json', encoding='utf-8')) or {}).values():
        pids.update(int(p['pid']) for p in v.get('players', []) if p.get('pid'))
    try:
        M = pd.read_csv('intl_matches.csv', dtype={'mid': str})
        recent = set(M[M.date >= (dt.datetime.now() - dt.timedelta(days=60)).strftime('%Y-%m-%d')].mid)
        SQ = json.load(open('intl_squads.json', encoding='utf-8'))
        for mid in recent:
            for k in ('h', 'a'):
                pids.update(int(p) for p in ((SQ.get(mid) or {}).get(k) or {}).get('p', {}))
    except Exception as e:
        print(f'αποστολες: {type(e).__name__}')
    pids = sorted(pids)
    print(f'παικτες προς ανανεωση: {len(pids)}', flush=True)
    cur = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    ok = err = changed = 0; t0 = time.time()
    with ThreadPoolExecutor(max_workers=6) as ex:
        for pid, name, mv, good in ex.map(one, pids):
            if not good:
                err += 1; continue
            ok += 1
            old = cur.get(str(pid))
            new = [name or (old[0] if old else str(pid)), float(mv) if mv else (old[1] if old else None)]
            if old != new:
                changed += 1
            cur[str(pid)] = new
    print(f'ΟΚ {ok} · σφαλματα {err} · αλλαγες {changed} · {time.time() - t0:.0f}s', flush=True)
    if not pids or err > 0.30 * len(pids):
        print('ΣΦΑΛΜΑ: πολλες αποτυχιες — το αρχειο ΔΕΝ γραφεται'); return 1
    json.dump(cur, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(dict(asof=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M'), n=ok, changed=changed),
              open(META, 'w', encoding='utf-8'), ensure_ascii=False)
    return 0


if __name__ == '__main__':
    sys.exit(main())
