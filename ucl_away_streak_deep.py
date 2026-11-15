# -*- coding: utf-8 -*-
"""ucl_away_streak_deep.py — CHAMPIONS LEAGUE: ΣΕΡΙ ΕΚΤΟΣ ΕΔΡΑΣ / ΚΟΥΡΑΣΗ / ΤΑΞΙΔΙ / ΞΕΚΟΥΡΑΣΗ, βαθια αναλυση (16/10/2026, Στελιος:
Ντορτμουντ, PSV, Μαν. Γιουναιτεντ, Μπαρτσελονα παιζουν 3ο συνεχομενο εκτος στην 3η αγωνιστικη 20-22/10). Προτυπο: el_dw_fatigue_deep.py.
Προηγουμενα (28/8): κουραση χτυπαει xG οχι σκορ · αποσταση = τιποτα · b2b εκτος = καμια ζημια · παρκαρισμενο UCL layer.
ΗΜΕΡΟΛΟΓΙΟ ομαδας = ΟΛΑ τα ματς που εχουμε: εγχωρια πρωταθληματα (data_<λιγκα>_<σεζον>.json, ολες οι λιγκες) + Ευρωπη (europe_fixtures
+ προκριματικα euq_fixtures). ΔΕΝ εχουμε εγχωρια ΚΥΠΕΛΛΑ → η ξεκουραση μπορει να ειναι μεγαλυτερη απ' οτι ηταν (σημειωνεται).
Ανα ομαδα-ματς: σερι εκτος ΜΑΖΙ με αυτο (1,2,3+) · μερες απο το προηγουμενο ματς · ματς στις 10/14 μερες · χλμ στις 7/10/14 μερες
(αλυσιδα γηπεδων: εδρα→γηπεδο Α→γηπεδο Β…, venues.json) · διαφορα ξεκουρασης με τον αντιπαλο.
Μετρηση (απο τη ματια της ομαδας, + = τα πηγε καλυτερα): (α) διαφορα γκολ − αγορα κλεισιματος (msup, μεσος Crown/SBOBET) και − 72ω
(η τελευταια τιμη ≤72ω, ή η πρωτη αν ανοιξε αργοτερα) · (β) − live μοντελο (LH−LA, 2223-2526) · (γ) xG διαφορα − μοντελο ·
(δ) συνολο γκολ − αγορα συνολων (mtot) · (ε) τυφλο AH στο κλεισιμο ΥΠΕΡ της ομαδας (μεσος 2 βιβλιων) · (στ) τα live UCL picks μας
(ucl_bb_timing_alerts.pkl: φαβ ≥10% σωστα τεταρτα, dog ≥4% p_cover, over ≥4%, under ≥10%) ΥΠΕΡ/ΚΑΤΑ ομαδας με το χαρακτηριστικο.
Εγχωριο ματς ΑΜΕΣΩΣ ΜΕΤΑ απο UCL (≤5 μερες): CORE7, Crown (Nowgoal 2223-2526 — SBOBET δεν υπαρχει στα εγχωρια), μοντελο europe_test_preds (md≥6).
SE = ομαδοποιημενο ανα ματς (αν και οι 2 ομαδες εχουν το χαρακτηριστικο, αλληλοαναιρουνται).
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ το τρεξιμο): επιδραση κουρασης «υπαρχει απεναντι στην αγορα» ΜΟΝΟ αν η αποκλιση απο το κλεισιμο
  εχει ιδια φορα σε ≥4/5 σεζον (≥3/4 αν 4) ΚΑΙ |t| ≥ 2 ΚΑΙ οι γειτονικοι οριμοι (2 εκτος / 3+ εκτος · τριτημορια χλμ) ειναι
  μονοτονοι ή ιδιας φορας. Ως διορθωση μοντελου: LOSO RMSE καλυτερο σε ≥4/5 σεζον (≥3/4). Αλλιως ΜΟΝΟ περιγραφικο.
Εξοδος: ucl_away_streak_deep_out.txt"""
import sys, os, io, json, glob, math, pickle, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.getcwd())
src = open('ucl_bb_timing.py', encoding='utf-8').read()
src = src[:src.index('rows = []\n# 13/10')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
g = {'__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
MIDS, COMP, FM, SEA, LH, LA, GDc, KO, TRAJ = (g[k] for k in ('MIDS', 'COMP', 'FM', 'SEA', 'LH', 'LA', 'GD', 'KO', 'TRAJ'))
picks, msup, mtot, parse_line = g['picks'], g['msup'], g['mtot'], g['u']['parse_line']
MI = {str(m): i for i, m in enumerate(MIDS)}
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))

# ---------------- 1. ΗΜΕΡΟΛΟΓΙΟ ----------------
NAT = ('AFCON', 'AFCONQ', 'AsianCup', 'CopaAmerica', 'EURO', 'EUROQ', 'Friendlies', 'GoldCup', 'WorldCup')
def pdt(s):
    if s[:4].isdigit(): return pd.Timestamp(s[:19])
    return pd.Timestamp(s.split(', ', 1)[1].replace(' UTC', ''))
