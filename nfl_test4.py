"""NFL τεστ 4: (α) ειδικες ομαδες στη μηχανη, (β) τιμολογηση με «κλειδια» (3, 7, 10 / 41, 44, 47), LOSO 2016-25 (+2026).

Νεα βαση = τεστ 2 (ομαδες + QB) + success rate (εγκριθηκε 3/11).
(α) + rating καθαρου EPA ειδικων ομαδων (FG, XP, punt, kickoff) ανα ματς → st_net_diff στο χαντικαπ.
    Κριτηριο: RMSE χαντικαπ καλυτερη σε ≥4/5 σεζον 2021-25.
(β) Πως διαλεγουμε pick απο το ιδιο μοντελο:
    Π  ποντοι      : |μοντελο − γραμμη| ≥ X (οπως ως τωρα)
    Κ  κανονικη    : πιθανοτητα καλυψης απο ομαλη κατανομη (σ = σφαλμα μοντελου) → EV ≥ Y%
    ΚΒ κλειδια-βαρη: ομαλη κατανομη × βαρος καθε αποτελεσματος (3, 7... πιο συχνα) απο ολα τα ματς εκπαιδευσης (σταθερο)
    ΚΛ κλειδια-τοπικα: πιθανοτητα καλυψης απο ΠΡΑΓΜΑΤΙΚΗ κατανομη αποτελεσματων ματς με παρομοια γραμμη (περιεχει
                     το βαρος του 3/7 και τις ισοπαλιες-push) → EV ≥ Y%
    Κριτηρια: ακριβεια πιθανοτητας καλυψης (log-loss) ΚΛ < Κ σε ≥4/5 σεζον · ROI ΚΛ vs Κ σε ιδιο ογκο picks.
    Ολα με αποδοσεις κλεισιματος (nflverse), push = επιστροφη.
"""
import numpy as np
import pandas as pd
from math import erf, sqrt
import nfl_model as M
import nfl_qb as Q
import nfl_mech as X
import nfl_test as T

FM = ['cl_epa_diff', 'pts_diff', 'qb_d', 'cl_sr_diff']
FT = ['pts_sum', 'cl_epa_sum', 'plays_sum', 'qb_s', 'cl_sr_sum']
S5 = list(range(2021, 2026))
S10 = list(range(2016, 2026))
EVS = [0.02, 0.04, 0.06, 0.08]


def ncdf(z):
    return 0.5 * (1 + erf(z / sqrt(2)))


def probs_normal(mu, L, sd):
    """P(νικη θετικης πλευρας), P(push) για αποτελεσμα ~ N(mu, sd) στρογγυλεμενο σε ακεραιο."""
    if float(L).is_integer():
        pw = 1 - ncdf((L + 0.5 - mu) / sd)
        pp = ncdf((L + 0.5 - mu) / sd) - ncdf((L - 0.5 - mu) / sd)
    else:
        pw, pp = 1 - ncdf((L - mu) / sd), 0.0
    return pw, pp


def probs_emp(mu, L, lines, outcomes, w0=1.0, nmin=150):
    """Πραγματικη κατανομη: αποτελεσματα ματς (εκπαιδευσης) με γραμμη κλεισιματος κοντα στο mu (χωρις μετατοπιση) —
    κραταει το σχημα (κλειδια 3/7, push) γυρω απο το αναμενομενο."""
    w = w0
    while True:
        sel = np.abs(lines - mu) <= w
        if sel.sum() >= nmin or w > 8:
            break
        w += 0.5
    r = outcomes[sel]
    pw, pp = np.mean(r > L), np.mean(r == L)
    return pw, pp


def key_weights(outcomes, mus, sd, lo, hi):
    """Βαρος καθε ακεραιου αποτελεσματος: πραγματικη συχνοτητα / συχνοτητα που θα εδινε η ομαλη κατανομη (ιδια ματς).
    >1 = «κλειδι» (π.χ. 3, 7), <1 = σπανιο (π.χ. 0, 1). Μετριεται σε ~2.400 ματς εκπαιδευσης → μικρος θορυβος."""
    ks = np.arange(lo, hi + 1)
    exp = np.zeros(len(ks))
    for m in mus:
        z = (ks - m) / sd
        exp += np.exp(-0.5 * z * z)
    exp /= exp.sum()
    obs = np.bincount(np.clip(outcomes.astype(int) - lo, 0, hi - lo), minlength=len(ks)) / len(outcomes)
    return ks, np.clip(obs / np.clip(exp, 1e-9, None), 0.05, 5)


