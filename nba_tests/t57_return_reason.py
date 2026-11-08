# -*- coding: utf-8 -*-
"""t57_return_reason.py — ΕΚΠΤΩΣΗ ΕΠΙΣΤΡΟΦΗΣ ΑΝΑ ΛΟΓΟ ΑΠΟΥΣΙΑΣ + ΟΜΑΔΑ ΕΛΕΓΧΟΥ (22/10/2026, Στελιος «απο ξεκουραση δεν θα επρεπε
να επιστρεφει ετοιμος; απο τραυματισμο εχει λογικη — αξιζει διαχωρισμος;»).
Ιδιος ορισμος επιστρεφοντα και ιδια βαση (σημερινο live, πιθανοτητες αναφορας) με το t56.
ΛΟΓΟΣ = ο λογος της επισημης αναφορας για τον παικτη στα ματς που ελειψε: ξεκουραση (Rest / Injury Management) · τραυματισμος (Injury/Illness)
  · χωρις αναφορα (δεν ηταν ποτε στην αναφορα — μονο απουσια 1 ματς, οπως στο t56) · αλλο (προσωπικοι λογοι, τιμωρια κλπ).
ΟΜΑΔΑ ΕΛΕΓΧΟΥ: οι ιδιοι παικτες στο 2ο-4ο ματς μετα την επιστροφη (επαιξαν στο προηγουμενο, αλλα ελειψαν σε ενα απο τα 4 πριν).
  Αν η «εκπτωση» εμφανιζεται και εκει → ειναι ειδος παικτη (υπερτιμημενη αξια), οχι «σκουρια» του 1ου ματς.
Μετρηση: κοινη παλινδρομηση (πραγμ − μοντελο) = a + Σ δ_ομαδας · RET_ομαδας, ολες οι σεζον και ανα σεζον · ιδια και για (πραγμ − αγορα).
Περιγραφικο (οχι κανονας). Εξοδος: t57_return_reason_out.txt"""
import os, sys, collections
SC = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(SC, 't56_return_discount.py'), encoding='utf-8').read().split("rows = []; miss = 0\n")[0]
g = {'__file__': os.path.join(SC, 't56_return_discount.py'), '__name__': 'x'}
exec(src, g)
np, pd, X, G, SER, dD, ACT = g['np'], g['pd'], g['X'], g['G'], g['SER'], g['dD'], g['ACT']
TG, APP, ROST, OTHER, KEY, REP_BY = g['TG'], g['APP'], g['ROST'], g['OTHER'], g['KEY'], g['REP_BY']
mins, value, status_at, p_out, abs_P, opening_ts, GI = g['mins'], g['value'], g['status_at'], g['p_out'], g['abs_P'], g['opening_ts'], g['GI']
RR = g['g']['R']
REAS = {}
for r in RR.sort_values('ep').itertuples(index=False): REAS[(r.team, r.gd, r.key)] = str(r.reason)
def cat(reasons):
    if not reasons: return 'χωρις αναφορα'
    t = ' '.join(reasons).lower()
    if 'rest' in t or 'management' in t: return 'ξεκουραση'
    if 'injury' in t or 'illness' in t: return 'τραυματισμος'
    return 'αλλο'
