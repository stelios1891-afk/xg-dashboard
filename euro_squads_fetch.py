"""euro_squads_fetch.py — 10/10/2026 (Στελιος: «να τα κατεβασουμε»): ενδεκαδες (FotMob matchDetails) για τα ΕΓΧΩΡΙΑ ματς των ευρωπαικων
ομαδων ΕΚΤΟΣ CORE7 (ολες οι λιγκες που εχουμε σε data_*.json) + τα ιδια τα ευρωπαικα ματς, 2021-07 → 2026-06, και μετα ιστορικο αξιας
(FotMob playerData) για τους νεους βασικους. Εξοδοι: euro_squads.json (ιδια μορφη με core7_squads.json), euro_player_values.json. Resumable.
Χρηση: python euro_squads_fetch.py [--count]"""
import sys, os, json, glob, time
from concurrent.futures import ThreadPoolExecutor
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from euro_engine import kodt
import core7_lineups_fetch_lib as L

CORE7 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie'}
SKIP = {'Europe', 'Brazil', 'MLS'}
from datetime import datetime
D0, D1 = datetime(2021, 7, 1), datetime(2026, 7, 1)
eu_teams = set(); eu_mids = []
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        eu_teams |= {int(m['home']['id']), int(m['away']['id'])}; eu_mids.append(str(mid))
dom = []
for f in glob.glob('data_*.json'):
    base = os.path.basename(f)[5:-5]; lg = '_'.join(base.split('_')[:-1])
    if lg in CORE7 or lg in SKIP or lg.startswith(('Nations', 'WC', 'Euro', 'AFCON', 'Copa', 'Friend', 'Intl')): continue
    try:
        d = json.load(open(f, encoding='utf-8'))
    except Exception:
        continue
    for mid, m in d.items():
        try:
            if m.get('hs') is None: continue
            h, a = int(m['home']['id']), int(m['away']['id'])
        except Exception:
            continue
        if h in eu_teams or a in eu_teams:
            dt = kodt(m.get('date'))
            if dt is not None and D0 <= dt < D1: dom.append(str(mid))
core = json.load(open('core7_squads.json', encoding='utf-8'))
OUT = 'euro_squads.json'
done = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
mids = sorted(set(dom) | set(eu_mids))
todo = [m for m in mids if m not in done and m not in core]
print(f'ευρωπαικες ομαδες {len(eu_teams)} · εγχωρια ματς τους (εκτος CORE7) {len(set(dom))} · ευρωπαικα {len(set(eu_mids))} · προς κατεβασμα {len(todo)}', flush=True)
if '--count' in sys.argv: sys.exit(0)
t0 = time.time()
with ThreadPoolExecutor(max_workers=6) as ex:
    for i, (mid, sq) in enumerate(ex.map(L.one, todo)):
        done[mid] = sq or {}
        if (i + 1) % 1000 == 0:
            json.dump(done, open(OUT, 'w', encoding='utf-8'))
            print(f'  {i + 1}/{len(todo)} · {(i + 1) / (time.time() - t0):.1f}/s', flush=True)
json.dump(done, open(OUT, 'w', encoding='utf-8'))
print(f'ενδεκαδες: {sum(1 for v in done.values() if v)} με lineup / {len(done)}', flush=True)
# ---------------- αξιες ----------------
PVO = 'euro_player_values.json'
pv = json.load(open(PVO, encoding='utf-8')) if os.path.exists(PVO) else {}
for seed in ('core7_player_values.json', 'intl_player_values.json', 'gsl_player_values.json'):
    if os.path.exists(seed):
        for k, v in json.load(open(seed, encoding='utf-8')).items():
            pv.setdefault(str(k), v)
pids = set()
for v in done.values():
    for k in ('h', 'a'):
        if v and k in v: pids.update(int(p) for p in v[k].get('st', []))
need = [p for p in pids if str(p) not in pv]
print(f'βασικοι {len(pids)} · ηδη {len(pids) - len(need)} · προς κατεβασμα {len(need)}', flush=True)
with ThreadPoolExecutor(max_workers=8) as ex:
    for i, (pid, rec) in enumerate(ex.map(L.player, need)):
        if rec: pv[str(pid)] = rec
        if (i + 1) % 1000 == 0:
            json.dump(pv, open(PVO, 'w', encoding='utf-8')); print(f'  αξιες {i + 1}/{len(need)}', flush=True)
json.dump(pv, open(PVO, 'w', encoding='utf-8'))
print(f'ΤΕΛΟΣ: αξιες {len(pv)} παικτες [{(time.time() - t0) / 60:.0f} λεπτα]', flush=True)
