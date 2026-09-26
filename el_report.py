# -*- coding: utf-8 -*-
"""el_report.py — ΕΒΔΟΜΑΔΙΑΙΑ ΑΝΑΦΟΡΑ picks Ευρωλιγκας (26/9/2026, αιτημα Στελιου) — «θερμομετρο» οπως το ποδοσφαιρο.
Πηγες: el_clv_bets.jsonl (καθε ΝΕΟ pick με την τιμη εισοδου· κραταμε την ΠΡΩΤΗ εισοδο ανα ματς/αγορα/πλευρα)
       el_projections.json (τελικα σκορ) · el_odds_hist.jsonl + el_closing_backfill.jsonl (closing Pinnacle = τελευταια τιμη πριν το τζαμπολ)
Ανα pick: αποτελεσμα (μοναδες στην τιμη εισοδου) · κινηση γραμμης ως το κλεισιμο (ποντοι, + = υπερ μας) · EV στο κλεισιμο
  (πιθανοτητα καλυψης της γραμμης μας με τον μεσο που βαζει η Pinnacle στο κλεισιμο, χωρις γκανιοτα × αποδοση εισοδου − 1).
Χρηση: python el_report.py report [μερες]  ·  python el_report.py weekly (Δευτερα, μια φορα → Telegram· απο scanner_tick)"""
import os, sys, json, math, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
STATE = F('el_report_last.txt')
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))

def _jl(p):
    try: return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]
    except FileNotFoundError: return []
def cover(mu, L, sig):
    if abs(L - round(L)) < 1e-9:
        pw = Phi((mu + L - 0.5) / sig); pl = Phi((-mu - L - 0.5) / sig); return pw, 1 - pw - pl
    return Phi((mu + L) / sig), 0.0
def implied_mu(L, oh, oa, sig):
    ph = (1 / oh) / ((1 / oh) + (1 / oa)); lo, hi = -L - 80.0, -L + 80.0     # γυρω απο τη γραμμη (και για συνολα ~170)
    for _ in range(60):
        mid = (lo + hi) / 2; pw, pp = cover(mid, L, sig); p = pw / (1 - pp) if pp < 1 else 0.5
        lo, hi = (mid, hi) if p < ph else (lo, mid)
    return (lo + hi) / 2

def settled():
    proj = json.load(open(F('el_projections.json'), encoding='utf-8'))
    games = {g['code']: g for g in proj['games']}
    sm, st = float(proj.get('sigma_margin', 11.5)), float(proj.get('sigma_total', 16.7))
    close = {}
    for r in _jl(F('el_odds_hist.jsonl')) + _jl(F('el_closing_backfill.jsonl')):
        if r.get('line') is None or r['t'] + ':00' >= r['commence'][:19]: continue
        if r['code'] not in close or r['t'] > close[r['code']]['t']: close[r['code']] = r
    first = {}
    for b in _jl(F('el_clv_bets.jsonl')):
        k = (b['code'], b['mkt'], b.get('bet', '').split(' ')[0] if b['mkt'] == 'total' else b['side'])
        if k not in first or b['seen'] < first[k]['seen']: first[k] = b
    out = []
    for b in first.values():
        g = games.get(b['code']); c = close.get(b['code'])
        rec = dict(b, settled=False)
        if g and g.get('played') and g.get('hs') is not None:
            m, t = g['hs'] - g['as_'], g['hs'] + g['as_']
            if b['mkt'] == 'hcap':
                v = (m if b['side'] == 1 else -m) + b['hcap']
            else:
                v = (t - b['hcap']) if b['bet'].startswith('Over') else (b['hcap'] - t)
            rec.update(settled=True, pnl=(b['odds'] - 1) if v > 0 else (0.0 if v == 0 else -1.0))
        if c:
            if b['mkt'] == 'hcap':
                Lc = c['line'] if b['side'] == 1 else -c['line']
                rec['move'] = b['hcap'] - Lc                                  # πηραμε +6, εκλεισε +4 → +2 υπερ μας
                mu = implied_mu(c['line'], c['oh'], c['oa'], sm)             # μεσος γηπ − φιλ της αγορας
                Lh = b['hcap'] if b['side'] == 1 else -b['hcap']
                pw, pp = cover(mu, Lh, sm); p = pw if b['side'] == 1 else 1 - pw - pp
            else:
                over = b['bet'].startswith('Over')
                rec['move'] = (c['tl'] - b['hcap']) if over else (b['hcap'] - c['tl'])
                mu = implied_mu(-c['tl'], c['to'], c['tu'], st)              # μεσο συνολο της αγορας
                po, pp = cover(mu, -b['hcap'], st); p = po if over else 1 - po - pp
            rec['ev_close'] = p * b['odds'] + pp - 1
        out.append(rec)
    return out