G = {}            # mid -> info
XG = {}           # mid -> (xg_h, xg_a)
for f in glob.glob('data_*_*.json'):
    lg, sea = f[5:-5].rsplit('_', 1)
    if not sea.isdigit() or lg in NAT or lg.startswith(('WCQ', 'NationsLeague')): continue
    try: D = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    for m in (D.values() if isinstance(D, dict) else D):
        try:
            mid = str(m['mid']); h, a = int(m['home']['id']), int(m['away']['id'])
            xh = sum(s['xg'] for s in m.get('shots') or [] if s.get('tid') == h and s.get('xg') is not None)
            xa = sum(s['xg'] for s in m.get('shots') or [] if s.get('tid') == a and s.get('xg') is not None)
            if m.get('shots'): XG[mid] = (xh, xa)
            if lg == 'Europe': continue
            G[mid] = dict(kind='dom', lg=lg, sea=sea, t=pdt(m['date']), h=h, a=a, hs=m.get('hs'), as_=m.get('as'), rnd=None)
        except Exception:
            pass
for fn in ('europe_fixtures.json', 'euq_fixtures.json', 'europe_fixtures_2627.json'):
    for k, L in json.load(open(fn, encoding='utf-8')).items():
        comp, sea = k.rsplit('_', 1)
        for m in L:
            sc = str(m.get('score') or '').split(' - ')
            hs, as_ = (int(sc[0]), int(sc[1])) if len(sc) == 2 and sc[1].strip().isdigit() else (None, None)
            G[str(m['mid'])] = dict(kind='eu', lg=comp, sea=sea, t=pd.Timestamp(m['utc'][:19]), h=int(m['hid']), a=int(m['aid']), hs=hs, as_=as_, rnd=str(m.get('round')))
V = json.load(open('venues.json', encoding='utf-8'))
LOC = {int(k): (v['lat'], v['lon']) for k, v in V.items() if v and v.get('lat')}
for _t, _c in ((951893, (40.41, 49.87)), (10217, (52.06, 4.38)), (8149, (52.457, 13.568)), (8463, (53.778, -1.572)), (10171, (45.814, 9.072))):
    LOC.setdefault(_t, _c)   # Sabah/ADO/Union/Leeds/Como — χειροκινητα αν λειπουν απο venues.json (ΒΗΜΑ 0)
def km(p, q):
    if p is None or q is None: return 0.0
    la1, lo1 = p; la2, lo2 = q; r = math.pi / 180
    x = 0.5 - math.cos((la2 - la1) * r) / 2 + math.cos(la1 * r) * math.cos(la2 * r) * (1 - math.cos((lo2 - lo1) * r)) / 2
    return 12742 * math.asin(math.sqrt(max(x, 0)))
def build_cal(G):
    cal = {}
    for mid, x in G.items():
        neut = x['rnd'] == 'final'
        for tid, aw in ((x['h'], False), (x['a'], True)):
            cal.setdefault(tid, []).append((x['t'], mid, None if neut else x['h'], aw or neut, x['kind']))
    for k in cal: cal[k].sort()
    return cal, {k: {e[1]: j for j, e in enumerate(v)} for k, v in cal.items()}
CAL, POS = build_cal(G)
def feats(tid, mid):
    L = CAL.get(tid); j = POS.get(tid, {}).get(mid)
    if L is None or j is None: return None
    t = L[j][0]; home = LOC.get(tid)
    s = 0
    for e in reversed(L[:j + 1]):
        if e[3]: s += 1
        else: break
    prev = L[j - 1] if j > 0 else None
    rest = (t - prev[0]).total_seconds() / 86400 if prev else np.nan
    dd = [(t - e[0]).total_seconds() / 86400 for e in L[:j]]
    n10 = sum(1 for d in dd if d <= 10); n14 = sum(1 for d in dd if d <= 14)
    kms = {}
    for N in (7, 10, 14):
        tot = 0.0
        for k in range(j, -1, -1):
            if (t - L[k][0]).total_seconds() / 86400 >= N and k != j: break
            here = LOC.get(L[k][2]) if L[k][2] is not None else home
            there = (LOC.get(L[k - 1][2]) if L[k - 1][2] is not None else home) if k > 0 else home
            tot += km(there, here)
        kms[N] = tot
    ok = any(e[4] == 'dom' and abs((e[0] - t).total_seconds()) <= 14 * 86400 for e in L)
    return dict(streak=s, rest=rest, n10=n10, n14=n14, km7=kms[7], km10=kms[10], km14=kms[14], ok=ok,
                trip=km(home, LOC.get(L[j][2])) if L[j][3] else 0.0, prev_kind=prev[4] if prev else None, prev_away=prev[3] if prev else None,
                prev2_eu_away=(j > 1 and L[j - 2][4] == 'eu' and L[j - 2][3]))

