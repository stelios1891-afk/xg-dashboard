# -*- coding: utf-8 -*-
"""nba_picks.py — VALUE PICKS NBA (6/10/2026, Στελιος «φτιαξε τη μηχανη»). Αντιγραφο του nba_picks (ιδιο ημερολογιο/κατασταση/μηνυματα) με αρχεια nba_*.
ΚΑΝΟΝΕΣ (nba_more_tests, καθαρο τεστ 2021-26): edge ≥8% · ΜΟΝΟ αν ηταν pick ΚΑΙ στην πρωτη γραμμη που ειδαμε (τα «αργα» picks: συνολα −15.8% 0/5)
· χαντικαπ ΟΧΙ απο τον 76ο αγωνα (21/10: ηταν 71· t27 LOSO) και στους 71-75 οχι pick υπερ ομαδας χωρις κινητρο κοντρα σε ομαδα με κινητρο. 19/10/2026: ΧΑΝΤΙΚΑΠ LIVE (Telegram) · ΣΥΝΟΛΑ ΚΡΥΦΑ: υπολογιζονται και γραφονται ΜΟΝΟ
στο nba_totals_log.jsonl για αναλυση — οχι ημερολογιο, οχι dashboard, οχι Telegram.
19/10/2026 (Στελιος «περνα το live»): οι απουσιες (ESPN Out) μπαινουν πλεον ΣΤΗΝ ΠΡΟΒΛΕΨΗ (nba_absence.py, nba_odds_scan) → το παλιο φιλτρο
«χωρις pick αν η πλευρα μας εχει νεα απουσια ≥30′» ΑΦΑΙΡΕΘΗΚΕ (το τεστ του ηταν look-ahead· η ESPN δινει μονο Out/Day-To-Day, οχι Doubtful).
ΣΚΙΩΔΗΣ «κοντρα στις ομαδες των πλει-οφ» (20/10, μονο καταγραφη → nba_shadow_po.jsonl): ομαδα με ≥8 νικες πλει-οφ περσι, αγων ≤15 → η αλλη πλευρα στην πρωτη γραμμη.
ΣΚΙΩΔΗΣ κανονας συνολων (μονο καταγραφη → nba_shadow_def.jsonl): ≤45′ πριν το τζαμπολ, ξαφνικες απουσιες με υπολοιπο ≥3 → «Over» στη γραμμη της στιγμης.
STEAM (19/10, ΔΟΚΙΜΑΣΤΙΚΟ live ¼ μοναδας + καταγραφη → nba_steam_log.jsonl): δικαιη τιμη χαντικαπ Pinnacle κινηθηκε ≥3 π. σε 60′ → πλευρα
της κινησης + φωτογραφια απουσιων · Telegram «🧪 STEAM» · ΕΚΤΟΣ ημερολογιου χαντικαπ (nba_clv_bets).
Κανονας και σ: απο nba_engine_test (βλ. HC_MIN και sigma_margin στο nba_projections.json)."""
import os, sys, json, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
from el_picks import cover
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
HC_MIN, ODDS_DELTA = 0.08, 0.05
PAPER_HCAP = False  # 19/10: ΧΑΝΤΙΚΑΠ LIVE (Στελιος «τα χαντικαπς τα θελουμε live») — ανοιγμα +7.1% Οκτ-Δεκ (B2B+απουσιες), αγων 1-10 το δυνατοτερο
PAPER_TOT = True    # ΣΥΝΟΛΑ μενουν ΚΑΤΑΓΡΑΦΗ (totals_test 19/10: κερδος μονο 2021-22, τελευταιες 2 σεζον αρνητικα)
TOT_LOG = 'nba_totals_log.jsonl'    # 19/10 (Στελιος «τα συνολα τα κραταμε, τα αναλυουμε, χωρις να εμφανιζονται»): ΚΡΥΦΟ αρχειο, εκτος ημερολογιου/οθονης/Telegram
def _is_tot_msg(t):                 # μηνυματα κατασταστασης (bk_pick_status.track) που αφορουν συνολα → οχι Telegram
    ls = t.split('\n'); return len(ls) > 1 and ls[1].replace('μπηκε: ', '').startswith(('Over ', 'Under '))
LATE_GP = 75                        # 21/10/2026 (Στελιος «περνα τα πικς μεχρι και τον 75ο»): t27 Τ1 LOSO οριου → 76 (+28/+31/+36μ vs 71)· αγωνας = μικροτερος των 2 ομαδων (+1)
MOTIV_FROM = 71                     # 21/10/2026 (Στελιος «κοψε τα μπετς υπερ ομαδων χωρις κινητρο»): αγωνες 71-75 → οχι pick ΥΠΕΡ ομαδας χωρις κινητρο
MOTIV_LOG = 'nba_motiv_skip.jsonl'  #   (κλειδωμενη / μαθ. εκτος play-in / 5 χειροτερες / πρακτικα εκτος) ΚΟΝΤΡΑ σε ομαδα με κινητρο (μαχη θεσης 1-6 ή play-in)· t24c/t27 Τ4
EAST = set('ATL BOS BRK CHO CHI CLE DET IND MIA MIL NYK ORL PHI TOR WAS'.split())
NOMOT, MOT = ('ΚΛΕΙΔΩΜΕΝΗ', 'ΑΔΙΑΦΟΡΗ', 'TANKING', 'ΠΡΑΚΤΙΚΑ ΕΚΤΟΣ'), ('ΜΑΧΗ ΘΕΣΗΣ 1-6', 'ΜΑΧΗ PLAY-IN')