def probs_key(mu, L, sd, ks, w):
    z = (ks - mu) / sd
    pk = np.exp(-0.5 * z * z) * w
    pk /= pk.sum()
    return pk[ks > L].sum(), pk[ks == L].sum()


def price(te, tr, kind):
    """Προσθετει p_w/p_p (θετικη πλευρα) για Κ και ΚΛ."""
    if kind == 'm':
        mu, L, y = te.mp.values, te.spread_line.values, te.result.values
        trl, tro, trm = tr.spread_line.values, tr.result.values, tr.mp.values
    else:
        mu, L, y = te.tp.values, te.total_line.values, te.total.values
        trl, tro, trm = tr.total_line.values, tr.total.values, tr.tp.values
    sd = np.sqrt(np.mean((tro - trm) ** 2))
    N = np.array([probs_normal(m, l, sd) for m, l in zip(mu, L)])
    E = np.array([probs_emp(m, l, trl, tro) for m, l in zip(mu, L)])
    lo, hi = (-70, 70) if kind == 'm' else (0, 120)
    ks, w = key_weights(tro, trm, sd, lo, hi)
    K = np.array([probs_key(m, l, sd, ks, w) for m, l in zip(mu, L)])
    return N, E, K, y, L


def ev_pick(P, L, y, o_pos, o_neg, thr):
    pw, pp = P[:, 0], P[:, 1]
    pl = 1 - pw - pp
    ev_pos = pw * (o_pos - 1) - pl
    ev_neg = pl * (o_neg - 1) - pw
    side = np.where(ev_pos >= ev_neg, 1, -1)
    ev = np.maximum(ev_pos, ev_neg)
    pick = ev >= thr
    r = (y - L) * side
    o = np.where(side > 0, o_pos, o_neg)
    pnl = np.where(r > 0, o - 1, np.where(r < 0, -1, 0))
    return pick, pnl


def logloss(P, y, L):
    pw, pp = P[:, 0], P[:, 1]
    ok = y != L
    q = np.clip(pw[ok] / np.clip(1 - pp[ok], 1e-9, None), 1e-4, 1 - 1e-4)
    win = (y[ok] > L[ok]).astype(float)
    return -np.mean(win * np.log(q) + (1 - win) * np.log(1 - q))


