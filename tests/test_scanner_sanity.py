# -*- coding: utf-8 -*-
"""
test_scanner_sanity.py — regression / sanity tests για τον live scanner (18/9/2026).

Σκοπος: να τρεχει ΠΡΙΝ απο καθε commit του scanner (scanner_tick.sh / euro-refresh /
data-refresh) και να μπλοκαρει τα προφανη:
  (a) ακεραιοτητα αρχειων εξοδου (JSON/JSONL φορτωνουν, ΟΧΙ git conflict markers,
      ΟΧΙ διπλες εγγραφες στο clv_bets, μονοτονα timestamps στο odds_history)
  (b) «κλειδωμενες» σταθερες του live μοντελου (ενα λαθος autostash να πιανεται)
      + MIN_PRIOR: cloud=6 (committed), τοπικα 6 ή 14
  (c) λογικη picks πανω στο τρεχον value_picks_latest.json
  (d) αναπαραγωγη pricing (golden values απο picks.evaluate_bet, 18/9/2026)
  (e) ευρωπαικα picks (euro_value_latest.json) — UEL μονο ως σκια (no_play=True)

ΧΩΡΙΣ δικτυο. Εξαρτησεις: pytest (+ οτι ηδη χρειαζεται το picks.py: pandas/numpy).
Τρεξιμο:  python -m pytest -q tests/test_scanner_sanity.py
"""
import os, sys, re, ast, json, math, subprocess, datetime

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'dashboard'))
os.chdir(ROOT)

IS_CLOUD = os.environ.get('GITHUB_ACTIONS') == 'true'

CORE7 = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
EURO_ALLOWED = {'ChampionsLeague', 'ConferenceLeague'}        # παιζονται
EURO_SHADOW = {'EuropaLeague'}                                # UEL ΚΛΕΙΣΤΟ 11/9 → ορατο ως ΣΚΙΑ (no_play=True), 18/9
KELLY_FRAC, STAKE_CAP = 0.125, 0.20
EPS = 1e-9

JSON_FILES = ['value_picks_latest.json', 'market_1x2_latest.json',
              'euro_value_latest.json', 'value_scan_state.json']
JSONL_FILES = ['odds_history.jsonl', 'clv_bets.jsonl', 'clv_ledger.jsonl',
               'dom_live_odds.jsonl', 'projected_lineups.jsonl']
CONFLICT_RE = re.compile(r'^(<<<<<<<|=======|>>>>>>>)')


# ----------------------------------------------------------------- βοηθητικα
def _p(name):
    return os.path.join(ROOT, name)


def _need(name):
    """Το αρχειο πρεπει να υπαρχει· αλλιως skip (δεν ειναι μερος αυτου του checkout)."""
    if not os.path.exists(_p(name)):
        pytest.skip(f'{name}: δεν υπαρχει σε αυτο το checkout')
    return _p(name)


def _json(name):
    path = _need(name)
    if os.path.getsize(path) == 0:
        pytest.fail(f'{name}: ΑΔΕΙΟ αρχειο (0 bytes) — το dashboard/scanner θα σκασει στο json.load')
    with open(path, encoding='utf-8') as fh:
        try:
            return json.load(fh)
        except Exception as e:
            pytest.fail(f'{name}: δεν φορτωνει ως JSON ({type(e).__name__}: {e})')


def _jsonl(name):
    """Καθε μη-κενη γραμμη πρεπει να ειναι εγκυρο JSON. Επιστρεφει λιστα dict."""
    path = _need(name)
    rows, bad = [], []
    with open(path, encoding='utf-8') as fh:
        for i, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception as e:
                bad.append(f'γραμμη {i}: {type(e).__name__} -> {line[:80]!r}')
    assert not bad, f'{name}: {len(bad)} γραμμες δεν ειναι εγκυρο JSON (πιθανο μισο-γραψιμο/conflict):\n' + '\n'.join(bad[:5])
    return rows


def _src_const(fname, name):
    """Τιμη σταθερας απο τον πηγαιο κωδικα (AST, ΧΩΡΙΣ import/εκτελεση) — για scripts που
    τρεχουν βαρια δουλεια στο import (euro_live_projections) ή σταθερες μεσα σε συναρτησεις
    (toa_live KELLY_FRAC/CAP, euro_shadow_scan EDGE_*). Πιανει και tuple-assign
    `A, B = 1, 2`. Επιστρεφει την ΤΕΛΕΥΤΑΙΑ αναθεση στο αρχειο."""
    with open(_p(fname), encoding='utf-8') as fh:
        tree = ast.parse(fh.read(), fname)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and tgt.id == name:
                try:
                    found.append(ast.literal_eval(node.value))
                except Exception:
                    pass
            elif isinstance(tgt, ast.Tuple) and isinstance(node.value, ast.Tuple):
                for el, val in zip(tgt.elts, node.value.elts):
                    if isinstance(el, ast.Name) and el.id == name:
                        try:
                            found.append(ast.literal_eval(val))
                        except Exception:
                            pass
    assert found, f'{fname}: δεν βρεθηκε σταθερα {name} στον κωδικα'
    return found[-1]


def _dt(s):
    """iso (με/χωρις tz, με/χωρις Z) -> aware UTC datetime ή None."""
    if not s:
        return None
    try:
        d = datetime.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    except ValueError:
        return None
    return d.replace(tzinfo=datetime.timezone.utc) if d.tzinfo is None else d.astimezone(datetime.timezone.utc)


def _approx(a, b, tol=EPS):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


# ================================================================ (a) ΑΚΕΡΑΙΟΤΗΤΑ ΑΡΧΕΙΩΝ
@pytest.mark.parametrize('name', JSON_FILES + JSONL_FILES)
def test_a_no_git_conflict_markers(name):
    path = _need(name)
    hits = []
    with open(path, encoding='utf-8', errors='replace') as fh:
        for i, line in enumerate(fh, 1):
            if CONFLICT_RE.match(line):
                hits.append(f'γραμμη {i}: {line.rstrip()[:60]}')
    assert not hits, (f'{name}: ΒΡΕΘΗΚΑΝ git conflict markers (<<<<<<< / ======= / >>>>>>>) — '
                      f'αποτυχημενο autostash/rebase, ΜΗΝ γινει commit:\n' + '\n'.join(hits[:6]))


@pytest.mark.parametrize('name', JSON_FILES)
def test_a_json_loads(name):
    d = _json(name)
    assert isinstance(d, dict), f'{name}: περιμενα dict στη ριζα, βρηκα {type(d).__name__}'


@pytest.mark.parametrize('name', JSONL_FILES)
def test_a_jsonl_every_line_parses(name):
    rows = _jsonl(name)
    assert all(isinstance(r, dict) for r in rows), f'{name}: υπαρχουν γραμμες που δεν ειναι JSON object'


