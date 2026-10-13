"""compression_battery.py — 13/10/2026 (Στελιος: «τρεξε οτι τεστ θεωρεις οτι θα βοηθησει στην αναλυση»).
ΣΥΜΠΙΕΣΗ ΣΤΑ ΕΥΡΩΠΑΪΚΑ: στο UEL/UECL οι αποστασεις μεταξυ ομαδων ειναι μικροτερες απ οσο λεει το μοντελο (team_strength_vs_same_opp).
Μετρο: ΚΛΙΣΗ του λαθους ως προς τη διαφορα της προβλεψης, απο τη σκοπια του γηπεδουχου · 0 = σωστη κλιμακα · −0.30 = η διαφορα ειναι
~30% μεγαλυτερη απ οσο πρεπει (συμπιεση) · + = μικροτερη (το αντιθετο, οπως UCL). Ιδιο μετρο για την ΑΓΟΡΑ (κλεισιμο Crown/SBOBET).
  Τ1 η αγορα το ξερει; (κλιση αγορας) · Τ2 καθε σεζον; · Τ3 φαση: λιγκα/ομιλοι vs νοκ-αουτ · πρωτες vs τελευταιες αγωνιστικες (νεα μορφη)
  Τ4 ΣΚΟΡ: υπαρχει ΚΑΙ οσο το σκορ ειναι ισο (xG ανα 90' σε ισοπαλια) ή μονο οταν καποιος προηγειται; · 1ο vs 2ο ημιχρονο
  Τ5 εδρα: ο δυνατος εντος vs εκτος · λιγκα του αδυναμου (top-5 vs αλλες) · Τ6 κατηγορια Α / Β
Διαγνωστικο — δεν αλλαζει τιποτα.
"""
import sys
exec(open('ucl_nonfm_teams.py', encoding='utf-8').read().split('# ===== 1 =====')[0])
NL = chr(10)
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
RND = {}
for f in ('europe_fixtures.json',):
    for k, lst in json.load(open(f, encoding='utf-8')).items():
        for m in lst: RND[str(m['mid'])] = m.get('round')
rows = []
for i, x in S.groupby('i'):
    h = x[x.venue == 'εντος'].iloc[0]; a = x[x.venue == 'εκτος'].iloc[0]
    j = VI[str(MIDS[i])]; mid = str(MIDS[i]); m = EUM.get(mid)
    # ---- κατασταση σκορ απο τα σουτ: xG οσο ισοπαλια / λεπτα ισοπαλιας ----
    lvl = None
    if m and m.get('shots'):
        hid = int(m['home']['id']); sh = sorted([s for s in m['shots'] if s.get('xg') is not None], key=lambda s: s.get('min') or 0)
        gh_ = ga_ = 0; t0 = 0; mins_lvl = 0.0; xl_h = xl_a = 0.0; x1h = x1a = 0.0
        for s in sh:
            mn = min(s.get('min') or 0, 95)
            if gh_ == ga_: mins_lvl += max(mn - t0, 0)
            t0 = max(t0, mn)
            if gh_ == ga_:
                if int(s['tid']) == hid: xl_h += s['xg']
                else: xl_a += s['xg']
            if mn <= 45:
                if int(s['tid']) == hid: x1h += s['xg']
                else: x1a += s['xg']
            if s.get('goal'):
                if int(s['tid']) == hid: gh_ += 1
                else: ga_ += 1
        if gh_ == ga_: mins_lvl += max(95 - t0, 0)
        if gh_ == int(m['hs']) and ga_ == int(m['as']) and mins_lvl >= 20:
            lvl = (xl_h * 90 / mins_lvl, xl_a * 90 / mins_lvl, x1h, x1a)
    rows.append(dict(i=i, comp=h.comp, cat=h['cat'], sea=h.sea, ph=h.ph, rnd=RND.get(mid), m=h.lam - a.lam, km=h.k - a.k, y=h.g - a.g, yx=h.xg - a.xg,
                     lh=h.lam, la=a.lam, lgh=V6['lg_h'][j], lga=V6['lg_a'][j],
                     lvl=(lvl[0] - lvl[1]) if lvl else np.nan, h1=(lvl[2] - lvl[3]) if lvl else np.nan))
