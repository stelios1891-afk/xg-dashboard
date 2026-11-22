# -*- coding: utf-8 -*-
"""el_coach_change_test.py — ΑΛΛΑΓΗ ΠΡΟΠΟΝΗΤΗ μεσα στη σεζον, Ευρωλιγκα (1/10/2026, Στελιος «τρεξε τον προπονητη»).
Αλλαγες: el_people.json (επισημο ρoστερ, τυπος 'E' = πρωτος προπονητης) με εναρξη μεσα στη σεζον· αλλαγες της ιδιας ομαδας σε ≤14 μερες
  (υπηρεσιακος → μονιμος) = ΜΙΑ αλλαγη, ημερομηνια = η πρωτη.
Για καθε αλλαγη: ματς της ομαδας ΠΡΙΝ (τελευταια 5) και ΜΕΤΑ (1-3, 4-6, 7-10, 11-20), απο τη ματια της ΟΜΑΔΑΣ:
  διαφορα − μοντελο (live μοντελο E2021-25· παλιο v1 για 2017-25), διαφορα − αγορα (Crown ανοιγμα/κλεισιμο, E2021-25), συνολο − μοντελο/αγορα.
  Επισης: τα picks μας (alert Crown, χαντικαπ) σε ματς 1-10 μετα την αλλαγη — υπερ ή κατα της ομαδας.
ΠΡΟ-ΔΗΛΩΜΕΝΟ: μονο μεγαλο & σταθερο αποτελεσμα γινεται κανονας (|t| ≥ 2 vs μοντελο ΚΑΙ ιδια φορα στις περισσοτερες σεζον)· αλλιως σημειωση.
Εξοδος: el_coach_change_test_out.txt"""
import sys, json, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), NS)
D, REC, PR, key, pick, settle, SE5 = (NS[k] for k in ('D', 'REC', 'PR', 'key', 'pick', 'settle', 'SE5'))
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
PP = json.load(open('el_people.json', encoding='utf-8')); S = json.load(open('el_sched.json', encoding='utf-8'))
OLD = pd.read_csv('el_preds_all.csv').set_index('key')
EV = []
for k, L in PP.items():
    s, team = k.split('_'); sch = S.get(s, [])
    if not sch or s not in [f'E{y}' for y in range(2017, 2026)]: continue
    d0 = min(x['utc'][:10] for x in sch); d1 = max(x['utc'][:10] for x in sch)
    ds = sorted(p['start'] for p in L if p['type'] == 'E' and d0 < p['start'] <= d1)
    grp = []
    for d in ds:
        if grp and (pd.Timestamp(d) - pd.Timestamp(grp[-1][-1])).days <= 14: grp[-1].append(d)
        else: grp.append([d])
    for g in grp: EV.append((s, team, g[0], [p['name'] for p in L if p['type'] == 'E' and p['start'] == g[-1]][0]))
P(f'αλλαγες προπονητη μεσα στη σεζον (2017-25): {len(EV)} · απο αυτες E2021-25: {sum(1 for e in EV if e[0] in SE5)}')
# ματς ομαδας με δεικτη ως προς την αλλαγη
MK = {}
for p in REC[21]:
    if p in REC[23]:
        MK[p] = (REC[21][p]['ser'][0][1], REC[21][p]['ser'][-1][1], REC[23][p]['ser'][0][1], REC[23][p]['ser'][-1][1])
