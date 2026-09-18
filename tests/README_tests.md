# tests/ — sanity tests του live scanner

Ένας έλεγχος που τρέχει **πριν από κάθε commit** του scanner και μπλοκάρει τα προφανή
(conflict markers από autostash, σπασμένα JSON, λάθος σταθερές όπως το `MIN_PRIOR`,
picks εκτός κανόνων). Δεν χρειάζεται δίκτυο ούτε TOA credits — διαβάζει μόνο τα αρχεία
του repo και κάνει import τα modules.

## Τρέξιμο

```bash
# Windows (laptop)
"C:/Users/steli/AppData/Local/Programs/Python/Python312/python.exe" -m pytest -q tests/test_scanner_sanity.py

# Linux runner / γενικά
python -m pytest -q tests/test_scanner_sanity.py
```

Απαιτεί μόνο `pytest` (τοπικά έγινε `pip install pytest` στις 18/9· **δεν** είναι στο
`requirements.txt` — βλ. πρόταση παρακάτω). Το `-v` δείχνει κάθε test με όνομα.
Χρήσιμα φίλτρα: `-k "test_a"` (μόνο ακεραιότητα), `-k min_prior`, `-k golden`.

Προσομοίωση cloud από το laptop (το τοπικό working copy έχει `MIN_PRIOR=14`, άρα
**περιμένουμε** να κοκκινίσει το `test_b_min_prior_cloud_is_6`):

```bash
GITHUB_ACTIONS=true python -m pytest -q tests/test_scanner_sanity.py -k min_prior
```

## Τι ελέγχει (52 tests)

| Ομάδα | Τι πιάνει |
|---|---|
| **(a) ακεραιότητα** | Τα 4 JSON + 5 JSONL εξόδου φορτώνουν (κάθε γραμμή JSONL)· κανένα `<<<<<<<`/`=======`/`>>>>>>>`· δομή πεδίων (`value_picks_latest`, `market_1x2`, `value_scan_state`, `clv_bets`, `odds_history`)· καμία διπλή εγγραφή ίδιου (ματς, πλευρά, γραμμή) στο `clv_bets`· μονότονα `t` σε `odds_history` & `dom_live_odds`. |
| **(b) σταθερές** | `picks.py`: EDGE .10, ζώνη 1.70-2.10, MIN_LINE .5, DRAW_BOOST 1.13, MARGIN .03, BLEND .60, DECAY .96, SOS 1.5 (n=6..13), ράμπα blend (100→60 στη 13η), HFA_FIX CORE7, TOP5=CORE7. `build_data`: CURRENT_SEASON 2627, K_WARM 8, KN_NORM 20. `scan_value`: RATINGS_SEASON 2526, ODDS_DELTA .05. `toa_live`: SPORT=CORE7, KELLY 0.125, CAP 0.20. Ευρωπαϊκά (AST, χωρίς import): γ=−0.47, UCL_FAV_SCALE 1.16, EU_DRAW_SCALE .85, W_EU 2, EDGE_FAV_UCL .10, EDGE_DOG_UCL .04, dogs .10 / favs .04 / overs .04, GAMMA_PLAYER 1.09· header του `euro_projections.json` ίδιο με τον κώδικα. **MIN_PRIOR**: στο cloud (`GITHUB_ACTIONS=true`) πρέπει να είναι 6· τοπικά 6 ή 14· και το **committed HEAD** (`git show HEAD:picks.py`) πρέπει να έχει 6. |
| **(c) picks** | Πάνω στο τρέχον `value_picks_latest.json`: odds ∈ [1.70, 2.10], hcap ≥ 0.5 (μόνο dog πλευρά), edge ≥ 10%, λίγκα ∈ CORE7, σέντρα στο μέλλον (ανοχή 3h λόγω τοπικής ώρας στο `scanned_at`) και όχι in-play, stake = 0.125·edge/(odds−1), `stake_final = stake·scale`, `scale = min(1, 0.20/gross)`, Σstake_final ≤ 0.20· και ότι edge/proj_odds **αναπαράγονται** από pw/pp με τον τύπο pricing. |
| **(d) golden pricing** | 5 hardcoded ζεύγη (xg_h, xg_a, line, oh, oa) → `picks.evaluate_bet` συγκρίνεται με τιμές pw/pp/edge/proj_odds υπολογισμένες 18/9/2026 (ανοχή 1e-9). Περιλαμβάνει: πραγματικό pick, βαθιά γραμμή +2.5, ακέραια γραμμή με push, quarter γραμμή που πρέπει να απορριφθεί, οριακό edge 10.04%. Αν αλλάξει το pricing κατά λάθος, σπάει εδώ. |
| **(e) ευρωπαϊκά** | `euro_value_latest.json`: το `rules` block ίδιο με τα live κατώφλια· **UEL μόνο ως ΣΚΙΑ** (`no_play=True`, δείχνεται/δεν παίζεται — 18/9)· UCL/UECL ποτέ `no_play`· ζώνη odds· ρόλος/γραμμή/κατώφλι ανά comp (UCL favs @10, UCL dogs @4 με `band='4-10'`, αλλιώς dogs @10 / favs @4, overs @4)· το κ=1.16 υπάρχει στο header των projections, τα xG του pick ταυτίζονται με το projection, και στα UCL picks η πλευρά του φαβορί είναι ≥ ουδέτερη·HFA. |

