"""intl_ng_hist_afconq.py — ΙΣΤΟΡΙΚΕΣ γραμμες Nowgoal (Crown 3, SBOBET 31, closing) για Africa Cup of Nations
(Nowgoal c93 combined id: qualifiers ΚΑΙ τελικη φαση μαζι) — 2 προηγουμενες εκδοσεις: 2022-2024 (AFCON2023),
2024-2026 (AFCON2025). Odds-only (δεν παιρνει xG/σουτ, αυτα ερχονται απο FotMob data_AFCON(Q)_*.json).
Resumable (ng id σε out ήδη -> skip). -> intl_ng_hist_afconq.json {ng: {sea, dt, hid, aid, hs, as, books:{}}}"""
import sys, os, json, gzip, time, urllib.request, http.cookiejar
sys.stdout.reconfigure(encoding='utf-8')
HOST = 'https://live11.nowgoal26.com'
OUT_F = 'intl_ng_hist_afconq.json'
SEASONS = ['2022-2024', '2024-2026', '2019-2022', '2017-2019']   # 25/9: + κυκλοι AFCON 2021 ('2019-2022' στο Nowgoal) και AFCON 2019 (Στελιος: «αμα λειπουν δεδομενα να τα βρουμε»)
cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
BASE = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'), ('Accept', '*/*'), ('Accept-Encoding', 'gzip'), ('Accept-Language', 'en-US,en;q=0.9'), ('X-Requested-With', 'XMLHttpRequest')]


def get(u, ref=None):
    op.addheaders = BASE + ([('Referer', ref)] if ref else []); d = op.open(u, timeout=25).read()
    if d[:2] == bytes([0x1f, 0x8b]): d = gzip.decompress(d)
    return d.decode('utf-8', 'replace')


def compact(rs):
    o = []
    for r in rs or []:
        if r.get('ht') == '':
            od = r.get('odds') or {}; o.append([r.get('mt'), od.get('g'), od.get('u'), od.get('d'), bool(r.get('close'))])
    return sorted(o, key=lambda x: x[0] or 0)


out = json.load(open(OUT_F, encoding='utf-8')) if os.path.exists(OUT_F) else {}
t0 = time.time(); n_new = 0
for sea in SEASONS:
    fn = f'ng_c93_{sea}.json'
    if not os.path.exists(fn):
        t = get(f'https://football.nowgoal26.com/jsData/matchResult/json/{sea}/c93_en.json', ref=f'https://football.nowgoal26.com/league/{sea}/93')
        open(fn, 'w', encoding='utf-8').write(t)
    try:
        j = json.loads(open(fn, encoding='utf-8-sig').read().lstrip('\ufeff'))
    except Exception:
        print(f'{sea}: \u03b4\u03b5\u03bd \u03c5\u03c0\u03b1\u03c1\u03c7\u03b5\u03b9 \u03c3\u03c4\u03bf Nowgoal (\u03bf\u03c7\u03b9 json) \u2014 \u03c0\u03b1\u03c1\u03b1\u03bb\u03b5\u03b9\u03c0\u03b5\u03c4\u03b1\u03b9', flush=True); os.remove(fn); continue
    rows = []
    for v in (j.get('ScheduleList') or {}).values():
        for r in v:
            if isinstance(r[4], list):
                rows.extend(r[4])
            else:
                rows.append(r)
    rows = sorted(rows, key=lambda r: str(r[3]))
    todo = [r for r in rows if str(r[0]) not in out]
    print(f'{sea}: {len(rows)} ματς, {len(todo)} νεα', flush=True)
    if not todo:
        continue
    get(f'{HOST}/asian-handicap-odds/{todo[0][0]}')
    for i, r in enumerate(todo):
        ng = int(r[0])
        rec = dict(sea=sea, dt=str(r[3]), hid=int(r[4]), aid=int(r[5]), hs=r[6], as_=r[7], books={})
        for cid in (3, 31):
            try:
                jj = json.loads(get(f'{HOST}/ajax/soccerajax?type=14&id={ng}&t=20&cid={cid}&h=0&r1=5&r2=0&r3=1', ref=f'{HOST}/asian-handicap-odds/{ng}'))
                D = jj.get('Data') or {}; rec['books'][str(cid)] = dict(ah=compact(D.get('ah')), ou=compact(D.get('ou')), op=compact(D.get('op')))
            except Exception as e:
                rec['books'][str(cid)] = dict(err=str(e)[:60])
            time.sleep(0.35)
        out[str(ng)] = rec; n_new += 1
        if (i + 1) % 20 == 0:
            print(f'  {sea} {i+1}/{len(todo)} · {(time.time()-t0)/60:.1f} min', flush=True)
            json.dump(out, open(OUT_F, 'w', encoding='utf-8'))
    json.dump(out, open(OUT_F, 'w', encoding='utf-8'))
print(f'ΤΕΛΟΣ: {n_new} νεα σε {(time.time()-t0)/60:.1f} min · συνολο {len(out)}', flush=True)
