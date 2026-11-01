"""euro_dominance_cost.py — 9/10/2026 (Στελιος: «δεν νομιζω οτι η υπερβολη στα ανισα ματς μας κοστιζει λεφτα — τσεκαρε»).
Picks με τους ΣΗΜΕΡΙΝΟΥΣ κανονες (FotMob+FotMob, 1.70-2.10, φαβ σωστα τεταρτα / dogs p_cover, UCL fav@10 dog@4, αλλα fav@4 dog@10),
κλεισιμο, μεσος Crown/Pinnacle, με 3 εκδοχες προβλεψης: Α χωρις γ & κ · Β μονο γ · Γ σημερινη (γ+κ).
Ανα διοργανωση/ρολο/εδρα και ανα ανισοτητα ματς (σημερινη υπεροχη). + ROI των picks ΜΕΣΑ στα ανισα ματς (≥1.2)."""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('euro_dominance_steps.py', encoding='utf-8').read().split("TOP7 = o['TOP7']")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'dc'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
o = g['o']; S2, S3, S4 = g['S2'], g['S3'], g['S4']; gen, CROWN, PIN = o['gen'], o['CROWN'], o['PIN']
MIDS, COMP, SEA = g['MIDS'], g['COMP'], g['SEA']
IDX = {m: i for i, m in enumerate(MIDS)}
SUP = np.abs(S4[0] - S4[1]); FAVH = S4[0] >= S4[1]
def picks_df(L):
    rows = []
    for bk, OD in (('C', CROWN), ('P', PIN)):
        for (mid, side), r in gen(L, OD).items():
            i = IDX[mid]
            rows.append(dict(bk=bk, mid=mid, side=side, comp=r['comp'], role=r['role'], sea=r['sea'], pnl=r['pnl'],
                             home=side == 1, sup=SUP[i], fav_side=(side == 1) == FAVH[i]))
    return pd.DataFrame(rows)
P = {'Α χωρις γ,κ': picks_df(S2), 'Β μονο γ': picks_df(S3), 'Γ σημερα γ+κ': picks_df(S4)}
def cell(x):
    if len(x) == 0: return f'{"—":>22s}'
    m = x.groupby('bk').pnl.agg(['mean', 'size']); se = x.groupby('bk').pnl.std() / np.sqrt(m['size'])
    ps = x.groupby('sea').pnl.mean()
    return f'{m["size"].mean():4.0f} {100 * m["mean"].mean():+6.1f}%±{100 * se.mean():4.1f} {int((ps > 0).sum())}/{ps.size}'
SEL = [('ΟΛΑ', lambda d: d), ('UCL', lambda d: d[d.comp == 'ChampionsLeague']), ('  UCL φαβ', lambda d: d[(d.comp == 'ChampionsLeague') & (d.role == 'fav')]),
       ('  UCL dog', lambda d: d[(d.comp == 'ChampionsLeague') & (d.role == 'dog')]), ('UEL', lambda d: d[d.comp == 'EuropaLeague']),
       ('  UEL φαβ εντος', lambda d: d[(d.comp == 'EuropaLeague') & (d.role == 'fav') & d.home]), ('  UEL φαβ εκτος', lambda d: d[(d.comp == 'EuropaLeague') & (d.role == 'fav') & ~d.home]),
       ('UECL', lambda d: d[d.comp == 'ConferenceLeague']), ('φαβ εντος (ολα)', lambda d: d[(d.role == 'fav') & d.home]), ('φαβ εκτος (ολα)', lambda d: d[(d.role == 'fav') & ~d.home]),
       ('dogs εντος', lambda d: d[(d.role == 'dog') & d.home]), ('dogs εκτος', lambda d: d[(d.role == 'dog') & ~d.home])]
print('1. PICKS ανα εκδοχη — n / ROI ±SE / θετικες σεζον (μεσος Crown/Pinnacle, κλεισιμο)')
print(f'   {"":18s} | ' + ' | '.join(f'{k:>24s}' for k in P))
for lab, f in SEL:
    print(f'   {lab:18s} | ' + ' | '.join(f'{cell(f(d)):>24s}' for d in P.values()))
print('\n2. ΑΝΑ ΑΝΙΣΟΤΗΤΑ ΜΑΤΣ (σημερινη υπεροχη φαβορι) — picks φαβορι / picks αουτσαιντερ')
for lo, hi, lab in ((0, .7, 'κοντα (<0.7)'), (.7, 1.2, 'φαβορι 0.7-1.2'), (1.2, 1.8, 'μεγαλο 1.2-1.8'), (1.8, 9, 'τεραστιο 1.8+')):
    print(f'   {lab:16s} ' + ' | '.join(f'{k[:1]}: φαβ {cell(d[(d.sup >= lo) & (d.sup < hi) & (d.role == "fav")]).strip()} · dog {cell(d[(d.sup >= lo) & (d.sup < hi) & (d.role == "dog")]).strip()}' for k, d in P.items()))
print('\n3. ΤΙ ΑΛΛΑΖΕΙ το γ+κ (Α → Γ): picks που ΦΕΥΓΟΥΝ / ΜΠΑΙΝΟΥΝ')
A, C = P['Α χωρις γ,κ'], P['Γ σημερα γ+κ']
ka = set(zip(A.bk, A.mid, A.side)); kc = set(zip(C.bk, C.mid, C.side))
out_ = A[[k not in kc for k in zip(A.bk, A.mid, A.side)]]; in_ = C[[k not in ka for k in zip(C.bk, C.mid, C.side)]]
com = C[[k in ka for k in zip(C.bk, C.mid, C.side)]]
for lab, d in (('φευγουν', out_), ('μπαινουν', in_), ('κοινα', com)):
    print(f'   {lab:9s} ΟΛΑ {cell(d).strip()} · φαβ {cell(d[d.role == "fav"]).strip()} · dog {cell(d[d.role == "dog"]).strip()} · UCL {cell(d[d.comp == "ChampionsLeague"]).strip()}')
