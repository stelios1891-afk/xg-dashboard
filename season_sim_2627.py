"""
season_sim_2627.py — ΦΕΤΙΝΗ (2026/27) προσομοιωση τελους σεζον, CORE7, με τη μεθοδο που περασε την
επικυρωση (season_sim_validate.py -> season_sim_choice.json). Εξοδος: season_projections.json (dashboard).

ΜΕΘΟΔΟΣ ΠΡΟΕΠΙΛΟΓΗΣ (αποφαση Στελιου 24/9/2026, season_sim_tests.py / season_sim_combo_test.py / season_sim_fade_test.py):
  D1_p1_c0.05 = βαση M2 (ρ=0.15, s0=0.10, Poisson x 1.13) + δυο στρωματα ΣΤΑ RATINGS του cutoff:
  (α) P1 opponent-adjusted xG στο ΦΕΤΙΝΟ κομματι, ΧΩΡΙΣ SoS: για καθε φετινο ματς καθε ομαδας
      xg_for x clip(μεσο xG λιγκας / xGA-ανα-ματς του αντιπαλου ΠΡΟ-ματς, .5, 2)  και
      xg_against x clip(μεσο xG λιγκας / xGF-ανα-ματς του αντιπαλου ΠΡΟ-ματς, .5, 2),
      προ-ματς = warm-start (περσινο flat prior + φετινα ως τοτε, K=8, ραμπα blend), μεσο xG = χαρακας λιγκας
      (περσινος -> φετινος, Kn=20, με τα ματς ως τοτε) — ΑΚΡΙΒΩΣ ο τυπος του B3/Δ1 των τεστ (opp_adjust_deep P1).
      Το φετινο rating ξαναχτιζεται απο τα διορθωμενα ματς (blend_league K=8 ραμπα πανω στο ιδιο live prior)· σουτ & γκολ raw.
  (β) στρωμα αξιας ροστερ c=0.05: Ax·exp(c·lv), Dx·exp(−c·lv), lv = ln(V_full / διαμεσος λιγκας των ομαδων με V),
      V_full απο core7_team_vfull.json (core7_team_vfull_build.py, τοπικα ~1x/μηνα)· ομαδες χωρις V -> lv=0·
      αν λειπει το αρχειο -> lv=0 για ολες + warning.
  Επικυρωση (train 2223-2425, κριση 2526): LL_mean .1302 -> .1263 (+.0038 ±.0014), 2526 .1288 -> .1231, MAE 5.29 -> 4.96,
  cov80 .759 -> .779. Το σβησιμο του P1 (fade test) και το SoS ΔΕΝ βελτιωνουν -> P1 πληρες ολη τη σεζον, SoS OFF.
FALLBACK: python season_sim_2627.py M2_r0.15_s0.10  (η προηγουμενη προεπιλογη: live ratings οπως το dashboard, με SoS).

Ratings βασης ΑΚΡΙΒΩΣ οπως το live dashboard: build_data.league_ratings (περσινο 2526 flat prior + φετινο 2627
warm-start K=8 + νεοφωτιστες με 2η κατηγορια λ=0.5 + χαρακας KN_NORM + SoS 1.5 @ n=6..13 [μονο στο M2 fallback]).
Fixtures/αποτελεσματα: FotMob leagues endpoint (results_view.season_matches): finished -> παιγμενα με σκορ,
οτιδηποτε αλλο (not started / σε εξελιξη) -> προσομοιωνεται· cancelled -> αγνοειται (δηλωμενο).
Θεσεις/κριτηρια ισοβαθμιας/ευρωπαικες θεσεις: season_sim.LEAGUE_RULES.
DEDUCTIONS 2627: κενο (καμια γνωστη σημερα).
Νεα πεδια στο season_projections.json (24/9): ανα ομαδα rating_total_raw (blend φετινο+περσινο ΧΩΡΙΣ SoS/P1/αξια),
vfull (εκ.€ ή null), lv· top-level p1, c_value, base_method, note. Ολα τα παλια πεδια αμεταβλητα.

Χρηση: python season_sim_2627.py [METHOD]   (προεπιλογη: chosen απο season_sim_choice.json)
"""
import os, sys, json, re, time, math
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
VFULL_FILE = 'core7_team_vfull.json'
P1_CLIP = (0.5, 2.0)


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
    """-> dict(s0, rho, db, p1, c). 'D1_p1_c0.05' = M2 ρ=.15 s0=.10 + P1 + αξια c· 'M2_r0.15_s0.10' = παλια προεπιλογη."""
    s0 = 0.0; rho = 0.0; db = SS.DRAW_BOOST; p1 = False; c = 0.0
    if name.startswith('D1'):
        s0, rho, p1, c = 0.10, 0.15, True, 0.05
    m = re.search(r'_s([0-9.]+)', name)
    if m: s0 = float(m.group(1))
    m = re.search(r'_r([0-9.]+)', name)
    if m: rho = float(m.group(1))
    m = re.search(r'_c([0-9.]+)', name)
    if m: c = float(m.group(1))
    if '_p1' in name: p1 = True
    if name.startswith('M3'): db = 1.0
    return dict(s0=s0, rho=rho, db=db, p1=p1, c=c)


