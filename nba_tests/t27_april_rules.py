# -*- coding: utf-8 -*-
"""t27_april_rules.py — ΚΛΕΙΣΙΜΟ ΑΠΡΙΛΙΟΥ: Τ1, Τ2, Τ4, Τ5 + ΥΠΟΨΙΑ «ΠΑΡΑΤΑΝΕ ΟΙ ΑΟΥΤΣΑΙΝΤΕΡ;» (21/10/2026, Στελιος).
Βαση: picks του t24c (_t24c_picks.csv: αντιγραφο live, απουσιες απο επισημες αναφορες στη στιγμη της τιμης, μονο Out, edge ≥8%, Μαρ-Απρ).
αγωνας = GN (ο μικροτερος αριθμος αγωνα των δυο ομαδων, οπως το live).
ΚΑΝΟΝΑΣ 2 = κανενα pick ΥΠΕΡ ομαδας χωρις κινητρο (κλειδωμενη/αδιαφορη/tanking) ΚΟΝΤΡΑ σε ομαδα με κινητρο (μαχη θεσης/play-in).
ΠΡΟ-ΔΗΛΩΜΕΝΑ (πριν το τρεξιμο):
 Τ1 LOSO οριου: για καθε σεζον Υ, οριο c ∈ {71,73,76,79} (picks μονο αν αγωνας < c) με το καλυτερο ROI (μοναδες) στις αλλες 4, εφαρμογη στην Υ.
    ΠΕΡΝΑ αν μοναδες LOSO > μοναδες με το σημερινο 71 ΣΥΝΟΛΙΚΑ και σε ≥3/5 σεζον, με CLV των προστιθεμενων picks > 0. Χωρις και με κανονα 2.
 Τ2 κανονας 2 απο τον 61ο: ΠΕΡΝΑ αν τα picks που αφαιρει στους 61-70 εχουν μοναδες ≤ 0 σε ≥4/5 σεζον.
 Τ4 «πρακτικα αποκλεισμενη» (θεση ≥11, ≥60 ματς, ≥5 νικες πισω απο τη 10η, οχι μαθηματικα εκτος, οχι 5 χειροτερες) = χωρις κινητρο:
    ΠΕΡΝΑ αν τα επιπλεον picks που αφαιρει στους 71-75 εχουν μοναδες ≤ 0 σε ≥4/5 σεζον (και περιγραφικα στους 61-70).
 Τ5 παραδειγματα: 3 picks 71-75 που αφαιρει ο κανονας 2 και 3 που μενουν.
 ΥΠΟΨΙΑ 2 (αουτσαιντερ «παρατανε»): ομαδες ΜΕ κινητρο, αουτσαιντερ στο ανοιγμα, αγωνες 76-82 vs 61-75:
    Δ λεπτων 5 βασικων απο τον μεσο ορο τους, βασικοι στην 4η οταν χανουν με 10+ (vs μεσο ορο), υπολοιπο μοντελου & αγορας·
    και χωριστα: αν ≥2 απο τα 3 ΕΠΟΜΕΝΑ ματς τους ειναι με ομαδες χωρις κινητρο («κρατανε δυναμεις»;) vs ≤1.
Εξοδος: t27_april_rules_out.txt"""
import os, sys, pickle, collections
import numpy as np, pandas as pd
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
D = pickle.load(open(os.path.join(ROOT, 'nba_diag_data.pkl'), 'rb')); G = D['G'].reset_index(drop=True); GN = np.asarray(D['GN']); MKH = D['MKH']
ACT = (G.hs - G.as_).values; SEAS = G.season.values.astype(int); dD = G.date.values.astype('datetime64[D]')
EAST = set('ATL BOS BRK CHO CHI CLE DET IND MIA MIL NYK ORL PHI TOR WAS'.split())
NOM = ('ΚΛΕΙΔΩΜΕΝΗ', 'ΑΔΙΑΦΟΡΗ', 'TANKING'); MOT = ('ΜΑΧΗ ΘΕΣΗΣ 1-6', 'ΜΑΧΗ PLAY-IN')
# --- γκρουπ (ιδιοι κανονες με t24) + «πρακτικα αποκλεισμενη» ---
W = collections.Counter(); L_ = collections.Counter(); GRP = {}; PRACT = set()
day = collections.defaultdict(list)
for i in np.argsort(dD, kind='stable'): day[(SEAS[i], dD[i])].append(i)
for (s, d) in sorted(day):
    teams = {t for (ss, t) in set(W) | set(L_) if ss == s}
    for i in day[(s, d)]: teams |= {G.home.values[i], G.away.values[i]}
    rec = {t: (W[(s, t)], L_[(s, t)]) for t in teams}
    pct = {t: (w + .5) / (w + l + 1) for t, (w, l) in rec.items()}
    worst5 = set(sorted(teams, key=lambda t: pct[t])[:5]) if len(teams) >= 30 else set()
    for conf in (EAST, set(teams) - EAST):
        ct = sorted([t for t in teams if t in conf], key=lambda t: -pct[t])
        if len(ct) < 15: continue
        Wn = [rec[t][0] for t in ct]; Rn = [82 - sum(rec[t]) for t in ct]
        for r, t in enumerate(ct):
            gp = sum(rec[t]); w, R = rec[t][0], 82 - gp
            if gp < 50: GRP[(s, d, t)] = 'νωρις'; continue
            up_ok = r > 0 and w + R >= Wn[r - 1]; down_ok = r < len(ct) - 1 and Wn[r + 1] + Rn[r + 1] >= w
            locked = (not up_ok) and (not down_ok); elim10 = w + R < Wn[9]
            if t in worst5: g = 'TANKING'
            elif elim10: g = 'ΑΔΙΑΦΟΡΗ'
            elif locked: g = 'ΚΛΕΙΔΩΜΕΝΗ'
            elif r < 6: g = 'ΜΑΧΗ ΘΕΣΗΣ 1-6'
            elif r < 12: g = 'ΜΑΧΗ PLAY-IN'
            else: g = 'αλλη'
            GRP[(s, d, t)] = g
            if g in ('ΜΑΧΗ PLAY-IN', 'αλλη') and r >= 10 and gp >= 60 and Wn[9] - w >= 5: PRACT.add((s, d, t))
    for i in day[(s, d)]:
        h, a = G.home.values[i], G.away.values[i]
        if ACT[i] > 0: W[(s, h)] += 1; L_[(s, a)] += 1
        elif ACT[i] < 0: W[(s, a)] += 1; L_[(s, h)] += 1
