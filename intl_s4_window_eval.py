"""
intl_s4_window_eval.py — ΑΞΙΟΛΟΓΗΣΗ Σ4 (σημασια παικτη) στο τεστ παραθυρου 72ω, με βαση το ΣΗΜΕΡΙΝΟ live (Σχεδιο Β + βαθια φαβορι). 25/9/2026.
ΠΡΟ-ΔΗΛΩΣΗ: (α) συναινεση ≥2/3 (ολα AH+OVER) οχι χειροτερη ΚΑΙ στα 2 βιβλια · (β) picks ΥΠΕΡ ομαδας που λειπει ≥10% της σημασιας της:
  ROI καλυτερο Ή λιγοτερα picks με ROI οχι χειροτερο, ΚΑΙ στα 2 βιβλια. Περνα = (α) ΚΑΙ (β). Ενα νουμερο = μεσος Crown/SBOBET.
"""
import sys, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
S4 = dict(pd.read_csv('intl_imp_s4.csv', dtype={'mid': str}).values.tolist())
def load(f):
    b = pd.read_csv(f, dtype={'mid': str, 'season': str}); b = b[(b.win == '72ω') & b.model.isin(['M1', 'M2', 'M3'])].copy()
    b['mkt'] = np.where(b.rule == 'OVER', 'O', 'AH'); b['dir'] = np.where(b.rule == 'OVER', 0, b.side)
    c = pd.DataFrame([gg.sort_values('hours').iloc[0].to_dict() | dict(model='ΣΥΝΑΙΝΕΣΗ') for _, gg in b.groupby(['book', 'mid', 'mkt', 'dir']) if gg.model.nunique() >= 2])
    b = pd.concat([b, c], ignore_index=True)
    b['g'] = [(S4.get(m, 0.0) if s == 1 else -S4.get(m, 0.0)) if r != 'OVER' else 0.0 for m, s, r in zip(b.mid, b.side, b.rule)]
    return b
L = load('intl_window_test_proper_ahhybrid_gddeepfav_bets.csv'); S = load('intl_window_test_proper_ahhybrid_s4_gddeepfav_bets.csv')
out = []
def P(s=''):
    print(s, flush=True); out.append(s)
def st(x):
    if len(x) == 0: return (0, np.nan, 0, 0, 0.0)
    cy = x.groupby('season').pnl.mean(); return (len(x), x.pnl.mean() * 100, int((cy > 0).sum()), cy.size, x.pnl.sum())
def row(x):
    c, s = st(x[x.book == 'Crown']), st(x[x.book == 'SBOBET'])
    return f"{(c[1] + s[1]) / 2:+6.1f}% (n~{(c[0] + s[0]) // 2}, {c[2]}/{c[3]} σεζον, ~{(c[4] + s[4]) / 2:+.1f}u)" + (' ⚠ διαφωνουν' if (c[1] > 0) != (s[1] > 0) else ''), c, s
P('Σ4 ΣΤΟ ΤΕΣΤ ΠΑΡΑΘΥΡΟΥ 72ω — βαση: live σημερα (Σχεδιο Β + βαθια φαβορι)')
for who in ('ΣΥΝΑΙΝΕΣΗ', 'M1', 'M2', 'M3'):
    P(f'\n--- {who} ---')
    for seg, fl in (('ΟΛΑ', lambda x: x.rule.notna()), ('handicap', lambda x: x.rule != 'OVER'), ('  ΥΠΕΡ ομαδας χωρις σημαντικους (≥10%)', lambda x: (x.rule != 'OVER') & (x.g >= .10)),
                    ('  παρομοιες απουσιες', lambda x: (x.rule != 'OVER') & (x.g.abs() < .10)), ('  ΚΟΝΤΡΑ σε ομαδα χωρις σημαντικους', lambda x: (x.rule != 'OVER') & (x.g <= -.10)), ('over', lambda x: x.rule == 'OVER')):
        a = L[L.model == who]; b = S[S.model == who]
        P(f'  {seg:40s} σημερα {row(a[fl(a)])[0]}  →  με Σ4 {row(b[fl(b)])[0]}')
P('\nΚΡΙΤΗΡΙΑ (συναινεση):')
okA = okB = True
for bk in ('Crown', 'SBOBET'):
    a = L[(L.model == 'ΣΥΝΑΙΝΕΣΗ') & (L.book == bk)]; b = S[(S.model == 'ΣΥΝΑΙΝΕΣΗ') & (S.book == bk)]
    ra, rb = a.pnl.mean(), b.pnl.mean(); okA &= rb >= ra - 1e-9
    fa = a[(a.rule != 'OVER') & (a.g >= .10)]; fb = b[(b.rule != 'OVER') & (b.g >= .10)]
    cond = (fb.pnl.mean() > fa.pnl.mean()) or (len(fb) < len(fa) and fb.pnl.mean() >= fa.pnl.mean() - 1e-9)
    okB &= bool(cond)
    P(f'  {bk}: ολα {ra * 100:+.1f} → {rb * 100:+.1f} {"✓" if rb >= ra - 1e-9 else "✗"} · υπερ ομαδας με απουσιες n{len(fa)} {fa.pnl.mean() * 100:+.1f}% → n{len(fb)} {fb.pnl.mean() * 100:+.1f}% {"✓" if cond else "✗"}')
P(f'ΑΠΟΤΕΛΕΣΜΑ: {"ΠΕΡΝΑ" if (okA and okB) else "ΔΕΝ ΠΕΡΝΑ"}')
open('intl_s4_window_eval_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
