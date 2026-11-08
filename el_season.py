# -*- coding: utf-8 -*-
"""el_season.py — ΤΡΕΧΟΥΣΑ ΣΕΖΟΝ Ευρωλιγκας για ολα τα σεναρια μπασκετ (1/10/2026, Στελιος «τρεξε το 5»: τελος τα καρφωμενα 'E2026'/'26-27').
Σεζον = ετος εναρξης: απο 1 Σεπτεμβριου η νεα (το προγραμμα βγαινει Ιουλιο, η προετοιμασια ξεκινα Αυγουστο, η πρεμιερα Οκτωβριο).
Παρακαμψη (π.χ. για τεστ): μεταβλητη περιβαλλοντος EL_SEASON_YEAR=2025.
Y = 2026 · SEASON = 'E2026' (API Ευρωλιγκας) · NG = '26-27' (Nowgoal)"""
import os, datetime as dt
def year(d=None):
    d = d or dt.datetime.now(dt.timezone.utc).date()
    return d.year if d.month >= 9 else d.year - 1
Y = int(os.environ.get('EL_SEASON_YEAR') or year())
SEASON = f'E{Y}'
NG = f'{Y % 100:02d}-{(Y + 1) % 100:02d}'
