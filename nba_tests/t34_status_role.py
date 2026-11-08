# -*- coding: utf-8 -*-
"""t34_status_role.py — ΠΙΘΑΝΟΤΗΤΕΣ ΑΠΟΥΣΙΑΣ: ΙΔΙΕΣ ΓΙΑ ΟΛΟΥΣ ή ΑΝΑ ΡΟΛΟ (21/10/2026, Στελιος «οκ ξεκινα το»).
Μηχανη = t22 (αντιγραφο live χωρις «εχασε 2», τελευταια επισημη αναφορα ≤ τ, τιμη Crown στο τ). Απουσιες: παικτες ρολου (≥20′, επαιξαν φετος).
  Α «μονο Out» (σημερα) · Β «ιδιες»: D .97 · Q .45 · P .07 · Γ «ανα ρολο» (t21, Τ−6ω): σταρ ≥30′ D .965 Q .42 P .04 · βασικος 20-30′ D .963 Q .46 P .07.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (πριν το τρεξιμο): το Γ αντικαθιστα το Β αν στο ΑΝΟΙΓΜΑ εχει ROI υψηλοτερο ΚΑΙ μοναδες ≥ Β σε ≥4/5 σεζον ΚΑΙ RMSE οχι χειροτερο.
  (Περιγραφικα ολες οι στιγμες.) Εξοδος: t34_status_role_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g['np'], __import__('pandas')
G, SEAS_G, dD, EV, ACT, VNO, SER, SHIFT = (g[k] for k in ('G', 'SEAS_G', 'dD', 'EV', 'ACT', 'VNO', 'SER', 'SHIFT'))
status_at, K2P, mins, value, line_at, cover_, SIG_, REP_SEASONS = (g[k] for k in ('status_at', 'K2P', 'mins', 'value', 'line_at', 'cover_', 'SIG_', 'REP_SEASONS'))
W = {'Α': lambda st, m: 1.0 if st == 'Out' else 0.0,
     'Β': lambda st, m: {'Out': 1.0, 'Doubtful': .97, 'Questionable': .45, 'Probable': .07}.get(st, 0.0),
     'Γ': lambda st, m: {'Out': 1.0, 'Doubtful': .965 if m >= 30 else .963, 'Questionable': .42 if m >= 30 else .46, 'Probable': .04 if m >= 30 else .07}.get(st, 0.0)}
def cost(t, d, s, tau, wf):
    c = 0.0
    for k, stt in status_at(t, d, tau).items():
        pid = K2P.get((k, t, s))
        if pid is None: continue
        m = mins(pid, t, s, d)
        if m is None or m < 20: continue
        w = wf(stt, m)
        if w: c += w * 0.75 * (value(pid, s - 1) + 2.0) * m / 48
    return c
TAUS = (('ανοιγμα', None), ('Τ−12ω', 12), ('Τ−6ω', 6), ('Τ−2ω', 2), ('Τ−30′', 0.5))
recs, errs = [], []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]): continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    close = line_at(rows, tip, sw); h, a, d = G.home.values[i], G.away.values[i], dD[i]
    for lab, hrs in TAUS:
        tau = rows[0][0] if hrs is None else tip - hrs * 3600
        if hrs is not None and tau < rows[0][0]: continue
        ln = line_at(rows, tau, sw)
        if not ln: continue
        L, oh, oa, fair, _ = ln
        for v, wf in W.items():
            m = VNO[i] - cost(h, d, s, tau, wf) + cost(a, d, s, tau, wf)
            errs.append((lab, v, s, ACT[i] - m))
            pw, pp, pl = cover_(m, L, SIG_); e1, e2 = pw * oh + pp - 1, pl * oa + pp - 1
            sd, e, od_ = (1, e1, oh) if e1 >= e2 else (-1, e2, oa)
            if e < .08: continue
            x = (ACT[i] + L) * sd; res = (od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0)
            recs.append(dict(i=i, sea=s, tau=lab, v=v, res=res, clv=sd * (close[3] - fair)))
X = pd.DataFrame(recs); E_ = pd.DataFrame(errs, columns=['tau', 'v', 'sea', 'err'])
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d):
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+5.1f}% ({len(d):4d}, {d.res.sum():+6.1f}μ, {int((ps > 0).sum())}/5) CLV {d.clv.mean():+.2f}'
P('NBA · ΠΙΘΑΝΟΤΗΤΕΣ ΑΠΟΥΣΙΑΣ: Α μονο Out · Β ιδιες (D .97 Q .45 P .07) · Γ ανα ρολο (σταρ ≥30′ / βασικος 20-30′)')
for lab, _ in TAUS:
    P(f'  {lab:8s} ' + ' | '.join(f'{v}: {cell(X[(X.tau == lab) & (X.v == v)])} RMSE {np.sqrt((E_[(E_.tau == lab) & (E_.v == v)].err ** 2).mean()):.4f}' for v in W))
o = X[X.tau == 'ανοιγμα']
ub = o[o.v == 'Β'].groupby('sea').res.sum(); ug = o[o.v == 'Γ'].groupby('sea').res.sum()
rb = np.sqrt((E_[(E_.tau == 'ανοιγμα') & (E_.v == 'Β')].err ** 2).mean()); rg = np.sqrt((E_[(E_.tau == 'ανοιγμα') & (E_.v == 'Γ')].err ** 2).mean())
ok = o[o.v == 'Γ'].res.mean() > o[o.v == 'Β'].res.mean() and int((ug.reindex(ub.index, fill_value=0) >= ub).sum()) >= 4 and rg <= rb + 1e-6
P(f'  ανοιγμα ανα σεζον μοναδες Β: {", ".join(f"{x:+.1f}" for x in ub)} · Γ: {", ".join(f"{x:+.1f}" for x in ug)} → Γ {"ΑΝΤΙΚΑΘΙΣΤΑ το Β" if ok else "ΔΕΝ αντικαθιστα το Β"}')
open(os.path.join(SC, 't34_status_role_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
