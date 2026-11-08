# NBA betting market: where it is said to be beatable (web research, 2026-10-06)

Scope: practitioner + academic sources on NBA sides/totals market efficiency, model components, injury timing, early vs late season.
Tags: **[DATA]** = backed by a stated sample or a peer-reviewed/working paper; **[ANEC]** = practitioner opinion, a single example, or a trend that was mined from data with no out-of-sample test; **[MIXED]** = has some data but a small sample, or the result was later contradicted.
"Market prices it" = what the source says or implies about the closing line: FULLY / PARTLY / NOT / UNKNOWN.

Caveat on coverage: Unabated, Pinnacle and VSiN pages often loaded as empty shells. Ed Miller & Davidow's book text is not online, and Kevin Cole/Dunks & Threes have no public NBA market-efficiency write-ups that I could find. Many search hits were SEO content farms. I excluded them unless noted, and tagged them [ANEC].

---

## 1. Mechanisms (one line each)

| # | Mechanism | Claimed effect | Market prices it? | Evidence | Source |
|---|---|---|---|---|---|
| 1 | **Injury/availability news speed** (knowing a star sits before books move) | ~25% projected ROI on such bets; "a second or two" matters | NOT at the moment of news; FULLY by close | [ANEC] (pro bettor's own tracking) | https://unabated.com/articles/nba-betting-path-to-profitability (Tomas O'Connell, intro by Jack Andrews) |
| 2 | **Opening lines with a meaningful player absent** are biased | Significant opener error; line moves away from the team with absences | PARTLY at open, FULLY at close (bias gone at close) | [DATA] Dare, Dennis & Paul 2015, Finance Research Letters 13 | https://ideas.repec.org/a/eee/finlet/v13y2015icp130-136.html |
| 3 | **Opening-line biases in general** are removed by informed money | Line moves are proportional to opener bias and remove it by close | FULLY by close | [DATA] Gandar, Dare, Brown & Zuber 1998, J. Finance | https://academicnewsletter.sufe.edu.cn/info/361852 (abstract) |
| 4 | **News overreaction then partial reversal** | Line jumps on news, then settles "somewhere in the middle" | PARTLY (overshoot) | [ANEC] | https://fiddlespicks.substack.com/p/navigating-nba-injury-news-with-an |
| 5 | **Back-to-back (0 days rest)** | −1.25 pts (2003-10, 7,848 games); HCA 2.0 when home team on B2B and road team rested, 4.5 in the reverse case | FULLY ("lines do account for rest") | [DATA] inpredictable (Beuoy) | https://www.inpredictable.com/2012/02/nba-home-court-advantage-and-rest.html |
| 6 | **Home team on 2nd night of B2B vs a rested visitor**, worse after eastward travel | Home team underperforms ATS (19 seasons) | NOT (in that era) | [DATA] Ashman, Bowman & Lambrinos 2010, J. Sports Econ 11(6) — old sample | https://ideas.repec.org/a/sae/jospec/v11y2010i6p602-613.html |
| 7 | **Eastward jet lag (home team)** | −1.29 pts per game; 2-hour jet lag −4.5 pts, 1-hour −0.7 (11,481 games, 2011-21); no effect for away teams; westward none | UNKNOWN (no market test) | [DATA] Frontiers in Physiology 2022 | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9245584/ |
| 8 | **Rest share of HCA** | ~0.3 pts of HCA explained by road-team rest deficit | (structural) | [DATA] Entine & Small 2008 | https://repository.upenn.edu/entities/publication/e871ae9f-87db-40bd-922e-53064fae121f |
| 9 | **Well-rested team (4+ days) vs opponent on ≤2 days**, Jan-Apr, road | 96-61-1 ATS road version; 331-288 broad version (since 2005) | NOT (implied) | [ANEC] data-mined filters, no out-of-sample test | https://www.actionnetwork.com/nba/nba-betting-system-taking-advantage-well-rested-teams |
| 10 | **3-in-4 / 4-in-6 schedule spots** | Team-specific ATS records (e.g., one team 10-32-1) | ? | [ANEC] team-level splits are mined (noise) | https://vsin.com/nba/steve-makinens-nba-betting-trends-and-best-bets-for-wednesday-march-18/ |
| 11 | **B2B defensive drop** | 2022-23: 117.2 vs 114.8 pts/100 allowed on a B2B vs 1 day rest | likely FULLY (in totals) | [DATA] descriptive only | https://www.nba.com/nbabet/trends-on-back-to-back-sets-league-details-for-the-2023-24-season |
| 12 | **Altitude (Denver, also Utah)** | DEN home-road net rating 8.6 vs league 6.0 since 1999-00 (≈ +1.3 pts extra HCA); the league now schedules to blunt it | Mostly FULLY (books add ~1-2 pts) | [DATA] descriptive; [ANEC] on ATS | https://africa.espn.com/nba/story/_/id/37762170/nba-finals-2023-how-denver-altitude-gives-nuggets-edge ; https://www.cbssports.com/nba/news/nba-trying-to-weaken-nuggets-home-court-advantage/ |
| 13 | **HCA decline** | ~3.3 pts long run, trending down; 2022-23 +2.1 (record low); linked to more 3s / fewer FTs | FULLY (market tracks it) | [DATA] | https://arxiv.org/pdf/1603.08821 ; https://harvardsportsanalysis.org/2017/03/nba-home-court-advantage-is-in-decline-are-3s-to-blame/ |
| 14 | **No-fans (COVID) HCA shock** | Blind underdog ML +16.7% in the bubble/no-fans period | NOT then; European basketball markets DID price it | [DATA] arXiv 2109.07581 (preprint); PMC9517988 | https://arxiv.org/abs/2109.07581v1 ; https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9517988/ |
| 15 | **Tanking / eliminated teams late season** | Spreads move 1.5-4.3 pts vs eliminated teams (season-dependent); evidence of real on-court tanking is mixed | FULLY or over-priced (market *believes* in tanking more than the results show) | [DATA] Soebbing & Humphreys 2010 (2003-09) | https://sites.ualberta.ca/~econwps/2010/wp2010-13.pdf |
| 16 | **Clinched-playoff letdown** | Fading clinched teams profitable vs the OPENER; the close partly prices it; after vig mostly not profitable in the NBA | PARTLY (open), mostly FULLY (close) | [DATA] Krieger, Pace, Clarke & Girdner 2015 | https://openjournals.libs.uga.edu/fsr/article/view/3242 |
| 17 | **Team intent (compete vs coast vs tank)** is what all-in-one metrics miss | Qualitative | PARTLY | [ANEC] | https://unabated.com/articles/nba-betting-path-to-profitability |
| 18 | **Streaks / hot hand** | Spreads react to streaks (34 seasons, strongest at 6+ games); betting with or against streaks earns NO profit | FULLY (no exploitable residue) | [DATA] Waggoner et al. 2014; Paul, Weinbach & Humphreys 2014 | https://repository.lsu.edu/kinesiology_pubs/326 ; https://ideas.repec.org/a/sae/jospec/v15y2014i6p636-649.html |
| 19 | **Overreaction to small early samples** (Voulgaris' 1999-2000 Lakers futures: books lengthened 4/1 → 6.5/1 after a few games) | Anecdote | NOT (futures, 1999) | [ANEC] | Nate Silver, *The Signal and the Noise* ch. 8 (excerpt: http://faculty.bard.edu/hhaggard/teaching/sci127Sp20/notes/SilverSignalExcerpt.pdf) |
| 20 | **Large home underdogs (+10 or more)** | 59.5% ATS but n=50, fading in later years | gone | [MIXED] | https://thesportjournal.org/article/nba-gambling-inefficiencies-a-second-look/ |
| 21 | **Preseason (exhibition) games**: spreads too large → underdogs | Profitable underdog strategy (NFL & NBA preseason) | NOT | [DATA] UWF study | https://ircommons.uwf.edu/esploro/outputs/journalArticle/Preseason-bias-in-the-NFL-and/99380090299306600 |
| 22 | **Revenge / lookahead / letdown spots** | Revenge 46.6% ATS (i.e., no edge); others vary | FULLY / no edge | [ANEC] Bet Labs aggregate | https://www.thescore.com/nba/news/1929323 ; https://www.covers.com/guides/how-to-recognize-and-handicap-spot-bets |
| 23 | **Coach game-management / qualitative signals** (press-conference code for pace, contract-year players, tanking lineups) | Voulgaris: Cavs games 192 → 207 pts in the last 3 weeks of 2002 (Ricky Davis contract year); his overall hit rate ~57% | NOT (at that time) | [ANEC] | Silver excerpt (above) |
| 24 | **Load management / star rest** | Unannounced rests hurt pre-set lines; NBA 2023 rest policy (stars in national-TV/Cup games) reduced it | PARTLY until news drops | [ANEC] | https://www.theringer.com/nba/2023/9/15/23874273/nba-resting-policy-load-management-rules |
| 25 | **In-Season Tournament (NBA Cup) games** | No systematic study found; only team ATS anecdotes | UNKNOWN | [ANEC] | https://www.actionnetwork.com/nba/how-to-bet-the-nba-in-season-tournament-knockout-stage-bets-for-suns-celtics-pelicans |
| 26 | **Line shopping / slow books** vs consensus | Sides/totals are "almost always close" to the true number; the edge comes from stale books | — | [ANEC] | https://unabated.com/articles/nba-betting-path-to-profitability |

---

## 2. TOTALS: what drives mispricing

| Driver | What sources say | Market prices it? | Evidence | Source |
|---|---|---|---|---|
| **Early-season level shift** | Totals (not sides) biased early each season; strategy 56.72% vs CLOSING total; line moves the right way from open to close but not far enough | PARTLY | [DATA] Baryla, Borghesi, Dare & Dennis 2007, Finance Research Letters | https://dc.etsu.edu/etsu-works/17780 |
| **Week-1 unders** | 58.2% unders in week 1, 2009-12; +11.1% per game | NOT (then) | [DATA] small sample (4 seasons × 1 week) | https://ircommons.uwf.edu/esploro/outputs/journalArticle/Early-season-NBA-overunder-bias/99380090347306600 |
| **Rule / ball / environment changes** | 2021-22: unders 148-104 (58.7%) first 5 weeks; avg close 223.2 (wk1) → 213.9 (wk5); pace 101.1 → 96.9; overs back to ~50% by wk 18-19 | NOT early, catches up | [DATA] one season, descriptive | https://www.nba.com/nbabet/early-nba-season-over-under-trends-and-teams-to-target-this-week-on-the-total |
| **Public over bias at high totals** | Bettors over-bet overs, more so as the total rises; unders >52.4% at high totals in 1995-2002 | NOT then → FULLY now (2012-19 fair bet not rejected; anomaly drifted to higher totals) | [DATA] Paul, Weinbach & Wilson 2004; Moore 2021 | https://ideas.repec.org/a/eee/quaeco/v44y2004i4p624-632.html ; https://ideas.repec.org/a/eee/quaeco/v82y2021icp26-29.html |
| **Overall over/under balance** | 2000-08 over is a fair bet; since 2005 ~11,244 O vs 11,132 U | FULLY | [DATA] | https://thesportjournal.org/article/nba-gambling-inefficiencies-a-second-look/ ; https://www.actionnetwork.com/education/do-games-go-over-or-under-more-often-in-sports-betting |
| **Pace matchup: who controls tempo** | Offense dictates its own seconds/possession (range ~2.5× wider than defensive pace); defensive pace correlates more with defensive efficiency (−0.36 vs −0.19) → model offensive pace and defensive pace separately, not one "pace" number | UNKNOWN (likely priced by sharp models) | [DATA] descriptive (inpredictable) | https://www.inpredictable.com/2015/03/offensive-versus-defensive-pace-in-nba.html ; https://inpredictable.com/2016/05/is-pace-contagious.html |
| **Pace ≠ points** | High pace + low efficiency (2022-23 Hornets) → raw pace misleads | — | [ANEC] | https://www.lsports.eu/?p=25244 |
| **3PT% variance** | Opponent 3P% has ~0 year-to-year correlation (defense controls attempts, not %) → regress opponent 3P% hard; luck-adjusted ratings strip it | Probably FULLY by sharp books; public overreacts | [DATA] on the stability; [ANEC] on betting value | https://www.theringer.com/nba/2021/2/12/22279459/nba-make-miss-3-point-shooting ; https://squared2020.com/2021/01/23/boston-vs-the-field-defensive-3pt/ |
| **Referees** | Ref crews' over records since 2005 ≈ 50% in aggregate; single-ref splits (e.g., 60% unders) are small-sample | FULLY / no edge | [DATA] aggregate (Bet Labs); [ANEC] per ref | https://www.actionnetwork.com/nba/nba-finals-referees-betting-trends-warriors-raptors-officials-2019 |
| **Referees inside a simulator** | Voulgaris' "Ewing" sim reportedly included referee foul tendencies | UNKNOWN | [ANEC] | https://grokipedia.com/page/Voulgaris (secondary) |
| **Overtime** | In one sample only 5 of 37 OT games stayed under; non-OT games went under 53.7% → the line must embed ~6% OT probability; close-spread games carry more OT mass | FULLY (in theory) | [ANEC] small sample | https://www.actionnetwork.com/education/do-games-go-over-or-under-more-often-in-sports-betting |
| **End-game fouling / garbage time** | Historically half totals were set at a 50/50 split, but Q4 of close games inflates scoring (FTs, fouling). This was Voulgaris' original edge in 1H/2H totals; later fixed. Blowouts change rotations and pace | FULLY now (historic edge) | [ANEC] | https://www.espn.com/blog/playbook/dollars/post/_/id/2935/meet-the-worlds-top-nba-gambler ; https://www.eugenewei.com/blog/2013/3/3/4v0k7l3sz5puqyydjxzmstsiipbznw |
| **Derivative splits (1H/1Q/team totals)** | Derived from the full-game total with fixed quarter shares (~26/25/25/23%); team 1H shares range 48-54% → softest numbers but highest vig | PARTLY | [ANEC] content-farm level | https://nbabettingsystem.com/articles/nba-first-quarter-and-first-half-betting/ |
| **Rest / B2B in totals** | B2B → worse defense (+2.4 pts/100 allowed) | likely FULLY | [DATA] descriptive | (see #11) |
| **Late-season / playoff context** | Contract-year/eliminated teams play fast (Cavs 2002 +15 pts/game); playoff G6/G7 unders 92-65 (58.6%) | NOT (then) / ? | [ANEC] | Silver excerpt; https://www.actionnetwork.com/nba/can-bettors-profit-fatigue-nba-playoffs |
| **Coaching style / intent** | Coach press-conference language ("learn the offense" → slower), pace changes after coaching changes; the market lags a few games | PARTLY (brief) | [ANEC] Voulgaris via Silver | Silver excerpt |

What sources agree on for totals: the full-game closing total is about as efficient as the side. The documented, data-backed residue is the **early-season level** (week 1 to ~week 5, more so when rules or the ball change). Everything else is either priced or anecdotal.

---

## 3. Player-level vs team-level modeling, and injury/lineup timing

- **Player-level is the standard among pros.** Voulgaris' "Ewing" valued each player on offense and defense with matchup-dependent values (e.g., a big defender worth more vs a dominant center), plus aging curves. It went live in 2008 "unremarkably" and only crushed after adding a secret second model in 2009, mostly after the All-Star break. [ANEC] https://www.eugenewei.com/blog/2013/3/3/4v0k7l3sz5puqyydjxzmstsiipbznw
- **The "heart" of a player model is minutes projection** (who absorbs an absent player's minutes, blowout minutes). [ANEC] https://vsin.com/nba/nba-a-new-player-based-model-for-handicapping-games/ (page did not load; snippet only) ; https://unabated.com/post/fine-tune-your-nba-prop-betting-strategy-using-unabated-nba
- **Counter-view from a winning pro:** the Pietrus model is *team-level* (27 variables, injuries applied before the preseason prior, plus team intent), because all-in-one player metrics cannot see role changes, synergy, coaching or intent. He still says sides/totals are "almost always close" to true. [ANEC] https://unabated.com/articles/nba-betting-path-to-profitability
- **Where the edge sits relative to news:**
  - *Before or at news:* the largest edge (~25% ROI claimed) is knowing a star's status before books move. That window is seconds to minutes. [ANEC] (Unabated/O'Connell)
  - *Opener vs close:* openers misprice absences, and closers do not. So any absence edge must be taken before the close. [DATA] Dare, Dennis & Paul 2015
  - *After news:* lines can overshoot and then partly revert. [ANEC] (fiddlespicks)
  - *Typical news time:* 60-90 min pre-tip (final injury reports/lineups). Pros race automated systems. [ANEC]
  - Unabated sells "conditional projections" (one projection set per questionable-star scenario) precisely because the value sits in pricing scenarios before resolution. [ANEC] https://unabated.com/articles/nba-betting-path-to-profitability
- **Implication stated by sources:** because the close fully absorbs availability, a model that beats the close needs either faster information or better *conditional* pricing (minutes redistribution), not better ratings of who is playing. This matches Dare et al. (bias at open, none at close) and Gandar et al. (line moves remove opener bias).
- **Market-level views of lineups:** Voulgaris charted defensive positioning and followed player Twitter and coach pressers. He calls the big obvious edges "already in the line" and says he needs "a thousand little secrets". [ANEC] Silver excerpt

---

## 4. Early season (Oct-Dec) vs late season efficiency

- **Early season, totals:** the only repeatedly published, data-backed inefficiency (Baryla et al. 2007, vs CLOSE; Girdner et al. 2013, week 1; the 2021-22 rule-change season). Direction in the documented cases is UNDER (books anchor on last season's scoring level). [DATA]
- **Early season, sides:** Baryla et al. find *no* comparable early bias in sides lines. [DATA] Practitioners still describe early-season overreaction to small samples (Voulgaris' Lakers futures). [ANEC]
- **Pros' model timing:** Voulgaris' model profited mainly *after the All-Star break*, not early. [ANEC] O'Connell credits his preseason prior with catching slow-starting good teams early (Boston, Memphis). [ANEC]
- **Preseason (exhibition) games:** spreads too large, so underdogs are profitable. [DATA] (UWF)
- **Late season:** markets *over*-price tanking in spreads (Soebbing & Humphreys). Clinched-team letdowns are priced at the opener but mostly corrected by the close (Krieger et al.). Contract-year / eliminated-team pace effects exist anecdotally. Rest/load-management news risk rises (rotations shorten, stars sit). [DATA]/[ANEC]
- **General trend:** anomalies documented in 1995-2010 data (high-total unders, big home dogs, B2B home teams) mostly disappear in 2012+ data (Moore 2021; Sport Journal). The modern market is described as among the most efficient in US sports.

---

## Relation to our own results (factual mapping only)

- Our spread value only in Oct-Dec (CLV slope ~+0.23) fits the literature, where early-season inefficiency comes from slow updating of prior levels. Literature finds it in *totals*, not sides; ours is the reverse.
- Our totals show no value. The literature's totals edge is a *league-wide level* shift (all games under early, especially with rule/ball changes), not team-pair matchups. Our model's early-season scoring-level prior (league mean drift wk 1-5) is the component the sources point at.
- Our "perfect knowledge of who plays + player metrics" test not beating the close is consistent with Dare et al. 2015 (absences fully priced at close). The sources place the availability edge *before* the close, in timing, not in the closing number.
- B2B / rest / altitude / HCA: sources say these are priced (inpredictable 2012; market HCA tracking). The only unpriced travel effect with data is eastward jet lag for *home* teams, which has no market test.
