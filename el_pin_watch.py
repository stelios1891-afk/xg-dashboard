# -*- coding: utf-8 -*-
"""el_pin_watch.py — PINNACLE: ΑΝΟΙΓΜΑ ΓΡΑΜΜΩΝ & ΟΡΙΑ ΠΟΝΤΑΡΙΣΜΑΤΟΣ Ευρωλιγκας (1/10/2026, Στελιος: «εχασα Εφες & Ρεαλ περιμενοντας να
ανοιξουν τα ορια — θελω alert οταν ανοιγει η Pinnacle και οταν ανεβαινουν τα ορια»).
Πηγη: δημοσια υπηρεσια της Pinnacle (guest.api.arcadia.pinnacle.com, χωρις λογαριασμο/κλειδι, 0 credits) — league 382 = Euroleague.
  Δουλευει και απο GitHub Actions (pinnacle_ci_probe 30/9). Οριο = maxRiskStake (μεγιστο ρισκο· νομισμα ΑΓΝΩΣΤΟ — δεν το γραφει η υπηρεσια).
Καθε σαρωση (scanner_tick, ~15′), για τα ματς των επομενων 48 ωρων, ΚΥΡΙΕΣ αγορες (χαντικαπ, συνολο, νικητης):
  • ΠΡΩΤΗ εμφανιση ματς στην Pinnacle → Telegram «🟢 ανοιξε η Pinnacle» (γραμμες, τιμες, ορια, edge μοντελου στην κυρια γραμμη)
  • ΑΥΞΗΣΗ οριου χαντικαπ/συνολου → Telegram «💰 οριο ↑» (με τωρινη γραμμη/τιμη & edge)
  • ΙΣΤΟΡΙΚΟ: καθε αλλαγη (γραμμη, τιμη, οριο) → el_pin_hist.jsonl — για να μαθουμε το μοτιβο (ποσο αργοτερα ανεβαινουν τα ορια).
Telegram: info bot (οχι picks bot — κανονας 26/9). State: el_pin_state.json."""
import os, sys, json, math, datetime as dt
import requests
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__)); F = lambda n: os.path.join(ROOT, n)
B = 'https://guest.api.arcadia.pinnacle.com/0.1'; LEAGUE = 382
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Accept': 'application/json',
     'Referer': 'https://www.pinnacle.com/', 'Origin': 'https://www.pinnacle.com'}
WINDOW_H = 48
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
def dec(a): return round(1 + (a / 100 if a > 0 else 100 / -a), 3) if a else None
def _load(p, d):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return d
def short(n):
    w = [x for x in (n or '').split() if x.upper() not in ('BC', 'KK', 'FC', 'SK', 'BK', 'JK', 'AS', 'CB')]
    return w[0] if w else (n or '')
def tok(s): return ''.join(c for c in (s or '').lower() if c.isalpha())
def cover(mu, L, sig):
    if abs(L - round(L)) < 1e-9:
        pw = Phi((mu + L - 0.5) / sig); pl = Phi((-mu - L - 0.5) / sig); return pw, 1 - pw - pl
    return Phi((mu + L) / sig), 0.0
