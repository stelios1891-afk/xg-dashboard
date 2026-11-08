"""
core7_motivation_test.py — 29/9/2026 (Στελιος: «τελευταιες αγωνιστικες — αδιαφοροι/ενδιαφερομενοι· η αγορα ριχνει πολυ τις τιμες λογω
κινητρου και το μοντελο βγαζει κοντρα· Caley: οι αδιαφοροι δεν παιζουν τοσο σαν αδιαφοροι»). ΜΟΝΟ τεστ.
CORE7 2223-2526, ολα τα ματς (europe_test_preds_all.csv· μοντελο = live μηχανη, τιμολογηση live = Dixon-Coles), closing/opening Pinnacle AH.
ΖΩΝΕΣ ανα λιγκα (προσεγγιση· extra θεσεις απο κυπελλο/συντελεστη αγνοουνται): (UCL, Ευρωπη, υποβιβασμος μαζι με μπαραζ)
  EPL/LaLiga/SerieA/Bundesliga 4/7/3 · Ligue1 4/6/3 · Eredivisie 2/8/3 · Primeira 2/5/3· + τιτλος (1η θεση).
ΚΙΝΗΤΡΟ (βαθμολογια ΠΡΙΝ το ματς, υπολοιπα ματς καθε ομαδας):
  ΜΑΘΗΜΑΤΙΚΑ αδιαφορος = δεν μπορει να περασει κανενα οριο ζωνης προς τα πανω (πονταρει max πονταρισμα 3·υπολ. vs τωρινοι βαθμοι της θεσης)
      ουτε να πεσει προς τα κατω (η ομαδα απο κατω δεν τη φτανει με 3·υπολ. της).
  ΠΡΑΚΤΙΚΑ αδιαφορος = καθε οριο απεχει > 1.5 βαθμο × υπολοιπα ματς (θα χρειαζοταν σχεδον σερι).
ΚΑΤΑΣΤΑΣΕΙΣ: και οι δυο ενδιαφερονται · αδιαφορο μονο το ΦΑΒΟΡΙ · αδιαφορο μονο το ΑΟΥΤΣΑΙΝΤΕΡ · ΚΑΙ ΟΙ ΔΥΟ αδιαφοροι (φαβορι = αγορα).
Υπολοιπες αγωνιστικες: 1-2 / 3-4 / 5-6 / 7-8.
ΜΕΤΡΑ: (1) τιμωρια αγορας = υπεροχη αγορας − υπεροχη μοντελου για τον αδιαφορο· κινηση opening→closing κοντρα στον αδιαφορο.
       (2) πραγματικο − αγορα για τον αδιαφορο (αν <0 η αγορα εχει δικιο, αν ≈0/>0 «δεν παιζουν σαν αδιαφοροι»).
       (3) ROI: τυφλο υπερ/κοντρα στον αδιαφορο (closing) · picks μοντελου (κανονες live: +handicap ≥0.5 dogs· και φαβορι ≤−0.5, edge≥10%).
"""
import sys
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
    try: return float(v) if v is not None and pd.notna(v) else np.nan
    except (TypeError, ValueError): return np.nan
_c = {}
def sup(line, oh, oa, T=2.7):
    key = (line, oh, oa)
    if key in _c: return _c[key]
    kk = 1 / oh + 1 / oa; tgt = (1 / oh) / kk; lo, hi = -5.0, 5.0
    parts = [line] if (line * 4) % 2 == 0 else [line - .25, line + .25]
    for _ in range(34):
        md = (lo + hi) / 2; d = picks.gd_dist_dom(max((T + md) / 2, .05), max((T - md) / 2, .05))
        c = [picks.p_cover(d, 1, L) for L in parts]; pe = sum(a for a, _ in c) / max(sum(1 - b for _, b in c), 1e-9)
        lo, hi = (md, hi) if pe < tgt else (lo, md)
    _c[key] = (lo + hi) / 2; return _c[key]
