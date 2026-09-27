"""
intl_unavailable.py — ΑΠΟΥΣΙΕΣ FotMob ΠΡΙΝ ΤΗΝ ΕΠΙΣΗΜΗ ΑΠΟΣΤΟΛΗ (27/9/2026, προταση Στελιου: «οι τιμες να βασιζονται στην predicted
και μετα να ανανεωνονται με την τελικη αποστολη»).

Το FotMob, μαζι με την ΠΡΟΒΛΕΠΟΜΕΝΗ ενδεκαδα (μερες πριν), δινει λιστα «unavailable» με λογο (injury / suspension) και εκτιμηση
επιστροφης (π.χ. Λαιμερ: injury, «A few weeks» · Γκρεγκοριτς: injury, «Doubtful»). Αυτη χρησιμοποιειται στην τιμη — ΟΧΙ η ιδια η
προβλεπομενη ενδεκαδα (ειναι εκτιμηση 11 βασικων· η ζυγαρια του μοντελου μετρηθηκε με τους 11 ακριβοτερους της ΚΛΗΣΗΣ/αποστολης,
οποτε ενας ακριβος που «καθεται» δεν ειναι απουσια).
Κανονας: injury ή suspension → ΕΚΤΟΣ απο την αξια κλησης (intl_project.v_call_of)· «Doubtful» → μενει μεσα (φαινεται μονο).
Μετα την επισημη αποστολη (~60′ πριν) ισχυει το intl_lineups_check.py.

Τρεχει σε καθε κυκλο του scanner· ανανεωνει ανα 2 ωρες για τα ματς NL A-D των επομενων 96 ωρων → intl_unavailable.json
{tid: {pid: {name, type, ret, doubtful, match}}, '_asof': ...}.
"""
import os, sys, json, datetime as dt
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT); sys.path.insert(0, ROOT)
import pandas as pd

OUT_F = 'intl_unavailable.json'
LEAGUE = {'NL A': 9806, 'NL B': 9807, 'NL C': 9808, 'NL D': 9809}
HOURS_AHEAD, EVERY_MIN = 96, 120


_MON = {m: i for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september',
                                      'october', 'november', 'december'], 1)}


def until_of(ret, asof):
    """εκτιμηση επιστροφης FotMob → ημερομηνια (ISO) ως την οποια ο παικτης ΛΕΙΠΕΙ· None = διαθεσιμος (π.χ. «Back in training»).
    «Late/Mid/Early <μηνας> <ετος>» → τελος/20/10 του μηνα· «A few days» +4 · «About a week» +7 · «About 1-2 weeks» +11 · «A few weeks» +21 ·
    «Unknown»/αλλο → +30 (λειπει για ολο το παραθυρο)· «Doubtful» → χειριζεται χωριστα (μενει μεσα)."""
    r = ret.lower().strip(); base = dt.date.fromisoformat(asof[:10])
    if 'back in training' in r or 'available' in r:
        return None
    for pre, day in (('late', 31), ('mid', 20), ('early', 10)):     # «επιστρεφει» στο ΤΕΛΟΣ του διαστηματος (συντηρητικα)
        if r.startswith(pre):
            parts = r.split()
            try:
                y_, m_ = int(parts[-1]), _MON[parts[1]]
                last_ = (dt.date(y_ + (m_ == 12), m_ % 12 + 1, 1) - dt.timedelta(days=1)).day
                return dt.date(y_, m_, min(day, last_)).isoformat()
            except Exception:
                break
    for key, add in (('few days', 4), ('about a week', 7), ('1-2 weeks', 11), ('2 weeks', 14), ('few weeks', 21), ('month', 30)):
        if key in r:
            return (base + dt.timedelta(days=add)).isoformat()
    return (base + dt.timedelta(days=30)).isoformat()


def get_json(url):
    import intl_fetch
    return json.loads(intl_fetch.get(url))


