# -*- coding: utf-8 -*-
"""lineup_window.py — 21/10/2026 (Στελιος: «ξεκινα με το 1-2»). ΜΟΝΟ ΚΑΤΑΓΡΑΦΗ / ΣΚΙΑ — κανενα pick, κανενα Telegram.
(1) ΠΑΡΑΘΥΡΟ ΣΕΝΤΡΑΣ: για καθε ματς CORE7 + Champions/Europa/Conference με σεντρα απο −80′ εως +5′, σε ΚΑΘΕ περασμα του scanner (~5′)
    ΚΑΙ ΚΑΘΕ 1′ αναμεσα στα περασματα (--watch, απο 21/10 βραδυ):
    ειδος ενδεκαδας FotMob (προσωρινη / προβλεπομενη / ΕΠΙΣΗΜΗ + βασικοι) και τιμες Pinnacle (κυριο χαντικαπ, κυριο συνολο).
    Γραφει στο lineup_window.jsonl μονο οταν κατι αλλαξε (με χρονοσφραγιδα) → ποτε βγηκε η ενδεκαδα, ποσο/ποτε κουνηθηκε η τιμη.
(2) ΣΚΙΑ «ΕΝΔΕΚΑΔΑ ΠΑΝΩ ΣΤΟ ΜΟΝΤΕΛΟ»: τη ΣΤΙΓΜΗ που εμφανιζεται η επισημη ενδεκαδα → διορθωση (xi_formula: αξια + εμπιστοσυνη, xGI για συνολα)
    πανω στην προβλεψη του live μοντελου (εγχωρια: match_projections_archive · Ευρωπη: euro_projections) → edge ΧΩΡΙΣ και ΜΕ διορθωση
    στην τιμη Pinnacle εκεινης της στιγμης, για καθε πλευρα χαντικαπ και over/under → lineup_shadow.jsonl (για CLV/αποτελεσμα αργοτερα).
    Σημαια 'pick' (μονο για αναλυση): αουτσαιντερ ≥6% · φαβορι ≥10% · συνολα ≥10% στο ΜΕ διορθωση."""
import os, sys, json, time, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'lineup_window.jsonl'); SHADOW = os.path.join(ROOT, 'lineup_shadow.jsonl'); ST = os.path.join(ROOT, 'lineup_window_state.json')
UTC = dt.timezone.utc
PRE_MIN, POST_MIN = 80, 5
PIN_DOM = {'EPL': 'epl', 'LaLiga': 'laliga', 'SerieA': 'seriea', 'Bundesliga': 'bundesliga', 'Ligue1': 'ligue1', 'Eredivisie': 'eredivisie', 'PrimeiraLiga': 'primeira'}
PIN_EU = {'ChampionsLeague': 'ucl', 'EuropaLeague': 'uel', 'ConferenceLeague': 'uecl'}
TH = dict(dog=0.06, fav=0.10, over=0.10, under=0.10)


def _t(s):
    d = dt.datetime.fromisoformat(str(s).replace('Z', '+00:00')); return d if d.tzinfo else d.replace(tzinfo=UTC)


def window_matches(now):
    out = []
    try:
        for fid, m in json.load(open(os.path.join(ROOT, 'match_projections_archive.json'), encoding='utf-8')).items():
            if m.get('score'): continue
            try: ko = _t(m.get('utc'))
            except Exception: continue
            if -POST_MIN * 60 <= (ko - now).total_seconds() <= PRE_MIN * 60:
                out.append(dict(mid=str(fid), comp=m.get('league'), ko=ko, home=m.get('home'), away=m.get('away'), hid=m.get('home_id'), aid=m.get('away_id'),
                                xh=m.get('home_adj_xg'), xa=m.get('away_adj_xg'), xh_ou=None, xa_ou=None, euro=False, md=m.get('gw')))
    except Exception as e:
        print(f'lineup_window: εγχωριο προγραμμα σφαλμα {str(e)[:60]}')
    try:
        for m in json.load(open(os.path.join(ROOT, 'euro_projections.json'), encoding='utf-8')).get('matches', []):
            if m.get('finished') or m.get('comp') not in PIN_EU: continue
            try: ko = _t(m.get('utc'))
            except Exception: continue
            if -POST_MIN * 60 <= (ko - now).total_seconds() <= PRE_MIN * 60:
                out.append(dict(mid=str(m['mid']), comp=m['comp'], ko=ko, home=m.get('home'), away=m.get('away'), hid=m.get('hid'), aid=m.get('aid'),
                                xh=m.get('xgh'), xa=m.get('xga'), xh_ou=m.get('xgh_ou'), xa_ou=m.get('xga_ou'), euro=True))
    except Exception as e:
        print(f'lineup_window: ευρωπαικο προγραμμα σφαλμα {str(e)[:60]}')
    return out


