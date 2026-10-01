# -*- coding: utf-8 -*-
"""ec_prior_build.py — ΑΦΕΤΗΡΙΑ σεζον EuroCup (1/10/2026, αποφαση Στελιου «περνα αυτη τη ρυθμιση»· ec_carry_test.py:
περσι .2 + ειδικοι κ_x 4 με 3 γνωμες → πρωτα 6 ματς 6/8 σεζον καλυτερα, ROI ανοιγμα +9.3 → +13.3%).
Γραφει ec_prior.json {season, carry, kx, kp, z{code}, pre{code}, fs{code: Flashscore id}, src} — το διαβαζει το ec_refresh.py.
  z  = μεσος (Eurohoops θεση → Φ⁻¹, Taking The Charge θεση → Φ⁻¹, αποδοση νικητη → −ln τυποποιημενο μεσα στις ομαδες)
       πηγες: ec_power_rankings.json + ec_outrights.json (οποιες υπαρχουν για τη σεζον).
  pre = αποδοση προετοιμασιας (ιδια με el_preseason_prior / ec_contrib_test): Σ[διαφορα ±20 − (R_ομαδας − R_αντιπαλου)]/(n+4)
       σε φιλικα/Super Cups 1 Αυγ … πρεμιερα EuroCup, R = κοινη κλιμακα ΠΕΡΣΙΝΗΣ σεζον (fs_bk_games).
Τρεχει ΜΙΑ φορα τη σεζον (και ξανα αν προστεθει γνωμη). Χρηση: python ec_prior_build.py [ετος]"""
import sys, json, math, re, unicodedata, datetime as dt, urllib.request
import numpy as np
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
from el_season import Y as _CY
Y = int(sys.argv[1]) if len(sys.argv) > 1 else _CY
SEASON = f'U{Y}'
CARRY, KX, KP = 0.2, 4.0, 0.5
H = {'User-Agent': 'Mozilla/5.0 Chrome/120.0', 'Accept': 'application/json'}
g = json.loads(urllib.request.urlopen(urllib.request.Request(f'https://api-live.euroleague.net/v2/competitions/U/seasons/{SEASON}/games', headers=H), timeout=40).read())['data']
NAME = {}
for x in g:
    for s in ('local', 'road'): NAME[x[s]['club']['code']] = x[s]['club']['name']
start = min(dt.date.fromisoformat(x['utcDate'][:10]) for x in g)
def norm(s): return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower().strip()
def toks(s): return {w for w in re.split(r'[^a-z]+', norm(s)) if len(w) >= 3}
# ---- ειδικοι (3 γνωμες) ----
nd = NormalDist(); sea_lbl = f'{Y}-{(Y + 1) % 100:02d}'
PR = json.load(open('ec_power_rankings.json', encoding='utf-8')); OR = json.load(open('ec_outrights.json', encoding='utf-8'))
def code_of(name):
    n = norm(name); hit = [c for c, nm in NAME.items() if norm(nm) == n]
    if hit: return hit[0]
    sc = sorted(((len(toks(name) & toks(nm)) / max(1, len(toks(name))), c) for c, nm in NAME.items()), reverse=True)
    return sc[0][1] if sc and sc[0][0] >= 0.5 else None
Z, src = {}, []
for k, v in PR.items():
    if k.startswith('_') or sea_lbl not in v: continue
    L = v[sea_lbl]['ranking']; src.append(f'{k.split(" (")[0]} ({len(L)})')
    for r, nm in enumerate(L, 1):
        c = code_of(nm)
        if c: Z.setdefault(c, []).append(nd.inv_cdf(1 - (r - .5) / len(L)))
        else: print('ΠΡΟΣΟΧΗ: καταταξη χωρις κωδικο:', nm)
if SEASON in OR:
    od = {code_of(n): o for n, o in OR[SEASON]['odds'].items()}
    od = {c: o for c, o in od.items() if c}
    if len(od) >= 0.8 * len(NAME):
        lv = {c: -math.log(o) for c, o in od.items()}; m_, s_ = np.mean(list(lv.values())), np.std(list(lv.values()))
        for c, v in lv.items(): Z.setdefault(c, []).append((v - m_) / s_)
        src.append(f'αποδοσεις νικητη ({len(od)}, {OR[SEASON]["date"]})')
