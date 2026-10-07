# -*- coding: utf-8 -*-
"""bk_move_rules_test.py — ΚΑΝΟΝΕΣ «ΚΙΝΗΣΗΣ ΑΓΟΡΑΣ» σε EuroCup / BCL / NBA (7/10/2026, Στελιος «κανε το ιδιο και στις υπολοιπες λιγκες μπασκετ»).
Ιδια προσομοιωση με Ευρωλιγκα (el_alert_types / el_totals_move_deep): Crown (Nowgoal) καθε αλλαγη τιμης· ALERT = πρωτη τιμη με edge ≥ κατωφλι του
live κανονα· ROI στην τιμη του alert. Χαντικαπ & συνολα. Προβλεψεις:
  EuroCup: χαντικαπ held (LOSO) σ 11.5 ≥8% · συνολα live (αγων 1-6 μιξη 50/50, 7+ μονο) σ 16.7 ≥6% · U2020-25
  BCL:     χαντικαπ live φορμουλα σ 12 ≥8% · συνολα κοινη κλιμακα+τυχη (LOSO) σ 17.3 ≥8% · 2021-25
  NBA:     χαντικαπ καθαρη + B2B σ 13.5 ≥8% · συνολα καθαρη + Φ3 σ 18 ≥8% · 2022-26 (μονο Crown — χωρις Bet365)
ΟΜΑΔΕΣ: στο ΑΝΟΙΓΜΑ · μετα, κοντρα <1.5 · ΚΟΝΤΡΑ ≥1.5 (πότε ξεπεραστηκε: <6ω / 6-12ω / ≥12ω · Bet365 κινηθηκε ≥1 κοντρα ή οχι · απότομη/σταδιακη · over/under)
  · γεννηθηκε στο ΤΕΛΕΥΤΑΙΟ 2ΩΡΟ.
ΠΡΟ-ΔΗΛΩΜΕΝΟΙ ΚΑΝΟΝΕΣ (ιδια κριτηρια με Ευρωλιγκα):
  Κ1 «κοντρα ≥1.5 → καταγραφη»: ΠΕΡΝΑ αν χωρις αυτα το ROI ολων ανεβαινει ΚΑΙ σε ≥75% των σεζον (στρογγ. πανω).
  Κ2 εξαιρεση «κοντρα που εγινε <6ω → pick»: ΠΕΡΝΑ αν (με Κ1) η υποομαδα εχει ROI > 0 σε ≥75% σεζον, n ≥ 30, και το υπολοιπο ειναι αρνητικο.
  Κ3 «γεννηθηκε στο τελευταιο 2ωρο → καταγραφη»: ΠΕΡΝΑ αν χωρις αυτα το ROI ανεβαινει ΚΑΙ σε ≥75% σεζον.
Εξοδος: bk_move_rules_out.txt"""
import sys, os, json, math, pickle, collections
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
ND = NormalDist(); Phi = ND.cdf
SHIFT = 8 * 3600
def cover(m_, L, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
def load_rows(path):
    R = collections.defaultdict(dict)
    for ln in open(path, encoding='utf-8'):
        r = json.loads(ln)
        if r.get('ot', 6) != 6: continue
        R[(r['ngid'], r['t'])][r.get('cid', 3)] = r['rows']
    return R
def series(rows, t, swap, tip, sg):
    out_ = []
    for x in sorted(rows or [], key=lambda x: x[0]):
        if x[4] != 2 or x[1] is None or not x[2] or not x[3]: continue
        ut = x[0] + SHIFT
        if ut > tip + 600: break
        if t == 21:
            L = -x[1] * (-1 if swap else 1); o1, o2 = (1 + x[2], 1 + x[3]) if not swap else (1 + x[3], 1 + x[2])
            ph = (1 / o1) / (1 / o1 + 1 / o2); mu = -L + sg * ND.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
        else:
            L = float(x[1]); o1, o2 = 1 + x[2], 1 + x[3]
            ph = (1 / o1) / (1 / o1 + 1 / o2); mu = L + sg * ND.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
        out_.append((ut, mu, L, o1, o2))
    return out_
def best(t, model, row, w, sg):
    _, mk, L, o1, o2 = row; m_ = mk + w * (model - mk)
    if t == 21: pw, pp, pl = cover(m_, L, sg)
    else: pw, pp, pl = cover(m_, -L, sg)
    e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    return (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
def settle(t, act, tot, side, row, od):
    L = row[2]; v = ((act + L) if t == 21 else (tot - L)) * side
    return (od - 1) if v > 0 else (0.0 if v == 0 else -1.0)
def simulate(games, t, sg, rule):
    """games: [dict(sea, tip, ser, b365, model, act, tot, gno)] → DataFrame alerts."""
    rows = []
    for g in games:
        ser = g['ser'][t]
        if len(ser) < 2 or g['model'][t] is None or not np.isfinite(g['model'][t]): continue
        w, thr = rule(g)
        o = ser[0]; tip = g['tip']
        for k_, row in enumerate(ser):
            if row[0] >= tip: break
            side, e, od = best(t, g['model'][t], row, w, sg)
            if e < thr: continue
            mv = -(row[1] - o[1]) * side
            t15 = next((x[0] for x in ser[:k_ + 1] if -(x[1] - o[1]) * side >= 1.5), None)
            jumps = [-(ser[j][1] - ser[j - 1][1]) * side for j in range(1, k_ + 1)]
            bs = g['b365'][t]; b_at = [x for x in bs if x[0] <= row[0]]
            bmv = (-(b_at[-1][1] - bs[0][1]) * side) if (bs and b_at) else np.nan
            c = ser[-1]; oc = c[3] if side == 1 else c[4]
            rows.append(dict(sea=g['sea'], at_open=(k_ == 0), side=side, mv=mv, h15=(tip - t15) / 3600 if t15 else np.nan, hrs=(tip - row[0]) / 3600,
                             bmv=bmv, jump=max(jumps) if jumps else 0.0, pnl=settle(t, g['act'], g['tot'], side, row, od),
                             pnl_c=settle(t, g['act'], g['tot'], side, c, oc)))
            break
    return pd.DataFrame(rows)
def L(lab, z, SEAS, w=40):
    if len(z) == 0: P(f'    {lab:{w}s} —'); return None
    pos = sum(1 for s in SEAS if (z.sea == s).any() and z[z.sea == s].pnl.mean() > 0); ny = sum(1 for s in SEAS if (z.sea == s).any())
    per = ' '.join(f'{str(s)[-2:]}:{z[z.sea == s].pnl.mean()*100:+.0f}' if (z.sea == s).any() else f'{str(s)[-2:]}:—' for s in SEAS)
    P(f'    {lab:{w}s} n {len(z):4d} · ROI {z.pnl.mean()*100:+6.1f}% ({pos}/{ny}) · {z.pnl.sum():+6.1f}u · κλεισιμο {z.pnl_c.mean()*100:+6.1f}% · [{per}]')
    return pos
def better_in(Zall, keep, SEAS):
    b = sum(1 for s in SEAS if (keep.sea == s).any() and (Zall.sea == s).any() and keep[keep.sea == s].pnl.mean() > Zall[Zall.sea == s].pnl.mean())
    return b
def analyse(name, games, SEAS):
    need = math.ceil(.75 * len(SEAS))
    for t, mname, sg, rule in name[1]:
        Z = simulate(games, t, sg, rule)
        if not len(Z): continue
        P(''); P(f'======== {name[0]} · {mname} · alerts {len(Z)} (στο ανοιγμα {int(Z.at_open.sum())}) ========')
        L('ΟΛΑ (σημερινος κανονας)', Z, SEAS); L('στο ΑΝΟΙΓΜΑ', Z[Z.at_open], SEAS)
        A = Z[~Z.at_open]; K = A[A.mv >= 1.5]
        L('μετα το ανοιγμα · κοντρα <1.5', A[A.mv < 1.5], SEAS); L('ΚΟΝΤΡΑ ≥1.5', K, SEAS)
        for lab, f in (('  ↳ ξεπεραστηκε <6ω πριν', K.h15 < 6), ('  ↳ 6-12ω', (K.h15 >= 6) & (K.h15 < 12)), ('  ↳ ≥12ω', K.h15 >= 12),
                       ('  ↳ Bet365 κι αυτο κοντρα ≥1', K.bmv >= 1), ('  ↳ Bet365 οχι (<0.5)', K.bmv < .5),
                       ('  ↳ απότομη (μια αλλαγη ≥1.5)', K.jump >= 1.5), ('  ↳ σταδιακη', K.jump < 1.5)):
            L(lab, K[f], SEAS)
        if t == 23:
            L('  ↳ OVER', K[K.side == 1], SEAS); L('  ↳ UNDER', K[K.side == -1], SEAS)
        late = Z[(~Z.at_open) & (Z.hrs < 2)]
        L('γεννηθηκε στο τελευταιο 2ωρο', late, SEAS); L('  ↳ εκ των οποιων κοντρα ≥1.5', late[late.mv >= 1.5], SEAS)
        P('   ΚΡΙΣΕΙΣ:')
        keep1 = Z.drop(K.index)
        b1 = better_in(Z, keep1, SEAS); ok1 = keep1.pnl.mean() > Z.pnl.mean() and b1 >= need
        P(f'    Κ1 «κοντρα ≥1.5 → καταγραφη»: ROI {Z.pnl.mean()*100:+.1f}% → {keep1.pnl.mean()*100:+.1f}% · καλυτερο σε {b1}/{len(SEAS)}' + ('  ✓ ΠΕΡΝΑ' if ok1 else '  ✗'))
        sub = K[K.h15 < 6]; rest = K[~(K.h15 < 6)]
        ps = sum(1 for s in SEAS if (sub.sea == s).any() and sub[sub.sea == s].pnl.mean() > 0)
        ok2 = ok1 and len(sub) >= 30 and ps >= need and sub.pnl.mean() > 0 and len(rest) and rest.pnl.mean() < 0
        P(f'    Κ2 εξαιρεση «κοντρα <6ω → pick»: n {len(sub)} · ROI {sub.pnl.mean()*100 if len(sub) else 0:+.1f}% ({ps}) · υπολοιπο {rest.pnl.mean()*100 if len(rest) else 0:+.1f}%' + ('  ✓ ΠΕΡΝΑ' if ok2 else '  ✗'))
        keep3 = Z.drop(late.index); b3 = better_in(Z, keep3, SEAS); ok3 = len(late) > 0 and keep3.pnl.mean() > Z.pnl.mean() and b3 >= need
        P(f'    Κ3 «τελευταιο 2ωρο → καταγραφη»: ROI {Z.pnl.mean()*100:+.1f}% → {keep3.pnl.mean()*100:+.1f}% · καλυτερο σε {b3}/{len(SEAS)}' + ('  ✓ ΠΕΡΝΑ' if ok3 else '  ✗'))
# ================= EuroCup =================
def ec_games():
    E = pickle.load(open('ec_fresh_market.pkl', 'rb')); T = pickle.load(open('ec_totals_fin.pkl', 'rb'))
    S = np.asarray(E['seasn']); act = E['act']; tot = T['TOT']; tt = pd.to_datetime(pd.Series(np.asarray(E['t'])), utc=True, errors='coerce')
    idx = collections.defaultdict(list)
    for i in range(len(act)):
        if np.isfinite(act[i]) and np.isfinite(tot[i]): idx[(int(round((tot[i] + act[i]) / 2)), int(round((tot[i] - act[i]) / 2)))].append(i)
    R = load_rows('nowgoal_ec/odds.jsonl'); G = []
    for sea in ('20-21', '21-22', '22-23', '23-24', '24-25', '25-26'):
        for g in json.load(open(f'nowgoal_ec/sched_{sea}.json', encoding='utf-8')):
            if g.get('hs') is None: continue
            tip = (pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)).tz_localize('UTC'); hit = None
            for key, sw in (((g['hs'], g['as_']), False), ((g['as_'], g['hs']), True)):
                for i in idx.get(key, []):
                    if pd.notna(tt[i]) and abs((tt[i] - tip).total_seconds()) <= 26 * 3600: hit = (i, sw); break
                if hit: break
            if not hit: continue
            i, sw = hit; ts = tip.timestamp(); r21, r23 = R.get((g['ngid'], 21), {}), R.get((g['ngid'], 23), {})
            G.append(dict(sea=S[i], tip=ts, act=act[i], tot=tot[i], gno=int(E['GN'][i]),
                          ser={21: series(r21.get(3), 21, sw, ts, 11.5), 23: series(r23.get(3), 23, sw, ts, 16.7)},
                          b365={21: [(x[0], x[1]) for x in series(r21.get(8), 21, sw, ts, 11.5)], 23: [(x[0], x[1]) for x in series(r23.get(8), 23, sw, ts, 16.7)]},
                          model={21: float(E['held'][i]), 23: float(T['FIN'][i])}))
    return [g for g in G if g['sea'] in ('U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025')]
# ================= BCL =================
def bcl_games():
    D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); TL = pickle.load(open('bcl_totals_luck_preds.pkl', 'rb')); T0 = pickle.load(open('bcl_totals_preds.pkl', 'rb'))
    MT = {m: v for m, v in zip(TL['id'], TL['H1'])}
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    E = {e['id']: e for k, Lx in FG.items() if k.startswith('BCL_') for e in Lx if e.get('hs') not in (None, '')}
    idx = collections.defaultdict(list)
    for i, mid in enumerate(D['id']):
        if mid in E: idx[(int(E[mid]['hs']), int(E[mid]['as_']))].append(i)
    R = load_rows('nowgoal_bcl/odds.jsonl'); G = []
    for f in sorted(os.listdir('nowgoal_bcl')):
        if not f.startswith('sched_'): continue
        for g in json.load(open('nowgoal_bcl/' + f, encoding='utf-8')):
            if g.get('hs') is None: continue
            tip = (pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)).timestamp(); hit = None
            for key, sw in (((g['hs'], g['as_']), False), ((g['as_'], g['hs']), True)):
                for i in idx.get(key, []):
                    if abs(E[D['id'][i]]['ts'] - tip) <= 26 * 3600: hit = (i, sw); break
                if hit: break
            if not hit: continue
            i, sw = hit; mid = D['id'][i]; e = E[mid]; r21, r23 = R.get((g['ngid'], 21), {}), R.get((g['ngid'], 23), {})
            hs, as_ = (int(e['hs']), int(e['as_']))
            G.append(dict(sea=int(D['y'][i]), tip=tip, act=hs - as_, tot=hs + as_, gno=0,
                          ser={21: series(r21.get(3), 21, sw, tip, 12.0), 23: series(r23.get(3), 23, sw, tip, 17.3)},
                          b365={21: [(x[0], x[1]) for x in series(r21.get(8), 21, sw, tip, 12.0)], 23: [(x[0], x[1]) for x in series(r23.get(8), 23, sw, tip, 17.3)]},
                          model={21: float(D['FIN'][i]), 23: float(MT.get(mid, np.nan))}))
    return [g for g in G if g['sea'] in (2021, 2022, 2023, 2024, 2025)]
