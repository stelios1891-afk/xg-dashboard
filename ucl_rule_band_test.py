# -*- coding: utf-8 -*-
"""ucl_rule_band_test.py — 19/10/2026 (Στελιος: «τρεξε το 2, 3, 4»): ιδια πληρης μεθοδος με ucl_dog_band_test / ucl_dog_loso για τους ΥΠΟΛΟΙΠΟΥΣ
κανονες του Champions League (κατηγορια Α): DNB (γραμμη 0, σημερα ≥4%) · ΦΑΒΟΡΙ (≤−0.5, σημερα ≥10%) · OVER (σημερα ≥4%).
ΚΑΝΟΝΑΣ LIVE: εισοδος στην ΠΡΩΤΗ εμφανιση ≤168ω (σημεια 168/144/120/96/72/60/48/36/24/18/12/8/6/4/2ω), οχι <2ω (χαντικαπ: late2h), 1.70-2.10,
  ΤΙΜΙΟΣ ΧΡΟΝΟΣ (μοντελο −7 μερες >120ω, −4 μερες 96-120ω), Crown & SBOBET (μεσος), 2022-26 (νεα μορφη 2024-26).
ΖΩΝΕΣ edge της πρωτης εμφανισης: 4-10% · 10-14% · ≥14%. ΜΕΤΡΑ: ROI εισοδου, ROI κλεισιματος, CLV (γκολ, + προς εμας), ανα σεζον, ΑΞΙΑ xG (χαντικαπ).
LOSO: για καθε κρυμμενη σεζον, κατωφλι ∈ {4,6,8,10,12,14%} με τις περισσοτερες μοναδες στις αλλες 3 → εφαρμογη στην κρυμμενη.
ΚΡΙΤΗΡΙΟ (γραφτηκε πριν, ιδιο με αουτσαιντερ): μια ζωνη κρατιεται αν (α) ROI>0 στις 4 σεζον και στη νεα μορφη, (β) θετικη ≥3/4 σεζον, (γ) CLV οχι
  αρνητικο (t<−1.5), (δ) ΑΞΙΑ xG>0 (χαντικαπ). Αλλαγη κατωφλιου μονο αν το ζητα το κριτηριο ΚΑΙ το LOSO δεν διαλεγει το σημερινο."""
import sys
_s = open('ucl_dog_band_test.py', encoding='utf-8').read()
exec(_s[:_s.index('R = []')])
NL = chr(10); SE = ['2223', '2324', '2425', '2526']
def ah_rows(role):
    out = []
    for k_ in range(len(x)):
        if x.cat[k_] != 'A': continue
        i = int(x.i[k_])
        for bk in ('Crown', 'SBOBET'):
            c = snapT(mids[k_], bk, 0)
            for side in (1, -1):
                seq = []
                for h in HS:
                    s = snapT(mids[k_], bk, h)
                    if not s: continue
                    L, oh, oa = s; ln = L if side == 1 else -L; o = oh if side == 1 else oa
                    if not (1.70 <= o <= 2.10): continue
                    if role == 'fav' and ln > -0.5: continue
                    if role == 'dnb' and abs(ln) > .01: continue
                    lh, la = model_at(k_, h); pw, pp = cover_q(ES.eu_dist(lh, la, .85), side, ln)
                    seq.append((h, L, ln, o, edge(pw, pp, o)))
                for T in (0.04, 0.06, 0.08, 0.10, 0.12, 0.14):
                    f = next((q for q in seq if q[4] >= T), None)
                    if not f: continue
                    h, L, ln, o, e = f; so = snapT(mids[k_], bk, h)
                    cl = side * (implied_margin(i, *c) - implied_margin(i, L, so[1], so[2])) if c else np.nan
                    if c:
                        lnc = c[0] if side == 1 else -c[0]; oc = c[1] if side == 1 else c[2]
                        pnl_c = picks.settle(GD[i], side, lnc, oc)
                    else: pnl_c = np.nan
                    out.append(dict(th=T, sea=x.sea[k_], bk=bk, e=e, h=h, pnl=picks.settle(GD[i], side, ln, o), pnl_c=pnl_c, clv=cl, xv=xg_value(i, side, ln, o)))
    return pd.DataFrame(out)
