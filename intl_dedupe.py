"""
intl_dedupe.py — ΚΛΕΙΔΙ ΑΣΦΑΛΕΙΑΣ κατα των διπλων ματς εθνικων (25/9/2026, εντολη Στελιου «να μην μετρανε duplicates»).

Αιτια που βρεθηκε 25/9: τα φιλικα του Nowgoal επαιρναν FotMob ids ως ΚΕΙΜΕΝΟ ('6595') ενω τα ματς του FotMob ως ΑΡΙΘΜΟ (6595),
οποτε ο ελεγχος διπλων του intl_build.py δεν τα εβλεπε ως ιδια ομαδα → 204 φιλικα (κυριως 2026) μετρουσαν ΔΥΟ φορες στο Elo,
και αλλα 24 ηταν γραμμενα ΑΝΑΠΟΔΑ (γηπεδουχος/φιλοξενουμενος αντεστραμμενοι απο τη μια πηγη).

Κανονας διπλου (ιδιο ματς): ιδιο ΜΗ-διατεταγμενο ζευγαρι ομαδων με σεντρα σε αποσταση <= 1 ημερα (δυο εθνικες δεν ξαναπαιζουν
μεταξυ τους μεσα σε 24 ωρες). Κρατιεται η καλυτερη πηγη: fotmob (xG/σουτ) > fotmob_score > nowgoal_friendly, μετα η νωριτερη εγγραφη.

Χρηση:
    import intl_dedupe
    M = intl_dedupe.dedupe(M, where='intl_rating2_hist')   # καθαριζει + τυπωνει ΠΡΟΕΙΔΟΠΟΙΗΣΗ αν βρηκε διπλα
    intl_dedupe.assert_clean(M)                             # σκληρος ελεγχος (σφαλμα αν υπαρχουν διπλα)
"""
import pandas as pd

SRC_RANK = {'fotmob': 0, 'fotmob_score': 1, 'nowgoal_friendly': 2}
WINDOW = pd.Timedelta(days=1)


def _norm(M):
    M = M.copy()
    M['hid'] = pd.to_numeric(M['hid'], errors='coerce').astype('Int64')
    M['aid'] = pd.to_numeric(M['aid'], errors='coerce').astype('Int64')
    M['mid'] = M['mid'].astype(str)
    return M


def find_duplicates(M):
    """Λιστα (index_που_φευγει, index_που_μενει). Δεν αλλαζει το M."""
    N = _norm(M)
    dt = pd.to_datetime(N['date'], errors='coerce', utc=True)
    rank = N['src'].map(SRC_RANK).fillna(9) if 'src' in N.columns else pd.Series(0, index=N.index)
    order = sorted(N.index, key=lambda i: (rank[i], dt[i] if pd.notna(dt[i]) else pd.Timestamp.max.tz_localize('UTC'), i))
    kept_mid = {}
    kept_pair = {}          # frozenset(hid, aid) -> [(dt, index)]
    drops = []
    for i in order:
        mid = N.at[i, 'mid']
        if mid in kept_mid:
            drops.append((i, kept_mid[mid])); continue
        h, a = N.at[i, 'hid'], N.at[i, 'aid']
        key = frozenset((int(h), int(a))) if pd.notna(h) and pd.notna(a) else None
        hit = None
        if key is not None and pd.notna(dt[i]):
            for d0, j in kept_pair.get(key, []):
                if abs(dt[i] - d0) <= WINDOW:
                    hit = j; break
        if hit is not None:
            drops.append((i, hit)); continue
        kept_mid[mid] = i
        if key is not None and pd.notna(dt[i]):
            kept_pair.setdefault(key, []).append((dt[i], i))
    return drops


def dedupe(M, where='', verbose=True):
    """Επιστρεφει M χωρις διπλα (ιδια σειρα/στηλες, hid/aid ακεραιοι). Τυπωνει προειδοποιηση αν αφαιρεσε κατι."""
    drops = find_duplicates(M)
    out = _norm(M)
    if drops:
        out = out.drop(index=[i for i, _ in drops])
        if verbose:
            n_rev = sum(1 for i, j in drops if int(out.at[j, 'hid']) != int(_norm(M).at[i, 'hid']))
            print(f'⚠ intl_dedupe{(" [" + where + "]") if where else ""}: αφαιρεθηκαν {len(drops)} διπλα ματς '
                  f'({n_rev} ανεστραμμενα γηπ/φιλοξ) — ΔΕΝ μετρανε στο rating', flush=True)
    out['hid'] = out['hid'].astype('int64'); out['aid'] = out['aid'].astype('int64')
    return out


def assert_clean(M, where=''):
    drops = find_duplicates(M)
    if drops:
        ex = [(M.loc[i, 'date'], M.loc[i, 'hid'], M.loc[i, 'aid']) for i, _ in drops[:3]]
        raise AssertionError(f'intl_dedupe{(" [" + where + "]") if where else ""}: {len(drops)} διπλα ματς εθνικων, π.χ. {ex}')
