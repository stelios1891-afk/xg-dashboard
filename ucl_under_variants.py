# -*- coding: utf-8 -*-
"""ucl_under_variants.py — 19/10/2026 (Στελιος: «τρεξτο» + «φετος βλεπουμε περισσοτερα under — μηπως η αγορα προσαρμοστηκε;»).
ΜΕΡΟΣ 1 — UCL UNDER, ΠΡΟ-ΔΗΛΩΜΕΝΕΣ παραλλαγες (κατηγορια Α, μηχανη συνολων live, τιμη 48ω πριν, 1.70-2.10, Crown/SBOBET μεσος):
  Α σημερα ≥10% · Β ≥14% · Γ ≥18% · Δ ≥10% μονο γραμμη <3 · Ε ≥10% μονο γραμμη ≤3 · Ζ κανενα under.
  ΚΡΙΤΗΡΙΟ (γραφτηκε πριν): παραλλαγη αντικαθιστα το σημερινο ΜΟΝΟ αν ROI > 0 ΚΑΙ στις 2 σεζον νεας μορφης ΚΑΙ στο συνολο 2022-26,
  και μοναδες ≥ σημερινου στη νεα μορφη. Αν καμια δεν περνα και το σημερινο δεν περνα ουτε αυτο → προταση «κανενα under» (Ζ).
ΜΕΡΟΣ 2 — ΠΡΟΣΑΡΜΟΓΗ ΑΓΟΡΑΣ: ανα σεζον (UCL, κατηγορια Α): δικαιο συνολο αγορας στο κλεισιμο, συνολο μοντελου, πραγματικα γκολ,
  και ποσα ματς το μοντελο βλεπει πανω/κατω απο την αγορα (≥0.25 γκολ). 2022-26 Crown/SBOBET (Nowgoal) · 2026-27 Pinnacle (euro_odds_hist)."""
import sys, os, json
_s = open('uel_full_review.py', encoding='utf-8').read().split("print('=' * 100 + NL + '1. ΣΥΝΟΛΑ")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
_KEEP = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _KEEP
sys.stdout.reconfigure(encoding='utf-8')
def snap_ou(mid, bk, h):
    ko = KO.get(mid); seq = TOU.get((mid, bk))
    if not ko or not seq: return None
    cut = ko - h * 3600 if h else ko + 900
    prev = [x for x in seq if x[0] <= cut]
    return prev[-1][1:] if prev else None
I = np.array([i for i in np.where(COMP == 'ChampionsLeague')[0] if SRCC[i] == 'FF']); M = [str(MIDS[i]) for i in I]; S = SEA[I]; TOT = GH[I] + GA[I]
U, AD = [], []
for k in range(len(I)):
    td = ES.tot_dist(OH[I][k], OA[I][k], DRAW_SCALE); mt = OH[I][k] + OA[I][k]
    fair = []
    for bk in ('Crown', 'SBOBET'):
        c = snap_ou(M[k], bk, 0)
        if c: fair.append(mtot(*c))
        s = snap_ou(M[k], bk, 48)
        if not s: continue
        L, o, un = s; po, pu = ES.p_over(td, L)
        if 1.70 <= un <= 2.10:
            U.append(dict(sea=S[k], bk=bk, L=L, e=pu * (un - 1) * (1 - picks.MARGIN) - po, pnl=settle(TOT[k], L, un, False)))
    if fair: AD.append(dict(sea=S[k], mkt=float(np.mean(fair)), mdl=mt, act=TOT[k]))
U = pd.DataFrame(U)
VAR = [('Α σημερα ≥10%', lambda y: y.e >= .10), ('Β ≥14%', lambda y: y.e >= .14), ('Γ ≥18%', lambda y: y.e >= .18),
       ('Δ ≥10% γραμμη <3', lambda y: (y.e >= .10) & (y.L < 3)), ('Ε ≥10% γραμμη ≤3', lambda y: (y.e >= .10) & (y.L <= 3))]
print('ΜΕΡΟΣ 1 — UCL UNDER (48ω πριν, κατηγορια Α)')
print(f'   {"παραλλαγη":20s} │ {"νεα μορφη 2024-26":^40s} │ {"ολες 2022-26":^28s} │ κριτηριο')
base_u = None
for lab, f in VAR:
    y = U[f(U)]
    def st(z):
        if not len(z): return 0, 0.0, 0.0
        m = z.groupby('bk').pnl.mean(); n = z.groupby('bk').size().mean(); return n, m.mean(), m.mean() * n
    yn = y[y.sea.isin(['2425', '2526'])]; n1, r1, u1 = st(yn); n2, r2, u2 = st(y)
    s = yn.groupby('sea').pnl.mean()
    if base_u is None: base_u = u1
    ok = r2 > 0 and len(s) == 2 and (s > 0).all() and u1 >= base_u - 1e-9
    print(f'   {lab:20s} │ {n1:4.0f} picks {100 * r1:+6.1f}% {u1:+5.1f}μ ({" ".join(f"{k}:{100 * v:+.0f}%" for k, v in s.items())}) │ {n2:4.0f} picks {100 * r2:+6.1f}% {u2:+5.1f}μ │ {"✓" if ok else "✗"}')
print('   Ζ κανενα under       │ 0 picks · 0 μοναδες')
# 2026-27 (Pinnacle): κλεισιμο = τελευταια εγγραφη πριν τη σεντρα · μοντελο = euro_projections (FotMob και οι 2)
H = {}
for l in open('euro_odds_hist.jsonl', encoding='utf-8'):
    r = json.loads(l)
    if r.get('comp') != 'ChampionsLeague' or not r.get('tl') or not r.get('to') or not r.get('tu'): continue
    if r['t'] < r['ko'][:16]: H[r['mid']] = r
PJ = json.load(open('euro_projections.json', encoding='utf-8'))
for v in PJ.values():
    if not (isinstance(v, list) and v and isinstance(v[0], dict) and 'mid' in v[0]): continue
    for m in v:
        if m.get('comp') != 'ChampionsLeague' or not m.get('finished') or m.get('src_h') != 'FotMob' or m.get('src_a') != 'FotMob': continue
        r = H.get(str(m['mid']))
        sc = str(m.get('score') or '').replace(' ', '').split('-')
        if not r or len(sc) != 2: continue
        AD.append(dict(sea='2627', mkt=mtot(r['tl'], r['to'], r['tu']), mdl=m.get('xgh_ou', m['xgh']) + m.get('xga_ou', m['xga']), act=int(sc[0]) + int(sc[1])))
A = pd.DataFrame(AD); A['gap'] = A.mdl - A.mkt
print('\nΜΕΡΟΣ 2 — ΣΥΝΟΛΑ UCL (κατηγορια Α) ανα σεζον: αγορα στο κλεισιμο vs μοντελο vs πραγματικα')
print(f'   {"σεζον":8s} {"ματς":>5s} │ {"αγορα":>6s} {"μοντελο":>8s} {"γκολ":>6s} │ {"μοντ−αγορα":>10s} │ {"μοντελο ΠΑΝΩ ≥0.25":>19s} {"μοντελο ΚΑΤΩ ≥0.25":>19s} │ {"γκολ−αγορα":>10s}')
for s, y in A.groupby('sea'):
    print(f'   {s:8s} {len(y):5d} │ {y.mkt.mean():6.2f} {y.mdl.mean():8.2f} {y.act.mean():6.2f} │ {y.gap.mean():+10.2f} │ {100 * (y.gap >= .25).mean():18.0f}% {100 * (y.gap <= -.25).mean():18.0f}% │ {(y.act - y.mkt).mean():+10.2f}')
