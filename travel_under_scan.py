# -*- coding: utf-8 -*-
"""travel_under_scan.py — 25/10/2026 (Στελιος: «υπαρχει παρομοιο μπετ;» με το under Ντορτμουντ–Αϊντραχτ → «φτιαξτο ναι και δες αν εχουμε καταγραφη»
→ «οχι απλη καταγραφη: διαφορετικα ΣΕΝΑΡΙΑ — η Ντορτμουντ 3 εκτος σερι (2 Ευρωπη, 1 πρωταθλημα), η Αρσεναλ 2 εκτος (πρωταθλημα+Ευρωπη) και μετα
εντος· η κουραση κουβαλιεται, τα συχνα ματς διαφερουν απο 1 εκτος»).
ΕΥΡΗΜΑ (travel_fatigue_full / travel_seq4 / travel_deep2, 16-18/10): μετα απο ΜΑΚΡΙΝΟ εκτος ευρωπαικο ταξιδι, στο ΕΠΟΜΕΝΟ ματς πρωταθληματος
μπαινουν λιγοτερα γκολ απο οσα περιμενει η αγορα (εντος 2.500-3.500 χλμ: −0.40, under κλεισ. +12.3% σε 34)· κοντρα στο χαντικαπ ΔΕΝ δουλευει·
στις «μεγαλες» ομαδες (υπεροχη ≥1.2) το under εχανε. ΤΑΣΗ, ΟΧΙ ΚΑΝΟΝΑΣ → ΠΛΗΡΟΦΟΡΙΑ + ΚΑΤΑΓΡΑΦΗ, κανενα pick.
ΚΑΤΑΓΡΑΦΗ (travel_under_log.json, ενα κλειδι ανα ματς): ΚΑΘΕ ματς CORE7 οπου εστω μια ομαδα επαιξε ευρωπαικο (εντος ή εκτος, οποια αποσταση)
≤6 μερες πριν — ωστε να συγκρινονται ΣΕΝΑΡΙΑ (και «ελεγχος» με Ευρωπη εντος / κοντινο ταξιδι). Για ΚΑΘΕ ομαδα: ΠΡΟΓΡΑΜΜΑ 14 ημερων
(καθε ματς: μερα, εντος/εκτος, Ευρωπη/πρωταθλημα/κυπελλο, αντιπαλος, χλμ ταξιδιου, ξεκουραση) + ΣΕΝΑΡΙΟ (π.χ. «Ε✈ Π✈ Ε✈ → Π🏠») +
συνοψη (ματς 7/14 μερων, σερι εκτος πριν, χλμ 14 μερων, ξεκουραση, ελαχιστη ξεκουραση, ευρωπαικα εκτος). Τιμες under (κυρια γραμμη
Pinnacle): πρωτη εμφανιση · τελευταια πριν τη σεντρα (≈ κλεισιμο) · αποτελεσμα. Πηγες προγραμματος: data_*_2627/2026 · match_projections_archive ·
europe_fixtures_2627 · euq_fixtures (2627) · cups_fixtures (κυπελλα 2627/2026 — στατικο αρχειο 16/10, cups_fetch.py).
INFO BOT: μια λιστα ανα ευρωπαικη εβδομαδα (12ω μετα το τελευταιο ευρωπαικο) με τα ματς «ταξιδιωτη» (εκτος ευρωπαικο ≥1.500 χλμ), με σεναριο.
Χρηση: python travel_under_scan.py (λιστα στην οθονη) · python travel_under_scan.py --tick (scanner)."""
import os, sys, json, glob, datetime as dt
import fatigue_flags as FF

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_F = os.path.join(ROOT, 'travel_under_log.json')
ST_F = os.path.join(ROOT, 'travel_under_state.json')
UTC = dt.timezone.utc
FOCUS_KM = 1500
HIST = {('εντος', 1500): (+0.04, -1.7, 119), ('εντος', 2500): (-0.40, +12.3, 34), ('εντος', 3500): (-0.47, +11.4, 8),
        ('εκτος', 1500): (-0.15, +14.6, 111), ('εκτος', 2500): (-0.18, +13.6, 26), ('εκτος', 3500): (+0.33, -63.5, 4)}
KIND_TXT = {'Ε': 'Ευρωπη', 'Π': 'πρωταθλημα', 'Κ': 'κυπελλο'}
_G = None


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


