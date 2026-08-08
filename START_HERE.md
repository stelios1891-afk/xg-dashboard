# Betting Model — Οδηγίες Αυτοματοποίησης (Brief για Claude Code)

Αυτός ο φάκελος περιέχει ένα **pre-match xG-based betting model** για Asian Handicap
στα 5 μεγάλα ευρωπαϊκά πρωταθλήματα (+ πειραματικά δευτερεύοντα). Ο ιδιοκτήτης
(Στέλιος) στοιχηματίζει ~24h πριν το kickoff. Όλη η αναλυτική δουλειά έχει γίνει
και είναι **κλειδωμένη** — ο στόχος τώρα είναι **ΑΥΤΟΜΑΤΟΠΟΙΗΣΗ**, όχι αλλαγή του μοντέλου.

---

## ΤΙ ΘΕΛΟΥΜΕ ΝΑ ΧΤΙΣΕΙΣ (ο στόχος σου, Claude Code)

Ένα **αυτόματο pipeline** που αντικαθιστά τη χειροκίνητη δουλειά μετά από κάθε αγωνιστική:

**Φάση 1 — FotMob core (ΞΕΚΙΝΑ ΑΠΟ ΕΔΩ, είναι το σίγουρο):**
1. Βρίσκει ποια νέα ματς έπαιξαν σε όλα τα πρωταθλήματα (match list endpoints).
2. Κατεβάζει shot-level data από FotMob (xG, σουτ, κόκκινες, σκορ) — με resume, χωρίς διπλοκατεβάσματα.
3. **Re-check αναθεωρήσεων Opta:** ξανακατεβάζει τα ματς των τελευταίων ~4 ημερών κάθε φορά,
   γιατί η Opta αναθεωρεί τα xG μερικές μέρες μετά. Έτσι πιάνονται οι αλλαγές αυτόματα.
4. Εφαρμόζει compression + penalty + red adjustment (βλ. κανόνες κάτω).
5. Ενημερώνει τα rolling ratings (walk-forward, μόνο προηγούμενα ματς).
6. Βγάζει τα **picks**: value +handicap bets βάσει των κανόνων στοιχηματισμού.
7. Τρέχει με **ΕΝΑ ΚΛΙΚ** (ή μία εντολή). Output: ένα καθαρό αρχείο/πίνακας με τα picks της ημέρας.

