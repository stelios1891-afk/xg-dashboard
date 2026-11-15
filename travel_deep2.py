# -*- coding: utf-8 -*-
"""travel_deep2.py — 18/10/2026 (Στελιος: «το χαντικαπ μπορει να μη βγαινει γιατι παιζουμε τυφλα — δες ποτε αρεσει στο ΜΟΝΤΕΛΟ η κοντρα·
κοιτα και ΝΩΡΙΤΕΡΑ απο το κλεισιμο· ισως τα νουμερα τα χαλανε Μπαρτσα/Ρεαλ/Μπαγερν και οχι οι πιο "γηινες" ομαδες· και ποδοσφαιρικα:
οταν προηγηθει η κουρασμενη ομαδα θα ριξει τον ρυθμο»).
Ιδιο ημερολογιο/αγορα/ταξιδιωτες με travel_fatigue_full (ομαδες Δυτ./Κεντρ. Ευρωπης, 2122-2526).
ΜΟΤΙΒΟ 1 = Ευρωπη → πρωταθλημα (1.5-6μ), χωρις αλλο ευρωπαικο ≤7μ μετα · ΜΟΤΙΒΟ 2 = Ευρωπη → πρωταθλημα → Ευρωπη (≤5μ).
ΤΑΞΙΔΙ = χλμ του ευρωπαικου (0 = ευρωπαικο εντος = ΕΛΕΓΧΟΣ) · ζωνες 0 / <1.500 / ≥1.500 / ≥2.500.
ΚΑΤΗΓΟΡΙΑ ΟΜΑΔΑΣ (απο την ΑΓΟΡΑ, ιδια σεζον): μεση υπεροχη κλεισιματος της ομαδας στα ματς πρωταθληματος — «μεγαλη» ≥1.2 γκολ
  (Μπαγερν, Μπαρτσα, Ρεαλ, Σιτι, Παρι…) · «δυνατη» 0.6-1.2 · «γηινη» <0.6.
ΤΙΜΕΣ (Crown, αλλιως Bet365): ΑΝΟΙΓΜΑ · ΜΕΤΑ ΤΟ ΕΥΡΩΠΑΙΚΟ (σεντρα+2ω, η πρωτη στιγμη που ξερεις το ταξιδι/αποτελεσμα) · ΚΛΕΙΣΙΜΟ.
  UNDER (με τεταρτα) και ΚΟΝΤΡΑ στην ομαδα της Ευρωπης (ασιατικο χαντικαπ).
ΜΟΝΤΕΛΟ (μονο CORE7, md714_diag_preds = live μηχανη, 2223-2526): «του αρεσει η κοντρα» = υπεροχη μοντελου για την ομαδα της Ευρωπης
  ≥0.20 γκολ ΚΑΤΩ απο την αγορα στην ιδια τιμη · «του αρεσει το under» = συνολο μοντελου ≥0.20 κατω.
ΡΥΘΜΟΣ (σουτ FotMob με λεπτο): οταν η ομαδα της Ευρωπης ΠΡΟΗΓΕΙΤΑΙ — xG/90 και των δυο ομαδων ΜΕΤΑ το γκολ vs ΠΡΙΝ, και
  xG/90 της ιδιας οταν προηγειται. Συγκριση με ΕΛΕΓΧΟ (ευρωπαικο εντος).
Εξοδος: travel_deep2_out.txt"""
import sys, os, json
_s = open('travel_fatigue_full.py', encoding='utf-8').read()
_s = _s[:_s.index('# ---------------- (Α) ΙΔΙΟ ΜΑΤΣ + (Β) ΕΠΟΜΕΝΟ ----------------')]
_SQ = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _SQ
sys.stdout.reconfigure(encoding='utf-8')
import glob
EUL = ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague', 'ChampionsLeagueQ', 'EuropaLeagueQ', 'ConferenceLeagueQ')

def seq(D, mid, ko):
    for bk in ('Crown', 'Bet365'):
        s_ = [r_ for r_ in (D.get((mid, bk)) or []) if r_[0] < ko]
        if s_: return s_
    return None
