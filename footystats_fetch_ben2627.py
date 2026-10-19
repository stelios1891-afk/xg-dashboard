# -*- coding: utf-8 -*-
"""footystats_fetch_ben2627.py — 19/10/2026 (Στελιος: «ψαξε αλλη πηγη xG για τις λιγκες του Ben»· ο Ben σταματησε τις 9 λιγκες 21/9).
ΦΕΤΙΝΗ σεζον FootyStats (2026/27 · ημερολογιακη 2026) για τις 9 λιγκες του Ben, με τη μηχανη του footystats_fetch2/3 (cache, parsers).
Σκοπος: (α) συγκριση FootyStats vs Ben στα φετινα κοινα ματς, (β) πιθανη αντικατασταση/συμπληρωμα του Ben. Idempotent."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import footystats_fetch2 as F2
import footystats_fetch3 as F3
ITEMS = ([(n, s, ["2026/27"]) for n, s in F3.BEN_SPLIT.items()] + [(n, s, ["2026"]) for n, s in F3.BEN_CAL.items()])
done = F3.preload_existing()
F3.run_pass("ΦΕΤΙΝΗ σεζον, 9 λιγκες Ben", ITEMS, done)
F2.write_outputs()
print("[ΤΕΛΟΣ] φετινα FootyStats για τις λιγκες του Ben")
