"""
intl_lineups_check.py — ΑΠΟΣΤΟΛΕΣ/11ΑΔΕΣ ΕΘΝΙΚΩΝ ΠΡΙΝ ΤΗ ΣΕΝΤΡΑ → μετατοπιση των ΔΙΚΩΝ μας τιμων (26/9/2026, εντολη Στελιου).

Τρεχει σε καθε κυκλο του scanner (~5′). Για καθε ματς εθνικων (NL A-D) που ξεκινα μεσα στα επομενα 90′:
  1. FotMob matchDetails → lineup. Οσο ειναι «predicted» (11 χωρις παγκο) περιμενει· μολις γινει επισημη (11 βασικοι + παγκος,
     ~60′ πριν — αν βγει στα 56′ ή στα 45′, πιανεται στον επομενο κυκλο) προχωρα.
  2. Αξια αποστολης = αθροισμα των 11 ακριβοτερων απο ΟΣΟΥΣ ΝΤΥΘΗΚΑΝ (ιδιο μετρο με την αξια κλησης TM, ιδια ζυγαρια 56 Elo/ln).
     Πιανει οσους λειπουν απο την αποστολη (π.χ. Σαμοροντοφ) ΚΑΙ οσους λειπαν απο τη λιστα TM (π.χ. Edmundsson Φεροε).
  3. Ξαναβγαζει Μ1 και Μ3 (το Μ2 δεν εχει αξια ροστερ) με την ΙΔΙΑ συνταγη του intl_project (diff → T → υπεροχη, βαθια φαβορι,
     νεο T για over) → fair (με γκανιοτα αγορας) + edge στη γραμμη της αγορας εκεινη τη στιγμη → συναινεση πριν/μετα.
  4. Telegram μια φορα ανα ματς (και ξανα αν αλλαξει η αποστολη) + intl_lineups.json για την καρτα του dashboard.
Η ενδεκαδα (βασικοι/παγκος) φαινεται ΜΟΝΟ ως πληροφορια — δεν μπαινει στην τιμη (δεν εχει μετρηθει βασικος vs παγκος στις εθνικες).
Τα picks και το Pick History ΔΕΝ αλλαζουν αυτοματα.
"""
import os, sys, json, math, datetime as dt
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT); sys.path.insert(0, ROOT)
import pandas as pd
import picks, intl_pricing as ip, intl_pick_status as ps

OUT_F = 'intl_lineups.json'
WIN_MIN = 90
LEAGUE = {'NL A': 9806, 'NL B': 9807, 'NL C': 9808, 'NL D': 9809}
REASON = {'injury': 'τραυμ.', 'suspension': 'τιμωρια', 'international duty': 'αλλη υποχρ.'}


def _j(f, default=None):
    try:
        return json.load(open(f, encoding='utf-8'))
    except Exception:
        return default


def get_json(url):
    import intl_fetch
    return json.loads(intl_fetch.get(url))


def fixtures(comp, cache={}):
    if comp not in cache:
        d = get_json(f'https://www.fotmob.com/api/data/leagues?id={LEAGUE[comp]}&season=2026%2F2027')
        cache[comp] = {(int(m['home']['id']), int(m['away']['id']), str(m['status'].get('utcTime', ''))[:10]): m['id']
                       for m in (d.get('fixtures') or {}).get('allMatches', [])}
    return cache[comp]


def lam(v, d, rh, ra, C):
    """ιδια συνταγη με intl_project: T καταστασης, υπεροχη a·diff, βαθια κατανομη a_deep·diff (NL: χωρις KO, −0.05)."""
    close = abs(rh - ra) < 150
    T = 0.29 + 0.33 * abs(d) / 100 + 0.49 * close + 0.10 * (rh + ra) / 2 / 100 - 0.05
    a = C['a'] if v == 'H' else C['aA']; ad = C['adeep'][v]
    return (max((T + a * d) / 2, .15), max((T - a * d) / 2, .15), max((T + ad * d) / 2, .15), max((T - ad * d) / 2, .15), T, close)


