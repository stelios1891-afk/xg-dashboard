# -*- coding: utf-8 -*-
"""el_onoff_alias_build.py — ΑΝΤΙΣΤΟΙΧΙΣΗ ΟΝΟΜΑΤΩΝ box score Ευρωλιγκας → προφιλ on/off 3StepsBasket (23/10/2026, Στελιος «κανε τσεκ
σε ολα τα ονοματα και προχωρα στη διορθωση»). Το el_absence.onoff_of ταιριαζει «επωνυμο + αρχικο μικρου ονοματος» → χανονταν 6 παικτες
με περσινο προφιλ (Vezenkov «Sasha» ≠ «Aleksandar», Tavares «Walter» ≠ «Edy», Shorts II, Washington Jr., Feliz Andres ανάποδα, Kramer/Kraemer)
→ η απουσια τους στα ΣΥΝΟΛΑ μετρουσε 0.
Μεθοδος: για καθε φετινο παικτη που ΔΕΝ βρισκει προφιλ, βρισκω την περσινη του γραμμη Ευρωλιγκας (ομαδα + φανελα, el_pbp/) και τον ιδιο
(ομαδα + φανελα) στο 3StepsBasket της περσινης σεζον· δεχομαι μονο αν μοιαζει και το ονομα (κοινη λεξη ή ομοιοτητα ≥0.75).
Εξοδος: el_onoff_alias.json {ονομα box: [επωνυμο-λεξεις, μικρο]} (το διαβαζει το el_absence.load_onoff). ΤΡΕΧΕΙ ΤΟΠΙΚΑ μια φορα τη σεζον
(μετα το el_onoff_build.py) + οποτε θελουμε μεσα στη σεζον (θελει el_pbp/ απο el_pbp_fetch.py)."""
import json, sys, glob, collections, difflib
import el_absence as E
sys.stdout.reconfigure(encoding='utf-8')
PREV, CUR, B3KEY = 'E2025', 'E2026', 'euroleague-2026'        # ετησια ενημερωση (περσινη σεζον EL, φετινη, 3steps της περσινης)
OO = E.load_onoff(base_only=True); P_ = OO[0]
B3 = json.load(open('bb3s_data.json', encoding='utf-8'))[B3KEY]
code = {t['clubId']: t['shortName'] for t in B3['teams']}
TJ = {}
for cl in B3['players'].values():
    for p in cl.get('players', []):
        TJ[(code.get(cl['id']), str(p.get('jersey')).strip())] = ((tuple(E._otok(p['surname'])), (E._otok(p['firstname']) or [''])[0]), f"{p['firstname']} {p['surname']}")
def boxes(season):
    out = collections.defaultdict(int)
    for fn in glob.glob(f'el_pbp/{season}_*.json'):
        d = json.load(open(fn, encoding='utf-8'))
        for st in d['box'].get('Stats') or []:
            for x in st.get('PlayersStats') or []:
                if str(x.get('Minutes') or '').strip() not in ('', 'DNP', '0:00'): out[(x['Player'], x['Team'].strip(), str(x.get('Dorsal')).strip())] += 1
    return out
prev, cur = boxes(PREV), boxes(CUR)
byname = collections.defaultdict(list)
for (nm, tm, j), g in prev.items(): byname[nm].append((g, tm, j))
alias, log = {}, []
for nm in sorted({k[0] for k in cur}):
    if E.onoff_of(nm, OO) is not None: continue
    for g, tm, j in sorted(byname.get(nm, []), reverse=True):
        hit = TJ.get((tm, j))
        if not hit or hit[0] not in P_: continue
        a = set(E._otok(nm)); b = set(E._otok(hit[1]))
        sim = difflib.SequenceMatcher(None, ' '.join(sorted(a)), ' '.join(sorted(b))).ratio()
        if a & b or sim >= 0.75:
            alias[nm] = [list(hit[0][0]), hit[0][1]]; log.append(f'{nm} → {hit[1]} ({tm} #{j}, {g} ματς περσι)'); break
json.dump(dict(built='2026-10-23', prev=PREV, cur=CUR, alias=alias), open('el_onoff_alias.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'el_onoff_alias.json: {len(alias)} αντιστοιχισεις'); [print('  ' + x) for x in log]
