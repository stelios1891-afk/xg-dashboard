# -*- coding: utf-8 -*-
"""el_clv_now.py — EUROLEAGUE: CLV ΩΣ ΤΩΡΑ (16/10/2026, Στελιος «το clv μεχρι στιγμης, μαζι με τα σημερινα, με τις τωρινες τιμες»).
Επισημα picks (el_clv_bets.jsonl: πρωτη ΜΗ-καταγραφη εγγραφη ανα ματς/αγορα/πλευρα). «Κλεισιμο» = τελευταια τιμη Pinnacle πριν το τζαμπολ·
για ματς που δεν αρχισαν ακομα = η ΤΩΡΙΝΗ τιμη. Ιδιος τροπος με bk_live_review_1510:
  CLV ποντοι = ποσους ποντους μετακινηθηκε η δικαιη αγορα (με αποδοσεις, κανονικη κατανομη σ του live μοντελου) ΠΡΟΣ την πλευρα μας.
  CLV % = αναμενομενη αποδοση του δικου μας εισιτηριου (γραμμη/τιμη που πηραμε) στη δικαιη πιθανοτητα του κλεισιματος.
Εξοδος: el_clv_now_out.txt"""
import sys, json, collections, datetime as dt, statistics as st, math
sys.stdout.reconfigure(encoding='utf-8')
src = open('bk_live_review_1510.py', encoding='utf-8').read()
src = src[:src.index('# ============================ ΦΟΡΤΩΣΗ')]
g = {'__name__': 'x'}
exec(src, g)
ts, probs, fair, market_series, snap, ROOT = (g[k] for k in ('ts', 'probs', 'fair', 'market_series', 'snap', 'ROOT'))
cur = json.load(open(ROOT + 'el_projections.json', encoding='utf-8'))
SM, STT = cur['sigma_margin'], cur['sigma_total']
GAMES = {str(x['code']): x for x in cur['games']}
SER = market_series('el')
NOW = dt.datetime.now(dt.timezone.utc)
rows = [json.loads(l) for l in open(ROOT + 'el_clv_bets.jsonl', encoding='utf-8') if l.strip()]
def dir_of(p):
    return str(p['side']) if p['mkt'] == 'hcap' else str(p.get('bet') or '').split(' ')[0]
grp = collections.defaultdict(list)
for r in rows:
    grp[f"{r['code']}|{r['mkt']}|{dir_of(r)}"].append(r)
out = []
def P(s=''):
    print(s); out.append(str(s))
recs = []
for k, rs in grp.items():
    rs.sort(key=lambda r: r['seen'])
    nonp = [r for r in rs if not r.get('paper')]
    kindp = 'pick' if nonp else 'paper'
    r = nonp[0] if nonp else rs[0]
    code = str(r['code']); gm = GAMES.get(code)
    tip = ts(gm['utc']) if gm else ts(r['when'] + ('Z' if len(r['when']) == 16 else ''))
    ser = SER.get(code, [])
    kind = 1 if r['mkt'] == 'hcap' else 2
    sig = SM if kind == 1 else STT; lo, hi = ((-80, 80) if kind == 1 else (90, 280))
    started = NOW >= tip
    cl = snap(ser, min(tip, NOW + dt.timedelta(minutes=1)), kind)
    atp = snap(ser, ts(r['seen']) + dt.timedelta(minutes=1), kind)
    if not cl or not atp:
        continue
    role = (('ΦΑΒΟΡΙ' if float(r['hcap']) < 0 else 'ΑΟΥΤΣΑΪΝΤΕΡ' if float(r['hcap']) > 0 else 'PK') if kind == 1
            else ('OVER' if str(r.get('bet', '')).startswith('Over') else 'UNDER'))
    d = (1 if int(r['side']) == 1 else -1) if kind == 1 else (1 if role == 'OVER' else -1)
    m_cl = fair(-cl[0] if kind == 1 else cl[0], cl[1], cl[2], sig, lo, hi)
    m_at = fair(-atp[0] if kind == 1 else atp[0], atp[1], atp[2], sig, lo, hi)
    L = float(r['hcap'])
    if kind == 1:
        w, p = probs(m_cl * d, -L, sig)
    else:
        w, p = probs(m_cl, L, sig) if d == 1 else probs(-m_cl, -L, sig)
    # ιδιο μετρο με το Pick History: η ΤΙΜΗ μας / τιμη κλεισιματος (με το περιθωριο) της ιδιας πλευρας, μεταφρασμενη στη γραμμη μας
    if kind == 1:
        cL, co = (cl[0], cl[1]) if d == 1 else (-cl[0], cl[2]); wc, pc = probs(m_cl * d, -cL, sig)
    else:
        cL, co = cl[0], (cl[1] if d == 1 else cl[2]); wc, pc = probs(m_cl, cL, sig) if d == 1 else probs(-m_cl, -cL, sig)
    eq = co * ((1 - p) / w) / ((1 - pc) / wc) if w > 0 and wc > 0 else float('nan')
    ph = float(r['odds']) / eq - 1
    res = None
    if gm and gm.get('hs') is not None and gm.get('as_') is not None:
        mar = gm['hs'] - gm['as_']; tot = gm['hs'] + gm['as_']
        x = ((mar if d == 1 else -mar) + L) if kind == 1 else ((tot - L) * d)
        res = 0.0 if abs(x) < 1e-9 else ((float(r['odds']) - 1) if x > 0 else -1.0)
    recs.append(dict(ph=ph, kind=kindp, mkt=('ΧΑΝΤΙΚΑΠ' if kind == 1 else 'ΣΥΝΟΛΑ'), role=role, clv=d * (m_cl - m_at),
                     ev=w * float(r['odds']) + p - 1, res=res, st=('παιχτηκε' if res is not None else ('σε εξελιξη' if started else 'ΑΝΟΙΧΤΟ (τωρινη τιμη)')),
                     lab=f"{tip:%d/%m} {r['home'][:18]}–{r['away'][:18]} · {('%+g' % L) if kind == 1 else r.get('bet')} @{r['odds']}",
                     now=f"{('%+g' % (cl[0] if d == 1 else -cl[0])) if kind == 1 else cl[0]} @{(cl[1] if d == 1 else cl[2]) if kind == 1 else (cl[1] if d == 1 else cl[2])}",
                     paper=r.get('paper')))
