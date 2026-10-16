"""travel_fatigue_full.py — 16/10/2026 (Στελιος: «ποσο επηρεαζει ενα μακρινο ταξιδι μια ομαδα, στο ιδιο το ματς και στο ΕΠΟΜΕΝΟ — με ΠΛΗΡΗ δεδομενα·
με νοιαζουν οι ομαδες που ΔΕΝ ειναι συνηθισμενες στα μακρινα ταξιδια, π.χ. οσες πηγαν στην Qarabağ, οχι η ιδια η Qarabağ»).
ΔΕΔΟΜΕΝΑ (συμπληρωμενα 16/10): ημερολογιο = εγχωρια data_* + fixtures_*_2122/2021 (FotMob, οσα ελειπαν) + ευρωπαικα & προκριματικα +
ΕΓΧΩΡΙΑ ΚΥΠΕΛΛΑ (cups_fixtures.json, 15.085 ματς) · γηπεδα venues.json (94% ομαδων) · αγορα: Nowgoal Crown (ευρωπαικα Crown/SBOBET· εγχωρια
CORE7 + οι επιπλεον λιγκες του nowgoal_fetch_extra, με Bet365 οπου λειπει Crown).
ΤΑΞΙΔΙΩΤΗΣ «ΑΣΥΝΗΘΙΣΤΟΣ»: εδρα στη Δυτικη/Κεντρικη Ευρωπη (μηκος −10°…25°, πλατος 36°…62°) — εξω Τουρκια, Ισραηλ, Κυπρος, Καυκασος,
Καζακσταν, Ισλανδια, Αρκτικος. Αποσταση = ευθεια εδρα → ευρωπαικο γηπεδο (~800 χλμ ≈ 1ω πτησης).
(Α) ΙΔΙΟ ΜΑΤΣ (ευρωπαικο εκτος): vs αγορα κλεισιματος — διαφορα, γκολ που βαζει / τρωει, συνολο, xG βαζει/τρωει vs αγορα, τυφλο AH.
(Β) ΕΠΟΜΕΝΟ ΜΑΤΣ (οποιοδηποτε, ≤6 μερες): vs αγορα κλεισιματος (εγχωρια με αποδοσεις) — εντος / εκτος· + ποσα ηταν κυπελλα (χωρις αγορα).
ΕΛΕΓΧΟΣ: ιδιες ομαδες μετα απο ευρωπαικο ΕΝΤΟΣ και μετα απο κοντινο ταξιδι (<1.500).
"""
import sys, os, json, glob
_s = open('ucl_away_streak_deep.py', encoding='utf-8').read()
_s = _s[:_s.index('# ---------------- 3. ΓΡΑΜΜΕΣ ΟΜΑΔΑΣ-ΜΑΤΣ: ΕΥΡΩΠΗ')]
_add_cal = '''
# --- 16/10: ΣΥΜΠΛΗΡΩΜΑ ΗΜΕΡΟΛΟΓΙΟΥ: fixtures_* (σεζον που ελειπαν) + εγχωρια κυπελλα ---
for f in glob.glob('fixtures_*_*.json'):
    lg, sea = f[9:-5].rsplit('_', 1)
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        if mid in G or not m.get('date'): continue
        try: G[mid] = dict(kind='dom', lg=lg, sea=sea, t=pdt(m['date']), h=int(m['home']['id']), a=int(m['away']['id']), hs=m.get('hs'), as_=m.get('as'), rnd=None)
        except Exception: pass
for k, L in json.load(open('cups_fixtures.json', encoding='utf-8')).items():
    for m in L:
        mid = str(m['mid'])
        if mid in G or not m.get('utc'): continue
        sc = str(m.get('score') or '').replace(' ', '').split('-')
        hs, as_ = (int(sc[0]), int(sc[1])) if len(sc) == 2 and sc[0].isdigit() and sc[1].isdigit() else (None, None)
        try: G[mid] = dict(kind='cup', lg=k.rsplit('_', 1)[0], sea=k.rsplit('_', 1)[1], t=pd.Timestamp(m['utc'][:19]), h=int(m['hid']), a=int(m['aid']), hs=hs, as_=as_, rnd=str(m.get('round')))
        except Exception: pass
'''
_o = "V = json.load(open('venues.json', encoding='utf-8'))"
assert _s.count(_o) == 1
_s = _s.replace(_o, _add_cal + _o, 1)
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
# αγορα εγχωριων: ΟΛΑ τα nowgoal_odds εκτος ευρωπαικων/μπασκετ/Βραζιλιας/MLS
skip = ('_UCL', '_UEL', '_UECL', 'Brazil', 'MLS', '_deep')
for f in glob.glob('nowgoal_odds/*.jsonl'):
    b = os.path.basename(f)
    if any(x in b for x in skip) or any(c in b for c in ('EPL', 'LaLiga', 'SerieA', 'Bundesliga.', 'Ligue1', 'PrimeiraLiga', 'Eredivisie')): continue
    if not b[:2].isdigit(): continue
    a_ = load_ah(f, {3: 'Crown', 8: 'Bet365'}); t_ = load_tou(f, {3: 'Crown', 8: 'Bet365'})
    for (mid, bk), v in a_.items(): AHD.setdefault((mid, bk), v)
    for (mid, bk), v in t_.items(): TOUD.setdefault((mid, bk), v)