GROUPS = ('ξεκουραση', 'τραυματισμος', 'χωρις αναφορα', 'αλλο', 'ελεγχος 2ο-4ο')
CNT = collections.Counter()
def players(t, s, d, tau):
    games = [x for x in TG[(t, s)] if x < d]
    out = collections.defaultdict(float)
    if not games: return out
    prev = games[-1]; st = status_at(t, d, tau)
    for pid in ROST[(t, s)]:
        ap = [x for x in APP[(pid, t, s)] if x < d]
        if not ap: continue
        m = mins(pid, t, s, d)
        if m is None or m < 20: continue
        stt = st.get(KEY.get(pid))
        if stt == 'Out': continue
        w = 1.0 - p_out(stt, m)
        if w <= 0: continue
        c = 0.75 * (value(pid, s - 1) + 2.0) * m / 48 * w
        if ap[-1] < prev:                                           # 1ο ματς επιστροφης (ιδιος ορισμος με t56)
            if any(ap[-1] < x < d for x in OTHER.get((pid, t, s), ())): continue
            missed = [x for x in games if x > ap[-1]]
            reasons = [REAS[(t, x, KEY.get(pid))] for x in missed if (t, x, KEY.get(pid)) in REAS]
            if len(missed) >= 2 and not any(kk == KEY.get(pid) for x in missed for ep, kk, _ in REP_BY.get((t, x), ())): continue
            gr = cat(reasons); CNT[(gr, ' | '.join(sorted(set(reasons)))[:60])] += 1
        else:                                                       # επαιξε στο προηγουμενο: ομαδα ελεγχου αν ελειψε σε ενα απο τα 4 πριν
            last4 = games[-5:-1]
            if not last4 or all(x in set(ap) for x in last4): continue
            gr = 'ελεγχος 2ο-4ο'
        out[gr] += c
    return out
rows = []
for r in X.itertuples(index=False):
    i = GI.get((str(r.date)[:10], r.home))
    if i is None or i not in SER: continue
    tau = opening_ts(i)
    if tau is None or abs(ACT[i] - r.act) > 0.5: continue
    d = dD[i]; s = int(r.sea)
    ph, pa = players(r.home, s, d, tau), players(r.away, s, d, tau)
    rec = dict(sea=s, m=r.m0 - abs_P(r.home, d, s, tau) + abs_P(r.away, d, s, tau), fair=r.fair, act=r.act)
    for gr in GROUPS: rec[gr] = pa.get(gr, 0.0) - ph.get(gr, 0.0)
    rows.append(rec)
D = pd.DataFrame(rows); SE = sorted(D.sea.unique())
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def reg(x, ycol):
    Xm = np.c_[np.ones(len(x)), x[list(GROUPS)].values]; y = (x.act - x[ycol]).values
    b, *_ = np.linalg.lstsq(Xm, y, rcond=None); r = y - Xm @ b
    cov = np.sum(r ** 2) / (len(y) - Xm.shape[1]) * np.linalg.inv(Xm.T @ Xm); return b[1:], np.sqrt(np.diag(cov))[1:]
P(f'ματς {len(D)} · ΒΑΣΗ σημερινο live (πιθανοτητες αναφορας)')
P('επιστροφες ανα ομαδα (ματς-παικτες) · συχνοτεροι λογοι:')
tot = collections.Counter()
for (gr, _), n in CNT.items(): tot[gr] += n
for gr in GROUPS[:4]:
    top = sorted(((n, rs) for (g_, rs), n in CNT.items() if g_ == gr), reverse=True)[:3]
    P(f'  {gr:14s} {tot[gr]:5d} · ' + ' · '.join(f'«{rs or "—"}» {n}' for n, rs in top))
P(f'  ελεγχος 2ο-4ο: ματς με τιμη ≠0 {int((D["ελεγχος 2ο-4ο"] != 0).sum())}')
P('')
P('δ = ποσοστο της αξιας που ΔΕΝ αποδιδει (0 = μοντελο σωστο · 1 = δεν αποδιδει τιποτα) — κοινη παλινδρομηση:')
for ycol, lab in (('m', 'ΜΟΝΤΕΛΟ'), ('fair', 'ΑΓΟΡΑ')):
    b, se = reg(D, ycol)
    P(f'  {lab:8s} ' + ' · '.join(f'{gr} {bb:+.2f}±{ss:.2f}' for gr, bb, ss in zip(GROUPS, b, se)))
P('  ανα σεζον (μοντελο):')
for s in SE:
    b, se = reg(D[D.sea == s], 'm'); P(f'    {s % 100}: ' + ' · '.join(f'{gr} {bb:+.2f}' for gr, bb in zip(GROUPS, b)))
open(os.path.join(SC, 't57_return_reason_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
