"""euro_role_venue.py — 9/10/2026 (Στελιος: «λιστα φαβορι εντος/εκτος, αουτσαιντερ εντος/εκτος, ROI»): ROI ανα διοργανωση × ρολος × εδρα,
σημερινη ευρωπαικη αλυσιδα, 2223-2526, FotMob+FotMob, 1.70-2.10, μεσος Crown/SBOBET. Picks μοντελου (σημερινοι κανονες) στο κλεισιμο και −24ω,
και ΤΥΦΛΑ (ολα τα φαβορι/αουτσαιντερ της ζωνης, χωρις μοντελο) για συγκριση."""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('uel_timing.py', encoding='utf-8').read(); src = src[:src.index("HAS = {}")].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'rv'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
B, MIDS, FM, COMP, SEA, GD, snap, picks = (g[k] for k in ('B', 'MIDS', 'FM', 'COMP', 'SEA', 'GD', 'snap', 'picks'))
blind = []
for i, mid in enumerate(MIDS):
    if not FM[i]: continue
    for bk in ('Crown', 'SBOBET'):
        for h in (0, 24):
            s = snap(mid, bk, h)
            if not s: continue
            L, oh, oa = s
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= o <= 2.10) or abs(ln) < 0.5: continue
                blind.append(dict(comp=COMP[i], sea=SEA[i], book=bk, h=h, role='fav' if ln < 0 else 'dog', home=side == 1, pnl=picks.settle(GD[i], side, ln, o)))
BL = pd.DataFrame(blind)
def cell(d):
    if len(d) < 4: return f'{"—":>22s}'
    ps = d.groupby('sea').pnl.mean()
    return f'{len(d) / d.book.nunique():4.0f} {100 * d.pnl.mean():+6.1f}% {int((ps > 0).sum())}/{ps.size}'.rjust(22)
LAB = {'ChampionsLeague': 'CHAMPIONS LEAGUE', 'EuropaLeague': 'EUROPA LEAGUE', 'ConferenceLeague': 'CONFERENCE LEAGUE'}
for c in ('EuropaLeague', 'ChampionsLeague', 'ConferenceLeague'):
    print(f'\n{LAB[c]}   (picks · ROI · σεζον θετικες)')
    print(f'   {"":22s}{"μοντελο κλεισιμο":>22s}{"μοντελο −24ω":>22s}{"τυφλα κλεισιμο":>22s}{"τυφλα −24ω":>22s}')
    for role, rl in (('fav', 'φαβορι'), ('dog', 'αουτσαιντερ')):
        for home, hl in ((True, 'εντος'), (False, 'εκτος')):
            sel = lambda D, h: D[(D.comp == c) & (D.h == h) & (D.role == role) & (D.home == home)]
            print(f'   {rl + " " + hl:22s}{cell(sel(B, 0))}{cell(sel(B, 24))}{cell(sel(BL, 0))}{cell(sel(BL, 24))}')