def games():
    """{team_id: [ματς...]} με ειδος: Ε (Ευρωπη/προκριματικα), Π (πρωταθλημα), Κ (κυπελλο). Χωρις διπλα (ιδια μερα & ζευγαρι)."""
    global _G
    if _G is not None:
        return _G
    G = {}
    def add(t, h, a, kind, comp, hn=None, an=None):
        if t is None or h is None or a is None:
            return
        key = (t.date().isoformat(), int(h), int(a))
        if key in G and G[key]['kind'] != 'Π':
            return                          # Ευρωπη/κυπελλο κερδιζει (το ιδιο ματς δεν ειναι πρωταθλημα)
        G[key] = dict(t=t, h=int(h), a=int(a), kind=kind, comp=comp, hn=hn, an=an)
    for f in glob.glob(os.path.join(ROOT, 'data_*_2627.json')) + glob.glob(os.path.join(ROOT, 'data_*_2026.json')):
        lg = os.path.basename(f)[5:-5].rsplit('_', 1)[0]
        if lg in FF._NAT or lg.startswith(('WCQ', 'NationsLeague')):
            continue
        D = FF._load(os.path.basename(f), {})
        for m in (D.values() if isinstance(D, dict) else D):
            try:
                add(FF._utc(m['date']), m['home']['id'], m['away']['id'], 'Π', lg, m['home'].get('name'), m['away'].get('name'))
            except Exception:
                pass
    for v in FF._load('match_projections_archive.json', {}).values():
        if isinstance(v, dict) and v.get('home_id') and v.get('away_id'):
            add(FF._utc(v.get('utc')), v['home_id'], v['away_id'], 'Π', v.get('league'), v.get('home'), v.get('away'))
    for fn, kind in (('europe_fixtures_2627.json', 'Ε'), ('euq_fixtures.json', 'Ε'), ('cups_fixtures.json', 'Κ')):
        for k, L in FF._load(fn, {}).items():
            if not str(k).endswith(('2627', '2026')):
                continue
            for m in L:
                add(FF._utc(m.get('utc')), m.get('hid'), m.get('aid'), kind, str(k).rsplit('_', 1)[0], m.get('hname'), m.get('aname'))
    T = {}
    for g in G.values():
        T.setdefault(g['h'], []).append(g); T.setdefault(g['a'], []).append(g)
    for k in T:
        T[k].sort(key=lambda g: g['t'])
    _G = T
    return T


def schedule(tid, ko, venue_tid, days=14):
    """Προγραμμα της ομαδας tid στις 14 μερες πριν το ματς (σεντρα ko, γηπεδο του venue_tid) + συνοψη + σεναριο."""
    tid = int(tid); L = FF._locs(); home = L.get(tid)
    allg = games().get(tid, [])
    prev = [g for g in allg if g['t'] < ko - dt.timedelta(hours=6)]
    win = [g for g in prev if (ko - g['t']).total_seconds() / 86400 <= days]
    before = prev[-len(win) - 1] if len(prev) > len(win) else None
    loc = L.get(before['h']) if before else home
    last_t = before['t'] if before else None
    seq, km14 = [], 0.0
    for g in win:
        ven = L.get(g['h']); km = FF._km(loc, ven) if (loc and ven) else 0.0; km14 += km
        away = g['h'] != tid
        opp = g['an'] if not away else g['hn']
        seq.append(dict(d=g['t'].strftime('%d/%m'), ha='εκτ' if away else 'εντ', kind=g['kind'], comp=g['comp'], opp=opp,
                        km=round(km), rest=round((g['t'] - last_t).total_seconds() / 86400, 1) if last_t else None))
        loc, last_t = ven or loc, g['t']
    ven_now = L.get(int(venue_tid)); trip = FF._km(loc, ven_now) if (loc and ven_now) else 0.0; km14 += trip
    streak = 0
    for g in reversed(prev):
        if g['h'] != tid: streak += 1
        else: break
    rests = [s['rest'] for s in seq if s['rest'] is not None] + ([round((ko - last_t).total_seconds() / 86400, 1)] if last_t else [])
    here = 'εκτ' if int(venue_tid) != tid else 'εντ'
    scen = ' '.join(f"{s['kind']}{'✈' if s['ha'] == 'εκτ' else '🏠'}" for s in seq) + f" → Π{'✈' if here == 'εκτ' else '🏠'}"
    return dict(seq=seq, scen=scen, n7=sum(1 for g in win if (ko - g['t']).days < 7), n14=len(win), away_streak_before=streak, here=here,
                trip_now=round(trip), km14=round(km14), rest=rests[-1] if rests else None, min_rest=min(rests) if rests else None,
                euro14=sum(1 for g in win if g['kind'] == 'Ε'), euro_away14=sum(1 for g in win if g['kind'] == 'Ε' and g['h'] != tid),
                cups14=sum(1 for g in win if g['kind'] == 'Κ'))


