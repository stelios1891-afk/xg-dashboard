"""NFL τεστ 14 — ΑΦΕΤΗΡΙΑ Β: τα win totals ΜΕΣΑ στις δυναμεις (οπως NBA), αντι για χωριστο ορο στο τελος. Χαντικαπ, βαση v3.

Σημερα: οι δυναμεις καθε ομαδας «μαζευονται» προς τον μεσο ορο (0) και τα win totals μπαινουν χωριστα στον τελικο
μετασχηματισμο (wt_d × K/(K+n)).
Νεο: οι δυναμεις μαζευονται προς ΣΤΟΧΟ = αυτο που «λενε» τα win totals της ομαδας για καθε μεγεθος
(EPA, ποντοι, success rate, ειδικες· ρυθμος = 0).
  Κλιμακα: για καθε μεγεθος, κλιση (δυναμη τελους σεζον ~ win totals πριν τη σεζον) — μετρημενη στις ΑΛΛΕΣ σεζον.
  α = ποσο εμπιστευομαστε τον στοχο (0.5/1/1.5) · m = ποσο δυνατο το μαζεμα (λ × 1/2/4: περισσοτερο = πιο αργα φευγει απο τον στοχο)
Παραλλαγες: Β1 στοχος μεσα, ΧΩΡΙΣ χωριστο ορο · Β2 στοχος μεσα ΚΑΙ χωριστος ορος.
Κριτηριο: RMSE καλυτερη απο βαση v3 σε ≥4/5 σεζον 2021-25 (ολη η σεζον) — και ξεχωριστα εβδ 1-6.
"""
import json, sys
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_qb as Q
import nfl_engine as E
import nfl_grid as G
import nfl_test8 as T8

S5, S10 = G.S5, G.S10
STATS = ('EPA', 'pts', 'plays', 'SR', 'st_net')
sys.stdout.reconfigure(encoding='utf-8')


def season_end_ratings(off, p):
    """Δυναμεις τελους καθε σεζον μονο απο τα ματς της (χωρις σβησιμο, χωρις στοχο) → για την κλιμακα."""
    o = off.copy()
    o['EPA'], o['SR'] = o['epa'], o['sr']
    rows = []
    for S in range(2015, 2026):
        tend = (S - 2015) * 30 + 23
        R = E.fit(o, tend, S, HL=1000, PREV=1, lam_o=p['lam_o'], lam_d=p['lam_d'], stats=STATS, sos=p['sos'],
                  nseas=0, home=False)
        for s, (mu, h, O, Dd) in R.items():
            for t in O:
                rows.append(dict(season=S, team=t, stat=s, O=O[t], D=Dd[t]))
    return pd.DataFrame(rows)


def make_prior(er, alpha):
    w = pd.read_csv('nfl_data/win_totals.csv')
    w['wc'] = w.wpct - w.groupby('season').wpct.transform('mean')
    x = er.merge(w[['season', 'team', 'wc']], on=['season', 'team'])
    slopes = {}
    for S in range(2015, 2028):
        tr = x[(x.season != S) & (x.season <= 2025)]
        slopes[S] = {s: (np.polyfit(d.wc, d.O, 1)[0], np.polyfit(d.wc, d.D, 1)[0]) for s, d in tr.groupby('stat')}
    wm = {S: d.set_index('team').wc.to_dict() for S, d in w.groupby('season')}

    def prior(S):
        if S not in wm or S not in slopes:
            return None
        out = {}
        for s in STATS:
            if s == 'plays':
                continue
            a, d = slopes[S][s]
            out[s] = ({t: alpha * a * v for t, v in wm[S].items()}, {t: alpha * d * v for t, v in wm[S].items()})
        return out
    return prior, slopes


def main():
    g, off = M.load()
    q = Q.load_qb()
    tg = E.qb_open_targets(g)
    p = json.load(open('nfl_data/base3_params.json'))['m']
    er = season_end_ratings(off, p)
    _, sl = make_prior(er, 1.0)
    print('κλιμακα (ολες οι σεζον εκτος 2016): ανα +0.1 wpct (≈ +1.7 νικες) η δυναμη τελους σεζον αλλαζει κατα',
          {s: (round(a / 10, 3), round(d / 10, 3)) for s, (a, d) in sl[2016].items()}, '(επιθεση, αμυνα)')
    Fw = [G.FM0 + [f'wt_d_{K}'] for K in T8.KS]
    F0 = [G.FM0]

    def run(extra, Fs):
        pp = dict(p)
        cfg_extra = {k: v for k, v in extra.items() if k not in ('alpha', 'm')}
        if 'm' in extra:
            pp['lam_o'], pp['lam_d'] = p['lam_o'] * extra['m'], p['lam_d'] * extra['m']
        if 'alpha' in extra:
            cfg_extra['prior'] = make_prior(er, extra['alpha'])[0]
        cfg = {k: pp[k] for k in ('HL', 'PREV', 'lam_o', 'lam_d', 'HLp', 'home')}
        cfg['sos'] = pp['sos']
        cfg.update(cfg_extra)
        feats = E.build(g, off, cfg, pp['win'])
        qbf = Q.qb_features(g, q, HLQ=pp['HLQ'], N0=pp['N0'], M0=pp['M0'], HL=pp['HL'], PREV=pp['PREV'], target=tg)
        f = G.frame(g, feats, qbf)
        pr = T8.loso(f, 'result', Fs)
        e2 = (f.result - pr) ** 2
        return np.sqrt(e2.groupby(f.season).mean()), np.sqrt(e2[f.wk <= 6].groupby(f.season[f.wk <= 6]).mean())

    rb, rb6 = run({}, Fw)
    print(f"\n  {'παραλλαγη':38} RMSE ολη καλυτ.21-25 16-25 | εβδ1-6 καλυτ.21-25 16-25 | 2026")
    print(f"  {'βαση v3 (χωριστος ορος)':38} {np.sqrt(np.mean(rb[S10] ** 2)):.3f}   —          | {np.sqrt(np.mean(rb6[S10] ** 2)):.3f}   —          | {rb[2026]:.3f}")
    rows = []
    for lab, Fs, keep in (('Β1 στοχος μεσα, χωρις ορο', F0, False), ('Β2 στοχος μεσα + ορος', Fw, True)):
        for a in (0.5, 1.0, 1.5):
            for m in (1, 2, 4):
                r, r6 = run({'alpha': a, 'm': m}, Fs)
                name = f'{lab} α{a} m{m}'
                rows.append((name, r, r6))
                print(f"  {name:38} {np.sqrt(np.mean(r[S10] ** 2)):.3f}   {sum(r[s] < rb[s] for s in S5)}/5 {sum(r[s] < rb[s] for s in S10):2}/10 |"
                      f" {np.sqrt(np.mean(r6[S10] ** 2)):.3f}   {sum(r6[s] < rb6[s] for s in S5)}/5 {sum(r6[s] < rb6[s] for s in S10):2}/10 | {r[2026]:.3f}", flush=True)
    r, r6 = run({}, F0)
    print(f"  {'(ελεγχος) καθολου win totals':38} {np.sqrt(np.mean(r[S10] ** 2)):.3f}   {sum(r[s] < rb[s] for s in S5)}/5 {sum(r[s] < rb[s] for s in S10):2}/10 |"
          f" {np.sqrt(np.mean(r6[S10] ** 2)):.3f}   {sum(r6[s] < rb6[s] for s in S5)}/5 | {r[2026]:.3f}")


if __name__ == '__main__':
    main()
