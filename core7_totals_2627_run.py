"""core7_totals_2627_run.py — 12/10/2026 (Στελιος: «ξανατρεξε το backtest απο την αρχη της χρονιας και ξεκινημα στοιχηματων απο εκει που βρισκομαστε σημερα»).
ΦΕΤΙΝΗ ΣΕΖΟΝ 2026-27, αγκυρα συνολων (λ=0.5) — ΧΩΡΙΣ αλλαγη live:
  μοντελο = match_projections_archive.json (παγωμενη προ-αγωνα προβλεψη, live μηχανη) · αγορα = Pinnacle (odds_history 'ou', απο 13/9)
  X: αγκυρα μαθαινει απο την 7η (οπως το τεστ) · Y: αγκυρα μαθαινει απο οσο νωριτερα υπαρχει κλεισιμο Pinnacle (13/9 → ~4η-5η)
  ΤΙΜΙΟΣ ΧΡΟΝΟΣ (core7_totals_anchor_md1_test Γ): pick στην τιμη που ισχυε 06:00 UTC μετα το προηγουμενο ματς ΚΑΙ των δυο ομαδων.
  (1) φετινα παιγμενα 7η+ (ζωντανη «αναπαραγωγη») · (2) επομενη αγωνιστικη: ΕΤΟΙΜΑ (και οι 2 ομαδες εχουν αποτελεσμα στο αρχειο)
      ή ΑΝΑΜΟΝΗ (περιμενει αποτελεσμα) · η αγκυρα μαθαινει απο το κλεισιμο, αρα και απο ματς χωρις καταχωρημενο σκορ · edge ≥10%, 1.70-2.10.
"""
import sys, json, datetime as dt, collections
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
import picks
NOW = dt.datetime.now(dt.timezone.utc); GR = dt.timedelta(hours=3)
A = json.load(open('match_projections_archive.json', encoding='utf-8'))
def utc(s):
    d = dt.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
OH = collections.defaultdict(list)
for l in open('odds_history.jsonl', encoding='utf-8'):
    try: r = json.loads(l)
    except Exception: continue
    if not r.get('ou') or not r.get('ko') or r.get('inplay'): continue
    OH[(str(r.get('hid')), str(r.get('aid')), str(r['ko'])[:10])].append((utc(r['t']), [float(x) for x in r['ou']], (r.get('lim') or {}).get('totals')))
for v in OH.values(): v.sort(key=lambda x: x[0])
IDX = np.add.outer(np.arange(13), np.arange(13)); KS = np.arange(25)
def tdist(h, a):
    M = picks.score_matrix_dom(max(h, .05), max(a, .05)); return np.bincount(IDX.ravel(), weights=np.asarray(M).ravel(), minlength=25)
def probs(d, L):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; po = pu = 0
    for x in parts: po += d[KS > x + .01].sum() / len(parts); pu += d[KS < x - .01].sum() / len(parts)
    return po, pu
def ou_eval(d, L, over, o, tg=None):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; e = s_ = 0
    for x in parts:
        pw = d[(KS > x + .01) if over else (KS < x - .01)].sum(); pp = d[np.abs(KS - x) < .01].sum()
        e += (pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)) / len(parts)
        if tg is not None:
            m = (tg - x) if over else (x - tg); s_ += ((o - 1) if m > .01 else (0 if abs(m) < .01 else -1)) / len(parts)
    return e, s_
def t_mkt(L, o, u, s):
    q = (1 / o) / (1 / o + 1 / u); lo, hi = 0.8, 7.0
    for _ in range(30):
        T = (lo + hi) / 2; po, pu = probs(tdist((T + s) / 2, (T - s) / 2), L)
        if po / max(po + pu, 1e-9) < q: lo = T
        else: hi = T
    return (lo + hi) / 2
rows = []
for fid, m in A.items():
    try: ko = utc(m['utc'])
    except Exception: continue
    if m.get('home_adj_xg') is None: continue
    sc = m.get('score'); tg = None
    if sc:
        try: tg = sum(int(x) for x in str(sc).split('-'))
        except ValueError: pass
    rows.append(dict(lg=m['league'], gw=m.get('gw') or 0, home=m['home'], away=m['away'], hid=str(m['home_id']), aid=str(m['away_id']), ko=ko,
                     hx=float(m['home_adj_xg']), ax=float(m['away_adj_xg']), tg=tg,
                     seq=OH.get((str(m['home_id']), str(m['away_id']), ko.strftime('%Y-%m-%d')), [])))
rows.sort(key=lambda r: r['ko'])
last = {}                                  # (λιγκα, ομαδα) → (σεντρα, εχει αποτελεσμα)
for r in rows:
    p = [last.get((r['lg'], r['hid'])), last.get((r['lg'], r['aid']))]
    r['prev'] = max(x[0] for x in p if x) if any(p) else None
    r['ready'] = all(x is None or x[1] for x in p)
    last[(r['lg'], r['hid'])] = last[(r['lg'], r['aid'])] = (r['ko'], r['tg'] is not None)