def gnum(g):
    """αριθμος αγωνα οπως στα τεστ: μικροτερος των δυο ομαδων + 1"""
    return min(int(g.get('gp_h') or 0), int(g.get('gp_a') or 0)) + 1

def motiv_groups():
    """{ομαδα: γκρουπ κινητρου} απο τη βαθμολογια της κανονικης περιοδου ΤΩΡΑ (ιδιοι κανονες με t24/t27).
    TANKING = 5 χειροτερες λιγκας · ΑΔΙΑΦΟΡΗ = μαθ. εκτος 10ης · ΚΛΕΙΔΩΜΕΝΗ = ουτε πανω ουτε κατω · ΜΑΧΗ ΘΕΣΗΣ = 1-6 · ΜΑΧΗ PLAY-IN = 7-12 ·
    ΠΡΑΚΤΙΚΑ ΕΚΤΟΣ = θεση ≥11, ≥60 ματς, ≥5 νικες πισω απο τη 10η (οχι ακομα μαθ. εκτος). Μονο για ομαδες με ≥50 ματς."""
    import collections
    GM = _load(F('nba_espn_games.json'), {})
    W, Lc = collections.Counter(), collections.Counter()
    for g in GM.values():
        if g.get('stype') != 2 or g.get('hs') is None or g.get('as_') is None: continue
        hw = g['hs'] > g['as_']
        W[g['home'] if hw else g['away']] += 1; Lc[g['away'] if hw else g['home']] += 1
    teams = set(W) | set(Lc)
    if len(teams) < 30: return {}
    pct = {t: (W[t] + .5) / (W[t] + Lc[t] + 1) for t in teams}
    worst5 = set(sorted(teams, key=lambda t: pct[t])[:5]); out = {}
    for conf in (EAST, teams - EAST):
        ct = sorted([t for t in teams if t in conf], key=lambda t: -pct[t])
        if len(ct) < 15: continue
        Wn = [W[t] for t in ct]; Rn = [82 - W[t] - Lc[t] for t in ct]
        for r, t in enumerate(ct):
            gp = W[t] + Lc[t]; w, R = W[t], 82 - gp
            if gp < 50: continue
            up_ok = r > 0 and w + R >= Wn[r - 1]; down_ok = r < len(ct) - 1 and Wn[r + 1] + Rn[r + 1] >= w
            if t in worst5: g = 'TANKING'
            elif w + R < Wn[9]: g = 'ΑΔΙΑΦΟΡΗ'
            elif not up_ok and not down_ok: g = 'ΚΛΕΙΔΩΜΕΝΗ'
            elif r < 6: g = 'ΜΑΧΗ ΘΕΣΗΣ 1-6'
            elif r < 12: g = 'ΜΑΧΗ PLAY-IN'
            else: g = 'αλλη'
            if g in ('ΜΑΧΗ PLAY-IN', 'αλλη') and r >= 10 and gp >= 60 and Wn[9] - w >= 5: g = 'ΠΡΑΚΤΙΚΑ ΕΚΤΟΣ'
            out[t] = g
    return out

def motiv_skip(g, side, MG, now):
    """True → κοβεται (pick υπερ ομαδας χωρις κινητρο κοντρα σε ομαδα με κινητρο)· καταγραφη μια φορα ανα ματς/πλευρα στο MOTIV_LOG."""
    us, them = (g['hcode'], g['acode']) if side == 1 else (g['acode'], g['hcode'])
    gu, gt = MG.get(us), MG.get(them)
    if gu not in NOMOT or gt not in MOT: return False
    fn = F(MOTIV_LOG); key = f"{g['code']}|{side}"
    try: done = {json.loads(l).get('key') for l in open(fn, encoding='utf-8')} if os.path.exists(fn) else set()
    except Exception: done = set()
    if key not in done:
        with open(fn, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(dict(key=key, seen=now.isoformat(timespec='minutes'), code=g['code'], home=g['home'], away=g['away'], side=side,
                                     team=us, team_grp=gu, opp=them, opp_grp=gt, gnum=gnum(g)), ensure_ascii=False) + chr(10))
    print(f'NBA κινητρο: κοπηκε pick υπερ {us} ({gu}) κοντρα σε {them} ({gt}) · αγωνας {gnum(g)}')
    return True
