"""uecl_a_total_factor.py — 12/10/2026 (επιλογη διορθωσης για το «υποτιμαμε τα γκολ στην Α του Conference»: ΔΗΜΙΟΥΡΓΙΑ +0.10 xG/πλευρα).
Μια παραμετρος: γκολ ΚΑΙ των 2 πλευρων ×t στο ζευγος συνολων (W2), μονο Conference κατηγορια Α. t απο τις αλλες 3 σεζον (LOSO) με
log-lik στα xG (λιγοτερη τυχη) και στα γκολ. Μετα: picks over @8 / under @10 με και χωρις t (εκτος δειγματος).
ΠΡΟ-ΔΗΛΩΜΕΝΟ: περνα αν (α) καλυτερη προβλεψη γκολ εκτος δειγματος ≥3/4 σεζον ΚΑΙ (β) μοναδες over+under με t ≥ χωρις t.
"""
import sys, os
_src = open('uecl_battery.py', encoding='utf-8').read().split('# ================= 1 =================')[0]
_DEV = open(os.devnull, 'w', encoding='utf-8'); _REAL = sys.stdout; sys.stdout = _DEV
exec(_src)
sys.stdout = _REAL; sys.stdout.reconfigure(encoding='utf-8')
IA = [i for i in UI if cat(i) == 'A' and OH[i] > 0]
def ll(idx, t, xg=False):
    s = 0.0
    for i in idx:
        a, b = OH[i] * t, OA[i] * t
        if xg:
            x = XG.get(i)
            if not x: continue
            s += x[0] * math.log(a) - a + x[1] * math.log(b) - b
        else:
            s += GH[i] * math.log(a) - a + GA[i] * math.log(b) - b
    return s
GRID = np.round(np.arange(0.94, 1.21, 0.01), 2); TS = {}; ok = 0
print('ΣΥΝΤΕΛΕΣΤΗΣ ΓΚΟΛ t (Conference, κατηγορια Α) — LOSO')
for s_ in SEAS:
    tr = [i for i in IA if SEA[i] != s_]; te = [i for i in IA if SEA[i] == s_]
    t = GRID[np.argmax([ll(tr, g) for g in GRID])]; tx = GRID[np.argmax([ll(tr, g, True) for g in GRID])]; TS[s_] = t
    d = ll(te, t) - ll(te, 1.0); ok += d > 0
    print(f'   τεστ {s_}: t (γκολ) = {t:.2f} · t (xG) = {tx:.2f} · Δlog-lik γκολ στη σεζον-τεστ {d:+.2f} (n{len(te)})')
print(f'   t με ολες: γκολ {GRID[np.argmax([ll(IA, g) for g in GRID])]:.2f} · xG {GRID[np.argmax([ll(IA, g, True) for g in GRID])]:.2f} · καλυτερο εκτος δειγματος {ok}/4')
def picks_t(tmap):
    out = []
    for i in IA:
        t = tmap.get(SEA[i], 1.0); td = ES.tot_dist(OH[i] * t, OA[i] * t, DRAW_SCALE)
        for bk in ('Crown', 'SBOBET'):
            got = False
            for h in HS:
                so = snap_ou(MIDS[i], bk, h)
                if not so or got: continue
                L, o, un = so; po, pu = ES.p_over(td, L)
                for nm, od, p, q_, th in (('over', o, po, pu, .08), ('under', un, pu, po, .10)):
                    if 1.70 <= od <= 2.10 and p * (od - 1) * (1 - picks.MARGIN) - q_ >= th:
                        got = True; out.append(dict(bk=bk, sea=SEA[i], k=nm, pnl=settle(GH[i] + GA[i], L, od, nm == 'over'))); break
    return pd.DataFrame(out)
P0 = picks_t({}); P1 = picks_t(TS)
for k in ('over', 'under'):
    print(f'   {k:6s} σημερα {cc(P0[P0.k == k])}')
    print(f'   {"":6s} με t   {cc(P1[P1.k == k])}')
u0 = P0.groupby('bk').pnl.sum().mean(); u1 = P1.groupby('bk').pnl.sum().mean()
print(f'   ΜΟΝΑΔΕΣ over+under: σημερα {u0:+.1f} → με t {u1:+.1f} · ΚΡΙΤΗΡΙΑ: προβλεψη {ok}/4 {"✓" if ok >= 3 else "✗"} · μοναδες {"✓" if u1 >= u0 else "✗"}')
