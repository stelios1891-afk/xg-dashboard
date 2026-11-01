# -*- coding: utf-8 -*-
"""t102_report_moment_picks.py — PICKS ΠΟΥ ΓΕΝΝΙΟΥΝΤΑΙ ΤΗ ΣΤΙΓΜΗ ΠΟΥ ΑΛΛΑΖΕΙ Η ΕΠΙΣΗΜΗ ΑΝΑΦΟΡΑ (25/10/2026, Στελιος «το καθενα πρεπει να το
τσεκαρεις την ακριβη στιγμη της απουσιας»). Πλαισιο t22/t101: live αντιγραφο (VNO) − απουσιες επισημης αναφορας (D .97 · Q .45 · P .07), Crown 5 σεζον.
ΓΕΓΟΝΟΣ = ωρα δημοσιευσης αναφορας (μετα το ανοιγμα, πριν το τζαμπολ) οπου αλλαζει το κοστος απουσιων του ματς (≥0.1π, παικτες ≥20′).
PICK ΓΕΝΝΗΜΕΝΟ ΑΠΟ ΤΗΝ ΑΠΟΥΣΙΑ: πλευρα με edge < κατωφλι λιγο πριν (μοντελο πριν, γραμμη πριν) ΚΑΙ ≥ κατωφλι μετα (μοντελο μετα, γραμμη στο +k′),
  k ∈ {0, 5, 15}· οχι pick στο ανοιγμα, μια φορα ανα ματς/πλευρα (το πρωτο γεγονος). Κατωφλι live 8% (Ιαν-Φεβ 12%). Αποτελεσμα/CLV στην τιμη του +k′.
ΟΜΑΔΕΣ (κανονας live): Α «ΤΟ ΑΦΗΝΕΙ» = μοντελο-μετα ≥ κατωφλι και στην ΠΡΩΤΗ γραμμη · Β «ΤΟ ΚΟΒΕΙ» = αλλιως.
ΠΡΟ-ΔΗΛΩΜΕΝΟ: ο κανονας χαλαρωνει για τη Β ΜΟΝΟ αν θετικη σε ≥4/5 σεζον ΚΑΙ CLV > 0 ΚΑΙ n ≥ 80.
Εξοδος: t102_report_moment_picks_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g['np'], g['pd']; SER, SHIFT, G, dD, SEAS_G, EV, VNO, ACT = g['SER'], g['SHIFT'], g['G'], g['dD'], g['SEAS_G'], g['EV'], g['VNO'], g['ACT']
abs_cost, W, line_at, cover_, SIG_, REP_SEASONS, REP_BY = g['abs_cost'], g['W_B'], g['line_at'], g['cover_'], g['SIG_'], g['REP_SEASONS'], g['REP_BY']
def edges(m, ln):
    pw, pp, pl = cover_(m, ln[0], SIG_); return {1: pw * ln[1] + pp - 1, -1: pl * ln[2] + pp - 1}
KS = (0, 5, 15); recs = []; nev = 0
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]): continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    mon = int(G.date.dt.month.values[i]); thr = .12 if mon in (1, 2) else .08
    h, a, d = G.home.values[i], G.away.values[i], dD[i]; t0 = rows[0][0]
    close = line_at(rows, tip, sw); ln0 = line_at(rows, t0, sw)
    AB = lambda tau: -abs_cost(h, d, s, tau, W)[0] + abs_cost(a, d, s, tau, W)[0]
    E0 = edges(VNO[i] + AB(t0), ln0)
    times = sorted({ep for t in (h, a) for b in (0, 1, 2, 3) for ep, _, _ in REP_BY.get((t, d - np.timedelta64(b, 'D')), ()) if t0 < ep < tip - 60})
    if not times: continue
    seen = {k: set() for k in KS}; prev = AB(times[0] - 1)
    for ep in times:
        cur = AB(ep)
        if abs(cur - prev) < 0.1: prev = cur; continue
        nev += 1; lb = line_at(rows, ep - 1, sw) or ln0; Eb = edges(VNO[i] + prev, lb); ER = edges(VNO[i] + cur, ln0)
        lh = line_at(rows, ep - 3600, sw) or ln0
        for k in KS:
            ln = line_at(rows, ep + 60 * k, sw)
            if ep + 60 * k >= tip: continue
            Ea = edges(VNO[i] + cur, ln)
            for sd in (1, -1):
                if Ea[sd] < thr or Eb[sd] >= thr or E0[sd] >= thr or sd in seen[k]: continue
                seen[k].add(sd); od = ln[1] if sd == 1 else ln[2]; x = (ACT[i] + ln[0]) * sd
                recs.append(dict(i=i, sea=s, mon=mon, k=k, grp='Α' if ER[sd] >= thr else 'Β', res=(od - 1) if x > 0 else (0.0 if x == 0 else -1.0),
                                 clv=sd * (close[3] - ln[3]), dab=sd * (cur - prev), pre=sd * (lb[0] - lh[0]), post=sd * (ln[0] - lb[0]),
                                 hrs=(tip - ep) / 3600, e=Ea[sd], eb=Eb[sd], er=ER[sd]))
        prev = cur
X = pd.DataFrame(recs); out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d):
    if not len(d): return '—'
    ps = d.groupby('sea').res.sum(); pos = int((ps > 0).sum()); ok = pos >= 4 and d.clv.mean() > 0 and len(d) >= 80
    return (f'{100 * d.res.mean():+6.1f}% ({len(d):4d} picks, {d.res.sum():+6.1f}μ, θετ {pos}/{d.sea.nunique()}) · CLV {d.clv.mean():+.2f}π · Οκτ-Δεκ {100 * d[d.mon.isin([10, 11, 12])].res.mean():+.1f}%'
            + (' ✓ ΠΕΡΝΑ' if ok else ''))
P(f'NBA ΧΑΝΤΙΚΑΠ · PICKS ΓΕΝΝΗΜΕΝΑ ΤΗ ΣΤΙΓΜΗ ΑΛΛΑΓΗΣ ΤΗΣ ΕΠΙΣΗΜΗΣ ΑΝΑΦΟΡΑΣ · Crown · σεζον {sorted(X.sea.unique())} · γεγονοτα (αλλαγη ≥0.1π) {nev}')
P('κελι = ROI στην τιμη του +k′ · CLV = κινηση γραμμης απο τη στιγμη ως το κλεισιμο προς εμας (ποντοι)')
for k in KS:
    P(f'\n=== τιμη στο +{k}′ μετα την αναφορα ===')
    for grp, nm in (('Α', 'Α ΤΟ ΑΦΗΝΕΙ ο κανονας 1ης γραμμης'), ('Β', 'Β ΤΟ ΚΟΒΕΙ ο κανονας 1ης γραμμης')):
        d = X[(X.k == k) & (X.grp == grp)]; P(f'  {nm:34s} {cell(d)}')
        if len(d): P(f'     μεσο: απουσιες υπερ μας {d.dab.mean():+.2f}π · γραμμη την ωρα ΠΡΙΝ την αναφορα ηρθε προς εμας {d.pre.mean():+.2f}π · '
                     f'μεσα στα {k}′ {d.post.mean():+.2f}π · {d.hrs.median():.1f}ω πριν το τζαμπολ · edge {100 * d.e.mean():.1f}% (πριν {100 * d.eb.mean():.1f}%, 1η γραμμη {100 * d.er.mean():.1f}%)')
    d = X[X.k == k]; P('  ανα σεζον (μοναδες Α / Β): ' + ' · '.join(f'{s}: {d[(d.sea == s) & (d.grp == "Α")].res.sum():+.1f} / {d[(d.sea == s) & (d.grp == "Β")].res.sum():+.1f}' for s in sorted(d.sea.unique())))
X.to_csv(os.path.join(SC, '_t102_picks.csv'), index=False)
P(chr(10) + 'ελεγχος (2 παραδειγματα, +0′):')
for grp in ('Α', 'Β'):
    dd = X[(X.k == 0) & (X.grp == grp)]
    if len(dd):
        r = dd.iloc[len(dd) // 2]; j = int(r.i)
        P(f'   {grp}: {G.home.values[j]}-{G.away.values[j]} {str(dD[j])} · {r.hrs:.1f}ω πριν · απουσιες {r.dab:+.2f}π · edge πριν {100*r.eb:.1f}% → μετα {100*r.e:.1f}% · 1η γραμμη {100*r.er:.1f}% · αποτ {r.res:+.2f}')
open(os.path.join(SC, 't102_report_moment_picks_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
