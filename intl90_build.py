# -*- coding: utf-8 -*-
"""intl90_build.py — 19/10/2026: ξαναχτιζει τη βαση εθνικων με τον ΙΔΙΟ κωδικα του intl_build.py σε 2 εκδοχες, ΧΩΡΙΣ να αγγιξει intl_matches.csv:
  intl90_matches.csv      = 90' (data_*.json οπως διορθωθηκαν σημερα + τα 13 ματς χωρις σουτ απο intl90_scan.json + intl90_results_scores_fixed.json)
  intl90_matches_old.csv  = ιδια ματς με το ΤΕΛΙΚΟ σκορ (οπως ηταν πριν: hs_ft/as_ft, σουτ παρατασης μεσα)
Στηλες extra: et (παραταση/πεναλτι), hs_ft/as_ft."""
import json, sys, builtins
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
SCAN = {m: r for m, r in json.load(open('intl90_scan.json', encoding='utf-8')).items() if r.get('extra')}
ETMID = {}            # mid -> (hs_ft, as_ft)
MODE = sys.argv[1] if len(sys.argv) > 1 else 'new'


def FIXD(d):
    for mid, m in d.items():
        mid = str(mid)
        if m.get('reg90') and m.get('hs_ft') is not None:
            ETMID[mid] = (m['hs_ft'], m['as_ft'])
            if MODE == 'old':
                m['hs'], m['as'] = m['hs_ft'], m['as_ft']; m['shots'] = (m.get('shots') or []) + (m.get('shots_et') or [])
        elif mid in SCAN:
            r = SCAN[mid]; ETMID[mid] = tuple(r['stored'])
            if MODE == 'new' and r.get('ft90') is not None:
                m['hs'], m['as'] = r['ft90']
        elif m.get('p90') and m.get('round') is not None:
            pass
    return d


src = open('intl_build.py', encoding='utf-8').read()
a = "for mid, m in json.load(open(f, encoding='utf-8')).items():"
assert a in src
src = src.replace(a, "for mid, m in FIXD(json.load(open(f, encoding='utf-8'))).items():")
if MODE == 'new':
    src = src.replace("open('intl_results_scores.json'", "open('intl90_results_scores_fixed.json'")
OUT = 'intl90_matches.csv' if MODE == 'new' else 'intl90_matches_old.csv'
src = src.replace("M.to_csv('intl_matches.csv', index=False)", "M['et'] = M.mid.isin(ETMID) | M.mid.isin(SCAN); M.to_csv(OUT, index=False)")
assert 'intl_matches.csv' not in src.replace("'intl_matches.csv'", 'X') or True
# score-only ματς με παραταση: σημαια et
_o = open
def _guard(p, mode='r', *a_, **k):
    if any(c in mode for c in 'wa+') and not str(p).startswith('intl90_'):
        raise RuntimeError(f'ΜΠΛΟΚ εγγραφης {p}')
    return _o(p, mode, *a_, **k)
builtins.open = _guard
g = dict(FIXD=FIXD, SCAN=SCAN, ETMID=ETMID, OUT=OUT, __name__='intl90')
exec(compile(src, 'intl_build_90', 'exec'), g)
builtins.open = _o
print(MODE, OUT, 'ματς με παραταση/πεναλτι σημαδεμενα:', int(g['M'].et.sum()))
