# -*- coding: utf-8 -*-
"""t73_totals_out_fade.py — ΣΥΝΟΛΑ: OUT ΕΠΙΘΕΤΙΚΟΥ → OVER (κοντρα στην υπερ-αντιδραση) · OUT ΑΜΥΝΤΙΚΟΥ → OVER (24/10/2026, Στελιος «τρεξ'το και χωρισε σε ωρες — μετα τις 1-2 τα
ξημερωματα σπανια θα ειμαι ον»). Συνεχεια των t50/t51/t53 (το «επομενο: κανονικο τεστ για αιφνιδια Out» δεν ειχε τρεξει).
ΕΙΔΗΣΕΙΣ: ιδιες με t50 (NBC 2021-26 με ωρα αρχικου tweet οπου υπαρχει, ομαδα απο box score, παικτης ρολου ≥20′, ματς ≤36ω, ΜΟΝΟ ΝΕΑ σε
  σχεση με την επισημη αναφορα ως τη στιγμη της ειδησης). ΑΙΦΝΙΔΙΟ OUT = «εκτος» ενω στην αναφορα ηταν ΚΑΘΟΛΟΥ ή Available.
  Αξια χαντικαπ 0.75·(αξια+2)·λεπτα/48 ≥ 0.3 π. (οπως t50). Τιμες Crown (nowgoal), ποντος στην πλευρα ΚΟΝΤΡΑ στην ομαδα που χανει τον παικτη.
ΣΤΙΓΜΕΣ: ειδηση +1′ / +3′ / +5′ / +8′ / +15′.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ (πριν το τρεξιμο): ΚΥΡΙΑ στιγμη = +5′ (ρεαλιστικο: alert → ποντος). ΠΕΡΝΑ αν n ≥ 200 ΚΑΙ ROI > 0 ΚΑΙ CLV > 0
  ΚΑΙ θετικο ROI σε ≥4/5 σεζον ΚΑΙ ROI > 0 και στο υποσυνολο με ΑΚΡΙΒΗ ωρα tweet (απαντηση στην αμφιβολια του t51).
ΩΡΑ ΕΛΛΑΔΑΣ της ειδησης (Europe/Athens): 08-14 · 14-20 · 20-24 · 00-02 · 02-08 → μεριδιο ειδησεων + ROI· «ξυπνιος» = 08:00-02:00.
ΣΥΝΟΛΑ (24/10/2026, Στελιος «τρεξε τα τεστ»): ιδιες ειδησεις με t70 (αιφνιδια Out: καθολου/Available στην αναφορα). Αξια συνολου ανα παικτη
  = −0.5·(επιθ+0.5)·λεπτα/48 + 1.0·(αμυνα+0.5)·λεπτα/48 (οπως live/t50): + = χανεται κυριως ΑΜΥΝΑ → περισσοτεροι ποντοι → OVER · − = UNDER.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (πριν το τρεξιμο): |αξια συνολου| ≥ 0.3 π., ποντος στην κατευθυνση της αξιας στο +5′ (κυριο). ΠΕΡΝΑ αν n ≥ 150 ΚΑΙ ROI > 0 ΚΑΙ
  CLV > 0 ΚΑΙ θετικο σε ≥4/5 σεζον. Χωριστα (πληροφορια): μονο OVER (αμυντικοι) · μονο UNDER (επιθετικοι) · ωρα Ελλαδας.
t73 (24/10/2026, Στελιος «κανε το 2»): οι 2 ιδεες βγηκαν ΜΕΤΑ το t72 (αιφνιδια Out) → εκει ειναι «εντος δειγματος».
  ΑΝΕΞΑΡΤΗΤΟΣ ελεγχος = ΙΔΙΟΣ μηχανισμος σε ΑΛΛΕΣ ειδησεις: Out ενω η αναφορα τον ειχε Questionable / Doubtful / Probable (δεν χρησιμοποιηθηκαν στο t72).
  Κ1 ΕΠΙΘΕΤΙΚΟΣ (αξια συνολου ≤ −0.3 π.) → OVER · κυρια στιγμη = ΚΛΕΙΣΙΜΟ (αφου η αγορα εχει ηδη κατεβει) · επισης +5′ / +15′.
  Κ2 ΑΜΥΝΤΙΚΟΣ (αξια ≥ +0.3 π.) → OVER · κυρια στιγμη = +5′ · επισης +15′ / κλεισιμο.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (πριν το τρεξιμο), ΣΤΟ ΑΝΕΞΑΡΤΗΤΟ δειγμα: καθε κανονας ΠΕΡΝΑ αν n ≥ 150 ΚΑΙ ROI > 0 ΚΑΙ θετικο σε ≥4/5 σεζον.
Το εντος-δειγματος (αιφνιδια) τυπωνεται μονο για συγκριση. Εξοδος: nba_tests/t73_totals_out_fade_out.txt"""
import os, sys, io, contextlib, datetime as dt
from zoneinfo import ZoneInfo
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
_src = open(os.path.join(SC, 't50_news_5s.py'), encoding='utf-8').read().split('KS = (-15, 0, 1, 8, 15, 30)')[0]
_src = _src.replace("out = []\ndef P(s=''): print(s, flush=True); out.append(str(s))", "def P(s=''): pass")
G_ = {'__file__': os.path.join(SC, 't50_news_5s.py'), '__name__': 't50'}
with contextlib.redirect_stdout(_B()): exec(_src, G_)
sys.stdout.reconfigure(encoding='utf-8')
np, pd, D, at_t, TOT = G_['np'], G_['pd'], G_['D'], G_['at_t'], G_['TOT']
ATH = ZoneInfo('Europe/Athens')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
KS = (1, 3, 5, 8, 15)
R = []
for r in D.itertuples(index=False):
    if r.kind != 'out' or abs(r.tt) < 0.3: continue
    grp = 'ΑΝΕΞΑΡΤΗΤΟ' if r.st0 in ('Questionable', 'Doubtful', 'Probable') else ('εντος (αιφνιδια)' if r.st0 in ('καθολου', 'Available') else None)
    if grp is None: continue
    c = at_t(r.i, r.tip); F0 = at_t(r.i, r.t0)
    if c is None or F0 is None: continue
    rec = dict(S=r.S, grp=grp, st0=r.st0, kind='ΕΠΙΘΕΤΙΚΟΣ' if r.tt < 0 else 'ΑΜΥΝΤΙΚΟΣ', val=abs(r.tt), mv_close=-(c['fair'] - F0['fair']), real=TOT[r.i] - F0['fair'])
    for lab, ts in (('+5′', r.t0 + 300), ('+15′', r.t0 + 900), ('κλεισιμο', None)):
        x = c if ts is None else (at_t(r.i, ts) if ts <= r.tip else None)
        if x is None: continue
        rr = TOT[r.i] - x['T']; rec[lab] = (x['oo'] - 1) if rr > 0 else (0.0 if rr == 0 else -1.0)
        rec['clv' + lab] = c['fair'] - x['fair']                              # κλεισιμο − στιγμη, προς το OVER
    R.append(rec)