# ---------------- ΒΗΜΑ 0: τα 4 ματς της 3ης αγωνιστικης ----------------
AR = json.load(open('match_projections_archive.json', encoding='utf-8'))
G0 = dict(G)
for k, v in AR.items():
    if isinstance(v, dict) and v.get('utc') and str(v.get('utc')) >= '2026-10-16' and v.get('home_id'):
        G0['p' + str(v.get('fid') or k)] = dict(kind='dom', lg=v.get('league'), sea='2627', t=pd.Timestamp(v['utc'][:19]),
                                               h=int(v['home_id']), a=int(v['away_id']), hs=None, as_=None, rnd=None)
NM = {}
for x in json.load(open('europe_fixtures_2627.json', encoding='utf-8')).values():
    for m in x: NM[int(m['hid'])] = m['hname']; NM[int(m['aid'])] = m['aname']
for k, v in AR.items():
    if isinstance(v, dict) and v.get('home_id'): NM[int(v['home_id'])] = v['home']; NM[int(v['away_id'])] = v['away']
CAL, POS = build_cal(G0)
P('=== ΒΗΜΑ 0. ΣΕΙΡΕΣ 9-26/10 (Ε=εντος, Χ=εκτος · μερες απο το προηγ. · χλμ απο εδρα · αλυσιδα 14 μερων ως το UCL ματς) ===')
for tid in (9789, 8640, 10260, 8634):
    seq = [e for e in CAL[tid] if pd.Timestamp('2026-10-08') <= e[0] <= pd.Timestamp('2026-10-27')]
    parts = []; prev = None
    for e in seq:
        x = G0[e[1]]; opp = x['a'] if x['h'] == tid else x['h']
        tag = ('UCL ' if x['kind'] == 'eu' else '') + ('Χ ' if e[3] else 'Ε ') + NM.get(opp, str(opp))[:14]
        rd = f"{(e[0] - prev).total_seconds() / 86400:.1f}μ" if prev is not None else ''
        parts.append(f"{e[0]:%d/%m} {tag} [{rd}{', %d χλμ' % km(LOC.get(tid), LOC.get(x['h'])) if e[3] else ''}]"); prev = e[0]
    P(f"  {NM.get(tid, tid)[:17]:17s} " + ' → '.join(parts))
    um = [e for e in seq if G0[e[1]]['kind'] == 'eu' and e[0] > pd.Timestamp('2026-10-16')]
    if um:
        F = feats(tid, um[0][1]); x = G0[um[0][1]]; opp = x['h']; Fo = feats(opp, um[0][1])
        P(f"      UCL 3ης: σερι εκτος {F['streak']} · ξεκουραση {F['rest']:.1f}μ (αντιπ. {Fo['rest']:.1f}μ{'' if Fo['ok'] else ' — εγχωρια αντιπαλου ΑΓΝΩΣΤΑ'}) · "
          f"ματς 14μ {F['n14']} (αντ. {Fo['n14']}) · χλμ αλυσιδα 7/14μ {F['km7']:.0f}/{F['km14']:.0f} · ταξιδι απο εδρα {F['trip']:.0f}")
CAL, POS = build_cal(G)

# ---------------- 2. ΑΓΟΡΑ & ΓΡΑΜΜΕΣ ----------------
def load_tou(pattern, cids):
    T = {}
    for f in glob.glob(pattern):
        for line in open(f, encoding='utf-8'):
            r = json.loads(line); bk = cids.get(r['cid'])
            if bk is None: continue
            seq = sorted((int(mt), g['pl'](gg), float(o) + 1, float(un) + 1) for mt, o, gg, un in (r.get('ou') or [])
                         if mt and g['pl'](gg) is not None and o not in (None, '') and un not in (None, ''))
            if seq and len(seq) > len(T.get((str(r['mid']), bk), [])): T[(str(r['mid']), bk)] = seq
    return T
def load_ah(pattern, cids):
    T = {}
    for f in glob.glob(pattern):
        for line in open(f, encoding='utf-8'):
            r = json.loads(line); bk = cids.get(r['cid'])
            if bk is None: continue
            rows = []
            for mt, u, gg, dn in r.get('ah') or []:
                gl = parse_line(gg)
                try: rows.append((int(mt), -gl, float(u) + 1, float(dn) + 1))
                except (TypeError, ValueError): pass
            rows = sorted(x for x in rows if x[1] is not None)
            if rows and len(rows) > len(T.get((str(r['mid']), bk), [])): T[(str(r['mid']), bk)] = rows
    return T
TOUE = load_tou('nowgoal_odds/*_U*.jsonl', {3: 'Crown', 31: 'SBOBET'})
CORE7 = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
AHD = {}; TOUD = {}
for lg in CORE7:
    AHD.update(load_ah(f'nowgoal_odds/*_{lg}*.jsonl', {3: 'Crown'})); TOUD.update(load_tou(f'nowgoal_odds/*_{lg}*.jsonl', {3: 'Crown'}))
