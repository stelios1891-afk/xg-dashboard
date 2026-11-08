# -*- coding: utf-8 -*-
"""toa_el_ht_fetch.py — 29/10/2026: τιμες PINNACLE (TOA historical, regions eu, totals) ΣΤΟ ΗΜΙΧΡΟΝΟ για τα φετινα bets ημιχρονου
(el_ht_pin_slots.json, παραθυρο = Crown in-play με σκορ ημιχρονου). Ενα snapshot ανα bet, 60″ πριν το τελος του παραθυρου (~10 credits).
Τρεχει ΜΟΝΟ στο GitHub Actions (TOA_KEY). Εξοδος: toa_el_ht.jsonl"""
import os, json, datetime as dt, requests
KEY = os.environ.get('TOA_KEY'); assert KEY, 'TOA_KEY'
S = json.load(open('el_ht_pin_slots.json', encoding='utf-8'))
OUT = 'toa_el_ht2.jsonl'   # v2: ΟΛΑ τα ματς κοντα στην ωρα τζαμπολ, ταιριασμα ονοματων τοπικα (το v1 κρατουσε το πρωτο → λαθος ματς)
done = set()
if os.path.exists(OUT):
    for ln in open(OUT, encoding='utf-8'): done.add(json.loads(ln)['ng'])
left = None
with open(OUT, 'a', encoding='utf-8') as fo:
    for s in S:
        if s['ng'] in done: continue
        snap = dt.datetime.fromtimestamp(max(s['t_b'] - 60, s['t_a']), dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        r = requests.get('https://api.the-odds-api.com/v4/historical/sports/basketball_euroleague/odds',
                         params=dict(apiKey=KEY, regions='eu', markets='totals', oddsFormat='decimal', date=snap), timeout=40)
        left = r.headers.get('x-requests-remaining')
        if r.status_code != 200: print(snap, r.status_code, r.text[:120]); continue
        j = r.json()
        G = [g for g in (j.get('data') or []) if abs(dt.datetime.fromisoformat(g['commence_time'].replace('Z', '+00:00')).timestamp() - s['tip']) <= 1800]
        fo.write(json.dumps(dict(ng=s['ng'], req=snap, snap_ts=j.get('timestamp'), games=G), ensure_ascii=False) + '\n')
        print(s['home'], s['away'], snap, len(G), 'ματς κοντα', flush=True)
print('credits που μενουν:', left)
