"""uel_totals_mechanisms.py — 15/10/2026 (Στελιος: «δεν εχουμε δει τις διορθωσεις στα συνολα, ισως εκει αξιζει κατι — ηδη εχουμε δει θετικα σε over και under»).
ΣΥΝΟΛΑ EUROPA LEAGUE, κατηγορια Α (FotMob+FotMob, οπως ο scanner), καθε μηχανισμος ΧΩΡΙΣΤΑ (τα αλλα ως σημερα), λογος εκδοχη/βαση πανω στο live λ:
  K περσινη σεζον 4/8/16/32 · W περσινα ευρωπαικα 0/1/2/4 · φετινα ευρωπαικα 0/0.5/1/2 · μεριδιο xG 20-100% · ΑΓΚΥΡΑ στο συνολο ανοιγματος 0/.15/.3/.5 ·
  ΚΛΙΜΑΚΑ συνολου ×0.95/1/1.05/1.10 · ισοπαλιες ×1/.85/.75 · εδρα 1.00/1.139/1.25   (αξια & γ: ΔΕΝ αλλαζουν το συνολο → εκτος)
ΑΚΡΙΒΕΙΑ: log-πιθανοφανεια συνολου γκολ ανα σεζον vs σημερινο · μεσο μοντελο vs γκολ vs αγορα (κλεισιμο).
PICKS (1.70-2.10, Crown & SBOBET, ενα ανα ματς/βιβλιο/πλευρα): OVER ≥8% πρωτη φορα ≤12ω (προταση σκιας) · OVER ≥4% ≤72ω · UNDER ≥10% ≤72ω · UNDER ≥10% ≤12ω.
LOSO ανα μηχανισμο & αγορα: ρυθμιση απο τις αλλες 3 σεζον (μοναδες) → αποτελεσμα στην 4η.
"""
import sys, pickle
_s = open('uel_full_review.py', encoding='utf-8').read().split("print('=' * 100 + NL + '1. ΣΥΝΟΛΑ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
import io, contextlib
import os
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
HF0 = 1.139
I = np.array([i for i in UEL if SRCC[i] == 'FF']); M = [str(MIDS[i]) for i in I]; S = SEA[I]; TOT = GH[I] + GA[I]
OH0, OA0 = OH[I], OA[I]
def rp(var, base):
    a = pickle.load(open(var, 'rb')); b = pickle.load(open(base, 'rb'))
    ia = {str(m): k for k, m in enumerate(a['mids'])}; ib = {str(m): k for k, m in enumerate(b['mids'])}
    rh = np.array([a['lh'][ia[m]] / b['lh'][ib[m]] if m in ia and m in ib and b['lh'][ib[m]] > 0 else 1.0 for m in M])
    ra = np.array([a['la'][ia[m]] / b['la'][ib[m]] if m in ia and m in ib and b['la'][ib[m]] > 0 else 1.0 for m in M])
    return OH0 * rh, OA0 * ra
IS = pickle.load(open('euro_inseason_eu_preds.pkl', 'rb')); iis = {str(m): k for k, m in enumerate(IS['mids'])}
def ris(w):
    b = np.array(IS['live']['0.0']); v = np.array(IS['live'][w])
    rh = np.array([v[0][iis[m]] / b[0][iis[m]] if m in iis and b[0][iis[m]] > 0 else 1.0 for m in M])
    ra = np.array([v[1][iis[m]] / b[1][iis[m]] if m in iis and b[1][iis[m]] > 0 else 1.0 for m in M])
    return OH0 * rh, OA0 * ra
# συνολο ανοιγματος (πρωτη τιμη, μεσος βιβλιων)
MO = []
for m in M:
    v = []
    for bk in ('Crown', 'SBOBET'):
        seq = TOU.get((m, bk)); ko = KO.get(m)
        if seq and ko and seq[0][0] <= ko: v.append(mtot(*seq[0][1:]))
    MO.append(np.mean(v) if v else np.nan)
MO = np.array(MO)
def anc(a):
    T = OH0 + OA0; T2 = np.where(np.isfinite(MO), (1 - a) * T + a * np.nan_to_num(MO), T); return OH0 * T2 / T, OA0 * T2 / T
P = lambda t: f'euro_v6w2_preds_{t}.pkl'
FAM = {
    '1. περσινη σεζον K': [('K 4', rp(P('K4'), P('base06')), .85, 0), ('K 8', (OH0, OA0), .85, 1), ('K 16', rp(P('K16'), P('base06')), .85, 0), ('K 32', rp(P('K32'), P('base06')), .85, 0)],
    '2. περσινα ευρωπαικα W': [('W 0', rp(P('W0'), P('base06')), .85, 0), ('W 1', rp(P('W1'), P('base06')), .85, 0), ('W 2', (OH0, OA0), .85, 1), ('W 4', rp(P('W4'), P('base06')), .85, 0)],
    '3. φετινα ευρωπαικα': [('βαρος 0', (OH0, OA0), .85, 0), ('βαρος 0.5', ris('0.5'), .85, 1), ('βαρος 1', ris('1.0'), .85, 0), ('βαρος 2', ris('2.0'), .85, 0)],
    '4. μεριδιο xG': [(f'xG {int(b * 100)}%', rp(P(f'bl{b}'), P('bl0.6')) if b != .6 else (OH0, OA0), .85, int(b == .6)) for b in (.2, .4, .6, .8, 1.0)],
    '5. αγκυρα στο ανοιγμα': [(f'αγκυρα {a:.2f}', anc(a) if a else (OH0, OA0), .85, int(a == 0)) for a in (0, .15, .3, .5)],
    '6. κλιμακα συνολου': [(f'×{k:.2f}', (OH0 * k, OA0 * k), .85, int(k == 1)) for k in (.95, 1.0, 1.05, 1.10)],
    '7. ισοπαλιες': [(f'×{d:.2f}', (OH0, OA0), d, int(d == .85)) for d in (1.0, .85, .75)],
    '8. εδρα': [(f'εδρα {h:.3g}', (OH0 * h / HF0, OA0 * HF0 / h), .85, int(h == HF0)) for h in (1.0, HF0, 1.25)],
}
SN = {(k, bk, h): snap_ou(m, bk, h) for k, m in enumerate(M) for bk in ('Crown', 'SBOBET') for h in HS}
MK = [('OVER ≥8% ≤12ω', 'over', .08, 12), ('OVER ≥4% ≤72ω', 'over', .04, 72), ('UNDER ≥10% ≤72ω', 'under', .10, 72), ('UNDER ≥10% ≤12ω', 'under', .10, 12)]
def run(oh, oa, ds):
    rows = []; ll = np.zeros(len(I))
    for k in range(len(I)):
        td = ES.tot_dist(oh[k], oa[k], ds); ll[k] = np.log(max(td.get(int(TOT[k]), 1e-9), 1e-9))
        for nm, side, th, win in MK:
            for bk in ('Crown', 'SBOBET'):
                for h in [hh for hh in HS if 0 < hh <= win]:
                    s = SN[(k, bk, h)]
                    if not s: continue
                    L, o, un = s; po, pu = ES.p_over(td, L)
                    od, pw, pl = (o, po, pu) if side == 'over' else (un, pu, po)
                    if not (1.70 <= od <= 2.10): continue
                    if pw * (od - 1) * (1 - picks.MARGIN) - pl < th: continue
                    rows.append(dict(mk=nm, k=k, bk=bk, sea=S[k], pnl=settle(TOT[k], L, od, side == 'over'))); break
    return ll, pd.DataFrame(rows, columns=['mk', 'k', 'bk', 'sea', 'pnl'])
SEAS_ = sorted(set(S))
def u(y): return y.groupby('bk').pnl.sum().mean() if len(y) else 0.0
def cell(y):
    if len(y) == 0: return '—'
    m = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean(); return f'{n:3.0f} {100 * m.mean():+4.0f}% {m.mean() * n:+5.1f}'
LL0, _ = run(OH0, OA0, .85)
CLT = []
for k, m in enumerate(M):
    s = SN[(k, 'Crown', 0)] or SN[(k, 'SBOBET', 0)]; CLT.append(mtot(*s) if s else np.nan)
CLT = np.array(CLT); okc = np.isfinite(CLT)
print(f'ΣΥΝΟΛΑ EUROPA LEAGUE κατηγορια Α: {len(I)} ματς (' + ', '.join(f'{s}: {(S == s).sum()}' for s in SEAS_) + f') · γκολ {TOT[okc].mean():.2f} · αγορα κλεισιμο {CLT[okc].mean():.2f}')
print('κελι = picks ανα βιβλιο · ROI · μοναδες · Δπιθ. = log-πιθανοφανεια συνολου γκολ vs σημερινο ανα σεζον 22/23/24/25 (+ = καλυτερο)')
LOS = []
for fam, vs in FAM.items():
    print(f'{NL}── {fam} ' + '─' * 120)
    print(f'   {"ρυθμιση":12s} │ {"μοντελο":>7s} │ {"Δπιθ. ανα σεζον":>27s} │' + '│'.join(f'{n:>17s}' for n, *_ in MK) + '│ μοναδες ανα σεζον (ολα)')
    R = {}
    for nm, (oh, oa), ds, cur in vs:
        ll, Pk = run(oh, oa, ds); R[nm] = Pk
        dl = [ll[S == s].sum() - LL0[S == s].sum() for s in SEAS_]
        print(f' {"►" if cur else " "} {nm:12s} │ {(oh + oa)[okc].mean():7.2f} │ ' + ' '.join(f'{v:+6.1f}' for v in dl) + ' │' +
              '│'.join(f'{cell(Pk[Pk.mk == n]):>17s}' for n, *_ in MK) + '│ ' + ' '.join(f'{u(Pk[Pk.sea == s]):+5.1f}' for s in SEAS_))
    cur_nm = [nm for nm, _, _, c in vs if c][0]
    for n, *_ in MK:
        ch = []; outs = []
        for s in SEAS_:
            best = max(R, key=lambda z: u(R[z][(R[z].mk == n) & (R[z].sea != s)])); ch.append(best)
            outs.append(R[best][(R[best].mk == n) & (R[best].sea == s)])
        Z = pd.concat(outs); Z0 = R[cur_nm][R[cur_nm].mk == n]
        LOS.append((fam, n, ch, Z0, Z))
print(f'{NL}LOSO ανα μηχανισμο & αγορα (εκτος δειγματος) — σημερινο → LOSO · μοναδες ανα σεζον 22/23/24/25')
for fam, n, ch, Z0, Z in LOS:
    print(f'   {fam:24s} {n:17s} │ {cell(Z0):>17s} → {cell(Z):>17s} │ ' + ' '.join(f'{u(Z[Z.sea == s]):+5.1f}' for s in SEAS_) + f' │ {", ".join(ch)}')
