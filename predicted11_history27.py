# -*- coding: utf-8 -*-
"""
predicted11_history27.py — Αναδρομικες προβλεψεις FutbolFantasy (user 15) για το 26/27:
LaLiga (temporada 143) + EPL (145) + SerieA (146), αγωνιστικες 1-4.

Ιδια μεθοδος με predicted11_history.py (25/26). Οι προβλεψεις κλειδωνουν ~2h προ σεντρας
(date_end) — αρα ειναι τιμια pre-match πληροφορια για τα ματς που εχουν ηδη παιχτει.
Εξοδος: predicted11_history_2627.jsonl · resumable.
"""
import sys, os, json, gzip, re, time, random, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
HDR = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Accept-Encoding': 'gzip',
       'Referer': 'https://www.predicted11.com/'}
TOKEN = '9999999999-bc50eedf25a5927ebd9935813ce5b4b9'
USER = 15
TEMPORADAS = {143: ('LaLiga', 4), 145: ('EPL', 4), 146: ('SerieA', 4)}
OUT = 'predicted11_history_2627.jsonl'


def getb(u):
    r = urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=25)
    d = r.read()
    if d[:2] == b'\x1f\x8b':
        d = gzip.decompress(d)
    return d


h = getb('https://www.predicted11.com/es/usuario/FutbolFantasy?campeonato=laliga').decode('utf-8', 'replace')
m = re.search(r'window\.profileTeamsData\s*=\s*(\{.*?\});', h, re.S)
TD = json.loads(m.group(1))
teams = {}
for temp, groups in TD.items():
    t = int(temp)
    if t not in TEMPORADAS:
        continue
    lst = []
    seen_t = set()
    for g, arr in groups.items():
        for it in (arr or []):
            if isinstance(it, dict) and it.get('team_id') and it.get('grupo_id') \
                    and it['team_id'] not in seen_t:
                seen_t.add(it['team_id'])
                lst.append((it['team_id'], it['grupo_id'], it.get('team_name', '')))
    teams[t] = lst
for t, lst in teams.items():
    print(f'temporada {t} ({TEMPORADAS[t][0]}): {len(lst)} ομαδες', flush=True)

done = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding='utf-8'):
        try:
            r = json.loads(line)
            done.add((r['temporada'], r['team_id'], r['jornada']))
        except Exception:
            pass

fh = open(OUT, 'a', encoding='utf-8')
n_ok = n_err = 0
t0 = time.time()
for temp, (lg, njor) in TEMPORADAS.items():
    for tid, gid, tname in teams.get(temp, []):
        for j in range(1, njor + 1):
            if (temp, tid, j) in done:
                continue
            u = f'https://frpg.predicted11.com/api/juegos/participacion-criterios/{USER}/{tid}/{gid}/{j}/get/{TOKEN}'
            try:
                d = json.loads(getb(u))
                if int(d.get('temporada') or 0) != temp:
                    continue
                pred = [dict(nm=p.get('nombre'), pos=p.get('posicion')) for p in (d.get('participacion') or [])]
                rec = dict(temporada=temp, lg=lg, jornada=j, team_id=tid, team=tname,
                           puntuacion=d.get('puntuacion'),
                           date_start=d.get('date_start'), date_end=d.get('date_end'),
                           date_resultado=d.get('date_resultado'),
                           pred=pred, actual=d.get('respuesta'),
                           respuesta_url=d.get('respuesta_url'))
                fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
                n_ok += 1
            except urllib.error.HTTPError:
                n_err += 1
            except Exception as e:
                n_err += 1
                print(f'  ερρ {lg} {tname} J{j}: {type(e).__name__}', flush=True)
            if (n_ok + n_err) % 50 == 0:
                fh.flush()
                print(f'  {n_ok+n_err} αιτηματα · ok {n_ok} · err {n_err}', flush=True)
            time.sleep(0.35 + random.random() * 0.3)
fh.close()
print(f'ΤΕΛΟΣ 26/27: ok {n_ok} · err {n_err} · {(time.time()-t0)/60:.1f} λεπτα', flush=True)
