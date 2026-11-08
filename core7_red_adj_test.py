"""
core7_red_adj_test.py — 5/10/2026 (Στελιος): ΚΟΚΚΙΝΕΣ ΚΑΡΤΕΣ στις εισοδους της μηχανης — CORE7 (5 σεζον 2122-2526) + Βραζιλια + MLS.
Αφορμη: στη Βραζιλια/MLS το «χωρις διορθωση» ηταν καλυτερο σε 4/4 & 6/6 σεζον. Live (build_inputs*/picks.load_matches):
  red_xg = +0.0083·λεπτα_αριθμητικης_υπεροχης − ½·0.0083·λεπτα_μειονεκτηματος  → ΠΡΟΣΤΙΘΕΤΑΙ στο xG (ο πλεονεκτων παιρνει ΚΙ ΑΛΛΟ)
Τροποι: live · καθολου · ΑΝΑΠΟΔΑ · μονο σουτ ΠΡΙΝ την 1η κοκκινη (αναγωγη σε 95′) · το ιδιο + γκολ · σουτ μετα ×½ · ματς με κοκκινη <70′ εκτος ιστορικου.
Μηχανη = southam_tune (ιδια λογικη με live· εδρα LOSO απο xG, νεοφωτιστες pooled — για CORE7 ελαφρως απλουστερη απο τη live, ιδια για ολους τους τροπους).
Κριτης: ματς αγωνιστικης ≥7 — LL 1Χ2, λαθος υπεροχης vs γκολ (Sg) / vs πραγματικο xG ολου του ματς (Sx), συνολα Tg/Tx. LOSO ανα σεζον.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import southam_tune as T
V = {'live (+ στον πλεονεκτουντα)': {}, 'καθολου': {'red': False}, 'ΑΝΑΠΟΔΑ': {'red': 'rev'}, 'σουτ πριν την κοκκινη': {'red': 'cut'},
     'σουτ+γκολ πριν': {'red': 'cutg'}, 'σουτ μετα ×½': {'red': 'half'}, 'κοκκινη<70′ εκτος': {'red': 'drop'},
     'ΕΜΠΕΙΡΙΚΗ ×1.72/−.0072': {'red': 'emp'}, 'ΕΜΠΕΙΡ. ανα σκορ': {'red': 'emps'}, 'ΕΜΠΕΙΡ. προσθετικη': {'red': 'empa'},
     'Skripnikov ×1.8/×.75': {'red': 'skrip'}, 'Caley ×1.4': {'red': 'caley'}}
SA = dict(T.FILES)
CORE = {lg: {s: f'data_{lg}_{s}.json' for s in ('2122', '2223', '2324', '2425', '2526')}
        for lg in ('EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie')}
import pandas as pd, numpy as np
for title, files in (('CORE7 (7 λιγκες, 5 σεζον)', CORE), ('ΒΡΑΖΙΛΙΑ & MLS', SA)):
    T.FILES = files; T.RAW = None; T._INP.clear()
    if files is CORE:
        T.MARKET_F = '__none__'; T._MK = None
        # μια «λιγκα» για τον κριτη: ενωνουμε τις 7 (ιδιες σεζον) — αλλα η μηχανη τρεχει ανα λιγκα
        orig_eval = T.evaluate
        def ev7(P, **kw):
            E = orig_eval(P, **kw); E['league'] = 'CORE7'; return E
        T.evaluate = ev7
        # compare τυπωνει ανα ('Brazil','MLS') — εδω χρειαζομαστε 'CORE7'
        import types
    ev = {}
    for nm, v in V.items():
        ev[nm] = T.evaluate(T.run(v)).set_index('mid')
    if files is CORE: T.evaluate = orig_eval
    B = ev['live (+ στον πλεονεκτουντα)']
    lgs = ['CORE7'] if files is CORE else ['Brazil', 'MLS']
    print(f'\n{"=" * 100}\n{title} — Δ απο live ×1000 (ΑΡΝΗΤΙΚΟ = καλυτερο) ±SE [σεζον καλυτερες]\n{"=" * 100}')
    for lg in lgs:
        b = B[B.league == lg]; seas = sorted(b.season.unique())
        print(f'  [{lg}] n{len(b)} ματς')
        for nm, E in ev.items():
            e = E[E.league == lg]; row = []
            for m in ('LL', 'Sg', 'Sx', 'Tg', 'Tx'):
                d = (e[m] - b[m]).dropna(); bs = sum(1 for s in seas if d[e.loc[d.index, 'season'] == s].mean() < 0)
                row.append(f'{m} {1000*d.mean():+6.2f}±{1000*d.std()/np.sqrt(len(d)):4.2f}[{bs}/{len(seas)}]')
            print(f'   {nm:28s} ' + '  '.join(row))
        for m in ('LL', 'Sg', 'Sx'):
            per = {nm: E[E.league == lg].groupby('season')[m].mean() for nm, E in ev.items()}; ch = []; g = []
            for s in seas:
                best = min(per, key=lambda nm: np.mean([per[nm][o] for o in seas if o != s])); ch.append(best); g.append(per[best][s] - per['live (+ στον πλεονεκτουντα)'][s])
            print(f'   LOSO [{m}]: ' + ' · '.join(f'{s}→{c}' for s, c in zip(seas, ch)) + ' · κερδος εκτος ' + ' '.join(f'{1000*x:+.2f}' for x in g) + f' · {sum(x < -1e-12 for x in g)}/{len(g)}')
    if files is CORE:
        # ανα λιγκα (καθολου vs live), LL & Sg
        P0 = T.evaluate(T.run({})); P1 = T.evaluate(T.run({'red': False}))
        T.FILES = files
        x = P0.set_index('mid').join(P1.set_index('mid')[['LL', 'Sg', 'Sx']], rsuffix='_n')
        print('   ανα λιγκα (καθολου − live) ×1000: ' + ' · '.join(f"{lg}: LL {1000*(g.LL_n-g.LL).mean():+.2f} Sx {1000*(g.Sx_n-g.Sx).mean():+.2f}" for lg, g in x.groupby('league')))
