"""
southam_phase3.py — 5/10/2026 ΦΑΣΗ 3: ΜΟΝΤΕΛΟ × ΓΡΑΜΜΕΣ ΧΑΝΤΙΚΑΠ/ΣΥΝΟΛΩΝ (Nowgoal Crown+SBOBET) — Βραζιλια 2023-26, MLS 2021-26, κανονικη περιοδος.
(α) ΚΛΙΣΗ b ανα αγορα: (πραγματικο − αγορα) ~ b·(μοντελο − αγορα) — υπεροχη (χαντικαπ) & συνολο γκολ, στο ΑΝΟΙΓΜΑ και στο ΚΛΕΙΣΙΜΟ.
    Η «αγορα» = λ που αναπαραγουν γραμμη+τιμες χωρις γκανιοτα (χαντικαπ λυνει υπεροχη, συνολο λυνει γκολ, Dixon-Coles).
(β) ΠΡΟΒΛΕΠΕΙ ΤΗΝ ΚΙΝΗΣΗ; (κλεισιμο − ανοιγμα) ~ k·(μοντελο − ανοιγμα). k>0 = η αγορα κινειται προς εμας → αξια στο ανοιγμα.
(γ) PICKS με τους κανονες μας: dogs (+0.5 και πανω, παλια τεταρτα p_cover, edge≥10%) · φαβορι (≤−0.5, σωστα τεταρτα, edge≥10%)
    · OVER/UNDER (σωστα τεταρτα, edge≥8%) — ολα @1.70-2.10 — ανα παραθυρο (1-6 / 7-14 / 15+) × χρονο (ανοιγμα/24ω/κλεισιμο) × σεζον.
(δ) ζωνες edge (για να φανει αν το κερδος ακολουθει το edge).
Ενας αριθμος = μεσος Crown/SBOBET (* διαφωνουν >5). Τιποτα live.
"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks

P = pd.read_csv('southam_preds.csv', dtype={'mid': str, 'season': str})
L = pd.read_csv('southam_lines.csv', dtype={'mid': str, 'ng': str, 'season': str})
L = L[(L['sub'] == 'League') & L.mid.isin(set(P.mid))]
D = L.merge(P[['mid', 'lh_base', 'la_base', 'md', 'noprior', 'h_xg_act', 'a_xg_act', 'newc_h', 'newc_a']], on='mid')
D['per'] = np.where(D.md <= 6, '1-6', np.where(D.md <= 14, '7-14', '15+'))
D['gd'] = D.hg - D.ag; D['tg'] = D.hg + D.ag

# ---------- αγορα → (υπεροχη, συνολο) με πλεγμα ----------
TOT = np.round(np.arange(1.6, 4.61, 0.05), 3); SUP = np.round(np.arange(-3.0, 3.001, 0.025), 3)
AHL = np.round(np.arange(-3.5, 3.51, 0.25), 2); OUL = np.round(np.arange(1.0, 5.01, 0.25), 2)
def parts(x): return [x] if (x * 4) % 2 == 0 else [x - .25, x + .25]
print('πλεγμα...', flush=True)
PA = np.zeros((len(TOT), len(SUP), len(AHL))); PO = np.zeros((len(TOT), len(SUP), len(OUL)))
for i, t in enumerate(TOT):
    for j, s in enumerate(SUP):
        lh, la = (t + s) / 2, (t - s) / 2
        if la < .05 or lh < .05: PA[i, j] = np.nan; PO[i, j] = np.nan; continue
        M = picks.score_matrix_dom(lh, la); gd = {}; tg = {}
        for a in range(13):
            for b in range(13):
                gd[a - b] = gd.get(a - b, 0) + M[a, b]; tg[a + b] = tg.get(a + b, 0) + M[a, b]
        for k, ln in enumerate(AHL):                   # «δικαιη» πιθανοτητα γηπεδουχου = W/(W+L) με σωστα τεταρτα
            W = Lo = 0
            for x in parts(ln):
                W += sum(p for g, p in gd.items() if g + x > .01); Lo += sum(p for g, p in gd.items() if g + x < -.01)
            PA[i, j, k] = W / (W + Lo)
        for k, ln in enumerate(OUL):
            W = Lo = 0
            for x in parts(ln):
                W += sum(p for g, p in tg.items() if g - x > .01); Lo += sum(p for g, p in tg.items() if g - x < -.01)
            PO[i, j, k] = W / (W + Lo)
def mkt(ah, oh, oa, ou, ov, un):
    ph = (1 / oh) / (1 / oh + 1 / oa); ka = int(np.argmin(abs(AHL - ah)))
    if pd.isna(ou): po, ko = None, None
    else: po = (1 / ov) / (1 / ov + 1 / un); ko = int(np.argmin(abs(OUL - ou)))
    ti = int(np.argmin(abs(TOT - (ou + 0.1 if pd.notna(ou) else 2.7))))
    for _ in range(3):
        sj = int(np.nanargmin(abs(PA[ti, :, ka] - ph)))
        if po is None: break
        ti = int(np.nanargmin(abs(PO[:, sj, ko] - po)))
    return SUP[sj], TOT[ti]
R = np.array([mkt(*v) for v in D[['ah', 'oh', 'oa', 'ou', 'ov', 'un']].values])
D['msup'], D['mtot'] = R[:, 0], R[:, 1]
D['sup'] = D.lh_base - D.la_base; D['tot'] = D.lh_base + D.la_base
D.to_csv('southam_phase3_rows.csv', index=False)

def bfit(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float); k = np.isfinite(x) & np.isfinite(y); x, y = x[k], y[k]
    X = np.c_[np.ones(len(x)), x]; c, *_ = np.linalg.lstsq(X, y, rcond=None); r = y - X @ c
    return c[1], np.sqrt((r ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
print('\n(α) ΚΛΙΣΗ b (πραγματικο − αγορα) ~ b·(μοντελο − αγορα) · ±SE · (σε xG: ιδιο με πραγματικο xG) · Crown')
for lg in ('Brazil', 'MLS'):
    for per in ('7-14', '15+'):
        for w in ('open', 'close'):
            d = D[(D.league == lg) & (D.per == per) & (D.win == w) & (D.book == 'Crown')]
            b1, s1 = bfit(d.sup - d.msup, d.gd - d.msup); b2, s2 = bfit(d.sup - d.msup, d.h_xg_act - d.a_xg_act - d.msup)
            b3, s3 = bfit(d.tot - d.mtot, d.tg - d.mtot); b4, s4 = bfit(d.tot - d.mtot, d.h_xg_act + d.a_xg_act - d.mtot)
            ps = ' '.join(f'{s}:{bfit(g.sup - g.msup, g.gd - g.msup)[0]:+.2f}' for s, g in d.groupby('season'))
            pt = ' '.join(f'{s}:{bfit(g.tot - g.mtot, g.tg - g.mtot)[0]:+.2f}' for s, g in d.groupby('season'))
            print(f'  {lg:6s} {per:5s} {w:5s} n{len(d):4d} | ΥΠΕΡΟΧΗ γκολ b={b1:+.2f}±{s1:.2f} xG b={b2:+.2f}±{s2:.2f} [{ps}]'
                  f' | ΣΥΝΟΛΟ γκολ b={b3:+.2f}±{s3:.2f} xG b={b4:+.2f}±{s4:.2f} [{pt}] | μεσο μοντ−αγορα συνολο {(d.tot-d.mtot).mean():+.2f}')

print('\n(β) ΚΙΝΗΣΗ ΓΡΑΜΜΗΣ: (κλεισιμο − ανοιγμα) ~ k·(μοντελο − ανοιγμα) · Crown · k>0 = η αγορα ερχεται προς εμας')
W = D[D.book == 'Crown'].pivot_table(index='mid', columns='win', values=['msup', 'mtot'], aggfunc='first')
W.columns = [f'{a}_{b}' for a, b in W.columns]
W = W.reset_index().merge(D[D.book == 'Crown'].drop_duplicates('mid')[['mid', 'league', 'season', 'per', 'sup', 'tot']], on='mid')
for lg in ('Brazil', 'MLS'):
    for per in ('7-14', '15+'):
        d = W[(W.league == lg) & (W.per == per)].dropna(subset=['msup_open', 'msup_close'])
        k1, s1 = bfit(d.sup - d.msup_open, d.msup_close - d.msup_open); k2, s2 = bfit(d.tot - d.mtot_open, d.mtot_close - d.mtot_open)
        print(f'  {lg:6s} {per:5s} n{len(d):4d} · υπεροχη k={k1:+.3f}±{s1:.3f} · συνολο k={k2:+.3f}±{s2:.3f} · μεση |κινηση| υπεροχης {(d.msup_close-d.msup_open).abs().mean():.3f}'
              f' · ανα σεζον υπεροχη ' + ' '.join(f'{s}:{bfit(g.sup-g.msup_open, g.msup_close-g.msup_open)[0]:+.2f}' for s, g in d.groupby('season')))

# ---------- (γ) PICKS ----------
def ou_edge(lh, la, line, odds, over):
    M = picks.score_matrix_dom(max(lh, .05), max(la, .05)); tg = {}
    for a in range(13):
        for b in range(13): tg[a + b] = tg.get(a + b, 0) + M[a, b]
    e = 0
    for x in parts(line):
        w = sum(p for g, p in tg.items() if (g - x > .01 if over else x - g > .01)); q = sum(p for g, p in tg.items() if abs(g - x) < .01)
        e += (w * (odds - 1) * (1 - picks.MARGIN) - (1 - w - q)) / len(parts(line))
    return e
def settle_ou(tg, line, odds, over):
    s = 0
    for x in parts(line):
        m = (tg - x) if over else (x - tg); s += ((odds - 1) if m > .01 else (0 if abs(m) < .01 else -1)) / len(parts(line))
    return s
BETS = []
for r in D[D.win.isin(['open', '24h', 'close'])].itertuples():
    base = dict(mid=r.mid, league=r.league, season=r.season, book=r.book, win=r.win, per=r.per, noprior=r.noprior)
    for b in picks.evaluate_bet(r.lh_base, r.la_base, r.ah, r.oh, r.oa):
        BETS.append(dict(base, kind='DOG', edge=b['edge'], odds=b['odds'], line=b['hcap'], home=b['side'] == 1, pnl=picks.settle(r.gd, b['side'], b['hcap'], b['odds'])))
    for b in picks.evaluate_fav(r.lh_base, r.la_base, r.ah, r.oh, r.oa):
        BETS.append(dict(base, kind='FAV', edge=b['edge'], odds=b['odds'], line=b['hcap'], home=b['side'] == 1, pnl=picks.settle(r.gd, b['side'], b['hcap'], b['odds'])))
    if pd.notna(r.ou):
        for over, o, nm in ((True, r.ov, 'OVER'), (False, r.un, 'UNDER')):
            if 1.70 <= o <= 2.10:
                e = ou_edge(r.lh_base, r.la_base, r.ou, o, over)
                if e >= 0.08:
                    BETS.append(dict(base, kind=nm, edge=e, odds=o, line=r.ou, home=None, pnl=settle_ou(r.tg, r.ou, o, over)))
BT = pd.DataFrame(BETS); BT.to_pickle('southam_phase3_bets.pkl')
def st(d):
    if len(d) < 16: return f'n{len(d)//2:4d}' + ' ' * 27
    a = [d[d.book == b].pnl.mean() for b in ('Crown', 'SBOBET')]
    ps = d.groupby('season').pnl.mean(); se = d.pnl.std() / np.sqrt(len(d) / 2)
    return f'n{len(d)//2:4d} {100*np.nanmean(a):+6.1f}%{"*" if abs(a[0]-a[1]) > .05 else " "}(±{100*se:4.1f}) {int((ps > 0).sum())}/{len(ps)}'
print('\n(γ) PICKS μοντελου — n = picks ανα βιβλιο (μεσος) · ROI μεσος Crown/SBOBET · σεζον θετικες')
for lg in ('Brazil', 'MLS'):
    print(f'\n  [{lg}]            ανοιγμα                            | 24ω                                | κλεισιμο')
    for kind in ('DOG', 'FAV', 'OVER', 'UNDER'):
        for per in ('1-6', '7-14', '15+'):
            x = BT[(BT.league == lg) & (BT.kind == kind) & (BT.per == per)]
            print(f'   {kind:5s} {per:5s} ' + ' | '.join(st(x[x.win == w]) for w in ('open', '24h', 'close')))
    x = BT[(BT.league == lg) & (BT.per == '15+') & (BT.win == 'close')]
    print('   ανα σεζον 15+ κλεισιμο: ' + ' · '.join(f'{k}: ' + ' '.join(f'{s}:{100*g.pnl.mean():+.0f}%' for s, g in x[x.kind == k].groupby('season')) for k in ('DOG', 'FAV', 'OVER', 'UNDER')))
print('\n(δ) ΖΩΝΕΣ EDGE (7+ αγων, κλεισιμο | ανοιγμα)')
for lg in ('Brazil', 'MLS'):
    for kind in ('DOG', 'FAV', 'OVER', 'UNDER'):
        s = []
        for lo, hi in ((.08, .10), (.10, .13), (.13, .18), (.18, 9)):
            x = BT[(BT.league == lg) & (BT.kind == kind) & (BT.per != '1-6') & (BT.edge >= lo) & (BT.edge < hi)]
            s.append(f'{int(lo*100)}-{int(hi*100) if hi < 9 else "∞"}%: {st(x[x.win == "close"]).strip()} | {st(x[x.win == "open"]).strip()}')
        print(f'  {lg:6s} {kind:5s} ' + '  ·  '.join(s))