def main(notify_tg=True):
    now = dt.datetime.now(dt.timezone.utc)
    try:
        M = requests.get(f'{B}/leagues/{LEAGUE}/matchups', headers=H, timeout=30).json()
        MK = requests.get(f'{B}/leagues/{LEAGUE}/markets/straight', headers=H, timeout=30).json()
    except Exception as e:
        print('Pinnacle: σφαλμα', e); return
    proj = _load(F('el_projections.json'), {}); sm, st = float(proj.get('sigma_margin', 11.5)), float(proj.get('sigma_total', 16.7))
    games = [g for g in proj.get('games', []) if not g.get('played')]
    def find(home, away, start):
        th, ta = tok(home), tok(away)
        for g in games:
            try: t0 = dt.datetime.fromisoformat(g['utc'].replace('Z', '+00:00'))
            except Exception: continue
            if abs((t0 - start).total_seconds()) > 6 * 3600: continue
            gh, ga = tok(g['home']), tok(g['away'])
            if (th[:5] in gh or gh[:5] in th) and (ta[:5] in ga or ga[:5] in ta): return g
        return None
    state = _load(F('el_pin_state.json'), {}); msgs = []; hist = []
    for m in M:
        ps = m.get('participants') or []
        if len(ps) != 2 or m.get('parentId'): continue
        start = dt.datetime.fromisoformat(m['startTime'].replace('Z', '+00:00'))
        hrs = (start - now).total_seconds() / 3600
        if not (0 < hrs <= WINDOW_H): continue
        home = next((p['name'] for p in ps if p.get('alignment') == 'home'), ps[0]['name'])
        away = next((p['name'] for p in ps if p.get('alignment') == 'away'), ps[1]['name'])
        cur = {}
        for x in MK:
            if x.get('matchupId') != m['id'] or x.get('period') != 0 or x.get('isAlternate') or x.get('type') not in ('spread', 'total', 'moneyline'): continue
            pr = {p.get('designation'): p for p in x.get('prices', [])}
            lim = max([l.get('amount', 0) for l in x.get('limits', [])] or [0])
            if x['type'] == 'spread' and 'home' in pr:
                cur['sp'] = dict(line=pr['home'].get('points'), oh=dec(pr['home'].get('price')), oa=dec((pr.get('away') or {}).get('price')), lim=lim)
            elif x['type'] == 'total' and 'over' in pr:
                cur['tot'] = dict(line=pr['over'].get('points'), oo=dec(pr['over'].get('price')), ou=dec((pr.get('under') or {}).get('price')), lim=lim)
            elif x['type'] == 'moneyline' and 'home' in pr:
                cur['ml'] = dict(oh=dec(pr['home'].get('price')), oa=dec((pr.get('away') or {}).get('price')), lim=lim)
        if not cur: continue
        k = str(m['id']); prev = state.get(k)
        g = find(home, away, start)
        try:
            from zoneinfo import ZoneInfo; tip = start.astimezone(ZoneInfo('Europe/Athens')).strftime('%a %d/%m %H:%M')
        except Exception:
            tip = start.astimezone(dt.timezone(dt.timedelta(hours=3))).strftime('%a %d/%m %H:%M')
        def edges():
            if not g: return ''
            out_ = []
            if cur.get('sp') and cur['sp']['line'] is not None and cur['sp']['oh']:
                L = float(cur['sp']['line']); pw, pp = cover(float(g['margin']), L, sm); pl = 1 - pw - pp
                eh, ea = pw * cur['sp']['oh'] + pp - 1, pl * cur['sp']['oa'] + pp - 1
                out_.append(f"μοντελο γηπ {float(g['margin']):+.1f} → edge {short(home)} {L:+g}: {eh*100:+.0f}% · {short(away)} {-L:+g}: {ea*100:+.0f}%")
            if cur.get('tot') and cur['tot']['line'] is not None and cur['tot']['oo']:
                T = float(cur['tot']['line']); po, pq = cover(float(g['total']), -T, st); pu = 1 - po - pq
                out_.append(f"συνολο μοντ. {float(g['total']):.1f} → Over {T:g}: {(po * cur['tot']['oo'] + pq - 1)*100:+.0f}% · Under: {(pu * cur['tot']['ou'] + pq - 1)*100:+.0f}%")
            return '\n'.join(out_)
        def desc():
            s_ = []
            if cur.get('sp'): s_.append(f"χαντικαπ {short(home)} {cur['sp']['line']:+g} @{cur['sp']['oh']} / {cur['sp']['oa']} · οριο {cur['sp']['lim']:g}")
            if cur.get('tot'): s_.append(f"συνολο {cur['tot']['line']:g} @{cur['tot']['oo']} / {cur['tot']['ou']} · οριο {cur['tot']['lim']:g}")
            if cur.get('ml'): s_.append(f"νικητης @{cur['ml']['oh']} / {cur['ml']['oa']} · οριο {cur['ml']['lim']:g}")
            return '\n'.join(s_)
        if prev is None:
            msgs.append(f"🟢 ΑΝΟΙΞΕ Η PINNACLE · {home} - {away} ({tip}, σε {hrs:.0f}ω)\n{desc()}" + (f"\n{edges()}" if edges() else ''))
        else:
            ups = []
            for mk_, nm in (('sp', 'χαντικαπ'), ('tot', 'συνολο')):
                a, b = (prev.get(mk_) or {}).get('lim', 0), (cur.get(mk_) or {}).get('lim', 0)
                if b > a: ups.append(f'{nm} {a:g} → {b:g}')
            if ups:
                msgs.append(f"💰 ΟΡΙΟ PINNACLE ↑ · {home} - {away} ({tip}, σε {hrs:.1f}ω)\n{' · '.join(ups)}\n{desc()}" + (f"\n{edges()}" if edges() else ''))
        if prev is None or any((prev.get(x) or {}) != (cur.get(x) or {}) for x in ('sp', 'tot', 'ml')):
            hist.append(dict(t=now.isoformat(timespec='minutes'), id=m['id'], home=home, away=away, start=m['startTime'], hrs=round(hrs, 2), code=(g or {}).get('code'), **cur))
        state[k] = dict(cur, home=home, away=away, start=m['startTime'], first_seen=(prev or {}).get('first_seen', now.isoformat(timespec='minutes')))
    state = {k: v for k, v in state.items() if dt.datetime.fromisoformat(v['start'].replace('Z', '+00:00')) > now - dt.timedelta(days=3)}
    json.dump(state, open(F('el_pin_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if hist:
        with open(F('el_pin_hist.jsonl'), 'a', encoding='utf-8') as fh:
            for r in hist: fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'[Pinnacle ορια] ματς ≤{WINDOW_H}ω: {sum(1 for v in state.values())} · αλλαγες {len(hist)} · μηνυματα {len(msgs)}')
    for s_ in msgs: print('  ' + s_.replace('\n', ' | '))
    if msgs and notify_tg:
        try:
            import notify; notify.send('\n\n'.join(msgs), channel='info')
        except Exception as e:
            print('Telegram σφαλμα:', e)
if __name__ == '__main__':
    main(notify_tg='--no-tg' not in sys.argv)
