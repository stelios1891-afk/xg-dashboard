# -*- coding: utf-8 -*-
"""el_gtd_model_test.py — ΕΥΡΩΛΙΓΚΑ: ΠΟΣΟ ΝΑ ΜΕΤΡΑΕΙ ΕΝΑΣ «GTD» (αμφιβολος) ΣΤΟ ΜΟΝΤΕΛΟ (23/10/2026, ερωτημα εγκεκριμενο απο Στελιο).
Live σημερα (el_absence.py): απο τη σελιδα lineups της RotoWire μετρανε ΜΟΝΟ οι OUT (×1)· οι GTD μετρανε σαν να παιζουν (×0).
el_gtd_study: οσοι ηταν καποια στιγμη αμφιβολοι (≤72ω πριν) επαιξαν 48.5% (βασικος 54%, ρολιστας 47%).

ΚΑΤΑΣΤΑΣΗ ΣΤΟ ΑΝΟΙΓΜΑ (απο το ιστορικο ειδησεων RotoWire, ταξινομηση/ωρα ΝΥ/MAP/find() του el_gtd_study.py ως εχουν):
  για καθε ματς & ομαδα & παικτη: η ΤΕΛΕΥΤΑΙΑ ειδηση με κατηγορια, μετα το προηγουμενο ματς EL της ομαδας, ≤72ω πριν το ματς
  ΚΑΙ ΠΡΙΝ ΤΗΝ ΩΡΑ ΑΝΟΙΓΜΑΤΟΣ της γραμμης Crown (χαντικαπ: ανοιγμα χαντικαπ · συνολα: ανοιγμα συνολου).
  ΕΚΤΟΣ / ΜΑΛΛΟΝ ΕΚΤΟΣ → OUT · ΑΜΦΙΒΟΛΟΣ / ΜΑΛΛΟΝ ΠΑΙΖΕΙ → GTD · ΠΑΙΖΕΙ ή καμια → διαθεσιμος.
  Κανονας «τακτικος» (≥3/10 φετινα), λεπτα (≥10′), PIR τυπος, g(k), on/off: ΙΔΙΑ με τα harness / το live.
ΤΑ HARNESS ΟΡΙΖΟΥΝ ΑΠΟΝΤΕΣ ΕΚ ΤΩΝ ΥΣΤΕΡΩΝ (box score: τακτικος που δεν επαιξε = απων, πληρης γνωση). Γι' αυτο τρεχουν ΔΥΟ ορισμοι:
  N  = «ειδησεις στο ανοιγμα» (οτι θα εβλεπε το live): OUT ×1, GTD ×m.
  H  = «harness + GTD»: αποντες του box score ×1, ΕΚΤΟΣ απο οσους ηταν GTD στο ανοιγμα → ×m (ειτε επαιξαν ειτε οχι).
  (+ ref = harness ως εχει, για αναπαραγωγη · N+ = N + «μεταφορα»: χωρις ειδηση στο παραθυρο, αλλα η τελευταια φετινη ειδηση ηταν
   ΕΚΤΟΣ και δεν εχει ξαναπαιξει → OUT· μονο περιγραφικο.) Πρωτα πινακας: ποσο ταιριαζει ο N με τον ορισμο του harness.
ΕΚΔΟΧΕΣ m (ιδιες σε N και H):
  G0 = GTD ×0 (= σημερινο live) · G1 = GTD ×p ρολου (βασικος ≥20′ 0.46 · ρολιστας 10-20′ 0.53 · λιγα <10′ 0.62 · χωρις φετινα 0.65,
  ρολος = μ.ο. λεπτων 10 τελευταιων φετινων ματς που επαιξε, οπως el_gtd_study) · G2 = GTD ×0.5 · G3 = ΑΜΦΙΒΟΛΟΣ ×p ρολου, ΜΑΛΛΟΝ ΠΑΙΖΕΙ ×0.53.
ΣΗΜΕΙΑ ΜΕΤΡΗΣΗΣ:
  Α. ΧΑΝΤΙΚΑΠ — στησιμο el_absence_v2_test V1 / el_regular_rule_test R0 (1481 ματς, live προβλεψεις, ανοιγμα Crown, picks ≥8%, σ 11.5).
     ref ΠΡΕΠΕΙ να δωσει: 626 picks, +65.8μ, +10.5% (LOSO β0/β1). Κυριο = LOSO επανεκτιμηση β0/β1 · δευτερευον = σταθεροι live 0.56/1.06.
  Β. ΣΥΝΟΛΑ — el_absence_onoff_test W4 (1563 ματς, LOSO bO/bD, ridge 1, picks συνολων ≥8% ανοιγμα).
     ref R0 ΠΡΕΠΕΙ: 511 picks, +59.0μ, RMSE 16.523 · ref R0+alias (live): 516 picks, +55.9μ. Ολες οι εκδοχες πανω στο R0+alias.
     Δευτερευον = σταθεροι live bO −0.426 / bD −0.7975.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ το τρεξιμο), χωριστα για Α και Β, στον ορισμο N με LOSO συντελεστες:
  η G1 ΑΝΤΙΚΑΘΙΣΤΑ τη G0 αν: RMSE καλυτερο απο G0 σε ≥4/5 σεζον ΚΑΙ μοναδες picks ≥ G0 ΚΑΙ θετικες σεζον ≥4/5.
  (G2/G3, ορισμος H, σταθεροι συντελεστες: ιδιοι ελεγχοι, περιγραφικα.)
ΠΕΡΙΓΡΑΦΙΚΑ: GTD στο ανοιγμα ανα σεζον & μεσο κοστος & ποσοι επαιξαν · RMSE/ΔRMSE ανα σεζον · picks/over-under/αγωνιστικες 1-10 vs 11+ ·
  κλιση (πραγματικο − μοντελο G0) πανω στο κοστος GTD ×1 (0 = live σωστο, ~0.5 = προταση σωστη) · ποσο τιμολογει η αγορα το GTD.
  Ελεγχος 3 παραδειγματων.
ΠΡΟΣΘΗΚΗ 23/10 (ζητηση Στελιου μεσω συντονιστη, ΠΡΙΝ το 2ο τρεξιμο — ιδια κριτηρια):
  (1) ΔΙΟΡΘΩΣΗ ΤΑΞΙΝΟΜΗΣΗΣ (μονο μεσα σε αυτο το script· το el_gtd_study.py μενει ως εχει):
      ΕΚΤΟΣ πιανει και «is out for/of», «remains out», «(is/remains) sidelined», «wasn't/was not/isn't/is not included», «not on the roster»,
      «won't/will not travel» (το FUTURE φιλτρο τα αφηνε εξω) · DOMESTIC: «league game» μονο οταν ΔΕΝ ειναι «EuroLeague game», και
      acb/bbl/lega/lnb μονο ως ολοκληρη λεξη (επιανε «planetacb», «repubblica»). Ολες οι εκδοχες τρεχουν με τη νεα ταξινομηση.
  (2) ΝΕΑ ΕΚΔΟΧΗ G_page («GTD της σελιδας lineups»· φετινος ελεγχος σελιδας vs ειδησεων: το GTD της σελιδας ειναι ΠΛΑΤΥ):
      στο ανοιγμα, GTD = τακτικος που (i) τελευταια ειδηση ΑΜΦΙΒΟΛΟΣ/ΜΑΛΛΟΝ ΠΑΙΖΕΙ, Ή (iii) ειδηση τραυματισμου (πεδιο inj ή
      «injur/sustained/soreness») μετα το προηγουμενο ματς χωρις μεταγενεστερη οριστικη (ΠΑΙΖΕΙ/ΕΚΤΟΣ), Ή (ii) ΔΕΝ επαιξε στο
      προηγουμενο ματς EL της ομαδας και δεν υπαρχει καμια ειδηση με κατασταση μετα απο αυτο (προτεραιοτητα i > iii > ii).
      OUT (ειδηση ΕΚΤΟΣ/ΜΑΛΛΟΝ ΕΚΤΟΣ) ×1. p = 1 − ποσοστο που επαιξε ανα πηγη (i/ii/iii) × ρολο, μετρημενο ΠΡΩΤΑ (πινακας)·
      στο μοντελο το p εκτιμαται LOSO (χωρις τη σεζον-τεστ· κελι <20 → p της πηγης). Κριτηριο ιδιο με G1: G_page αντι G0 αν
      RMSE καλυτερο ≥4/5 ΚΑΙ μοναδες ≥ G0 ΚΑΙ θετικες ≥4/5, χωριστα Α/Β, ορισμος N, LOSO συντελεστες.
Εξοδος: el_gtd_model_test_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, json, collections, contextlib, time, math
import datetime as dt
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd
from statistics import NormalDist
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
T0 = time.time()
ATH = ZoneInfo('Europe/Athens')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open(os.path.join(ROOT, 'el_gtd_model_test_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
Phi = NormalDist().cdf
def gr(ts): return dt.datetime.fromtimestamp(ts, dt.timezone.utc).astimezone(ATH).strftime('%d/%m/%Y %H:%M')
# ======================= 1. ΕΙΔΗΣΕΙΣ (el_gtd_study ως εχει) =======================
gsrc = open('el_gtd_study.py', encoding='utf-8').read()
cut = 'rows = []; why = collections.Counter()'
assert gsrc.count(cut) == 1
GS = {'__name__': 'gs'}
_argv = sys.argv; sys.argv = [sys.argv[0]]
with contextlib.redirect_stdout(_B()): exec(gsrc.split(cut)[0], GS)
sys.argv = _argv
sys.stdout.reconfigure(encoding='utf-8')
import re
DOM2 = re.compile(r"domestic|(?<!euro)league game|\bacb\b|\blega\b|\bbbl\b|greek basket|turkish|aba league|\blnb\b|betclic|winner league|super league")
EXTRA_OUT = re.compile(r"is out (for|of)|remains out|will remain out|(is|remains) sidelined|(wasn't|was not|isn't|is not) included|not included (on|in) the (roster|squad)"
                       r"|(is |was )?not on the roster|isn't on the roster|won't travel|will not travel")
INJ = re.compile(r"injur|sustained|soreness")
def cat_v2(r):
    t = GS['txt'](r); n = (r.get('news') or '').lower()
    if DOM2.search(t): return None
    if EXTRA_OUT.search(n): return 'ΕΚΤΟΣ'
    if not GS['FUTURE'].search(n): return None
    for c, rx in GS['CRX']:
        if rx.search(n): return c
    for c, rx in GS['CRX']:
        if rx.search((r.get('headline') or '').lower()): return c
    return None
TRANS = collections.Counter()
for r in GS['R']:
    old = r['cat']; r['cat'] = cat_v2(r)
    if old != r['cat']: TRANS[(old or 'καμια', r['cat'] or 'καμια')] += 1
P(f'ειδησεις RotoWire: {len(GS["R"])} · με κατηγορια {sum(1 for r in GS["R"] if r["cat"])} · κωδικοι ομαδων MAP {len(GS["MAP"])} ({time.time() - T0:.0f} δευτ.)')
P('ΔΙΟΡΘΩΣΗ ΤΑΞΙΝΟΜΗΣΗΣ (παλια → νεα κατηγορια, πληθος ειδησεων): ' + ' · '.join(f'{a} → {b}: {n}' for (a, b), n in TRANS.most_common()))
NEWS = collections.defaultdict(list)                       # (σεζον, κωδικος EL) → [(utc, ονομα RW, κατηγορια|None, τιτλος, κειμενο, τραυματισμος;)]
for r in GS['R']:
    inj = bool(r.get('inj')) or bool(INJ.search(GS['txt'](r)))
    if not r['cat'] and not inj: continue
    t = GS['utc_of'](r)
    if t is None: continue
    team = GS['MAP'].get((GS['season_of'](t), r['team']))
    if team: NEWS[(GS['season_of'](t), team)].append((t, r['player'], r['cat'], r.get('headline') or '', r.get('news') or '', inj))
for v in NEWS.values(): v.sort(key=lambda x: x[0])
ST = {'ΕΚΤΟΣ': 'OUT', 'ΜΑΛΛΟΝ ΕΚΤΟΣ': 'OUT', 'ΑΜΦΙΒΟΛΟΣ': 'GTD', 'ΜΑΛΛΟΝ ΠΑΙΖΕΙ': 'GTD', 'ΠΑΙΖΕΙ': 'AV'}
# ======================= 2. HARNESS ΧΑΝΤΙΚΑΠ (el_absence_v2_test ως εχει) =======================
A = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_absence_v2_test.py', encoding='utf-8').read().split("P(''); P('## ΣΥΝΤΕΛΕΣΤΕΣ")[0], A)
sys.stdout.reconfigure(encoding='utf-8')
rows, keys, TG, PH, NAME, value, MU, SD, SE, D, REC, NP = (A[k] for k in ('rows', 'keys', 'TG', 'PH', 'NAME', 'value', 'MU', 'SD', 'SE', 'D', 'REC', 'NP'))
PAV = A['ns']; LT = PAV['ns']; PL = PAV['PL']
P(f'harness χαντικαπ: {len(rows)} ματς ({time.time() - T0:.0f} δευτ.)')
POS = []
for pos, d_ in REC[21].items():
    sea = D.season.values[pos]
    if sea not in SE: continue
    hc, ac = D.home.values[pos], D.away.values[pos]; t = pd.Timestamp(D.t.values[pos]); key = (sea, hc, ac, t.strftime('%Y-%m-%d %H:%M'))
    if key not in NP or NP[key].get('h_new') is None: continue
    ts = t.timestamp()
    if PAV['absents'](sea, hc, ts) is None or PAV['absents'](sea, ac, ts) is None: continue
    POS.append(pos)
assert len(POS) == len(rows) and all(abs(pd.Timestamp(D.t.values[p]).timestamp() - k[3]) < 1 for p, k in zip(POS, keys))
PLIDX = collections.defaultdict(list)
for k, g in PL.items(): PLIDX[(g['season'], g['hcode'], g['acode'])].append((pd.Timestamp(g['utc']).tz_localize(None).timestamp(), g.get('rnd')))
def rnd_of(sea, hc, ac, ts):
    c = [x[1] for x in PLIDX[(sea, hc, ac)] if abs(x[0] - ts) < 86400]; return c[0] if c else None
for r, pos, (sea, hc, ac, ts) in zip(rows, POS, keys):
    r.update(pos=pos, sea=sea, hc=hc, ac=ac, ts=ts, topen=REC[21][pos]['open'][0], mu_open=REC[21][pos]['open'][1], mu_close=REC[21][pos][0][1],
             rnd=rnd_of(sea, hc, ac, ts))
# ---- ονομα RotoWire → pid (find() του el_gtd_study πανω στο ρόστερ σεζον-ομαδας) ----
tok, find = GS['tok'], GS['find']
RKEY = {}
def roster_keys(sea, team):
    if (sea, team) not in RKEY:
        d = {}
        for _, _, gd in TG.get((sea, team), []):
            for pid in gd:
                nm = NAME.get(pid, '')
                sur = tok(nm.split(',')[0]); fst = tok(nm.split(',')[1]) if ',' in nm else []
                d[(tuple(sur), (fst or [''])[0][:1])] = pid
        RKEY[(sea, team)] = d
    return RKEY[(sea, team)]
PIDC = {}
def pid_of(sea, team, name):
    k = (sea, team, name)
    if k not in PIDC: PIDC[k] = find(roster_keys(sea, team), name)
    return PIDC[k]
NOMATCH = collections.Counter()
def news_state(sea, team, ts, topen):
    """→ {pid: (κατηγορια, utc ειδησης, ονομα, τιτλος, κειμενο)} τελευταια ειδηση στο (προηγ. ματς, min(ανοιγμα, ματς)), ≤72ω"""
    prev = [x[0] for x in TG.get((sea, team), []) if x[0] < ts - 3600]
    lo = max(ts - 72 * 3600, prev[-1] if prev else -1e18); hi = min(topen, ts)
    st, pg = {}, {}
    for t, nm, c, hl, nw, inj in NEWS.get((sea, team), []):
        if t <= lo: continue
        if t >= hi: break
        pid = pid_of(sea, team, nm)
        if pid is None: NOMATCH['χωρις αντιστοιχιση'] += 1; continue
        if c is not None:
            st[pid] = (c, t, nm, hl, nw); pg[pid] = ({'OUT': 'OUT', 'GTD': 'i', 'AV': 'AV'}[ST[c]], t, nm, hl, nw)
        elif pg.get(pid, (None,))[0] in (None, 'AV'):
            pg[pid] = ('iii', t, nm, hl, nw)
    return st, pg
def carry_out(sea, team, ts, topen, pid):
    """N+: χωρις ειδηση στο παραθυρο· η τελευταια φετινη ειδηση (πριν το ανοιγμα) ειναι ΕΚΤΟΣ/ΜΑΛΛΟΝ ΕΚΤΟΣ και δεν επαιξε απο τοτε"""
    hi = min(topen, ts); last = None
    for t, nm, c, hl, nw, inj in NEWS.get((sea, team), []):
        if t >= hi: break
        if c is not None and pid_of(sea, team, nm) == pid: last = (t, c)
    if not last or ST[last[1]] != 'OUT': return False
    return not any(last[0] < x[0] < ts - 3600 and x[2].get(pid, (0,))[0] > 0 for x in TG.get((sea, team), []))
P_ROLE = {'βασικος ≥20′': 0.46, 'ρολιστας 10-20′': 0.53, 'λιγα λεπτα <10′': 0.62, 'χωρις φετινα': 0.65}
def role_of(m): return 'χωρις φετινα' if m is None else ('βασικος ≥20′' if m >= 20 else ('ρολιστας 10-20′' if m >= 10 else 'λιγα λεπτα <10′'))
def gk(k): return 1.0 if k <= 3 else (.5 if k <= 10 else 0.0)
# ---- υποψηφιοι (τακτικοι με αξια) ανα ομαδα, χαντικαπ ----
def cand_A(sea, team, ts, topen):
    L = TG.get((sea, team), []); prev = [x for x in L if x[0] < ts - 3600]; today = next((x[2] for x in L if abs(x[0] - ts) < 3600), None)
    cnt = collections.Counter(p for _, _, d in prev[-10:] for p, v in d.items() if v[0] > 0)
    nst, npg = news_state(sea, team, ts, topen); res = []
    for pid, c in cnt.items():
        if c < 3: continue
        pprev = bool(prev) and prev[-1][2].get(pid, (0,))[0] > 0; pg_ = npg.get(pid)
        pstate = pg_[0] if pg_ else (None if pprev else 'ii')
        k = 0
        for _, _, d in reversed(prev):
            if d.get(pid, (0,))[0] > 0: break
            k += 1
        v = value(pid, ts)
        if v is None or v['min'] < 10: continue
        sm = [d[pid][0] for _, _, d in prev if d.get(pid, (0,))[0] > 0][-10:]
        ns_ = nst.get(pid); played = today.get(pid, (0,))[0] > 0
        res.append(dict(pid=pid, k=k + 1, played=played, mins_today=today.get(pid, (0,))[0], cat=ns_[0] if ns_ else None, pstate=pstate, pnews=pg_, pprev=pprev, season=sea,
                        state=ST[ns_[0]] if ns_ else None, news=ns_, role=role_of(float(np.mean(sm)) if sm else None),
                        carry=(ns_ is None and carry_out(sea, team, ts, topen, pid)), **v))
    return res
for r in rows:
    r['CH'] = cand_A(r['sea'], r['hc'], r['ts'], r['topen']); r['CA'] = cand_A(r['sea'], r['ac'], r['ts'], r['topen'])
    a0 = sorted((p['pid'], p['k']) for p in r['CH'] if not p['played']); b0 = sorted((p['pid'], p['k']) for p in r['ah'])
    assert a0 == b0, ('ref ≠ harness', r['sea'], r['hc'], r['ts'])
    assert sorted((p['pid'], p['k']) for p in r['CA'] if not p['played']) == sorted((p['pid'], p['k']) for p in r['aa']), ('ref ≠ harness (φιλ)', r['sea'], r['ac'], r['ts'])
P(f'ελεγχος: «ref» (τακτικοι που δεν επαιξαν) = αποντες harness σε ολα τα {len(rows)} ματς: OK ({time.time() - T0:.0f} δευτ.)')
VERS = ['G0', 'G1', 'G2', 'G3', 'Gp']
PSRC = ('i', 'ii', 'iii')
def rolek(p): return 'βασικος' if p['role'] == 'βασικος ≥20′' else ('ρολιστας' if p['role'] == 'ρολιστας 10-20′' else 'αλλο')
PG_ALL = [p for r in rows for p in r['CH'] + r['CA'] if gk(p['k']) > 0 and p['pstate'] in PSRC]
PPAGE = {}
for s in SE + ['ολα']:
    tr = [p for p in PG_ALL if p['season'] != s]
    for src in PSRC:
        xs = [p for p in tr if p['pstate'] == src]; base_p = 1 - np.mean([p['played'] for p in xs])
        for rk in ('βασικος', 'ρολιστας', 'αλλο'):
            ys_ = [p['played'] for p in xs if rolek(p) == rk]
            PPAGE[(s, src, rk)] = (1 - float(np.mean(ys_))) if len(ys_) >= 20 else float(base_p)
def mult(p, ver):
    if ver == 'G0': return 0.0
    if ver == 'G2': return 0.5
    if ver == 'G3' and p['cat'] == 'ΜΑΛΛΟΝ ΠΑΙΖΕΙ': return 0.53
    return P_ROLE[p['role']]
def weight(p, defn, ver):
    if defn == 'ref': return 0.0 if p['played'] else 1.0
    if ver == 'Gp':
        pp = PPAGE[(p['season'], p['pstate'], rolek(p))] if p['pstate'] in PSRC else None
        if defn == 'N': return 1.0 if p['pstate'] == 'OUT' else (pp if pp is not None else 0.0)
        if defn == 'H': return pp if pp is not None else (0.0 if p['played'] else 1.0)
    if defn in ('N', 'N+'):
        if p['state'] == 'OUT' or (defn == 'N+' and p['carry']): return 1.0
        return mult(p, ver) if p['state'] == 'GTD' else 0.0
    if defn == 'H':
        if p['state'] == 'GTD': return mult(p, ver)
        return 0.0 if p['played'] else 1.0
DEFS = [('ref', None)] + [(d, v) for d in ('N', 'H') for v in VERS] + [('N+', 'G0'), ('N+', 'G1')]
def lab(d, v): return 'ref (harness)' if d == 'ref' else f'{d}-{"Gpage" if v == "Gp" else v}'
B_LIVE = np.array([0.56, 1.06])
def featA(r, d, v):
    x = np.zeros(2)
    for lst, s in ((r['CA'], 1), (r['CH'], -1)):
        for p in lst:
            w = weight(p, d, v) * p['min'] / 40 * gk(p['k']) * s
            if w: x[0] += w; x[1] += w * (p['pir'] - MU['pir']) / SD['pir']
    return x
def gtd_costA(r, fixed=True):
    """σημασμενο κοστος GTD ×1 (live τυπος): φιλοξ − γηπ (+ = καλο για γηπ)"""
    c = 0.0
    for lst, s in ((r['CA'], 1), (r['CH'], -1)):
        for p in lst:
            if p['state'] == 'GTD' and gk(p['k']) > 0:
                c += s * (B_LIVE[0] + B_LIVE[1] * (p['pir'] - MU['pir']) / SD['pir']) * p['min'] / 40 * gk(p['k'])
    return c
YA_ = np.array([r['act'] - r['m'] for r in rows]); ysA = np.array([r['y'] for r in rows]); rndA = np.array([r['rnd'] if r['rnd'] else 99 for r in rows])
XFA = {(d, v): np.array([featA(r, d, v) for r in rows]) for d, v in DEFS}
HELD_A, FIX_A = {}, {}
for dv, X in XFA.items():
    h = np.zeros(len(rows))
    for s in SE:
        m = ysA != s; b = np.linalg.solve(X[m].T @ X[m] + np.eye(2), X[m].T @ YA_[m]); h[ysA == s] = (X @ b)[ysA == s]
    HELD_A[dv] = h; FIX_A[dv] = X @ B_LIVE
def picksA(adj):
    L = []
    for r, a in zip(rows, adj):
        Lh, o1, o2 = r['op']; m = r['m'] + a
        if abs(Lh - round(Lh)) < 1e-9: pw = Phi((m + Lh - .5) / 11.5); pl = Phi((-m - Lh - .5) / 11.5)
        else: pw = Phi((m + Lh) / 11.5); pl = 1 - pw
        pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; sd, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e >= .08:
            x = (r['act'] + Lh) * sd; L.append(dict(season=r['y'], rnd=r['rnd'] or 99, pick='γηπ' if sd == 1 else 'φιλ', fav=(sd == 1) == (Lh < 0),
                                                    units=(od - 1) if x > 0 else (0 if x == 0 else -1)))
        else: L.append(dict(season=r['y'], rnd=r['rnd'] or 99, pick=None, fav=None, units=np.nan))
    return pd.DataFrame(L)
rmse = lambda v, m: float(np.sqrt(np.mean(v[m] ** 2))) if m.any() else float('nan')
def summ(df):
    q = df[df.pick.notna()]; U = {s: q[q.season == s].units for s in SE}
    return len(q), float(q.units.sum()), float(q.units.mean() * 100) if len(q) else 0.0, sum(1 for s in SE if len(U[s]) and U[s].sum() > 0), {s: float(U[s].sum()) for s in SE}
def picks_line(df):
    n, u, roi, pos, us = summ(df)
    return f'picks {n:4d} · μοναδες {u:+6.1f}μ · ROI {roi:+5.1f}% · θετικες σεζον {pos}/5 · ανα σεζον ' + ' '.join(f'{s[-2:]}:{us[s]:+.1f}' for s in SE)
def crit(Y, ys, h, h0, df, df0):
    d = [rmse(Y - h, ys == s) - rmse(Y - h0, ys == s) for s in SE]; n, u, roi, pos, _ = summ(df); u0 = summ(df0)[1]
    return d, (sum(x < 0 for x in d) >= 4 and u >= u0 - 1e-9 and pos >= 4)
# ======================= 3. HARNESS ΣΥΝΟΛΩΝ (el_absence_onoff_test W4, ιδιο patch με el_onoff_hybrid_test) =======================
ALIAS = {n: (tuple(v[0]), v[1]) for n, v in json.load(open('el_onoff_alias.json', encoding='utf-8'))['alias'].items()}
base = open('el_absence_onoff_test.py', encoding='utf-8').read().split('# ---- ΧΑΝΤΙΚΑΠ ----')[0]
a1 = "res.append(dict(w=w, **(pr or dict(onO=0.0, onD=0.0, usg=None))))"; a2 = "rows.append(dict(y=sea,"
a3 = "def profile(name, yr):\n    k = key_of(name)\n"
a4 = """    exec(open('el_line_timing.py', encoding='utf-8').read().split("lp = np.array(lastpre)")[0], ns)"""
a5 = "PL = json.load(open('el_players.json', encoding='utf-8'))"
for a in (a1, a2, a3, a4, a5): assert base.count(a) == 1, a
base = base.replace(a1, "res.append(dict(w=w, pid=pid, **(pr or dict(onO=0.0, onD=0.0, usg=None))))").replace(a2, "rows.append(dict(hc=hc, ac=ac, ts=ts, pos=pos, y=sea,")
base = base.replace(a3, a3 + "    _a = ALIAS.get(str(name))\n    if _a is not None and _a in PROF and PROF[_a].get(yr - 1) is not None and PROF[_a][yr - 1][2] > 0: k = _a\n")
base = base.replace(a4, "    ns = LT").replace(a5, "PL = PL_INJ")
RUN = {}
for nm, al in (('R0', {}), ('R0+alias', ALIAS)):
    NS = {'ALIAS': al, 'LT': LT, 'PL_INJ': PL}
    with contextlib.redirect_stdout(_B()): exec(base, NS)
    sys.stdout.reconfigure(encoding='utf-8')
    RUN[nm] = NS
    P(f'harness συνολων {nm}: εκτελεστηκε ({time.time() - T0:.0f} δευτ.)')
NB = RUN['R0+alias']; rowsB = NB['rows']; ysB = NB['ys']; YT = NB['YT']; YH, YAw = NB['YH'], NB['YA']; tp = NB['tp']; SDB = NB['SD']
TGB, PHB, NAMEB, profile = NB['TG'], NB['PH'], NB['NAME'], NB['profile']
CHK = {}
for nm in ('R0', 'R0+alias'):
    h = RUN[nm]['HELD']['W4 μονο on/off']; u, s_ = RUN[nm]['tpicks'](h); CHK[nm] = (len(RUN[nm]['rows']), rmse(RUN[nm]['YT'] - h, RUN[nm]['ALL']), u, s_.strip())
P(''); P('## ΑΝΑΠΑΡΑΓΩΓΗ HARNESS')
for nm, (n, rm, u, s_) in CHK.items(): P(f'  ΣΥΝΟΛΑ {nm}: ματς {n} · RMSE {rm:.3f} · {s_}')
okB = CHK['R0'][0] == 1563 and abs(CHK['R0'][1] - 16.523) < 0.0006 and abs(CHK['R0'][2] - 59.0) < 0.06 and CHK['R0'][3].startswith('511 picks') \
      and abs(CHK['R0+alias'][2] - 55.9) < 0.06 and CHK['R0+alias'][3].startswith('516 picks')
dfA_ref = picksA(HELD_A[('ref', None)]); nA, uA, roiA, posA, _ = summ(dfA_ref)
okA = nA == 626 and abs(uA - 65.8) < 0.06 and posA == 5
P(f'  ΧΑΝΤΙΚΑΠ ref (LOSO β): {picks_line(dfA_ref)}  · αναμενομενο 626 / +65.8μ / 5/5')
P(f'  → χαντικαπ {"✓ αναπαραγεται" if okA else "✗ ΔΕΝ αναπαραγεται"} · συνολα {"✓ αναπαραγονται R0 και R0+alias" if okB else "✗ ΔΕΝ αναπαραγονται"}')
if not (okA and okB): P('!!! STOP: το harness δεν αναπαραγεται'); save(); sys.exit(1)
assert len(RUN['R0']['rows']) == len(rowsB)
for r in rowsB:
    r['topen'] = r['op'][0]; r['rnd'] = rnd_of(r['y'], r['hc'], r['ac'], r['ts'])
def cand_B(sea, team, ts, topen):
    """ιδιο με absents() του W4, αλλα κραταει και οσους επαιξαν (για GTD) + κατασταση ειδησεων"""
    L = TGB.get((sea, team), []); prev = [x for x in L if x[0] < ts - 3600]; today = next((x[1] for x in L if abs(x[0] - ts) < 3600), None)
    if today is None: return None
    cnt = collections.Counter(p for _, d in prev[-10:] for p, v in d.items() if v > 0); nst, npg = news_state(sea, team, ts, topen); res = []
    for pid, c in cnt.items():
        if c < 3: continue
        pprev = bool(prev) and prev[-1][1].get(pid, 0) > 0; pg_ = npg.get(pid)
        pstate = pg_[0] if pg_ else (None if pprev else 'ii')
        k = 0
        for _, d in reversed(prev):
            if d.get(pid, 0) > 0: break
            k += 1
        h = [mn for t, mn in PHB[pid] if t < ts - 3600][-10:]
        if not h or np.mean(h) < 10: continue
        w = np.mean(h) / 40 * gk(k + 1)
        if w <= 0: continue
        pr = profile(NAMEB[pid], int(sea[1:]))
        sm = [d[pid] for _, d in prev if d.get(pid, 0) > 0][-10:]; ns_ = nst.get(pid)
        res.append(dict(pid=pid, k=k + 1, w=w, played=today.get(pid, 0) > 0, onO=(pr or {}).get('onO', 0.0), onD=(pr or {}).get('onD', 0.0), has=pr is not None,
                        cat=ns_[0] if ns_ else None, state=ST[ns_[0]] if ns_ else None, news=ns_, role=role_of(float(np.mean(sm)) if sm else None),
                        carry=(ns_ is None and carry_out(sea, team, ts, topen, pid)), pstate=pstate, pnews=pg_, pprev=pprev, season=sea))
    return res
for r in rowsB:
    r['CH'] = cand_B(r['y'], r['hc'], r['ts'], r['topen']); r['CA'] = cand_B(r['y'], r['ac'], r['ts'], r['topen'])
    a0 = sorted((p['pid'], round(p['w'], 9), p['onO']) for p in r['CH'] if not p['played']); b0 = sorted((p['pid'], round(p['w'], 9), p['onO']) for p in r['ah'])
    assert a0 == b0, ('ref συνολων ≠ harness', r['y'], r['hc'], r['ts'])
P(f'  ελεγχος: «ref» συνολων = αποντες W4 (R0+alias) σε ολα τα {len(rowsB)} ματς: OK ({time.time() - T0:.0f} δευτ.)')
def featB(r, d, v):
    def side(own, opp):
        return (sum(weight(p, d, v) * p['w'] * p['onO'] / SDB['onO'] for p in own), sum(weight(p, d, v) * p['w'] * p['onD'] / SDB['onD'] for p in opp))
    return np.array(side(r['CH'], r['CA'])), np.array(side(r['CA'], r['CH']))
B_TOT = np.array([-0.426, -0.7975])
HELD_B, FIX_B = {}, {}
for d, v in DEFS:
    F = [featB(r, d, v) for r in rowsB]; XH = np.array([f[0] for f in F]); XA = np.array([f[1] for f in F]); h = np.zeros(len(rowsB))
    for s in SE:
        tr = ysB != s; X = np.r_[XH[tr], XA[tr]]; y = np.r_[YH[tr], YAw[tr]]; b = np.linalg.solve(X.T @ X + np.eye(2), X.T @ y)
        m = ysB == s; h[m] = XH[m] @ b + XA[m] @ b
    HELD_B[(d, v)] = h; FIX_B[(d, v)] = XH @ B_TOT + XA @ B_TOT
assert abs(rmse(YT - HELD_B[('ref', None)], ysB != '') - CHK['R0+alias'][1]) < 1e-6, 'ref συνολων ≠ R0+alias'
def gtd_effB(r):
    """επιδραση GTD ×1 στο συνολο (σταθεροι live bO/bD)"""
    e = 0.0
    for own, opp in ((r['CH'], r['CA']), (r['CA'], r['CH'])):
        e += sum(B_TOT[0] * p['w'] * p['onO'] / SDB['onO'] for p in own if p['state'] == 'GTD')
        e += sum(B_TOT[1] * p['w'] * p['onD'] / SDB['onD'] for p in opp if p['state'] == 'GTD')
    return e
def picksB(adj):
    L = []
    for r, a in zip(rowsB, adj):
        o = r['op']; T_, oo, ou = o[2], o[3], o[4]; po, pp, pu = tp(r['T'] + a, T_); eo, eu = po * oo + pp - 1, pu * ou + pp - 1
        sd, e, od = (1, eo, oo) if eo >= eu else (-1, eu, ou)
        if e >= .08:
            x = (r['hs'] + r['as_'] - T_) * sd; L.append(dict(season=r['y'], rnd=r['rnd'] or 99, pick='over' if sd == 1 else 'under', units=(od - 1) if x > 0 else (0 if x == 0 else -1)))
        else: L.append(dict(season=r['y'], rnd=r['rnd'] or 99, pick=None, units=np.nan))
    return pd.DataFrame(L)
# ======================= 4. ΠΙΝΑΚΕΣ =======================
P(''); P('## 0. ΩΡΑ ΑΝΟΙΓΜΑΤΟΣ Crown (ωρες πριν το τζαμπολ) — καθοριζει ποιες ειδησεις «προλαβαινουν»')
for nm, RW in (('χαντικαπ', rows), ('συνολα', rowsB)):
    hh = np.array([(r['ts'] - r['topen']) / 3600 for r in RW])
    P(f'  {nm:8s}: διαμεσος {np.median(hh):.1f}ω · 25% {np.percentile(hh, 25):.1f}ω · 75% {np.percentile(hh, 75):.1f}ω · ανοιγμα >72ω πριν: {np.mean(hh > 72) * 100:.0f}% · <24ω: {np.mean(hh < 24) * 100:.0f}% · ανα σεζον διαμεσος '
      + ' '.join(f'{s[-2:]}:{np.median(hh[np.array([r["y"] for r in RW]) == s]):.0f}ω' for s in SE))
P(f'  ονοματα ειδησεων στο παραθυρο χωρις αντιστοιχιση στο ρόστερ (αγνοηθηκαν): {NOMATCH["χωρις αντιστοιχιση"]}')
# ---- Ι. ταιριασμα ορισμων ----
P(''); P('## 1. ΠΟΣΟ ΤΑΙΡΙΑΖΕΙ Ο ΟΡΙΣΜΟΣ «ΕΙΔΗΣΕΙΣ ΣΤΟ ΑΝΟΙΓΜΑ» (N) ΜΕ ΤΟΝ ΟΡΙΣΜΟ ΤΟΥ HARNESS (box score) — χαντικαπ, 1481 ματς')
P('   (μοναδα = τακτικος παικτης-ματς με βαρος g(k) > 0, δηλ. k ≤ 10· «απων harness» = δεν επαιξε)')
allc = [(r, p) for r in rows for p in r['CH'] + r['CA'] if gk(p['k']) > 0]
absn = [p for r, p in allc if not p['played']]
P(f'  αποντες harness: {len(absn)} · η ειδηση στο ανοιγμα τους ελεγε → '
  + ' · '.join(f'{lb} {n} ({100 * n / len(absn):.0f}%)' for lb, n in (('OUT', sum(p['state'] == 'OUT' for p in absn)), ('GTD', sum(p['state'] == 'GTD' for p in absn)),
                                                                     ('ΠΑΙΖΕΙ', sum(p['state'] == 'AV' for p in absn)), ('καμια ειδηση', sum(p['state'] is None for p in absn)))))
for kb, f in (('k 1-3 (πρωτα ματς απουσιας)', lambda p: p['k'] <= 3), ('k 4-10 (μακροχρονια)', lambda p: 3 < p['k'] <= 10)):
    xs = [p for p in absn if f(p)]
    P(f'    {kb:28s} n {len(xs):4d} · OUT {100 * sum(p["state"] == "OUT" for p in xs) / len(xs):3.0f}% · GTD {100 * sum(p["state"] == "GTD" for p in xs) / len(xs):3.0f}% · '
      f'ΠΑΙΖΕΙ {100 * sum(p["state"] == "AV" for p in xs) / len(xs):3.0f}% · καμια {100 * sum(p["state"] is None for p in xs) / len(xs):3.0f}% (απο αυτους «μεταφορα ΕΚΤΟΣ» N+: {sum(p["carry"] for p in xs)})')
for stt, lb in (('OUT', 'OUT στην ειδηση'), ('GTD', 'GTD στην ειδηση'), ('AV', 'ΠΑΙΖΕΙ στην ειδηση')):
    xs = [p for r, p in allc if p['state'] == stt]
    P(f'  {lb:20s}: n {len(xs):4d} · τελικα ΔΕΝ επαιξαν {100 * sum(not p["played"] for p in xs) / max(1, len(xs)):5.1f}%')
xs = [p for r, p in allc if p['carry']]
P(f'  N+ «μεταφορα ΕΚΤΟΣ»   : n {len(xs):4d} · τελικα ΔΕΝ επαιξαν {100 * sum(not p["played"] for p in xs) / max(1, len(xs)):5.1f}%')
cref = FIX_A[('ref', None)]; cN = FIX_A[('N', 'G0')]; cNp = FIX_A[('N+', 'G0')]
P(f'  διορθωση ανα ματς (σταθεροι live συντελεστες, ποντοι): μεσο |ref| {np.mean(np.abs(cref)):.2f} · μεσο |N-G0| {np.mean(np.abs(cN)):.2f} · μεσο |N+-G0| {np.mean(np.abs(cNp)):.2f} · '
  f'συσχετιση ref↔N-G0 {np.corrcoef(cref, cN)[0, 1]:.2f} · ref↔N+-G0 {np.corrcoef(cref, cNp)[0, 1]:.2f}')
# ---- ΙΙ. GTD στο ανοιγμα ανα σεζον ----
P(''); P('## 2. GTD ΣΤΟ ΑΝΟΙΓΜΑ ανα σεζον (χαντικαπ ματς· τακτικοι με g(k) > 0)')
P('   κοστος = live τυπος (0.56 + 1.06·z_PIR) × λεπτα/40 × g(k), ποντοι χαντικαπ ανα παικτη')
for s in SE + ['ολα']:
    R_ = [r for r in rows if s == 'ολα' or r['y'] == s]
    g = [p for r in R_ for p in r['CH'] + r['CA'] if p['state'] == 'GTD' and gk(p['k']) > 0]
    o = [p for r in R_ for p in r['CH'] + r['CA'] if p['state'] == 'OUT' and gk(p['k']) > 0]
    cst = [(B_LIVE[0] + B_LIVE[1] * (p['pir'] - MU['pir']) / SD['pir']) * p['min'] / 40 * gk(p['k']) for p in g]
    c1 = [c * P_ROLE[p['role']] for c, p in zip(cst, g)]
    mg = sum(1 for r in R_ if any(p['state'] == 'GTD' and gk(p['k']) > 0 for p in r['CH'] + r['CA']))
    P(f'  {s:5s}: ματς {len(R_):4d} · ματς με ≥1 GTD {mg:3d} ({100 * mg / len(R_):.0f}%) · GTD παικτες {len(g):3d} (OUT {len(o):4d}) · μεσο κοστος GTD ×1 {np.mean(cst) if cst else 0:+.2f}π · '
      f'×p (G1) {np.mean(c1) if c1 else 0:+.2f}π · οι GTD ΕΠΑΙΞΑΝ {100 * np.mean([p["played"] for p in g]) if g else 0:.0f}% · βασικοι/ρολιστες {sum(p["role"] == "βασικος ≥20′" for p in g)}/{sum(p["role"] == "ρολιστας 10-20′" for p in g)}')
gB = [p for r in rowsB for p in r['CH'] + r['CA'] if p['state'] == 'GTD']
P(f'  συνολα: ματς με ≥1 GTD {sum(1 for r in rowsB if any(p["state"] == "GTD" for p in r["CH"] + r["CA"]))}/{len(rowsB)} · GTD παικτες {len(gB)} · με περσινο on/off προφιλ {sum(p["has"] for p in gB)} · '
  f'μεση |επιδραση GTD ×1 στο συνολο| (ματς με GTD) {np.mean([abs(gtd_effB(r)) for r in rowsB if any(p["state"] == "GTD" for p in r["CH"] + r["CA"])]):.2f}π')
gg = [p for r, p in allc if p['state'] == 'GTD']
P('  ποσοι GTD-στο-ανοιγμα επαιξαν, ανα ρολο & κατηγορια: ' + ' · '.join(f'{k}: {100 * np.mean([p["played"] for p in gg if f(p)]):.0f}% ({sum(1 for p in gg if f(p))})'
  for k, f in (('βασικος', lambda p: p['role'] == 'βασικος ≥20′'), ('ρολιστας', lambda p: p['role'] == 'ρολιστας 10-20′'),
               ('ΑΜΦΙΒΟΛΟΣ', lambda p: p['cat'] == 'ΑΜΦΙΒΟΛΟΣ'), ('ΜΑΛΛΟΝ ΠΑΙΖΕΙ', lambda p: p['cat'] == 'ΜΑΛΛΟΝ ΠΑΙΖΕΙ'))
  if sum(1 for p in gg if f(p))) + f' · (p του G1 = 1 − ποσοστο που επαιξε: βασικος 0.46, ρολιστας 0.53)')
P(''); P('## 2β. G_page — «GTD της σελιδας» στο ανοιγμα: ΠΟΣΟΙ ΕΠΑΙΞΑΝ ΤΕΛΙΚΑ (χαντικαπ ματς, τακτικοι με g(k) > 0, ολες οι σεζον)')
P('   (i) ειδηση ΑΜΦΙΒΟΛΟΣ/ΜΑΛΛΟΝ ΠΑΙΖΕΙ · (iii) ειδηση τραυματισμου χωρις οριστικη · (ii) εκτος στο προηγουμενο ματς, καμια ειδηση με κατασταση μετα')
SRCN = {'i': '(i) αμφιβολος/μαλλον παιζει', 'ii': '(ii) εκτος στο προηγ., χωρις ειδηση', 'iii': '(iii) ειδηση τραυματισμου'}
for src in PSRC:
    xs = [p for p in PG_ALL if p['pstate'] == src]
    cells = ' · '.join(f'{rk} {100 * np.mean([p["played"] for p in xs if rolek(p) == rk]):.0f}% (n {sum(1 for p in xs if rolek(p) == rk)})'
                       for rk in ('βασικος', 'ρολιστας', 'αλλο') if any(rolek(p) == rk for p in xs))
    P(f'  {SRCN[src]:38s} n {len(xs):4d} · ΕΠΑΙΞΑΝ {100 * np.mean([p["played"] for p in xs]):5.1f}% · ανα ρολο: {cells}')
    P(f'  {"":38s} ανα σεζον: ' + ' · '.join(f'{s_[-2:]}: {100 * np.mean([p["played"] for p in xs if p["season"] == s_]):.0f}% ({sum(1 for p in xs if p["season"] == s_)})' for s_ in SE if any(p['season'] == s_ for p in xs)))
    P(f'  {"":38s} k (ματς απουσιας μαζι με το σημερινο): ' + ' · '.join(f'k {kb}: {100 * np.mean([p["played"] for p in xs if f(p)]):.0f}% ({sum(1 for p in xs if f(p))})'
      for kb, f in (('1', lambda p: p['k'] == 1), ('2-3', lambda p: 2 <= p['k'] <= 3), ('4-10', lambda p: p['k'] >= 4)) if any(f(p) for p in xs)))
P('  p που μπαινει στο G_page (= 1 − ποσοστο που επαιξε· ολες οι σεζον — στο μοντελο LOSO): ' + ' · '.join(f'{src}/{rk} {PPAGE[("ολα", src, rk)]:.2f}' for src in PSRC for rk in ('βασικος', 'ρολιστας')))
P('  LOSO p ανα κρατημενη σεζον (βασικος): ' + ' · '.join(f'{src}: ' + '/'.join(f'{PPAGE[(s_, src, "βασικος")]:.2f}' for s_ in SE) for src in PSRC))
for s_ in SE + ['ολα']:
    R_ = [r for r in rows if s_ == 'ολα' or r['y'] == s_]
    g = [p for r in R_ for p in r['CH'] + r['CA'] if p['pstate'] in PSRC and gk(p['k']) > 0]
    cst = [(B_LIVE[0] + B_LIVE[1] * (p['pir'] - MU['pir']) / SD['pir']) * p['min'] / 40 * gk(p['k']) for p in g]
    mg_ = sum(1 for r in R_ if any(p['pstate'] in PSRC and gk(p['k']) > 0 for p in r['CH'] + r['CA']))
    P(f'  {s_:5s}: ματς με ≥1 G_page-GTD {mg_:4d}/{len(R_)} ({100 * mg_ / len(R_):.0f}%) · G_page-GTD παικτες {len(g):4d} (i {sum(p["pstate"] == "i" for p in g)} · ii {sum(p["pstate"] == "ii" for p in g)} · iii {sum(p["pstate"] == "iii" for p in g)}) · '
      f'μεσο κοστος ×1 {np.mean(cst) if cst else 0:+.2f}π · επαιξαν {100 * np.mean([p["played"] for p in g]) if g else 0:.0f}%')
absn2 = [p for r, p in allc if not p['played']]
P(f'  αποντες harness ({len(absn2)}) κατα G_page: ' + ' · '.join(f'{lb} {n} ({100 * n / len(absn2):.0f}%)' for lb, n in (
    ('OUT', sum(p['pstate'] == 'OUT' for p in absn2)), ('(i)', sum(p['pstate'] == 'i' for p in absn2)), ('(ii)', sum(p['pstate'] == 'ii' for p in absn2)),
    ('(iii)', sum(p['pstate'] == 'iii' for p in absn2)), ('ΠΑΙΖΕΙ', sum(p['pstate'] == 'AV' for p in absn2)), ('τιποτα', sum(p['pstate'] is None for p in absn2)))))
# ---- ΙΙΙ. Α ΧΑΝΤΙΚΑΠ ----
DFA = {dv: picksA(HELD_A[dv]) for dv in DEFS}; DFAF = {dv: picksA(FIX_A[dv]) for dv in DEFS}; DFA0 = picksA(np.zeros(len(rows)))
P(''); P('## 3. Α. ΧΑΝΤΙΚΑΠ — RMSE (ποντοι διαφορας, LOSO) ανα σεζον και ΔRMSE vs G0 του ιδιου ορισμου (− = καλυτερο)')
for coefs, HH, DD in (('LOSO β0/β1 (κυριο)', HELD_A, DFA), ('σταθεροι live 0.56/1.06', FIX_A, DFAF)):
    P(f'  --- {coefs} ---')
    P(f'  {"χωρις διορθωση":16s} RMSE {rmse(YA_, ysA != ""):.3f} · ανα σεζον ' + ' '.join(f'{rmse(YA_, ysA == s):.3f}' for s in SE))
    for d, v in DEFS:
        h = HH[(d, v)]; base0 = HH[('ref', None)] if d == 'ref' else HH[(d, 'G0')]
        dd = [rmse(YA_ - h, ysA == s) - rmse(YA_ - base0, ysA == s) for s in SE]
        P(f'  {lab(d, v):16s} RMSE {rmse(YA_ - h, ysA != ""):.3f} · ανα σεζον ' + ' '.join(f'{rmse(YA_ - h, ysA == s):.3f}' for s in SE)
          + ('' if d == 'ref' or v == 'G0' else ' · Δ vs G0 ' + ' '.join(f'{x:+.4f}' for x in dd) + f' (καλυτερο {sum(x < 0 for x in dd)}/5)'))
P(''); P('## 4. Α. ΧΑΝΤΙΚΑΠ — PICKS ≥8% στο ανοιγμα Crown (μοναδες = κερδος σε μοναδες ποντασματος 1μ)')
for coefs, DD, HH in (('LOSO β0/β1 (κυριο)', DFA, HELD_A), ('σταθεροι live 0.56/1.06', DFAF, FIX_A)):
    P(f'  --- {coefs} ---')
    P(f'  {"χωρις διορθωση":16s} {picks_line(DFA0)}')
    for d, v in DEFS:
        ln = f'  {lab(d, v):16s} {picks_line(DD[(d, v)])}'
        if d != 'ref' and v != 'G0':
            dd, ok = crit(YA_, ysA, HH[(d, v)], HH[(d, 'G0')], DD[(d, v)], DD[(d, 'G0')])
            ln += f'  | κριτηριο vs {d}-G0: RMSE {sum(x < 0 for x in dd)}/5, μοναδες {summ(DD[(d, v)])[1] - summ(DD[(d, "G0")])[1]:+.1f}μ, θετ {summ(DD[(d, v)])[3]}/5 → {"✓" if ok else "✗"}'
        P(ln)
P(''); P('## 5. Α. ΧΑΝΤΙΚΑΠ — αγωνιστικες 1-10 vs 11+ και φαβορι/αουτσαιντερ (LOSO β· n · μοναδες · ROI)')
def seg(q, f): x = q[f(q)]; return f'{len(x):3d} · {x.units.sum():+6.1f}μ · {x.units.mean() * 100 if len(x) else 0:+5.1f}%'
for d, v in DEFS:
    q = DFA[(d, v)]; q = q[q.pick.notna()]
    P(f'  {lab(d, v):16s} αγων 1-10: {seg(q, lambda z: z.rnd <= 10)} · 11+: {seg(q, lambda z: z.rnd > 10)} · φαβορι: {seg(q, lambda z: z.fav == True)} · αουτσαιντερ: {seg(q, lambda z: z.fav == False)}')
P(''); P('## 6. Α. ΧΑΝΤΙΚΑΠ — ποια picks αλλαζουν G0 → G1 (ορισμος N, LOSO)')
q0, q1 = DFA[('N', 'G0')], DFA[('N', 'G1')]
same = (q0.pick == q1.pick) & q0.pick.notna(); only0 = q0.pick.notna() & q1.pick.isna()
only1 = q1.pick.notna() & q0.pick.isna(); flip = q0.pick.notna() & q1.pick.notna() & (q0.pick != q1.pick)
P(f'  ιδια picks {int(same.sum())} · μονο G0 {int(only0.sum())} ({q0[only0].units.sum():+.1f}μ) · μονο G1 {int(only1.sum())} ({q1[only1].units.sum():+.1f}μ) · αλλαξε πλευρα {int(flip.sum())} (G0 {q0[flip].units.sum():+.1f}μ / G1 {q1[flip].units.sum():+.1f}μ)')
# ---- περιγραφικο: κλιση ----
def ols(x, y):
    X = np.c_[np.ones(len(x)), x]; b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b
    se = np.sqrt(np.diag(e @ e / (len(y) - 2) * np.linalg.inv(X.T @ X))); return b[1], se[1]
P(''); P('## 7. ΠΕΡΙΓΡΑΦΙΚΟ — στα ματς με GTD: (πραγματικο − μοντελο G0) πανω στο κοστος GTD ×1 (κλιση: 0 = το live σωστο · ~0.5 = η προταση σωστη · 1 = σαν OUT)')
xg = np.array([gtd_costA(r) for r in rows]); mg = xg != 0
for nm, adj in (('N-G0 (σταθεροι live)', FIX_A[('N', 'G0')]), ('H-G0 (σταθεροι live)', FIX_A[('H', 'G0')])):
    res_ = YA_ - adj; b, se = ols(xg[mg], res_[mg])
    P(f'  ΧΑΝΤΙΚΑΠ {nm:22s}: ματς {int(mg.sum())} · κλιση {b:+.2f} ± {se:.2f} (τυπ. σφαλμα) · ανα σεζον '
      + ' '.join(f'{s[-2:]}:{ols(xg[mg & (ysA == s)], res_[mg & (ysA == s)])[0]:+.2f}' for s in SE if (mg & (ysA == s)).sum() >= 5))
def page_costA(r, srcs=PSRC):
    c = 0.0
    for lst, s in ((r['CA'], 1), (r['CH'], -1)):
        for p in lst:
            if p['pstate'] in srcs and gk(p['k']) > 0:
                c += s * (B_LIVE[0] + B_LIVE[1] * (p['pir'] - MU['pir']) / SD['pir']) * p['min'] / 40 * gk(p['k'])
    return c
res_ = YA_ - FIX_A[('N', 'G0')]
for nm, srcs in (('G_page ολα (i+ii+iii)', PSRC), ('G_page (i)', ('i',)), ('G_page (ii)', ('ii',)), ('G_page (iii)', ('iii',))):
    xp = np.array([page_costA(r, srcs) for r in rows]); mp_ = xp != 0
    b, se = ols(xp[mp_], res_[mp_])
    P(f'  ΧΑΝΤΙΚΑΠ κοστος {nm:22s} ×1, υπολοιπο N-G0: ματς {int(mp_.sum())} · κλιση {b:+.2f} ± {se:.2f} (1 = σαν OUT, 0 = σαν να παιζει)')
mo = np.array([r['mu_open'] - r['m'] for r in rows]); mc = np.array([r['mu_close'] - r['m'] for r in rows])
for nm, z in (('ανοιγμα', mo), ('κλεισιμο', mc)):
    X = np.c_[np.ones(len(rows)), FIX_A[('N', 'G0')], xg]; b = np.linalg.lstsq(X, z, rcond=None)[0]; e = z - X @ b
    se = np.sqrt(np.diag(e @ e / (len(z) - 3) * np.linalg.inv(X.T @ X)))
    P(f'  ΑΓΟΡΑ χαντικαπ {nm:8s}: (γραμμη − μοντελο) = {b[1]:+.2f} ± {se[1]:.2f} × κοστος OUT + {b[2]:+.2f} ± {se[2]:.2f} × κοστος GTD (1 = τιμολογει ολο το κοστος, 0 = τιποτα)')
xgB = np.array([gtd_effB(r) for r in rowsB]); mgB = xgB != 0
for nm, adj in (('N-G0 (σταθεροι live)', FIX_B[('N', 'G0')]), ('H-G0 (σταθεροι live)', FIX_B[('H', 'G0')])):
    res_ = YT - adj; b, se = ols(xgB[mgB], res_[mgB])
    P(f'  ΣΥΝΟΛΑ   {nm:22s}: ματς {int(mgB.sum())} · κλιση {b:+.2f} ± {se:.2f} · ανα σεζον '
      + ' '.join(f'{s[-2:]}:{ols(xgB[mgB & (ysB == s)], res_[mgB & (ysB == s)])[0]:+.2f}' for s in SE if (mgB & (ysB == s)).sum() >= 5))
moB = np.array([r['op'][1] - r['T'] for r in rowsB]); mcB = np.array([r['cl'][1] - r['T'] for r in rowsB])
for nm, z in (('ανοιγμα', moB), ('κλεισιμο', mcB)):
    X = np.c_[np.ones(len(rowsB)), FIX_B[('N', 'G0')], xgB]; b = np.linalg.lstsq(X, z, rcond=None)[0]; e = z - X @ b
    se = np.sqrt(np.diag(e @ e / (len(z) - 3) * np.linalg.inv(X.T @ X)))
    P(f'  ΑΓΟΡΑ συνολα  {nm:8s}: (γραμμη − μοντελο) = {b[1]:+.2f} ± {se[1]:.2f} × επιδραση OUT + {b[2]:+.2f} ± {se[2]:.2f} × επιδραση GTD')
save()
# ---- IV. Β ΣΥΝΟΛΑ ----
DFB = {dv: picksB(HELD_B[dv]) for dv in DEFS}; DFBF = {dv: picksB(FIX_B[dv]) for dv in DEFS}; DFB0 = picksB(np.zeros(len(rowsB)))
P(''); P('## 8. Β. ΣΥΝΟΛΑ — RMSE συνολου (ποντοι, LOSO) ανα σεζον και ΔRMSE vs G0 του ιδιου ορισμου (− = καλυτερο) · ref = R0+alias (live)')
for coefs, HH in (('LOSO bO/bD (κυριο)', HELD_B), ('σταθεροι live −0.426/−0.7975', FIX_B)):
    P(f'  --- {coefs} ---')
    P(f'  {"χωρις διορθωση":16s} RMSE {rmse(YT, ysB != ""):.3f} · ανα σεζον ' + ' '.join(f'{rmse(YT, ysB == s):.3f}' for s in SE))
    for d, v in DEFS:
        h = HH[(d, v)]; base0 = HH[('ref', None)] if d == 'ref' else HH[(d, 'G0')]
        dd = [rmse(YT - h, ysB == s) - rmse(YT - base0, ysB == s) for s in SE]
        P(f'  {lab(d, v):16s} RMSE {rmse(YT - h, ysB != ""):.3f} · ανα σεζον ' + ' '.join(f'{rmse(YT - h, ysB == s):.3f}' for s in SE)
          + ('' if d == 'ref' or v == 'G0' else ' · Δ vs G0 ' + ' '.join(f'{x:+.4f}' for x in dd) + f' (καλυτερο {sum(x < 0 for x in dd)}/5)'))
P(''); P('## 9. Β. ΣΥΝΟΛΑ — PICKS συνολων ≥8% στο ανοιγμα Crown')
for coefs, DD, HH in (('LOSO bO/bD (κυριο)', DFB, HELD_B), ('σταθεροι live', DFBF, FIX_B)):
    P(f'  --- {coefs} ---')
    P(f'  {"χωρις διορθωση":16s} {picks_line(DFB0)}')
    for d, v in DEFS:
        ln = f'  {lab(d, v):16s} {picks_line(DD[(d, v)])}'
        if d != 'ref' and v != 'G0':
            dd, ok = crit(YT, ysB, HH[(d, v)], HH[(d, 'G0')], DD[(d, v)], DD[(d, 'G0')])
            ln += f'  | κριτηριο vs {d}-G0: RMSE {sum(x < 0 for x in dd)}/5, μοναδες {summ(DD[(d, v)])[1] - summ(DD[(d, "G0")])[1]:+.1f}μ, θετ {summ(DD[(d, v)])[3]}/5 → {"✓" if ok else "✗"}'
        P(ln)
P(''); P('## 10. Β. ΣΥΝΟΛΑ — OVER / UNDER και αγωνιστικες 1-10 vs 11+ (LOSO· n · μοναδες · ROI)')
for d, v in DEFS:
    q = DFB[(d, v)]; q = q[q.pick.notna()]
    P(f'  {lab(d, v):16s} over: {seg(q, lambda z: z.pick == "over")} · under: {seg(q, lambda z: z.pick == "under")} · αγων 1-10: {seg(q, lambda z: z.rnd <= 10)} · 11+: {seg(q, lambda z: z.rnd > 10)}')
q0, q1 = DFB[('N', 'G0')], DFB[('N', 'G1')]
same = (q0.pick == q1.pick) & q0.pick.notna(); only0 = q0.pick.notna() & q1.pick.isna(); only1 = q1.pick.notna() & q0.pick.isna(); flip = q0.pick.notna() & q1.pick.notna() & (q0.pick != q1.pick)
P(f'  αλλαγες N-G0 → N-G1: ιδια {int(same.sum())} · μονο G0 {int(only0.sum())} ({q0[only0].units.sum():+.1f}μ) · μονο G1 {int(only1.sum())} ({q1[only1].units.sum():+.1f}μ) · αλλαξε πλευρα {int(flip.sum())}')
# ---- V. ΚΡΙΤΗΡΙΟ ----
P(''); P('################ ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (ορισμος N, LOSO): G1 / G_page αντι G0 ################')
for vv, vn in (('G1', 'G1'), ('Gp', 'G_page')):
    for nm, Y, ys, HH, DD in (('Α ΧΑΝΤΙΚΑΠ', YA_, ysA, HELD_A, DFA), ('Β ΣΥΝΟΛΑ', YT, ysB, HELD_B, DFB)):
        dd, ok = crit(Y, ys, HH[('N', vv)], HH[('N', 'G0')], DD[('N', vv)], DD[('N', 'G0')])
        n1, u1, r1, p1, _ = summ(DD[('N', vv)]); n0, u0, r0, p0, _ = summ(DD[('N', 'G0')])
        P(f'  {vn:6s} {nm}: RMSE καλυτερο σε {sum(x < 0 for x in dd)}/5 (Δ {" ".join(f"{x:+.4f}" for x in dd)}) · μοναδες {vn} {u1:+.1f}μ ({n1}) vs G0 {u0:+.1f}μ ({n0}) · θετικες {vn} {p1}/5 → '
          + ('κριτηριο ΠΛΗΡΟΥΤΑΙ' if ok else 'κριτηριο ΔΕΝ πληρουται'))
save()
# ---- VI. ΠΑΡΑΔΕΙΓΜΑΤΑ ----
P(''); P('################ ΕΛΕΓΧΟΣ ΠΑΡΑΔΕΙΓΜΑΤΩΝ — 3 ματς με σημαντικο GTD στο ανοιγμα (ορισμος N, σταθεροι live συντελεστες, ωρα Ελλαδας) ################')
BIDX = {(r['y'], r['hc'], r['ac'], round(r['ts'])): i for i, r in enumerate(rowsB)}
pk = lambda x: x if isinstance(x, str) else '—'
cands = []
for i, r in enumerate(rows):
    for side, lst in (('γηπ', r['CH']), ('φιλ', r['CA'])):
        for p in lst:
            if p['state'] != 'GTD' or gk(p['k']) == 0: continue
            c = (B_LIVE[0] + B_LIVE[1] * (p['pir'] - MU['pir']) / SD['pir']) * p['min'] / 40 * gk(p['k'])
            cands.append((c, i, side, p))
cands.sort(key=lambda x: -x[0])
picked, seenS = [], set()
for want_played in (True, False, None):
    for c, i, side, p in cands:
        if rows[i]['y'] in seenS or (want_played is not None and p['played'] != want_played): continue
        picked.append((c, i, side, p)); seenS.add(rows[i]['y']); break
for c, i, side, p in picked:
    r = rows[i]; nw = p['news']; m0 = r['m'] + FIX_A[('N', 'G0')][i]; m1 = r['m'] + FIX_A[('N', 'G1')][i]; mp = r['m'] + FIX_A[('N', 'Gp')][i]
    P(f'  {r["y"]} αγων {r["rnd"]} · {r["hc"]}-{r["ac"]} · τζαμπολ {gr(r["ts"])} · ανοιγμα Crown {gr(r["topen"])} ({(r["ts"] - r["topen"]) / 3600:.0f}ω πριν)')
    P(f'    παικτης: {NAME.get(p["pid"], p["pid"])} ({side}) · ρολος {p["role"]} · λεπτα {p["min"]:.1f}′ · PIR/40 {p["pir"]:.1f} · k {p["k"]}')
    P(f'    ειδηση ({nw[2]}): «{nw[3]}» — {nw[4][:200]}')
    P(f'    ωρα ειδησης {gr(nw[1])} = {(r["topen"] - nw[1]) / 3600:.1f}ω ΠΡΙΝ το ανοιγμα · {(r["ts"] - nw[1]) / 3600:.1f}ω πριν το ματς · κατηγορια {nw[0]} → GTD')
    P(f'    ΕΠΑΙΞΕ; {"ΝΑΙ " + format(p["mins_today"], ".0f") + "′" if p["played"] else "ΟΧΙ"} · κοστος G0 0.00π · G1 {c * P_ROLE[p["role"]]:.2f}π (×{P_ROLE[p["role"]]} του {c:.2f}π)')
    P(f'    ΧΑΝΤΙΚΑΠ: γραμμη ανοιγματος γηπ {r["op"][0]:+.1f} (αγορα αναμενει {r["mu_open"]:+.1f}) · μοντελο {r["m"]:+.1f} → G0 {m0:+.1f} / G1 {m1:+.1f} / G_page {mp:+.1f} · πραγματικο {r["act"]:+.0f} · '
      f'pick G0 {pk(DFAF[("N", "G0")].pick[i])} / G1 {pk(DFAF[("N", "G1")].pick[i])} / G_page {pk(DFAF[("N", "Gp")].pick[i])}')
    j = BIDX.get((r['y'], r['hc'], r['ac'], round(r['ts'])))
    if j is not None:
        rb = rowsB[j]
        P(f'    ΣΥΝΟΛΟ: γραμμη ανοιγματος {rb["op"][2]:.1f} · μοντελο {rb["T"]:.1f} → G0 {rb["T"] + FIX_B[("N", "G0")][j]:.1f} / G1 {rb["T"] + FIX_B[("N", "G1")][j]:.1f} · '
          f'πραγματικο {rb["hs"] + rb["as_"]:.0f} · pick G0 {pk(DFBF[("N", "G0")].pick[j])} / G1 {pk(DFBF[("N", "G1")].pick[j])} / G_page {pk(DFBF[("N", "Gp")].pick[j])}')
    others = [f'{NAME.get(q["pid"], q["pid"])} {q["state"]}' for q in r['CH'] + r['CA'] if q['state'] in ('OUT', 'GTD') and q['pid'] != p['pid'] and gk(q['k']) > 0]
    P(f'    αλλοι OUT/GTD στο ματς: {", ".join(others) or "κανενας"}')
P(''); P('################ ΕΛΕΓΧΟΣ ΠΑΡΑΔΕΙΓΜΑΤΩΝ G_page — (ii) και (iii) με το μεγαλυτερο κοστος (διαφορετικες σεζον) ################')
seenS = set()
for src in ('ii', 'iii', 'ii', 'iii'):
    best = None
    for i, r in enumerate(rows):
        if r['y'] in seenS: continue
        for side, lst in (('γηπ', r['CH']), ('φιλ', r['CA'])):
            for p in lst:
                if p['pstate'] != src or gk(p['k']) == 0: continue
                c = (B_LIVE[0] + B_LIVE[1] * (p['pir'] - MU['pir']) / SD['pir']) * p['min'] / 40 * gk(p['k'])
                if best is None or c > best[0]: best = (c, i, side, p)
    if not best: continue
    c, i, side, p = best; r = rows[i]; seenS.add(r['y']); pp = weight(p, 'N', 'Gp')
    P(f'  [{src}] {r["y"]} αγων {r["rnd"]} · {r["hc"]}-{r["ac"]} · τζαμπολ {gr(r["ts"])} · ανοιγμα {gr(r["topen"])}')
    seq = ''.join('Π' if d.get(p['pid'], (0,))[0] > 0 else '·' for _, _, d in [x for x in TG[(r['sea'], r['hc'] if side == 'γηπ' else r['ac'])] if x[0] < r['ts'] - 3600][-6:])
    P(f'    {NAME.get(p["pid"], p["pid"])} ({side}) · ρολος {p["role"]} · λεπτα {p["min"]:.1f}′ · PIR/40 {p["pir"]:.1f} · k {p["k"]} · 6 τελευταια ματς ομαδας (Π = επαιξε) {seq} · επαιξε στο προηγ.: {"ναι" if p["pprev"] else "οχι"}')
    if p['pnews']: P(f'    ειδηση {gr(p["pnews"][1])} ({(r["topen"] - p["pnews"][1]) / 3600:.1f}ω πριν το ανοιγμα): «{p["pnews"][3]}» — {p["pnews"][4][:180]}')
    else: P('    καμια ειδηση στο παραθυρο (προηγ. ματς → ανοιγμα)')
    P(f'    ΕΠΑΙΞΕ; {"ΝΑΙ " + format(p["mins_today"], ".0f") + "′" if p["played"] else "ΟΧΙ"} · κοστος ×1 {c:.2f}π · G0 0 · G_page ×{pp:.2f} = {c * pp:.2f}π · '
      f'χαντικαπ: γραμμη γηπ {r["op"][0]:+.1f} · μοντελο {r["m"]:+.1f} → G0 {r["m"] + FIX_A[("N", "G0")][i]:+.1f} / G_page {r["m"] + FIX_A[("N", "Gp")][i]:+.1f} · πραγματικο {r["act"]:+.0f}')
P(''); P(f'χρονος {time.time() - T0:.0f} δευτ.')
save()
