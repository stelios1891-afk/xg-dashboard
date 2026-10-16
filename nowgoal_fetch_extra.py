# -*- coding: utf-8 -*-
"""
nowgoal_fetch_extra.py -- Κατεβασμα ιστορικου αποδοσεων Nowgoal (Bet365 cid=8, Crown cid=3) για τα ματς του
nowgoal_map_extra.json (22 επιπλεον εγχωριες λιγκες). Ιδια λογικη/μορφη με nowgoal_fetch.py:
ενα request ανα ματς x βιβλιο δινει ah/op/ou, κραταμε ΜΟΝΟ pre-match (ht==''). Εξοδος: nowgoal_odds/{sea}_{lg}.jsonl
    {"mid","ng","cid","ah":[[mt,u,g,d],...],"op":...,"ou":...}   (νεοτερο πρωτο)
Σειρα: ΠΡΩΤΑ ματς ομαδων που επαιξαν Ευρωπη τη σεζον (eu=1), μετα τα υπολοιπα· μεσα σε καθε φαση: σειρα λιγκων
προτεραιοτητας, σεζον νεοτερη πρωτα. Resumable (done-set απο ολα τα nowgoal_odds/*.jsonl).
"""
import sys, os, json, gzip, time, random, urllib.request, http.cookiejar
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

OUT_DIR = 'nowgoal_odds'
os.makedirs(OUT_DIR, exist_ok=True)
BOOKS = {8: 'Bet365', 3: 'Crown'}
PRIO = ['CzechFirstLeague', 'CroatiaHNL', 'SerbiaSuperLiga', 'SlovakiaNikeLiga', 'SloveniaPrvaLiga', 'HungaryNBI',
        'BulgariaFirstLeague', 'BosniaPremierLeague', 'UkrainePremierLeague', 'RomaniaLigaI', 'Ekstraklasa',
        'AustrianBundesliga', 'SwissSuperleague', 'DanishSuperLiga', 'Belgium', 'ScottishPrem', 'TurkishSuperLig',
        'GreeceSL', 'CyprusFirstDivision', 'IsraelLigatHaAl', 'Eliteserien', 'Allsvenskan']
CAL = {'Eliteserien', 'Allsvenskan'}

cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
BASE = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'),
        ('Accept', '*/*'), ('Accept-Encoding', 'gzip')]


def get(u, ref=None):
    op.addheaders = BASE + ([('Referer', ref)] if ref else [])
    r = op.open(u, timeout=25)
    d = r.read()
    if d[:2] == b'\x1f\x8b':
        d = gzip.decompress(d)
    return d.decode('utf-8', 'replace')


HOST = 'https://live11.nowgoal26.com'
MAP = json.load(open('nowgoal_map_extra.json', encoding='utf-8'))
done = set()
for f in os.listdir(OUT_DIR):
    if f.endswith('.jsonl'):
        for line in open(os.path.join(OUT_DIR, f), encoding='utf-8'):
            try:
                r = json.loads(line); done.add((r['mid'], r['cid']))
            except Exception:
                pass


def rank(m):
    yr = int(m['sea']) - 2000 if m['lg'] in CAL else int(m['sea'][:2])
    return (0 if m.get('eu') else 1, PRIO.index(m['lg']) if m['lg'] in PRIO else 99, -yr)


todo = []
for mid, m in MAP.items():
    for cid in BOOKS:
        if (mid, cid) not in done:
            todo.append((rank(m), mid, m, cid))
todo.sort(key=lambda x: x[0])
print(f'ματς×βιβλια: {len(MAP) * len(BOOKS)} · ηδη: {len(done)} · προς κατεβασμα: {len(todo)} '
      f'(eu φαση: {sum(1 for t in todo if t[0][0] == 0)})', flush=True)
if todo:
    get(f"{HOST}/asian-handicap-odds/{todo[0][2]['ng']}")


def compact(rows):
    out = []
    for r in rows or []:
        if r.get('ht') == '':
            o = r.get('odds') or {}
            out.append([r.get('mt'), o.get('u'), o.get('g'), o.get('d')])
    return out


t0 = time.time(); n_ok = 0; n_err = 0; consec_err = 0
handles = {}
for i, (rk, mid, m, cid) in enumerate(todo):
    ng = m['ng']
    url = f'{HOST}/ajax/soccerajax?type=14&id={ng}&t=20&cid={cid}&h=0&r1=5&r2=0&r3=1'
    ref = f'{HOST}/asian-handicap-odds/{ng}'
    try:
        j = json.loads(get(url, ref=ref))
        if j.get('ErrCode') != 0:
            raise RuntimeError(f'ErrCode {j.get("ErrCode", j)}')
        data = j.get('Data') or {}
        rec = dict(mid=mid, ng=ng, cid=cid,
                   ah=compact(data.get('ah')), op=compact(data.get('op')), ou=compact(data.get('ou')))
        key = f"{m['sea']}_{m['lg']}"
        if key not in handles:
            handles[key] = open(os.path.join(OUT_DIR, key + '.jsonl'), 'a', encoding='utf-8')
        handles[key].write(json.dumps(rec, ensure_ascii=False) + '\n')
        n_ok += 1; consec_err = 0
    except Exception as e:
        n_err += 1; consec_err += 1
        print(f'  ερρ {mid}/{cid}: {type(e).__name__} {str(e)[:60]}', flush=True)
        if consec_err >= 8:
            print('8 συνεχομενα σφαλματα — παυση 5 λεπτα', flush=True)
            time.sleep(300); consec_err = 0
            try:
                get(ref)
            except Exception as e2:
                print('  re-init ερρ', e2, flush=True)
    if (i + 1) % 50 == 0:
        for h in handles.values():
            h.flush()
    if (i + 1) % 500 == 0:
        el = time.time() - t0; rate = (i + 1) / el
        print(f'  {i+1}/{len(todo)} · ok {n_ok} · err {n_err} · {rate:.1f}/s · ETA {(len(todo)-i-1)/rate/3600:.1f}h '
              f'· τρεχον: {m["lg"]} {m["sea"]} eu={m.get("eu")}', flush=True)
    time.sleep(0.35 + random.random() * 0.3)
for h in handles.values():
    h.close()
print(f'ΤΕΛΟΣ: ok {n_ok} · err {n_err} · {(time.time()-t0)/3600:.1f}h')
