# -*- coding: utf-8 -*-
"""ec_outrights_2026_compare.py — ΣΥΜΦΩΝΕΙ η αφετηρια του μοντελου EuroCup 2026-27 με τις αποδοσεις ΝΙΚΗΤΗ; (1/10/2026, Στελιος — screenshot broker,
μετα την 1η αγωνιστικη). Αποδοσεις → ec_outrights.json['U2026'].
Συγκριση: αφετηρια = 0.7×περσινο EuroCup (παλιες) / 0 (νεες) + ειδικοι 3·z (απο ec_newcomers_2026.py).
Αγορα → z = (−ln αποδοσης − μεσος)/τ.α. μεσα στις 32 → 3·z (ιδια κλιμακα με τους ειδικους). ΠΡΟΣΟΧΗ: οι αποδοσεις νικητη εξαρτωνται και απο τον ΟΜΙΛΟ.
Εξοδος: ec_outrights_2026_compare_out.txt"""
import json, math, sys, io, contextlib
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ODDS = {'PAOK Thessaloniki': 3.25, 'Aris Thessaloniki': 3.75, 'Bahcesehir College Istanbul': 6.0, 'Hapoel Midtown Jerusalem': 7.5, 'Napoli Basketball': 16,
        'Turk Telekom Ankara': 20, 'La Laguna Tenerife': 24, 'Cosea JL Bourg-en-Bresse': 30, 'Umana Reyer Venice': 30, 'Buducnost VOLI Podgorica': 50,
        'Roma Basketball': 50, 'Maxima Roma': 60, 'Tofas Bursa': 65, 'Kids&Us Manresa': 100, 'Balkan Botevgrad': 100, 'Baglietto Derthona Tortona': 100,
        'Riga Zelli': 100, 'Siauliai Basketball': 100, 'Slask Wroclaw': 100, 'Bosna BH Telecom Sarajevo': 100, 'U-BT Cluj-Napoca': 150,
        'Dolomiti Energia Trento': 200, 'Cedevita Olimpija Ljubljana': 200, 'London Lions': 200, 'NINERS Chemnitz': 200, 'Skyliners Frankfurt': 200,
        'Le Mans Sarthe Basket': 200, 'Neptunas Klaipeda': 200, 'Rostock Seawolves': 200, 'Recoletas Salud San Pablo Burgos': 200, 'ratiopharm ulm': 200,
        'Lietkabelis Panevezys': 500}
OR = json.load(open('ec_outrights.json', encoding='utf-8'))
OR['U2026'] = dict(date='2026-10-01', src='broker (screenshot Στελιου)', after_round=1, odds=ODDS)
json.dump(OR, open('ec_outrights.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
NS = {}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('ec_newcomers_2026.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", '').replace("open('ec_newcomers_2026_out.txt', 'w'", "open('_unused_nc.txt', 'w'"), NS)
res = {r[0]: r for r in NS['res']}
PR = json.load(open('ec_power_rankings.json', encoding='utf-8'))
tt = [v for k, v in PR.items() if k.startswith('Taking')][0]['2026-27']
GRP = {}
for nm, g in zip(tt['ranking'], tt['groups']):
    m = next((x for x in res if NS['toks'](x) & NS['toks'](nm) == NS['toks'](x) or x == nm), None)
    if m: GRP[m] = g[-1]
names = list(res)
assert set(names) == set(ODDS), set(names) ^ set(ODDS)
lo = np.array([-math.log(ODDS[n]) for n in names]); zo = (lo - lo.mean()) / lo.std()
MKT = {n: 3 * z for n, z in zip(names, zo)}
def start(r):  # (nm, lg, nt, cs, carry, ex, isnew, ..) ή (nm,'?',None,None,None,ex)
    if r[2] is None: return r[5], r[5], 0.0, True
    return (0 if r[6] else r[4]) + r[5], r[5], (0 if r[6] else r[4]), r[6]
S = {n: start(res[n]) for n in names}
def rk(d): o = sorted(d, key=lambda k: -d[k]); return {k: i + 1 for i, k in enumerate(o)}
rS, rM = rk({n: S[n][0] for n in names}), rk(MKT)
out = []
P = lambda s='': (out.append(s), print(s))
def spear(a, b): return float(np.corrcoef([rk(a)[n] for n in names], [rk(b)[n] for n in names])[0, 1])
P('=== ΑΦΕΤΗΡΙΑ ΜΟΝΤΕΛΟΥ vs ΑΠΟΔΟΣΕΙΣ ΝΙΚΗΤΗ (EuroCup 2026-27, μετα την 1η) ===')
P(f'  συσχετιση σειρας (1 = ιδια σειρα): ΑΦΕΤΗΡΙΑ {spear({n: S[n][0] for n in names}, MKT):.2f} · μονο ΕΙΔΙΚΟΙ {spear({n: S[n][1] for n in names}, MKT):.2f} · '
  f'μονο ΠΕΡΣΙΝΟ (17 παλιες) {float(np.corrcoef([rk({n: S[n][2] for n in names if not S[n][3]})[n] for n in names if not S[n][3]], [rk({n: MKT[n] for n in names if not S[n][3]})[n] for n in names if not S[n][3]])[0, 1]):.2f}')
P('  ομαδα | ομιλος | αποδοση | θεση αγορας | αφετηρια (θεση) | αγορα σε ποντους | διαφορα θεσεων')
for n in sorted(names, key=lambda n: rM[n]):
    P(f'  {"🆕" if S[n][3] else "  "} {n:34s} {GRP.get(n, "?")} | {ODDS[n]:6.2f} | {rM[n]:2d} | {S[n][0]:+5.1f} ({rS[n]:2d}) | {MKT[n]:+5.1f} | {rS[n] - rM[n]:+3d}')
P(''); P('=== ΜΕΣΟΣ ΑΝΑ ΟΜΙΛΟ (αφετηρια μοντελου) ===')
for g in 'ABCD':
    gg = [n for n in names if GRP.get(n) == g]
    P(f'  Ομιλος {g}: {np.mean([S[n][0] for n in gg]):+.1f} · ' + ', '.join(f'{n.split()[0]} {S[n][0]:+.1f}' for n in sorted(gg, key=lambda n: -S[n][0])))
nw = [n for n in names if S[n][3]]; od = [n for n in names if not S[n][3]]
P(''); P(f'  νεες vs παλιες: αφετηρια {np.mean([S[n][0] for n in nw]):+.1f} / {np.mean([S[n][0] for n in od]):+.1f} · αγορα {np.mean([MKT[n] for n in nw]):+.1f} / {np.mean([MKT[n] for n in od]):+.1f}')
open('ec_outrights_2026_compare_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
