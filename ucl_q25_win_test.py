# -*- coding: utf-8 -*-
"""ucl_q25_win_test.py — 19/10/2026 (Στελιος: «οταν η αγορα ειναι στο −0.25 @1.90 η απλη νικη δινει 2.1-2.2· αν βρισκουμε αξια στη νικη αλλα
ξεπερναει το 2.1 και δεν παιζουμε −0.25 με τον σημερινο κανονα, τι πρεπει να κανουμε;»).
Champions League κατηγορια Α 2022-26, σημερινη αλυσιδα. ΠΕΡΙΠΤΩΣΕΙΣ: η ομαδα ειναι στο −0.25 στην κυρια γραμμη (Crown/SBOBET κλεισιμο) και η ΑΠΛΗ ΝΙΚΗ
(1Χ2 κλεισιμο, Pinnacle) ειναι >2.10, με edge μοντελου στη νικη ≥4% / ≥10%. Για ΤΙΣ ΙΔΙΕΣ περιπτωσεις: ROI αν επαιζες
 (1) −0.25 στην τιμη της αγορας · (2) απλη νικη · (3) DNB (τιμη απο το 1Χ2: νικη × (1 − 1/ισοπαλια)) · + edge μοντελου σε καθε μια.
+ το ιδιο για +0.25 (μικρος αουτσαιντερ) με νικη 2.60-4.00. Edge = τυπος scanner (κερδη × 0.97)."""
import sys, json
_s = open('uel_all_mechanisms.py', encoding='utf-8').read()
exec(_s[:_s.index("x = A[A.comp == 'EuropaLeague']")])
import euro_shadow_scan as ES
sys.stdout.reconfigure(encoding='utf-8')
x = A[(A.comp == 'ChampionsLeague') & (A.cat == 'A')].reset_index(drop=True); mids = [str(MIDS[int(i)]) for i in x.i]
X12 = {}
for l in open('nowgoal_1x2_euro.jsonl', encoding='utf-8'):
    r = json.loads(l)
    if r.get('book') and r.get('close'): X12[str(r['mid'])] = r
def ed(pw, pp, o): return pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
R = []
for k_ in range(len(x)):
    r = X12.get(mids[k_]); i = int(x.i[k_])
    if not r: continue
    D_ = ES.eu_dist(x.lh[k_], x.la[k_], .85); gd = GD[i]
    for bk in ('Crown', 'SBOBET'):
        c = snapT(mids[k_], bk, 0)
        if not c: continue
        L, oh, oa = c
        ow_h, od, ow_a = r['close']
        for side, ln, oq, ow in ((1, L, oh, ow_h), (-1, -L, oa, ow_a)):
            if abs(abs(ln) - 0.25) > .01: continue
            pwin = sum(p for g, p in D_.items() if (g > 0 if side == 1 else g < 0))
            e_win = pwin * (ow - 1) * (1 - picks.MARGIN) - (1 - pwin)
            pw, pp = cover_q(D_, side, ln); e_q = ed(pw, pp, oq)
            dnb = ow * (1 - 1 / od); pw0, pp0 = cover_q(D_, side, 0.0); e_d = ed(pw0, pp0, dnb)
            m = side * gd
            R.append(dict(sea=x.sea[k_], bk=bk, ln=ln, ow=ow, oq=oq, dnb=dnb, e_win=e_win, e_q=e_q, e_d=e_d,
                          p_win=(ow - 1) if m > 0 else -1.0, p_q=picks.settle(gd, side, ln, oq), p_d=(dnb - 1) if m > 0 else (0.0 if m == 0 else -1.0),
                          res='Ν' if m > 0 else ('Ι' if m == 0 else 'Η')))
D = pd.DataFrame(R)
def cell(y, col):
    if not len(y): return f'{"—":>30s}'
    m = y.groupby('bk')[col].mean(); n = y.groupby('bk').size().mean(); s = y.groupby('sea')[col].mean()
    return f'{n:4.0f} {100 * m.mean():+6.1f}% {m.mean() * n:+5.1f}μ {int((s > 0).sum())}/{len(s)}'
for sgn, nm, lo, hi in ((-1, 'ΟΜΑΔΑ ΣΤΟ −0.25 (μικρο φαβορι)', 2.10, 2.60), (1, 'ΟΜΑΔΑ ΣΤΟ +0.25 (μικρος αουτσαιντερ)', 2.60, 4.00)):
    y0 = D[(np.sign(D.ln) == sgn) & (D.ow > lo) & (D.ow <= hi)]
    print(f'\n{"=" * 125}\n{nm} · απλη νικη {lo:.2f}-{hi:.2f} · κλεισιμο · κελι = bets ανα βιβλιο · ROI · μοναδες · θετικες σεζον')
    print(f'   {"φιλτρο (edge στη ΝΙΚΗ)":26s} │ {"(1) " + ("−0.25" if sgn < 0 else "+0.25"):>30s} │ {"(2) απλη νικη":>30s} │ {"(3) DNB":>30s} │ αποτελεσμα Ν/Ι/Η · μεσες τιμες')
    for th in (None, .04, .10):
        y = y0 if th is None else y0[y0.e_win >= th]
        lab = 'ολα (χωρις μοντελο)' if th is None else f'edge νικης ≥{int(th * 100)}%'
        if not len(y): print(f'   {lab:26s} │ —'); continue
        print(f'   {lab:26s} │ {cell(y, "p_q")} │ {cell(y, "p_win")} │ {cell(y, "p_d")} │ '
              f'{100 * (y.res == "Ν").mean():.0f}/{100 * (y.res == "Ι").mean():.0f}/{100 * (y.res == "Η").mean():.0f}% · '
              f'{"−" if sgn < 0 else "+"}0.25 @{y.oq.mean():.2f} · νικη @{y.ow.mean():.2f} · DNB @{y.dnb.mean():.2f}')
    y = y0[y0.e_win >= .10]
    if len(y): print(f'   edge μοντελου (μεσος) στις περιπτωσεις «νικη ≥10%»: −/+0.25 {100 * y.e_q.mean():+.1f}% · νικη {100 * y.e_win.mean():+.1f}% · DNB {100 * y.e_d.mean():+.1f}%  '
                     f'(το μοντελο «βλεπει» αξια και στις τρεις; ποση;)')
