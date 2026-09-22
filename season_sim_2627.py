"""
season_sim_2627.py — ΦΕΤΙΝΗ (2026/27) προσομοιωση τελους σεζον, CORE7, με τη μεθοδο που περασε την
επικυρωση (season_sim_validate.py -> season_sim_choice.json). Εξοδος: season_projections.json (dashboard).

Ratings ΑΚΡΙΒΩΣ οπως το live dashboard: build_data.league_ratings (περσινο 2526 flat prior + φετινο
warm-start K=8 + νεοφωτιστες με 2η κατηγορια λ=0.5 + χαρακας KN_NORM + SoS 1.5 @ n=6..13).
Fixtures/αποτελεσματα: FotMob leagues endpoint (results_view.season_matches): finished -> παιγμενα με σκορ,
οτιδηποτε αλλο (not started / σε εξελιξη) -> προσομοιωνεται· cancelled -> αγνοειται (δηλωμενο).
Θεσεις/κριτηρια ισοβαθμιας/ευρωπαικες θεσεις: season_sim.LEAGUE_RULES.
DEDUCTIONS 2627: κενο (καμια γνωστη σημερα).

Χρηση: python season_sim_2627.py [METHOD]   (προεπιλογη: chosen απο season_sim_choice.json)
"""
import os, sys, json, re, time
from datetime import datetime, timezone
import numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'dashboard'))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import picks, build_data as BD
import season_sim as SS

N_RUNS = 10000
DEDUCTIONS_2627 = {}   # {(league, team_name): pts}


def season_matches(lg):
    """Ολα τα ματς της σεζον απο το FotMob leagues endpoint (οπως results_view.season_matches + cancelled)."""
    lid = BD.LEAGUE_FOTMOB[lg]
    d = BD._fotmob(f'https://www.fotmob.com/api/data/leagues?id={lid}&season={BD.CURRENT_FOTMOB_SEASON}')
    out = []
    for m in d.get('fixtures', {}).get('allMatches', []):
        st = m.get('status', {}); h, a = m.get('home', {}), m.get('away', {})
        score = (st.get('scoreStr') or '').replace(' ', ''); hs = aw = None
        if '-' in score:
            try: hs, aw = [int(x) for x in score.split('-')]
            except ValueError: pass
        out.append(dict(gw=int(m.get('round') or 0), finished=bool(st.get('finished')), cancelled=bool(st.get('cancelled')),
                        home=h.get('name'), away=a.get('name'), home_id=h.get('id'), away_id=a.get('id'), hs=hs, aw=aw))
    return out


def parse_method(name):
    s0 = 0.0; rho = 0.0; db = SS.DRAW_BOOST
    m = re.search(r'_s([0-9.]+)', name)
    if m: s0 = float(m.group(1))
    m = re.search(r'_r([0-9.]+)', name)
    if m: rho = float(m.group(1))
    if name.startswith('M3'): db = 1.0
    return s0, rho, db


