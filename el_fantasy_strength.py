# -*- coding: utf-8 -*-
"""el_fantasy_strength.py — ΔΥΝΑΜΗ ΟΜΑΔΑΣ απο τις τιμες EuroLeague Fantasy 2026-27 (25/9/2026, ερωτημα Στελιου).
ΠΡΟΣΟΧΗ: τιμες μονο φετος → ΚΑΝΕΝΑ ιστορικο τεστ. Μονο συγκριση με ειδικους / μοντελο / αγορα.
Δυναμη = Σ (τιμη παικτη − μεση τιμη) × «τυπικο μεριδιο λεπτων της θεσης του στην ομαδα» (1ος ακριβοτερος = οσο παιζει
  ιστορικα ο 1ος σε λεπτα παικτης μιας ομαδας Ευρωλιγκας, κτλ· απο el_players 2019-26).
Μετατροπη σε rating: με το ιδιο «ποσοστημοριο → rating» που χρησιμοποιησαμε για τους ειδικους (ιστορικη κατανομη ratings ομαδων).
Εξοδος: el_fantasy_strength_out.txt"""
import sys, json, re, unicodedata, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, 'dashboard'); sys.path.insert(0, '.')
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
F = pd.read_excel('el_fantasy_prices_2026.xlsx')
CLUB = {'Olympiacos': 'OLY', 'Panathinaikos': 'PAN', 'Fenerbahce': 'ULK', 'Real Madrid': 'MAD', 'Dubai': 'DUB', 'Hapoel Tel Aviv': 'HTA',
        'Zalgiris': 'ZAL', 'Anadolu Efes': 'IST', 'Crvena Zvezda': 'RED', 'Milano': 'MIL', 'Valencia': 'PAM', 'Barcelona': 'BAR',
        'Maccabi Tel Aviv': 'TEL', 'Partizan': 'PAR', 'Bayern Munich': 'MUN', 'Paris': 'PRS', 'Besiktas': 'BES', 'Baskonia': 'BAS',
        'Virtus Bologna': 'VIR', 'ASVEL': 'ASV'}
F['code'] = F.Club.map(CLUB)
assert F.code.notna().all(), F[F.code.isna()].Club.unique()
# τυπικο μεριδιο λεπτων ανα θεση (1ος, 2ος, … σε λεπτα) — Ευρωλιγκα 2019-26
PL = json.load(open('el_players.json', encoding='utf-8'))
tm = {}
for k, g in PL.items():
    if g.get('comp') != 'E' or 'err' in g or 'ph' not in g or g['season'] < 'E2019': continue
    for side, tc in (('ph', g['hcode']), ('pa', g['acode'])):
        for p in g[side]:
            if p[3]: tm.setdefault((g['season'], tc), {}); tm[(g['season'], tc)][p[0]] = tm[(g['season'], tc)].get(p[0], 0) + p[3]
shares = []
for d in tm.values():
    v = np.sort(np.array(list(d.values())))[::-1]; shares.append(np.pad(v / v.sum(), (0, 25))[:18])
W = np.mean(shares, axis=0)
P('τυπικο μεριδιο λεπτων ανα θεση (1ος…10ος): ' + ' '.join(f'{x*100:.0f}%' for x in W[:10]))
mu = F.Price.mean()
st = {}
for c, g in F.groupby('code'):
    p = np.sort(g.Price.values)[::-1]
    st[c] = float(np.sum((np.pad(p, (0, 18))[:18] - mu) * W))
