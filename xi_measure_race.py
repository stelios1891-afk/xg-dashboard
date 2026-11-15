# -*- coding: utf-8 -*-
"""xi_measure_race.py — 21/10/2026 (Στελιος: «ποιος ειναι ο καλυτερος τροπος να υπολογισεις τη δυναμη μιας ενδεκαδας; αξια, βαθμολογια FotMob, τι;
τρεξε τα παντα — πριν βγαλουμε συμπερασματα πρεπει να βρουμε τον καλυτερο τροπο»).
ΑΓΩΝΑΣ ΜΕΤΡΩΝ για τη δυναμη του ΚΑΘΕ παικτη (μονο πληροφορια ΠΡΙΝ το ματς, walk-forward απο 2021-22):
  M1 ΒΑΘΜΟΛΟΓΙΑ FotMob — φθινων (0.95/εμφ.) μεσος σταθμισμενος με λεπτα, συρρικνωση K=5 προς μεσο θεσης (οπως Lineup Lab)
  M2 ΒΑΘΜΟΛΟΓΙΑ ανα θεση — ιδια, αλλα σε μοναδες τυπικης αποκλισης της θεσης του (διορθωνει «φουσκωμα» επιθετικων / αδικια τερματοφυλακων)
  M3 ΑΞΙΑ — ln(αξια) στην ημερομηνια του ματς (ιστορικο ανα εξαμηνο)
  M4 ΕΜΠΙΣΤΟΣΥΝΗ ΠΡΟΠΟΝΗΤΗ — μεριδιο λεπτων οταν ειναι στην αποστολη (τελευταια 10 ματς της ομαδας)
  M5 ΕΠΙΔΡΑΣΗ ΣΤΟ xG (RAPM) — ridge: διαφορα xG της ομαδας ανα ματς ~ λεπτα παικτων (+) − αντιπαλων (−) + εδρα, βαρος φθινει με τον χρονο,
     ξαναεκτιμηση καθε 14 μερες με ΜΟΝΟ τα προηγουμενα ματς (λ = 30 / 100 / 300)
ΔΥΝΑΜΗ ΕΝΔΕΚΑΔΑΣ = μεσος ορος των 11 βασικων · Δ = ενδεκαδα σημερα − φθινων (0.9) μεσος των προηγουμενων ενδεκαδων της ομαδας
  (το μοντελο εχει ηδη τη «συνηθισμενη» συνθεση· μετραμε την αποκλιση). Χαρακτηριστικο ματς = Δ γηπ − Δ φιλ.
ΚΡΙΤΗΡΙΟ (γραφτηκε ΠΡΙΝ): στοχος = λαθος του live μοντελου (core7_mech_preds_bl_0.6) σε ΔΙΑΦΟΡΑ xG (λιγοτερος θορυβος) και σε ΔΙΑΦΟΡΑ ΓΚΟΛ·
  νικητης = μεγαλυτερη μειωση τετραγωνικου λαθους εκτος δειγματος (LOSO 4 σεζον 2223-2526), θετικη σε ≥3/4 σεζον ΚΑΙ σε ≥5/7 λιγκες.
  Μετα: συνδυασμοι (πολλαπλη LOSO) και ανα θεση. Χρησιμοποιουνται οι ΠΡΑΓΜΑΤΙΚΕΣ ενδεκαδες (κρινουμε το μετρο, οχι τη λιστα απουσων)."""
import sys, json, glob, re, collections, datetime as dt, math
import numpy as np, pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import lsqr
sys.stdout.reconfigure(encoding='utf-8')
NL = chr(10)
LG = {'EPL': 'EPL', 'LaLiga': 'LaLiga', 'SerieA': 'SerieA', 'Bundesliga': 'Bundesliga', 'Ligue1': 'Ligue1', 'Eredivisie': 'Eredivisie', 'PrimeiraLiga': 'PrimeiraLiga'}
# ---------- ματς FotMob: ημερομηνια, ομαδες, xG 90′, γκολ ----------
FM = {}
for lg in LG:
    for f in glob.glob(f'data_{lg}_*.json'):
        sea = re.search(r'_(\d{4})\.json$', f).group(1)
        for k, v in json.load(open(f, encoding='utf-8')).items():
            try: d = dt.datetime.strptime(v['date'], '%a, %b %d, %Y, %H:%M UTC')
            except Exception: continue
            hid = v['home']['id']; xh = xa = 0.0; has = False
            for s in v.get('shots') or []:
                if s.get('xg') is None: continue
                has = True
                if s.get('tid') == hid: xh += s['xg']
                else: xa += s['xg']
            FM[str(k)] = dict(lg=lg, sea=sea, date=d, hid=hid, aid=v['away']['id'], hs=v.get('hs'), as_=v.get('as'), xh=xh if has else None, xa=xa if has else None)
