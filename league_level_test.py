# -*- coding: utf-8 -*-
"""league_level_test.py — 29/10/2026 (Στελιος: «τρεξτο» — πιο γρηγορος «χαρακας» λιγκας για να πιανεται νωρις αλλαγη επιπεδου, οπως φετος
+0.37 xG/ματς). ΜΗΧΑΝΗ = europe_test (live: K=8, ραμπα 100→60/40, SoS 0.75 στα φετινα πριν τη μιξη), ΧΩΡΙΣ την εμπειρικη διορθωση κοκκινων
(ιδια σε ολες τις παραλλαγες → δεν επηρεαζει τη συγκριση). + ΦΕΤΙΝΗ σεζον 2627 απο το teamgame_inputs.csv (live εισοδοι).
ΠΡΟΒΛΕΨΗ = (δυναμη Α × δυναμη Β) / χαρακας → αν μονο ο χαρακας γινει γρηγορος ενω οι ομαδες ειναι μισες περσινες, το επιπεδο ΠΕΦΤΕΙ.
ΠΑΡΑΛΛΑΓΕΣ: KN = 20 (live) / 10 / 5 · REL = το περσινο κομματι της δυναμης καθε ομαδας (prior) ΚΛΙΜΑΚΩΝΕΤΑΙ στο ΤΡΕΧΟΝ επιπεδο της λιγκας
  (xG/σουτ × χαρακα_τωρα/χαρακα_περσι, σουτ × ιδιο) πριν τη μιξη με το φετινο.
ΜΕΤΡΗΣΗ: μεροληψια συνολου (μοντελο − πραγματικα γκολ) · τετραγωνικο λαθος συνολου · 1Χ2 RPS (Dixon-Coles) — ανα σεζον × αγων 1-6 / 7-14 / 15+.
ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ): καλυτερο λαθος συνολου σε ≥3/4 ιστορικες σεζον στις 7+ · 1Χ2 RPS οχι χειροτερο (≤ +0.0003) · μικροτερη φετινη μεροληψια.
Χρηση: python league_level_test.py <KN> <REL 0/1>  → league_level_<KN>_<REL>.pkl ·  python league_level_test.py report"""
import sys, os, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

if sys.argv[1] != 'report':
    KN, REL = float(sys.argv[1]), int(sys.argv[2])
    os.environ['SOS_MODE'] = 'current'
    src = open('europe_test.py', encoding='utf-8').read()
    pre = src[:src.index("print('Χτισιμο προβλεψεων")]
    for o, n in (("K = 8.0; BL = 0.60; SPLIT = 13; KG = 12.0; ST = 1.5; GLO, GHI = 6, 13",
                  "K = 8.0; BL = 0.60; SPLIT = 13; KG = 12.0; ST = 0.75; GLO, GHI = 6, 13"),
                 ("w = acc['n'] / (acc['n'] + 20.0)", "w = acc['n'] / (acc['n'] + KN_V)"),
                 ("            key = (tid, n)\n", "            key = (tid, n, acc['n'] if REL_V else 0)\n")):
        assert pre.count(o) == 1, o
        pre = pre.replace(o, n)
    # REL: περσινο κομματι στο τρεχον επιπεδο λιγκας (και στο warm() και στο sos_current())
    o_w = "            if p is None:\n                p = CC.promo_prior(lg, sea, tid)\n            v = p if n == 0"
    n_w = ("            if p is None:\n                p = CC.promo_prior(lg, sea, tid)\n"
           "            if REL_V: p = (p[0] * cur[1] / plx, p[1] * cur[1] / plx, p[2] * cur[0] / pls, p[3] * cur[0] / pls)\n"
           "            v = p if n == 0")
    o_s = "            if p is None:\n                p = CC.promo_prior(lg, sea, tid)\n            if n == 0:\n                return p"
    n_s = ("            if p is None:\n                p = CC.promo_prior(lg, sea, tid)\n"
           "            if REL_V: p = (p[0] * cur[1] / plx, p[1] * cur[1] / plx, p[2] * cur[0] / pls, p[3] * cur[0] / pls)\n"
           "            if n == 0:\n                return p")
    assert pre.count(o_w) == 1 and pre.count(o_s) == 1
    pre = pre.replace(o_w, n_w).replace(o_s, n_s)
    g = {'__name__': 'llt', 'KN_V': KN, 'REL_V': REL}
    class _Q(io.StringIO):
        def reconfigure(self, **k): pass
    with contextlib.redirect_stdout(_Q()):
        exec(pre.replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), g)
    sys.stdout = sys.__stdout__; sys.stdout.reconfigure(encoding='utf-8')
    import sos_test
    _pv = sos_test.prev_season
    def _prev(sea): return '2526' if str(sea) == '2627' else _pv(sea)
    sos_test.prev_season = _prev; g['prev_season'] = _prev          # η 2627 δεν ειναι στις FIVE_SEASONS
    M27, id27 = sos_test.load_matches_5s(sos_test.CORE7, ['2627'], csv='teamgame_inputs.csv')
    g['M'] = pd.concat([g['M'], M27], ignore_index=True); g['id2'].update(id27)
    g['SEAS'] = ['2223', '2324', '2425', '2526', '2627']
    P = g['run']()
    TG = g['M'][['mid', 'hg', 'ag']].copy(); TG['mid'] = TG['mid'].astype(str)
    P = P.merge(TG.drop_duplicates('mid'), on='mid', how='left')
    P.to_pickle(f'league_level_{int(KN)}_{REL}.pkl')
    print(f'KN {KN} REL {REL}: {len(P)} ματς · 2627: {(P.season == "2627").sum()}')
    sys.exit(0)

