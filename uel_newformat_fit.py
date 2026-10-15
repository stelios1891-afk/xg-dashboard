"""uel_newformat_fit.py — 15/10/2026 (Στελιος: «στο Champions χτισαμε τη μηχανη με βαρος στις 2 σεζον νεου φορματ — να κανουμε το ιδιο στο Europa;»).
Οπως το κ του Champions (εκτιμηση ΜΟΝΟ στο νεο φορματ, 2-fold: 2425 → κριση 2526 και αντιστροφα), τρεις διορθωσεις μιας παραμετρου για το Europa:
  κ   = κλιμακα γκολ ΦΑΒΟΡΙ (οπως Champions 1.16)                       λ_φαβ × κ
  s   = συμπιεση ΔΙΑΦΟΡΑΣ (συνολο ιδιο)                                 διαφορα × s
  t   = κλιμακα ΣΥΝΟΛΟΥ                                                  λ × t
Εκτιμηση με πιθανοφανεια γκολ στην ΑΛΛΗ σεζον νεου φορματ. Αποτελεσμα: Δπιθανοφανεια, picks χαντικαπ ανα αγορα (κανονες UEL, ≤72ω),
στις 2 σεζον νεου φορματ (+ στις παλιες για ελεγχο, με την παραμετρο του μεσου ορου).
"""
import sys
_s = open('uel_all_mechanisms.py', encoding='utf-8').read()
exec(_s[:_s.index('FAM = {}')]); exec(_s[_s.index('# στιγμιοτυπα'):_s.index('SEAM = {s:')])
NEWS = ('2425', '2526')
fh = LH >= LA
def adj(kind, p):
    if kind == 'κ': return np.where(fh, LH * p, LH), np.where(fh, LA, LA * p)
    if kind == 's':
        T = LH + LA; m = (LH - LA) * p; return np.maximum((T + m) / 2, .05), np.maximum((T - m) / 2, .05)
    return LH * p, LA * p
GRID = {'κ': np.round(np.arange(0.80, 1.21, 0.02), 2), 's': np.round(np.arange(0.50, 1.21, 0.05), 2), 't': np.round(np.arange(0.85, 1.11, 0.01), 2)}
NAME = {'κ': 'κλιμακα φαβορι κ', 's': 'συμπιεση διαφορας s', 't': 'κλιμακα συνολου t'}
def ll_s(lh, la, s): m = (x.sea == s).values; return ll(x[m], lh[m], la[m])
P0 = evaluate(LH, LA, .85, 'q')
print(f'EUROPA, εκτιμηση ΜΟΝΟ στο νεο φορματ (2-fold) · picks Α & Β, κανονες UEL, ≤72ω · κελι = picks/βιβλιο · ROI · μοναδες')
print(f'   σημερινο                         │ ' + ' │ '.join(f'{g}: {cell(P0[f(P0) & P0.sea.isin(NEWS)])}' for g, f in GR) + f' │ ΝΕΟ ΣΥΝΟΛΟ {cell(P0[P0.sea.isin(NEWS)])}')
for kind in ('κ', 's', 't'):
    fit = {}
    for s in NEWS:
        other = [q for q in NEWS if q != s][0]
        fit[s] = max(GRID[kind], key=lambda p: ll_s(*adj(kind, p), other))
    # εφαρμογη ανα σεζον νεου φορματ με την παραμετρο της αλλης
    lh = LH.copy(); la = LA.copy()
    for s in NEWS:
        m = (x.sea == s).values; a, b = adj(kind, fit[s]); lh[m] = a[m]; la[m] = b[m]
    pm = np.mean(list(fit.values()))
    for s in ('2223', '2324'):
        m = (x.sea == s).values; a, b = adj(kind, pm); lh[m] = a[m]; la[m] = b[m]
    P = evaluate(lh, la, .85, 'q')
    dl = {s: ll_s(lh, la, s) - ll_s(LH, LA, s) for s in seas}
    print(f'{NL}── {NAME[kind]}: εκτιμηση 2425 → {fit["2526"]} (για 2526) · 2526 → {fit["2425"]} (για 2425) · Δπιθ. νεο ' +
          ' '.join(f'{s}: {dl[s]:+.1f}' for s in NEWS) + ' · παλιο (με ' + f'{pm:.2f}) ' + ' '.join(f'{s}: {dl[s]:+.1f}' for s in ('2223', '2324')))
    print(f'   ΝΕΟ φορματ  │ ' + ' │ '.join(f'{g}: {cell(P[f(P) & P.sea.isin(NEWS)])}' for g, f in GR) + f' │ ΣΥΝΟΛΟ {cell(P[P.sea.isin(NEWS)])}')
    print(f'   ανα σεζον   │ ' + ' · '.join(f'{s}: {u(P0[P0.sea == s]):+.1f} → {u(P[P.sea == s]):+.1f}' for s in seas))
