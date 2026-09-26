"""
intl_window_test.py — ΤΕΣΤ «ΠΑΡΑΘΥΡΟΥ» (25/9/2026, αιτημα Στελιου): μετρα τα picks ΟΠΩΣ ΘΑ ΠΑΙΖΟΝΤΑΝ, οχι μονο στο closing.
Παραδειγματα που το closing χανει: Ιταλια−Βελγιο (over που εξαφανιστηκε γιατι η γραμμη ηρθε προς εμας), Πορτογαλια (φαβορι χαντικαπ, ιδιο).

ΠΡΟ-ΔΗΛΩΣΗ (πριν τρεξει):
  Δεδομενα: ιδια καθαρα δεδομενα/LOSO/τιμολογηση με intl_model_choice_v3.py (ratings ανα ματς = γνωστα πριν το ματς, σταθερα μεσα στο παραθυρο).
  Γραμμες: ΟΛΕΣ οι pre-match κινησεις Nowgoal με χρονοσφραγιδα (Crown = κυριο, SBOBET = επιβεβαιωση).
  ΠΑΡΑΘΥΡΟ (κυριο): τελευταιες 72 ωρες πριν τη σεντρα (Στελιος: «max 3 μερες πριν»). Για πληροφορια και 48ω / 24ω.
  Κανονας bet: σαρωνουμε τις κινησεις χρονολογικα· η ΠΡΩΤΗ κινηση οπου ο live κανονας περναει = bet σε αυτη τη γραμμη/τιμη
     (ενα bet ανα ματς/αγορα/μοντελο). Live κανονες: AH |γραμμη| ≥0.5, τιμη 1.70-2.10, edge ≥10% · OVER edge ≥8% ΚΑΙ (κοντινο ή νοκ-αουτ) ·
     νεκρο ματς = τιποτα.
  Συγκριση: (α) μονο closing (τελευταια κινηση — οπως το backtest), (β) παραθυρο 72ω, (γ) τα bets του παραθυρου που ΔΕΝ υπαρχουν στο closing
     (οι περιπτωσεις «Ιταλια−Βελγιο»), (δ) CLV των bets του παραθυρου απεναντι στο closing χωρις γκανιοτα.
  Περιγραφικο — δεν αλλαζει κανονα. Εξοδος: intl_window_test_out.txt, intl_window_test_bets.csv
"""
import sys, json, glob, math, os
MODE = os.environ.get('WIN_MODE', 'first')   # first | next (τιμη επομενης κινησης) | persist30 (πρεπει να ισχυει ≥30λ)
SUF = '' if MODE == 'first' else '_' + MODE
OVER_FORMULA = os.environ.get('OVER_FORMULA', 'live')   # live = P(συνολο>floor(γραμμη))·τιμη−1 (οπως το live) | proper = σωστο EV με push/μισα (25/9)
if OVER_FORMULA != 'live':
    SUF = SUF + '_' + OVER_FORMULA
AH_FORMULA = os.environ.get('AH_FORMULA', 'live')      # live = picks.p_cover (τεταρτα σαν μισες) | proper = μισο/μισο στις διπλανες γραμμες
if AH_FORMULA != 'live':
    SUF = SUF + '_ah' + AH_FORMULA
OVER_ALL = os.environ.get('OVER_ALL') == '1'          # 1 = over και σε ΜΗ κοντινα ματς (για συγκριση· ο live κανονας θελει κοντινο ή KO)
if OVER_ALL:
    SUF = SUF + '_overall'
AH_MINLINE = float(os.environ.get('AH_MINLINE', '0.5'))   # 25/9: 0 = και DNB (γραμμη 0) και ±0.25 (ερωτηση Στελιου)· live = 0.5
if AH_MINLINE != 0.5:
    SUF = SUF + f'_min{AH_MINLINE:g}'
