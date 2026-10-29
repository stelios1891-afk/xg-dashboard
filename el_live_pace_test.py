# -*- coding: utf-8 -*-
"""el_live_pace_test.py — ΕΥΡΩΛΙΓΚΑ ΣΥΝΟΛΑ IN-PLAY: «δικαιη live γραμμη με ρυθμο» vs Crown (29/10/2026, Στελιος «τρεξτο»).
Συνεχεια του el_half_luck_test (βημα Α: ρυθμος συνεχιζει 0.30/π, ευστοχια 0.015/π · η live αγορα μεταφερει ρυθμο μονο 0.14).

ΠΡΟ-ΔΗΛΩΜΕΝΗ ΜΕΘΟΔΟΣ:
  Σημεια: τελος 1ης περιοδου · ημιχρονο · τελος 3ης περιοδου (σκορ απο το pbp).
  Κομματια αποκλισης στο σημειο (ιδια με el_half_luck_test): ΡΥΘΜΟΣ / ΕΥΣΤΟΧΙΑ / ΥΠΟΛΟΙΠΟ.
  ΕΚΠΑΙΔΕΥΣΗ μονο E2021-E2024 (χωρις αποδοσεις): (υπολοιπο ματς − μεριδιο × γραμμη κλεισιματος) ~ σταθερα + ρυθμος + ευστοχια + υπολοιπο
     → συντελεστες β και σ (τυπ. αποκλιση καταλοιπου). Μεριδια ποντων ανα σημειο επισης μονο απο E2021-24.
  ΔΙΚΗ ΜΑΣ live γραμμη = ποντοι ως τωρα + (1 − μεριδιο) × γραμμη κλεισιματος + σταθερα + β·κομματια.
  ΑΞΙΟΛΟΓΗΣΗ μονο E2025 (Crown in-play, η τελευταια γραμμη με σκορ = ακριβως το σκορ του σημειου):
     P(over) = Φ((δικη − live)/σ) · edge = P·αποδοση − 1 · bet στην πλευρα με edge ≥ κατωφλι {6, 8, 10}% (κυριο 8%) · push σε ακεραια.
     ΣΥΓΚΡΙΣΗ: ιδια γραμμη ΧΩΡΙΣ τα κομματια («κανονικο υπολοιπο», η αρχικη ιδεα) — δειχνει αν ο ρυθμος προσθετει.
     Κλιση (τελικο − live) ~ (δικη − live): > 0 με t ≥ 2 = η δικη μας γραμμη βλεπει κατι που η Crown δεν τιμολογει.
  ΠΕΡΝΑ (ανα σημειο): ROI > 0 στο 8% ΚΑΙ στο 6% ΚΑΙ στο 10% ΚΑΙ κλιση > 0 με t ≥ 2.
  ΠΕΡΙΟΡΙΣΜΟΣ: 1 σεζον in-play → το καλυτερο δυνατο = ΣΚΙΑ (EuroCup χωρις pbp, φετος χωρις in-play Nowgoal).
Εξοδος: el_live_pace_test_out.txt"""
import sys, io, contextlib
import numpy as np
from statistics import NormalDist
Phi = NormalDist().cdf
src = open('el_half_luck_test.py', encoding='utf-8').read()
A = src.split("def ols(X, y):")[0]
A = A.replace("sc2=score_at(2), swap=swap", "sc2=score_at(2), sc3=score_at(3), swap=swap")
A = A.replace("for nq in (1, 2):\n    fr = ", "for nq in (1, 2, 3):\n    fr = ").replace("SH = {1: None, 2: None}\nrows = {1: [], 2: []}", "SH = {}\nrows = {1: [], 2: [], 3: []}")
A = A.replace("SEAS = ['E2021', 'E2022', 'E2023', 'E2024', 'E2025']", "SEAS = ['E2021', 'E2022', 'E2023', 'E2024', 'E2025', 'E2026']")
assert "'E2025', 'E2026']" in A
assert "sc3=score_at(3)" in A and "for nq in (1, 2, 3):" in A and "rows = {1: [], 2: [], 3: []}" in A
B = src.split("# ---- ΒΗΜΑ Β: live γραμμη Crown ----")[1].split("P('\\n=== ΒΗΜΑ Β")[0]      # live_at, settle
class _B(io.StringIO):
    def reconfigure(self, **k): pass