def hist_raw(Mc_lg):
    """Φετινο rolling hist (ιδιο schema με picks.league_state) απο τα ματς της λιγκας — raw xG."""
    hist = {}
    for r in Mc_lg.itertuples(index=False):
        for tid, opp, sf, xf, sa, xa, gf, ga in [(int(r.home), int(r.away), r.h_ns, r.h_xg, r.a_ns, r.a_xg, r.hg, r.ag),
                                                 (int(r.away), int(r.home), r.a_ns, r.a_xg, r.h_ns, r.h_xg, r.ag, r.hg)]:
            h = hist.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[], opp=[]))
            h['sf'].append(sf); h['xf'].append(xf); h['sa'].append(sa); h['xa'].append(xa); h['gf'].append(gf); h['ga'].append(ga); h['opp'].append(opp)
    return hist


def hist_p1(Mc_lg, prior_r, pls, plx):
    """P1 opponent-adjusted φετινο hist (walk-forward, ΜΟΝΟ προ-ματς πληροφορια) — τυπος opp_adjust_deep P1 / season_sim_tests B3.
    -> (hist με xf/xa διορθωμενα, n_clip)."""
    Mc_lg = Mc_lg.sort_values(['date', 'mid']).reset_index(drop=True)
    hist = {}; acc = dict(ns=0.0, xg=0.0, n=0); nclip = 0

    def warm(tid):
        h = hist.get(tid); n = len(h['sf']) if h else 0
        p = prior_r[tid]
        return p if n == 0 else BD._shrink(BD._rating(h, n), p, n, BD.K_WARM)

    for r in Mc_lg.itertuples(index=False):
        H, A = int(r.home), int(r.away)
        if acc['n']:
            w = acc['n'] / (acc['n'] + BD.KN_NORM)
            ls = pls * ((acc['ns'] / acc['n']) / pls) ** w; lx = plx * ((acc['xg'] / max(acc['ns'], 1e-9)) / plx) ** w
        else:
            ls, lx = pls, plx
        wh = warm(H); wa = warm(A); lxls = ls * lx
        f = dict(hf=lxls / (wa[1] * wa[3]), af=lxls / (wh[1] * wh[3]), hg=lxls / (wa[0] * wa[2]), ag=lxls / (wh[0] * wh[2]))
        for k in f:
            if f[k] < P1_CLIP[0] or f[k] > P1_CLIP[1]:
                nclip += 1
            f[k] = float(np.clip(f[k], *P1_CLIP))
        acc['ns'] += r.h_ns + r.a_ns; acc['xg'] += r.h_xg + r.a_xg; acc['n'] += 2
        for tid, opp, sf, xf, sa, xa, gf, ga in [(H, A, r.h_ns, r.h_xg * f['hf'], r.a_ns, r.a_xg * f['hg'], r.hg, r.ag),
                                                 (A, H, r.a_ns, r.a_xg * f['af'], r.h_ns, r.h_xg * f['ag'], r.ag, r.hg)]:
            h = hist.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[], opp=[]))
            h['sf'].append(sf); h['xf'].append(xf); h['sa'].append(sa); h['xa'].append(xa); h['gf'].append(gf); h['ga'].append(ga); h['opp'].append(opp)
    return hist, nclip


def load_vfull(log):
    if not os.path.exists(VFULL_FILE):
        log(f"  !! {VFULL_FILE} ΔΕΝ βρεθηκε — στρωμα αξιας ανενεργο (lv=0 για ολες). Τρεξε core7_team_vfull_build.py τοπικα.")
        return {}, None
    d = json.load(open(VFULL_FILE, encoding='utf-8'))
    out = {lg: {int(t): v['vfull'] for t, v in L.items() if v.get('vfull')} for lg, L in d.get('leagues', {}).items()}
    return out, d.get('asof')


