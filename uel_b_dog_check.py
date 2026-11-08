"""uel_b_dog_check.py — 12/10/2026 (Στελιος «ναι» — ισχυει και στο Europa League το ευρημα του Conference: κατηγορια Β, αουτσαιντερ ΧΩΡΙΣ FotMob @10;)
Τρεχει ΑΚΡΙΒΩΣ το uecl_b_dog_test με διοργανωση Europa League (ιδια κριτηρια Κ1-Κ4, κατωφλια, τυφλα, χρονισμος, fair xG).
"""
import sys
src = open('uecl_b_dog_test.py', encoding='utf-8').read()
src = src.replace("_src = open('uecl_battery.py', encoding='utf-8').read()",
                  "_src = open('uecl_battery.py', encoding='utf-8').read().replace(\"open('uecl_full_review.py', encoding='utf-8').read()\", "
                  "\"open('uecl_full_review.py', encoding='utf-8').read().replace(\\\"CMP = 'ConferenceLeague'\\\", \\\"CMP = 'EuropaLeague'\\\")\")")
src = src.replace("F.to_csv('uecl_b_dog_picks.csv', index=False)", "")
exec(src)
