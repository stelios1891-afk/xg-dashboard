# -*- coding: utf-8 -*-
"""t_common.py — κοινη βαση για t1/t2/t6 (20/10). Τρεχει ΜΙΑ φορα την αλυσιδα news_test (→ absence_test → ablate, production CFG_H)
και σωζει σε _t_cache.pkl: MG (production), LOSS2 (γνωστες απουσιες K=2), B2H/B2A, FD/NF (ξαφνικες απουσιες, box score),
ανοιγμα/κλεισιμο ανα αγωνα (Crown, φιλτραρισμενο ≤ τζαμπολ+15′ οπως news_test), GN, βασικα G.
ΒΑΣΗ = MG + 3.0·(B2A − B2H) + 0.75·LOSS[2]  (ιδια με timing_abs_test V_OPEN = production προταση)."""
import os, io, sys, contextlib, pickle, time
SC = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(SC, '_t_cache.pkl')

def build():
    t0 = time.time(); ns = {'__file__': os.path.join(SC, 'news_test.py')}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(open(os.path.join(SC, 'news_test.py'), encoding='utf-8').read().split("def reg(y, X, m):")[0], ns)
    np = ns['np']; G = ns['G']; dD = ns['dD']; SEAS_G = ns['SEAS_G']
    B2H = np.zeros(len(G)); B2A = np.zeros(len(G)); last = {}
    for i in np.argsort(dD, kind='stable'):
        s, h_, a_, d = SEAS_G[i], G.home.values[i], G.away.values[i], dD[i]
        B2H[i] = float(last.get((s, h_)) == d - np.timedelta64(1, 'D')); B2A[i] = float(last.get((s, a_)) == d - np.timedelta64(1, 'D'))
        last[(s, h_)] = d; last[(s, a_)] = d
    GN = np.zeros(len(G), int); cnt = {}
    for i in np.argsort(dD, kind='stable'):
        s, h_, a_ = SEAS_G[i], G.home.values[i], G.away.values[i]
        GN[i] = min(cnt.get((s, h_), 0), cnt.get((s, a_), 0)) + 1; cnt[(s, h_)] = cnt.get((s, h_), 0) + 1; cnt[(s, a_)] = cnt.get((s, a_), 0) + 1
    SER, SHIFT, SIG, nd = ns['SER'], ns['SHIFT'], ns['SIG'], ns['nd']
    def tup(x, sw):
        L = -x[1] * (-1 if sw else 1); oh, oa = (1 + x[2], 1 + x[3]) if not sw else (1 + x[3], 1 + x[2])
        ph = (1 / oh) / (1 / oh + 1 / oa); return (float(L), float(-L + SIG * nd.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))), float(oh), float(oa))
    OC = {}
    for i, (sw, tip, r21, _) in SER.items():
        rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
        if not rows: continue
        OC[int(i)] = dict(o=tup(rows[0], sw), c=tup(rows[-1], sw), nmov=len(rows), hrs=(tip - rows[0][0]) / 3600)
    out = dict(MG=np.asarray(ns['MG'], float), LOSS2=ns['LOSS'][2][0], B2H=B2H, B2A=B2A, FD=ns['FD'], NF=ns['NF'], OC=OC,
               MKH={int(k): v for k, v in ns['MKH'].items()}, GN=GN, SEAS_G=SEAS_G, ACT=ns['ACT'], EV=ns['EV'], SIG=SIG,
               G=G[['season', 'date', 'home', 'away', 'hs', 'as_']].copy())
    pickle.dump(out, open(CACHE, 'wb')); print(f'cache built in {time.time() - t0:.0f}s', file=sys.stderr)
    return out

def load():
    if os.path.exists(CACHE): return pickle.load(open(CACHE, 'rb'))
    return build()

# ---------- κοινα εργαλεια ----------
import numpy as np
from statistics import NormalDist
Phi = NormalDist().cdf
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9:
        pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
def side_pick(mu, L, o1, o2, s):
    """ιδια λογικη με roi_od: πλευρα με το μεγαλυτερο edge → (side, edge, odds, p_win_decl, p_push)"""
    pw, pp, pl = cover(mu, L, s); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    return (1, e1, o1, pw, pp) if e1 >= e2 else (-1, e2, o2, pl, pp)
def settle(act, L, s_, od_):
    x = (act + L) * s_; return ((od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0)), (1.0 if x > 0 else (0.5 if x == 0 else 0.0))

if __name__ == '__main__':
    build()
