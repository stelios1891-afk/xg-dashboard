# -*- coding: utf-8 -*-
"""
nowgoal_fetch.py -- Κατεβασμα ιστορικου αποδοσεων απο Nowgoal για τα mapped ματς.

Ανα ματς x bookmaker (Bet365 cid=8, Crown cid=3): ενα request δινει και τις 3 αγορες
(ah=χαντικαπ, op=1Χ2, ou=γκολ) με unix timestamps. Κραταμε ΜΟΝΟ pre-match (ht=='').

Εξοδος: nowgoal_odds/{sea}_{lg}.jsonl — μια γραμμη ανα (ματς, βιβλιο):
    {"mid","ng","cid","ah":[[mt,u,g,d],...],"op":...,"ou":...}   (νεοτερο πρωτο)
Resumable (done-set απο τα υπαρχοντα αρχεια). Ευγενικος ρυθμος ~1.5 req/s.
Σειρα: σεζον 2526,2425,2324,2223 πρωτα (ερευνα CLV), μετα 2122.
"""
import sys, os, json, gzip, time, random, urllib.request, http.cookiejar
sys.stdout.reconfigure(encoding='utf-8')

OUT_DIR = 'nowgoal_odds'
os.makedirs(OUT_DIR, exist_ok=True)
BOOKS = {8: 'Bet365', 3: 'Crown'}
SEA_ORDER = ['2526', '2425', '2324', '2223', '2122']

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


# 30/9: host live10 → live11 (18/9)· init session απο σελιδα ΜΑΤΣ (η αρχικη = Cloudflare verify → code 1001)
HOST = 'https://live11.nowgoal26.com'

MAP = json.load(open('nowgoal_map.json', encoding='utf-8'))
# done-set
done = set()
for f in os.listdir(OUT_DIR):
    if f.endswith('.jsonl'):
        for line in open(os.path.join(OUT_DIR, f), encoding='utf-8'):
            try:
                r = json.loads(line)
                done.add((r['mid'], r['cid']))
            except Exception:
                pass

todo = []
# 2026-08-29 Στελιος: +2024-25 (η 2526 ηδη πληρης -> skip απο done-set) · 29/9: NG_SEASONS=2324,2223 για τα τεστ χρονου σε 4 σεζον
SEAS_ON = tuple(os.environ.get('NG_SEASONS', '2526,2425').split(','))
for mid, m in MAP.items():
    if m['sea'] not in SEAS_ON:
        continue
    for cid in BOOKS:
        if (mid, cid) not in done:
            todo.append((SEA_ORDER.index(m['sea']) if m['sea'] in SEA_ORDER else 9, mid, m, cid))
todo.sort(key=lambda x: x[0])
print(f'ματς×βιβλια: {len(MAP) * len(BOOKS)} · ηδη: {len(done)} · προς κατεβασμα: {len(todo)}', flush=True)
if todo:
    get(f"{HOST}/asian-handicap-odds/{todo[0][2]['ng']}")   # init session (ΟΧΙ home page)


def compact(rows):
    """κρατα ΜΟΝΟ pre-match (ht=='') ως [mt, u, g, d] — νεοτερο πρωτο."""
    out = []
    for r in rows or []:
        if r.get('ht') == '':
            o = r.get('odds') or {}
            out.append([r.get('mt'), o.get('u'), o.get('g'), o.get('d')])
    return out


t0 = time.time(); n_ok = 0; n_err = 0; consec_err = 0
handles = {}
for i, (pri, mid, m, cid) in enumerate(todo):
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
            get(ref)                                  # φρεσκα cookies (σελιδα ματς)
    if (i + 1) % 200 == 0:
        for h in handles.values():
            h.flush()
        el = time.time() - t0; rate = (i + 1) / el
        print(f'  {i+1}/{len(todo)} · ok {n_ok} · err {n_err} · {rate:.1f}/s · ETA {(len(todo)-i-1)/rate/3600:.1f}h', flush=True)
    time.sleep(0.35 + random.random() * 0.3)
for h in handles.values():
    h.close()
print(f'ΤΕΛΟΣ: ok {n_ok} · err {n_err} · {(time.time()-t0)/3600:.1f}h')
