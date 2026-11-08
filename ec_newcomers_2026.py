# -*- coding: utf-8 -*-
"""ec_newcomers_2026.py — ΤΙ RATING ΠΑΙΡΝΟΥΝ ΦΕΤΟΣ οι 32 ομαδες EuroCup 2026-27 (1/10/2026, Στελιος: «τι rating παιρνουν οι 15 νεες σημερα;»).
Για καθε ομαδα: περσινη διοργανωση/πρωταθλημα (Flashscore 2025-26) · net rating μεσα στη λιγκα της · ΚΟΙΝΗ ΚΛΙΜΑΚΑ (ridge ολων των ματς,
οι λιγκες «δενουν» μεσω BCL / FIBA Europe Cup / EuroCup / Ευρωλιγκα) σε σχεση με τον μεσο ορο των ομαδων EuroCup 2025-26 ·
τι παιρνει το μοντελο ως αφετηρια: παλιες = 0.7 × περσινο EuroCup, νεες = 0 · + ειδικοι 3 × z (μεσος Eurohoops/TTC).
Επιπλεον: ΕΠΙΠΕΔΟ ΚΑΘΕ ΔΙΟΡΓΑΝΩΣΗΣ (μεσος κοινης κλιμακας των ομαδων της) → «ποσα σκαλια» κατω απο το EuroCup.
Εξοδος: ec_newcomers_2026_out.txt"""
import json, math, re, unicodedata, sys
import numpy as np
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
FG = json.load(open('fs_bk_games.json', encoding='utf-8')); XT = json.load(open('fs_bk_extra.json', encoding='utf-8'))
Y = 2025
rows, lg_of, name_of = [], {}, {}
for key, L in list(FG.items()) + list(XT.items()):
    c, yy = key.split('_')
    if int(yy) != Y: continue
    for e in L:
        try: m = float(np.clip(int(e['hs']) - int(e['as_']), -20, 20)); raw = int(e['hs']) - int(e['as_'])
        except Exception: continue
        if not (e.get('hid') and e.get('aid')): continue
        rows.append((e['hid'], e['aid'], m, raw, c))
        for t, n in ((e['hid'], e['home']), (e['aid'], e['away'])):
            name_of[t] = n; lg_of.setdefault(t, {}).setdefault(c, 0); lg_of[t][c] += 1
teams = sorted(name_of); ix = {t: i for i, t in enumerate(teams)}; n = len(teams); k = len(rows)
A = np.zeros((k + n, n + 1)); b = np.zeros(k + n); r_ = np.arange(k)
A[r_, [ix[r[0]] for r in rows]] = 1; A[r_, [ix[r[1]] for r in rows]] = -1; A[r_, n] = 1; b[:k] = [r[2] for r in rows]
A[k + np.arange(n), np.arange(n)] = math.sqrt(2)
x = np.linalg.lstsq(A, b, rcond=None)[0]; CR = {t: float(x[ix[t]]) for t in teams}
EUROPE = {'EL', 'EC', 'BCL', 'FEC'}
# περσινο rating ΜΟΝΟ απο ματς EuroCup (οπως το «μεταφερει» το μοντελο ×0.7)
er = [r for r in rows if r[4] == 'EC']; et = sorted({r[0] for r in er} | {r[1] for r in er}); ei = {t: i for i, t in enumerate(et)}; ne = len(et)
Ae = np.zeros((len(er) + ne, ne + 1)); be = np.zeros(len(er) + ne); q = np.arange(len(er))
Ae[q, [ei[r[0]] for r in er]] = 1; Ae[q, [ei[r[1]] for r in er]] = -1; Ae[q, ne] = 1; be[:len(er)] = [r[2] for r in er]
Ae[len(er) + np.arange(ne), np.arange(ne)] = math.sqrt(2)
xe = np.linalg.lstsq(Ae, be, rcond=None)[0]; ECR = {t: float(xe[ei[t]] - np.mean(xe[:ne])) for t in et}
def home_league(t):
    d = {c: v for c, v in lg_of[t].items() if c not in EUROPE}
    return max(d, key=d.get) if d else '-'
def euro_comp(t):
    d = {c: v for c, v in lg_of[t].items() if c in EUROPE}
    return '/'.join(sorted(d)) if d else '-'
# net rating ΜΕΣΑ στη λιγκα (πραγματικη διαφορα ανα ματς, μονο ματς της λιγκας)
net = {}
for h, a, m, raw, c in rows:
    for t, s in ((h, raw), (a, -raw)):
        if c == home_league(t): net.setdefault(t, []).append(s)
ec_teams = [t for t in teams if 'EC' in lg_of[t]]
mu_ec = float(np.mean([CR[t] for t in ec_teams]))
out = []
P = lambda s='': (out.append(s), print(s))
P(f'=== ΕΠΙΠΕΔΟ ΔΙΟΡΓΑΝΩΣΕΩΝ 2025-26 (μεσος κοινης κλιμακας των ομαδων της, σε σχεση με τον μεσο EuroCup = 0) ===')
lev = {}
for c in sorted({r[4] for r in rows}):
    tt = [t for t in teams if (c in EUROPE and c in lg_of[t]) or (c not in EUROPE and home_league(t) == c)]
    if len(tt) >= 6: lev[c] = float(np.mean([CR[t] for t in tt])) - mu_ec