SQ = json.load(open('core7_squads.json', encoding='utf-8'))
PM = json.load(open('player_matches.json', encoding='utf-8'))
VAL = {}
for f in ('core7_player_values.json', 'euro_player_values.json'):
    for k, v in json.load(open(f, encoding='utf-8')).items():
        if v.get('hist') and str(k) not in VAL: VAL[str(k)] = [(h[0], h[1]) for h in v['hist'] if h[1]]
ORDER = sorted([k for k in FM if k in SQ and SQ[k].get('h') and SQ[k].get('a')], key=lambda k: FM[k]['date'])
print(f'ματς με ενδεκαδες: {len(ORDER)} ({FM[ORDER[0]]["date"]:%Y-%m-%d} → {FM[ORDER[-1]]["date"]:%Y-%m-%d})')
# ---------- θεσεις & στατιστικα θεσεων ----------
PL_POS = {}
POSV = collections.defaultdict(list)
for k in ORDER:
    for s in ('h', 'a'):
        for e in ((PM.get(k) or {}).get(s) or {}).get('p', []) or []:
            PL_POS[str(e[0])] = e[3]
            if e[1] is not None: POSV[e[3]].append(e[1])
POS_MU = {p: float(np.mean(v)) for p, v in POSV.items() if p in (0, 1, 2, 3)}; POS_SD = {p: float(np.std(v)) for p, v in POSV.items() if p in (0, 1, 2, 3)}
for _p in list(PL_POS):
    if PL_POS[_p] not in (0, 1, 2, 3): PL_POS[_p] = 2          # αγνωστη θεση → μεσος
def value_at(pid, ds):
    h = VAL.get(pid)
    if not h: return None
    v = None
    for t, x in h:
        if t <= ds: v = x
        else: break
    return v if v is not None else h[0][1]
# ---------- RAPM (ridge, walk-forward καθε 14 μερες) ----------
LAMS = (30.0, 100.0, 300.0)
PIDX = {}
rows_t, rows_i, rows_v, rows_y, rows_d = [], [], [], [], []
def pid_ix(p):
    if p not in PIDX: PIDX[p] = len(PIDX)
    return PIDX[p]
RAPM = {lam: {} for lam in LAMS}; next_fit = None
def refit(now):
    if len(rows_y) < 500: return
    n = len(rows_y); P = len(PIDX)                              # περιλαμβανει τη στηλη εδρας '__HOME__'
    age = np.array([(now - d).days for d in rows_d], float); w = np.sqrt(np.exp(-age / 365.0))
    data = np.array(rows_v) * w[np.array(rows_t)]
    X = csr_matrix((data, (rows_t, rows_i)), shape=(n, P)); y = np.array(rows_y) * w
    for lam in LAMS:
        b = lsqr(X, y, damp=math.sqrt(lam))[0]
        RAPM[lam] = {p: b[i] for p, i in PIDX.items()}
