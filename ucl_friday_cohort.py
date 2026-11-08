"""ucl_friday_cohort.py — 16/10/2026 (Στελιος: «παρε ΜΟΝΟ τα picks που εμφανιζονται την Παρασκευη, μην προσθεσεις κανενα αλλο, και δειξε πως
αποδιδουν αν τα επαιζα σημερα, αυριο πρωι/βραδυ, Κυριακη πρωι/βραδυ, Δευτερα πρωι/βραδυ, Τριτη πρωι, 6/4/2ω, κλεισιμο»).
ΣΤΑΘΕΡΗ ΟΜΑΔΑ PICKS: ματς Champions League (Τριτη/Τεταρτη), pick = οσα περνουν τον κανονα live στην τιμη της ΠΑΡΑΣΚΕΥΗΣ 13:00 (ωρα Ελλαδας)
με ΤΙΜΙΟ μοντελο (δυναμη ομαδων −4 μερες, χωρις τα ματς του Σαββατοκυριακου). Η ιδια πλευρα (ιδια ομαδα / ιδιο over/under) μπαινει μετα σε
καθε σημειο με την ΤΙΜΗ ΚΑΙ ΓΡΑΜΜΗ εκεινης της στιγμης — κανενα νεο pick δεν προστιθεται, κανενα δεν κοβεται.
Σημεια (ωρα Ελλαδας): Παρ 13:00 · Σαβ 10:00 · Σαβ 22:00 · Κυρ 10:00 · Κυρ 22:00 · Δευ 10:00 · Δευ 22:00 · (Τρι 10:00 · Τρι 22:00 για ματς Τεταρτης)
· ημερα ματς 10:00 · −6ω · −4ω · −2ω · κλεισιμο.
ΧΑΝΤΙΚΑΠ κατηγορια Α: φαβορι ≥10% (σωστα τεταρτα) · αουτσαιντερ ≥4% · DNB ≥4% · 1.70-2.10 στην Παρασκευη.
ΣΥΝΟΛΑ: over ≥4% κατηγορια Α · over ≥4% κατηγορια Β (×1.22 στην ομαδα FotMob) · under ≥10% κατηγορια Α — νεα μορφη 2425-2526 + ολες.
Crown & SBOBET, μεσος. «Κινηση» = πόσο αλλαξε η τιμη προς/κοντρα απο την Παρασκευη (γκολ).
"""
import sys, os, pickle, datetime as dt
from zoneinfo import ZoneInfo
ATH = ZoneInfo('Europe/Athens')
NL = chr(10)
def points(ko_ts):
    """σημεια χρονου (λεπτομερη) για ματς με σεντρα ko_ts → [(ετικετα, unix)]"""
    k = dt.datetime.fromtimestamp(ko_ts, dt.timezone.utc).astimezone(ATH)
    d0 = k.date(); wd = k.weekday()                          # 1 = Τριτη, 2 = Τεταρτη
    fri = d0 - dt.timedelta(days=(wd - 4) % 7)
    def at(d, hh): return dt.datetime(d.year, d.month, d.day, hh, 0, tzinfo=ATH).timestamp()
    P = [('Παρ 13:00', at(fri, 13)), ('Σαβ 10:00', at(fri + dt.timedelta(1), 10)), ('Σαβ 22:00', at(fri + dt.timedelta(1), 22)),
         ('Κυρ 10:00', at(fri + dt.timedelta(2), 10)), ('Κυρ 22:00', at(fri + dt.timedelta(2), 22)),
         ('Δευ 10:00', at(fri + dt.timedelta(3), 10)), ('Δευ 22:00', at(fri + dt.timedelta(3), 22))]
    if wd == 2: P += [('Τρι 10:00', at(fri + dt.timedelta(4), 10)), ('Τρι 22:00', at(fri + dt.timedelta(4), 22))]
    P += [('ημερα ματς 10:00', at(d0, 10)), ('−6ω', ko_ts - 6 * 3600), ('−4ω', ko_ts - 4 * 3600), ('−2ω', ko_ts - 2 * 3600), ('κλεισιμο', None)]
    return [(l, t) for l, t in P if t is None or t < ko_ts]
LABS = ['Παρ 13:00', 'Σαβ 10:00', 'Σαβ 22:00', 'Κυρ 10:00', 'Κυρ 22:00', 'Δευ 10:00', 'Δευ 22:00', 'Τρι 10:00', 'Τρι 22:00',
        'ημερα ματς 10:00', '−6ω', '−4ω', '−2ω', 'κλεισιμο']
import pandas as pd, numpy as np
def table(R, title):
    print(f'{NL}{title}')
    if not len(R): print('   —'); return
    base = R[R.lab == 'Παρ 13:00']
    n = base.groupby('bk').size().mean()
    print(f'   picks (ανα βιβλιο) την Παρασκευη: {n:.0f} · σεζον: ' + ', '.join(f'{s}: {int((base.sea == s).sum() / 2)}' for s in sorted(base.sea.unique())))
    print(f'   {"σημειο":17s} │ {"ROI":>7s} │ {"μοναδες":>8s} │ {"θετ. σεζον":>10s} │ {"κινηση απο Παρ":>14s} │ {"μεση αποδοση":>12s} │ {"εκτος 1.70-2.10":>15s}')
    for lab in LABS:
        y = R[R.lab == lab]
        if not len(y): continue
        m = y.groupby('bk').pnl.mean(); s = y.groupby('sea').pnl.mean(); nn = y.groupby('bk').size().mean()
        print(f'   {lab:17s} │ {100 * m.mean():+6.1f}% │ {m.mean() * nn:+7.1f}μ │ {int((s > 0).sum())}/{len(s):<8d} │ {y.mv.mean():+14.3f} │ {y.od.mean():12.2f} │ {100 * (~y.inz).mean():14.0f}%')
