"""
intl_tmix_eval.py — ΑΞΙΟΛΟΓΗΣΗ T_MODE=mix (συνολο γκολ = T σημερα + xG επιθεσης/αμυνας ομαδων) στο τεστ παραθυρου 72ω, βαση το live (Σχ.Β + βαθια φαβορι).
26/9/2026 (Στελιος: «η λογικη επιλογης των over ποδοσφαιρικα δεν μου μοιαζει καλη — παιζουν ρολο τα xG στο συνολο;»).
ΠΡΟ-ΔΗΛΩΣΗ: (α) συναινεση: over ROI ΚΑΙ ολα ROI οχι χειροτερα, ΚΑΙ στα 2 βιβλια · (β) over συναινεσης στο ΧΑΜΗΛΟ τριτο τασης γκολ
  (οριο 2.54, οπως intl_over_team_tendency): λιγοτερα Η καλυτερο ROI, και στα 2 βιβλια. Περνα = (α) ΚΑΙ (β). Ενα νουμερο = μεσος Crown/SBOBET.
"""
import sys, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
M = pd.read_csv('intl_matches.csv', dtype={'mid': str}, parse_dates=['date']).sort_values('date')
import intl_dedupe
M = intl_dedupe.dedupe(M, where='tmix_eval').sort_values('date'); M['tot'] = M.hs + M['as']
hist = {}; TEN = {}
for r in M.itertuples():
    v = [np.mean(hist[t][-12:]) if len(hist.get(t, [])) >= 6 else np.nan for t in (int(r.hid), int(r.aid))]; TEN[r.mid] = np.nanmean(v) if not all(np.isnan(v)) else np.nan
    if r.ctype in ('nl', 'qual', 'tourn'):
        for t in (int(r.hid), int(r.aid)): hist.setdefault(t, []).append(r.tot)
def load(f):
    b = pd.read_csv(f, dtype={'mid': str, 'season': str}); b = b[(b.win == '72ω') & b.model.isin(['M1', 'M2', 'M3'])].copy()
    b['mkt'] = np.where(b.rule == 'OVER', 'O', 'AH'); b['dir'] = np.where(b.rule == 'OVER', 0, b.side)
    c = pd.DataFrame([g.sort_values('hours').iloc[0].to_dict() | dict(model='ΣΥΝΑΙΝΕΣΗ') for _, g in b.groupby(['book', 'mid', 'mkt', 'dir']) if g.model.nunique() >= 2])
    b = pd.concat([b, c], ignore_index=True); b['ten'] = b.mid.map(TEN); return b
L = load('intl_window_test_proper_ahhybrid_gddeepfav_bets.csv'); X = load('intl_window_test_proper_ahhybrid_Tmix_gddeepfav_bets.csv')
out = []
def P(s=''):
    print(s, flush=True); out.append(s)
def st(x):
    if len(x) == 0: return (0, np.nan, 0, 0, 0.0)
    cy = x.groupby('season').pnl.mean(); return (len(x), x.pnl.mean() * 100, int((cy > 0).sum()), cy.size, x.pnl.sum())
def row(x):
    c, s = st(x[x.book == 'Crown']), st(x[x.book == 'SBOBET'])
    return f"{(c[1] + s[1]) / 2:+6.1f}% (n~{(c[0] + s[0]) // 2}, {c[2]}/{c[3]} σεζον, ~{(c[4] + s[4]) / 2:+.1f}u)" + (' ⚠' if (c[1] > 0) != (s[1] > 0) else '')
P('T + xG ΟΜΑΔΩΝ ΣΤΟ ΤΕΣΤ ΠΑΡΑΘΥΡΟΥ 72ω — βαση: live (Σχ.Β + βαθια φαβορι, σωστο over)')
SEG = (('ΟΛΑ', lambda x: x.rule.notna()), ('handicap', lambda x: x.rule != 'OVER'), ('over', lambda x: x.rule == 'OVER'),
       ('  over — «στεγνες» ομαδες (ταση ≤2.54)', lambda x: (x.rule == 'OVER') & (x.ten <= 2.54)), ('  over — υπολοιπα', lambda x: (x.rule == 'OVER') & (x.ten > 2.54)))
for who in ('ΣΥΝΑΙΝΕΣΗ', 'M1', 'M2', 'M3'):
    P(f'\n--- {who} ---')
    for lab, fl in SEG:
        a = L[L.model == who]; b = X[X.model == who]; P(f'  {lab:38s} σημερα {row(a[fl(a)])}  →  με xG ομαδων {row(b[fl(b)])}')
P('\nΚΡΙΤΗΡΙΑ (συναινεση):'); okA = okB = True
for bk in ('Crown', 'SBOBET'):
    a = L[(L.model == 'ΣΥΝΑΙΝΕΣΗ') & (L.book == bk)]; b = X[(X.model == 'ΣΥΝΑΙΝΕΣΗ') & (X.book == bk)]
    oa, ob = a[a.rule == 'OVER'].pnl.mean(), b[b.rule == 'OVER'].pnl.mean(); ta, tb = a.pnl.mean(), b.pnl.mean()
    la, lb = a[(a.rule == 'OVER') & (a.ten <= 2.54)], b[(b.rule == 'OVER') & (b.ten <= 2.54)]
    cA = ob >= oa - 1e-9 and tb >= ta - 1e-9; cB = (len(lb) < len(la)) or (lb.pnl.mean() > la.pnl.mean()); okA &= cA; okB &= cB
    P(f'  {bk}: over {oa * 100:+.1f}→{ob * 100:+.1f} · ολα {ta * 100:+.1f}→{tb * 100:+.1f} {"✓" if cA else "✗"} · στεγνες n{len(la)} {la.pnl.mean() * 100:+.1f}% → n{len(lb)} {lb.pnl.mean() * 100:+.1f}% {"✓" if cB else "✗"}')
P(f'ΑΠΟΤΕΛΕΣΜΑ: {"ΠΕΡΝΑ" if (okA and okB) else "ΔΕΝ ΠΕΡΝΑ"}')
open('intl_tmix_eval_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