SEAS = ['2122', '2223', '2324', '2425', '2526']
def zone(t):
    c = LOC.get(t)
    return bool(c and -10 <= c[1] <= 25 and 36 <= c[0] <= 62)
def mk(mid, ko, ah, tou, gd, books):
    for bset in books:
        M = mkt(mid, ko, ah, tou, bset, None, gd)
        if np.isfinite(M['c']): return M
    return None
# ---------------- (Α) ΙΔΙΟ ΜΑΤΣ + (Β) ΕΠΟΜΕΝΟ ----------------
RA, RB = [], []
for mid, x in G.items():
    if x['kind'] != 'eu' or x['sea'] not in SEAS or x['rnd'] == 'final' or x['hs'] is None: continue
    if x['lg'] not in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague', 'ChampionsLeagueQ', 'EuropaLeagueQ', 'ConferenceLeagueQ'): continue
    i = MI.get(mid); gd = x['hs'] - x['as_']; ko = int(x['t'].tz_localize('UTC').timestamp())
    for s, tid, oid in ((1, x['h'], x['a']), (-1, x['a'], x['h'])):
        if not zone(tid): continue
        trip = km(LOC.get(tid), LOC.get(x['h'])) if s == -1 else 0.0
        if s == -1 and (LOC.get(tid) is None or LOC.get(x['h']) is None): continue
        # (Α) ιδιο ματς — μονο ο φιλοξενουμενος
        if s == -1:
            M = mk(mid, ko, TRAJ, TOUE, gd, (('Crown', 'SBOBET'),))
            if M:
                xg = XG.get(mid); tot = x['hs'] + x['as_']
                RA.append(dict(mid=mid, sea=x['sea'], comp=x['lg'], trip=trip, rc=s * (gd - M['c']), rt=tot - M['tc'],
                               xf=(xg[1] - (M['tc'] - M['c']) / 2) if xg else np.nan, xa=(xg[0] - (M['tc'] + M['c']) / 2) if xg else np.nan,
                               roi=M['pa']))
        # (Β) επομενο ματς ≤6 μερες
        L = CAL.get(tid); j = POS.get(tid, {}).get(mid)
        if L is None or j is None or j + 1 >= len(L): continue
        nx = L[j + 1]; gap = (nx[0] - x['t']).total_seconds() / 86400
        if gap > 6 or gap < 1.5: continue
        y = G[nx[1]]
        if y['hs'] is None: continue
        s2 = 1 if y['h'] == tid else -1; gd2 = y['hs'] - y['as_']; ko2 = int(y['t'].tz_localize('UTC').timestamp())
        rec = dict(mid=nx[1], sea=x['sea'], comp=x['lg'], kind=y['kind'], lg=y['lg'], prev_home=(s == 1), trip=trip, gap=gap, nhome=(s2 == 1),
                   gf=y['hs'] if s2 == 1 else y['as_'], ga=y['as_'] if s2 == 1 else y['hs'], s2=s2, gd2=gd2, tot2=y['hs'] + y['as_'], src='AH/OU')
        if y['kind'] == 'dom':
            M2 = mk(nx[1], ko2, AHD, TOUD, gd2, (('Crown',), ('Bet365',)))
            if M2:
                xg2 = XG.get(nx[1])
                rec.update(rc=s2 * (gd2 - M2['c']), rt=y['hs'] + y['as_'] - M2['tc'],
                           xf=((xg2[0] if s2 == 1 else xg2[1]) - (M2['tc'] + s2 * M2['c']) / 2) if xg2 else np.nan,
                           xa=((xg2[1] if s2 == 1 else xg2[0]) - (M2['tc'] - s2 * M2['c']) / 2) if xg2 else np.nan,
                           roi=M2['ph'] if s2 == 1 else M2['pa'])
        RB.append(rec)