def main():
    t0 = time.time()
    out_f = open('season_sim_2627_out.txt', 'w', encoding='utf-8')
    def log(s=''):
        print(s); out_f.write(s + '\n'); out_f.flush()
    choice = json.load(open('season_sim_choice.json')) if os.path.exists('season_sim_choice.json') else {}
    method = sys.argv[1] if len(sys.argv) > 1 else choice.get('chosen') or 'M0'
    s0, rho, db = parse_method(method)
    log(f"SEASON PROJECTIONS 2026/27 — μεθοδος {method} (s0={s0}, ρ={rho}, draw_boost={db}), N={N_RUNS}")
    Mp, id2name = picks.load_matches(list(BD.LEAGUE_FOTMOB), [BD.RATINGS_SEASON_DEFAULT])
    Mc, id2c = picks.load_matches(list(BD.LEAGUE_FOTMOB), [BD.CURRENT_SEASON])
    id2name.update(id2c); name2id = {v: k for k, v in id2name.items()}
    proj = dict(generated=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'), method=method,
                s0=s0, rho=rho, draw_boost=db, n_runs=N_RUNS, leagues={})
    for lg in SS.CORE7:
        LR = BD.league_ratings(lg, Mp, Mc, id2name=id2name, name2id=name2id)
        bl, ns, lg_shots, lg_xgps, hf = LR['blended'], LR['ns'], LR['lg_shots'], LR['lg_xgps'], LR['hf']
        rules = SS.LEAGUE_RULES[lg]; tb = rules['tb']
        sm = season_matches(lg)
        played = []; fixtures = []; names = {}; skipped = 0
        for m in sm:
            h = int(m['home_id']); a = int(m['away_id']); names[h] = m['home']; names[a] = m['away']
            if m['finished'] and m['hs'] is not None:
                played.append((h, a, int(m['hs']), int(m['aw'])))
            elif m.get('cancelled'):
                skipped += 1
            else:
                fixtures.append((h, a))
        teams = sorted(set(names)); T = len(teams)
        missing = [names[t] for t in teams if t not in bl]
        if missing:
            log(f"  !! {lg}: χωρις rating: {missing} — παραλειπεται"); continue
        games_left = {t: 0 for t in teams}
        for h, a in fixtures:
            games_left[h] += 1; games_left[a] += 1
        bl_use = SS.regress_ratings(bl, games_left, 2 * (T - 1), rho, lg_shots, lg_xgps) if rho else bl
        lh, la = SS.fixture_lambdas(fixtures, bl_use, lg_shots, lg_xgps, hf)
        noise = {t: s0 / np.sqrt(1 + ns.get(t, 0) / 8.0) for t in teams} if s0 else None
        ded = {t: DEDUCTIONS_2627[(lg, names[t])] for t in teams if (lg, names[t]) in DEDUCTIONS_2627}
        sim = SS.simulate(teams, played, fixtures, lh, la, tb, n_runs=N_RUNS, seed=2627,
                          draw_boost=db, noise_sd=noise, deductions=ded)
        summ = SS.summarize(sim, lg, '2627')
        mean_xg = lg_shots * lg_xgps
        L = dict(n_teams=T, played_matches=len(played), remaining=len(fixtures), tiebreak=tb,
                 slots=dict(ucl=rules['ucl'], ucl5=rules['ucl5'], eur=rules['eur'], rel=rules['rel'], rel_po=rules['rel_po']),
                 lg_xg_mean=round(mean_xg, 3), promoted=[names[t] for t in LR['promoted'] if t in names], teams={})
        for t in teams:
            s = summ[t]; Ax, Dx, SF, SA = bl[t]
            att = SF * Ax; dfn = SA * Dx
            L['teams'][names[t]] = dict(
                id=t, pts_now=int(s['pts_now']), played=s['played'], w=s['w_now'], d=s['d_now'], l=s['l_now'], gd_now=s['gd_now'],
                e_w=round(s['e_w'], 2), e_d=round(s['e_d'], 2), e_l=round(s['e_l'], 2), e_gd=round(s['e_gd'], 1),
                e_pts=round(s['e_pts'], 1), pts_p10=round(s['pts_p10'], 1), pts_p50=round(s['pts_p50'], 1), pts_p90=round(s['pts_p90'], 1),
                p_title=round(s['p_title'], 4), p_ucl=round(s['p_ucl'], 4),
                p_ucl5=round(s['p_ucl5'], 4) if s['p_ucl5'] is not None else None,
                p_eur=round(s['p_eur'], 4), p_rel=round(s['p_rel'], 4),
                p_rel_po=round(s['p_rel_po'], 4) if s['p_rel_po'] is not None else None,
                pos_dist=[round(x, 4) for x in s['pos_dist']],
                rating_att=round(att, 3), rating_def=round(dfn, 3), rating_total=round(att - dfn, 3),
                n_cur=int(ns.get(t, 0)))
        proj['leagues'][lg] = L
        log(f"  {lg:13s}: {T} ομαδες, παιγμενα {len(played)}, υπολοιπα {len(fixtures)}, cancelled {skipped}, "
            f"νεοφωτιστες {L['promoted']}  ({time.time()-t0:.0f}s)")
    json.dump(proj, open('season_projections.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # ---------- πινακες ----------
    for lg in SS.CORE7:
        if lg not in proj['leagues']:
            continue
        L = proj['leagues'][lg]; rules = SS.LEAGUE_RULES[lg]
        rows = sorted(L['teams'].items(), key=lambda kv: -kv[1]['e_pts'])
        full = (lg == 'EPL')
        log(f"\n{'='*120}\n{lg} 2026/27 — προβολη τελους σεζον ({method}, N={N_RUNS}) — παιγμενα {L['played_matches']}, υπολοιπα {L['remaining']}\n{'='*120}")
        hdr = (f"{'#':>2s} {'Ομαδα':26s}{'P':>3s}{'W-D-L':>8s}{'Pts':>4s} | {'E[pts]':>7s}{'p10':>5s}{'p90':>5s} | "
               f"{'Τιτλ':>6s}{'UCL':>6s}{'UCL5':>6s}{'EUR':>6s}{'REL':>6s}{'RELpo':>6s} | {'att':>5s}{'def':>5s}{'tot':>6s}{'n':>3s}")
        log(hdr); log('-' * len(hdr))
        for i, (nm, r) in enumerate(rows):
            if not full and 3 <= i < len(rows) - 3:
                if i == 3: log('   ...')
                continue
            log(f"{i+1:2d} {nm[:26]:26s}{r['played']:3d}{r['w']:3d}-{r['d']:d}-{r['l']:<2d}{r['pts_now']:4d} | {r['e_pts']:7.1f}{r['pts_p10']:5.0f}{r['pts_p90']:5.0f} | "
                f"{100*r['p_title']:6.1f}{100*r['p_ucl']:6.1f}{(100*r['p_ucl5'] if r['p_ucl5'] is not None else float('nan')):6.1f}{100*r['p_eur']:6.1f}"
                f"{100*r['p_rel']:6.1f}{(100*r['p_rel_po'] if r['p_rel_po'] is not None else float('nan')):6.1f} | "
                f"{r['rating_att']:5.2f}{r['rating_def']:5.2f}{r['rating_total']:+6.2f}{r['n_cur']:3d}")
    log(f"\nseason_projections.json γραφτηκε ({time.time()-t0:.0f}s).")
    out_f.close()


if __name__ == '__main__':
    main()
