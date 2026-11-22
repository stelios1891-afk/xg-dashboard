# -*- coding: utf-8 -*-
"""el_late_groups.py — ΕΥΡΩΛΙΓΚΑ: ΑΡΓΑ PICKS ΣΕ ΓΚΡΟΥΠ ΑΝΑ ΑΙΤΙΑ (29/10/2026, Στελιος «ευρωλιγκα μονο ναι συμφωνω»).
Σαρωση σαν scanner (καθε αλλαγη τιμης Crown + καθε ειδηση RotoWire +15′), ΣΗΜΕΡΙΝΗ μηχανη: χαντικαπ «PIR + αμυνα» (LOSO), συνολα ΧΩΡΙΣ διορθωση.
ΧΩΡΙΣ τους κανονες αποφυγης (για να φανουν ολα)· σημειωνεται αν θα τα εκοβε σημερα late2h / late6dog / move15.
pick = πρωτη φορα edge ≥8% (χαντικαπ σ 11.5, συνολα σ live). «Αργο» = γεννηθηκε ΜΕΤΑ την 1η τιμη.
ΓΚΡΟΥΠ (με τη σειρα — το πρωτο που ταιριαζει), κινηση = αναμενομενη διαφορα/συνολο της αγορας (με τις αποδοσεις), − = ΚΟΝΤΡΑ σε εμας:
  Α ΑΠΟΥΣΙΑ        αλλαξε η ΔΙΚΗ μας προβλεψη (ειδηση) και χωρις την αλλαγη στην ιδια τιμη δεν θα ηταν pick
  Β ΞΑΦΝΙΚΗ        κοντρα ≥1 π. μεσα σε 1 ωρα
  Γ ΣΤΑΔΙΑΚΗ       κοντρα ≥0.5 π. σε 3 ή 6 ωρες (χωρις αλμα)
  Δ ΜΟΝΟ ΑΠΟΔΟΣΗ   ιδια γραμμη με 3ω πριν, αλλαξε μονο η αποδοση
  Ε ΑΚΙΝΗΤΗ/ΑΛΛΟ   τα υπολοιπα (μικρες αλλαγες που περασαν το 8%)
ΜΕΤΡΗΣΗ ανα γκρουπ × αγορα (φαβ/αουτσ/over/under) × ωρα: picks, μοναδες, ROI, θετικες σεζον, CLV (π.), μοναδες αν το επαιζα στο ΚΛΕΙΣΙΜΟ.
ΚΡΙΤΗΡΙΟ υποψηφιου κανονα (προ-δηλωμενο): ≥30 picks · αρνητικο σε ≥4/5 σεζον · και κραταει «εκτος δειγματος» (επιλογη σε 4 σεζον → ελεγχος στην 5η).
Εξοδος: el_late_groups_out.txt"""
import os, sys, io, contextlib, bisect, collections, time
import numpy as np
ROOT = r'C:\Users\steli\My Drive\Betting Model'; os.chdir(ROOT); sys.path.insert(0, ROOT)
T00 = time.time()
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open('el_pird_tests.py', encoding='utf-8').read().split('# ---- σαρωση σαν scanner ----')[0]
s0 = "def save(): open('el_pird_tests_out.txt', 'w', encoding='utf-8').write('" + chr(92) + "n'.join(out))"
assert src.count(s0) == 1
TH = {'__name__': 'pird'}
with contextlib.redirect_stdout(_B()): exec(src.replace(s0, 'def save(): return'), TH)
src2 = open('el_totals_absence_final.py', encoding='utf-8').read().split('# ---- σαρωση ----')[0]
s2 = "def save(): open('el_totals_absence_final_out.txt', 'w', encoding='utf-8').write('" + chr(92) + "n'.join(out))"
assert src2.count(s2) == 1
TT = {'__name__': 'taf'}
with contextlib.redirect_stdout(_B()): exec(src2.replace(s2, 'def save(): return'), TT)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open('el_late_groups_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
S = TH['S']; SE = S['SE']
P(f'harness ετοιμα · {time.time() - T00:.0f} δευτ.')
def mu_at(ser, t):
    i = bisect.bisect_right([x[0] for x in ser], t) - 1
    return ser[max(i, 0)]
def classify(ser, t, row, sd, absent_cause):
    if absent_cause: return 'Α ΑΠΟΥΣΙΑ'
    m_now = row[1]
    if (m_now - mu_at(ser, t - 3600)[1]) * sd <= -1.0: return 'Β ΞΑΦΝΙΚΗ'
    if min((m_now - mu_at(ser, t - 3 * 3600)[1]) * sd, (m_now - mu_at(ser, t - 6 * 3600)[1]) * sd) <= -0.5: return 'Γ ΣΤΑΔΙΑΚΗ'
    if abs(mu_at(ser, t - 3 * 3600)[2] - row[2]) < 1e-9: return 'Δ ΜΟΝΟ ΑΠΟΔΟΣΗ'
    return 'Ε ΑΚΙΝΗΤΗ/ΑΛΛΟ'
RECS = []
# ================= ΧΑΝΤΙΚΑΠ =================
rows, N, NT, REC, edge_pick, settle, featsPD, BPD = (S['rows'], S['N'], S['NT'], S['REC'], S['edge_pick'], S['settle'], TH['featsPD'], TH['BPD'])
for i, r in enumerate(rows):
    b = BPD[('loso', r['y'])]
    d_ = REC[21][r['pos']]; tip = d_['tip']; ser = [x for x in d_['ser'] if x[0] < tip]
    if not ser or b is None: continue
    t0 = ser[0][0]; tl = [x[0] for x in ser]
    nts = set(t + 900 for team in (r['hc'], r['ac']) for t in NT.get((r['sea'], team), []) if t0 < t + 900 < tip)
    prev_a = None
    for j, e in enumerate(sorted(set(tl) | nts)):
        row = ser[bisect.bisect_right(tl, e) - 1]
        a = float(featsPD(i, e) @ b)
        sd, ed, od = edge_pick(r['m'] + a, row[2], row[3], row[4])
        if ed >= .08:
            abs_cause = False
            if j > 0 and prev_a is not None and abs(a - prev_a) > 1e-9:
                sd0, ed0, _ = edge_pick(r['m'] + prev_a, row[2], row[3], row[4]); abs_cause = not (ed0 >= .08 and sd0 == sd)
            hrs = (tip - e) / 3600; dog = (row[2] > 0) if sd == 1 else (row[2] < 0)
            cl = ser[-1]; sdc, edc, odc = sd, None, (cl[3] if sd == 1 else cl[4])
            RECS.append(dict(mkt='χαντικαπ', kind='αουτσ.' if dog else 'φαβορι', sea=r['y'], late=j > 0, hrs=hrs, grp=('ΑΝΟΙΓΜΑ' if j == 0 else classify(ser, e, row, sd, abs_cause)),
                             u=settle(r['act'], row[2], sd, od), uc=settle(r['act'], cl[2], sd, odc), clv=(cl[1] - row[1]) * sd,
                             rule=('late2h' if hrs < 2 else ('late6dog' if dog and hrs < 6 and (e - t0) >= 45 * 60 else ''))))
            break
        prev_a = a
P(f'χαντικαπ: {sum(1 for x in RECS if x["mkt"] == "χαντικαπ")} picks · {time.time() - T00:.0f} δευτ.')
# ================= ΣΥΝΟΛΑ =================
rowsB, SER, HAS, tp, NTB = TT['rowsB'], TT['SER'], TT['HAS'], TT['tp'], TT['NTB']
for i, r in enumerate(rowsB):
    if not HAS[i]: continue
    ser, tip = SER[i]; t0 = ser[0][0]; mu0 = ser[0][1]
    for j, row in enumerate(ser):
        po, pp, pu = tp(r['T'], row[2]); eo, eu = po * row[3] + pp - 1, pu * row[4] + pp - 1
        sd, ed, od = (1, eo, row[3]) if eo >= eu else (-1, eu, row[4])
        if ed < .08: continue
        e = row[0]; hrs = (tip - e) / 3600; rule = ''
        if (row[1] - mu0) * sd <= -1.5:
            cx = next(x[0] for x in ser if (x[1] - mu0) * sd <= -1.5)
            if (tip - cx) / 3600 >= 6: rule = 'move15'
        x = (r['hs'] + r['as_'] - row[2]) * sd; cl = ser[-1]; xc = (r['hs'] + r['as_'] - cl[2]) * sd; odc = cl[3] if sd == 1 else cl[4]
        RECS.append(dict(mkt='συνολα', kind='over' if sd == 1 else 'under', sea=r['y'], late=j > 0, hrs=hrs, grp=('ΑΝΟΙΓΜΑ' if j == 0 else classify(ser, e, row, sd, False)),
                         u=(od - 1) if x > 0 else (0.0 if x == 0 else -1.0), uc=(odc - 1) if xc > 0 else (0.0 if xc == 0 else -1.0), clv=(cl[1] - row[1]) * sd, rule=rule))
        break
P(f'συνολα: {sum(1 for x in RECS if x["mkt"] == "συνολα")} picks · {time.time() - T00:.0f} δευτ.')
# ================= ΠΙΝΑΚΕΣ =================
def stat(L):
    if not L: return None
    u = np.array([x['u'] for x in L]); uc = np.array([x['uc'] for x in L]); ps = {s: sum(x['u'] for x in L if x['sea'] == s) for s in SE}
    return dict(n=len(L), U=u.sum(), roi=u.mean() * 100, pos=sum(v > 0 for v in ps.values()), neg=sum(v < 0 for v in ps.values()), ps=ps,
                clv=np.mean([x['clv'] for x in L]), UC=uc.sum())
def fmt(st):
    if st is None: return '—'
    return (f'{st["n"]:4d} picks · {st["U"]:+6.1f}μ · ROI {st["roi"]:+6.1f}% · θετ {st["pos"]}/5 · CLV {st["clv"]:+.2f} · στο κλεισιμο {st["UC"]:+6.1f}μ · '
            + ' '.join(f'{s[-2:]}:{v:+.1f}' for s, v in st['ps'].items()))
GRP = ['ΑΝΟΙΓΜΑ', 'Α ΑΠΟΥΣΙΑ', 'Β ΞΑΦΝΙΚΗ', 'Γ ΣΤΑΔΙΑΚΗ', 'Δ ΜΟΝΟ ΑΠΟΔΟΣΗ', 'Ε ΑΚΙΝΗΤΗ/ΑΛΛΟ']
KIND = {'χαντικαπ': ['φαβορι', 'αουτσ.'], 'συνολα': ['over', 'under']}
HB = [('>12ω', lambda h: h > 12), ('6-12ω', lambda h: 6 < h <= 12), ('2-6ω', lambda h: 2 < h <= 6), ('<2ω', lambda h: h <= 2)]
for mkt in ('χαντικαπ', 'συνολα'):
    R = [x for x in RECS if x['mkt'] == mkt]
    P(''); P(f'################ {mkt.upper()} · ολα τα picks (χωρις κανονες αποφυγης) ################')
    P(f'  ΟΛΑ                    {fmt(stat(R))}')
    P(f'  σημερα παιζονται       {fmt(stat([x for x in R if not x["rule"]]))}')
    for g in GRP:
        L = [x for x in R if x['grp'] == g]
        P(''); P(f'  ## {g}: {fmt(stat(L))}')
        if g == 'ΑΝΟΙΓΜΑ': continue
        for rl in sorted({x['rule'] for x in L}):
            P(f'     {"παιζονται σημερα" if not rl else "κοβει ο " + rl:22s} {fmt(stat([x for x in L if x["rule"] == rl]))}')
        for k in KIND[mkt]:
            P(f'     {k:8s} {fmt(stat([x for x in L if x["kind"] == k]))}')
        for hb, f in HB:
            Lh = [x for x in L if f(x['hrs'])]
            if Lh: P(f'     {hb:8s} {fmt(stat(Lh))}' + (f' · κοβονται σημερα {sum(1 for x in Lh if x["rule"])}' if any(x['rule'] for x in Lh) else ''))
    save()
# ================= ΥΠΟΨΗΦΙΟΙ ΚΑΝΟΝΕΣ =================
P(''); P('################ ΥΠΟΨΗΦΙΟΙ ΚΑΝΟΝΕΣ (μονο οσα ΠΑΙΖΟΝΤΑΙ σημερα · κελια γκρουπ × αγορα × ωρα · ≥30 picks · αρνητικα ≥4/5 σεζον) ################')
P('  «εκτος δειγματος»: για καθε σεζον, το κελι επιλεγεται μονο αν στις ΑΛΛΕΣ 4 ειναι αρνητικο σε ≥3/4 με ROI <0 → τι εκανε στη σεζον που αφησαμε εξω')
cells = collections.defaultdict(list)
for x in RECS:
    if not x['late'] or x['rule']: continue
    for hb, f in [('ολες οι ωρες', lambda h: True)] + HB:
        if f(x['hrs']): cells[(x['mkt'], x['grp'], x['kind'], hb)].append(x)
        cells[(x['mkt'], x['grp'], 'ολα', hb)].append(x) if f(x['hrs']) else None
found = False
for key, L in sorted(cells.items()):
    st = stat(L)
    if st['n'] < 30 or st['neg'] < 4: continue
    found = True; oos = []
    for s in SE:
        Lo = [x for x in L if x['sea'] != s]; ps = [sum(x['u'] for x in Lo if x['sea'] == q) for q in SE if q != s]
        sel = sum(v < 0 for v in ps) >= 3 and sum(x['u'] for x in Lo) < 0
        if sel: oos.append(sum(x['u'] for x in L if x['sea'] == s))
    P(f'  {" · ".join(key):55s} {fmt(st)} · εκτος δειγματος: επιλεγεται {len(oos)}/5, εκει {sum(oos):+.1f}μ ({sum(v < 0 for v in oos)}/{len(oos)} αρνητικα)')
if not found: P('  κανενα κελι δεν πληροι ≥30 picks & ≥4/5 αρνητικες σεζον')
P(f'\nχρονος {time.time() - T00:.0f} δευτ.'); save()
