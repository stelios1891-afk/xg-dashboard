"""NFL διαγνωση βασης v2: ΠΟΥ χανει το μοντελο και ΓΙΑΤΙ (οπως τενις / ευρωπαικα).

Βαση v2 (QB ανοιγματος, LOSO): χαντ mp, συνολα tp. Γραμμες SBR (διαμεσος βιβλιων): ανοιγμα εβδομαδας & κλεισιμο, 2019-25.
Ολα «υπερ της πλευρας» που λεει ο τιτλος: + = η πλευρα αυτη τα πηγε καλυτερα απο το νουμερο συγκρισης.
  Α  φαβορι/αουτσαιντερ ανα μεγεθος γραμμης: (μοντελο − γραμμη) και (πραγμ − γραμμη) υπερ φαβορι, picks ανοιγματος
  Β  εντος/εκτος × φαβορι/αουτσαιντερ: picks ανοιγματος, (πραγμ − μοντελο)
  Γ  μεγεθος διαφωνιας (edge): κερδιζει περισσοτερο οταν διαφωνουμε περισσοτερο;
  Δ  ΣΥΝΟΛΑ: over/under, υψηλες/χαμηλες γραμμες, κλειστα/ανοιχτα, picks
  Ε  ανα κομματι σεζον
  Ζ  ΑΙΤΙΑ: πραγμ − γραμμη = β·(συνεισφορα καθε κομματιου του μοντελου) — ποιο κομματι «ξερει» κατι που η αγορα δεν ξερει
     (β≈0: η αγορα το εχει ηδη, β>0: εχει αξια, β<0: το μοντελο το υπερ-βαραινει)
"""
import json
import numpy as np
import pandas as pd
import nfl_model as M
import nfl_qb as Q
import nfl_engine as E
import nfl_grid as G
import nfl_test as T
import nfl_test8 as T8

S7 = range(2019, 2026)


def se(a):
    a = np.asarray(a, float)
    return a.std() / np.sqrt(max(len(a), 1))


def pnl(side, res_minus_line, od_pos, od_neg):
    od = np.where(side > 0, od_pos, od_neg)
    od = np.where(np.isnan(od), 1.909, od)
    r = res_minus_line * side
    return np.where(r > 0, od - 1, np.where(r < 0, -1, 0))


def row(lab, d, pn):
    per = [d[d.season == S] for S in S7]
    pos = sum(pn[(d.season == S).values].sum() > 0 for S in range(2021, 2026))
    return f"  {lab:34} picks {len(d):4} ROI {100 * pn.mean():+6.1f}% (21-25 θετ {pos}/5) · καλυψη {100 * (pn > 0).mean():4.1f}%"


