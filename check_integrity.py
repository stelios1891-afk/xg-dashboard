"""
check_integrity.py — τρεχει ΟΛΟΥΣ τους structural ελεγχους του portfolio μαζι.
Καθαρο PASS/FAIL + λιστα· exit 0 (pass) / 1 (fail).

Τρεξε το ΠΡΙΝ εμπιστευτεις οποιοδηποτε validated νουμερο. Ειναι ΤΟ ΙΔΙΟ gate
(picks.integrity_report) που:
  - τρεχει αυτοματα στην κορυφη καθε `python picks.py backtest`  (Lvl2)
  - μπλοκαρει το live bot μεσω picks.assert_integrity()          (Lvl4)

Ελεγχοι: coverage% · collision (2+ ομαδες→ιδιο ονομα) · unresolved→None ·
team-imbalance (silent wrong-key) · n-vs-fixtures (double-count) · date-match ±1μερα · duplicates.

Χρηση:  python check_integrity.py
"""
import sys
import picks as P

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ok = P.print_integrity(P.TOP5, P.ALL_SEASONS)
print('ΤΕΛΙΚΟ:  ' + ('PASS ✅ — τα validated νουμερα ειναι αξιοπιστα'
                     if ok else 'FAIL ❌ — ΜΗΝ εμπιστευτεις κανενα νουμερο πριν διορθωσεις'))
sys.exit(0 if ok else 1)
