"""southam_cups_fetch.py — 5/10/2026: προγραμμα ΚΥΠΕΛΛΩΝ/ηπειρωτικων (FotMob, μονο λιστα ματς) για κουραση/rotation Βραζιλιας & MLS.
→ southam_cups.json [{comp, utc, hid, aid, home, away, round}] · Libertadores 45, Sudamericana 299, Copa do Brasil 9067,
  Leagues Cup 10043, CONCACAF Champions Cup 297, US Open Cup 9441, Club World Cup (78 αν υπαρχει)."""
import urllib.request, gzip, json, time, sys
sys.stdout.reconfigure(encoding='utf-8')
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36', 'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}
def get(u):
    r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=30).read()
    return json.loads(gzip.decompress(r) if r[:2] == b'\x1f\x8b' else r)
COMPS = {'Libertadores': 45, 'Sudamericana': 299, 'CopaDoBrasil': 9067, 'LeaguesCup': 10043, 'ConcacafCC': 297, 'USOpenCup': 9441, 'ClubWorldCup': 78}
out = []
for comp, lid in COMPS.items():
    try:
        seas = get(f'https://www.fotmob.com/api/data/leagues?id={lid}').get('allAvailableSeasons') or []
    except Exception as e:
        print(comp, 'ERR', e); continue
    for s in seas:
        if not any(y in s for y in ('2021', '2022', '2023', '2024', '2025', '2026')): continue
        try:
            d = get(f'https://www.fotmob.com/api/data/leagues?id={lid}&season={s.replace("/", "%2F")}')
        except Exception as e:
            print(comp, s, 'ERR', e); continue
        n = 0
        for m in d.get('fixtures', {}).get('allMatches', []):
            st = m.get('status', {})
            if st.get('cancelled'): continue
            out.append(dict(comp=comp, season=s, utc=st.get('utcTime'), hid=int(m['home']['id']), aid=int(m['away']['id']),
                            home=m['home'].get('name'), away=m['away'].get('name'), round=str(m.get('roundName') or m.get('round') or '')))
            n += 1
        print(comp, s, n, flush=True); time.sleep(0.4)
json.dump(out, open('southam_cups.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('συνολο', len(out))
