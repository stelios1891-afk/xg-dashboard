"""travel_seq4.py — 17/10/2026 (Στελιος: «ακολουθια Ευρωπη → πρωταθλημα → ΕΥΡΩΠΗ (3ο ματς) → ΠΡΩΤΑΘΛΗΜΑ (4ο ματς): τι γινεται στο 3ο και στο 4ο;»).
Ιδιο ημερολογιο/αγορα με travel_fatigue_full (ομαδες Δυτ./Κεντρ. Ευρωπης, 2122-2526, κυπελλα μεσα στο ημερολογιο).
ΑΚΟΛΟΥΘΙΑ (συνεχομενα ματς της ομαδας, κανενα αλλο αναμεσα): Ε1 ευρωπαικο → Π1 πρωταθλημα (1.5-6μ) → Ε2 ευρωπαικο (1.5-6μ) → Π2 πρωταθλημα (1.5-6μ).
Κουραση = χλμ των ΕΚΤΟΣ ευρωπαικων ταξιδιων Ε1 + Ε2 (απο την εδρα): 0 (και τα 2 εντος) / <2.000 / 2.000-4.000 / ≥4.000.
3ο ΜΑΤΣ (Ε2): vs αγορα κλεισιματος (Crown/SBOBET) — εντος / εκτος. 4ο ΜΑΤΣ (Π2): vs αγορα (Crown/Bet365 ή Pinnacle 1Χ2) — εντος / εκτος.
Στηλες: συνολο − αγορα · τυφλο UNDER · διαφορα − αγορα (βαζει/τρωει) · τυφλο χαντικαπ ΚΟΝΤΡΑ στην ομαδα. ΕΛΕΓΧΟΣ: ιδιες ομαδες, Π μετα απο ΜΟΝΟ ενα ευρωπαικο."""
import sys, os
_s = open('travel_fatigue_full.py', encoding='utf-8').read()
_s = _s[:_s.index('# ---------------- (Α) ΙΔΙΟ ΜΑΤΣ + (Β) ΕΠΟΜΕΝΟ ----------------')]
_SQ = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _SQ
sys.stdout.reconfigure(encoding='utf-8')
import x12_implied as X12
X12D = {}
for l in open('nowgoal_1x2.jsonl', encoding='utf-8'):
    r = json.loads(l)
    if r.get('close') and min(r['close']) > 1: X12D[str(r['mid'])] = r['close']
EUL = ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague', 'ChampionsLeagueQ', 'EuropaLeagueQ', 'ConferenceLeagueQ')
def ev_trip(tid, e):
    return km(LOC.get(tid), LOC.get(e[2])) if (e[3] and e[2] is not None and LOC.get(tid) and LOC.get(e[2])) else 0.0
def measure(tid, e, kind):
    """team-perspective vs αγορα για ενα ματς του ημερολογιου"""
    y = G[e[1]]
    if y['hs'] is None: return None
    s = 1 if y['h'] == tid else -1; gd = y['hs'] - y['as_']; tot = y['hs'] + y['as_']; ko = int(y['t'].tz_localize('UTC').timestamp())
    if kind == 'eu':
        M = mk(e[1], ko, TRAJ, TOUE, gd, (('Crown', 'SBOBET'),)); books = ('Crown', 'SBOBET'); tou = TOUE
    else:
        M = mk(e[1], ko, AHD, TOUD, gd, (('Crown',), ('Bet365',))); books = ('Crown', 'Bet365'); tou = TOUD
    if M:
        return dict(rc=s * (gd - M['c']), rt=tot - M['tc'], und=under_close(e[1], ko, tou, tot, books), opp=M['pa'] if s == 1 else M['ph'], home=(s == 1))
    c = X12D.get(e[1]) if kind == 'dom' else None
    if c:
        h, a = X12.lam_from_1x2(*c)
        return dict(rc=s * (gd - (h - a)), rt=tot - (h + a + 0.16), und=np.nan, opp=np.nan, home=(s == 1))
    return None