MOVE_INJ = 1.5                      # 20/10: κινηση (δικαιη γραμμη, ποντοι) απο το ανοιγμα → στο νεο pick και η λιστα απουσιων
SHADOW_MIN = 45                     # 19/10: σκιωδης κανονας συνολων — λεπτα πριν το τζαμπολ
TOT_MIN, TOT_W = 0.08, 1.0          # NBA συνολα: μοντελο (με Φ3) μονο του, edge ≥8% — nba_fix_test: Οκτ-Δεκ +3.2% (3/5), ολη +1.9% (3/5), Κ2 ≈0
TOT_MIN_LATE, TOT_W_LATE = 0.08, 1.0
TOT_EARLY_GNO = 5
# ec_totals_bias_test / ec_totals_thr_test (Crown ανοιγμα U2020-25, αγων 7+): μιξη ≥6% −1.1% (125) · μοντελο μονο ≥6% +10.3% (339, 4/6)·
#   LOSO κατωφλιου ≤6% σε 6/6 · ζωνη 6-8% +27% (40), CLV +0.62, bootstrap P .96. ΠΡΟΣΟΧΗ: βαθμονομηση φτωχη (edge 15%+ → +2.2%).

def tot_rule(game):
    """(βαρος μοντελου, κατωφλι edge) για τα συνολα του ματς."""
    return (TOT_W, TOT_MIN) if int((game or {}).get('gno') or 0) <= TOT_EARLY_GNO else (TOT_W_LATE, TOT_MIN_LATE)

def tot_mix(game, pin, st):
    """Αναμενομενο συνολο για τα picks (αγων 1-6: μιξη 50/50 με την αγορα · 7+: μοντελο μονο του)· None αν λειπουν τιμες."""
    if not game or game.get('total') is None or game.get('total_src') != 'μοντελο' or pin.get('tl') is None or not pin.get('to') or not pin.get('tu'): return None
    from statistics import NormalDist
    T, ov, un = float(pin['tl']), float(pin['to']), float(pin['tu'])
    po = (1 / ov) / (1 / ov + 1 / un); mk = T + st * NormalDist().inv_cdf(min(max(po, 1e-4), 1 - 1e-4))
    return mk + tot_rule(game)[0] * (float(game['total']) - mk), mk

def _load(p, d):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return d

def shadow_def(g, pin, ko, now):
    """19/10: ΣΚΙΩΔΗΣ κανονας (news_rule.py): αμυντικος που λειπει ξαφνικα → η αγορα υποτιμα το συνολο. ΜΟΝΟ καταγραφη, μια φορα ανα ματς."""
    try:
        from nba_absence import SH_THR
        if not (0 < (ko - now).total_seconds() <= SHADOW_MIN * 60) or float(g.get('abs_shadow') or 0) < SH_THR: return
        if pin.get('tl') is None or not pin.get('to'): return
        fn = F('nba_shadow_def.jsonl'); done = set()
        if os.path.exists(fn):
            for ln in open(fn, encoding='utf-8'):
                try: done.add(str(json.loads(ln)['code']))
                except Exception: pass
        if str(g['code']) in done: return
        rec = dict(seen=now.isoformat(timespec='minutes'), code=g['code'], home=g['home'], away=g['away'], when=ko.strftime('%Y-%m-%dT%H:%M'),
                   bet=f"Over {float(pin['tl']):g}", line=float(pin['tl']), odds=float(pin['to']), shadow=g.get('abs_shadow'),
                   fresh=[p[0] for p in (g.get('abs_h') or []) + (g.get('abs_a') or []) if p[2]], model_total=g.get('total'), paper=True)
        with open(fn, 'a', encoding='utf-8') as fh: fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
        print(f"ΣΚΙΩΔΕΣ (αμυνα λειπει): {g['home']} - {g['away']} · Over {float(pin['tl']):g} @{float(pin['to']):.2f} · υπολοιπο {g.get('abs_shadow')}")
    except Exception as e:
        print('σκιωδης κανονας σφαλμα —', e)

