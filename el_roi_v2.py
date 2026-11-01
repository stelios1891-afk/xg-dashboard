# -*- coding: utf-8 -*-
"""el_roi_v2.py — ROI στο closing (Pinnacle) ΟΛΩΝ των σεζον 2020-2025: v1 vs v2 (LOSO) vs v2 τελικη (24/9/2026, αιτημα Στελιου).
v2 = χαντικαπ απο ρυθμιση el_loso_tests, συνολο απο ρυθμιση el_loso_totals.
  «v2 LOSO»  : καθε σεζον με τη ρυθμιση που διαλεχτηκε ΑΠΟ ΤΙΣ ΑΛΛΕΣ 5 (τιμιο — ετσι θα ειχε γινει)
  «v2 τελικη»: η ρυθμιση που θα μπει live, σε ολες τις σεζον (ελαφρα αισιοδοξο: διαλεχτηκε βλεποντας και αυτες)
Κανονες (διορθωση Στελιου): EDGE = P(μοντελο)×αποδοση − 1, κατωφλια 3/5/8/10/15% οπως στο ποδοσφαιρο.
Τιμες: Pinnacle closing (αν λειπει: διαμεσος γραμμη βιβλιων @1.91). ΜΟΝΟ κανονικη περιοδος. Αναφορα — δεν αλλαζει τιποτα.
Εξοδος: el_roi_v2_out.txt"""
import sys, json, math, unicodedata, re
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))

src = open('el_loso_totals.py', encoding='utf-8').read().split('GRID = list(')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)     # φερνει run (χαντικαπ), run_t (συνολο), D, IDX, SE, EVAL κτλ

# ---- τιμες closing ανα ματς (ιδιο ταιριασμα με el_mech_tests, + αποδοσεις) ----
price = {}
for o in byid.values():
    ct = pd.Timestamp(o['commence']); c = EV[(EV.t - ct).abs() <= pd.Timedelta(minutes=25)]
    if not len(c): continue
    th, ta = tok(o['home']), tok(o['away'])
    sc = sorted([(len(th & tok(r.hname)) + len(ta & tok(r.aname)) - 0.5 * (len(th & tok(r.aname)) + len(ta & tok(r.hname))), i) for i, r in c.iterrows()], reverse=True)
    if len(c) > 1 and sc[0][0] <= 0: continue
    i = sc[0][1]; r = D.loc[i]
    flip = len(th & tok(r.aname)) > len(th & tok(r.hname))
    hn, an = (o['away'], o['home']) if flip else (o['home'], o['away'])
    def line(bk):
        sp = tt = None
        for m in bk['markets']:
            if m['key'] == 'spreads':
                a_ = [x for x in m['outcomes'] if x['name'] == hn]; b_ = [x for x in m['outcomes'] if x['name'] == an]
                if a_ and b_ and a_[0].get('point') is not None: sp = (float(a_[0]['point']), a_[0]['price'], b_[0]['price'])
            if m['key'] == 'totals':
                ov = [x for x in m['outcomes'] if x['name'] == 'Over']; un = [x for x in m['outcomes'] if x['name'] == 'Under']
                if ov and un: tt = (float(ov[0]['point']), ov[0]['price'], un[0]['price'])
        return sp, tt
    pin = [b for b in o['bookmakers'] if b['key'] == 'pinnacle']
    sp, tt = line(pin[0]) if pin else (None, None)
    if sp is None or tt is None:
        al = [line(b) for b in o['bookmakers']]
        if sp is None and any(x[0] for x in al): sp = (float(np.median([x[0][0] for x in al if x[0]])), 1.91, 1.91)
        if tt is None and any(x[1] for x in al): tt = (float(np.median([x[1][0] for x in al if x[1]])), 1.91, 1.91)
    if sp and tt: price[i] = sp + tt
PRC = np.array([price.get(i, (np.nan,) * 6) for i in IDX], float)
assert np.allclose(-PRC[:, 0], MM, equal_nan=True) and np.allclose(PRC[:, 3], MT, equal_nan=True)

H_V1 = dict(); H_FIN = dict(adj=False, HL=60, carry=1.0, lam=8, h=4.0)
H_LOSO = {'E2020': dict(adj=False, HL=120, carry=1.0, lam=14, h=4.0), 'E2024': dict(adj=False, HL=60, carry=0.7, lam=8, h=4.0)}
T_FIN = (0.25, 9999, 0.7, 50.0, 0.0)
T_LOSO = {'E2023': (0.25, 9999, 1.0, 50.0, 0.0), 'E2024': (0.25, 9999, 1.0, 50.0, 0.0)}
cache_h, cache_t = {}, {}
def hpred(kw):
    k = tuple(sorted(kw.items()))
    if k not in cache_h: cache_h[k] = run(**kw)[IDX, 0]
    return cache_h[k]
