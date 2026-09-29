"""proj_archive.py — ΑΡΧΕΙΟ ΠΡΟΒΛΕΨΕΩΝ Match Projections (29/9/2026, Στελιος: «γιατι δεν κρατιουνται οι προηγουμενες
αγωνιστικες; να μενουν σταθερες με οσα γνωριζαν ΠΡΙΝ το ματς»).

match_projections_archive.json = {fid (FotMob match id): καρτα-ματς οπως την εβγαζε το build_matches}
  • snapshot()  — καθημερινα στο data-refresh: για καθε ματς που ΔΕΝ εχει αρχισει ξαναγραφει την καρτα (τρεχουσα προβλεψη +
                  γραμμες αγορας + ζευγος γκολ)· μολις αρχισει, η τελευταια εγγραφη ΠΑΓΩΝΕΙ (δεν ξαναγγιζεται). Γραφει και το σκορ.
  • backfill()  — μια φορα: ανακατασκευη των ματς που παιχτηκαν πριν υπαρξει το αρχειο, με τη live μηχανη και ΜΟΝΟ τα ματς
                  πριν τη μερα του καθε αγωνα (ιδιο με core7_anchor.replay_preds)· αγορα = κλεισιμο απο odds_history.jsonl. src='recon'.
Πεδια πλεον της καρτας: _mk (γραμμες αγορας AH/OU), _ou (ζευγος γκολ αποσυμπιεσης), score, src ('live'|'recon'), frozen_at.
"""
import os, sys, json, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ARCH_F = os.path.join(ROOT, 'match_projections_archive.json')
HORIZON_DAYS = 21          # καταγραφη επερχομενων μεχρι 21 μερες πριν (οχι ολη τη σεζον — μεγεθος αρχειου)
VOLATILE = ('frozen_at', 'score')


