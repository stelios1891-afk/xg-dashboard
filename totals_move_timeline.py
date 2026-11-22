"""totals_move_timeline.py — 15/10/2026 (Στελιος: «η αγορα κινειται προς το μοντελο και στα 2 συνολα; αν ναι απο ποια στιγμη και μετα — 8, 6, 4 ωρες;
πιο πριν ποτε κινειται;»). Κατηγορια Α (FotMob και οι 2), 4 σεζον, live μηχανη συνολων. Για καθε ματς: γκολ που δικαιολογει η τιμη συνολων
(Crown, αλλιως SBOBET) σε καθε στιγμη. Ομαδες κατα τη γνωμη του μοντελου στην ΠΡΩΤΗ τιμη: μοντελο ≥0.3 ΠΑΝΩ (over) / ≥0.3 ΚΑΤΩ (under).
Δειχνει: ποσο εχει κινηθει η αγορα απο την πρωτη τιμη ως καθε στιγμη (προς την πλευρα του μοντελου = +) και ΠΟΣΟ σε καθε διαστημα.
"""
import sys, os
NL = chr(10)
_TM = sys.stdout
src = open('uel_full_review.py', encoding='utf-8').read().split('# ======================= 1. ΣΥΝΟΛΑ')[0]
src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(src); sys.stdout = _TM; sys.stdout.reconfigure(encoding='utf-8')
W = ['πρωτη', 168, 72, 48, 36, 24, 12, 8, 6, 4, 2, 1, 0]
LAB = {'πρωτη': 'πρωτη τιμη', 0: 'κλεισιμο'}
def snapW(mid, bk, w):
    ko = KO.get(mid); seq = TOU.get((mid, bk))
    if not ko or not seq: return None
    if w == 'πρωτη': return seq[0][1:] if seq[0][0] <= ko else None
    cut = ko - w * 3600 if w else ko + 900
    prev = [x for x in seq if x[0] <= cut]
    return prev[-1][1:] if prev else None
for cm, lab in (('EuropaLeague', 'EUROPA'), ('ChampionsLeague', 'CHAMPIONS'), ('ConferenceLeague', 'CONFERENCE')):
    rows = []
    for i in [i for i in np.where(COMP == cm)[0] if SRCC[i] == 'FF']:
        for bk in ('Crown', 'SBOBET'):
            S = {w: snapW(MIDS[i], bk, w) for w in W}
            if S['πρωτη'] and S[0]: break
        if not S['πρωτη'] or not S[0]: continue
        M = {w: (mtot(*S[w]) if S[w] else np.nan) for w in W}
        d = (OH[i] + OA[i]) - M['πρωτη']
        rows.append(dict(d=d, **{str(w): M[w] for w in W}))
    X = pd.DataFrame(rows)
    print(f'{NL}===== {lab} κατηγορια Α: {len(X)} ματς')
    for gl, m_, sg in (('μοντελο ΠΑΝΩ απο την αγορα ≥0.3 (over)', X.d >= .3, 1), ('μοντελο ΚΑΤΩ απο την αγορα ≥0.3 (under)', X.d <= -.3, -1),
                       ('κοντα (±0.3)', X.d.abs() < .3, 1)):
        y = X[m_]
        if len(y) < 10: continue
        base = y['πρωτη']
        line1 = f'   {gl:42s} n{len(y):3d} │ κινηση απο πρωτη τιμη (+ = προς το μοντελο): '
        cum = []; prev = 0.0; inc = []
        for w in W[1:]:
            v = (sg * (y[str(w)] - base)).mean(); cum.append(f'{LAB.get(w, str(w) + "ω")} {v:+.2f}'); inc.append(v - prev); prev = v
        print(line1 + ' · '.join(cum))
        print(f'   {"":42s}       κινηση ΜΕΣΑ σε καθε διαστημα: ' + ' · '.join(f'{(LAB.get(W[k], str(W[k]) + "ω"))}→{(LAB.get(W[k + 1], str(W[k + 1]) + "ω"))} {inc[k]:+.2f}' for k in range(len(W) - 1)))
