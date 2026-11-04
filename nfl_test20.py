"""NFL τεστ 20 — ΔΙΟΡΘΩΣΗ ΥΠΟΛΟΓΙΣΜΟΥ ΠΙΘΑΝΟΤΗΤΑΣ (γιατι χανουν τα over).

Ευρημα: η μηχανη προβλεπει τον ΜΕΣΟ ΟΡΟ, ενω το στοιχημα κρινεται στη ΔΙΑΜΕΣΟ. Τα συνολα εχουν μακρια δεξια ουρα
(ματς με 70+ ποντους): μεσο λαθος +0.05 αλλα διαμεσο −0.72. Η ομαλη κατανομη δινει στα over πιο πολλη πιθανοτητα απ' οση εχουν.
Δυο διορθωσεις, ολα LOSO (κατανομες/β απο τις αλλες σεζον):
  Δ1 ΚΑΤΑΝΟΜΗ: αντι για ομαλη γυρω απο το μοντελο, η ΠΡΑΓΜΑΤΙΚΗ κατανομη λαθους (πραγμ − μοντελο) των αλλων σεζον
     (εξομαλυμενη, κραταει την ασυμμετρια) × βαρη κλειδιων.
  Δ2 ΕΜΠΙΣΤΟΣΥΝΗ: η διαφωνια με τη γραμμη ειναι μερικως θορυβος (b<1). μ' = γραμμη + β(μοντελο − γραμμη), β = κλιση
     (πραγμ − γραμμη) ~ (μοντελο − γραμμη) στις αλλες σεζον (ιδια ωρα).
Μετραμε: προβλεπομενη vs πραγματικη νικη ανα πλευρα, ROI over/under, θετικες σεζον 2021-25. Χαντικαπ και συνολα, ανοιγμα εβδομαδας.
"""
import sys
import numpy as np
import pandas as pd
import nfl_test as T
import nfl_test4 as T4

S7, S5 = list(range(2019, 2026)), list(range(2021, 2026))
sys.stdout.reconfigure(encoding='utf-8')


def smooth_density(res, grid, bw=1.5):
    """Εξομαλυμενη πυκνοτητα (Gaussian kernel) των λαθων πανω σε πλεγμα ακεραιων."""
    h, e = np.histogram(res, bins=np.arange(grid[0] - 0.5, grid[-1] + 1.5), density=False)
    z = np.arange(-int(4 * bw), int(4 * bw) + 1)
    k = np.exp(-0.5 * (z / bw) ** 2)
    d = np.convolve(h, k, mode='same')
    return d / d.sum()


def probs(mu, L, ks, w, dens=None, grid=None, sd=None):
    if dens is None:
        z = (ks - mu) / sd
        pk = np.exp(-0.5 * z * z) * w
    else:
        pk = np.interp(ks - mu, grid, dens, left=0, right=0) * w
    pk = pk / pk.sum()
    return pk[ks > L].sum(), pk[ks == L].sum()