def model_eval(v, d, V, mk, C, xgsum, TMIX):
    """edges/fair/pick ενος μοντελου (H=Μ1, AV=Μ3) με diff d, στη γραμμη της αγορας mk."""
    lh, la, lhD, laD, T, close = lam(v, d, V['R_h'], V['R_a'], C)
    dist, dd = picks.gd_dist(lh, la), picks.gd_dist(lhD, laD)
    out = dict(xg=(round(lh, 2), round(la, 2)), picks=[])
    if mk.get('ah_line') is not None and mk.get('oh') and mk.get('oa'):
        S = 1 / mk['oh'] + 1 / mk['oa']
        for side, ud, odds, tag in ((1, mk['ah_line'], mk['oh'], 'h'), (-1, -mk['ah_line'], mk['oa'], 'a')):
            dx = ip.dist_for(dist, dd, ud)
            e = ip.ah_ev(dx, side, ud, odds, picks.MARGIN); f = ip.ah_fair(dx, side, ud)
            out[f'e_{tag}'] = round(e * 100, 1); out[f'f_{tag}'] = round(f / S, 2) if f else None
            if 1.70 <= odds <= 2.10 and e >= .10 and abs(ud) >= .5:
                out['picks'].append(('AH', 1 if side == 1 else 2))
    if mk.get('ou_line') is not None and mk.get('over'):
        To = ip.t_over(T, v, xgsum, TMIX)
        e = ip.over_ev(To, mk['ou_line'], mk['over']); out['e_o'] = round(e * 100, 1)
        if e >= .08 and close:
            out['picks'].append(('OVER', 0))
    return out


def m2_eval(m, src, mk):
    e = ((m.get('edges') or {}).get('A') or {}).get(src) or {}
    out = dict(e_h=e.get('ah_home'), e_a=e.get('ah_away'), e_o=e.get('over'), picks=[])
    if mk.get('ah_line') is not None:
        for side, ud, odds, k in ((1, mk['ah_line'], mk.get('oh'), 'ah_home'), (2, -mk['ah_line'], mk.get('oa'), 'ah_away')):
            if odds and e.get(k) is not None and 1.70 <= odds <= 2.10 and e[k] >= 10 and abs(ud) >= .5:
                out['picks'].append(('AH', side))
    if e.get('over') is not None and e['over'] >= 8 and 'OVER' in str((m.get('picks') or {}).get('over_A', '')):
        out['picks'].append(('OVER', 0))
    return out


def cons(evs):
    cnt = {}
    for lab, ev in evs.items():
        for p in ev['picks']:
            cnt.setdefault(p, []).append(lab)
    return {p: labs for p, labs in cnt.items() if len(labs) >= 2}


def team_value(ids, tid, VC, PVN):
    vmap = {int(p['pid']): p['v'] for p in (VC.get(str(tid)) or {}).get('players', []) if p.get('pid') and p.get('v')}
    vals = []
    for i in ids:
        v = vmap.get(int(i)) or ((PVN.get(str(i)) or [None, None])[1])
        if v:
            vals.append((v, int(i)))
    vals.sort(reverse=True)
    return (sum(v for v, _ in vals[:11]) if len(vals) >= 11 else None), vals


