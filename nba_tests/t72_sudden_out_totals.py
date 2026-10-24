# -*- coding: utf-8 -*-
"""t72_sudden_out_totals.py — ΑΙΦΝΙΔΙΑ OUT ΣΤΑ ΣΥΝΟΛΑ (με εμφαση στους ΑΜΥΝΤΙΚΟΥΣ) (24/10/2026, Στελιος «τρεξ'το και χωρισε σε ωρες — μετα τις 1-2 τα
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
Εξοδος: nba_tests/t72_sudden_out_totals_out.txt"""
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
    if r.kind != 'out' or r.st0 not in ('καθολου', 'Available') or abs(r.tt) < 0.3: continue
    c = at_t(r.i, r.tip); F0 = at_t(r.i, r.t0)
    if c is None or F0 is None: continue
    sgn = 1.0 if r.tt > 0 else -1.0                      # +1 over · −1 under
    base = F0['fair']; mv = lambda x: sgn * (x['fair'] - base)
    hh = dt.datetime.fromtimestamp(r.t0, ATH).hour
    rec = dict(S=r.S, st0=r.st0, val=abs(r.tt), side='OVER' if sgn > 0 else 'UNDER', tweet=r.src != 'NBC', hrs=r.hrs, gr=hh, close=mv(c), real=sgn * (TOT[r.i] - base))
    for k in KS:
        if r.t0 + k * 60 > r.tip: continue
        x = at_t(r.i, r.t0 + k * 60)
        if x is None: continue
        od = x['oo'] if sgn > 0 else x['ou']; rr = (TOT[r.i] - x['T']) * sgn
        rec[f'r{k}'] = (od - 1) if rr > 0 else (0.0 if rr == 0 else -1.0); rec[f'c{k}'] = mv(c) - mv(x); rec[f'm{k}'] = mv(x)
    R.append(rec)
E = pd.DataFrame(R)
def cell(x, k):
    x = x.dropna(subset=[f'r{k}'])
    if not len(x): return '—'
    ps = x.groupby('S')[f'r{k}'].mean()
    return f"{100 * x[f'r{k}'].mean():+6.1f}% ({len(x):4d}, {x[f'r{k}'].sum():+6.1f}μ, {int((ps > 0).sum())}/{x.S.nunique()}) CLV {x[f'c{k}'].mean():+.2f}π"
P(f'NBA ΣΥΝΟΛΑ · ΑΙΦΝΙΔΙΑ OUT · NBC 2021-26 · |αξια συνολου| ≥0.3 π. · {len(E)} ειδησεις (OVER {int((E.side == "OVER").sum())}, UNDER {int((E.side == "UNDER").sum())}) '
  f'(καθολου {int((E.st0 == "καθολου").sum())}, Available {int((E.st0 == "Available").sum())}) · με ωρα tweet {100 * E.tweet.mean():.0f}%')
P(f'  αγορα: κινηση ως το κλεισιμο {E.close.mean():+.2f} π. · πραγματικη επιπτωση {E.real.mean():+.2f} ± {E.real.std() / np.sqrt(len(E)):.2f} π. · μεση αξια {E.val.mean():.2f}')
P('  κινηση γραμμης απο τη στιγμη της ειδησης: ' + ' · '.join(f'+{k}′ {E[f"m{k}"].mean():+.2f}' for k in KS) + f' · κλεισιμο {E.close.mean():+.2f}')
P('\n=== ΠΟΝΤΟΣ ΣΤΗΝ ΚΑΤΕΥΘΥΝΣΗ ΤΗΣ ΑΞΙΑΣ ΣΥΝΟΛΟΥ (ROI · ποντοι · μοναδες · θετικες σεζον · CLV) ===')
for k in KS: P(f'  +{k:<2d}′  {cell(E, k)} · ανα σεζον ' + ' '.join(f'{s % 100}:{100 * v:+.0f}%' for s, v in E.dropna(subset=[f"r{k}"]).groupby("S")[f"r{k}"].mean().items()))
P('\n=== ΥΠΟΣΥΝΟΛΑ (+5′) ===')
for lab, m in (('ΜΟΝΟ OVER (αμυντικοι)', E.side == 'OVER'), ('ΜΟΝΟ UNDER (επιθετικοι)', E.side == 'UNDER'), ('OVER αξια ≥0.6', (E.side == 'OVER') & (E.val >= 0.6)), ('ΜΕ ακριβη ωρα tweet', E.tweet), ('μονο ωρα NBC', ~E.tweet), ('ηταν ΚΑΘΟΛΟΥ στην αναφορα', E.st0 == 'καθολου'), ('ηταν Available', E.st0 == 'Available'),
               ('αξια 0.3-0.6 π.', E.val < 0.6), ('αξια ≥0.6 π.', E.val >= 0.6),
               ('<1ω πριν το ματς', E.hrs < 1), ('1-3ω πριν', (E.hrs >= 1) & (E.hrs < 3)), ('3-12ω πριν', (E.hrs >= 3) & (E.hrs < 12)), ('≥12ω πριν', E.hrs >= 12)):
    P(f'  {lab:26s} {cell(E[m], 5)}')
P('\n=== ΩΡΑ ΕΛΛΑΔΑΣ ΤΗΣ ΕΙΔΗΣΗΣ (μεριδιο · +5′ · +15′) ===')
BINS = ((8, 14, '08:00-14:00'), (14, 20, '14:00-20:00'), (20, 24, '20:00-24:00'), (0, 2, '00:00-02:00'), (2, 8, '02:00-08:00'))
for lo, hi, lab in BINS:
    x = E[(E.gr >= lo) & (E.gr < hi)]
    P(f'  {lab}  {100 * len(x) / len(E):4.0f}% των ειδησεων · +5′ {cell(x, 5)} · +15′ {cell(x, 15)}')
aw = (E.gr >= 8) | (E.gr < 2)
P(f'  ΞΥΠΝΙΟΣ (08:00-02:00)  {100 * aw.mean():4.0f}% · +5′ {cell(E[aw], 5)} · +15′ {cell(E[aw], 15)}')
P(f'  ΝΥΧΤΑ   (02:00-08:00)  {100 * (~aw).mean():4.0f}% · +5′ {cell(E[~aw], 5)} · +15′ {cell(E[~aw], 15)}')
x = E.dropna(subset=['r5']); ps = x.groupby('S').r5.mean(); xt = x[x.tweet]
ok = len(x) >= 150 and x.r5.mean() > 0 and x.c5.mean() > 0 and (ps > 0).sum() >= 4
P(f'\nΚΡΙΤΗΡΙΟ (+5′): n {len(x)} (≥150) · ROI {100 * x.r5.mean():+.1f}% (>0) · CLV {x.c5.mean():+.2f} (>0) · θετικες σεζον {int((ps > 0).sum())}/5 (≥4) · '
  f'ROI με tweet {100 * xt.r5.mean():+.1f}% (>0) → {"ΠΕΡΝΑΕΙ" if ok else "ΔΕΝ ΠΕΡΝΑΕΙ"}')
open(os.path.join(SC, 't72_sudden_out_totals_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