def test_a_value_picks_shape():
    d = _json('value_picks_latest.json')
    for k in ('scanned_at', 'ratings_season', 'gross', 'scale', 'cap', 'picks'):
        assert k in d, f'value_picks_latest.json: λειπει το πεδιο {k!r}'
    assert isinstance(d['picks'], list), 'value_picks_latest.json: το picks δεν ειναι λιστα'
    need = {'lg', 'home', 'away', 'home_id', 'away_id', 'when', 'md', 'mxh', 'mxa',
            'side', 'hcap', 'odds', 'pw', 'pp', 'edge', 'proj_odds', 'stake', 'stake_final'}
    for p in d['picks']:
        miss = need - set(p)
        assert not miss, f'pick {p.get("home")}-{p.get("away")}: λειπουν πεδια {sorted(miss)}'
        assert p['side'] in (1, -1), f'pick {p["home"]}-{p["away"]}: side={p["side"]} (περιμενα ±1)'


def test_a_market_1x2_shape():
    d = _json('market_1x2_latest.json')
    assert 'scanned_at' in d and isinstance(d.get('odds'), dict), 'market_1x2_latest.json: περιμενα {scanned_at, odds{}}'
    for k, v in d['odds'].items():
        assert re.fullmatch(r'\d+_\d+', k), f'market_1x2: κλειδι {k!r} δεν ειναι "hid_aid"'
        for f in ('h', 'd', 'a'):
            assert isinstance(v.get(f), (int, float)) and v[f] > 1.0, f'market_1x2 {k}: αποδοση {f}={v.get(f)!r} μη εγκυρη'
        assert _dt(v.get('when')) is not None, f'market_1x2 {k}: when={v.get("when")!r} δεν ειναι ημερομηνια'


def test_a_scan_state_shape():
    d = _json('value_scan_state.json')
    for k, v in d.items():
        parts = k.split('|')
        assert len(parts) == 5, f'value_scan_state: κλειδι {k!r} δεν ειναι "lg|home|away|side|hcap"'
        assert parts[0] in CORE7, f'value_scan_state: λιγκα {parts[0]!r} εκτος CORE7 στο κλειδι {k!r}'
        assert isinstance(v.get('odds'), (int, float)) and 'edge' in v, f'value_scan_state {k!r}: λειπει odds/edge'


def test_a_clv_bets_no_duplicate_entries():
    """Ιδιο ματς + ιδια πλευρα + ιδια γραμμη = μια εγγραφη (το state του scanner το εγγυαται·
    διπλη σημαινει χαμενο/κατεστραμμενο state). Σημ.: ιδιο ματς/πλευρα με ΑΛΛΗ γραμμη
    ειναι νομιμο (η γραμμη κουνηθηκε -> νεο pick, βλ. scan_value.pick_key)."""
    rows = _jsonl('clv_bets.jsonl')
    seen, dup = {}, []
    for i, b in enumerate(rows, 1):
        key = (b.get('hid'), b.get('aid'), b.get('ko'), b.get('side'), b.get('hcap'), bool(b.get('h72')))   # 26/9: h72 = εισοδος ≤72ω (νομιμη διπλη με παλια)
        if key in seen:
            dup.append(f'{b.get("lg")} {b.get("home")}-{b.get("away")} side={b.get("side")} hcap={b.get("hcap")} '
                       f'(γραμμες {seen[key]} & {i})')
        seen[key] = i
    assert not dup, f'clv_bets.jsonl: {len(dup)} ΔΙΠΛΕΣ εγγραφες ιδιου (ματς, πλευρα, γραμμη):\n' + '\n'.join(dup[:8])


def test_a_clv_bets_h72_once_per_match_side():
    """26/9/2026: απο εδω και περα μια εισοδος (h72) ανα ματς & πλευρα, μεσα σε 72ω πριν τη σεντρα."""
    rows = [b for b in _jsonl('clv_bets.jsonl') if b.get('h72')]
    seen = set()
    for b in rows:
        k = (b.get('hid'), b.get('aid'), str(b.get('ko'))[:16], b.get('side'))
        assert k not in seen, f'clv_bets: 2η εισοδος h72 για {b.get("home")}-{b.get("away")} side={b.get("side")}'
        seen.add(k)
        assert 0 < b.get('hours_before', 0) <= 72, f'clv_bets h72 εκτος 72ω: {b.get("home")}-{b.get("away")} {b.get("hours_before")}'


def test_a_clv_bets_fields():
    rows = _jsonl('clv_bets.jsonl')
    need = {'seen', 'lg', 'home', 'away', 'hid', 'aid', 'ko', 'side', 'hcap', 'odds', 'edge', 'stake'}
    for i, b in enumerate(rows, 1):
        miss = need - set(b)
        assert not miss, f'clv_bets γραμμη {i}: λειπουν πεδια {sorted(miss)}'
        assert b['lg'] in CORE7, f'clv_bets γραμμη {i}: λιγκα {b["lg"]!r} εκτος CORE7'


@pytest.mark.parametrize('name', ['odds_history.jsonl', 'dom_live_odds.jsonl'])
def test_a_timestamps_monotonic(name):
    rows = _jsonl(name)
    prev, prev_i, bad = None, 0, []
    for i, r in enumerate(rows, 1):
        t = _dt(r.get('t'))
        assert t is not None, f'{name} γραμμη {i}: t={r.get("t")!r} δεν ειναι ημερομηνια'
        if prev is not None and t < prev:
            bad.append(f'γραμμη {i}: {r["t"]} < γραμμη {prev_i}: {rows[prev_i-1]["t"]}')
        prev, prev_i = t, i
    assert not bad, (f'{name}: τα timestamps ΔΕΝ ειναι μονοτονα ({len(bad)} πισωγυρισματα — '
                     f'πιθανο ανακατεμα γραμμων απο rebase/autostash):\n' + '\n'.join(bad[:6]))


def test_a_odds_history_rows_shape():
    rows = _jsonl('odds_history.jsonl')
    need = {'t', 'lg', 'hid', 'aid', 'ko', 'line', 'oh', 'oa'}
    for i, r in enumerate(rows, 1):
        miss = need - set(r)
        assert not miss, f'odds_history γραμμη {i}: λειπουν πεδια {sorted(miss)}'
        assert r['lg'] in CORE7, f'odds_history γραμμη {i}: λιγκα {r["lg"]!r} εκτος CORE7'


# ================================================================ (b) ΚΛΕΙΔΩΜΕΝΕΣ ΣΤΑΘΕΡΕΣ
def test_b_picks_locked_constants():
    import picks
    exp = dict(EDGE=0.10, OMIN=1.70, OMAX=2.10, MIN_LINE=0.5, DRAW_BOOST=1.13, MARGIN=0.03,
               BLEND=0.60, DECAY=0.96, SOS=1.5, SOS_MIN_N=6, SOS_MAX_N=13,
               BLEND_EARLY=1.00, BLEND_SPLIT=13, BLEND_KG=12.0)
    bad = [f'{k}={getattr(picks, k, None)!r} (περιμενα {v!r})' for k, v in exp.items()
           if not _approx(getattr(picks, k, None), v)]
    assert not bad, 'picks.py: ΑΛΛΑΞΑΝ κλειδωμενες σταθερες (λαθος autostash/commit;): ' + ', '.join(bad)