OLD = pd.read_csv(os.path.join(SC, '_t24_groups.csv'), usecols=['i', 't', 'g'])
agree = np.mean([GRP.get((SEAS[r.i], dD[r.i], r.t), 'νωρις') == r.g for r in OLD.itertuples(index=False)])
P(f'ελεγχος: γκρουπ ιδια με t24 σε {100 * agree:.1f}% των ομαδα-ματς · «πρακτικα αποκλεισμενες» ομαδα-μερες: {len(PRACT)}')
Y = pd.read_csv(os.path.join(SC, '_t24c_picks.csv')); Y = Y[Y.v == 'Α'].copy(); Y['gn'] = GN[Y.i]
Y['bad'] = Y.g.isin(NOM) & Y.og.isin(MOT)
Y['pract'] = [(SEAS[i], dD[i], t) in PRACT for i, t in zip(Y.i, Y.team)]
Y['bad4'] = Y.bad | (Y.pract & Y.og.isin(MOT))
TAUS = ('ανοιγμα', 'Τ−2ω', 'Τ−30′')
def u_by(d): return d.groupby('sea').res.sum().reindex(sorted(Y.sea.unique()), fill_value=0.0)
# ---------- Τ1 ----------
P(''); P('=== Τ1 · LOSO ΟΡΙΟΥ ΑΓΩΝΑ (picks μονο αν αγωνας < οριο) · βαση: σημερινο 71 ===')
CUTS = (71, 73, 76, 79)
for rule in (False, True):
    for tau in TAUS:
        y = Y[(Y.tau == tau) & (Y.gn >= 61)]
        if rule: y = y[~(y.bad & (y.gn >= 71))]
        U = {c: u_by(y[y.gn < c]) for c in CUTS}
        ch = []; diff = []; added = []
        for s in U[71].index:
            best = max(CUTS, key=lambda c: U[c].drop(s).sum()); ch.append(best)
            diff.append(U[best][s] - U[71][s]); added.append(y[(y.sea == s) & (y.gn >= 71) & (y.gn < best)])
        A_ = pd.concat(added) if added else y.iloc[:0]
        ok = sum(1 for x in diff if x > 0); tot = sum(diff)
        P(f'  {"με κανονα 2" if rule else "χωρις κανονα"} · {tau:8s} επιλογες {ch} · LOSO − 71: {tot:+.1f}μ (θετικο {ok}/5: {", ".join(f"{x:+.1f}" for x in diff)}) · '
          f'προστεθηκαν {len(A_)} picks CLV {A_.clv.mean() if len(A_) else float("nan"):+.2f} → {"ΠΕΡΝΑ" if (tot > 0 and ok >= 3 and len(A_) and A_.clv.mean() > 0) else "ΔΕΝ περνα"}')
    P('')
