"""
core7_blind_scan.py — 29/9/2026 ΤΕΣΤ 2: ΤΥΦΛΗ ΣΑΡΩΣΗ ΑΓΟΡΩΝ στα εγχωρια (CORE7, 2223-2526) — ΧΩΡΙΣ μοντελο, οπως intl_market_pockets.
Κανονες «παιζω ΚΑΘΕ φορα Χ σε κατασταση Ψ» στις τιμες κλεισιματος. ΜΟΝΟ τεστ.
ΑΓΟΡΕΣ: AH Pinnacle closing (4 σεζον· 2ο βιβλιο: Avg closing 2223-24 + Crown/Nowgoal 2425-26)
        1Χ2 Pinnacle closing (2223-24· 2ο: Bet365 closing) · O/U 2.5 Avg closing (2223-24· 2ο: Bet365 closing).
ΕΠΙΛΟΓΕΣ AH: αουτσαιντερ / φαβορι / γηπεδουχος / φιλοξενουμενος / γηπ.-dog / φιλοξ.-dog / γηπ.-φαβ / φιλοξ.-φαβ.
            1Χ2: 1 / Χ / 2 / φαβορι 1Χ2 / αουτσαιντερ 1Χ2 · O/U: over / under.
ΚΑΤΑΣΤΑΣΕΙΣ: ολα · φαση (αγων. 1-6 / 7-14 / 15 ως −7 / τελευταιες 6) · βαθος γραμμης AH (0-0.25 / 0.5-0.75 / 1-1.25 / 1.5-1.75 / ≥2) ·
  ευρωπαϊκο ≤4 μερες πριν (φαβορι / αουτσαιντερ) · νεοφωτιστος (φαβορι / αουτσαιντερ) · προηγουμενο αποτελεσμα ομαδας της επιλογης
  (νικη / ισοπαλια / ηττα / βαρια ηττα ≥3) · λιγκα.
ΠΡΟ-ΔΗΛΩΣΗ (ιδια με εθνικες): κελι «περνα» αν n≥60, ROI≥+3%, θετικο σε ≥3/4 σεζον (2/2 οπου 2 σεζον), t≥1.5 ΚΑΙ ROI>0 στο 2ο βιβλιο.
Με ~300 κελια αναμενονται ~15-20 «τυχαια» με t≥1.5 → μονο οσα εχουν ΚΑΙ μηχανισμο αξιζουν επομενο βημα.
"""
import sys, json, glob
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
src = open('sos_test.py', encoding='utf-8').read(); ns = {}; exec(src[:src.index('# ---------- team ratings')], ns)
P = pd.read_csv('europe_test_preds_all.csv', dtype={'season': str}); P = P[P.gd.notna()].copy(); P['mid'] = P.mid.astype(str)
P['date'] = pd.to_datetime(P.date)
LG = sorted(P.league.unique()); SEAS = sorted(P.season.unique())
reg, res = ns['build_odds_layer'](LG, SEAS)
def f(o, k):
    v = o.get(k) if o is not None else None
    try:
        return float(v) if v is not None and pd.notna(v) else np.nan
    except (TypeError, ValueError):
        return np.nan                       # κελια τυπου '#' στα αρχεια football-data
# Crown closing (Nowgoal) για 2425-26
def pl(g):
    s = str(g)
    if '/' in s:
        a, b = s.split('/'); return (float(a) + float(b)) / 2
    return float(s)
CROWN = {}
for fn in glob.glob('nowgoal_odds/2425_*.jsonl') + glob.glob('nowgoal_odds/2526_*.jsonl'):
    for ln in open(fn, encoding='utf-8'):
        r = json.loads(ln)
        if r.get('cid') != 3: continue
        rows = []
        for x in r.get('ah') or []:
            try: rows.append((int(x[0]), -pl(x[2]), float(x[1]) + 1, float(x[3]) + 1))
            except Exception: pass
        if rows:
            prev = CROWN.get(str(r['mid']))
            last = max(rows)
            if prev is None or last[0] > prev[0]: CROWN[str(r['mid'])] = last