def test_b_picks_hfa_and_core7():
    import picks
    exp_hfa = {'EPL': 1.10, 'LaLiga': 1.15, 'SerieA': 1.08, 'Bundesliga': 1.12, 'Ligue1': 1.105,
               'Eredivisie': 1.130, 'PrimeiraLiga': 1.116}
    bad = [f'{lg}: {picks.HFA_FIX.get(lg)!r} (περιμενα {v})' for lg, v in exp_hfa.items()
           if not _approx(picks.HFA_FIX.get(lg), v)]
    assert not bad, 'picks.HFA_FIX: αλλαξε το σταθερο HFA: ' + ', '.join(bad)
    assert list(picks.TOP5) == CORE7, f'picks.TOP5 (CORE7) = {picks.TOP5} — περιμενα {CORE7} (Belgium/ScottishPrem ΕΚΤΟΣ απο 8/2026)'


def test_b_blend_ramp_lands_on_060():
    import picks
    assert _approx(picks.blend_at(None), 0.60) and _approx(picks.blend_at(14), 0.60), \
        f'blend_at: ωριμο βαρος xG {picks.blend_at(None)} / 14η {picks.blend_at(14)} — περιμενα 0.60'
    assert _approx(picks.blend_at(0), 1.00), f'blend_at(0)={picks.blend_at(0)} — περιμενα 1.00 (md1 = 100% xG)'
    assert picks.blend_at(7) > picks.blend_at(10) > picks.blend_at(13) - EPS, 'blend_at: η ραμπα δεν ειναι φθινουσα προς το 0.60'
    assert _approx(picks.blend_at(13), 0.60), f'blend_at(13)={picks.blend_at(13)} — η ραμπα πρεπει να προσγειωνεται ΑΚΡΙΒΩΣ στο 0.60 στη 13η (καμια ασυνεχεια 13/14)'


def test_b_min_prior_cloud_is_6():
    """MIN_PRIOR: cloud (GitHub Actions / committed HEAD) = 6 · τοπικο working copy = 14
    (παιζει 15η+) ή 6. Το 14 ΔΕΝ πρεπει ΠΟΤΕ να φτασει στο cloud (memory min-prior-switch-point)."""
    import picks
    if IS_CLOUD:
        assert picks.MIN_PRIOR == 6, (f'ΣΤΟ CLOUD picks.MIN_PRIOR={picks.MIN_PRIOR} — περιμενα 6. '
                                      f'Το τοπικο 14 εφτασε στο repo (λαθος commit/autostash)!')
    else:
        assert picks.MIN_PRIOR in (6, 14), f'picks.MIN_PRIOR={picks.MIN_PRIOR} — τοπικα επιτρεπονται μονο 6 ή 14'


def test_b_min_prior_committed_head_is_6():
    """Ο,τι ειναι committed (= αυτο που τρεχει ο cloud scanner) πρεπει να εχει MIN_PRIOR = 6."""
    try:
        src = subprocess.run(['git', 'show', 'HEAD:picks.py'], cwd=ROOT, capture_output=True,
                             timeout=30).stdout.decode('utf-8', errors='replace')
    except Exception as e:
        pytest.skip(f'git δεν ειναι διαθεσιμο ({type(e).__name__})')
    if not src.strip():
        pytest.skip('κενο committed picks.py (rev-parse/shallow;)')
    # 2026-09-18: ο διακοπτης ειναι ρητος — MIN_PRIOR = 6 if os.environ.get('GITHUB_ACTIONS') == 'true' else 14.
    # Δεκτο: (α) η env-μορφη με 6 στο cloud σκελος, ή (β) σκετο MIN_PRIOR = 6 (παλιο σχημα). ΟΧΙ σκετο 14.
    m_env = re.search(r"^MIN_PRIOR\s*=\s*(\d+)\s+if\s+os\.environ\.get\('GITHUB_ACTIONS'\)\s*==\s*'true'\s+else\s+(\d+)", src, re.M)
    m_old = re.search(r'^\s*BLEND\s*=.*?MIN_PRIOR\s*=\s*(\d+)', src, re.M) or re.search(r'^MIN_PRIOR\s*=\s*(\d+)\s*(#.*)?$', src, re.M)
    if m_env:
        assert int(m_env.group(1)) == 6, (f'COMMITTED picks.py: το cloud σκελος του MIN_PRIOR ειναι {m_env.group(1)} — περιμενα 6.')
    elif m_old:
        assert int(m_old.group(1)) == 6, (f'COMMITTED picks.py (HEAD) εχει MIN_PRIOR={m_old.group(1)} — περιμενα 6. '
                                          f'Το τοπικο 14 μπηκε στο repo· ο cloud scanner θα σιωπησει μεχρι τη 15η!')
    else:
        pytest.fail('δεν βρεθηκε MIN_PRIOR στο committed picks.py σε καμια απο τις δυο αποδεκτες μορφες')


def test_b_build_data_constants():
    import build_data
    assert build_data.CURRENT_SEASON == '2627', f'build_data.CURRENT_SEASON={build_data.CURRENT_SEASON!r} (περιμενα 2627)'
    assert build_data.RATINGS_SEASON_DEFAULT == '2526', f'build_data.RATINGS_SEASON_DEFAULT={build_data.RATINGS_SEASON_DEFAULT!r} (περιμενα 2526)'
    assert _approx(build_data.K_WARM, 8.0), f'build_data.K_WARM={build_data.K_WARM} (περιμενα 8 — warm-start n/(n+8))'
    assert _approx(build_data.KN_NORM, 20.0), f'build_data.KN_NORM={build_data.KN_NORM} (περιμενα 20)'
    assert set(build_data.LEAGUE_FOTMOB) >= set(CORE7), f'build_data.LEAGUE_FOTMOB λειπουν λιγκες CORE7: {set(CORE7) - set(build_data.LEAGUE_FOTMOB)}'


def test_b_scan_value_and_toa_constants():
    import scan_value, toa_live, build_data
    assert scan_value.RATINGS_SEASON == build_data.RATINGS_SEASON_DEFAULT == '2526', \
        f'scan_value.RATINGS_SEASON={scan_value.RATINGS_SEASON!r} / build_data {build_data.RATINGS_SEASON_DEFAULT!r} — περιμενα 2526 (περσινο prior)'
    assert _approx(scan_value.ODDS_DELTA, 0.05), f'scan_value.ODDS_DELTA={scan_value.ODDS_DELTA} (περιμενα 0.05)'
    assert list(toa_live.SPORT) == CORE7, f'toa_live.SPORT λιγκες = {list(toa_live.SPORT)} — περιμενα CORE7 {CORE7}'
    kf = _src_const('toa_live.py', 'KELLY_FRAC'); cap = _src_const('toa_live.py', 'CAP')
    assert _approx(kf, KELLY_FRAC), f'toa_live KELLY_FRAC={kf} (περιμενα 0.125 = 1/8 Kelly)'
    assert _approx(cap, STAKE_CAP), f'toa_live CAP={cap} (περιμενα 0.20 συνολικη εκθεση)'


