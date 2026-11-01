# -*- coding: utf-8 -*-
"""t1_edge_size.py — ΤΕΣΤ 1 (Στελιος 20/10: «αν οσο μεγαλυτερο το edge τοσο καλυτερο το pick, ή τα φουσκωμενα edges ειναι ψευτικα»)
= TODO #3 (CLV ανα μεγεθος edge) + βαθμονομηση. ΜΟΝΟ μετρηση, τιποτα live.
Βαση = production + B2B 3.0 + απουσιες (MG + 3·(B2A−B2H) + 0.75·LOSS[2]). Picks = πλευρα με το μεγαλυτερο edge στο ΑΝΟΙΓΜΑ (Crown), edge ≥8%.
Για καθε pick: δηλωμενη πιθ. (p_win + p_push/2), πραγματικη καλυψη, ROI ανοιγματος, ROI στο ΚΛΕΙΣΙΜΟ (ιδια πλευρα, γραμμη/αποδοση κλεισιματος),
CLV ποντοι = (δικαιη διαφορα κλεισ. − ανοιγμ.) προς τη μερια μας · CLV πιθ. = P_κλεισ(καλυψη γραμμης ανοιγματος) − P_ανοιγμ (χωρις γκανιοτα).
Καδοι edge 8-10/10-12/12-16/16-25/25+ · μηνες Οκτ/Νοε/Δεκ/Ιαν+ · με/χωρις ξαφνικη απουσια (news_test FRESH, NF>0, box score).

ΠΡΟ-ΔΗΛΩΜΕΝΑ (πριν το τρεξιμο):
 (Μ) «ROI μονοτονο στο edge» = ROI καθε καδου ≥ ROI προηγουμενου − 1.5pp (θορυβος) σε ολους τους καδους ΚΑΙ ROI(≥16%) > ROI(8-12%) + 1.5pp.
 (Π) «μεγαλα edges = πληροφορια που λειπει» = μεσο CLV ποντων στους καδους ≥16% ΑΡΝΗΤΙΚΟ με t ≤ −2 ΚΑΙ χαμηλοτερο απο του 8-10%.
 Βαθμονομηση: Δ = πραγματικη − δηλωμενη πιθ. ανα καδο (αρνητικο που μεγαλωνει = φουσκωμενα edges).
Εξοδος: t1_edge_size_out.txt"""
import os, sys
SC = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, SC)
sys.stdout.reconfigure(encoding='utf-8')
from t_common import load, cover, side_pick, settle, np
D = load()
MG, OC, S, EV, ACT, SIG = D['MG'], D['OC'], D['SEAS_G'], D['EV'], D['ACT'], D['SIG']
V = MG + 3.0 * (D['B2A'] - D['B2H']) + 0.75 * D['LOSS2']
MON = D['G'].date.dt.month.values; NF = D['NF']; FD = D['FD']

def pside(mk, L, s_):
    pw, pp, pl = cover(mk, L, SIG); return (pw if s_ == 1 else pl) + pp / 2

R = []
for i, d in OC.items():
    if S[i] not in EV or not np.isfinite(V[i]): continue
    L, mk, o1, o2 = d['o']; Lc, mkc, c1, c2 = d['c']
    s_, e, od_, p, pp = side_pick(V[i], L, o1, o2, SIG)
    if e < .08: continue
    pnl, win = settle(ACT[i], L, s_, od_)
    pnl_c, win_c = settle(ACT[i], Lc, s_, c1 if s_ == 1 else c2)
    # φρεσκια απουσια: στη δικη μας πλευρα / αντιπαλου (FD>0 = ο γηπεδουχος εχασε περισσοτερα)
    fr = 'καμια' if NF[i] == 0 else ('δικη μας' if np.sign(FD[i]) == s_ else 'αντιπαλου')
    R.append(dict(i=i, Y=S[i], m=MON[i], e=e, p=p + pp / 2, win=win, pnl=pnl, pnlc=pnl_c,
                  clv=(mkc - mk) * s_, clvp=pside(mkc, L, s_) - pside(mk, L, s_), fr=fr, dis=abs(V[i] - mk)))
print(f'picks ανοιγματος ≥8%: {len(R)} (ολη η σεζον, 5 σεζον) · Οκτ-Δεκ {sum(r["m"] in (10, 11, 12) for r in R)}')