P('  περιγραφικα (ανοιγμα, χωρις κανονα): ' + ' · '.join(f'αγωνας {lo}-{hi}: ' + f'{100 * Y[(Y.tau == "ανοιγμα") & (Y.gn >= lo) & (Y.gn <= hi)].res.mean():+.1f}%' for lo, hi in ((71, 72), (73, 75), (76, 78), (79, 82))))
# ---------- Τ2 ----------
P(''); P('=== Τ2 · ΚΑΝΟΝΑΣ 2 στους αγωνες 61-70 (picks που θα αφαιρουσε) ===')
for tau in TAUS:
    d = Y[(Y.tau == tau) & (Y.gn >= 61) & (Y.gn <= 70) & Y.bad]; u = u_by(d)
    P(f'  {tau:8s} αφαιρει {len(d)} picks · ROI τους {100 * d.res.mean():+.1f}% · μοναδες/σεζον {", ".join(f"{x:+.1f}" for x in u)} · ≤0 σε {int((u <= 0).sum())}/5 → '
      f'{"ΠΕΡΝΑ" if (u <= 0).sum() >= 4 else "ΔΕΝ περνα"}')
# ---------- Τ4 ----------
P(''); P('=== Τ4 · «ΠΡΑΚΤΙΚΑ ΑΠΟΚΛΕΙΣΜΕΝΗ» ως χωρις κινητρο (επιπλεον picks που αφαιρει) ===')
for lo, hi in ((71, 75), (61, 70)):
    for tau in TAUS:
        d = Y[(Y.tau == tau) & (Y.gn >= lo) & (Y.gn <= hi) & Y.bad4 & ~Y.bad]; u = u_by(d)
        P(f'  αγωνες {lo}-{hi} · {tau:8s} επιπλεον {len(d)} picks · ROI {100 * d.res.mean() if len(d) else float("nan"):+.1f}% · μοναδες/σεζον {", ".join(f"{x:+.1f}" for x in u)} · ≤0 σε {int((u <= 0).sum())}/5'
          + (f' → {"ΠΕΡΝΑ" if (u <= 0).sum() >= 4 else "ΔΕΝ περνα"}' if lo == 71 else ' (περιγραφικο)'))
# ---------- Τ5 ----------
P(''); P('=== Τ5 · ΠΑΡΑΔΕΙΓΜΑΤΑ (αγωνες 71-75, ανοιγμα) ===')
y = Y[(Y.tau == 'ανοιγμα') & (Y.gn >= 71) & (Y.gn <= 75)]
def show(r):
    own = r.L if r.sd == 1 else -r.L; i = int(r.i); mg = ACT[i] if r.sd == 1 else -ACT[i]
    P(f'   {str(G.date.values[i])[:10]} · στηριζουμε {r.team} ({r.g}) {own:+g} @{r.od:.2f} vs {r.opp} ({r.og}) · {"εντος" if r.sd == 1 else "εκτος"} · '
      f'μοντελο {r.team} {(r.m if r.sd == 1 else -r.m):+.1f} · edge {100 * r.e:.0f}% · αποτελεσμα {r.team} {mg:+.0f} → {r.res:+.2f}μ')
