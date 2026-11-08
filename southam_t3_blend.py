"""southam_t3_blend.py — 5/10/2026 ΟΜΑΔΕΣ 3-4: μιξη xG/γκολ, φθορα, ραμπα, warm-start K, «γυρισμα» περσινου προς τον μεσο. Κυριο: LL & Sx (+Sg)."""
import southam_tune as T
V = {'βαση': {}}
for b in (0.4, 0.5, 0.7, 0.8, 1.0): V[f'μιξη {b}'] = {'blend': b}
V['χωρις ραμπα'] = {'ramp': False}
for d in (0.92, 0.94, 0.98, 1.0): V[f'φθορα {d}'] = {'decay': d}
T.compare(V, 'βαση', 'ΟΜΑΔΑ 3 — ΜΙΞΗ xG/ΓΚΟΛ & ΦΘΟΡΑ (υπεροχη/1Χ2)', main=('LL', 'Sx', 'Sg'))
V = {'βαση': {}}
for K in (2, 4, 12, 16, 24, 40): V[f'K {K}'] = {'K': K}
for r in (0.15, 0.3, 0.5): V[f'περσινο→μεσο {r}'] = {'prior_reg': r}
V['K12+μεσο0.3'] = {'K': 12, 'prior_reg': 0.3}
T.compare(V, 'βαση', 'ΟΜΑΔΑ 4 — ΠΕΡΣΙΝΗ ΣΕΖΟΝ (warm-start)', main=('LL', 'Sx', 'Sg'))
