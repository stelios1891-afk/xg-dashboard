"""euro_totals_move_split.py — 14/10/2026 (Στελιος: «αν μετρησουμε μονο τα picks που βγαινουν στο ανοιγμα και η αγορα ερχεται μετα προς το
μοντελο, μηπως σε αυτα προβλεπουμε καλυτερα και δεν ειναι η τυχη των γκολ;»). Picks συνολων κατηγοριας Α (UCL over ≥4% / under ≥10% · UECL over ≥−2%
· UEL over ≥4% / under ≥10%), πρωτη εμφανιση ≤72ω (χωρις τελευταια τιμη), Crown & SBOBET. ΚΙΝΗΣΗ = πόσο κινηθηκε η γραμμη συνολου μετα την εισοδο
ΠΡΟΣ το pick (+ = προς εμας). Δυο εκδοχες:
  (α) ΔΙΑΓΝΩΣΤΙΚΟ: κινηση ως το ΚΛΕΙΣΙΜΟ (δεν την ξερουμε οταν πονταρουμε — δειχνει μονο αν η κινηση «σημαινει» κατι)
  (β) ΕΦΑΡΜΟΣΙΜΟ: picks που βγηκαν ≥24ω πριν· κινηση ως τις 12ω πριν → πονταρουμε ΣΤΙΣ 12ω (τιμη 12ω) μονο αν ηρθε προς εμας
ROI και ΑΞΙΑ ΜΕ ΒΑΣΗ ΤΑ ΤΕΛΙΚΑ xG.
"""
import sys, os
NL = chr(10)
src = open('uel_full_review.py', encoding='utf-8').read().split('# ======================= 1. ΣΥΝΟΛΑ')[0]
src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
_MY = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(src); sys.stdout = _MY; sys.stdout.reconfigure(encoding='utf-8')
RULES = {'ChampionsLeague': (('over', .04), ('under', .10)), 'ConferenceLeague': (('over', -.02),), 'EuropaLeague': (('over', .04), ('under', .10))}
P = []
for cm in RULES:
    for i in [i for i in np.where(COMP == cm)[0] if SRCC[i] == 'FF']:
        td = ES.tot_dist(OH[i], OA[i], DRAW_SCALE); x = XG.get(str(MIDS[i])); tot = GH[i] + GA[i]
        tdx = ES.tot_dist(max(x[0], .05), max(x[1], .05), DRAW_SCALE) if x else None
        def xval(L, od, side):
            if tdx is None: return np.nan
            qo, qu = ES.p_over(tdx, L); qw, ql = (qo, qu) if side == 'over' else (qu, qo); return qw * (od - 1) * (1 - picks.MARGIN) - ql
        for bk in ('Crown', 'SBOBET'):
            sc = snap_ou(MIDS[i], bk, 0); s12 = snap_ou(MIDS[i], bk, 12)
            for side, th in RULES[cm]:
                sg = 1 if side == 'over' else -1
                for h in HS[:-1]:
                    s = snap_ou(MIDS[i], bk, h)
                    if not s: continue
                    L, o, un = s; po, pu = ES.p_over(td, L); od = o if side == 'over' else un
                    if not (1.70 <= od <= 2.10): continue
                    pw, pl = (po, pu) if side == 'over' else (pu, po)
                    if pw * (od - 1) * (1 - picks.MARGIN) - pl < th: continue
                    m0 = mtot(L, o, un)
                    mvc = sg * (mtot(*sc) - m0) if sc else np.nan
                    rec = dict(comp=cm, sea=SEA[i], bk=bk, side=side, h=h, mvc=mvc, pnl=settle(tot, L, od, side == 'over'), xv=xval(L, od, side),
                               mv12=np.nan, p12=np.nan, x12=np.nan)
                    if h >= 24 and s12:
                        L2, o2, u2 = s12; od2 = o2 if side == 'over' else u2
                        rec['mv12'] = sg * (mtot(L2, o2, u2) - m0)
                        if 1.70 <= od2 <= 2.10: rec['p12'] = settle(tot, L2, od2, side == 'over'); rec['x12'] = xval(L2, od2, side)
                    P.append(rec); break
P = pd.DataFrame(P)
def line(y, col='pnl', xc='xv'):
    y = y.dropna(subset=[col])
    if len(y) < 8: return f'n{len(y) / 2:4.0f} (λιγα)'
    return f'{len(y) / 2:4.0f} picks · ROI {100 * y[col].mean():+6.1f}% · ΑΞΙΑ xG {100 * y[xc].mean():+5.1f}%'
for cm, lab in (('ChampionsLeague', 'CHAMPIONS'), ('ConferenceLeague', 'CONFERENCE'), ('EuropaLeague', 'EUROPA (οχι live)')):
    for side in ('over', 'under'):
        X = P[(P.comp == cm) & (P.side == side)]
        if len(X) == 0: continue
        print(f'{NL}===== {lab} {side.upper()} — ολα: {line(X)}')
        print('   (α) κινηση ως το ΚΛΕΙΣΙΜΟ (διαγνωστικο):')
        for l, m_ in (('ηρθε ΠΡΟΣ εμας ≥0.10', X.mvc >= .10), ('σχεδον τιποτα (±0.10)', X.mvc.abs() < .10), ('πηγε ΚΟΝΤΡΑ ≥0.10', X.mvc <= -.10)):
            print(f'      {l:24s} {line(X[m_])}')
        Y = X[X.h >= 24]
        print(f'   (β) ΕΦΑΡΜΟΣΙΜΟ: picks ≥24ω πριν ({len(Y) / 2:.0f}), κινηση ως τις 12ω, ποντο ΣΤΙΣ 12ω:')
        for l, m_ in (('ηρθε ΠΡΟΣ εμας ≥0.10', Y.mv12 >= .10), ('σχεδον τιποτα (±0.10)', Y.mv12.abs() < .10), ('πηγε ΚΟΝΤΡΑ ≥0.10', Y.mv12 <= -.10)):
            print(f'      {l:24s} στην εισοδο {line(Y[m_])} │ στις 12ω {line(Y[m_], "p12", "x12")}')
