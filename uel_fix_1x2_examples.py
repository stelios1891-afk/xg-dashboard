"""uel_fix_1x2_examples.py — 15/10/2026 (Στελιος: «στειλε μου τα παραδειγματα Liverpool και Leverkusen σε τιμες 1Χ2: μοντελο πριν, μοντελο μετα
με τη διορθωση και αγορα — φαινεται οτι η διορθωση κατεβασε παρα πολυ αυτες τις ομαδες»).
Ολα τα ματς Europa League των Liverpool & Bayer Leverkusen (καθε κατηγορια) 2223-2526: δικαιες αποδοσεις 1-Χ-2 του σημερινου μοντελου, του
διορθωμενου (ΒΕ, LOSO παραμετροι της σεζον) και της ΑΓΟΡΑΣ. ΑΓΟΡΑ: δεν εχουμε ιστορικες τιμες 1Χ2 για αυτα τα ματς → 1Χ2 που ΒΓΑΙΝΕΙ απο το
ασιατικο χαντικαπ κλεισιματος (Crown, αλλιως SBOBET: γραμμη+αποδοση → διαφορα γκολ, ιδιο συνολο γκολ με το μοντελο, ισοπαλιες ×0.85).
"""
import sys
exec(open('uel_fix_cut_picks.py', encoding='utf-8').read().split("xa_ = x[x.cat == 'A']")[0])
def p3(lh, la):
    D_ = ES.eu_dist(max(lh, .05), max(la, .05), 0.85)
    p1 = sum(p for k, p in D_.items() if k > 0); px = D_.get(0, 0.0); return p1, px, 1 - p1 - px
od = lambda p: f'{1 / p:5.2f}' if p > 0.005 else '  >99'
for team in ('Liverpool', 'Bayer Leverkusen'):
    print(f'\n{"=" * 118}\n{team.upper()} — Europa League · δικαιες αποδοσεις 1 - Χ - 2 (γηπεδουχος / ισοπαλια / φιλοξενουμενος)')
    print(f'   {"σεζ":4s} {"ματς":38s} {"κατ":3s} │ {"ΜΟΝΤΕΛΟ ΠΡΙΝ":^19s} │ {"ΜΕΤΑ τη διορθωση":^19s} │ {"ΑΓΟΡΑ (απο χαντικαπ)":^20s} │ γραμμη │ σκορ')
    for r in x.itertuples():
        hn, an = NM.get(int(r.i), ('?', '?'))
        if team not in (hn, an): continue
        i = int(r.i); mid = str(MIDS[i])
        s = snapT(mid, 'Crown', 0) or snapT(mid, 'SBOBET', 0)
        a0 = p3(r.lh, r.la); a1 = p3(r.lh3, r.la3)
        if s:
            mk = implied_margin(i, *s); T = r.lh + r.la; a2 = p3((T + mk) / 2, (T - mk) / 2); ln = f'{s[0]:+.2f}'
        else:
            a2 = (np.nan, np.nan, np.nan); ln = '  —  '
        f3 = lambda a: ' '.join(od(p) for p in a) if np.isfinite(a[0]) else '        —        '
        print(f'   {r.sea:4s} {(hn + " - " + an)[:38]:38s} {r.cat:3s} │ {f3(a0)} │ {f3(a1)} │ {f3(a2):>20s} │ {ln:>6s} │ {int(GH[i])}-{int(GA[i])}')
