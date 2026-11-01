"""euro_format_deep.py — 15/10/2026 (Στελιος: «στο Champions χτισαμε τη live μηχανη με βαρος στις 2 σεζον του νεου φορματ — να κανουμε το ιδιο στο
Europa; τι αλλαξε στο Champions απο το παλιο στο νεο φορματ; επαναλαμβανονται τα ιδια στο Europa; π.χ. σκοραρουν παραπανω γιατι κυνηγανε διαφορα
τερματων — αναλυσε το βαθια»).
ΠΑΛΙΟ (2223+2324, ομιλοι 6 αγωνιστικων) vs ΝΕΟ (2425+2526, league phase 36 ομαδων) — ΜΟΝΟ φαση ομιλων/league phase (γυροι 1-8), UCL / UEL / UECL.
Μοντελο = σημερινη ευρωπαικη αλυσιδα (euro_blend_dump_0.6) ΧΩΡΙΣ το κ του Champions (το λ του φαβορι ÷1.16 στο UCL νεο) → ιδια βαση και στις 3.
Αγορα = Crown κλεισιμο (γραμμη χαντικαπ γηπεδουχου, γραμμη συνολου). Φαβορι = του ΜΟΝΤΕΛΟΥ (μεγαλυτερο λ).
 1. ΓΚΟΛ: πραγματικα − μοντελο, − γραμμη συνολου, xG − μοντελο (ευκαιριες ή φινιρισμα;)
 2. ΦΑΒΟΡΙ / ΑΟΥΤΣΑΙΝΤΕΡ: γκολ − λ, xG − λ  (αυτο ηταν το ευρημα του Champions: +γκολ ΜΟΝΟ φαβορι, ΜΟΝΟ νεο)
 3. ΔΙΑΦΟΡΑ: κλιση πραγματικης διαφορας στη διαφορα μοντελου · διαφορα φαβορι πανω απο τη γραμμη της αγορας
 4. ΙΣΟΠΑΛΙΕΣ πραγματικες vs μοντελο · ΕΔΡΑ (γηπ − φιλ) vs μοντελο
 5. «ΚΥΝΗΓΙ ΔΙΑΦΟΡΑΣ»: γκολ ΟΤΑΝ το φαβορι ηδη προηγειται ≥2 (νεκρα γκολ), γκολ 76'+ , και ποσα «νεκρα» γκολ βαζει ο αουτσαιντερ
 6. ΑΓΩΝΙΣΤΙΚΕΣ: νεο φορματ 1-6 vs 7-8 (UEL/UCL)
 7. ΑΝΑ ΣΕΖΟΝ τα βασικα (σταθεροτητα)
"""
import sys, json, glob, pickle, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import euro_shadow_scan as ES
NL = chr(10)
D = pickle.load(open('euro_blend_dump_0.6.pkl', 'rb'))
FX = json.load(open('europe_fixtures.json', encoding='utf-8')); RND = {}; KO = {}
for k, lst in FX.items():
    for m in lst:
        RND[str(m['mid'])] = str(m.get('round'))
        try: KO[str(m['mid'])] = int(dt.datetime.strptime(m['utc'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc).timestamp())
        except Exception: pass
EU = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items(): EU[str(k)] = m
def pl(g):
    try:
        p = [float(x) for x in str(g).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception: return None
AH = {}; OU = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        r = json.loads(ln)
        if r['cid'] != 3: continue
        mid = str(r['mid']); ko = KO.get(mid)
        if not ko: continue
        a = sorted((int(mt), pl(g)) for mt, u, g, dn in (r.get('ah') or []) if mt and pl(g) is not None and int(mt) <= ko + 900)
        o = sorted((int(mt), pl(g)) for mt, ov, g, un in (r.get('ou') or []) if mt and pl(g) is not None and int(mt) <= ko + 900)
        if a: AH[mid] = a[-1][1]
        if o: OU[mid] = o[-1][1]
rows = []
for k, mid in enumerate(D['MIDS']):
    mid = str(mid); cm = D['COMP'][k]; sea = str(D['SEA'][k]); rd = RND.get(mid, '')
    if sea not in ('2223', '2324', '2425', '2526') or rd not in [str(x) for x in range(1, 9)]: continue
    lh, la = float(D['LH'][k]), float(D['LA'][k])
    if cm == 'ChampionsLeague' and sea in ('2425', '2526'):          # αφαιρεση κ (μονο φαβορι, UCL νεο)
        if lh >= la: lh /= 1.16
        else: la /= 1.16
    gh, ga = int(D['GH'][k]), int(D['GA'][k]); m = EU.get(mid) or {}
    sh = m.get('shots') or []; hid = int(m['home']['id']) if m.get('home') else None
    xh = sum(s['xg'] for s in sh if s.get('xg') is not None and hid is not None and int(s['tid']) == hid) if sh else np.nan
    xa = sum(s['xg'] for s in sh if s.get('xg') is not None and hid is not None and int(s['tid']) != hid) if sh else np.nan
    fh = lh >= la
    # γκολ ανα κατασταση (απο σουτ)
    dead_f = dead_d = late = 0; covered = False
    if sh and hid is not None:
        gs = sorted((s.get('min') or 0, int(s['tid']) == hid) for s in sh if s.get('goal'))
        if sum(1 for _, h in gs if h) == gh and sum(1 for _, h in gs if not h) == ga:
            covered = True; sc_h = sc_a = 0
            for mn, h in gs:
                lead_f = (sc_h - sc_a) if fh else (sc_a - sc_h)
                fav_goal = (h == fh)
                if lead_f >= 2:
                    if fav_goal: dead_f += 1
                    else: dead_d += 1
                if mn >= 76: late += 1
                if h: sc_h += 1
                else: sc_a += 1
    dist = ES.eu_dist(lh, la, .85); pdraw = dist.get(0, 0)
    sup = AH.get(mid)
    rows.append(dict(comp=cm, sea=sea, new=sea in ('2425', '2526'), rd=int(rd), lh=lh, la=la, gh=gh, ga=ga, xh=xh, xa=xa,
                     lf=max(lh, la), ld=min(lh, la), gf=gh if fh else ga, gdg=ga if fh else gh, xf=xh if fh else xa, xd=xa if fh else xh,
                     mm=abs(lh - la), gdf=(gh - ga) if fh else (ga - gh), supf=(sup if fh else -sup) if sup is not None else np.nan,
                     ou=OU.get(mid, np.nan), pdraw=pdraw, draw=int(gh == ga), hm=lh - la, ha=gh - ga, cv=covered,
                     dead_f=dead_f, dead_d=dead_d, late=late))
X = pd.DataFrame(rows)
def ms(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return f'{v.mean():+.2f}±{v.std() / np.sqrt(len(v)):.2f}' if len(v) > 5 else '—'
def slope(y, a, b):
    ok = np.isfinite(y[a]) & np.isfinite(y[b]); return np.polyfit(y[a][ok], y[b][ok].astype(float), 1)[0] if ok.sum() > 20 else np.nan
CL = {'ChampionsLeague': 'CHAMPIONS', 'EuropaLeague': 'EUROPA', 'ConferenceLeague': 'CONFERENCE'}
print('ΠΑΛΙΟ = 2223+2324 (ομιλοι) · ΝΕΟ = 2425+2526 (league phase) · μονο φαση ομιλων/league phase · μοντελο χωρις κ · ±=τυπικο σφαλμα')
print(f'{NL}1-4. ΒΑΣΙΚΑ (ανα ματς)')
hdr = (f'   {"":22s} {"ματς":>5s} │ {"γκολ":>5s} {"−μοντ.":>10s} {"−γραμμη":>10s} {"xG−μοντ.":>10s} │ {"ΦΑΒ γκολ−λ":>11s} {"ΦΑΒ xG−λ":>11s} │ {"DOG γκολ−λ":>11s} {"DOG xG−λ":>11s} │'
       f' {"κλιση":>5s} {"φαβ−γραμμη":>11s} │ {"ισοπ πραγμ/μοντ":>15s} │ {"εδρα−μοντ.":>11s}')
print(hdr)
for cm in CL:
    for nw in (False, True):
        y = X[(X.comp == cm) & (X.new == nw)]
        print(f'   {CL[cm] + (" ΝΕΟ" if nw else " ΠΑΛΙΟ"):22s} {len(y):5d} │ {(y.gh + y.ga).mean():5.2f} {ms(y.gh + y.ga - y.lh - y.la):>10s} {ms(y.gh + y.ga - y.ou):>10s} {ms(y.xh + y.xa - y.lh - y.la):>10s} │'
              f' {ms(y.gf - y.lf):>11s} {ms(y.xf - y.lf):>11s} │ {ms(y.gdg - y.ld):>11s} {ms(y.xd - y.ld):>11s} │ {slope(y, "mm", "gdf"):5.2f} {ms(y.gdf - y.supf):>11s} │'
              f' {100 * y.draw.mean():5.1f}% / {100 * y.pdraw.mean():4.1f}% │ {ms(y.ha - y.hm):>11s}')
print(f'{NL}5. «ΚΥΝΗΓΙ ΔΙΑΦΟΡΑΣ» (ματς οπου τα γκολ απο σουτ = τελικο σκορ) — ανα ματς')
print(f'   {"":22s} {"ματς":>5s} │ {"νεκρα γκολ ΦΑΒ (ηδη +2)":>24s} {"νεκρα γκολ DOG (φαβ +2)":>24s} │ {"γκολ 76+":>9s} │ {"ΦΑΒ γκολ−λ οταν ΔΕΝ ηταν +2":>27s}')
for cm in CL:
    for nw in (False, True):
        y = X[(X.comp == cm) & (X.new == nw) & X.cv]
        print(f'   {CL[cm] + (" ΝΕΟ" if nw else " ΠΑΛΙΟ"):22s} {len(y):5d} │ {ms(y.dead_f):>24s} {ms(y.dead_d):>24s} │ {ms(y.late):>9s} │ {ms(y.gf - y.dead_f - y.lf):>27s}')
print(f'{NL}5β. ΑΝΑ ΜΕΓΕΘΟΣ ΦΑΒΟΡΙ (διαφορα μοντελου) — ΦΑΒ γκολ − λ  │ νεκρα γκολ ΦΑΒ')
for cm in CL:
    for nw in (False, True):
        y = X[(X.comp == cm) & (X.new == nw) & X.cv]
        cells = []
        for lo, hi in ((0, .5), (.5, 1), (1, 9)):
            z = y[(y.mm >= lo) & (y.mm < hi)]; cells.append(f'{lo}-{hi if hi < 9 else "+"}: n{len(z):3d} {ms(z.gf - z.lf):>10s} │ {ms(z.dead_f):>10s}')
        print(f'   {CL[cm] + (" ΝΕΟ" if nw else " ΠΑΛΙΟ"):22s} ' + '   ║   '.join(cells))
print(f'{NL}6. ΝΕΟ ΦΟΡΜΑΤ: αγωνιστικες 1-6 vs 7-8 (τελευταιες, οταν κρινεται η θεση) — ΦΑΒ γκολ−λ · DOG γκολ−λ · γκολ−μοντελο · νεκρα ΦΑΒ')
for cm in ('ChampionsLeague', 'EuropaLeague'):
    for lab, f in (('1-6', lambda y: y.rd <= 6), ('7-8', lambda y: y.rd >= 7)):
        y = X[(X.comp == cm) & X.new]; y = y[f(y)]
        print(f'   {CL[cm]:10s} {lab}: n{len(y):3d} │ ΦΑΒ {ms(y.gf - y.lf)} · DOG {ms(y.gdg - y.ld)} · συνολο {ms(y.gh + y.ga - y.lh - y.la)} · νεκρα ΦΑΒ {ms(y[y.cv].dead_f)}')
print(f'{NL}7. ΑΝΑ ΣΕΖΟΝ — ΦΑΒ γκολ−λ │ DOG γκολ−λ │ συνολο−μοντελο │ συνολο−γραμμη │ κλιση διαφορας')
for cm in CL:
    for s in ('2223', '2324', '2425', '2526'):
        y = X[(X.comp == cm) & (X.sea == s)]
        print(f'   {CL[cm]:10s} {s}: n{len(y):3d} │ {ms(y.gf - y.lf):>10s} │ {ms(y.gdg - y.ld):>10s} │ {ms(y.gh + y.ga - y.lh - y.la):>10s} │ {ms(y.gh + y.ga - y.ou):>10s} │ {slope(y, "mm", "gdf"):5.2f}')
X.to_pickle('euro_format_deep_rows.pkl')