STEAM_X, STEAM_W = 3.0, 3600           # 19/10 (Στελιος «ναι»): ΣΚΙΩΔΗΣ καταγραφη κινησεων ≥3 π. σε 60′ (steam_why.py: ≥3 π. +5.9% στο +5′,
STEAM_LOG, STEAM_STATE = 'nba_steam_log.jsonl', 'nba_steam_state.json'   # ανεξηγητες απο απουσιες +27% n77 post-hoc)
STEAM_LIVE, STEAM_STAKE = True, 0.25     # 19/10 (Στελιος «βαλτο λαιβ και σαν καταγραφη»): ΔΟΚΙΜΑΣΤΙΚΟ live, ¼ μοναδας, Telegram «🧪 STEAM» — εκτος ημερολογιου χαντικαπ
STEAM_NEW = []
def steam_watch(g, pin, o, ko, now, sm, ST):
    """Δικαιη τιμη Pinnacle (αναμενομενη διαφορα γηπ) ανα scan στο ST· αν κινηθηκε ≥STEAM_X απο την τιμη που ισχυε 60′ πριν → μια
    εγγραφη ανα ματς στο STEAM_LOG, με «φωτογραφια» απουσιων (διορθωση μας τωρα vs 60′ πριν + πληρης λιστα ESPN) για να ξεχωριζουμε
    κινησεις-ειδησεις απο κινησεις-χρημα χωρις εκ των υστερων γνωση."""
    try:
        from statistics import NormalDist
        L, oh, oa = float(pin['line']), float(pin['oh']), float(pin['oa'])
        ph = (1 / oh) / (1 / oh + 1 / oa); fair = -L + sm * NormalDist().inv_cdf(min(max(ph, 1e-4), 1 - 1e-4))
        ts = dt.datetime.fromisoformat(str(o.get('when') or now.isoformat(timespec='minutes'))).replace(tzinfo=dt.timezone.utc)
        H = ST.setdefault(str(g['code']), dict(h=[], done=False))
        if H['h'] and H['h'][-1][0] >= ts.isoformat(timespec='minutes'): return       # ιδιο scan Pinnacle — τιποτα νεο
        dm = float(g.get('abs_dm') or 0)
        H['h'].append([ts.isoformat(timespec='minutes'), round(fair, 3), round(dm, 3), L, oh, oa])
        H['h'] = [x for x in H['h'] if dt.datetime.fromisoformat(x[0]).replace(tzinfo=dt.timezone.utc) >= ts - dt.timedelta(seconds=3 * STEAM_W)]
        if H['done']: return
        ref = [x for x in H['h'] if dt.datetime.fromisoformat(x[0]).replace(tzinfo=dt.timezone.utc) <= ts - dt.timedelta(seconds=STEAM_W)]
        if not ref: return
        ref = ref[-1]; dF = fair - ref[1]
        if abs(dF) < STEAM_X: return
        sd = 1 if dF > 0 else -1; H['done'] = True
        inj = _load(F('nba_injuries.json'), {}); IT = {v.get('code'): v.get('players', []) for v in inj.get('teams', {}).values()}
        team, hc, od = (g['home'], L, oh) if sd == 1 else (g['away'], -L, oa)
        rec = dict(seen=now.isoformat(timespec='minutes'), scan_t=ts.isoformat(timespec='minutes'), code=g['code'], home=g['home'], away=g['away'],
                   when=ko.strftime('%Y-%m-%dT%H:%M'), hrs_before=round((ko - ts).total_seconds() / 3600, 2),
                   ref_t=ref[0], ref_age_min=round((ts - dt.datetime.fromisoformat(ref[0]).replace(tzinfo=dt.timezone.utc)).total_seconds() / 60),
                   move=round(dF, 2), side=sd, bet=f'{team} {hc:+g}', line=hc, odds=od, fair=round(fair, 2), fair_ref=ref[1], line_ref=ref[3],
                   abs_dm=round(dm, 2), abs_dm_ref=ref[2], news=round(sd * (dm - ref[2]), 2),      # news>0: η αλλαγη στις απουσιες ΕΞΗΓΕΙ την κινηση
                   abs_h=g.get('abs_h'), abs_a=g.get('abs_a'), inj_h=IT.get(g.get('hcode')), inj_a=IT.get(g.get('acode')), inj_fetched=inj.get('fetched'),
                   model_margin=g.get('margin'), paper=not STEAM_LIVE, stake=STEAM_STAKE if STEAM_LIVE else 0)
        with open(F(STEAM_LOG), 'a', encoding='utf-8') as fh: fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
        STEAM_NEW.append(rec)
        print(f"ΣΚΙΩΔΕΣ STEAM: {g['home']} - {g['away']} · κινηση {dF:+.1f} π. σε {rec['ref_age_min']}′ → {rec['bet']} @{od:.2f} · ειδηση {rec['news']:+.1f}")
    except Exception as e:
        print('steam watch σφαλμα —', e)

PO_WINS_MIN, PO_GW, PO_LOG = 8, 15, 'nba_shadow_po.jsonl'   # 20/10: ΣΚΙΩΔΗΣ «κοντρα στις ομαδες των πλει-οφ» (μονο καταγραφη)
# (endseason_test 20/10: ομαδες με ≥8 νικες πλει-οφ περσι, αγων ≤15: καλυψαν 42.5% στο ανοιγμα, ποντος κοντρα +10.7% (308, 4/5)· post-hoc)
def _po_wins(season):
    try:
        import pandas as pd
        L = pd.read_csv(F('nba_gamelogs.csv'), usecols=['table', 'season_end', 'team', 'team_game_score', 'opp_team_game_score'], low_memory=False)
        L = L[(L.table == 'team_game_log_post') & (L.season_end == season - 1)]
        return {t: int(v) for t, v in (pd.to_numeric(L.team_game_score) > pd.to_numeric(L.opp_team_game_score)).groupby(L.team).sum().items()}
    except Exception as e:
        print('πλει-οφ νικες σφαλμα —', e); return {}
