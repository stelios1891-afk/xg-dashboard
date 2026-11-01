# -*- coding: utf-8 -*-
"""el_steam_pinnacle.py — 17/10/2026 (Στελιος: «ξεχωρισε τα ματς με τις μεγαλες κινησεις και δες την τιμη τους στην Pinnacle»).
Ευρωλιγκα 2020-26. Γεγονοτα = el_steam_events.json (πρωτη κινηση ≥1.5 π. σε 60′ ανα ματς/αγορα/βιβλιο: Crown, Bet365, SBOBET, William Hill).
Pinnacle (TOA historical): −60′ (πριν την κινηση), +5′ (αμεσως μετα), +60′ (toa_el_steam.jsonl) και κλεισιμο 5′ πριν (toa_el_closing.jsonl).
Δικαιη τιμη Pinnacle σε ποντους (ιδια μεθοδος: γραμμη + σ·Φ⁻¹(p) χωρις περιθωριο). Ταιριασμα ματς: τζαμπολ ±25′ + ομοιοτητα ονοματων.
ΕΡΩΤΗΣΕΙΣ: (1) ειχε ΗΔΗ κινηθει η Pinnacle πριν την κινηση του βιβλιου; (2) ακολουθησε μετα; (3) ποσο απο την κινηση εχει η Pinnacle στο κλεισιμο;
(4) ROI αν παιζες στην PINNACLE στο +5′ / +60′ / κλεισιμο. Εξοδος: el_steam_pinnacle_out.txt"""
import sys, json, difflib, re, glob
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
IQ = NormalDist().inv_cdf
SIGM = {'spreads': 11.5, 'totals': 16.7}
BKN = {3: 'Crown', 8: 'Bet365', 31: 'SBOBET', 10: 'William Hill'}

def norm(s):
    return re.sub(r'\b(bc|kk|bk|fc|pbc|sad|basketball|basket|ae|ac)\b', ' ', s.lower().replace('-', ' ')).strip()

def fair(game, mk):
    for b in game.get('bookmakers', []):
        if b['key'] != 'pinnacle': continue
        for m in b['markets']:
            if m['key'] != mk: continue
            o = m['outcomes']
            if mk == 'spreads':
                h = next((x for x in o if x['name'] == game['home']), None); a = next((x for x in o if x['name'] == game['away']), None)
                if not h or not a: return None
                L, d1, d2 = -h['point'], h['price'], a['price']
            else:
                ov = next((x for x in o if x['name'] == 'Over'), None); un = next((x for x in o if x['name'] == 'Under'), None)
                if not ov or not un: return None
                L, d1, d2 = ov['point'], ov['price'], un['price']
            p1 = (1 / d1) / (1 / d1 + 1 / d2)
            return dict(L=L, d1=d1, d2=d2, F=L + SIGM[mk] * IQ(min(max(p1, 1e-4), 1 - 1e-4)), upd=m.get('last_update'))
    return None

def pick(cands, home, away):
    best, bs = None, 0
    for g in cands:
        s = difflib.SequenceMatcher(None, norm(g['home']), norm(home)).ratio() + difflib.SequenceMatcher(None, norm(g['away']), norm(away)).ratio()
        if s > bs: best, bs = g, s
    return best if bs >= 0.9 else None

def ts_(s): return pd.Timestamp(s).timestamp()

def settle(y, L, d, side):
    v = side * (y - L); return 0.0 if v == 0 else (d - 1 if v > 0 else -1.0)

EV = json.load(open('el_steam_events.json', encoding='utf-8'))
SN = {}
for l in open('toa_el_steam.jsonl', encoding='utf-8'):
    r = json.loads(l); SN.setdefault(r['slot'], []).append(r)
CL = []
for l in open('toa_el_closing.jsonl', encoding='utf-8'):
    r = json.loads(l); r['ct'] = ts_(r['commence']); CL.append(r)
SCH = {}
for f in glob.glob('nowgoal_el/sched_*.json'):
    for g in json.load(open(f, encoding='utf-8')): SCH[g['ngid']] = g
R = []
for e in EV:
    g = SCH.get(e['ngid'])
    if not g or g.get('hs') is None: continue
    y = g['hs'] - g['as_'] if e['mk'] == 'spreads' else g['hs'] + g['as_']; sd = 1 if e['dF'] > 0 else -1
    P = {}
    for lab, s in zip(('πριν', '+5′', '+60′'), (e['ts'] - 3600, e['ts'] + 300, e['ts'] + 3600)):
        c = [x for x in SN.get(f"{e['mk']}|{s // 300}", []) if abs(ts_(x['commence']) - e['tip']) <= 1500]
        m = pick(c, e['home'], e['away']) if c else None
        P[lab] = fair(m, e['mk']) if m else None
    c = [x for x in CL if abs(x['ct'] - e['tip']) <= 1500]; m = pick(c, e['home'], e['away']) if c else None
    P['κλεισιμο'] = fair(m, e['mk']) if m else None
    if not (P['πριν'] or P['+5′']): continue
    rec = dict(sea=e['sea'], mk=e['mk'], bk=BKN[e['bk']], mv=abs(e['dF']), side=sd, hrs=(e['tip'] - e['ts']) / 3600, prio=e['prio'])
    b = P['πριν']
    for lab in ('+5′', '+60′', 'κλεισιμο'):
        q = P[lab]
        rec['pin_' + lab] = settle(y, q['L'], q['d1'] if sd == 1 else q['d2'], sd) if q else np.nan
        rec['mvpin_' + lab] = (sd * (q['F'] - b['F']) / abs(e['dF'])) if (q and b) else np.nan
    rec['clv_pin'] = sd * (P['κλεισιμο']['F'] - P['+5′']['F']) if (P['κλεισιμο'] and P['+5′']) else np.nan
    rec['has_before'] = b is not None
    q5 = P['+5′']
    rec['age5'] = ((e['ts'] + 300 - ts_(q5['upd'])) / 60) if (q5 and q5.get('upd')) else np.nan   # ποσα λεπτα «παλια» η τιμη Pinnacle στο +5′
    R.append(rec)
