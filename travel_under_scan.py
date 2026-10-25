# -*- coding: utf-8 -*-
"""travel_under_scan.py — 25/10/2026 (Στελιος: «υπαρχει παρομοιο μπετ;» με το under Ντορτμουντ–Αϊντραχτ).
Βρισκει επερχομενα ματς πρωταθληματος CORE7 οπου μια ομαδα ερχεται απο ΕΚΤΟΣ ευρωπαικο (≤6 μερες πριν), με ταξιδι εδρα → γηπεδο.
Μοτιβο 1 = δεν ακολουθει Ευρωπη ≤7 μερες μετα · μοτιβο 2 = Ευρωπη ξανα ≤5 μερες μετα (travel_fatigue_full / travel_seq4, 15-18/10).
Ταξιδιωτης «ασυνηθιστος» = εδρα μηκος −10…25, πλατος 36…62 (οπως στο τεστ). Κατηγορια ομαδας απο την υπεροχη της αγορας (Pinnacle κυρια γραμμη):
μεγαλη ≥1.2 · δυνατη 0.6-1.2 · γηινη <0.6 (υπεροχη του ταξιδιωτη, + = φαβορι). Γραμμη συνολων = κυρια (τιμες πιο κοντα στο ισο).
ΜΟΝΟ ΠΛΗΡΟΦΟΡΙΑ — κανενα pick, τιποτα live."""
import sys, json, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
import fatigue_flags as FF
import picks

UTC = dt.timezone.utc
now = dt.datetime.now(UTC)
L = FF._locs()
EU = {}
for k, Ls in FF._load('europe_fixtures_2627.json', {}).items():
    for m in Ls:
        t = FF._utc(m.get('utc'))
        if t: EU[(t.date().isoformat(), int(m['hid']), int(m['aid']))] = (t, k.split('_')[0], m)
def euro_games(tid):
    return sorted([(t, comp, m) for (d, h, a), (t, comp, m) in EU.items() if h == tid or a == tid], key=lambda x: x[0])
ODDS = FF._load('dom_odds_latest.json', {}).get('odds', {})
def main_line(ladder):
    if not ladder: return None
    return min(ladder, key=lambda r: abs(r[1] - r[2]))
A = FF._load('match_projections_archive.json', {})
rows = []
for fid, m in A.items():
    if m.get('score'): continue
    ko = FF._utc(m.get('utc'))
    if not ko or ko < now or ko > now + dt.timedelta(days=9): continue
    for side, tid, opp in (('εντος', m['home_id'], m['away_id']), ('εκτος', m['away_id'], m['home_id'])):
        tid = int(tid)
        prev = [g for g in euro_games(tid) if g[0] < ko and (ko - g[0]).days <= 6]
        if not prev: continue
        t_eu, comp, em = prev[-1]
        if int(em['hid']) == tid:            # το ευρωπαικο ηταν ΕΝΤΟΣ → οχι ταξιδι
            continue
        home = L.get(tid); ven = L.get(int(em['hid']))
        if not home or not ven: continue
        km = FF._km(home, ven)
        inzone = -10 <= home[1] <= 25 and 36 <= home[0] <= 62
        nxt = [g for g in euro_games(tid) if g[0] > ko]
        gap_after = (nxt[0][0] - ko).total_seconds() / 86400 if nxt else 99
        patt = 'μοτιβο 2 (Ευρωπη ξανα ≤5μ)' if gap_after <= 5 else ('μοτιβο 1' if gap_after > 7 else 'ενδιαμεσο (5-7μ)')
        od = ODDS.get(f"{m['home_id']}_{m['away_id']}") or {}
        ah = main_line(od.get('ah')); ou = main_line(od.get('ou'))
        sup = None
        if ah:   # γραμμη γηπεδουχου ah[0] (αρνητικη = δινει) → υπεροχη γηπ. ≈ −γραμμη (προσεγγιση απο την κυρια γραμμη)
            sup_h = -ah[0] + (0.25 if ah[1] < ah[2] else -0.25 if ah[1] > ah[2] else 0) * 0
            sup = sup_h if side == 'εντος' else -sup_h
        cat = None if sup is None else ('μεγαλη' if sup >= 1.2 else ('δυνατη' if sup >= 0.6 else 'γηινη'))
        T_model = (m.get('home_adj_xg') or 0) + (m.get('away_adj_xg') or 0)
        rows.append(dict(ko=ko, lg=m.get('league'), home=m['home'], away=m['away'], team=m['home'] if side == 'εντος' else m['away'], side=side,
                         eu=f"{comp} @{em.get('hname')} {t_eu.strftime('%d/%m')}", km=round(km), inzone=inzone, rest=round((ko - t_eu).total_seconds() / 86400, 1),
                         patt=patt, ah=ah, ou=ou, sup=sup, cat=cat, T_model=round(T_model, 2)))
rows.sort(key=lambda r: (-r['km'], r['ko']))
GR = lambda t: (t + dt.timedelta(hours=3 if t < dt.datetime(2026, 10, 25, 1, tzinfo=UTC) else 2)).strftime('%a %d/%m %H:%M')
print(f'επερχομενα ματς CORE7 (9 μερες) με ομαδα που ερχεται απο ΕΚΤΟΣ ευρωπαικο: {len(rows)}')
for r in rows:
    print(f"{GR(r['ko'])} │ {r['lg']:12s} {r['home'][:22]:22s} – {r['away'][:22]:22s} │ ταξιδιωτης {r['team'][:20]:20s} ({r['side']}) │ {r['eu']} · {r['km']:5d} χλμ"
          f"{'' if r['inzone'] else ' (εκτος ζωνης)'} · ξεκ. {r['rest']}μ │ {r['patt']} │ κατηγ. {r['cat']} (υπερ. {r['sup']}) │ "
          f"ΣΥΝΟΛΑ {r['ou'][0] if r['ou'] else '—'} over {r['ou'][1] if r['ou'] else ''} / under {r['ou'][2] if r['ou'] else ''} · μοντελο {r['T_model']} │ "
          f"AH γηπ {r['ah'][0] if r['ah'] else '—'} @{r['ah'][1] if r['ah'] else ''}/{r['ah'][2] if r['ah'] else ''}")
