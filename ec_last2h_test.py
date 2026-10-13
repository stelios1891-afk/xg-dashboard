# -*- coding: utf-8 -*-
"""ec_last2h_test.py — EuroCup: PICKS ΠΟΥ ΠΡΩΤΟΒΓΑΙΝΟΥΝ ΚΟΝΤΑ ΣΤΗΝ ΕΝΑΡΞΗ (13/10/2026, εγκεκριμενο τεστ· αναλογο ucl_last2h_test /
el_over_late_test). ΠΕΡΙΓΡΑΦΙΚΟ + ενας προ-δηλωμενος κανονας· καμια αλλαγη live.
ΠΡΟΣΟΜΟΙΩΣΗ LIVE: Crown (Nowgoal) ΟΛΟ το ιστορικο γραμμης U2020-U2025, σε ΚΑΘΕ αλλαγη τιμης απο το ανοιγμα ως το τζαμπολ:
  ΧΑΝΤΙΚΑΠ: live προβλεψεις EC ΜΕ ειδικους (ec_fresh_market.pkl 'live' = ec_audit_1310 κ_x 4), σ 11.5, edge ≥8%.
  ΣΥΝΟΛΑ:   ec_totals_fin.pkl FIN (live μηχανη συνολων)· κανονας ec_picks: αγων 1-6 (GN ≤5) μιξη 50/50 με την αγορα ΕΚΕΙΝΗΣ της στιγμης
            (αγορα = γραμμη + 16.7·Φ⁻¹(P over χωρις γκανιοτα)), αγων 7+ μοντελο μονο του · edge ≥6% · σ 16.7.
  ALERT = πρωτη στιγμη που υπαρχει το pick (ανα ματς & πλευρα). Καταγραφεται: ωρες πριν, αν υπηρχε στο ανοιγμα, κινηση ανοιγμα→alert
  (ποντοι, − = ΚΟΝΤΡΑ στο pick), κινηση alert→κλεισιμο, ROI στην τιμη alert και στην τιμη κλεισιματος (ιδια πλευρα), σεζον.
ΠΡΟ-ΔΗΛΩΜΕΝΟΣ ΚΑΝΟΝΑΣ (γραφτηκε ΠΡΙΝ την εκτελεση): «pick που πρωτοεμφανιζεται < 2ω πριν το τζαμπολ (οχι στο ανοιγμα) → καταγραφη».
  ΠΕΡΝΑ ανα αγορα (φαβορι / αουτσαιντερ / over / under, και χαντικαπ μαζι) αν ΟΛΑ:
  (1) κομμενα ROI < 0 ΚΑΙ χειροτερα απο οσα μενουν, στην τιμη alert ΚΑΙ στο κλεισιμο,
  (2) χειροτερα σε ≥4/6 σεζον (μετρανε σεζον με ≥2 κομμενα),
  (3) ιδια φορα (κομμενα χειροτερα απο οσα μενουν στο alert) με ορια 1ω και 3ω,
  (4) μοναδες με τον κανονα ≥ χωρις.
Επισης: «κοντρα πριν την εισοδο» (0 / 0.5-1.5 / 2-2.5 / ≥3) στα αργα picks (οχι στο ανοιγμα) και αν η κοντρα συνεχιζει μετα.
Εξοδος: ec_last2h_test_out.txt"""
import sys, io, json, pickle, contextlib
import numpy as np, pandas as pd
from statistics import NormalDist
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open('el_model_test.py', encoding='utf-8').read().split('# ---------------- ρυθμιση (χωρις αποδοσεις) ----------------')[0]
src = src.replace("B = json.load(open('el_box.json', encoding='utf-8'))",
                  "B = {k: v for k, v in json.load(open('el_players.json', encoding='utf-8')).items() if v.get('comp') == 'U'}")
src = src.replace("open('el_model_test_out.txt', 'w'", "open('_unused_ecl2h.txt', 'w'")
NS = {}
with contextlib.redirect_stdout(_B()):
    exec(src, NS)
