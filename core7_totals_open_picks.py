"""core7_totals_open_picks.py — 12/10/2026 (Στελιος: «στειλε μου ποια picks βγαινουν για την επομενη αγωνιστικη και τι ορια εχουμε αυτη τη στιγμη»).
ΑΓΚΥΡΑ ΣΥΝΟΛΩΝ ΣΤΟ ΑΝΟΙΓΜΑ (core7_goals_blend_timing / core7_goals_anchor_open_out: 7-14 Crown +12.9% n221 4/4, κυριως UNDER, CLV +0.18)
— ΖΩΝΤΑΝΗ αναπαραγωγη ΧΩΡΙΣ αλλαγη στο live (ουτε Telegram ουτε ημερολογιο):
  μοντελο = match_projections_archive.json (live μηχανη, παγωμενη προ-αγωνα για τα παιγμενα, τρεχουσα για τα επερχομενα)
  αγορα = Pinnacle (odds_history.jsonl: ου [γραμμη, over, under] απο 13/9, ορια lim.totals)
  T_mkt = συνολο που δικαιολογει το κλεισιμο (Dixon-Coles, υπεροχη μοντελου) · αγκυρα: για καθε παιγμενο ματς αγωνιστικης ≥7
  e = T_mkt − (T_μοντ + o_γηπ + o_φιλ) → o_γηπ, o_φιλ += 0.5·e/2 (ιδιο με το τεστ, λ=0.5).
  επερχομενα: T' = T_μοντ + o_γηπ + o_φιλ · edge στην ΤΩΡΙΝΗ κυρια γραμμη Pinnacle · pick αν edge ≥10%, 1.70-2.10, σεντρα ≥120ω μπροστα.
"""
import sys, json, datetime as dt, collections
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
import picks
NOW = dt.datetime.now(dt.timezone.utc)
A = json.load(open('match_projections_archive.json', encoding='utf-8'))
def utc(s):
    d = dt.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
# ---- Pinnacle: τελευταια εγγραφη πριν τη σεντρα (κλεισιμο) & τωρινη ----
OH = collections.defaultdict(list)
for l in open('odds_history.jsonl', encoding='utf-8'):
    try: r = json.loads(l)
    except Exception: continue
    if not r.get('ou') or not r.get('ko'): continue
    OH[(str(r.get('hid')), str(r.get('aid')), str(r['ko'])[:10])].append((utc(r['t']), r['ou'], (r.get('lim') or {}).get('totals'), r.get('lg'), r['ko']))
IDX = np.add.outer(np.arange(13), np.arange(13)); KS = np.arange(25)
def tdist(h, a):
    M = picks.score_matrix_dom(max(h, .05), max(a, .05)); return np.bincount(IDX.ravel(), weights=np.asarray(M).ravel(), minlength=25)
def probs(d, L):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; po = pu = pp = 0
    for x in parts:
        po += d[KS > x + .01].sum() / len(parts); pu += d[KS < x - .01].sum() / len(parts); pp += d[np.abs(KS - x) < .01].sum() / len(parts)
    return po, pu, pp
def edge(d, L, over, o):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; e = 0
    for x in parts:
        pw = d[(KS > x + .01) if over else (KS < x - .01)].sum(); pp = d[np.abs(KS - x) < .01].sum()
        e += (pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)) / len(parts)
    return e
def t_mkt(L, o, u, s):
    q = (1 / o) / (1 / o + 1 / u); lo, hi = 0.8, 7.0
    for _ in range(30):
        T = (lo + hi) / 2; po, pu, _ = probs(tdist((T + s) / 2, (T - s) / 2), L)
        if po / max(po + pu, 1e-9) < q: lo = T
        else: hi = T
    return (lo + hi) / 2
# ---- ματς του αρχειου ----
rows = []
for fid, m in A.items():
    try:
        ko = utc(m.get('utc') or m.get('ko') or m.get('kickoff'))
    except Exception:
        continue
    hx, ax = m.get('home_adj_xg'), m.get('away_adj_xg')
    if hx is None or ax is None: continue
    rows.append(dict(fid=fid, lg=m.get('lg') or m.get('league'), gw=m.get('gw'), home=m.get('home'), away=m.get('away'), hid=str(m.get('home_id')),
                     aid=str(m.get('away_id')), ko=ko, hx=float(hx), ax=float(ax)))
