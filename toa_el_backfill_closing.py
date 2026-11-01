# -*- coding: utf-8 -*-
"""toa_el_backfill_closing.py — συμπληρωνει CLOSING Pinnacle (1-2, handicap, συνολο) για ματς Ευρωλιγκας της σεζον
που ΞΕΚΙΝΗΣΑΝ χωρις εγγραφη πριν το τζαμπολ στο el_odds_hist.jsonl (24/9/2026, αιτημα Στελιου).
Για καθε ωρα τζαμπολ: ενα ιστορικο snapshot TOA 5' πριν (h2h,spreads,totals · eu · 30 credits), ιδιο parsing/ταιριασμα
με τον scanner (el_odds_scan.build_records) -> el_closing_backfill.jsonl (ιδια μορφη με el_odds_hist.jsonl· t < commence = «κλεισιμο» για το dashboard).
Idempotent: ματς που εχουν ηδη προ-τζαμπολ εγγραφη αγνοουνται. Τρεχει ΜΟΝΟ στο GitHub (TOA_KEY)."""
import os, sys, json, datetime as dt
import requests
sys.stdout.reconfigure(encoding='utf-8')
import el_odds_scan as E
KEY = os.environ.get('TOA_KEY')
if not KEY:
    print('TOA_KEY λειπει (μονο GitHub) — 0 credits'); sys.exit(0)
SEASON = 'E2026'
S = json.load(open('el_sched.json', encoding='utf-8'))[SEASON]
now = dt.datetime.now(dt.timezone.utc)
have = set()
for fn in ('el_odds_hist.jsonl', 'el_closing_backfill.jsonl'):
  if os.path.exists(fn):
    for ln in open(fn, encoding='utf-8'):
        try:
            r = json.loads(ln)
            if E._pdt(r['t']) < E._pdt(r['commence']): have.add(str(r['code']))
        except Exception:
            pass
todo = [x for x in S if E._pdt(x['utc']) <= now and str(x['code']) not in have]
games = [dict(code=x['code'], round=x.get('rnd'), utc=E._pdt(x['utc']), hcode=x['hcode'], acode=x['acode'], home=x['home'], away=x['away'])
         for x in S]
tips = sorted({x['utc'][:16] for x in todo})
print(f'ματς που ξεκινησαν χωρις closing: {len(todo)} · ωρες τζαμπολ: {tips}')
rows_all = []
for tip in tips:
    snap = E._pdt(tip) - dt.timedelta(minutes=5)
    r = requests.get('https://api.the-odds-api.com/v4/historical/sports/basketball_euroleague/odds',
                     params=dict(apiKey=KEY, regions='eu', markets='h2h,spreads,totals', oddsFormat='decimal',
                                 date=snap.strftime('%Y-%m-%dT%H:%M:%SZ')), timeout=40)
    print(f'  {tip}: HTTP {r.status_code} · credits left {r.headers.get("x-requests-remaining")}', flush=True)
    if r.status_code != 200: continue
    j = r.json(); ts = E._pdt(j.get('timestamp') or snap.isoformat())
    want = {str(x['code']) for x in todo if x['utc'][:16] == tip}
    _, hist_rows, unm, n = E.build_records(j.get('data') or [], games, ts, {})
    got = [h for h in hist_rows if str(h['code']) in want]
    print(f'     ταιριαξαν {len(got)}/{len(want)}' + (f' · αταιριαστα {unm[:3]}' if unm else ''))
    rows_all += got
with open('el_closing_backfill.jsonl', 'a', encoding='utf-8') as fh:
    for h in rows_all:
        fh.write(json.dumps(h, ensure_ascii=False) + '\n')
print(f'ΟΚ: {len(rows_all)} closing γραμμες -> el_closing_backfill.jsonl')
