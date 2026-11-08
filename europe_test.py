# -*- coding: utf-8 -*-
"""
europe_test.py -- Η ΥΠΟΘΕΣΗ ΤΟΥ ΣΤΕΛΙΟΥ: φαβορι που ερχεται απο ευρωπαικο ματς
"παιρνει το προβαδισμα και ριχνει ρυθμο" -> κερδιζει με ΜΙΚΡΟΤΕΡΟ περιθωριο
-> το +1.5 του αουτσαιντερ καλυπτει συχνοτερα.

ΔΕΝ ψαχνουμε "το φαβορι χανει" (η βιβλιογραφια λεει οχι) — ψαχνουμε συμπιεση
του ΠΕΡΙΘΩΡΙΟΥ νικης, που ειναι αορατη στο W/D/L αλλα ορατη στα χαντικαπ.

Μεθοδος: πληρης live διαμορφωση (ραμπα blend, K=8, SoS 1.5 n=6..13,
χαρακας λιγκας = ραμπα περσινος->φετινος Kn=20 [1/9/2026], promo priors LOSO χωρις look-ahead).
Ελεγχος δυναμης: συγκρινουμε το ΥΠΟΛΟΙΠΟ (πραγματικο περιθωριο - προβλεπομενο),
οχι το ωμο περιθωριο — ωστε "φαβορι απο Ευρωπη" και "φαβορι χωρις Ευρωπη"
να συγκρινονται δικαια ακομα κι αν οι ευρωπαικες ομαδες ειναι καλυτερες.

A) Περιθωριο & καλυψη +1.5 ανα ομαδα-καταταξη (fav/dog x EU/οχι)
B) Τα ΔΙΚΑ ΜΑΣ στοιχηματα: ROI οταν το φαβορι ερχεται απο Ευρωπη vs οχι
C) Βαρυτητα: ποσο επαιξαν στην Ευρωπη οι παικτες της σημερινης ενδεκαδας
"""
import sys, os, json
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
from picks import HFA_FIX, wmean
from sos_test import bet_signals_5s, prev_season
import corrected_config as CC

SEAS = ['2223', '2324', '2425', '2526']
K = 8.0; BL = 0.60; SPLIT = 13; KG = 12.0; ST = 1.5; GLO, GHI = 6, 13
D_BLEND = (1.0 - BL) * (SPLIT + KG) / SPLIT
# 29/9/2026 (Στελιος «φαβορι»): ξεχωριστο βαρος γκολ ανα πλευρα — ποσοστο του βαρους γκολ που ΚΡΑΤΑΕΙ η αμυνα/επιθεση
# (1.0 = σημερα· DEF_GW=0 → αμυνα μονο xG). Αφορμη core7_finishing_persist: αμυνα γκολ−xGA ΜΗ μονιμο, υπερ-αντιδραση −0.20 (t −3.9).
DEF_GW = float(os.environ.get('DEF_GW', '1.0')); ATT_GW = float(os.environ.get('ATT_GW', '1.0'))
SOS_MODE = os.environ.get('SOS_MODE', 'blended')   # 1/10: 'current' = SoS μονο στα φετινα νουμερα πριν τη μιξη
M, id2 = CC.M, CC.id2name
EUD = 4                                   # "ερχεται απο Ευρωπη" = ευρωπαικο <= 4 μερες πριν

FLAGS = pd.read_csv('europe_flags.csv')
FLAGS['mid'] = FLAGS['mid'].astype(str)


def blend_at(n):
    return 1.0 - D_BLEND * n / (n + KG) if n <= SPLIT else BL


