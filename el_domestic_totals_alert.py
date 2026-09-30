# -*- coding: utf-8 -*-
"""el_domestic_totals_alert.py — ΕΓΧΩΡΙΑ ΣΤΑ ΣΥΝΟΛΑ, κριση στην ΤΙΜΗ ΠΟΥ ΠΑΙΖΟΥΜΕ (1/10/2026, Στελιος: «κοιτας παλι στο κλεισιμο της
Pinnacle — δες στο ανοιγμα ~1 μερα πριν και τι picks αλλαζει»).
Προσομοιωση alert οπως el_alert_types (Crown, καθε αλλαγη τιμης, πρωτη τιμη με edge ≥8%, κανονας καταγραφης «κοντρα ≥1.5π»).
LIVE = συνολο live (v2+Κ2+προετοιμασια) · ΝΕΟ = LIVE + .25·(ΔT_γηπ + ΔT_φιλ) απο τον 11ο αγωνα (el_domestic_totals_test, Α σταθερο).
Αναφορα αγων 11+: ROI στην τιμη του alert, μοναδες, over/under, x/5 · picks που ΚΟΒΕΙ / ΠΡΟΣΘΕΤΕΙ / κοινα · μονο οσα βγαινουν στο ανοιγμα.
Εξοδος: el_domestic_totals_alert_out.txt"""
import sys, pickle
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
X = {}
exec(open('el_domestic_totals_test.py', encoding='utf-8').read().split('base = np.array(C2, float)')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), X)
DD, IDXd, SIG, RNDd = X['D'], X['IDX'], X['SIG'], X['RND']
SIGK = {(DD.season.values[i], DD.home.values[i], DD.away.values[i], str(pd.Timestamp(DD.t.values[i]))[:16]): (float(SIG[j]), float(RNDd[j])) for j, i in enumerate(IDXd)}
NS = {}
exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), NS)
REC, PR, key, pick, settle, D, SE5 = (NS[k] for k in ('REC', 'PR', 'key', 'pick', 'settle', 'D', 'SE5'))
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
def first(m, r, p):
    ser, tip = r['ser'], r['tip']; o = ser[0]
    for k_, row in enumerate(ser):
        if row[0] >= tip: break
        side, e, od = pick(23, m, row)
        if e < 0.08: continue
        if k_ > 0 and -(row[1] - o[1]) * side >= 1.5: return None          # καταγραφη
        return dict(side='over' if side == 1 else 'under', pnl=settle(23, p, side, row, od), open=(k_ == 0), hrs=(tip - row[0]) / 3600)
    return None
rows = []; miss = 0
for p, r in REC[23].items():
    k = key(p); m0 = PR.get(k, {}).get('t_new')
    if m0 is None or not np.isfinite(m0): continue
    if k not in SIGK: miss += 1; continue
    sig, rnd = SIGK[k]
    if rnd < 11: continue
    m1 = m0 + 0.25 * sig
    a, b = first(m0, r, p), first(m1, r, p)
    rows.append(dict(sea=D.season.values[p], sig=sig, a=a, b=b))
P(f'αγων 11+: {len(rows)} ματς με σειρα Crown (χωρις σημα: {miss})')
def summ(L):
    if not L: return '—'
    z = pd.DataFrame(L); pos = sum(1 for s in SE5 if (z.sea == s).any() and z[z.sea == s].pnl.mean() > 0)
    return f'{z.pnl.mean()*100:+6.1f}% ({len(z):3d}, {z.pnl.sum():+5.1f} μον.) {pos}/5'
for scope, f in (('ΟΛΑ τα alerts', lambda x: True), ('μονο οσα βγαινουν ΣΤΟ ΑΝΟΙΓΜΑ', lambda x: x['open'])):
    P(''); P(f'=== {scope} ===')
    for nm, fld in (('LIVE', 'a'), ('ΝΕΟ (με εγχωρια)', 'b')):
        L = [dict(x[fld], sea=x['sea']) for x in rows if x[fld] and f(x[fld])]
        P(f'  {nm:18s} ολα {summ(L)} · over {summ([l for l in L if l["side"] == "over"])} · under {summ([l for l in L if l["side"] == "under"])}')
    G = {}
    for x in rows:
        a = x['a'] if x['a'] and f(x['a']) else None; b = x['b'] if x['b'] and f(x['b']) else None
        if a and b and a['side'] == b['side']: G.setdefault(('ΚΟΙΝΑ', a['side']), []).append(dict(b, sea=x['sea'], sg=x['sig'] * (1 if a['side'] == 'over' else -1)))
        else:
            if a: G.setdefault(('τα ΚΟΒΕΙ', a['side']), []).append(dict(a, sea=x['sea'], sg=x['sig'] * (1 if a['side'] == 'over' else -1)))
            if b: G.setdefault(('τα ΠΡΟΣΘΕΤΕΙ', b['side']), []).append(dict(b, sea=x['sea'], sg=x['sig'] * (1 if b['side'] == 'over' else -1)))
    for grp in ('ΚΟΙΝΑ', 'τα ΚΟΒΕΙ', 'τα ΠΡΟΣΘΕΤΕΙ'):
        for sd in ('over', 'under'):
            L = G.get((grp, sd), [])
            if L: P(f'    {grp:13s} {sd:5s}: {summ(L)} · εγχωριο σημα προς την πλευρα {np.mean([l["sg"] for l in L]):+.1f} π.')
open('el_domestic_totals_alert_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ---- ΓΙΑΤΙ: τα picks που γεννιουνται ΜΕΤΑ το ανοιγμα ----
P(''); P('=== ΜΕΤΑ ΤΟ ΑΝΟΙΓΜΑ: τι κανει το ΝΕΟ στα ματς οπου το LIVE βγαζει pick αργοτερα (και αντιστροφα) ===')
def cls(x, y):
    if y is None: return 'κανενα pick'
    if y['side'] != x['side']: return 'ΑΝΤΙΘΕΤΗ πλευρα'
    return 'ιδια πλευρα ΣΤΟ ΑΝΟΙΓΜΑ' if y['open'] else 'ιδια πλευρα, κι αυτο αργοτερα'
for nm, f1, f2 in (('LIVE αργοτερα → ΝΕΟ:', 'a', 'b'), ('ΝΕΟ αργοτερα → LIVE:', 'b', 'a')):
    P(f'  {nm}')
    G = {}
    for x in rows:
        a = x[f1]
        if a and not a['open']: G.setdefault(cls(a, x[f2]), []).append((a, x[f2], x['sea']))
    for c, L in sorted(G.items(), key=lambda kv: -len(kv[1])):
        r1 = [a['pnl'] for a, b, s in L]; r2 = [b['pnl'] for a, b, s in L if b]
        P(f'    {c:30s} {len(L):3d} · {nm[:4]} στην αργοτερη τιμη {np.mean(r1)*100:+6.1f}% ({np.sum(r1):+5.1f} μον.)'
          + (f' · το αλλο {np.mean(r2)*100:+6.1f}% ({np.sum(r2):+5.1f} μον.)' if r2 else ''))
open('el_domestic_totals_alert_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
