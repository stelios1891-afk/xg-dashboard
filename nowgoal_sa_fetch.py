# -*- coding: utf-8 -*-
"""
nowgoal_sa_fetch.py -- Ιστορικο pre-match αποδοσεων Nowgoal (AH + OU + 1Χ2) για Brazil Serie A & MLS, 2021-2026.

Εισοδος: nowgoal_sa_matches.json (απο nowgoal_sa_map.py) -- ΔΕΝ εξαρταται απο το FotMob mapping.
Εξοδος:
  nowgoal_odds/{ετος}_{Brazil|MLS}.jsonl  -- ιδιο format με nowgoal_europe_fetch.py: ΜΙΑ γραμμη ανα (ματς, βιβλιο)
        {mid, ng, cid, ah:[[unix,home_odds_HK,line,away_odds_HK],...], op:[...], ou:[[unix,over,line,under],...]}  (νεοτερο πρωτο)
        cid 3 = Crown, 31 = SBOBET. mid = FotMob mid αν υπαρχει στο nowgoal_sa_map.json, αλλιως ng<ngid>
        (το nowgoal_sa_remap.py ξαναγραφει τα mid οταν εμφανιστουν νεα FotMob αρχεια).
  nowgoal_sa_1x2_{lg}.jsonl -- ιδιο format με nowgoal_intl_1x2.jsonl (Crown & SBOBET, 1x2.nowgoal26.com/{ng}.js)
        (το nowgoal_sa_remap.py τα ενωνει στο nowgoal_sa_1x2.jsonl)
Resumable: done-set ανα (ng, cid) / ng. Μονο ματς με ωρα εναρξης πριν απο τωρα-3ω.
Χρηση: SA_LG=Brazil python nowgoal_sa_fetch.py   (ή MLS · χωρις SA_LG = και τα δυο)   [--limit N]
"""
import sys, os, re, glob, json, gzip, time, random, datetime as dt, urllib.request, http.cookiejar
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

OUT_DIR = 'nowgoal_odds'; os.makedirs(OUT_DIR, exist_ok=True)
BOOKS = {3: 'Crown', 31: 'SBOBET'}
BK1X2 = {'Crown': 'Crown', 'Sbobet': 'SBOBET'}
HOST = 'https://live11.nowgoal26.com'
LGS = [os.environ['SA_LG']] if os.environ.get('SA_LG') else ['Brazil', 'MLS']
SEAS = os.environ['SA_SEAS'].split(',') if os.environ.get('SA_SEAS') else None      # π.χ. SA_SEAS=2026,2025
TAG = os.environ.get('SA_TAG', '')
LIMIT = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None

cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
BASE = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'),
        ('Accept', '*/*'), ('Accept-Encoding', 'gzip')]


def get(u, ref=None):
    op.addheaders = BASE + ([('Referer', ref)] if ref else [])
    r = op.open(u, timeout=30)
    d = r.read()
    if d[:2] == b'\x1f\x8b':
        d = gzip.decompress(d)
    return d.decode('utf-8', 'replace')


def compact(rows):
    """κρατα ΜΟΝΟ pre-match (ht=='') ως [mt, u, g, d] -- νεοτερο πρωτο."""
    out = []
    for r in rows or []:
        if r.get('ht') == '':
            o = r.get('odds') or {}
            out.append([r.get('mt'), o.get('u'), o.get('g'), o.get('d')])
    return out


def parse_1x2(txt, match_date):
    game = re.search(r'var game\s*=\s*Array\((.*?)\);', txt, re.S)
    det = re.search(r'var gameDetail\s*=\s*Array\((.*?)\);', txt, re.S)
    if not game or not det:
        return {}
    rows = re.findall(r'"([^"]*)"', game.group(1))
    dets = dict(x.split('^', 1) for x in re.findall(r'"([^"]*)"', det.group(1)) if '^' in x)
    y0 = int(match_date[:4]); m0 = int(match_date[5:7]); out = {}
    for r in rows:
        f = r.split('|')
        if len(f) < 13 or f[2] not in BK1X2:
            continue
        try:
            op_, cl_ = [float(x) for x in f[3:6]], [float(x) for x in f[10:13]]
        except ValueError:
            continue
        hist = []
        for it in dets.get(f[1], '').split(';'):
            p = it.split('|')
            if len(p) < 4:
                continue
            try:
                mo, dd = int(p[3][:2]), int(p[3][3:5]); hh, mi = int(p[3][6:8]), int(p[3][9:11])
                yr = y0 - 1 if mo > m0 + 6 else (y0 + 1 if mo < m0 - 6 else y0)
                t = dt.datetime(yr, mo, dd, hh, mi, tzinfo=dt.timezone.utc) - dt.timedelta(hours=8)     # UTC+8 -> UTC
                hist.append([int(t.timestamp()), float(p[0]), float(p[1]), float(p[2])])
            except (ValueError, IndexError):
                continue
        hist.sort()
        out[BK1X2[f[2]]] = dict(open=op_, close=cl_, rows=hist)
    return out


M = json.load(open('nowgoal_sa_matches.json', encoding='utf-8'))
try:
    FM = {str(v['ng']): k for k, v in json.load(open('nowgoal_sa_map.json', encoding='utf-8')).items()}   # ng -> our mid
