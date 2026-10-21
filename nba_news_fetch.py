# -*- coding: utf-8 -*-
"""nba_news_fetch.py — ΙΣΤΟΡΙΚΟ ΕΙΔΗΣΕΩΝ ΠΑΙΚΤΩΝ NBA 2025-26 ΜΕ ΑΚΡΙΒΗ ΩΡΑ (21/10/2026, Στελιος «ξεκινα με το 3»).
Σκοπος: καθε ειδηση (αμφιβολος / εκτος / παιζει / δηλωσεις προπονητη) με ωρα → διπλα στις κινησεις τιμων Crown/Bet365 (ποσο & ποτε κουνηθηκε η γραμμη).
ΠΗΓΕΣ (δημοσιες σελιδες, χωρις λογαριασμο· αργος ρυθμος ~1 αιτημα / 1.2″, μια φορα):
  nbc  — nbcsports.com/fantasy/basketball/player-news?p=N (10 ειδησεις/σελιδα, ωρα UTC σε ms) → nba_news/nbc_2526.jsonl
  rw   — RotoWire ανα ομαδα: basketball/ajax/get-more-updates.php?type=team&itemID=XXX&lastUpdateTime=…&numUpdates=1 → η ακριβης ωρα της ειδησης
         ερχεται ως newLastUpdateTime (ωρα Pacific) → nba_news/rw_2526.jsonl
ΚΑΙ ΣΤΙΣ ΔΥΟ: links tweet (x/twitter.com/…/status/ID) → ακριβης ωρα του αρχικου tweet απο το ID (snowflake), ωρα UTC.
Συνεχιζει απο εκει που σταματησε (nba_news/state.json). Χρηση: python -I nba_news_fetch.py nbc | rw | all"""
import os, re, sys, json, time, html, datetime as dt, urllib.request, urllib.error, urllib.parse
from zoneinfo import ZoneInfo
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, 'nba_news'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36'}
START, END = dt.datetime(2025, 9, 25, tzinfo=dt.timezone.utc), dt.datetime(2026, 4, 20, tzinfo=dt.timezone.utc)
PT = ZoneInfo('America/Los_Angeles'); SLEEP = 1.2
STF = os.path.join(OUT, 'state.json')
def st_load():
    try: return json.load(open(STF, encoding='utf-8'))
    except Exception: return {}
def st_save(S): json.dump(S, open(STF, 'w', encoding='utf-8'), ensure_ascii=False)
def get(u, hdr=None):
    for k in range(5):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers={**UA, **(hdr or {})}), timeout=40).read().decode('utf-8', 'ignore')
        except urllib.error.HTTPError as e:
            if e.code in (403, 429): print('μπλοκ/ορια', e.code, '— αναμονη 10′', flush=True); time.sleep(600)
            else: time.sleep(5 + 10 * k)
        except Exception: time.sleep(5 + 10 * k)
    return None
def tweets(s):
    out = []
    for user, tid in re.findall(r'(?:x|twitter)\.com/([A-Za-z0-9_]+)/status/(\d+)', s):
        t = dt.datetime.fromtimestamp(((int(tid) >> 22) + 1288834974657) / 1000, dt.timezone.utc)
        out.append([user, tid, t.isoformat(timespec='seconds')])
    return out
def clean(x): return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', x or ''))).strip()
# ---------------- NBC ----------------
def nbc():
    S = st_load(); p = S.get('nbc_page', 1); fn = os.path.join(OUT, 'nbc_2526.jsonl'); n = 0
    with open(fn, 'a', encoding='utf-8') as fh:
        while True:
            s = get(f'https://www.nbcsports.com/fantasy/basketball/player-news?p={p}')
            if s is None: print('NBC: αποτυχια σελιδας', p, flush=True); break
            posts = s.split('class="PlayerNewsPost"')[1:]
            if not posts: print('NBC: τελος (αδεια σελιδα)', p, flush=True); break
            oldest = None
            for q in posts:
                d = re.search(r'data-date="([^"]+)"', q)
                if not d: continue
                ts = dt.datetime.fromisoformat(d.group(1).replace('Z', '+00:00')); oldest = ts if oldest is None or ts < oldest else oldest
                if not (START <= ts <= END): continue
                fn_ = re.search(r'PlayerNewsPost-firstName">([^<]*)<', q); ln_ = re.search(r'PlayerNewsPost-lastName">([^<]*)<', q)
                src = re.search(r'PlayerNewsPost-source">.*?<a href="([^"]+)"[^>]*>([^<]*)<', q, re.S)
                rec = dict(src='nbc', ts=ts.isoformat(timespec='milliseconds'), player=clean((fn_.group(1) if fn_ else '') + ' ' + (ln_.group(1) if ln_ else '')),
                           team=(re.search(r'PlayerNewsPost-team-abbr">([^<]*)<', q) or [None, None])[1],
                           headline=clean((re.search(r'PlayerNewsPost-headline">(.*?)</h3>', q, re.S) or [None, ''])[1]),
                           analysis=clean((re.search(r'PlayerNewsPost-analysis">(.*?)</div>', q, re.S) or [None, ''])[1])[:600],
                           type=clean((re.search(r'PlayerNewsPost-type">(.*?)</div>', q, re.S) or [None, ''])[1]),
                           source=[src.group(2).strip(), src.group(1)] if src else None, tweets=tweets(q))
                fh.write(json.dumps(rec, ensure_ascii=False) + '\n'); n += 1
            fh.flush(); S['nbc_page'] = p + 1; st_save(S)
            if p % 50 == 0: print(f'NBC σελιδα {p} · {oldest} · {n} νεες', flush=True)
            if oldest and oldest < START: print('NBC: εφτασε πριν τη σεζον', p, flush=True); break
            p += 1; time.sleep(SLEEP)
    S['nbc_done'] = True; st_save(S); print('NBC ΤΕΛΟΣ ·', n, 'ειδησεις', flush=True)
