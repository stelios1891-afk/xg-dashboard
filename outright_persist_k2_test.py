# -*- coding: utf-8 -*-
"""outright_persist_k2_test.py — ΣΗΜΕΡΑ vs ΠΡΟΤΑΣΗ: ποσο γρηγορα σβηνουν οι αποδοσεις νικητη (13/10/2026, follow-up του outright_persist_test,
προταση Στελιου: σβησιμο ΜΟΝΟ με ματς διοργανωσης σε ~2-4 ματς).
Ιδια δεδομενα/ορισμοι με outright_persist_test.py: βασεις απο outright_persist_bases.pkl (BCL22 · EC23-25 · EL24-25, χωρις outrights/ειδικους),
  ιδιο z (−ln αποδοσης, χωρις τιμη = 1.5×μεγιστη, τυποποιηση ανα διοργανωση-σεζον), r = μεσος αριθμος ματς κανονικης περιοδου που εχουν
  ηδη παιξει οι δυο ομαδες. Μοντελο: pred = βαση + κ·(z_γ − z_φ)·k/(k + r).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (γραφτηκε ΠΡΙΝ την εκτελεση, ΜΙΑ εκτελεση):
  ΣΚΕΛΗ: ΣΗΜΕΡΑ = k 0.6 (≈ σημερινο BCL live, 0.5-0.75 σε ματς διοργανωσης) · ΠΡΟΤΑΣΗ = k ∈ {2, 3, 4}.
  Για καθε σκελος: κ απο LOSO στις 6 διοργανωσεις-σεζον (πλεγμα κ 0…6 ανα 0.5), ελαχιστο τετραγωνικο λαθος διαφορας στις ΑΛΛΕΣ 5
    (ολα τα ματς κανονικης περιοδου)· για την ΠΡΟΤΑΣΗ το k ∈ {2,3,4} επιλεγεται ΜΑΖΙ με το κ μεσα στο LOSO (εκτος δειγματος).
  ΠΕΡΝΑ αν: held-out RMSE ΠΡΟΤΑΣΗΣ < ΣΗΜΕΡΑ σε ≥5/6 διοργανωσεις-σεζον ΚΑΙ ενωμενη held-out διαφορα MSE (ΠΡΟΤΑΣΗ − ΣΗΜΕΡΑ) < 0
    με |Δ|/τ.σ. ≥ 1.
  ΑΝΑΦΟΡΑ: ανα fold (κ,k) και ΔRMSE ΠΡΟΤΑΣΗ−ΣΗΜΕΡΑ · ενωμενα σε ματς 1-3 (r<3) / 4-6 (3≤r<6) / 7-10 (6≤r<10) / 11+ (r≥10) ·
    καθε σταθερο k (0.6, 1, 2, 3, 4) in-sample ενωμενα (καλυτερο κ) · ROI χαντικαπ edge ≥8% στο ΑΝΟΙΓΜΑ (BCL σ12 Crown/Bet365 · EC/EL σ11.5 Crown)
    ΣΗΜΕΡΑ vs ΠΡΟΤΑΣΗ (LOSO) σε ματς 1-3 / 4-6 / 7+ · ποσο απο το αρχικο αποτελεσμα μενει (k/(k+r)) σε r = 1, 3, 5, 10.
Εξοδος: outright_persist_k2_test_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, math, pickle, collections, builtins, time
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
SCR = r'C:\Users\steli\AppData\Local\Temp\claude\C--Users-steli-My-Drive-Betting-Model\67d4ba59-0c37-4db7-a951-badbf5076962\scratchpad'
OUTF, CACHE = 'outright_persist_k2_test_out.txt', 'outright_persist_bases.pkl'
out = []
def P(s=''): print(s, flush=True); out.append(str(s))

# ---------------- ΦΡΟΥΡΟΣ: τα παλια scripts που εκτελουνται για τις βασεις ΔΕΝ γραφουν στο repo ----------------
_real_open = builtins.open
def _guard(file, mode='r', *a, **k):
    if isinstance(file, (str, os.PathLike)) and any(c in mode for c in 'wax+'):
        bn = os.path.basename(str(file))
        if bn not in (OUTF, CACHE):
            os.makedirs(SCR, exist_ok=True); file = os.path.join(SCR, bn)
    return _real_open(file, mode, *a, **k)

def _snap():
    return {f: os.path.getmtime(f) for f in os.listdir('.') if os.path.isfile(f)}

# =============================== ΒΑΣΕΙΣ ===============================
def build_bcl():
    D = pickle.load(open('bcl_engine_preds_live.pkl', 'rb')); MK = pickle.load(open('bcl_mk.pkl', 'rb'))
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    y = 2022
    G = sorted([e for e in FG[f'BCL_{y}'] if e.get('hs') not in (None, '')], key=lambda e: e['ts'])
    RSST = ('EUROPE: Champions League', 'EUROPE: Champions League - Winners stage')
    cnt = collections.Counter(); R = {}; EV = {}
    for e in G:
        if e['stage'] not in RSST: continue
        R[e['id']] = (cnt[e['hid']] + cnt[e['aid']]) / 2.0
        cnt[e['hid']] += 1; cnt[e['aid']] += 1; EV[e['id']] = e
    gs_teams = {}
    for e in G:
        if e['stage'] == 'EUROPE: Champions League': gs_teams[e['hid']] = e['home']; gs_teams[e['aid']] = e['away']
    ids = list(D['id']); rows = []
    for k_, i in enumerate(ids):
        if int(D['y'][k_]) != y or i not in EV: continue
        b = float(D['FIN'][k_])
        if not np.isfinite(b): continue
        e = EV[i]; mk = []
        for bk in (3, 8):
            v = MK.get(i, {}).get(bk, {}).get('o')
            if v: mk.append((float(v[0]), float(v[2]), float(v[3])))
        rows.append(dict(cs='BCL22', comp='BCL', home=e['hid'], away=e['aid'], act=float(int(e['hs']) - int(e['as_'])), base=b, base_alt=np.nan,
                         r=R[i], mk=mk, sig=12.0))
    return rows, gs_teams

def build_ec():
    NS = {'__name__': 'ecx'}
    src = open('ec_expert_test.py', encoding='utf-8').read()
    head = src.split("EX = json.load(open('ec_expert.json'")[0]
    exec(head, NS)
    D = NS['D']; base = NS['run'](0.5, 1, 1, 0.0)
    mseg = src.split("N = NormalDist(); Phi = N.cdf")[1].split("FAMS = ")[0]
    exec("N = NormalDist(); Phi = N.cdf" + mseg, NS)
    MK = NS['MK']
    rows = []; teams = {}
    for S in ('U2023', 'U2024', 'U2025'):
        idx = [i for i in np.where(D.season.values == S)[0] if D.phase.values[i] == 'RS']
        idx = sorted(idx, key=lambda i: pd.Timestamp(D.t.values[i]))
        cnt = collections.Counter(); tm = {}
        for i in idx:
            h, a = D.home.values[i], D.away.values[i]; tm[h] = D.hname.values[i]; tm[a] = D.aname.values[i]
            r = (cnt[h] + cnt[a]) / 2.0; cnt[h] += 1; cnt[a] += 1
            if not np.isfinite(base[i]): continue
            mk = [(float(MK[i]['o'][0]), float(MK[i]['o'][2]), float(MK[i]['o'][3]))] if i in MK else []
            rows.append(dict(cs='EC' + S[-2:], comp='EC', home=h, away=a, act=float(D.hs.values[i] - D.as_.values[i]), base=float(base[i]),
                             base_alt=np.nan, r=r, mk=mk, sig=11.5))
        teams[S] = tm
    return rows, teams

def build_el():
    NS = {'__name__': 'elx'}
    src = open('el_preseason_test.py', encoding='utf-8').read()
    head = src.split('# ---- 1. διαγνωση ----')[0]
    exec(head, NS)
    fdef = 'def run_pre(kp):' + src.split('def run_pre(kp):')[1].split('E10 = RSM')[0]
    exec(fdef, NS)
    cfg = NS['cfg']; live_like = NS['NS']['live_like']; GN = NS['GN']; D = NS['D']
    P(f'  EL live cfg πριν: {dict(cfg)}')
    res = {}
    for wt in (0.7, 0.5):
        cfg['we'] = 0.0; cfg['wt'] = wt
        a = live_like(0.0, 99, 2); b = NS['run_pre'](0.5)
        res[wt] = np.where(GN > 10, a, b)
        print(f'  EL βαση wt {wt} ετοιμη', flush=True)
    base, alt = res[0.7], res[0.5]
    # ---- Crown ανοιγμα (Nowgoal) με αντιστοιχιση σκορ + ωρα (οπως ec_expert_test) ----
    N = NormalDist()
    tcol = 't' if 't' in D.columns else 'date'
    TT = pd.to_datetime(D[tcol].values)
    TT = TT.tz_localize(None) if getattr(TT, 'tz', None) is not None else TT
    ROWS = {}
    for ln in open('nowgoal_el/odds.jsonl', encoding='utf-8'):
        r = json.loads(ln)
        if r.get('ot') == 6 and r.get('t', 21) == 21 and r['cid'] == 3: ROWS[r['ngid']] = r['rows']
    MK = {}
    for sea, es in (('24-25', 'E2024'), ('25-26', 'E2025')):
        ix2 = {}
        for i in np.where(D.season.values == es)[0]:
            try: ix2.setdefault((int(D.hs.values[i]), int(D.as_.values[i])), []).append(i)
            except Exception: pass
        for g in json.load(open(f'nowgoal_el/sched_{sea}.json', encoding='utf-8')):
            if g.get('hs') is None or g['ngid'] not in ROWS: continue
            tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit, sw = None, False
            for (a_, b_), swp in (((g['hs'], g['as_']), False), ((g['as_'], g['hs']), True)):
                for i in ix2.get((a_, b_), []):
                    if abs(TT[i] - tip) <= pd.Timedelta(hours=26): hit, sw = i, swp; break
                if hit is not None: break
            if hit is None: continue
            rws = sorted([x for x in ROWS[g['ngid']] if x[4] == 2 and x[1] is not None and x[2] and x[3] and x[0] + 8 * 3600 <= tip.timestamp() + 600], key=lambda x: x[0])
            if not rws: continue
            x = rws[0]; o1, o2 = 1 + x[2], 1 + x[3]; L = -x[1]
            MK[hit] = (-L, o2, o1) if sw else (L, o1, o2)
    rows = []; teams = {}
    for es in ('E2024', 'E2025'):
        idx = sorted([i for i in np.where(D.season.values == es)[0] if D.phase.values[i] == 'RS'], key=lambda i: TT[i])
        cnt = collections.Counter(); tm = {}
        for i in idx:
            h, a = D.home.values[i], D.away.values[i]; tm[h] = 1; tm[a] = 1
            r = (cnt[h] + cnt[a]) / 2.0; cnt[h] += 1; cnt[a] += 1
            if not np.isfinite(base[i]): continue
            rows.append(dict(cs='EL' + es[-2:], comp='EL', home=h, away=a, act=float(D.hs.values[i] - D.as_.values[i]), base=float(base[i]),
                             base_alt=float(alt[i]), r=r, mk=[MK[i]] if i in MK else [], sig=11.5))
        teams[es] = sorted(tm)
    return rows, teams

if os.path.exists(CACHE):
    C = pickle.load(open(CACHE, 'rb')); P(f'(βασεις απο cache {CACHE})')
else:
    s0 = _snap(); builtins.open = _guard; t0 = time.time()
    try:
        bcl_rows, bcl_teams = build_bcl(); print(f'BCL ετοιμο {time.time()-t0:.0f}s', flush=True)
        ec_rows, ec_teams = build_ec(); print(f'EC ετοιμο {time.time()-t0:.0f}s', flush=True)
        el_rows, el_teams = build_el(); print(f'EL ετοιμο {time.time()-t0:.0f}s', flush=True)
    finally:
        builtins.open = _real_open
    s1 = _snap()
    ch = sorted(f for f in s1 if f not in (OUTF, CACHE) and (f not in s0 or s1[f] != s0[f]))
    C = dict(rows=bcl_rows + ec_rows + el_rows, bcl_teams=bcl_teams, ec_teams=ec_teams, el_teams=el_teams, changed=ch)
    pickle.dump(C, open(CACHE, 'wb'))
P(f'ελεγχος: αρχεια του repo που αλλαξαν κατα το χτισιμο των βασεων: {C["changed"] or "κανενα"}')

# =============================== OUTRIGHTS → z ===============================
EC_OR = json.load(open('ec_outrights.json', encoding='utf-8'))
EX = json.load(open('ec_expert.json', encoding='utf-8'))          # αντιστοιχιση ονοματων → κωδικων (ec_expert_map.py)
EL_OR = json.load(open('el_outrights.json', encoding='utf-8'))
BCL_OR = json.load(open('bcl_outrights.json', encoding='utf-8'))
EL_MAP = {
 'E2024': {'ΟΛΥΜΠΙΑΚΟΣ': 'OLY', 'ΠΑΝΑΘΗΝΑΪΚΟΣ': 'PAN', 'ΡΕΑΛ ΜΑΔΡΙΤΗΣ': 'MAD', 'ΦΕΝΕΡΜΠΑΧΤΣΕ': 'ULK', 'ΜΟΝΑΚΟ': 'MCO', 'ΜΠΑΡΤΣΕΛΟΝΑ': 'BAR',
           'ΕΦΕΣ': 'IST', 'ΠΑΡΤΙΖΑΝ': 'PAR', 'ΜΙΛΑΝΟ': 'MIL', 'ΕΡΥΘΡΟΣ ΑΣΤΕΡΑΣ': 'RED', 'ΜΠΑΣΚΟΝΙΑ': 'BAS', 'ΜΑΚΑΜΠΙ ΤΕΛ ΑΒΙΒ': 'TEL',
           'ΒΙΡΤΟΥΣ ΜΠΟΛΟΝΙΑ': 'VIR', 'ΜΠΑΓΕΡΝ ΜΟΝΑΧΟΥ': 'MUN', 'ΠΑΡΙ': 'PRS', 'ΖΑΛΓΚΙΡΙΣ': 'ZAL', 'ΒΙΛΕΡΜΠΑΝ': 'ASV', 'ΑΛΜΠΑ ΒΕΡΟΛΙΝΟΥ': 'BER'},
 'E2025': {'Παναθηναϊκός': 'PAN', 'Ολυμπιακός': 'OLY', 'Ρεάλ Μαδρίτης': 'MAD', 'Φενέρμπαχτσε': 'ULK', 'Χαποέλ Τελ Αβίβ': 'HTA', 'Μονακό': 'MCO',
           'Μπαρτσελόνα': 'BAR', 'Αναντολού Έφες': 'IST', 'Αρμάνι Μιλάνο': 'MIL', 'Παρτίζαν': 'PAR', 'Ερυθρός Αστέρας': 'RED', 'Ντουμπάι': 'DUB',
           'Μακάμπι Τελ Αβίβ': 'TEL', 'Βίρτους Μπολόνια': 'VIR', 'Ζάλγκιρις Κάουνας': 'ZAL', 'Βαλένθια': 'PAM', 'Μπάγερν Μονάχου': 'MUN',
           'Μπασκόνια': 'BAS', 'Παρί': 'PRS', 'Βιλερμπάν': 'ASV'}}
BCL_MAP = {'Lenovo Tenerife': 'Tenerife', 'Unicaja': 'Unicaja', 'Galatasaray': 'Galatasaray', 'BAXI Manresa': 'Manresa', 'UCAM Murcia': 'Murcia',
           'MHP RIESEN Ludwigsburg': 'Ludwigsburg', 'SIG Strasbourg': 'Strasbourg', 'Pinar Karsiyaka': 'Karsiyaka', 'Peristeri': 'Peristeri',
           'AEK': 'AEK Athens', 'PAOK': 'PAOK'}
Z = {}
def zset(cs, allteams, odds_by_team):
    """allteams: κωδικοι ολων των ομαδων κανονικης περιοδου · odds_by_team: {κωδικος: αποδοση} μονο για οσες ειναι στη λιστα"""
    mx = max(odds_by_team.values())
    x = {t: -math.log(odds_by_team[t]) if t in odds_by_team else -math.log(1.5 * mx) for t in allteams}
    v = np.array(list(x.values())); m, s = v.mean(), v.std()
    for t in allteams: Z[(cs, t)] = ((x[t] - m) / s, t in odds_by_team)
    return mx
P(''); P('=== ΑΝΤΙΣΤΟΙΧΙΣΗ ΟΝΟΜΑΤΩΝ / z ===')
# BCL
nm2id = {v: k for k, v in C['bcl_teams'].items()}
od = {}
for nm, o in BCL_OR['U2022']['odds'].items():
    od[nm2id[BCL_MAP[nm]]] = o
mx = zset('BCL22', list(C['bcl_teams']), od)
P(f'BCL22 (ΣΗΜΑΙΑ: δημοσιευση ΚΑΤΑ την 1η αγωνιστικη, 11/32 στη λιστα, χωρις τιμη → αποδοση {1.5*mx:.1f}): '
  + ' · '.join(f'{nm}→{BCL_MAP[nm]}' for nm in BCL_OR['U2022']['odds']))
# EC
for S in ('U2023', 'U2024', 'U2025'):
    allt = list(C['ec_teams'][S]); od = {c: d['odds'] for c, d in EX[S].items() if d.get('odds') and c in allt}
    raw = EC_OR[S]['odds']
    for c, o in od.items(): assert any(abs(o - v) < 1e-9 for v in raw.values()), (S, c, o)
    used = set(round(v, 4) for v in od.values())
    notmapped = [f'{n} ({v})' for n, v in raw.items() if round(v, 4) not in used]
    mx = zset('EC' + S[-2:], allt, od)
    unl = [f'{c} {C["ec_teams"][S][c]}' for c in allt if c not in od]
    P(f'EC{S[-2:]}: στη λιστα {len(od)}/{len(allt)} · ονοματα λιστας που ΔΕΝ επαιξαν (αγνοουνται): {notmapped or "—"} · '
      f'χωρις τιμη (→ {1.5*mx:.1f}): {unl or "—"}')
# EL
for key, es in (('2024-25 (bet365)', 'E2024'), ('2025-26 (Novibet;)', 'E2025')):
    allt = C['el_teams'][es]; od = {}
    for nm, o in EL_OR[key]:
        c = EL_MAP[es][nm]; assert c in allt, (es, nm, c); od[c] = o
    mx = zset('EL' + es[-2:], allt, od)
    P(f'EL{es[-2:]}: στη λιστα {len(od)}/{len(allt)} · ' + ' · '.join(f'{nm}→{EL_MAP[es][nm]}' for nm, _ in EL_OR[key])
      + (f' · χωρις τιμη: {[c for c in allt if c not in od]}' if len(od) < len(allt) else ''))

# =============================== ΠΙΝΑΚΑΣ ΔΕΔΟΜΕΝΩΝ ===============================
R = pd.DataFrame(C['rows'])
R['zd'] = [Z[(c, h)][0] - Z[(c, a)][0] for c, h, a in zip(R.cs, R.home, R.away)]
R['both'] = [Z[(c, h)][1] and Z[(c, a)][1] for c, h, a in zip(R.cs, R.home, R.away)]
R['res'] = R.act - R.base
CSS = ['BCL22', 'EC23', 'EC24', 'EC25', 'EL24', 'EL25']
COMPS = ['BCL', 'EC', 'EL']
P(''); P('ματς κανονικης περιοδου ανα διοργανωση-σεζον: ' + ' · '.join(f'{c} {int((R.cs == c).sum())}' for c in CSS)
  + f' · συνολο {len(R)} · RMSE βασης ' + ' · '.join(f'{c} {np.sqrt(np.mean(R.res[R.cs == c] ** 2)):.2f}' for c in CSS))
P('τ.α. (z_γ − z_φ): ' + ' · '.join(f'{c} {R.zd[R.cs == c].std():.2f}' for c in CSS))

Phi = NormalDist().cdf
def pick_u(m, L, o1, o2, x, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m + L - .5) / s); pl = Phi((-m - L - .5) / s)
    else: pw = Phi((m + L) / s); pl = 1 - pw
    pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    if e < .08: return None
    v = x * side; return (od - 1) if v > 0 else (0 if v == 0 else -1)

# =============================== ΣΚΕΛΗ ===============================
ACT, BASE, ZD, RR, CS, CO = R.act.values, R.base.values, R.zd.values, R.r.values, R.cs.values, R.comp.values
KAP = [x / 2 for x in range(13)]                     # 0 … 6 ανα 0.5
def pred(kp, k): return BASE + kp * ZD * (k / (k + RR))
SQ0 = (ACT - BASE) ** 2
SQC = {}
def sq(kp, k):
    if (kp, k) not in SQC: SQC[(kp, k)] = (ACT - pred(kp, k)) ** 2
    return SQC[(kp, k)]
ARMS = {'ΣΗΜΕΡΑ (k 0.6)': [0.6], 'ΠΡΟΤΑΣΗ (k 2-4)': [2, 3, 4]}
HELD, CH = {}, {}
for arm, ks in ARMS.items():
    held = np.full(len(R), np.nan); ch = {}
    for c in CSS:
        tr = CS != c
        g = min([(kp, k) for kp in KAP for k in ks], key=lambda g: (sq(*g)[tr].sum(), g[0], g[1]))
        ch[c] = g; held[CS == c] = pred(*g)[CS == c]
    HELD[arm], CH[arm] = held, ch
T, Pp = 'ΣΗΜΕΡΑ (k 0.6)', 'ΠΡΟΤΑΣΗ (k 2-4)'
sT, sP = (ACT - HELD[T]) ** 2, (ACT - HELD[Pp]) ** 2
def rm(s, m): return math.sqrt(s[m].mean())
P(''); P('=== LOSO ανα fold: επιλογη (κ,k) · held-out RMSE · Δ ΠΡΟΤΑΣΗ − ΣΗΜΕΡΑ ===')
wins = 0
for c in CSS:
    m = CS == c; d = rm(sP, m) - rm(sT, m); wins += d < 0
    P(f'  εξω {c:6s} n {m.sum():3d} · ΣΗΜΕΡΑ κ {CH[T][c][0]:g} k 0.6 → {rm(sT, m):.3f} · ΠΡΟΤΑΣΗ κ {CH[Pp][c][0]:g} k {CH[Pp][c][1]:g} → {rm(sP, m):.3f}'
      f' · Δ {d:+.3f} · (βαση {rm(SQ0, m):.3f})')
SPL = [('1-3', RR < 3), ('4-6', (RR >= 3) & (RR < 6)), ('7-10', (RR >= 6) & (RR < 10)), ('11+', RR >= 10), ('ολα', RR >= 0)]
P(''); P('=== ΕΝΩΜΕΝΑ held-out (ΔRMSE ΠΡΟΤΑΣΗ − ΣΗΜΕΡΑ · ΔMSE ± τ.σ. · και vs βαση) ===')
for s, mm in SPL:
    dd = sP[mm] - sT[mm]
    P(f'  ματς {s:4s} n {int(mm.sum()):4d} · ΣΗΜΕΡΑ {rm(sT, mm):.3f} ({rm(sT, mm) - rm(SQ0, mm):+.3f} vs βαση) · ΠΡΟΤΑΣΗ {rm(sP, mm):.3f} ({rm(sP, mm) - rm(SQ0, mm):+.3f})'
      f' · Δ {rm(sP, mm) - rm(sT, mm):+.3f} · ΔMSE {dd.mean():+.2f} ± {dd.std(ddof=1)/math.sqrt(len(dd)):.2f}')
dd = sP - sT; dm, se = dd.mean(), dd.std(ddof=1) / math.sqrt(len(dd))
P(''); P('=== ΑΝΑΦΟΡΑ: σταθερο k, in-sample ενωμενα (καλυτερο κ) · ΔRMSE vs βαση ===')
P(f'  {"k":>4s} {"κ*":>4s} ' + ' '.join(f'{s:>8s}' for s, _ in SPL))
for k in (0.6, 1, 2, 3, 4):
    kp = min(KAP, key=lambda kp: sq(kp, k).sum())
    P(f'  {k:>4g} {kp:>4g} ' + ' '.join(f'{rm(sq(kp, k), mm) - rm(SQ0, mm):+8.3f}' for s, mm in SPL))
# ROI
def roi(vec):
    res = collections.defaultdict(list)
    for j in range(len(R)):
        mk = R.mk.values[j]
        if not mk: continue
        us = [u for (L, o1, o2) in mk for u in [pick_u(vec[j], L, o1, o2, ACT[j] + L, R.sig.values[j])] if u is not None]
        if not us: continue
        z = '1-3' if RR[j] < 3 else ('4-6' if RR[j] < 6 else '7+')
        for key in (z, 'ολα'): res[key].append((float(np.mean(us)), CS[j]))
    return res
def cr(L):
    if not L: return '—'
    a = np.array([u for u, _ in L]); ss = sorted(set(c for _, c in L))
    pos = sum(1 for c in ss if np.mean([u for u, cc in L if cc == c]) > 0)
    return f'{a.mean()*100:+5.1f}% ({len(a)}, {a.sum():+.1f}μ, {pos}/{len(ss)})'
RB, RT, RP = roi(BASE), roi(HELD[T]), roi(HELD[Pp])
P(''); P('=== ROI ΧΑΝΤΙΚΑΠ (ΜΟΝΟ αναφορα) · edge ≥8% στο ΑΝΟΙΓΜΑ · (picks, μοναδες, θετικες διοργανωσεις-σεζον) ===')
for z in ('1-3', '4-6', '7+', 'ολα'):
    P(f'  ματς {z:4s}: βαση {cr(RB[z]):30s} · ΣΗΜΕΡΑ {cr(RT[z]):30s} · ΠΡΟΤΑΣΗ {cr(RP[z])}')
# μεριδιο που μενει
kP = collections.Counter(CH[Pp][c][1] for c in CSS).most_common(1)[0][0]
P(''); P(f'=== ΠΟΣΟ ΑΠΟ ΤΟ ΑΡΧΙΚΟ ΑΠΟΤΕΛΕΣΜΑ ΜΕΝΕΙ, k/(k+r) · ΠΡΟΤΑΣΗ με το συχνοτερο επιλεγμενο k = {kP:g} ===')
for r_ in (1, 3, 5, 10):
    P(f'  r {r_:2d}: ΣΗΜΕΡΑ {0.6/(0.6+r_):.0%} · ΠΡΟΤΑΣΗ {kP/(kP+r_):.0%}  (k 2: {2/(2+r_):.0%} · k 3: {3/(3+r_):.0%} · k 4: {4/(4+r_):.0%})')
kTm = np.mean([CH[T][c][0] for c in CSS]); kPm = np.mean([CH[Pp][c][0] for c in CSS])
P(f'  σε ποντους ανα 1 z (μεσο LOSO κ: ΣΗΜΕΡΑ {kTm:.2f}, ΠΡΟΤΑΣΗ {kPm:.2f}): ' + ' · '.join(
    f'r {r_}: {kTm*0.6/(0.6+r_):.2f} vs {kPm*kP/(kP+r_):.2f}' for r_ in (0, 1, 3, 5, 10)))
# κριτηριο
c1 = wins >= 5; c2 = dm < 0 and abs(dm) / se >= 1
P(''); P('=== ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ ===')
P(f'  ΠΡΟΤΑΣΗ καλυτερη σε {wins}/6 (απαιτειται ≥5) → {"✓" if c1 else "✗"}')
P(f'  ενωμενη ΔMSE {dm:+.3f} ± {se:.3f} (|Δ|/τ.σ. {abs(dm)/se:.2f}, απαιτειται <0 και ≥1) → {"✓" if c2 else "✗"}')
P(f'  → {"ΠΕΡΝΑ" if (c1 and c2) else "ΔΕΝ ΠΕΡΝΑ"}')
_real_open(OUTF, 'w', encoding='utf-8').write('\n'.join(out))
