# -*- coding: utf-8 -*-
"""oddsportal_ci_probe.py — ΕΦΑΠΑΞ (1/10/2026): Oddsportal outrights EuroCup απο GitHub με headless browser (απο Ελλαδα μπλοκαρει).
Β' δοκιμη: Playwright → κειμενο σελιδας (ομαδα + αποδοση) και tooltip ανοιγματος (hover) για ιστορικες σεζον."""
import os, time
from playwright.sync_api import sync_playwright
os.makedirs('op_probe', exist_ok=True)
out = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36', locale='en-US')
    for sea in ['-2024-2025', '-2023-2024', '-2022-2023', '-2021-2022', '-2019-2020', '-2018-2019', '-2017-2018']:
        u = f'https://www.oddsportal.com/basketball/europe/eurocup{sea}/outrights/'
        try:
            pg.goto(u, wait_until='networkidle', timeout=60000); time.sleep(4)
            try: pg.click('#onetrust-reject-all-handler', timeout=3000)
            except Exception: pass
            txt = pg.inner_text('body')
            open(f'op_probe/text{sea}.txt', 'w', encoding='utf-8').write(txt)
            out.append(f'{u} → {len(txt)} chars')
            # hover πρωτη αποδοση → tooltip ανοιγματος
            try:
                cells = pg.locator('[data-testid*="odd"], .odds-cell, p.height-content').all()
                out.append(f'   odds-like cells: {len(cells)}')
                if cells:
                    cells[0].hover(); time.sleep(2)
                    tip = pg.inner_text('body')
                    i = tip.find('Opening')
                    out.append('   hover: ' + (tip[max(0, i - 300):i + 300].replace('\n', ' | ') if i >= 0 else 'no "Opening" text'))
            except Exception as e:
                out.append(f'   hover ERR {e}')
            pg.screenshot(path=f'op_probe/shot{sea}.png', full_page=False)
        except Exception as e:
            out.append(f'{u} → ERR {e}')
        time.sleep(5)
    b.close()
open('op_probe/out2.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
