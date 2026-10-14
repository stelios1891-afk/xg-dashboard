"""euro_components_build.py — 14/10/2026. Βοηθητικο: κομματια της ευρωπαικης προβλεψης ανα ματς (απο nonfm_rating_decomp):
t_γηπ, t_φιλ (δυναμη ομαδας μεσα στη λιγκα της) και D = ρ·(s λιγκας γηπ − s λιγκας φιλ), κατηγορια → euro_components.pkl {mid: dict}
"""
import sys, os, pickle
_CB = sys.stdout
exec(open('nonfm_rating_decomp.py', encoding='utf-8').read().split('# ---------- Poisson παλινδρομηση')[0])
sys.stdout = _CB; sys.stdout.reconfigure(encoding='utf-8')
OUT = {str(r.mid): dict(th=float(r.th), ta=float(r.ta), D=float(r.D), cat=r.cat, comp=r.comp) for r in R.itertuples()}
pickle.dump(OUT, open('euro_components.pkl', 'wb'))
print(len(OUT), 'ματς')