def flat_prior(b):
    out = {}
    for (lg, sea), G in M.groupby(['league', 'season'], sort=False):
        agg = {}
        for _, r in G.iterrows():
            for tid, sf, xf, sa, xa, gf, ga in [
                    (r['home'], r['h_ns'], r['h_xg'], r['a_ns'], r['a_xg'], r['hg'], r['ag']),
                    (r['away'], r['a_ns'], r['a_xg'], r['h_ns'], r['h_xg'], r['ag'], r['hg'])]:
                d = agg.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[]))
                for k, v in [('sf', sf), ('xf', xf), ('sa', sa), ('xa', xa), ('gf', gf), ('ga', ga)]:
                    d[k].append(v)
        pr = {}
        for tid, d in agg.items():
            sf = np.mean(d['sf']); sa = np.mean(d['sa'])
            ba = 1 - (1 - b) * ATT_GW; bd = 1 - (1 - b) * DEF_GW
            pr[tid] = ((ba * np.mean(d['xf']) + (1 - ba) * np.mean(d['gf'])) / max(sf, 1e-9),
                       (bd * np.mean(d['xa']) + (1 - bd) * np.mean(d['ga'])) / max(sa, 1e-9), sf, sa)
        out[(lg, str(sea))] = pr
    return out


FL = flat_prior(BL)


def rat(t, b):
    sf = wmean(t['sf']); sa = wmean(t['sa'])
    ba = 1 - (1 - b) * ATT_GW; bd = 1 - (1 - b) * DEF_GW
    return ((ba * wmean(t['xf']) + (1 - ba) * wmean(t['gf'])) / max(sf, 1e-9),
            (bd * wmean(t['xa']) + (1 - bd) * wmean(t['ga'])) / max(sa, 1e-9), sf, sa)


def shrink(r, p, n):
    w = n / (n + K)
    return tuple(max(pi, 1e-9) * (max(ri, 1e-9) / max(pi, 1e-9)) ** w for ri, pi in zip(r, p))


def run():
    preds = []
    for (lg, sea), G in M.groupby(['league', 'season'], sort=False):
        sea = str(sea)
        if sea not in SEAS:
            continue
        pls, plx = CC.NORM[(lg, prev_season(sea))]
        hf = HFA_FIX[lg]
        prev = FL.get((lg, prev_season(sea)), {})
        G = G.sort_values(['date', 'mid']).reset_index(drop=True)
        hist = {}; cache = {}
        # χαρακας λιγκας: ραμπα περσινος -> φετινος-ως-τωρα (Kn=20, οπως το live KN_NORM 1/9/2026)
        acc = dict(ns=0.0, xg=0.0, n=0)
        cur = [pls, plx]                     # τρεχων χαρακας (ενημερωνεται προ καθε ματς)

        def upd_norms():
            if acc['n'] == 0:
                cur[0], cur[1] = pls, plx; return
            cls = acc['ns'] / acc['n']; clx = acc['xg'] / max(acc['ns'], 1e-9)
            w = acc['n'] / (acc['n'] + 20.0)
            cur[0] = pls * (cls / pls) ** w; cur[1] = plx * (clx / plx) ** w

        def warm(tid):
            h = hist.get(tid); n = len(h['sf']) if h else 0
            key = (tid, n)
            if key in cache:
                return cache[key]
            p = prev.get(tid)
            if p is None:
                p = CC.promo_prior(lg, sea, tid)
            v = p if n == 0 else shrink(rat(h, blend_at(n)), p, n)
            cache[key] = v
            return v

        def sosadj(r, t):
            if not t or not (GLO <= len(t['opp']) <= GHI):
                return r
            oA = []; oD = []; oSF = []; oSA = []
            for o in t['opp']:
                a = warm(o)
                oA.append(a[0]); oD.append(a[1]); oSF.append(a[2]); oSA.append(a[3])
            mA, mD, mSF, mSA = wmean(oA), wmean(oD), wmean(oSF), wmean(oSA)
            lsx, lxx = cur[0], cur[1]
            return (r[0] * (lxx / max(mD, 1e-9)) ** ST, r[1] * (lxx / max(mA, 1e-9)) ** ST,
                    r[2] * (lsx / max(mSA, 1e-9)) ** ST, r[3] * (lsx / max(mSF, 1e-9)) ** ST)

        def sos_current(tid, t):
            """1/10/2026 «σωστο SoS»: η διορθωση προγραμματος στα ΦΕΤΙΝΑ νουμερα ΠΡΙΝ τη μιξη με το περσινο
            (το φετινο προγραμμα δεν επηρεασε το περσινο κομματι). Αντιπαλοι = πληρες (αναμεικτο) rating."""
            h = hist.get(tid); n = len(h['sf']) if h else 0
            p = prev.get(tid)
            if p is None:
                p = CC.promo_prior(lg, sea, tid)
            if n == 0:
                return p
            rc = rat(h, blend_at(n))
            if GLO <= len(h['opp']) <= GHI:
                rc = sosadj(rc, h)
            return shrink(rc, p, n)

        for _, r in G.iterrows():
            H, A = r['home'], r['away']
            hh = hist.get(H); ha = hist.get(A)
            nh = len(hh['sf']) if hh else 0
            na = len(ha['sf']) if ha else 0
            mn = min(nh, na)
            upd_norms(); ls, lx = cur[0], cur[1]
            if SOS_MODE == 'current':
                rh = sos_current(H, hh); ra = sos_current(A, ha)
            else:
                rh = sosadj(warm(H), hh); ra = sosadj(warm(A), ha)
            xg_h = min(max((rh[2] * ra[3] / ls) * (rh[0] * (ra[1] / lx)) * hf, .05), 6.)
            xg_a = min(max((ra[2] * rh[3] / ls) * (ra[0] * (rh[1] / lx)) / hf, .05), 6.)
            preds.append(dict(league=lg, season=sea, mid=str(r['mid']), date=r['date'],
                              home=H, away=A, home_name=id2.get(H), away_name=id2.get(A),
                              gd=r['hg'] - r['ag'], md=mn, xg_h=xg_h, xg_a=xg_a))
            acc['ns'] += r['h_ns'] + r['a_ns']; acc['xg'] += r['h_xg'] + r['a_xg']; acc['n'] += 2
            for tid, opp, sf, xf, sa2, xa, gf, ga in [
                    (H, A, r['h_ns'], r['h_xg'], r['a_ns'], r['a_xg'], r['hg'], r['ag']),
                    (A, H, r['a_ns'], r['a_xg'], r['h_ns'], r['h_xg'], r['ag'], r['hg'])]:
                dd = hist.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[], opp=[]))
                for k_, v in [('sf', sf), ('xf', xf), ('sa', sa2), ('xa', xa),
                              ('gf', gf), ('ga', ga), ('opp', opp)]:
                    dd[k_].append(v)
    return pd.DataFrame(preds)


