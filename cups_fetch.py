# -*- coding: utf-8 -*-
"""
cups_fetch.py -- domestic cups / league cups / super cups (countries with European-competition teams) from FotMob.

Per cup: leagues?id=ID (no season) -> allAvailableSeasons, then leagues?id=ID&season=LABEL for every
label whose start year is within 2021..2026.  Key: Country_Cup_<season code from FotMob label>
(split-year label 2024/2025 -> 2425, calendar label 2025 -> 2025).
NOTE: FotMob puts Super Cups under the PREVIOUS season label (they are played in August) -> use utc, not the label.
Value: list of dicts mid, utc, hid, hname, aid, aname, score, round, finished  (score empty if not played).
Cache/resume: keys already in cups_fixtures.json are not downloaded again.
    python cups_fetch.py            # resume
    python cups_fetch.py --refresh  # also re-download keys that still have unfinished matches (current season)
Outputs: cups_fixtures.json, cups_fetch.log
"""
import sys, os, json, time, threading
from concurrent.futures import ThreadPoolExecutor
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from discover import get

CUPS = {
    'England': {'FACup': 132, 'EFLCup': 133, 'CommunityShield': 247, 'EFLCupQual': 12889},
    'Spain': {'CopaDelRey': 138, 'Supercopa': 139},
    'Italy': {'CoppaItalia': 141, 'Supercoppa': 222},
    'Germany': {'DFBPokal': 209, 'SuperCup': 8924},
    'France': {'CoupeDeFrance': 134, 'TropheeDesChampions': 207},
    'Portugal': {'TacaDePortugal': 186, 'TacaDaLiga': 187, 'SuperCup': 188},
    'Netherlands': {'KNVBBeker': 235, 'SuperCup': 237, 'SuperCupB': 11029},
    'Belgium': {'BelgianCup': 149, 'SuperCup': 266},
    'Scotland': {'ScottishCup': 137, 'LeagueCup': 180},
    'Turkey': {'TurkishCup': 151, 'SuperCup': 166},
    'Greece': {'GreekCup': 145, 'SuperCup': 8816},
    'Czechia': {'CzechCup': 254},
    'Austria': {'OFBCup': 278},
    'Switzerland': {'SwissCup': 164},
    'Denmark': {'DBUPokalen': 242},
    'Norway': {'Norgesmesterskapet': 206},
    'Sweden': {'SvenskaCupen': 171},
    'Finland': {'SuomenCup': 143, 'FinlandLeagueCup': 342},
    'Iceland': {'IcelandicCup': 217, 'LeagueCup': 10076, 'SuperCup': 10009},
    'Poland': {'PucharPolski': 198, 'Superpuchar': 200},
    'Hungary': {'MagyarKupa': 213},
    'Romania': {'CupaRomaniei': 190, 'Supercupa': 192},
    'Bulgaria': {'BulgarianCup': 271, 'SuperCup': 272},
    'Croatia': {'CroatianCup': 275, 'SuperCup': 276},
    'Serbia': {'KupSrbije': 183},
    'Slovakia': {'SlovakCup': 177},
    'Slovenia': {'SloveniaCup': 174},
    'Cyprus': {'CyprusCup': 330, 'SuperCup': 521},
    'Israel': {'StateCup': 9097, 'SuperCup': 9862},
    'Ireland': {'FAICup': 219, 'SuperCup': 9431},
    'NorthernIreland': {'IrishCup': 9389, 'LeagueCup': 8978},
    'Wales': {'WelshCup': 9166},
    'Ukraine': {'UkraineCup': 442},
    'Russia': {'RussianCup': 193, 'SuperCup': 195},
    'Belarus': {'BelarusianCup': 9521, 'SuperCup': 9658},
    'Moldova': {'CupaMoldova': 9530},
    'NorthMacedonia': {'MacedonianCup': 9528},
    'Luxembourg': {'CoupeDeLuxembourg': 9527},
    'FaroeIslands': {'Logmanssteypid': 9523},
    'Albania': {'SuperCup': 10175},
    'Armenia': {'SuperCup': 490},
    'Kazakhstan': {'SuperCup': 9504},
    'Estonia': {'SuperCup': 9069},
    'Latvia': {'SuperCup': 9486},
    'Lithuania': {'SuperCup': 9493},
}
FIX = 'cups_fixtures.json'
LOG = 'cups_fetch.log'
WORKERS = 5
Y0, Y1 = 2021, 2026
lock = threading.Lock()


