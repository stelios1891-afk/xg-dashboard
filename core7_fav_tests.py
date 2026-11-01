"""
core7_fav_tests.py — 28/9/2026 (Στελιος: «τρεξε ολα εκτος απο το 5»). ΤΕΣΤ ΦΑΒΟΡΙ στα εγχωρια (CORE7, 2223-2526, closing Pinnacle AH). ΜΟΝΟ τεστ.
Μοντελα φαβορι: A = σημερινη μηχανη + αγκυρα (λ=0.5) · D = χωρις συμπιεση + πεναλτι 0.76 + αγκυρα. DRAW_BOOST 1.13.
Picks φαβορι: γραμμη ≤ −0.5, 1.70-2.10, edge ≥10% (κουρεμα 3%). Παραθυρα: αγωνιστικες 7-14 / 15+.
 T2 ΣΩΣΤΑ ΤΕΤΑΡΤΑ μονο για φαβορι: παλιος τροπος (p_cover, −0.25 σαν −0.5) vs σωστος (μισο/μισο).
 T3 ΣΧΗΜΑ ΣΚΟΡ φαβορι: πολλαπλασιαστες ανα κατηγορια (ηττα/ισοπαλια/νικη 1/νικη 2/νικη 3+ απο τη σκοπια του φαβορι του μοντελου),
    LOSO (απο τις αλλες σεζον: πραγματικη συχνοτητα / προβλεπομενη), κανονικοποιηση → τιμολογηση φαβορι.
 T4 ΚΑΤΑΣΤΑΣΕΙΣ (στα picks φαβορι του D): αντιπαλος «καθεται πισω» (μεριδιο σουτ 10 τελευταιων <42%) · φαβορι με ευρωπαϊκο ≤4 μερες πριν ·
    νεκρα ματς τελους σεζον (καμια ζωνη τιτλου/UCL/Ευρωπης/υποβιβασμου δεν αλλαζει πια) · γηπεδουχο/φιλοξενουμενο φαβορι.
"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_mech_anchor.py', encoding='utf-8').read()
g = {'__name__': 'fav'}
with contextlib.redirect_stdout(_Q()):
    exec(src[:src.index('rows = []' + chr(10) + 'for v in VARS')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), g)
picks, ODDS, SM, anchored = g['picks'], g['ODDS'], g['SM'], g['anchored']
picks.DRAW_BOOST = 1.13

def load(v):
    P = pd.read_csv(f'core7_mech_preds_{v}.csv', dtype={'season': str}); P = P[P.gd.notna()].copy(); P['mid'] = P.mid.astype(str)
    P['date'] = pd.to_datetime(P.date); P['xh'] = P.xg_h.clip(.05, 6); P['xa'] = P.xg_a.clip(.05, 6)
    P['s0'] = P.xh - P.xa; P['T'] = P.xh + P.xa; P['s_mkt'] = P.mid.map(SM)
    return anchored(P)
MOD = {'A σημερα+αγκυρα': load('base'), 'D χωρις συμπ.+πεν.0.76+αγκυρα': load('both')}
SEAS = sorted(MOD['A σημερα+αγκυρα'].season.unique())

def parts(ud):
    return [ud] if (ud * 4) % 2 == 0 else [ud - 0.25, ud + 0.25]
def ev(dist, side, ud, odds, proper):
    ps = parts(ud) if proper else [ud]; e = 0.0
    for L in ps:
        pw, pp = picks.p_cover(dist, side, L); e += (pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp)) / len(ps)
    return e
def fav_bets(Q, proper=False, shape=None):
    out = []
    for r in Q[(Q.md >= 6) & Q.s_mkt.notna()].itertuples():
        L, ah, aa = ODDS[r.mid]; lh, la = max((r.T + r.s) / 2, .05), max((r.T - r.s) / 2, .05); dist = picks.gd_dist(lh, la)
        if shape is not None:
            mult = shape[r.season]; fs = 1 if r.s >= 0 else -1
            dist = {k: v * mult[min(max(fs * k, -1), 3)] for k, v in dist.items()}; z = sum(dist.values()); dist = {k: v / z for k, v in dist.items()}
        for side, ud, odds in ((1, L, ah), (-1, -L, aa)):
            if ud <= -0.5 and 1.70 <= odds <= 2.10 and ev(dist, side, ud, odds, proper) >= 0.10:
                out.append(dict(mid=r.mid, win='7-14' if r.md <= 13 else '15+', season=r.season, side=side, ud=ud,
                                pnl=picks.settle(r.gd, side, ud, odds), home=r.home, away=r.away, date=r.date, league=r.league))
    return pd.DataFrame(out)
def summ(B, lab):
    cells = []
    for win in ('7-14', '15+'):
        d = B[B.win == win] if len(B) else B
        if not len(d): cells.append(f'{win}: —'); continue
        ps = d.groupby('season').pnl.mean()
        cells.append(f'{win}: n{len(d)} {100*d.pnl.mean():+.1f}% (±{100*d.pnl.std()/np.sqrt(len(d)):.1f}) {d.pnl.sum():+.0f}u {int((ps > 0).sum())}/{len(ps)}')
    print(f'  {lab:44s} ' + ' · '.join(cells))

print('T2. ΣΩΣΤΑ ΤΕΤΑΡΤΑ ΜΟΝΟ ΓΙΑ ΦΑΒΟΡΙ')
BASE = {}
for k, Q in MOD.items():
    BASE[k] = fav_bets(Q); summ(BASE[k], f'{k} · παλιος τροπος (σημερα)')
    Bp = fav_bets(Q, proper=True); summ(Bp, f'{k} · ΣΩΣΤΑ τεταρτα')
    for lab, d in (('μονο γραμμες x.25/x.75', lambda b: b[(b.ud * 4) % 2 != 0]), ('ακεραιες/μισες', lambda b: b[(b.ud * 4) % 2 == 0])):
        summ(d(BASE[k]), f'     παλιος: {lab}'); summ(d(Bp), f'     σωστος: {lab}')

print('\nT3. ΣΧΗΜΑ ΣΚΟΡ ΦΑΒΟΡΙ (πολλαπλασιαστες LOSO: ηττα / Χ / +1 / +2 / +3+)')
for k, Q in MOD.items():
    Z = Q[Q.md >= 6]; pred = {}; act = {}
    for r in Z.itertuples():
        d = picks.gd_dist(max((r.T + r.s) / 2, .05), max((r.T - r.s) / 2, .05)); fs = 1 if r.s >= 0 else -1
        pp = {c: 0.0 for c in (-1, 0, 1, 2, 3)}
        for gd_, v in d.items(): pp[min(max(fs * gd_, -1), 3)] += v
        a = min(max(fs * r.gd, -1), 3)
        for c in pp: pred.setdefault(r.season, {}).setdefault(c, 0.0); pred[r.season][c] += pp[c]
        act.setdefault(r.season, {}).setdefault(a, 0); act[r.season][a] += 1
    shape = {}
    for s_ in SEAS:
        oth = [x for x in SEAS if x != s_]
        shape[s_] = {c: sum(act[x].get(c, 0) for x in oth) / sum(pred[x][c] for x in oth) for c in (-1, 0, 1, 2, 3)}
    allm = {c: sum(act[x].get(c, 0) for x in SEAS) / sum(pred[x][c] for x in SEAS) for c in (-1, 0, 1, 2, 3)}
    print(f'  {k}: πολλαπλασιαστες (ολο το δειγμα) ηττα {allm[-1]:.3f} · Χ {allm[0]:.3f} · +1 {allm[1]:.3f} · +2 {allm[2]:.3f} · +3+ {allm[3]:.3f}')
    summ(BASE[k], '     χωρις διορθωση σχηματος'); summ(fav_bets(Q, shape=shape), '     ΜΕ διορθωση σχηματος (LOSO)')

print('\nT4. ΚΑΤΑΣΤΑΣΕΙΣ (picks φαβορι, και τα 2 μοντελα)')
# μεριδιο σουτ (walk-forward, 10 τελευταια ματς) απο τα inputs
TG = pd.read_csv('teamgame_inputs_5s_wf.csv', dtype={'season': str}); TG['mid'] = TG.mid.astype(str); TG = TG.sort_values(['date', 'mid'])
share = {}; hist = {}
for mid, gm in TG.groupby('mid', sort=False):
    if len(gm) != 2: continue
    rs = gm.to_dict('records')
    for a, b in ((rs[0], rs[1]), (rs[1], rs[0])):
        h = hist.get(a['team'], [])[-10:]
        share[(mid, a['team'])] = np.mean(h) if len(h) >= 5 else np.nan
    for a, b in ((rs[0], rs[1]), (rs[1], rs[0])):
        hist.setdefault(a['team'], []).append(a['ns'] / max(a['ns'] + b['ns'], 1))
FL = pd.read_csv('europe_flags.csv'); FL['mid'] = FL.mid.astype(str); EU = {(m, t): d for m, t, d in zip(FL.mid, FL.team, FL.eu_prev_days)}
# νεκρα ματς: βαθμολογια πριν απο καθε ματς
ZONES = {'EPL': (4, 7, 3), 'LaLiga': (4, 7, 3), 'SerieA': (4, 7, 3), 'Bundesliga': (4, 7, 3), 'Ligue1': (3, 5, 3), 'Eredivisie': (2, 5, 3), 'PrimeiraLiga': (2, 5, 3)}
Pall = MOD['A σημερα+αγκυρα'].sort_values(['league', 'season', 'date']).reset_index(drop=True)
DEAD = {}
for (lg, sea), G in Pall.groupby(['league', 'season']):
    teams = sorted(set(G.home) | set(G.away)); n = len(teams); tot = 2 * (n - 1); pts = {t: 0 for t in teams}; pl = {t: 0 for t in teams}
    ucl, eur, rel = ZONES[lg]; bounds = [1, ucl, eur, n - rel]
    for r in G.itertuples():
        tab = sorted(teams, key=lambda t: -pts[t]); pos = {t: i + 1 for i, t in enumerate(tab)}
        def alive(t):
            p, rem = pts[t], tot - pl[t]
            if rem > 10: return True
            for k in bounds:
                above = pos[t] <= k
                if above:
                    nxt = tab[k] if k < n else None
                    if nxt is not None and pts[nxt] + 3 * (tot - pl[nxt]) >= p: return True
                else:
                    if p + 3 * rem >= pts[tab[k - 1]]: return True
            return False
        DEAD[r.mid] = (not alive(r.home), not alive(r.away))
        pts[r.home] += 3 if r.gd > 0 else (1 if r.gd == 0 else 0); pts[r.away] += 3 if r.gd < 0 else (1 if r.gd == 0 else 0); pl[r.home] += 1; pl[r.away] += 1
TEAMID = dict(zip(Pall.mid, zip(Pall.home, Pall.away)))
for k in MOD:
    B = BASE[k].copy()
    if not len(B): continue
    B['fav_team'] = [TEAMID[m][0] if s == 1 else TEAMID[m][1] for m, s in zip(B.mid, B.side)]
    B['opp_team'] = [TEAMID[m][1] if s == 1 else TEAMID[m][0] for m, s in zip(B.mid, B.side)]
    # τα ids του Pall ειναι team ids (home/away) — ιδια με TG.team
    B['opp_share'] = [share.get((m, t), np.nan) for m, t in zip(B.mid, B.opp_team)]
    B['fav_eu'] = [EU.get((m, t), np.nan) for m, t in zip(B.mid, B.fav_team)]
    dd = [DEAD.get(m, (False, False)) for m in B.mid]
    B['fav_dead'] = [d[0] if s == 1 else d[1] for d, s in zip(dd, B.side)]; B['opp_dead'] = [d[1] if s == 1 else d[0] for d, s in zip(dd, B.side)]
    print(f'  [{k}]')
    for lab, m in (('αντιπαλος καθεται πισω (<42% σουτ)', B.opp_share < 0.42), ('αντιπαλος ΟΧΙ πισω', B.opp_share >= 0.42),
                   ('φαβορι με ευρωπαϊκο ≤4 μερες', B.fav_eu <= 4), ('φαβορι χωρις ευρωπαϊκο πριν', ~(B.fav_eu <= 4)),
                   ('νεκρος ο ΑΝΤΙΠΑΛΟΣ', B.opp_dead & ~B.fav_dead), ('νεκρο το ΦΑΒΟΡΙ', B.fav_dead & ~B.opp_dead), ('ΚΑΙ ΟΙ ΔΥΟ νεκροι', B.fav_dead & B.opp_dead),
                   ('κανενας νεκρος', ~B.fav_dead & ~B.opp_dead), ('γηπεδουχο φαβορι', B.side == 1), ('φιλοξενουμενο φαβορι', B.side == -1)):
        summ(B[m.fillna(False).values], '    ' + lab)
