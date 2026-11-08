# -*- coding: utf-8 -*-
"""el_round1_changes.py — ΑΝΑΦΟΡΑ (25/9/2026, αιτημα Στελιου): ποσο αλλαξε καθε ομαδα + τα picks της 1ης αγωνιστικης.
Αλλαγη: συνεχεια (el_continuity.csv, μεριδιο περσινων λεπτων που μενει) · ποιοι εφυγαν / ηρθαν (el_people.json + el_players.json).
Picks: μοντελο live (χαντικαπ v1 · συνολο v2 + παρατασεις) vs Pinnacle (closing οπου παιχτηκε, αλλιως τελευταια τιμη), edge ≥5%.
Εξοδος: el_round1_changes_out.txt"""
import sys, json, math
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, 'dashboard')
import euroleague_view as ev
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))

S = json.load(open('el_sched.json', encoding='utf-8'))
people = json.load(open('el_people.json', encoding='utf-8'))
PL = json.load(open('el_players.json', encoding='utf-8'))
CO = pd.read_csv('el_continuity.csv'); CO = CO[CO.season == 'E2026'].set_index('team')

# στατιστικα 2025-26 ανα παικτη-ομαδα (Ευρωλιγκα + EuroCup)
st = {}
for k, g in PL.items():
    if g.get('season') not in ('E2025', 'U2025') or 'err' in g or 'ph' not in g: continue
    for side, tc in (('ph', g['hcode']), ('pa', g['acode'])):
        for p in g[side]:
            r = st.setdefault((p[0], g['comp'], tc), dict(name=p[1], g=0, min=0.0, pir=0.0))
            if p[3] and p[3] > 0: r['g'] += 1; r['min'] += p[3]; r['pir'] += (p[18] or 0)
def best_prev(pid):
    c = [(k, v) for k, v in st.items() if k[0] == pid and v['g'] > 0]
    return max(c, key=lambda kv: kv[1]['min']) if c else None
first = min(x['utc'] for x in S['E2026'])[:10]
lim = (pd.Timestamp(first) + pd.Timedelta(days=10)).strftime('%Y-%m-%d')
names = {x['hcode']: x['home'] for x in S['E2026']}

P('=== ΑΛΛΑΓΗ ΚΑΘΕ ΟΜΑΔΑΣ (2025-26 → 2026-27) ===')
P('συνεχεια = % των περσινων λεπτων της ομαδας που επαιξαν παικτες που ειναι ακομα εκει · PIR/αγ = ιδιο της Ευρωλιγκας περσι')
P('(«ισοζυγιο PIR» = χοντρη ενδειξη κατευθυνσης: PIR/αγ των νεων που επαιζαν Ευρωλιγκα/EuroCup − των βασικων που εφυγαν· ΟΧΙ μετρημενο μοντελο)')
rows = []
for c in sorted(names):
    roster = {'P' + p['code'] for p in people.get(f'E2026_{c}', []) if p['type'] == 'J' and p['code'] and p['start'] <= lim}
    prev = {k[0]: v for k, v in st.items() if k[1] == 'E' and k[2] == c and v['g'] > 0}
    tot = sum(v['min'] for v in prev.values()) or 1
    gone = sorted([(pid, v) for pid, v in prev.items() if pid not in roster], key=lambda kv: -kv[1]['min'])
    new = []
    for pid in roster:
        if pid in prev: continue
        bp = best_prev(pid)
        new.append((pid, bp))
    key_gone = [(v['name'], v['min'] / tot * 5, v['pir'] / v['g']) for pid, v in gone if v['min'] / tot * 5 >= 0.08]
    key_new = sorted([(bp[1]['name'], bp[0][1], bp[0][2], bp[1]['pir'] / bp[1]['g'], bp[1]['min'] / bp[1]['g']) for pid, bp in new if bp and bp[1]['min'] / bp[1]['g'] >= 12],
                     key=lambda x: -x[3])
    unknown = sum(1 for pid, bp in new if not bp or bp[1]['min'] / bp[1]['g'] < 12)
    bal = sum(x[3] for x in key_new if x[1] == 'E') + 0.6 * sum(x[3] for x in key_new if x[1] == 'U') - sum(x[2] for x in key_gone)
    cont = CO.cont.get(c, math.nan)
    rows.append(dict(c=c, cont=cont, bal=bal))
    coach = CO.loc[c] if c in CO.index else None
    P('')
    P(f'■ {names[c]} ({c}) · συνεχεια {cont*100:.0f}%' + (f' · ΝΕΟΣ προπονητης: {str(coach.coach).title()} (πριν {str(coach.prev_coach).title()})' if coach is not None and coach.coach_change else '')
      + f' · ισοζυγιο PIR {bal:+.1f}')
    P('   εφυγαν: ' + (', '.join(f'{n.title()} ({pir:.1f})' for n, sh, pir in key_gone) or '—'))
    P('   ηρθαν:  ' + (', '.join(f'{n.title()} ({"EL" if cp == "E" else "EC"} {tc} {pir:.1f})' for n, cp, tc, pir, m in key_new) or '—')
      + (f' + {unknown} χωρις Ευρωπη περσι (NBA/πρωταθλημα/νεαροι)' if unknown else ''))
