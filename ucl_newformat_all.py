# -*- coding: utf-8 -*-
"""ucl_newformat_all.py — 19/10/2026 (Στελιος: «ειχαμε πει οτι το νεο φορματ αλλαξε το τσαμπιονς λιγκ — ξανατρεξε ΤΑ ΠΑΝΤΑ μονο σε αυτες τις 2 σεζον·
βγαλαμε το under και ανεβασαμε το αουτσαιντερ — ηταν κι αυτα σε ολες τις σεζον;»).
ΟΛΟΙ οι κανονες Champions League κατηγοριας Α, ΜΟΝΟ νεα μορφη 2024-25 & 2025-26: ΦΑΒΟΡΙ (≤−0.5, σωστα τεταρτα) · ΑΟΥΤΣΑΙΝΤΕΡ (≥+0.5, p_cover) ·
  DNB (γραμμη 0) · OVER · UNDER.
ΙΔΙΑ ΜΕΘΟΔΟΣ με ucl_rule_band_test: εισοδος στην ΠΡΩΤΗ εμφανιση ≤168ω (οχι <2ω), 1.70-2.10, ΤΙΜΙΟΣ ΧΡΟΝΟΣ (μοντελο −7 μερες >120ω, −4 μερες 96-120ω),
  Crown & SBOBET (μεσος), ισοπαλιες ×0.85, κ UCL 1.16. Επιπλεον γραμμη «≤72ω» για συγκριση.
ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ το τρεξιμο, ιδιο πνευμα με τα προηγουμενα αλλα για 2 σεζον): μια ζωνη edge κρατιεται αν
  (α) ROI > 0 στη νεα μορφη, (β) θετικη ΚΑΙ στις 2 σεζον, (γ) CLV οχι αρνητικο (t < −1.5), (δ) ΑΞΙΑ xG > 0 (μονο χαντικαπ).
LOSO 2 σεζον: κατωφλι ∈ {4,6,8,10,12,14%} διαλεγεται στη μια σεζον → εφαρμοζεται στην αλλη (και αναποδα)."""
import sys
_s = open('ucl_rule_band_test.py', encoding='utf-8').read()
exec(_s[:_s.index("for role, nm, live in")])
TS = (0.04, 0.06, 0.08, 0.10, 0.12, 0.14)
def dog_rows():
    out = []
    for k_ in range(len(x)):
        if x.cat[k_] != 'A' or x.sea[k_] not in NEW: continue
        i = int(x.i[k_])
        for bk in ('Crown', 'SBOBET'):
            c = snapT(mids[k_], bk, 0)
            for side in (1, -1):
                seq = []
                for h in HS:
                    s = snapT(mids[k_], bk, h)
                    if not s: continue
                    L, oh, oa = s; ln = L if side == 1 else -L; o = oh if side == 1 else oa
                    if ln < 0.5 or not (1.70 <= o <= 2.10): continue
                    lh, la = model_at(k_, h); pw, pp = picks.p_cover(ES.eu_dist(lh, la, .85), side, ln)
                    seq.append((h, L, ln, o, edge(pw, pp, o)))
                for T in TS:
                    f = next((q for q in seq if q[4] >= T), None)
                    if not f: continue
                    h, L, ln, o, e = f; so = snapT(mids[k_], bk, h)
                    cl = side * (implied_margin(i, *c) - implied_margin(i, L, so[1], so[2])) if c else np.nan
                    if c:
                        lnc = c[0] if side == 1 else -c[0]; oc = c[1] if side == 1 else c[2]
                        pnl_c = picks.settle(GD[i], side, lnc, oc) if lnc >= 0.5 else np.nan
                    else: pnl_c = np.nan
                    out.append(dict(th=T, sea=x.sea[k_], bk=bk, e=e, h=h, pnl=picks.settle(GD[i], side, ln, o), pnl_c=pnl_c, clv=cl, xv=xg_value(i, side, ln, o)))
    return pd.DataFrame(out)
