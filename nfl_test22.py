"""NFL τεστ 22 — CLV ανα κατηγορια: αρνητικα ή ατυχα; Picks απεναντι στην Pinnacle (2020-25), κλεισιμο = Pinnacle 30′ πριν.

CLV % (απλη μεθοδος, οπως Pick History): τιμη μας / τιμη κλεισιματος ιδιας πλευρας − 1, με το περιθωριο της Pinnacle.
  Αν αλλαξε η γραμμη: τιμη κλεισιματος μεταφρασμενη στη γραμμη μας = κλεισιμο × δικαιη(γραμμη μας)/δικαιη(γραμμη κλεισιματος),
  απο την πραγματικη κατανομη αποτελεσματων γυρω απο τη γραμμη κλεισιματος (με τα κλειδια 3/7/10, push).
  0% στην απλη μεθοδο = ζημια ολου του περιθωριου (~−2.4%)· νεκρα ≈ +2.5% CLV.
CLV π. = ποντοι που κινηθηκε η γραμμη υπερ μας ως το κλεισιμο.
Αναμ. ROI = αν το κλεισιμο (χωρις περιθωριο) ειναι η αληθεια, τι περιμενουμε απο τη δικη μας τιμη & γραμμη.
Διαφορα = πραγματικο − αναμενομενο, z = διαφορα / τυπικο σφαλμα: |z|<2 → μεσα στην τυχη.
  Θετικο CLV & αρνητικο ROI, z<0 → ΑΤΥΧΑ · αρνητικο CLV/αναμ. & αρνητικο ROI → ΠΡΑΓΜΑΤΙΚΑ αρνητικα.
"""
import sys
import numpy as np
import pandas as pd
import nfl_test4 as T4
import nfl_test20 as T20

S = list(range(2020, 2026))
sys.stdout.reconfigure(encoding='utf-8')


def add_close(z, kind, close):
    """z: picks απο T20.run. Προσθετει clv_pts, clv_pct, exp_roi απεναντι στο κλεισιμο της Pinnacle."""
    line, oP, oN, y = (('spread', 'h_dec', 'a_dec', 'result') if kind == 'm' else ('total', 'o_dec', 'u_dec', 'total'))
    c = close[['game_id', line, oP, oN]].rename(columns={line: 'Lc', oP: 'cp', oN: 'cn'})
    z = z.merge(c, on='game_id', how='inner').dropna(subset=['Lc', 'cp', 'cn', y]).copy()
    lo, hi = (-70, 70) if kind == 'm' else (0, 120)
    ks = np.arange(lo, hi + 1)
    res = (z[y] - z.Lc).values
    grid = np.arange(-60, 61)
    dens = T20.smooth_density(res, grid)
    exp = np.zeros(len(ks))
    for m in z.Lc.values:
        exp += np.interp(ks - m, grid, dens, left=0, right=0)
    exp /= exp.sum()
    obs = np.bincount(np.clip(z[y].astype(int).values - lo, 0, hi - lo), minlength=len(ks)) / len(z)
    w = np.clip(obs / np.clip(exp, 1e-9, None), 0.05, 5)
    out = {k: [] for k in ('clv_pct', 'exp_roi', 'p_close')}
    for L, Lc, cp, cn, sd, od_p, od_n in zip(z.L, z.Lc, z.cp, z.cn, z.side, z.op.fillna(1.909), z.on.fillna(1.909)):
        pk = np.interp(ks - Lc, grid, dens, left=0, right=0) * w
        pk = pk / pk.sum()
        push_c = pk[ks == Lc].sum()
        pv = (1 / cp) / (1 / cp + 1 / cn)              # χωρις περιθωριο στη γραμμη κλεισιματος
        up_c, dn_c = pv * (1 - push_c), (1 - pv) * (1 - push_c)
        if L < Lc:
            between = pk[(ks > L) & (ks <= Lc)].sum()
            up, dn = up_c + between, 1 - (up_c + between) - pk[ks == L].sum()
        elif L > Lc:
            between = pk[(ks >= Lc) & (ks < L)].sum()
            dn, up = dn_c + between, 1 - (dn_c + between) - pk[ks == L].sum()
        else:
            up, dn = up_c, dn_c
        up, dn = max(up, 1e-4), max(dn, 1e-4)
        if sd > 0:
            win, lose, win_c, lose_c, ours, co = up, dn, up_c, dn_c, od_p, cp
        else:
            win, lose, win_c, lose_c, ours, co = dn, up, dn_c, up_c, od_n, cn
        f_ours, f_close = 1 + lose / win, 1 + lose_c / win_c
        eq = co * f_ours / f_close
        out['clv_pct'].append(ours / eq - 1)
        out['exp_roi'].append(win * (ours - 1) - lose)
        out['p_close'].append(win_c / (win_c + lose_c))
    for k, v in out.items():
        z[k] = v
    z['clv_pts'] = (z.Lc - z.L) * z.side
    return z