def test_b_euro_locked_constants():
    """Ευρωπαικο stack (μεσω AST — το euro_live_projections.py τρεχει βαρια δουλεια στο import)."""
    exp_proj = dict(GAMMA_LG_DEFLATE=-0.470, UCL_FAV_SCALE=1.16, EU_DRAW_SCALE=0.85, W_EU=2.0)
    bad = [f'{k}={_src_const("euro_live_projections.py", k)!r} (περιμενα {v})' for k, v in exp_proj.items()
           if not _approx(_src_const('euro_live_projections.py', k), v)]
    assert not bad, 'euro_live_projections.py: αλλαξαν σταθερες (γ ξεφουσκωμα / κ UCL / X-scale / w prior): ' + ', '.join(bad)
    exp_scan = dict(EDGE_DOG=0.10, EDGE_FAV=0.04, EDGE_OVER=0.04, EDGE_FAV_UCL=0.10, EDGE_DOG_UCL=0.04)
    bad = [f'{k}={_src_const("euro_shadow_scan.py", k)!r} (περιμενα {v})' for k, v in exp_scan.items()
           if not _approx(_src_const('euro_shadow_scan.py', k), v)]
    assert not bad, 'euro_shadow_scan.py: αλλαξαν κατωφλια (UCL favs @10 / UCL dogs @4 / dogs @10 / favs @4): ' + ', '.join(bad)
    exp_eng = dict(GAMMA_PLAYER=1.09, KN_NORM=20.0, MIN_NOPRIOR_N=6)
    bad = [f'{k}={_src_const("euro_engine.py", k)!r} (περιμενα {v})' for k, v in exp_eng.items()
           if not _approx(_src_const('euro_engine.py', k), v)]
    assert not bad, 'euro_engine.py: αλλαξαν σταθερες: ' + ', '.join(bad)


def test_b_euro_projections_header_matches_source():
    """Το euro_projections.json (εισοδος του euro scanner) πρεπει να εχει βγει με τις live σταθερες."""
    d = _json('euro_projections.json')
    exp = dict(lg_deflate=-0.470, ucl_fav_scale=1.16, eu_draw_scale=0.85, w_eu_prior=2.0)
    bad = [f'{k}={d.get(k)!r} (περιμενα {v})' for k, v in exp.items() if not _approx(d.get(k), v)]
    assert not bad, 'euro_projections.json βγηκε με ΑΛΛΕΣ σταθερες απο τις live: ' + ', '.join(bad)


# ================================================================ (c) ΛΟΓΙΚΗ PICKS (τρεχον αρχειο)
def _picks():
    d = _json('value_picks_latest.json')
    return d, d.get('picks', [])


def _lab(p):
    team = p['home'] if p['side'] == 1 else p['away']
    return f'[{p["lg"]}] {p["home"]}-{p["away"]} {team} +{p["hcap"]:g} @{p["odds"]}'


def test_c_odds_in_zone():
    import picks
    _, P = _picks()
    bad = [f'{_lab(p)} (odds {p["odds"]})' for p in P if not (picks.OMIN - EPS <= p['odds'] <= picks.OMAX + EPS)]
    assert not bad, f'picks εκτος ζωνης αποδοσεων [{picks.OMIN}, {picks.OMAX}]:\n' + '\n'.join(bad)


def test_c_only_dog_side_hcap_ge_half():
    import picks
    _, P = _picks()
    bad = [f'{_lab(p)} (hcap {p["hcap"]})' for p in P if p['hcap'] < picks.MIN_LINE - EPS]
    assert not bad, f'picks με hcap < {picks.MIN_LINE} (ΜΟΝΟ +handicap πλευρα dog >= 0.5 επιτρεπεται):\n' + '\n'.join(bad)


def test_c_edge_threshold():
    import picks
    _, P = _picks()
    bad = [f'{_lab(p)} edge {p["edge"]*100:.2f}%' for p in P if p['edge'] < picks.EDGE - EPS]
    assert not bad, f'picks με edge < {picks.EDGE*100:.0f}% (εγχωριο κατωφλι):\n' + '\n'.join(bad)


def test_c_league_in_core7():
    _, P = _picks()
    bad = [f'{_lab(p)}' for p in P if p['lg'] not in CORE7]
    assert not bad, 'picks σε λιγκα ΕΚΤΟΣ CORE7 (Belgium/ScottishPrem/UEL κλπ ΔΕΝ παιζονται):\n' + '\n'.join(bad)


def test_c_kickoff_in_future_not_inplay():
    """Ο scanner πεταει τα in-play (toa_live inplay=True) πριν τα picks. Το scanned_at γραφεται
    σε τοπικη ωρα της μηχανης που εσκαναρε (runner=UTC, laptop=Ελλαδα) → ανοχη 3h."""
    d, P = _picks()
    scanned = _dt(d.get('scanned_at'))
    assert scanned is not None, f'value_picks_latest.scanned_at={d.get("scanned_at")!r} δεν ειναι ημερομηνια'
    bad = []
    for p in P:
        if p.get('inplay'):
            bad.append(f'{_lab(p)} — inplay=True'); continue
        ko = _dt(p.get('when'))
        if ko is None:
            bad.append(f'{_lab(p)} — when={p.get("when")!r} μη εγκυρο'); continue
        if ko < scanned - datetime.timedelta(hours=3):
            bad.append(f'{_lab(p)} — σεντρα {p["when"]} ΠΡΙΝ το scan {d["scanned_at"]}')
    assert not bad, 'picks σε ματς που εχει ηδη αρχισει/τελειωσει:\n' + '\n'.join(bad)


def test_c_stakes_kelly_and_cap():
    d, P = _picks()
    assert _approx(d.get('cap'), STAKE_CAP), f'value_picks_latest.cap={d.get("cap")} (περιμενα 0.20)'
    bad = []
    for p in P:
        k = KELLY_FRAC * p['edge'] / (p['odds'] - 1)
        if p['stake'] > k + 1e-9:
            bad.append(f'{_lab(p)}: stake {p["stake"]:.5f} > 0.125·edge/(odds−1) = {k:.5f}')
        if not _approx(p['stake_final'], p['stake'] * d['scale'], 1e-9):
            bad.append(f'{_lab(p)}: stake_final {p["stake_final"]:.5f} ≠ stake·scale {p["stake"]*d["scale"]:.5f}')
    assert not bad, 'staking ΕΚΤΟΣ κανονα (1/8 Kelly):\n' + '\n'.join(bad)
    gross = sum(p['stake'] for p in P)
    assert _approx(gross, d['gross'], 1e-6), f'gross {d["gross"]} ≠ Σstake {gross}'
    exp_scale = STAKE_CAP / gross if gross > STAKE_CAP else 1.0
    assert _approx(d['scale'], exp_scale, 1e-9), f'scale={d["scale"]} — περιμενα min(1, 0.20/gross)={exp_scale}'
    tot = sum(p['stake_final'] for p in P)
    assert tot <= STAKE_CAP + 1e-9, f'Σstake_final = {tot:.4f} > cap 0.20 (η συνολικη εκθεση ξεπερασε το οριο)'


