# -*- coding: utf-8 -*-
"""t26_mass_rest.py — Τ3: ΜΑΖΙΚΗ ΞΕΚΟΥΡΑΣΗ / ΠΟΛΛΕΣ ΑΠΟΥΣΙΕΣ (21/10/2026). Αφορμη: BOS–WAS 14/4/2024 (6 βασικοι «Rest»): μοντελο αφαιρεσε ~13 π.
και εμενε BOS +14, πραγματικο +10 → ο αντικαταστατης −2 ισως πολυ γενναιοδωρος οταν λειπουν πολλοι μαζι (παιζουν παικτες G-League).
ΜΗΧΑΝΗ = t22 (αντιγραφο live χωρις «εχασε 2», απουσιες απο την τελευταια επισημη αναφορα ≤ τ, μονο Out). ΟΛΗ η σεζον (ολοι οι μηνες).
ΠΑΡΑΛΛΑΓΗ: απουσιες ομαδας ταξινομημενες κατα λεπτα· ο 1ος και 2ος με αντικαταστατη −2 (οπως σημερα), ο 3ος και μετα με ΑΝΤΙΚ ∈ {−2, −3, −4, −5}.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (πριν το τρεξιμο): LOSO — ΑΝΤΙΚ επιλεγεται με RMSE (στιγμη Τ−30′) στις αλλες 4 σεζον· ΠΕΡΝΑ αν
  (α) RMSE σε ματς με ≥3 απουσιες καλυτερο απο το −2 σε ≥4/5 σεζον, (β) RMSE ολων οχι χειροτερο σε ≥4/5,
  (γ) ROI picks ≥8% στο ανοιγμα (αγωνες ≤70, οπως live) οχι χειροτερο απο το −2 κατα >1.5pp, και ουτε στο Τ−30′.
Εξοδος: t26_mass_rest_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0]
src = src.replace("if os.environ.get('T22_AUDIT'):", "if False:")
g22 = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g22)
sys.stdout.reconfigure(encoding='utf-8')
for k in ('np', 'pd', 'G', 'SEAS_G', 'dD', 'EV', 'ACT', 'VNO', 'SER', 'SHIFT', 'cover_', 'SIG_', 'REP_SEASONS', 'status_at', 'K2P', 'mins', 'value', 'line_at'):
    globals()[k] = g22[k]
import pickle
GN = np.asarray(pickle.load(open(os.path.join(os.path.dirname(SC), 'nba_diag_data.pkl'), 'rb'))['GN'])
REPS = (-2.0, -3.0, -4.0, -5.0)
def parts(t, d, s, tau):
    """λιστα (λεπτα, αξια) των Out παικτων ρολου (≥20′, επαιξαν φετος) στο τ"""
    L = []
    for k, stt in status_at(t, d, tau).items():
        if stt != 'Out': continue
        pid = K2P.get((k, t, s))
        if pid is None: continue
        m = mins(pid, t, s, d)
        if m is None or m < 20: continue
        L.append((m, value(pid, s - 1)))
    return sorted(L, reverse=True)
def cost(L, rep3):
    return sum(0.75 * (v - (-2.0 if j < 2 else rep3)) * m / 48 for j, (m, v) in enumerate(L))
recs = []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]): continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    h, a, d = G.home.values[i], G.away.values[i], dD[i]
    for lab, tau in (('ανοιγμα', rows[0][0]), ('Τ−30′', tip - 1800)):
        if tau < rows[0][0]: tau = rows[0][0]
        ln = line_at(rows, tau, sw)
        if not ln: continue
        L, oh, oa, fair, _ = ln
        Ph, Pa = parts(h, d, s, tau), parts(a, d, s, tau)
        for rep in REPS:
            m = VNO[i] - cost(Ph, rep) + cost(Pa, rep)
            pw, pp, pl = cover_(m, L, SIG_); e1, e2 = pw * oh + pp - 1, pl * oa + pp - 1
            sd, e, od_ = (1, e1, oh) if e1 >= e2 else (-1, e2, oa)
            res = None
            if e >= .08:
                x = (ACT[i] + L) * sd; res = (od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0)
            recs.append(dict(i=i, sea=s, tau=lab, rep=rep, err=ACT[i] - m, many=max(len(Ph), len(Pa)) >= 3, res=res, gn=int(GN[i])))
X = pd.DataFrame(recs)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
rm = lambda d: float(np.sqrt((d.err ** 2).mean()))
P('NBA · Τ3 ΜΑΖΙΚΕΣ ΑΠΟΥΣΙΕΣ: αντικαταστατης για τον 3ο+ απωντα · ολη η σεζον · απουσιες απο επισημες αναφορες (μονο Out)')
for lab in ('Τ−30′', 'ανοιγμα'):
    P(''); P(f'=== {lab} ===')
    D_ = X[X.tau == lab]
    P(f'  ματς με ≥3 απουσιες (σε μια ομαδα): {int(D_[(D_.rep == -2) & D_.many].shape[0])} / {int(D_[D_.rep == -2].shape[0])}')
    for rep in REPS:
        d = D_[D_.rep == rep]; dm = d[d.many]; pk = d[d.res.notna() & (d.gn <= 70)]
        ps = pk.groupby('sea').res.sum()
        P(f'  ΑΝΤΙΚ 3ου+ {rep:+.0f}: RMSE ολα {rm(d):.4f} · ≥3 απουσιες {rm(dm):.3f} (μεση λαθος {dm.err.mean():+.2f}) · '
          f'ROI ≤70 {100 * pk.res.mean():+5.1f}% ({len(pk)}, {int((ps > 0).sum())}/5)')
    P('  ανα σεζον RMSE ≥3 απουσιες: ' + ' · '.join(f'{rep:+.0f}: ' + '/'.join(f'{rm(D_[(D_.rep == rep) & D_.many & (D_.sea == y)]):.2f}' for y in sorted(D_.sea.unique())) for rep in REPS))
# LOSO
P(''); P('=== LOSO (επιλογη με RMSE ολων στο Τ−30′ στις αλλες 4) ===')
D_ = X[X.tau == 'Τ−30′']; win_m = win_a = 0; ch = []
for y in sorted(D_.sea.unique()):
    tr = D_[D_.sea != y]; best = min(REPS, key=lambda r: rm(tr[tr.rep == r])); ch.append(best)
    te = D_[D_.sea == y]; b0 = te[te.rep == -2]; b1 = te[te.rep == best]
    wm = rm(b1[b1.many]) < rm(b0[b0.many]); wa = rm(b1) <= rm(b0); win_m += wm; win_a += wa
    P(f'  {y}: επιλογη {best:+.0f} · RMSE ≥3 απουσιες {rm(b0[b0.many]):.3f} → {rm(b1[b1.many]):.3f} · ολα {rm(b0):.4f} → {rm(b1):.4f}')
P(f'  επιλογες {ch} · ≥3 απουσιες καλυτερο {win_m}/5 · ολα οχι χειροτερο {win_a}/5')
open(os.path.join(SC, 't26_mass_rest_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