for c, v in sorted(lev.items(), key=lambda z: -z[1]): P(f'  {c:4s} {v:+6.1f}  ({sum(1 for t in teams if (c in EUROPE and c in lg_of[t]) or (c not in EUROPE and home_league(t) == c))} ομαδες)')
# ---- 32 ομαδες 2026-27 ----
PR = json.load(open('ec_power_rankings.json', encoding='utf-8'))
EH = [v for kk, v in PR.items() if kk.startswith('Euro')][0]['2026-27']['ranking']
TT = [v for kk, v in PR.items() if kk.startswith('Taking')][0]['2026-27']['ranking']
nd = NormalDist()
STOP = {'bc', 'kk', 'basket', 'basketball', 'club', 'de', 'the', 'bk', 'sk', 'pbc', 'cb', 'fc', 'as', 'sp', 'en', 'sa', 'bkt', 'bh', 'telecom', 'energia', 'salud',
        'recoletas', 'san', 'pablo', 'kids', 'us', 'college', 'istanbul', 'thessaloniki', 'midtown', 'voli', 'umana', 'reyer', 'baglietto', 'cosea', 'jl', 'u', 'bt',
        'dolomiti', 'le', 'sarthe', 'seawolves', 'skyliners', 'niners', 'ratiopharm', 'ratiopahm', 'maxima', 'lions', 'zelli', 'balkan', 'turk', 'telekom', 'hapoel'}
ALIAS = {'venice': 'venezia', 'ljubljana': 'olimpija', 'podgorica': 'buducnost', 'tenerife': 'tenerife', 'laguna': 'tenerife', 'wroclaw': 'slask', 'panevezys': 'lietkabelis',
         'klaipeda': 'neptunas', 'derthona': 'tortona', 'bresse': 'bourg', 'bursa': 'tofas', 'sarajevo': 'bosna', 'ankara': 'telekom'}
def toks(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return {ALIAS.get(t, t) for t in re.split(r'[^a-z]+', s) if t and t not in STOP}
EXTRA = {'Turk Telekom Ankara': {'telekom'}, 'Hapoel Midtown Jerusalem': {'jerusalem'}, 'London Lions': {'london'}, 'Balkan Botevgrad': {'balkan', 'botevgrad'},
         'Riga Zelli': {'riga'}, 'Le Mans Sarthe Basket': {'mans'}, 'Maxima Roma': {'roma'}, 'Roma Basketball': {'roma'}}
def find(name):
    tk = EXTRA.get(name, toks(name)); best = []
    for t, nm in name_of.items():
        tn = toks(nm) | {w for w in re.split(r'[^a-z]+', unicodedata.normalize('NFKD', nm).encode('ascii', 'ignore').decode().lower()) if w}
        sc = len(tk & tn)
        if sc: best.append((sc, sum(lg_of[t].values()), t))
    best.sort(reverse=True)
    return [b_[2] for b_ in best[:3]]
EC25 = set(ec_teams)
P(''); P('=== 32 ΟΜΑΔΕΣ EuroCup 2026-27: τι «ξερουμε» και τι παιρνει το μοντελο στην αφετηρια (ποντοι διαφορας/ματς vs μεσο EuroCup) ===')
P('  ομαδα | περσι: πρωταθλημα (+Ευρωπη) | net στη λιγκα | ΚΟΙΝΗ κλιμακα | μοντελο: περσινο EC×0.7 | ειδικοι EH/TTC θεσεις → 3×z | ΣΥΝΟΛΟ αφετηριας')
res = []; RKT = {}
for nm in EH:
    ids = find(nm); t = ids[0] if ids else None
    tt_nm = nm if nm in TT else next((x for x in TT if len(toks(x) & toks(nm)) >= 2 or (toks(x) & toks(nm)) == toks(nm)), None)
    RKT[nm] = TT.index(tt_nm) + 1 if tt_nm else 0
    zs = [nd.inv_cdf(1 - (EH.index(nm) + .5) / len(EH))] + ([nd.inv_cdf(1 - (RKT[nm] - .5) / len(TT))] if RKT[nm] else [])
    ex = 3 * float(np.mean(zs))
    if t is None:
        res.append((nm, '?', None, None, None, ex)); continue
    isnew = t not in EC25
    carry = 0.0 if isnew else 0.7 * ECR[t]
    nt = float(np.mean(net.get(t, [0])))
    res.append((nm, f'{home_league(t)} ({euro_comp(t)})', nt, CR[t] - mu_ec, carry, ex, isnew, name_of[t]))
for r in sorted(res, key=lambda r: (not r[6] if len(r) > 6 else 0, -(r[4] or 0) - r[5])):
    if r[2] is None: P(f'  🆕 {r[0]:32s} | ΔΕΝ ΥΠΑΡΧΕΙ στα δεδομενα 2025-26 (κατω κατηγορια;) | νεα → 0 | EH {EH.index(r[0]) + 1:2d} TTC {RKT[r[0]]:2d} → {r[5]:+4.1f} | {r[5]:+5.1f}'); continue
    nm, lg, nt, cs, carry, ex, isnew, fsn = r
    P(f'  {"🆕 " if isnew else "   "}{nm:32s} | {lg:14s} | {nt:+5.1f} | {cs:+5.1f} | {"νεα → 0" if isnew else f"{carry:+5.1f}":>8s} | '
      f'EH {EH.index(nm) + 1:2d} TTC {RKT[nm]:2d} → {ex:+4.1f} | {(0 if isnew else carry) + ex:+5.1f}   [{fsn}]')
open('ec_newcomers_2026_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