rows = []
for s, team, d, nm in EV:
    idx = [i for i in range(len(D)) if D.season.values[i] == s and team in (D.home.values[i], D.away.values[i])]
    idx.sort(key=lambda i: D.t.values[i])
    tev = pd.Timestamp(d, tz='UTC')
    pre = [i for i in idx if pd.Timestamp(D.t.values[i]).tz_localize('UTC') < tev] if pd.Timestamp(D.t.values[0]).tzinfo is None else [i for i in idx if pd.Timestamp(D.t.values[i]) < tev]
    post = [i for i in idx if i not in pre]
    for rel, i in [(-(len(pre) - j), i) for j, i in enumerate(pre)][-5:] + [(j + 1, i) for j, i in enumerate(post)][:20]:
        sg = 1 if D.home.values[i] == team else -1
        mar = (D.hs.values[i] - D.as_.values[i]); tot = D.hs.values[i] + D.as_.values[i]
        pr = PR.get(key(i), {}); kk = D.key.values[i]
        r = dict(ev=f'{s}_{team}', season=s, rel=rel, phase=D.phase.values[i],
                 r_old=(mar - OLD.m_model.get(kk, np.nan)) * sg if kk in OLD.index else np.nan,
                 r_mod=(mar - pr.get('h_new', np.nan)) * sg, t_mod=tot - pr.get('t_new', np.nan))
        if i in MK:
            mo, mc, to, tc = MK[i]; r.update(r_mo=(mar - mo) * sg, r_mc=(mar - mc) * sg, t_mc=tot - tc, mv=(mc - mo) * sg)
        rows.append(r)
R = pd.DataFrame(rows)
def win(lab, m):
    x = R[m]
    cells = []
    for c, nm in (('r_old', 'vs παλιο μοντ.(2017-25)'), ('r_mod', 'vs live μοντ.'), ('r_mc', 'vs αγορα κλεισ.'), ('r_mo', 'vs ανοιγμα'), ('t_mod', 'ΣΥΝΟΛΟ vs μοντ.'), ('t_mc', 'ΣΥΝΟΛΟ vs αγορα'), ('mv', 'αγορα κινηθηκε')):
        v = x[c].dropna() if c in x else pd.Series(dtype=float)
        if len(v) >= 5: cells.append(f'{nm} {v.mean():+.2f}' + (f' (t {v.mean()/(v.std()/math.sqrt(len(v))):+.1f}, n {len(v)})' if c != 'mv' else ''))
    P(f'  {lab:16s} ' + ' · '.join(cells))
P(''); P('=== ΑΠΟ ΤΗ ΜΑΤΙΑ ΤΗΣ ΟΜΑΔΑΣ ΠΟΥ ΑΛΛΑΞΕ ΠΡΟΠΟΝΗΤΗ (+ = καλυτερα απ οσο περιμεναν) ===')
win('5 ματς ΠΡΙΝ', R.rel < 0)
win('ματς 1-3 μετα', R.rel.between(1, 3))
win('ματς 4-6', R.rel.between(4, 6))
win('ματς 7-10', R.rel.between(7, 10))
win('ματς 11-20', R.rel.between(11, 20))
P(''); P('  ανα σεζον (ματς 1-6 μετα, vs live μοντελο / vs παλιο μοντελο):')
for Y in sorted(R.season.unique()):
    x = R[(R.season == Y) & R.rel.between(1, 6)]
    P(f'    {Y}: n {len(x):3d} ({x.ev.nunique()} αλλαγες) · vs live {x.r_mod.mean():+.2f} · vs παλιο {x.r_old.mean():+.2f}' + (f' · vs αγορα {x.r_mc.mean():+.2f}' if 'r_mc' in x and x.r_mc.notna().any() else ''))
# ---- picks μας ----
P(''); P('=== ΤΑ PICKS ΜΑΣ (alert Crown, χαντικαπ, live μοντελο) σε ματς 1-10 μετα την αλλαγη ===')
evp = {}
for s, team, d, nm in EV:
    idx = sorted([i for i in range(len(D)) if D.season.values[i] == s and team in (D.home.values[i], D.away.values[i])], key=lambda i: D.t.values[i])
    post = [i for i in idx if str(D.t.values[i])[:10] >= d][:10]
    for i in post: evp[i] = team
