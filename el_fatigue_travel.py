# -*- coding: utf-8 -*-
"""el_fatigue_travel.py — Ευρωλιγκα: κουραση / διαβολοβδομαδες / ταξιδια (25/9/2026, αιτημα Στελιου).
Για καθε ομαδα-ματς (κανονικη περιοδος 2017-2025): ποσο πηγε πανω/κατω απο (α) το μοντελο, (β) την αγορα (closing, 2023-25).
Κατηγοριες 2ου ματς διαβολοβδομαδας (≤3.5 μερες απο το προηγουμενο): ΕΚΤΟΣ→ΕΚΤΟΣ, ΕΝΤΟΣ→ΕΚΤΟΣ, ΕΚΤΟΣ→ΕΝΤΟΣ, ΕΝΤΟΣ→ΕΝΤΟΣ.
Συγκριση με τα ΚΑΝΟΝΙΚΑ ματς του ιδιου τυπου (εκτος με εκτος, εντος με εντος, ≥5 μερες ξεκουρασης).
Ταξιδι: χλμ απο το προηγουμενο γηπεδο (διαβολοβδομαδα) ή απο την εδρα της ομαδας (κανονικη εβδομαδα)· ζωνες ωρας.
ΠΕΡΙΓΡΑΦΙΚΟ — μονο εγχωρια ματς δεν ειναι μεσα (δεν τα εχουμε ακομα). Εξοδος: el_fatigue_travel_out.txt"""
import sys, json, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))

CITY = {  # γηπεδο -> (lat, lon)
 'ASTROBALLE': (45.77, 4.88), 'LDLC ARENA': (45.77, 4.88), 'ARENA NURNBERGER VERSICHERUNG': (49.45, 11.08), 'BROSE ARENA': (49.89, 10.90),
 'LANXESS ARENA': (50.94, 6.98), 'PALAU BLAUGRANA': (41.38, 2.12), 'STARK ARENA': (44.81, 20.42), 'BELGRADE ARENA': (44.81, 20.42),
 'KOMBANK ARENA': (44.81, 20.42), 'ALEKSANDAR NIKOLIC HALL': (44.81, 20.47), 'ZALGIRIO ARENA': (54.89, 23.92), 'BUESA ARENA': (42.86, -2.67),
 'FERNANDO BUESA ARENA': (42.86, -2.67), 'MAX SCHMELING HALLE': (52.54, 13.40), 'MERCEDES-BENZ ARENA': (52.51, 13.44), 'UBER ARENA': (52.51, 13.44),
 'MORACA': (42.44, 19.26), 'GRAN CANARIA ARENA': (28.10, -15.45), 'MEGASPORT ARENA': (55.79, 37.56), 'USH CSKA': (55.79, 37.56),
 'SPORTS PALACE YANTARNY': (54.72, 20.46), 'VOLKSWAGEN ARENA': (41.11, 29.01), 'ARENA HUSEJIN SMAJLOVIC ZENICA': (44.20, 17.91),
 'COCA-COLA ARENA': (25.21, 55.27), 'ZETRA ARENA': (43.87, 18.41), 'BASKET HALL KAZAN': (55.80, 49.11), 'SIBUR ARENA': (59.97, 30.22),
 'YUBILEYNY SPORTS PALACE': (59.95, 30.29), 'ARENA 8888 SOFIA': (42.68, 23.32), 'ARENA BOTEVGRAD': (42.90, 23.79),
 'MENORA MIVTACHIM ARENA': (32.05, 34.79), 'PAIS ARENA JERUSALEM': (31.75, 35.19), 'ANTALYA SPORTS HALL': (36.89, 30.70),
 'ARENA RIGA': (56.97, 24.14), 'BASKETBALL DEVELOPMENT CENTER': (41.03, 28.99), 'TURKCELL BASKETBALL DEVELOPMENT CENTER': (41.03, 28.99),
 'SINAN ERDEM SPORTS HALL': (40.99, 28.83), 'SINAN ERDEM SPORTS HALL.': (40.99, 28.83), 'XIAOMI ARENA': (41.03, 28.99),
 'ARENA MYTISHCHI': (55.91, 37.73), 'MOVISTAR ARENA': (40.42, -3.67), 'WIZINK CENTER': (40.42, -3.67), 'MARTIN CARPENA': (36.70, -4.46),
 'ETIHAD ARENA': (24.47, 54.60), 'SALLE GASTON MEDECIN': (43.73, 7.42), 'ALLIANZ CLOUD': (45.47, 9.15), 'FORUM': (45.40, 9.15),
 'MEDIOLANUM FORUM': (45.40, 9.15), 'UNIPOL FORUM': (45.40, 9.15), 'PALABANCODESIO': (45.62, 9.21), 'AUDI DOME': (48.13, 11.52),
 'BMW PARK': (48.13, 11.52), 'SAP GARDEN': (48.18, 11.55), 'HERAKLION ARENA': (35.34, 25.13), 'PEACE AND FRIENDSHIP STADIUM': (37.94, 23.66),
 'TELEKOM CENTER ATHENS': (38.04, 23.79), 'OAKA': (38.04, 23.79), 'OAKA ALTION': (38.04, 23.79), 'OLYMPIC SPORTS CENTER ATHENS': (38.04, 23.79),
 'LA FONTETA': (39.45, -0.36), 'PABELLON FUENTE DE SAN LUIS': (39.45, -0.36), 'ROIG ARENA': (39.46, -0.36), 'ACCOR ARENA': (48.84, 2.38),
 'ADIDAS ARENA': (48.89, 2.36), 'KALNAPILIO ARENA': (55.73, 24.36), 'ULKER SPORTS AND EVENT HALL': (40.98, 29.06),
 'PALADOZZA': (44.49, 11.33), 'UNIPOL ARENA': (44.47, 11.25), 'VIRTUS ARENA': (44.50, 11.40), 'VIRTUS SEGAFREDO ARENA': (44.50, 11.40)}
