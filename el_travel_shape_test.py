# -*- coding: utf-8 -*-
"""el_travel_shape_test.py — ΤΑΞΙΔΙ 2ου ΜΑΤΣ ΔΙΑΒΟΛΟΒΔΟΜΑΔΑΣ: ΣΧΗΜΑ του κανονα (10/10/2026, Στελιος: «δεν βγαζει νοημα, στα 1000 χλμ +4.5 και
στα 984 μηδεν» → «τρεξε το τεστ»). Live (el_travel.py): γηπ. εμεινε σπιτι & φιλοξ. ≥1000 χλμ απο το προηγ. γηπεδο σε ≤3.5 μερες → +4.5/+6.6.
Ιδιο δειγμα με el_dw_fatigue_deep (E2021-25 RS, live μοντελο h_new, Crown). Ολες οι εκδοχες ΜΟΝΟ οταν ο γηπεδουχος επαιξε και το 1ο ματς σπιτι.
ΕΚΔΟΧΕΣ (μια παραμετρος η καθε μια εκτος F, εκτιμηση LOSO):
 A ΣΚΑΛΙ ≥1000 χλμ (αναφορα) · B ΖΩΝΗ ΩΡΑΣ: ο φιλοξ. αλλαζει ≥1 ωρα (σταθερη «χειμερινη» ωρα γηπεδου, χωρις θερινη/χειμερινη αλλαγη)
 C ΟΜΑΛΗ ραμπα 600→1400 χλμ (0 → πληρης) · D ΟΜΑΛΗ ραμπα 400→1600 · E ≥1000 Η ζωνη ωρας (ενωση) · F ≥1000 ΚΑΙ ξεχωριστα ζωνη ωρας (2 παραμετροι)
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): εκδοχη ΑΝΤΙΚΑΘΙΣΤΑ το σκαλι αν (1) LOSO RMSE καλυτερο απο «καμια διορθωση» σε ≥4/5 σεζον ΚΑΙ (2) συνολικο
LOSO RMSE (αθροισμα 5 σεζον) ΟΧΙ χειροτερο απο το σκαλι. Αναφορα: picks χαντικαπ (alert Crown, ≥8%), και τι δινει η καθε εκδοχη στα 4 ματς της 15-16/10.
Εξοδος: el_travel_shape_out.txt"""
import sys, io, contextlib, json, math
import numpy as np, pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
NS = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_dw_fatigue_deep.py', encoding='utf-8').read().split("def loso2(fn, lab):")[0]
         .replace("open('el_dw_fatigue_deep_out.txt', 'w'", "open('_unused_shape.txt', 'w'"), NS)
sys.stdout.reconfigure(encoding='utf-8')
G, T, HH, SE5, VEN, D, REC, PR, key, pick, settle, km, ll = (NS[k] for k in ('G', 'T', 'HH', 'SE5', 'VEN', 'D', 'REC', 'PR', 'key', 'pick', 'settle', 'km', 'll'))
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
# ---- σταθερη ωρα γηπεδου = η μικροτερη που εμφανιζεται (χειμερινη) ----
SCH = json.load(open('el_sched.json', encoding='utf-8'))
STD = {}
for L in SCH.values():
    for x in L:
        try: v = float(x.get('tz'))
        except Exception: continue
        n = str(x.get('vname') or '').strip().upper()
        if n: STD[n] = min(STD.get(n, 99), v)
T['vn'] = [str((VEN.get(k) or (None, None))[0] or '').strip().upper() for k in T.key]
T['prev_vn'] = T.groupby(['season', 'team']).vn.shift(1)
T['tzd'] = [abs(STD[a] - STD[b]) if (d and a in STD and b in STD) else np.nan for a, b, d in zip(T.vn, T.prev_vn, T.dw2)]
TA = T[T.side == -1].set_index('pos')
G['a_tzd'] = TA.loc[G.index, 'tzd'].values
base = HH & G.a_travel.notna()
P(f'ματς 2ου διαβολοβδομαδας με γηπ. σπιτι και γνωστη αποσταση: {int(base.sum())} · με ζωνη ωρας ≥1: {int((base & (G.a_tzd >= 1)).sum())} · ≥1000 χλμ: {int((base & (G.a_travel >= 1000)).sum())} · και τα δυο: {int((base & (G.a_tzd >= 1) & (G.a_travel >= 1000)).sum())}')
ramp = lambda k, lo, hi: np.clip((k - lo) / (hi - lo), 0, 1)
VAR = {
    'A ΣΚΑΛΙ ≥1000 χλμ (live)':          lambda x: [(x.a_travel >= 1000).astype(float)],
    'B ΖΩΝΗ ΩΡΑΣ ≥1':                     lambda x: [(x.a_tzd >= 1).astype(float)],
    'C ΟΜΑΛΗ 600→1400 χλμ':               lambda x: [ramp(x.a_travel, 600, 1400)],
    'D ΟΜΑΛΗ 400→1600 χλμ':               lambda x: [ramp(x.a_travel, 400, 1600)],
    'E ≥1000 Η ζωνη ωρας':                lambda x: [((x.a_travel >= 1000) | (x.a_tzd >= 1)).astype(float)],
    'F ≥1000 + ζωνη ωρας (2 τιμες)':      lambda x: [(x.a_travel >= 1000).astype(float), (x.a_tzd >= 1).astype(float)],
}
def feats(fn, x, m):
    F = np.zeros((len(x), 2)); fs = fn(x[m]) if m.any() else []
    for j, f in enumerate(fs): F[np.where(m.values)[0], j] = np.nan_to_num(np.asarray(f, float))
    return F[:, :len(fn(x[m])) if m.any() else 1]
