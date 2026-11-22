# -*- coding: utf-8 -*-
"""core7_totals_b80.py — 10/11/2026 (Στελιος: «βαλτη σε παραλληλη καταγραφη»).
ΠΑΡΑΛΛΗΛΗ ΚΑΤΑΓΡΑΦΗ συνολων 5 μερες πριν με ΑΛΛΟ μειγμα xG/γκολ: ραμπα 100→80 (σημερα 100→60). Τεστ Τ5/Τ14 (core7_totals_early_mech):
4 σεζον +37.5μ vs +29.6μ (Crown +7.6 / Bet365 +8.1), ακριβεια καλυτερη 4/4, 15η+ ROI +12.9% → +19.9%· περασε 3/5 κριτηρια (CLV −0.013, LOSO μοιρασμενο).
ΤΙ ΚΑΝΕΙ: κραταει ΔΙΚΟ ΤΗΣ αρχειο προβλεψεων match_projections_archive_b80.json, με την ΙΔΙΑ μηχανη του live (dashboard/build_data + proj_archive)
και ΜΟΝΗ αλλαγη το τελικο μειγμα της ραμπας (picks.BLEND 0.60 → 0.80, η ραμπα ξεκινα παντα απο 100% xG):
  • backfill: τα ΠΑΙΓΜΕΝΑ φετινα ματς που λειπουν, ανακατασκευη με ματς ΠΡΙΝ τη μερα του αγωνα (για να μαθει η αγκυρα απο την 7η)
  • snapshot: τα επερχομενα (≤21 μερες), παγωμενα πριν τη σεντρα — οπως το live αρχειο
Η καταγραφη (core7_totals_shadow.py) τρεχει τον ΙΔΙΟ κανονα και στα δυο αρχεια → core7_totals_shadow_b80.json. ΚΑΝΕΝΑ pick/Telegram· το χαντικαπ ΔΕΝ αλλαζει.
Τρεχει: data-refresh (μετα το proj_archive). Ελεγχος: B80_BL=0.60 python core7_totals_b80.py backfill <αρχειο> → πρεπει να ξαναβγαζει το live."""
import os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'dashboard'))
import picks

BL = float(os.environ.get('B80_BL', '0.80'))
picks.BLEND = BL
picks._BLEND_D = (picks.BLEND_EARLY - BL) * (picks.BLEND_SPLIT + picks.BLEND_KG) / picks.BLEND_SPLIT
import proj_archive
proj_archive.ARCH_F = os.path.join(ROOT, sys.argv[2] if len(sys.argv) > 2 else 'match_projections_archive_b80.json')

if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    assert abs(picks.blend_at(13) - BL) < 0.02 and picks.blend_at(None) == BL and picks.blend_at(0) == 1.0
    print(f'μειγμα: ραμπα 100→{int(BL * 100)} · αρχειο {os.path.basename(proj_archive.ARCH_F)}')
    proj_archive.backfill()                   # μονο οσα παιγμενα λειπουν (την 1η φορα: ολη η σεζον)
    if not (len(sys.argv) > 1 and sys.argv[1] == 'backfill'):
        proj_archive.snapshot()
