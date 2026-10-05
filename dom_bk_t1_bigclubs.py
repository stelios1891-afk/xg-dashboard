# -*- coding: utf-8 -*-
"""dom_bk_t1_bigclubs.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ, ΤΕΣΤ 1: «φουσκωνει» η αγορα τις μεγαλες/δημοφιλεις ομαδες; (5/10/2026, Στελιος:
«διαφορετικοι μηχανισμοι στα εγχωρια, οχι αντιγραφη»). ΧΩΡΙΣ μοντελο — μονο αγορα vs αποτελεσμα.
Δεδομενα: nowgoal_dom/odds.jsonl (Crown + Bet365, χαντικαπ) + bk_domestic.json (σκορ) · Ισπανια ACB & Ιταλια LBA · 2020-21…2025-26.
Αγορα = αναμενομενη διαφορα γηπεδουχου απο γραμμη+τιμες (σ 12.2), ΜΕΣΟΣ Crown/Bet365 · ROI στις τιμες Crown (αλλιως Bet365).
Ομαδες: «ΓΙΓΑΝΤΕΣ» = Ρεαλ, Μπαρτσελονα (ACB) · Αρμανι Μιλανο, Βιρτους (LBA)· «ΟΜΑΔΕΣ ΕΥΡΩΛΙΓΚΑΣ» = οποιες επαιζαν EL τη σεζον (el_sched).
ΜΕΤΡΑ: υπολοιπο = πραγματικη διαφορα − αγορα (απο την πλευρα της ομαδας) · ROI «στα τυφλα» (ολα τα ματς) υπερ/κατα · ανα βαθος γραμμης.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): ανεπαρκεια αγορας αν |μεσο υπολοιπο στο ΚΛΕΙΣΙΜΟ| ≥ 1.0 ποντο ΚΑΙ t ≥ 2 ΚΑΙ ιδιο προσημο σε ≥5/6 σεζον.
  Αναφορα: ROI τυφλο στο κλεισιμο/ανοιγμα (θετικο σε ποσες σεζον).
Εξοδος: dom_bk_t1_bigclubs_out.txt"""
import sys, json, math, collections
import numpy as np
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
N = NormalDist(); SIG = 12.2
LGS = ['ACB', 'LBA']; SEAS = ['20-21', '21-22', '22-23', '23-24', '24-25', '25-26']
NAME = dict(ACB='Ισπανια', LBA='Ιταλια')
GIANTS = dict(ACB=['madrid', 'barcelona'], LBA=['milan', 'virtus'])
ELKW = ['madrid', 'barcelona', 'baskonia', 'valencia', 'milan', 'virtus', 'monaco', 'asvel', 'bayern', 'alba', 'efes', 'fenerbahce',
        'olympiacos', 'panathinaikos', 'zalgiris', 'maccabi', 'partizan', 'zvezda', 'paris', 'unicaja']
S = json.load(open('el_sched.json', encoding='utf-8'))
ELS = {}
for s, L in S.items():
    y = int(s[1:]); sea = f'{y % 100:02d}-{(y + 1) % 100:02d}'
    ELS[sea] = {kw for x in L for kw in ELKW if kw in (x['home'] + ' ' + x['away']).lower()}
D = json.load(open('bk_domestic.json', encoding='utf-8'))
ROWS = collections.defaultdict(dict)
for ln in open('nowgoal_dom/odds.jsonl', encoding='utf-8'):
    r = json.loads(ln)
    if r['t'] == 21: ROWS[r['ngid']][r['cid']] = r['rows']
