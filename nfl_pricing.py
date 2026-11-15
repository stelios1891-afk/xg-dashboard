"""NFL τιμολογηση ΣΥΝΟΛΩΝ (βαση v6, Στελιος 4/11): πιθανοτητα νικης με Δ1 + Δ2 του τεστ 20.

  Δ1 πραγματικη (ασυμμετρη) κατανομη λαθους μοντελου, αντι για ομαλη — η μηχανη δινει μεσο ορο, το στοιχημα κρινεται στη διαμεσο
  Δ2 μ' = γραμμη + β(μοντελο − γραμμη) — η διαφωνια μετραει οσο εχει αποδειχθει οτι αξιζει
Η μηχανη (προβλεψη συνολου) ΔΕΝ αλλαζει. Κατανομη και β μετριουνται στις αλλες σεζον (LOSO).

  python nfl_pricing.py   → nfl_data/base6_totals.csv (ανα ματς & ωρα: γραμμη, πλευρα, προβλεπομενη νικη, edge, αποτελεσμα)
"""
import sys
import numpy as np
import pandas as pd
import nfl_test20 as T20

SLOTS = (('wk', 'tp'), ('120', 'tp'), ('72', 'n72'), ('24', 'n24'), ('3', 'n3'), ('close', 'n3'))
S7, S5 = list(range(2019, 2026)), list(range(2021, 2026))


def price_totals(p, col, o, H):
    return T20.run(p, 't', col, o, H=H, use_emp=True, use_beta=True)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    p = pd.read_csv('nfl_data/base5_preds.csv')
    for k, d in (('n72', 'tp_d3'), ('n24', 'tp_d1'), ('n3', 'tp_d0')):
        p[k] = p[d].fillna(p.tp_wx)            # πριν το 2024 δεν υπαρχει προγνωση: πραγματικος καιρος (αισιοδοξο)
    o = pd.read_csv('nfl_data/sbr_slots.csv')
    o = o[o.book == 'cons']
    out = []
    for H, col in SLOTS:
        new = price_totals(p, col, o, H)
        old = T20.run(p, 't', col, o, H=H)
        rows = []
        for lab, z in (('παλια τιμολογηση', old), ('ΝΕΑ τιμολογηση', new)):
            for t in (0.08, 0.10):
                # απο τις 3 μερες και μετα μονο 2024-26 ειναι τιμια (υπαρχει προγνωση)
                seas = range(2019, 2026) if col == 'tp' else range(2024, 2026)
                m = (z.ev >= t) & z.season.isin(list(seas))
                y26 = z[(z.ev >= t) & (z.season == 2026)]
                ov, un = z[m & (z.side > 0)], z[m & (z.side < 0)]
                pos = sum(z.pnl[m & (z.season == S)].sum() > 0 for S in seas)
                rows.append(f"   {lab:17} ≥{int(t * 100):2}%: picks {int(m.sum()):4} ROI {100 * z.pnl[m].mean():+6.1f}% · θετικες {pos}/{len(seas)} · OVER {len(ov):3} {100 * ov.pnl.mean() if len(ov) else 0:+6.1f}% · UNDER {len(un):3} {100 * un.pnl.mean() if len(un) else 0:+6.1f}% · 2026 {len(y26):2}/{y26.pnl.sum():+5.1f}μ")
        print(f"\n{H} ({'2019-25' if col == 'tp' else '2024-25, τιμια προγνωση'}):")
        print('\n'.join(rows))
        out.append(new.assign(H=H, model=new[col])[['game_id', 'season', 'wk', 'H', 'L', 'model', 'side', 'pred', 'ev', 'pnl', 'total']])
    pd.concat(out).to_csv('nfl_data/base6_totals.csv', index=False)
    print('\nαποθηκευτηκε nfl_data/base6_totals.csv')


if __name__ == '__main__':
    main()
