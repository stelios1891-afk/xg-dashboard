# -*- coding: utf-8 -*-
"""t101_late_picks_absences.py — ΑΡΓΑ PICKS ΧΑΝΤΙΚΑΠ ΜΕ ΑΠΟΥΣΙΕΣ ΣΤΟ ΜΟΝΤΕΛΟ (25/10/2026, Στελιος «το ευρημα για τα μπετς μετα το ανοιγμα
μηπως ηταν οταν δεν υπολογιζαμε απουσιες;» — αφορμη Grizzlies −3: 8% τωρα, 3.6% στην πρωτη γραμμη).
Πλαισιο t22: live αντιγραφο (VNO) − απουσιες απο την ΕΠΙΣΗΜΗ αναφορα με ωρα ≤ τ (πιθανοτητες D .97 · Q .45 · P .07, οπως το live), Crown 5 σεζον.
Κατωφλι οπως live: 8% (Ιαν-Φεβ 12%). ΑΡΓΟ pick = πλευρα με edge ≥ κατωφλι στο τ ∈ {Τ−12ω, Τ−6ω, Τ−2ω, Τ−30′} που ΔΕΝ ηταν pick στο ανοιγμα
(μοντελο+αναφορα του ανοιγματος, γραμμη ανοιγματος). Μετραει μια φορα, την πρωτη στιγμη. Αποτελεσμα/CLV στην τιμη του τ.
ΟΜΑΔΕΣ (κανονας live: edge του ΤΩΡΙΝΟΥ μοντελου στην ΠΡΩΤΗ γραμμη ≥ κατωφλι):
  Α «ΤΟ ΑΦΗΝΕΙ ο κανονας» (το μοντελο αλλαξε αρκετα — συνηθως απουσια — ωστε και η πρωτη γραμμη να ειναι pick)
  Β «ΤΟ ΚΟΒΕΙ ο κανονας» (το pick υπαρχει μονο επειδη ηρθε η τιμη) · Β1 χωρις αλλαγη απουσιων (|Δ| <0.3π) · Β2 με αλλαγη απουσιων (τυπου Grizzlies)
ΠΡΟ-ΔΗΛΩΜΕΝΟ: ο κανονας χαλαρωνει για μια ομαδα ΜΟΝΟ αν θετικη σε ≥4/5 σεζον ΚΑΙ CLV > 0 ΚΑΙ n ≥ 80.
Εξοδος: t101_late_picks_absences_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g['np'], g['pd']; SER, SHIFT, G, dD, SEAS_G, EV, VNO, ACT = g['SER'], g['SHIFT'], g['G'], g['dD'], g['SEAS_G'], g['EV'], g['VNO'], g['ACT']
abs_cost, W, line_at, cover_, SIG_, REP_SEASONS = g['abs_cost'], g['W_B'], g['line_at'], g['cover_'], g['SIG_'], g['REP_SEASONS']
def edges(m, ln):
    L, oh, oa = ln[0], ln[1], ln[2]; pw, pp, pl = cover_(m, L, SIG_)
    return {1: pw * oh + pp - 1, -1: pl * oa + pp - 1}, (oh, oa), pp
TAUS = (('Τ−12ω', 12), ('Τ−6ω', 6), ('Τ−2ω', 2), ('Τ−30′', 0.5))
recs = []; n_open = 0
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]): continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    mon = int(G.date.dt.month.values[i]); thr = .12 if mon in (1, 2) else .08
    h, a, d = G.home.values[i], G.away.values[i], dD[i]; t0 = rows[0][0]
    close = line_at(rows, tip, sw); ln0 = line_at(rows, t0, sw)
    ab0 = -abs_cost(h, d, s, t0, W)[0] + abs_cost(a, d, s, t0, W)[0]; m0 = VNO[i] + ab0
    E0, _, _ = edges(m0, ln0); n_open += sum(E0[k] >= thr for k in E0)
    seen = set()
    for lab, hrs in TAUS:
        tau = tip - hrs * 3600
        if tau <= t0: continue
        ln = line_at(rows, tau, sw)
        abt = -abs_cost(h, d, s, tau, W)[0] + abs_cost(a, d, s, tau, W)[0]; m = VNO[i] + abt
        E, (oh, oa), pp = edges(m, ln); ER, _, _ = edges(m, ln0)          # ER = τωρινο μοντελο στην ΠΡΩΤΗ γραμμη (κανονας live)
        for sd in (1, -1):
            if E[sd] < thr or E0[sd] >= thr or sd in seen: continue
            seen.add(sd)
            od = oh if sd == 1 else oa; x = (ACT[i] + ln[0]) * sd
            grp = 'Α' if ER[sd] >= thr else ('Β2' if abs(abt - ab0) >= 0.3 else 'Β1')
            recs.append(dict(i=i, sea=s, mon=mon, tau=lab, grp=grp, res=(od - 1) if x > 0 else (0.0 if x == 0 else -1.0),
                             clv=sd * (close[3] - ln[3]), dab=sd * (abt - ab0), dln=sd * (ln[0] - ln0[0]), e=E[sd], e0=E0[sd], er=ER[sd]))
X = pd.DataFrame(recs); out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d):
    if not len(d): return '—'
    ps = d.groupby('sea').res.sum(); pos = int((ps > 0).sum())
    ok = pos >= 4 and d.clv.mean() > 0 and len(d) >= 80
    return (f'{100 * d.res.mean():+6.1f}% ({len(d):4d} picks, {d.res.sum():+6.1f}μ, θετ {pos}/{d.sea.nunique()}) · CLV {d.clv.mean():+.2f}π · Οκτ-Δεκ {100 * d[d.mon.isin([10, 11, 12])].res.mean():+.1f}%'
            + (' ✓' if ok else ''))
P(f'NBA ΧΑΝΤΙΚΑΠ · ΑΡΓΑ picks ΜΕ απουσιες (επισημη αναφορα της στιγμης) · Crown · σεζον {sorted(X.sea.unique())} · picks ανοιγματος συνολο {n_open}')
P('κελι = ROI στην τιμη της στιγμης (picks, μοναδες, θετικες σεζον) · CLV = κινηση γραμμης απο τη στιγμη ως το κλεισιμο προς εμας (ποντοι)')
GN = {'Α': 'Α  ΤΟ ΑΦΗΝΕΙ ο κανονας (τωρινο μοντελο ≥ κατωφλι και στην 1η γραμμη)', 'Β1': 'Β1 ΤΟ ΚΟΒΕΙ · μονο κινηση τιμης', 'Β2': 'Β2 ΤΟ ΚΟΒΕΙ · τιμη + αλλαγη απουσιων (τυπου Grizzlies)'}
P(f'\nΟΛΑ τα αργα picks: {cell(X)}')
for k in ('Α', 'Β1', 'Β2'):
    d = X[X.grp == k]; P(f'\n{GN[k]}:\n   ολα   {cell(d)}')
    if len(d): P(f'   μεσο: edge τωρα {100 * d.e.mean():.1f}% · στο ανοιγμα (τοτε) {100 * d.e0.mean():.1f}% · τωρινο μοντελο στην 1η γραμμη {100 * d.er.mean():.1f}% · '
                 f'απουσιες υπερ μας {d.dab.mean():+.2f}π · γραμμη ηρθε προς εμας {d.dln.mean():+.2f}π')
    for lab, _ in TAUS: P(f'   {lab:6s} {cell(d[d.tau == lab])}')
B = X[X.grp != 'Α']; P(f'\nΟΛΑ οσα κοβει ο κανονας (Β1+Β2): {cell(B)}')
for s, d in X.groupby('sea'): P(f'   {s}: Α {d[d.grp == "Α"].res.sum():+.1f}μ ({(d.grp == "Α").sum()}) · Β1 {d[d.grp == "Β1"].res.sum():+.1f}μ ({(d.grp == "Β1").sum()}) · Β2 {d[d.grp == "Β2"].res.sum():+.1f}μ ({(d.grp == "Β2").sum()})')
X.to_csv(os.path.join(SC, '_t101_picks.csv'), index=False)
P(chr(10) + 'ελεγχος (2 παραδειγματα):')
for k in ('Α', 'Β2'):
    r = X[X.grp == k].iloc[0]; j = int(r.i)
    P(f'   {k}: {G.home.values[j]}-{G.away.values[j]} {str(dD[j])} · {r.tau} · edge τωρα {100*r.e:.1f}% · ανοιγμα {100*r.e0:.1f}% · τωρινο στην 1η {100*r.er:.1f}% · απουσιες {r.dab:+.2f}π · γραμμη {r.dln:+.1f}π · αποτ {r.res:+.2f}')
open(os.path.join(SC, 't101_late_picks_absences_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