def collect(now=None, horizon_days=9):
    now = now or dt.datetime.now(UTC)
    L = FF._locs()
    ODDS = FF._load('dom_odds_latest.json', {}).get('odds', {})
    rows = []
    for fid, m in FF._load('match_projections_archive.json', {}).items():
        ko = FF._utc(m.get('utc'))
        if not ko or ko > now + dt.timedelta(days=horizon_days) or ko < now - dt.timedelta(days=10):
            continue
        hid, aid = int(m['home_id']), int(m['away_id'])
        sched = {s: schedule(t, ko, hid) for s, t in (('home', hid), ('away', aid))}
        trav = []
        for s, tid in (('home', hid), ('away', aid)):
            eu = [g for g in games().get(tid, []) if g['kind'] == 'Ε' and g['t'] < ko and (ko - g['t']).total_seconds() / 86400 <= 6]
            if eu:
                g = eu[-1]; away = g['h'] != tid
                km = FF._km(L.get(tid), L.get(g['h'])) if away and L.get(tid) and L.get(g['h']) else 0.0
                home_loc = L.get(tid)
                inzone = bool(home_loc) and -10 <= home_loc[1] <= 25 and 36 <= home_loc[0] <= 62
                nxt = [x for x in games().get(tid, []) if x['kind'] == 'Ε' and x['t'] > ko]
                gap = (nxt[0]['t'] - ko).total_seconds() / 86400 if nxt else 99
                trav.append(dict(side=s, team=m['home'] if s == 'home' else m['away'], eu_comp=g['comp'], eu_at=g['hn'], eu_t=g['t'],
                                 eu_away=away, km=round(km), inzone=inzone, patt=2 if gap <= 5 else (1 if gap > 7 else 0)))
        if not trav:
            continue
        od = ODDS.get(f"{hid}_{aid}") or {}
        ah, ou = _main_line(od.get('ah')), _main_line(od.get('ou'))
        sup_h = None if not ah else -ah[0]
        for t in trav:
            sup = None if sup_h is None else (sup_h if t['side'] == 'home' else -sup_h)
            t['sup'] = sup
            t['cat'] = None if sup is None else ('μεγαλη' if sup >= 1.2 else ('δυνατη' if sup >= 0.6 else 'γηινη'))
            t['focus'] = bool(t['eu_away'] and t['km'] >= FOCUS_KM and t['inzone'])
        rows.append(dict(fid=str(fid), lg=m.get('league'), ko=ko, home=m['home'], away=m['away'], ah=ah, ou=ou, trav=trav, sched=sched,
                         T_model=round((m.get('home_adj_xg') or 0) + (m.get('away_adj_xg') or 0), 2), score=m.get('score')))
    rows.sort(key=lambda r: r['ko'])
    return rows


def _settle_under(tg, L, o):
    parts = [L] if (L * 4) % 2 == 0 else [L - 0.25, L + 0.25]
    return round(sum(((o - 1) if tg < x - 0.01 else (-1.0 if tg > x + 0.01 else 0.0)) for x in parts) / len(parts), 3)


def _team_txt(sc):
    s = ' → '.join(f"{x['kind']}{'✈' if x['ha'] == 'εκτ' else '🏠'}{(x['opp'] or '')[:12]}{(' ' + format(x['km'], ',').replace(',', '.')) if (x['km'] >= 300 and x['ha'] == 'εκτ') else ''}"
                   for x in sc['seq'][-4:])
    return (f"{s} → σημερα {'✈' if sc['here'] == 'εκτ' else '🏠'}  ({sc['n14']} ματς/14μ · {sc['n7']}/7μ · ξεκ. {sc['rest']}μ · "
            f"σερι εκτος πριν {sc['away_streak_before']} · {format(sc['km14'], ',').replace(',', '.')} χλμ/14μ)")