def tpred(c):
    if c not in cache_t: cache_t[c] = run_t(*c)
    return cache_t[c]
M_V1, T_V1 = hpred(H_V1), tpred((0.5, 120, 0.7, 5.0, 0.0))
M_FIN, T_FIN_ = hpred(H_FIN), tpred(T_FIN)
M_LO = np.array(M_FIN); T_LO = np.array(T_FIN_)
for s in EVAL:
    msk = SE == s
    if s in H_LOSO: M_LO[msk] = hpred(H_LOSO[s])[msk]
    if s in T_LOSO: T_LO[msk] = tpred(T_LOSO[s])[msk]

RSm = RS
SM, ST = 11.5, 16.7
PHI = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
def probs(mu, L, sig):
    """P(καλυψη), P(push), P(χασιμο) για το «mu + L > 0» (ακεραιες γραμμες: διορθωση συνεχειας)."""
    if abs(L - round(L)) < 1e-9:
        pw = PHI((mu + L - 0.5) / sig); pl = PHI((-mu - L - 0.5) / sig); return pw, 1 - pw - pl, pl
    pw = PHI((mu + L) / sig); return pw, 0.0, 1 - pw
def bets(mm, tt):
    rows = []
    for j in range(len(IDX)):
        if not RSm[j] or np.isnan(PRC[j, 0]): continue
        L, oh, oa, TL, ov, un = PRC[j]
        pw, pp, pl = probs(mm[j], L, SM)                  # γηπεδουχος με γραμμη L
        eh, ea = pw * oh + pp - 1, pl * oa + pp - 1
        side, e, o = (1, eh, oh) if eh >= ea else (-1, ea, oa)
        v = (ACT[j] + L) * side; fav = (L < 0) if side == 1 else (L > 0)
        rows.append(dict(season=SE[j], mkt='sp', edge=e, role='φαβορι' if fav else 'αουτσαιντερ', p=(o - 1) if v > 0 else (0 if v == 0 else -1)))
        po, pq, pu = probs(tt[j], -TL, ST)                # over: συνολο − TL > 0
        eo, eu = po * ov + pq - 1, pu * un + pq - 1
        over, e2, o2 = (True, eo, ov) if eo >= eu else (False, eu, un)
        v2 = (TOT[j] - TL) * (1 if over else -1)
        rows.append(dict(season=SE[j], mkt='tot', edge=e2, role='over' if over else 'under', p=(o2 - 1) if v2 > 0 else (0 if v2 == 0 else -1)))
    return pd.DataFrame(rows)

def cell(g):
    if not len(g): return '—'
    return f'{g.p.mean()*100:+5.1f}% ({len(g)}, {g.p.sum():+.1f}u)'
VERS = (('v1', M_V1, T_V1), ('v2 LOSO (τιμιο)', M_LO, T_LO), ('v2 τελικη', M_FIN, T_FIN_))
B = {lab: bets(m, t) for lab, m, t in VERS}
P('Edge = P(μοντελο) × αποδοση Pinnacle closing − 1 (Κανονικη κατανομη: σ διαφορας 11.5, σ συνολου 16.7)· πλευρα με το μεγαλυτερο edge.')
for mkt, nm in (('sp', 'ΧΑΝΤΙΚΑΠ'), ('tot', 'ΣΥΝΟΛΟ ΠΟΝΤΩΝ')):
    for thr in (0.03, 0.05, 0.08, 0.10, 0.15):
        P(''); P(f'=== {nm} · edge ≥ {thr*100:.0f}% — ROI (στοιχηματα, μοναδες) ===')
        P(f'{"":18s} ' + ' '.join(f'{s[1:]:>20s}' for s in EVAL) + f' {"ΣΥΝΟΛΟ":>22s}  σεζον+')
        for lab, _, _ in VERS:
            g = B[lab]; g = g[(g.mkt == mkt) & (g.edge >= thr)]
            pos = sum(1 for s in EVAL if len(g[g.season == s]) and g[g.season == s].p.mean() > 0)
            P(f'{lab:18s} ' + ' '.join(f'{cell(g[g.season == s]):>20s}' for s in EVAL) + f' {cell(g):>22s}  {pos}/6')
        for lab in ('v1', 'v2 LOSO (τιμιο)'):
            g = B[lab]; g = g[(g.mkt == mkt) & (g.edge >= thr)]
            P(f'   {lab}: ' + ' · '.join(f'{r} {cell(g[g.role == r])}' for r in sorted(g.role.unique())))
open('el_roi_v2_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