# ---------- walk-forward ----------
RT = {}                 # pid -> (Σw·rt, Σw)
TEAM_MIN = collections.defaultdict(list)     # team -> [(set in squad, {pid: min})]
BASE = collections.defaultdict(dict)          # team -> measure -> decayed mean XI
OUT = []
MEAS = ['M1', 'M2', 'M3', 'M4'] + [f'M5_{int(l)}' for l in LAMS]
for k in ORDER:
    m = FM[k]; sq = SQ[k]; ds = m['date'].strftime('%Y-%m-%d')
    if next_fit is None or m['date'] >= next_fit:
        refit(m['date']); next_fit = m['date'] + dt.timedelta(days=14)
    rec = dict(mid=k, lg=m['lg'], sea=m['sea'], date=ds)
    for fs, tid in (('h', m['hid']), ('a', m['aid'])):
        st = [str(p) for p in sq[fs]['st']]
        def m1(p):
            s = RT.get(p); pos = PL_POS.get(p, 2); mu = POS_MU.get(pos, 6.7)
            return (s[0] + 5 * mu) / (s[1] + 5) if s else mu
        def m2(p):
            pos = PL_POS.get(p, 2); return (m1(p) - POS_MU.get(pos, 6.7)) / max(POS_SD.get(pos, .5), 1e-6)
        def m3(p):
            v = value_at(p, ds); return math.log(v) if v else None
        hist = TEAM_MIN[tid][-10:]
        def m4(p):
            ins = [mn.get(p) for _, mn in hist if p in mn]
            return (sum(ins) / (90.0 * len(ins))) if ins else 0.3
        vals = {'M1': [m1(p) for p in st], 'M2': [m2(p) for p in st], 'M3': [m3(p) for p in st], 'M4': [m4(p) for p in st]}
        for lam in LAMS: vals[f'M5_{int(lam)}'] = [RAPM[lam].get(p, 0.0) for p in st]
        v3 = [x for x in vals['M3'] if x is not None]; med = float(np.median(v3)) if v3 else None
        vals['M3'] = [x if x is not None else (med if med is not None else np.nan) for x in vals['M3']]
        for me in MEAS:
            S = float(np.nanmean(vals[me])) if len(vals[me]) else np.nan
            b = BASE[tid].get(me)
            rec[f'{me}_{fs}'] = S - b if (b is not None and np.isfinite(S)) else np.nan
            rec[f'{me}_{fs}_lvl'] = S
            BASE[tid][me] = S if b is None else (0.9 * b + 0.1 * S if np.isfinite(S) else b)
            # ανα θεση (αμυνα = 0/1, επιθεση = 2/3): αθροισμα αποκλισης vs συνηθισμενου
            for grp, poss in (('D', (0, 1)), ('O', (2, 3))):
                xs = [x for p, x in zip(st, vals[me]) if PL_POS.get(p, 2) in poss and np.isfinite(x)]
                Sg = float(np.mean(xs)) if xs else np.nan; key = me + grp; bg = BASE[tid].get(key)
                rec[f'{key}_{fs}'] = Sg - bg if (bg is not None and np.isfinite(Sg)) else np.nan
                BASE[tid][key] = Sg if bg is None else (0.9 * bg + 0.1 * Sg if np.isfinite(Sg) else bg)
    OUT.append(rec)
    # ---------- ενημερωσεις ΜΕΤΑ το ματς ----------
    for fs, tid, opp in (('h', m['hid'], 'a'), ('a', m['aid'], 'h')):
        mins = {str(p): mn for p, mn in sq[fs]['p'].items()}
        TEAM_MIN[tid].append((set(mins), mins))
        for e in ((PM.get(k) or {}).get(fs) or {}).get('p', []) or []:
            p, rt = str(e[0]), e[1]
            if rt is None: continue
            w = max(mins.get(p, 90), 1) / 90.0; s0 = RT.get(p, (0.0, 0.0)); RT[p] = (s0[0] * 0.95 + w * rt, s0[1] * 0.95 + w)
    if m['xh'] is not None:
        for fs, sign_y in (('h', 1.0), ('a', -1.0)):
            r = len(rows_y)
            for p, mn in sq[fs]['p'].items():
                if mn > 0: rows_t.append(r); rows_i.append(pid_ix(str(p))); rows_v.append(mn / 90.0)
            ofs = 'a' if fs == 'h' else 'h'
            for p, mn in sq[ofs]['p'].items():
                if mn > 0: rows_t.append(r); rows_i.append(pid_ix(str(p))); rows_v.append(-mn / 90.0)
            rows_t.append(r); rows_i.append(pid_ix('__HOME__')); rows_v.append(sign_y)
            rows_y.append((m['xh'] - m['xa']) * sign_y); rows_d.append(m['date'])
D = pd.DataFrame(OUT)
D.to_csv('xi_measure_rows.csv', index=False)
print('ετοιμο: xi_measure_rows.csv', len(D))
