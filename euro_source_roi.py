"""
euro_source_roi.py — 9/10/2026 (Στελιος): (1) ΟΛΕΣ οι ομαδες του φετινου UEL και ΑΠΟ ΠΟΥ ερχεται το rating τους (euro_projections.json)·
(2) ΙΣΤΟΡΙΚΑ (2223-2526, σημερινη ευρωπαικη αλυσιδα) ROI ανα ΠΗΓΗ rating × αγορα (φαβορι εντος/εκτος, αουτσαιντερ εντος/εκτος).
Πηγες: FotMob (xG σουτ) · Opta/Ben (Griffis xG) · γκολ (+Elo οπου λειπει xG). Picks με τους σημερινους κανονες ΧΩΡΙΣ τον φραχτη «μονο FotMob»
(για να φανει τι θα εκανε καθε πηγη), κλεισιμο, μεσος Crown/SBOBET, 1.70-2.10. Και ΤΥΦΛΑ στις ιδιες ομαδες για συγκριση.
"""
import sys, io, json, pickle, contextlib, collections
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
# ---- (1) φετινο UEL ----
P = json.load(open('euro_projections.json', encoding='utf-8'))['matches']
T = {}
for m in P:
    if m.get('comp') != 'EuropaLeague': continue
    for side in ('h', 'a'):
        t = m['home' if side == 'h' else 'away']; T.setdefault(t, collections.Counter())[(m.get(f'src_{side}'), m.get(f'lg_{side}'))] += 1
print(f'(1) ΦΕΤΙΝΟ EUROPA LEAGUE — {len(T)} ομαδες · πηγη rating (απο τα projections)')
SRCN = collections.Counter()
rows = []
for t, c in T.items():
    (src, lg), _ = c.most_common(1)[0]; rows.append((src or '—', lg or '—', t)); SRCN[src or '—'] += 1
for src, lg, t in sorted(rows): print(f'   {src:10s} {lg:26s} {t}')
print('   ΣΥΝΟΛΟ ανα πηγη: ' + ' · '.join(f'{k}: {v}' for k, v in SRCN.most_common()))
# ---- (2) ιστορικα ----
src = open('uel_battery.py', encoding='utf-8').read(); src = src[:src.index('P0 = make_picks')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'esr'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
MIDS, GD, SEA, COMP, SNAP, SB, LH_N, LA_N, sdist, cover_q, edge, picks = (g[k] for k in (
    'MIDS', 'GD', 'SEA', 'COMP', 'SNAP', 'SB', 'LH_N', 'LA_N', 'sdist', 'cover_q', 'edge', 'picks'))
V = pickle.load(open('euro_v6_preds.pkl', 'rb')); assert list(V['mids']) == list(MIDS)
NAME = {'shots': 'FotMob', 'griffis': 'Opta/Ben', 'goals': 'γκολ/Elo'}
SH = [NAME.get(s, s) for s in V['src_h']]; SA = [NAME.get(s, s) for s in V['src_a']]
R = []
for i, mid in enumerate(MIDS):
    dist = None
    for bk, sn in (('Crown', SNAP.get(mid)), ('SBOBET', SB.get(mid))):
        if not sn: continue
        if dist is None: dist = sdist(LH_N[i], LA_N[i])
        L, oh, oa = sn; c = COMP[i]
        for side, ln, o in ((1, L, oh), (-1, -L, oa)):
            if not (1.70 <= o <= 2.10) or abs(ln) < 0.5: continue
            role = 'fav' if ln < 0 else 'dog'
            pw, pp = cover_q(dist, side, ln) if role == 'fav' else picks.p_cover(dist, side, ln)
            e = edge(pw, pp, o)
            thr = (0.10 if role == 'fav' else 0.04) if c == 'ChampionsLeague' else (0.04 if role == 'fav' else 0.10)
            R.append(dict(comp=c, sea=SEA[i], book=bk, role=role, home=side == 1, pick=e >= thr,
                          src_me=SH[i] if side == 1 else SA[i], src_opp=SA[i] if side == 1 else SH[i], pnl=picks.settle(GD[i], side, ln, o)))
R = pd.DataFrame(R)
MK = [('fav', True, 'φαβ εντος'), ('fav', False, 'φαβ εκτος'), ('dog', True, 'αουτ εντος'), ('dog', False, 'αουτ εκτος')]
def cell(d):
    if len(d) < 6: return f'{"n" + str(round(len(d) / 2)):>5s}{"":>12s}'
    ps = d.groupby('sea').pnl.mean()
    return f'{"n" + str(round(len(d) / d.book.nunique())):>5s} {100 * d.pnl.mean():+6.1f}% {int((ps > 0).sum())}/{ps.size}'
def table(D, key, title):
    print(f'\n   {title}')
    print(f'   {"πηγη":12s}' + ''.join(f'{lab:>24s}' for _, _, lab in MK))
    for s in ('FotMob', 'Opta/Ben', 'γκολ/Elo'):
        x = D[D[key] == s]
        print(f'   {s:12s}' + ''.join(f'{cell(x[(x.role == r) & (x.home == h)]):>24s}' for r, h, _ in MK))
for comp, lab in (('EuropaLeague', 'EUROPA LEAGUE'), ('ChampionsLeague', 'CHAMPIONS LEAGUE'), ('ConferenceLeague', 'CONFERENCE LEAGUE')):
    D = R[R.comp == comp]
    print(f'\n(2) {lab} 2223-2526 — κελι = picks · ROI · σεζον θετικες (μεσος Crown/SBOBET, κλεισιμο)')
    table(D[D.pick], 'src_me', 'PICKS ΜΟΝΤΕΛΟΥ — πηγη της ομαδας που ΠΟΝΤΑΡΟΥΜΕ')
    table(D[D.pick], 'src_opp', 'PICKS ΜΟΝΤΕΛΟΥ — πηγη του ΑΝΤΙΠΑΛΟΥ')
    table(D, 'src_me', 'ΤΥΦΛΑ (ολες οι πλευρες της ζωνης) — πηγη της ομαδας')
