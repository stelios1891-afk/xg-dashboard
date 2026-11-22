"""NFL τεστ 21 — ΑΠΕΝΑΝΤΙ ΣΤΗΝ PINNACLE (στιγμιοτυπα TOA, nfl_pin_build.py), 2020-2025. Το 2026 δεν εχει κατεβει απο το TOA.

Συνολα: μηχανη v4 (ανοιγμα/5 μερες) · v5 με προγνωση κοντα στο ματς (τιμια μονο 2024-25) · τιμολογηση v6 (ασυμμετρη κατανομη + β)
       και για συγκριση η παλια. Χαντικαπ: v3, τιμολογηση ομαλη × κλειδια.
Ιδιες πραγματικες αποδοσεις Pinnacle της ωρας. Κριτηριο: ROI θετικο σε ≥4/5 σεζον 2021-25.
Συγκριση ΙΔΙΩΝ ματς: Pinnacle vs μεση γραμμη αμερικανικων βιβλιων (SBR) στο ανοιγμα.
ΠΡΟΣΟΧΗ: «wk» = το πρωτο στιγμιοτυπο 16:00 UTC (18:00/19:00 Ελλαδας) με Pinnacle μετα το προηγουμενο ματς.
"""
import sys
import numpy as np
import pandas as pd
import nfl_test20 as T20

S5 = list(range(2021, 2026))
sys.stdout.reconfigure(encoding='utf-8')


def report(lab, z, y, col, seasons, thr=(0.04, 0.06, 0.08, 0.10)):
    h = z[z.season.isin(seasons)]
    rl = np.sqrt(np.mean((h[y] - h.L) ** 2)); rm = np.sqrt(np.mean((h[y] - h[col]) ** 2))
    b = np.polyfit(h[col] - h.L, h[y] - h.L, 1)[0]
    print(f'\n {lab}: {len(h)} ματς · λαθος γραμμη {rl:.2f} / μοντελο {rm:.2f} · b {b:+.2f}')
    for t in thr:
        m = h.ev >= t
        per = {S: (int((m & (h.season == S)).sum()), h.pnl[m & (h.season == S)].sum()) for S in seasons}
        pos = sum(per[S][1] > 0 for S in S5 if S in per)
        a, c = h[m & (h.side > 0)], h[m & (h.side < 0)]
        print(f"  edge ≥{int(t * 100):2}%: picks {int(m.sum()):4} ROI {100 * h.pnl[m].mean():+6.1f}% · {h.pnl[m].sum():+6.1f}μ · θετικες 21-25 {pos}/{sum(1 for S in S5 if S in per)} | "
              f"+ πλευρα {len(a):3} {100 * a.pnl.mean() if len(a) else 0:+6.1f}% · − πλευρα {len(c):3} {100 * c.pnl.mean() if len(c) else 0:+6.1f}% | "
              + ' '.join(f"{S % 100}:{per[S][0]}/{100 * per[S][1] / max(per[S][0], 1):+.0f}%" for S in seasons))


def main():
    p = pd.read_csv('nfl_data/base5_preds.csv')
    for k, d in (('n72', 'tp_d3'), ('n24', 'tp_d1'), ('n3', 'tp_d0')):
        p[k] = p[d].fillna(p.tp_wx)
    o = pd.read_csv('nfl_data/pin_slots.csv')
    s = pd.read_csv('nfl_data/sbr_slots.csv'); s = s[s.book == 'cons']
    S20 = list(range(2020, 2026))
    print('=== ΣΥΝΟΛΑ απεναντι στην PINNACLE (+ πλευρα = OVER, − = UNDER) ===')
    for H, col, seas, lb in (('wk', 'tp', S20, 'ανοιγμα, χωρις καιρο'), ('120', 'tp', S20, '5 μερες, χωρις καιρο'),
                             ('72', 'n72', [2024, 2025], '72ω, προγνωση 3μ (τιμια)'), ('24', 'n24', [2024, 2025], '24ω*, προγνωση 1μ (τιμια)'),
                             ('3', 'n3', [2024, 2025], '3ω, προγνωση ιδιας μερας (τιμια)'), ('close', 'n3', [2024, 2025], '30′, προγνωση ιδιας μερας (τιμια)')):
        report(f'{lb} — ΝΕΑ τιμολογηση', T20.run(p, 't', col, o, H=H, use_emp=True, use_beta=True), 'total', col, seas)
        report(f'{lb} — παλια τιμολογηση', T20.run(p, 't', col, o, H=H), 'total', col, seas)
    print('\n=== ΧΑΝΤΙΚΑΠ απεναντι στην PINNACLE, v3 (+ πλευρα = γηπεδουχος, − = φιλοξενουμενος) ===')
    for H, lb in (('wk', 'ανοιγμα'), ('120', '5 μερες'), ('72', '72ω'), ('24', '24ω*'), ('3', '3ω'), ('close', '30′')):
        report(lb, T20.run(p, 'm', 'mp', o, H=H), 'result', 'mp', S20)
    print('\n=== ΙΔΙΑ ΜΑΤΣ στο ανοιγμα: PINNACLE vs αμερικανικα βιβλια (SBR) ===')
    for kind, y, col, lab, kw in (('t', 'total', 'tp', 'ΣΥΝΟΛΑ νεα τιμολογηση', dict(use_emp=True, use_beta=True)), ('m', 'result', 'mp', 'ΧΑΝΤΙΚΑΠ', {})):
        zp = T20.run(p, kind, col, o, H='wk', **kw)
        zs = T20.run(p, kind, col, s, H='wk', **kw)
        ids = set(zp[zp.season.isin(S20)].game_id) & set(zs[zs.season.isin(S20)].game_id)
        zp, zs = zp[zp.game_id.isin(ids)], zs[zs.game_id.isin(ids)]
        d = zp[['game_id', 'L']].merge(zs[['game_id', 'L']], on='game_id', suffixes=('_p', '_s'))
        print(f"  {lab}: ιδια ματς {len(ids)} · μεση |Pinnacle − SBR| γραμμη {(d.L_p - d.L_s).abs().mean():.2f} π. · μεση αποδοση Pinnacle {zp[['op', 'on']].mean().mean():.3f} vs SBR {zs[['op', 'on']].mean().mean():.3f}")
        for t in (0.06, 0.08, 0.10):
            a, b = zp[zp.ev >= t], zs[zs.ev >= t]
            print(f"    edge ≥{int(t * 100):2}%: Pinnacle {len(a):4} picks ROI {100 * a.pnl.mean():+6.1f}% · SBR {len(b):4} picks ROI {100 * b.pnl.mean():+6.1f}%")
    o2 = o[o.H == 'wk']
    print(f"\n  ωρα στιγμιοτυπου «ανοιγμα» Pinnacle: διαμεσος {o2.h_age.median():.0f}ω πριν την εναρξη · 25-75%: {o2.h_age.quantile(.25):.0f}-{o2.h_age.quantile(.75):.0f}ω")


if __name__ == '__main__':
    main()