def at(seq, t):
    pre = [x for x in seq if x[0] <= t]
    return pre[-1] if pre else None
def mkt(mid, ko, ah, tou, books, Tmod, gd):
    """μεσος ορος βιβλιων: msup κλεισ., msup 72ω, mtot κλεισ., pnl υπερ γηπ./φιλ. στο κλεισιμο"""
    R = dict(c=[], o=[], tc=[], ph=[], pa=[])
    for bk in books:
        ts = [x for x in (tou.get((mid, bk)) or []) if x[0] < ko]
        if ts: R['tc'].append(mtot(*ts[-1][1:]))
    T = np.mean(R['tc']) if R['tc'] else (Tmod if Tmod is not None and np.isfinite(Tmod) else 2.75)
    for bk in books:
        seq = [x for x in (ah.get((mid, bk)) or []) if x[0] < ko]
        if not seq: continue
        cl = seq[-1]; op = at(seq, ko - 72 * 3600) or seq[0]
        R['c'].append(msup(cl[1], cl[2], cl[3], T)); R['o'].append(msup(op[1], op[2], op[3], T))
        if gd is not None:
            R['ph'].append(picks.settle(gd, 1, cl[1], cl[2])); R['pa'].append(picks.settle(gd, -1, -cl[1], cl[3]))
    return {k: (np.mean(v) if v else np.nan) for k, v in R.items()}

# ---------------- 3. ΓΡΑΜΜΕΣ ΟΜΑΔΑΣ-ΜΑΤΣ: ΕΥΡΩΠΗ ----------------
rows = []
for mid, x in G.items():
    if x['kind'] != 'eu' or x['sea'] not in ('2122', '2223', '2324', '2425', '2526') or x['rnd'] == 'final': continue
    if x['lg'] not in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'): continue
    i = MI.get(mid)
    gd = (GDc[i] if i is not None else (x['hs'] - x['as_'] if x['hs'] is not None else None))
    if gd is None: continue
    ko = int(KO.get(mid) or x['t'].tz_localize('UTC').timestamp())
    mod = (LH[i] - LA[i]) if i is not None else np.nan; Tm = (LH[i] + LA[i]) if i is not None else None
    M = mkt(mid, ko, TRAJ, TOUE, ('Crown', 'SBOBET'), Tm, gd)
    if not np.isfinite(M['c']): continue
    xg = XG.get(mid); xgd = (xg[0] - xg[1]) if xg else np.nan
    tot = (g['GH'][i] + g['GA'][i]) if i is not None else (x['hs'] + x['as_'] if x['hs'] is not None else np.nan)
    Fh, Fa = feats(x['h'], mid), feats(x['a'], mid)
    if Fh is None or Fa is None: continue
    for s, F, Fo in ((1, Fh, Fa), (-1, Fa, Fh)):
        rows.append(dict(mid=mid, comp=x['lg'], sea=x['sea'], s=s, **{**F, 'ok': F['ok'] and Fo['ok']},
                         o_streak=Fo['streak'], o_rest=Fo['rest'], o_n14=Fo['n14'], o_km14=Fo['km14'], rdiff=F['rest'] - Fo['rest'],
                         rc=s * (gd - M['c']), ro=s * (gd - M['o']), mv=s * (M['c'] - M['o']), rm=s * (gd - mod), rx=s * (xgd - mod),
                         rxm=s * (xgd - M['c']), rt=tot - M['tc'], roi=M['ph'] if s == 1 else M['pa']))
E = pd.DataFrame(rows)
SEAS = ['2122', '2223', '2324', '2425', '2526']
def cse(v, cl):
    v = np.asarray(v, float); cl = np.asarray(cl); m = np.isfinite(v); v, cl = v[m], cl[m]; n = len(v)
    if n < 3: return (v.mean() if n else np.nan), np.nan, n
    mu = v.mean(); s = pd.Series(v - mu).groupby(cl).sum(); Gn = len(s)
    return mu, math.sqrt((s ** 2).sum() * Gn / max(Gn - 1, 1)) / n, n
def line(lab, d, base=None, short=False):
    mu, se, n = cse(d.rc, d.mid)
    if n < 5: return f'  {lab:31s} n {n:4d}'
    ps = d.groupby('sea').rc.mean(); ps = ps[d.groupby('sea').size() >= 3]
    sg = int((np.sign(ps) == np.sign(mu)).sum())
    f = lambda c: cse(d[c], d.mid)[0]
    b = '' if base is None else f' (−βασ {mu - base:+.2f})'
    s1 = (f'  {lab:31s} n {n:4d} · κλεισ {mu:+.2f}±{se:.2f} t {mu / se:+.1f}{b} · 72ω {f("ro"):+.2f} · κιν.αγ {f("mv"):+.2f}')
    if short: return s1 + f' · AH {100 * f("roi"):+.1f}% · {sg}/{len(ps)}'
    return (s1 + f' · μοντ {f("rm"):+.2f} · xG−μοντ {f("rx"):+.2f} · Σ−αγ {f("rt"):+.2f} · AH {100 * f("roi"):+.1f}%'
            + ' · [' + ' '.join(f'{k[:2]}:{v:+.2f}' for k, v in ps.items()) + f'] {sg}/{len(ps)}')
