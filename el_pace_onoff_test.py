# -*- coding: utf-8 -*-
"""el_pace_onoff_test.py — EUROLEAGUE ΣΥΝΟΛΑ: «ΡΥΘΜΟΣ ΑΠΟΝΤΩΝ» (25/10/2026, Στελιος «τρεξτο»).
Αφορμη: Ολυμπιακος–Φενερ 23/10 (χωρις Fournier/Dorsey/Montero) 67.5 κατοχες vs ~76.7 μεσος του ΟΣΦ, 125 ποντοι vs μοντελο 172 (pick over 171).
Το live on/off (el_onoff_prev, W4) μετραει ΠΟΝΤΟΥΣ ΑΝΑ 100 ΚΑΤΟΧΕΣ με/χωρις τον παικτη — ΟΧΙ ποσο γρηγορα παιζει η ομαδα.
ΝΕΟ: ρυθμος on/off παικτη = κατοχες ομαδας ανα 40′ ΟΣΟ ΕΙΝΑΙ ΜΕΣΑ − ΟΣΟ ΕΙΝΑΙ ΕΞΩ (3StepsBasket, ΜΟΝΟ η ΠΡΟΗΓΟΥΜΕΝΗ σεζον,
  Ευρωλιγκα + EuroCup), μαζεμα προς 0 × n/(n+1500) (n = αρμονικος κατοχων μεσα/εξω, ιδιο με το on/off).
Ματς: F = Σ (και των δυο ομαδων) w × z(ρυθμος), w = λεπτα/40 × (1 πληρες k 1-3 · ½ k 4-10) — ιδιος ορισμος απουσιας με το live.
ΜΟΝΤΕΛΟ: συνολο = live (μοντελο + W4 on/off, LOSO) + c·F· c με ridge στις αλλες σεζον (LOSO). Αναμενομενο c < 0.
ΠΡΟ-ΔΗΛΩΜΕΝΑ (εγκριθηκαν πριν): ΠΕΡΝΑ αν LOSO RMSE συνολου καλυτερο απο το live σε ≥4/5 ΚΑΙ c ιδιο προσημο ≥4/5 ΚΑΙ μοναδες picks
  συνολων (≥8% ανοιγμα) ≥ live ΚΑΙ ΕΠΙΒΕΒΑΙΩΣΗ EuroCup: σωστο προσημο (<0) ≥4/5 σεζον & t ≤ −2.
ΔΙΟΡΘΩΣΗ (πριν την αναφορα): 2020-21 Ευρωλιγκα & EuroCup η πηγη εχει ελλιπη λεπτα ομαδας (22-27′/ματς) → λεπτα ομαδας = 40.3 × ματς οταν < 39′/ματς.
Εξοδος: el_pace_onoff_out.txt"""
import sys, io, re, contextlib
import numpy as np
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open('el_absence_onoff_test.py', encoding='utf-8').read().split("open('el_absence_onoff_out.txt'")[0]
rep = [
 ("            n = 1 / (1 / tpo + 1 / (op - tpo)); sh = n / (n + K_SHR)\n",
  "            n = 1 / (1 / tpo + 1 / (op - tpo)); sh = n / (n + K_SHR)\n"
  "            tmin = t['secondsPlayed'] / 60 / 5; tmin = tmin if tmin >= 39 * tg else 40.3 * tg; mon = (p.get('mins') or 0) * g * sc; moff = tmin - mon\n"
  "            pace = (40 * tpo / mon - 40 * (op - tpo) / moff) if (mon > 50 and moff > 50) else 0.0\n"),
 ("p.get('usgRate', 0) * tpo, 0, 0, 0])", "p.get('usgRate', 0) * tpo, pace * sh * tpo, 0, 0])"),
 ("    return dict(onO=v[0] / v[2], onD=v[1] / v[2], usg=v[3] / v[2])", "    return dict(onO=v[0] / v[2], onD=v[1] / v[2], usg=v[3] / v[2], pace=v[4] / v[2])"),
 ("dict(onO=0.0, onD=0.0, usg=None)", "dict(onO=0.0, onD=0.0, usg=None, pace=0.0)"),
 ("def P(s=''): print(s, flush=True); out.append(str(s))", "def P(s=''): pass"),
]
for a, b in rep:
    assert src.count(a) == 1, a[:50]; src = src.replace(a, b)
