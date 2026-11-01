"""uel_by_category_review.py — 14/10/2026 (Στελιος: «χωρισε μου το europa σε κατηγοριες βαση fotmob — τι κραταμε, τι πεταμε, τι θα μπορουσε να
βελτιωσει οτιδηποτε δεν κραταμε»). Τρεχει ΑΚΡΙΒΩΣ το uecl_full_review (βαθμονομηση ανα κατηγορια, χαντικαπ Α, DNB/±0.25, συνολα Α/Β/Γ, τυφλα)
πανω στο Europa League. Ιδια κριτηρια ✓ ΠΕΡΝΑ.
"""
src = open('uecl_full_review.py', encoding='utf-8').read().replace("CMP = 'ConferenceLeague'", "CMP = 'EuropaLeague'")
exec(src)
