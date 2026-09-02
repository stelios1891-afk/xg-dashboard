# -*- coding: utf-8 -*-
"""lineup_forward_report.py — Αξιολογηση του forward τεστ ενδεκαδων (2627).

Παιρνει τις καταγραφες του lineup_forward.jsonl (Δ ενδεκαδας τη στιγμη της προβλεψης),
τις ενωνει με αποτελεσματα (teamgame_inputs.csv) και αποδοσεις ~−24h (odds_history.jsonl)
και απανταει: ΠΡΟΣΘΕΤΟΥΝ οι projected 11αδες πληροφορια ΠΕΡΑ απο την αγορα;

ΤΕΣΤ 1 (κυριο, χρειαζεται ~150+ ματς): slope του Δdiff πανω στο υπολοιπο
  (πραγματικη διαφορα γκολ − implied sup αγορας στις −24h). Θετικο slope με t>=2
  = οι 11αδες ξερουν κατι που η −24h αγορα δεν εχει τιμολογησει.
ΤΕΣΤ 2 (betting, ενδεικτικο ως το md15): προστιθεται οταν αρχισουν να περνανε
  ματς με md>=7 (ιδια μεθοδος με predicted11_retro).
"""
import sys, json, math, datetime
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks

_dc = {}
def gdd(xh, xa):
    key = (round(xh, 2), round(xa, 2))
    if key not in _dc:
        _dc[key] = picks.gd_dist(key[0], key[1])
    return _dc[key]

def cover_p(s, T, L):
    xh = max((T + s) / 2, 0.05); xa = max((T - s) / 2, 0.05)
    d = gdd(xh, xa)
    def one(l):
        w = sum(p for k, p in d.items() if k + l > 1e-9)
        pu = sum(p for k, p in d.items() if abs(k + l) < 1e-9)
        return w / max(w + (1 - w - pu), 1e-9)
    q = round(L * 4)
    if q % 2 == 1:
        return 0.5 * (one((q - 1) / 4.0) + one((q + 1) / 4.0))
    return one(L)

def implied_sup(T, L, oh, oa):
    p = (1.0 / oh) / (1.0 / oh + 1.0 / oa)
    lo, hi = -3.5, 3.5
    for _ in range(20):
        mid = (lo + hi) / 2
        if cover_p(mid, T, L) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

# ---- καταγραφες: κρατα ανα ματς το snapshot πιο κοντα στο ko-24h ----
rows = {}
for line in open('lineup_forward.jsonl', encoding='utf-8'):
    r = json.loads(line)
    try:
        ko = datetime.datetime.fromisoformat(r['ko'].replace('Z', '+00:00'))
        t = datetime.datetime.fromisoformat(r['ts'])
    except Exception:
        continue
    tgt = ko - datetime.timedelta(hours=24)
    if t > ko:
        continue
    key = r.get('fid') or (r['home_id'], r['away_id'], r['ko'])
    d = abs((t - tgt).total_seconds())
    if key not in rows or d < rows[key][0]:
        rows[key] = (d, r)
F = pd.DataFrame([r for _, r in rows.values()])
print('καταγεγραμμενα ματς (μοναδικα):', len(F))

# ---- αποτελεσματα ----
TG = pd.read_csv('teamgame_inputs.csv')
TG['season'] = TG.season.astype(str)
cur = TG[TG.season == '2627']
res = {}
for _, g in cur[cur.is_home == True].iterrows():   # noqa: E712
    res[(int(g.team), int(g.opp))] = g.gf
for _, g in cur[cur.is_home == False].iterrows():  # noqa: E712
    k = (int(g.opp), int(g.team))
    if k in res:
        res[k] = res[k] - g.gf
F['gd'] = [res.get((r.home_id, r.away_id)) for r in F.itertuples()]
S = F.dropna(subset=['gd']).copy()
print('απο αυτα εχουν παιχτει και εχουμε σκορ:', len(S))

# ---- αποδοσεις κοντα στις -24h απο odds_history ----
hist = {}
try:
    for line in open('odds_history.jsonl', encoding='utf-8'):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        k = (r.get('hid'), r.get('aid'))
        hist.setdefault(k, []).append(r)
except FileNotFoundError:
    pass

def mkt_at(hid, aid, ko_iso):
    snaps = hist.get((hid, aid)) or []
    try:
        ko = datetime.datetime.fromisoformat(ko_iso.replace('Z', '+00:00')).timestamp()
    except Exception:
        return None
    best = None
    for s in snaps:
        ts = s.get('ts') or s.get('t')
        line = s.get('line') if s.get('line') is not None else s.get('ah')
        oh, oa = s.get('oh'), s.get('oa')
        if ts is None or line is None or oh is None or oa is None:
            continue
        d = abs(ts - (ko - 24 * 3600))
        if best is None or d < best[0]:
            best = (d, float(line), float(oh), float(oa))
    return best

sup_m = []
for r in S.itertuples():
    b = mkt_at(r.home_id, r.away_id, r.ko)
    sup_m.append(None if b is None else implied_sup(2.6, b[1], b[2], b[3]))
S['sup_mkt'] = sup_m
S2 = S.dropna(subset=['sup_mkt']).copy()
print('με αποδοσεις ~-24h:', len(S2))

if len(S2) >= 30:
    S2['resid'] = S2.gd - S2.sup_mkt
    x = (S2.dh - S2.da).values
    y = S2.resid.values
    b = np.cov(x, y)[0, 1] / max(np.var(x), 1e-12)
    r2 = y - (y.mean() - b * x.mean()) - b * x
    se = math.sqrt((r2 @ r2) / max(len(y) - 2, 1) / max(np.var(x) * len(y), 1e-12))
    print()
    print('=== ΤΕΣΤ 1: προσθετουν οι 11αδες πληροφορια ΠΕΡΑ απο την -24h αγορα; ===')
    print('n=%d ματς · slope %+.3f γκολ ανα 1.0 Δdiff · t=%+.1f · corr %.3f' % (
        len(S2), b, b / se, np.corrcoef(x, y)[0, 1]))
    print('(αναμενομενο απο το retro 2526: slope ~+2.0, t>=2 στο ωριμο παραθυρο)')
else:
    print()
    print('Πολυ λιγα ακομα για το ΤΕΣΤ 1 (χρειαζονται >=30 με σκορ+αποδοσεις).')
