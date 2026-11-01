"""played.py — «✅ το έπαιξα» του dashboard για τα scripts του scanner (27/10/2026, Στελιος: «κοψε μονο το ΞΑΝΑ PICK για οσα εχω παιξει»).
Διαβαζει το played_picks.json (το γραφει το dashboard, dashboard/played_store.py· ο scanner το τραβαει με git pull σε καθε γυρο).
Κλειδι καρτας = λιγκα|γηπ|φιλ|αγορα|πλευρα|μερα UTC — εδω ταιριαζουμε σε γηπ|φιλ|πλευρα|μερα (η λιγκα/αγορα γραφονται διαφορετικα
ανα script· πλευρα = 1 / -1 / Over / Under, αρκει για να ξεχωρισει χαντικαπ απο συνολα)."""
import os, json

ROOT = os.path.dirname(os.path.abspath(__file__))
_CACHE = None


def _keys():
    global _CACHE
    if _CACHE is None:
        try:
            with open(os.path.join(ROOT, 'played_picks.json'), encoding='utf-8') as fh:
                d = json.load(fh)
            _CACHE = {tuple(k.split('|')[i] for i in (1, 2, 4, 5)) for k in d if k.count('|') == 5}
        except Exception:
            _CACHE = set()
    return _CACHE


def is_played(home, away, side, when):
    """side: 1 / -1 / 'Over' / 'Under' (ή 'Over 171.5') · when: ωρα σεντρας UTC (ISO, με 'T' ή κενο)."""
    s = str(side).split(' ')[0]
    if s in ('1', '1.0'): s = '1'
    elif s in ('-1', '-1.0'): s = '-1'
    return (str(home), str(away), s, str(when or '')[:10]) in _keys()