U = E[(E.comp == 'ChampionsLeague') & E.ok]
P(''); P(f'=== 1. UCL 2122-2526 · ομαδα-ματς με πληρες ημερολογιο {len(U)} ({U.mid.nunique()} ματς· εκτος ημερολογιου {int((~E[E.comp == "ChampionsLeague"].ok).sum())}) ===')
P('  στηλες: πραγμ. διαφορα γκολ − αγορα (κλεισ ±SE, t) · −72ω · κινηση αγορας 72ω→κλεισ (− = την «τιμωρησε») · − μοντελο (2223+) · xG−μοντ ·')
P('          συνολο γκολ − αγορα συνολων · τυφλο AH υπερ ομαδας στο κλεισιμο · [ανα σεζον κλεισ] ιδια φορα/σεζον')
AW = U[U.s == -1]; base1 = cse(AW[AW.streak == 1].rc, AW[AW.streak == 1].mid)[0]
P(line('ΕΚΤΟΣ σερι 1 (προηγ. εντος) [βαση]', AW[AW.streak == 1]))
P(line('ΕΚΤΟΣ σερι 2', AW[AW.streak == 2], base1))
P(line('ΕΚΤΟΣ σερι 3+', AW[AW.streak >= 3], base1))
P(line('  σερι 3+ ΚΑΙ ξεκουρ. ≤3.5μ', AW[(AW.streak >= 3) & (AW.rest <= 3.5)], base1))
P(line('  μοτιβο UCL Χ→εγχ.Χ→UCL Χ', AW[(AW.streak >= 3) & (AW.prev_kind == 'dom') & AW.prev2_eu_away], base1))
P(line('ΕΝΤΟΣ μετα απο εκτος', U[(U.s == 1) & (U.prev_away == True)]))
P('  — ξεκουραση (ολες οι ομαδες) —')
P(line('ξεκουραση ≥1μ ΛΙΓΟΤΕΡΗ απο αντιπ.', U[U.rdiff <= -1]))
P(line('ξεκουραση ≤3.0μ (απολυτη)', U[U.rest <= 3.0]))
P(line('ματς στις 14μ ≥4', U[U.n14 >= 4]))
P(line('ματς στις 14μ ≤2', U[U.n14 <= 2]))
q1, q2 = AW.km14.quantile([1 / 3, 2 / 3])
P(f'  — χλμ αλυσιδας 14 μερων, φιλοξενουμενος (τριτημορια: <{q1:.0f} / {q1:.0f}-{q2:.0f} / >{q2:.0f}) —')
P(line('χλμ14 χαμηλο', AW[AW.km14 < q1], base1)); P(line('χλμ14 μεσαιο', AW[(AW.km14 >= q1) & (AW.km14 < q2)], base1))
P(line('χλμ14 υψηλο', AW[AW.km14 >= q2], base1))
P(line('ταξιδι απο εδρα ≥2000 χλμ', AW[AW.trip >= 2000], base1))
P(line('ΕΚ ΤΩΝ ΥΣΤΕΡΩΝ: χλμ14 υψ.+ταξ.<1200', AW[(AW.km14 >= q2) & (AW.trip < 1200)], base1, short=True))
P(line('  γειτονικο: χλμ14 υψ.+ταξ.<1600', AW[(AW.km14 >= q2) & (AW.trip < 1600)], base1, short=True))
_x = AW.km14 - AW.trip
P('  «επιπλεον» χλμ14 (εκτος του τωρινου ταξιδιου) 0 / 1-500 / 500-1000 / 1000-2000 / 2000+: ' + ' · '.join(
  f'{cse(AW[(_x >= lo) & (_x < hi)].rc, AW[(_x >= lo) & (_x < hi)].mid)[0]:+.2f} (n {int(((_x >= lo) & (_x < hi)).sum())})' for lo, hi in ((0, 1), (1, 500), (500, 1000), (1000, 2000), (2000, 1e9))))

# ---------------- κλισεις (μια γραμμη ανα ματς, ματια γηπεδουχου, διαφορες γηπ−φιλ) ----------------
def slope(d, y, xc, lab, scale=1.0):
    d = d[np.isfinite(d[y]) & np.isfinite(d[xc])]
    def fit(dd):
        X = np.c_[np.ones(len(dd)), dd[xc] / scale]; b = np.linalg.lstsq(X, dd[y], rcond=None)[0]
        e = dd[y] - X @ b; cov = (e @ e) / max(len(dd) - 2, 1) * np.linalg.inv(X.T @ X); return b[1], math.sqrt(cov[1, 1])
    b, se = fit(d); ps = [fit(d[d.sea == s])[0] for s in SEAS if (d.sea == s).sum() > 20]
    sg = sum(np.sign(p) == np.sign(b) for p in ps)
    return f'  {lab:44s} n {len(d):4d} · κλιση {b:+.3f} (t {b / se:+.1f}) · ιδια φορα {sg}/{len(ps)} · [' + ' '.join(f'{p:+.2f}' for p in ps) + ']', b, b / se, sg, len(ps)