def ll(v):
    return CITY.get(str(v).strip().upper())
def km(a, b):
    if not a or not b: return np.nan
    p1, p2 = math.radians(a[0]), math.radians(b[0]); dl = math.radians(b[1] - a[1])
    return 6371 * math.acos(min(1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)))

D = pd.read_csv('el_preds_all.csv')                      # ολα τα ματς με προβλεψη μοντελου (παγωμενο el_model_test)
MK = pd.read_csv('el_model_preds.csv')[['key', 'm_mkt']]
D = D.merge(MK, on='key', how='left')
S = json.load(open('el_sched.json', encoding='utf-8'))
tz = {f"{s}_{x['code']}": x.get('tz') for s, L in S.items() for x in L}
D['tz'] = D.key.map(tz)
D = D[D.phase == 'RS'].copy()
D['t'] = pd.to_datetime(D.t, utc=True)
missing = sorted({v for v in D.vname.dropna().unique() if not ll(v)})
if missing: P(f'γηπεδα χωρις πολη: {missing}')
D['loc'] = D.vname.map(ll)

# μακροσκελες: μια γραμμη ανα ομαδα-ματς
L = pd.concat([D.assign(team=D.home, side=1), D.assign(team=D.away, side=-1)])
L = L.sort_values(['season', 'team', 't']).reset_index(drop=True)
L['res'] = (L.act - L.m_model) * L.side                  # υπερ της ομαδας, vs μοντελο
L['mres'] = (L.act - L.m_mkt) * L.side                   # υπερ της ομαδας, vs αγορα
g = L.groupby(['season', 'team'])
L['gap'] = g.t.diff().dt.total_seconds() / 86400
L['gap_next'] = -g.t.diff(-1).dt.total_seconds() / 86400
L['prev_side'] = g.side.shift(1); L['prev_loc'] = g['loc'].shift(1); L['prev_tz'] = g.tz.shift(1)
home_loc = L[L.side == 1].groupby(['season', 'team'])['loc'].agg(lambda s: s.mode().iloc[0] if len(s.dropna()) else None)
L['home_loc'] = [home_loc.get((s, t)) for s, t in zip(L.season, L.team)]
dw2 = L.gap <= 3.5
L['travel'] = [km(p, c) if d else (km(h, c) if sd == -1 else 0.0) for p, c, h, sd, d in zip(L.prev_loc, L['loc'], L.home_loc, L.side, dw2)]
L['tzs'] = (L.tz - L.prev_tz).abs().where(dw2)

def row(g, lab, base_res=None, base_m=None):
    r = g.res.dropna(); m = g.mres.dropna()
    se = 11.5 / math.sqrt(max(len(r), 1))
    d = f' · vs κανονικα {r.mean() - base_res:+5.2f}' if base_res is not None else ''
    dm = f' / {m.mean() - base_m:+5.2f}' if base_m is not None and len(m) >= 15 else ''
    P(f'  {lab:40s} ματς {len(r):4d} · vs μοντελο {r.mean():+5.2f} (±{1.96*se:.1f}){d} · vs αγορα (2023-25, n={len(m)}) {m.mean() if len(m) else float("nan"):+5.2f}{dm}')