rows = []
for _, r in P.iterrows():
    g = ns['reg_of'](r['season']); o = picks.match_odds(reg[g]['Om'], r['season'], res[g](r['home_name']), res[g](r['away_name']), r['date'])
    if o is None: continue
    L, ah, aa = f(o, 'AHCh'), f(o, 'PCAHH'), f(o, 'PCAHA')
    if L != L: continue
    b2 = (L, f(o, 'AvgCAHH'), f(o, 'AvgCAHA'))
    if (b2[1] != b2[1]) and r.mid in CROWN:
        c = CROWN[r.mid]; b2 = (c[1], c[2], c[3])
    rows.append(dict(mid=r.mid, league=r.league, season=r.season, date=r.date, md=int(r.md), h=r.home, a=r.away, gd=int(r.gd),
                     hg=f(o, 'FTHG'), ag=f(o, 'FTAG'), L=L, ah=ah, aa=aa, L2=b2[0], ah2=b2[1], aa2=b2[2],
                     o1=f(o, 'PSCH'), ox=f(o, 'PSCD'), o2=f(o, 'PSCA'), b1=f(o, 'B365CH'), bx=f(o, 'B365CD'), b2_=f(o, 'B365CA'),
                     ov=f(o, 'AvgC>2.5'), un=f(o, 'AvgC<2.5'), bov=f(o, 'B365C>2.5'), bun=f(o, 'B365C<2.5')))
D = pd.DataFrame(rows).sort_values(['league', 'season', 'date']).reset_index(drop=True)
print(f'ματς με closing AH: {len(D)} · 2ο βιβλιο AH: {D.ah2.notna().sum()} · 1Χ2: {D.o1.notna().sum()} · O/U: {D.ov.notna().sum()}')
# φαση: αγωνιστικες συνολο ανα λιγκα-σεζον
tot = D.groupby(['league', 'season']).md.transform('max') + 1
D['phase'] = np.where(D.md <= 5, '1-6', np.where(D.md <= 13, '7-14', np.where(D.md >= tot - 6, 'τελευταιες 6', '15 ως −7')))
# νεοφωτιστοι: ομαδα που δεν υπηρχε στη λιγκα την προηγουμενη σεζον
TG = pd.read_csv('teamgame_inputs_5s_wf.csv', dtype={'season': str})
TEAMS = {(lg, s): set(g.team) for (lg, s), g in TG.groupby(['league', 'season'])}
prevs = {'2223': '2122', '2324': '2223', '2425': '2324', '2526': '2425'}
D['h_promo'] = [h not in TEAMS.get((lg, prevs[s]), {h}) for h, lg, s in zip(D.h, D.league, D.season)]
D['a_promo'] = [a not in TEAMS.get((lg, prevs[s]), {a}) for a, lg, s in zip(D.a, D.league, D.season)]
# ευρωπαϊκο ≤4 μερες
FL = pd.read_csv('europe_flags.csv'); FL['mid'] = FL.mid.astype(str); EU = {(m, t): d for m, t, d in zip(FL.mid, FL.team, FL.eu_prev_days)}
D['h_eu'] = [EU.get((m, t), np.nan) <= 4 for m, t in zip(D.mid, D.h)]; D['a_eu'] = [EU.get((m, t), np.nan) <= 4 for m, t in zip(D.mid, D.a)]
# προηγουμενο αποτελεσμα (ιδια σεζον+λιγκα, απο preds_all)
last = {}; hl, al = [], []
for r in D.sort_values('date').itertuples():
    hl.append((r.Index, last.get((r.h, r.season)))); al.append((r.Index, last.get((r.a, r.season))))
    last[(r.h, r.season)] = r.gd; last[(r.a, r.season)] = -r.gd
D['h_last'] = pd.Series(dict(hl)); D['a_last'] = pd.Series(dict(al))
def lastlab(x):
    if x is None or x != x: return None
    return 'βαρια ηττα ≥3' if x <= -3 else ('ηττα' if x < 0 else ('ισοπαλια' if x == 0 else 'νικη'))

# ---- στοιχηματα ανα πλευρα AH ----
AH = []
for r in D.itertuples():
    for side, ud, odds, ud2, odds2 in ((1, r.L, r.ah, r.L2, r.ah2), (-1, -r.L, r.aa, -r.L2 if r.L2 == r.L2 else np.nan, r.aa2)):
        if not (odds == odds): continue
        role = 'dog' if ud > 0 else ('fav' if ud < 0 else 'pk')
        pnl = picks.settle(r.gd, side, ud, odds)
        pnl2 = picks.settle(r.gd, side, ud2, odds2) if odds2 == odds2 and ud2 == ud2 else np.nan
        me = 'h' if side == 1 else 'a'
        AH.append(dict(season=r.season, league=r.league, phase=r.phase, side='γηπ' if side == 1 else 'φιλοξ', role=role, depth=abs(ud),
                       eu_me=getattr(r, me + '_eu'), promo_me=getattr(r, me + '_promo'), last_me=lastlab(getattr(r, me + '_last')), pnl=pnl, pnl2=pnl2))
