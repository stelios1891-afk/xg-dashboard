# -*- coding: utf-8 -*-
"""el_travel.py — ΤΑΞΙΔΙ ΣΤΟ 2ο ΜΑΤΣ ΔΙΑΒΟΛΟΒΔΟΜΑΔΑΣ, διορθωση χαντικαπ (1/10/2026, αποφαση Στελιου «περασε το +4.5 και το +6.6»).
el_dw_fatigue_deep.py (E2021-25, live μοντελο, Crown): φιλοξενουμενος που ταξιδευει ≥1000 χλμ απο το ΠΡΟΗΓΟΥΜΕΝΟ γηπεδο του, με ≤3.5 μερες
ξεκουραση, ΕΝΩ ο γηπεδουχος επαιξε και το προηγουμενο ματς (≤3.5 μερες) στο σπιτι του:
  φιλοξ. απο ΕΝΤΟΣ (π.χ. Ζαλγκιρις Καουνας → Παρισι): +4.09 vs μοντελο (49 ματς) → +4.5 με συγκρατηση
  φιλοξ. απο ΕΚΤΟΣ (2ο εκτος σερι): +7.66 (28) → +6.6 με συγκρατηση
  γηπεδουχος ταξιδεψε κι αυτος: ~0 → καμια διορθωση · κατω απο 1000 χλμ: καμια διαβαθμιση (σκαλι, οχι αναλογικο)
LOSO: RMSE καλυτερο 4/5 σεζον, δυο τιμες > μια τιμη 5/5· ιστορικα picks χαντικαπ στα 77 ματς: +7.3 → +24.0 μον. (3/5 σεζον).
Μονο χαντικαπ (συνολα: καμια επιδραση). Ουδετερα ματς: καμια διορθωση."""
import math, datetime as dt
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
    return CITY.get(str(v).strip().upper()) if v else None
def km(a, b):
    if not a or not b: return None
    p1, p2 = math.radians(a[0]), math.radians(b[0]); dl = math.radians(b[1] - a[1])
    return 6371 * math.acos(min(1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)))
DW_DAYS, KM_MIN = 3.5, 1000
ADJ_FROM_HOME, ADJ_FROM_AWAY = 4.5, 6.6
def _t(x): return dt.datetime.fromisoformat(x['utc'].replace('Z', '+00:00'))
def adjustments(sched, neutral=lambda x: False):
    """{code: dict(adj=+π. υπερ γηπεδουχου, km, from, home_prev, note)} για τα 2α ματς διαβολοβδομαδας που πιανει ο κανονας.
    sched = λιστα ματς της σεζον (el_sched.json[SEASON]). Μη αντιστοιχισμενα γηπεδα → καμια διορθωση (και σημειωση missing)."""
    S = sorted(sched, key=_t); prev = {}; out = {}; missing = set()
    for x in S:
        h, a = x['hcode'], x['acode']; ph, pa = prev.get(h), prev.get(a)
        if ph and pa and not neutral(x):
            rh, ra = (_t(x) - _t(ph)).total_seconds() / 86400, (_t(x) - _t(pa)).total_seconds() / 86400
            if rh <= DW_DAYS and ra <= DW_DAYS and ph['hcode'] == h:          # και οι 2 στο 2ο ματς · γηπ. επαιξε το προηγ. στο σπιτι
                c0, c1 = ll(pa.get('vname')), ll(x.get('vname'))
                if not c0: missing.add(pa.get('vname'))
                if not c1: missing.add(x.get('vname'))
                d = km(c0, c1)
                if d is not None and d >= KM_MIN:
                    fh = pa['hcode'] == a
                    out[x['code']] = dict(adj=ADJ_FROM_HOME if fh else ADJ_FROM_AWAY, km=round(d), frm='εντος' if fh else 'εκτος',
                                          note=f"🧳 ταξιδι: {x.get('away')} {round(d)} χλμ σε ≤3.5 μερες απο {'το σπιτι της' if fh else 'αλλο εκτος'}, "
                                               f"{x.get('home')} εμεινε σπιτι → +{ADJ_FROM_HOME if fh else ADJ_FROM_AWAY} π. στον γηπεδουχο")
        prev[h] = x; prev[a] = x
    return out, sorted(m for m in missing if m)
