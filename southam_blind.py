"""
southam_blind.py — 5/10/2026 ΦΑΣΗ 2: ΤΥΦΛΕΣ ΤΣΕΠΕΣ ΤΗΣ ΑΓΟΡΑΣ (χαντικαπ & συνολα, Nowgoal Crown+SBOBET, 2021-2026, μονο κανονικη περιοδος).
Χωρις μοντελο: ποιες κατηγοριες στοιχηματων κερδιζουν/χανουν σταθερα; (ιδια μεθοδος με euro_favbias / pocket_screening)
 · χαντικαπ ανα ρολο (φαβορι/αουτσαιντερ) × εδρα × βαθος γραμμης · ζωνη τιμης 1.70-2.10 (οπως οι κανονες μας) ΚΑΙ ολες οι τιμες
 · ανα παραθυρο σεζον (1-6 / 7-14 / 15+) · ανα χρονο (ανοιγμα / 24ω / κλεισιμο)
 · συνολα: over/under ανα γραμμη · γκολ − γραμμη
 · κινηση γραμμης ανοιγμα→κλεισιμο: ακολουθω / αντιστρεφω (στο κλεισιμο)
Ενας αριθμος = μεσος Crown/SBOBET (* = διαφωνουν >5 μοναδες). σεζον = θετικες/συνολο (μεσος βιβλιων ανα σεζον).
"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks

L = pd.read_csv('southam_lines.csv', dtype={'ng': str, 'mid': str, 'season': str})
L = L[L['sub'] == 'League'].copy()
# αγωνιστικη: σειρα ματς της ομαδας στη σεζον
first = L.drop_duplicates('ng').sort_values('ko')
cnt = {}; md = {}
for r in first.itertuples():
    a = cnt.get((r.league, r.season, r.home), 0) + 1; b = cnt.get((r.league, r.season, r.away), 0) + 1
    cnt[(r.league, r.season, r.home)] = a; cnt[(r.league, r.season, r.away)] = b; md[r.ng] = max(a, b)
L['md'] = L.ng.map(md)
L['per'] = np.where(L.md <= 6, '1-6', np.where(L.md <= 14, '7-14', '15+'))
L['gd'] = L.hg - L.ag; L['tg'] = L.hg + L.ag

def settle_ou(tg, line, odds, over=True):
    parts = [line] if (line * 4) % 2 == 0 else [line - .25, line + .25]; s = 0
    for x in parts:
        m = (tg - x) if over else (x - tg)
        s += ((odds - 1) if m > .01 else (0 if abs(m) < .01 else -1)) / len(parts)
    return s

# μακρυς πινακας στοιχηματων: καθε ματς×βιβλιο×χρονος → 2 πλευρες AH + over + under
B = []
for r in L.itertuples():
    for side, ln, o in ((1, r.ah, r.oh), (-1, -r.ah, r.oa)):
        B.append(dict(ng=r.ng, league=r.league, season=r.season, book=r.book, win=r.win, per=r.per, mkt='AH',
                      home=side == 1, line=ln, odds=o, pnl=picks.settle(r.gd, side, ln, o)))
    if pd.notna(r.ou):
        B.append(dict(ng=r.ng, league=r.league, season=r.season, book=r.book, win=r.win, per=r.per, mkt='OVER',
                      home=None, line=r.ou, odds=r.ov, pnl=settle_ou(r.tg, r.ou, r.ov), res=r.tg - r.ou))
        B.append(dict(ng=r.ng, league=r.league, season=r.season, book=r.book, win=r.win, per=r.per, mkt='UNDER',
                      home=None, line=r.ou, odds=r.un, pnl=settle_ou(r.tg, r.ou, r.un, False)))
B = pd.DataFrame(B)
B.to_pickle('southam_blind_bets.pkl')

def st(d):
    if len(d) < 40: return f'n{len(d)//2:5d}' + ' ' * 26
    a = [d[d.book == b].pnl.mean() for b in ('Crown', 'SBOBET')]
    ps = d.groupby('season').pnl.mean(); se = d.pnl.std() / np.sqrt(len(d) / 2)
    flag = '*' if abs(a[0] - a[1]) > .05 else ' '
    return f'n{len(d)//2:5d} {100*np.nanmean(a):+6.1f}%{flag}(±{100*se:4.1f}) {int((ps > 0).sum())}/{len(ps)}'
Z = lambda d: d[(d.odds >= 1.70) & (d.odds <= 2.10)]
for lg in ('Brazil', 'MLS'):
    X = B[B.league == lg]
    print(f'\n===================== {lg} — τυφλα, κανονικη περιοδος 2021-2026 · n = ματς (μεσος 2 βιβλιων) =====================')
    print('\n ΧΑΝΤΙΚΑΠ ανα πλευρα & γραμμη — ΚΛΕΙΣΙΜΟ | ΑΝΟΙΓΜΑ   [ολες οι τιμες]   ||  ζωνη 1.70-2.10 κλεισιμο')
    for home in (True, False):
        for lo, hi, lab in ((-9, -1.25, '≤ −1.5'), (-1.25, -0.6, '−1/−1.25'), (-0.6, -0.4, '−0.5'), (-0.4, -0.1, '−0.25'),
                            (-0.1, 0.1, '0'), (0.1, 0.4, '+0.25'), (0.4, 0.6, '+0.5'), (0.6, 1.25, '+0.75/+1'), (1.25, 9, '≥ +1.25')):
            c = X[(X.mkt == 'AH') & (X.home == home) & (X.line > lo) & (X.line <= hi)]
            print(f'  {"ΓΗΠΕΔ" if home else "ΦΙΛΟΞ"} {lab:9s} {st(c[c.win == "close"])} | {st(c[c.win == "open"])} || {st(Z(c[c.win == "close"]))}')
    print('\n ΧΑΝΤΙΚΑΠ ανα παραθυρο σεζον (κλεισιμο, ολες οι τιμες): γηπεδουχος / φιλοξ· φαβορι (≤−0.5) / αουτσαιντερ (≥+0.5)')
    for per in ('1-6', '7-14', '15+'):
        c = X[(X.mkt == 'AH') & (X.win == 'close') & (X.per == per)]
        print(f'  {per:5s} γηπ {st(c[c.home == True])} · φιλοξ {st(c[c.home == False])} · φαβ {st(c[c.line <= -0.5])} · dog {st(c[c.line >= 0.5])}')
    print('\n ΧΡΟΝΟΣ (ολες οι τιμες): γηπεδουχος / φιλοξενουμενος / βαθια dogs ≥+1')
    for w in ('open', '72h', '24h', '3h', 'close'):
        c = X[(X.mkt == 'AH') & (X.win == w)]
        print(f'  {w:6s} γηπ {st(c[c.home == True])} · φιλοξ {st(c[c.home == False])} · dogs ≥+1 {st(c[c.line >= 1])}')
    print('\n ΣΥΝΟΛΑ ανα γραμμη (κλεισιμο | ανοιγμα): OVER · UNDER · γκολ − γραμμη')
    for lo, hi, lab in ((0, 2.3, '≤2.25'), (2.3, 2.6, '2.5'), (2.6, 2.9, '2.75'), (2.9, 3.1, '3'), (3.1, 9, '≥3.25')):
        for w in ('close', 'open'):
            o = X[(X.mkt == 'OVER') & (X.win == w) & (X.line > lo) & (X.line <= hi)]; u = X[(X.mkt == 'UNDER') & (X.win == w) & (X.line > lo) & (X.line <= hi)]
            print(f'  {lab:6s} {w:5s} OVER {st(o)} · UNDER {st(u)} · γκολ−γραμμη {o.res.mean():+.2f}')
    print('  ανα παραθυρο (κλεισιμο): ' + ' · '.join(f'{p}: OVER {st(X[(X.mkt == "OVER") & (X.win == "close") & (X.per == p)])}' for p in ('1-6', '7-14', '15+')))
    print('  ανα σεζον OVER κλεισιμο: ' + ' '.join(f'{s}:{100*g.pnl.mean():+.1f}%' for s, g in X[(X.mkt == 'OVER') & (X.win == 'close')].groupby('season')))

# ---- κινηση γραμμης ανοιγμα → κλεισιμο ----
print('\n===================== ΚΙΝΗΣΗ ΓΡΑΜΜΗΣ (ανοιγμα→κλεισιμο, ιδιο βιβλιο): παιζω ΣΤΟ ΚΛΕΙΣΙΜΟ την πλευρα που «πηρε» την κινηση / την αντιθετη =====================')
W = L.pivot_table(index=['ng', 'book'], columns='win', values=['ah', 'oh', 'oa', 'ou', 'ov', 'un'], aggfunc='first')
W.columns = [f'{a}_{b}' for a, b in W.columns]; W = W.reset_index().merge(L.drop_duplicates('ng')[['ng', 'league', 'season', 'gd', 'tg', 'per']], on='ng')
W = W.dropna(subset=['ah_open', 'ah_close'])
W['mv'] = W.ah_close - W.ah_open            # <0 = πηγε προς τον γηπεδουχο
rows = []
for r in W.itertuples():
    if r.mv == 0: continue
    side = 1 if r.mv < 0 else -1               # πλευρα που «αγοραστηκε»
    ln = r.ah_close if side == 1 else -r.ah_close; o = r.oh_close if side == 1 else r.oa_close
    lo = -r.ah_close if side == 1 else r.ah_close; oo = r.oa_close if side == 1 else r.oh_close
    rows.append(dict(league=r.league, season=r.season, book=r.book, size=abs(r.mv), home=side == 1,
                     follow=picks.settle(r.gd, side, ln, o), fade=picks.settle(r.gd, -side, lo, oo),
                     follow_open=picks.settle(r.gd, side, r.ah_open if side == 1 else -r.ah_open, r.oh_open if side == 1 else r.oa_open)))
V = pd.DataFrame(rows)
for lg in ('Brazil', 'MLS'):
    for sz, lab in ((0.25, 'κινηση 0.25'), (0.5, 'κινηση ≥0.5')):
        x = V[(V.league == lg) & ((V['size'] == 0.25) if sz == 0.25 else (V['size'] >= 0.5))]
        f = lambda c: f'{100*x[c].mean():+5.1f}% ({int((x.groupby("season")[c].mean() > 0).sum())}/{x.season.nunique()})'
        print(f'  {lg:6s} {lab:12s} n{len(x)//2:5d} · ακολουθω στο κλεισιμο {f("follow")} · αντιστρεφω στο κλεισιμο {f("fade")} · (ακολουθω ΣΤΟ ΑΝΟΙΓΜΑ {f("follow_open")} = CLV)')
W['tmv'] = W.ou_close - W.ou_open
for lg in ('Brazil', 'MLS'):
    x = W[(W.league == lg) & W.tmv.notna()]
    up = x[x.tmv > 0]; dn = x[x.tmv < 0]
    po = lambda d, ov: np.mean([settle_ou(t, l, o, ov) for t, l, o in zip(d.tg, d.ou_close, d.ov_close if ov else d.un_close)])
    print(f'  {lg:6s} συνολο ανεβηκε n{len(up)//2}: OVER στο κλεισιμο {100*po(up, True):+.1f}% · κατεβηκε n{len(dn)//2}: UNDER στο κλεισιμο {100*po(dn, False):+.1f}%')
