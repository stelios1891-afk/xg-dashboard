"""
southam_totals_timing.py — 5/10/2026 ΦΑΣΗ 3β: ΣΥΝΟΛΑ (και υπεροχη) ΣΤΟ ΑΝΟΙΓΜΑ — «η αγορα ερχεται προς το μοντελο».
Ευρημα φασης 3: (κλεισιμο − ανοιγμα) ~ k·(μοντελο − ανοιγμα), k συνολου +0.25..+0.46 (t 10-20), υπεροχης +0.03..+0.12.
Κανονας (χωρις ματια στο μελλον):
  1) διορθωση προκαταληψης: μοντελο_adj = μοντελο + μεσος(κλεισιμο − μοντελο) των ΠΡΟΗΓΟΥΜΕΝΩΝ ματς ιδιας λιγκας (κυλιομενο, τελευταια 150)
  2) k απο τις ΑΛΛΕΣ σεζον (LOSO) · αναμενομενη κινηση = k·(μοντελο_adj − ανοιγμα)
  3) στοιχημα ΣΤΟ ΑΝΟΙΓΜΑ (ιδιο βιβλιο) προς την πλευρα της αναμενομενης κινησης, αν |κινηση| ≥ κατωφλι · τιμη 1.70-2.10
Μετρα: ROI στο ανοιγμα · CLV (πιθανοτητα κλεισιματος − ανοιγματος για την πλευρα μας, ιδια γραμμη) · ποσοστο που η γραμμη ηρθε προς εμας
· ανα σεζον x/N · ανα παραθυρο · ανα βιβλιο. Ελεγχος: ιδια στο 72ω/24ω (οσο πιο κοντα, τοσο λιγοτερο να μενει).
"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
D = pd.read_csv('southam_phase3_rows.csv', dtype={'mid': str, 'season': str})
D = D[D.per != '1-6'].copy()          # 1-6: μοντελο σχεδον περσινο — χωριστα στο τελος
def parts(x): return [x] if (x * 4) % 2 == 0 else [x - .25, x + .25]
def settle_ou(tg, line, odds, over):
    s = 0
    for x in parts(line):
        m = (tg - x) if over else (x - tg); s += ((odds - 1) if m > .01 else (0 if abs(m) < .01 else -1)) / len(parts(line))
    return s
def run(D, entry, mkt='tot', thr=0.10, per_filter=None, inc16=False):
    out = []
    for lg in ('Brazil', 'MLS'):
        for book in ('Crown', 'SBOBET'):
            X = D[(D.league == lg) & (D.book == book)]
            W = X.pivot_table(index='mid', columns='win', values=['m' + mkt, 'ou', 'ov', 'un', 'ah', 'oh', 'oa', 'ko'], aggfunc='first')
            W.columns = [f'{a}_{b}' for a, b in W.columns]
            meta = X.drop_duplicates('mid').set_index('mid')[['season', 'per', mkt, 'tg', 'gd']]
            W = W.join(meta).dropna(subset=[f'm{mkt}_{entry}', f'm{mkt}_close']).sort_values(f'ko_close')
            # 1) κυλιομενη διορθωση προκαταληψης (μονο προηγουμενα ματς)
            diff = (W[f'm{mkt}_close'] - W[mkt]).shift(1)
            W['bias'] = diff.rolling(150, min_periods=30).mean().fillna(0)
            W['adj'] = W[mkt] + W.bias
            # 2) k LOSO
            ks = {}
            for s in W.season.unique():
                o = W[W.season != s]; x = o.adj - o[f'm{mkt}_{entry}']; y = o[f'm{mkt}_close'] - o[f'm{mkt}_{entry}']
                ks[s] = float((x * y).sum() / (x * x).sum())
            W['exp'] = [ks[s] * (a - m) for s, a, m in zip(W.season, W.adj, W[f'm{mkt}_{entry}'])]
            for mid, r in W.iterrows():
                if abs(r.exp) < thr or (per_filter and r.per not in per_filter): continue
                if mkt == 'tot':
                    over = r.exp > 0; line = r[f'ou_{entry}']; o = r[f'ov_{entry}'] if over else r[f'un_{entry}']
                    if pd.isna(line) or not (1.70 <= o <= 2.10): continue
                    lc = r['ou_close']; oc = (r['ov_close'] if over else r['un_close']); oc2 = (r['un_close'] if over else r['ov_close'])
                    pnl = settle_ou(r.tg, line, o, over)
                    clv_line = (lc - line) * (1 if over else -1)        # +: η γραμμη πηγε υπερ μας
                    pc = (1 / oc) / (1 / oc + 1 / oc2); po = (1 / o) / (1 / o + 1 / (r[f'un_{entry}'] if over else r[f'ov_{entry}']))
                    side = 'OVER' if over else 'UNDER'
                else:
                    home = r.exp > 0; line = r[f'ah_{entry}'] if home else -r[f'ah_{entry}']; o = r[f'oh_{entry}'] if home else r[f'oa_{entry}']
                    if not (1.70 <= o <= 2.10): continue
                    import picks
                    pnl = picks.settle(r.gd, 1 if home else -1, line, o)
                    lc = r['ah_close'] if home else -r['ah_close']; clv_line = (line - lc) if False else (lc - line) * -1
                    clv_line = line - lc       # +: παιρνουμε περισσοτερα απο το κλεισιμο
                    oc = r['oh_close'] if home else r['oa_close']; oc2 = r['oa_close'] if home else r['oh_close']
                    pc = (1 / oc) / (1 / oc + 1 / oc2); po = (1 / o) / (1 / o + 1 / (r[f'oa_{entry}'] if home else r[f'oh_{entry}']))
                    side = 'HOME' if home else 'AWAY'
                out.append(dict(league=lg, book=book, season=r.season, per=r.per, side=side, exp=r.exp, pnl=pnl, clv_line=clv_line,
                                moved_our_way=clv_line > 0, moved_against=clv_line < 0, clv_p=(pc - po) if abs(clv_line) < 1e-9 else np.nan, k=ks[r.season]))
    return pd.DataFrame(out)
def st(d):
    if len(d) == 0 or 'book' not in d: return 'n   0'
    if len(d) < 16: return f'n{len(d)//2:4d}'
    a = [d[d.book == b].pnl.mean() for b in ('Crown', 'SBOBET')]; ps = d.groupby('season').pnl.mean()
    se = d.pnl.std() / np.sqrt(len(d) / 2)
    return (f'n{len(d)//2:4d} ROI {100*np.nanmean(a):+5.1f}%{"*" if abs(a[0]-a[1]) > .05 else " "}(±{100*se:3.1f}) {int((ps > 0).sum())}/{len(ps)}'
            f' · γραμμη υπερ μας {100*d.moved_our_way.mean():3.0f}% κοντρα {100*d.moved_against.mean():3.0f}%')
for mkt, lab in (('tot', 'ΣΥΝΟΛΑ'), ('sup', 'ΧΑΝΤΙΚΑΠ')):
    print(f'\n================ {lab} — στοιχημα στο ΑΝΟΙΓΜΑ οταν η αναμενομενη κινηση ≥ κατωφλι (αγων 7+) ================')
    for thr in ((0.05, 0.10, 0.15, 0.20) if mkt == 'tot' else (0.03, 0.06, 0.10)):
        R = run(D, 'open', mkt, thr)
        for lg in ('Brazil', 'MLS'):
            x = R[R.league == lg]
            print(f'  κατωφλι {thr:.2f} {lg:6s} ' + st(x) + ' · ' + ' · '.join(f'{s}: {st(x[x.side == s]).split(" · ")[0]}' for s in sorted(x.side.unique())))
    thr = 0.10 if mkt == 'tot' else 0.06
    R = run(D, 'open', mkt, thr)
    print(f'  ανα σεζον (κατωφλι {thr}): ' + ' | '.join(f'{lg}: ' + ' '.join(f'{s}:{100*g.pnl.mean():+.0f}%' for s, g in R[R.league == lg].groupby('season')) for lg in ('Brazil', 'MLS')))
    print(f'  ανα παραθυρο: ' + ' | '.join(f'{lg} {p}: {st(R[(R.league == lg) & (R.per == p)]).split(" · ")[0]}' for lg in ('Brazil', 'MLS') for p in ('7-14', '15+')))
    print(f'  k (LOSO) που χρησιμοποιηθηκε: ' + ', '.join(f'{lg} {s}: {g.k.iloc[0]:.2f}' for (lg, s), g in R.groupby(['league', 'season'])))
    for entry in ('72h', '24h'):
        R2 = run(D, entry, mkt, thr)
        print(f'  ΙΔΙΟΣ κανονας στο {entry:5s}: ' + ' | '.join(f'{lg}: {st(R2[R2.league == lg])}' for lg in ('Brazil', 'MLS')))
