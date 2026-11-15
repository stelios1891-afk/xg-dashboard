"""compression_fix_test.py — 13/10/2026 (συνεχεια compression_battery: στο UEL/UECL η διαφορα του μοντελου ειναι ~25% φουσκωμενη, 4/4 σεζον,
ολες οι κατηγοριες, και σε ισοπαλια· η αγορα οχι). ΔΟΚΙΜΗ ΔΙΟΡΘΩΣΗΣ — ΜΙΑ παραμετρος ανα διοργανωση:
  διαφορα του ζευγους χαντικαπ × s (συνολο γκολ ιδιο), ΟΛΑ τα ματς της διοργανωσης (Α, Β, Γ), s απο τις αλλες 3 σεζον (LOSO, Poisson log-lik).
ΠΡΟ-ΔΗΛΩΜΕΝΑ: Κ1 log-lik εκτος δειγματος καλυτερο ≥3/4 σεζον · Κ2 RPS 1Χ2 καλυτερο συνολικα · Κ3 picks χαντικαπ (κατηγορια Α, κανονες
UECL/UEL: φαβ ≥4% σωστα τεταρτα, dog ≥10% p_cover, 1.70-2.10, πρωτη εμφανιση ≤72ω, Crown & SBOBET): μοναδες ≥ σημερα ΚΑΙ θετικες ≥3/4 σεζον.
UCL μονο ως ελεγχος (εκει δεν αναμενεται συμπιεση). Διαγνωστικο — τιποτα live.
"""
import sys
exec(open('ucl_nonfm_teams.py', encoding='utf-8').read().split('# ===== 1 =====')[0])
from math import lgamma
import math
NL = chr(10)
CMAP = {'UCL': 'ChampionsLeague', 'UEL': 'EuropaLeague', 'UECL': 'ConferenceLeague'}
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
SEAS_ = ('2223', '2324', '2425', '2526')
def pair(i, s_):
    T = LH_N[i] + LA_N[i]; m = (LH_N[i] - LA_N[i]) * s_
    return max((T + m) / 2, .05), max((T - m) / 2, .05)
def ll(idx, s_):
    t = 0.0
    for i in idx:
        a, b = pair(i, s_); t += GH[i] * math.log(a) - a + GA[i] * math.log(b) - b
    return t
def rps(idx, s_):
    v = []
    for i in idx:
        D = sdist(*pair(i, s_)); p1 = sum(p for k, p in D.items() if k > 0); px = D.get(0, 0)
        y = GD[i]; o1 = 1.0 if y > 0 else 0.0; o2 = 1.0 if y >= 0 else 0.0
        v.append(((p1 - o1) ** 2 + (p1 + px - o2) ** 2) / 2)
    return float(np.mean(v))
SNAP = {}
def picks_for(idx, smap):
    out = []
    for i in idx:
        if SRCC[i] != 'FF': continue
        D = sdist(*pair(i, smap.get(SEA[i], 1.0)))
        for bk in ('Crown', 'SBOBET'):
            got = set()
            for h in HS:
                key = (i, bk, h)
                if key not in SNAP: SNAP[key] = snap_ah(MIDS[i], bk, h)
                s = SNAP[key]
                if not s: continue
                L, oh, oa = s
                for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                    if side in got or not (1.70 <= o <= 2.10): continue
                    if ln <= -0.5: pw, pp = cover_q(D, side, ln); th = .04; k = 'φαβορι'
                    elif ln >= 0.5: pw, pp = picks.p_cover(D, side, ln); th = .10; k = 'αουτσαιντερ'
                    else: continue
                    if edge(pw, pp, o) >= th:
                        got.add(side); out.append(dict(bk=bk, sea=SEA[i], k=k, pnl=picks.settle(GD[i], side, ln, o)))
    return pd.DataFrame(out)
def cc_(x):
    if len(x) == 0: return '—'
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea').pnl.mean()
    return f'{n:4.0f} picks {100 * m.mean():+6.1f}% μον {m.mean() * n:+5.1f} (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')'
GRID = np.round(np.arange(0.50, 1.21, 0.05), 2)
for cm in ('UEL', 'UECL', 'UCL'):
    idx_all = [i for i in range(len(MIDS)) if COMP[i] == CMAP[cm] and LH_N[i] > 0 and VI.get(str(MIDS[i])) is not None]
    print(f'{NL}===== {cm}: {len(idx_all)} ματς')
    SM = {}; k1 = 0
    for s_ in SEAS_:
        tr = [i for i in idx_all if SEA[i] != s_]; te = [i for i in idx_all if SEA[i] == s_]
        sv = GRID[np.argmax([ll(tr, g) for g in GRID])]; SM[s_] = sv; d = ll(te, sv) - ll(te, 1.0); k1 += d > 0
        print(f'   τεστ {s_}: s = {sv:.2f} · Δlog-lik {d:+.2f} · RPS {rps(te, 1.0):.4f} → {rps(te, sv):.4f} (n{len(te)})')
    r0 = np.mean([rps([i for i in idx_all if SEA[i] == s_], 1.0) for s_ in SEAS_]); r1 = np.mean([rps([i for i in idx_all if SEA[i] == s_], SM[s_]) for s_ in SEAS_])
    print(f'   s με ολες: {GRID[np.argmax([ll(idx_all, g) for g in GRID])]:.2f} · Κ1 {k1}/4 {"✓" if k1 >= 3 else "✗"} · Κ2 RPS {r0:.4f} → {r1:.4f} {"✓" if r1 < r0 else "✗"}')
    P0 = picks_for(idx_all, {}); P1 = picks_for(idx_all, SM)
    for k in ('φαβορι', 'αουτσαιντερ'):
        print(f'   {k:12s} σημερα {cc_(P0[P0.k == k])}')
        print(f'   {"":12s} με s   {cc_(P1[P1.k == k])}')
    u0 = P0.groupby('bk').pnl.sum().mean() if len(P0) else 0; u1 = P1.groupby('bk').pnl.sum().mean() if len(P1) else 0
    ps = P1.groupby('sea').pnl.mean() if len(P1) else pd.Series(dtype=float)
    print(f'   Κ3 μοναδες χαντικαπ Α: {u0:+.1f} → {u1:+.1f} {"✓" if u1 >= u0 else "✗"} · σεζον θετικες με s {(ps > 0).sum()}/4 {"✓" if (ps > 0).sum() >= 3 else "✗"}')
