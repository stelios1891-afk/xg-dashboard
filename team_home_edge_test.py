# -*- coding: utf-8 -*-
"""team_home_edge_test.py — 19/10/2026 (Στελιος: «σε συγκεκριμενες ομαδες — Μποντο, Καραμπαγκ, Γαλατα, Σαμπαχ, Καιρατ κ.α. — η κουραση του ταξιδιου,
οι καιρικες συνθηκες κτλπ ΔΕΝ αντικατοπτριζονται απο το κοινο πλεονεκτημα εδρας· δεν ειχαμε βρει κατι, ξαναδες το πιο επιμονα»).
Ευρωπαικα 2022-26, σημερινη αλυσιδα (harness uel_all_mechanisms: λ ματς, αγορα κλεισιματος Crown/SBOBET), xG FotMob (data_Europe).
ΜΕΤΡΟ ανα ομαδα: «εξτρα εδρα» = (πραγματικο − μοντελο) στα ΕΝΤΟΣ μειον (πραγματικο − μοντελο) στα ΕΚΤΟΣ — σε ΓΚΟΛ διαφορας και σε xG διαφορας.
  Ετσι η γενικη δυναμη της ομαδας (που μπορει να ειναι λαθος) αφαιρειται· μενει μονο το «εξτρα» της εδρας της.
ΟΜΑΔΕΣ ΟΡΙΣΜΕΝΕΣ ΠΡΙΝ (ονοματα FotMob):
  ΑΝΑΤΟΛΙΚΕΣ/ΜΑΚΡΙΝΕΣ: Qarabağ, Sabah, Kairat, Astana, Galatasaray, Fenerbahçe, Beşiktaş, Trabzonspor, Başakşehir
  ΒΟΡΕΙΕΣ/ΚΡΥΕΣ: Bodø/Glimt, Molde, Brann, Rosenborg, Malmö FF, BK Häcken, Djurgården, IF Elfsborg, FC København, FC Midtjylland, HJK, KuPS
  ΚΑΥΤΕΣ ΕΔΡΕΣ: FK Crvena Zvezda, Partizan, PAOK, Olympiacos, Panathinaikos, AEK Athens, Ferencváros, Legia Warszawa, Celtic, Rangers
ΚΡΙΤΗΡΙΟ (γραφτηκε πριν): μια ομαδα-ομαδα εχει πραγματικο εξτρα πλεονεκτημα αν (1) εξτρα εδρα σε xG > 0 με t ≥ 2, (2) θετικο και στα δυο μισα
  (2022-24 / 2024-26), (3) η αγορα ΔΕΝ το εχει ηδη: «πραγματικο − αγορα» στα εντος > 0 (t ≥ 1.5), (4) χαντικαπ γηπεδουχου στο κλεισιμο θετικο.
+ ΑΠΟΣΤΑΣΗ ΤΑΞΙΔΙΟΥ του φιλοξενουμενου (ευθεια γηπεδο→γηπεδο): ζωνες χλμ — residual γηπεδουχου σε γκολ/xG και κλεισιμο."""
import sys, json, glob, math
_s = open('uel_all_mechanisms.py', encoding='utf-8').read()
exec(_s[:_s.index("x = A[A.comp == 'EuropaLeague']")])
sys.stdout.reconfigure(encoding='utf-8')
INFO = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        sh = m.get('shots') or []; hid = int(m['home']['id'])
        xg = (sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) == hid), sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) != hid)) if sh else None
        INFO[str(mid)] = (m['home']['name'], m['away']['name'], hid, int(m['away']['id']), xg)
V = json.load(open('venues.json', encoding='utf-8'))
def km(a, b):
    va, vb = V.get(str(a)), V.get(str(b))
    if not va or not vb: return np.nan
    p1, p2 = math.radians(va['lat']), math.radians(vb['lat']); dl = math.radians(vb['lon'] - va['lon'])
    return 6371 * math.acos(min(1, max(-1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl))))