**Φάση 2 — markstats enrichment (ΜΕΤΑ, χρειάζεται login):**
- Style features ανά αγώνα (field tilt, def line, PPDA, buildup%, xT, deep entries, per-period).
- Το markstats (https://markstats.club) είναι πίσω από **login (email/password)**.
- ΑΣΦΑΛΗΣ ΤΡΟΠΟΣ: διάβασε τα δεδομένα μέσα από τον browser του χρήστη όπου είναι ήδη
  συνδεδεμένος (π.χ. Claude in Chrome / browser session). **ΜΗΝ** αποθηκεύεις κωδικούς
  σε plain αρχεία, ΜΗΝ κάνεις scripted login που ρισκάρει κλείδωμα λογαριασμού.
- Endpoints (static JSON, per country+season): `/static/matches_{Country}_{season}.json`,
  `match_passes_...`, `match_pass_network_...`, `match_perf_per_period_...`
  (Country ∈ England/Spain/Italy/Germany/France, season π.χ. "2025-2026").

**Φάση 3 — full scheduling:** να τρέχει μόνο του (Windows Task Scheduler ή cloud), χωρίς κλικ.

**Setup περιβάλλοντος:**
- Windows, δύο μηχανές (desktop + laptop). Τα δεδομένα/μοντέλο σε **κοινό φάκελο Google Drive**
  (mirror mode, ΟΧΙ streaming) ώστε να συγχρονίζονται. Ένα μοντέλο, όχι δύο.

---

## ΑΡΧΙΤΕΚΤΟΝΙΚΗ ΜΟΝΤΕΛΟΥ (ΚΛΕΙΔΩΜΕΝΗ — μην την αλλάξεις)

**Shot processing:** shots × xG/shot, opponent-adjusted (att × def / league_mean).

**Caley step-wise compression** (ανά μη-penalty σουτ, μετά per-league rescale ώστε να
διατηρείται το άθροισμα raw npxG):
- xG ≤ 0.2 → × 1.00
- xG ≤ 0.4 → × 0.45
- xG ≤ 0.5 → × 0.25
- xG ≤ 0.7 → × 0.15
- αλλιώς   → × 0.05

**Penalty xG:** σταθερό **0.25** ανά πέναλτι, **εκτός** compression (για αποφυγή διπλο-compression).

**Red card adjustment:** pseudo-shots με Q=0.10 xG/shot. Πλεονέκτημα = 0.0083 × (λεπτά αριθμητικής
υπεροχής) για τη μία ομάδα, μείον το μισό για την ομάδα σε μειονεκτικότητα. Διατηρεί το xG/shot ratio.

**Decay:** εκθετικό **0.96** στα rolling ratings.

**Blend:** **80/20** (80% xG-based, 20% goals-based). Κρίσιμο — χωρίς αυτό αποκλίνει το slope.

**HFA:** ΣΤΑΘΕΡΟ per-league (11-σεζόν within-pairing, out-of-sample). Multiplier γηπεδούχου:
| League | HFA× | | League | HFA× |
|---|---|---|---|---|
| EPL (England) | 1.10 | | Bundesliga2 | 1.102 |
| LaLiga (Spain) | 1.15 | | Eredivisie | 1.130 |
| SerieA (Italy) | 1.08 | | PrimeiraLiga | 1.116 |
| Bundesliga (Germany) | 1.12 | | GreeceSL | 1.133 |
| Ligue1 (France) | 1.105 | | Belgium | 1.120 |
Φιλοξενούμενος = × (1/HFA). Εφαρμογή συμμετρικά. (Παλιά μέθοδος per-season sqrt ratio =
look-ahead, ΚΑΤΑΡΓΗΘΗΚΕ. Το ROI ήταν ίδιο, +7.6%→+6.9%, αλλά το σταθερό είναι καθαρό.)

**Score model:** Poisson + **draw boost 13%** (πολλαπλασιάζει τη διαγώνιο ισοπαλιών, μετά renormalize).

**MIN_PRIOR:** 6 ματς ελάχιστο ιστορικό πριν βγει πρόβλεψη.

---

## ΚΑΝΟΝΕΣ ΣΤΟΙΧΗΜΑΤΙΣΜΟΥ (ΚΛΕΙΔΩΜΕΝΟΙ)

- **edge threshold: 10%** (model P(cover) × odds − fair ≥ 0.10)
- **ΜΟΝΟ +handicap** (underdog). **ΠΟΤΕ φαβορί** (−handicap): επιβεβαιωμένο anti-edge, η αγορά τα τιμολογεί σωστά.
- **γραμμή ≥ 0.5** (όχι +0.25, όχι pick'em)
- **odds range 1.70–2.10**
- **flat staking €1000/bet**
- **Odds priority:** Betfair Exchange closing (BFECAHH/BFECAHA) → Pinnacle (PCAHH) → Avg (AvgCAHH).
  Τα φίλτρα ΕΙΝΑΙ το edge: χωρίς αυτά το ROI πέφτει στο ~0%.

Portfolio: ~375 bets/σεζόν στα top-5, ROI ~+7-8% (out-of-sample, 2 σεζόν), SE ±3.3%.

---

## ΠΗΓΕΣ ΔΕΔΟΜΕΝΩΝ

**FotMob (χωρίς login):**
- Shots: `https://www.fotmob.com/api/data/matchDetails?matchId={ID}` (header User-Agent Mozilla, gzip)
- Fixtures/match list: `https://www.fotmob.com/api/data/leagues?id={LID}&season={YYYY%2FYYYY}`
- League IDs: EPL 47, LaLiga 87, SerieA 55, Bundesliga 54, Ligue1 53.
  Euro: CL 42, EL 73, ECL 10216. Secondary: Bundesliga2 146, Eredivisie 57,
  PrimeiraLiga 61, GreeceSL 135, MLS 130, Belgium 40.
- Δες `dl.py` για δουλεύον downloader (resume, incremental).

**football-data.co.uk (odds, χωρίς login):**
- `https://www.football-data.co.uk/mmz4281/{season}/{code}.csv`
- Codes: E0 SP1 I1 D1 F1 (top-5), D2 N1 P1 G1 B1 (secondary). season π.χ. 2526.
- Στήλες κλειδιά: AHCh (closing AH line), BFECAHH/BFECAHA (Betfair closing), PCAHH/PCAHA,
  AvgCAHH/AvgCAHA, FTHG/FTAG (γκολ). Pre-match: AHh, BFEAHH (για δευτερεύοντα που δεν έχουν closing).

**markstats.club (style features, LOGIN):** βλ. Φάση 2 παραπάνω.

---

## ΑΡΧΕΙΑ ΣΕ ΑΥΤΟΝ ΤΟΝ ΦΑΚΕΛΟ

**Κύρια scripts (δουλεύοντα):**
- `dl.py` — FotMob downloader (resume). Χρήση: `python dl.py {League}_{season}` (π.χ. EPL_2526).
- `build_inputs.py` — compression + penalty + red adj → teamgame_inputs.csv
- `build_supremacy.py` — rolling ratings + 80/20 blend → model_predictions.csv
- `compare_corr.py` — model vs market correlation
- `decay_roi.py` — ΠΕΡΙΕΧΕΙ πλήρη betting engine (Poisson, draw boost, AH settlement, edge, filters)
- `hfa_compare.py` — betting με το σταθερό HFA (χρησιμοποίησέ το ως reference για το HFA table)

**Δεδομένα:**
- `data_{League}_{season}.json` — κατεβασμένα ματς (shots). Top-5 + δευτερεύοντα, 2 σεζόν.
- `odds/` (top-5) και `odds2/` (δευτερεύοντα) — football-data CSV.
- `hist/` — 11 σεζόν γκολ ανά λίγκα (για το HFA within-pairing).
- `euro_fixtures.json` — CL/EL/ECL fixtures 2 σεζόν (για fatigue scenarios).
- `match_index.json` — match IDs ανά λίγκα-σεζόν.
- CSVs: teamgame_inputs.csv, model_predictions.csv, pred_secondary.csv, compare_corr.csv.

**Βοηθητικά/ανάλυσης (reference, όχι κρίσιμα για το pipeline):**
- decay_sweep/phase, fatigue_*, chaos_test, build_secondary, two_season, struct_2season κ.λπ.

---

## ΣΗΜΕΙΩΣΕΙΣ / ΠΑΓΙΔΕΣ

- Το FotMob API δίνει gzip· κάνε decompress. User-Agent Mozilla υποχρεωτικό.
- Μεγάλα κατεβάσματα χτυπάνε timeout — τρέξε ανά λίγκα-σεζόν, με resume.
- Ελλάδα/MLS: μόνο 1 σεζόν διαθέσιμη σε xG (FotMob δεν έχει shotmap πριν το 25/26). MLS χωρίς odds.
- Το compression/HFA/blend είναι ΚΛΕΙΔΩΜΕΝΑ. Μην τα "βελτιώσεις". Ο στόχος είναι αυτοματοποίηση.
- Πριν οποιαδήποτε αλλαγή λογικής: ρώτα τον χρήστη. Αυτό είναι validated μοντέλο 2 σεζόν.
