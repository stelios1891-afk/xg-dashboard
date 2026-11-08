# -*- coding: utf-8 -*-
"""t35_totals_build.py — ΣΥΝΟΛΑ NBA · ΒΑΣΗ (21/10/2026, Στελιος «οτι θες κανε με τα συνολα, μεχρι να βρουμε μια κερδοφορα μηχανη»).
ΟΛΑ τα ματς κανονικης (5 σεζον με επισημες αναφορες) σε 3 στιγμες (ανοιγμα Crown · Τ−2ω · Τ−30′):
  μοντελο = αντιγραφο live: μηχανη συνολων CFG_T (0.7, 8, 60, .5, 5, 0,0,0) + Φ3 live (μεσο πραγμ − μοντελο, 150 τελευταια ματς ΤΗΣ σεζον, ≥30 αλλιως 0)
  + απουσιες: C_O·LO + C_D·LD (−0.5 / +1.0), LO/LD = Σ (επιθ/αμυνα − (−0.5))·λεπτα/48 των αποντων ρολου (≥20′, επαιξαν φετος)
    απο την ΤΕΛΕΥΤΑΙΑ επισημη αναφορα ≤ τ — και «μονο Out» (live) και «πιθανοτητες ανα ρολο» (t34).
  γραμμη συνολου Crown στο τ (over/under τιμες) · δικαιο συνολο στο τ και στο κλεισιμο · πραγματικο συνολο · κατοχες (pace) αν υπαρχει.
Εξοδος: nba_tests/_t35_totals.csv"""
import os, sys, io, contextlib, pickle
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g['np'], __import__('pandas'); nt = g['nt']
G, SEAS_G, dD, EV, SER, SHIFT = g['G'], g['SEAS_G'], g['dD'], g['EV'], g['SER'], g['SHIFT']
status_at, K2P, mins, REP_SEASONS = g['status_at'], g['K2P'], g['mins'], g['REP_SEASONS']
TT = np.asarray(nt['TT'], float); LEV = np.nan_to_num(np.asarray(nt['Llive'], float)); TOT = np.asarray(nt['TOT'], float)
odval, mk_t, SIGT = nt['odval'], nt['mk_t'], nt['SIGT']
GN = np.asarray(pickle.load(open(os.path.join(ROOT, 'nba_diag_data.pkl'), 'rb'))['GN'])
PACE = G.pace.values if 'pace' in G else np.full(len(G), np.nan)
PR = {'star': {'Out': 1.0, 'Doubtful': .965, 'Questionable': .42, 'Probable': .04}, 'starter': {'Out': 1.0, 'Doubtful': .963, 'Questionable': .46, 'Probable': .07}}
def od_loss(t, d, s, tau):
    lo = ld = lop = ldp = 0.0; n = 0
    for k, stt in status_at(t, d, tau).items():
        pid = K2P.get((k, t, s))
        if pid is None: continue
        m = mins(pid, t, s, d)
        if m is None or m < 20: continue
        o_, d_ = odval(pid, s - 1); xo = (o_ + 0.5) * m / 48; xd = (d_ + 0.5) * m / 48
        if stt == 'Out': lo += xo; ld += xd; n += 1
        w = PR['star' if m >= 30 else 'starter'].get(stt, 0.0); lop += w * xo; ldp += w * xd
    return lo, ld, lop, ldp, n
rows = []
for i, (sw, tip, r21, r23) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(TT[i]) or not r23: continue
    rr = [[x[0] + SHIFT] + list(x[1:]) for x in r23]; rr = [x for x in rr if x[0] <= tip + 900]
    if not rr: continue
    h, a, d = G.home.values[i], G.away.values[i], dD[i]; cl = rr[-1]
    for lab, hrs in (('ανοιγμα', None), ('Τ−2ω', 2), ('Τ−30′', 0.5)):
        tau = rr[0][0] if hrs is None else tip - hrs * 3600
        if hrs is not None and tau < rr[0][0]: continue
        pre = [x for x in rr if x[0] <= tau]
        if not pre: continue
        x = pre[-1]
        loh, ldh, loph, ldph, nh = od_loss(h, d, s, tau); loa, lda, lopa, ldpa, na = od_loss(a, d, s, tau)
        rows.append(dict(i=i, sea=s, date=str(d), mon=int(G.date.dt.month.values[i]), gn=int(GN[i]), tau=lab, hrs=(tip - tau) / 3600, home=h, away=a,
                         tt=TT[i], lev=LEV[i], lo=loh + loa, ld=ldh + lda, lop=loph + lopa, ldp=ldph + ldpa, nout=nh + na,
                         T=float(x[1]), oo=1 + x[2], ou=1 + x[3], fair=mk_t(x), cfair=mk_t(cl), cT=float(cl[1]), tot=TOT[i], pace=PACE[i]))
X = pd.DataFrame(rows); X.to_csv(os.path.join(SC, '_t35_totals.csv'), index=False)
print('γραμμες', len(X), '· ματς', X.i.nunique(), '· σ', round(SIGT, 2))