M = pd.DataFrame(rows); M = M[M.km.notna()]
def slope(x, ycol, pcol='m'):
    if len(x) < 25: return None
    p = x[pcol].values; e = x[ycol].values - p
    if ycol == 'h1': e = x[ycol].values - p * 0.45                       # 1ο ημιχρονο ≈ 45% της προβλεψης
    b = np.polyfit(p, e, 1)[0]; r = e - np.polyval(np.polyfit(p, e, 1), p)
    se = np.sqrt((r ** 2).sum() / (len(p) - 2) / ((p - p.mean()) ** 2).sum()); return b, se
def fmt(v): return '   —   ' if v is None else f'{v[0]:+.2f}±{v[1]:.2f}'
def line(x, lab):
    a = slope(x, 'y'); b = slope(x, 'yx'); c = slope(x, 'y', 'km')
    return f'   {lab:34s} n{len(x):4d} · ΜΟΝΤΕΛΟ γκολ {fmt(a)} · xG {fmt(b)} · ΑΓΟΡΑ γκολ {fmt(c)}'
U = M[M.comp.isin(['UEL', 'UECL'])]
print('ΣΥΜΠΙΕΣΗ (κλιση λαθους · 0 = σωστο · αρνητικο = το μοντελο βλεπει μεγαλυτερες αποστασεις απ οσες υπαρχουν)')
print(NL + 'Τ1. ΑΝΑ ΔΙΟΡΓΑΝΩΣΗ — και η ΑΓΟΡΑ το ιδιο μετρο')
for cm in ('UCL', 'UEL', 'UECL'): print(line(M[M.comp == cm], cm))
print(line(U, 'UEL + UECL'))
print(NL + 'Τ2. ΑΝΑ ΣΕΖΟΝ (UEL + UECL)')
for s_, x in U.groupby('sea'): print(line(x, f'σεζον {s_}'))
print(NL + 'Τ3. ΦΑΣΗ (UEL + UECL)')
for ph, x in U.groupby('ph'): print(line(x, f'φαση {ph}'))
N = U[U.sea.isin(['2425', '2526']) & (U.ph == 'league')].copy(); N['r'] = pd.to_numeric(N.rnd, errors='coerce')
print(line(N[N.r <= 4], 'νεα μορφη, αγωνιστικες 1-4'))
print(line(N[N.r >= 5], 'νεα μορφη, αγωνιστικες 5-8'))
print(NL + 'Τ4. ΣΚΟΡ — υπαρχει ΚΑΙ σε ισοπαλια; (xG ανα 90 λεπτα ΟΣΟ το σκορ ειναι ισο) · και 1ο ημιχρονο (xG)')
for cm, x in (('UEL + UECL', U), ('UCL', M[M.comp == 'UCL'])):
    z = x.dropna(subset=['lvl'])
    a = slope(z, 'lvl'); b = slope(z, 'yx'); c = slope(z, 'h1')
    print(f'   {cm:12s} n{len(z):4d} · xG ΟΛΟΥ του ματς {fmt(b)} · xG/90 ΣΕ ΙΣΟΠΑΛΙΑ {fmt(a)} · xG 1ου ημιχρονου {fmt(c)}')
print(NL + 'Τ5. ΕΔΡΑ ΤΟΥ ΦΑΒΟΡΙ & ΛΙΓΚΑ ΤΟΥ ΑΟΥΤΣΑΙΝΤΕΡ (UEL + UECL)')
print(line(U[U.m > 0], 'φαβορι μοντελου ΕΝΤΟΣ'))
print(line(U[U.m < 0], 'φαβορι μοντελου ΕΚΤΟΣ'))
dog_lg = np.where(U.m >= 0, U.lga, U.lgh)
print(line(U[np.isin(dog_lg, list(TOP5))], 'αουτσαιντερ απο top-5'))
print(line(U[~np.isin(dog_lg, list(TOP5))], 'αουτσαιντερ απο αλλη λιγκα'))
fav_lg = np.where(U.m >= 0, U.lgh, U.lga)
print(line(U[np.isin(fav_lg, list(TOP5))], 'φαβορι απο top-5'))
print(line(U[~np.isin(fav_lg, list(TOP5))], 'φαβορι απο αλλη λιγκα'))
print(NL + 'Τ6. ΚΑΤΗΓΟΡΙΑ (UEL + UECL)')
for c, x in U.groupby('cat'): print(line(x, f'κατηγορια {c}'))
M.to_pickle('compression_battery_rows.pkl')