Z = {c: float(np.mean(v)) for c, v in Z.items()}
# ---- προετοιμασια ----
FG = json.load(open('fs_bk_games.json', encoding='utf-8')); PS = json.load(open('fs_bk_preseason.json', encoding='utf-8'))
def common(y):
    rows = []
    for key, L in FG.items():
        c, yy = key.split('_')
        if int(yy) != y: continue
        for e in L:
            try: m = float(np.clip(int(e['hs']) - int(e['as_']), -20, 20))
            except Exception: continue
            if e.get('hid') and e.get('aid'): rows.append((e['hid'], e['aid'], m))
    teams = sorted({r[0] for r in rows} | {r[1] for r in rows}); ix = {t: i for i, t in enumerate(teams)}; n = len(teams); k = len(rows)
    A = np.zeros((k + n, n + 1)); b = np.zeros(k + n); r_ = np.arange(k)
    A[r_, [ix[r[0]] for r in rows]] = 1; A[r_, [ix[r[1]] for r in rows]] = -1; A[r_, n] = 1; b[:k] = [r[2] for r in rows]
    A[k + np.arange(n), np.arange(n)] = math.sqrt(2)
    x = np.linalg.lstsq(A, b, rcond=None)[0]
    return {t: float(x[ix[t]]) for t in teams}
C = common(Y - 1)
FS = {}
# (α) ματς EuroCup της σεζον στο Flashscore ↔ επισημο προγραμμα (σκορ + ημερομηνια)
res = {}
for x in g:
    if x['played'] and x['local']['score'] is not None:
        res.setdefault((int(x['local']['score']), int(x['road']['score'])), []).append(x)
for e in FG.get(f'EC_{Y}', []):
    try: hs, as_ = int(e['hs']), int(e['as_'])
    except Exception: continue
    d = dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).date()
    for x in res.get((hs, as_), []):
        if abs((dt.date.fromisoformat(x['utcDate'][:10]) - d).days) <= 1:
            FS[x['local']['club']['code']] = e['hid']; FS[x['road']['club']['code']] = e['aid']; break
# (β) οι υπολοιπες με ονομα (Flashscore ονοματα περσινης/φετινης σεζον)
fsn = {}
for key, L in list(FG.items()) + list(PS.items()):
    if not key.endswith(str(Y)) and not key.endswith(str(Y - 1)): continue
    for e in L:
        if e.get('hid'): fsn.setdefault(e['hid'], e['home'])
        if e.get('aid'): fsn.setdefault(e['aid'], e['away'])
for c, nm in NAME.items():
    if c in FS: continue
    tk = toks(nm) - {'basketball', 'basket', 'club', 'college', 'telecom', 'salud', 'energia'}
    best = sorted(((len(tk & toks(n)), t) for t, n in fsn.items() if tk & toks(n)), reverse=True)
    if best and best[0][0] >= 1: FS[c] = best[0][1]
acc = {}
inv = {v: c for c, v in FS.items()}
for key, L in PS.items():
    if not key.endswith(str(Y)): continue
    for e in L:
        if not e.get('ts'): continue
        d = dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).date()
        if not (dt.date(Y, 8, 1) <= d < start): continue
        try: m = float(np.clip(int(e['hs']) - int(e['as_']), -20, 20))
        except Exception: continue
        for me, op, sg in ((e.get('hid'), e.get('aid'), 1), (e.get('aid'), e.get('hid'), -1)):
            c = inv.get(me)
            if c and me in C and op in C: acc.setdefault(c, []).append(sg * m - (C[me] - C[op]))
PRE = {c: round(sum(L) / (len(L) + 4.0), 3) for c, L in acc.items()}
out = dict(season=SEASON, built=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes'), carry=CARRY, kx=KX, kp=KP,
           z={c: round(v, 3) for c, v in Z.items()}, pre=PRE, fs=FS, fs_name={c: fsn.get(t) for c, t in FS.items()}, src=src,
           note='αφετηρια = carry×περσινο EuroCup (νεες 0) + (kx·z + kp·pre)·100/72 (μισο επιθεση/μισο αμυνα)')
json.dump(out, open('ec_prior.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'{SEASON}: πηγες γνωμης {src} · z {len(Z)}/{len(NAME)} · Flashscore {len(FS)}/{len(NAME)} · προετοιμασια {len(PRE)} ομαδες')
for c in sorted(NAME, key=lambda c: -Z.get(c, -9)):
    print(f"  {c} {NAME[c][:30]:30s} z {Z.get(c, float('nan')):+.2f} → {KX * Z.get(c, 0):+.1f} · προετ. {PRE.get(c, 0):+.1f} ({len(acc.get(c, []))} ματς) · FS {fsn.get(FS.get(c), '—')}")
