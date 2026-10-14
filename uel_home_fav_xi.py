"""uel_home_fav_xi.py — 14/10/2026 (Στελιος: «γυρνα πισω στα χαντικαπ»). Ο LIVE κανονας «UEL φαβορι εντος» (80% xG, ≤−0.5, edge ≥4%, 36-12ω)
χωρισμενος ανα ποσοστο ενδεκαδας του γηπεδουχου φαβορι (πληρης καλυψη, uel_xi_ratios.pkl). ROI στην εισοδο & στο κλεισιμο + αξια xG. Διαγνωστικο.
"""
import sys, pickle, glob
src = open('uel_lineup_rule2.py', encoding='utf-8').read().split('# ---------- φαβορι αγορας με την τιμη 1ω')[0]
exec(src)
XR = pickle.load(open('uel_xi_ratios.pkl', 'rb'))
EUM = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items(): EUM[str(k)] = m
def xv(i, ln, o):
    m = EUM.get(str(MIDS[i]))
    if not m or not m.get('shots'): return np.nan
    h = int(m['home']['id'])
    a = sum(s['xg'] for s in m['shots'] if s.get('xg') is not None and int(s['tid']) == h)
    b = sum(s['xg'] for s in m['shots'] if s.get('xg') is not None and int(s['tid']) != h)
    pw, pp = picks.p_cover(picks.gd_dist(max(a, .05), max(b, .05)), 1, ln)
    return o / ((1 - pp) / max(pw, 1e-9)) - 1
rows = []
for i in range(len(MIDS)):
    if COMP[i] != 'EuropaLeague' or str(MIDS[i]) not in I8: continue
    k = I8[str(MIDS[i])]
    if not D8['FM'][k]: continue
    dist = sdist(D8['LH'][k], D8['LA'][k])
    for bk in ('Crown', 'SBOBET'):
        for h in (36, 24, 18, 12):
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            L, oh, oa = s
            if L <= -0.5 and 1.70 <= oh <= 2.10 and edge(*cover_q(dist, 1, L), oh) >= .04:
                s0 = snap_ah(MIDS[i], bk, 0)
                rows.append(dict(sea=SEA[i], bk=bk, r=XR.get(str(MIDS[i]), (np.nan,))[0], pnl=picks.settle(GD[i], 1, L, oh),
                                 p0=picks.settle(GD[i], 1, s0[0], s0[1]) if s0 else np.nan, xv=xv(i, L, oh)))
                break
P = pd.DataFrame(rows)
def cc(x, col='pnl'):
    x = x.dropna(subset=[col])
    if len(x) < 6: return f'n{len(x) / 2:3.0f} (λιγα)'
    m = x.groupby('bk')[col].mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea')[col].mean()
    return f'{n:4.0f} picks {100 * m.mean():+6.1f}% (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')'
print(f'LIVE κανονας «UEL φαβορι εντος» — καλυψη ενδεκαδας {100 * P.r.notna().mean():.0f}%')
for lab, m_ in (('ολα', P.r.notna() | P.r.isna()), ('<85% (rotation)', P.r < .85), ('85-100%', (P.r >= .85) & (P.r < 1)), ('≥100% (πληρης)', P.r >= 1),
                ('≥85%', P.r >= .85), ('αγνωστη', P.r.isna())):
    x = P[m_]; print(f'   {lab:16s} εισοδος {cc(x)} | κλεισιμο {cc(x, "p0")} | αξια xG {100 * x.xv.mean():+.1f}%')