IMP_S4 = os.environ.get('IMP_S4') == '1'     # 25/9: σημασια παικτη Σ4 (συμμετοχες×rating×αρχηγος) στο diff, συντελεστης LOSO ανα σεζον (intl_imp_s4_export.py)
if IMP_S4:
    SUF = SUF + '_s4'
T_MODE = os.environ.get('T_MODE', 'live')   # 26/9: live = T σημερα · mix = T σημερα + xG επιθεσης/αμυνας ομαδων (βαρη LOSO ανα σεζον στα γκολ)
if T_MODE != 'live':
    SUF = SUF + '_T' + T_MODE + (f"N{os.environ['XG_N']}" if os.environ.get('XG_N') else '')
GD_FIX = os.environ.get('GD_FIX', 'none')   # 25/9 διορθωση dogs: none | slope (κλιση υπεροχης ανα μοντελο, LOSO) | shape (slope + κοινα γκολ λ3, LOSO)
if GD_FIX != 'none':
    SUF = SUF + '_gd' + GD_FIX


def _pk(T, k):
    return math.exp(-T) * T ** k / math.factorial(k)


def over_ev(T, line, odds):
    """edge (αναμενομενη αποδοση) του over. live: οπως ο κωδικας του live· proper: τεταρτα = μισο/μισο, ακεραια = push επιστρεφει."""
    if OVER_FORMULA == 'live':
        return (1 - sum(_pk(T, k) for k in range(int(math.floor(line)) + 1))) * odds - 1
    q = round(line * 4) / 4
    if abs(q * 2 - round(q * 2)) > 1e-9:
        return 0.5 * over_ev(T, q - .25, odds) + 0.5 * over_ev(T, q + .25, odds)
    pw = 1 - sum(_pk(T, k) for k in range(int(math.floor(q)) + 1))
    pp = _pk(T, int(q)) if float(q).is_integer() else 0.0
    return pw * (odds - 1) - (1 - pw - pp)
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')