def main():
    g, off = M.load()
    q = Q.load_qb()
    tg = E.qb_open_targets(g)
    P = json.load(open('nfl_data/base2_params.json'))
    f = T8.base_frame(g, off, q, tg, P['m'])
    p = pd.read_csv('nfl_data/test8_preds.csv')[['game_id', 'mp_βαση v2', 'tp']].rename(columns={'mp_βαση v2': 'mp'})
    f = f.merge(p, on='game_id')
    o = pd.read_csv('nfl_data/sbr_slots.csv'); o = o[o.book == 'cons']
    for H, sfx in (('wk', 'o'), ('close', 'c')):
        s = o[o.H == H][['game_id', 'spread', 'total', 'h_dec', 'a_dec', 'o_dec', 'u_dec']].rename(
            columns=lambda c: c if c == 'game_id' else f'{c}_{sfx}')
        f = f.merge(s, on='game_id', how='left')
    x = f[f.season.between(2019, 2025) & f.spread_o.notna()].copy()
    print(f'ματς 2019-25 με γραμμες: {len(x)}')

    # ---------- Α φαβορι / αουτσαιντερ
    print('\n=== Α ΦΑΒΟΡΙ vs ΑΟΥΤΣΑΙΝΤΕΡ (ανοιγμα εβδ.) — υπερ ΦΑΒΟΡΙ της αγορας ===')
    fs = np.sign(x.spread_o).replace(0, 1)
    x['fs'] = fs
    x['bk'] = pd.cut(x.spread_o.abs(), [-0.1, 2.5, 4, 6.5, 9.5, 30], labels=['0-2.5', '3-4', '4.5-6.5', '7-9.5', '10+'])
    print(f"  {'γραμμη':8} {'n':>4} | μοντελο−γραμμη | πραγμ−γραμμη | πραγμ−μοντελο | picks ΦΑΒ: n ROI | picks ΑΟΥΤ: n ROI")
    side = np.sign(x.mp - x.spread_o)
    pk = (x.mp - x.spread_o).abs() >= 2.5
    pn_all = pnl(side.values, (x.result - x.spread_o).values, x.h_dec_o.values, x.a_dec_o.values)
    for b, d in x.groupby('bk', observed=True):
        i = d.index
        s_ = fs[i]
        mm = ((d.mp - d.spread_o) * s_); rr = ((d.result - d.spread_o) * s_); rm = ((d.result - d.mp) * s_)
        fav = pk[i] & (side[i] == s_); dog = pk[i] & (side[i] == -s_)
        pf = pn_all[x.index.get_indexer(i[fav])]; pdg = pn_all[x.index.get_indexer(i[dog])]
        print(f"  {b:8} {len(d):4} | {mm.mean():+5.2f} ±{se(mm):.2f}  | {rr.mean():+5.2f} ±{se(rr):.2f} | {rm.mean():+5.2f} ±{se(rm):.2f}  |"
              f" {fav.sum():3} {100 * pf.mean() if len(pf) else 0:+6.1f}% | {dog.sum():3} {100 * pdg.mean() if len(pdg) else 0:+6.1f}%")
    cal = np.polyfit(x.mp, x.result, 1)[0]; calm = np.polyfit(x.spread_o, x.result, 1)[0]
    print(f'  κλιση πραγμ ~ μοντελο {cal:.2f} · πραγμ ~ ανοιγμα {calm:.2f} · μοντελο ~ ανοιγμα {np.polyfit(x.spread_o, x.mp, 1)[0]:.2f} (1 = ιδιο ευρος)')

    # ---------- Β εντος / εκτος
    print('\n=== Β ΕΝΤΟΣ / ΕΚΤΟΣ × ΦΑΒΟΡΙ / ΑΟΥΤΣΑΙΝΤΕΡ (picks ανοιγματος, ≥2.5) ===')
    print(f"  μεσο πραγμ − μοντελο (γηπ): {(x.result - x.mp).mean():+.2f} ±{se(x.result - x.mp):.2f} · πραγμ − ανοιγμα: {(x.result - x.spread_o).mean():+.2f} · μοντελο − ανοιγμα: {(x.mp - x.spread_o).mean():+.2f}")
    xi = x.reset_index(drop=True); pki = pk.values; sdi = side.values; fsi = fs.values
    for lab, m in (('γηπεδουχος ΦΑΒΟΡΙ', (sdi > 0) & (fsi > 0)), ('γηπεδουχος ΑΟΥΤΣ.', (sdi > 0) & (fsi < 0)),
                   ('φιλοξενουμενος ΦΑΒΟΡΙ', (sdi < 0) & (fsi < 0)), ('φιλοξενουμενος ΑΟΥΤΣ.', (sdi < 0) & (fsi > 0)),
                   ('ολοι οι γηπεδουχοι', sdi > 0), ('ολοι οι φιλοξενουμενοι', sdi < 0)):
        mm = pki & m
        print(row(lab, xi[mm], pn_all[mm]))

    # ---------- Γ μεγεθος διαφωνιας
    print('\n=== Γ ΜΕΓΕΘΟΣ ΔΙΑΦΩΝΙΑΣ (ανοιγμα) — υπερ της πλευρας του μοντελου ===')
    e = (x.mp - x.spread_o).abs().values
    gain = ((x.result - x.spread_o) * side).values
    clv = ((x.spread_c - x.spread_o) * side).values
    for lo, hi in ((0, 1), (1, 2.5), (2.5, 4), (4, 6), (6, 99)):
        m = (e >= lo) & (e < hi)
        print(f"  διαφωνια {lo}-{hi} π.: n {m.sum():4} · πραγμ − γραμμη {gain[m].mean():+5.2f} ±{se(gain[m]):.2f} · κινηση γραμμης ως κλεισιμο {np.nanmean(clv[m]):+5.2f} · ROI {100 * pn_all[m].mean():+6.1f}%")

    # ---------- Δ συνολα
    print('\n=== Δ ΣΥΝΟΛΑ (ανοιγμα εβδ., ≥3 π.) ===')
    print(f"  μεσο πραγμ − μοντελο {(x.total - x.tp).mean():+.2f} ±{se(x.total - x.tp):.2f} · πραγμ − ανοιγμα {(x.total - x.total_o).mean():+.2f} · μοντελο − ανοιγμα {(x.tp - x.total_o).mean():+.2f}")
    ts = np.sign(x.tp - x.total_o).values
    tpk = (x.tp - x.total_o).abs().values >= 3
    tpn = pnl(ts, (x.total - x.total_o).values, x.o_dec_o.values, x.u_dec_o.values)
    print(row('OVER', xi[tpk & (ts > 0)], tpn[tpk & (ts > 0)]))
    print(row('UNDER', xi[tpk & (ts < 0)], tpn[tpk & (ts < 0)]))
    x['tb'] = pd.cut(x.total_o, [0, 41, 44, 47, 50, 70], labels=['≤41', '41.5-44', '44.5-47', '47.5-50', '50+'])
    dome = (~x.roof.isin(['outdoors'])).values if 'roof' in x else None
    gx = g.set_index('game_id').roof
    x['dome'] = (~x.game_id.map(gx).isin(['outdoors'])).astype(int)
    print(f"  {'γραμμη':8} {'n':>4} | μοντελο−γραμμη | πραγμ−γραμμη | OVER picks n ROI | UNDER picks n ROI")
    for b, d in x.groupby('tb', observed=True):
        ii = x.index.get_indexer(d.index)
        mo = tpk[ii] & (ts[ii] > 0); mu = tpk[ii] & (ts[ii] < 0)
        print(f"  {b:8} {len(d):4} | {(d.tp - d.total_o).mean():+5.2f}        | {(d.total - d.total_o).mean():+5.2f} ±{se(d.total - d.total_o):.2f} |"
              f" {mo.sum():3} {100 * tpn[ii][mo].mean() if mo.any() else 0:+6.1f}% | {mu.sum():3} {100 * tpn[ii][mu].mean() if mu.any() else 0:+6.1f}%")
    for dv, lab in ((1, 'κλειστα'), (0, 'ανοιχτα')):
        d = x[x.dome == dv]; ii = x.index.get_indexer(d.index)
        mo = tpk[ii] & (ts[ii] > 0); mu = tpk[ii] & (ts[ii] < 0)
        print(f"  {lab:8} {len(d):4} | μοντ−γρ {(d.tp - d.total_o).mean():+5.2f} | πραγμ−γρ {(d.total - d.total_o).mean():+5.2f} | OVER {mo.sum()} {100 * tpn[ii][mo].mean():+.1f}% | UNDER {mu.sum()} {100 * tpn[ii][mu].mean():+.1f}%")

    # ---------- Ε κομματι σεζον
    print('\n=== Ε ΑΝΑ ΚΟΜΜΑΤΙ ΣΕΖΟΝ (ανοιγμα) ===')
    for lo, hi in ((1, 4), (5, 9), (10, 13), (14, 18)):
        m = (xi.wk >= lo).values & (xi.wk <= hi).values
        print(f"  εβδ {lo}-{hi}: χαντ " + row('', xi[m & pki], pn_all[m & pki]).strip() + ' || συνολα ' + row('', xi[m & tpk], tpn[m & tpk]).strip())

    # ---------- Ζ αιτια
    print('\n=== Ζ ΑΙΤΙΑ: ποιο κομματι του μοντελου εχει πληροφορια που ΔΕΝ εχει η αγορα (ανοιγμα / κλεισιμο) ===')
    F = G.FM0 + ['wt_d_16']
    c = T.ols(f[f.season <= 2025], F, 'result')
    names = {'EPA_diff': 'EPA (αποδοση φασεων)', 'pts_diff': 'ποντοι', 'qb_d': 'QB', 'SR_diff': 'success rate',
             'st_net_diff': 'ειδικες ομαδες', 'wt_d_16': 'win totals'}
    for k_, n_ in zip(F, c[1:]):
        x[f'C_{k_}'] = n_ * x[k_]
    for L, lab in (('spread_o', 'ΑΝΟΙΓΜΑ'), ('spread_c', 'ΚΛΕΙΣΙΜΟ')):
        d = x.dropna(subset=[L])
        X = np.c_[np.ones(len(d)), d[L].values, d[[f'C_{k_}' for k_ in F]].values]
        y = d.result.values
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ b
        cov = res.var() * np.linalg.inv(X.T @ X)
        s_ = np.sqrt(np.diag(cov))
        print(f'  {lab}: πραγμ = {b[1]:.2f}·γραμμη + Σ β·κομματι  (β=1 → το μοντελο το βαραινει σωστα, β=0 → η αγορα το εχει ηδη)')
        print('     ' + ' · '.join(f'{names[k_]} {b[i + 2]:+.2f}±{s_[i + 2]:.2f}' for i, k_ in enumerate(F)))
        sd = {names[k_]: round(d[f'C_{k_}'].std(), 2) for k_ in F}
    print('  ευρος καθε κομματιου (τυπ. αποκλιση σε ποντους):', sd)
    # ποια κομματια διαφωνουν με την αγορα
    d = x.copy()
    gap = d.mp - d.spread_o
    print('  συσχετιση καθε κομματιου με τη διαφωνια μοντελο−ανοιγμα:',
          {names[k_]: round(np.corrcoef(d[f'C_{k_}'], gap)[0, 1], 2) for k_ in F})


if __name__ == '__main__':
    main()