def at(s_, t):
    pr = [r_ for r_ in s_ if r_[0] <= t]; return pr[-1] if pr else None
def und_set(r_, tot):
    L, u = r_[1], r_[3]; parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]
    return sum(((u - 1) if tot < x_ else (0 if tot == x_ else -1)) for x_ in parts) / len(parts)
def opp_set(r_, gd2, s2):
    return picks.settle(gd2, -s2, (-r_[1] if s2 == 1 else r_[1]), (r_[3] if s2 == 1 else r_[2]))

# ---- ΚΑΤΗΓΟΡΙΑ ΟΜΑΔΑΣ: μεση υπεροχη κλεισιματος στα ματς πρωταθληματος (ιδια σεζον) ----
SUP = {}
for mid, y in G.items():
    if y['kind'] != 'dom' or y['hs'] is None or y['sea'] not in SEAS: continue
    ko = int(y['t'].tz_localize('UTC').timestamp())
    M = mk(mid, ko, AHD, TOUD, y['hs'] - y['as_'], (('Crown',), ('Bet365',)))
    if not M: continue
    SUP.setdefault((y['h'], y['sea']), []).append(M['c']); SUP.setdefault((y['a'], y['sea']), []).append(-M['c'])
SUPM = {k: np.mean(v) for k, v in SUP.items() if len(v) >= 8}
def tier(tid, sea):
    v = SUPM.get((tid, sea))
    return None if v is None else ('μεγαλη' if v >= 1.2 else 'δυνατη' if v >= 0.6 else 'γηινη')

# ---- ΜΟΝΤΕΛΟ (CORE7) ----
MP = pd.read_pickle('md714_diag_preds.pkl'); MOD = {str(r.mid): (r.xg_h, r.xg_a) for r in MP.itertuples()}

# ---- ΣΟΥΤ (λεπτο, xG, γκολ) για τον ρυθμο ----
SH = {}
for f in glob.glob('data_*_2[12345]2[23456].json'):
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    if not isinstance(d, dict): continue
    for mid, m in d.items():
        if isinstance(m, dict) and m.get('shots'): SH[str(mid)] = m['shots']
def tempo(mid, tid, hs_id):
    """οταν η tid προηγηθει (πρωτη φορα): xG/90 και των δυο πριν/μετα, xG/90 της tid μετα · None αν δεν προηγηθηκε ποτε"""
    sh = SH.get(str(mid))
    if not sh: return None
    sh = sorted(sh, key=lambda z: z.get('min') or 0); sc = {True: 0, False: 0}; tl = None
    for z in sh:
        if z.get('goal'):
            sc[z['tid'] == tid] += 1
            if sc[True] > sc[False] and tl is None: tl = z.get('min') or 0
    if tl is None or tl >= 85 or tl < 5: return None
    pre = sum(z['xg'] for z in sh if (z.get('min') or 0) <= tl); post = sum(z['xg'] for z in sh if (z.get('min') or 0) > tl)
    own = sum(z['xg'] for z in sh if (z.get('min') or 0) > tl and z['tid'] == tid)
    return dict(pre90=90 * pre / tl, post90=90 * post / (95 - tl), own90=90 * own / (95 - tl), opp90=90 * (post - own) / (95 - tl))

