"""uel_home_why2.py — συμπληρωμα: UEL ανα ρολο φαβορι (μοντελο) × εδρα, σε xG ΚΑΙ γκολ (σκοπια φαβορι μοντελου)· και ποιος «φταιει»: η πλευρα του φαβορι ή του αουτσαιντερ."""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('uel_home_why.py', encoding='utf-8').read(); src = src[:src.index("print('1. ΕΔΡΑ")].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'hw2'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
COMP, LH_N, LA_N, GH, GA, XH, XA, SEA, LGH, LGA = (g[k] for k in ('COMP', 'LH_N', 'LA_N', 'GH', 'GA', 'XH', 'XA', 'SEA', 'LGH', 'LGA'))
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
for c in ('EuropaLeague', 'ChampionsLeague', 'ConferenceLeague'):
    print(f'\n[{c}] ανα φαβορι μοντελου (|υπεροχη| ≥0.5) — πραγματικο − μοντελο ΑΝΑ ΠΛΕΥΡΑ (xG / γκολ)')
    for lab, fh in (('φαβορι ΕΝΤΟΣ', True), ('φαβορι ΕΚΤΟΣ', False)):
        m = (COMP == c) & np.isfinite(XH) & (((LH_N - LA_N) >= 0.5) if fh else ((LA_N - LH_N) >= 0.5))
        fx, fg, fl = (XH, GH, LH_N) if fh else (XA, GA, LA_N); dx, dg, dl = (XA, GA, LA_N) if fh else (XH, GH, LH_N)
        t5 = np.isin(LGH if fh else LGA, list(TOP5))
        print(f'   {lab:14s} n{m.sum():4d} · ΦΑΒΟΡΙ xG {np.mean(fx[m] - fl[m]):+.2f} γκολ {np.mean(fg[m] - fl[m]):+.2f} · ΑΟΥΤΣΑΙΝΤΕΡ xG {np.mean(dx[m] - dl[m]):+.2f} γκολ {np.mean(dg[m] - dl[m]):+.2f}'
              f' · φαβορι top-5: xG {np.mean((fx - fl)[m & t5]):+.2f} (n{(m & t5).sum()}) / οχι top-5: {np.mean((fx - fl)[m & ~t5]):+.2f} (n{(m & ~t5).sum()})')
