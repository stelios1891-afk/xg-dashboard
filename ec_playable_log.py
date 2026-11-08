# -*- coding: utf-8 -*-
"""ec_playable_log.py — EuroCup: ΗΤΑΝ ΤΟ PICK ΑΚΟΜΑ ΕΝΕΡΓΟ ΤΗ ΣΤΙΓΜΗ ΠΟΥ ΜΠΟΡΩ ΝΑ ΠΑΙΞΩ; (13/10/2026, Στελιος: «τα ορια ειναι πολυ κακα — το 500 της
Pinnacle ειναι 250 σε μενα· περιμενω να ανοιξει 2ος/3ος μπουκ, οριακα παιζω 1 ωρα πριν»). ΚΑΤΑΓΡΑΦΗ μονο — δεν αλλαζει picks/Telegram.
Καθε τικ του scanner (μετα το ec_picks + el_pin_watch EC): για καθε pick του ημερολογιου (ec_clv_bets, πρωτη εγγραφη ανα ματς/πλευρα, οχι paper)
με σεντρα στο μελλον, οταν περασει καθε «σημειο» γραφει ΜΙΑ φορα στο ec_playable.jsonl αν ηταν ακομα pick (ec_value_latest) + τρεχουσα γραμμη/τιμη Pinnacle:
  lim500 = πρωτη φορα που το οριο Pinnacle της αγορας ≥500 · h2 = 2ω πριν · h1 = 1ω πριν · h05 = 30′ πριν.
--backfill: τα παλια picks απο το git ιστορικο του ec_value_latest.json (χωρις τιμες). --report: πινακας αποτελεσματων ανα σημειο.
Χρηση: python ec_playable_log.py [--backfill | --report]"""
import os, sys, json, datetime as dt, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
OUT = F('ec_playable.jsonl')
CPS = (('lim500', None), ('h2', 2.0), ('h1', 1.0), ('h05', 0.5))
LAB = {'lim500': 'όριο Pinnacle 500', 'h2': '2ω πριν', 'h1': '1ω πριν', 'h05': '30′ πριν'}

def U(s):
    s = str(s).replace('Z', '+00:00')
    t = dt.datetime.fromisoformat(s)
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)

def _dir(mkt, side, bet):
    return str(side) if mkt == 'hcap' else str(bet or '').split(' ')[0]

def _jsonl(p):
    try:
        return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]
    except Exception:
        return []

def ledger_picks():
    """{(code, mkt, dir): πρωτη μη-paper εγγραφη}"""
    first = {}
    for b in _jsonl(F('ec_clv_bets.jsonl')):
        if b.get('paper'):
            continue
        k = (str(b['code']), b['mkt'], _dir(b['mkt'], b.get('side'), b.get('bet')))
        if k not in first or b['seen'] < first[k]['seen']:
            first[k] = b
    return first

def done_set():
    return {(r['code'], r['mkt'], r['dir'], r['cp']) for r in _jsonl(OUT)}

def lim500_times():
    """{code: {'hcap'|'total': πρωτη στιγμη με οριο ≥500}} απο το ec_pin_hist."""
    out = collections.defaultdict(dict)
    for r in sorted(_jsonl(F('ec_pin_hist.jsonl')), key=lambda r: r['t']):
        c = str(r.get('code'))
        for k, mk in (('sp', 'hcap'), ('tot', 'total')):
            if (r.get(k) or {}).get('lim', 0) >= 500 and mk not in out[c]:
                out[c][mk] = r['t']
    return out

def tick():
    now = dt.datetime.now(dt.timezone.utc)
    try:
        latest = json.load(open(F('ec_value_latest.json'), encoding='utf-8'))
    except Exception:
        return
    active = {(str(p['code']), p['mkt'], _dir(p['mkt'], p.get('side'), p.get('bet'))) for p in latest.get('picks', [])}
    odds = (json.load(open(F('ec_odds_latest.json'), encoding='utf-8')) if os.path.exists(F('ec_odds_latest.json')) else {}).get('odds', {})
    l5 = lim500_times(); done = done_set(); new = []
    for k, b in ledger_picks().items():
        tip = U(b['when'])
        if tip <= now - dt.timedelta(minutes=5):
            continue
        pin = (odds.get(k[0]) or {}).get('pin') or {}
        for cp, h in CPS:
            if (k + (cp,)) in done:
                continue
            reached = (k[1] in l5.get(k[0], {})) if h is None else (now >= tip - dt.timedelta(hours=h))
            if not reached:
                continue
            if k[1] == 'hcap':
                ln = pin.get('line'); od = pin.get('oh') if k[2] == '1' else pin.get('oa')
                ln = (ln if k[2] == '1' else (-ln if ln is not None else None))
            else:
                ln = pin.get('tl'); od = pin.get('to') if k[2] == 'Over' else pin.get('tu')
            new.append(dict(code=k[0], mkt=k[1], dir=k[2], cp=cp, at=now.isoformat(timespec='minutes'), when=b['when'], home=b['home'], away=b['away'],
                            pick_line=b['hcap'], pick_odds=b['odds'], active=k in active, line=ln, odds=od, src='live'))
    if new:
        with open(OUT, 'a', encoding='utf-8') as fh:
            for r in new:
                fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'[EuroCup «παιζεται;»] νεες εγγραφες {len(new)}')