def row(lab, d):
    if len(d) < 5:
        return f"  {lab:30} picks {len(d):4} (λιγα)"
    a, e = d.pnl.mean(), d.exp_roi.mean()
    se = d.pnl.std() / np.sqrt(len(d))
    win = (d.pnl > 0).sum() / max((d.pnl != 0).sum(), 1)
    z_ = (a - e) / se
    return (f"  {lab:30} picks {len(d):4} | ROI {100 * a:+6.1f}% καλ. {100 * win:4.1f}% | CLV {d.clv_pts.mean():+5.2f} π. {100 * d.clv_pct.mean():+5.1f}% "
            f"(θετικο {100 * (d.clv_pct > 0).mean():3.0f}%) | αναμ. {100 * e:+5.1f}% | διαφ. {100 * (a - e):+6.1f} z {z_:+.1f}")


def main():
    p = pd.read_csv('nfl_data/base5_preds.csv')
    o = pd.read_csv('nfl_data/pin_slots.csv')
    g = pd.read_csv('nfl_data/games.csv', low_memory=False)[['game_id', 'roof']]
    close = o[o.H == 'close']
    print('=== ΧΑΝΤΙΚΑΠ v3 (edge ≥6%) απεναντι στο κλεισιμο Pinnacle ===')
    for H, lb in (('wk', 'ΕΙΣΟΔΟΣ ΑΝΟΙΓΜΑ'), ('120', 'ΕΙΣΟΔΟΣ 5 ΜΕΡΕΣ'), ('72', 'ΕΙΣΟΔΟΣ 72ω'), ('24', 'ΕΙΣΟΔΟΣ 24ω*')):
        z = T20.run(p, 'm', 'mp', o, H=H)
        z = add_close(z[z.season.isin(S)], 'm', close)
        d = z[z.ev >= 0.06]
        fs = np.sign(d.L).replace(0, 1)
        fav = d.side == fs
        print(f'\n {lb}')
        for lab, m in (('ΟΛΑ', d.ev > -9), ('ΦΑΒΟΡΙ', fav), ('ΑΟΥΤΣΑΙΝΤΕΡ', ~fav), ('φαβορι εντος', fav & (d.side > 0)), ('φαβορι εκτος', fav & (d.side < 0)),
                       ('αουτσ. εντος', ~fav & (d.side > 0)), ('αουτσ. εκτος', ~fav & (d.side < 0)),
                       ('γραμμη 0-3 φαβορι', fav & (d.L.abs() < 3)), ('γραμμη 0-3 αουτσ.', ~fav & (d.L.abs() < 3)),
                       ('γραμμη 3-7 φαβορι', fav & d.L.abs().between(3, 6.99)), ('γραμμη 3-7 αουτσ.', ~fav & d.L.abs().between(3, 6.99)),
                       ('γραμμη 7+ φαβορι', fav & (d.L.abs() >= 7)), ('γραμμη 7+ αουτσ.', ~fav & (d.L.abs() >= 7))):
            print(row(lab, d[m]))
    print('\n=== ΣΥΝΟΛΑ απεναντι στο κλεισιμο Pinnacle (χωρις καιρο) ===')
    for H, lb in (('wk', 'ΕΙΣΟΔΟΣ ΑΝΟΙΓΜΑ'), ('120', 'ΕΙΣΟΔΟΣ 5 ΜΕΡΕΣ')):
        for name, kw, t in (('παλια τιμολογηση, edge ≥8% (πολλα over)', {}, 0.08), ('νεα v6, edge ≥6%', dict(use_emp=True, use_beta=True), 0.06),
                            ('νεα v6, edge ≥10%', dict(use_emp=True, use_beta=True), 0.10)):
            z = T20.run(p, 't', 'tp', o, H=H, **kw)
            z = add_close(z[z.season.isin(S)], 't', close).merge(g, on='game_id')
            d = z[z.ev >= t]
            dm = d.roof != 'outdoors'
            print(f'\n {lb} — {name}')
            for lab, m in (('ΟΛΑ', d.ev > -9), ('OVER', d.side > 0), ('UNDER', d.side < 0), ('over κλειστα', (d.side > 0) & dm), ('over ανοιχτα', (d.side > 0) & ~dm),
                           ('under κλειστα', (d.side < 0) & dm), ('under ανοιχτα', (d.side < 0) & ~dm)):
                print(row(lab, d[m]))
            ov = d[d.side > 0]
            if len(ov) >= 5:
                r = ov.total - ov.L
                print(f"   over: πραγμ − γραμμη μεσο {r.mean():+.2f} · διαμεσο {r.median():+.1f} | ανα σεζον ROI: " + ' '.join(f"{s % 100}:{100 * ov[ov.season == s].pnl.mean() if (ov.season == s).any() else 0:+.0f}" for s in S))
    # ελεγχος μεθοδου: τυφλα ολα τα ματς, ιδια γραμμη (κλεισιμο) → CLV 0, αναμ ≈ −περιθωριο/2
    z = T20.run(p, 'm', 'mp', o, H='close')
    z = add_close(z[z.season.isin(S)], 'm', close)
    print(f"\nΕΛΕΓΧΟΣ μεθοδου (εισοδος στο κλεισιμο, ολα τα ματς): CLV {z.clv_pts.mean():+.3f} π. {100 * z.clv_pct.mean():+.2f}% · αναμ. {100 * z.exp_roi.mean():+.2f}% (πρεπει ≈ −περιθωριο 2.4%) · πραγματικο ROI {100 * z.pnl.mean():+.1f}%")


if __name__ == '__main__':
    main()