def main():
    now = dt.datetime.now(dt.timezone.utc)
    D = _j('intl_projections_dashboard.json', {})
    due = []
    for c in D.get('comps', []):
        if c.get('comp') not in LEAGUE:
            continue
        for m in c.get('matches', []):
            try:
                ko = dt.datetime.fromisoformat(m['utc'].replace(' ', 'T')[:16]).replace(tzinfo=dt.timezone.utc)
            except Exception:
                continue
            if 0 < (ko - now).total_seconds() / 60 <= WIN_MIN:
                due.append((c['comp'], m, ko))
    if not due:
        print('intl lineups: κανενα ματς στα επομενα 90′'); return 0
    state = _j(OUT_F, {}) or {}
    P = pd.read_csv('intl_projections.csv')
    VC, PVN = _j('intl_vcall_tm.json', {}), _j('intl_player_values_now.json', {})
    C = _j('intl_project_coefs.json'); AD = _j('intl_xg_attdef.json'); TMIX = _j('intl_tmix_config.json')
    if not C:
        print('intl lineups: λειπει intl_project_coefs.json'); return 0
    msgs = []; changed = False
    for comp, m, ko in due:
        key = f"{comp}|{m['home']}|{m['away']}|{m['utc']}"
        try:
            mid = fixtures(comp).get((int(m['hid']), int(m['aid']), m['utc'][:10]))
            j = get_json(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}') if mid else None
        except Exception as e:
            print(f'  {key}: FotMob {type(e).__name__}'); continue
        lu = ((j or {}).get('content') or {}).get('lineup') or {}
        th, ta = lu.get('homeTeam') or {}, lu.get('awayTeam') or {}
        if lu.get('lineupType') == 'predicted' or len(th.get('subs') or []) < 7 or len(ta.get('subs') or []) < 7:
            print(f'  {key}: η αποστολη δεν εχει βγει ακομα ({lu.get("lineupType")}) — ξανα στον επομενο κυκλο'); continue
        ids = {s: [int(p['id']) for p in (t.get('starters') or []) + (t.get('subs') or [])] for s, t in (('h', th), ('a', ta))}
        sig = sorted(ids['h']) + [0] + sorted(ids['a'])
        if state.get(key, {}).get('sig') == sig:
            continue                                   # ιδια αποστολη — ηδη ενημερωθηκαμε
        row = P[(P.home == m['home']) & (P.away == m['away']) & (P.utc.str[:16] == m['utc'].replace(' ', 'T')[:16])]
        if row.empty:
            continue
        row = row.iloc[0]
        teams = {}
        for s, tid, nm, t, vb in (('h', m['hid'], m['home'], th, row.get('Vh_raw')), ('a', m['aid'], m['away'], ta, row.get('Va_raw'))):
            v23, vals = team_value(ids[s], tid, VC, PVN)
            vb = float(vb) if pd.notna(vb) else (float(row['V_h' if s == 'h' else 'V_a']) * 1e6 if pd.notna(row['V_h' if s == 'h' else 'V_a']) else None)
            call = sorted([p for p in (VC.get(str(tid)) or {}).get('players', []) if p.get('v')], key=lambda p: -p['v'])
            call_ids = {int(p['pid']) for p in call if p.get('pid')}
            top_call = call[:11]
            out23 = [f"{p['tm'].title()}({p['v'] / 1e6:.1f}M)" for p in top_call if p.get('pid') and int(p['pid']) not in ids[s]]
            new = [f"{(PVN.get(str(i)) or [str(i)])[0]}({v / 1e6:.1f}M)" for v, i in vals[:11] if i not in call_ids]
            starters = {int(p['id']) for p in (t.get('starters') or [])}
            bench = [f"{(PVN.get(str(i)) or [str(i)])[0]}" for v, i in vals[:6] if i not in starters]
            unav = [f"{p.get('name')} ({REASON.get(str((p.get('unavailability') or {}).get('type', '')).lower(), 'εκτος')})" for p in (t.get('unavailable') or [])]
            dE = C['elo_per_ln'] * math.log(v23 / vb) if (v23 and vb) else 0.0
            teams[s] = dict(nm=nm, v0=vb, v1=v23, dE=round(dE, 1), out23=out23, new=new, bench=bench, unav=unav)
        delta = teams['h']['dE'] - teams['a']['dE']
        src, mk = ps.market_src(m)
        xgsum = ip.team_xg_sum(AD, m['hid'], m['aid'])
        ev0, ev1 = {}, {}
        for v, lab in (('H', 'Μ1'), ('AV', 'Μ3')):
            V = (m.get('versions') or {}).get(v)
            if not V or V.get('diff') is None:
                continue
            ev0[lab] = model_eval(v, V['diff'], V, mk, C, xgsum, TMIX)
            ev1[lab] = model_eval(v, V['diff'] + delta, V, mk, C, xgsum, TMIX)
        m2 = m2_eval(m, src, mk)
        c0, c1 = cons({**ev0, 'Μ2': m2}), cons({**ev1, 'Μ2': m2})
        def cl(cc):
            if not cc:
                return 'καμια'
            out = []
            for (mkt, side), labs in cc.items():
                if mkt == 'OVER':
                    out.append(f"Over {mk.get('ou_line'):g} ({'+'.join(sorted(labs))})")
                else:
                    ln = mk['ah_line'] if side == 1 else -mk['ah_line']
                    out.append(f"{m['home'] if side == 1 else m['away']} {ln:+g} ({'+'.join(sorted(labs))})")
            return ' · '.join(out)
        lines = [f"📋 ΑΠΟΣΤΟΛΕΣ · {comp} · {m['home']} – {m['away']} ({ps_time(ko)})"]
        for s in ('h', 'a'):
            t = teams[s]
            ln_ = f"{t['nm']}: αξια {t['v0'] / 1e6:.1f}→{t['v1'] / 1e6:.1f}M ({t['dE']:+.0f} Elo)" if (t['v0'] and t['v1']) else f"{t['nm']}: αξια —"
            if t['out23']:
                ln_ += ' · εκτος 23: ' + ', '.join(t['out23'][:4])
            if t['new']:
                ln_ += ' · νεοι (οχι στη λιστα TM): ' + ', '.join(t['new'][:3])
            if t['unav']:
                ln_ += ' · μη διαθεσιμοι: ' + ', '.join(t['unav'][:3])
            if t['bench']:
                ln_ += ' · ακριβοι στον παγκο: ' + ', '.join(t['bench'][:3])
            lines.append(ln_)
        if mk.get('ah_line') is not None:
            eds = []
            for lab in ev0:
                eds.append(f"{lab} γηπ {ev0[lab].get('e_h', 0):+.0f}→{ev1[lab].get('e_h', 0):+.0f}% / φιλ {ev0[lab].get('e_a', 0):+.0f}→{ev1[lab].get('e_a', 0):+.0f}%")
            lines.append(f"AH {mk['ah_line']:+g} @{mk['oh']:.2f}/{mk['oa']:.2f} ({src.capitalize()}): " + ' · '.join(eds)
                         + (f" · Μ2 {m2['e_h']:+.0f}/{m2['e_a']:+.0f}%" if m2.get('e_h') is not None else ''))
        lines.append(f"Συναινεση: πριν {cl(c0)} → με αποστολες {cl(c1)}")
        rec = dict(t=now.strftime('%Y-%m-%d %H:%M'), sig=sig, mid=mid, min_before=round((ko - now).total_seconds() / 60),
                   teams=teams, delta_elo=round(delta, 1), src=src, ev0=ev0, ev1=ev1, m2=m2,
                   cons0=cl(c0), cons1=cl(c1), text='\n'.join(lines), update=key in state)
        state[key] = rec; changed = True
        msgs.append(('🔄 ΑΛΛΑΓΗ ΑΠΟΣΤΟΛΗΣ\n' if rec['update'] else '') + rec['text'])
        print(rec['text'])
    if changed:
        json.dump(state, open(OUT_F, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    if msgs and os.environ.get('TELEGRAM_TOKEN') and os.environ.get('TELEGRAM_CHAT_ID'):
        import notify
        for t in msgs:
            notify.send(t)
    return 0


def ps_time(ko):
    try:
        from zoneinfo import ZoneInfo
        return ko.astimezone(ZoneInfo('Europe/Athens')).strftime('%H:%M')
    except Exception:
        return ko.strftime('%H:%M UTC')


if __name__ == '__main__':
    sys.exit(main())