def line(lab, R):
    if not R:
        P(f'  {lab:22s} —'); return
    c = [x['clv'] for x in R]; e = [x['ev'] for x in R]; rr = [x['res'] for x in R if x['res'] is not None]
    pos = sum(1 for x in c if x > 0.05); neg = sum(1 for x in c if x < -0.05)
    se = st.pstdev(c) / math.sqrt(len(c)) if len(c) > 1 else float('nan')
    P(f"  {lab:22s} picks {len(R):3d} · CLV {st.mean(c):+.2f} π. (±{se:.2f}) · προς εμας {pos} / κοντρα {neg} / ιδιο {len(c)-pos-neg} · "
      f"CLV % {100*st.mean(e):+5.1f}% (οπως Pick History {100*st.mean([x['ph'] for x in R]):+5.1f}%) · ROI παιγμενων {('%+.1f%% (%d)' % (100*st.mean(rr), len(rr))) if rr else '—'}")
P(f"EUROLEAGUE · CLV ως τωρα ({NOW + dt.timedelta(hours=3):%d/%m %H:%M} ωρα Ελλαδας) · κλεισιμο Pinnacle, τα ανοιχτα με την ΤΩΡΙΝΗ τιμη")
P('CLV π. = ποντοι που κινηθηκε η δικαιη αγορα προς εμας απο τη στιγμη του pick · CLV % = αξια του εισιτηριου μας στην τιμη κλεισιματος/τωρα')
OF = [x for x in recs if x['kind'] == 'pick']
P(''); P('=== ΕΠΙΣΗΜΑ PICKS ===')
for lab, f in (('ΦΑΒΟΡΙ', lambda x: x['role'] == 'ΦΑΒΟΡΙ'), ('ΑΟΥΤΣΑΪΝΤΕΡ', lambda x: x['role'] == 'ΑΟΥΤΣΑΪΝΤΕΡ'),
               ('ΧΑΝΤΙΚΑΠ ολα', lambda x: x['mkt'] == 'ΧΑΝΤΙΚΑΠ'), ('OVER', lambda x: x['role'] == 'OVER'),
               ('UNDER', lambda x: x['role'] == 'UNDER'), ('ΣΥΝΟΛΑ ολα', lambda x: x['mkt'] == 'ΣΥΝΟΛΑ'), ('ΟΛΑ', lambda x: True)):
    line(lab, [x for x in OF if f(x)])
P(''); P('  μονο τα παιγμενα:')
for lab, f in (('ΧΑΝΤΙΚΑΠ', lambda x: x['mkt'] == 'ΧΑΝΤΙΚΑΠ'), ('ΣΥΝΟΛΑ', lambda x: x['mkt'] == 'ΣΥΝΟΛΑ')):
    line(lab, [x for x in OF if f(x) and x['res'] is not None])
P(''); P('=== ΚΑΤΑΓΡΑΦΕΣ (δεν παιζονται: τελευταιο 2ωρο / κοντρα ≥1.5) ===')
line('ολες', [x for x in recs if x['kind'] == 'paper'])
P(''); P('=== ΑΝΟΙΧΤΑ / ΣΗΜΕΡΙΝΑ (τωρινη τιμη) ===')
for x in [x for x in OF if x['res'] is None]:
    P(f"  {x['lab']:62s} → τωρα {x['now']:14s} · CLV {x['clv']:+.1f} π. · {100*x['ev']:+.1f}% (PH {100*x['ph']:+.1f}%) · {x['role']} · {x['st']}")
open('el_clv_now_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