NS = {}
with contextlib.redirect_stdout(_B()): exec(A, NS); exec(B, NS)
sys.stdout.reconfigure(encoding='utf-8')
rows, live_at, settle = NS['rows'], NS['live_at'], NS['settle']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def save(): open('el_live_pace_test_out.txt' if TEST == 'E2025' else f'el_live_pace_test_{TEST}_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
TRAIN = ('E2021', 'E2022', 'E2023', 'E2024'); TEST = sys.argv[1] if len(sys.argv) > 1 else 'E2025'   # 29/10: E2026 = 2η ανεξαρτητη σεζον, ΙΔΙΟΙ συντελεστες
NM = {1: 'ΤΕΛΟΣ 1ης ΠΕΡΙΟΔΟΥ', 2: 'ΗΜΙΧΡΟΝΟ', 3: 'ΤΕΛΟΣ 3ης ΠΕΡΙΟΔΟΥ'}
K = ('pace', 'shoot', 'rest')
P(f'ΔΙΚΗ live γραμμη με ρυθμο vs Crown · εκπαιδευση E2021-24 · αξιολογηση {TEST} (δεν την ειδε η εκπαιδευση)')
for nq in (1, 2, 3):
    R = rows[nq]; Tr = [r for r in R if r['g']['sea'] in TRAIN]; Te = [r for r in R if r['g']['sea'] == TEST]
    fr = np.mean([r['pts'] / r['g']['tot'] for r in Tr])
    y = np.array([(r['g']['tot'] - r['pts']) - (1 - fr) * r['g']['L'] for r in Tr])
    X = np.column_stack([np.ones(len(Tr))] + [np.array([r[k] for r in Tr]) for k in K])
    b, *_ = np.linalg.lstsq(X, y, rcond=None); sig = (y - X @ b).std(); sig0 = (y - y.mean()).std()
    P(f'\n## {NM[nq]} · μεριδιο ποντων ως εδω {fr * 100:.1f}% (εκπαιδευση {len(Tr)} ματς)')
    P(f'  συντελεστες (εκπαιδευση): σταθερα {b[0]:+.2f} · ρυθμος {b[1]:+.3f} · ευστοχια {b[2]:+.3f} · υπολοιπο {b[3]:+.3f} · σ υπολοιπου ματς {sig:.1f} π. (χωρις κομματια {sig0:.1f})')
    Bt = []
    for r in Te:
        g = r['g']; lv = live_at(g, {1: g['sc1'], 2: g['sc2'], 3: g['sc3']}[nq])
        if not lv: continue
        base = r['pts'] + (1 - fr) * g['L']
        F = base + b[0] + sum(b[j + 1] * r[k] for j, k in enumerate(K)); F0 = base + y.mean()
        Bt.append(dict(r=r, Lv=lv[0], oo=lv[1], ou=lv[2], F=F, F0=F0, tot=g['tot']))
    P(f'  αξιολογηση {TEST}: ματς με live γραμμη στο σκορ του σημειου {len(Bt)} / {len(Te)} · γκανιοτα {np.mean([1 / x["oo"] + 1 / x["ou"] - 1 for x in Bt]) * 100:.1f}%')
    yy = np.array([x['tot'] - x['Lv'] for x in Bt])
    res = {}
    for lab, fk, sg in (('ΜΕ ΡΥΘΜΟ (δικη γραμμη)', 'F', sig), ('ΧΩΡΙΣ κομματια (κανονικο υπολοιπο)', 'F0', sig0)):
        d = np.array([x[fk] - x['Lv'] for x in Bt])
        sl = np.polyfit(d, yy, 1)[0]; rr = np.corrcoef(d, yy)[0, 1]; t = sl / (np.sqrt((1 - rr * rr) / (len(d) - 2)) * yy.std() / d.std())
        P(f'  {lab}: δικη − live: μεσος {d.mean():+.2f} π., τυπ. {d.std():.2f} · κλιση (τελικο − live) ~ (δικη − live) {sl:+.2f} (t {t:+.1f})')
        line = []
        for th in (.06, .08, .10):
            U = []
            for x in Bt:
                po = Phi((x[fk] - x['Lv']) / sg); eo = po * x['oo'] - 1; eu = (1 - po) * x['ou'] - 1
                if max(eo, eu) < th: continue
                side, od = ('O', x['oo']) if eo >= eu else ('U', x['ou'])
                U.append((settle(x['tot'], x['Lv'], side, od), side))
            if not U: line.append(f'≥{th * 100:.0f}%: —'); res[(lab, th)] = None; continue
            u = np.array([a for a, _ in U]); res[(lab, th)] = u.mean()
            no = sum(s == 'O' for _, s in U); uo = [a for a, s in U if s == 'O']; uu = [a for a, s in U if s == 'U']
            line.append(f'≥{th * 100:.0f}%: {len(u)} bets ROI {u.mean() * 100:+.1f}% (±{u.std() / np.sqrt(len(u)) * 100:.1f}) {u.sum():+.1f}μ [over {no} {np.mean(uo) * 100 if uo else 0:+.0f}% · under {len(uu)} {np.mean(uu) * 100 if uu else 0:+.0f}%]')
        for l_ in line: P(f'     {l_}')
        res[(lab, 'slope')] = (sl, t)
    lab = 'ΜΕ ΡΥΘΜΟ (δικη γραμμη)'; sl, t = res[(lab, 'slope')]
    ok = all(res.get((lab, th)) is not None and res[(lab, th)] > 0 for th in (.06, .08, .10)) and sl > 0 and t >= 2
    P(f'  ΚΡΙΣΗ (ROI > 0 στο 6/8/10% ΚΑΙ κλιση > 0 με t ≥ 2): {"✓ ΠΕΡΝΑ (→ μονο ΣΚΙΑ, 1 σεζον)" if ok else "✗ ΔΕΝ ΠΕΡΝΑ"}')
    save()
save()

# ---- ΠΡΟΣΘΗΚΗ ΜΕΤΑ ΤΗΝ ΕΚΤΕΛΕΣΗ (μονο πλαισιο, εκτος κρισης): ΗΜΙΧΡΟΝΟ ≥8% — απο που ερχεται; ----
P('\n=== ΠΛΑΙΣΙΟ (μετα την κριση): ΗΜΙΧΡΟΝΟ, bets ≥8% με ρυθμο ===')
nq = 2; R = rows[nq]; Tr = [r for r in R if r['g']['sea'] in TRAIN]; Te = [r for r in R if r['g']['sea'] == TEST]
fr = np.mean([r['pts'] / r['g']['tot'] for r in Tr])
y = np.array([(r['g']['tot'] - r['pts']) - (1 - fr) * r['g']['L'] for r in Tr])
X = np.column_stack([np.ones(len(Tr))] + [np.array([r[k] for r in Tr]) for k in K]); b, *_ = np.linalg.lstsq(X, y, rcond=None); sig = (y - X @ b).std()
L8 = []
for r in Te:
    g = r['g']; lv = live_at(g, g['sc2'])
    if not lv: continue
    F = r['pts'] + (1 - fr) * g['L'] + b[0] + sum(b[j + 1] * r[k] for j, k in enumerate(K))
    po = Phi((F - lv[0]) / sig); eo = po * lv[1] - 1; eu = (1 - po) * lv[2] - 1
    if max(eo, eu) < .08: continue
    side, od = ('O', lv[1]) if eo >= eu else ('U', lv[2])
    L8.append(dict(u=settle(g['tot'], lv[0], side, od), side=side, tip=g['tip'], pc=b[1] * r['pace'] + b[3] * r['rest'], g=g, r=r, lv=lv, F=F))
L8.sort(key=lambda x: x['tip']); h = len(L8) // 2
def st(Z): u = np.array([z['u'] for z in Z]); return f'{len(u)} bets ROI {u.mean() * 100:+.1f}% {u.sum():+.1f}μ' if len(u) else '—'
P(f'  1ο μισο σεζον {st(L8[:h])} · 2ο μισο {st(L8[h:])}')
P(f'  ο ρυθμος+υπολοιπο σπρωχνουν τη γραμμη μας ≥ +1 π. {st([z for z in L8 if z["pc"] >= 1])} · ≤ −1 π. {st([z for z in L8 if z["pc"] <= -1])} · σχεδον τιποτα (|.|<1) {st([z for z in L8 if abs(z["pc"]) < 1])}')
import pandas as pd
for z in L8[:3] + [z for z in L8 if abs(z['pc']) >= 2][:3]:
    g = z['g']; P(f'  π.χ. {pd.Timestamp(g["tip"], unit="s").date()} {g["teams"][0]}–{g["teams"][1]}: κλεισιμο {g["L"]} · ημιχρ. {z["r"]["pts"]} · ρυθμος {z["r"]["pace"]:+.1f} π. · δικη {z["F"]:.1f} vs live {z["lv"][0]} → {z["side"]} · τελικο {g["tot"]} → {z["u"]:+.2f}μ')
save()
