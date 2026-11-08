# -*- coding: utf-8 -*-
"""el_gtd_study.py — ΕΥΡΩΛΙΓΚΑ: ΠΟΣΟ ΣΥΧΝΑ ΠΑΙΖΕΙ ΕΝΑΣ ΑΜΦΙΒΟΛΟΣ (23/10/2026, Στελιος «ξεκινα το 3 της ευρωλιγκας»).
Πηγη: ιστορικο RotoWire Ευρωλιγκας (el_news/rw_el_hist.jsonl, el_rw_hist_fetch.py, 9/2021-5/2026) — ΧΩΡΙΣ πεδιο καταστασης·
η κατασταση διαβαζεται απο τιτλο + κειμενο με φρασεις (CAT πιο κατω). ΒΗΜΑ 1 (--sample): ταξινομηση + τυχαια παραδειγματα ανα κατηγορια
για ελεγχο απο τον Στελιο ΠΡΙΝ απο οποιοδηποτε νουμερο. ΒΗΜΑ 2: καθε ειδηση → επομενο ματς Ευρωλιγκας της ομαδας ≤72ω (el_sched.json) →
επαιξε; (λεπτα > 0 στο box, el_pbp/) · ποσοστα ανα κατηγορια, ρολο (λεπτα/PIR περσι-φετος), ωρες πριν, σεζον.
Ωρα RotoWire: ts_raw σε ωρα Νεας Υορκης (ελεγχεται: οι «Will not play …» πρεπει να ειναι πριν το ματς).
Εξοδος: el_gtd_study_out.txt"""
import json, re, sys, random, collections, datetime as dt
from zoneinfo import ZoneInfo
sys.stdout.reconfigure(encoding='utf-8')
NY = ZoneInfo('America/New_York')
R = [json.loads(l) for l in open('el_news/rw_el_hist.jsonl', encoding='utf-8')]
def txt(r): return ((r.get('headline') or '') + ' || ' + (r.get('news') or '')).lower()
# 23/10 β' εκδοση (μετα τα πρωτα δειγματα): (1) εξω οι ειδησεις για ΕΓΧΩΡΙΑ ματς · (2) μονο ειδησεις για ΕΠΟΜΕΝΟ ματς (μελλοντικη διατυπωση)
# · (3) ΟΡΙΣΤΙΚΟ «εκτος» πρωτο (π.χ. «Not ready to return… will not play») · (4) αρνησεις («did not travel / not traveling») = εκτος.
DOMESTIC = re.compile(r"domestic|league game|acb|lega|bbl|greek basket|turkish|aba league|lnb|betclic|winner league|super league")
FUTURE = re.compile(r"\bwill\b|won't|could|may |might|expected|unlikely|doubtful|questionable|uncertain|game-time|should|probable|is set to|on track|not travel|did not travel|traveled|travelled|is listed|is available|is unavailable")
CAT = [
    ('ΕΚΤΟΣ', r"will not play|won't play|ruled out|will miss|won't suit up|will not suit up|will be out|will sit|will not be available|won't be available|did not travel|not traveling|not travelling|not make the trip|left off the (roster|squad)|not included in the (roster|squad)|is out (for|of)"),
    ('ΑΜΦΙΒΟΛΟΣ', r"game[- ]time decision|game[- ]time call|questionable|uncertain|up in the air|in question|day-to-day|could (play|return|suit up|be available)|may (play|return|be available|not play)|might (play|return|not play)|status (is |remains )?(unclear|uncertain|in doubt)|50-50|touch-and-go"),
    ('ΜΑΛΛΟΝ ΕΚΤΟΣ', r"doubtful|unlikely to (play|suit up|be available|return)|not expected to (play|suit up|be available)|probably (won't|will not)|expected to (miss|sit)|likely to (miss|sit)"),
    ('ΜΑΛΛΟΝ ΠΑΙΖΕΙ', r"expected to (play|suit up|be available|return|feature)|probable|likely to (play|suit up)|should (play|be available|suit up|be an option)|set to (play|return)|on track to play|poised to play"),
    ('ΠΑΙΖΕΙ', r"will play|will suit up|will be available|cleared to play|traveled .{0,40}with (his|the) (teammates|team)|travelled .{0,40}with (his|the) (teammates|team)|is available for|will be in the lineup|will return to action"),
]
CRX = [(c, re.compile(p)) for c, p in CAT]
def cat(r):
    t = txt(r); n = (r.get('news') or '').lower()
    if DOMESTIC.search(t) or not FUTURE.search(n): return None
    for c, rx in CRX:
        if rx.search(n): return c                           # πρωτα το κειμενο (ακριβεστερο απο τον τιτλο)
    for c, rx in CRX:
        if rx.search((r.get('headline') or '').lower()): return c
    return None
