"""uel_cat_comp_diag.py — 15/10/2026 (Στελιος: «τι διαφερει τοσο πολυ με τις αλλες κατηγοριες;»).
Ανα διοργανωση (UEL/UECL/UCL) × κατηγορια (Α = και οι 2 FotMob, Β = μια χωρις): ποσο «τεντωμενες» ειναι οι διαφορες του μοντελου
(κλιση πραγματικης διαφορας γκολ πανω στη διαφορα του μοντελου· 1 = σωστο, <1 = το μοντελο τις φουσκωνει), ιδια κλιση για την αγορα (κλεισιμο),
και η αγορα πανω στο μοντελο (ποσο απο τη γνωμη μας εχει ηδη η αγορα).
"""
import sys
exec(open("euro_value_filter_check.py", encoding="utf-8").read().split("# πλευρα ΧΩΡΙΣ FotMob")[0])
NL = chr(10)
mk = []
for r in A.itertuples():
    m = str(MIDS[int(r.i)]); s = snapT(m, 'Crown', 0) or snapT(m, 'SBOBET', 0); mk.append(implied_margin(int(r.i), *s) if s else np.nan)
A['mk'] = mk; A['mm'] = A.lh - A.la
def sl(y, a, b):
    ok = np.isfinite(y[a]) & np.isfinite(y[b]); return np.polyfit(y[a][ok], y[b][ok].astype(float), 1)[0] if ok.sum() > 20 else np.nan
print(f'{"διοργανωση":18s} {"κατ.":4s} {"ματς":>5s} │ {"πραγμ/μοντελο":>13s} {"πραγμ/αγορα":>11s} {"αγορα/μοντελο":>13s} │ {"μεσο |μοντελο|":>14s} {"μεσο |αγορα|":>12s} │ {"γκολ − μοντελο (γηπ)":>20s}')
for cm in ('EuropaLeague', 'ConferenceLeague', 'ChampionsLeague'):
    for c in ('A', 'B'):
        y = A[(A.comp == cm) & (A.cat == c) & A.mk.notna()]
        print(f'{cm:18s} {c:4s} {len(y):5d} │ {sl(y, "mm", "gd"):13.2f} {sl(y, "mk", "gd"):11.2f} {sl(y, "mm", "mk"):13.2f} │ {y.mm.abs().mean():14.2f} {y.mk.abs().mean():12.2f} │ {(y.gd - y.mm).mean():+20.2f}')
