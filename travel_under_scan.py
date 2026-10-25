# -*- coding: utf-8 -*-
"""travel_under_scan.py — 25/10/2026 (Στελιος: «υπαρχει παρομοιο μπετ;» με το under Ντορτμουντ–Αϊντραχτ → «φτιαξτο ναι και δες αν εχουμε καταγραφη»).
ΕΥΡΗΜΑ (travel_fatigue_full / travel_seq4 / travel_deep2, 16-18/10): μετα απο ΜΑΚΡΙΝΟ εκτος ευρωπαικο ταξιδι, στο ΕΠΟΜΕΝΟ ματς πρωταθληματος
μπαινουν λιγοτερα γκολ απο οσα περιμενει η αγορα (εντος 2.500-3.500 χλμ: −0.40, under κλεισ. +12.3% σε 34)· κοντρα στο χαντικαπ ΔΕΝ δουλευει·
στις «μεγαλες» ομαδες (υπεροχη ≥1.2) το under εχανε. ΤΑΣΗ, ΟΧΙ ΚΑΝΟΝΑΣ (10-120 bets ανα κελι) → ΠΛΗΡΟΦΟΡΙΑ + ΚΑΤΑΓΡΑΦΗ, κανενα pick.
Βρισκει επερχομενα ματς CORE7 (≤9 μερες) οπου μια ομαδα ερχεται απο ΕΚΤΟΣ ευρωπαικο (≤6 μερες πριν), αποσταση εδρα → γηπεδο ≥1.500 χλμ.
Μοτιβο 1 = οχι Ευρωπη ≤7 μερες μετα · μοτιβο 2 = Ευρωπη ξανα ≤5 μερες μετα. Κατηγορια απο την υπεροχη της αγορας (κυρια γραμμη Pinnacle):
μεγαλη ≥1.2 · δυνατη 0.6-1.2 · γηινη <0.6. Γραμμη συνολων = κυρια (τιμες πιο κοντα στο ισο), απο dom_odds_latest.json (scanner).
Χρηση:  python travel_under_scan.py          → λιστα στην οθονη
        python travel_under_scan.py --tick   → (scanner, καθε περασμα) ΚΑΤΑΓΡΑΦΗ travel_under_log.json: πρωτη τιμη under, τελευταια πριν τη
            σεντρα (≈ κλεισιμο), αποτελεσμα · και ΜΙΑ ΦΟΡΑ ανα ευρωπαικη εβδομαδα (12ω μετα το τελευταιο ευρωπαικο) λιστα στο info bot."""
import os, sys, json, datetime as dt
import fatigue_flags as FF

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_F = os.path.join(ROOT, 'travel_under_log.json')
ST_F = os.path.join(ROOT, 'travel_under_state.json')
UTC = dt.timezone.utc
MIN_KM = 1500
# ιστορικο ανα κελι (travel_fatigue_full (Β), CORE7 2022-26, επομενο ματς ≤6 μερες): (γκολ vs αγορα, under στο κλεισιμο, bets)
HIST = {('εντος', 1500): (+0.04, -1.7, 119), ('εντος', 2500): (-0.40, +12.3, 34), ('εντος', 3500): (-0.47, +11.4, 8),
        ('εκτος', 1500): (-0.15, +14.6, 111), ('εκτος', 2500): (-0.18, +13.6, 26), ('εκτος', 3500): (+0.33, -63.5, 4)}


def _bucket(km):
    return 3500 if km >= 3500 else (2500 if km >= 2500 else 1500)


def _main_line(ladder):
    return min(ladder, key=lambda r: abs(r[1] - r[2])) if ladder else None


def _gr(t):
    try:
        from zoneinfo import ZoneInfo
        t = t.astimezone(ZoneInfo('Europe/Athens'))
    except Exception:
        t = t + dt.timedelta(hours=2)
    return ['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ'][t.weekday()] + t.strftime(' %d/%m %H:%M')