A = pd.DataFrame(RA); B = pd.DataFrame(RB)
# 16/10: οπου λειπει χαντικαπ/συνολα → κλεισιμο 1Χ2 (Pinnacle/Bet365/Crown, nowgoal_1x2.jsonl) → αναμενομενα γκολ με αντιστροφη Poisson
# (x12_implied· επικυρωση CORE7: συνολο r 0.95 με σταθερη μετατοπιση −0.16 → +0.16, διαφορα r 0.98). Τυφλο AH δεν υπαρχει για αυτα.
import x12_implied as X12
X12D = {}
if os.path.exists('nowgoal_1x2.jsonl'):
    for l in open('nowgoal_1x2.jsonl', encoding='utf-8'):
        r = json.loads(l)
        if r.get('close') and min(r['close']) > 1: X12D[str(r['mid'])] = r['close']
if 'rc' not in B: B['rc'] = np.nan; B['rt'] = np.nan; B['xf'] = np.nan; B['xa'] = np.nan; B['roi'] = np.nan
for k in B.index[(B.kind == 'dom') & B.rc.isna()]:
    c = X12D.get(str(B.at[k, 'mid']))
    if not c: continue
    h, a = X12.lam_from_1x2(*c); T = h + a + 0.16; s2 = B.at[k, 's2']
    B.at[k, 'rc'] = s2 * (B.at[k, 'gd2'] - (h - a)); B.at[k, 'rt'] = B.at[k, 'tot2'] - T; B.at[k, 'src'] = '1X2'
for Z in (A, B):
    if 'rc' in Z: Z['sf'] = (Z.rt + Z.rc) / 2; Z['sa'] = (Z.rt - Z.rc) / 2