print('Χτισιμο προβλεψεων (πληρης live μεθοδος)...', flush=True)
P = run()
P = P[P.md >= GLO].copy()                     # απο την 7η — εκει που στοιχηματιζουμε

# --- flags ανα mid/πλευρα ---
fl = FLAGS.set_index(['mid', 'team'])
for side, tcol in (('h', 'home'), ('a', 'away')):
    idx = list(zip(P.mid, P[tcol]))
    P[side + '_eu_prev'] = [fl.eu_prev_days.get(i, np.nan) for i in idx]
    P[side + '_eu_next'] = [fl.eu_next_days.get(i, np.nan) for i in idx]
    P[side + '_eu_comp'] = [fl.eu_comp.get(i, None) for i in idx]

# --- φαβορι κατα το μοντελο ---
P['fav_home'] = P.xg_h >= P.xg_a
P['fav_sup'] = np.where(P.fav_home, P.xg_h - P.xg_a, P.xg_a - P.xg_h)
P['fav_margin'] = np.where(P.fav_home, P.gd, -P.gd)
P['resid'] = P.fav_margin - P.fav_sup
P['fav_eu'] = np.where(P.fav_home, P.h_eu_prev, P.a_eu_prev) <= EUD
P['dog_eu'] = np.where(P.fav_home, P.a_eu_prev, P.h_eu_prev) <= EUD
P['fav_eu_next'] = np.where(P.fav_home, P.h_eu_next, P.a_eu_next) <= EUD
P['fav_comp'] = np.where(P.fav_home, P.h_eu_comp, P.a_eu_comp)
P['dog_cover15'] = (P.fav_margin <= 1).astype(int)     # +1.5 του αουτσαιντερ καλυπτει

CLEAR = P.fav_sup >= 0.30                              # "πραγματικο" φαβορι (οχι 50-50 ματς)