R = []
for tid, L in CAL.items():
    if not zone(tid): continue
    for j in range(len(L) - 1):
        e, p = L[j], L[j + 1]
        x = G[e[1]]
        if x['kind'] != 'eu' or x['lg'] not in EUL or x['sea'] not in SEAS or x['hs'] is None: continue
        g1 = (p[0] - e[0]).total_seconds() / 86400
        if p[4] != 'dom' or not (1.5 <= g1 <= 6): continue
        nxt = next(((q[0] - p[0]).total_seconds() / 86400 for q in L[j + 2:] if q[4] == 'eu'), 99)
        pat = 2 if nxt <= 5 else (1 if nxt > 7 else None)
        if pat is None: continue
        away = x['a'] == tid
        if away and (LOC.get(tid) is None or LOC.get(x['h']) is None): continue
        trip = km(LOC.get(tid), LOC.get(x['h'])) if away else 0.0
        y = G[p[1]]
        if y['hs'] is None: continue
        s2 = 1 if y['h'] == tid else -1; gd2 = y['hs'] - y['as_']; tot = y['hs'] + y['as_']
        ko = int(x['t'].tz_localize('UTC').timestamp()); ko2 = int(y['t'].tz_localize('UTC').timestamp())
        sa_, so_ = seq(AHD, p[1], ko2), seq(TOUD, p[1], ko2)
        if not sa_ or not so_: continue
        rec = dict(sea=x['sea'], pat=pat, trip=trip, home=(s2 == 1), tier=tier(tid, x['sea']), tot=tot)
        for lab, t in (('open', None), ('eu', ko + 7200), ('close', ko2)):
            ra = sa_[0] if t is None else at(sa_, t); ro = so_[0] if t is None else at(so_, t)
            if ra is None or ro is None: rec['u_' + lab] = rec['k_' + lab] = np.nan; continue
            T = mtot(*ro[1:]); c = msup(ra[1], ra[2], ra[3], T)
            rec['u_' + lab] = und_set(ro, tot); rec['k_' + lab] = opp_set(ra, gd2, s2)
            rec['T_' + lab] = T; rec['c_' + lab] = s2 * c
            mp = MOD.get(str(p[1]))
            if mp:
                rec['mdiff_' + lab] = s2 * (mp[0] - mp[1]) - s2 * c
                rec['mtot_' + lab] = mp[0] + mp[1] - T
        rec['rt'] = tot - rec.get('T_close', np.nan); rec['rc'] = s2 * gd2 - rec.get('c_close', np.nan)
        tp = tempo(p[1], tid, y['h'])
        if tp: rec.update(tp)
        R.append(rec)
D = pd.DataFrame(R)
D['zone'] = np.select([D.trip < 1, D.trip < 1500, D.trip < 2500], ['0 (εντος)', '<1.500', '1.500-2.500'], '≥2.500')
print(f'γραμμες: {len(D)} · μοτιβο 1 {int((D.pat == 1).sum())} · μοτιβο 2 {int((D.pat == 2).sum())} · με μοντελο {int(D.mdiff_close.notna().sum())} · '
      f'με ρυθμο {int(D.pre90.notna().sum())} · χωρις κατηγορια {int(D.tier.isna().sum())}')

def roi(v):
    v = pd.Series(v).dropna(); return f'{100 * v.mean():+6.1f}% ({len(v):3d})' if len(v) >= 8 else f'{"—":>7s} ({len(v):3d})'
def ms(v):
    v = pd.Series(v).dropna(); return f'{v.mean():+.2f}' if len(v) >= 8 else '  —'
H = (f'   {"":26s} {"n":>4s} │ {"γκολ−αγ":>7s} │ {"UNDER ανοιγμα":>14s} {"μετα Ευρωπη":>14s} {"κλεισιμο":>14s} │ '
     f'{"ΚΟΝΤΡΑ ανοιγμα":>14s} {"μετα Ευρωπη":>14s} {"κλεισιμο":>14s} │ {"διαφ−αγ":>7s}')
def row(lab, y):
    print(f'   {lab:26s} {len(y):4d} │ {ms(y.rt):>7s} │ {roi(y.u_open):>14s} {roi(y.u_eu):>14s} {roi(y.u_close):>14s} │ '
          f'{roi(y.k_open):>14s} {roi(y.k_eu):>14s} {roi(y.k_close):>14s} │ {ms(y.rc):>7s}')