norm = L[(L.gap >= 5) & (L.gap_next >= 5)]
nA, nH = norm[norm.side == -1], norm[norm.side == 1]
P('=== 1. ΒΑΣΗ: κανονικα ματς (≥5 μερες πριν και μετα) — απο τη ματια της ομαδας ===')
row(nA, 'κανονικο ΕΚΤΟΣ'); row(nH, 'κανονικο ΕΝΤΟΣ')
bA, bH = nA.res.mean(), nH.res.mean(); mA, mH = nA.mres.mean(), nH.mres.mean()

P('\n=== 2. 2ο ΜΑΤΣ ΔΙΑΒΟΛΟΒΔΟΜΑΔΑΣ (≤3.5 μερες μετα το 1ο) — «vs κανονικα» = διαφορα απο τα κανονικα του ιδιου τυπου ===')
X = L[dw2]
for lab, pv, sd in (('ΕΚΤΟΣ → ΕΚΤΟΣ (2 εκτος σερι)', -1, -1), ('ΕΝΤΟΣ → ΕΚΤΟΣ', 1, -1), ('ΕΚΤΟΣ → ΕΝΤΟΣ', -1, 1), ('ΕΝΤΟΣ → ΕΝΤΟΣ (2 εντος)', 1, 1)):
    g2 = X[(X.prev_side == pv) & (X.side == sd)]
    row(g2, lab, bA if sd == -1 else bH, mA if sd == -1 else mH)
P('\n  1ο ματς διαβολοβδομαδας (η ομαδα ξερει οτι παιζει ξανα σε 2 μερες):')
F = L[(L.gap_next <= 3.5) & (L.gap >= 4)]
row(F[F.side == -1], '    1ο ματς ΕΚΤΟΣ', bA, mA); row(F[F.side == 1], '    1ο ματς ΕΝΤΟΣ', bH, mH)

P('\n=== 3. ΑΝΤΙΠΑΛΟΙ: ποιος ειναι κουρασμενος (απο τη ματια του ΓΗΠΕΔΟΥΧΟΥ) ===')
H = L[L.side == 1].copy(); A = L[L.side == -1][['key', 'gap', 'prev_side']].rename(columns={'gap': 'gap_a', 'prev_side': 'prev_a'})
H = H.merge(A, on='key')
H['tired_h'] = H.gap <= 3.5; H['tired_a'] = H.gap_a <= 3.5
for lab, c in (('κανενας κουρασμενος', ~H.tired_h & ~H.tired_a), ('μονο ο γηπεδουχος', H.tired_h & ~H.tired_a),
               ('μονο ο φιλοξενουμενος', ~H.tired_h & H.tired_a), ('και οι δυο', H.tired_h & H.tired_a),
               ('φιλοξ. με 2 εκτος σερι, γηπ. ξεκουραστος', ~H.tired_h & H.tired_a & (H.prev_a == -1)),
               ('φιλοξ. με 2 εκτος σερι, γηπ. κουρασμενος', H.tired_h & H.tired_a & (H.prev_a == -1))):
    row(H[c], lab)

P('\n=== 4. ΤΑΞΙΔΙ του ΦΙΛΟΞΕΝΟΥΜΕΝΟΥ (χλμ ως το γηπεδο) ===')
AW = L[L.side == -1].copy()
for lab, sub in (('κανονικη εβδομαδα (απο την εδρα του)', AW[AW.gap >= 5]), ('2ο ματς διαβολοβδομαδας (απο το προηγουμενο γηπεδο)', AW[AW.gap <= 3.5])):
    P(f'  {lab}:')
    base = sub.res.mean()
    for lo, hi in ((0, 1000), (1000, 2000), (2000, 3000), (3000, 99999)):
        g4 = sub[(sub.travel >= lo) & (sub.travel < hi)]
        if len(g4) >= 25: row(g4, f'    {lo}-{hi if hi < 9999 else "+"} χλμ', base)
P('  ζωνες ωρας (2ο ματς διαβολοβδομαδας, φιλοξενουμενος):')
T2 = AW[AW.gap <= 3.5]
for lab, c in (('ιδια ζωνη', T2.tzs == 0), ('1 ωρα', T2.tzs == 1), ('2+ ωρες', T2.tzs >= 2)):
    if c.sum() >= 25: row(T2[c], '    ' + lab, T2.res.mean())

P('\n=== 5. ΑΝΑ ΣΕΖΟΝ: 2 εκτος σερι vs κανονικο εκτος (vs μοντελο) ===')
for s, g5 in X[(X.prev_side == -1) & (X.side == -1)].groupby('season'):
    b = nA[nA.season == s].res.mean()
    P(f'  {s}: ματς {len(g5):3d} · {g5.res.mean() - b:+5.2f}')
open('el_fatigue_travel_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