def summarize(rows, title):
    s = [r for r in rows if r['settled']]
    if not s: return f'{title}: κανενα pick με αποτελεσμα'
    w = sum(r['pnl'] > 0 for r in s); l = sum(r['pnl'] < 0 for r in s); p = sum(r['pnl'] == 0 for r in s)
    u = sum(r['pnl'] for r in s); mv = [r['move'] for r in s if 'move' in r]; ev = [r['ev_close'] for r in s if 'ev_close' in r]
    by = []
    for mk, nm in (('hcap', 'χαντικαπ'), ('total', 'συνολα')):
        x = [r for r in s if r['mkt'] == mk]
        if x: by.append(f'{nm} {len(x)}: {sum(r["pnl"] for r in x):+.2f}u')
    txt = (f'{title}: {len(s)} picks · {w}-{l}' + (f'-{p}' if p else '') + f' · {u:+.2f} μον. · ROI {u / len(s) * 100:+.1f}%\n'
           f'   ({" · ".join(by)})')
    if mv: txt += f'\n   κινηση γραμμης ως το κλεισιμο: {sum(mv) / len(mv):+.2f} π. μ.ο. · υπερ μας {sum(x > 0 for x in mv)}/{len(mv)}'
    if ev: txt += f' · EV στο κλεισιμο {sum(ev) / len(ev) * 100:+.1f}%'
    return txt

def report(days=7):
    rows = settled(); now = dt.datetime.now(dt.timezone.utc)
    cut = (now - dt.timedelta(days=days)).strftime('%Y-%m-%dT%H:%M')
    week = [r for r in rows if r['when'] >= cut]
    lines = ['🏀 EUROLEAGUE — εβδομαδιαια αναφορα picks', summarize(week, f'τελευταιες {days} μερες'), summarize(rows, 'σεζον ως τωρα')]
    det = [r for r in week if r['settled']]
    if det:
        lines.append('\nαναλυτικα:')
        for r in sorted(det, key=lambda r: r['when']):
            bet = r.get('bet') or f"{r['home'] if r['side'] == 1 else r['away']} {r['hcap']:+g}"
            lines.append(f"  αγ.{r['round']} {r['home'][:14]}-{r['away'][:14]}: {bet} @{r['odds']:.2f} → {r['pnl']:+.2f}"
                         + (f" · γραμμη {r['move']:+.1f}" if 'move' in r else ''))
    pend = [r for r in rows if not r['settled']]
    if pend: lines.append(f'\nεκκρεμη (δεν εχουν παιχτει): {len(pend)}')
    lines.append('(σημ.: η γραμμη ιστορικα ΔΕΝ κινειται υπερ μας — το κερδος ερχεται απο τα αποτελεσματα· EV στο κλεισιμο ≈ −4% ειναι το «αναμενομενο»)')
    return '\n'.join(lines)

def weekly(notify_tg=True):
    now = dt.datetime.now(dt.timezone.utc)
    last = open(STATE, encoding='utf-8').read().strip() if os.path.exists(STATE) else ''
    if now.weekday() != 0 or last == now.strftime('%Y-%m-%d'):
        return
    msg = report(7)
    if notify_tg and 'κανενα pick' not in msg.split('\n')[1]:
        try:
            import notify; notify.send(msg)
        except Exception as e:
            print('Telegram σφαλμα:', e)
    open(STATE, 'w', encoding='utf-8').write(now.strftime('%Y-%m-%d'))
    print(msg)

if __name__ == '__main__':
    if 'weekly' in sys.argv:
        weekly(notify_tg='--no-tg' not in sys.argv)
    else:
        d = int(sys.argv[sys.argv.index('report') + 1]) if 'report' in sys.argv and len(sys.argv) > sys.argv.index('report') + 1 else 7
        print(report(d))
