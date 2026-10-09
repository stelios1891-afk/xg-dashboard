"""euro_rotation_venue.py — 9/10/2026 (Στελιος: «ροτεισον εντος vs εκτος για τις ιδιες ομαδες· μηπως εκτος κανουν περισσοτερο;»).
Απο τη βαση του euro_rotation_model (βασικοι = top-11 εγχωριες εκκινησεις πριν το ματς): μεσες αλλαγες /11 ανα διοργανωση × κατηγορια ×
ρολο (φαβορι/αουτσαιντερ μοντελου, |υπεροχη| ≥0.5) × εντος/εκτος · και πραγματικο − μοντελο (γκολ & xG της ομαδας) στο ιδιο κελι.
Και ΙΔΙΕΣ ΟΜΑΔΕΣ: ομαδες με ματς ΚΑΙ εντος ΚΑΙ εκτος στην ιδια σεζον → διαφορα αλλαγων εκτος − εντος (ζευγαρωτα)."""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('euro_rotation_model.py', encoding='utf-8').read(); src = src[:src.index('# ---- σχεδιασμος')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'rv'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
S, LH_N, LA_N = g['S'], g['LH_N'], g['LA_N']
sup = np.array([(LH_N[i] - LA_N[i]) * (1 if h else -1) for i, h in zip(S.i, S.home)])
S['role'] = np.where(sup >= 0.5, 'φαβορι', np.where(sup <= -0.5, 'αουτσαιντερ', 'ισορροπο'))
Z = S[S.nb.notna()].copy(); Z['eg'] = Z.y - Z.lam; Z['ex'] = Z.x - Z.lam
def cell(d):
    if len(d) < 8: return f'n{len(d):3d}' + ' ' * 30
    return f'n{len(d):3d} αλλαγες {d.rot.mean():.2f} · γκολ−μοντ {d.eg.mean():+.2f} · xG−μοντ {d.ex.mean():+.2f}'
for comp in ('EuropaLeague', 'ChampionsLeague', 'ConferenceLeague'):
    print(f'\n[{comp}]  (εντος | εκτος)')
    for cls in ('top5_mid', 'top5_top', 'top5_low', 'ptnl'):
        for role in ('φαβορι', 'αουτσαιντερ'):
            x = Z[(Z.comp == comp) & (Z.cls == cls) & (Z.role == role)]
            if len(x) < 8: continue
            print(f'   {cls:9s} {role:11s} εντος: {cell(x[x.home == 1])} | εκτος: {cell(x[x.home == 0])}')
print('\nΙΔΙΕΣ ΟΜΑΔΕΣ, ιδια σεζον (ζευγαρωτα): αλλαγες εκτος − εντος')
for comp in ('EuropaLeague', 'ChampionsLeague', 'ConferenceLeague'):
    for cls in ('top5_mid', 'top5_top', 'ptnl'):
        x = Z[(Z.comp == comp) & (Z.cls == cls)]
        p = x.groupby(['team', 'sea', 'home']).rot.mean().unstack('home').dropna()
        if len(p) < 5: continue
        d = p[0] - p[1]
        print(f'   {comp:17s} {cls:9s} ομαδες-σεζον {len(p):3d} · εντος {p[1].mean():.2f} · εκτος {p[0].mean():.2f} · διαφορα {d.mean():+.2f} ±{d.std() / np.sqrt(len(d)):.2f}')
