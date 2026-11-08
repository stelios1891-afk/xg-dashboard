# -*- coding: utf-8 -*-
"""el_half_luck_test.py — ΕΥΡΩΛΙΓΚΑ ΣΥΝΟΛΑ IN-PLAY: «ευστοχια vs ρυθμος» στο 1ο ημιχρονο (και στην 1η περιοδο) (29/10/2026, Στελιος).
Ιδεα: ποντοι πανω/κατω απο το αναμενομενο λογω ΤΡΟΜΕΡΗΣ ευστοχιας/αστοχιας → το 2ο ημιχρονο «ισορροπει» → under/over in-play.

ΠΡΟ-ΔΗΛΩΜΕΝΗ ΜΕΘΟΔΟΣ (εγκριθηκε «οκ τρεξτο»):
  Ματς: κανονικη περιοδος, ΧΩΡΙΣ παραταση, γραμμη κλεισιματος συνολου Crown (pre-match).
  Αναμενομενο σημειου (ημιχρονο / 1η περιοδος) = μεριδιο ποντων (50.4% / 25.1%) × γραμμη κλεισιματος.
  Αποκλιση σημειου e = ποντοι − αναμενομενο, σπασμενη σε 3 κομματια (αθροιζουν ακριβως στο e):
    ΡΥΘΜΟΣ   = (κατοχες − αναμενομενες κατοχες) × αναμενομενοι ποντοι/κατοχη
               κατοχες = FGA + 0.44·FTA − OREB + TO (και οι 2 ομαδες)·
               αναμενομενες = μεσος λιγκας της σεζον στο σημειο + αποκλιση ρυθμου των 2 ομαδων στα ΠΡΟΗΓΟΥΜΕΝΑ ματς τους (σβησιμο n/(n+5))
    ΕΥΣΤΟΧΙΑ = ποντοι − (2·p2·σουτ2 + 3·p3·σουτ3 + pft·βολες)  με p = ποσοστα λιγκας της σεζον (τρεις ποντους χωριστα για πληροφορια)
    ΥΠΟΛΟΙΠΟ = e − ΡΥΘΜΟΣ − ΕΥΣΤΟΧΙΑ (ποσα σουτ/βολες ανα κατοχη: λαθη, επιθ. ριμπαουντ, φαουλ — και λαθος της γραμμης)
  ΒΗΜΑ Α (χωρις αποδοσεις, E2021-E2025): (υπολοιπο ματς − αναμενομενο υπολοιπο) ~ ΡΥΘΜΟΣ + ΕΥΣΤΟΧΙΑ + ΥΠΟΛΟΙΠΟ.
     Συντελεστης = ποσο απο καθε ποντο της πηγης «συνεχιζει» στο υπολοιπο ματς.
     ΠΕΡΝΑ: συντελεστης ΕΥΣΤΟΧΙΑΣ μικροτερος του ΡΥΘΜΟΥ με t ≥ 2 (στη διαφορα) στο ημιχρονο. Αλλιως ΣΤΟΠ (το Β τυπωνεται μονο ως πληροφορια).
  ΒΗΜΑ Β (με αποδοσεις, Crown in-play, E2025): live γραμμη = η ΤΕΛΕΥΤΑΙΑ εγκυρη in-play γραμμη με σκορ = ακριβως το σκορ του σημειου.
     (τελικο − live γραμμη) ~ ΡΥΘΜΟΣ + ΕΥΣΤΟΧΙΑ + ΥΠΟΛΟΙΠΟ (συντελεστες ≠ 0 = η live αγορα δεν τα «ζυγιζει» σωστα· ΕΥΣΤΟΧΙΑ < 0 = υπερ-αντιδρα στην ευστοχια).
     Κανονες: UNDER οταν ΕΥΣΤΟΧΙΑ ≥ +X, OVER οταν ΕΥΣΤΟΧΙΑ ≤ −X, X ∈ {6, 10, 14} π.· εκκαθαριση στην αποδοση Crown (push στην ακεραια).
     + αντιθετο σεναριο ρυθμου: OVER οταν ΡΥΘΜΟΣ ≥ +X, UNDER οταν ≤ −X.
     ΠΕΡΝΑ: ROI > 0 στο κυριο X=10 και θετικο στα 6/14· EuroCup ΔΕΝ εχει play-by-play → ο ελεγχος «ιδιο προσημο EC» ΔΕΝ γινεται (δηλωνεται).
     ΠΕΡΙΟΡΙΣΜΟΣ: in-play γραμμες μονο 1+ σεζον → το καλυτερο δυνατο = ΣΚΙΑ.
Εξοδος: el_half_luck_test_out.txt"""
import sys, io, os, json, contextlib, collections
import numpy as np, pandas as pd
class _B(io.StringIO):
    def reconfigure(self, **k): pass