def log(msg):
    line = time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + msg
    with lock:
        print(line, flush=True)
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')


def jget(url, tries=4):
    for i in range(tries):
        try:
            time.sleep(0.25)
            r = json.loads(get(url))
            if not isinstance(r, dict):
                raise ValueError('non-dict JSON: %r' % (r,))
            return r
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(2.0 * (i + 1))


def label_code(lab):
    if '/' in lab:
        a, b = lab.split('/')
        return a[2:] + b[2:], int(a)
    return lab, int(lab)


def parse_rows(d):
    rows = []
    for m in d.get('fixtures', {}).get('allMatches', []):
        st = m.get('status', {})
        if st.get('cancelled'):
            continue
        rows.append(dict(mid=str(m['id']), utc=st.get('utcTime', ''),
                         hid=int(m['home']['id']), hname=m['home']['name'],
                         aid=int(m['away']['id']), aname=m['away']['name'],
                         score=st.get('scoreStr', '') if st.get('finished') else '',
                         round=str(m.get('round', '')),
                         finished=bool(st.get('finished'))))
    rows.sort(key=lambda r: (r['utc'], r['mid']))
    return rows


def main():
    refresh = '--refresh' in sys.argv
    store = json.load(open(FIX, encoding='utf-8')) if os.path.exists(FIX) else {}
    jobs = [(c, cup, lid) for c, cups in CUPS.items() for cup, lid in cups.items()]
    errors = []

    def save():
        with lock:
            for i in range(8):
                try:
                    tmp = FIX + '.tmp'
                    with open(tmp, 'w', encoding='utf-8') as f:
                        json.dump(store, f, ensure_ascii=False)
                    os.replace(tmp, FIX)
                    break
                except OSError:
                    time.sleep(1.0 + i)
            else:
                with open(FIX, 'w', encoding='utf-8') as f:
                    json.dump(store, f, ensure_ascii=False)

    def work(job):
        try:
            work_inner(job)
        except Exception as e:
            log('%s: UNEXPECTED %s: %s' % (job, type(e).__name__, e))
            errors.append((job, 'unexpected', str(e)))

    def work_inner(job):
        c, cup, lid = job
        try:
            d0 = jget('https://www.fotmob.com/api/data/leagues?id=%d' % lid)
        except Exception as e:
            log('%s_%s (id %d): ERROR seasons %s: %s' % (c, cup, lid, type(e).__name__, e))
            errors.append((c, cup, lid, 'seasons', str(e)))
            return
        labs = d0.get('allAvailableSeasons') or []
        sel = d0.get('details', {}).get('selectedSeason')
        log('%s_%s (id %d, %s): seasons %s' % (c, cup, lid, d0.get('details', {}).get('name'), labs[:9]))
        for lab in labs:
            try:
                code, y = label_code(lab)
            except Exception:
                continue
            if not (Y0 <= y <= Y1):
                continue
            key = '%s_%s_%s' % (c, cup, code)
            old = store.get(key)
            if old is not None and not (refresh and any(not r['finished'] for r in old)):
                continue
            try:
                if lab == sel:
                    d = d0
                else:
                    d = jget('https://www.fotmob.com/api/data/leagues?id=%d&season=%s' % (lid, lab.replace('/', '%2F')))
            except Exception as e:
                log('%s: ERROR %s: %s' % (key, type(e).__name__, e))
                errors.append((c, cup, lid, lab, str(e)))
                continue
            rows = parse_rows(d)
            with lock:
                store[key] = rows
            save()
            log('%s: %d matches, finished %d, %s -> %s' % (
                key, len(rows), sum(r['finished'] for r in rows),
                rows[0]['utc'][:10] if rows else '-', rows[-1]['utc'][:10] if rows else '-'))

    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(work, jobs))
    save()
    log('DONE keys %d matches %d errors %d' % (len(store), sum(len(v) for v in store.values()), len(errors)))
    for e in errors:
        log('  ERR %s' % (e,))


if __name__ == '__main__':
    main()