def t_av(prev):
    t = prev + dt.timedelta(hours=2); n = t.replace(hour=6, minute=0, second=0, microsecond=0)
    return n if n > t else n + dt.timedelta(days=1)
WEND = dt.datetime(2026, 10, 20, 6, 0, tzinfo=dt.timezone.utc)
for lab, start in (('X · αγκυρα απο την 7η (οπως το τεστ)', 7), ('Y · αγκυρα απο την αρχη (οσο υπαρχει κλεισιμο Pinnacle, απο 13/9)', 1)):
    OFF = collections.defaultdict(float); used = collections.Counter(); played = []; nxt = []
    for r in rows:
        s = r['hx'] - r['ax']; kh, ka = (r['lg'], r['hid']), (r['lg'], r['aid'])
        Tp = r['hx'] + r['ax'] + OFF[kh] + OFF[ka]; seq = r['seq']
        if r['ko'] <= NOW:
            if r['tg'] is not None and r['gw'] >= 7 and r['prev'] and seq:                         # φετινο «παιγμενο» pick στον τιμιο χρονο
                ta = t_av(r['prev']); bef = [x for x in seq if x[0] <= ta]; q = bef[-1] if bef else (seq[0] if seq[0][0] < r['ko'] else None)
                if q:
                    L, o, u = q[1]; d = tdist((Tp + s) / 2, (Tp - s) / 2)
                    best = max((ou_eval(d, L, True, o, r['tg']) + ('Over', o), ou_eval(d, L, False, u, r['tg']) + ('Under', u)))
                    if best[0] >= .10 and 1.70 <= best[3] <= 2.10: played.append((r, L, best))
            pre = [x for x in seq if x[0] < r['ko']]
            if pre and r['gw'] >= start:
                L, o, u = pre[-1][1]; e = t_mkt(L, o, u, s) - Tp
                OFF[kh] += .25 * e; OFF[ka] += .25 * e; used[r['lg']] += 1
        elif r['ko'] > NOW and r['ko'] < WEND and seq:
            L, o, u = seq[-1][1]; d = tdist((Tp + s) / 2, (Tp - s) / 2)
            best = max((ou_eval(d, L, True, o) + ('Over', o), ou_eval(d, L, False, u) + ('Under', u)))
            nxt.append((r, L, best, seq[-1][2], Tp, t_mkt(L, o, u, s), OFF[kh] + OFF[ka]))
    print('=' * 110 + '\n' + lab)
    print('   ματς που εμαθε η αγκυρα: ' + ' · '.join(f'{k} {v}' for k, v in sorted(used.items())))
    n = len(played); pnl = sum(b[1] for _, _, b in played)
    print(f'   (1) ΦΕΤΙΝΑ ΠΑΙΓΜΕΝΑ 7η+ (τιμιος χρονος, Pinnacle): {n} picks · {pnl:+.2f} μοναδες' + (f' ({100 * pnl / n:+.0f}%)' if n else ''))
    for r, L, (e, p, sd, o) in played:
        print(f"       {(r['ko'] + GR):%d/%m} {r['lg']:12s} αγ.{r['gw']:2d} {r['home'][:18]:18s}-{r['away'][:18]:18s} {sd} {L:g} @{o:.2f} edge {100 * e:.0f}% · γκολ {r['tg']} → {p:+.2f}")
    ok = [x for x in nxt if x[0]['gw'] >= 7 and x[2][0] >= .10 and 1.70 <= x[2][3] <= 2.10]
    print(f'   (2) ΕΠΟΜΕΝΗ ΑΓΩΝΙΣΤΙΚΗ (ως 19/10), μονο 7η+: {len(ok)} picks με τη ΣΗΜΕΡΙΝΗ τιμη Pinnacle')
    for r, L, (e, p, sd, o), lim, Tp, Tk, off in sorted(ok, key=lambda x: x[0]['ko']):
        st = 'ΕΤΟΙΜΟ ' if r['ready'] else 'ΑΝΑΜΟΝΗ'
        print(f"       {st} {(r['ko'] + GR):%a %d/%m %H:%M} {r['lg']:12s} αγ.{r['gw']:2d} {r['home'][:18]:18s}-{r['away'][:18]:18s} {sd} {L:g} @{o:.2f} edge {100 * e:.0f}% · "
              f"γκολ μοντ {r['hx'] + r['ax']:.2f} αγκυρα {off:+.2f} → {Tp:.2f} · αγορα {Tk:.2f} · οριο {lim}")
    print('   ανα λιγκα (επομενη αγωνιστικη): ' + ' · '.join(f"{lg} αγ.{min(x[0]['gw'] for x in nxt if x[0]['lg'] == lg)}: {sum(1 for x in ok if x[0]['lg'] == lg)}/"
                                                       f"{sum(1 for x in nxt if x[0]['lg'] == lg)}" for lg in sorted({x[0]['lg'] for x in nxt})))