Αν λείπει κάποιο αρχείο εξόδου → `skip` (δεν είναι μέρος του checkout). Άδειο JSON (0 bytes)
→ **fail** (το dashboard θα σκάσει).

## Αποτέλεσμα 18/9/2026 (laptop)

`52 passed` σε ~3s. Ευρήματα από τα πραγματικά αρχεία — βλ. σημειώσεις στο τέλος.

## ΠΡΟΤΑΣΗ (όχι υλοποίηση): πύλη πριν το commit

**Προσοχή:** στον scanner το `git commit` ΔΕΝ ζει στο `scanner.yml` αλλά στο
`scanner_tick.sh` (το workflow το καλεί σε βρόχο 10×5'). Άρα η πύλη μπαίνει σε δύο σημεία:

### 1. `scanner.yml` — να υπάρχει pytest στον runner

Στο step `Install deps`, μία λέξη παραπάνω (ή προσθήκη `pytest` στο `requirements.txt`):

```yaml
      - name: Install deps
        run: pip install -r requirements.txt pytest
```

### 2. `scanner_tick.sh` — η πύλη ακριβώς πριν το `git commit`

Μέσα στο `else` του `if git diff --cached --quiet ...`, **πριν** τη γραμμή
`git commit -m "picks/market update [skip ci]"`:

```bash
  if ! python -m pytest -q -p no:cacheprovider tests/test_scanner_sanity.py; then
    echo "::warning::SANITY TESTS FAILED — το commit ακυρωνεται (το workflow συνεχιζει)"
    git reset -q            # ξε-stage: τιποτα δεν φευγει προς το repo
    exit 0
  fi
```

Ένα αποτυχημένο test → **κανένα commit/push** σε αυτό το τικ, exit 0 → το workflow και η
αλυσίδα (Chain next run) συνεχίζουν κανονικά. Το επόμενο τικ ξανασκανάρει, ξαναγράφει τα
αρχεία και ξανατρέχει τα tests· αν το πρόβλημα είναι μόνιμο (π.χ. λάθος σταθερά στο
repo) το Telegram/Actions log το δείχνει σε κάθε τικ.

### 3. `euro-refresh.yml` / `data-refresh.yml` — καθαρά YAML (εκεί το commit είναι step)

Ακριβώς **πριν** το step `Commit if changed` / `Commit if raw data changed`:

```yaml
      - name: Sanity tests (αποτυχια = ΟΧΙ commit, το workflow συνεχιζει)
        id: sanity
        continue-on-error: true
        run: pip install -q pytest && python -m pytest -q -p no:cacheprovider tests/test_scanner_sanity.py
```

και στο commit step μία γραμμή `if:`:

```yaml
      - name: Commit if changed
        if: steps.sanity.outcome == 'success'
```

Το `continue-on-error: true` κρατά το workflow πράσινο· το `if:` στο commit step είναι
αυτό που ακυρώνει το commit.

## Σημειώσεις / ευρήματα (18/9/2026)

- **MIN_PRIOR split = uncommitted τοπική αλλαγή.** Το `picks.py` είναι `M` στο git status:
  working copy 14, HEAD 6. Δεν υπάρχει env var ή άλλος μηχανισμός cloud/local — το «cloud=6»
  ισχύει μόνο επειδή το hunk δεν έχει γίνει commit. Γι' αυτό υπάρχουν δύο tests: το
  `GITHUB_ACTIONS` (πιάνει το λάθος **στον runner**) και το `git show HEAD:picks.py`
  (πιάνει το λάθος **από το laptop**, πριν φύγει push).
- **UEL = σκιά (λύθηκε 18/9).** Ο `euro_shadow_scan.py` βγάζει picks και για `EuropaLeague`
  (dogs @10 / favs @4) αλλά με `no_play=True` + `note`· το dashboard τα δείχνει με ετικέτα
  «👁 ΣΚΙΑ · δεν παίζεται» (εντολή Στέλιου: να τα βλέπει χωρίς να παίζονται). Το τεστ (e)
  απαιτεί το flag αντί για απουσία.