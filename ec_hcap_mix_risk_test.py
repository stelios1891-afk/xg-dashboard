# -*- coding: utf-8 -*-
"""ec_hcap_mix_risk_test.py — EuroCup ΧΑΝΤΙΚΑΠ: «ΙΔΙΑ ΧΡΗΜΑΤΑ ΜΕ ΛΙΓΟΤΕΡΟ ΡΙΣΚΟ»; (5/10/2026, Στελιος «μηπως ημασταν αυστηροι;»).
ΝΕΟ ερωτημα (το προηγουμενο κριτηριο ρωτουσε «περισσοτερα χρηματα;» → οχι, ιδια). Τα κριτηρια οριζονται ΤΩΡΑ, ΑΦΟΥ ειδαμε το
ec_hcap_mix_nested_test → γι' αυτο ψηλος πηχης + ελεγχος σε ΑΝΕΞΑΡΤΗΤΑ δεδομενα (τιμες Bet365, ποτε δεν χρησιμοποιηθηκαν).
Προβλεψεις = καθαρες (μηχανη επιλεγμενη στις αλλες σεζον, ιδιες με ec_hcap_mix_nested_test). Κανονες: ΣΗΜ (w1 σ11.5 ≥8%) · ΜΙΞ (w.5 σ12.3 ≥6%).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (ΠΡΙΝ την εκτελεση):
  Τ1 ROI ανα bet: bootstrap 5000 (ανα ματς): P(ROI ΜΙΞ > ROI ΣΗΜ) ≥ 0.90                                          [Crown ανοιγμα]
  Τ2 ΡΙΣΚΟ: χειροτερη σεζον ΜΙΞ > χειροτερη σεζον ΣΗΜ ΚΑΙ μεγιστη βυθιση (χρονολογικα, μοναδες) ΜΙΞ < ΣΗΜ          [Crown ανοιγμα]
  Τ3 BET365 ανοιγμα (ανεξαρτητο βιβλιο, ιδια ματς): ROI ΜΙΞ > ROI ΣΗΜ με P ≥ 0.80
  Τ4 CROWN ΚΛΕΙΣΙΜΟ: ROI ΜΙΞ > ROI ΣΗΜ με P ≥ 0.80
  Τ5 CLV ανα pick: P(μεση κινηση γραμμης προς τα picks ΜΙΞ > ΣΗΜ) ≥ 0.90
  ΑΠΟΦΑΣΗ: ΜΙΞ («ιδια χρηματα, λιγοτερο ρισκο») μονο αν Τ1 ✓ ΚΑΙ Τ2 ✓ ΚΑΙ ≥2 απο Τ3/Τ4/Τ5 ✓.
Εξοδος: ec_hcap_mix_risk_out.txt"""
import sys, json, io, contextlib
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
src = open('ec_hcap_mix_nested_test.py', encoding='utf-8').read()
src = src.split("# ---- (2) nested κανονας ----")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
NS = {'__name__': 'r'}
exec(src, NS)
HELD, MK, act, GN, seasn, EVM, cover = (NS[k] for k in ('HELD', 'MK', 'act', 'GN', 'seasn', 'EVM', 'cover'))
Z = NS['Z']; NN = NormalDist()
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
# ---- Bet365 ανοιγμα (ιδια αντιστοιχιση με ec_fresh_engine_test) ----
esrc = open('el_model_test.py', encoding='utf-8').read().split('# ---------------- ρυθμιση (χωρις αποδοσεις) ----------------')[0]
esrc = esrc.replace("B = json.load(open('el_box.json', encoding='utf-8'))", "B = {k: v for k, v in json.load(open('ec_box.json', encoding='utf-8')).items() if v.get('season') != 'U2026'}")
esrc = esrc.replace("sys.stdout.reconfigure(encoding='utf-8')", '').replace("open('el_model_test_out.txt', 'w'", "open('_unused_ecm.txt', 'w'")
EN = {}
with contextlib.redirect_stdout(io.StringIO()):
    exec(esrc, EN)
D = EN['D']
assert len(D) == len(act) and np.allclose((D.hs - D.as_).values, act), 'αλλη σειρα ματς'
SCH = {}
for sea in ('20-21', '21-22', '22-23', '23-24', '24-25', '25-26'):
    for g in json.load(open(f'nowgoal_ec/sched_{sea}.json', encoding='utf-8')):
        if g.get('hs') is not None: SCH[g['ngid']] = g