E = pd.DataFrame(R)
def cell(x, k):
    x = x.dropna(subset=[k])
    if not len(x): return '—', 0, 0, 0
    ps = x.groupby('S')[k].sum()
    return (f"{100 * x[k].mean():+6.1f}% ({len(x):4d}, {x[k].sum():+6.1f}μ, {int((ps > 0).sum())}/{x.S.nunique()}) CLV {x['clv' + k].mean():+.2f}π · ανα σεζον "
            + ' '.join(f'{s % 100}:{100 * x[x.S == s][k].mean():+.0f}%' for s in sorted(x.S.unique())), len(x), 100 * x[k].mean(), int((ps > 0).sum()))
P(f'NBA ΣΥΝΟΛΑ · OUT → OVER · NBC 2021-26 · |αξια συνολου| ≥0.3 π. · {len(E)} ειδησεις')
for grp in ('ΑΝΕΞΑΡΤΗΤΟ', 'εντος (αιφνιδια)'):
    P(f'\n=== {grp} ===')
    for kind in ('ΕΠΙΘΕΤΙΚΟΣ', 'ΑΜΥΝΤΙΚΟΣ'):
        x = E[(E.grp == grp) & (E.kind == kind)]
        if not len(x): continue
        P(f'  {kind} εκτος → OVER · n {len(x)} · η αγορα κατεβαινει (ανοιγμα ειδησης→κλεισιμο) {x.mv_close.mean():+.2f} π. · πραγματικο − γραμμη τη στιγμη της ειδησης {x.real.mean():+.2f} ± {x.real.std() / np.sqrt(len(x)):.2f}')
        for k in ('+5′', '+15′', 'κλεισιμο'): P(f'     {k:9s} {cell(x, k)[0]}')
    if grp == 'ΑΝΕΞΑΡΤΗΤΟ':
        for st in ('Questionable', 'Doubtful', 'Probable'):
            x = E[(E.grp == grp) & (E.st0 == st)]
            P(f'  (ανα κατασταση {st}: επιθ. κλεισιμο {cell(x[x.kind == "ΕΠΙΘΕΤΙΚΟΣ"], "κλεισιμο")[0][:40]} · αμυντ. +5′ {cell(x[x.kind == "ΑΜΥΝΤΙΚΟΣ"], "+5′")[0][:40]})')
x = E[E.grp == 'ΑΝΕΞΑΡΤΗΤΟ']
_, n1, r1, p1 = cell(x[x.kind == 'ΕΠΙΘΕΤΙΚΟΣ'], 'κλεισιμο'); _, n2, r2, p2 = cell(x[x.kind == 'ΑΜΥΝΤΙΚΟΣ'], '+5′')
P(f'\nΚΡΙΤΗΡΙΟ (ανεξαρτητο): Κ1 επιθετικος → OVER στο κλεισιμο: n {n1} · ROI {r1:+.1f}% · θετικες {p1}/5 → {"ΠΕΡΝΑΕΙ" if n1 >= 150 and r1 > 0 and p1 >= 4 else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
P(f'                       Κ2 αμυντικος → OVER στο +5′: n {n2} · ROI {r2:+.1f}% · θετικες {p2}/5 → {"ΠΕΡΝΑΕΙ" if n2 >= 150 and r2 > 0 and p2 >= 4 else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
open(os.path.join(SC, 't73_totals_out_fade_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