def row(d, label):
    if not len(d):
        return '  %-34s      —' % label
    se = d.resid.std() / np.sqrt(len(d))
    return ('  %-34s n=%4d | sup %5.2f | περιθ. %5.2f | υπολ. %+.3f ±%.3f | dog+1.5 %5.1f%%'
            % (label, len(d), d.fav_sup.mean(), d.fav_margin.mean(),
               d.resid.mean(), se, d.dog_cover15.mean() * 100))


print()
print('=' * 110)
print('Α. ΠΕΡΙΘΩΡΙΟ ΦΑΒΟΡΙ — υπολοιπο = πραγματικο περιθωριο − προβλεπομενο · md7+ · 4 σεζον')
print('   (αρνητικο υπολοιπο = το φαβορι αποδιδει ΚΑΤΩ απο την προβλεψη μας -> καλο για το +hcap μας)')
print('=' * 110)
base = P[CLEAR & ~P.fav_eu & ~P.dog_eu & ~P.fav_eu_next]
print(row(base, 'ΒΑΣΗ: κανεις απο Ευρωπη'))
print(row(P[CLEAR & P.fav_eu & ~P.dog_eu], 'ΦΑΒΟΡΙ απο Ευρωπη (<=4μ), dog οχι'))
print(row(P[CLEAR & P.dog_eu & ~P.fav_eu], 'DOG απο Ευρωπη, φαβορι οχι'))
print(row(P[CLEAR & P.fav_eu & P.dog_eu], 'και οι δυο απο Ευρωπη'))
print(row(P[CLEAR & P.fav_eu_next & ~P.fav_eu], 'ΦΑΒΟΡΙ με Ευρωπη ΣΕ <=4μ (κοιταζει μπροστα)'))
print()
print('  Διασπαση του "ΦΑΒΟΡΙ απο Ευρωπη":')
fe = P[CLEAR & P.fav_eu & ~P.dog_eu]
for c in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'):
    print(row(fe[fe.fav_comp == c], '    %s' % c))
print(row(fe[fe.fav_home], '    φαβορι ΕΝΤΟΣ εδρας'))
print(row(fe[~fe.fav_home], '    φαβορι ΕΚΤΟΣ εδρας'))
prev_days = np.where(fe.fav_home, fe.h_eu_prev, fe.a_eu_prev)
print(row(fe[prev_days <= 3], '    3 μερες μετα την Ευρωπη'))
print(row(fe[prev_days == 4], '    4 μερες μετα την Ευρωπη'))
for lo, hi, nm in [(6, 13, '    md7-14'), (14, 99, '    md15+')]:
    print(row(fe[(fe.md >= lo) & (fe.md <= hi)], nm))

# ---------- Β. ΤΑ ΔΙΚΑ ΜΑΣ ΣΤΟΙΧΗΜΑΤΑ ----------
print()
print('=' * 110)
print('Β. ΤΑ ΔΙΚΑ ΜΑΣ ΣΤΟΙΧΗΜΑΤΑ (underdog +hcap): ROI οταν το ΦΑΒΟΡΙ ερχεται απο Ευρωπη')
print('=' * 110)
B = bet_signals_5s(P, CC.reg, CC.resolvers).dropna(subset=['pnl'])
key = P[['season', 'date', 'home_name', 'away_name', 'mid', 'md',
         'h_eu_prev', 'a_eu_prev', 'h_eu_next', 'a_eu_next']].rename(
    columns={'home_name': 'home', 'away_name': 'away'})
B = B.merge(key, on=['season', 'date', 'home', 'away'], how='left')
# side=1: παιζουμε γηπεδουχο -> φαβορι ο φιλοξενουμενος· side=-1: αντιστροφα
B['fav_prev'] = np.where(B.side == 1, B.a_eu_prev, B.h_eu_prev)
B['fav_next'] = np.where(B.side == 1, B.a_eu_next, B.h_eu_next)
B['dog_prev'] = np.where(B.side == 1, B.h_eu_prev, B.a_eu_prev)


def broi(d, label):
    if not len(d):
        return '  %-40s      —' % label
    se = d.pnl.std() / np.sqrt(len(d))
    pv = [d[d.season == s].pnl.mean() for s in SEAS if len(d[d.season == s])]
    return ('  %-40s n=%4d | ROI %+6.1f%% ±%.1f%% | %+7.1fu | %d/%d σεζον θετ.'
            % (label, len(d), d.pnl.mean() * 100, se * 100, d.pnl.sum(),
               sum(1 for x in pv if x > 0), len(pv)))