R = []
for r in A.itertuples():
    i = int(r.i); mid = str(MIDS[i]); inf = INFO.get(mid)
    if not inf: continue
    h, a, hid, aid, xg = inf; gd = GD[i]; mdiff = r.lh - r.la
    mk = []
    for bk in ('Crown', 'SBOBET'):
        c = snapT(mid, bk, 0)
        if c: mk.append((implied_margin(i, *c), c, bk))
    mkt = np.mean([z[0] for z in mk]) if mk else np.nan
    ah = np.nan
    if mk:
        L, oh, oa = mk[0][1]; ah = picks.settle(gd, 1, L, oh)
    trav = km(aid, hid)
    for side, tm in ((1, h), (-1, a)):
        R.append(dict(team=tm, home=side == 1, sea=r.sea, comp=r.comp, rd=side * (gd - mdiff),
                      rx=side * ((xg[0] - xg[1]) - mdiff) if xg else np.nan,
                      rm=side * (gd - mkt) if np.isfinite(mkt) else np.nan, mm=side * (mkt - mdiff) if np.isfinite(mkt) else np.nan,
                      ah=ah if side == 1 else np.nan, trav=trav if side == 1 else np.nan))
D = pd.DataFrame(R)
def t(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return (v.mean() / (v.std() / np.sqrt(len(v)))) if len(v) > 3 and v.std() > 0 else np.nan
def extra(y, col):
    hm, aw = y[y.home][col].dropna(), y[~y.home][col].dropna()
    if len(hm) < 3 or len(aw) < 3: return np.nan, np.nan
    d = hm.mean() - aw.mean(); se = math.sqrt(hm.var() / len(hm) + aw.var() / len(aw)); return d, d / se if se > 0 else np.nan
GROUPS = {
 'ΑΝΑΤΟΛΙΚΕΣ/ΜΑΚΡΙΝΕΣ': ['Qarabağ', 'Qarabag', 'Qarabağ FK', 'Sabah FK', 'Sabah', 'Kairat Almaty', 'Kairat', 'FC Astana', 'Astana', 'Galatasaray', 'Fenerbahçe', 'Beşiktaş', 'Trabzonspor', 'Başakşehir'],
 'ΒΟΡΕΙΕΣ/ΚΡΥΕΣ': ['Bodø/Glimt', 'Molde', 'Brann', 'Rosenborg', 'Malmö FF', 'BK Häcken', 'Djurgården', 'IF Elfsborg', 'FC København', 'FC Midtjylland', 'HJK', 'KuPS'],
 'ΚΑΥΤΕΣ ΕΔΡΕΣ': ['FK Crvena Zvezda', 'Crvena Zvezda', 'Partizan', 'PAOK', 'Olympiacos', 'Panathinaikos', 'AEK Athens', 'Ferencváros', 'Legia Warszawa', 'Celtic', 'Rangers']}
ALLG = sum(GROUPS.values(), [])
H1, H2 = ['2223', '2324'], ['2425', '2526']
print('ΕΞΤΡΑ ΕΔΡΑ = (πραγμ − μοντελο) ΕΝΤΟΣ μειον (πραγμ − μοντελο) ΕΚΤΟΣ · σε γκολ διαφορας και xG διαφορας ανα ματς · + = η εδρα τους αξιζει παραπανω')
print(f'   {"ομαδα":28s} {"εντ/εκτ":>7s} │ {"εξτρα γκολ":>10s} {"t":>5s} │ {"εξτρα xG":>9s} {"t":>5s} │ {"xG 22-24":>8s} {"xG 24-26":>8s} │ {"αγορα: εξτρα που δινει":>22s} {"γκολ−αγορα εντος":>16s} {"t":>5s} │ {"AH γηπ. κλεισ.":>14s}')
def line(lab, y):
    nh, na = int(y.home.sum()), int((~y.home).sum())
    eg, tg = extra(y, 'rd'); ex, tx = extra(y, 'rx'); e1, _ = extra(y[y.sea.isin(H1)], 'rx'); e2, _ = extra(y[y.sea.isin(H2)], 'rx')
    em, _ = extra(y, 'mm'); hm = y[y.home].rm.dropna(); ah = y[y.home].ah.dropna()
    print(f'   {lab:28s} {nh:3d}/{na:<3d} │ {eg:+10.2f} {tg:5.1f} │ {ex:+9.2f} {tx:5.1f} │ {e1:+8.2f} {e2:+8.2f} │ {em:+22.2f} {hm.mean():+16.2f} {t(hm):5.1f} │ '
          f'{100 * ah.mean():+8.1f}% ({len(ah)})')
    return dict(ex=ex, tx=tx, e1=e1, e2=e2, rm=hm.mean(), trm=t(hm), ah=ah.mean())
print('   — ΟΜΑΔΕΣ ΟΡΙΣΜΕΝΕΣ ΠΡΙΝ —')
res = {}
for g, names in GROUPS.items(): res[g] = line(g, D[D.team.isin(names)])
line('ΟΛΕΣ ΟΙ ΑΛΛΕΣ (ελεγχος)', D[~D.team.isin(ALLG)])
print('\n   — ΑΝΑ ΟΜΑΔΑ (≥8 εντος & ≥8 εκτος), ταξινομηση με εξτρα xG —')
tm = []
for team, y in D.groupby('team'):
    if y.home.sum() >= 8 and (~y.home).sum() >= 8:
        ex, tx = extra(y, 'rx'); tm.append((ex, team))
tm.sort(reverse=True)
for ex, team in tm[:15]: line(('* ' if team in ALLG else '  ') + team, D[D.team == team])
print('   ...')
for ex, team in tm[-6:]: line(('* ' if team in ALLG else '  ') + team, D[D.team == team])
# επιμονη: συσχετιση εξτρα xG 22-24 vs 24-26 ανα ομαδα
pr = []
for team, y in D.groupby('team'):
    a1, _ = extra(y[y.sea.isin(H1)], 'rx'); a2, _ = extra(y[y.sea.isin(H2)], 'rx')
    if np.isfinite(a1) and np.isfinite(a2) and y[y.sea.isin(H1)].home.sum() >= 4 and y[y.sea.isin(H2)].home.sum() >= 4: pr.append((a1, a2))
pr = np.array(pr)
print(f'\n   ΕΠΙΜΟΝΗ (ολες οι ομαδες με ≥4 εντος σε καθε μισο, n={len(pr)}): συσχετιση εξτρα-xG 2022-24 με 2024-26 = {np.corrcoef(pr[:, 0], pr[:, 1])[0, 1]:+.2f}')
print('\n   — ΑΠΟΣΤΑΣΗ ΤΑΞΙΔΙΟΥ ΦΙΛΟΞΕΝΟΥΜΕΝΟΥ (residual γηπεδουχου) —')
H = D[D.home & D.trav.notna()]
for lab, lo, hi in (('<1.000 χλμ', 0, 1000), ('1.000-2.000', 1000, 2000), ('2.000-3.000', 2000, 3000), ('≥3.000', 3000, 1e9)):
    y = H[(H.trav >= lo) & (H.trav < hi)]
    print(f'   {lab:14s} {len(y):4d} ματς │ γκολ−μοντ {y.rd.mean():+.2f} (t {t(y.rd):.1f}) · xG−μοντ {y.rx.mean():+.2f} (t {t(y.rx):.1f}) · γκολ−αγορα {y.rm.mean():+.2f} · AH γηπ. {100 * y.ah.mean():+.1f}%')
print('\nΚΡΙΤΗΡΙΟ ανα ομαδα-ομαδα: (1) εξτρα xG>0 t≥2 · (2) θετικο και στα 2 μισα · (3) γκολ−αγορα εντος >0 t≥1.5 · (4) AH γηπ. >0')
for g, r in res.items():
    ok = [r['ex'] > 0 and r['tx'] >= 2, r['e1'] > 0 and r['e2'] > 0, r['rm'] > 0 and r['trm'] >= 1.5, r['ah'] > 0]
    print(f'   {g:22s} ' + ' · '.join(f'({k + 1}) {"✓" if v else "✗"}' for k, v in enumerate(ok)) + f' → {"ΠΕΡΝΑ" if all(ok) else "δεν περνα"}')