A = pd.DataFrame(AH)
def depthlab(x):
    return '0-0.25' if x <= 0.25 else ('0.5-0.75' if x <= 0.75 else ('1-1.25' if x <= 1.25 else ('1.5-1.75' if x <= 1.75 else '≥2')))
A['dep'] = A.depth.map(depthlab)
SEL = {'αουτσαιντερ': A.role == 'dog', 'φαβορι': A.role == 'fav', 'γηπεδουχος': A.side == 'γηπ', 'φιλοξενουμενος': A.side == 'φιλοξ',
       'γηπ.-αουτσ.': (A.side == 'γηπ') & (A.role == 'dog'), 'φιλοξ.-αουτσ.': (A.side == 'φιλοξ') & (A.role == 'dog'),
       'γηπ.-φαβ.': (A.side == 'γηπ') & (A.role == 'fav'), 'φιλοξ.-φαβ.': (A.side == 'φιλοξ') & (A.role == 'fav')}
COND = {'ολα': np.ones(len(A), bool)}
for ph in ('1-6', '7-14', '15 ως −7', 'τελευταιες 6'): COND[f'φαση {ph}'] = (A.phase == ph).values
for dp in ('0-0.25', '0.5-0.75', '1-1.25', '1.5-1.75', '≥2'): COND[f'γραμμη {dp}'] = (A.dep == dp).values
COND['με ευρωπαϊκο ≤4μ'] = A.eu_me.values.astype(bool); COND['νεοφωτιστος'] = A.promo_me.values.astype(bool)
for lr in ('νικη', 'ισοπαλια', 'ηττα', 'βαρια ηττα ≥3'): COND[f'πριν: {lr}'] = (A.last_me == lr).values
for lg in LG: COND[f'{lg}'] = (A.league == lg).values
out = []
def cell(mkt, sel, cond, d, n_seas):
    if len(d) < 60: return
    roi = d.pnl.mean(); se = d.pnl.std() / np.sqrt(len(d)); ps = d.groupby('season').pnl.mean()
    r2 = d.pnl2.mean() if d.pnl2.notna().sum() >= 30 else np.nan
    out.append(dict(αγορα=mkt, επιλογη=sel, κατασταση=cond, n=len(d), ROI=roi, t=roi / se if se > 0 else 0, θετ=int((ps > 0).sum()), σεζ=len(ps), ROI_2ο=r2, n_seas=n_seas))
for sn, sm in SEL.items():
    for cn, cm in COND.items():
        cell('AH', sn, cn, A[sm.values & cm], 4)
# ---- 1Χ2 ----
X = []
for r in D[D.o1.notna()].itertuples():
    for lab, odds, odds2, hit in (('1', r.o1, r.b1, r.gd > 0), ('Χ', r.ox, r.bx, r.gd == 0), ('2', r.o2, r.b2_, r.gd < 0)):
        fav = odds == min(r.o1, r.o2) and lab != 'Χ'; dog = odds == max(r.o1, r.o2) and lab != 'Χ'
        me = 'h' if lab == '1' else ('a' if lab == '2' else None)
        X.append(dict(season=r.season, league=r.league, phase=r.phase, out=lab, fav=fav, dog=dog, odds=odds,
                      eu_me=bool(getattr(r, me + '_eu')) if me else False, promo_me=bool(getattr(r, me + '_promo')) if me else False,
                      pnl=(odds - 1) if hit else -1.0, pnl2=((odds2 - 1) if hit else -1.0) if odds2 == odds2 else np.nan))
Xd = pd.DataFrame(X)
S1 = {'1 (γηπ)': Xd.out == '1', 'Χ': Xd.out == 'Χ', '2 (φιλοξ)': Xd.out == '2', 'φαβορι 1Χ2': Xd.fav, 'αουτσαιντερ 1Χ2': Xd.dog,
      'φαβορι ≥70% (τιμη<1.43)': Xd.fav & (Xd.odds < 1.43), 'αουτσ. τιμη≥5': Xd.dog & (Xd.odds >= 5)}
