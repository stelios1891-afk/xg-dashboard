"""
core7_consensus_test.py — ΤΕΣΤ 28/9/2026: ΣΥΝΑΙΝΕΣΗ live + ΑΓΚΥΡΑ στα εγχωρια (βημα 2 μετα το core7_anchor_test: η αγκυρα μονη
βελτιωνει RPS 4/4 αλλα κοβει τα picks 1072→467 → ✗ κριτηριο μοναδων).
Αγκυρα: λ=0.5, c=0 (η επιλογη LOSO σε 3/4 σεζον). Picks = κανονες live (+handicap ≥0.5, 1.70-2.10, edge≥10%) στο closing Pinnacle AH.
ΡΟΕΣ: LIVE (σημερα) · ΑΓΚΥΡΑ · ΣΥΝΑΙΝΕΣΗ (ιδιο ματς & πλευρα και στα δυο) · ΜΟΝΟ-LIVE (live χωρις αγκυρα) · ΜΟΝΟ-ΑΓΚΥΡΑ.
ΠΡΟ-ΔΗΛΩΣΗ: η ΣΥΝΑΙΝΕΣΗ ΠΕΡΝΑ αν στο md15+ (α) ROI > LIVE, (β) θετικη σε ≥3/4 σεζον, (γ) τα picks που κοβει (ΜΟΝΟ-LIVE) ειναι ΚΑΤΩ απο
τη συναινεση σε ROI (δηλ. η κοπη αφαιρει τα χειροτερα). Μοναδες αναφερονται (λιγοτερα bets αναμενομενα). md7-14 πληροφοριακα.
"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_anchor_test.py', encoding='utf-8').read()
pre = src[:src.index('res = {}')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'cons'}
with contextlib.redirect_stdout(_Q()):
    exec(pre, g)
D, run, picks = g['D'], g['run'], g['picks']
SEAS = sorted(D.season.unique())

def pick_map(s_arr):
    out = {}
    for i in np.where(D.s_mkt.notna().values)[0]:
        r = D.loc[i]; t = r.xh + r.xa; s = s_arr[i]
        for b in picks.evaluate_bet(max((t + s) / 2, .05), max((t - s) / 2, .05), r.L, r.ah, r.aa):
            out[(i, b['side'])] = (b['hcap'], b['odds'], b['edge'])
    return out
S0 = run(0, 0); SA = run(0.5, 0)
P0, PA = pick_map(S0), pick_map(SA)
def stream(keys, src):
    rows = []
    for k in keys:
        i, side = k; ud, odds, e = src[k]; r = D.loc[i]
        rows.append(dict(win=r.win, season=r.season, league=r.league, ud=ud, pnl=picks.settle(r.gd, side, ud, odds)))
    return pd.DataFrame(rows)
ST = {'LIVE (σημερα)': stream(P0.keys(), P0), 'ΑΓΚΥΡΑ': stream(PA.keys(), PA),
      'ΣΥΝΑΙΝΕΣΗ': stream([k for k in P0 if k in PA], P0), 'ΜΟΝΟ-LIVE (κοβονται)': stream([k for k in P0 if k not in PA], P0),
      'ΜΟΝΟ-ΑΓΚΥΡΑ (νεα)': stream([k for k in PA if k not in P0], PA)}
res = {}
for w_ in ('md15+', 'md7-14'):
    print(f'\n[{w_}]  n · ROI (±SE) · μοναδες · ROI ανα σεζον')
    for name, d in ST.items():
        d = d[d.win == w_] if len(d) else d
        if not len(d): print(f'  {name:22s} —'); continue
        ps = d.groupby('season').pnl.mean()
        print(f'  {name:22s} n{len(d):5d} · ROI {100*d.pnl.mean():+5.1f}% (±{100*d.pnl.std()/np.sqrt(len(d)):.1f}) · {d.pnl.sum():+6.1f}u · ' +
              ' '.join(f'{s_}:{100*ps.get(s_, np.nan):+.0f}' for s_ in SEAS) + f' · θετικες {int((ps > 0).sum())}/{len(ps)}')
        res[(w_, name)] = (d.pnl.mean(), int((ps > 0).sum()))
print('\nΑΝΑ ΒΑΘΟΣ ΓΡΑΜΜΗΣ (md15+): ROI LIVE / ΣΥΝΑΙΝΕΣΗ / ΜΟΝΟ-LIVE')
for lo, hi in ((0.5, 1), (1, 1.5), (1.5, 9)):
    cells = []
    for name in ('LIVE (σημερα)', 'ΣΥΝΑΙΝΕΣΗ', 'ΜΟΝΟ-LIVE (κοβονται)'):
        d = ST[name]; d = d[(d.win == 'md15+') & (d.ud >= lo) & (d.ud < hi)]
        cells.append(f'{name.split()[0]} n{len(d)} {100*d.pnl.mean():+.1f}%' if len(d) else '—')
    print(f'  γραμμη +{lo}–{hi if hi < 9 else "∞"}: ' + ' · '.join(cells))
c = res[('md15+', 'ΣΥΝΑΙΝΕΣΗ')]; l = res[('md15+', 'LIVE (σημερα)')]; cut = res[('md15+', 'ΜΟΝΟ-LIVE (κοβονται)')]
a_, b_, c_ = c[0] > l[0], c[1] >= 3, cut[0] < c[0]
print(f'\nΚΡΙΣΗ md15+: (α) ROI συναινεσης {100*c[0]:+.1f}% > live {100*l[0]:+.1f}% {"✓" if a_ else "✗"} · (β) θετικη {c[1]}/4 {"✓" if b_ else "✗"} · '
      f'(γ) κομμενα {100*cut[0]:+.1f}% < συναινεση {"✓" if c_ else "✗"} → {"ΠΕΡΝΑ" if a_ and b_ and c_ else "ΔΕΝ ΠΕΡΝΑ"}')
