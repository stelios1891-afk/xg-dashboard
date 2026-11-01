# -*- coding: utf-8 -*-
"""t84_b2b_rest_expected.py — ΞΕΚΟΥΡΑΣΗ ΣΤΟ 2ο ΜΑΤΣ BACK-TO-BACK (25/10/2026, Στελιος «ναι» στον ορισμο).
Αφορμη t83: απο το 2024-25 η ειδηση ξεκουρασης στο 2ο ματς B2B κουναει τη γραμμη μονο 12-13% της αξιας (η αγορα την εχει απο πριν).
ΠΛΑΙΣΙΟ = t22 (ιδια στιγμη τιμη + αναφορα, αντιγραφο live, πιθανοτητες καταστασης Out 1 · D .97 · Q .45 · P .07 = ΟΠΩΣ ΤΟ LIVE).
ΣΤΙΓΜΕΣ: ανοιγμα · Τ−6ω · Τ−2ω. Picks edge ≥8% στην τιμη της στιγμης, CLV = κινηση ως το κλεισιμο προς εμας.
«ΞΕΚΟΥΡΑΣΗ» = λογος στην αναφορα «Rest» Ή «Injury Management / Maintenance» (απο το 2023-24 η πολιτικη συμμετοχης του NBA γραφει ετσι
  την ξεκουραση — 4.433 «Rest», ~4.000 «Injury Management»).
ΕΚΔΟΧΕΣ (αφορουν ΜΟΝΟ ομαδα σε 2ο ματς B2B):
  Α (σημερα): ολες οι απουσιες μετρανε πληρως μολις δηλωθουν.
  Β «μιση ξεκουραση»: απουσια-ξεκουραση μετραει w ∈ {0, .25, .5} της αξιας (w με LOSO, μοναδες ολων των στιγμων στις αλλες σεζον).
  Γ «αναμενομενη ξεκουραση»: πριν δηλωσει η ομαδα (καμια γραμμη αναφορας ως τη στιγμη) → για καθε παικτη ρολου (≥20′) που επαιξε ΧΘΕΣ:
     −p·αξια, p = ποσοστο που ξεκουραστηκε σε προηγουμενα 2α ματς B2B (φετος+περσι, μονο ΠΡΙΝ το ματς), συρρικνωση προς τον μεσο
     της λιγκας με 4 ψευτο-ματς. Μολις δηλωσει η ομαδα → πραγματικες καταστασεις (οπως Α).
ΚΡΙΤΗΡΙΑ (εγκριθηκαν πριν): Β ή Γ ΠΕΡΝΑ αν vs Α: ROI ΚΑΙ CLV οχι χειροτερα στο συνολο · ROI καλυτερο στις 2025+2026 μαζι ·
  οχι χειροτερη σε ≥4/5 σεζον (μοναδες) · σφαλμα προβλεψης (ματς με ομαδα σε 2ο B2B) καλυτερο σε ≥3/5 σεζον.
Εξοδος: nba_tests/t84_b2b_rest_expected_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
_src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(_src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd, G, SEAS_G, dD, EV, ACT = g['np'], g['pd'], g['G'], g['SEAS_G'], g['dD'], g['EV'], g['ACT']
VNO, SER, SHIFT, cover_, SIG_, value = g['VNO'], g['SER'], g['SHIFT'], g['cover_'], g['SIG_'], g['value']
K2P, mins, HM, line_at, R, W_B = g['K2P'], g['mins'], g['HM'], g['line_at'], g['R'], g['W_B']
REP_SEASONS = g['REP_SEASONS']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))

# ---- αναφορες με λογο ----
R = R.copy(); R['rest'] = R.reason.fillna('').str.contains(r'rest|management|maintenance', case=False, regex=True)
REPR = collections.defaultdict(list)                       # (ομαδα, ημερα) → [(ep, key, status, rest)]
for r in R.itertuples(index=False): REPR[(r.team, r.gd)].append((r.ep, r.key, r.status, bool(r.rest)))
for k in REPR: REPR[k].sort()
def status_at(t, d, tau):
    st = {}
    for back in (3, 2, 1, 0):
        for ep, k, s, rs in REPR.get((t, d - np.timedelta64(back, 'D')), ()):
            if ep <= tau: st[k] = (s, rs)
    return st
def submitted(t, d, tau):
    return any(ep <= tau for ep, *_ in REPR.get((t, d), ()))
# ---- ημερες ματς ανα ομαδα → 2ο ματς B2B ----
PLAYED = set()
for i in range(len(G)): PLAYED.add((G.home.values[i], dD[i])); PLAYED.add((G.away.values[i], dD[i]))
b2b = lambda t, d: (t, d - np.timedelta64(1, 'D')) in PLAYED
# λεπτα ανα (pid, ομαδα, ημερα)
MIND = {}
for (pid, t, s), L in HM.items():
    for dd_, m in L: MIND[(pid, t, dd_)] = m
# ---- ιστορικο ξεκουρασης σε 2α ματς B2B: για καθε (ομαδα, ημερα) 2ου B2B → παικτες ρολου που επαιξαν χθες + αν ξεκουραστηκαν ----
P2K = {}                                                   # (pid) → key για την ομαδα/σεζον
for (k, t, s), pid in K2P.items(): P2K[(pid, t, s)] = k
TS = collections.defaultdict(list)
for (pid, t, s), k in P2K.items(): TS[(t, s)].append((pid, k))
B2EV = collections.defaultdict(list)                       # pid → [(ημερα, ξεκουραστηκε 0/1)]
for i in np.argsort(dD, kind='stable'):
    d, s = dD[i], int(SEAS_G[i])
    if s not in REP_SEASONS: continue
    for t in (G.home.values[i], G.away.values[i]):
        if not b2b(t, d): continue
        rep = {}
        for ep, k, st, rs in REPR.get((t, d), ()): rep[k] = (st, rs)        # τελευταια κατασταση της ημερας
        for pid, k in TS[(t, s)]:
            if MIND.get((pid, t, d - np.timedelta64(1, 'D')), 0) < 20: continue
            st = rep.get(k); B2EV[pid].append((d, 1 if (st and st[0] == 'Out' and st[1]) else 0))
allv = [x for L in B2EV.values() for _, x in L]; P0 = float(np.mean(allv)) if allv else 0.05; A_SH = 4.0
P(f'ιστορικο 2ων ματς B2B: {len(allv)} παικτης-ματς (ρολος, επαιξε χθες) · ξεκουραστηκε {100 * P0:.1f}% (μεσος λιγκας)')
def p_rest(pid, d, s):
    L = [x for dd_, x in B2EV.get(pid, ()) if dd_ < d and int(str(dd_)[:4]) + (1 if int(str(dd_)[5:7]) >= 7 else 0) >= s - 1]
    return (sum(L) + A_SH * P0) / (len(L) + A_SH), len(L)
def cost(t, d, s, tau, ver, w=1.0, det=None):
    st = status_at(t, d, tau); is_b2 = b2b(t, d)
    if ver == 'Γ' and is_b2 and not submitted(t, d, tau):
        c = 0.0
        for pid, k in TS[(t, s)]:
            if MIND.get((pid, t, d - np.timedelta64(1, 'D')), 0) < 20: continue
            m = mins(pid, t, s, d)
            if m is None or m < 20: continue
            p, n = p_rest(pid, d, s); cc = p * 0.75 * (value(pid, s - 1) + 2.0) * m / 48; c += cc
            if det is not None and p > P0 * 1.5: det.append((k, round(p, 2), n, round(cc, 2)))
        # οτι υπαρχει ηδη στην αναφορα για αλλους λογους (π.χ. τραυματισμος απο μερες) μετραει κανονικα
        for k, (stt, rs) in st.items():
            ww = W_B.get(stt)
            if not ww or rs: continue
            pid = K2P.get((k, t, s)); m = mins(pid, t, s, d) if pid is not None else None
            if m is None or m < 20 or MIND.get((pid, t, d - np.timedelta64(1, 'D')), 0) >= 20: continue
            c += ww * 0.75 * (value(pid, s - 1) + 2.0) * m / 48
        return c
    c = 0.0
    for k, (stt, rs) in st.items():
        ww = W_B.get(stt)
        if not ww: continue
        pid = K2P.get((k, t, s))
        if pid is None: continue
        m = mins(pid, t, s, d)
        if m is None or m < 20: continue
        if ver == 'Β' and is_b2 and rs: ww *= w
        c += ww * 0.75 * (value(pid, s - 1) + 2.0) * m / 48
    return c
TAUS = (('ανοιγμα', None), ('Τ−6ω', 6), ('Τ−2ω', 2))
VERS = [('Α', 1.0), ('Β0', 0.0), ('Β25', .25), ('Β50', .5), ('Γ', 1.0)]
recs, errs = [], []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]): continue
    h, a, d = G.home.values[i], G.away.values[i], dD[i]
    aff = b2b(h, d) or b2b(a, d)
    if not aff: continue                                  # μονο ματς με ομαδα σε 2ο B2B (τα υπολοιπα ιδια σε ολες τις εκδοχες)
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    close = line_at(rows, tip, sw)
    for lab, hrs in TAUS:
        tau = rows[0][0] if hrs is None else tip - hrs * 3600
        if hrs is not None and tau < rows[0][0]: continue
        ln = line_at(rows, tau, sw)
        if not ln: continue
        L, oh, oa, fair, _ = ln
        for vname, w in VERS:
            ver = vname[0]
            m = VNO[i] - cost(h, d, s, tau, ver, w) + cost(a, d, s, tau, ver, w)
            errs.append(dict(sea=s, tau=lab, v=vname, se=(ACT[i] - m) ** 2))
            pw, pp, pl = cover_(m, L, SIG_); e1, e2 = pw * oh + pp - 1, pl * oa + pp - 1
            sd, e, od_ = (1, e1, oh) if e1 >= e2 else (-1, e2, oa)
            if e < .08: continue
            x = (ACT[i] + L) * sd; res = (od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0)
            recs.append(dict(i=i, sea=s, tau=lab, v=vname, sd=sd, res=res, clv=sd * (close[3] - fair)))
X = pd.DataFrame(recs); E = pd.DataFrame(errs)
# LOSO επιλογη w για Β
SEAS = sorted(X.sea.unique())
selw = {Y: max(('Β0', 'Β25', 'Β50'), key=lambda v: X[(X.v == v) & (X.sea != Y)].res.sum()) for Y in SEAS}
XB = pd.concat([X[(X.v == selw[Y]) & (X.sea == Y)] for Y in SEAS]).assign(v='Β'); X = pd.concat([X, XB])
EB = pd.concat([E[(E.v == selw[Y]) & (E.sea == Y)] for Y in SEAS]).assign(v='Β'); E = pd.concat([E, EB])
def cell(d):
    if not len(d): return '—'
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+6.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, θετ {int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f}π'
P(f'ματς με ομαδα σε 2ο B2B · σεζον {SEAS} · LOSO w (Β): ' + ' · '.join(f'{Y % 100}:{selw[Y][1:]}%' for Y in SEAS))
for lab, _ in TAUS:
    P(f'\n=== {lab} ===')
    for v in ('Α', 'Β', 'Γ', 'Β0', 'Β25', 'Β50'):
        d = X[(X.tau == lab) & (X.v == v)]; d2 = d[d.sea >= 2025]
        rm = ' '.join(f'{Y % 100}:{np.sqrt(E[(E.tau == lab) & (E.v == v) & (E.sea == Y)].se.mean()):.3f}' for Y in SEAS)
        P(f'  {v:4s} {cell(d)} · 2025+26: {cell(d2)} · σφαλμα {rm}')
P('\n=== ΚΡΙΤΗΡΙΑ (ολες οι στιγμες μαζι) ===')
A_ = X[X.v == 'Α']; ua = A_.groupby('sea').res.sum()
ea = {Y: np.sqrt(E[(E.v == 'Α') & (E.sea == Y)].se.mean()) for Y in SEAS}
for v in ('Β', 'Γ'):
    V = X[X.v == v]; uv = V.groupby('sea').res.sum()
    ev = {Y: np.sqrt(E[(E.v == v) & (E.sea == Y)].se.mean()) for Y in SEAS}
    c1 = V.res.mean() >= A_.res.mean() and V.clv.mean() >= A_.clv.mean()
    c2 = V[V.sea >= 2025].res.mean() > A_[A_.sea >= 2025].res.mean()
    c3 = sum(uv.get(Y, 0) >= ua.get(Y, 0) - 1e-9 for Y in SEAS)
    c4 = sum(ev[Y] < ea[Y] - 1e-6 for Y in SEAS)
    P(f'  {v}: ROI {100 * V.res.mean():+.1f}% vs Α {100 * A_.res.mean():+.1f}% · CLV {V.clv.mean():+.2f} vs {A_.clv.mean():+.2f} → {"✓" if c1 else "✗"} · '
      f'2025+26 ROI {100 * V[V.sea >= 2025].res.mean():+.1f}% vs {100 * A_[A_.sea >= 2025].res.mean():+.1f}% → {"✓" if c2 else "✗"} · '
      f'σεζον οχι χειροτερη {c3}/5 → {"✓" if c3 >= 4 else "✗"} · σφαλμα καλυτερο {c4}/5 → {"✓" if c4 >= 3 else "✗"} → '
      f'{"ΠΕΡΝΑΕΙ" if c1 and c2 and c3 >= 4 and c4 >= 3 else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
# ---- αλλαγες picks (ανοιγμα) Γ vs Α ----
for lab, _ in TAUS:
    a = X[(X.tau == lab) & (X.v == 'Α')].set_index(['i', 'sd']); c = X[(X.tau == lab) & (X.v == 'Γ')].set_index(['i', 'sd'])
    gone, new = a[~a.index.isin(c.index)], c[~c.index.isin(a.index)]
    P(f'  {lab}: Γ κοβει {len(gone)} picks του Α ({cell(gone.reset_index())}) · προσθετει {len(new)} ({cell(new.reset_index())})')
# ---- ελεγχος: 2 παραδειγματα 2025-26 με μεγαλη αναμενομενη ξεκουραση ----
P('\n=== ΕΛΕΓΧΟΣ: παραδειγματα αναμενομενης ξεκουρασης (Γ, στο ανοιγμα) ===')
shown = 0
for i, (sw, tip, r21, _) in SER.items():
    if shown >= 3 or int(SEAS_G[i]) != 2026: continue
    h, a, d, s = G.home.values[i], G.away.values[i], dD[i], 2026
    for t in (h, a):
        if not b2b(t, d): continue
        rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]
        if not rows: continue
        det = []; c = cost(t, d, s, rows[0][0], 'Γ', 1.0, det)
        if c < 1.0 or not det: continue
        fin = {k: v for k, v in status_at(t, d, tip).items()}
        P(f'  {a}@{h} {str(d)[:10]} · {t} σε 2ο B2B · αναμενομενη ξεκουραση στο ανοιγμα {c:.2f} π. · ' +
          ' · '.join(f'{k} p={p} (απο {n} ματς) −{cc}' for k, p, n, cc in det) + ' · τελικα: ' +
          ', '.join(f'{k}={fin.get(k, ("παιζει",))[0]}' for k, *_ in det))
        shown += 1
open(os.path.join(SC, 't84_b2b_rest_expected_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