EB = [(.08, .10), (.10, .12), (.12, .16), (.16, .25), (.25, 9)]
def row(b, lbl):
    if not b: print(f'  {lbl:14s} |     0'); return None
    a = lambda k: np.array([r[k] for r in b])
    ps = {Y: sum(r['pnl'] for r in b if r['Y'] == Y) for Y in EV}
    clv = a('clv'); se = clv.std(ddof=1) / np.sqrt(len(b)) if len(b) > 1 else np.nan
    print(f'  {lbl:14s} | {len(b):5d} | {a("p").mean():.3f} {a("win").mean():.3f} {a("win").mean() - a("p").mean():+.3f} | {a("pnl").mean() * 100:+6.1f}% {a("pnlc").mean() * 100:+6.1f}% | '
          f'{clv.mean():+5.2f} ±{se:4.2f} (t {clv.mean() / se:+5.1f}) {a("clvp").mean() * 100:+5.1f}pp | {sum(ps[Y] > 0 for Y in EV)}/5 | {a("dis").mean():4.1f}')
    return a('pnl').mean() * 100, clv.mean(), clv.mean() / se
HDR = f'  {"καδος":14s} |     n | δηλ.  πραγμ  Δ     | ROIανοιγ ROIκλεισ | CLV ποντοι          CLV πιθ | θετ  | |μοντ−αγ|'
def table(Rs, title):
    print(f'\n=== {title} ==='); print(HDR); out = {}
    for lo, hi in EB:
        out[(lo, hi)] = row([r for r in Rs if lo <= r['e'] < hi], f'{lo * 100:g}-{hi * 100:g}%' if hi < 9 else f'{lo * 100:g}%+')
    row(Rs, 'ΟΛΑ ≥8%'); return out

T = table(R, 'Α. ΟΛΗ Η ΣΕΖΟΝ — ανα καδο δηλωμενου edge')
Tod = table([r for r in R if r['m'] in (10, 11, 12)], 'Β. ΟΚΤ-ΔΕΚ — ανα καδο')
for nm, ms in (('Οκτ', (10,)), ('Νοε', (11,)), ('Δεκ', (12,)), ('Ιαν+', (1, 2, 3, 4, 5, 6))):
    table([r for r in R if r['m'] in ms], f'Γ. μηνας {nm}')
for fr in ('καμια', 'δικη μας', 'αντιπαλου'):
    table([r for r in R if r['fr'] == fr], f'Δ. ξαφνικη απουσια: {fr} (box score — ΔΕΝ ηταν γνωστη στο ανοιγμα)')

# ---------- ετυμηγορια με τα προ-δηλωμενα ----------
def verdict(Tb, lbl):
    rois = [Tb[k][0] for k in EB if Tb[k]]
    mono = all(rois[j] >= rois[j - 1] - 1.5 for j in range(1, len(rois)))
    big = [r for r in (R if lbl == 'ολη' else [r for r in R if r['m'] in (10, 11, 12)]) if r['e'] >= .16]
    sm = [r for r in (R if lbl == 'ολη' else [r for r in R if r['m'] in (10, 11, 12)]) if r['e'] < .12]
    rb, rs = np.mean([r['pnl'] for r in big]) * 100, np.mean([r['pnl'] for r in sm]) * 100
    cb = np.array([r['clv'] for r in big]); tb = cb.mean() / (cb.std(ddof=1) / np.sqrt(len(cb)))
    c8 = Tb[EB[0]][1]
    print(f'  [{lbl}] (Μ) μονοτονο: {"ΝΑΙ" if (mono and rb > rs + 1.5) else "ΟΧΙ"} (ROI ανα καδο {" / ".join(f"{x:+.1f}" for x in rois)} · ≥16% {rb:+.1f}% vs 8-12% {rs:+.1f}%)')
    print(f'  [{lbl}] (Π) μεγαλα edges αρνητικο CLV: {"ΝΑΙ" if (cb.mean() < 0 and tb <= -2 and cb.mean() < c8) else "ΟΧΙ"} (CLV ≥16% {cb.mean():+.2f} π. t {tb:+.1f} · 8-10% {c8:+.2f} π.)')
print('\n=== ΕΤΥΜΗΓΟΡΙΑ (προ-δηλωμενα κριτηρια) ===')
verdict(T, 'ολη'); verdict(Tod, 'Οκτ-Δεκ')
