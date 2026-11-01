# -*- coding: utf-8 -*-
"""t24c_motivation_reports.py — ΚΙΝΗΤΡΟ ΜΕ ΑΠΟΥΣΙΕΣ ΑΠΟ ΤΙΣ ΕΠΙΣΗΜΕΣ ΑΝΑΦΟΡΕΣ (21/10/2026, Στελιος: «εφοσον εχουμε τις λιστες του NBA,
γιατι μετραμε με τον κανονα των 2 αγωνων και οχι με τα reports;»).
Ιδια γκρουπ με t24 (nba_tests/_t24_groups.csv: βαθμολογια ως τη μερα). Ιδια μηχανη με t22 (αντιγραφο live χωρις «εχασε 2» + απουσιες απο
την τελευταια επισημη αναφορα με ωρα ≤ τ, τιμη Crown στο τ). Στιγμες: ανοιγμα · Τ−2ω · Τ−30′. Α = μονο Out · Β = πιθανοτητες (D .97 Q .45 P .07).
Πινακες: Μαρτιος & Απριλιος, picks ΥΠΕΡ καθε γκρουπ / ΚΟΝΤΡΑ καθε γκρουπ, + «ΥΠΕΡ χωρις-κινητρο (κλειδωμενη/αδιαφορη/tanking) vs ομαδα με κινητρο».
Περιγραφικο (κανενας κανονας). Εξοδος: t24c_motivation_reports_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0]
src = src.replace("if os.environ.get('T22_AUDIT'):", "if False:")
g22 = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g22)
sys.stdout.reconfigure(encoding='utf-8')
for k in ('np', 'pd', 'G', 'SEAS_G', 'dD', 'EV', 'ACT', 'VNO', 'SER', 'SHIFT', 'cover_', 'SIG_', 'REP_SEASONS', 'W_A', 'W_B', 'abs_cost', 'line_at'):
    globals()[k] = g22[k]
GR = pd.read_csv(os.path.join(SC, '_t24_groups.csv'), usecols=['i', 't', 'g'])
GRP = {(int(r.i), r.t): r.g for r in GR.itertuples(index=False)}
MON = G.date.dt.month.values
TAUS = (('ανοιγμα', None), ('Τ−2ω', 2), ('Τ−30′', 0.5))
recs = []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REP_SEASONS or not np.isfinite(VNO[i]) or MON[i] not in (3, 4): continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    close = line_at(rows, tip, sw); h, a, d = G.home.values[i], G.away.values[i], dD[i]
    gh, ga = GRP.get((i, h), 'νωρις'), GRP.get((i, a), 'νωρις')
    for lab, hrs in TAUS:
        tau = rows[0][0] if hrs is None else tip - hrs * 3600
        if hrs is not None and tau < rows[0][0]: continue
        ln = line_at(rows, tau, sw)
        if not ln: continue
        L, oh, oa, fair, _ = ln
        for vname, W in (('Α', W_A), ('Β', W_B)):
            ch, _ = abs_cost(h, d, s, tau, W); ca, _ = abs_cost(a, d, s, tau, W)
            m = VNO[i] - ch + ca
            pw, pp, pl = cover_(m, L, SIG_); e1, e2 = pw * oh + pp - 1, pl * oa + pp - 1
            sd, e, od_ = (1, e1, oh) if e1 >= e2 else (-1, e2, oa)
            if e < .08: continue
            x = (ACT[i] + L) * sd; res = (od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0)
            recs.append(dict(i=i, sea=s, mon=int(MON[i]), tau=lab, v=vname, res=res, clv=sd * (close[3] - fair), e=e, sd=sd, L=L, od=od_, team=h if sd == 1 else a, opp=a if sd == 1 else h, m=m,
                             g=gh if sd == 1 else ga, og=ga if sd == 1 else gh))
X = pd.DataFrame(recs)
X.to_csv(os.path.join(SC, '_t24c_picks.csv'), index=False)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d):
    if not len(d): return '        —'
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+6.1f}% ({len(d):3d}, {d.res.sum():+6.1f}μ, {int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f}'
GROUPS = ('ΚΛΕΙΔΩΜΕΝΗ', 'ΜΑΧΗ ΘΕΣΗΣ 1-6', 'ΜΑΧΗ PLAY-IN', 'ΑΔΙΑΦΟΡΗ', 'TANKING')
NOMOT = ('ΚΛΕΙΔΩΜΕΝΗ', 'ΑΔΙΑΦΟΡΗ', 'TANKING'); MOT = ('ΜΑΧΗ ΘΕΣΗΣ 1-6', 'ΜΑΧΗ PLAY-IN')
P('NBA · ΚΙΝΗΤΡΟ ΜΕ ΑΠΟΥΣΙΕΣ ΑΠΟ ΕΠΙΣΗΜΕΣ ΑΝΑΦΟΡΕΣ (τιμη & αναφορα την ιδια στιγμη) · 5 σεζον · picks edge ≥8%')
P('κελι: ROI (picks, μοναδες, θετικες σεζον) CLV ποντοι')
for mon, per in ((4, 'ΑΠΡΙΛΙΟΣ'), (3, 'ΜΑΡΤΙΟΣ')):
    for v, vl in (('Α', 'Α μονο Out'), ('Β', 'Β πιθανοτητες')):
        P(''); P(f'=== {per} · {vl} ===')
        P(f'  {"":38s} | ' + ' | '.join(f'{lab:46s}' for lab, _ in TAUS))
        D_ = X[(X.mon == mon) & (X.v == v)]
        P(f'  {"ΟΛΑ":38s} | ' + ' | '.join(f'{cell(D_[D_.tau == lab]):46s}' for lab, _ in TAUS))
        for g in GROUPS:
            P(f'  {"ΥΠΕΡ " + g:38s} | ' + ' | '.join(f'{cell(D_[(D_.tau == lab) & (D_.g == g)]):46s}' for lab, _ in TAUS))
        for g in GROUPS:
            P(f'  {"ΚΟΝΤΡΑ " + g:38s} | ' + ' | '.join(f'{cell(D_[(D_.tau == lab) & (D_.og == g)]):46s}' for lab, _ in TAUS))
        P(f'  {"ΥΠΕΡ χωρις-κινητρο vs με κινητρο":38s} | ' + ' | '.join(f'{cell(D_[(D_.tau == lab) & D_.g.isin(NOMOT) & D_.og.isin(MOT)]):46s}' for lab, _ in TAUS))
        P(f'  {"ΟΛΑ εκτος αυτων":38s} | ' + ' | '.join(f'{cell(D_[(D_.tau == lab) & ~(D_.g.isin(NOMOT) & D_.og.isin(MOT))]):46s}' for lab, _ in TAUS))
open(os.path.join(SC, 't24c_motivation_reports_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