def main():
    g, off = M.load()
    q = Q.load_qb()
    base = X.frame(g, off, q, stats=('cl_epa', 'pts', 'plays', 'cl_sr'))
    st = X.frame(g, off, q, stats=('cl_epa', 'pts', 'plays', 'cl_sr', 'st_net'))
    pb = X.run(base, FM, FT)
    ps = X.run(st, FM + ['st_net_diff'], FT)
    print('=== (α) ΕΙΔΙΚΕΣ ΟΜΑΔΕΣ ===')
    print(f"{'σεζον':6} χαντ RMSE βαση / +ειδικες / αγορα")
    better = []
    for S in range(2016, 2027):
        a, b = pb[pb.season == S], ps[ps.season == S]
        r1, r2 = np.sqrt(np.mean((a.result - a.mp) ** 2)), np.sqrt(np.mean((b.result - b.mp) ** 2))
        rk = np.sqrt(np.mean((a.result - a.spread_line) ** 2))
        better.append((S, r2 < r1))
        print(f"{S:6} {r1:6.3f} / {r2:6.3f} / {rk:6.3f}  {'✓' if r2 < r1 else '✗'}")
    for lab, p in (('βαση', pb), ('+ειδικες', ps)):
        a = p[p.season <= 2025]
        e = T.evaluate(a, a.mp.values, a.tp.values)
        n, pl = e['roi_m'][2.5]
        print(f"  {lab}: 2016-25 RMSE {e['rmse_m']:.3f} b {e['b_m']:+.2f} · ROI ≥2.5 π. {n} picks {100 * pl / n:+.1f}%")
    print(f"  καλυτερες σεζον: 2021-25 {sum(b for s, b in better if s in S5)}/5 · 2016-25 {sum(b for s, b in better if s in S10)}/10")
    # συντελεστης
    tr = st[st.season <= 2025]
    c = T.ols(tr, FM + ['st_net_diff'], 'result')
    print('  συντελεστες (σταθ, epa, ποντοι, QB, SR, ειδικες):', np.round(c, 3))

    use = ps if sum(b for s, b in better if s in S5) >= 4 else pb
    print('\n=== (β) ΤΙΜΟΛΟΓΗΣΗ — μοντελο:', 'βαση+ειδικες' if use is ps else 'βαση', '===')
    for kind, lab, op, on, thrP in (('m', 'ΧΑΝΤΙΚΑΠ', 'home_spread_odds', 'away_spread_odds', [1.5, 2.5, 3.5]),
                                    ('t', 'ΣΥΝΟΛΑ', 'over_odds', 'under_odds', [2, 3, 4])):
        rows = {}
        for S in range(2016, 2027):
            te = use[use.season == S]
            tr = use[(use.season != S) & (use.season <= 2025)]
            N, E, K, y, L = price(te, tr, kind)
            o_pos, o_neg = T.dec(te[op].values), T.dec(te[on].values)
            mu = te.mp.values if kind == 'm' else te.tp.values
            r = dict(ll_N=logloss(N, y, L), ll_E=logloss(E, y, L), ll_K=logloss(K, y, L))
            for t in thrP:
                pick = np.abs(mu - L) >= t
                side = np.sign(mu - L)
                rr = (y - L) * side
                o = np.where(side > 0, o_pos, o_neg)
                pnl = np.where(rr > 0, o - 1, np.where(rr < 0, -1, 0))
                r[('Π', t)] = (pick.sum(), pnl[pick].sum())
            for nm, P in (('Κ', N), ('ΚΛ', E), ('ΚΒ', K)):
                for t in EVS:
                    pick, pnl = ev_pick(P, L, y, o_pos, o_neg, t)
                    r[(nm, t)] = (pick.sum(), pnl[pick].sum())
            rows[S] = r
        print(f'\n{lab}: log-loss πιθανοτητας καλυψης (μικροτερο = καλυτερο) Κ / ΚΛ')
        print('  ' + ' · '.join(f"{S % 100}: {rows[S]['ll_N']:.4f}/{rows[S]['ll_E']:.4f}{'✓' if rows[S]['ll_E'] < rows[S]['ll_N'] else '✗'}" for S in rows))
        print('  ΚΒ (ομαλη × βαρος κλειδιων): ' + ' · '.join(f"{S % 100}: {rows[S]['ll_K']:.4f}{'✓' if rows[S]['ll_K'] < rows[S]['ll_N'] else '✗'}" for S in rows))
        print(f"  ΚΒ καλυτερη απο Κ: 2021-25 {sum(rows[S]['ll_K'] < rows[S]['ll_N'] for S in S5)}/5 · 2016-25 {sum(rows[S]['ll_K'] < rows[S]['ll_N'] for S in S10)}/10")
        print(f"  ΚΛ καλυτερη: 2021-25 {sum(rows[S]['ll_E'] < rows[S]['ll_N'] for S in S5)}/5 · 2016-25 {sum(rows[S]['ll_E'] < rows[S]['ll_N'] for S in S10)}/10")
        keys = [k for k in rows[2016] if isinstance(k, tuple)]
        print(f"  {'κανονας':12} 2016-25 picks  ROI   | 2021-25 picks  ROI  θετικες | 2026 picks μον.")
        for k in keys:
            n10 = sum(rows[S][k][0] for S in S10); p10 = sum(rows[S][k][1] for S in S10)
            n5 = sum(rows[S][k][0] for S in S5); p5 = sum(rows[S][k][1] for S in S5)
            pos = sum(rows[S][k][1] > 0 for S in S5)
            lab2 = f"{k[0]} ≥{k[1]}" + ('π' if k[0] == 'Π' else '')
            if k[0] != 'Π':
                lab2 = f"{k[0]} EV≥{int(k[1] * 100)}%"
            print(f"  {lab2:12} {n10:6} {100 * p10 / max(n10, 1):+6.1f}% | {n5:6} {100 * p5 / max(n5, 1):+6.1f}%  {pos}/5   | {rows[2026][k][0]:4} {rows[2026][k][1]:+.1f}")
    use.to_csv('nfl_data/test4_preds.csv', index=False)


if __name__ == '__main__':
    main()