LT = {}
with contextlib.redirect_stdout(_B()):
    exec(open('el_line_timing.py', encoding='utf-8').read().split('ATH = ')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), LT)
sys.stdout.reconfigure(encoding='utf-8')
D, mapping, series, ROWS, SHIFT = LT['D'], LT['mapping'], LT['series'], LT['ROWS'], LT['SHIFT']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open('el_half_luck_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
BOX = json.load(open('el_box.json', encoding='utf-8'))
key_of = {(b['season'], b['hs'], b['as_'], b['utc'][:10]): k for k, b in BOX.items()}
SEAS = ['E2021', 'E2022', 'E2023', 'E2024', 'E2025']   # E2026: δεν εχει αντιστοιχιση Nowgoal ακομα
QK = ['FirstQuarter', 'SecondQuarter', 'ThirdQuarter', 'ForthQuarter']

def stats(evs):
    s = collections.Counter()
    for e in evs:
        p = e.get('PLAYTYPE')
        if p == '2FGM': s['m2'] += 1; s['a2'] += 1
        elif p == '2FGA': s['a2'] += 1
        elif p == '3FGM': s['m3'] += 1; s['a3'] += 1
        elif p == '3FGA': s['a3'] += 1
        elif p == 'FTM': s['mf'] += 1; s['af'] += 1
        elif p == 'FTA': s['af'] += 1
        elif p == 'O': s['orb'] += 1
        elif p == 'TO': s['to'] += 1
    s['pts'] = 2 * s['m2'] + 3 * s['m3'] + s['mf']
    s['poss'] = s['a2'] + s['a3'] + 0.44 * s['af'] - s['orb'] + s['to']
    return s

# ---- ματς ----
G = []
nm = collections.Counter()
for ng, (i, swap) in mapping.items():
    pos = D.index.get_loc(i); sea = D.season.values[pos]
    if D.phase.values[pos] != 'RS' or sea not in SEAS: continue
    tt = pd.Timestamp(D.t.values[pos]); tip = (tt.tz_localize('UTC') if tt.tzinfo is None else tt).timestamp()
    ser = [r for r in series(ng, 23, swap) if r[0] <= tip + 600]
    if len(ser) < 1: nm['χωρις γραμμη'] += 1; continue
    k = None
    for dd in (0, -1, 1):
        k = key_of.get((sea, int(D.hs.values[pos]), int(D.as_.values[pos]), str((tt + pd.Timedelta(days=dd)).date())))
        if k: break
    if not k or not os.path.exists(f'el_pbp/{k}.json'): nm['χωρις pbp'] += 1; continue
    if BOX[k].get('min', 200) > 200.5: nm['παραταση'] += 1; continue
    J = json.load(open(f'el_pbp/{k}.json', encoding='utf-8'))
    pb = J['pbp']
    if any(not isinstance(pb.get(q), list) or not pb.get(q) for q in QK): nm['ελλιπες pbp'] += 1; continue
    tot = int(D.hs.values[pos] + D.as_.values[pos])
    sq = [stats(pb[q]) for q in QK]
    if sum(s['pts'] for s in sq) != tot: nm['pbp ≠ τελικο'] += 1; continue
    # σκορ (γηπ, φιλ) στο τελος Q1 / Q2 απο το pbp
    def score_at(nq):
        last = (0, 0)
        for q in QK[:nq]:
            for e in pb[q]:
                if e.get('POINTS_A') is not None and e.get('POINTS_B') is not None: last = (int(e['POINTS_A']), int(e['POINTS_B']))
        return last
    teams = (D.home.values[pos], D.away.values[pos])
    G.append(dict(ng=ng, pos=pos, sea=sea, tip=tip, L=float(ser[-1][2]), tot=tot, teams=teams, q=sq, sc1=score_at(1), sc2=score_at(2), swap=swap))
P(f'ματς: {len(G)} · εκτος: ' + ', '.join(f'{k} {v}' for k, v in nm.items()))
for s in SEAS: P(f'  {s}: {sum(g["sea"] == s for g in G)}')
G.sort(key=lambda g: g['tip'])
bad = sum(sum(g['sc2']) != g['q'][0]['pts'] + g['q'][1]['pts'] for g in G)
P(f'ελεγχος: σκορ ημιχρονου απο POINTS_A/B ≠ αθροισμα σουτ Q1+Q2 σε {bad} ματς')

# ---- κομματια ανα σημειο ----
SH = {1: None, 2: None}
rows = {1: [], 2: []}
for nq in (1, 2):
    fr = np.mean([sum(s['pts'] for s in g['q'][:nq]) / g['tot'] for g in G]); SH[nq] = fr
    lg = {}
    for s in SEAS:
        A = [sum((g['q'][j] for j in range(nq)), collections.Counter()) for g in G if g['sea'] == s]
        tot_ = sum(A, collections.Counter())
        lg[s] = dict(p2=tot_['m2'] / tot_['a2'], p3=tot_['m3'] / tot_['a3'], pf=tot_['mf'] / tot_['af'], poss=np.mean([a['poss'] for a in A]))
    hist = collections.defaultdict(list)                                     # (σεζον, ομαδα) -> αποκλισεις κατοχων προηγουμενων ματς
    for g in G:
        a = sum((g['q'][j] for j in range(nq)), collections.Counter()); l = lg[g['sea']]
        dev = 0.0
        for t in g['teams']:
            h = hist[(g['sea'], t)]; n = len(h)
            if n: dev += np.mean(h) * n / (n + 5)
        pe = l['poss'] + dev
        exp_pts = fr * g['L']; ppp = exp_pts / pe
        e = a['pts'] - exp_pts
        pace = (a['poss'] - pe) * ppp
        sexp = 2 * l['p2'] * a['a2'] + 3 * l['p3'] * a['a3'] + l['pf'] * a['af']
        shoot = a['pts'] - sexp
        s3 = 3 * (a['m3'] - l['p3'] * a['a3']); s2f = shoot - s3
        rest = e - pace - shoot
        e_rest = (g['tot'] - a['pts']) - (1 - fr) * g['L']
        rows[nq].append(dict(g=g, e=e, pace=pace, shoot=shoot, s3=s3, s2f=s2f, rest=rest, e_rest=e_rest, pts=a['pts']))
        for t in g['teams']: hist[(g['sea'], t)].append(a['poss'] - l['poss'])

def ols(X, y):
    X = np.column_stack([np.ones(len(y))] + X); b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b; s2 = r @ r / (len(y) - X.shape[1]); V = s2 * np.linalg.inv(X.T @ X); return b, V

NM = {1: '1η ΠΕΡΙΟΔΟΣ', 2: 'ΗΜΙΧΡΟΝΟ'}
P('\n=== ΒΗΜΑ Α: ποσο «συνεχιζει» καθε πηγη αποκλισης στο υπολοιπο ματς (χωρις αποδοσεις) ===')
P('   συντελεστης = για καθε 1 π. της πηγης, ποσοι ποντοι ΕΞΤΡΑ ερχονται στο υπολοιπο ματς (0 = τιποτα, το υπολοιπο ειναι «κανονικο»)')
passA = None
for nq in (1, 2):
    R = rows[nq]
    y = np.array([r['e_rest'] for r in R]); E = np.array([r['e'] for r in R])
    pace, shoot, rest = (np.array([r[k] for r in R]) for k in ('pace', 'shoot', 'rest'))
    P(f'\n## {NM[nq]} (μεριδιο ποντων {SH[nq] * 100:.1f}%, ματς {len(R)})')
    P(f'  τυπικο μεγεθος (τυπ. αποκλιση, ποντοι): συνολικη αποκλιση {E.std():.1f} · ρυθμος {pace.std():.1f} · ευστοχια {shoot.std():.1f} · υπολοιπο {rest.std():.1f}')
    P(f'  συσχετιση ρυθμου-ευστοχιας {np.corrcoef(pace, shoot)[0, 1]:+.2f}')
    b, V = ols([E], y); P(f'  ολοι μαζι (σκετοι ποντοι): {b[1]:+.3f} (t {b[1] / np.sqrt(V[1, 1]):+.1f})')
    b, V = ols([pace, shoot, rest], y); se = np.sqrt(np.diag(V))
    dif = b[2] - b[1]; sdif = np.sqrt(V[1, 1] + V[2, 2] - 2 * V[1, 2])
    P(f'  ΡΥΘΜΟΣ {b[1]:+.3f} (t {b[1] / se[1]:+.1f}) · ΕΥΣΤΟΧΙΑ {b[2]:+.3f} (t {b[2] / se[2]:+.1f}) · ΥΠΟΛΟΙΠΟ {b[3]:+.3f} (t {b[3] / se[3]:+.1f})')
    P(f'  ΕΥΣΤΟΧΙΑ − ΡΥΘΜΟΣ = {dif:+.3f} (t {dif / sdif:+.1f})')
    s3, s2f = (np.array([r[k] for r in R]) for k in ('s3', 's2f'))
    b2, V2 = ols([pace, s3, s2f, rest], y); se2 = np.sqrt(np.diag(V2))
    P(f'  (πληροφορια) ευστοχια τριποντων {b2[2]:+.3f} (t {b2[2] / se2[2]:+.1f}) · ευστοχια διποντων+βολων {b2[3]:+.3f} (t {b2[3] / se2[3]:+.1f})')
    for s in SEAS:
        m = np.array([r['g']['sea'] == s for r in R])
        if m.sum() < 60: continue
        bs, Vs = ols([pace[m], shoot[m], rest[m]], y[m])
        P(f'    {s} (n {m.sum()}): ρυθμος {bs[1]:+.2f} · ευστοχια {bs[2]:+.2f} · υπολοιπο {bs[3]:+.2f}')
    P('  ανα ζωνη ΕΥΣΤΟΧΙΑΣ (ποντοι πανω/κατω απο τα αναμενομενα λογω σουτ): ματς · μεση ευστοχια · υπολοιπο ματς vs αναμενομενο')
    for lo, hi, lab in ((-99, -10, '≤−10 (αστοχια)'), (-10, -4, '−10…−4'), (-4, 4, '−4…+4'), (4, 10, '+4…+10'), (10, 99, '≥+10 (ευστοχια)')):
        m = (shoot > lo) & (shoot <= hi)
        P(f'    {lab:>16}: {m.sum():4d} · {shoot[m].mean():+5.1f} · {y[m].mean():+5.2f}')
    if nq == 2: passA = (dif / sdif <= -2)
P(f'\nΚΡΙΣΗ ΒΗΜΑΤΟΣ Α (ημιχρονο: ευστοχια μικροτερη του ρυθμου με t ≤ −2): {"✓ ΠΕΡΝΑ" if passA else "✗ ΔΕΝ ΠΕΡΝΑ → ΣΤΟΠ (το Β μονο ως πληροφορια)"}')
save()

# ---- ΒΗΜΑ Β: live γραμμη Crown ----
def live_at(g, sc):
    hs, as_ = sc; best = None
    for x in sorted(ROWS.get((g['ng'], 23), []), key=lambda x: x[0]):
        if len(x) < 7 or x[4] != 3 or x[5] is None or x[6] is None: continue
        if not x[1] or not x[2] or not x[3] or x[1] <= 0 or x[2] <= 0 or x[3] <= 0: continue
        if {int(x[5]), int(x[6])} == {hs, as_} and int(x[5]) + int(x[6]) == hs + as_ and (int(x[5]), int(x[6])) in ((hs, as_), (as_, hs)):
            best = (float(x[1]), 1 + x[2], 1 + x[3])
    return best
def settle(tot, L, side, o):
    if tot == L: return 0.0
    win = (tot > L) if side == 'O' else (tot < L)
    return (o - 1) if win else -1.0
P('\n=== ΒΗΜΑ Β: απεναντι στη LIVE γραμμη Crown (E2025 — φετος δεν υπαρχουν ακομα in-play Nowgoal) ===')
for nq in (1, 2):
    R = [r for r in rows[nq] if r['g']['sea'] in ('E2025', 'E2026')]
    B = []
    for r in R:
        g = r['g']; lv = live_at(g, g['sc1'] if nq == 1 else g['sc2'])
        if lv: B.append(dict(r, Lv=lv[0], oo=lv[1], ou=lv[2]))
    P(f'\n## {NM[nq]}: ματς με pbp {len(R)} · με live γραμμη στο σκορ του σημειου {len(B)} (E2025 {sum(b["g"]["sea"] == "E2025" for b in B)} · E2026 {sum(b["g"]["sea"] == "E2026" for b in B)})')
    if not B: continue
    y = np.array([b['g']['tot'] - b['Lv'] for b in B])
    impl = np.array([b['Lv'] - b['pts'] - (1 - SH[nq]) * b['g']['L'] for b in B])
    P(f'  τι κανει η live αγορα: live γραμμη − ποντοι ως τωρα − αναμενομενο υπολοιπο (pre-match) = μεσος {impl.mean():+.2f} π.')
    E = np.array([b['e'] for b in B]); pace, shoot, rest = (np.array([b[k] for b in B]) for k in ('pace', 'shoot', 'rest'))
    bm, Vm = ols([E], impl); P(f'  η αγορα μεταφερει στο υπολοιπο: {bm[1]:+.3f} ανα ποντο αποκλισης (το βημα Α λεει ποσο πραγματικα μεταφερεται)')
    bm, Vm = ols([pace, shoot, rest], impl); sm = np.sqrt(np.diag(Vm))
    P(f'     ανα πηγη: ρυθμος {bm[1]:+.3f} (t {bm[1] / sm[1]:+.1f}) · ευστοχια {bm[2]:+.3f} (t {bm[2] / sm[2]:+.1f}) · υπολοιπο {bm[3]:+.3f} (t {bm[3] / sm[3]:+.1f})')
    P(f'  τελικο − live γραμμη: μεσος {y.mean():+.2f} · over {np.mean(y > 0) * 100:.1f}% · τυπ. αποκλιση {y.std():.1f}')
    b, V = ols([pace, shoot, rest], y); se = np.sqrt(np.diag(V))
    P(f'  (τελικο − live) ~ ρυθμος {b[1]:+.3f} (t {b[1] / se[1]:+.1f}) · ευστοχια {b[2]:+.3f} (t {b[2] / se[2]:+.1f}) · υπολοιπο {b[3]:+.3f} (t {b[3] / se[3]:+.1f})')
    P('     (ευστοχια < 0 = η live αγορα υπερ-αντιδρα στην ευστοχια → under μετα απο «ζεστο» σουτ θα κερδιζε)')
    vig = np.mean([1 / b_['oo'] + 1 / b_['ou'] - 1 for b_ in B]); P(f'  γκανιοτα live συνολου {vig * 100:.1f}%')
    for nmk, key, sgn in (('ΕΥΣΤΟΧΙΑ (ζεστο σουτ → UNDER, κρυο → OVER)', 'shoot', -1), ('ΡΥΘΜΟΣ (γρηγορο → OVER, αργο → UNDER)', 'pace', +1)):
        P(f'  κανονας {nmk}:')
        for X in (6, 10, 14):
            U = []
            for b_ in B:
                v = b_[key]
                if abs(v) < X: continue
                side = ('O' if v > 0 else 'U') if sgn > 0 else ('U' if v > 0 else 'O')
                U.append((settle(b_['g']['tot'], b_['Lv'], side, b_['oo'] if side == 'O' else b_['ou']), side, b_['g']['sea']))
            if not U: P(f'    ≥{X:2d} π.: —'); continue
            u = np.array([x[0] for x in U]); se_ = u.std() / np.sqrt(len(u))
            byside = {s_: [x[0] for x in U if x[1] == s_] for s_ in ('O', 'U')}
            bys = ' · '.join(f'{s_} {len(v)} {np.mean(v) * 100:+.1f}%' for s_, v in byside.items() if v)
            byse = ' · '.join(f'{s_} {sum(1 for x in U if x[2] == s_)} {np.mean([x[0] for x in U if x[2] == s_]) * 100:+.1f}%' for s_ in ('E2025', 'E2026') if any(x[2] == s_ for x in U))
            P(f'    ≥{X:2d} π.: {len(u):3d} bets · ROI {u.mean() * 100:+6.1f}% (±{se_ * 100:.1f}) · {u.sum():+6.1f}μ · {bys} · {byse}')
save()
