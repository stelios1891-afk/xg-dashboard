"""southam_t8_combo.py — 5/10/2026: ΣΥΝΔΥΑΣΜΟΣ οσων περασαν (υπεροχη/1Χ2). Βραζ: χωρις κοκκινες. MLS: κυλιομενη εδρα K300 + περσινο→μεσο 0.3 + χωρις κοκκινες (+ SoS ως 20η)."""
import southam_tune as T
V = {'βαση': {}, 'χωρις κοκκινες': {'red': False},
     'MLS: εδρα+μεσο': {'hfa': 'roll', 'hfa_K': 300, 'prior_reg': 0.3},
     'MLS: εδρα+μεσο+κοκκ': {'hfa': 'roll', 'hfa_K': 300, 'prior_reg': 0.3, 'red': False},
     'MLS: ολα+SoS20': {'hfa': 'roll', 'hfa_K': 300, 'prior_reg': 0.3, 'red': False, 'sos_hi': 19}}
T.compare(V, 'βαση', 'ΣΥΝΔΥΑΣΜΟΣ (υπεροχη/1Χ2)', main=('LL', 'Sg', 'Sx'))