def value_layer(bl, V, c):
    """Ax·exp(c·lv), Dx·exp(−c·lv), lv = ln(V/διαμεσος λιγκας των ομαδων με V)· χωρις V -> lv=0. -> (blended, lv dict)."""
    lv = {t: 0.0 for t in bl}
    vs = [v for t, v in V.items() if t in bl and v and v > 0]
    if not c or len(vs) < 3:
        return dict(bl), lv
    med = float(np.median(vs))
    out = {}
    for t, r in bl.items():
        v = V.get(t)
        lv[t] = math.log(v / med) if (v and v > 0) else 0.0
        out[t] = (r[0] * math.exp(c * lv[t]), r[1] * math.exp(-c * lv[t]), r[2], r[3])
    return out, lv


def main():
    t0 = time.time()
    out_f = open('season_sim_2627_out.txt', 'w', encoding='utf-8')
    def log(s=''):
        print(s); out_f.write(s + '\n'); out_f.flush()
    choice = json.load(open('season_sim_choice.json', encoding='utf-8')) if os.path.exists('season_sim_choice.json') else {}
    method = sys.argv[1] if len(sys.argv) > 1 else choice.get('chosen') or 'M0'
    mp = parse_method(method); s0, rho, db, use_p1, c_val = mp['s0'], mp['rho'], mp['db'], mp['p1'], mp['c']
    log(f"SEASON PROJECTIONS 2026/27 — μεθοδος {method} (s0={s0}, ρ={rho}, draw_boost={db}, P1={use_p1}, αξια c={c_val}), N={N_RUNS}")
    Mp, id2name = picks.load_matches(list(BD.LEAGUE_FOTMOB), [BD.RATINGS_SEASON_DEFAULT])
    Mc, id2c = picks.load_matches(list(BD.LEAGUE_FOTMOB), [BD.CURRENT_SEASON])
    id2name.update(id2c); name2id = {v: k for k, v in id2name.items()}
    VF, vf_asof = load_vfull(log) if c_val else ({}, None)
    note = ("D1: M2 (ρ=.15,s0=.10) + P1 opponent-adjusted xG στο φετινο (walk-forward, clip .5-2, SoS OFF) + αξια ροστερ c=.05 "
            "(Ax·e^{c·lv}, Dx·e^{-c·lv}, lv=ln V_full/διαμεσος λιγκας, χωρις V -> 0). Επικυρωση 5σ: LL .1302->.1263, 2526 .1288->.1231."
            if use_p1 or c_val else "M2 βαση: live ratings (με SoS), χωρις P1/αξια.")
    proj = dict(generated=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'), method=method,
                s0=s0, rho=rho, draw_boost=db, n_runs=N_RUNS, p1=bool(use_p1), c_value=c_val,
                base_method='M2_r0.15_s0.10', vfull_asof=vf_asof, note=note, leagues={})
    for lg in SS.CORE7:
        # μια κληση FotMob για τα fixtures: cache ωστε το league_ratings (2x: prior-only + live) να μην ξανακατεβασει
        fx = BD.fetch_upcoming(lg); _orig_fu = BD.fetch_upcoming; BD.fetch_upcoming = lambda l, _fx=fx: _fx
        try:
            LR = BD.league_ratings(lg, Mp, Mc, id2name=id2name, name2id=name2id)                 # live (SoS οπου n=6..13)
            LR0 = BD.league_ratings(lg, Mp, Mc.iloc[0:0], id2name=id2name, name2id=name2id)     # ΜΟΝΟ prior (+ νεοφωτιστες)
        finally:
            BD.fetch_upcoming = _orig_fu
        bl_live, ns, lg_shots, lg_xgps, hf = LR['blended'], LR['ns'], LR['lg_shots'], LR['lg_xgps'], LR['hf']
        prior_r, pls, plx = LR0['blended'], LR0['lg_shots'], LR0['lg_xgps']
        Mc_lg = Mc[Mc.league == lg]
        bl_raw, _ = BD.blend_league(prior_r, hist_raw(Mc_lg))          # φετινο+περσινο ΧΩΡΙΣ SoS (αναφορα rating_total_raw)
        nclip = 0
        if use_p1:
            hp1, nclip = hist_p1(Mc_lg, prior_r, pls, plx)
            bl, _ = BD.blend_league(prior_r, hp1)                       # P1 ratings, SoS OFF
        else:
            bl = bl_live
        bl, lv = value_layer(bl, VF.get(lg, {}), c_val)
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
        Vlg = VF.get(lg, {})
        L = dict(n_teams=T, played_matches=len(played), remaining=len(fixtures), tiebreak=tb,
                 slots=dict(ucl=rules['ucl'], ucl5=rules['ucl5'], eur=rules['eur'], rel=rules['rel'], rel_po=rules['rel_po']),
                 lg_xg_mean=round(mean_xg, 3), promoted=[names[t] for t in LR['promoted'] if t in names],
                 n_with_vfull=sum(1 for t in teams if Vlg.get(t)), p1_clipped=int(nclip), teams={})
        for t in teams:
            s = summ[t]; Ax, Dx, SF, SA = bl[t]
            att = SF * Ax; dfn = SA * Dx
            rr = bl_raw.get(t, bl[t]); raw_tot = rr[2] * rr[0] - rr[3] * rr[1]
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
                rating_total_raw=round(raw_tot, 3),
                vfull=round(Vlg[t] / 1e6, 1) if Vlg.get(t) else None, lv=round(lv.get(t, 0.0), 3),
                n_cur=int(ns.get(t, 0)))
        proj['leagues'][lg] = L
        log(f"  {lg:13s}: {T} ομαδες, παιγμενα {len(played)}, υπολοιπα {len(fixtures)}, cancelled {skipped}, "
            f"νεοφωτιστες {L['promoted']}, με V_full {L['n_with_vfull']}/{T}, P1 clip {nclip}  ({time.time()-t0:.0f}s)")
    json.dump(proj, open('season_projections.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # ---------- πινακες ----------
    for lg in SS.CORE7:
        if lg not in proj['leagues']:
            continue
        L = proj['leagues'][lg]; rules = SS.LEAGUE_RULES[lg]
        rows = sorted(L['teams'].items(), key=lambda kv: -kv[1]['e_pts'])
        full = (lg == 'EPL')
        log(f"\n{'='*130}\n{lg} 2026/27 — προβολη τελους σεζον ({method}, N={N_RUNS}) — παιγμενα {L['played_matches']}, υπολοιπα {L['remaining']}\n{'='*130}")
        hdr = (f"{'#':>2s} {'Ομαδα':26s}{'P':>3s}{'W-D-L':>8s}{'Pts':>4s} | {'E[pts]':>7s}{'p10':>5s}{'p90':>5s} | "
               f"{'Τιτλ':>6s}{'UCL':>6s}{'UCL5':>6s}{'EUR':>6s}{'REL':>6s}{'RELpo':>6s} | {'raw':>6s}{'att':>5s}{'def':>5s}{'tot':>6s}{'V':>5s}{'lv':>6s}{'n':>3s}")
        log(hdr); log('-' * len(hdr))
        for i, (nm, r) in enumerate(rows):
            if not full and 3 <= i < len(rows) - 3:
                if i == 3: log('   ...')
                continue
            log(f"{i+1:2d} {nm[:26]:26s}{r['played']:3d}{r['w']:3d}-{r['d']:d}-{r['l']:<2d}{r['pts_now']:4d} | {r['e_pts']:7.1f}{r['pts_p10']:5.0f}{r['pts_p90']:5.0f} | "
                f"{100*r['p_title']:6.1f}{100*r['p_ucl']:6.1f}{(100*r['p_ucl5'] if r['p_ucl5'] is not None else float('nan')):6.1f}{100*r['p_eur']:6.1f}"
                f"{100*r['p_rel']:6.1f}{(100*r['p_rel_po'] if r['p_rel_po'] is not None else float('nan')):6.1f} | "
                f"{r['rating_total_raw']:+6.2f}{r['rating_att']:5.2f}{r['rating_def']:5.2f}{r['rating_total']:+6.2f}"
                f"{(r['vfull'] if r['vfull'] is not None else float('nan')):5.0f}{r['lv']:+6.2f}{r['n_cur']:3d}")
    log(f"\nseason_projections.json γραφτηκε ({time.time()-t0:.0f}s).")
    out_f.close()


if __name__ == '__main__':
    main()