def conv(rows):
    R = sorted([x for x in rows if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
    if not R: return None
    f = lambda x: (-x[1], 1 + x[2], 1 + x[3])
    return f(R[0]), f(R[-1])
def mu(L, o1, o2):
    ph = (1 / o1) / (1 / o1 + 1 / o2); return -L + SIG * N.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
G = []
for lg in LGS:
    for sea in SEAS:
        v = D.get(f'{lg}_{sea}') or {}
        tm = v.get('teams', {})
        for g in v.get('games', []):
            try: hs, as_ = int(g[4]), int(g[5])
            except Exception: continue
            od = {c: conv(ROWS.get(int(g[0]), {}).get(c, [])) for c in (3, 8)}
            od = {c: x for c, x in od.items() if x}
            if not od: continue
            mo = float(np.mean([mu(*x[0]) for x in od.values()])); mc = float(np.mean([mu(*x[1]) for x in od.values()]))
            bk = od.get(3) or od.get(8)
            hn, an = tm.get(str(g[2]), ''), tm.get(str(g[3]), '')
            G.append(dict(lg=lg, sea=sea, hn=hn, an=an, act=hs - as_, mo=mo, mc=mc, op=bk[0], cl=bk[1]))
print(f'ματς με αγορα: {len(G)}')
out = []
def P(s=''): print(s, flush=True); out.append(s)
def has(name, kws): n = name.lower(); return any(k in n for k in kws)
def settle(act_team, L_team, odds):
    v = act_team + L_team; return (odds - 1) if v > 0 else (0 if v == 0 else -1)
def report(lab, items):
    """items: [(sea, πραγματικο υπερ ομαδας, αγορα κλεισ., αγορα ανοιγμ., (L_team_open, odds_open), (L_team_close, odds_close), (opp...))]"""
    if len(items) < 30: P(f'  {lab:46s} n {len(items)} (λιγα)'); return
    r = np.array([a - mc for _, a, mc, *_ in items]); ro = np.array([a - mo for _, a, _, mo, *_ in items])
    se = r.std(ddof=1) / math.sqrt(len(r)); per = {s: np.mean([a - mc for s_, a, mc, *_ in items if s_ == s]) for s in SEAS if sum(1 for x in items if x[0] == s) >= 8}
    ok = abs(r.mean()) >= 1.0 and abs(r.mean() / se) >= 2 and sum(np.sign(p) == np.sign(r.mean()) for p in per.values()) >= 5
    roi = {}
    for k, idx in (('υπερ κλεισ.', 5), ('υπερ ανοιγμ.', 4), ('κατα κλεισ.', 6)):
        R = [(settle(it[1] if k != 'κατα κλεισ.' else -it[1], it[idx][0], it[idx][1]), it[0]) for it in items]
        a = np.array([q[0] for q in R]); pos = sum(1 for s in per if np.mean([q[0] for q in R if q[1] == s]) > 0)
        roi[k] = f'{a.mean()*100:+.1f}% ({pos}/{len(per)})'
    P(f'  {lab:46s} n {len(items):4d} · υπολοιπο κλεισ. {r.mean():+.2f} (t {r.mean()/se:+.1f}) · ανοιγμ. {ro.mean():+.2f} · σεζον '
      + ' '.join(f'{p:+.1f}' for p in per.values()) + ' · ROI ' + ' · '.join(f'{k} {v}' for k, v in roi.items()) + ('  ← ΑΝΕΠΑΡΚΕΙΑ' if ok else ''))
def side_items(g, home):
    """απο την πλευρα της ομαδας (γηπ αν home)."""
    s = 1 if home else -1
    (Lo, o1o, o2o), (Lc, o1c, o2c) = g['op'], g['cl']
    team_o = (Lo, o1o) if home else (-Lo, o2o); team_c = (Lc, o1c) if home else (-Lc, o2c)
    opp_c = (-Lc, o2c) if home else (Lc, o1c)
    return (g['sea'], s * g['act'], s * g['mc'], s * g['mo'], team_o, team_c, opp_c)
for lg in LGS:
    GG = [g for g in G if g['lg'] == lg]
    P(''); P(f'=== {NAME[lg]} · {len(GG)} ματς · 6 σεζον ===')
    P(f'  (ολα τα ματς: γηπεδουχος υπολοιπο κλεισ. {np.mean([g["act"] - g["mc"] for g in GG]):+.2f})')
    gi = [side_items(g, True) for g in GG if has(g['hn'], GIANTS[lg]) and not has(g['an'], GIANTS[lg])] + \
         [side_items(g, False) for g in GG if has(g['an'], GIANTS[lg]) and not has(g['hn'], GIANTS[lg])]
    report('ΓΙΓΑΝΤΕΣ (απεναντι σε μη-γιγαντες)', gi)
    report('  … ως γηπεδουχοι', [side_items(g, True) for g in GG if has(g['hn'], GIANTS[lg]) and not has(g['an'], GIANTS[lg])])
    report('  … ως φιλοξενουμενοι', [side_items(g, False) for g in GG if has(g['an'], GIANTS[lg]) and not has(g['hn'], GIANTS[lg])])
    el = lambda g, nm: has(nm, ELS.get(g['sea'], set()))
    report('ΟΜΑΔΕΣ ΕΥΡΩΛΙΓΚΑΣ (απεναντι σε μη-EL)', [side_items(g, True) for g in GG if el(g, g['hn']) and not el(g, g['an'])] +
           [side_items(g, False) for g in GG if el(g, g['an']) and not el(g, g['hn'])])
    P('  ΑΝΑ ΒΑΘΟΣ ΓΡΑΜΜΗΣ (απο την πλευρα του ΦΑΒΟΡΙ, κλεισιμο):')
    for lo, hi in ((0.5, 4.5), (5, 9.5), (10, 14.5), (15, 99)):
        it = []
        for g in GG:
            Lc = g['cl'][0]
            if lo <= abs(Lc) <= hi + 1e-9:
                it.append(side_items(g, Lc < 0))
        report(f'    φαβορι {lo:g}-{hi:g}' if hi < 99 else f'    φαβορι ≥{lo:g}', it)
open('dom_bk_t1_bigclubs_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
