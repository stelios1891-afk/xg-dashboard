# -*- coding: utf-8 -*-
"""euro_regulation.py — 19/10/2026 (Στελιος: «αυτο ειναι τεραστιο λαθος και πρεπει να διορθωθει»).
ΚΑΝΟΝΙΚΟΣ ΧΡΟΝΟΣ (90′) σε ΟΛΑ τα αρχεια FotMob (data_*.json: Ευρωπη, εθνικες, πλει-οφ λιγκων, MLS).
Το FotMob δινει: σκορ = ΤΕΛΙΚΟ μετα την παραταση (χωρις τη διαδικασια πεναλτι) · σουτ ολα, μαζι με παραταση και πεναλτι διαδικασιας.
Τα στοιχηματα (χαντικαπ / συνολα / 1Χ2) κλεινουν στο 90′ → hs/as/shots/reds γινονται 90′:
   hs, as        = σκορ 90′ απο το γεγονος «FT» του FotMob (μετρα και αυτογκολ)
   shots         = σουτ με period FirstHalf/SecondHalf (καθυστερησεις μεσα) · shots_et = παραταση + πεναλτι διαδικασιας
   reds          = κοκκινες ως το 90′ (+καθυστερηση) · reds_et = στην παραταση
   hs_ft, as_ft  = τελικο σκορ · reg90 = True · p90 = True (διαχωρισμος με την περιοδο του FotMob, οχι με το λεπτο)
ΠΡΟΣΟΧΗ: το «λεπτο > 90» ΔΕΝ αρκει — σε Copa/MLS/Gold Cup οι καθυστερησεις του 90′ γραφονται 91′+ και μετα πεναλτι χωρις παραταση.
Χρηση: python euro_regulation.py  → ελεγχει ολα τα data_*.json, ξανακατεβαζει απο FotMob οσα ματς εχουν σουτ μετα το 90′ (ή ειναι reg90 χωρις p90)."""
import json, os, glob, sys, time

REG_PERIODS = ('FirstHalf', 'SecondHalf')


def _shot(s):
    return {'tid': s.get('teamId'), 'xg': s.get('expectedGoals'), 'min': s.get('min'), 'sit': s.get('situation'),
            'goal': s.get('eventType') == 'Goal'}


def apply_md(rec, md):
    """Διορθωνει την εγγραφη rec (μορφη dl.parse) με βαση το matchDetails md. Επιστρεφει True αν ηταν παραταση/πεναλτι."""
    c = md.get('content') or {}
    raw = [s for s in ((c.get('shotmap') or {}).get('shots') or []) if not s.get('isOwnGoal')]
    ev = ((c.get('matchFacts') or {}).get('events') or {}).get('events', []) or []
    extra = any(s.get('period') not in REG_PERIODS for s in raw if s.get('period')) or \
        any(e.get('type') == 'Half' and e.get('halfStrShort') in ('AET', 'PEN', 'Pen', 'AP') for e in ev)
    # αναιρεση παλιας λαθος διορθωσης (λεπτο>90) αν τελικα δεν ηταν παραταση
    if rec.get('reg90') and rec.get('hs_ft') is not None:
        rec['hs'], rec['as'] = rec['hs_ft'], rec['as_ft']
        rec['shots'] = (rec.get('shots') or []) + (rec.get('shots_et') or [])
        rec['reds'] = (rec.get('reds') or []) + (rec.get('reds_et') or [])
    for k in ('hs_ft', 'as_ft', 'shots_et', 'reds_et', 'reg90', 'ft_src'):
        rec.pop(k, None)
    if raw:
        rec['shots'] = [_shot(s) for s in raw if (s.get('period') or 'SecondHalf') in REG_PERIODS] if extra else [_shot(s) for s in raw]
    rec['p90'] = True
    if not extra:
        return False
    ft = next((e for e in ev if e.get('type') == 'Half' and e.get('halfStrShort') == 'FT'), None)
    teams = (md.get('header') or {}).get('teams') or []
    rec['hs_ft'] = teams[0].get('score') if teams else rec.get('hs')
    rec['as_ft'] = teams[1].get('score') if len(teams) > 1 else rec.get('as')
    if ft is not None and ft.get('homeScore') is not None:
        rec['hs'], rec['as'] = ft['homeScore'], ft['awayScore']
    rec['shots_et'] = [_shot(s) for s in raw if (s.get('period') or 'SecondHalf') not in REG_PERIODS]
    reds = rec.get('reds') or []
    rec['reds_et'] = [r for r in reds if (r.get('min') or 0) > 90]
    rec['reds'] = [r for r in reds if (r.get('min') or 0) <= 90]
    rec['reg90'] = True
    return True


def suspect(rec):
    if not isinstance(rec, dict) or rec.get('p90'):
        return False
    return bool(rec.get('reg90')) or any(isinstance(s, dict) and (s.get('min') or 0) > 90 for s in (rec.get('shots') or []))


def fix_file(path, sleep=0.3, log=None):
    import intl_fetch
    d = json.load(open(path, encoding='utf-8'))
    recs = d.values() if isinstance(d, dict) else d
    n_chk = n_et = 0
    for r in recs:
        if not suspect(r):
            continue
        old = (r.get('hs'), r.get('as'))
        try:
            md = json.loads(intl_fetch.get(f"https://www.fotmob.com/api/data/matchDetails?matchId={r['mid']}"))
        except Exception as e:
            if log: log(f"      ⚠ {r.get('mid')}: FotMob {str(e)[:60]}")
            continue
        et = apply_md(r, md); n_chk += 1; n_et += et
        if log:
            h = (r.get('home') or {}).get('name'); a = (r.get('away') or {}).get('name')
            log(f"      {'ΠΑΡΑΤΑΣΗ' if et else 'κανονικο '} {h} - {a}: αρχειο {old[0]}-{old[1]} → 90′ {r.get('hs')}-{r.get('as')}"
                + (f" (τελικο {r.get('hs_ft')}-{r.get('as_ft')})" if et else ''))
        time.sleep(sleep)
    if n_chk:
        tmp = path + '.tmp'; json.dump(d, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False); os.replace(tmp, path)
    return n_chk, n_et


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    root = os.path.dirname(os.path.abspath(__file__)); T = [0, 0]
    for f in sorted(glob.glob(os.path.join(root, 'data_*.json'))):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        recs = d.values() if isinstance(d, dict) else (d if isinstance(d, list) else [])
        if not any(suspect(r) for r in recs):
            continue
        print(os.path.basename(f))
        c, e = fix_file(f, log=print); T[0] += c; T[1] += e
    print(f'ΕΛΕΓΧΘΗΚΑΝ {T[0]} ματς · με παραταση/πεναλτι {T[1]}')