# ---------------- OVER: μηχανη συνολων (harness uel_full_review) + τιμιος χρονος ----------------
def over_rows():
    import io, contextlib, pickle as _p
    g = {}
    src = open('uel_full_review.py', encoding='utf-8').read().split("print('=' * 100 + NL + '1. ΣΥΝΟΛΑ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
    with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
    TOU_, KO_, ES_, OH_, OA_, SEA_, GH_, GA_, MIDS_, COMP_, SRCC_ = (g[k] for k in ('TOU', 'KO', 'ES', 'OH', 'OA', 'SEA', 'GH', 'GA', 'MIDS', 'COMP', 'SRCC'))
    settle_, mtot_ = g['settle'], g['mtot']
    I = [i for i in np.where(COMP_ == 'ChampionsLeague')[0] if SRCC_[i] == 'FF']; M = [str(MIDS_[i]) for i in I]
    def rp(var):
        a = _p.load(open(var, 'rb')); b = _p.load(open('euro_v6w2_preds_base06.pkl', 'rb'))
        ia = {str(m): k for k, m in enumerate(a['mids'])}; ib = {str(m): k for k, m in enumerate(b['mids'])}
        rh = np.array([a['lh'][ia[m]] / b['lh'][ib[m]] if m in ia and m in ib and b['lh'][ib[m]] > 0 else 1.0 for m in M])
        ra = np.array([a['la'][ia[m]] / b['la'][ib[m]] if m in ia and m in ib and b['la'][ib[m]] > 0 else 1.0 for m in M])
        return rh, ra
    r4, r7 = rp('euro_v6w2_preds_sh4.pkl'), rp('euro_v6w2_preds_sh7.pkl')
    def snap(mid, bk, h):
        ko = KO_.get(mid); seq = TOU_.get((mid, bk))
        if not ko or not seq: return None
        cut = ko - h * 3600 if h else ko + 900
        prev = [z for z in seq if z[0] <= cut]
        return prev[-1][1:] if prev else None
    out = []
    for k, i in enumerate(I):
        tot = GH_[i] + GA_[i]
        for bk in ('Crown', 'SBOBET'):
            c = snap(M[k], bk, 0); seq = []
            for h in HS:
                s = snap(M[k], bk, h)
                if not s: continue
                L, o, un = s
                if not (1.70 <= o <= 2.10): continue
                rh, ra = (r7 if h > 120 else (r4 if h >= 96 else (np.ones(len(I)), np.ones(len(I)))))
                td = ES_.tot_dist(OH_[i] * rh[k], OA_[i] * ra[k], .85); po, pu = ES_.p_over(td, L)
                seq.append((h, L, o, un, po * (o - 1) * (1 - picks.MARGIN) - pu))
            for T in (0.04, 0.06, 0.08, 0.10, 0.12, 0.14):
                f = next((q for q in seq if q[4] >= T), None)
                if not f: continue
                h, L, o, un, e = f
                cl = (mtot_(*c) - mtot_(L, o, un)) if c else np.nan
                out.append(dict(th=T, sea=SEA_[i], bk=bk, e=e, h=h, pnl=settle_(tot, L, o, True), pnl_c=settle_(tot, c[0], c[1], True) if c else np.nan, clv=cl, xv=np.nan))
    return pd.DataFrame(out)
def units(y, col='pnl'):
    y = y[y[col].notna()]
    if not len(y): return 0.0, np.nan, 0
    m = y.groupby('bk')[col].mean(); n = y.groupby('bk').size().mean(); return m.mean() * n, m.mean(), n
def tv(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return v.mean() / (v.std() / np.sqrt(len(v))) if len(v) > 3 and v.std() > 0 else np.nan
for role, nm, live in (('dnb', 'DNB (γραμμη 0)', .04), ('fav', 'ΦΑΒΟΡΙ (≤−0.5)', .10), ('over', 'OVER', .04)):
    D = over_rows() if role == 'over' else ah_rows(role)
    print(f'{NL}{"#" * 130}{NL}{nm} — σημερινο κατωφλι {int(live * 100)}%')
    base = D[D.th == .04]
    print(f'   {"ζωνη (edge πρωτης εμφ.)":24s} │ {"picks":>5s} {"ROI εισοδ.":>10s} {"μοναδες":>8s} │ {"ROI κλεισ.":>10s} │ {"CLV":>7s} {"t":>5s} │ {"ΑΞΙΑ xG":>8s} │ {"νεα μορφη":>16s} │ ανα σεζον')
    verdict = {}
    for lab, lo, hi in (('4-10%', .04, .10), ('10-14%', .10, .14), ('≥14%', .14, 9), ('ΟΛΑ ≥4%', .04, 9)):
        y = base[(base.e >= lo) & (base.e < hi)]
        u, r, n = units(y); _, rc, _ = units(y, 'pnl_c'); _, xv, _ = units(y, 'xv'); un, rn, nn = units(y[y.sea.isin(NEW)])
        s = y.groupby('sea').pnl.mean(); cl = y.clv.dropna()
        print(f'   {lab:24s} │ {n:5.0f} {100 * r:+9.1f}% {u:+8.1f} │ {100 * rc:+9.1f}% │ {cl.mean():+7.3f} {tv(cl):5.1f} │ {100 * xv:+7.1f}% │ {nn:4.0f} {100 * rn:+7.1f}% │ '
              + ' '.join(f'{k}:{100 * v:+.0f}%' for k, v in s.items()) + f' ({int((s > 0).sum())}/4)')
        verdict[lab] = (r > 0 and rn > 0, (s > 0).sum() >= 3, not (cl.mean() < 0 and tv(cl) < -1.5), (role == 'over') or xv > 0)
    print('   ΚΑΤΩΦΛΙΑ (πρωτη εμφανιση με edge ≥ T):')
    for T in (0.04, 0.06, 0.08, 0.10, 0.12, 0.14):
        y = D[D.th == T]; u, r, n = units(y); s = y.groupby('sea').pnl.mean()
        print(f'      ≥{int(T * 100):2d}% {n:4.0f} picks ROI {100 * r:+6.1f}% μοναδες {u:+6.1f} ({int((s > 0).sum())}/4)' + (' ← σημερα' if abs(T - live) < 1e-9 else ''))
    tot = []
    for hold in SE:
        tr = D[D.sea != hold]; best = max((0.04, 0.06, 0.08, 0.10, 0.12, 0.14), key=lambda T: units(tr[tr.th == T])[0])
        uh, rh_, nh = units(D[(D.sea == hold) & (D.th == best)]); ul, rl, nl = units(D[(D.sea == hold) & (D.th == live)])
        tot.append((uh, nh, ul, nl)); print(f'      LOSO κρυμμενη {hold}: διαλεγει ≥{int(best * 100)}% → {100 * rh_:+.1f}% ({uh:+.1f}μ) · σημερινο {int(live * 100)}%: {100 * rl:+.1f}% ({ul:+.1f}μ)')
    t_ = np.array(tot); print(f'      ΕΚΤΟΣ ΔΕΙΓΜΑΤΟΣ: LOSO {t_[:, 0].sum():+.1f}μ ({100 * t_[:, 0].sum() / max(t_[:, 1].sum(), 1):+.1f}%) · σημερινο {t_[:, 2].sum():+.1f}μ ({100 * t_[:, 2].sum() / max(t_[:, 3].sum(), 1):+.1f}%)')
    for lab, v in verdict.items():
        if lab == 'ΟΛΑ ≥4%': continue
        print(f'   κριτηριο {lab:8s}: (α) {"✓" if v[0] else "✗"} (β) {"✓" if v[1] else "✗"} (γ) {"✓" if v[2] else "✗"} (δ) {"✓" if v[3] else "✗"} → {"κρατιεται" if all(v) else "ΔΕΝ περνα"}')
