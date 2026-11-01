"""euro_blend_build.py — 9/10/2026: ξαναχτιζει τα ευρωπαικα λ (euro_v6w2_test, κοκκινες emps) με ΑΛΛΗ μιξη xG/γκολ στα εγχωρια ratings.
Χρηση: python euro_blend_build.py 0.8  → euro_v6w2_preds_bl0.8.pkl  (ραμπα 100% xG στο 0 → b στα 13+ ματς, prior = b)."""
import sys, os, runpy
b = float(sys.argv[1])
import picks
picks.BLEND = b; picks._BLEND_D = (picks.BLEND_EARLY - b) * (picks.BLEND_SPLIT + picks.BLEND_KG) / picks.BLEND_SPLIT
assert abs(picks.blend_at(None) - b) < 1e-9 and abs(picks.blend_at(13) - b) < 1e-9
os.environ['RED_MODE'] = 'emps'; os.environ['NO_SANITY'] = '1'; os.environ['W2_OUT'] = f'euro_v6w2_preds_bl{b}.pkl'
runpy.run_path('euro_v6w2_test.py', run_name='__main__')
