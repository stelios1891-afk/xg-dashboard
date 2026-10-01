"""
intl_freshness.py — ΦΡΕΝΟ ΦΡΕΣΚΑΔΑΣ ΕΘΝΙΚΩΝ (1/10/2026, εντολη Στελιου: «η ανανεωση αποτελεσματων & ratings ειναι ΒΑΣΙΚΗ
προυποθεση πριν στοιχηματισουμε»). Αφορμη: το intl-refresh εσπαγε σιωπηλα 27/9→1/10 και τα picks εβγαιναν με ratings της 26/9.

ΕΛΕΓΧΟΣ (καλειται απο το intl_picks_ledger μονο οταν υπαρχουν νεα picks — 5 κλησεις FotMob):
  (α) ΑΠΟΤΕΛΕΣΜΑΤΑ: καθε ματς NL A-D / φιλικο που το FotMob δινει ΤΕΛΕΙΩΜΕΝΟ (τελευταιες 21 μερες) πρεπει να υπαρχει στο intl_matches.csv.
      Αν λειπει → οι δυο ομαδες του ειναι «μπαγιατικες» (το rating τους δεν ξερει το τελευταιο τους ματς).
  (β) RATINGS: καθε ματς του intl_matches.csv (τελευταιες 60 μερες) πρεπει να υπαρχει στις προβλεψεις του Μ1 (intl_preds_H.csv) ΚΑΙ της
      αγκυρας (intl_preds_anchor.csv) — αλλιως τα ratings δεν ξαναχτιστηκαν → ΟΛΑ τα picks σταματουν.
Pick με ομαδα μπαγιατικη (ή (β) ✗) ΔΕΝ καταγραφεται / ΔΕΝ στελνεται· ξαναελεγχεται σε καθε τικ και βγαινει μολις φρεσκαρει.
Κατασταση → intl_guard_state.json (την διαβαζει και το dashboard: «⏸ περιμενει ανανεωση»).
"""
import os, json, gzip, time, urllib.request, datetime as dt
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_F = os.path.join(ROOT, 'intl_guard_state.json')
LEAGUES = {'NL A': (9806, '2026%2F2027'), 'NL B': (9807, '2026%2F2027'), 'NL C': (9808, '2026%2F2027'),
           'NL D': (9809, '2026%2F2027'), 'Friendlies': (114, '2026')}
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36', 'Accept-Encoding': 'gzip'}
LOOKBACK_D, RATINGS_D = 21, 60


def fotmob_finished(now):
    """[(mid, hid, aid, utc, comp, 'home – away')] τελειωμενα ματς των τελευταιων LOOKBACK_D ημερων· None αν απετυχε ΚΑΘΕ κληση."""
    out, ok = [], 0
    for comp, (lid, sea) in LEAGUES.items():
        try:
            raw = urllib.request.urlopen(urllib.request.Request(f'https://www.fotmob.com/api/data/leagues?id={lid}&season={sea}', headers=HDR),
                                         timeout=25).read()
            raw = gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw
            ok += 1
            for m in json.loads(raw).get('fixtures', {}).get('allMatches', []):
                st = m.get('status', {})
                if not st.get('finished') or st.get('cancelled') or st.get('awarded'):
                    continue
                try:
                    t = dt.datetime.fromisoformat(st['utcTime'].replace('Z', '+00:00'))
                except Exception:
                    continue
                if (now - t).days > LOOKBACK_D:
                    continue
                out.append((str(m['id']), int(m['home']['id']), int(m['away']['id']), t.strftime('%Y-%m-%d %H:%M'), comp,
                            f"{m['home']['name']} – {m['away']['name']}"))
        except Exception as e:
            print(f'  φρενο: FotMob {comp} σφαλμα {str(e)[:60]}', flush=True)
        time.sleep(0.3)
    return out if ok else None


def check(now=None, finished=None):
    """→ dict(ok_ratings, stale_teams {tid: [ματς που λειπουν]}, missing_matches, fotmob_ok, note)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    M = pd.read_csv(os.path.join(ROOT, 'intl_matches.csv'), dtype={'mid': str}, parse_dates=['date'])
    have = set(M.mid)
    # (β) ratings ξαναχτισμενα;
    recent = set(M[M.date >= pd.Timestamp(now.replace(tzinfo=None)) - pd.Timedelta(days=RATINGS_D)].mid)
    miss_r = {}
    for f in ('intl_preds_H.csv', 'intl_preds_anchor.csv'):
        try:
            P = set(pd.read_csv(os.path.join(ROOT, f), dtype={'mid': str}, usecols=['mid']).mid)
        except Exception:
            P = set()
        miss_r[f] = len(recent - P)
    ok_ratings = all(v == 0 for v in miss_r.values())
    # (α) αποτελεσματα περασμενα;
    if finished is None:
        finished = fotmob_finished(now)
    stale, missing = {}, []
    if finished is not None:
        for mid, h, a, utc, comp, lab in finished:
            if mid not in have:
                missing.append(dict(mid=mid, utc=utc, comp=comp, match=lab))
                for t in (h, a):
                    stale.setdefault(t, []).append(f'{lab} ({utc[:10]})')
    note = []
    if not ok_ratings:
        note.append('ratings ΔΕΝ ξαναχτιστηκαν: ' + ', '.join(f'{k} λειπουν {v}' for k, v in miss_r.items() if v))
    if missing:
        note.append(f'{len(missing)} τελειωμενα ματς δεν εχουν περασει: ' + '; '.join(f"{x['match']} {x['utc'][:10]}" for x in missing[:6]))
    if finished is None:
        note.append('FotMob μη διαθεσιμο — ελεγχος αποτελεσματων ΑΔΥΝΑΤΟΣ')
    return dict(ok_ratings=ok_ratings, stale_teams=stale, missing_matches=missing, fotmob_ok=finished is not None,
                note=' · '.join(note), checked=now.strftime('%Y-%m-%d %H:%M'))


def blocked(r, g):
    """Λογος μπλοκαρισματος για pick r (με hid/aid) ή None."""
    if not g['ok_ratings']:
        return 'ratings εθνικων δεν ξαναχτιστηκαν'
    if not g['fotmob_ok']:
        return 'FotMob μη διαθεσιμο — δεν επιβεβαιωνεται οτι τα αποτελεσματα ειναι περασμενα'
    why = []
    for side in ('hid', 'aid'):
        t = r.get(side)
        if t is not None and int(t) in g['stale_teams']:
            why += g['stale_teams'][int(t)]
    return ('λειπει αποτελεσμα: ' + '; '.join(sorted(set(why)))) if why else None


def save_state(g, blocked_keys):
    st = dict(g, stale_teams={str(k): v for k, v in (g.get('stale_teams') or {}).items()}, blocked=blocked_keys)
    with open(STATE_F, 'w', encoding='utf-8') as fh:
        json.dump(st, fh, ensure_ascii=False, indent=1)


def load_state():
    try:
        return json.load(open(STATE_F, encoding='utf-8'))
    except Exception:
        return {}
