# -*- coding: utf-8 -*-
"""intl90_harness.py — τρεχει ενα ΥΠΑΡΧΟΝ script εθνικων με διορθωμενα (new) ή παλια (old) σκορ ΧΩΡΙΣ να αγγιξει live αρχεια.
  python intl90_harness.py <old|new> <script.py> [ENV=VAL ...]
  - διαβασμα intl_matches.csv -> intl90_matches.csv (new) / intl90_matches_old.csv (old)
  - καθε ΕΓΓΡΑΦΗ αρχειου -> φακελος intl90_work/<mode>/<ονομα> (τα live αρχεια μενουν ανεγγιχτα)
  - διαβασμα αρχειου που εχει ηδη γραφτει στο intl90_work/<mode>/ -> απο εκει (ετσι αλυσιδα rating -> preds -> backtest με 90')"""
import sys, os, builtins, io
sys.stdout.reconfigure(encoding='utf-8')
MODE, SCRIPT = sys.argv[1], sys.argv[2]
for kv in sys.argv[3:]:
    k, v = kv.split('=', 1); os.environ[k] = v
ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(ROOT, 'intl90_work', MODE); os.makedirs(WORK, exist_ok=True)
MATCHES = 'intl90_matches_old.csv' if MODE.startswith('old') else 'intl90_matches.csv'
_open = builtins.open


def _map(p, mode):
    s = os.fspath(p) if not isinstance(p, int) else p
    if isinstance(s, int):
        return s
    base = os.path.basename(s); absd = os.path.dirname(os.path.abspath(s))
    if absd != ROOT:
        if any(c in mode for c in 'wax+') and not os.path.abspath(s).startswith(os.path.join(ROOT, 'intl90_work')):
            return os.path.join(WORK, '_sub_' + base)
        return s
    if any(c in mode for c in 'wax+'):
        if base.startswith('intl90_') and base.endswith('_out.txt'):
            return s
        return os.path.join(WORK, base)
    if base == 'intl_matches.csv':
        return os.path.join(ROOT, MATCHES)
    w = os.path.join(WORK, base)
    return w if os.path.exists(w) else s


PATCH = os.environ.get('I90_PATCH')      # "αρχειο.py|παλιο κειμενο|νεο κειμενο" — αλλαγη πηγαιου ΜΟΝΟ στη μνημη (για παραλλαγες)


def guarded_open(p, mode='r', *a, **k):
    if PATCH and 'b' not in mode and not any(c in mode for c in 'wax+') and not isinstance(p, int) and os.path.basename(os.fspath(p)) == PATCH.split('|')[0]:
        f_, o_, n_ = PATCH.split('|')
        txt = _open(_map(p, mode), mode, *a, **k).read(); assert o_ in txt, 'patch δεν βρεθηκε'
        return io.StringIO(txt.replace(o_, n_))
    return _open(_map(p, mode), mode, *a, **k)


builtins.open = guarded_open
io.open = guarded_open
import pandas as pd
_rc = pd.read_csv


def read_csv(p, *a, **k):
    if isinstance(p, (str, os.PathLike)):
        p = _map(p, 'r')
    return _rc(p, *a, **k)


pd.read_csv = read_csv
_tc = pd.DataFrame.to_csv
def to_csv(self, p=None, *a, **k):
    if isinstance(p, (str, os.PathLike)):
        p = _map(p, 'w')
    return _tc(self, p, *a, **k)
pd.DataFrame.to_csv = to_csv
_sc = pd.Series.to_csv
def sto_csv(self, p=None, *a, **k):
    if isinstance(p, (str, os.PathLike)):
        p = _map(p, 'w')
    return _sc(self, p, *a, **k)
pd.Series.to_csv = sto_csv
import os as _os
_rep = _os.replace
def _replace(a, b):
    return _rep(_map(a, 'w'), _map(b, 'w'))
_os.replace = _replace
sys.argv = [SCRIPT]
sys.path.insert(0, ROOT)
os.chdir(ROOT)
src = _open(SCRIPT, encoding='utf-8').read()
exec(compile(src, SCRIPT, 'exec'), {'__name__': '__main__', '__file__': os.path.join(ROOT, SCRIPT)})
