"""fixtures_fetch_missing.py — 16/10/2026: ΠΡΟΓΡΑΜΜΑ & ΣΚΟΡ (χωρις σουτ) εγχωριων λιγκων για σεζον που λειπουν απο τα data_* (2021-22 σε 19 λιγκες,
2021 σε ημερολογιακες) — για το ημερολογιο ταξιδιων/κουρασης. Ξεχωριστα αρχεια fixtures_<λιγκα>_<σεζον>.json (ΔΕΝ αγγιζουμε τα data_*,
γιατι οι μηχανες βλεπουν «χωρις σουτ» ως λιγκα μονο-γκολ). Μορφη: {mid: {date, home{name,id}, away{name,id}, hs, as}}."""
import sys, json, os, time, urllib.parse
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
from discover import get
JOBS = {'CzechFirstLeague': 122, 'CroatiaHNL': 252, 'BulgariaFirstLeague': 270, 'CyprusFirstDivision': 136, 'SerbiaSuperLiga': 182,
        'UkrainePremierLeague': 441, 'IsraelLigatHaAl': 127, 'HungaryNBI': 212, 'SlovakiaNikeLiga': 176, 'RomaniaLigaI': 189,
        'SloveniaPrvaLiga': 173, 'AzerbaijanPremierLeague': 262, 'ArmeniaPremierLeague': 118, 'BosniaPremierLeague': 267,
        'AlbaniaKategoriaSuperiore': 260, 'GreeceSL': 135, 'TurkishSuperLig': 71, 'ScottishPrem': 64, 'Ekstraklasa': 196}
CAL = {'LithuaniaALyga': 228, 'GeorgiaErovnuliLiga': 439, 'KazakhstanPremierLeague': 225, 'FinlandVeikkausliiga': 51, 'LatviaVirsliga': 226}
tasks = [(lg, lid, '2021/2022', '2122') for lg, lid in JOBS.items()] + [(lg, lid, '2021', '2021') for lg, lid in CAL.items()]
for lg, lid, fs, sea in tasks:
    out = f'fixtures_{lg}_{sea}.json'
    if os.path.exists(out): print('ηδη', out); continue
    try:
        d = json.loads(get(f'https://www.fotmob.com/api/data/leagues?id={lid}&season={urllib.parse.quote(fs)}'))
    except Exception as e:
        print('ΑΠΟΤΥΧΙΑ', lg, fs, type(e).__name__); continue
    nm = (d.get('details') or {}).get('name')
    arr = (d.get('matches') or {}).get('allMatches') or (d.get('fixtures') or {}).get('allMatches') or []
    R = {}
    for m in arr:
        st = m.get('status') or {}
        sc = st.get('scoreStr') or ''
        hs = as_ = None
        if st.get('finished') and '-' in sc:
            try: hs, as_ = [int(x) for x in sc.replace(' ', '').split('-')]
            except Exception: pass
        R[str(m['id'])] = dict(date=st.get('utcTime') or m.get('utcTime'), home=dict(name=m['home']['name'], id=int(m['home']['id'])),
                               away=dict(name=m['away']['name'], id=int(m['away']['id'])), hs=hs, **{'as': as_})
    json.dump(R, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'{lg} {fs} («{nm}»): {len(R)} ματς, με σκορ {sum(1 for v in R.values() if v["hs"] is not None)}', flush=True)
    time.sleep(0.5)