R = pd.DataFrame(rows).set_index('c')
q = 0.49
P('')
P('=== PICKS 1ης ΑΓΩΝΙΣΤΙΚΗΣ (edge ≥5%, Pinnacle) ===')
d = ev.load_all(); proj = d['proj']; sm, stt = proj['sigma_margin'], proj['sigma_total']
tally = {k: [0, 0, 0] for k in ('πολυ · χαντικαπ', 'λιγο · χαντικαπ', 'πολυ · συνολο', 'λιγο · συνολο')}
for g in proj['games']:
    if g['round'] != 1: continue
    mk = ev.market_for(g, d) or {}
    if mk.get('line') is None: continue
    L, oh, oa, TL, ov, un = mk['line'], mk['oh'], mk['oa'], mk['tl'], mk['to'], mk['tu']
    pw, pp, pl = ev.spread_probs(float(g['margin']), L, sm)
    eh, ea = ev.edge(pw, pp, oh), ev.edge(pl, pp, oa)
    po, pq, pu = ev.total_probs(float(g['total']), TL, stt)
    eo, eu = ev.edge(po, pq, ov), ev.edge(pu, pq, un)
    played = g.get('hs') is not None
    res = f"{g['hs']}-{g['as_']}" if played else 'δεν παιχτηκε'
    ch, ca = R.cont.get(g['hcode']), R.cont.get(g['acode'])
    P('')
    P(f"■ {g['home']} ({ch*100:.0f}%) – {g['away']} ({ca*100:.0f}%) · τελικο {res} · τιμες: {mk.get('kind')}")
    P(f"   γραμμη: μοντ {-float(g['margin']):+.1f} vs αγορα {L:+.1f} · συνολο: μοντ {float(g['total']):.1f} vs αγορα {TL:.1f}")
    for lab, e, team, other, won in (
        (f"{g['home']} {L:+.1f} @{oh}", eh, g['hcode'], g['acode'], (g['hs'] - g['as_'] + L) if played else None),
        (f"{g['away']} {-L:+.1f} @{oa}", ea, g['acode'], g['hcode'], (g['as_'] - g['hs'] - L) if played else None),
        (f"Over {TL} @{ov}", eo, None, None, (g['hs'] + g['as_'] - TL) if played else None),
        (f"Under {TL} @{un}", eu, None, None, (TL - g['hs'] - g['as_']) if played else None)):
        if e < 0.05: continue
        cv = lambda t: 0.0 if pd.isna(R.cont.get(t)) else R.cont.get(t)   # νεα ομαδα (Μπεσικτας) = αλλαξε ολοκληρη
        big = min(cv(g['hcode']), cv(g['acode'])) < q
        cls = ('πολυ' if big else 'λιγο') + (' · χαντικαπ' if team else ' · συνολο')
        if team:
            why = f"στηριζουμε {team} ({cv(team)*100:.0f}%) κοντρα σε {other} ({cv(other)*100:.0f}%)"
        else:
            why = 'συνολο'
        r = '—' if won is None else ('ΚΕΡΔΙΣΕ' if won > 0 else ('push' if won == 0 else 'ΕΧΑΣΕ'))
        if won is not None: tally[cls][0 if won > 0 else (2 if won == 0 else 1)] += 1
        P(f"   PICK {lab:34s} edge {e*100:+.1f}% · {why} · ματς με ομαδα που αλλαξε ΠΟΛΥ: {'ναι' if big else 'οχι'} · {r}")
P('')
P('=== ΣΥΝΟΨΗ (παιγμενα) ===')
for k, v in tally.items():
    P(f'  ματς με ομαδα που αλλαξε {k}: κερδισαν {v[0]} · εχασαν {v[1]}' + (f' · push {v[2]}' if v[2] else ''))
open('el_round1_changes_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