# ---------------- ΑΝΑΦΟΡΑ ----------------
import picks
VARS = [(20, 0, 'σημερινο (Kn 20)'), (10, 0, 'μονο χαρακας Kn 10'), (5, 0, 'μονο χαρακας Kn 5'),
        (20, 1, 'περσινο στο φετινο επιπεδο + Kn 20'), (10, 1, 'περσινο στο φετινο επιπεδο + Kn 10'), (5, 1, 'περσινο στο φετινο επιπεδο + Kn 5')]
def rps(xh, xa, gd):
    d = picks.gd_dist_dom(max(xh, .05), max(xa, .05))
    ks = np.array(sorted(d)) if isinstance(d, dict) else None
    if isinstance(d, dict):
        ph = sum(v for k, v in d.items() if k > 0); pd_ = d.get(0, 0); pa = 1 - ph - pd_
    else:
        raise ValueError
    y = (1, 0, 0) if gd > 0 else ((0, 1, 0) if gd == 0 else (0, 0, 1))
    c1 = ph - y[0]; c2 = ph + pd_ - y[0] - y[1]
    return (c1 ** 2 + c2 ** 2) / 2
R = {}
for kn, rel, lab in VARS:
    f = f'league_level_{kn}_{rel}.pkl'
    if not os.path.exists(f): continue
    P = pd.read_pickle(f); P = P[P.hg.notna()].copy()
    P['T'] = P.xg_h + P.xg_a; P['tg'] = P.hg + P.ag; P['err'] = P['T'] - P.tg
    P['win'] = np.where(P.md < 6, '1-6', np.where(P.md < 14, '7-14', '15+'))
    P['rps'] = [rps(a, b, c) for a, b, c in zip(P.xg_h, P.xg_a, P.gd)]
    R[(kn, rel)] = (lab, P)
base = R[(20, 0)][1].set_index('mid')
print('ΧΑΡΑΚΑΣ ΛΙΓΚΑΣ & ΕΠΙΠΕΔΟ — μεροληψια συνολου (μοντελο − πραγματικα γκολ, − = το μοντελο βγαζει λιγοτερα) · Δ λαθους² vs σημερινο (− = καλυτερο) · Δ 1Χ2 RPS ×1000 (− = καλυτερο)')
for win in ('1-6', '7-14', '15+', '7+'):
    print(f"\n=== αγωνιστικες {win}")
    for (kn, rel), (lab, P) in R.items():
        Z = P[P.win.isin(['7-14', '15+'])] if win == '7+' else P[P.win == win]
        B = base.loc[Z.mid]
        cells = []; better = 0; nh = 0
        for sea in ('2223', '2324', '2425', '2526', '2627'):
            z = Z[Z.season == sea]; b = B[B.season == sea]
            if not len(z): continue
            dmse = (z.err ** 2).mean() - (b.err ** 2).mean(); drps = 1000 * (z.rps.mean() - b.rps.mean())
            if sea != '2627':
                nh += 1; better += dmse < 0
            cells.append(f"{sea[2:]}: μερ {z.err.mean():+.2f} Δλ² {dmse:+.3f} Δ1Χ2 {drps:+.2f}")
        hz = Z[Z.season != '2627']; hb = B[B.season != '2627']
        print(f"   {lab:38s} │ ιστορικα: μεροληψια {hz.err.mean():+.3f} · Δλ² {(hz.err ** 2).mean() - (hb.err ** 2).mean():+.4f} "
              f"({better}/{nh} σεζον καλυτερο) · Δ1Χ2 {1000 * (hz.rps.mean() - hb.rps.mean()):+.2f} │ " + ' · '.join(cells))