# ================= NBA =================
def nba_games():
    Dd = pickle.load(open('nba_diag_data.pkl', 'rb')); Gd, HH, HT, EV = Dd['G'], Dd['HH'], Dd['HT'], Dd['EV']
    S = Gd.season.values.astype(int); TOT = (Gd.hs + Gd.as_).values.astype(float); DT = Gd.date.values
    RES = np.zeros(len(Gd)); order = np.argsort(DT, kind='stable')
    for y in sorted(set(S)):
        ii = order[S[order] == y]; ds = DT[ii]
        for jj, i in enumerate(ii):
            past = [TOT[ii[q]] - HT[ii[q]] for q in range(max(0, jj - 400), jj) if ds[q] < ds[jj] and np.isfinite(HT[ii[q]])][-150:]
            RES[i] = np.mean(past) if len(past) >= 30 else 0.0
    HT3 = HT + RES
    keyd = collections.defaultdict(list)
    for i in range(len(Gd)): keyd[(int(S[i]), int(Gd.hs.values[i]), int(Gd.as_.values[i]))].append(i)
    R = collections.defaultdict(dict)
    for ln in open('nowgoal_nba/odds.jsonl', encoding='utf-8'):
        r = json.loads(ln); R[r['ngid']][r['t']] = r['rows']
    G = []
    for sea, se in {'21-22': 2022, '22-23': 2023, '23-24': 2024, '24-25': 2025, '25-26': 2026}.items():
        try: Sx = json.load(open(f'nowgoal_nba/sched_{sea}.json', encoding='utf-8'))
        except FileNotFoundError: continue
        for g in Sx:
            if g['hs'] is None or g['ngid'] not in R: continue
            tipT = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)
            us = tipT.tz_localize('UTC').tz_convert('America/New_York').tz_localize(None).normalize()
            cand = [i for i in keyd.get((se, g['hs'], g['as_']), []) if abs((pd.Timestamp(DT[i]) - us).days) <= 1]; sw = False
            if not cand: cand = [i for i in keyd.get((se, g['as_'], g['hs']), []) if abs((pd.Timestamp(DT[i]) - us).days) <= 1]; sw = True
            if len(cand) != 1: continue
            i = cand[0]; tip = tipT.timestamp()
            G.append(dict(sea=se, tip=tip, act=float(Gd.hs.values[i] - Gd.as_.values[i]), tot=TOT[i], gno=0,
                          ser={21: series(R[g['ngid']].get(21), 21, sw, tip, 13.5), 23: series(R[g['ngid']].get(23), 23, sw, tip, 18.0)},
                          b365={21: [], 23: []}, model={21: float(HH[i]), 23: float(HT3[i])}))
    return G
m8 = lambda g: (1.0, .08)
ec_tot = lambda g: (.5, .06) if g['gno'] <= 5 else (1.0, .06)
for name, loader, SEAS in ((('EuroCup', ((21, 'ΧΑΝΤΙΚΑΠ', 11.5, m8), (23, 'ΣΥΝΟΛΑ', 16.7, ec_tot))), ec_games, ['U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']),
                           (('BCL', ((21, 'ΧΑΝΤΙΚΑΠ', 12.0, m8), (23, 'ΣΥΝΟΛΑ', 17.3, m8))), bcl_games, [2021, 2022, 2023, 2024, 2025]),
                           (('NBA', ((21, 'ΧΑΝΤΙΚΑΠ', 13.5, m8), (23, 'ΣΥΝΟΛΑ', 18.0, m8))), nba_games, [2022, 2023, 2024, 2025, 2026])):
    try:
        gm = loader(); P(''); P(f'################ {name[0]}: {len(gm)} ματς με ιστορικο Crown ################')
        analyse(name, gm, SEAS)
    except Exception as e:
        import traceback; traceback.print_exc(); P(f'{name[0]}: σφαλμα {e}')
open('bk_move_rules_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