def ms(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return f'{v.mean():+.2f}±{v.std() / np.sqrt(max(len(v), 1)):.2f}' if len(v) > 2 else '   —'
def line(lab, y):
    ss = [s for s in SEAS if (y.sea == s).sum() >= 4]
    print(f'   {lab:36s} {len(y):5d} │ {ms(y.rc):>11s} │ {ms(y.sf):>11s} │ {ms(y.sa):>11s} │ {ms(y.rt):>11s} │ {ms(y.xf):>11s} {ms(y.xa):>11s} │ {100 * np.nanmean(y.roi):+6.1f}% │ ' +
          ' '.join(f'{s[2:]}:{y[y.sea == s].rt.mean():+.2f}' for s in ss))
HDR = (f'   {"":36s} {"n":>5s} │ {"διαφορα−αγ":>11s} │ {"βαζει−αγ":>11s} │ {"τρωει−αγ":>11s} │ {"συνολο−αγ":>11s} │ {"xG βαζει−αγ":>11s} {"xG τρωει−αγ":>11s} │ {"τυφλο AH":>7s} │ ανα σεζον (συνολο−αγ)')
BK = ((0, 1500, '<1.500 χλμ (≤2ω)'), (1500, 2500, '1.500-2.500 (2-3ω)'), (2500, 3500, '2.500-3.500 (3-4.5ω)'), (3500, 99999, '≥3.500 (4.5ω+)'))
print('ΤΑΞΙΔΙ & ΚΟΥΡΑΣΗ — ομαδες Δυτικης/Κεντρικης Ευρωπης («ασυνηθιστες» στα μακρινα ταξιδια) · ευρωπαικα 2122-2526 (+προκριματικα)')
print(f'δεδομενα: ημερολογιο {len(G):,} ματς (κυπελλα {sum(1 for v in G.values() if v["kind"] == "cup"):,}) · γηπεδα {len(LOC):,} ομαδες · '
      f'εγχωρια ματς με αγορα {len({k[0] for k in AHD}):,}')
print(f'\n(Α) ΙΔΙΟ ΜΑΤΣ — ο ταξιδιωτης εκτος στην Ευρωπη · + = περισσοτερα απ οσα περιμενε η αγορα στο κλεισιμο')
print(HDR)
for lo, hi, lab in BK: line(lab, A[(A.trip >= lo) & (A.trip < hi)])
print(f'\n(Β) ΕΠΟΜΕΝΟ ΜΑΤΣ (1.5-6 μερες μετα) — ολα: {len(B):,} · με αγορα (εγχωρια): {B.rc.notna().sum() if "rc" in B else 0:,} · κυπελλα (χωρις αγορα): {int((B.kind == "cup").sum()):,} · ευρωπαικα: {int((B.kind == "eu").sum()):,}')
Bm = B[B.rc.notna()] if 'rc' in B else B.iloc[:0]
for where, m in (('ΕΝΤΟΣ', Bm.nhome), ('ΕΚΤΟΣ', ~Bm.nhome), ('ΟΛΑ', Bm.nhome | ~Bm.nhome)):
    print(f'  — επομενο ματς {where} —'); print(HDR)
    y = Bm[m]
    line('μετα απο ευρωπαικο ΕΝΤΟΣ [ελεγχος]', y[y.prev_home])
    for lo, hi, lab in BK:
        line('μετα απο εκτος ' + lab, y[~y.prev_home & (y.trip >= lo) & (y.trip < hi)])
print('\n  — ΕΛΕΓΧΟΣ ΑΝΤΟΧΗΣ: ιδιο αποτελεσμα ανα πηγη αγορας (AH/OU Crown vs 1Χ2-αντιστροφη) —'); print(HDR)
for src in ('AH/OU', '1X2'):
    y = Bm[Bm.src == src]
    line(f'[{src}] μετα απο ΕΝΤΟΣ', y[y.prev_home]); line(f'[{src}] μετα απο εκτος <1.500', y[~y.prev_home & (y.trip < 1500)])
    line(f'[{src}] μετα απο εκτος 1.500-2.500', y[~y.prev_home & (y.trip >= 1500) & (y.trip < 2500)]); line(f'[{src}] μετα απο εκτος ≥2.500', y[~y.prev_home & (y.trip >= 2500)])
print('\n  — επομενο ματς σε ΚΥΠΕΛΛΟ (χωρις αγορα): μεσα γκολ βαζει / τρωει —')
C = B[B.kind == 'cup']
for lab, m in (('μετα απο ευρωπαικο ΕΝΤΟΣ', C.prev_home), ('μετα απο εκτος <2.500', ~C.prev_home & (C.trip < 2500)), ('μετα απο εκτος ≥2.500', ~C.prev_home & (C.trip >= 2500))):
    z = C[m]; print(f'   {lab:36s} {len(z):5d} │ βαζει {z.gf.mean():.2f} · τρωει {z.ga.mean():.2f}')
y = Bm[~Bm.prev_home & (Bm.trip >= 2500)]
print('\n  μακρινα (≥2.500) πριν απο εγχωριο με αγορα — ανα λιγκα του επομενου: ' + ', '.join(f'{k} {v}' for k, v in y.lg.value_counts().head(20).items()))
A.to_pickle('travel_fatigue_A.pkl'); B.to_pickle('travel_fatigue_B.pkl')