def fotmob(mid):
    import intl_fetch
    d = json.loads(intl_fetch.get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}'))
    lu = (d.get('content') or {}).get('lineup') or {}; rec = dict(type=lu.get('lineupType'))
    for side, k in (('homeTeam', 'h'), ('awayTeam', 'a')):
        t = lu.get(side) or {}
        rec[k + '_tid'] = t.get('id')
        if lu.get('lineupType') in ('standard', 'predicted'):
            rec[k + '_xi'] = [p['id'] for p in (t.get('starters') or []) if p.get('id')]
            rec[k + '_val'] = {str(p['id']): p.get('marketValue') for p in (t.get('starters') or []) if p.get('id')}
        rec[k + '_out'] = [u.get('id') for u in (t.get('unavailable') or [])]
        rec[k + '_names'] = {str(p.get('id')): p.get('name') for grp in ('starters', 'subs', 'unavailable') for p in (t.get(grp) or []) if p.get('id')}
    return rec


def pin_odds(events, m):
    from euro_odds_scan import sim
    best, bs = None, 0.0
    for g in events:
        try: ct = _t(g.get('commence_time'))
        except Exception: continue
        if abs((ct - m['ko']).total_seconds()) > 15 * 60: continue
        s = (sim(g.get('home_team', ''), m['home'] or '') + sim(g.get('away_team', ''), m['away'] or '')) / 2
        if s > bs: best, bs = g, s
    if not best or bs < 0.45: return None
    ah = ou = None
    for b in best.get('bookmakers', []):
        for mk in b.get('markets', []):
            if mk.get('key') == 'spreads':
                hp = ho = ao = None
                for o in mk.get('outcomes', []):
                    if o.get('name') == best.get('home_team'): hp, ho = o.get('point'), o.get('price')
                    elif o.get('name') == best.get('away_team'): ao = o.get('price')
                if hp is not None and ho and ao: ah = [float(hp), float(ho), float(ao)]
            elif mk.get('key') == 'totals':
                pt = ov = un = None
                for o in mk.get('outcomes', []):
                    nm = str(o.get('name', '')).lower()
                    if nm == 'over': pt, ov = o.get('point'), o.get('price')
                    elif nm == 'under': un = o.get('price')
                if pt is not None and ov and un: ou = [float(pt), float(ov), float(un)]
    return dict(ah=ah, ou=ou, lim=best.get('limits'))