sys.stdout.reconfigure(encoding='utf-8')
D = NS['D']
Z = pickle.load(open('ec_fresh_market.pkl', 'rb')); T = pickle.load(open('ec_totals_fin.pkl', 'rb'))
assert len(D) == len(Z['live']) == len(T['FIN']) and np.allclose(Z['act'], (D.hs - D.as_).values)
MODEL, FIN, GN = Z['live'], T['FIN'], np.asarray(T['GN'])
ACT = (D.hs - D.as_).values.astype(float); TOT = (D.hs + D.as_).values.astype(float); seasn = D.season.values
EVM = ['U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']
NN = NormalDist(); Phi = NN.cdf
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
# ---- Crown ολο το ιστορικο (χαντικαπ t=21, συνολα t=23) ----
SCH = {}
for sea in ('20-21', '21-22', '22-23', '23-24', '24-25', '25-26'):
    for g in json.load(open(f'nowgoal_ec/sched_{sea}.json', encoding='utf-8')):
        if g.get('hs') is not None: SCH[g['ngid']] = g
ROWS = {21: {}, 23: {}}
for ln in open('nowgoal_ec/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['cid'] == 3 and r['t'] in ROWS: ROWS[r['t']][r['ngid']] = r['rows']
ix2 = {}
for i in range(len(D)): ix2.setdefault((int(D.hs.values[i]), int(D.as_.values[i])), []).append(i)
HIST = {21: {}, 23: {}}
for ng, g in SCH.items():
    tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit, sw = None, False
    for (a_, b_), swp in (((g['hs'], g['as_']), False), ((g['as_'], g['hs']), True)):
        for i in ix2.get((a_, b_), []):
            if abs(pd.Timestamp(D.t.values[i]).tz_localize(None) - tip) <= pd.Timedelta(hours=26): hit, sw = i, swp; break
        if hit is not None: break
    if hit is None or seasn[hit] not in EVM: continue
    for t_ in (21, 23):
        rows = sorted([x for x in ROWS[t_].get(ng, []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 < tip.timestamp()],
                      key=lambda x: x[0])
        if not rows: continue
        if t_ == 21:   # (ts, γραμμη γηπ L, τιμη γηπ, τιμη φιλ)
            h = [(x[0] + 8 * 3600,) + ((x[1], 1 + x[3], 1 + x[2]) if sw else (-x[1], 1 + x[2], 1 + x[3])) for x in rows]
        else:          # (ts, γραμμη Τ, over, under)
            h = [(x[0] + 8 * 3600, float(x[1]), 1 + x[2], 1 + x[3]) for x in rows]
        HIST[t_][hit] = (tip.timestamp(), h)
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
res_ = lambda x, o: (o - 1) if x > 0 else (0 if x == 0 else -1)
def edges_h(i, x):
    _, L, o1, o2 = x; pw, pp, pl = cover(MODEL[i], L, 11.5)
    return {1: (pw * o1 + pp - 1, o1), -1: (pl * o2 + pp - 1, o2)}
def edges_t(i, x):
    _, Tl, oo, ou = x; po_ = (1 / oo) / (1 / oo + 1 / ou); mk = Tl + 16.7 * NN.inv_cdf(min(max(po_, 1e-4), 1 - 1e-4))
    w = .5 if GN[i] <= 5 else 1.0; mu = mk + w * (FIN[i] - mk); po, pq, pu = cover(mu, -Tl, 16.7)
    return {1: (po * oo + pq - 1, oo), -1: (pu * ou + pq - 1, ou)}
rows = []
for t_, ef, thr, mod in ((21, edges_h, .08, MODEL), (23, edges_t, .06, FIN)):
    for i, (tip, h) in HIST[t_].items():
        if not np.isfinite(mod[i]): continue
        c = h[-1]; o = h[0]
        for side in (1, -1):
            for k_, x in enumerate(h):
                e, od = ef(i, x)[side]
                if e < thr: continue
                L = x[1]
                if t_ == 21:
                    mv_b = -(L - o[1]) * side; mv_a = -(c[1] - L) * side          # + = προς εμας (η γραμμη της πλευρας μας μικρυνε) · − = κοντρα
                    mk = 'fav' if L * side <= 0 else 'dog'
                    pa = res_((ACT[i] + L) * side, od); pc = res_((ACT[i] + c[1]) * side, c[2] if side == 1 else c[3])
                else:
                    mv_b = (L - o[1]) * side; mv_a = (c[1] - L) * side             # over: γραμμη ↑ = προς εμας
                    mk = 'over' if side == 1 else 'under'
                    pa = res_((TOT[i] - L) * side, od); pc = res_((TOT[i] - c[1]) * side, c[2] if side == 1 else c[3])
                rows.append(dict(i=i, sea=seasn[i], mk=mk, hrs=(tip - x[0]) / 3600, at_open=(k_ == 0), mv=mv_b, mv_after=mv_a, edge=e, pa=pa, pc=pc, gn=int(GN[i])))
                break
X = pd.DataFrame(rows)
NAME = dict(fav='ΦΑΒΟΡΙ', dog='ΑΟΥΤΣΑΪΝΤΕΡ', over='OVER', under='UNDER', hc='ΧΑΝΤΙΚΑΠ ΜΑΖΙ')
def sub(m): return X[X.mk.isin(['fav', 'dog'])] if m == 'hc' else X[X.mk == m]
def cell(d, col='pa'):
    if not len(d): return f'{"—":>24s}'
    ps = d.groupby('sea')[col].mean()
    return f'{100 * d[col].mean():+6.1f}% ({len(d):3d}, {int((ps > 0).sum())}/{ps.size})'
P(f'EuroCup Crown U2020-U2025 · ματς με ιστορικο χαντικαπ {len(HIST[21])} / συνολων {len(HIST[23])} · alerts {len(X)} '
  + ' · '.join(f'{NAME[m]} {int((X.mk == m).sum())}' for m in ('fav', 'dog', 'over', 'under'))
  + f' · διαμεσες ωρες ανοιγματος πριν το τζαμπολ {np.median([(t - h[0][0]) / 3600 for t, h in HIST[21].values()]):.1f}')
P('ROI στην τιμη alert | ROI ιδιου pick στο κλεισιμο · (picks, θετικες σεζον) · κινηση πριν = ανοιγμα→alert (− = κοντρα) · μετα = alert→κλεισιμο')
WIN = [('απο ΑΝΟΙΓΜΑ', lambda d: d.at_open), ('24ω+', lambda d: ~d.at_open & (d.hrs >= 24)), ('12-24ω', lambda d: ~d.at_open & (d.hrs >= 12) & (d.hrs < 24)),
       ('6-12ω', lambda d: ~d.at_open & (d.hrs >= 6) & (d.hrs < 12)), ('3-6ω', lambda d: ~d.at_open & (d.hrs >= 3) & (d.hrs < 6)),
       ('2-3ω', lambda d: ~d.at_open & (d.hrs >= 2) & (d.hrs < 3)), ('1-2ω', lambda d: ~d.at_open & (d.hrs >= 1) & (d.hrs < 2)),
       ('<1ω', lambda d: ~d.at_open & (d.hrs < 1)), ('ΟΛΑ', lambda d: d.hrs >= -1)]
P(''); P('################ 1. ΑΝΑ ΠΑΡΑΘΥΡΟ ΠΡΩΤΗΣ ΕΜΦΑΝΙΣΗΣ ################')
for m in ('fav', 'dog', 'over', 'under', 'hc'):
    D_ = sub(m); P(''); P(f'=== {NAME[m]} ===')
    P(f'  {"παραθυρο":13s} {"ROI alert":>24s} {"ROI κλεισιμο":>24s} {"κιν. πριν":>9s} {"κιν. μετα":>9s}')
    for lab, f in WIN:
        d = D_[f(D_)]
        P(f'  {lab:13s} {cell(d)} {cell(d, "pc")} {d.mv.mean() if len(d) else 0:+9.2f} {d.mv_after.mean() if len(d) else 0:+9.2f}')
P(''); P('################ 2. ΠΡΟ-ΔΗΛΩΜΕΝΟΣ ΚΑΝΟΝΑΣ: πρωτη εμφανιση < 2ω (οχι στο ανοιγμα) → καταγραφη ################')
for m in ('fav', 'dog', 'over', 'under', 'hc'):
    D_ = sub(m); R = {}
    P(''); P(f'=== {NAME[m]} ===')
    for hh in (2, 1, 3):
        cut = D_[(D_.hrs < hh) & ~D_.at_open]; keep = D_.drop(cut.index)
        ys = [s for s in EVM if (cut.sea == s).sum() >= 2]
        worse = sum(1 for s in ys if cut[cut.sea == s].pa.mean() < keep[keep.sea == s].pa.mean())
        R[hh] = dict(cut=cut, keep=keep, worse=worse, ny=len(ys), u0=D_.pa.sum(), u1=keep.pa.sum())
        P(f'  <{hh}ω: κοβει alert {cell(cut)} · κλεισ {cell(cut, "pc")} | μενουν alert {cell(keep)} · κλεισ {cell(keep, "pc")} | '
          f'χειροτερα σε {worse}/{len(ys)} σεζον · μοναδες {R[hh]["u0"]:+.1f} → {R[hh]["u1"]:+.1f}')
    c, k = R[2]['cut'], R[2]['keep']
    if not len(c): P('  ΚΡΙΣΗ: κανενα κομμενο → ΔΕΝ ΠΕΡΝΑ'); continue
    c1 = c.pa.mean() < 0 and c.pc.mean() < 0 and c.pa.mean() < k.pa.mean() and c.pc.mean() < k.pc.mean()
    c2 = R[2]['worse'] >= 4
    c3 = all(len(R[hh]['cut']) and R[hh]['cut'].pa.mean() < R[hh]['keep'].pa.mean() for hh in (1, 3))
    c4 = R[2]['u1'] >= R[2]['u0']
    P(f'  ΚΡΙΣΗ <2ω: (1) {"✓" if c1 else "✗"} · (2) {R[2]["worse"]}/{R[2]["ny"]} σεζον (≥4) {"✓" if c2 else "✗"} · (3) 1ω & 3ω {"✓" if c3 else "✗"} · '
      f'(4) μοναδες {"✓" if c4 else "✗"} → {"ΠΕΡΝΑ" if all((c1, c2, c3, c4)) else "ΔΕΝ ΠΕΡΝΑ"}')
P(''); P('################ 3. ΚΟΝΤΡΑ ΠΡΙΝ ΤΗΝ ΕΙΣΟΔΟ (αργα picks: οχι στο ανοιγμα) ################')
BK = [('προς εμας ≥0.5', lambda v: v >= .25), ('0 (καμια)', lambda v: (v > -.25) & (v < .25)), ('κοντρα 0.5-1.5', lambda v: (v <= -.25) & (v > -1.75)),
      ('κοντρα 2-2.5', lambda v: (v <= -1.75) & (v > -2.75)), ('κοντρα ≥3', lambda v: v <= -2.75)]
for m in ('fav', 'dog', 'over', 'under', 'hc'):
    D_ = sub(m); D_ = D_[~D_.at_open]
    P(''); P(f'=== {NAME[m]} (αργα: {len(D_)}) ===')
    P(f'  {"κινηση πριν":15s} {"ROI alert":>24s} {"ROI κλεισιμο":>24s} {"κιν. μετα":>9s} {"% κοντρα συνεχιζει":>18s}')
    for lab, f in BK:
        d = D_[f(D_.mv)]
        P(f'  {lab:15s} {cell(d)} {cell(d, "pc")} {d.mv_after.mean() if len(d) else 0:+9.2f} {100 * (d.mv_after <= -.25).mean() if len(d) else 0:17.0f}%')
open('ec_last2h_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
