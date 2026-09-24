#!/usr/bin/env bash
# scanner_tick.sh — ΕΝΑ πληρες περασμα του scanner (18/9/2026, anti-thinning).
# Εξηχθη 1:1 απο τα steps του scanner.yml ωστε το workflow να το τρεχει ΣΕ ΒΡΟΧΟ
# (ο runner μενει ζωντανος ~1 ωρα, τικ καθε 5') — τα scheduled crons του GitHub
# αραιωνονται αγρια (κενα 3-5h) και δεν ειναι αξιοπιστα απο μονα τους.
# Χρηση: bash scanner_tick.sh [auto|force]   (force = χειροκινητο, χωρις gating)
# Το gating συχνοτητας/credits ζει ΜΕΣΑ στα scripts (scan_value.auto, euro/dom
# odds gates) — τα «σκετα» τικ κοστιζουν 0 TOA credits.
set -u
MODE="${1:-auto}"

if [ "$MODE" = "force" ]; then
  python scan_value.py || echo "SCANNER FAILED (το τικ συνεχιζει)"
else
  python scan_value.py auto || echo "SCANNER FAILED (το τικ συνεχιζει)"
fi
python shadow_scan.py || echo "shadow failed (μη κρισιμο)"
python brazil_shadow.py || echo "brazil shadow failed (μη κρισιμο)"
python euro_odds_scan.py || echo "euro odds failed (μη κρισιμο)"
python dom_odds_scan.py || echo "dom odds failed (μη κρισιμο)"
python dom_fav_shadow.py || echo "fav shadow failed (μη κρισιμο)"
python euro_shadow_scan.py || echo "euro shadow failed (μη κρισιμο)"
# 25/9: 🌐 International — TOA (Nations League) odds + rebuild του tab json (fallback Nowgoal αν δεν υπαρχει TOA)
python intl_odds_scan.py || echo "intl odds failed (μη κρισιμο)"
python intl_dashboard_build.py || echo "intl build failed (μη κρισιμο)"
# 25/9: 🏀 Euroleague — TOA odds (3 credits/request, gating μεσα στο script: ≤48h πριν το τζαμπολ, 60'/15')
python el_odds_scan.py || echo "el odds failed (μη κρισιμο)"

# ---- commit ΜΟΝΟ οταν αλλαξαν picks/market (ιδιο gate με πριν) ----
git config user.name "scanner-bot"
git config user.email "actions@github.com"
for f in clv_bets.jsonl clv_ledger.jsonl shadow_picks.jsonl shadow_state.json brazil_shadow.jsonl brazil_shadow_state.json euro_odds_latest.json dom_odds_latest.json euro_shadow.jsonl euro_shadow_state.json euro_value_latest.json euro_live_odds.jsonl euro_odds_hist.jsonl dom_odds_hist.jsonl dom_live_odds.jsonl dom_fav_shadow.jsonl dom_fav_shadow_state.json dom_uncomp_pairs.json intl_odds_latest.json intl_odds_hist.jsonl intl_live_odds.jsonl intl_closing.jsonl intl_projections_dashboard.json el_odds_latest.json el_odds_hist.jsonl; do [ -f "$f" ] || : > "$f"; done
git add -f value_last_scan.txt 2>/dev/null || true   # ποτε εγινε το τελευταιο TOA scan — χωρις αυτο καθε runner ξαναπληρωνε (24/9)
git add -f intl_odds_latest.json intl_odds_hist.jsonl intl_live_odds.jsonl intl_closing.jsonl intl_projections_dashboard.json 2>/dev/null || true   # 25/9 intl (δεν ειναι gitignored· -f για σιγουρια)
git add value_scan_state.json value_picks_latest.json market_1x2_latest.json odds_history.jsonl odds_history_state.json clv_bets.jsonl clv_ledger.jsonl shadow_picks.jsonl shadow_state.json brazil_shadow.jsonl brazil_shadow_state.json euro_odds_latest.json dom_odds_latest.json euro_shadow.jsonl euro_shadow_state.json euro_value_latest.json euro_live_odds.jsonl euro_odds_hist.jsonl dom_odds_hist.jsonl dom_live_odds.jsonl dom_fav_shadow.jsonl dom_fav_shadow_state.json dom_uncomp_pairs.json el_odds_latest.json el_odds_hist.jsonl
if git diff --cached --quiet -- value_last_scan.txt value_scan_state.json market_1x2_latest.json odds_history_state.json clv_bets.jsonl clv_ledger.jsonl shadow_picks.jsonl brazil_shadow.jsonl euro_odds_latest.json dom_odds_latest.json euro_shadow.jsonl euro_value_latest.json euro_live_odds.jsonl euro_odds_hist.jsonl dom_odds_hist.jsonl dom_live_odds.jsonl dom_fav_shadow.jsonl dom_fav_shadow_state.json dom_uncomp_pairs.json intl_odds_latest.json intl_odds_hist.jsonl intl_live_odds.jsonl intl_closing.jsonl intl_projections_dashboard.json el_odds_latest.json el_odds_hist.jsonl; then
  echo "no pick/market changes — skip commit"
else
  # ---- sanity gate (2026-09-18): αν σπασει καποιος ελεγχος, ΔΕΝ γινεται commit, το τικ συνεχιζει ----
  if ! python -m pytest -q -p no:cacheprovider tests/test_scanner_sanity.py; then
    echo "::warning::SANITY TESTS FAILED — το commit ακυρωνεται (το workflow συνεχιζει)"
    git reset -q
    exit 0
  fi
  git commit -m "picks/market update [skip ci]"
  # rebase πριν το push: μεσα στη βροχη μπορει να τρεχουν παραλληλα euro-refresh/one-offs
  git pull --rebase --autostash || true
  git push || echo "push failed — θα ξαναπροσπαθησει το επομενο τικ"
fi
exit 0