res = {'υπερ της ομαδας με νεο προπονητη': [], 'κατα της ομαδας με νεο προπονητη': []}
for p, team in evp.items():
    if p not in REC[21]: continue
    m = PR.get(key(p), {}).get('h_new')
    if m is None or not np.isfinite(m): continue
    ser, tip = REC[21][p]['ser'], REC[21][p]['tip']
    for k_, row in enumerate(ser):
        if row[0] >= tip: break
        side, e, od = pick(21, m, row)
        if e < 0.08: continue
        if k_ > 0 and (tip - row[0]) / 3600 < 2: break
        tside = 1 if D.home.values[p] == team else -1
        res['υπερ της ομαδας με νεο προπονητη' if side == tside else 'κατα της ομαδας με νεο προπονητη'].append((settle(21, p, side, row, od), D.season.values[p]))
        break
for k, L in res.items():
    if L:
        a = np.array([x[0] for x in L]); P(f'  {k:36s} n {len(a):3d} · ROI {a.mean()*100:+6.1f}% · μοναδες {a.sum():+5.1f}')
P(''); P('  αλλαγες: ' + ' · '.join(f'{s[-2:]} {t} {d} {n[:14]}' for s, t, d, n in EV))
open('el_coach_change_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
P(''); P('  picks ανα σεζον (μοναδες υπερ / κατα της ομαδας με νεο προπονητη):')
for Y in SE5:
    a = [x[0] for x in res['υπερ της ομαδας με νεο προπονητη'] if x[1] == Y]; b = [x[0] for x in res['κατα της ομαδας με νεο προπονητη'] if x[1] == Y]
    P(f'    {Y}: υπερ n {len(a):2d} {sum(a):+5.1f} μον. · κατα n {len(b):2d} {sum(b):+5.1f} μον.')
open('el_coach_change_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ---- ΠΟΤΕ βγαινουν τα picks & που στεκεται το μοντελο vs αγορα (απο τη ματια της ομαδας) ----
P(''); P('=== ΠΟΤΕ: picks ανα φαση μετα την αλλαγη · (μοντελο − αγορα) για την ομαδα: + = το μοντελο την εκτιμα ΠΕΡΙΣΣΟΤΕΡΟ απο την αγορα ===')
evn = {}
for s, team, d, nm in EV:
    idx = sorted([i for i in range(len(D)) if D.season.values[i] == s and team in (D.home.values[i], D.away.values[i])], key=lambda i: D.t.values[i])
    pre = [i for i in idx if str(D.t.values[i])[:10] < d][-5:]; post = [i for i in idx if str(D.t.values[i])[:10] >= d][:10]
    for j, i in enumerate(pre): evn[i] = (team, j - len(pre))
    for j, i in enumerate(post): evn[i] = (team, j + 1)
W = {}
for p, (team, rel) in evn.items():
    if p not in REC[21]: continue
    m = PR.get(key(p), {}).get('h_new')
    if m is None or not np.isfinite(m): continue
    tside = 1 if D.home.values[p] == team else -1
    ph = 'πριν (5)' if rel < 0 else ('1-3' if rel <= 3 else ('4-6' if rel <= 6 else '7-10'))
    w = W.setdefault(ph, dict(gap=[], up=[], dn=[]))
    w['gap'].append((m - REC[21][p]['ser'][0][1]) * tside)
    ser, tip = REC[21][p]['ser'], REC[21][p]['tip']
    for k_, row in enumerate(ser):
        if row[0] >= tip: break
        side, e, od = pick(21, m, row)
        if e < 0.08: continue
        if k_ > 0 and (tip - row[0]) / 3600 < 2: break
        w['up' if side == tside else 'dn'].append(settle(21, p, side, row, od)); break
for ph in ('πριν (5)', '1-3', '4-6', '7-10'):
    w = W.get(ph)
    if not w: continue
    f = lambda L: f'{len(L):2d} picks {sum(L):+5.1f} μον. ({np.mean(L)*100:+.0f}%)' if L else ' 0 picks'
    P(f'  {ph:9s} ματς {len(w["gap"]):3d} · μοντελο − αγορα (ανοιγμα) για την ομαδα {np.mean(w["gap"]):+.2f} π. · picks ΥΠΕΡ: {f(w["up"])} · ΚΑΤΑ: {f(w["dn"])}')
open('el_coach_change_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