H = U[U.s == 1].copy()
H['d_streak'] = H.streak - H.o_streak; H['d_n14'] = H.n14 - H.o_n14; H['d_km'] = H.km14 - H.o_km14
P('  — κλισεις (1 γραμμη/ματς, y = υπολοιπο γηπ., x = γηπ − φιλ): + στην ξεκουραση = ο πιο ξεκουραστος καλυτερα · + στα χλμ = ο πιο ΤΑΞΙΔΕΜΕΝΟΣ καλυτερα —')
SL = {}
for y, yl in (('rc', 'κλεισ'), ('rm', 'μοντ'), ('rx', 'xG−μοντ')):
    for xc, xl, sc in (('rdiff', 'διαφ. ξεκουρασης (μερες)', 1), ('d_km', 'διαφ. χλμ14 (ανα 1000)', 1000)):
        if y == 'rx' and xc == 'd_km': continue
        s_, b, t, sg, np_ = slope(H, y, xc, f'{yl} ~ {xl}', sc); P(s_); SL[(y, xc)] = (b, t, sg, np_)

# ---------------- UEL/UECL (πλαισιο) ----------------
P(''); P('=== 2. ΠΛΑΙΣΙΟ: UEL / UECL (ιδιες στηλες, συντομα) ===')
for comp, nm in (('EuropaLeague', 'UEL'), ('ConferenceLeague', 'UECL')):
    W = E[(E.comp == comp) & E.ok & (E.s == -1)]; b0 = cse(W[W.streak == 1].rc, W[W.streak == 1].mid)[0]
    P(line(f'{nm} εκτος σερι 1 [βαση]', W[W.streak == 1], short=True)); P(line(f'{nm} εκτος σερι 2', W[W.streak == 2], b0, short=True))
    P(line(f'{nm} εκτος σερι 3+', W[W.streak >= 3], b0, short=True))
    Wa = E[(E.comp == comp) & E.ok]; P(line(f'{nm} ξεκουρ. ≥1μ λιγοτερη', Wa[Wa.rdiff <= -1], short=True))

# ---------------- 3. ΕΓΧΩΡΙΟ ΜΕΤΑ ΑΠΟ UCL ----------------
EP = pd.read_csv('europe_test_preds.csv'); EP['mid'] = EP.mid.astype(str)
EPM = {m: (h - a, h + a) for m, h, a in zip(EP.mid, EP.xg_h, EP.xg_a)}
UCLT = {(x['sea'], t) for x in G.values() if x['kind'] == 'eu' and x['lg'] == 'ChampionsLeague' for t in (x['h'], x['a'])}
EUT = {(x['sea'], t) for x in G.values() if x['kind'] == 'eu' and x['lg'] in ('EuropaLeague', 'ConferenceLeague') and x['rnd'] and x['rnd'][0].isdigit() for t in (x['h'], x['a'])}
drows = []
for mid, x in G.items():
    if x['kind'] != 'dom' or x['lg'] not in CORE7 or x['sea'] not in SEAS[1:] or x['hs'] is None: continue
    tm = [t for t in (x['h'], x['a']) if (x['sea'], t) in UCLT or (x['sea'], t) in EUT]
    if not tm: continue
    gd = x['hs'] - x['as_']; ko = int(x['t'].tz_localize('UTC').timestamp())
    pm = EPM.get(mid, (np.nan, None))
    M = mkt(mid, ko, AHD, TOUD, ('Crown',), pm[1], gd)
    if not np.isfinite(M['c']): continue
    xg = XG.get(mid); xgd = (xg[0] - xg[1]) if xg else np.nan
    for t in tm:
        s = 1 if t == x['h'] else -1; L = CAL[t]; j = POS[t][mid]
        pe = L[j - 1] if j > 0 else None
        if pe is None: continue
        pk = G[pe[1]]; gap = (x['t'] - pe[0]).total_seconds() / 86400
        F = feats(t, mid)
        drows.append(dict(mid=mid, sea=x['sea'], ucl=(x['sea'], t) in UCLT, s=s, prev_eu=pk['kind'] == 'eu' and gap <= 5, prev_ucl=pk['lg'] == 'ChampionsLeague',
                          prev_away=pe[3], streak=F['streak'], rest=F['rest'], rc=s * (gd - M['c']), ro=s * (gd - M['o']), mv=s * (M['c'] - M['o']),
                          rm=s * (gd - pm[0]), rx=s * (xgd - pm[0]), rt=x['hs'] + x['as_'] - M['tc'], roi=M['ph'] if s == 1 else M['pa']))