ZONES = {'EPL': (4, 7, 3), 'LaLiga': (4, 7, 3), 'SerieA': (4, 7, 3), 'Bundesliga': (4, 7, 3), 'Ligue1': (4, 6, 3), 'Eredivisie': (2, 8, 3), 'PrimeiraLiga': (2, 5, 3)}
rows = []
for (lg, sea), G in P.sort_values(['date', 'mid']).groupby(['league', 'season']):
    teams = sorted(set(G.home) | set(G.away)); n = len(teams); tot = 2 * (n - 1)
    ucl, eur, rel = ZONES[lg]; bounds = [1, ucl, eur, n - rel]
    pts = {t: 0 for t in teams}; pl = {t: 0 for t in teams}
    def status(t, tab, pos):
        p, rem = pts[t], tot - pl[t]; strict = False; practical = False
        for k in bounds:
            if pos[t] <= k:                       # πανω απο το οριο: μπορει να πεσει;
                nxt = tab[k]; reach = pts[nxt] + 3 * (tot - pl[nxt]); gap = p - pts[nxt]
            else:                                  # κατω: μπορει να ανεβει;
                reach_p = p + 3 * rem; gap = pts[tab[k - 1]] - p; reach = None
            if reach is not None:
                if reach >= p: strict = True
            else:
                if reach_p >= pts[tab[k - 1]]: strict = True
            if gap <= 1.5 * rem: practical = True
        return strict, practical            # True = ενδιαφερεται (ζωντανο οριο)
    for r in G.itertuples():
        tab = sorted(teams, key=lambda t: (-pts[t]))
        pos = {t: i + 1 for i, t in enumerate(tab)}
        remh, rema = tot - pl[r.home], tot - pl[r.away]
        rem = min(remh, rema)          # υπολοιπα ματς (περιλαμβανει το τρεχον)
        if rem <= 8:
            sh, ph = status(r.home, tab, pos); sa, pa = status(r.away, tab, pos)
            rows.append(dict(mid=r.mid, league=lg, season=sea, rem=rem, home=r.home_name, away=r.away_name, gd=int(r.gd), xh=r.xg_h, xa=r.xg_a, date=r.date,
                             h_alive_s=sh, a_alive_s=sa, h_alive_p=ph, a_alive_p=pa, hpos=pos[r.home], apos=pos[r.away]))
        pts[r.home] += 3 if r.gd > 0 else (1 if r.gd == 0 else 0); pts[r.away] += 3 if r.gd < 0 else (1 if r.gd == 0 else 0)
        pl[r.home] += 1; pl[r.away] += 1
D = pd.DataFrame(rows)
odds = {}
for _, r in P[P.mid.isin(set(D.mid))].iterrows():
    g = ns['reg_of'](r['season']); o = picks.match_odds(reg[g]['Om'], r['season'], res[g](r['home_name']), res[g](r['away_name']), r['date'])
    if o is None: continue
    odds[r['mid']] = (f(o, 'AHCh'), f(o, 'PCAHH'), f(o, 'PCAHA'), f(o, 'AHh'), f(o, 'PAHH'), f(o, 'PAHA'))
D['L'] = D.mid.map(lambda m: odds.get(m, (np.nan,) * 6)[0]); D['ah'] = D.mid.map(lambda m: odds.get(m, (np.nan,) * 6)[1]); D['aa'] = D.mid.map(lambda m: odds.get(m, (np.nan,) * 6)[2])
D['Lo'] = D.mid.map(lambda m: odds.get(m, (np.nan,) * 6)[3]); D['aho'] = D.mid.map(lambda m: odds.get(m, (np.nan,) * 6)[4]); D['aao'] = D.mid.map(lambda m: odds.get(m, (np.nan,) * 6)[5])
D = D[D.L.notna() & D.ah.notna()].reset_index(drop=True)
D['s_mkt'] = [sup(L, a, b) for L, a, b in zip(D.L, D.ah, D.aa)]
D['s_open'] = [sup(L, a, b) if L == L and a == a and b == b else np.nan for L, a, b in zip(D.Lo, D.aho, D.aao)]
D['s_mod'] = D.xh.clip(.05, 6) - D.xa.clip(.05, 6)
D['fav_home'] = D.s_mkt >= 0
print(f'ματς τελευταιων 8 αγωνιστικων με closing: {len(D)} · υπολοιπα: ' + str(D.rem.value_counts().sort_index().to_dict()))
for defn in ('s', 'p'):
    al_h, al_a = D[f'h_alive_{defn}'], D[f'a_alive_{defn}']
    fav_alive = np.where(D.fav_home, al_h, al_a); dog_alive = np.where(D.fav_home, al_a, al_h)
    D[f'state_{defn}'] = np.where(fav_alive & dog_alive, 'και οι δυο ενδιαφερονται', np.where(~fav_alive & dog_alive, 'αδιαφορο ΜΟΝΟ το φαβορι',
                          np.where(fav_alive & ~dog_alive, 'αδιαφορο ΜΟΝΟ το αουτσαιντερ', 'ΚΑΙ ΟΙ ΔΥΟ αδιαφοροι')))
REMB = [('1-2', 1, 2), ('3-4', 3, 4), ('5-6', 5, 6), ('7-8', 7, 8)]
STATES = ['και οι δυο ενδιαφερονται', 'αδιαφορο ΜΟΝΟ το φαβορι', 'αδιαφορο ΜΟΝΟ το αουτσαιντερ', 'ΚΑΙ ΟΙ ΔΥΟ αδιαφοροι']

