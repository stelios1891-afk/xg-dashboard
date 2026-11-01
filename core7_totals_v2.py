"""
core7_totals_v2.py — ΤΕΣΤ 1/10/2026 (Στελιος: «αλλαξε αρκετα το μοντελο και ειναι πιο ακριβες — να ξαναδουμε και συνολο γκολ»).
ΣΥΝΟΛΑ ΓΚΟΛ εγχωριων CORE7, 2223-2526, αγων. 7+ (md≥6). ΠΑΛΙΑ μηχανη (αρχειο Β, παλιο SoS 1.5) vs ΝΕΑ (live: σωστο SoS 0.75).
Κατανομη συνολου = πινακας σκορ Dixon-Coles (score_matrix_dom, ιδιος με τα AH). Σωστα τεταρτα (2.75 = μισο 2.5 / μισο 3).
ΑΓΟΡΕΣ (κλεισιμο): Pinnacle γραμμη 2.5 (football-data PC>2.5/PC<2.5) · Crown & Bet365 πραγματικη γραμμη (Nowgoal, τελευταια pre-KO).
ΚΑΝΟΝΑΣ: over ή under, τιμη 1.70-2.10, edge ≥ κατωφλι (κουρεμα 3%)· κατωφλια 5 / 7.5 / 10%.
ΑΚΡΙΒΕΙΑ: Brier P(over 2.5) μοντελου vs Pinnacle (χωρις γκανιοτα) — ανα σεζον.
ΠΡΟ-ΔΗΛΩΣΗ: κελι (μηχανη ΝΕΑ × πλευρα × κατωφλι) ΥΠΟΨΗΦΙΟ αν στις 15+: ROI > 0 σε ΚΑΙ ΤΑ 3 βιβλια, θετικο ≥3/4 σεζον (Crown),
  n ≥ 40 (Crown). ~6 κελια → ο,τι περασει = σκια. Δεν αλλαζει τιποτα live.
"""
import sys, io, os, json, glob, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_anchor_test.py', encoding='utf-8').read()
pre = src[:src.index('res = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'tot'}
with contextlib.redirect_stdout(_Q()):
    exec(pre, g)
D, picks, ns, reg, resolvers = g['D'], g['picks'], g['ns'], g['reg'], g['resolvers']
D['win'] = np.where(D.md >= 14, '15+', '7-14')
key = ['league', 'season', 'h', 'a', 'date']
def load(v):
    P = pd.read_csv(f'core7_mech_preds_{v}.csv', dtype={'season': str, 'mid': str}); P['date'] = pd.to_datetime(P.date)
    m = D[key].merge(P[['league', 'season', 'home_name', 'away_name', 'date', 'xg_h', 'xg_a', 'mid']],
                     left_on=key, right_on=['league', 'season', 'home_name', 'away_name', 'date'], how='left')
    assert len(m) == len(D) and m.xg_h.notna().mean() > .99
    return m.xg_h.clip(.05, 6).values, m.xg_a.clip(.05, 6).values, m.mid.values
ENG = {'ΠΑΛΙΑ': load('base'), 'ΝΕΑ': load('cur_0.75_6_13')}
D['mid'] = ENG['ΝΕΑ'][2]
# Pinnacle 2.5 + τελικο σκορ απο football-data
FULL = {}                                   # odds_full/{lg}_{sea}_fd.csv (2425/2526: PC>2.5 & FTHG) ανα (lg, sea, home_fd, away_fd)
for f in glob.glob('odds_full/*_fd.csv'):
    lg_, sea_ = os.path.basename(f)[:-7].rsplit('_', 1)
    try: X = pd.read_csv(f)
    except Exception: continue
    for x in X.to_dict('records'): FULL[(lg_, sea_, x.get('HomeTeam'), x.get('AwayTeam'))] = x
pin, tg_fd = [], []
for r in D.itertuples():
    gg = ns['reg_of'](r.season); hn, an = resolvers[gg](r.h), resolvers[gg](r.a)
    o = picks.match_odds(reg[gg]['Om'], r.season, hn, an, r.date)
    o = {} if o is None else o
    x = FULL.get((r.league, r.season, hn, an)) or {}
    def num(k):
        for src_ in (o, x):
            try:
                v = float(src_.get(k))
                if v == v: return v
            except Exception: pass
        return np.nan
    po_, pu_ = num('PC>2.5'), num('PC<2.5')
    pin.append((2.5, po_, pu_) if (po_ > 1 and pu_ > 1) else (2.5, np.nan, np.nan))
    tg_fd.append(num('FTHG') + num('FTAG'))
# τελικο σκορ απο FotMob (load_matches, ανα mid) — το football-data δεν εχει FTHG για 2425/2526 στο reg
_M, _ = picks.load_matches(sorted(D.league.unique()), sorted(D.season.unique()))
_TG = {str(k): v for k, v in zip(_M.mid, _M.hg + _M.ag)}
D['tg'] = [t if t == t else _TG.get(str(m), np.nan) for t, m in zip(tg_fd, D.mid)]
def parse_line(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]
        return sum(p) / len(p)
    except Exception:
        return None
NG = {}
for f in glob.glob('nowgoal_odds/*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get('cid') not in (3, 8) or not r.get('ou'): continue
        best = None
        for mt, ov, gl, un in r['ou']:
            L = parse_line(gl)
            try: oo, uu = float(ov) + 1, float(un) + 1
            except (TypeError, ValueError): continue
            if L is None or mt is None or oo <= 1 or uu <= 1: continue
            if best is None or mt > best[0]: best = (mt, L, oo, uu)
        if best: NG[(str(r['mid']), 'Crown' if r['cid'] == 3 else 'Bet365')] = best[1:]
def tdist(h, a):
    M = picks.score_matrix_dom(h, a); d = {}
    for i in range(13):
        for j in range(13): d[i + j] = d.get(i + j, 0) + M[i, j]
    return d
def p_ou(d, L, over):
    """(p_win, p_push) για over/under στη γραμμη L (μισες/ακεραιες)."""
    pw = sum(v for k, v in d.items() if (k > L + 0.01 if over else k < L - 0.01)); pp = sum(v for k, v in d.items() if abs(k - L) < 0.01)
    return pw, pp
def edge(d, L, over, o):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; e = 0
    for x in parts:
        pw, pp = p_ou(d, x, over); e += (pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)) / len(parts)
    return e
def settle(t, L, over, o):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; s = 0
    for x in parts:
        m = (t - x) if over else (x - t)
        s += ((o - 1) if m > 0.01 else (0 if abs(m) < 0.01 else -1)) / len(parts)
    return s
rows, brier = [], []
for i, r in enumerate(D.itertuples()):
    if r.tg != r.tg: continue
    quotes = [('Pinnacle', pin[i])] + [(bk, NG.get((r.mid, bk))) for bk in ('Crown', 'Bet365')]
    for en, (XH, XA, _) in ENG.items():
        d = tdist(XH[i], XA[i])
        if pin[i][1] == pin[i][1]:
            po = sum(v for k, v in d.items() if k > 2.5); io_ = 1 / pin[i][1]; iu = 1 / pin[i][2]
            brier.append((en, r.season, r.win, (po - (r.tg > 2.5)) ** 2, (io_ / (io_ + iu) - (r.tg > 2.5)) ** 2))
        for bk, q in quotes:
            if q is None or q[1] != q[1]: continue
            L, oo, uu = q
            for over, o in ((True, oo), (False, uu)):
                if not (1.70 <= o <= 2.10): continue
                rows.append(dict(eng=en, book=bk, season=r.season, win=r.win, side='OVER' if over else 'UNDER',
                                 edge=edge(d, L, over, o), pnl=settle(r.tg, L, over, o)))
B = pd.DataFrame(rows); BR = pd.DataFrame(brier, columns=['eng', 'season', 'win', 'bm', 'bk'])
SEAS = sorted(B.season.unique()); BK = ('Pinnacle', 'Crown', 'Bet365')
print('ΕΛΕΓΧΟΣ: B ανα σεζον', B.groupby(['season','book']).size().to_dict()); print('tg NaN ανα σεζον', D.groupby('season').tg.apply(lambda x: x.isna().sum()).to_dict()); print('Brier ανα σεζον', BR.groupby('season').size().to_dict())
print('ΑΚΡΙΒΕΙΑ — Brier P(over 2.5), μικροτερο = καλυτερο (Pinnacle χωρις γκανιοτα = αγορα)')
for en in ENG:
    x = BR[BR.eng == en]
    print(f'  {en:6s} μοντελο {x.bm.mean():.4f} · αγορα {x.bk.mean():.4f} · ' + ' '.join(f'{s}: {x[x.season == s].bm.mean():.4f}' for s in SEAS)
          + f' · 15+ {x[x.win == "15+"].bm.mean():.4f}')
def fm(x):
    if len(x) < 5: return f'n{len(x):4d}          —        '
    ps = x.groupby('season').pnl.mean()
    return f'n{len(x):4d} {100*x.pnl.mean():+6.1f}% {x.pnl.sum():+6.1f}u {int((ps > 0).sum())}/4'
passed = []
for win in ('15+', '7-14'):
    print(f'\n========== αγων. {win} — Pinnacle(2.5) | Crown | Bet365 ==========')
    for side in ('OVER', 'UNDER'):
        x = B[(B.win == win) & (B.side == side) & (B.eng == 'ΝΕΑ')]
        print(f' [{side}] ΤΥΦΛΑ: ' + ' | '.join(fm(x[x.book == bk]) for bk in BK))
        for th in (0.05, 0.075, 0.10):
            for en in ENG:
                y = B[(B.win == win) & (B.side == side) & (B.eng == en) & (B.edge >= th)]
                cells = [y[y.book == bk] for bk in BK]; tag = ''
                if win == '15+' and en == 'ΝΕΑ' and all(len(c) and c.pnl.mean() > 0 for c in cells) and len(cells[1]) >= 40 \
                        and int((cells[1].groupby('season').pnl.mean() > 0).sum()) >= 3:
                    tag = '  ← ΥΠΟΨΗΦΙΟ'; passed.append(f'{side} ≥{100*th:g}%')
                print(f'   ≥{100*th:4.1f}% {en:6s} ' + ' | '.join(fm(c) for c in cells) + tag)
print(f'\nΚΡΙΣΗ (15+, ΝΕΑ μηχανη): υποψηφια κελια: {passed or "ΚΑΝΕΝΑ"}')