src = open('intl_model_choice_v3.py', encoding='utf-8').read()
G = {'__name__': 'window'}
exec(src[:src.index('bets = []')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass'), G)
D, MODELS, picks, T_of, p_over, ou_settle, A_GOAL = (G[k] for k in ('D', 'MODELS', 'picks', 'T_of', 'p_over', 'ou_settle', 'A_GOAL'))
print('#' * 40 + f' WINDOW TEST mode={MODE} over={OVER_FORMULA} ah={AH_FORMULA} over_all={OVER_ALL} ' + '#' * 40, flush=True)

M = pd.read_csv('intl_matches.csv', dtype={'mid': str})
KO = {m: pd.Timestamp(d).tz_localize('UTC').timestamp() for m, d in zip(M.mid, M.date)}


def hk(v):
    v = float(v); return v + 1 if v < 1.5 else v


def line_of(s):
    s = str(s)
    if '/' in s:
        a, b = s.split('/'); return (float(a) + float(b)) / 2
    return float(s)


def ok_row(x):
    return x[1] in ('', None) and not x[7] and x[4] not in (None, '') and x[5] not in (None, '', '0') and x[6] not in (None, '', '0')


ROWS = {}     # (mid, cid) -> {'ah': [(t, line_home, oh, oa)], 'ou': [(t, line, over, under)]}
for f in glob.glob('nowgoal_intl_odds/*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        r = json.loads(ln)
        if r.get('cid') not in (3, 31):
            continue
        mid = str(r['mid']); k = KO.get(mid)
        if k is None:
            continue
        rec = {'ah': [], 'ou': []}
        for x in (r.get('ah') or []):
            if ok_row(x) and x[0] < k:
                try: rec['ah'].append(((k - x[0]) / 3600, -line_of(x[4]), hk(x[5]), hk(x[6])))
                except Exception: pass
        for x in (r.get('ou') or []):
            if ok_row(x) and x[0] < k:
                try: rec['ou'].append(((k - x[0]) / 3600, line_of(x[4]), hk(x[5]), hk(x[6])))
                except Exception: pass
        rec['ah'].sort(key=lambda z: -z[0]); rec['ou'].sort(key=lambda z: -z[0])     # χρονολογικα (απο νωριτερα προς σεντρα)
        ROWS[(mid, 3 if r['cid'] == 3 else 31)] = rec


def sup_from_line(line, oh, oa, T):
    k = 1 / oh + 1 / oa; tgt = (1 / oh) / k; lo, hi = -4.0, 4.0
    for _ in range(40):
        md = (lo + hi) / 2; lh = max((T + md) / 2, 0.15); la = max((T - md) / 2, 0.15)
        pw, pp = picks.p_cover(picks.gd_dist(lh, la), 1, line); pe = pw / max(1 - pp, 1e-9)
        lo, hi = (md, hi) if pe < tgt else (lo, md)
    return (lo + hi) / 2


def ah_ev(dist, side, ud, odds):
    """edge AH. live: picks.p_cover στη γραμμη (τεταρτα = κοντινοτερη μιση). proper: τεταρτα = μισο στις δυο διπλανες γραμμες."""
    parts = [ud] if (AH_FORMULA == 'live' or (ud * 4) % 2 == 0) else [ud - 0.25, ud + 0.25]
    if AH_FORMULA == 'hybrid' and ud > 0 and abs(ud % 1 - 0.25) < 1e-9:      # 25/9 σχεδιο Β Στελιου: dog +x.25 με τον ΠΑΛΙΟ τροπο, ολα τα αλλα σωστα
        parts = [ud]
    e = 0.0
    for L in parts:
        pw, pp = picks.p_cover(dist, side, L); e += (pw * (odds - 1) * (1 - picks.MARGIN) - (1 - pw - pp)) / len(parts)
    return e


def ah_q(dist, line, oh, oa, dist_deep=None):
    for side, ud, odds in ((1, line, oh), (-1, -line, oa)):
        e = ah_ev(dist_deep if (dist_deep is not None and ud <= -2 + 1e-9) else dist, side, ud, odds)   # 25/9 deepfav: σωστη υπεροχη μονο για φαβορι −2 και βαθυτερα
        if 1.70 <= odds <= 2.10 and e >= .10 and abs(ud) >= AH_MINLINE - 1e-9:
            return side, ud, odds, e
    return None


# ---- 25/9 ΔΙΟΡΘΩΣΗ ΚΑΤΑΝΟΜΗΣ ΔΙΑΦΟΡΑΣ ΓΚΟΛ (LOSO: οι παραμετροι καθε σεζον απο τις ΑΛΛΕΣ σεζον, μονο αγωνιστικα, μονο αποτελεσματα — οχι αποδοσεις) ----
COMP = D.ctype.isin(['nl', 'qual', 'tourn'])
SEAS_ = sorted(D.season.unique()); GDP = {}
def _gd_ll(sub, m, a, l3):
    ll = 0.0
    for r in sub.itertuples():
        d_ = getattr(r, f'd_{m}'); T_ = T_of(d_, r); s_ = a * d_
        lh_, la_ = max((T_ + s_) / 2 - l3, .10), max((T_ - s_) / 2 - l3, .10)
        ll += math.log(max(picks.gd_dist(lh_, la_).get(int(r.gd), 1e-9), 1e-9))
    return ll
if GD_FIX != 'none':      # (deepfav = slope, αλλα εφαρμοζεται ΜΟΝΟ στα φαβορι −2 και βαθυτερα)
    for sea in SEAS_:
        tr = D[COMP & (D.season != sea)]
        for m in MODELS:
            dd = tr[f'd_{m}'].values.astype(float); a = float(np.sum(dd * tr.gd.values) / np.sum(dd ** 2))
            l3 = 0.0
            if GD_FIX == 'shape':
                l3 = max(np.arange(0, 0.61, 0.05), key=lambda z: _gd_ll(tr, m, a, z))
            GDP[(sea, m)] = (a, float(l3))
    for m in MODELS:
        print(f'  GD_FIX={GD_FIX} {m}: ' + ' · '.join(f'{sea} a={GDP[(sea, m)][0] * 100:.3f} λ3={GDP[(sea, m)][1]:.2f}' for sea in SEAS_), flush=True)


def model_dist(r, m, T, diff):
    if GD_FIX in ('none', 'deepfav'):
        s_ = A_GOAL * diff; return picks.gd_dist(max((T + s_) / 2, .15), max((T - s_) / 2, .15))
    a, l3 = GDP[(r.season, m)]; s_ = a * diff
    return picks.gd_dist(max((T + s_) / 2 - l3, .10), max((T - s_) / 2 - l3, .10))


# ---- 26/9 T_MODE=mix: T = b0 + b1·T_live + b2·(λh_xG + λa_xG)· λ απο intl_xg_totals.csv (walk-forward, 12 ματς, shrink, διορθωση αντιπαλου) ----
TMIX = {}; XGS = {}
if T_MODE == 'mix':
    if os.environ.get('XG_N'):      # 26/9: πληθος ματς για το xG ομαδων (intl_xg_team_windows.py)
        _X = pd.read_csv(f"intl_xg_teamN{os.environ['XG_N']}.csv", dtype={'mid': str}); _X = _X[_X.n >= 3]; XGS = dict(zip(_X.mid, _X.xgsum))
    else:
        _X = pd.read_csv('intl_xg_totals.csv', dtype={'mid': str}); XGS = dict(zip(_X.mid, _X.lh_xg + _X.la_xg))
    _C = D[D.ctype.isin(['nl', 'qual', 'tourn'])]
    for _sea in sorted(D.season.unique()):
        for _m in MODELS:
            _tr = [(T_of(getattr(r, f'd_{_m}'), r), XGS[str(r.mid)], r.tot) for r in _C[_C.season != _sea].itertuples() if str(r.mid) in XGS]
            _A = np.array([[1, a, b] for a, b, _ in _tr]); _y = np.array([t for _, _, t in _tr])
            TMIX[(_sea, _m)] = np.linalg.lstsq(_A, _y, rcond=None)[0]
    print('T_MODE=mix βαρη (b0, b1·T_live, b2·xG): ' + ' · '.join(f"{k[0]} {k[1]}: {v[0]:+.2f} {v[1]:.2f} {v[2]:.2f}" for k, v in TMIX.items() if k[1] == 'M1'), flush=True)


def T_final(diff, r, m):
    T0 = T_of(diff, r)
    if T_MODE != 'mix' or str(r.mid) not in XGS:
        return T0
    b = TMIX[(r.season, m)]; return max(b[0] + b[1] * T0 + b[2] * XGS[str(r.mid)], 0.8)


S4_D, S4_COEF = {}, {}
if IMP_S4:
    S4_D = dict(pd.read_csv('intl_imp_s4.csv', dtype={'mid': str}).values.tolist()); S4_COEF = json.load(open('intl_imp_s4_coef.json', encoding='utf-8'))
    print(f'Σ4: {len(S4_D)} ματς με dW6', flush=True)


bets = []
WINS = (('closing', None), ('72ω', 72), ('48ω', 48), ('24ω', 24))
if os.environ.get('WIN_HOURS'):      # καμπυλη: π.χ. WIN_HOURS=72,64,56,48 (25/9, ερωτηση Στελιου «ποτε ακριβως διακρινεται η αλλαγη»)
    WINS = (('closing', None),) + tuple((f'{h}ω', float(h)) for h in os.environ['WIN_HOURS'].split(','))
    SUF = SUF + '_curve'
for r in D.itertuples():
    if r.dead:
        continue
    for cid, book in ((3, 'Crown'), (31, 'SBOBET')):
        rec = ROWS.get((str(r.mid), cid))
        if not rec:
            continue
        cl_ah = rec['ah'][-1] if rec['ah'] else None; cl_ou = rec['ou'][-1] if rec['ou'] else None
        cdist = None
        if cl_ah:
            Tc = cl_ou[1] if cl_ou else 2.6; sc = sup_from_line(cl_ah[1], cl_ah[2], cl_ah[3], Tc)
            cdist = picks.gd_dist(max((Tc + sc) / 2, .15), max((Tc - sc) / 2, .15))
        for m in MODELS:
            diff = getattr(r, f'd_{m}') + (S4_COEF.get(str(r.season), {}).get(m, 0.0) * S4_D.get(str(r.mid), 0.0) if IMP_S4 else 0.0); T = T_final(diff, r, m)
            dist = model_dist(r, m, T, diff)      # 25/9: GD_FIX (none = ιδιο με πριν)
            dist_deep = None
            if GD_FIX == 'deepfav':
                a_, _l3 = GDP[(r.season, m)]; s_ = a_ * diff
                dist_deep = picks.gd_dist(max((T + s_) / 2, .15), max((T - s_) / 2, .15))
            base = dict(mid=r.mid, season=r.season, ctype=r.ctype, model=m, book=book, close=bool(r.close), ko=bool(r.ko))
            for wlab, W in WINS:
                # --- AH ---
                cand = [cl_ah] if (W is None and cl_ah) else [z for z in rec['ah'] if z[0] <= (W or 0)]
                for ci, (h, line, oh, oa) in enumerate(cand):
                    q = ah_q(dist, line, oh, oa, dist_deep)
                    if q and W is not None and MODE == 'persist30':
                        # πρεπει να ισχυει συνεχομενα ≥30λ: ολες οι κινησεις των επομενων 30λ περνανε κι αυτες τον κανονα
                        nxt = [z for z in cand[ci + 1:] if h - z[0] <= 0.5]
                        if any(ah_q(dist, z[1], z[2], z[3]) is None for z in nxt):
                            continue
                    if q and W is not None and MODE == 'next':
                        # εκτελεση με καθυστερηση: τιμη/γραμμη της ΕΠΟΜΕΝΗΣ κινησης, ιδια πλευρα (οποιο κι αν ειναι τοτε το edge)
                        if ci + 1 >= len(cand):
                            break
                        h, l2, oh2, oa2 = cand[ci + 1]; side0 = q[0]
                        ud = l2 if side0 == 1 else -l2; odds = oh2 if side0 == 1 else oa2
                        e = ah_ev(dist, side0, ud, odds)
                        q = (side0, ud, odds, e)
                    if q:
                        side, ud, odds, e = q; clv = np.nan
                        if cdist is not None:
                            pw, pp = picks.p_cover(cdist, side, ud); fc = (1 - pp) / pw if pw > 0 else np.nan; clv = odds / fc - 1
                        bets.append(dict(base, win=wlab, hours=round(h, 1), rule='AH dog' if ud >= .5 else ('AH fav' if ud <= -.5 else 'AH small'), side=side, line=ud,
                                         odds=odds, edge=e, pnl=picks.settle(int(r.gd), side, ud, odds), clv=clv))
                        break
                # --- OVER ---
                if not (r.ko or r.close or OVER_ALL):
                    continue
                cand = [cl_ou] if (W is None and cl_ou) else [z for z in rec['ou'] if z[0] <= (W or 0)]
                for ci, (h, line, oo, uu) in enumerate(cand):
                    e = over_ev(T, line, oo)
                    if e >= .08 and W is not None and MODE == 'persist30':
                        nxt = [z for z in cand[ci + 1:] if h - z[0] <= 0.5]
                        if any(over_ev(T, z[1], z[2]) < .08 for z in nxt):
                            continue
                    if e >= .08 and W is not None and MODE == 'next':
                        if ci + 1 >= len(cand):
                            break
                        h, line, oo, uu = cand[ci + 1]
                        e = max(over_ev(T, line, oo), .08)   # το bet εχει ηδη αποφασιστει· καταγραφη στην τιμη της επομενης κινησης
                    if e >= .08:
                        clv = np.nan
                        if cl_ou and abs(cl_ou[1] - line) < 1e-9:
                            po = (1 / cl_ou[2]) / (1 / cl_ou[2] + 1 / cl_ou[3]); clv = oo * po - 1
                        bets.append(dict(base, win=wlab, hours=round(h, 1), rule='OVER', side=0, line=line, odds=oo, edge=e,
                                         pnl=ou_settle(int(r.tot), line, oo), clv=clv))
                        break
B = pd.DataFrame(bets); B.to_csv(f'intl_window_test{SUF}_bets.csv', index=False)

out = []
def P(s=''):
    print(s, flush=True); out.append(s)
def st(g):
    if len(g) < 5:
        return f'n{len(g):4d}                  —'
    s = g.groupby('season').pnl.mean(); t = g.pnl.mean() / (g.pnl.std(ddof=1) / math.sqrt(len(g)))
    c = g.clv.dropna(); cs = f' CLV {c.mean()*100:+5.1f}%' if len(c) >= 5 else ''
    return f'n{len(g):4d} {g.pnl.mean()*100:+6.1f}% t{t:+4.1f} {int((s > 0).sum())}/{s.size}{cs}'
LAB = {'M1': 'Μ1 H+αξια', 'M2': 'Μ2 Αγκυρα', 'M3': 'Μ3 Αγκ+αξια'}
for book in ('Crown', 'SBOBET'):
    P('=' * 120); P(f'{book} — bet στην ΠΡΩΤΗ κινηση που περναει ο live κανονας μεσα στο παραθυρο (n / ROI / t / θετικες σεζον / CLV vs closing)'); P('=' * 120)
    for rule in ('AH dog', 'AH fav', 'OVER', 'ΟΛΑ'):
        P(f'--- {rule} ---')
        for m in MODELS:
            g0 = B[(B.book == book) & (B.model == m) & ((B.rule == rule) if rule != 'ΟΛΑ' else True)]
            cells = []
            for wlab, _ in WINS:
                cells.append(f'{wlab}: {st(g0[g0.win == wlab])}')
            P(f'{LAB[m]:12s} ' + ' | '.join(cells))
        P('')
    P('ΤΑ «ΧΑΜΕΝΑ» ΤΟΥ CLOSING — bets του παραθυρου 72ω σε ματς/αγορα οπου το closing ΔΕΝ εδινε pick (τυπου Ιταλια−Βελγιο):')
    for m in MODELS:
        g = B[(B.book == book) & (B.model == m)]
        cl = set(zip(g[g.win == 'closing'].mid, g[g.win == 'closing'].rule.str[:2]))
        w = g[g.win == '72ω']; lost = w[[(a, b[:2]) not in cl for a, b in zip(w.mid, w.rule)]]
        kept = w[[(a, b[:2]) in cl for a, b in zip(w.mid, w.rule)]]
        P(f'{LAB[m]:12s} χαμενα απο closing: {st(lost)}  (AH {st(lost[lost.rule != "OVER"])} · OVER {st(lost[lost.rule == "OVER"])})')
        P(f'{"":12s} κοινα με closing:   {st(kept)}')
    P('')
P('ΣΗΜΕΙΩΣΕΙΣ: ωρες = πριν τη σεντρα της κινησης που εγινε το bet. CLV AH = τιμη bet / fair closing (supremacy απο closing AH χωρις γκανιοτα, T = closing O/U)· '
  'CLV OVER μονο οταν η closing γραμμη = γραμμη bet. Ιδια LOSO/τιμολογηση με intl_model_choice_v3. Περιγραφικο — δεν αλλαζει κανονα.')
open(f'intl_window_test{SUF}_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