def run(p, kind, col, o, H='wk', use_emp=False, use_beta=False):
    line, oP, oN, y = (('spread', 'h_dec', 'a_dec', 'result') if kind == 'm' else ('total', 'o_dec', 'u_dec', 'total'))
    s = o[o.H == H][['game_id', line, oP, oN]].rename(columns={line: 'L', oP: 'op', oN: 'on'})
    z = p.merge(s, on='game_id').dropna(subset=['L', col]).copy()
    lo, hi = (-70, 70) if kind == 'm' else (0, 120)
    grid = np.arange(-60, 61)
    out = []
    for S in sorted(z.season.unique()):
        tr = p[(p.season != S) & p.season.between(2016, 2025)].dropna(subset=[col, y])
        res = (tr[y] - tr[col]).values
        sd = np.sqrt(np.mean(res ** 2))
        ks = np.arange(lo, hi + 1)
        if use_emp:
            dens = smooth_density(res, grid)
            exp = np.zeros(len(ks))
            for m in tr[col].values:
                exp += np.interp(ks - m, grid, dens, left=0, right=0)
            exp /= exp.sum()
            obs = np.bincount(np.clip(tr[y].astype(int).values - lo, 0, hi - lo), minlength=len(ks)) / len(tr)
            w = np.clip(obs / np.clip(exp, 1e-9, None), 0.05, 5)
        else:
            dens = None
            ks, w = T4.key_weights(tr[y].values, tr[col].values, sd, lo, hi)
        te = z[z.season == S].copy()
        mu = te[col].values
        if use_beta:
            trz = z[(z.season != S) & z.season.between(2016, 2025)]
            b = np.polyfit(trz[col] - trz.L, trz[y] - trz.L, 1)[0]
            mu = te.L.values + b * (mu - te.L.values)
        P = np.array([probs(m, l, ks, w, dens, grid, sd) for m, l in zip(mu, te.L)])
        te['pw'], te['pp'] = P[:, 0], P[:, 1]
        out.append(te)
    z = pd.concat(out)
    z['pl'] = 1 - z.pw - z.pp
    op, on = z.op.fillna(1.909).values, z.on.fillna(1.909).values
    ev_p, ev_n = z.pw * (op - 1) - z.pl, z.pl * (on - 1) - z.pw
    z['side'] = np.where(ev_p >= ev_n, 1, -1)
    z['ev'] = np.maximum(ev_p, ev_n)
    r = (z[y] - z.L) * z.side
    od = np.where(z.side > 0, op, on)
    z['pnl'] = np.where(r > 0, od - 1, np.where(r < 0, -1, 0))
    z['pred'] = np.where(z.side > 0, z.pw, z.pl)
    z['win'] = (r > 0).astype(float)
    return z


def show(lab, z, names=('OVER', 'UNDER')):
    h = z[z.season.between(2019, 2025)]
    print(f'\n {lab}')
    for t in (0.02, 0.04, 0.06, 0.08, 0.10):
        m = h.ev >= t
        per = {S: h[m & (h.season == S)].pnl.sum() for S in S7}
        n = int(m.sum())
        pos = sum(per[S] > 0 for S in S5)
        y26 = z[(z.season == 2026) & (z.ev >= t)]
        a, b = h[m & (h.side > 0)], h[m & (h.side < 0)]
        print(f"  edge ≥{int(t * 100):2}%: picks {n:4} ROI {100 * h[m].pnl.mean():+5.1f}% {pos}/5 · 2026 {len(y26):3}/{y26.pnl.sum():+5.1f}μ | "
              f"{names[0]} {len(a):3} {100 * a.pnl.mean():+5.1f}% (προβλ {100 * a.pred.mean():.0f}% πραγμ {100 * a.win.mean():.0f}%) · "
              f"{names[1]} {len(b):3} {100 * b.pnl.mean():+5.1f}% (προβλ {100 * b.pred.mean():.0f}% πραγμ {100 * b.win.mean():.0f}%) | "
              + ' '.join(f"{S % 100}:{100 * per[S] / max(int((m & (h.season == S)).sum()), 1):+.0f}%" for S in S7))


def main():
    p = pd.read_csv('nfl_data/base5_preds.csv')
    o = pd.read_csv('nfl_data/sbr_slots.csv'); o = o[o.book == 'cons']
    print('=== ΣΥΝΟΛΑ, ανοιγμα εβδομαδας (v4) ===')
    show('Σημερα: ομαλη κατανομη', run(p, 't', 'tp', o))
    show('Δ1 πραγματικη κατανομη (ασυμμετρη)', run(p, 't', 'tp', o, use_emp=True))
    show('Δ2 μονο εμπιστοσυνη β', run(p, 't', 'tp', o, use_beta=True))
    show('Δ1 + Δ2', run(p, 't', 'tp', o, use_emp=True, use_beta=True))
    print('\n=== ΧΑΝΤΙΚΑΠ, ανοιγμα εβδομαδας (v3) ===')
    nm = ('ΓΗΠΕΔΟΥΧΟΣ', 'ΦΙΛΟΞΕΝ.')
    show('Σημερα: ομαλη κατανομη', run(p, 'm', 'mp', o), nm)
    show('Δ1 πραγματικη κατανομη', run(p, 'm', 'mp', o, use_emp=True), nm)
    show('Δ2 μονο εμπιστοσυνη β', run(p, 'm', 'mp', o, use_beta=True), nm)
    show('Δ1 + Δ2', run(p, 'm', 'mp', o, use_emp=True, use_beta=True), nm)


if __name__ == '__main__':
    main()
