#!/bin/bash
# 19/10: ξανατρεξιμο τεστ κατηγοριων Β/Γ με πηγη Ben (pen76_chk) vs γκολ+Elo (pen76_elo)
cd "/c/Users/steli/My Drive/Betting Model"
T="ucl_nonfm_fix_test ucl_nonfm_fix2_test ucl_gap_totals_test euro_both_nonfm_totals nonfm_spread_allcomp uecl_categories uecl_category_metrics uecl_b_dog_test uecl_b_dog_path uecl_g_under_check"
for t in $T; do
  for arm in chk elo; do
    ( W2_IN=euro_v6w2_preds_pen76_$arm.pkl PYTHONIOENCODING=utf-8 timeout 3000 python $t.py > rerun_1910/${t}_$arm.txt 2>&1; echo "$t $arm rc=$?" >> rerun_1910/status.txt ) &
  done
  wait
done
echo ALLDONE >> rerun_1910/status.txt