def shadow_po(g, f0, pin, ko, now, POW, done):
    """Μια εγγραφη ανα (ματς, ομαδα πλει-οφ): ποντος ΚΟΝΤΡΑ στην ομαδα στην ΠΡΩΤΗ γραμμη (ιδιο με το τεστ: ανοιγμα)."""
    try:
        for side, t, gp in ((1, g['hcode'], g.get('gp_h')), (-1, g['acode'], g.get('gp_a'))):
            if POW.get(t, 0) < PO_WINS_MIN or int(gp or 0) + 1 > PO_GW or f"{g['code']}|{t}" in done: continue
            L0 = float(f0['line']); bet_side = -side
            rec = dict(seen=now.isoformat(timespec='minutes'), code=g['code'], home=g['home'], away=g['away'], when=ko.strftime('%Y-%m-%dT%H:%M'),
                       po_team=t, po_wins=POW[t], gno=int(gp or 0) + 1, side=bet_side, bet=f"{g['away'] if bet_side == -1 else g['home']} {(-L0 if bet_side == -1 else L0):+g}",
                       line=(-L0 if bet_side == -1 else L0), odds=float(f0['oa'] if bet_side == -1 else f0['oh']), line_now=float(pin['line']),
                       model_margin=g.get('margin'), paper=True)
            with open(F(PO_LOG), 'a', encoding='utf-8') as fh: fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
            done.add(f"{g['code']}|{t}")
            print(f"ΣΚΙΩΔΕΣ (κοντρα σε ομαδα πλει-οφ {t} {POW[t]} νικες): {rec['bet']} @{rec['odds']:.2f}")
    except Exception as e:
        print('σκιωδης πλει-οφ σφαλμα —', e)

def compute():
    proj = _load(F('nba_projections.json'), {}); odds = _load(F('nba_odds_latest.json'), {}).get('odds', {})
    sm, st = float(proj.get('sigma_margin', 11.5)), float(proj.get('sigma_total', 16.7))
    games = {str(g['code']): g for g in proj.get('games', [])}
    now = dt.datetime.now(dt.timezone.utc); picks = []
    global FIRST
    FIRST = _load(F('nba_first_lines.json'), {})
    ST = {k: v for k, v in _load(F(STEAM_STATE), {}).items() if k in odds}
    POW = _po_wins(int(proj.get('season') or 0)); PO_DONE = set()
    if os.path.exists(F(PO_LOG)):
        for ln in open(F(PO_LOG), encoding='utf-8'):
            try: r_ = json.loads(ln); PO_DONE.add(f"{r_['code']}|{r_['po_team']}")
            except Exception: pass
    MG = None                                   # γκρουπ κινητρου (υπολογιζονται μονο αν χρειαστουν: αγωνας ≥71)
    for code, o in odds.items():
        g = games.get(str(code)); pin = o.get('pin') or {}
        if not g or g.get('played'): continue
        ko = dt.datetime.fromisoformat(o['commence'].replace('Z', '+00:00'))
        if ko <= now: continue
        if pin.get('line') is None or not pin.get('oh') or not pin.get('oa'): continue
        base = dict(lg='NBA', paper=PAPER_HCAP, home=g['home'], away=g['away'], hcode=g['hcode'], acode=g['acode'], code=g['code'], round=g['round'], group=g.get('group'),
                    when=ko.strftime('%Y-%m-%dT%H:%M'), nba=True, model=proj.get('model', '')[:60])
        L, oh, oa = float(pin['line']), float(pin['oh']), float(pin['oa']); m = float(g['margin'])
        f0 = FIRST.setdefault(str(code), dict(line=L, oh=oh, oa=oa, tl=pin.get('tl'), to=pin.get('to'), tu=pin.get('tu'), seen=now.isoformat(timespec='minutes')))
        shadow_def(g, pin, ko, now)
        steam_watch(g, pin, o, ko, now, sm, ST)
        shadow_po(g, f0, pin, ko, now, POW, PO_DONE)
        pw, pp = cover(m, L, sm); pl = 1 - pw - pp
        pw0, pp0 = cover(m, float(f0['line']), sm); pl0 = 1 - pw0 - pp0
        for side, p_, od, hc in ((1, pw, oh, L), (-1, pl, oa, -L)):
            e = p_ * od + pp - 1
            e0 = (pw0 * f0['oh'] + pp0 - 1) if side == 1 else (pl0 * f0['oa'] + pp0 - 1)
            if e >= HC_MIN and e0 >= HC_MIN and gnum(g) <= LATE_GP:
                if gnum(g) >= MOTIV_FROM:
                    if MG is None: MG = motiv_groups()
                    if motiv_skip(g, side, MG, now): continue
                pk = dict(base, mkt='hcap', side=side, hcap=hc, odds=od, edge=round(e, 4),
                          proj_odds=round((p_ + (1 - p_ - pp)) / p_, 2) if p_ > 0 else None, model_line=round(-m, 1), mkt_line=L,
                          first=dict(line=f0['line'], oh=f0['oh'], oa=f0['oa'], seen=f0.get('seen')))
                try:                                   # 20/10 (Στελιος): κινηση αγορας απο το ανοιγμα (μονο ενδειξη)
                    import nba_board; pk['move_note'], pk['move_pts'] = nba_board.move_note(pk, f0, pin, sm)
                except Exception as e_:
                    print('κινηση αγορας σφαλμα —', e_)
                picks.append(pk)
        # ---- συνολο (6/10): μοντελο μονο του ≥8% ----
        tm = tot_mix(g, pin, st)
        tm0 = tot_mix(g, dict(tl=f0.get('tl'), to=f0.get('to'), tu=f0.get('tu')), st) if f0.get('tl') is not None else None
        if tm and tm0:
            mu, mk = tm; T = float(pin['tl']); T0 = float(f0['tl'])
            po0, pq0 = cover(tm0[0], -T0, st); pu0 = 1 - po0 - pq0
            ok0 = {'Over': po0 * float(f0['to']) + pq0 - 1 >= tot_rule(g)[1], 'Under': pu0 * float(f0['tu']) + pq0 - 1 >= tot_rule(g)[1]}
            po, pq = cover(mu, -T, st); pu = 1 - po - pq
            for nm, p_, od in (('Over', po, float(pin['to'])), ('Under', pu, float(pin['tu']))):
                e = p_ * od + pq - 1
                if e >= tot_rule(g)[1] and ok0[nm]:
                    picks.append(dict(base, mkt='total', paper=PAPER_TOT, side=0, hcap=T, bet=f'{nm} {T:g}', odds=od, edge=round(e, 4),
                                      proj_odds=round((p_ + (1 - p_ - pq)) / p_, 2) if p_ > 0 else None, model_total=round(float(g['total']), 1),
                                      mix_total=round(mu, 1), mkt_total=round(mk, 1), mkt_line=T, gno=g.get('gno')))
    json.dump(FIRST, open(F('nba_first_lines.json'), 'w', encoding='utf-8'))
    json.dump(ST, open(F(STEAM_STATE), 'w', encoding='utf-8'), ensure_ascii=False)
    return picks