def shadow(m, fm, od, now):
    import picks, euro_shadow_scan as ES, xi_formula as XF
    import numpy as np
    dh = XF.team_delta(fm['h_tid'], fm.get('h_xi'), fm.get('h_val')); da = XF.team_delta(fm['a_tid'], fm.get('a_xi'), fm.get('a_val'))
    gd_adj, tot_adj = XF.adjust(dh, da)
    rec = dict(t=now.isoformat()[:16], mid=m['mid'], comp=m['comp'], ko=m['ko'].isoformat()[:16], home=m['home'], away=m['away'],
               mins_to_ko=round((m['ko'] - now).total_seconds() / 60), gd_adj=gd_adj, tot_adj=tot_adj,
               h_changes=dh and dh['n_changes'], a_changes=da and da['n_changes'],
               h_out=[fm.get('h_names', {}).get(str(p), p) for p in (dh or {}).get('out_of_usual', [])],
               a_out=[fm.get('a_names', {}).get(str(p), p) for p in (da or {}).get('out_of_usual', [])],
               ah=od and od.get('ah'), ou=od and od.get('ou'), sides=[])
    if gd_adj is None or m.get('xh') is None or not od: return rec
    def ed(pw, pp, o): return pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
    def dist(xh, xa):
        return ES.eu_dist(xh, xa, .85) if m['euro'] else picks.gd_dist_dom(max(xh, .05), max(xa, .05))
    if od.get('ah'):
        lh, oh, oa = od['ah']
        for side, ln, o in ((1, lh, oh), (-1, -lh, oa)):
            if abs(ln) < 0.5 or not (1.70 <= o <= 2.10): continue
            role = 'dog' if ln > 0 else 'fav'; e = []
            bx, ba = m['xh'], m['xa']
            if not m['euro']:            # 21/10: ιδια xG με το live — αγκυρα κοντων γραμμων 15+ (dogs) / αγκυρα .7 (φαβορι 15+)
                try:
                    import core7_anchor
                    if role == 'dog': bx, ba, _ = core7_anchor.apply(m['comp'], m['hid'], m['aid'], bx, ba, lh, m.get('md'))
                    elif (m.get('md') or 0) >= picks.FAV_MIN_MD: bx, ba, _ = core7_anchor.apply_fav(m['comp'], m['hid'], m['aid'], bx, ba, m.get('md'))
                except Exception as _e:
                    print(f'lineup_window: αγκυρα σφαλμα {str(_e)[:60]}')
            for sh in (0.0, gd_adj):
                d = dist(bx + sh / 2, ba - sh / 2)
                pw, pp = picks.p_cover(d, side, ln) if role == 'dog' else ES.cover_q(d, side, ln); e.append(round(ed(pw, pp, o), 4))
            rec['sides'].append(dict(mkt='AH', side=side, line=ln, odds=o, role=role, e0=e[0], e1=e[1], pick=bool(e[1] >= TH[role])))
    if od.get('ou') and tot_adj is not None:
        L, oo, uu = od['ou']
        xh = m['xh_ou'] if m.get('xh_ou') else m['xh']; xa = m['xa_ou'] if m.get('xa_ou') else m['xa']
        for over, o in ((True, oo), (False, uu)):
            if not (1.70 <= o <= 2.10): continue
            e = []
            for sh in (0.0, tot_adj):
                f = (xh + xa + sh) / max(xh + xa, .1)
                if m['euro']:
                    po, pu = ES.p_over(ES.tot_dist(xh * f, xa * f, .85), L)
                else:
                    M = picks.score_matrix_dom(xh * f, xa * f); idx = np.add.outer(np.arange(13), np.arange(13))
                    tt = np.bincount(idx.ravel(), weights=np.asarray(M).ravel(), minlength=25); ks = np.arange(25)
                    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; po = pu = 0
                    for x in parts: po += tt[ks > x + .01].sum() / len(parts); pu += tt[ks < x - .01].sum() / len(parts)
                pw, pl = (po, pu) if over else (pu, po); e.append(round(pw * (o - 1) * (1 - picks.MARGIN) - pl, 4))
            role = 'over' if over else 'under'
            rec['sides'].append(dict(mkt='OU', side=role, line=L, odds=o, role=role, e0=e[0], e1=e[1], pick=bool(e[1] >= TH[role])))
    return rec


