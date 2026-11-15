"""
core7_714_shortfav_move.py — 9/10/2026 (Στελιος: «γιατι στο κλεισιμο καλυτερα; τα φαβορι παιρνουν χρημα προς την εναρξη»).
Κινηση αγορας απο −72ω/−24ω ως το κλεισιμο: (α) ΟΛΑ τα κοντα φαβορι στο κλεισιμο, (β) τα picks του κανονα R στο κλεισιμο.
«Δυναμη φαβορι» = πιθανοτητα καλυψης χωρις γκανιοτα στο χαντικαπ του φαβορι, μεταφρασμενη σε γραμμη: |γραμμη| + (0.5 − p_novig)·~1.6 (περιπου γκολ).
Θετικο = η αγορα ΕΣΠΡΩΞΕ το φαβορι (το εκανε πιο φαβορι), αρνητικο = γυρισε κοντρα.
"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
class _Q(io.StringIO):
    def reconfigure(self, **k): pass
src = open('core7_714_shortfav_timing.py', encoding='utf-8').read()
src = src[:src.index("HOURS = [")].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
g = {'__name__': 'mv'}
with contextlib.redirect_stdout(_Q()): exec(src, g)
W, NG, KO, picks, ev_ok = g['W'], g['NG'], g['KO'], g['picks'], g['ev_ok']
def strength(L, oh, oa, side):
    o_f, o_d = (oh, oa) if side == 1 else (oa, oh)
    p = (1 / o_f) / (1 / o_f + 1 / o_d); Lf = -L if side == 1 else L      # χαντικαπ φαβορι ως θετικος αριθμος
    return Lf + (p - 0.5) * 1.6
rows = []
for r in W.itertuples():
    ko = KO.get(r.mid)
    if ko is None: continue
    dist = picks.gd_dist_dom(r.xh, r.xa)
    for bk in ('Crown', 'Bet365'):
        seq = NG.get((r.mid, bk))
        if not seq: continue
        close = [x for x in seq if x[0] <= ko + 600]
        if not close: continue
        L, oh, oa = close[-1][1:]
        if abs(L) not in (0.5, 0.75): continue
        side = 1 if L < 0 else -1; o = oh if side == 1 else oa
        if not (1.70 <= o <= 2.10): continue
        rec = dict(book=bk, season=r.season, pick=ev_ok(dist, side, -abs(L), o) >= 0.0, s_close=strength(L, oh, oa, side), pnl=picks.settle(r.gd, side, -abs(L), o))
        for h in (72, 24, 6):
            prev = [x for x in seq if x[0] <= ko - h * 3600]
            if prev: rec[f's{h}'] = strength(*prev[-1][1:], side)
        rows.append(rec)
B = pd.DataFrame(rows)
for h in (72, 24, 6): B[f'mv{h}'] = B.s_close - B[f's{h}']
def line(d, lab):
    out = f'   {lab:34s} n{len(d):4d} · ROI κλεισ. {100*d.pnl.mean():+5.1f}%'
    for h in (72, 24, 6):
        x = d[f'mv{h}'].dropna()
        out += f' · απο −{h}ω: {x.mean():+.3f} (εσπρωξαν {100*(x > 0.02).mean():.0f}% / γυρισε κοντρα {100*(x < -0.02).mean():.0f}%)'
    return out
for bk in ('Crown', 'Bet365'):
    x = B[B.book == bk]
    print(f'[{bk}] κινηση «δυναμης φαβορι» ως το κλεισιμο (θετικο = χρημα ΣΤΟ φαβορι)')
    print(line(x, 'ΟΛΑ τα κοντα φαβορι'))
    print(line(x[x.pick], 'picks κανονα R (κλεισιμο)'))
    print(line(x[~x.pick], 'τα υπολοιπα (οχι pick)'))
    m = x.mv24.notna()
    print(line(x[m & (x.mv24 > 0.02)], 'ολα: εσπρωξαν απο −24ω'))
    print(line(x[m & (x.mv24 < -0.02)], 'ολα: γυρισε κοντρα απο −24ω'))
    print(line(x[x.pick & m & (x.mv24 > 0.02)], 'picks R: εσπρωξαν απο −24ω'))
    print(line(x[x.pick & m & (x.mv24 < -0.02)], 'picks R: γυρισε κοντρα απο −24ω'))