except FileNotFoundError:
    FM = {}
now = dt.datetime.utcnow()
cut = (now - dt.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M')

done_ah, done_x = set(), set()
for lg in LGS:
    for f in os.listdir(OUT_DIR):
        if f.endswith(f'_{lg}.jsonl'):
            for line in open(os.path.join(OUT_DIR, f), encoding='utf-8'):
                try:
                    r = json.loads(line); done_ah.add((int(r['ng']), int(r['cid'])))
                except Exception:
                    pass
    for fx in glob.glob(f'nowgoal_sa_1x2_{lg}*.jsonl'):
        for line in open(fx, encoding='utf-8'):
            try:
                done_x.add(int(json.loads(line)['ng']))
            except Exception:
                pass

todo = []
for ng, m in M.items():
    if m['lg'] in LGS and m['dt_utc'] <= cut and (SEAS is None or m['sea'] in SEAS):
        todo.append((0, m['sea'], int(ng), m))
# πρωτα οι πιο προσφατες σεζον, χρονολογικα εντος σεζον
todo.sort(key=lambda x: (-int(x[1]), x[3]['dt_utc']))
todo = [t for t in todo if not (all((t[2], c) in done_ah for c in BOOKS) and t[2] in done_x)]
if LIMIT:
    todo = todo[:LIMIT]
print(f'{LGS}: ματς προς κατεβασμα {len(todo)} (ματς συνολο {sum(1 for m in M.values() if m["lg"] in LGS)})', flush=True)
if not todo:
    sys.exit(0)

get(f"{HOST}/asian-handicap-odds/{todo[0][2]}")       # init session απο σελιδα ΜΑΤΣ


def jitter():
    time.sleep(0.45 + random.random() * 0.5)


t0 = time.time(); n_ok = n_err = consec = 0
H = {}
for i, (_, sea, ng, m) in enumerate(todo):
    lg = m['lg']; mid = FM.get(str(ng), f'ng{ng}')
    ref = f'{HOST}/asian-handicap-odds/{ng}'
    try:
        for cid in BOOKS:
            if (ng, cid) in done_ah:
                continue
            for att in range(3):
                try:
                    j = json.loads(get(f'{HOST}/ajax/soccerajax?type=14&id={ng}&t=20&cid={cid}&h=0&r1=5&r2=0&r3=1', ref=ref))
                    if j.get('ErrCode') != 0:
                        raise RuntimeError(f'ErrCode {j.get("ErrCode")}')
                    break
                except Exception as e:
                    if att == 2:
                        raise
                    time.sleep(3 + 4 * att)
            data = j.get('Data') or {}
            rec = dict(mid=mid, ng=ng, cid=cid, ah=compact(data.get('ah')), op=compact(data.get('op')), ou=compact(data.get('ou')))
            key = f'{sea}_{lg}'
            if key not in H:
                H[key] = open(os.path.join(OUT_DIR, key + '.jsonl'), 'a', encoding='utf-8')
            H[key].write(json.dumps(rec, ensure_ascii=False) + '\n'); H[key].flush()
            done_ah.add((ng, cid))
            jitter()
        if ng not in done_x:
            for att in range(3):
                try:
                    res = parse_1x2(get(f'https://1x2.nowgoal26.com/{ng}.js', ref=f'{HOST}/1x2-odds/{ng}'), m['date_utc'])
                    break
                except Exception as e:
                    if att == 2:
                        raise
                    time.sleep(3 + 4 * att)
            kx = f'x_{lg}'
            if kx not in H:
                H[kx] = open(f'nowgoal_sa_1x2_{lg}{TAG}.jsonl', 'a', encoding='utf-8')
            if not res:     # ΚΕΝΟ: γραφουμε ενα placeholder ωστε να μη ξαναζητηθει
                H[kx].write(json.dumps(dict(mid=mid, ng=ng, book=None), ensure_ascii=False) + '\n')
            for bk, v in res.items():
                H[kx].write(json.dumps(dict(mid=mid, ng=ng, book=bk, **v), ensure_ascii=False) + '\n')
            H[kx].flush(); done_x.add(ng)
            jitter()
        n_ok += 1; consec = 0
    except Exception as e:
        n_err += 1; consec += 1
        print(f'  ερρ ng{ng}: {type(e).__name__} {str(e)[:80]}', flush=True)
        if consec >= 6:
            print('6 συνεχομενα σφαλματα -- παυση 5 λεπτα', flush=True)
            time.sleep(300); consec = 0
            try:
                get(ref)
            except Exception:
                pass
    if (i + 1) % 100 == 0:
        el = time.time() - t0; rate = (i + 1) / el
        print(f'  {i+1}/{len(todo)} · ok {n_ok} · err {n_err} · {rate*3600:.0f} ματς/ω · ETA {(len(todo)-i-1)/rate/3600:.1f}h · τρεχον {sea} {m["dt_utc"]}', flush=True)
for h in H.values():
    h.close()
print(f'ΤΕΛΟΣ: ok {n_ok} · err {n_err} · {(time.time()-t0)/3600:.2f}h', flush=True)