def _row_txt(r):
    out = []
    for t in r['trav']:
        if not t['focus']:
            continue
        h = HIST[('εντος' if t['side'] == 'home' else 'εκτος', _bucket(t['km']))]
        sc = r['sched'][t['side']]; op = r['sched']['away' if t['side'] == 'home' else 'home']
        km = format(t['km'], ',').replace(',', '.')
        ou = f"under {r['ou'][0]} @{r['ou'][2]}" if r['ou'] else 'συνολα: δεν ανοιξαν ακομα'
        out.append(f"{'★' if t['km'] >= 2500 else '•'} {_gr(r['ko'])} {r['home']} – {r['away']}\n"
                   f"   {t['team']}: {_team_txt(sc)}\n"
                   f"   αντιπαλος: {_team_txt(op)}\n"
                   f"   {ou} · μοντελο {r['T_model']} · {t['cat'] or '—'}{' · μοτιβο 2 (Ευρωπη ξανα ≤5μ)' if t['patt'] == 2 else ''}"
                   f" · ιστορικο ({km} χλμ): {h[0]:+.2f} γκολ, under {h[1]:+.1f}% ({h[2]} bets)"
                   + (' ⚠ μεγαλη: εκει το under εχανε' if t['cat'] == 'μεγαλη' else ''))
    return '\n'.join(out)


def tick():
    now = dt.datetime.now(UTC)
    rows = collect(now)
    log = FF._load('travel_under_log.json', {})
    old_first = {k.split('|')[0]: v.get('first') for k, v in log.items() if '|' in k}          # 25/10: παλια μορφη (ανα ομαδα) → ανα ματς
    log = {k: v for k, v in log.items() if '|' not in k}
    st = FF._load('travel_under_state.json', {})
    changed = bool(old_first)
    for r in rows:
        e = log.get(r['fid'])
        if e is None and r['ko'] > now and r['ou']:
            first = old_first.get(r['fid']) or dict(t=now.isoformat()[:16], line=r['ou'][0], over=r['ou'][1], under=r['ou'][2])
            e = log[r['fid']] = dict(seen=first['t'], lg=r['lg'], ko=r['ko'].isoformat()[:16], home=r['home'], away=r['away'],
                                     T_model=r['T_model'], ah_first=r['ah'], first=first,
                                     trav=[{k: (v.isoformat()[:16] if isinstance(v, dt.datetime) else v) for k, v in t.items()} for t in r['trav']],
                                     sched=r['sched'])
            changed = True
        if e is None:
            continue
        if r['ko'] > now and r['ou']:
            last = dict(t=now.isoformat()[:16], line=r['ou'][0], over=r['ou'][1], under=r['ou'][2])
            if (e.get('last') or {}).get('line') != last['line'] or (e.get('last') or {}).get('under') != last['under']:
                e['last'] = last; e['ah_last'] = r['ah']; changed = True
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
    fut = [r for r in rows if r['ko'] > now and any(t['focus'] for t in r['trav'])]
    if fut:
        wk = max(t['eu_t'] for r in fut for t in r['trav'] if t['focus'])
        wkey = wk.date().isoformat()
        if now >= wk + dt.timedelta(hours=12) and wkey not in st.get('sent', []):
            txt = ('✈️ ΜΑΚΡΙΝΟ ΕΥΡΩΠΑΪΚΟ ΤΑΞΙΔΙ → επομενο ματς πρωταθληματος (πληροφορια, ΟΧΙ pick)\n'
                   'Ιστορικα μπαινουν λιγοτερα γκολ απο οσα περιμενει η αγορα, κυριως ≥2.500 χλμ (★)· στις μεγαλες ομαδες το under εχανε.\n'
                   'Προγραμμα 14 ημερων: Ε = Ευρωπη · Π = πρωταθλημα · Κ = κυπελλο · ✈ εκτος (χλμ ταξιδιου) · 🏠 εντος.\n\n'
                   + '\n\n'.join(_row_txt(r) for r in fut))
            try:
                import notify
                notify.send(txt, channel='info')
                st.setdefault('sent', []).append(wkey); st['sent'] = st['sent'][-20:]
                json.dump(st, open(ST_F, 'w', encoding='utf-8'), ensure_ascii=False)
                print(f'travel_under: λιστα εβδομαδας {wkey} σταλθηκε ({len(fut)} ματς)')
            except Exception as ex:
                print(f'travel_under: αποστολη απετυχε {str(ex)[:80]}')
    print(f'travel_under: ματς με ευρωπαικο ≤6μ {len(rows)} · καταγραφη {len(log)}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--tick' in sys.argv:
        tick()
    else:
        _now = dt.datetime.now(UTC)
        for r in collect(_now):
            if r['ko'] > _now and any(t['focus'] for t in r['trav']):
                print(_row_txt(r)); print()