def test_c_edge_and_proj_odds_reproduce_from_pw_pp():
    """Ο τυπος pricing πανω στο ΠΡΑΓΜΑΤΙΚΟ αρχειο: edge = pw·(odds−1)·(1−MARGIN) − (1−pw−pp),
    fair = (1−pp)/pw. Αν αλλαξει ο τυπος (ή το MARGIN) στο live, σπαει εδω."""
    import picks
    _, P = _picks()
    bad = []
    for p in P:
        e = p['pw'] * (p['odds'] - 1) * (1 - picks.MARGIN) - (1 - p['pw'] - p['pp'])
        f = (1 - p['pp']) / p['pw'] if p['pw'] > 0 else float('inf')
        if not _approx(e, p['edge'], 1e-9):
            bad.append(f'{_lab(p)}: edge {p["edge"]:.6f} ≠ τυπος {e:.6f}')
        if not _approx(f, p['proj_odds'], 1e-9):
            bad.append(f'{_lab(p)}: proj_odds {p["proj_odds"]:.6f} ≠ (1−pp)/pw {f:.6f}')
        if not (0 < p['pw'] < 1 and 0 <= p['pp'] < 1 and p['pw'] + p['pp'] <= 1 + 1e-9):
            bad.append(f'{_lab(p)}: pw={p["pw"]}, pp={p["pp"]} εκτος [0,1]')
    assert not bad, 'pricing στο value_picks_latest.json ΔΕΝ αναπαραγεται απο τον τυπο:\n' + '\n'.join(bad)


# ================================================================ (d) GOLDEN PRICING
# Υπολογιστηκαν 18/9/2026 με picks.evaluate_bet (EDGE .10, ζωνη 1.70-2.10, MIN_LINE .5,
# DRAW_BOOST 1.13, MARGIN .03). (xg_h, xg_a, line[home persp.], oh, oa) -> picks.
GOLDEN = [
    # 1) Tottenham-Aston Villa 18/9 (πραγματικο pick): dog Villa +0.5
    ((1.246, 1.004, -0.5, 1.95, 1.89),
     [dict(side=-1, hcap=0.5, odds=1.89, pw=0.5970840973286032, pp=0.0,
           edge=0.11254679855238636, proj_odds=1.6748059519154357)]),
    # 2) Levante-Barcelona 13/9 (clv_bets): dog Levante +2.5, βαθια γραμμη
    ((1.058, 2.497, 2.5, 1.88, 2.04),
     [dict(side=1, hcap=2.5, odds=1.88, pw=0.7348024962836962, pp=0.0,
           edge=0.3620299071114592, proj_odds=1.3609099112449328)]),
    # 3) ακεραια γραμμη +1.0 με push (pp>0), odds στο ανω οριο 2.10
    ((1.8, 0.9, -1.0, 1.87, 2.1),
     [dict(side=-1, hcap=1.0, odds=2.1, pw=0.4308693255923392, pp=0.24208304355679694,
           edge=0.13268993955616215, proj_odds=1.7590413413655148)]),
    # 4) quarter γραμμη ±0.25 < MIN_LINE 0.5 -> ΚΑΝΕΝΑ pick
    ((1.3, 1.1, -0.25, 1.9, 2.0), []),
    # 5) οριακο edge 10.04% -> pick (αν το EDGE ανεβει/ο τυπος αλλαξει, χανεται)
    ((1.5, 1.2, -0.5, 1.9, 1.95),
     [dict(side=-1, hcap=0.5, odds=1.95, pw=0.5726899801575689, pp=0.0,
           edge=0.10042379687276859, proj_odds=1.746145444564722)]),
]


@pytest.mark.parametrize('args,expected', GOLDEN, ids=[f'golden{i+1}' for i in range(len(GOLDEN))])
def test_d_evaluate_bet_golden(args, expected):
    import picks
    out = picks.evaluate_bet(*args)
    assert len(out) == len(expected), (f'evaluate_bet{args}: {len(out)} picks αντι {len(expected)} — '
                                       f'το pricing/φιλτρα ΑΛΛΑΞΑΝ (βγηκε: {out})')
    for got, exp in zip(out, expected):
        for k, v in exp.items():
            assert _approx(got.get(k), v, 1e-9), (f'evaluate_bet{args}: {k}={got.get(k)!r} αντι golden {v!r} '
                                                  f'(διαφορα {abs(float(got.get(k)) - v):.2e}) — το pricing ΑΛΛΑΞΕ')


def test_d_gd_dist_is_probability():
    import picks
    dist = picks.gd_dist(1.4, 1.1)
    s = sum(dist.values())
    assert _approx(s, 1.0, 1e-6), f'gd_dist δεν αθροιζει στο 1 ({s})'
    assert dist[0] > 0.2, f'P(ισοπαλια)={dist[0]:.3f} — υποπτα χαμηλο (DRAW_BOOST 1.13 χαθηκε;)'


# ================================================================ (e) ΕΥΡΩΠΑΪΚΑ
def _euro():
    if not os.path.exists(_p('euro_value_latest.json')):
        pytest.skip('euro_value_latest.json δεν υπαρχει')
    d = _json('euro_value_latest.json')
    return d, d.get('picks', [])


def _elab(p):
    return f'[{p.get("comp")}] {p.get("home")}-{p.get("away")} {p.get("team")} {p.get("line")} @{p.get("odds")} ({p.get("role")}, edge {float(p.get("edge", 0))*100:.1f}%)'


def test_e_rules_block_matches_live():
    d, _ = _euro()
    r = d.get('rules', {})
    exp = dict(edge_dog=0.10, edge_fav=0.04, edge_fav_ucl=0.10, edge_dog_ucl=0.04)
    bad = [f'{k}={r.get(k)!r} (περιμενα {v})' for k, v in exp.items() if not _approx(r.get(k), v)]
    z = r.get('zone')
    if not (isinstance(z, list) and len(z) == 2 and _approx(z[0], 1.70) and _approx(z[1], 2.10)):
        bad.append(f'zone={z!r} (περιμενα [1.70, 2.10])')
    assert not bad, 'euro_value_latest.rules ≠ live κανονες (UCL favs @10, UCL dogs @4, dogs @10, favs @4): ' + ', '.join(bad)


def test_e_uel_only_as_shadow():
    """UEL: επιτρεπεται ΜΟΝΟ με no_play=True (σκια — δειχνεται, δεν παιζεται, 18/9). Αλλες λιγκες:
    ποτε no_play, ποτε εκτος UCL/UEL/UECL."""
    d, P = _euro()
    bad = []
    for p in P:
        c = p.get('comp')
        if c in EURO_SHADOW:
            if p.get('no_play') is not True:
                bad.append(f'{_elab(p)}: UEL pick ΧΩΡΙΣ no_play=True (UEL κλειστο 11/9, μονο σκια)')
        elif c in EURO_ALLOWED:
            if p.get('no_play'):
                bad.append(f'{_elab(p)}: no_play σε {c} (μονο το UEL ειναι σκια)')
        else:
            bad.append(f'{_elab(p)}: αγνωστη διοργανωση {c!r}')
    assert not bad, 'UEL σκια / διοργανωσεις:' + chr(10) + chr(10).join(bad)
    assert 'EuropaLeague' in (d.get('rules', {}).get('no_play_comps') or []), (
        'euro_value_latest.rules.no_play_comps δεν περιεχει EuropaLeague (τρεξε euro_shadow_scan.py)')


