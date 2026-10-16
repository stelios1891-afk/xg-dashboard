"""ucl_early_honest_totals.py — 16/10/2026 (Στελιος: «τρεξε και τα συνολα»). Ιδιο με ucl_early_honest αλλα ΣΥΝΟΛΑ Champions League.
Κανονες live: over ≥4%, under ≥10%, κατηγορια Α (FotMob+FotMob), 1.70-2.10, ισοπαλιες ×0.85, κ UCL νεου φορματ (harness uel_full_review).
Τιμη ΑΚΡΙΒΩΣ στο σημειο χρονου (Crown & SBOBET, μεσος) · ΤΙΜΙΟΣ ΧΡΟΝΟΣ: δυναμη ομαδων −4 μερες (120ω/96ω) ή −7 (168ω), euro_variant_build SHIFT.
Τα συνολα κρινονται κυριως στη ΝΕΑ ΜΟΡΦΗ (2425-2526, βαση του live κανονα) — δειχνονται και τα 4 χρονια.
"""
import sys, os, pickle
_s = open('uel_full_review.py', encoding='utf-8').read().split("print('=' * 100 + NL + '1. ΣΥΝΟΛΑ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
I = np.array([i for i in np.where(COMP == 'ChampionsLeague')[0] if SRCC[i] == 'FF']); M = [str(MIDS[i]) for i in I]; S = SEA[I]; TOT = GH[I] + GA[I]
OH0, OA0 = OH[I], OA[I]
def rp(var, base):
    a = pickle.load(open(var, 'rb')); b = pickle.load(open(base, 'rb'))
    ia = {str(m): k for k, m in enumerate(a['mids'])}; ib = {str(m): k for k, m in enumerate(b['mids'])}
    rh = np.array([a['lh'][ia[m]] / b['lh'][ib[m]] if m in ia and m in ib and b['lh'][ib[m]] > 0 else 1.0 for m in M])
    ra = np.array([a['la'][ia[m]] / b['la'][ib[m]] if m in ia and m in ib and b['la'][ib[m]] > 0 else 1.0 for m in M])
    return OH0 * rh, OA0 * ra
H4 = rp('euro_v6w2_preds_sh4.pkl', 'euro_v6w2_preds_base06.pkl'); H7 = rp('euro_v6w2_preds_sh7.pkl', 'euro_v6w2_preds_base06.pkl')
print(f'αλλαγη συνολου μοντελου τιμιο vs «ξερει»: −4 μερες {np.mean(np.abs(H4[0] + H4[1] - OH0 - OA0)):.3f} · −7 μερες {np.mean(np.abs(H7[0] + H7[1] - OH0 - OA0)):.3f} γκολ')
def run(oh, oa, h):
    rows = []
    for k in range(len(I)):
        td = ES.tot_dist(oh[k], oa[k], DRAW_SCALE)
        for bk in ('Crown', 'SBOBET'):
            s = snap_ou(M[k], bk, h); c = snap_ou(M[k], bk, 0)
            if not s: continue
            L, o, un = s; po, pu = ES.p_over(td, L)
            for side, od, pw, pl_, th in (('over', o, po, pu, .04), ('under', un, pu, po, .10)):
                if not (1.70 <= od <= 2.10): continue
                if pw * (od - 1) * (1 - picks.MARGIN) - pl_ < th: continue
                clv = ((mtot(*c) - mtot(L, o, un)) * (1 if side == 'over' else -1)) if c else np.nan
                rows.append(dict(sea=S[k], bk=bk, side=side, pnl=settle(TOT[k], L, od, side == 'over'), clv=clv))
    return pd.DataFrame(rows, columns=['sea', 'bk', 'side', 'pnl', 'clv'])
def cellx(y):
    if len(y) == 0: return '—'
    m = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean(); s = y.groupby('sea').pnl.mean()
    return f'{n:4.0f} {100 * m.mean():+6.1f}% {m.mean() * n:+6.1f}μ {int((s > 0).sum())}/{len(s)} · CLV {y.clv.mean():+.3f}'
NEWS = ('2425', '2526')
print(f'{NL}CHAMPIONS LEAGUE ΣΥΝΟΛΑ, κατηγορια Α · κελι = picks ανα βιβλιο · ROI · μοναδες · θετικες σεζον · κινηση αγορας ως το κλεισιμο (γκολ, + = προς εμας)')
for h, hon, lab in ((168, H7, '−7 μερες'), (120, H4, '−4 μερες'), (96, H4, '−4 μερες'), (72, None, ''), (48, None, ''), (24, None, ''), (12, None, '')):
    P0 = run(OH0, OA0, h); P1 = run(*hon, h) if hon is not None else None
    print(f'{NL}── τιμη {h}ω πριν')
    for side, nm in (('over', 'OVER ≥4%'), ('under', 'UNDER ≥10%')):
        for per, f in (('4 σεζον', lambda y: y.sea.notna()), ('νεα μορφη', lambda y: y.sea.isin(NEWS))):
            a = P0[(P0.side == side) & f(P0)]
            line = f'   {nm:11s} {per:10s} ξερει: {cellx(a):46s}'
            if P1 is not None:
                b = P1[(P1.side == side) & f(P1)]; line += f' │ ΤΙΜΙΟ ({lab}): {cellx(b)}'
            print(line)
    if P1 is not None:
        print('      ανα σεζον (μοναδες, over+under) ξερει: ' + ' '.join(f'{s}: {P0[P0.sea == s].groupby("bk").pnl.sum().mean():+5.1f}' for s in sorted(set(S))) +
              ' │ τιμιο: ' + ' '.join(f'{s}: {P1[P1.sea == s].groupby("bk").pnl.sum().mean():+5.1f}' for s in sorted(set(S))))