def tot_rows(over):
    import io, contextlib, pickle as _p
    g = {}
    src = open('uel_full_review.py', encoding='utf-8').read().split("print('=' * 100 + NL + '1. ΣΥΝΟΛΑ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
    with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
    TOU_, KO_, ES_, OH_, OA_, SEA_, GH_, GA_, MIDS_, COMP_, SRCC_ = (g[k] for k in ('TOU', 'KO', 'ES', 'OH', 'OA', 'SEA', 'GH', 'GA', 'MIDS', 'COMP', 'SRCC'))
    settle_, mtot_ = g['settle'], g['mtot']
    I = [i for i in np.where(COMP_ == 'ChampionsLeague')[0] if SRCC_[i] == 'FF' and SEA_[i] in NEW]; M = [str(MIDS_[i]) for i in I]
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
    sg = 1 if over else -1; out = []
    for k, i in enumerate(I):
        tot = GH_[i] + GA_[i]
        for bk in ('Crown', 'SBOBET'):
            c = snap(M[k], bk, 0); seq = []
            for h in HS:
                s = snap(M[k], bk, h)
                if not s: continue
                L, oo, un = s; o = oo if over else un
                if not (1.70 <= o <= 2.10): continue
                rh, ra = (r7 if h > 120 else (r4 if h >= 96 else (np.ones(len(I)), np.ones(len(I)))))
                po, pu = ES_.p_over(ES_.tot_dist(OH_[i] * rh[k], OA_[i] * ra[k], .85), L)
                pw, pl = (po, pu) if over else (pu, po)
                seq.append((h, L, oo, un, o, pw * (o - 1) * (1 - picks.MARGIN) - pl))
            for T in TS:
                f = next((q for q in seq if q[5] >= T), None)
                if not f: continue
                h, L, oo, un, o, e = f
                cl = sg * (mtot_(*c) - mtot_(L, oo, un)) if c else np.nan
                pc = settle_(tot, c[0], c[1] if over else c[2], over) if c else np.nan
                out.append(dict(th=T, sea=SEA_[i], bk=bk, e=e, h=h, pnl=settle_(tot, L, o, over), pnl_c=pc, clv=cl, xv=np.nan))
    return pd.DataFrame(out)
FULL = HS
JOBS = (('fav', 'ΦΑΒΟΡΙ (≤−0.5)', 'σημερα ≥10%', .10), ('dog', 'ΑΟΥΤΣΑΙΝΤΕΡ (≥+0.5)', 'σημερα ≥10% (4-10% σκια απο 19/10)', .10),
        ('dnb', 'DNB (γραμμη 0)', 'σημερα ≥4%', .04), ('over', 'OVER', 'σημερα ≥4%', .04), ('under', 'UNDER', 'σημερα ΣΚΙΑ (ηταν ≥10%)', .10))
def build(role):
    if role == 'over': return tot_rows(True)
    if role == 'under': return tot_rows(False)
    if role == 'dog': return dog_rows()
    D = ah_rows(role); return D[D.sea.isin(NEW)]
SUM = []
for role, nm, today, live in JOBS:
    D = build(role); globals()['HS'] = tuple(h for h in FULL if h <= 72); D72 = build(role); globals()['HS'] = FULL
    print(f'{NL}{"#" * 132}{NL}{nm} — {today} · ΜΟΝΟ ΝΕΑ ΜΟΡΦΗ 2024-26 · picks ανα βιβλιο')
    base = D[D.th == .04]
    print(f'   {"ζωνη (edge πρωτης εμφ.)":24s} │ {"picks":>5s} {"ROI":>7s} {"μοναδ.":>7s} │ {"ROI κλεισ.":>10s} │ {"CLV":>7s} {"t":>5s} │ {"ΑΞΙΑ xG":>8s} │ {"2425":>6s} {"2526":>6s} │ {"≤72ω: picks ROI":>16s} │ κριτηριο')
    for lab, lo, hi in (('4-10%', .04, .10), ('10-14%', .10, .14), ('≥14%', .14, 9), ('≥10%', .10, 9), ('ΟΛΑ ≥4%', .04, 9)):
        y = base[(base.e >= lo) & (base.e < hi)]; y7 = D72[(D72.th == .04) & (D72.e >= lo) & (D72.e < hi)]
        u, r, n = units(y); _, rc, _ = units(y, 'pnl_c'); _, xv, _ = units(y, 'xv'); _, r7, n7 = units(y7)
        s = y.groupby('sea').pnl.mean(); cl = y.clv.dropna(); s25, s26 = s.get('2425', np.nan), s.get('2526', np.nan)
        ok = (r > 0, s25 > 0 and s26 > 0, not (cl.mean() < 0 and tv(cl) < -1.5), role in ('over', 'under') or xv > 0)
        v = ' '.join('✓' if q else '✗' for q in ok) + (' → ΚΡΑΤΙΕΤΑΙ' if all(ok) else ' → ✗')
        print(f'   {lab:24s} │ {n:5.0f} {100 * r:+6.1f}% {u:+7.1f} │ {100 * rc:+9.1f}% │ {cl.mean():+7.3f} {tv(cl):5.1f} │ '
              + (f'{100 * xv:+7.1f}%' if np.isfinite(xv) else f'{"—":>8s}') + f' │ {100 * s25:+5.0f}% {100 * s26:+5.0f}% │ {n7:5.0f} {100 * r7:+8.1f}% │ {v}')
        if lab in ('4-10%', '≥10%'): SUM.append((nm, lab, n, r, s25, s26, v))
    print('   ΚΑΤΩΦΛΙΑ (πρωτη εμφανιση με edge ≥ T, ≤168ω):')
    for T in TS:
        y = D[D.th == T]; u, r, n = units(y); s = y.groupby('sea').pnl.mean()
        print(f'      ≥{int(T * 100):2d}% {n:4.0f} picks ROI {100 * r:+6.1f}% μοναδες {u:+6.1f} (2425 {100 * s.get("2425", np.nan):+.0f}% · 2526 {100 * s.get("2526", np.nan):+.0f}%)'
              + (' ← σημερα' if abs(T - live) < 1e-9 else ''))
    tot = []
    for hold in NEW:
        tr = D[D.sea != hold]; best = max(TS, key=lambda T: units(tr[tr.th == T])[0])
        uh, rh_, nh = units(D[(D.sea == hold) & (D.th == best)]); u4, r4_, n4 = units(D[(D.sea == hold) & (D.th == .04)]); u10, r10, n10 = units(D[(D.sea == hold) & (D.th == .10)])
        tot.append((uh, nh, u4, n4, u10, n10))
        print(f'      LOSO κρυμμενη {hold}: διαλεγει ≥{int(best * 100)}% → {100 * rh_:+.1f}% ({uh:+.1f}μ) · ≥4%: {100 * r4_:+.1f}% ({u4:+.1f}μ) · ≥10%: {100 * r10:+.1f}% ({u10:+.1f}μ)')
    t_ = np.array(tot)
    print(f'      ΕΚΤΟΣ ΔΕΙΓΜΑΤΟΣ: LOSO {t_[:, 0].sum():+.1f}μ · ≥4% {t_[:, 2].sum():+.1f}μ · ≥10% {t_[:, 4].sum():+.1f}μ')
print(f'{NL}{"#" * 132}{NL}ΣΥΝΟΨΗ ΖΩΝΩΝ (νεα μορφη, ≤168ω): αγορα │ ζωνη │ picks │ ROI │ 2425 │ 2526 │ κριτηριο α β γ δ')
for nm, lab, n, r, a, b, v in SUM:
    print(f'   {nm:22s} │ {lab:6s} │ {n:4.0f} │ {100 * r:+6.1f}% │ {100 * a:+5.0f}% │ {100 * b:+5.0f}% │ {v}')