def main(fast=False):
    """fast=True (σκοπια ανα 1′): για ματς που ΗΔΗ εχουν επισημη ενδεκαδα δεν ξαναρωταμε το FotMob — μονο τιμη Pinnacle."""
    now = dt.datetime.now(UTC)
    W = window_matches(now)
    if not W:
        if not fast: print('lineup_window: κανενα ματς στο παραθυρο σεντρας')
        return 0
    try: st = json.load(open(ST, encoding='utf-8'))
    except Exception: st = {}
    import pin_api
    EV = {}
    for key in {PIN_EU.get(m['comp']) or PIN_DOM.get(m['comp']) for m in W}:
        if not key: continue
        try: EV[key] = pin_api.toa_like(key, include_alt=False)
        except Exception as e: EV[key] = []; print(f'lineup_window: Pinnacle {key} σφαλμα {str(e)[:60]}')
    n_snap = n_sh = 0
    with open(OUT, 'a', encoding='utf-8') as out, open(SHADOW, 'a', encoding='utf-8') as sh:
        for m in W:
            prev = st.get(m['mid'], {})
            if fast and prev.get('shadow') and prev.get('sig'):
                fm = {k: v for k, v in json.loads(prev['sig']).items() if k in ('type', 'h_xi', 'a_xi')}
            else:
                try: fm = fotmob(m['mid'])
                except Exception as e: fm = dict(type=None, err=str(e)[:60])
            od = pin_odds(EV.get(PIN_EU.get(m['comp']) or PIN_DOM.get(m['comp']), []), m)
            snap = dict(type=fm.get('type'), h_xi=fm.get('h_xi'), a_xi=fm.get('a_xi'),          # προβλεπομενη ΚΑΙ επισημη (το type λεει ποια)
                        ah=od and od.get('ah'), ou=od and od.get('ou'))
            sig = json.dumps(snap, sort_keys=True)
            if prev.get('sig') != sig:
                out.write(json.dumps(dict(t=now.isoformat()[:16], mid=m['mid'], comp=m['comp'], ko=m['ko'].isoformat()[:16], home=m['home'], away=m['away'],
                                          mins_to_ko=round((m['ko'] - now).total_seconds() / 60), lim=od and od.get('lim'), **snap), ensure_ascii=False) + '\n'); n_snap += 1
            if fm.get('type') == 'standard' and not prev.get('shadow'):
                try:
                    sh.write(json.dumps(shadow(m, fm, od, now), ensure_ascii=False, default=float) + '\n'); n_sh += 1; prev['shadow'] = now.isoformat()[:16]
                except Exception as e:
                    print(f'lineup_window: σκια {m["mid"]} σφαλμα {str(e)[:80]}')
            prev['sig'] = sig; prev['ko'] = m['ko'].isoformat()[:16]; st[m['mid']] = prev
            time.sleep(0.25)
    st = {k: v for k, v in st.items() if _t(v['ko'] + ':00+00:00') > now - dt.timedelta(days=2)}
    json.dump(st, open(ST, 'w', encoding='utf-8'), ensure_ascii=False)
    if not fast or n_snap or n_sh:
        print(f'lineup_window{" (1′)" if fast else ""} {now.strftime("%H:%M")}: ματς στο παραθυρο {len(W)} · νεες εγγραφες {n_snap} · σκιες {n_sh}')
    return len(W)


def watch(end_epoch):
    """21/10 (Στελιος: «απο το −80 μεχρι να βγει η ενδεκαδα να τραβαει καθε 1 λεπτο»): τρεχει στο κενο αναμεσα στα τικ του scanner
    (αντι για σκετο sleep 300) — καθε 60″ ξανακοιταει το παραθυρο −80′..+5′. Χωρις ματς στο παραθυρο = μονο αναγνωση αρχειων.
    Ματς χωρις επισημη ενδεκαδα: FotMob + Pinnacle καθε λεπτο · ματς με επισημη: μονο Pinnacle (κινηση τιμης ανα λεπτο ως τη σεντρα)."""
    while end_epoch - time.time() > 55:
        t0 = time.time()
        try: main(fast=True)
        except Exception as e: print(f'lineup_window watch σφαλμα {str(e)[:80]}')
        time.sleep(max(1.0, min(60 - (time.time() - t0), end_epoch - time.time() - 55)))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) > 2 and sys.argv[1] == '--watch': watch(float(sys.argv[2]))
    else: main()