C1 = {'ολα': np.ones(len(Xd), bool)}
for ph in ('1-6', '7-14', '15 ως −7', 'τελευταιες 6'): C1[f'φαση {ph}'] = (Xd.phase == ph).values
C1['με ευρωπαϊκο ≤4μ'] = Xd.eu_me.values; C1['νεοφωτιστος'] = Xd.promo_me.values
for lg in LG: C1[lg] = (Xd.league == lg).values
for sn, sm in S1.items():
    for cn, cm in C1.items():
        cell('1Χ2', sn, cn, Xd[sm.values & cm], 2)
# ---- O/U 2.5 ----
O = []
for r in D[D.ov.notna() & D.hg.notna()].itertuples():
    t = r.hg + r.ag; closeg = abs(r.L) <= 0.25
    for lab, odds, odds2, hit in (('over', r.ov, r.bov, t > 2.5), ('under', r.un, r.bun, t < 2.5)):
        O.append(dict(season=r.season, league=r.league, phase=r.phase, out=lab, closeg=closeg, big=abs(r.L) >= 1.5, eu=bool(r.h_eu or r.a_eu),
                      promo=bool(r.h_promo or r.a_promo), pnl=(odds - 1) if hit else -1.0, pnl2=((odds2 - 1) if hit else -1.0) if odds2 == odds2 else np.nan))
Od = pd.DataFrame(O)
C2 = {'ολα': np.ones(len(Od), bool), 'κοντινα (AH ≤0.25)': Od.closeg.values, 'ανισοπαλα (AH ≥1.5)': Od.big.values,
      'ευρωπαϊκο ≤4μ (καποια ομαδα)': Od.eu.values, 'νεοφωτιστος στο ματς': Od.promo.values}
for ph in ('1-6', '7-14', '15 ως −7', 'τελευταιες 6'): C2[f'φαση {ph}'] = (Od.phase == ph).values
for lg in LG: C2[lg] = (Od.league == lg).values
for sn in ('over', 'under'):
    for cn, cm in C2.items():
        cell('O/U 2.5', sn, cn, Od[(Od.out == sn).values & cm], 2)
R = pd.DataFrame(out)
R['ΠΕΡΝΑ'] = (R.n >= 60) & (R.ROI >= 0.03) & (R.θετ >= np.where(R.n_seas == 4, 3, 2)) & (R.t >= 1.5) & (R.ROI_2ο > 0)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 400)
fmt = R.assign(ROI=(100 * R.ROI).round(1), t=R.t.round(1), ROI_2ο=(100 * R.ROI_2ο).round(1))
print(f'\nΚΕΛΙΑ που ελεγχθηκαν: {len(R)} (AH {int((R.αγορα == "AH").sum())} · 1Χ2 {int((R.αγορα == "1Χ2").sum())} · O/U {int((R.αγορα == "O/U 2.5").sum())})'
      f' · με t≥1.5: {int((R.t >= 1.5).sum())} · ΠΕΡΝΟΥΝ ολα τα κριτηρια: {int(R.ΠΕΡΝΑ.sum())}')
print('\n=== ΠΕΡΝΟΥΝ ===')
print(fmt[R.ΠΕΡΝΑ].sort_values('t', ascending=False)[['αγορα', 'επιλογη', 'κατασταση', 'n', 'ROI', 't', 'θετ', 'σεζ', 'ROI_2ο']].to_string(index=False))
print('\n=== ΚΟΝΤΑ (t≥1.5 αλλα κοβεται σε καποιο κριτηριο) ===')
print(fmt[(R.t >= 1.5) & ~R.ΠΕΡΝΑ].sort_values('t', ascending=False).head(15)[['αγορα', 'επιλογη', 'κατασταση', 'n', 'ROI', 't', 'θετ', 'σεζ', 'ROI_2ο']].to_string(index=False))
print('\n=== ΧΕΙΡΟΤΕΡΑ (η αγορα «κερδιζει») ===')
print(fmt.sort_values('t').head(8)[['αγορα', 'επιλογη', 'κατασταση', 'n', 'ROI', 't', 'θετ', 'σεζ']].to_string(index=False))
print('\nΒΑΣΗ (ολα): ' + ' · '.join(f"{r.αγορα} {r.επιλογη} {100*r.ROI:+.1f}%" for r in R[R.κατασταση == 'ολα'].itertuples()))
R.to_csv('core7_blind_scan_cells.csv', index=False)
