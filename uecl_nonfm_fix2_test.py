"""uecl_nonfm_fix2_test.py — 12/10/2026 (Στελιος: «στη Β του UCL τι τεστ καναμε και πως το διορθωσαμε; εδω γιατι δεν μπορουμε να διορθωσουμε κατι,
εφοσον ειναι πραγματικοτητα;»). ΑΚΡΙΒΩΣ το ucl_nonfm_fix2_test (χωριστες διορθωσεις LOSO: δ στα γκολ της ομαδας FotMob ΜΟΝΟ στο μοντελο συνολων,
μ στη διαφορα ΜΟΝΟ στο μοντελο χαντικαπ · ιδια προ-δηλωμενα Κ1/Κ2 + picks) πανω στο CONFERENCE κατηγορια Β.
Αλλαγες: δ επιτρεπεται και ΑΡΝΗΤΙΚΟ (−0.40…+0.40, στο UECL η ομαδα FotMob βαζει ΛΙΓΟΤΕΡΑ) · κανονες picks UECL: φαβ ≥10%, dog ≥10%, over ≥4%, under ≥14%.
"""
import sys
src = open('ucl_nonfm_fix2_test.py', encoding='utf-8').read()
rep = [("for i in np.where(ucl)[0]:", "for i in np.where(COMP == 'ConferenceLeague')[0]:"),
       ("GD_ = GRID", "GD_ = np.round(np.arange(-0.40, 0.41, 0.02), 2)"),
       ("if e >= (fav_thr if role == 'fav' else 0.04):", "if e >= (fav_thr if role == 'fav' else 0.10):"),
       ("if e >= (.04 if side == 'over' else .10):", "if e >= (.04 if side == 'over' else .14):"),
       ("print(f'UCL ματς με μια", "print(f'CONFERENCE ματς με μια"),
       ("('χαντικαπ DOG μεγαλης ≥4%', 'dog_big'), ('χαντικαπ DOG μικρης ≥4%', 'dog_small'), ('over ≥4%', 'over'), ('under ≥10%', 'under')",
        "('χαντικαπ DOG μεγαλης ≥10%', 'dog_big'), ('χαντικαπ DOG μικρης ≥10%', 'dog_small'), ('over ≥4%', 'over'), ('under ≥14%', 'under')")]
for a, b in rep:
    assert a in src, a
    src = src.replace(a, b)
exec(src)
ds = P2[P2.side == 'dog_small']; m = ds.groupby('bk').pnl.mean(); ps = ds.groupby('sea').pnl.mean()
print(f'+ (UECL) DOG μικρης με διορθωση: μοναδες {units(ds):+.1f} vs σημερα {units(P0[P0.side == "dog_small"]):+.1f}')
