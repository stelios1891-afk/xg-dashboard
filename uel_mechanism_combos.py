"""uel_mechanism_combos.py — 15/10/2026: συνεχεια του uel_all_mechanisms (μονο Europa). Οι μηχανισμοι που βοηθησαν ΧΩΡΙΣΤΑ (K 16/32, xG 80-100%,
φετινα ευρωπαικα 0.5, αξια ενδεκαδας) — ΜΑΖΙ: προστιθενται ή επικαλυπτονται; Ξαναχτισμενα λ για K+xG μαζι (euro_variant_build K16x80/K16x100/K32x100).
Ανα συνδυασμο: RPS, Δ1Χ2 ανα σεζον, picks ανα αγορα, μοναδες ανα σεζον, και ΑΝΑ ΒΙΒΛΙΟ (Crown / SBOBET). Αξια: LOSO βαρος (μοναδες) απο τις αλλες 3.
"""
import sys
_s = open('uel_all_mechanisms.py', encoding='utf-8').read()
exec(_s[:_s.index('FAM = {}')])
_s2 = _s[_s.index('# στιγμιοτυπα'):_s.index('SEAM = {s:')]
exec(_s2)
SEAM = {s: (x.sea == s).values for s in seas}
_, LL0 = acc(LH, LA, .85)
ISr = ratio_is('0.5'); ISf = (ISr[0] / LH, ISr[1] / LA)         # λογος «φετινα ευρωπαικα 0.5»
def with_is(lh, la): return lh * ISf[0], la * ISf[1]
C = {}
C['σημερινο live (K8 · xG60 · φετινα 0.5)'] = with_is(LH, LA)
C['K16'] = with_is(*ratio('K16', 'base06'))
C['xG100'] = with_is(*ratio('1.0', '0.6'))
C['K16 + xG80'] = with_is(*ratio('K16x80', 'base06'))
C['K16 + xG100'] = with_is(*ratio('K16x100', 'base06'))
C['K32 + xG100'] = with_is(*ratio('K32x100', 'base06'))
C['K16 + xG100 χωρις φετινα'] = ratio('K16x100', 'base06')
WS = (0.0, .25, .5, .75)
RES = {}
for nm, (lh, la) in C.items():
    r, l = acc(lh, la, .85); P = evaluate(lh, la, .85, 'q'); RES[nm] = (r, l, P)
# + αξια (LOSO βαρος) πανω στους δυο καλυτερους
for base in ('σημερινο live (K8 · xG60 · φετινα 0.5)', 'K16 + xG100', 'K16 + xG80'):
    lh0, la0 = C[base]; per = {w: (*acc(*mix(lh0, la0, VM, w, HASV), .85), evaluate(*mix(lh0, la0, VM, w, HASV), .85, 'q')) for w in WS}
    r = np.zeros(len(x)); l = np.zeros(len(x)); outs = []; ch = []
    for s in seas:
        w = max(WS, key=lambda w_: u(per[w_][2][per[w_][2].sea != s])); ch.append(w)
        r[SEAM[s]] = per[w][0][SEAM[s]]; l[SEAM[s]] = per[w][1][SEAM[s]]; outs.append(per[w][2][per[w][2].sea == s])
    RES[f'{base} + αξια LOSO ({",".join(f"{w:.2f}" for w in ch)})'] = (r, l, pd.concat(outs))
    for w in (.5, .75): RES[f'{base} + αξια {w:.2f}'] = per[w]
REF = RES['σημερινο live (K8 · xG60 · φετινα 0.5)']
print(f'EUROPA LEAGUE {len(x)} ματς · picks Α & Β · κελι = picks ανα βιβλιο · ROI · μοναδες · Δ1Χ2 vs σημερινο live (+ = καλυτερο) 22/23/24/25')
print(f'   {"συνδυασμος":60s} │ {"RPS":>6s} │ {"Δ1Χ2 ανα σεζον":>27s} │' + '│'.join(f'{g:>16s}' for g, _ in GR) + f'│ {"ΣΥΝΟΛΟ":>16s} │ μοναδες ανα σεζον       │ Crown / SBOBET')
for nm, (r, l, P) in RES.items():
    dl = [l[SEAM[s]].sum() - REF[1][SEAM[s]].sum() for s in seas]
    bk = P.groupby('bk').pnl.sum()
    print(f'   {nm[:60]:60s} │ {r.mean():.4f} │ ' + ' '.join(f'{v:+6.1f}' for v in dl) + ' │' + '│'.join(f'{cell(P[f(P)]):>16s}' for _, f in GR) +
          f'│ {cell(P):>16s} │ ' + ' '.join(f'{u(P[P.sea == s]):+5.1f}' for s in seas) + f' │ {bk.get("Crown", 0):+5.1f} / {bk.get("SBOBET", 0):+5.1f}')
print(f'{NL}ΑΝΑ ΑΓΟΡΑ × ΣΕΖΟΝ (μοναδες, μεσος βιβλιων) — σημερινο live vs K16+xG100 vs K16+xG100+αξια LOSO')
keys = ['σημερινο live (K8 · xG60 · φετινα 0.5)', 'K16 + xG100'] + [k for k in RES if k.startswith('K16 + xG100 + αξια LOSO')]
for g, f in GR:
    print(f'   {g:12s} ' + ' │ '.join(f'{k.split(" (")[0][:22]:22s} ' + ' '.join(f'{u(RES[k][2][f(RES[k][2]) & (RES[k][2].sea == s)]):+5.1f}' for s in seas) for k in keys))