DD = pd.DataFrame(drows)
P(''); P('=== 3. ΕΓΧΩΡΙΟ ΜΑΤΣ ΑΜΕΣΩΣ ΜΕΤΑ ΑΠΟ ΕΥΡΩΠΗ (≤5μ) · CORE7 · Crown μονο · 2223-2526 (4 σεζον) ===')
du = DD[DD.ucl]; db = du[(~du.prev_eu) & (du.s == -1)]; bD = cse(db.rc, db.mid)[0]
P(line('UCL ομαδες: εγχ. ΕΚΤΟΣ χωρις Ευρωπη πριν [βαση]', db))
P(line('UCL Χ → εγχ. Χ (σερι 2)', du[du.prev_eu & du.prev_ucl & du.prev_away & (du.s == -1) & (du.streak == 2)], bD))
P(line('UCL Χ → εγχ. Χ = 3ο εκτος σερι', du[du.prev_eu & du.prev_ucl & du.prev_away & (du.s == -1) & (du.streak >= 3)], bD))
P(line('UCL Ε → εγχ. Χ', du[du.prev_eu & du.prev_ucl & ~du.prev_away.astype(bool) & (du.s == -1)], bD))
P(line('UCL Χ → εγχ. Ε', du[du.prev_eu & du.prev_ucl & du.prev_away.astype(bool) & (du.s == 1)]))
de = DD[~DD.ucl]
P(line('UEL/UECL Χ → εγχ. Χ (πλαισιο)', de[de.prev_eu & de.prev_away.astype(bool) & (de.s == -1)], cse(de[(~de.prev_eu) & (de.s == -1)].rc, de[(~de.prev_eu) & (de.s == -1)].mid)[0], short=True))

# ---------------- 4. LOSO διορθωση μοντελου (UCL, 2223-2526) ----------------
P(''); P('=== 4. ΩΣ ΔΙΟΡΘΩΣΗ ΜΟΝΤΕΛΟΥ (LOSO, UCL 2223-2526): δ = μεσο υπολοιπο vs μοντελο στις αλλες σεζον· ΔRMSE ολης της σεζον (− = καλυτερο) ===')
UM = U[np.isfinite(U.rm)]
for lab, fl in (('εκτος σερι 3+', lambda d: (d.s == -1) & (d.streak >= 3)), ('εκτος σερι ≥2', lambda d: (d.s == -1) & (d.streak >= 2)),
                ('ξεκουραση ≥1μ λιγοτερη', lambda d: d.rdiff <= -1), ('χλμ14 υψηλο (φιλοξ.)', lambda d: (d.s == -1) & (d.km14 >= q2))):
    res = []; ds = []
    for s in SEAS[1:]:
        tr = UM[(UM.sea != s) & fl(UM)]; te = UM[UM.sea == s]
        if not len(tr) or not len(te): continue
        dl = tr.rm.mean(); ds.append(dl)
        e0 = te.rm.values; f = fl(te).values
        # η διορθωση μετακινει την προβλεψη ΥΠΕΡ της ομαδας κατα δ → υπολοιπο −δ· στο ματς μετραμε (gd−pred)^2 μια φορα (γραμμη γηπ.)
        hm = te[te.s == 1].set_index('mid'); am = te[te.s == -1].set_index('mid')
        corr = (fl(hm).astype(float) * dl) - (fl(am.reindex(hm.index)).astype(float) * dl)
        r0 = hm.rm; r1 = hm.rm - corr
        res.append(math.sqrt((r1 ** 2).mean()) - math.sqrt((r0 ** 2).mean()))
    P(f"  {lab:24s} δ ανα σεζον [{' '.join(f'{x:+.2f}' for x in ds)}] · ΔRMSE [{' '.join(f'{x:+.4f}' for x in res)}] → καλυτερο {sum(x < 0 for x in res)}/{len(res)}")

# ---------------- 5. ΤΑ PICKS ΜΑΣ ----------------
A = pd.read_pickle('ucl_bb_timing_alerts.pkl'); A['mid'] = A.mid.astype(str)
FL = {}
for r in U.itertuples():
    FL[(r.mid, r.s)] = dict(st3=(r.s == -1 and r.streak >= 3), st2=(r.s == -1 and r.streak >= 2), rest=r.rdiff <= -1, km=(r.s == -1 and r.km14 >= q2))
def side_of(r):
    ko = KO.get(r.mid) or int(G[r.mid]['t'].tz_localize('UTC').timestamp()); x = at(TRAJ.get((r.mid, r.bk)) or [], ko - r.hrs * 3600 + 1)
    if x is None: return np.nan
    return 1 if abs(x[1] - r.ln) < 1e-9 else (-1 if abs(-x[1] - r.ln) < 1e-9 else np.nan)
