"""euro_value_changed_picks.py — 10/10/2026 (Στελιος: «ποια ματς εφυγαν/μπηκαν — προβλεψη πριν, μετα, αγορα»).
Στρωμα αξιας (παραλλαγη _D, LOSO c ανα σεζον) · picks με τους σημερινους κανονες στο κλεισιμο Crown (και σημανση αν αλλαζει και στην Pinnacle)."""
import sys, io, json, math, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('euro_value_all_test_D.py', encoding='utf-8').split if False else open('euro_value_all_test_D.py', encoding='utf-8').read()
src = src.split('RB = roi_tab(BASE)')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'vc'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
LV, LR, DD, SEA, BASE, corr_lam, ll, CG = (g[k] for k in ('LV', 'LR', 'DD', 'SEA', 'BASE', 'corr_lam', 'll', 'CG'))
o = g['g']; GG = o['g']; MIDS, COMP, GD, FMm = GG['MIDS'], GG['COMP'], GG['GD'], GG['FMm']; S = GG['S']
eu_dist, cover_q = o['eu_dist'], o['cover_q']; import picks
aff = np.isfinite(LV); LH = BASE[0].copy(); LA = BASE[1].copy()
for te in ['2223', '2324', '2425', '2526']:
    tr = aff & (SEA != te)
    ab = tuple(np.linalg.lstsq(np.c_[np.ones(tr.sum()), LR[tr], DD[tr]], LV[tr], rcond=None)[0])
    c = max(CG, key=lambda c: ll(*corr_lam(LV, c, ab), tr))
    m = SEA == te; L = corr_lam(LV, c, ab); LH[m] = L[0][m]; LA[m] = L[1][m]
ef = json.load(open('europe_fixtures.json', encoding='utf-8'))
INFO = {str(x['mid']): (x['utc'][:10], x['score']) for v in ef.values() for x in v}
def evalp(lh, la, i, OD):
    out = {}
    if not FMm[i] or MIDS[i] not in OD: return out
    lf, oh, oa = OD[MIDS[i]]; dist = eu_dist(lh, la); ucl = COMP[i] == 'ChampionsLeague'
    for side, ln, od in ((1, lf, oh), (-1, -lf, oa)):
        if not (1.70 <= od <= 2.10): continue
        role = 'fav' if ln <= -0.5 else ('dog' if ln >= 0.5 else None)
        if role is None: continue
        pw, pp = cover_q(dist, side, ln) if role == 'fav' else picks.p_cover(dist, side, ln)
        e = pw * (od - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
        thr = (0.10 if role == 'fav' else 0.04) if ucl else (0.04 if role == 'fav' else 0.10)
        out[side] = dict(role=role, ln=ln, od=od, e=e, fair=(1 - pp) / pw if pw > 0 else 99, pick=e >= thr, pnl=picks.settle(GD[i], side, ln, od))
    return out
def msup(L, oh, oa, T):
    tq = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -4.5, 4.5
    for _ in range(24):
        s = (lo + hi) / 2; d = picks.gd_dist(max((T + s) / 2, .05), max((T - s) / 2, .05)); w, p = picks.p_cover(d, 1, L)
        if w / max(1 - p, 1e-9) < tq: lo = s
        else: hi = s
    return (lo + hi) / 2
CR, PIN = o['CROWN'], o['PIN']
rows = []
for i, mid in enumerate(MIDS):
    a0, a1 = evalp(BASE[0][i], BASE[1][i], i, CR), evalp(LH[i], LA[i], i, CR)
    p0, p1 = evalp(BASE[0][i], BASE[1][i], i, PIN), evalp(LH[i], LA[i], i, PIN)
    for side in (1, -1):
        b, n = a0.get(side), a1.get(side)
        if not b or not n or b['pick'] == n['pick']: continue
        pin_too = bool(p0.get(side) and p1.get(side) and p0[side]['pick'] != p1[side]['pick'])
        team = S.hname.values[i] if side == 1 else S.aname.values[i]
        rows.append(dict(kind='ΕΦΥΓΕ' if b['pick'] else 'ΜΠΗΚΕ', date=INFO.get(mid, ('', ''))[0], comp=COMP[i][:4],
                         match=f'{S.hname.values[i]} – {S.aname.values[i]}', score=INFO.get(mid, ('', ''))[1],
                         pick=f'{team} {"+" if b["ln"] >= 0 else ""}{b["ln"]:g} @{b["od"]:.2f}', role=b['role'],
                         sup0=BASE[0][i] - BASE[1][i], sup1=LH[i] - LA[i], mk=msup(*CR[mid], BASE[0][i] + BASE[1][i]),
                         f0=b['fair'], f1=n['fair'], e0=b['e'], e1=n['e'], pnl=b['pnl'], pin=pin_too))
R = pd.DataFrame(rows).sort_values(['kind', 'date'])
for k in ('ΕΦΥΓΕ', 'ΜΠΗΚΕ'):
    x = R[R.kind == k]
    print(f'\n===== {k} ({len(x)} picks Crown · ROI {100 * x.pnl.mean():+.1f}% · {x.pnl.sum():+.1f}μ) =====')
    print('ημερ.      διοργ ματς (σκορ)                                   | pick                         | υπεροχη γηπ: πριν → μετα · αγορα | δικαιη τιμη pick: πριν → μετα · edge | αποτ.')
    for r in x.itertuples():
        print(f'{r.date} {r.comp:4s} {(r.match + " " + r.score)[:52]:52s} | {r.pick[:28]:28s} | {r.sup0:+.2f} → {r.sup1:+.2f} · {r.mk:+.2f} | {r.f0:.2f} → {r.f1:.2f} · {100 * r.e0:+.0f}% → {100 * r.e1:+.0f}% | {r.pnl:+.2f}{"" if r.pin else " (μονο Crown)"}')