def test_e_zone_role_and_thresholds():
    _, P = _euro()
    bad = []
    for p in P:
        o, ln, role, e, comp = float(p['odds']), float(p['line']), p.get('role'), float(p['edge']), p.get('comp')
        if not (1.70 - EPS <= o <= 2.10 + EPS):
            bad.append(f'{_elab(p)}: odds εκτος [1.70, 2.10]')
        ucl = comp == 'ChampionsLeague'
        if role == 'fav':
            if ln > -0.5 + EPS:
                bad.append(f'{_elab(p)}: φαβορι με line {ln} (περιμενα <= −0.5)')
            thr = 0.10 if ucl else 0.04
            if e < thr - EPS:
                bad.append(f'{_elab(p)}: φαβορι edge {e*100:.1f}% < κατωφλι {thr*100:.0f}%')
        elif role == 'dog':
            if ln < 0.5 - EPS:
                bad.append(f'{_elab(p)}: dog με line {ln} (περιμενα >= +0.5)')
            thr = 0.04 if ucl else 0.10
            if e < thr - EPS:
                bad.append(f'{_elab(p)}: dog edge {e*100:.1f}% < κατωφλι {thr*100:.0f}%')
            if ucl and e < 0.10 and p.get('band') != '4-10':
                bad.append(f'{_elab(p)}: UCL dog στη ζωνη 4-10% χωρις band="4-10"')
        elif role == 'over':
            if e < 0.04 - EPS:
                bad.append(f'{_elab(p)}: over edge {e*100:.1f}% < 4%')
        else:
            bad.append(f'{_elab(p)}: αγνωστος ρολος {role!r}')
    assert not bad, 'ευρωπαικα picks εκτος κανονων:\n' + '\n'.join(bad)


def test_e_ucl_kappa_applied():
    """Το κ (UCL_FAV_SCALE=1.16) εφαρμοζεται στα projections· ο euro scanner τιμολογει απο εκει.
    Ελεγχος: header του euro_projections.json + τα xG του pick ταυτιζονται με το projection."""
    _, P = _euro()
    if not os.path.exists(_p('euro_projections.json')):
        pytest.skip('euro_projections.json δεν υπαρχει')
    proj = _json('euro_projections.json')
    assert _approx(proj.get('ucl_fav_scale'), 1.16), \
        f'euro_projections.ucl_fav_scale={proj.get("ucl_fav_scale")!r} — το κ=1.16 ΔΕΝ εφαρμοστηκε στα projections'
    by_mid = {str(m.get('mid')): m for m in proj.get('matches', [])}
    bad = []
    for p in P:
        m = by_mid.get(str(p.get('mid')))
        if m is None:
            bad.append(f'{_elab(p)}: mid {p.get("mid")} δεν υπαρχει στο euro_projections.json'); continue
        if p.get('role') in ('fav', 'dog'):
            if not (_approx(p.get('xgh'), m.get('xgh'), 1e-6) and _approx(p.get('xga'), m.get('xga'), 1e-6)):
                bad.append(f'{_elab(p)}: xG pick {p.get("xgh")}/{p.get("xga")} ≠ projection {m.get("xgh")}/{m.get("xga")} (μπαγιατικο pricing)')
        if p.get('comp') == 'ChampionsLeague' and m.get('covered'):
            # με κ=1.16 η πλευρα του φαβορι πρεπει να ειναι > ουδετερη·HFA (xgh0·hfa ή xga0/hfa)
            hfa = float(proj.get('hfa', 1.0))
            base_h, base_a = m['xgh0'] * hfa, m['xga0'] / hfa
            fav_ratio = (m['xgh'] / base_h) if m['xgh'] >= m['xga'] else (m['xga'] / base_a)
            if fav_ratio < 1.0:
                bad.append(f'{_elab(p)}: UCL φαβορι xG/βαση = {fav_ratio:.3f} < 1 — το κ δεν φαινεται εφαρμοσμενο')
    assert not bad, 'κ UCL / συνεπεια projections:\n' + '\n'.join(bad)


# ---------------------------------------------------------------- F. ΕΘΝΙΚΕΣ: κλειδι ασφαλειας κατα των διπλων ματς (25/9/2026)
def test_f_intl_dedupe_logic():
    """intl_dedupe πιανει: ιδιο ζευγος με ids κειμενο/αριθμο, ανεστραμμενο γηπ/φιλοξ, ±1 μερα· κραταει FotMob· αφηνει ρεβανς μετα απο μερες."""
    import pandas as pd
    import intl_dedupe
    M = pd.DataFrame([
        dict(mid='1', src='fotmob', date='2026-06-04 19:10', hid=6723, aid=6709, hs=1, **{'as': 2}),
        dict(mid='ng1', src='nowgoal_friendly', date='2026-06-04 19:10', hid='6723', aid='6709', hs=1, **{'as': 2}),   # ids κειμενο
        dict(mid='ng2', src='nowgoal_friendly', date='2026-06-04 21:00', hid=6709, aid=6723, hs=2, **{'as': 1}),       # ανεστραμμενο
        dict(mid='ng3', src='nowgoal_friendly', date='2026-06-05 18:00', hid=6723, aid=6709, hs=1, **{'as': 2}),       # +1 μερα
        dict(mid='2', src='fotmob', date='2026-06-09 19:10', hid=6723, aid=6709, hs=0, **{'as': 0}),                   # αλλο ματς (5 μερες μετα)
    ])
    C = intl_dedupe.dedupe(M, verbose=False)
    assert sorted(C.mid) == ['1', '2'], f'κρατηθηκαν {sorted(C.mid)} — περιμενα μονο τα FotMob 1 και 2'
    intl_dedupe.assert_clean(C)
    with pytest.raises(AssertionError):
        intl_dedupe.assert_clean(M)


def test_f_intl_matches_has_no_duplicates():
    """Ο πινακας ματς εθνικων (οπου υπαρχει — τοπικα, οχι στο repo) ΔΕΝ εχει διπλα."""
    import pandas as pd
    import intl_dedupe
    p = os.path.join(ROOT, 'intl_matches.csv')
    if not os.path.exists(p):
        pytest.skip('intl_matches.csv δεν υπαρχει εδω (χτιζεται τοπικα)')
    intl_dedupe.assert_clean(pd.read_csv(p, dtype={'mid': str}), where='intl_matches.csv')


def test_f_intl_build_uses_guard():
    """Το intl_build.py περναει απο τον κοινο ελεγχο διπλων και κανει τα ids ακεραιους (αιτια του bug 25/9)."""
    p = os.path.join(ROOT, 'intl_build.py')
    if not os.path.exists(p):
        pytest.skip('intl_build.py ζει μονο τοπικα')
    src = open(p, encoding='utf-8').read()
    assert 'intl_dedupe.assert_clean' in src, 'intl_build.py χωρις intl_dedupe.assert_clean'
    assert 'int(NAMES[' in src, 'intl_build.py: τα ids των φιλικων Nowgoal πρεπει να γινονται int'


def test_f_intl_venue_flags_one_row_per_match():
    """intl_venue_flags.csv (οπου υπαρχει — τοπικα) εχει μια γραμμη ανα ματς· αλλιως το join πολλαπλασιαζει ματς στο Elo (bug 25/9: 286 φιλικα ×4)."""
    import pandas as pd
    import intl_dedupe
    p = os.path.join(ROOT, 'intl_venue_flags.csv')
    if not os.path.exists(p):
        pytest.skip('intl_venue_flags.csv δεν υπαρχει εδω (τοπικο)')
    intl_dedupe.assert_unique_mid(pd.read_csv(p, dtype={'mid': str}), where='intl_venue_flags.csv')


