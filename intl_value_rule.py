"""
intl_value_rule.py — ΚΑΝΟΝΑΣ ΤΕΡΜΑΤΟΦΥΛΑΚΑ στην αξια ροστερ εθνικων (27/9/2026, προταση Στελιου).

Μεχρι τωρα: αξια = αθροισμα των 11 ακριβοτερων (χωρις θεσεις) → μετρουσαν και 2-3 ακριβοι τερματοφυλακες ενω παιζει ενας
(Σερβια: Petrovic 28.6M + Milinkovic-Savic 16.1M — παιζει ο δευτερος). Νεο: ΕΝΑΣ τερματοφυλακας + οι 10 ακριβοτεροι παικτες γηπεδου.
Ποιος τερματοφυλακας: (3) αυτος που ΞΕΚΙΝΑ στην επισημη αποστολη · (2) αλλιως αυτος της προβλεπομενης 11αδας FotMob ·
(1) αλλιως ο τερματοφυλακας του ΤΕΛΕΥΤΑΙΟΥ ΕΠΙΣΗΜΟΥ ματς · αν δεν ειναι στην αποστολη, βασικες 730 ημερων σταθμισμενες με προσφατοτητα
(μισο ανα 180 ημ.) και ειδος (φιλικο ×0.5) · αλλιως ο ακριβοτερος.
Διακοπτης: intl_vcall_config.json 'gk_rule' (ενεργοποιειται μονο αν περασει το τεστ intl_gk_test).
Θεσεις: intl_player_gk.json (pid τερματοφυλακων, απο FotMob playerData).
"""
import json, datetime as dt

try:
    GK = set(int(x) for x in json.load(open('intl_player_gk.json', encoding='utf-8')))
except Exception:
    GK = set()
_STARTS = None
VR_GK_ALL = GK


def enabled():
    try:
        return bool(json.load(open('intl_vcall_config.json', encoding='utf-8')).get('gk_rule', False))
    except Exception:
        return False


def _load_starts():
    """{tid: [(date, [starter pids])]} απο intl_squads.json + intl_matches.csv."""
    global _STARTS
    if _STARTS is not None:
        return _STARTS
    _STARTS = {}
    try:
        import pandas as pd
        SQ = json.load(open('intl_squads.json', encoding='utf-8'))
        M = pd.read_csv('intl_matches.csv', dtype={'mid': str})
        for r in M.itertuples():
            rec = SQ.get(r.mid) or {}
            for sk, t in (('h', r.hid), ('a', r.aid)):
                st = (rec.get(sk) or {}).get('st') or []
                if st:
                    _STARTS.setdefault(int(t), []).append((str(r.date)[:16], [int(x) for x in st], str(getattr(r, 'ctype', ''))))
    except Exception:
        pass
    return _STARTS


def usual_keeper(tid, keepers, before):
    """ο «βασικος» τερματοφυλακας (απο τη λιστα keepers): βασικες εμφανισεις πριν το before (730 ημερες) ΣΤΑΘΜΙΣΜΕΝΕΣ με προσφατοτητα
    (μισο βαρος ανα 180 ημερες) και ειδος ματς (επισημο 1.0, φιλικο 0.5). Σερβια: Milinkovic-Savic (24/9) > Petrovic (φθινοπωρο 2025)."""
    if not keepers:
        return None
    b_ = dt.datetime.fromisoformat(str(before)[:16].replace(' ', 'T'))
    sc, last = {}, {}
    for d, st, ct in _load_starts().get(int(tid), []):
        d_ = dt.datetime.fromisoformat(d.replace(' ', 'T'))
        age = (b_ - d_).days
        if not (0 <= age <= 730) or d_ >= b_:
            continue
        w = (1.0 if ct in ('nl', 'qual', 'tourn') else 0.5) * 0.5 ** (age / 180)
        for p in st:
            if p in keepers:
                sc[p] = sc.get(p, 0) + w; last[p] = max(last.get(p, ''), d)
    if not sc:
        return None
    # 27/9: ΠΡΩΤΑ ο τερματοφυλακας του ΤΕΛΕΥΤΑΙΟΥ ΕΠΙΣΗΜΟΥ ματς (τρεχουσα επιλογη προπονητη — Σερβια: Milinkovic-Savic 24/9)·
    # η σταθμισμενη βαθμολογια μονο αν αυτος δεν ειναι στην αποστολη
    comp_ = [(d, st) for d, st, ct in _load_starts().get(int(tid), [])
             if ct in ('nl', 'qual', 'tourn') and 0 <= (b_ - dt.datetime.fromisoformat(d.replace(' ', 'T'))).days <= 730
             and dt.datetime.fromisoformat(d.replace(' ', 'T')) < b_]
    for d, st in sorted(comp_, reverse=True):
        g_ = [p for p in st if p in VR_GK_ALL]
        if g_:
            return g_[0] if g_[0] in keepers else max(sc, key=lambda p: (sc[p], last[p]))
    return max(sc, key=lambda p: (sc[p], last[p]))


def top11(items, tid=None, before=None, prefer_gk=None, need=14):
    """items = [(pid ή None, αξια)] → αξια ροστερ. Με ενεργο κανονα: 1 τερματοφυλακας (prefer_gk → usual → ακριβοτερος) + 10 παικτες γηπεδου.
    Χωρις: οι 11 ακριβοτεροι. None αν λιγοτεροι απο need παικτες με αξια."""
    items = [(p, v) for p, v in items if v]
    if len(items) < need:
        return None
    if not enabled() or not GK:
        return float(sum(sorted((v for _, v in items), reverse=True)[:11]))
    keepers = {int(p): v for p, v in items if p is not None and int(p) in GK}
    field = sorted((v for p, v in items if p is None or int(p) not in GK), reverse=True)
    if not keepers:
        return float(sum(field[:11]))
    gk = prefer_gk if (prefer_gk is not None and int(prefer_gk) in keepers) else None
    if gk is None and tid is not None and before is not None:
        gk = usual_keeper(tid, set(keepers), before)
    if gk is None:
        gk = max(keepers, key=keepers.get)
    return float(keepers[int(gk)] + sum(field[:10]))