D = pd.DataFrame(R)
print(f'γεγονοτα με Pinnacle: {len(D)} απο {len(EV)} · με «πριν» {int(D.has_before.sum())} · με +5′ {int(D["pin_+5′"].notna().sum())} · '
      f'με κλεισιμο {int(D["pin_κλεισιμο"].notna().sum())}')

def roi(v):
    v = v.dropna(); return f'{100 * v.mean():+6.1f}% ({len(v):3d})' if len(v) >= 12 else f'{"—":>7s} ({len(v):3d})'
def pct(v):
    v = v.dropna(); return f'{100 * v.mean():5.0f}%' if len(v) >= 12 else '   —'
def pos(y, col):
    s = y.groupby('sea')[col].mean()[y.groupby('sea')[col].count() >= 5]; return f'{int((s > 0).sum())}/{len(s)}'
HDR = (f'   {"":26s} │ {"Pinnacle πηγε προς ιδια μερια (% της κινησης)":^44s} │ {"ROI στην PINNACLE":^44s} │ {"CLV":>6s}\n'
       f'   {"":26s} │ {"στο +5′":>13s} {"στο +60′":>13s} {"κλεισιμο":>13s}   │ {"+5′":>14s} {"+60′":>14s} {"κλεισιμο":>14s} │ {"Pin":>6s}')
def row(lab, y):
    if len(y) < 12: print(f'   {lab:26s} │ λιγα ({len(y)})'); return
    print(f'   {lab:26s} │ {pct(y["mvpin_+5′"]):>13s} {pct(y["mvpin_+60′"]):>13s} {pct(y["mvpin_κλεισιμο"]):>13s}   │ {roi(y["pin_+5′"]):>14s} '
          f'{roi(y["pin_+60′"]):>14s} {roi(y["pin_κλεισιμο"]):>14s} │ {y.clv_pin.mean():+6.2f}  θετ.σεζ(+5′) {pos(y, "pin_+5′")}')
for mk, nm in (('spreads', 'ΧΑΝΤΙΚΑΠ'), ('totals', 'ΣΥΝΟΛΑ')):
    y0 = D[D.mk == mk]
    print(f'\n{"=" * 150}\n{nm} — κινηση ≥1.5 π. σε 60′ σε ενα βιβλιο, τι εκανε η Pinnacle (απο −60′) · ROI = ποντος στην Pinnacle προς τη μερια της κινησης\n{HDR}')
    row('ΟΛΑ', y0)
    for bk in BKN.values(): row(f'  κινηθηκε {bk}', y0[y0.bk == bk])
    for lab, lo, hi in (('  1.5-2 π.', 1.5, 2), ('  2-3 π.', 2, 3), ('  ≥3 π.', 3, 99)): row(lab, y0[(y0.mv >= lo) & (y0.mv < hi)])
    for lab, lo, hi in (('  6-24ω πριν', 6, 99), ('  2-6ω πριν', 2, 6), ('  <2ω πριν', 0, 2)): row(lab, y0[(y0.hrs >= lo) & (y0.hrs < hi)])
    print('   — η Pinnacle ΔΕΝ ειχε κινηθει ακομα (στο +5′ < ¼ της κινησης) —')
    nf = y0[y0['mvpin_+5′'] < 0.25]; row('  ολα', nf)
    for lab, lo, hi in (('  1.5-2 π.', 1.5, 2), ('  ≥2 π.', 2, 99)): row(lab, nf[(nf.mv >= lo) & (nf.mv < hi)])
    for bk in BKN.values(): row(f'  κινηθηκε {bk}', nf[nf.bk == bk])
    print('   — ποσο «φρεσκια» ηταν η τιμη Pinnacle στο +5′ (λεπτα απο την τελευταια ενημερωση της αγορας) —')
    for lab, lo, hi in (('  ενημερωση ≤10′ πριν', -1e9, 10), ('  10-60′ πριν', 10, 60), ('  >60′ πριν', 60, 1e9)): row(lab, y0[(y0.age5 >= lo) & (y0.age5 < hi)])
    print('   — η Pinnacle ειχε ΗΔΗ κινηθει (στο +5′ ≥ ¾) —')
    row('  ολα', y0[y0['mvpin_+5′'] >= 0.75])
D.to_pickle('el_steam_pinnacle.pkl')