RES, PAR = {}, {}
for nm, fn in VAR.items():
    rb, rn, pars = [], [], []
    for Y in SE5:
        tr_, te = G[G.season != Y], G[G.season == Y]
        Ft = feats(fn, tr_, base.loc[tr_.index]); b = np.linalg.lstsq(Ft, tr_.rm_m.values, rcond=None)[0] if Ft.any() else np.zeros(Ft.shape[1]); pars.append(b)
        Fe = feats(fn, te, base.loc[te.index])
        rb.append(np.sqrt(np.mean((te.margin - te.hm) ** 2))); rn.append(np.sqrt(np.mean((te.margin - te.hm - Fe @ b) ** 2)))
    RES[nm] = (np.array(rb), np.array(rn)); PAR[nm] = np.mean(pars, axis=0)
P(''); P('## LOSO RMSE (− = καλυτερα) · παραμετρος = ποντοι υπερ γηπεδουχου στην πληρη διορθωση')
rA = RES['A ΣΚΑΛΙ ≥1000 χλμ (live)'][1]
for nm in VAR:
    rb, rn = RES[nm]; w = int(sum(rn < rb))
    ok = '' if nm.startswith('A') else ('  <- ΑΝΤΙΚΑΘΙΣΤΑ' if w >= 4 and rn.sum() <= rA.sum() else '  ✗')
    P(f'  {nm:32s} παραμ. {" / ".join(f"{v:+.2f}" for v in PAR[nm])} · vs καμια ' + ' '.join(f'{v:+.3f}' for v in rn - rb)
      + f' → {w}/5 · συνολο vs καμια {rn.sum() - rb.sum():+.4f} · vs ΣΚΑΛΙ {rn.sum() - rA.sum():+.4f} ({int(sum(rn < rA))}/5 σεζον καλυτερα){ok}')
# ---- picks (alert Crown, ≥8%, οχι τελευταιο 2ωρο) με παραμετρους LOSO ----
def first_pick(m, r, p):
    ser, tip = r['ser'], r['tip']
    for k_, row in enumerate(ser):
        if row[0] >= tip: break
        side, e, od = pick(21, m, row)
        if e < 0.08: continue
        if k_ > 0 and (tip - row[0]) / 3600 < 2: return None
        return settle(21, p, side, row, od)
    return None
P(''); P('## PICKS χαντικαπ (alert Crown, ≥8%) ΣΤΑ ΜΑΤΣ ΠΟΥ ΑΓΓΙΖΕΙ ΚΑΘΕ ΕΚΔΟΧΗ (ολη η εικονα: και τα υπολοιπα ματς μενουν ιδια)')
for nm, fn in VAR.items():
    tot0, tot1, n0, n1, per = 0.0, 0.0, 0, 0, {}
    for Y in SE5:
        tr_ = G[G.season != Y]; Ft = feats(fn, tr_, base.loc[tr_.index]); b = np.linalg.lstsq(Ft, tr_.rm_m.values, rcond=None)[0]
        te = G[(G.season == Y)]; Fe = feats(fn, te, base.loc[te.index]); adj = pd.Series(Fe @ b, index=te.index)
        for p in te.index[(adj.abs() > 1e-9).values | False]:
            if p not in REC[21]: continue
            m0 = PR.get(key(p), {}).get('h_new')
            if m0 is None or not np.isfinite(m0): continue
            a, c = first_pick(m0, REC[21][p], p), first_pick(m0 + adj[p], REC[21][p], p)
            if a is not None: tot0 += a; n0 += 1
            if c is not None: tot1 += c; n1 += 1
            per[Y] = per.get(Y, 0.0) + (c or 0.0) - (a or 0.0)
    P(f'  {nm:32s} χωρις διορθωση {n0:3d} picks {tot0:+6.1f}μ → με διορθωση {n1:3d} picks {tot1:+6.1f}μ · διαφορα ανα σεζον ' + ' '.join(f'{Y[-2:]}:{per.get(Y, 0):+.1f}' for Y in SE5))
# ---- τα 4 ματς της Πεμ/Παρ 15-16/10 (γηπ. σπιτι στο 1ο) ----
P(''); P('## 15-16/10 (γηπ. επαιξε και το 1ο σπιτι): τι θα εδινε καθε εκδοχη (παραμετρος ολων των σεζον, υπερ γηπεδουχου)')
CUR = [('Φενερ – Παρτιζαν', 'BELGRADE ARENA', 'ULKER SPORTS AND EVENT HALL'), ('Βαλενθια – Μακαμπι', 'PALAU BLAUGRANA', 'ROIG ARENA'),
       ('Μιλανο – Ντουμπαι', 'FERNANDO BUESA ARENA', 'UNIPOL FORUM'), ('Μπαρτσελονα – Ολυμπιακος', 'ROIG ARENA', 'PALAU BLAUGRANA')]
for nm_, a, b in CUR:
    k = km(ll(a), ll(b)); tz = abs(STD.get(a, 0) - STD.get(b, 0)); x = pd.DataFrame(dict(a_travel=[k], a_tzd=[tz]))
    cells = []
    for nm, fn in VAR.items():
        F = np.array([np.asarray(f, float) for f in fn(x)]).T; cells.append(f'{nm[0]} {float((F @ PAR[nm])[0]):+.1f}')
    P(f'  {nm_:26s} {k:5.0f} χλμ · ζωνη ωρας {tz:.0f} · ' + ' · '.join(cells))
open('el_travel_shape_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