# ---------------- RotoWire ----------------
RW_TEAMS = 'ATL BOS BKN CHA CHI CLE DAL DEN DET GSW HOU IND LAC LAL MEM MIA MIL MIN NOP NYK OKC ORL PHI PHX POR SAC SAS TOR UTA WAS'.split()
ALT = {'GSW': 'GS', 'NOP': 'NO', 'SAS': 'SA', 'PHX': 'PHO', 'UTA': 'UTAH', 'WAS': 'WSH', 'BKN': 'BRK', 'NYK': 'NY'}
def rw_call(team, last):
    u = ('https://www.rotowire.com/basketball/ajax/get-more-updates.php?type=team&itemID=' + team + '&lastUpdateTime=' +
         urllib.parse.quote(last) + '&numUpdates=1')
    s = get(u, {'X-Requested-With': 'XMLHttpRequest'})
    try: return json.loads(s) if s else None
    except Exception: return None
def rw():
    S = st_load(); fn = os.path.join(OUT, 'rw_2526.jsonl'); done = set(S.get('rw_done', []))
    end_pt = END.astimezone(PT).strftime('%Y-%m-%d %H:%M:%S.000'); start_pt = START.astimezone(PT)
    with open(fn, 'a', encoding='utf-8') as fh:
        for team in RW_TEAMS:
            if team in done: continue
            code = S.get('rw_code', {}).get(team, team); last = S.get('rw_last', {}).get(team, end_pt); n = 0; same = 0; prev_t = None
            d = rw_call(code, last)
            if (not d or not d.get('updatesHTML')) and team in ALT:
                code = ALT[team]; d = rw_call(code, last)
            S.setdefault('rw_code', {})[team] = code
            while d and d.get('updatesHTML'):
                t_pt = d.get('newLastUpdateTime')
                q = d['updatesHTML']
                try: ts = dt.datetime.strptime(t_pt, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=PT)
                except Exception: ts = None
                if ts and ts < start_pt: break
                if t_pt == prev_t: same += 1
                else: same = 0
                nw = re.search(r'news-update__news">(.*?)</div>', q, re.S); news = nw.group(1) if nw else ''
                rec = dict(src='rw', team=team, ts=ts.astimezone(dt.timezone.utc).isoformat(timespec='milliseconds') if ts else None, ts_pt=t_pt,
                           player=clean((re.search(r'player-link"[^>]*>([^<]+)', q) or [None, ''])[1]),
                           headline=clean((re.search(r'news-update__headline">([^<]+)', q) or [None, ''])[1]),
                           news=clean(news)[:600], date_txt=clean((re.search(r'timestamp">([^<]+)', q) or [None, ''])[1]),
                           inj=clean((re.search(r'news-update__inj">([^<]+)', q) or [None, ''])[1]),
                           links=re.findall(r'href="([^"]+)"', news)[:6], tweets=tweets(news))
                if same == 0: fh.write(json.dumps(rec, ensure_ascii=False) + '\n'); n += 1
                prev_t = t_pt
                # επομενη: 1 ms πριν (αποφυγη κολληματος σε ιδια ωρα)
                try: last = (dt.datetime.strptime(t_pt, '%Y-%m-%d %H:%M:%S.%f') - dt.timedelta(milliseconds=1)).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                except Exception: break
                S.setdefault('rw_last', {})[team] = last
                if n % 100 == 0 and same == 0: fh.flush(); st_save(S); print(f'RotoWire {team}: {n} · {t_pt}', flush=True)
                if same > 5: print('RotoWire', team, 'κολλημα στην ιδια ωρα — επομενη ομαδα', flush=True); break
                time.sleep(SLEEP); d = rw_call(code, last)
            fh.flush(); done.add(team); S['rw_done'] = sorted(done); st_save(S); print(f'RotoWire {team} ΤΕΛΟΣ · {n} ειδησεις', flush=True)