def collect(now=None, horizon_days=9):
    now = now or dt.datetime.now(UTC)
    L = FF._locs()
    EU = {}
    for k, Ls in FF._load('europe_fixtures_2627.json', {}).items():
        for m in Ls:
            t = FF._utc(m.get('utc'))
            if t:
                EU[(t.date().isoformat(), int(m['hid']), int(m['aid']))] = (t, k.split('_')[0], m)
    def euro_games(tid):
        return sorted([v for (d, h, a), v in EU.items() if h == tid or a == tid], key=lambda x: x[0])
    ODDS = FF._load('dom_odds_latest.json', {}).get('odds', {})
    rows = []
    for fid, m in FF._load('match_projections_archive.json', {}).items():
        ko = FF._utc(m.get('utc'))
        if not ko or ko > now + dt.timedelta(days=horizon_days) or ko < now - dt.timedelta(days=10):
            continue
        for side, tid in (('εντος', m['home_id']), ('εκτος', m['away_id'])):
            tid = int(tid)
            prev = [g for g in euro_games(tid) if g[0] < ko and (ko - g[0]).total_seconds() / 86400 <= 6]
            if not prev:
                continue
            t_eu, comp, em = prev[-1]
            if int(em['hid']) == tid:
                continue
            home, ven = L.get(tid), L.get(int(em['hid']))
            if not home or not ven:
                continue
            km = FF._km(home, ven)
            if km < MIN_KM or not (-10 <= home[1] <= 25 and 36 <= home[0] <= 62):
                continue
            nxt = [g for g in euro_games(tid) if g[0] > ko]
            gap = (nxt[0][0] - ko).total_seconds() / 86400 if nxt else 99
            od = ODDS.get(f"{m['home_id']}_{m['away_id']}") or {}
            ah, ou = _main_line(od.get('ah')), _main_line(od.get('ou'))
            sup = None if not ah else (-ah[0] if side == 'εντος' else ah[0])
            rows.append(dict(key=f"{fid}|{tid}", fid=str(fid), lg=m.get('league'), ko=ko, home=m['home'], away=m['away'],
                             team=m['home'] if side == 'εντος' else m['away'], side=side, eu_comp=comp, eu_at=em.get('hname'),
                             eu_t=t_eu, km=round(km), rest=round((ko - t_eu).total_seconds() / 86400, 1),
                             patt=2 if gap <= 5 else (1 if gap > 7 else 0), sup=sup,
                             cat=None if sup is None else ('μεγαλη' if sup >= 1.2 else ('δυνατη' if sup >= 0.6 else 'γηινη')),
                             ou=ou, T_model=round((m.get('home_adj_xg') or 0) + (m.get('away_adj_xg') or 0), 2), score=m.get('score')))
    rows.sort(key=lambda r: (r['ko'], -r['km']))
    return rows


def _settle_under(tg, L, o):
    parts = [L] if (L * 4) % 2 == 0 else [L - 0.25, L + 0.25]
    r = 0.0
    for x in parts:
        r += ((o - 1) if tg < x - 0.01 else (-1.0 if tg > x + 0.01 else 0.0)) / len(parts)
    return round(r, 3)


def _line_txt(r):
    h = HIST[(r['side'], _bucket(r['km']))]
    ou = f"under {r['ou'][0]} @{r['ou'][2]}" if r['ou'] else 'συνολα: δεν ανοιξαν ακομα'
    km = f"{r['km']:,}".replace(',', '.')
    return (f"{'★' if r['km'] >= 2500 else '•'} {_gr(r['ko'])} {r['home']} – {r['away']}\n"
            f"   {r['team']} ({r['side']}) απο {r['eu_at']} · {km} χλμ · ξεκ. {r['rest']}μ"
            f"{' · μοτιβο 2 (Ευρωπη ξανα ≤5μ)' if r['patt'] == 2 else ''} · {r['cat'] or '—'}\n"
            f"   {ou} · μοντελο {r['T_model']} · ιστορικο κελιου: {h[0]:+.2f} γκολ, under {h[1]:+.1f}% ({h[2]} bets)"
            + (' ⚠ μεγαλη: εκει το under εχανε' if r['cat'] == 'μεγαλη' else ''))