def main(force=False):
    now = dt.datetime.now(dt.timezone.utc)
    try:
        cur = json.load(open(OUT_F, encoding='utf-8'))
    except Exception:
        cur = {}
    last = cur.get('_asof')
    if last and not force:
        try:
            if (now - dt.datetime.fromisoformat(last).replace(tzinfo=dt.timezone.utc)).total_seconds() / 60 < EVERY_MIN:
                print(f'intl unavailable: φρεσκο ({last}) — τιποτα'); return 0
        except Exception:
            pass
    try:
        P = pd.read_csv('intl_projections.csv')
    except Exception:
        return 0
    P = P[P.comp.isin(list(LEAGUE))].copy()
    P['ko'] = pd.to_datetime(P.utc, utc=True)
    P = P[(P.ko > now) & (P.ko <= now + pd.Timedelta(hours=HOURS_AHEAD))]
    if P.empty:
        print('intl unavailable: κανενα ματς NL στις επομενες 96 ωρες'); return 0
    fx = {}
    for comp in sorted(set(P.comp)):
        try:
            d = get_json(f'https://www.fotmob.com/api/data/leagues?id={LEAGUE[comp]}&season=2026%2F2027')
            for m in (d.get('fixtures') or {}).get('allMatches', []):
                fx[(int(m['home']['id']), int(m['away']['id']), str(m['status'].get('utcTime', ''))[:10])] = m['id']
        except Exception as e:
            print(f'  {comp}: FotMob {type(e).__name__}')
    out = {'_asof': now.strftime('%Y-%m-%dT%H:%M'), '_xi': {}}; n_m = 0
    for r in P.sort_values('ko').itertuples():
        hid, aid = int(r.hid), int(r.aid)
        mid = fx.get((hid, aid, str(r.utc)[:10]))
        if not mid:
            continue
        try:
            j = get_json(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}')
        except Exception as e:
            print(f'  {r.home}-{r.away}: {type(e).__name__}'); continue
        lu = (j.get('content') or {}).get('lineup') or {}
        n_m += 1
        for side, tid in (('homeTeam', hid), ('awayTeam', aid)):
            # 27/9 (Στελιος): ΠΡΟΒΛΕΠΟΜΕΝΗ ενδεκαδα → οσοι ΛΕΙΠΟΥΝ απο τη λιστα TM προστιθενται στην αξια (π.χ. Hancko/Lobotka, Edmundsson)·
            # ο παγκος ΔΕΝ ειναι απουσια (δεν αφαιρειται κανεις επειδη δεν ειναι στην 11αδα)
            xi_ = [dict(pid=int(p['id']), name=p.get('name')) for p in ((lu.get(side) or {}).get('starters') or []) if p.get('id')]
            if xi_ and str(tid) not in out['_xi']:
                out['_xi'][str(tid)] = dict(match=f'{r.home} - {r.away}', utc=str(r.utc)[:16], type=lu.get('lineupType'), players=xi_)
            for p in ((lu.get(side) or {}).get('unavailable') or []):
                un = p.get('unavailability') or {}
                ret = str(un.get('expectedReturn') or '')
                t = out.setdefault(str(tid), {})
                if str(p.get('id')) in t:              # ιδιος παικτης σε 2 ματς της ομαδας — κρατα το πρωτο (πλησιεστερο)
                    continue
                t[str(p.get('id'))] = dict(name=p.get('name'), type=str(un.get('type') or '').lower(), ret=ret,
                                           doubtful=('doubt' in ret.lower()), match=f'{r.home} - {r.away}',
                                           until=(None if 'doubt' in ret.lower() else until_of(ret, out['_asof'])))
    import hashlib
    body = {k: v for k, v in out.items() if not k.startswith('_')}
    out['_hash'] = hashlib.md5(json.dumps([body, out['_xi']], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    changed = out['_hash'] != cur.get('_hash')
    n_p = sum(len(v) for v in body.values())
    print(f'intl unavailable: {n_m} ματς · {n_p} μη διαθεσιμοι' + (' · ΑΛΛΑΓΗ' if changed else ''))
    if CHECK:
        # scanner: ΔΕΝ γραφει το json (το γραφει το intl-reproject.yml)· αν αλλαξε → ζηταει ξαναυπολογισμο προβολων
        st = _state()
        last_d = st.get('last_dispatch')
        recent = last_d and (now - dt.datetime.fromisoformat(last_d).replace(tzinfo=dt.timezone.utc)).total_seconds() < 30 * 60
        st['last_check'] = now.strftime('%Y-%m-%dT%H:%M')
        if changed and not recent and _dispatch():
            st['last_dispatch'] = now.strftime('%Y-%m-%dT%H:%M'); print('  → ζητηθηκε intl-reproject (νεες προβολες)')
        json.dump(st, open(STATE_F, 'w', encoding='utf-8'))
        return 0
    json.dump(out, open(OUT_F, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return 0


STATE_F = 'intl_unavailable_scan_state.json'
CHECK = '--check' in sys.argv


def _state():
    try:
        return json.load(open(STATE_F, encoding='utf-8'))
    except Exception:
        return {}


def _dispatch():
    import urllib.request
    tok, repo = os.environ.get('GH_DISPATCH_TOKEN'), os.environ.get('GH_REPO')
    if not tok or not repo:
        print('  (χωρις GH_DISPATCH_TOKEN — τοπικα, δεν ζηταω)'); return False
    req = urllib.request.Request(f'https://api.github.com/repos/{repo}/actions/workflows/intl-reproject.yml/dispatches',
                                 data=json.dumps({'ref': 'main'}).encode(), method='POST',
                                 headers={'Authorization': f'Bearer {tok}', 'Accept': 'application/vnd.github+json'})
    try:
        urllib.request.urlopen(req, timeout=20).read(); return True
    except Exception as e:
        print(f'  dispatch απετυχε {type(e).__name__}'); return False


if __name__ == '__main__':
    if CHECK:     # στον scanner: ελεγχος ανα 60′ (state χωριστο αρχειο)
        try:
            _lc = _state().get('last_check')
            if _lc and (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(_lc).replace(tzinfo=dt.timezone.utc)).total_seconds() < 3600:
                print('intl unavailable (check): προσφατος ελεγχος — τιποτα'); sys.exit(0)
        except Exception:
            pass
    sys.exit(main(force=('--force' in sys.argv or CHECK)))
