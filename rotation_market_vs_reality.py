"""rotation_market_vs_reality.py — 14/10/2026 (Στελιος: «δεν ειμαι σιγουρος οτι η αγορα ειναι σωστη — για τις ομαδες που κανουν rotation,
τι προεβλεψε η αγορα και τι εγινε στην πραγματικοτητα»).
Ευρωπαικα 4 σεζον (κυριως Europa League, + Conference & Champions League για συγκριση). Για ΚΑΘΕ ομαδα με γνωστη ενδεκαδα (ποσοστο = αξια βασικων /
διαμεσος 5 τελευταιων εγχωριων, οπως uel_lineup_rule_test), απο τη σκοπια της ομαδας:
  ΑΓΟΡΑ = διαφορα γκολ που δικαιολογει η τιμη χαντικαπ 1ω πριν (≈ οταν βγαινει η ενδεκαδα) και στο κλεισιμο (Crown, αλλιως SBOBET)
  ΜΟΝΤΕΛΟ = η δικη μας διαφορα · ΠΡΑΓΜΑΤΙΚΟΤΗΤΑ = διαφορα γκολ και διαφορα xG
ανα ποσοστο ενδεκαδας (μεγαλο rotation <0.80 · 0.80-0.90 · 0.90-1.00 · πληρης ≥1.00), χωριστα για φαβορι και αουτσαιντερ (της αγορας).
"""
import sys, glob
src = open('uel_lineup_rule_test.py', encoding='utf-8').read().split('\nrows = []\n')[0]
exec(src)
def implied_margin(i, L, oh, oa):
    q = (1 / oh) / (1 / oh + 1 / oa); T = LH_N[i] + LA_N[i]; lo, hi = -5.0, 5.0
    for _ in range(26):
        M = (lo + hi) / 2
        pw, pp = cover_q(sdist(max((T + M) / 2, .05), max((T - M) / 2, .05)), 1, L)
        if pw / max(1 - pp, 1e-9) < q: lo = M
        else: hi = M
    return (lo + hi) / 2
EUM = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items(): EUM[str(k)] = m
def xgd(mid):
    m = EUM.get(str(mid))
    if not m or not m.get('shots'): return np.nan
    h, a = int(m['home']['id']), int(m['away']['id'])
    f = lambda t: sum(s['xg'] for s in m['shots'] if s.get('xg') is not None and int(s['tid']) == t)
    return f(h) - f(a)
rows = []
for i in range(len(MIDS)):
    if COMP[i] not in ('EuropaLeague', 'ConferenceLeague', 'ChampionsLeague') or LH_N[i] <= 0: continue
    j = VI.get(str(MIDS[i]))
    if j is None: continue
    s1 = snap_ah(MIDS[i], 'Crown', 1) or snap_ah(MIDS[i], 'SBOBET', 1)
    s0 = snap_ah(MIDS[i], 'Crown', 0) or snap_ah(MIDS[i], 'SBOBET', 0)
    if not s1 or not s0: continue
    km1 = implied_margin(i, *s1); km0 = implied_margin(i, *s0); xd = xgd(MIDS[i])
    ko = pd.Timestamp(V6['date'][j])
    for side, nm in ((1, 'h'), (-1, 'a')):
        r = ratio(MIDS[i], nm, ko)
        if not np.isfinite(r): continue
        rows.append(dict(comp=COMP[i], sea=SEA[i], ratio=r, fav=side * km1 > 0, home=side == 1,
                         mkt1=side * km1, mkt0=side * km0, mdl=side * (LH_N[i] - LA_N[i]), act=side * GD[i], xg=side * xd,
                         win=float(side * GD[i] > 0), draw=float(GD[i] == 0)))
X = pd.DataFrame(rows)
se = lambda a: a.std() / max(np.sqrt(len(a)), 1)
BINS = ((0, .80, 'μεγαλο rotation <80%'), (.80, .90, 'rotation 80-90%'), (.90, 1.0, '90-100%'), (1.0, 9, 'ΠΛΗΡΗΣ ≥100%'))
def table(x, lab):
    print(f'   {lab}')
    print(f'      {"ενδεκαδα":22s} {"n":>4s} {"ΑΓΟΡΑ 1ω":>9s} {"ΑΓΟΡΑ κλεισ":>11s} {"ΜΟΝΤΕΛΟ":>8s} {"ΠΡΑΓΜ. γκολ":>12s} {"xG":>6s}   πραγμ − αγορα     νικες')
    for lo, hi, l in BINS:
        y = x[(x.ratio >= lo) & (x.ratio < hi)]
        if len(y) < 10: print(f'      {l:22s} {len(y):4d} (λιγα)'); continue
        d = y.act - y.mkt1
        print(f'      {l:22s} {len(y):4d} {y.mkt1.mean():+9.2f} {y.mkt0.mean():+11.2f} {y.mdl.mean():+8.2f} {y.act.mean():+12.2f} {y.xg.mean():+6.2f}   '
              f'{d.mean():+.2f} ±{se(d):.2f}      {100 * y.win.mean():.0f}%')
for cm, lab in (('EuropaLeague', 'EUROPA LEAGUE'), ('ConferenceLeague', 'CONFERENCE LEAGUE'), ('ChampionsLeague', 'CHAMPIONS LEAGUE')):
    x = X[X.comp == cm]
    print(f'\n===== {lab} — ολες οι ομαδες με γνωστη ενδεκαδα: {len(x)} · rotation <90% στο {100 * (x.ratio < .9).mean():.0f}% (διαφορα απο τη σκοπια της ομαδας)')
    table(x[x.fav], 'ΦΑΒΟΡΙ ΤΗΣ ΑΓΟΡΑΣ')
    table(x[~x.fav], 'ΑΟΥΤΣΑΙΝΤΕΡ ΤΗΣ ΑΓΟΡΑΣ')
U = X[X.comp == 'EuropaLeague']
print('\n===== EUROPA: ΠΟΣΟ «ΚΟΣΤΙΖΕΙ» ΤΟ ROTATION — κλιση ως προς ln(ποσοστο ενδεκαδας): ποσα γκολ διαφορας ανα 10% λιγοτερη αξια')
for col, l in (('act', 'ΠΡΑΓΜΑΤΙΚΗ διαφορα γκολ (αφου αφαιρεθει η πρωινη αγορα → τι ΔΕΝ ειχε η αγορα)'), ('mkt1', 'ΑΓΟΡΑ 1ω'), ('mkt0', 'ΑΓΟΡΑ κλεισιμο')):
    y = U[np.isfinite(U[col])]
    base = y[col] - (y.mkt1 if col == 'act' else 0)
    b = np.polyfit(np.log(y.ratio.clip(.5, 1.6)), base, 1)[0] if col == 'act' else np.polyfit(np.log(y.ratio.clip(.5, 1.6)), y[col] - y.mdl, 1)[0]
    print(f'   {l:80s} {b * 0.105:+.3f} γκολ ανα 10%')