ns = {}
with contextlib.redirect_stdout(_B()): exec(src, ns)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
rows, HELD, YT, ys, SE, EC, tpicks, rmse = ns['rows'], ns['HELD'], ns['YT'], ns['ys'], ns['SE'], ns['EC'], ns['tpicks'], ns['rmse']
allp = [p for r in rows for p in r['ah'] + r['aa'] if p['usg'] is not None]
SDP = float(np.std([p['pace'] for p in allp]))
P(f'Ευρωλιγκα 2021-25: ματς {len(rows)} · ρυθμος on/off (μετα το μαζεμα) τυπ. αποκλιση {SDP:.2f} κατοχες/40′ · απουσιες με προφιλ {len(allp)}')
F = np.array([sum(p['w'] * p['pace'] / SDP for p in r['ah'] + r['aa']) for r in rows])
P(f'F (ανα ματς): μη μηδενικο σε {int((np.abs(F) > 1e-9).sum())} ματς · 90% μεταξυ {np.percentile(F, 5):+.2f} και {np.percentile(F, 95):+.2f}')
W4 = HELD['W4 μονο on/off']; R0 = YT - W4
cfit = lambda m: float((F[m] @ R0[m]) / (F[m] @ F[m] + 1.0))
call = cfit(np.ones(len(rows), bool)); per = {s: cfit(ys == s) for s in SE}
same = sum(1 for v in per.values() if np.sign(v) == np.sign(call))
hh = np.zeros(len(rows))
for Y in SE: hh[ys == Y] = cfit(ys != Y) * F[ys == Y]
P(f'\n## c (ποντοι συνολου ανα 1 τυπ. αποκλιση ρυθμου × 40′ απουσιας) {call:+.2f} · ανα σεζον ' + ' '.join(f'{s[-2:]}:{v:+.2f}' for s, v in per.items()) + f' (ιδιο προσημο {same}/5, αναμενομενο <0)')
d = [rmse(R0 - hh, ys == s) - rmse(R0, ys == s) for s in SE]
P(f'## LOSO RMSE συνολου: live (W4) {rmse(R0, ys == ys):.3f} → +ρυθμος {rmse(R0 - hh, ys == ys):.3f} · ανα σεζον ' + ' '.join(f'{x:+.3f}' for x in d) + f' → καλυτερο {sum(x < 0 for x in d)}/5')
u0, s0 = tpicks(W4); u1, s1 = tpicks(W4 + hh)
P(f'## PICKS συνολων ≥8% ανοιγμα\n   live (W4)     {s0}\n   + ρυθμος      {s1}')
EL_OK = sum(x < 0 for x in d) >= 4 and same >= 4 and call < 0 and u1 >= u0
# ---- EuroCup επιβεβαιωση: ποντοι ομαδας − απλη βαση ~ σταθερα, εδρα, λεπτα, on/off, + ρυθμος (και των δυο ομαδων) ----
er, EY, Ey, EX = ns['er'], ns['EY'], ns['Ey'], ns['EX']
FE = np.array([sum(p['w'] * p['pace'] / SDP for p in e[3] + e[4]) for e in er])
EX2 = np.c_[EX[:, :6], FE]
def ols(m):
    Xm, Ym = EX2[m], EY[m]; b = np.linalg.lstsq(Xm, Ym, rcond=None)[0]; r_ = Ym - Xm @ b
    se = np.sqrt(np.diag(np.sum(r_ ** 2) / (len(Ym) - Xm.shape[1]) * np.linalg.inv(Xm.T @ Xm))); return b, se
b, se = ols(np.ones(len(EY), bool)); okc = 0
P(f'\n## ΕΠΙΒΕΒΑΙΩΣΗ EuroCup 2021-25 · ομαδα-ματς {len(EY)} · ρυθμος {b[6]:+.2f} ποντοι ομαδας (t {b[6] / se[6]:+.1f})')
for s in EC:
    bb, _ = ols(Ey == s); okc += bb[6] < 0; P(f'    {s}: {bb[6]:+.2f}')
EC_OK = okc >= 4 and b[6] / se[6] <= -2
P(f'   σωστο προσημο (<0) {okc}/5 · t {b[6] / se[6]:+.1f} → ' + ('ΕΠΙΒΕΒΑΙΩΝΕΤΑΙ' if EC_OK else 'ΔΕΝ επιβεβαιωνεται'))
P(f'\nΚΡΙΤΗΡΙΑ: RMSE {sum(x < 0 for x in d)}/5 (≥4) · προσημο c {same}/5 & <0 · μοναδες {u1:+.1f} vs {u0:+.1f} · EuroCup {"✓" if EC_OK else "✗"} → '
  + ('ΠΕΡΝΑΕΙ' if EL_OK and EC_OK else 'ΔΕΝ ΠΕΡΝΑΕΙ'))
# ---- παραδειγμα: Ολυμπιακος–Φενερ 23/10/2026 (προφιλ 2025-26) ----
prof = ns['profile']
P('\n## ΠΑΡΑΔΕΙΓΜΑ Ολυμπιακος–Φενερ 23/10/2026 (ρυθμος on/off 2025-26, μετα το μαζεμα):')
Fx = 0.0
for nm, mn in (('Fournier, Evan', 24), ('Dorsey, Tyler', 18), ('Montero, Jean', 26)):
    pr = prof(nm, 2026)
    if pr: w = mn / 40; Fx += w * pr['pace'] / SDP; P(f'   {nm:16s} {mn}′ · ρυθμος on/off {pr["pace"]:+.2f} κατοχες/40′ · συνεισφορα στο F {w * pr["pace"] / SDP:+.2f}')
    else: P(f'   {nm:16s} χωρις προφιλ')
P(f'   F {Fx:+.2f} → διορθωση συνολου με c {call:+.2f}: {call * Fx:+.1f} ποντοι (μοντελο 172.0 → {172.0 + call * Fx:.1f} · κλεισιμο 166.5 · αποτελεσμα 125)')
open('el_pace_onoff_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