ROWS8 = {}
for ln in open('nowgoal_ec/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['cid'] == 8 and r['t'] == 21: ROWS8[r['ngid']] = r['rows']
ix2 = {}
for i in range(len(D)): ix2.setdefault((int(D.hs.values[i]), int(D.as_.values[i])), []).append(i)
MK8 = {}
for ng, g in SCH.items():
    tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit, sw = None, False
    for (a_, b_), swp in (((g['hs'], g['as_']), False), ((g['as_'], g['hs']), True)):
        for i in ix2.get((a_, b_), []):
            if abs(pd.Timestamp(D.t.values[i]).tz_localize(None) - tip) <= pd.Timedelta(hours=26): hit, sw = i, swp; break
        if hit is not None: break
    if hit is None: continue
    rows = sorted([x for x in ROWS8.get(ng, []) if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tip.timestamp() + 600], key=lambda x: x[0])
    if not rows: continue
    x = rows[0]; o1, o2 = 1 + x[2], 1 + x[3]; L = -x[1]; ph = (1 / o1) / (1 / o1 + 1 / o2); mu = -L + 11.5 * NN.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
    MK8[hit] = (-L, -mu, o2, o1) if sw else (L, mu, o1, o2)
P(f'Bet365 ανοιγμα: {sum(1 for i in MK8 if seasn[i] in EVM)} ματς (Crown {sum(1 for i in MK if seasn[i] in EVM)})')
CUR, MIX = (1.0, 11.5, .08), (.5, 12.3, .06)
def bets(book, rule):
    """λιστα (i, μοναδα, CLV) — book: 'o' Crown ανοιγμα, 'c' Crown κλεισιμο, 'b' Bet365 ανοιγμα."""
    w, s, thr = rule; R = []
    idx = [i for i in (MK8 if book == 'b' else MK) if seasn[i] in EVM and np.isfinite(HELD[i]) and (book != 'b' or i in MK)]
    for i in idx:
        L, mk, o1, o2 = MK8[i] if book == 'b' else MK[i][book]
        pw, pp, pl = cover(mk + w * (HELD[i] - mk), L, s); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e < thr: continue
        x = (act[i] + L) * side; u = (od - 1) if x > 0 else (0 if x == 0 else -1)
        R.append((i, u, (MK[i]['c'][1] - MK[i]['o'][1]) * side))
    return R
rng = np.random.default_rng(31)
def boot_roi(Ra, Rb, key=1, n=5000):
    """bootstrap ανα ματς (κοινος δειγματοχωρος ματς): P(μεσος ΜΙΞ > μεσος ΣΗΜ)."""
    games = sorted({r[0] for r in Ra} | {r[0] for r in Rb}); gi = {g: k for k, g in enumerate(games)}
    va = np.full(len(games), np.nan); vb = np.full(len(games), np.nan)
    for r in Ra: va[gi[r[0]]] = r[key]
    for r in Rb: vb[gi[r[0]]] = r[key]
    wins = 0
    for _ in range(n):
        s = rng.integers(0, len(games), len(games)); a, b = va[s], vb[s]
        if np.nanmean(a) > np.nanmean(b): wins += 1
    return wins / n
def summary(R, lab):
    u = np.array([r[1] for r in R]); ps = {Y: sum(r[1] for r in R if seasn[r[0]] == Y) for Y in EVM}
    order = sorted(R, key=lambda r: str(Z['t'][r[0]])); cum = np.cumsum([r[1] for r in order]); dd = float(np.max(np.maximum.accumulate(cum) - cum)) if len(cum) else 0
    P(f'  {lab:30s} {len(u):4d} picks · ROI {u.mean()*100:+.1f}% · {u.sum():+.1f}u · χειροτερη σεζον {min(ps.values()):+.1f}u · μεγ. βυθιση {dd:.1f}u · '
      + ' '.join(f'{Y[-2:]}:{v:+.1f}' for Y, v in ps.items()))
    return u.mean(), min(ps.values()), dd
P(''); P('################ Crown ΑΝΟΙΓΜΑ ################')
Ro_c, Ro_m = bets('o', CUR), bets('o', MIX)
rc, wc, dc = summary(Ro_c, 'ΣΗΜ (w1 σ11.5 ≥8%)'); rm_, wm, dm = summary(Ro_m, 'ΜΙΞ (w.5 σ12.3 ≥6%)')
p1 = boot_roi(Ro_m, Ro_c)
T1 = p1 >= .90; T2 = wm > wc and dm < dc
P(f'  Τ1 P(ROI ΜΙΞ > ΣΗΜ) = {p1:.2f} → {"✓" if T1 else "✗"} · Τ2 χειροτερη σεζον {wm:+.1f} vs {wc:+.1f}, βυθιση {dm:.1f} vs {dc:.1f} → {"✓" if T2 else "✗"}')
P(''); P('################ Τ3 Bet365 ΑΝΟΙΓΜΑ (ανεξαρτητο βιβλιο) ################')
Rb_c, Rb_m = bets('b', CUR), bets('b', MIX)
summary(Rb_c, 'ΣΗΜ'); summary(Rb_m, 'ΜΙΞ')
p3 = boot_roi(Rb_m, Rb_c); T3 = p3 >= .80
P(f'  P(ROI ΜΙΞ > ΣΗΜ) = {p3:.2f} → {"✓" if T3 else "✗"}')
P(''); P('################ Τ4 Crown ΚΛΕΙΣΙΜΟ ################')
Rc_c, Rc_m = bets('c', CUR), bets('c', MIX)
summary(Rc_c, 'ΣΗΜ'); summary(Rc_m, 'ΜΙΞ')
p4 = boot_roi(Rc_m, Rc_c); T4 = p4 >= .80
P(f'  P(ROI ΜΙΞ > ΣΗΜ) = {p4:.2f} → {"✓" if T4 else "✗"}')
P(''); P('################ Τ5 CLV ανα pick (Crown ανοιγμα → κλεισιμο) ################')
P(f'  ΣΗΜ {np.mean([r[2] for r in Ro_c]):+.2f} π. · ΜΙΞ {np.mean([r[2] for r in Ro_m]):+.2f} π.')
p5 = boot_roi(Ro_m, Ro_c, key=2); T5 = p5 >= .90
P(f'  P(CLV ΜΙΞ > ΣΗΜ) = {p5:.2f} → {"✓" if T5 else "✗"}')
k = sum([T3, T4, T5])
P(''); P('################ ΠΡΟ-ΔΗΛΩΜΕΝΗ ΑΠΟΦΑΣΗ ################')
P(f'  Τ1 {"✓" if T1 else "✗"} · Τ2 {"✓" if T2 else "✗"} · Τ3/Τ4/Τ5: {k}/3 ✓ → ' + ('ΜΙΞΗ ΠΕΡΝΑ («ιδια χρηματα, λιγοτερο ρισκο»)' if T1 and T2 and k >= 2 else 'ΔΕΝ ΠΕΡΝΑ — μενει ο σημερινος'))
open('ec_hcap_mix_risk_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
