# -*- coding: utf-8 -*-
"""ucl_first_seen_day.py — CHAMPIONS LEAGUE: ΑΠΟΤΕΛΕΣΜΑ ΑΝΑ ΜΕΡΑ/ΩΡΑ ΠΟΥ ΠΡΩΤΟΒΓΗΚΕ ΤΟ PICK (13/10/2026, Στελιος: «θελω το τεστ να δειχνει
οταν πρωτοβγηκε το καθε pick … picks που προεκυψαν την ιδια μερα» — αφορμη Arsenal–Lille under 3 (9.4ω πριν) & Atletico–United over 3 (12.6ω)).
Πηγη: ucl_bb_timing_alerts.pkl (ucl_bb_timing.py: σημερινοι κανονες, ΚΑΘΕ αλλαγη τιμης ≤72ω, Crown & SBOBET, πρωτη εμφανιση ανα ματς/πλευρα).
Ωρα Ελλαδας (Europe/Athens). Κουβαδες: ηδη στις 72ω · 3 μερες πριν · 2 μερες πριν · προηγουμενη μερα · ΙΔΙΑ ΜΕΡΑ πρωι (<12:00) / μεσημερι-απογευμα (≥12:00).
Για καθε κουβα: ROI στην τιμη που βγηκε · ROI αν περιμενα το κλεισιμο · κινηση αγορας ΠΡΙΝ (απο τις 72ω ως την εμφανιση) και ΜΕΤΑ (ως το κλεισιμο)
σε γκολ (+ = προς το pick, − = κοντρα) · % που βγηκαν μετα απο κοντρα ≥0.15.
Συνολα: ΝΕΑ ΜΟΡΦΗ 2024-26 (βαση του live κανονα)· χαντικαπ: ολες οι σεζον (+ νεα μορφη). Μεσος ορος 2 βιβλιων. ΠΕΡΙΓΡΑΦΙΚΟ.
Εξοδος: ucl_first_seen_day_out.txt"""
import sys, io, contextlib
import numpy as np, pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
sys.stdout.reconfigure(encoding='utf-8')
t = open('uel_timing.py', encoding='utf-8').read(); t = t[:t.index('HOURS = ')]
u = {'__name__': 'ut'}
with contextlib.redirect_stdout(io.StringIO()): exec(t.replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), u)
KO = u['KO']
ATH = ZoneInfo('Europe/Athens')
X = pd.read_pickle('ucl_bb_timing_alerts.pkl')
def bucket(r):
    ko = datetime.fromtimestamp(KO[r.mid], timezone.utc).astimezone(ATH)
    fs = datetime.fromtimestamp(KO[r.mid] - r.hrs * 3600, timezone.utc).astimezone(ATH)
    if r.at_open: return '0 ηδη στις 72ω'
    dd = (ko.date() - fs.date()).days
    if dd >= 3: return '1 3 μερες πριν'
    if dd == 2: return '2 2 μερες πριν'
    if dd == 1: return '3 προηγουμενη μερα'
    return '4 ΙΔΙΑ ΜΕΡΑ πρωι (<12:00)' if fs.hour < 12 else '5 ΙΔΙΑ ΜΕΡΑ 12:00+'
X['bk_'] = X.apply(bucket, axis=1)
X['ko_h'] = X.mid.map(lambda m: datetime.fromtimestamp(KO[m], timezone.utc).astimezone(ATH).hour)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d, col='pa'):
    if not len(d): return f'{"—":>30}'
    g = d.groupby('bk')[col]; ps = d.groupby('sea')[col].mean()
    return f'{100*g.mean().mean():+6.1f}% ({g.size().mean():3.0f}, {g.sum().mean():+5.1f}μ, {int((ps > 0).sum())}/{ps.size})'
def line(lab, d):
    if not len(d):
        P(f'  {lab:<26} —'); return
    P(f'  {lab:<26} {cell(d)} | {cell(d, "pc")} | {d.mv.mean():+.2f} | {d.mv_after.mean():+.2f} | {100*(d.mv <= -0.15).mean():3.0f}% | {d.o.mean():.2f}')
NAME = dict(fav='ΦΑΒΟΡΙ', dog='ΑΟΥΤΣΑΪΝΤΕΡ', over='OVER', under='UNDER')
LAB = {'0 ηδη στις 72ω': 'ηδη στις 72ω', '1 3 μερες πριν': '3 μερες πριν', '2 2 μερες πριν': '2 μερες πριν',
       '3 προηγουμενη μερα': 'προηγουμενη μερα', '4 ΙΔΙΑ ΜΕΡΑ πρωι (<12:00)': 'ΙΔΙΑ ΜΕΡΑ πρωι (<12:00)', '5 ΙΔΙΑ ΜΕΡΑ 12:00+': 'ΙΔΙΑ ΜΕΡΑ 12:00 ως σεντρα'}
P('CHAMPIONS LEAGUE · ΠΟΤΕ ΠΡΩΤΟΒΓΗΚΕ ΤΟ PICK (ωρα Ελλαδας) · μεσος Crown/SBOBET')
P('στηλες: ROI στην τιμη που βγηκε (picks, μοναδες, θετικες σεζον) | ROI αν περιμενα κλεισιμο | κινηση ΠΡΙΝ (72ω→εμφανιση) | κινηση ΜΕΤΑ (→κλεισιμο) | % μετα απο κοντρα ≥0.15 | μεση αποδοση')
P('κινηση σε γκολ: + = η αγορα ηρθε ΠΡΟΣ το pick · − = πηγε ΚΟΝΤΡΑ')
for m, scopes in (('over', [('νεα μορφη 2024-26', ['2425', '2526'])]), ('under', [('νεα μορφη 2024-26', ['2425', '2526']), ('ολες οι σεζον (πλαισιο)', None)]),
                  ('fav', [('ολες οι σεζον', None), ('νεα μορφη 2024-26', ['2425', '2526'])]), ('dog', [('ολες οι σεζον', None), ('νεα μορφη 2024-26', ['2425', '2526'])])):
    for sl, ss in scopes:
        D = X[(X.mk == m) & (X.sea.isin(ss) if ss else True)]
        P(''); P(f'=== {NAME[m]} · {sl} ===')
        for b in sorted(LAB):
            line(LAB[b], D[D.bk_ == b])
        P('  ' + '-' * 60)
        line('ΣΥΝΟΛΟ ΙΔΙΑΣ ΜΕΡΑΣ', D[D.bk_.str.startswith(('4', '5'))])
        line('ΟΛΑ ΤΑ ΠΡΙΝ', D[~D.bk_.str.startswith(('4', '5'))])
        if m == 'over':
            for c, cl in (('FF', 'FotMob+FotMob'), ('NF1', 'μια χωρις FotMob')):
                line(f'ιδια μερα · {cl}', D[D.bk_.str.startswith(('4', '5')) & (D.cat == c)])
P(''); P('(σημ.) τα ματς UCL ειναι κυριως 19:45/22:00 ωρα Ελλαδας· «ιδια μερα» = απο τα μεσανυχτα ως τη σεντρα (~10-22ω πριν).')
open('ucl_first_seen_day_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