def migrate():
    """19/10 (Στελιος): ΜΙΑ ΦΟΡΑ (idempotent) — τα χαντικαπ του ημερολογιου ΕΚΤΟΣ καταγραφης (live) · τα συνολα ΕΞΩ απο το ημερολογιο → TOT_LOG.
    Γινεται απο τον scanner (οχι χειροκινητα), ωστε να μη συγκρουεται με τα δικα του commits."""
    fn = F('nba_clv_bets.jsonl')
    if not os.path.exists(fn): return
    keep, moved, changed = [], [], False
    for ln in open(fn, encoding='utf-8'):
        if not ln.strip(): continue
        try: b = json.loads(ln)
        except Exception: keep.append(ln.rstrip('\n')); continue
        if b.get('mkt') == 'total': moved.append(b); changed = True; continue
        if b.get('mkt') == 'hcap' and b.get('paper'): b['paper'] = False; changed = True
        keep.append(json.dumps(b, ensure_ascii=False))
    if not changed: return
    if moved:
        with open(F(TOT_LOG), 'a', encoding='utf-8') as fh:
            for b in moved: fh.write(json.dumps(dict(b, migrated=True), ensure_ascii=False) + '\n')
    open(fn, 'w', encoding='utf-8').write('\n'.join(keep) + ('\n' if keep else ''))
    print(f'NBA ημερολογιο: {len(moved)} συνολα → {TOT_LOG} (κρυφα) · χαντικαπ εκτος καταγραφης')

def log_totals(tots, now):
    """Συνολα: ΜΟΝΟ στο κρυφο TOT_LOG (πρωτη εμφανιση καθε ματς & πλευρας), για αναλυση."""
    fn = F(TOT_LOG); done = set()
    if os.path.exists(fn):
        for ln in open(fn, encoding='utf-8'):
            try: b = json.loads(ln); done.add(f"{b['code']}|{str(b.get('bet', '')).split()[0]}")
            except Exception: pass
    new = [p for p in tots if f"{p['code']}|{p['bet'].split()[0]}" not in done]
    if new:
        with open(fn, 'a', encoding='utf-8') as fh:
            for p in new:
                fh.write(json.dumps(dict(seen=now, **{k: p.get(k) for k in ('lg', 'code', 'home', 'away', 'when', 'bet', 'hcap', 'odds', 'edge',
                                                                           'model_total', 'mkt_total', 'gno')}, paper=True), ensure_ascii=False) + '\n')
    return len(new)

