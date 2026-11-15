"""weather_fetch_common.py — κοινα βοηθητικα για τα fetch καιρου (Open-Meteo με ορια, ημερομηνιες FotMob)."""
import os, json, gzip, time, urllib.request, urllib.error
LG = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
CD = 'weather_cache'; os.makedirs(CD, exist_ok=True)
def day_of(fotmob_date):
    return time.strftime('%Y-%m-%d', time.strptime(fotmob_date.replace(' UTC', ''), '%a, %b %d, %Y, %H:%M'))
def get(u, hdr=None, tries=8):
    hdr = hdr or {'User-Agent': 'Mozilla/5.0'}
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=hdr), timeout=60).read()
            return json.loads(gzip.decompress(r) if r[:2] == b'\x1f\x8b' else r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                w = 65 if i < 2 else 900
                print(f'  429 (ορια) — αναμονη {w}s', flush=True); time.sleep(w); continue
            if i == tries - 1: raise
            time.sleep(2 + 2 * i)
        except Exception:
            if i == tries - 1: raise
            time.sleep(2 + 2 * i)
    raise RuntimeError('429 επιμενει')
def save(u, f, days):
    """κατεβαζει, κραταει μονο τις μερες των ματς· False = σταματα (ορια)."""
    try:
        x = get(u); hh = x['hourly']; keep = [i for i, tm in enumerate(hh['time']) if tm[:10] in days]
        json.dump({k: [v[i] for i in keep] for k, v in hh.items()}, open(f, 'w', encoding='utf-8'))
        time.sleep(0.3); return True
    except Exception as e:
        print('  σφαλμα', os.path.basename(f), str(e)[:80], flush=True)
        return 'επιμενει' not in str(e)