def analyse(defn, lab):
    print(f'\n{"=" * 110}\n{lab}\n{"=" * 110}')
    S = D[f'state_{defn}']
    print('  πληθος ματς ανα κατασταση × υπολοιπες αγωνιστικες:')
    print('   ' + ' | '.join(f'{st}: ' + ' '.join(f'{b}:{int(((S == st) & D.rem.between(lo, hi)).sum())}' for b, lo, hi in REMB) for st in STATES))
    # σκοπια: για «μονο φαβορι αδιαφορο» -> πλευρα φαβορι· «μονο αουτσαιντερ» -> πλευρα αουτσαιντερ· αλλιως φαβορι
    print('\n  (1)-(2) σκοπια της ΑΔΙΑΦΟΡΗΣ ομαδας (για «και οι δυο»/«κανενας» σκοπια φαβορι). γκολ:')
    print(f"  {'κατασταση':32s} {'n':>5s} {'αγορα−μοντελο':>14s} {'κινηση open→close':>18s} {'πραγματικο−αγορα':>18s} {'πραγματικο−μοντελο':>19s}")
    for st in STATES:
        d = D[S == st]
        if len(d) < 15: print(f'  {st:32s} {len(d):5d}  —'); continue
        side = np.where(d.fav_home, 1, -1) if st != 'αδιαφορο ΜΟΝΟ το αουτσαιντερ' else np.where(d.fav_home, -1, 1)
        mm = side * (d.s_mkt - d.s_mod); mv = side * (d.s_mkt - d.s_open); am = side * (d.gd - d.s_mkt); ao = side * (d.gd - d.s_mod)
        se = lambda x: np.nanstd(x) / np.sqrt(np.sum(~np.isnan(x)))
        print(f"  {st:32s} {len(d):5d} {np.nanmean(mm):+8.2f} ±{se(mm):.2f} {np.nanmean(mv):+10.3f} ±{se(mv):.3f} {np.nanmean(am):+10.2f} ±{se(am):.2f} {np.nanmean(ao):+11.2f} ±{se(ao):.2f}")
    print('\n  (3) ROI (closing Pinnacle): τυφλο ΥΠΕΡ της αδιαφορης ομαδας · τυφλο ΚΟΝΤΡΑ · picks μοντελου (dogs +≥0.5 & φαβορι ≤−0.5, edge≥10%, 1.70-2.10)')
    for st in STATES:
        d = D[S == st]
        if len(d) < 15: continue
        blind_for, blind_ag, mp, mp_for = [], [], [], []
        for r in d.itertuples():
            if st == 'αδιαφορο ΜΟΝΟ το αουτσαιντερ': dside = -1 if r.fav_home else 1
            else: dside = 1 if r.fav_home else -1
            for side, ud, o in ((1, r.L, r.ah), (-1, -r.L, r.aa)):
                pn = picks.settle(r.gd, side, ud, o)
                (blind_for if side == dside else blind_ag).append(pn)
                if 1.70 <= o <= 2.10 and abs(ud) >= 0.5:
                    dist = picks.gd_dist_dom(max(r.xh, .05), max(r.xa, .05)); pw, pp = picks.p_cover(dist, side, ud)
                    if pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp) >= 0.10:
                        mp.append(pn); mp_for.append(side == dside)
        mp = np.array(mp); mp_for = np.array(mp_for, bool)
        def fm(x): return f'{100*np.mean(x):+.1f}% (n{len(x)}, ±{100*np.std(x)/np.sqrt(max(len(x),1)):.1f})' if len(x) else '—'
        print(f"  {st:32s} υπερ αδιαφορου {fm(blind_for)} · κοντρα {fm(blind_ag)} · picks μοντελου {fm(mp)} [υπερ αδιαφορου {fm(mp[mp_for])} / κοντρα {fm(mp[~mp_for])}]")
    print('\n  ανα υπολοιπες αγωνιστικες — πραγματικο−αγορα για την αδιαφορη ομαδα (μονο «αδιαφορο ΜΟΝΟ φαβορι» + «ΜΟΝΟ αουτσαιντερ» μαζι):')
    for b, lo, hi in REMB:
        d = D[S.isin(STATES[1:3]) & D.rem.between(lo, hi)]
        if len(d) < 15: print(f'   {b}: n{len(d)} —'); continue
        side = np.where(S[d.index] == STATES[1], np.where(d.fav_home, 1, -1), np.where(d.fav_home, -1, 1))
        am = side * (d.gd - d.s_mkt); mm = side * (d.s_mkt - d.s_mod)
        print(f'   {b}: n{len(d)} · αγορα−μοντελο {np.mean(mm):+.2f} · πραγματικο−αγορα {np.mean(am):+.2f} ±{np.std(am)/np.sqrt(len(d)):.2f}')
analyse('s', 'ΟΡΙΣΜΟΣ Α — ΜΑΘΗΜΑΤΙΚΑ αδιαφορος (τιποτα δεν μπορει να αλλαξει)')
analyse('p', 'ΟΡΙΣΜΟΣ Β — ΠΡΑΚΤΙΚΑ αδιαφορος (καθε οριο > 1.5 βαθμο ανα υπολοιπο ματς)')
D.to_csv('core7_motivation_rows.csv', index=False)