def tick():
    now = dt.datetime.now(UTC)
    rows = collect(now)
    log = FF._load('travel_under_log.json', {})
    st = FF._load('travel_under_state.json', {})
    changed = False
    for r in rows:
        e = log.get(r['key'])
        if e is None and r['ko'] > now and r['ou']:
            e = log[r['key']] = dict(seen=now.isoformat()[:16], lg=r['lg'], ko=r['ko'].isoformat()[:16], home=r['home'], away=r['away'],
                                    team=r['team'], side=r['side'], eu=f"{r['eu_comp']} @{r['eu_at']}", km=r['km'], rest=r['rest'],
                                    patt=r['patt'], cat=r['cat'], sup=r['sup'], T_model=r['T_model'],
                                    first=dict(t=now.isoformat()[:16], line=r['ou'][0], over=r['ou'][1], under=r['ou'][2]))
            changed = True
        if e is None:
            continue
        if r['ko'] > now and r['ou']:
            last = dict(t=now.isoformat()[:16], line=r['ou'][0], over=r['ou'][1], under=r['ou'][2])
            if e.get('last', {}).get('line') != last['line'] or e.get('last', {}).get('under') != last['under']:
                e['last'] = last; changed = True
        if r['score'] and 'tg' not in e:
            try:
                a, b = [int(x) for x in str(r['score']).replace(' ', '').split('-')]
                e['score'] = f'{a}-{b}'; e['tg'] = a + b
                e['pnl_first'] = _settle_under(a + b, e['first']['line'], e['first']['under'])
                lst = e.get('last') or e['first']
                e['pnl_close'] = _settle_under(a + b, lst['line'], lst['under'])
                changed = True
            except Exception:
                pass
    if changed:
        json.dump(log, open(LOG_F, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    # ΜΙΑ λιστα ανα ευρωπαικη εβδομαδα: οταν περασουν 12ω απο το τελευταιο ευρωπαικο της εβδομαδας
    fut = [r for r in rows if r['ko'] > now]
    if fut:
        wk = max(r['eu_t'] for r in fut)
        wkey = wk.date().isoformat()
        if now >= wk + dt.timedelta(hours=12) and wkey not in st.get('sent', []):
            txt = ('✈️ ΜΑΚΡΙΝΟ ΕΥΡΩΠΑΪΚΟ ΤΑΞΙΔΙ → επομενο ματς πρωταθληματος (πληροφορια, ΟΧΙ pick)\n'
                   'Ιστορικα μπαινουν λιγοτερα γκολ απο οσα περιμενει η αγορα, κυριως ≥2.500 χλμ (★)· στις μεγαλες ομαδες το under εχανε.\n\n'
                   + '\n'.join(_line_txt(r) for r in fut))
            try:
                import notify
                notify.send(txt, channel='info')
                st.setdefault('sent', []).append(wkey); st['sent'] = st['sent'][-20:]
                json.dump(st, open(ST_F, 'w', encoding='utf-8'), ensure_ascii=False)
                print(f'travel_under: λιστα εβδομαδας {wkey} σταλθηκε ({len(fut)} ματς)')
            except Exception as ex:
                print(f'travel_under: αποστολη απετυχε {str(ex)[:80]}')
    print(f'travel_under: υποψηφια {len(rows)} · καταγραφη {len(log)}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--tick' in sys.argv:
        tick()
    else:
        _now = dt.datetime.now(UTC)
        for r in collect(_now):
            if r['ko'] > _now:
                print(_line_txt(r)); print()