for wlo, whi, wnm in [(6, 99, 'ΟΛΑ (md7+)'), (6, 13, 'md7-14'), (14, 99, 'md15+')]:
    w = B[(B.md >= wlo) & (B.md <= whi)]
    print('  --- %s ---' % wnm)
    print(broi(w[w.fav_prev <= EUD], 'φαβορι απο Ευρωπη (<=4μ)'))
    print(broi(w[~(w.fav_prev <= EUD) & ~(w.fav_next <= EUD)], 'φαβορι ΧΩΡΙΣ Ευρωπη γυρω'))
    print(broi(w[w.fav_next <= EUD], 'φαβορι με Ευρωπη σε <=4μ (μπροστα)'))
    print(broi(w[w.dog_prev <= EUD], '(ελεγχος) DOG απο Ευρωπη'))

# ---------- Γ. ΒΑΡΥΤΗΤΑ: ποσο επαιξε στην Ευρωπη η σημερινη ενδεκαδα ----------
print()
print('=' * 110)
print('Γ. ΒΑΡΥΤΗΤΑ: λεπτα της σημερινης ενδεκαδας στο ευρωπαικο (μονο ΦΑΒΟΡΙ απο Ευρωπη)')
print('=' * 110)
SQ = json.load(open('squads_all.json', encoding='utf-8'))
ESQ = json.load(open('europe_squads.json', encoding='utf-8'))
EU = json.load(open('europe_fixtures.json', encoding='utf-8'))
eu_matches = {}                                   # (sea, tid) -> [(date, mid)]
for kk, rows in EU.items():
    comp, sea = kk.rsplit('_', 1)
    for m in rows:
        d = m['utc'][:10]
        for tid in (m['hid'], m['aid']):
            eu_matches.setdefault((sea, tid), []).append((d, m['mid']))
for k in eu_matches:
    eu_matches[k].sort()

fe = P[CLEAR & P.fav_eu & ~P.dog_eu].copy()
loads = []
for r in fe.itertuples():
    fav_tid = int(r.home if r.fav_home else r.away)
    lst = eu_matches.get((r.season, fav_tid), [])
    emid = None
    for d, mm in reversed(lst):
        if d < r.date:
            emid = mm; break
    dom = SQ.get(str(r.mid)); eur = ESQ.get(str(emid)) if emid else None
    if not dom or not eur:
        loads.append(np.nan); continue
    dside = dom.get('h') if int((dom.get('h') or {}).get('t') or -1) == fav_tid else dom.get('a')
    eside = None
    for sd in ('h', 'a'):
        if eur.get(sd) and int(eur[sd].get('t') or -1) == fav_tid:
            eside = eur[sd]; break
    if not dside or not eside:
        loads.append(np.nan); continue
    dmins = dside['p']; emins = eside['p']
    starters = sorted(dmins, key=lambda p: -dmins[p])[:11]      # η "ενδεκαδα" = top-11 λεπτα σημερα
    loads.append(sum(emins.get(p, 0) for p in starters) / 990.0)
fe['eu_load'] = loads
fe = fe.dropna(subset=['eu_load'])
q1, q2 = fe.eu_load.quantile([1 / 3, 2 / 3])
print('  φορτιο = λεπτα των σημερινων 11 στο ευρωπαικο / 990   (n=%d, μεσο %.2f)' % (len(fe), fe.eu_load.mean()))
print(row(fe[fe.eu_load <= q1], '    ΕΛΑΦΡΥ φορτιο (rotation στην Ευρωπη)'))
print(row(fe[(fe.eu_load > q1) & (fe.eu_load <= q2)], '    ΜΕΣΑΙΟ'))
print(row(fe[fe.eu_load > q2], '    ΒΑΡΥ (οι ιδιοι επαιξαν και εκει)'))
P.to_csv('europe_test_preds.csv', index=False)
print('\nΓραφτηκε europe_test_preds.csv (n=%d)' % len(P))