P('  αφαιρουνται:'); [show(r) for r in y[y.bad].sample(min(3, int(y.bad.sum())), random_state=1).itertuples()]
P('  μενουν:'); [show(r) for r in y[~y.bad].sample(3, random_state=1).itertuples()]
# ---------- ΥΠΟΨΙΑ 2 ----------
P(''); P('=== ΥΠΟΨΙΑ 2 · ΑΟΥΤΣΑΙΝΤΕΡ ΜΕ ΚΙΝΗΤΡΟ: παρατανε / κρατανε δυναμεις; ===')
F = pd.read_csv(os.path.join(SC, '_t25_feats.csv'))
FK = {(r.date, r.team): r for r in F.itertuples(index=False)}
sched = collections.defaultdict(list)
for i in np.argsort(dD, kind='stable'):
    sched[(SEAS[i], G.home.values[i])].append(i); sched[(SEAS[i], G.away.values[i])].append(i)
rows = []
for i, d_ in MKH.items():
    if GN[i] < 61: continue
    L = d_['o'][0]; s = SEAS[i]; d = dD[i]
    for t, o, sg in ((G.home.values[i], G.away.values[i], 1), (G.away.values[i], G.home.values[i], -1)):
        g = GRP.get((s, d, t)); og = GRP.get((s, d, o))
        if g not in MOT: continue
        own = L if sg == 1 else -L
        if own <= 0: continue                                            # μονο αουτσαιντερ
        seq = sched[(s, t)]; k = seq.index(i); nxt = seq[k + 1:k + 4]
        easy = sum(1 for j in nxt if GRP.get((s, d, G.away.values[j] if G.home.values[j] == t else G.home.values[j])) in NOM)
        f = FK.get((str(d), t))
        rows.append(dict(sea=s, gn=GN[i], late=GN[i] >= 76, home=sg == 1, og=og, own=own, easy=easy,
                         rm=np.nan, rc=sg * (ACT[i] - d_['c'][1]) if 'c' in d_ else np.nan, ro=sg * (ACT[i] - d_['o'][1]),
                         dcore=(f.core_min - f.core_min_avg) if f is not None else np.nan,
                         trail=(f.q4c_trail10 - f.q4c_trail10_avg) if f is not None else np.nan,
                         cover=float(sg * ACT[i] + own > 0)))
Z = pd.DataFrame(rows)
def zl(d): return (f'n{len(d):4d} · Δ λεπτα βασικων {d.dcore.mean():+5.1f} · Δ βασικοι 4η οταν χανουν 10+ {100 * d.trail.mean():+5.1f}% (n{d.trail.notna().sum()}) · '
                   f'καλυψη γραμμης ανοιγματος {100 * d.cover.mean():4.1f}% · υπολ. vs αγορα ανοιγ. {d.ro.mean():+5.2f}')
for lab, m in (('αγωνες 61-75', ~Z.late), ('αγωνες 76-82', Z.late)):
    P(f'  {lab}: {zl(Z[m])}')
    for nm, mm in (('  αντιπαλος με κινητρο', Z.og.isin(MOT)), ('  αντιπαλος χωρις κινητρο', Z.og.isin(NOM))):
        P(f'     {nm:26s} {zl(Z[m & mm])}')
    for nm, mm in (('  επομενα 3: ≥2 ευκολα', Z.easy >= 2), ('  επομενα 3: ≤1 ευκολο', Z.easy <= 1)):
        P(f'     {nm:26s} {zl(Z[m & mm & Z.og.isin(MOT)])}  [μονο vs κινητρο]')
    for nm, mm in (('  εκτος εδρας', ~Z.home), ('  εντος', Z.home)):
        P(f'     {nm:26s} {zl(Z[m & mm & Z.og.isin(MOT)])}  [μονο vs κινητρο]')
open(os.path.join(SC, 't27_april_rules_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