A['side'] = [side_of(r) if r.mk in ('fav', 'dog') else np.nan for r in A.itertuples()]
P(''); P('=== 5. LIVE UCL PICKS (alert, μεσος Crown/SBOBET, 2223-2526): ROI (picks/βιβλιο) — ΥΠΕΡ / ΚΑΤΑ ομαδας με το χαρακτηριστικο / ουδετερα ===')
def roi(d):
    if not len(d): return '   —         '
    gb = d.groupby('bk').pa; return f'{100 * gb.mean().mean():+6.1f}% ({gb.size().mean():4.0f})'
for fk, fn in (('st3', 'εκτος σερι 3+'), ('st2', 'εκτος σερι ≥2'), ('rest', 'ξεκουρ. ≥1μ λιγοτερη'), ('km', 'χλμ14 υψηλο')):
    on = []; ag = []; ne = []
    for r in A.itertuples():
        a, b = FL.get((r.mid, 1)), FL.get((r.mid, -1))
        if a is None or b is None: continue
        if r.mk in ('fav', 'dog'):
            if not np.isfinite(r.side): continue
            me, op = (a, b) if r.side == 1 else (b, a)
            (on if me[fk] else ag if op[fk] else ne).append(r.Index)
        else:
            (on if (a[fk] or b[fk]) else ne).append(r.Index)
    ah = lambda ix: A.loc[ix][A.loc[ix].mk.isin(['fav', 'dog'])]
    ou = lambda ix, m: A.loc[ix][A.loc[ix].mk == m]
    P(f'  {fn:22s} AH: υπερ {roi(ah(on))} · κατα {roi(ah(ag))} · ουδ {roi(ah(ne))} | OVER με/χωρις {roi(ou(on, "over"))} / {roi(ou(ne, "over"))}'
      f' | UNDER με/χωρις {roi(ou(on, "under"))} / {roi(ou(ne, "under"))}')

# ---------------- 6. ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ ----------------
P(''); P('=== 6. ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (UCL, απεναντι στο κλεισιμο) ===')
def crit(lab, d, neigh_ok, extra=''):
    mu, se, n = cse(d.rc, d.mid); ps = d.groupby('sea').rc.mean(); ps = ps[d.groupby('sea').size() >= 3]
    sg = int((np.sign(ps) == np.sign(mu)).sum()); need = 4 if len(ps) >= 5 else 3
    ok = sg >= need and abs(mu / se) >= 2 and neigh_ok
    P(f'  {lab:26s} n {n:4d} · {mu:+.2f} t {mu / se:+.1f} · σεζον {sg}/{len(ps)} (θελει {need}) · γειτονικα {"✓" if neigh_ok else "✗"}{extra} → {"ΠΕΡΝΑ" if ok else "ΔΕΝ ΠΕΡΝΑ (περιγραφικο)"}')
m2 = cse(AW[AW.streak == 2].rc, AW[AW.streak == 2].mid)[0]; m3 = cse(AW[AW.streak >= 3].rc, AW[AW.streak >= 3].mid)[0]
crit('εκτος σερι 3+', AW[AW.streak >= 3], bool(np.sign(m2) == np.sign(m3) or base1 >= m2 >= m3 or base1 <= m2 <= m3), f' (σερι2 {m2:+.2f} / 3+ {m3:+.2f})')
t3 = [cse(AW[c].rc, AW[c].mid)[0] for c in (AW.km14 < q1, (AW.km14 >= q1) & (AW.km14 < q2), AW.km14 >= q2)]
crit('χλμ14 υψηλο (φιλοξ.)', AW[AW.km14 >= q2], (t3[0] >= t3[1] >= t3[2]) or (t3[0] <= t3[1] <= t3[2]), f' (τριτημ. {t3[0]:+.2f}/{t3[1]:+.2f}/{t3[2]:+.2f})')
b, t, sg, np_ = SL[('rc', 'rdiff')]
crit('ξεκουραση ≥1μ λιγοτερη', U[U.rdiff <= -1], np.sign(b) == -np.sign(cse(U[U.rdiff <= -1].rc, U[U.rdiff <= -1].mid)[0]), f' (κλιση διαφ. ξεκουρ. {b:+.3f} t {t:+.1f})')
b, t, sg, np_ = SL[('rc', 'd_km')]
P(f'  κλιση χλμ14 (συνεχης)       n {len(H):4d} · {b:+.3f}/1000χλμ t {t:+.1f} · σεζον {sg}/{np_} · τριτημ. μονοτονα {"✓" if (t3[0] <= t3[1] <= t3[2]) else "✗"} → '
  f'{"ΠΕΡΝΑ τα ορια" if (sg >= 4 and abs(t) >= 2) else "ΔΕΝ ΠΕΡΝΑ"} — ΦΟΡΑ: ο πιο ταξιδεμενος τα πηγε {"ΚΑΛΥΤΕΡΑ" if b > 0 else "χειροτερα"} απο την αγορα (αντιθετα απο «κουραση» αν +)')
P('  σημ.: ημερολογιο ΧΩΡΙΣ εγχωρια κυπελλα· 2122 χωρις live μοντελο (στηλες μοντ/xG μονο 2223+)· νοκ-αουτ με παραταση: διαφορα απο FotMob.')