# ---------------- NBC παλιες σεζον (21/10/2026, Στελιος «οκ ξεκινα»: 2021-22 … 2024-25 για τα τεστ t48/t49 σε 5 σεζον) ----------------
# Δικο του αρχειο κατασταστασης (το rw() ξαναγραφει ολο το state.json) · εξοδος nba_news/nbc_hist.jsonl · διπλα (ιδια ωρα+παικτης+τιτλος) πετιουνται
# (οι σελιδες «γλιστρανε» οσο μπαινουν νεες ειδησεις).
H_START, H_END = dt.datetime(2021, 9, 25, tzinfo=dt.timezone.utc), dt.datetime(2025, 4, 20, tzinfo=dt.timezone.utc)
HSTF = os.path.join(OUT, 'state_nbc_hist.json')
def nbc_page(p):
    s = get(f'https://www.nbcsports.com/fantasy/basketball/player-news?p={p}')
    if s is None: return None, []
    posts = s.split('class="PlayerNewsPost"')[1:]
    return s, posts
def page_date(p):
    _, posts = nbc_page(p)
    d = [dt.datetime.fromisoformat(m.replace('Z', '+00:00')) for q in posts for m in re.findall(r'data-date="([^"]+)"', q)[:1]]
    return min(d) if d else None
def nbc_hist():
    try: H = json.load(open(HSTF, encoding='utf-8'))
    except Exception: H = {}
    fn = os.path.join(OUT, 'nbc_hist.jsonl'); seen = set()
    if os.path.exists(fn):
        for ln in open(fn, encoding='utf-8'):
            try: r = json.loads(ln); seen.add((r['ts'], r['player'], r['headline']))
            except Exception: pass
    p = H.get('page')
    if p is None:                                              # δυαδικη αναζητηση: πρωτη σελιδα με ειδησεις ≤ H_END
        lo, hi = 1, 30000
        while hi - lo > 5:
            mid = (lo + hi) // 2; d = page_date(mid); time.sleep(SLEEP)
            if d is None or d < H_END: hi = mid
            else: lo = mid
        p = max(1, lo - 3); print('NBC παλιες: αρχη απο σελιδα', p, flush=True)
    n = 0
    with open(fn, 'a', encoding='utf-8') as fh:
        while True:
            s, posts = nbc_page(p)
            if s is None: print('NBC παλιες: αποτυχια σελιδας', p, flush=True); time.sleep(60); continue
            if not posts: print('NBC παλιες: τελος (αδεια σελιδα)', p, flush=True); break
            oldest = None
            for q in posts:
                d = re.search(r'data-date="([^"]+)"', q)
                if not d: continue
                ts = dt.datetime.fromisoformat(d.group(1).replace('Z', '+00:00')); oldest = ts if oldest is None or ts < oldest else oldest
                if not (H_START <= ts <= H_END): continue
                fn_ = re.search(r'PlayerNewsPost-firstName">([^<]*)<', q); ln_ = re.search(r'PlayerNewsPost-lastName">([^<]*)<', q)
                src = re.search(r'PlayerNewsPost-source">.*?<a href="([^"]+)"[^>]*>([^<]*)<', q, re.S)
                rec = dict(src='nbc', ts=ts.isoformat(timespec='milliseconds'), player=clean((fn_.group(1) if fn_ else '') + ' ' + (ln_.group(1) if ln_ else '')),
                           team=(re.search(r'PlayerNewsPost-team-abbr">([^<]*)<', q) or [None, None])[1],
                           headline=clean((re.search(r'PlayerNewsPost-headline">(.*?)</h3>', q, re.S) or [None, ''])[1]),
                           analysis=clean((re.search(r'PlayerNewsPost-analysis">(.*?)</div>', q, re.S) or [None, ''])[1])[:600],
                           type=clean((re.search(r'PlayerNewsPost-type">(.*?)</div>', q, re.S) or [None, ''])[1]),
                           source=[src.group(2).strip(), src.group(1)] if src else None, tweets=tweets(q))
                k = (rec['ts'], rec['player'], rec['headline'])
                if k in seen: continue
                seen.add(k); fh.write(json.dumps(rec, ensure_ascii=False) + '\n'); n += 1
            fh.flush(); H['page'] = p + 1; json.dump(H, open(HSTF, 'w', encoding='utf-8'))
            if p % 100 == 0: print(f'NBC παλιες σελιδα {p} · {oldest} · {n} νεες', flush=True)
            if oldest and oldest < H_START: print('NBC παλιες: εφτασε πριν το 2021-22 · ΤΕΛΟΣ', p, n, flush=True); break
            p += 1; time.sleep(SLEEP)
if __name__ == '__main__':
    m = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if m == 'nbc_hist': nbc_hist(); sys.exit()
    if m in ('nbc', 'all') and not st_load().get('nbc_done'): nbc()
    if m in ('rw', 'all'): rw()
