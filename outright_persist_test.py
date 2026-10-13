# -*- coding: utf-8 -*-
"""outright_persist_test.py — ΠΟΣΟ ΠΡΕΠΕΙ ΝΑ ΚΡΑΤΑΝΕ ΟΙ ΑΠΟΔΟΣΕΙΣ ΝΙΚΗΤΗ (13/10/2026, Στελιος: «οι αποδόσεις νικητή πόσο πρέπει να κρατάνε;»).
Ερωτημα: για ποσα ματς της σεζον οι PRE-SEASON αποδοσεις νικητη (outrights) πρεπει να επηρεαζουν το rating ομαδας στο μπασκετ.
Σημερα (BCL live): outrights μονο στην αφετηρια (κx 4.5 π./z) με βαρος ridge ~1.5 ματς → σβηνουν σε ~5-8 ματς (μετρανε και τα εγχωρια).

ΔΕΔΟΜΕΝΑ (μονο ΑΠΟΔΟΣΕΙΣ ΝΙΚΗΤΗ, οχι καταταξεις ειδικων· πριν την 1η αγωνιστικη):
  EuroCup  ec_outrights.json U2023 (19 ονοματα), U2024 (13), U2025 (20)   [U2021 εξω: μετα την 5η · U2026 εξω: φετινη]
  Euroleague el_outrights.json '2024-25 (bet365)' → E2024, '2025-26 (Novibet;)' → E2025 (ελληνικα ονοματα → κωδικοι με το χερι) [2026-27 εξω]
  BCL      bcl_outrights.json U2022 (11 ομαδες, ΜΕΡΙΚΗ λιστα, δημοσιευμενη ΚΑΤΑ τη διαρκεια της 1ης αγωνιστικης — σημαια)  [U2026* εξω]
  → εως 6 διοργανωσεις-σεζον.
z (προ-δηλωμενο): για καθε διοργανωση-σεζον, ΟΛΕΣ οι ομαδες της κανονικης περιοδου· με τιμη x = −ln(αποδοση)· χωρις τιμη
  x = −ln(1.5 × μεγιστη αποδοση των ομαδων της λιστας που επαιξαν)· z = (x − μεσος)/τ.α. πανω σε ολες τις ομαδες της σεζον.
ΒΑΣΗ (walk-forward προβλεψη διαφορας γηπεδουχου, ΧΩΡΙΣ outrights/ειδικους):
  BCL: bcl_engine_preds_live.pkl D['FIN'] (live φορμουλα χωρις αποδοσεις νικητη).
  EC : μηχανη ec_expert_test (εγχωρια κ1 απο τον 1ο αγωνα, προετοιμασια κ_pre 0.5 = live κ_pre, carry 0.7, λ4, HL∞) με κ_x = 0.
  EL : μηχανη live (el_preseason_test/el_anchor_test: Β1 K12 HL60 εδρα 5 τυχη .5 ×1.1 απο 7ο, προετοιμασια κ.5 στους ≤10,
       φετινα εγχωρια κ.5 απο τον 11ο) ΧΩΡΙΣ ειδικους BasketNews (we = 0) και βαρος περσινου 0.7 (= v1 carry χωρις ειδικους· το live 0.5
       ρυθμιστηκε ΜΑΖΙ με τους ειδικους). Ευαισθησια: ιδιο με βαρος 0.5 (μονο στον πινακα κλισης).
       (el_newmodel_preds h_new ΠΕΡΙΕΧΕΙ ειδικους → δεν χρησιμοποιειται.)
ΜΟΝΤΕΛΟ (εκ των υστερων, ιδιο για ολες): pred = βαση + κ·(z_γηπ − z_φιλ)·k/(k + r),
  r = μεσος αριθμος ματς ΚΑΝΟΝΙΚΗΣ ΠΕΡΙΟΔΟΥ (της ιδιας διοργανωσης, φετος) που εχουν ηδη παιξει οι δυο ομαδες πριν απο αυτο.
  (BCL: «κανονικη περιοδος» = ομιλοι + 2η φαση ομιλων/Round of 16, χωρις προκριματικα/play-offs/F4. EC/EL: phase RS.)
  πλεγμα κ ∈ {0..6} π./z · k ∈ {1, 2, 4, 8, 16, 1e9 (= δεν σβηνει ποτε)}.
ΠΡΟ-ΔΗΛΩΜΕΝΗ ΑΞΙΟΛΟΓΗΣΗ (γραφτηκε ΠΡΙΝ την εκτελεση, ΜΙΑ εκτελεση):
  1. «Ποσο κραταει» (περιγραφικο): OLS κλιση του (πραγματικο − βαση) πανω στο (z_γ − z_φ), με σταθερο ορο, ανα μπλοκ r:
     0-2 (ματς 1-3), 3-5, 6-9, 10-19, 20+ → κλιση (π./z), t, n· ενωμενα και ανα διοργανωση.
     (Ευαισθησια, ΟΧΙ κριτηριο: μονο ματς οπου ΚΑΙ οι δυο ομαδες ειναι στη λιστα· EL με βαρος περσινου 0.5.)
  2. LOSO στις διοργανωσεις-σεζον: επιλογη (κ,k) με ελαχιστο τετραγωνικο λαθος διαφορας στις ΑΛΛΕΣ (ολα τα ματς κανονικης περιοδου)·
     held-out RMSE vs βαση (κ=0) ανα fold, ενωμενα, και σε ματς 1-3 (r<3) / 4-10 (3≤r<10) / 11+ (r≥10).
  3. Προφιλ: για καθε k, καλυτερο κ (in-sample ενωμενα) και ΔRMSE vs βαση σε 1-3 / 4-10 / 11+ / ολα.
  4. Αναφορα: ποιο k αντιστοιχει στο σημερινο BCL live (βαρος ~1.5 ματς).
  5. ROI (ΜΟΝΟ αναφορα): χαντικαπ edge ≥8% στο ΑΝΟΙΓΜΑ (BCL σ12 μεσος Crown/Bet365 · EC σ11.5 Crown · EL σ11.5 Crown),
     βαση vs βαση + LOSO ορος, ματς 1-3 / 4+.
  ΚΡΙΤΗΡΙΟ: μεγαλυτερη διαρκεια (k ≥ 4) ειναι «καλυτερη απο σημερα» ΜΟΝΟ αν
    (i) LOSO με k ∈ {4,8,16,1e9} (κ ελευθερο) εχει μικροτερο held-out RMSE απο LOSO με k ∈ {1,2} (= σημερινο, κ ελευθερο)
        σε ≥5/6 διοργανωσεις-σεζον (≥4 αν ειναι λιγοτερες απο 6), ΚΑΙ
    (ii) το in-sample καλυτερο k ειναι ≥4 σε ≥2 απο τις 3 διοργανωσεις (BCL / EC / EL χωριστα).
  Επισης τυπωνεται η «κατα γραμμα» εκδοχη: ελευθερο LOSO vs βαση (κ=0) ανα fold και ποιο k επιλεγει.
Εξοδος: outright_persist_test_out.txt (+ cache βασεων outright_persist_bases.pkl)"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, math, pickle, collections, builtins, time
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
SCR = r'C:\Users\steli\AppData\Local\Temp\claude\C--Users-steli-My-Drive-Betting-Model\67d4ba59-0c37-4db7-a951-badbf5076962\scratchpad'
OUTF, CACHE = 'outright_persist_test_out.txt', 'outright_persist_bases.pkl'
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

# =============================== 1. ΚΛΙΣΗ ανα σταδιο ===============================
BLK = [(0, 3, 'r 0-2 (ματς 1-3)'), (3, 6, 'r 3-5 (ματς 4-6)'), (6, 10, 'r 6-9 (ματς 7-10)'), (10, 20, 'r 10-19 (ματς 11-20)'), (20, 999, 'r 20+ (ματς 21+)')]
def ols(x, y):
    if len(x) < 8 or np.std(x) == 0: return None
    A = np.c_[np.ones(len(x)), x]; c, *_ = np.linalg.lstsq(A, y, rcond=None); e = y - A @ c
    s2 = e @ e / (len(x) - 2); se = math.sqrt(s2 * np.linalg.inv(A.T @ A)[1, 1]); return c[1], c[1] / se, len(x)
def cellb(m, resid=None):
    o = ols(R.zd.values[m], (R.res.values if resid is None else resid)[m])
    return f'{o[0]:+5.2f} (t {o[1]:+4.1f}, n {o[2]:3d})' if o else f'{"—":>22}'
P(''); P('=== 1. ΚΛΙΣΗ του (πραγματικο − βαση) πανω στο (z_γ − z_φ), π. ανα 1 z — ανα σταδιο (r = μεσος αριθμος ματς που εχουν ηδη παιξει) ===')
P(f'  {"σταδιο":22s} {"ΕΝΩΜΕΝΑ":24s} {"BCL (1 σεζον)":24s} {"EC (3)":24s} {"EL (2)":24s}')
for lo, hi, lab in BLK:
    mb = (R.r >= lo) & (R.r < hi)
    P(f'  {lab:22s} {cellb(mb.values):24s} ' + ' '.join(f'{cellb((mb & (R.comp == c)).values):24s}' for c in COMPS))
P(f'  {"ΟΛΑ":22s} {cellb(np.ones(len(R), bool)):24s} ' + ' '.join(f'{cellb((R.comp == c).values):24s}' for c in COMPS))
P('  ανα διοργανωση-σεζον (r<3 / 3-9 / 10+): ' + ' · '.join(
    f'{c}: ' + '/'.join((lambda o: f'{o[0]:+.1f}' if o else '—')(ols(R.zd.values[m], R.res.values[m]))
                        for m in (((R.cs == c) & (R.r < 3)).values, ((R.cs == c) & (R.r >= 3) & (R.r < 10)).values, ((R.cs == c) & (R.r >= 10)).values))
    for c in CSS))
P('  ευαισθησια (ΟΧΙ κριτηριο) — μονο ματς οπου ΚΑΙ οι δυο ομαδες ειναι στη λιστα:')
for lo, hi, lab in BLK:
    mb = (R.r >= lo) & (R.r < hi) & R.both
    P(f'    {lab:22s} ενωμενα {cellb(mb.values)} · ' + ' · '.join(f'{c} {cellb((mb & (R.comp == c)).values)}' for c in COMPS))
P('  ευαισθησια (ΟΧΙ κριτηριο) — EL με βαση βαρους περσινου 0.5 (αντι 0.7):')
mEL = (R.comp == 'EL').values; resA = (R.act - R.base_alt).values
for lo, hi, lab in BLK:
    mb = ((R.r >= lo) & (R.r < hi)).values & mEL
    P(f'    {lab:22s} EL {cellb(mb, resA)}   (βαση 0.7: {cellb(mb)})')

# =============================== ΠΛΕΓΜΑ ===============================
KAP = [0, 1, 2, 3, 4, 5, 6]; KS = [1, 2, 4, 8, 16, 1e9]
GRID = [(kp, k) for kp in KAP for k in KS]
ACT, BASE, ZD, RR, CS, CO = R.act.values, R.base.values, R.zd.values, R.r.values, R.cs.values, R.comp.values
def pred(kp, k): return BASE + kp * ZD * (k / (k + RR))
SQ = {g: (ACT - pred(*g)) ** 2 for g in GRID}
SQ0 = (ACT - BASE) ** 2
def kl(k): return '∞' if k >= 1e8 else f'{k:g}'
SPL = [('1-3', RR < 3), ('4-10', (RR >= 3) & (RR < 10)), ('11+', RR >= 10), ('ολα', RR >= 0)]
def drm(sq, m): return math.sqrt(sq[m].mean()) - math.sqrt(SQ0[m].mean())

# =============================== 2. LOSO ===============================
def loso(allowed):
    held = np.full(len(R), np.nan); ch = {}
    for c in CSS:
        tr = CS != c
        g = min([g for g in GRID if g[1] in allowed or g[0] == 0], key=lambda g: (SQ[g][tr].sum(), g[0], -g[1]))
        ch[c] = g; held[CS == c] = pred(*g)[CS == c]
    return held, ch
P(''); P('=== 2. LOSO στις διοργανωσεις-σεζον (επιλογη (κ,k) με ελαχιστο τετρ. λαθος στις ΑΛΛΕΣ 5, ολα τα ματς) ===')
HL_ = {}
for lab, allowed in (('ΕΛΕΥΘΕΡΟ k', KS), ('k ∈ {1,2} (≈ σημερα)', [1, 2]), ('k ≥ 4', [4, 8, 16, 1e9])):
    held, ch = loso(allowed); HL_[lab] = (held, ch); sqh = (ACT - held) ** 2
    P(f'  -- {lab} --')
    for c in CSS:
        m = CS == c
        P(f'    εξω {c:6s} επιλογη κ {ch[c][0]} k {kl(ch[c][1]):>3s} · n {m.sum():3d} · RMSE βαση {math.sqrt(SQ0[m].mean()):.3f} → {math.sqrt(sqh[m].mean()):.3f} '
          f'({drm(sqh, m):+.3f}) · 1-3: {drm(sqh, m & (RR < 3)):+.3f} (n {int((m & (RR < 3)).sum())})')
    d = SQ0 - sqh
    P(f'    ΕΝΩΜΕΝΑ: ' + ' · '.join(f'{s} {drm(sqh, mm):+.3f} (n {int(mm.sum())})' for s, mm in SPL)
      + f' · ΔMSE {d.mean():+.2f} ± {d.std(ddof=1)/math.sqrt(len(d)):.2f} (τ.σ.) · καλυτερο απο βαση σε {sum(drm(sqh, CS == c) < 0 for c in CSS)}/6')
hA, _ = HL_['k ≥ 4']; hB, _ = HL_['k ∈ {1,2} (≈ σημερα)']
sA, sB = (ACT - hA) ** 2, (ACT - hB) ** 2
wins = [c for c in CSS if sA[CS == c].mean() < sB[CS == c].mean()]
P(f'  ΣΥΓΚΡΙΣΗ k≥4 vs k∈{{1,2}} (held-out RMSE ανα fold): ' + ' · '.join(
    f'{c} {math.sqrt(sA[CS == c].mean()) - math.sqrt(sB[CS == c].mean()):+.3f}' for c in CSS) + f' → k≥4 καλυτερο σε {len(wins)}/6')
dd = sB - sA
P(f'    ενωμενα ΔRMSE (k≥4 − k∈{{1,2}}): ' + ' · '.join(f'{s} {math.sqrt(sA[mm].mean()) - math.sqrt(sB[mm].mean()):+.3f}' for s, mm in SPL)
  + f' · ΔMSE {(-dd).mean():+.2f} ± {dd.std(ddof=1)/math.sqrt(len(dd)):.2f}')

# =============================== 3. ΠΡΟΦΙΛ ===============================
P(''); P('=== 3. ΠΡΟΦΙΛ (in-sample, ενωμενα 6 διοργανωσεις-σεζον): για καθε k το καλυτερο κ και ΔRMSE vs βαση ===')
P(f'  {"k":>4s} {"κ*":>3s} ' + ' '.join(f'{s:>14s}' for s, _ in SPL))
for k in KS:
    kp = min(KAP, key=lambda kp: SQ[(kp, k)].sum())
    P(f'  {kl(k):>4s} {kp:>3d} ' + ' '.join(f'{drm(SQ[(kp, k)], mm):+14.3f}' for s, mm in SPL))
gb = min(GRID, key=lambda g: SQ[g].sum()); P(f'  καλυτερο ενωμενα: κ {gb[0]} k {kl(gb[1])}')
P('  ανα διοργανωση (in-sample): καλυτερο (κ,k) · και καλυτερο κ για καθε k (ΔRMSE ολα)')
bestk = {}
for c in COMPS:
    m = CO == c; g = min(GRID, key=lambda g: (SQ[g][m].sum(), g[0], -g[1])); bestk[c] = g
    prof = ' · '.join((lambda kp: f'k {kl(k)}: κ {kp} {drm(SQ[(kp, k)], m):+.3f}')(min(KAP, key=lambda kp: SQ[(kp, k)][m].sum())) for k in KS)
    P(f'    {c:4s} (n {m.sum()}): καλυτερο κ {g[0]} k {kl(g[1])} ({drm(SQ[g], m):+.3f}) | {prof}')
P('  ανα διοργανωση-σεζον (in-sample, πληροφοριακο): ' + ' · '.join(
    (lambda g: f'{c}: κ{g[0]} k{kl(g[1])}')(min(GRID, key=lambda g: (SQ[g][CS == c].sum(), g[0], -g[1]))) for c in CSS))

# =============================== 4. ΑΝΑΦΟΡΑ σημερινου BCL ===============================
P(''); P('=== 4. ΑΝΑΦΟΡΑ: σημερινο BCL live ===')
P('  outrights στην αφετηρια με βαρος ridge ~1.5 ματς → μεριδιο αφετηριας ≈ 1.5/(1.5 + n), n = ΟΛΑ τα ματς στα δεδομενα (BCL + εγχωρια).')
P('  Αν μετρουσαν μονο ματς BCL: k ≈ 1.5 (αναμεσα σε k 1 και 2). Επειδη μετρανε και τα εγχωρια (~1-2 ανα ματς BCL), σε μοναδες ματς BCL')
P('  το ισοδυναμο ειναι k ≈ 0.5-0.75 → το πλησιεστερο σημειο του πλεγματος ειναι k = 1 (ανω οριο του σημερινου).')

# =============================== 5. ROI (αναφορα) ===============================
Phi = NormalDist().cdf
def pick_u(m, L, o1, o2, x, s):
    if abs(L - round(L)) < 1e-9: pw = Phi((m + L - .5) / s); pl = Phi((-m - L - .5) / s)
    else: pw = Phi((m + L) / s); pl = 1 - pw
    pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    if e < .08: return None
    v = x * side; return (od - 1) if v > 0 else (0 if v == 0 else -1)
hF, chF = HL_['ΕΛΕΥΘΕΡΟ k']
def roi(vec):
    res = collections.defaultdict(list)
    for j in range(len(R)):
        mk = R.mk.values[j]
        if not mk: continue
        us = [u for (L, o1, o2) in mk for u in [pick_u(vec[j], L, o1, o2, ACT[j] + L, R.sig.values[j])] if u is not None]
        if not us: continue
        u = float(np.mean(us)); z = '1-3' if RR[j] < 3 else '4+'
        for key in ((CO[j], z), (CO[j], 'ολα'), ('ΟΛΑ', z), ('ΟΛΑ', 'ολα')): res[key].append((u, CS[j]))
    return res
RB, RL = roi(BASE), roi(hF)
def cr(L):
    if not L: return '—'
    a = np.array([u for u, _ in L]); ss = sorted(set(c for _, c in L))
    pos = sum(1 for c in ss if np.mean([u for u, cc in L if cc == c]) > 0)
    return f'{a.mean()*100:+5.1f}% ({len(a)}, {a.sum():+.1f}μ, {pos}/{len(ss)})'
P(''); P('=== 5. ROI ΧΑΝΤΙΚΑΠ (ΜΟΝΟ αναφορα) · edge ≥8% στο ΑΝΟΙΓΜΑ · βαση vs βαση + LOSO ορος (ελευθερο k) · (picks, μοναδες, θετικες σεζον) ===')
P('  ματς με τιμη ανοιγματος: ' + ' · '.join(f'{c} {sum(1 for j in range(len(R)) if CS[j] == c and R.mk.values[j])}' for c in CSS))
for c in COMPS + ['ΟΛΑ']:
    for z in ('1-3', '4+', 'ολα'):
        P(f'  {c:4s} ματς {z:4s}: βαση {cr(RB[(c, z)]):32s} · με outrights {cr(RL[(c, z)])}')

# =============================== ΚΡΙΤΗΡΙΟ ===============================
n_ok = len(wins); c1 = n_ok >= 5
c2n = sum(1 for c in COMPS if bestk[c][1] >= 4 and bestk[c][0] > 0)
c2 = c2n >= 2
P(''); P('=== ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ ===')
P(f'  (i) LOSO k≥4 καλυτερο απο LOSO k∈{{1,2}} σε {n_ok}/6 (απαιτειται ≥5) → {"✓" if c1 else "✗"}')
P(f'  (ii) in-sample καλυτερο k ≥4 σε {c2n}/3 διοργανωσεις ({", ".join(f"{c}: k {kl(bestk[c][1])}, κ {bestk[c][0]}" for c in COMPS)}) (απαιτειται ≥2) → {"✓" if c2 else "✗"}')
P(f'  → {"ΠΕΡΝΑ: μεγαλυτερη διαρκεια (k≥4) καλυτερη απο σημερα" if (c1 and c2) else "ΔΕΝ ΠΕΡΝΑ το προ-δηλωμενο κριτηριο για k≥4"}')
P(f'  (κατα γραμμα: ελευθερο LOSO επελεξε k ' + ', '.join(f'{c}:{kl(chF[c][1])}/κ{chF[c][0]}' for c in CSS)
  + f' · καλυτερο απο βαση (κ=0) σε {sum(((ACT - hF) ** 2)[CS == c].mean() < SQ0[CS == c].mean() for c in CSS)}/6)')
_real_open(OUTF, 'w', encoding='utf-8').write('\n'.join(out))