S = pd.Series(st).sort_values(ascending=False)
# ποσοστημοριο → rating: ιστορικη κατανομη ratings ομαδων (οπως στους ειδικους) απο el_projections/ratings v1 τελους σεζον
src = open('el_player_value2b.py', encoding='utf-8').read().split('rows = []')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
g_ = {}; exec(src, g_)
ENDS = [np.sort(np.array(list(g_['team_end'](s).values())))[::-1] for s in g_['SEAS'] if s >= 'E2018']
def q2r(q): return float(np.mean([np.interp(q, (np.arange(len(e)) + .5) / len(e), e) for e in ENDS]))
FR = {c: q2r((i + 0.5) / len(S)) for i, c in enumerate(S.index)}
BN = dict(OLY=1, PAN=2, ULK=3, MAD=4, DUB=5, HTA=6, ZAL=7, IST=8, RED=9, MIL=10, PAM=11, BAR=12, TEL=13, PAR=14, MUN=15, PRS=16, BES=17, BAS=18, VIR=19, ASV=20)
proj = json.load(open('el_projections.json', encoding='utf-8'))
v1 = {r['code']: r['net'] for r in proj['ratings']}
import euroleague_view as ev
d = ev.load_all()
# rating v1 ΠΡΙΝ την 1η αγωνιστικη (απο τις προβλεψεις «πριν το ματς» δεν βγαινει ανα ομαδα) → χρησιμοποιουμε τον τωρινο πινακα
P('')
P(f'{"":4s} {"ομαδα":24s} {"δυναμη fantasy":>14s} {"θεση":>5s} {"BasketNews":>10s} {"μοντελο v1 (θεση)":>18s}')
v1rank = {c: i + 1 for i, c in enumerate(sorted(v1, key=lambda c: -v1[c]))}
names = {r['code']: r['name'] for r in proj['ratings']}
for i, c in enumerate(S.index, 1):
    P(f'{i:3d}. {names.get(c, c)[:24]:24s} {S[c]:+14.2f} {i:5d} {BN[c]:10d} {v1rank.get(c, 0):18d}')
def spearmanr(a, b):
    class R: pass
    r = R(); r.correlation = float(np.corrcoef(pd.Series(list(a)).rank(), pd.Series(list(b)).rank())[0, 1]); return r
P('')
P(f'συμφωνια καταταξεων (Spearman): fantasy–ειδικοι {spearmanr([BN[c] for c in S.index], range(1, 21)).correlation:.2f} · '
  f'fantasy–μοντελο {spearmanr([v1rank[c] for c in S.index], range(1, 21)).correlation:.2f} · ειδικοι–μοντελο {spearmanr([BN[c] for c in S.index], [v1rank[c] for c in S.index]).correlation:.2f}')
# ματς με τιμη αγορας: γραμμη fantasy vs αγορα vs v1
EXR = {c: q2r((BN[c] - 0.5) / 20) for c in BN}
P('')
P('ΜΑΤΣ ΜΕ ΤΙΜΗ PINNACLE — γραμμη γηπεδουχου (εδρα 4.4 π., κατοχες 72): fantasy / ειδικοι / μοντελο v1 / αγορα / τελικο')
rows = []
for gm in proj['games']:
    mk = ev.market_for(gm, d) or {}
    if mk.get('line') is None: continue
    hb = 0 if gm['neutral'] else 4.4
    lf = -(hb + 0.72 * (FR[gm['hcode']] - FR[gm['acode']])); le = -(hb + 0.72 * (EXR[gm['hcode']] - EXR[gm['acode']]))
    res = f"{gm['hs']}-{gm['as_']}" if gm.get('hs') is not None else '—'
    rows.append((lf, le, -gm['margin'], mk['line'], gm.get('hs'), gm.get('as_')))
    P(f"  {gm['home'][:18]:18s}-{gm['away'][:18]:18s} fantasy {lf:+6.1f} · ειδικοι {le:+6.1f} · v1 {-gm['margin']:+6.1f} · αγορα {mk['line']:+6.1f} · {res}")
R = np.array([r[:4] for r in rows], float)
P(f'  μεση |διαφορα απο αγορα|: fantasy {np.mean(np.abs(R[:,0]-R[:,3])):.1f} · ειδικοι {np.mean(np.abs(R[:,1]-R[:,3])):.1f} · v1 {np.mean(np.abs(R[:,2]-R[:,3])):.1f}  ({len(R)} ματς)')
open('el_fantasy_strength_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