R3, R4, RC = [], [], []
for tid, L in CAL.items():
    if not zone(tid): continue
    for j in range(len(L) - 3):
        e1, p1, e2, p2 = L[j], L[j + 1], L[j + 2], L[j + 3]
        if G[e1[1]]['kind'] != 'eu' or G[e1[1]]['lg'] not in EUL or G[e1[1]]['sea'] not in SEAS: continue
        g1 = (p1[0] - e1[0]).total_seconds() / 86400
        if p1[4] != 'dom' or not (1.5 <= g1 <= 6): continue
        # ΕΛΕΓΧΟΣ: Ε1 → Π1 και ΜΕΤΑ οχι ευρωπαικο ≤7 μερες
        g2 = (e2[0] - p1[0]).total_seconds() / 86400
        k1 = ev_trip(tid, e1)
        if not (e2[4] == 'eu' and G[e2[1]]['lg'] in EUL and 1.5 <= g2 <= 6):
            if e2[4] != 'eu' or g2 > 7:
                m = measure(tid, p1, 'dom')
                if m: RC.append(dict(sea=G[e1[1]]['sea'], km=k1, **m))
            continue
        g3 = (p2[0] - e2[0]).total_seconds() / 86400
        k2 = ev_trip(tid, e2); tk = k1 + k2
        m3 = measure(tid, e2, 'eu')
        if m3: R3.append(dict(sea=G[e1[1]]['sea'], km=tk, k1=k1, k2=k2, **m3))
        if p2[4] == 'dom' and 1.5 <= g3 <= 6:
            m4 = measure(tid, p2, 'dom')
            if m4: R4.append(dict(sea=G[e1[1]]['sea'], km=tk, k1=k1, k2=k2, **m4))
D3, D4, DC = pd.DataFrame(R3), pd.DataFrame(R4), pd.DataFrame(RC)
for Z in (D3, D4, DC): Z['sf'] = (Z.rt + Z.rc) / 2; Z['sa'] = (Z.rt - Z.rc) / 2
def ms(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return f'{v.mean():+.2f}±{v.std() / np.sqrt(max(len(v), 1)):.2f}' if len(v) > 2 else '   —'
def pc(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return f'{100 * v.mean():+6.1f}% ({len(v):3d})' if len(v) >= 5 else f'   —   ({len(v):3d})'
KB = (('0 χλμ (και τα 2 ευρωπαικα εντος)', 0, 1), ('<2.000 χλμ', 1, 2000), ('2.000-4.000', 2000, 4000), ('≥4.000', 4000, 1e9))
HDR = f'   {"ταξιδια Ε1+Ε2":32s} {"n":>5s} │ {"συνολο−αγ":>11s} {"UNDER (n)":>15s} │ {"διαφορα−αγ":>11s} {"βαζει−αγ":>10s} {"τρωει−αγ":>10s} │ {"ΚΟΝΤΡΑ AH (n)":>15s}'
def row(lab, y):
    print(f'   {lab:32s} {len(y):5d} │ {ms(y.rt):>11s} {pc(y.und):>15s} │ {ms(y.rc):>11s} {ms(y.sf):>10s} {ms(y.sa):>10s} │ {pc(y.opp):>15s}')
print('ΑΚΟΛΟΥΘΙΑ Ε1 → Π1 → Ε2 → Π2 · ομαδες Δυτ./Κεντρ. Ευρωπης · 2122-2526 · + = περισσοτερα απ οσα περιμενε η αγορα στο κλεισιμο')
print(f'πληθος ακολουθιων με αγορα: 3ο ματς {len(D3)} · 4ο ματς {len(D4)} · ελεγχος (Ε → Π, χωρις Ευρωπη μετα) {len(DC)}')
for title, D in (('3ο ΜΑΤΣ = ΕΥΡΩΠΑΙΚΟ (Ε2)', D3), ('4ο ΜΑΤΣ = ΠΡΩΤΑΘΛΗΜΑ (Π2)', D4)):
    print(f'\n{"=" * 120}\n{title}')
    for where, h in (('ΕΝΤΟΣ', True), ('ΕΚΤΟΣ', False)):
        y0 = D[D.home == h]; print(f'  — {where} —'); print(HDR)
        for lab, lo, hi in KB: row(lab, y0[(y0.km >= lo) & (y0.km < hi)] if lo > 0 else y0[y0.km < 1])
print(f'\n{"=" * 120}\nΕΛΕΓΧΟΣ: πρωταθλημα μετα απο ΕΝΑ ευρωπαικο (Ε → Π, χωρις αλλο ευρωπαικο ≤7μ) — ανα χλμ του ευρωπαικου')
for where, h in (('ΕΝΤΟΣ', True), ('ΕΚΤΟΣ', False)):
    y0 = DC[DC.home == h]; print(f'  — {where} —'); print(HDR)
    for lab, lo, hi in (('ευρωπαικο εντος (0 χλμ)', 0, 1), ('<2.000 χλμ', 1, 2000), ('2.000-4.000', 2000, 4000), ('≥4.000', 4000, 1e9)):
        row(lab, y0[(y0.km >= lo) & (y0.km < hi)] if lo > 0 else y0[y0.km < 1])
D3.to_pickle('travel_seq4_E2.pkl'); D4.to_pickle('travel_seq4_P2.pkl')
