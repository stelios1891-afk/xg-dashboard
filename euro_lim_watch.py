# -*- coding: utf-8 -*-
"""euro_lim_watch.py — ΟΡΙΑ PINNACLE ΣΤΑ ΕΥΡΩΠΑΪΚΑ (10/10/2026, Στελιος: «θελω να ερχονται ειδοποιησεις οπως και στα μπασκετικα»).
Ιδια λογικη με το el_pin_watch (μπασκετ, 7/10): «💰 ΟΡΙΟ PINNACLE ↑» στο INFO bot, ΜΟΝΟ για ματς με ανοιχτο κανονικο pick
(euro_picks_ledger.jsonl: no_play=False, χωρις αποτελεσμα, σεντρα στο μελλον). Τα ορια τα διαβαζει ηδη ο euro_odds_scan (Pinnacle guest API,
πεδιο lim: spreads / totals / h2h) → εδω ΚΑΜΙΑ νεα κληση, μονο συγκριση με την προηγουμενη σαρωση (state: euro_lim_state.json).
Τρεχει στον scanner (scanner_tick.sh) μετα το euro_picks_ledger.py. Ιστορικο ορων: ηδη στο euro_odds_hist.jsonl (lim σε καθε αλλαγη).
"""
import os, sys, json, datetime as dt
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
ROOT = os.path.dirname(os.path.abspath(__file__)); F = lambda n: os.path.join(ROOT, n)
COMP_LAB = {'ChampionsLeague': 'Champions League', 'EuropaLeague': 'Europa League', 'ConferenceLeague': 'Conference League'}
MK = (('spreads', 'χάντικαπ'), ('totals', 'γκολ'))


def _load(p, d):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return d


def _dt(s):
    try:
        d = dt.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except Exception:
        return None


_DAYS = ['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ']


def _athens(d):
    try:
        from zoneinfo import ZoneInfo
        a = d.astimezone(ZoneInfo('Europe/Athens'))
    except Exception:
        a = d + dt.timedelta(hours=3)
    return f"{_DAYS[a.weekday()]} {a.strftime('%d/%m %H:%M')}"


def open_picks(now):
    act = {}
    if not os.path.exists(F('euro_picks_ledger.jsonl')):
        return act
    for ln in open(F('euro_picks_ledger.jsonl'), encoding='utf-8'):
        try:
            r = json.loads(ln)
        except Exception:
            continue
        ko = _dt(r.get('ko'))
        if r.get('no_play') or r.get('pnl') is not None or ko is None or ko <= now:
            continue
        act.setdefault(str(r['mid']), []).append(r)
    return act


def pick_line(r, o):
    """το pick μας + η τωρινη τιμη της κυριας γραμμης."""
    if r.get('mkt') in ('OVER', 'UNDER'):
        side = 'Over' if r['mkt'] == 'OVER' else 'Under'
        now_ = f"τώρα {side} {o['tl']:g} @{o['to' if side == 'Over' else 'tu']}" if o.get('tl') is not None else ''
        return f"pick: {side} {r['line']:g} @{r['odds']:.2f}" + (f' ({now_})' if now_ else '')
    team = r['home'] if r['side'] == 1 else r['away']
    ln = 'DNB (0)' if r.get('role') == 'dnb' else f"{'+' if r['line'] >= 0 else ''}{r['line']:g}"
    now_ = ''
    if o.get('line') is not None:
        L = o['line'] if r['side'] == 1 else -o['line']
        now_ = f"τώρα {'0' if abs(L) < 1e-9 else (('+' if L > 0 else '') + f'{L:g}')} @{o['oh'] if r['side'] == 1 else o['oa']}"
    return f"pick: {team} {ln} @{r['odds']:.2f}" + (f' ({now_})' if now_ else '')


def main(notify_tg=True):
    now = dt.datetime.now(dt.timezone.utc)
    odds = _load(F('euro_odds_latest.json'), {}).get('odds', {})
    state = _load(F('euro_lim_state.json'), {})
    act = open_picks(now)
    msgs = []
    for mid, o in odds.items():
        lim = o.get('lim') or {}
        if not lim:
            continue
        prev = state.get(mid)
        if prev is not None and mid in act:
            ups = [f'{nm} {prev.get(k) or 0:g} → {lim.get(k):g}' for k, nm in MK
                   if lim.get(k) and (prev.get(k) or 0) > 0 and lim.get(k) > (prev.get(k) or 0)]
            if ups:
                r0 = act[mid][0]; ko = _dt(o.get('ko') or r0.get('ko'))
                hrs = (ko - now).total_seconds() / 3600 if ko else float('nan')
                msgs.append(f"💰 ΟΡΙΟ PINNACLE ↑ · {COMP_LAB.get(r0['comp'], r0['comp'])} · {r0['home']} - {r0['away']} "
                            f"({_athens(ko) if ko else '?'}, σε {hrs:.0f}ω)\n" + ' · '.join(ups) + '\n' +
                            '\n'.join(pick_line(r, o) for r in act[mid]))
        state[mid] = dict({k: lim.get(k) for k in ('spreads', 'totals', 'h2h')}, ko=o.get('ko'))
    state = {k: v for k, v in state.items() if (_dt(v.get('ko')) or now) > now - dt.timedelta(days=3)}
    json.dump(state, open(F('euro_lim_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'[Pinnacle ορια Ευρωπη] ματς με ορια {len(state)} · με ανοιχτο pick {len(act)} · μηνυματα {len(msgs)}')
    for s_ in msgs:
        print('  ' + s_.replace('\n', ' | '))
    if msgs and notify_tg and os.environ.get('TELEGRAM_TOKEN'):
        try:
            import notify
            notify.send('\n\n'.join(msgs), channel='info')
        except Exception as e:
            print('Telegram σφαλμα (μη κρισιμο):', e)


if __name__ == '__main__':
    main(notify_tg='--no-tg' not in sys.argv)
