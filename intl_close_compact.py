"""
intl_close_compact.py — ΣΥΜΠΑΓΕΣ αρχειο closing Crown εθνικων (25/9/2026) για το αυτοματο refresh στο GitHub Actions.
Ο φακελος nowgoal_intl_odds/ (96MB) μενει τοπικα· εδω κρατιεται ΜΟΝΟ ο,τι χρειαζεται η αγκυρα (intl_mkt_anchor.py):
ανα FotMob mid -> closing 1Χ2 (op) και closing AH (ah_line γηπεδουχου, ah_h, ah_a δεκαδικες), με τον ΙΔΙΟ κωδικα του intl_vs_market.py.
Εξοδος: intl_close_hist.json. Τρεχει τοπικα μονο οταν ξανακατεβουν ιστορικα Nowgoal.
"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
src = open('intl_vs_market.py', encoding='utf-8').read(); ns = {}
exec(src[:src.index("M = pd.read_csv('intl_matches.csv'")], ns)
close = {k: {kk: vv for kk, vv in v.items() if kk != 'op_raw'} for k, v in ns['close'].items()}
json.dump(close, open('intl_close_hist.json', 'w', encoding='utf-8'), separators=(',', ':'))
print(f'intl_close_hist.json: {len(close)} ματς')
