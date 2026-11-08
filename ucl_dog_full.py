# -*- coding: utf-8 -*-
"""ucl_dog_full.py — 19/10/2026 (Στελιος: «αυτα τα αουτσαιντερ, ΛΑΣΚ, Φεγενορντ και Λειψια, πως αποδιδουν ιστορικα; πληρης αναλυση»).
Champions League, κατηγορια Α, ΑΟΥΤΣΑΙΝΤΕΡ live κανονας: γραμμη ≥ +0.5, p_cover, edge ≥4%, 1.70-2.10 (Crown & SBOBET, μεσος) — ιδια μηχανη με
ucl_early_honest (σημερινη αλυσιδα). Σημεια χρονου: 168/72/48/24/12ω, κλεισιμο. Αναλυση (στα 48ω = κυριο σημειο, και στα αλλα):
 ζωνη edge 4-6 / 6-10 / ≥10 · γραμμη +0.5/+0.75 · +1/+1.25 · +1.5/+1.75 · ≥+2 · εντος/εκτος · ανα σεζον · CLV (γκολ, + = προς εμας) ·
 ΤΥΦΛΑ: ολα τα αουτσαιντερ της ιδιας ζωνης αποδοσεων/γραμμων (χωρις μοντελο) — προσθετει κατι το μοντελο;"""
import sys
_s = open('uel_all_mechanisms.py', encoding='utf-8').read()
exec(_s[:_s.index("x = A[A.comp == 'EuropaLeague']")])
import euro_shadow_scan as ES
sys.stdout.reconfigure(encoding='utf-8')
x = A[A.comp == 'ChampionsLeague'].reset_index(drop=True)
mids = [str(MIDS[int(i)]) for i in x.i]; LH, LA = x.lh.values, x.la.values
CL = {(k_, bk): snapT(m, bk, 0) for k_, m in enumerate(mids) for bk in ('Crown', 'SBOBET')}
def run(h):
    out = []
    for k_ in range(len(x)):
        if x.cat[k_] != 'A': continue
        i = int(x.i[k_]); D_ = ES.eu_dist(LH[k_], LA[k_], .85)
        for bk in ('Crown', 'SBOBET'):
            s = snapT(mids[k_], bk, h)
            if not s: continue
            L, oh, oa = s; c = CL[(k_, bk)]
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= o <= 2.10) or ln < 0.5: continue
                pw, pp = picks.p_cover(D_, side, ln); e = edge(pw, pp, o)
                clv = side * (implied_margin(i, *c) - implied_margin(i, L, oh, oa)) if c else np.nan
                gd = GD[i]; marg = side * gd     # διαφορα απο τη ματια του αουτσαιντερ
                out.append(dict(sea=x.sea[k_], bk=bk, e=e, ln=ln, home=side == 1, pnl=picks.settle(gd, side, ln, o), clv=clv,
                                win=marg > 0, draw=marg == 0, lose_by=-marg if marg < 0 else 0))
    return pd.DataFrame(out)
def cell(y):
    if len(y) == 0: return f'{"—":>46s}'
    m = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean(); s = y.groupby('sea').pnl.mean()
    return f'{n:4.0f} {100 * m.mean():+6.1f}% {m.mean() * n:+6.1f}μ {int((s > 0).sum())}/{len(s)} · CLV {y.clv.mean():+.3f}'
NEW = ['2425', '2526']
for h in (168, 72, 48, 24, 12, 0):
    D = run(h); P = D[D.e >= .04]
    lab = 'κλεισιμο' if h == 0 else f'{h}ω πριν'
    print(f'\n{"=" * 130}\nΤΙΜΗ {lab.upper()} · κελι = picks ανα βιβλιο · ROI · μοναδες · θετικες σεζον · CLV (γκολ)')
    print(f'   {"":34s} {"ΝΕΑ ΜΟΡΦΗ 2024-26":^46s} │ {"ΟΛΕΣ 2022-26":^46s}')
    def rw(lb, f):
        print(f'   {lb:34s} {cell(P[f(P) & P.sea.isin(NEW)])} │ {cell(P[f(P)])}')
    rw('ΟΛΑ τα αουτσαιντερ ≥4%', lambda y: y.e >= 0)
    if h not in (48, 0): continue
    print('   — ζωνη edge —')
    rw('  4-6%', lambda y: y.e < .06); rw('  6-10%', lambda y: (y.e >= .06) & (y.e < .10)); rw('  ≥10%', lambda y: y.e >= .10)
    print('   — γραμμη (ποσα γκολ παιρνει) —')
    rw('  +0.5 / +0.75', lambda y: y.ln < 0.9); rw('  +1 / +1.25', lambda y: (y.ln >= 0.9) & (y.ln < 1.4))
    rw('  +1.5 / +1.75', lambda y: (y.ln >= 1.4) & (y.ln < 1.9)); rw('  +2 και πανω', lambda y: y.ln >= 1.9)
    print('   — εδρα —')
    rw('  αουτσαιντερ ΕΝΤΟΣ', lambda y: y.home); rw('  αουτσαιντερ ΕΚΤΟΣ', lambda y: ~y.home)
    print('   — ανα σεζον (ολες) —')
    for s in sorted(P.sea.unique()): print(f'   {"  " + s:34s} {"":46s} │ {cell(P[P.sea == s])}')
    print('   — ΤΙ ΓΙΝΕΤΑΙ ΣΤΟ ΓΗΠΕΔΟ (picks, ολες) —')
    y = P.drop_duplicates(subset=None)
    print(f'     ο αουτσαιντερ κερδισε {100 * y.win.mean():.0f}% · ισοπαλια {100 * y.draw.mean():.0f}% · εχασε {100 * (1 - y.win.mean() - y.draw.mean()):.0f}% '
          f'(με 1 γκολ {100 * (y.lose_by == 1).mean():.0f}% · 2 {100 * (y.lose_by == 2).mean():.0f}% · 3+ {100 * (y.lose_by >= 3).mean():.0f}%)')
    B = D[(D.ln >= 0.5)]
    print('   — ΤΥΦΛΑ (ολα τα αουτσαιντερ 1.70-2.10, γραμμη ≥+0.5, χωρις μοντελο) —')
    print(f'   {"  ολα":34s} {cell(B[B.sea.isin(NEW)])} │ {cell(B)}')
    print(f'   {"  οσα το μοντελο ΔΕΝ ηθελε (<4%)":34s} {cell(B[(B.e < .04) & B.sea.isin(NEW)])} │ {cell(B[B.e < .04])}')
