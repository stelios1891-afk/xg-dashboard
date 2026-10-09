"""euro_trace_match.py — 9/10/2026: ΒΗΜΑ-ΒΗΜΑ η live ευρωπαικη προβλεψη για ενα ματς (Στελιος: «Σαλτσμπουργκ−Μιλαν απο την αρχη μεχρι το τελος»).
Χρηση: python euro_trace_match.py "Salzburg" "Milan" — καμια εγγραφη αρχειου."""
import sys, io, json, math, contextlib
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')
HN, AN = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ('Salzburg', 'Milan')
src = open('euro_live_projections.py', encoding='utf-8').read()
src = src[:src.index('# ================================================================ 2627 fixtures')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
g = {'__name__': 'trace'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
eng, side_terms, s_v4, GKEYS, K = g['eng'], g['side_terms'], g['s_v4'], g['GKEYS'], g['K']
HF, GAM, DS = g['HF_LIVE'], g['GAMMA_LG_DEFLATE'], g['EU_DRAW_SCALE']; picks = g['picks']; RHO = g['RHO']
fx = json.load(open('europe_fixtures_2627.json', encoding='utf-8'))
m = next(x for k, l in fx.items() for x in l if x['hname'] == HN and x['aname'] == AN)
d = datetime.fromisoformat(m['utc'].replace('Z', '+00:00')).replace(tzinfo=None)
print(f'ΜΑΤΣ: {HN} – {AN} · {m["utc"]} · Europa League αγων. {m["round"]}\n')
info = {}
for tag, tid, nm in (('h', m['hid'], HN), ('a', m['aid'], AN)):
    st = eng.side_state(int(tid), d); rh = eng.rating_of(st, K)
    SL, XL = eng.ruler(st['lg'], st['sea'], d); att, leak, _, _, srcl = side_terms(eng, st, d, GKEYS)
    w = st['n'] / (st['n'] + K) if st['cur'] and st['prior'] else (1.0 if st['cur'] else 0.0)
    info[tag] = dict(st=st, rh=rh, SL=SL, XL=XL, att=att, leak=leak, w=w, src=srcl)
    f = lambda t: f'σουτ υπερ {t[2]:.1f} / κατα {t[3]:.1f} ανα ματς · xG ανα σουτ υπερ {t[0]:.3f} / κατα {t[1]:.3f}' if t else '—'
    print(f'[{nm}] λιγκα {st["lg"]} σεζον {st["sea"]} · πηγη {srcl} · φετινα εγχωρια ματς {st["n"]}')
    print(f'   ΦΕΤΙΝΑ   : {f(st["cur"])}')
    print(f'   PRIOR    : {f(st["prior"])}   (περσινο πρωταθλημα + περσινα ευρωπαικα με βαρος 2)')
    print(f'   ΜΙΞΗ     : {f(rh)}   (βαρος φετινων {w:.0%} = n/(n+8))')
    print(f'   ΧΑΡΑΚΑΣ λιγκας: σουτ/ματς {SL:.2f} · xG/σουτ {XL:.3f}')
    print(f'   ΣΧΕΤΙΚΗ ΔΥΝΑΜΗ: επιθεση ×{math.exp(att):.2f} του μεσου της λιγκας της · αμυνα (δεχεται) ×{math.exp(leak):.2f}')
    print(f'   ΕΠΙΠΕΔΟ ΛΙΓΚΑΣ (γεφυρες παικτων): s = {s_v4(st["lg"]):+.3f}\n')
h, a = info['h'], info['a']
lXs = math.log(((h['SL'] * a['SL']) ** 0.5) * ((h['XL'] * a['XL']) ** 0.5)); D = s_v4(h['st']['lg']) - s_v4(a['st']['lg'])
x0h = math.exp(lXs + h['att'] + a['leak'] + RHO * D); x0a = math.exp(lXs + a['att'] + h['leak'] - RHO * D)
print(f'ΒΗΜΑ 1 — ουδετερο γηπεδο, μετα τη διαφορα επιπεδου λιγκων (D = {D:+.3f}):  {HN} {x0h:.2f} – {AN} {x0a:.2f} xG')
x1h, x1a = x0h * HF, x0a / HF
print(f'ΒΗΜΑ 2 — εδρα (κοινη για ολη την Ευρωπη ×{HF:.3f}):                       {HN} {x1h:.2f} – {AN} {x1a:.2f}')
c = GAM * D; x2h, x2a = max(x1h - c / 2, .05), max(x1a + c / 2, .05)
print(f'ΒΗΜΑ 3 — «ξεφουσκωμα» μικρης λιγκας (γ={GAM}, μετακινηση {c / 2:+.2f}):        {HN} {x2h:.2f} – {AN} {x2a:.2f}')
dist = picks.gd_dist(x2h, x2a); p1 = sum(p for k_, p in dist.items() if k_ > 0); px = dist[0]; p2 = 1 - p1 - px
pxn = DS * px; f_ = (1 - pxn) / (1 - px); p1n, p2n = p1 * f_, p2 * f_
print(f'ΒΗΜΑ 4 — πιθανοτητες (Poisson) και ισοπαλιες ×{DS}:  1 {p1n:.1%} · Χ {pxn:.1%} · 2 {p2n:.1%}  → δικαιες αποδοσεις {1 / p1n:.2f} / {1 / pxn:.2f} / {1 / p2n:.2f}')
dsc = {k_: (v * DS if k_ == 0 else v * f_) for k_, v in dist.items()}
for L in (-0.5, -0.75, -1.0, -1.25):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; w = q = 0
    for P in parts:
        w += sum(v for k_, v in dsc.items() if -k_ + P > .01) / len(parts); q += sum(v for k_, v in dsc.items() if abs(-k_ + P) < .01) / len(parts)
    print(f'         {AN} {L:+.2f}: καλυψη {w:.1%} · επιστροφη {q:.1%} → δικαιη αποδοση {(1 - q) / w:.2f}')
try:
    od = json.load(open('euro_odds_latest.json', encoding='utf-8'))
    mk = (od.get('matches') or od).get(str(m['mid'])) if isinstance(od, dict) else None
    print(f'\nΑΓΟΡΑ (τελευταια σαρωση): {json.dumps(mk, ensure_ascii=False)[:400] if mk else "δεν υπαρχουν ακομα τιμες για το ματς"}')
except Exception as e:
    print('αγορα: —', e)