def test_f_intl_elo_walk_starts_after_seed():
    """Ο υπολογισμος Elo εθνικων ξεκινα ΑΚΡΙΒΩΣ μετα την αφετηρια eloratings (τελος 2019 → 1/1/2020)· οχι επικαλυψη (bug 25/9: απο 1/7/2019)."""
    for f, needle in (('intl_rating.py', "WALK_START = f'{int(SEED_YEAR) + 1}-01-01'"),
                      ('intl_rating2_hist.py', "CUTOFF = pd.Timestamp('2020-01-01')")):
        p = os.path.join(ROOT, f)
        if not os.path.exists(p):
            pytest.skip(f'{f} ζει μονο τοπικα')
        src = open(p, encoding='utf-8').read()
        assert needle in src, f'{f}: η εναρξη του υπολογισμου δεν ειναι η επομενη μερα της αφετηριας eloratings'
        assert "'2019-07-01'" not in src.replace("ηταν '2019-07-01'", ''), f'{f}: εμεινε εναρξη 1/7/2019 (επικαλυψη με την αφετηρια)'


def test_f_intl_over_pricing_push_aware():
    """Over εθνικων (25/9, αποφαση Στελιου): σωστο edge με push/μισα — x.25/x.75 ΔΕΝ ειναι x.5, οι ακεραιες επιστρεφουν στο push."""
    import intl_pricing as ip
    for line, exp in ((2.25, 0.154), (2.5, 0.035), (2.75, -0.071), (3.0, -0.177)):
        got = ip.over_ev(2.8, line, 1.95)
        assert abs(got - exp) < 0.002, f'over {line} @1.95, T 2.8: edge {got:+.3f}, αναμενομενο {exp:+.3f}'
    assert abs(ip.over_ev(2.8, 2.5, ip.over_fair(2.8, 2.5))) < 1e-6, 'fair τιμη δεν δινει edge 0'
    src = open(os.path.join(ROOT, 'intl_dashboard_build.py'), encoding='utf-8').read()
    assert 'intl_pricing.over_ev' in src and "po, _ = p_over(T, b['ou_line']); e = po" not in src, 'το dashboard build δεν χρησιμοποιει τον σωστο τυπο over'