for r in R: r['cat'] = cat(r)
if '--sample' in sys.argv:
    random.seed(7)
    cnt = collections.Counter(r['cat'] for r in R)
    print('ΚΑΤΗΓΟΡΙΕΣ:', ' · '.join(f'{k or "καμια"} {v}' for k, v in cnt.most_common()))
    for c, _ in CAT:
        xs = [r for r in R if r['cat'] == c]
        print(f'\n=== {c} ({len(xs)}) — 12 τυχαια ===')
        for r in random.sample(xs, min(12, len(xs))):
            print(f"  [{r['team']}] {r['player']}: «{r['headline']}» — {(r.get('news') or '')[:170]}")
    sys.exit()
# ---------------- ΒΗΜΑ 2: ειδηση → επομενο ματς Ευρωλιγκας → επαιξε; ----------------
import glob, os, unicodedata, statistics as st
def tok(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return [w for w in re.split(r'[^a-z]+', s) if w and w not in ('jr', 'sr', 'ii', 'iii', 'iv')]
S = json.load(open('el_sched.json', encoding='utf-8'))
G = {}                                                         # (σεζον, code) → (utc ts, hcode, acode)
for s_, L in S.items():
    for g in L:
        try: G[(s_, g['code'])] = (dt.datetime.fromisoformat(g['utc'].replace('Z', '+00:00')).timestamp(), g['hcode'], g['acode'])
        except Exception: pass
BOX = {}; MINS = collections.defaultdict(list)                 # (σεζον, code) → {ομαδα: {κλειδι επωνυμου: (λεπτα, ονομα)}}
for fn in glob.glob('el_pbp/*.json'):
    d = json.load(open(fn, encoding='utf-8')); key = (d['season'], d['code'])
    if key not in G: continue
    tm = collections.defaultdict(dict)
    for stt in d['box'].get('Stats') or []:
        for x in stt.get('PlayersStats') or []:
            m = str(x.get('Minutes') or '')
            try: mm = int(m.split(':')[0]) + int(m.split(':')[1]) / 60
            except Exception: mm = 0.0
            sur = tok(x['Player'].split(',')[0]); fst = tok(x['Player'].split(',')[1]) if ',' in x['Player'] else []
            tm[x['Team'].strip()][(tuple(sur), (fst or [''])[0][:1])] = (mm, x['Player'])
            if mm > 0: MINS[(d['season'], x['Team'].strip(), x['Player'])].append((G[key][0], mm))
    BOX[key] = tm
ROSTER = collections.defaultdict(dict)
for (s_, c), tm in BOX.items():
    for team, pl in tm.items():
        for k, v in pl.items(): ROSTER[(s_, team)][k] = (0.0, v[1])
TEAMG = collections.defaultdict(list)                          # (σεζον, ομαδα EL) → [(utc, code)]
for (s_, c), (ts, h, a) in G.items():
    if (s_, c) in BOX: TEAMG[(s_, h)].append((ts, c)); TEAMG[(s_, a)].append((ts, c))
for k in TEAMG: TEAMG[k].sort()
def season_of(t):
    d = dt.datetime.fromtimestamp(t, dt.timezone.utc); return f'E{d.year if d.month >= 7 else d.year - 1}'
def utc_of(r):
    try: return dt.datetime.fromisoformat(r['ts_raw']).replace(tzinfo=NY).timestamp()
    except Exception: return None
# αντιστοιχιση κωδικων RotoWire → EL απο κοινα επωνυμα (ανα σεζον)
rwsur = collections.defaultdict(set)
for r in R:
    t = utc_of(r)
    if t and r.get('player'): rwsur[(season_of(t), r['team'])].add(tuple(tok(r['player'])[-1:]))
elsur = collections.defaultdict(set)
for (s_, c), tm in BOX.items():
    for team, pl in tm.items():
        for (sur, f) in pl: elsur[(s_, team)].add(sur[-1:])
MAP = {}
for (s_, rw), names in rwsur.items():
    best = max(((len(names & v), team) for (s2, team), v in elsur.items() if s2 == s_), default=(0, None))
    if best[0] >= 3: MAP[(s_, rw)] = best[1]
def find(box_team, player):
    t = tok(player)
    if not t: return None
    sur, f = tuple(t[1:]) if len(t) > 1 else tuple(t), t[0][:1]
    for (bs, bf), v in box_team.items():
        if bs == sur and (bf == f or not bf): return v
    c = [v for (bs, bf), v in box_team.items() if bs and (bs[-1] == t[-1] or set(bs) & set(t[1:]))]
    return c[0] if len(c) == 1 else None
rows = []; why = collections.Counter()
for r in R:
    if not r['cat']: continue
    t = utc_of(r)
    if t is None: why['χωρις ωρα'] += 1; continue
    s_ = season_of(t); team = MAP.get((s_, r['team']))
    if not team: why['ομαδα χωρις αντιστοιχιση'] += 1; continue
    nxt = next(((ts, c) for ts, c in TEAMG.get((s_, team), []) if ts > t), None)
    if not nxt or nxt[0] - t > 72 * 3600: why['χωρις ματς ≤72ω'] += 1; continue
    bt = BOX[(s_, nxt[1])].get(team, {})
    hit = find(bt, r['player'])
    played = bool(hit and hit[0] > 0)
    rh = hit or find(ROSTER.get((s_, team), {}), r['player'])      # ο παικτης δεν ηταν στην αποστολη → ονομα απο το ρόστερ της σεζον
    nm = rh[1] if rh else None
    prev = [m for ts, m in MINS.get((s_, team, nm), []) if ts < nxt[0]][-10:] if nm else []
    rows.append(dict(cat=r['cat'], season=s_, team=team, player=r['player'], game=(s_, nxt[1]), hrs=(nxt[0] - t) / 3600, played=played,
                     in_box=hit is not None, known=rh is not None, mins=hit[0] if hit else 0.0, avg=(st.mean(prev) if prev else None), t=t))
# μια εγγραφη ανα (παικτη, ματς): η ΤΕΛΕΥΤΑΙΑ ειδηση πριν το ματς
last = {}
for x in sorted(rows, key=lambda x: x['t']): last[(x['player'], x['game'])] = x
E = list(last.values())
EVER = {}
for x in rows:
    if x['cat'] == 'ΑΜΦΙΒΟΛΟΣ' and (x['player'], x['game']) not in EVER: EVER[(x['player'], x['game'])] = x
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
P(f'Ειδησεις με κατηγορια: {sum(1 for r in R if r["cat"])} · συνδεθηκαν με επομενο ματς ≤72ω: {len(rows)} · αγνοηθηκαν: ' + ' · '.join(f'{k} {v}' for k, v in why.items()))
P(f'Μοναδικα (παικτης, ματς) με την ΤΕΛΕΥΤΑΙΑ ειδηση πριν το ματς: {len(E)} · αντιστοιχιστηκαν κωδικοι ομαδων: {len(MAP)}')
oos = [x for x in E if x['cat'] == 'ΕΚΤΟΣ']
P(f'ΕΛΕΓΧΟΣ ΩΡΑΣ: «ΕΚΤΟΣ» που τελικα ΕΠΑΙΞΑΝ: {100 * sum(x["played"] for x in oos) / max(1, len(oos)):.1f}% (n {len(oos)}) — πρεπει να ειναι πολυ μικρο· «ΠΑΙΖΕΙ» που επαιξαν: '
  f'{100 * sum(x["played"] for x in E if x["cat"] == "ΠΑΙΖΕΙ") / max(1, sum(1 for x in E if x["cat"] == "ΠΑΙΖΕΙ")):.1f}%')
P(f'  ονομα που δεν βρεθηκε ουτε στο ρόστερ της σεζον: {100 * sum(not x["known"] for x in E) / len(E):.1f}% · δεν ηταν στην αποστολη του ματς: {100 * sum(not x["in_box"] for x in E) / len(E):.1f}% (μετρανε ως «δεν επαιξε»)')
def role(x):
    a = x['avg']
    return 'χωρις φετινα' if a is None else ('βασικος ≥20′' if a >= 20 else ('ρολιστας 10-20′' if a >= 10 else 'λιγα λεπτα <10′'))
def hb(h): return '<6ω' if h < 6 else ('6-24ω' if h < 24 else '24-72ω')
P(''); P('ΠΟΣΟΣΤΟ ΠΟΥ ΕΠΑΙΞΕ ΤΕΛΙΚΑ (τελευταια ειδηση πριν το ματς):')
ORDER = ['ΕΚΤΟΣ', 'ΜΑΛΛΟΝ ΕΚΤΟΣ', 'ΑΜΦΙΒΟΛΟΣ', 'ΜΑΛΛΟΝ ΠΑΙΖΕΙ', 'ΠΑΙΖΕΙ']
for c in ORDER:
    xs = [x for x in E if x['cat'] == c]
    if not xs: continue
    pl = [x for x in xs if x['played']]
    P(f'  {c:14s} n {len(xs):4d} · ΕΠΑΙΞΑΝ {100 * len(pl) / len(xs):5.1f}% · λεπτα οσων επαιξαν {st.mean([x["mins"] for x in pl]) if pl else 0:4.1f}′ '
      f'(μ.ο. πριν {st.mean([x["avg"] for x in pl if x["avg"]]) if [x for x in pl if x["avg"]] else 0:4.1f}′)')
for dim, f in (('ΡΟΛΟ', role), ('ΩΡΕΣ ΠΡΙΝ ΤΟ ΜΑΤΣ', lambda x: hb(x['hrs'])), ('ΣΕΖΟΝ', lambda x: x['season'])):
    P(''); P(f'ΑΝΑ {dim} (επαιξαν % · n):')
    keys = sorted({f(x) for x in E})
    for c in ['ΜΑΛΛΟΝ ΕΚΤΟΣ', 'ΑΜΦΙΒΟΛΟΣ', 'ΜΑΛΛΟΝ ΠΑΙΖΕΙ']:
        cells = []
        for k in keys:
            xs = [x for x in E if x['cat'] == c and f(x) == k]
            if len(xs) >= 8: cells.append(f'{k}: {100 * sum(x["played"] for x in xs) / len(xs):.0f}% ({len(xs)})')
        P(f'  {c:14s} ' + ' · '.join(cells))
P(''); P('ΟΣΟΙ ΗΤΑΝ ΚΑΠΟΙΑ ΣΤΙΓΜΗ ΑΜΦΙΒΟΛΟΙ (ως 72ω πριν), ανεξαρτητα απο την τελευταια ειδηση:')
EV = [dict(x, played=last[k]['played'], final=last[k]['cat']) for k, x in EVER.items()]
P(f'  n {len(EV)} · ΕΠΑΙΞΑΝ {100 * sum(x["played"] for x in EV) / max(1, len(EV)):.1f}% · τελευταια ειδηση: ' + ' · '.join(f'{k} {v}' for k, v in collections.Counter(x['final'] for x in EV).most_common()))
for lab, f in (('ρολος', role), ('ωρες', lambda x: hb(x['hrs'])), ('σεζον', lambda x: x['season'])):
    P(f'  ανα {lab}: ' + ' · '.join(f'{k}: {100 * sum(x["played"] for x in EV if f(x) == k) / n:.0f}% ({n})' for k in sorted({f(x) for x in EV}) for n in [sum(1 for x in EV if f(x) == k)] if n >= 8))
P(''); P('ΑΜΦΙΒΟΛΟΙ: ΒΓΗΚΕ ΤΕΛΙΚΗ ΕΙΔΗΣΗ; (τελευταια ειδηση πριν το ματς, μετα την πρωτη «αμφιβολος»)')
for fin in ('ΠΑΙΖΕΙ', 'ΕΚΤΟΣ', 'ΜΑΛΛΟΝ ΕΚΤΟΣ', 'ΑΜΦΙΒΟΛΟΣ'):
    xs = [(EVER[k], last[k]) for k in EVER if last[k]['cat'] == fin]
    if not xs: continue
    hr = sorted(l['hrs'] for _, l in xs)
    P(f'  τελικη «{fin}»: {len(xs)} ({100 * len(xs) / len(EVER):.0f}%) · επαιξαν {100 * sum(l["played"] for _, l in xs) / len(xs):.0f}% · '
      f'ωρες πριν το ματς που βγηκε: διαμεσος {hr[len(hr) // 2]:.1f}ω (25% {hr[len(hr) // 4]:.1f} · 75% {hr[3 * len(hr) // 4]:.1f}) · <3ω {100 * sum(h < 3 for h in hr) / len(hr):.0f}%')
P(''); P('ΠΑΡΑΔΕΙΓΜΑΤΑ ΑΜΦΙΒΟΛΩΝ (10 τυχαια):')
random.seed(3)
for x in random.sample([x for x in E if x['cat'] == 'ΑΜΦΙΒΟΛΟΣ'], 10):
    P(f"  {x['season']} {x['team']} {x['player']} · ειδηση {x['hrs']:.0f}ω πριν · {'ΕΠΑΙΞΕ ' + format(x['mins'], '.0f') + '′' if x['played'] else 'ΔΕΝ επαιξε'} · μ.ο. {x['avg'] or 0:.0f}′")
open('el_gtd_study_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