rows.sort(key=lambda r: r['ko'])
OFF = collections.defaultdict(float); used = collections.Counter()
up = []
for r in rows:
    seq = OH.get((r['hid'], r['aid'], r['ko'].strftime('%Y-%m-%d')), [])
    T = r['hx'] + r['ax']; s = r['hx'] - r['ax']
    key_h, key_a = (r['lg'], r['hid']), (r['lg'], r['aid'])
    Tp = T + OFF[key_h] + OFF[key_a]
    if r['ko'] <= NOW:
        pre = [x for x in seq if x[0] < r['ko']]
        if pre and (r['gw'] or 0) >= 7:
            _, (L, o, u), *_ = pre[-1]
            e = t_mkt(float(L), float(o), float(u), s) - Tp
            OFF[key_h] += 0.25 * e; OFF[key_a] += 0.25 * e; used[r['lg']] += 1
    else:
        up.append(dict(r, T=T, Tp=Tp, s=s, seq=seq))
print(f'ΑΓΚΥΡΑ: ματς που μετρησαν (αγωνιστικη ≥7, με κλεισιμο Pinnacle): ' + ' · '.join(f'{lg} {n}' for lg, n in sorted(used.items())))
print(f'\nΕΠΕΡΧΟΜΕΝΑ (σεντρα ≥120ω μπροστα = ≥ {(NOW + dt.timedelta(hours=120)) + dt.timedelta(hours=3):%a %d/%m %H:%M} ωρα Ελλαδας) — edge ≥10%, 1.70-2.10, τωρινη γραμμη Pinnacle')
WEND = dt.datetime(2026, 10, 20, 6, 0, tzinfo=dt.timezone.utc)     # επομενη αγωνιστικη = ματς ως τη Δευτερα 19/10
up = [r for r in up if r['ko'] < WEND]
print('ΕΠΟΜΕΝΗ ΑΓΩΝΙΣΤΙΚΗ (ματς ως 19/10): ' + ' · '.join(f'{lg} {n}' for lg, n in sorted(collections.Counter(r['lg'] for r in up).items())))
out = []; allm = []
for r in up:
    hrs = (r['ko'] - NOW).total_seconds() / 3600
    if not r['seq']: continue
    t, (L, o, u), lim, lg, _ = r['seq'][-1]
    L, o, u = float(L), float(o), float(u)
    d = tdist((r['Tp'] + r['s']) / 2, (r['Tp'] - r['s']) / 2)
    Tk = t_mkt(L, o, u, r['s'])
    best = max(((edge(d, L, True, o), 'Over', o), (edge(d, L, False, u), 'Under', u)))
    allm.append((r, hrs, L, o, u, lim, Tk, best))
    if hrs >= 120 and best[0] >= 0.10 and 1.70 <= best[2] <= 2.10:
        out.append((r, hrs, L, best, lim, Tk))
for r, hrs, L, (e, side, od), lim, Tk in sorted(out, key=lambda x: x[0]['ko']):
    kg = r['ko'] + dt.timedelta(hours=3)
    print(f"   {kg:%a %d/%m %H:%M} {r['lg']:12s} {r['home'][:20]:20s} - {r['away'][:20]:20s} · {side} {L:g} @{od:.2f} · edge {100 * e:.0f}% · "
          f"γκολ: μοντελο {r['T']:.2f} → με αγκυρα {r['Tp']:.2f} · αγορα {Tk:.2f} · ΟΡΙΟ γκολ {lim} · σε {hrs / 24:.1f} μερες (αγων. {r['gw']})")
if not out: print('   κανενα')
near = [x for x in allm if x[1] >= 120 and x[7][0] >= 0.05 and not (x[7][0] >= .10 and 1.70 <= x[7][2] <= 2.10)]
print(f'\n(ματς ≥5 μερες με τιμη: {sum(1 for x in allm if x[1] >= 120)} · με edge 5-10% ή εκτος τιμης: {len(near)})')
for r, hrs, L, o, u, lim, Tk, (e, side, od) in sorted(near, key=lambda x: -x[7][0])[:8]:
    print(f"      {r['lg']:12s} {r['home'][:18]:18s} - {r['away'][:18]:18s} {side} {L:g} @{od:.2f} edge {100 * e:.0f}% · οριο {lim}")