def backfill():
    import subprocess
    log = subprocess.run(['git', 'log', '--format=%H %cI', '--', 'ec_value_latest.json'], capture_output=True, text=True, cwd=ROOT).stdout.split('\n')
    snaps = []
    for ln in log:
        if not ln.strip():
            continue
        h, t = ln.split()
        raw = subprocess.run(['git', 'show', f'{h}:ec_value_latest.json'], capture_output=True, cwd=ROOT).stdout
        try:
            d = json.loads(raw.decode('utf-8'))
        except Exception:
            continue
        snaps.append((U(t), {(str(p['code']), p['mkt'], _dir(p['mkt'], p.get('side'), p.get('bet'))) for p in d.get('picks', [])}))
    snaps.sort()
    l5 = lim500_times(); done = done_set(); new = []; now = dt.datetime.now(dt.timezone.utc)
    def act(k, t):
        prev = [a for ts, a in snaps if ts <= t]
        return None if not prev else (k in prev[-1])
    for k, b in ledger_picks().items():
        tip = U(b['when'])
        for cp, h in CPS:
            if (k + (cp,)) in done:
                continue
            t = U(l5[k[0]][k[1]]) if (h is None and k[1] in l5.get(k[0], {})) else (tip - dt.timedelta(hours=h) if h is not None else None)
            if t is None or t > now or t < snaps[0][0]:
                continue
            a = act(k, t)
            if a is None:
                continue
            new.append(dict(code=k[0], mkt=k[1], dir=k[2], cp=cp, at=t.isoformat(timespec='minutes'), when=b['when'], home=b['home'], away=b['away'],
                            pick_line=b['hcap'], pick_odds=b['odds'], active=a, line=None, odds=None, src='backfill'))
    with open(OUT, 'a', encoding='utf-8') as fh:
        for r in new:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'backfill: {len(new)} εγγραφες')

def report():
    res = {}
    try:
        for g in json.load(open(F('ec_projections.json'), encoding='utf-8')).get('games', []):
            if g.get('hs') is not None:
                res[str(g['code'])] = (int(g['hs']), int(g['as_']))
    except Exception:
        pass
    def settle(r, use_now):
        if r['code'] not in res:
            return None
        hs, as_ = res[r['code']]
        L = r['line'] if (use_now and r.get('line') is not None) else r['pick_line']
        o = r['odds'] if (use_now and r.get('odds')) else r['pick_odds']
        if r['mkt'] == 'hcap':
            x = ((hs - as_) if r['dir'] == '1' else (as_ - hs)) + float(L)
        else:
            x = (hs + as_ - float(L)) * (1 if r['dir'] == 'Over' else -1)
        return (float(o) - 1) if x > 0 else (0.0 if x == 0 else -1.0)
    R = _jsonl(OUT); first = ledger_picks()
    print('EuroCup · ήταν ακόμα pick τη στιγμή που μπορώ να παίξω; (αποτέλεσμα στην τιμή του pick)')
    allp = [settle(dict(code=k[0], mkt=k[1], dir=k[2], pick_line=b['hcap'], pick_odds=b['odds']), False) for k, b in first.items()]
    allp = [x for x in allp if x is not None]
    print(f'  όλα τα picks (στην πρώτη τιμή): {len(allp)} · {sum(allp):+.2f} μον.' if allp else '  —')
    for cp, _ in CPS:
        rows = [r for r in R if r['cp'] == cp]
        for a in (True, False):
            s = [settle(r, False) for r in rows if r['active'] is a]
            s = [x for x in s if x is not None]
            print(f"  {LAB[cp]:18s} {'ΕΝΕΡΓΑ' if a else 'ΕΠΕΣΑΝ'}: {len([r for r in rows if r['active'] is a]):3d} picks · κρίθηκαν {len(s):3d} · {sum(s):+6.2f} μον." + (f' ({100*sum(s)/len(s):+.0f}%)' if s else ''))

if __name__ == '__main__':
    if '--backfill' in sys.argv:
        backfill()
    elif '--report' in sys.argv:
        report()
    else:
        tick()