ZN = ('0 (εντος)', '<1.500', '1.500-2.500', '≥2.500')
for pat in (1, 2):
    P = D[D.pat == pat]
    print(f'\n{"=" * 160}\nΜΟΤΙΒΟ {pat} — ' + ('Ευρωπη → πρωταθλημα (χωρις Ευρωπη μετα)' if pat == 1 else 'Ευρωπη → πρωταθλημα → Ευρωπη') +
          ' · «γκολ−αγ» = πραγματικα γκολ − αγορα κλεισιματος · «διαφ−αγ» = διαφορα τερματων της ομαδας της Ευρωπης − αγορα')
    for where, h in (('ΕΝΤΟΣ', True), ('ΕΚΤΟΣ', False)):
        print(f'\n  — ματς πρωταθληματος {where} —\n{H}')
        for z in ZN: row(z, P[(P.home == h) & (P.zone == z)])
        print('   · μακρινο (≥1.500) ανα κατηγορια ομαδας:')
        for t in ('μεγαλη', 'δυνατη', 'γηινη'): row(f'  {t}', P[(P.home == h) & (P.trip >= 1500) & (P.tier == t)])
        print('   · ελεγχος (εντος Ευρωπη) ανα κατηγορια:')
        for t in ('μεγαλη', 'δυνατη', 'γηινη'): row(f'  {t}', P[(P.home == h) & (P.trip < 1) & (P.tier == t)])
print(f'\n{"=" * 160}\nΜΟΝΤΕΛΟ (μονο CORE7, 2223-2526) — μοτιβα 1+2 μαζι, εντος+εκτος · τιμη «μετα το ευρωπαικο» και κλεισιμο')
M_ = D[D.mdiff_eu.notna()]
for lab, y in (('ΟΛΑ με μοντελο', M_), ('  ταξιδι ≥1.500', M_[M_.trip >= 1500]), ('  εντος Ευρωπη (ελεγχος)', M_[M_.trip < 1])):
    print(f'   {lab}: n {len(y)}')
    for zl, yy in (('    του αρεσει η ΚΟΝΤΡΑ (≥0.20)', y[y.mdiff_eu <= -0.2]), ('    ΔΕΝ του αρεσει η κοντρα', y[y.mdiff_eu > -0.2])):
        print(f'{zl:40s} n {len(yy):3d} · κοντρα μετα Ευρωπη {roi(yy.k_eu)} · κλεισιμο {roi(yy.k_close)}')
    for zl, yy in (('    του αρεσει το UNDER (≥0.20)', y[y.mtot_eu <= -0.2]), ('    ΔΕΝ του αρεσει το under', y[y.mtot_eu > -0.2])):
        print(f'{zl:40s} n {len(yy):3d} · under μετα Ευρωπη {roi(yy.u_eu)} · κλεισιμο {roi(yy.u_close)}')
print(f'\n{"=" * 160}\nΡΥΘΜΟΣ: ματς οπου η ομαδα της Ευρωπης ΠΡΟΗΓΗΘΗΚΕ (5′-85′) · xG/90 · μοτιβα 1+2 μαζι')
print(f'   {"":26s} {"n":>4s} │ {"ολο το ματς πριν το γκολ":>24s} {"μετα το γκολ (και οι 2)":>24s} {"μετα/πριν":>9s} │ {"η ιδια μετα":>11s} {"αντιπαλος μετα":>14s}')
T_ = D[D.pre90.notna()]
for lab, y in [(z, T_[T_.zone == z]) for z in ZN] + [('≥1.500 γηινη', T_[(T_.trip >= 1500) & (T_.tier == 'γηινη')]),
                                                    ('≥1.500 μεγαλη/δυνατη', T_[(T_.trip >= 1500) & (T_.tier != 'γηινη')])]:
    if len(y) < 8: print(f'   {lab:26s} {len(y):4d} │ λιγα'); continue
    print(f'   {lab:26s} {len(y):4d} │ {y.pre90.mean():24.2f} {y.post90.mean():24.2f} {y.post90.mean() / y.pre90.mean():9.2f} │ {y.own90.mean():11.2f} {y.opp90.mean():14.2f}')
D.to_pickle('travel_deep2.pkl')