def key(p):                                   # 7/10: ΕΝΑ pick ανα ματς & πλευρα (η γραμμη εκτος κλειδιου)
    import bk_pick_status as _b; return _b.side_key('NBA', p)
def line(p, prev=None):
    t = dt.datetime.fromisoformat(p['when']).replace(tzinfo=dt.timezone.utc)
    try:
        from zoneinfo import ZoneInfo; t = t.astimezone(ZoneInfo('Europe/Athens'))
    except Exception:
        t = t + dt.timedelta(hours=3)
    tm = f"{['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ'][t.weekday()]} {t:%d/%m %H:%M}"
    if p['mkt'] == 'total':
        bet = p['bet']; why = f"μοντελο {p['model_total']:.1f} · αγορα {p['mkt_total']:.1f}" + (f" · μιξη {p['mix_total']:.1f}" if abs(p['mix_total'] - p['model_total']) > .05 else '')
    else:
        team = p['home'] if p['side'] == 1 else p['away']
        bet = f"{team} {'+' if p['hcap'] >= 0 else ''}{p['hcap']:g}"; why = f"μοντελο {p['model_line']:+.1f} · αγορα {p['mkt_line']:+.1f}"
    ch = f" (ηταν {prev:.2f})" if prev else ''
    return (f"🏀 NBA · {tm}\n{p['home']} - {p['away']}\n"
            f"{bet} @{p['odds']:.2f}{ch} · edge {p['edge']*100:.0f}% · fair {p['proj_odds']:.2f}\n({why})"
            + (f"\n📈 {p['move_note']}" if p.get('move_note') and prev is None else ''))     # 20/10: κινηση αγορας απο το ανοιγμα

def inj_block(p, P=None):
    """20/10 (Στελιος): pick σε ματς με κινηση ≥1.5 π. απο το ανοιγμα → και η λιστα απουσιων των 2 ομαδων (εξηγει την κινηση;)."""
    if p.get('mkt') != 'hcap' or p.get('move_pts') is None or abs(p['move_pts']) < MOVE_INJ: return ''
    try:
        import nba_board
        return '\n🩹 Λιστα ESPN (κοστος αν λειψει · ✓ = ηδη στην προβλεψη):\n' + nba_board.inj_text(p['hcode'], p['acode'], p['home'], p['away'], P)
    except Exception as e:
        print('λιστα απουσιων σφαλμα —', e); return ''

def steam_line(r):
    t = dt.datetime.fromisoformat(r['when']).replace(tzinfo=dt.timezone.utc)
    try:
        from zoneinfo import ZoneInfo; t = t.astimezone(ZoneInfo('Europe/Athens'))
    except Exception:
        t = t + dt.timedelta(hours=3)
    tm = f"{['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ'][t.weekday()]} {t:%d/%m %H:%M}"
    why = (f"εξηγειται απο απουσιες (+{r['news']:.1f} π.)" if r['news'] >= 0.5 else
           'ΑΝΤΙΘΕΤΑ απο τις απουσιες' if r['news'] <= -0.5 else 'χωρις νεα απουσια (καθαρο χρημα)')
    return (f"🧪 STEAM NBA (δοκιμαστικο · {STEAM_STAKE:g} μοναδας) · {tm}\n{r['home']} - {r['away']}\n"
            f"{r['bet']} @{r['odds']:.2f} · ηταν {r['side'] * r['line_ref']:+g} πριν {r['ref_age_min']}′\n"
            f"(κινηση {abs(r['move']):.1f} π. · {r['hrs_before']:.1f}ω πριν · {why})")

