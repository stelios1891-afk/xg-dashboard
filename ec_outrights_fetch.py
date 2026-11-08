# -*- coding: utf-8 -*-
"""ec_outrights_fetch.py — ΑΠΟΔΟΣΕΙΣ ΝΙΚΗΤΗ EuroCup πριν/νωρις στη σεζον απο το Wayback Machine (1/10/2026, Στελιος: «η αγορα outright
εχει λογικη πανω στα power rankings»). Oddsportal δεν κραταει παλιες σεζον (404)· Pinnacle δεν εχει outright EuroCup.
Στιγμιοτυπα (οσα βρεθηκαν):
  U2021 Oddschecker 27/10/2021 (ΜΕΤΑ ~4 αγωνιστικες) 20 ομαδες × 9 βιβλια
  U2023 Oddschecker 29/09/2023 (πριν την 1η) 1 βιβλιο, 12/19 ομαδες με τιμη
  U2024 Oddschecker 08/09/2024 (πριν) 1-3 βιβλια, 13/20
  U2025 bwin       16/09/2025 (πριν) 20/20
Εξοδος: ec_outrights.json {season: {date, src, after_round, odds: {ομαδα: μεση δεκαδικη αποδοση}}}"""
import re, json, time, requests
SN = [('U2021', '20211027082449', 'https://www.oddschecker.com/basketball/eurocup/uleb-eurocup/winner?selectionName=lokomotiv-kuban', 'oc', 5),
      ('U2023', '20230929044821', 'https://www.oddschecker.com/basketball/eurocup/winner', 'oc', 0),
      ('U2024', '20240908084452', 'https://www.oddschecker.com/basketball/eurocup/winner?selectionName=hapoel-tel-aviv', 'oc', 0),
      ('U2025', '20250916125155', 'https://www.bwin.com/en/sports/basketball-7/betting/europe-7/eurocup-men-7142', 'bwin', 0)]
res = {}
for sea, ts, u, kind, ar in SN:
    s = requests.get(f'https://web.archive.org/web/{ts}/{u}', headers={'User-Agent': 'Mozilla/5.0'}, timeout=60).text
    od = {}
    if kind == 'oc':
        for n, r in re.findall(r'<tr[^>]*data-bname="([^"]+)"[^>]*>(.*?)</tr>', s, re.S):
            v = [float(x) for x in re.findall(r'data-odig="([\d.]+)"', r) if float(x) > 0]
            if v: od[n] = round(sum(v) / len(v), 2)
    else:
        t = re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S); t = re.sub(r'<[^>]+>', ' ', t); t = re.sub(r'\s+', ' ', t)
        seg = t[t.find('League winner'):]; seg = seg[:seg.find('Show More')]
        for n, v in re.findall(r'([A-Za-z][A-Za-z\-\. ()]+?) (\d+\.\d\d)', seg): od.setdefault(n.strip().replace('League winner (including playoffs) ', ''), float(v))
    res[sea] = dict(date=f'{ts[:4]}-{ts[4:6]}-{ts[6:8]}', src=kind, after_round=ar, odds=od)
    print(sea, len(od), sorted(od.items(), key=lambda x: x[1])[:5]); time.sleep(2)
json.dump(res, open('ec_outrights.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