def test_f_intl_ah_quarters_split():
    """AH εθνικων (25/9, αποφαση Στελιου): τεταρτο = μισο/μισο στις διπλανες γραμμες· μισες/ακεραιες ιδιες με το picks.p_cover."""
    import picks, intl_pricing as ip
    dist = picks.gd_dist(1.6, 1.0)
    for side, ud, o in ((1, -0.75, 1.95), (1, -1.25, 2.05), (-1, 0.75, 1.85), (1, -2.25, 2.0)):
        avg = (ip.ah_ev(dist, side, ud - .25, o, picks.MARGIN) + ip.ah_ev(dist, side, ud + .25, o, picks.MARGIN)) / 2
        assert abs(ip.ah_ev(dist, side, ud, o, picks.MARGIN) - avg) < 1e-12, f'τεταρτο {ud}: δεν ειναι μισο/μισο'
    pw, pp = picks.p_cover(dist, 1, -0.5); old = pw * (1.95 - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
    assert abs(ip.ah_ev(dist, 1, -0.5, 1.95, picks.MARGIN) - old) < 1e-12, 'μιση γραμμη: διαφορα απο p_cover'
    assert abs(ip.ah_ev(dist, 1, -0.75, ip.ah_fair(dist, 1, -0.75), 0.0)) < 0.01, 'fair τιμη τεταρτου δεν δινει ~0'
    # 25/9 (β) Σχεδιο Β: dog +x.25 με τον ΠΑΛΙΟ τροπο (p_cover στη γραμμη), τα αλλα τεταρτα σωστα
    for ud in (0.25, 1.25, 2.25):
        pw, pp = picks.p_cover(dist, -1, ud); old = pw * (1.9 - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
        assert abs(ip.ah_ev(dist, -1, ud, 1.9, picks.MARGIN) - old) < 1e-12, f'Σχεδιο Β: dog +{ud} δεν τιμολογειται με τον παλιο τροπο'
    # 25/9 (γ) βαθια φαβορι: dist_for διαλεγει τη «βαθια» κατανομη ΜΟΝΟ για ≤ −2
    dd = picks.gd_dist(1.4, 1.0)
    assert ip.dist_for(dist, dd, -2.0) is dd and ip.dist_for(dist, dd, -2.5) is dd and ip.dist_for(dist, dd, -1.75) is dist and ip.dist_for(dist, dd, 1.25) is dist
    assert ip.dist_for(dist, None, -3.0) is dist
    cfg = json.load(open(os.path.join(ROOT, 'intl_deepfav_config.json'), encoding='utf-8'))['a_deep']
    assert 0.0038 < cfg['H'] < 0.0048 and 0.0045 < cfg['A'] < 0.0055 and 0.0038 < cfg['AV'] < 0.0048, cfg
    import intl_picks_ledger as L
    assert L.variant_of(dict(mkt='AH', line=1.25)).startswith('Σχ.Β') and L.variant_of(dict(mkt='AH', line=-2.5)).startswith('βαθυ') and L.variant_of(dict(mkt='AH', line=-1.5)) == ''
    src = open(os.path.join(ROOT, 'intl_dashboard_build.py'), encoding='utf-8').read()
    assert 'intl_pricing.ah_ev' in src and 'picks.p_cover(dist, side, ud); e = pw' not in src, 'το dashboard build δεν χρησιμοποιει σωστα τεταρτα AH'


def test_f_intl_consensus_and_ledger():
    """Κανονικα picks εθνικων (25/9): συναινεση ≥2/3 (handicap + over, οχι 1Χ2/εκτος κανονα), πρωτη εμφανιση ≤72ω, σημειωση <2ω."""
    import datetime as dt
    import intl_consensus as ic, intl_picks_ledger as L
    pk = {'H': 'DOG 2 +1.25 @1.90 (Bovada, +14%) · 1Χ2 φαβ γηπ ≥75% @1.20', 'A': 'DOG 2 +1.25 @1.90 (Bovada, +11%)', 'AV': 'FAV 1 -1.25 @1.95 (Bovada, +12%)',
          'over': 'OVER 2.25 @2.00 (Bovada, +20%)', 'over_A': '(εκτος κανονα: αναντιστοιχια, edge +9% Bovada)', 'over_AV': 'OVER 2.25 @2.00 (Bovada, +15%)'}
    cs = ic.consensus(pk)
    assert [(c['mkt'], c['side'], c['models']) for c in cs] == [('AH', 2, 'Μ1+Μ2'), ('OVER', 0, 'Μ1+Μ3')], cs
    assert abs(cs[0]['edge'] - 0.11) < 1e-9, 'edge συναινεσης = το μικροτερο'
    assert ic.late_note(1.5) and ic.late_note(0.4) and not ic.late_note(5)
    now = dt.datetime(2026, 9, 25, 17, 0, tzinfo=dt.timezone.utc)
    dash = {'comps': [{'comp': 'NL B', 'matches': [dict(home='X', away='Y', utc='2026-09-25 18:45', picks=pk),
                                                   dict(home='Z', away='W', utc='2026-09-29 18:45', picks=pk)]}]}
    known = set(); rows = L.new_entries(dash, known, now)
    cons = [r for r in rows if r['stream'] == 'ΣΥΝΑΙΝΕΣΗ']
    assert len(cons) == 2 and all(r['home'] == 'X' for r in rows), 'μονο ματς ≤72ω'
    assert all(r['late'] for r in cons), 'pick 1.75ω πριν πρεπει να εχει σημειωση'
    assert L.new_entries(dash, known, now) == [], 'δευτερη φορα: καμια νεα εγγραφη (πρωτη εμφανιση μονο)'
    # Telegram (25/9): μηνυμα νεου pick + εκκαθαρισης χτιζεται· χωρις TELEGRAM_TOKEN δεν στελνει ουτε βαζει σημαια
    msg = L.tg_new_msg(cons)
    assert 'ΕΘΝΙΚΕΣ' in msg and 'Y +1.25 @1.90' in msg and 'Over 2.25' in msg and '21:45' in msg, msg
    assert 'Μ1+Μ2' in msg and cons[0]['late'] in msg
    done = [dict(cons[0], result='0-1', pnl=0.9), dict(cons[1], result='0-1', pnl=-1.0)]
    sm = L.tg_settle_msg(done, done)
    assert '✅' in sm and '❌' in sm and 'ROI -5.0%' in sm, sm
    old = {k: os.environ.pop(k, None) for k in ('TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')}
    try:
        assert L.telegram(rows, now) is False and not any(r.get('tg') for r in rows), 'χωρις token δεν πρεπει να σημαδευει'
    finally:
        for k, v in old.items():
            if v is not None:
                os.environ[k] = v


def test_g_intl_refresh_guards():
    """Αυτοματο refresh εθνικων (25/9): βαση χωρις διπλα, Μ1 κλειδωμενο στο H3, λ αγκυρας 0.3, closing Odds API για τα νεα ματς."""
    import pandas as pd, intl_dedupe
    f = os.path.join(ROOT, 'intl_matches.csv')
    if os.path.exists(f):
        M = pd.read_csv(f, dtype={'mid': str, 'season': str})
        intl_dedupe.assert_clean(M, where='test')
        assert M.mid.is_unique, 'διπλα mid στο intl_matches.csv'
    src = open(os.path.join(ROOT, 'intl_refresh.py'), encoding='utf-8').read()
    assert "INTL_PIN_VARIANT='H3'" in src, 'το refresh πρεπει να κλειδωνει το Μ1 στο H3'
    anc = open(os.path.join(ROOT, 'intl_mkt_anchor.py'), encoding='utf-8').read()
    assert 'run(0.3, keep=True)' in anc and 'intl_closing.jsonl' in anc and 'intl_close_hist.json' in anc
    if os.path.exists(os.path.join(ROOT, 'intl_hfa_config.json')):
        assert json.load(open(os.path.join(ROOT, 'intl_hfa_config.json'), encoding='utf-8'))['variant'] == 'H3'
    # 25/9: Nowgoal ταιριαζει ΜΟΝΟ με ιδια ημερομηνια (ωρα Πεκινου) — ο ρεβανς του ιδιου ζευγους δεν παιρνει τις γραμμες του αλλου ματς
    assert intl_dedupe.ng_same_fixture('2026-09-25 02:45', '2026-09-24T18:45')
    assert not intl_dedupe.ng_same_fixture('2026-09-28 00:00', '2026-10-04T18:45')
    rec = [{'dt': '2026-09-28 00:00', 'x': 1}]
    assert intl_dedupe.ng_pick(rec, '2026-09-27 16:00') and intl_dedupe.ng_pick(rec, '2026-10-04 18:45') is None
    # 25/9 (αποφαση Στελιου): στρωμα αξιας = ΚΛΗΣΗ (TM) — συντελεστης απο το τεστ, fallback V_full στην ιδια κλιμακα, προστασια απο μπλοκαρισμα TM
    cfg = json.load(open(os.path.join(ROOT, 'intl_vcall_config.json'), encoding='utf-8'))
    assert 30 < cfg['elo_per_doubling'] < 50 and 0.8 < cfg['r_scale'] < 1.5, cfg
    pj = open(os.path.join(ROOT, 'intl_project.py'), encoding='utf-8').read()
    assert 'ELO_LN_CALL * math.log(vh / va)' in pj and 'def v_call_of' in pj, 'το Μ1 πρεπει να χρησιμοποιει την αξια κλησης'
    ct = open(os.path.join(ROOT, 'intl_callups_tm.py'), encoding='utf-8').read()
    assert 'len(OUT) < 0.8 * len(TIDS)' in ct, 'χωρις προστασια: μπλοκαρισμα TM θα εσβηνε την κληση'
    pr = os.path.join(ROOT, 'intl_projections.csv')
    if os.path.exists(pr):
        import pandas as pd
        P = pd.read_csv(pr)
        if 'val_src' in P:
            assert (P.val_src.astype(str).str.count('κληση') >= 1).mean() > 0.5, 'λιγοτερα απο τα μισα ματς με αξια κλησης'


def test_h_intl_new_T_over():
    """26/9 (αποφαση Στελιου): νεο T για τα over = T + xG επιθεσης/αμυνας ομαδων· χωρις xG → T σημερα· μονο over (handicap απο intl_project)."""
    import intl_pricing as ip
    cfg = json.load(open(os.path.join(ROOT, 'intl_tmix_config.json'), encoding='utf-8'))
    for v in ('H', 'A', 'AV'):
        b0, b1, b2 = cfg[v]; assert 0.6 < b1 < 0.95 and 0.35 < b2 < 0.75 and -1.2 < b0 < -0.4, (v, cfg[v])
    AD = {'_meta': {'mu': 1.23, 'hf': 1.15}, '1': {'att': 0.6, 'dfn': 0.9, 'n': 12}, '2': {'att': 0.7, 'dfn': 1.0, 'n': 12}, '3': {'att': 1.5, 'dfn': 1.4, 'n': 2}}
    xs = ip.team_xg_sum(AD, 1, 2); assert xs is not None and xs < 1.4, xs
    assert ip.team_xg_sum(AD, 1, 3) is None, 'λιγοτερα απο 3 ματς με xG → χωρις νεο T'
    assert ip.t_over(2.5, 'H', None, cfg) == 2.5 and ip.t_over(2.5, 'H', xs, cfg) < 2.5, 'ομαδες με λιγα xG πρεπει να κατεβαζουν το T'
    src = open(os.path.join(ROOT, 'intl_dashboard_build.py'), encoding='utf-8').read()
    assert 'intl_pricing.t_over(T_H' in src and 'team_xg_sum(AD_XG' in src, 'το dashboard δεν χρησιμοποιει το νεο T στα over'
    ad = json.load(open(os.path.join(ROOT, 'intl_xg_attdef.json'), encoding='utf-8'))
    assert '_meta' in ad and len(ad) > 80, 'intl_xg_attdef.json χωρις meta/ομαδες'