def main(notify_tg=True):
    migrate()
    picks = compute()
    if STEAM_NEW:
        for r in STEAM_NEW: print(steam_line(r).replace('\n', ' | '))
        if notify_tg and STEAM_LIVE:
            try:
                import notify; notify.send((chr(10) * 2).join(steam_line(r) for r in STEAM_NEW))
            except Exception as e:
                print('Telegram σφαλμα (steam):', e)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes')
    tots = [p for p in picks if p['mkt'] == 'total']; picks = [p for p in picks if p['mkt'] != 'total']   # 19/10: συνολα ΚΡΥΦΑ
    n_tot_new = log_totals(tots, now)
    state = _load(F('nba_value_state.json'), {})
    import bk_pick_status as _b; _b.migrate_keys(state, 'NBA')
    new, changed, cur = [], [], set()
    for p in picks:
        k = key(p); cur.add(k); prev = state.get(k)
        if prev is None:
            new.append(p); state[k] = dict(odds=p['odds'], edge=p['edge'], when=p['when'], first_seen=now, hcap=p['hcap'])
        elif not _b.same_line(prev, p):                 # 7/10: ιδια πλευρα, αλλη γραμμη → ΙΔΙΟ pick, σιωπηλα (οχι νεο/ημερολογιο/Telegram)
            state[k].update(hcap=p['hcap'], odds=p['odds'], edge=p['edge'])
        elif abs(p['odds'] - prev.get('odds', p['odds'])) >= ODDS_DELTA:
            changed.append((p, prev.get('odds'))); state[k].update(odds=p['odds'], edge=p['edge'])
    for p in picks:
        st0 = state.get(key(p), {})
        try:
            p['hrs_birth'] = round((dt.datetime.fromisoformat(p['when']).replace(tzinfo=dt.timezone.utc)
                                    - dt.datetime.fromisoformat(st0.get('first_seen', now))).total_seconds() / 3600, 1)
        except Exception:
            p['hrs_birth'] = None
    today = now[:10]
    # 1/10/2026: pick που ΔΕΝ ισχυει πια → μηνυμα· ξαναγινεται → «ΞΑΝΑ PICK» (bk_pick_status, ιδιο με Ευρωλιγκα/εθνικες)
    import bk_pick_status as bps
    proj_ = _load(F('nba_projections.json'), {}); sm_, st_ = float(proj_.get('sigma_margin', 11.5)), float(proj_.get('sigma_total', 16.7))
    odds_ = _load(F('nba_odds_latest.json'), {}).get('odds', {})
    games_ = {str(g['code']): g for g in proj_.get('games', [])}
    for c_, g_ in list(games_.items()):                  # συνολα: ο ελεγχος «ισχυει ακομα;» με την ιδια μιξη 50/50
        tm_ = tot_mix(g_, (odds_.get(c_) or {}).get('pin') or {}, st_)
        if tm_: games_[c_] = dict(g_, total=tm_[0])
    drops, backs = bps.track(state, picks, F('nba_clv_bets.jsonl'), games_, odds_,
                             lambda m: sm_ if m == 'hcap' else st_, lambda m, g=None: HC_MIN if m == 'hcap' else tot_rule(g)[1], cover, 'NBA', now)
    state = {k: v for k, v in state.items() if k in cur or (v.get('when') or '9999')[:10] >= today}
    if new:
        with open(F('nba_clv_bets.jsonl'), 'a', encoding='utf-8') as fh:
            for p in new:
                fh.write(json.dumps(dict(seen=now, **{k: p[k] for k in ('lg', 'code', 'round', 'home', 'away', 'mkt', 'side', 'hcap', 'odds', 'edge', 'when')},
                                         bet=p.get('bet'), paper=p.get('paper', True), model_line=p.get('model_line'), model_total=p.get('model_total'), mix_total=p.get('mix_total'),
                                         mkt_total=p.get('mkt_total'), mkt_line=p.get('mkt_line'), model=p.get('model')), ensure_ascii=False) + '\n')
    json.dump(state, open(F('nba_value_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(dict(scanned_at=now, hc_min=HC_MIN, tot_min=TOT_MIN, tot_w=TOT_W, n_new=len(new), n_changed=len(changed), picks=picks),
              open(F('nba_value_latest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    new_l = [p for p in new if not p.get('paper', True)]; chg_l = [(p, pr) for p, pr in changed if not p.get('paper', True)]   # 19/10: μονο τα live (χαντικαπ)
    if notify_tg and (new_l or chg_l):
        msg = []
        if new_l:
            try:
                import nba_board; P_ = nba_board.players()
            except Exception:
                P_ = None
            msg += [f'🏀 {len(new_l)} ΝΕΑ value picks NBA', ''] + [line(p) + inj_block(p, P_) + '\n' for p in sorted(new_l, key=lambda x: x['when'])]
        if chg_l: msg += [f'🔄 {len(chg_l)} ΑΛΛΑΞΑΝ odds (NBA)'] + [line(p, pr) for p, pr in chg_l]
        try:
            import notify; notify.send('\n'.join(msg))
        except Exception as e:
            print('Telegram σφαλμα:', e)
    for t in backs + drops: print(t.replace(chr(10), ' | '))
    backs = [t for t in backs if not (PAPER_TOT and _is_tot_msg(t))]; drops = [t for t in drops if not (PAPER_TOT and _is_tot_msg(t))]
    if notify_tg and (backs or drops):
        try:
            import notify
            if backs: notify.send((chr(10) * 2).join(backs))
            if drops: notify.send('🏀 NBA · pick που ΔΕΝ ισχυει πια (αλλαξε γραμμη/τιμη)' + chr(10) * 2 + (chr(10) * 2).join(drops), silent=True)
        except Exception as e:
            print('Telegram σφαλμα (κατασταση):', e)
    print(f'[NBA picks] {len(picks)} χαντικαπ (live) · {len(new)} νεα · {len(changed)} αλλαγες · συνολα (κρυφα): {len(tots)} ({n_tot_new} νεα στο {TOT_LOG})')
    for p in picks: print('  ' + line(p).replace('\n', ' | '))
    return picks

if __name__ == '__main__':
    main(notify_tg='--no-tg' not in sys.argv)
