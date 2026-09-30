# -*- coding: utf-8 -*-
"""oddsportal_ci_probe.py — ΕΦΑΠΑΞ (1/10/2026): απαντα το Oddsportal (outrights EuroCup, παλιες σεζον) απο GitHub; (απο Ελλαδα μπλοκαρει)
Αποθηκευει κατασταση + δειγμα HTML για να δουμε αν υπαρχουν αποδοσεις/ιστορικο ανοιγματος."""
import requests, re, os, time
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
     'Accept-Language': 'en-US,en;q=0.9'}
os.makedirs('op_probe', exist_ok=True)
out = []
S = requests.Session()
for sea in ['', '-2025-2026', '-2024-2025', '-2023-2024', '-2022-2023', '-2021-2022', '-2018-2019']:
    u = f'https://www.oddsportal.com/basketball/europe/eurocup{sea}/outrights/'
    try:
        r = S.get(u, headers=H, timeout=30)
        t = r.text
        feeds = sorted(set(re.findall(r'(/(?:feed|ajax)[^"\'\s<>]{5,120})', t)))[:15]
        out.append(f'{u} → {r.status_code} · {len(t)} bytes · final {r.url}')
        out.append('   feeds: ' + ' | '.join(feeds))
        open(f'op_probe/page{sea or "-cur"}.html', 'w', encoding='utf-8').write(t)
    except Exception as e:
        out.append(f'{u} → ERR {e}')
    time.sleep(2)
open('op_probe/out.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