def load():
    try:
        with open(ARCH_F, encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return {}


def save(A):
    # μια εγγραφη ανα γραμμη → μικρα git diffs (το αρχειο ξαναγραφεται καθε μερα)
    with open(ARCH_F, 'w', encoding='utf-8') as fh:
        rows = [json.dumps(k) + ':' + json.dumps(A[k], ensure_ascii=False, separators=(',', ':'), sort_keys=True) for k in sorted(A)]
        fh.write('{\n' + ',\n'.join(rows) + '\n}\n')


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _utc(s):
    try:
        return datetime.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    except Exception:
        return None


def _ckey(m):
    return f"{m.get('home_id') or ''}_{m.get('away_id') or ''}"


def _same(a, b):
    return {k: v for k, v in a.items() if k not in VOLATILE} == {k: v for k, v in b.items() if k not in VOLATILE}


def _finished(lg):
    import build_data
    d = build_data._fotmob(f'https://www.fotmob.com/api/data/leagues?id={build_data.LEAGUE_FOTMOB[lg]}'
                           f'&season={build_data.CURRENT_FOTMOB_SEASON}')
    out = []
    for m in d.get('fixtures', {}).get('allMatches', []):
        st = m.get('status', {})
        if st.get('finished') and not st.get('cancelled'):
            h, a = m.get('home', {}), m.get('away', {})
            out.append(dict(gw=int(m.get('round') or 0), utc=st.get('utcTime', ''), fid=m.get('id'),
                            home_name=h.get('name'), home_id=h.get('id'), away_name=a.get('name'), away_id=a.get('id'),
                            score=(st.get('scoreStr') or '').replace(' ', '')))
    return out


def snapshot():
    """Καθημερινα: ενημερωνει ΜΟΝΟ ματς που δεν εχουν αρχισει· γραφει σκορ στα τελειωμενα. → (νεα/αλλαγμενα, σκορ)"""
    import build_data, cards
    A = load(); now = _now()
    matches, _ = build_data.build_matches()
    try:
        dom = json.load(open(os.path.join(ROOT, 'dom_odds_latest.json'), encoding='utf-8')).get('odds', {})
    except Exception:
        dom = {}
    up = cards._uncomp_pairs()
    n_up = 0
    for m in matches:
        if not m.get('projectable') or not m.get('fid'):
            continue
        ko = _utc(m.get('utc'))
        if ko is None or ko <= now or ko > now + datetime.timedelta(days=HORIZON_DAYS):
            continue                                   # αρχισε → παγωμενο, δεν αγγιζεται · πολυ μακρια → αργοτερα
        k = str(m['fid']); old = A.get(k) or {}
        rec = dict(m)
        rec['_mk'] = dom.get(_ckey(m)) or old.get('_mk')          # κρατα την τελευταια γνωστη αγορα οταν ο scanner ειναι σε παυση
        p = up.get(_ckey(m)); rec['_ou'] = [p['xh'], p['xa']] if p else old.get('_ou')
        for f in ('mkt_hw_odds', 'mkt_d_odds', 'mkt_aw_odds'):
            if rec.get(f) is None and old.get(f) is not None:
                rec[f] = old[f]
        rec['src'] = 'live'
        if not old or not _same(old, rec):
            rec['frozen_at'] = now.strftime('%Y-%m-%dT%H:%MZ'); A[k] = rec; n_up += 1
    n_sc = 0
    for lg in build_data.LEAGUE_FOTMOB:
        try:
            for f in _finished(lg):
                r = A.get(str(f['fid']))
                if r is not None and f['score'] and r.get('score') != f['score']:
                    r['score'] = f['score']; n_sc += 1
        except Exception as e:
            print(f'σκορ {lg}: {type(e).__name__}: {e}')
    save(A)
    print(f'proj_archive: {n_up} νεες/αλλαγμενες προβλεψεις (μη αρχισμενα) · {n_sc} σκορ · συνολο {len(A)}')
    return n_up, n_sc


def _hist_closing():
    """{(hid, aid): τελευταια εγγραφη odds_history πριν τη σεντρα}"""
    idx = {}
    p = os.path.join(ROOT, 'odds_history.jsonl')
    if not os.path.exists(p):
        return idx
    for ln in open(p, encoding='utf-8'):
        try:
            r = json.loads(ln)
            t = datetime.datetime.fromisoformat(str(r['t'])[:16]); ko = datetime.datetime.fromisoformat(str(r['ko'])[:16])
        except Exception:
            continue
        if r.get('inplay') or t > ko + datetime.timedelta(minutes=10):
            continue
        k = (str(r.get('hid')), str(r.get('aid')))
        if k not in idx or t >= idx[k][0]:
            idx[k] = (t, r)
    return {k: v[1] for k, v in idx.items()}


def backfill(leagues=None, overwrite=False):
    """Ανακατασκευη ΠΑΙΓΜΕΝΩΝ ματς (οσα λειπουν απο το αρχειο): ratings απο τα ματς ΠΡΙΝ τη μερα του αγωνα."""
    import picks, build_data
    picks.MIN_PRIOR = 6
    A = load(); H = _hist_closing()
    lgs = leagues or list(build_data.LEAGUE_FOTMOB)
    Mp, id2name = picks.load_matches(list(build_data.LEAGUE_FOTMOB), [build_data.RATINGS_SEASON_DEFAULT])
    Mc, id2c = picks.load_matches(list(build_data.LEAGUE_FOTMOB), [build_data.CURRENT_SEASON]); id2name.update(id2c)
    name2id = {v: k for k, v in id2name.items()}
    n = 0
    for lg in lgs:
        fin = [f for f in _finished(lg) if overwrite or str(f['fid']) not in A]
        if not fin:
            continue
        G = Mc[(Mc.league == lg) & (Mc.season == build_data.CURRENT_SEASON)]
        teams = sorted(set(G.home) | set(G.away))
        fx = [dict(home_id=int(t), away_id=None, home_name=id2name.get(t)) for t in teams]
        by_day = {}
        for f in fin:
            by_day.setdefault(f['utc'][:10], []).append(f)
        for day in sorted(by_day):
            Mt = G[G.date < day]
            LR = build_data.league_ratings(lg, Mp, Mt, build_data.RATINGS_SEASON_DEFAULT, build_data.CURRENT_SEASON,
                                           dict(id2name), dict(name2id), fixtures=fx)
            bl, ns = LR['blended'], LR['ns']
            for f in by_day[day]:
                Hh, Aa = int(f['home_id']), int(f['away_id'])
                rh, ra = bl.get(Hh), bl.get(Aa)
                rec = dict(league=lg, gw=f['gw'], utc=f['utc'], fid=f['fid'], home=f['home_name'], away=f['away_name'],
                           home_id=f['home_id'], away_id=f['away_id'], projectable=False, promoted=(Hh in LR['promoted'] or Aa in LR['promoted']),
                           score=f['score'], src='recon', frozen_at=_now().strftime('%Y-%m-%dT%H:%MZ'))
                if rh and ra:
                    pf = build_data._predict_ratings(rh, ra, LR['lg_shots'], LR['lg_xgps'], LR['hf'])
                    pf.update(build_data.one_x_two(pf['home_adj_xg'], pf['away_adj_xg']))
                    nh, na = ns.get(Hh, 0), ns.get(Aa, 0)
                    pf['warm_cur'] = round((nh / (nh + build_data.K_WARM) + na / (na + build_data.K_WARM)) / 2, 3)
                    rec.update(pf); rec['projectable'] = True
                    c = H.get((str(f['home_id']), str(f['away_id'])))
                    if c:
                        h2h = c.get('h2h') or []
                        if len(h2h) == 3 and all(h2h):
                            rec['mkt_hw_odds'], rec['mkt_d_odds'], rec['mkt_aw_odds'] = h2h
                        pin = c.get('pin') if c.get('pin') and all(x is not None for x in c['pin']) else None
                        line, oh, oa = pin if pin else (c.get('line'), c.get('oh'), c.get('oa'))
                        mk = {}
                        if line is not None and oh and oa:
                            mk.update(line=line, oh=oh, oa=oa)
                        ou = c.get('ou')
                        if ou and len(ou) == 3 and all(x is not None for x in ou):
                            mk.update(tl=ou[0], to=ou[1], tu=ou[2])
                        rec['_mk'] = mk or None
                A[str(f['fid'])] = rec; n += 1
        print(f'{lg:13s} ανακατασκευη {sum(len(v) for v in by_day.values())} ματς', flush=True)
    save(A)
    print(f'backfill: {n} ματς · αρχειο {len(A)}')
    return n


def default_gw(upcoming, all_gws):
    """Η αγωνιστικη του «τρεχοντος» σαββατοκυριακου: το πρωτο επερχομενο ματς (κατα ωρα) του οποιου η αγωνιστικη
    εχει ≥3 επερχομενα ματς (να μην πεφτουμε σε αναβληθεν ματς παλιας αγωνιστικης)."""
    if not upcoming:
        return all_gws[-1] if all_gws else None
    cnt = {}
    for m in upcoming:
        cnt[m['gw']] = cnt.get(m['gw'], 0) + 1
    for m in sorted(upcoming, key=lambda x: str(x.get('utc'))):
        if cnt.get(m['gw'], 0) >= 3:
            return m['gw']
    return min(cnt)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    if len(sys.argv) > 1 and sys.argv[1] == 'backfill':
        backfill()
    else:
        snapshot()
