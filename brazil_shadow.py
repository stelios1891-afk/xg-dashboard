# -*- coding: utf-8 -*-
"""brazil_shadow.py — ΣΚΙΩΔΗΣ καταγραφη picks Βραζιλιας (Serie A, 2026) — ΟΧΙ Telegram, ΟΧΙ live.

Ο ΑΚΡΙΒΗΣ μηχανισμος του expansion_test (3/9/2026, Βραζιλια pooled +5.9%, 3/4 σεζον):
- ΚΑΘΑΡΟ in-season: rolling ratings (DECAY 0.96 μεσω picks.wmean), blend_at(n), προβλεψη
  ΜΟΝΟ οταν και οι 2 ομαδες εχουν >= 14 φετινα ματς (MIN_N=14 ΤΟΠΙΚΑ — οχι picks.MIN_PRIOR,
  που στο cloud ειναι 6).
- Inputs: ιδιος ορισμος ns_eff/xg_model (compression + pen 0.25 + red adj + running rescale).
- Χαρακας: running μεσοι σεζον. HFA=1.17 (LOSO ευρος 1.156-1.181 του τεστ). SoS ανενεργο.
- Picks: picks.evaluate_bet/settle ως εχουν. Αποδοσεις: TOA live (soccer_brazil_campeonato,
  Pinnacle spreads, ~1 credit) — καλειται ΜΟΝΟ αν υπαρχουν ματς στις επομενες 4 μερες.
Εξοδος: brazil_shadow.jsonl (append σε αλλαγη, state: brazil_shadow_state.json).
Αξιολογηση: με τα αποτελεσματα του brazil_refresh οταν κριθουν (δες shadow_report λογικη).
"""
import sys, os, json, re, datetime, unicodedata
import urllib.request, gzip
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import picks

SEASON = '2026'
MIN_N = 14
HFA_BR = 1.17
HORIZON_DAYS = 4
OUT = 'brazil_shadow.jsonl'
STATE_F = 'brazil_shadow_state.json'
SPORT = 'soccer_brazil_campeonato'
ALIAS_BR = {'Atletico MG': 'Atletico Mineiro', 'Atletico GO': 'Atletico Goianiense',
            'America MG': 'America Mineiro', 'Red Bull Bragantino': 'Bragantino',
            'Botafogo RJ': 'Botafogo', 'Chapecoense AF': 'Chapecoense', 'Santos FC': 'Santos',
            # ονοματα του fixtures endpoint (διαφερουν απο τα match-data ονοματα)
            'RB Bragantino': 'Bragantino', 'Atlético-MG': 'Atletico Mineiro',
            'Atlético-GO': 'Atletico Goianiense', 'América-MG': 'America Mineiro',
            'São Paulo': 'Sao Paulo'}

HDR = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Referer': 'https://www.fotmob.com/'}


def fot(url):
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30).read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)


def wcomp(xg):
    if xg <= 0.2: return 1.00
    if xg <= 0.4: return 0.45
    if xg <= 0.5: return 0.25
    if xg <= 0.7: return 0.15
    return 0.05


def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return frozenset(re.findall(r'[a-z]{3,}', s)) - {'the'}


def build_hist():
    """Rolling hist ανα ομαδα απο data_Brazil_2026 (ιδιοι ορισμοι με expansion_test)."""
    d = json.load(open(f'data_Brazil_{SEASON}.json', encoding='utf-8'))
    rows = []
    for mid, m in d.items():
        if m['hs'] is None or m['as'] is None or not m['shots']:
            continue
        try:
            dt = datetime.datetime.strptime(m['date'].replace(' UTC', ''), '%a, %b %d, %Y, %H:%M')
        except Exception:
            continue
        hid = int(m['home']['id']); aid = int(m['away']['id'])
        agg = {hid: dict(raw=0.0, comp=0.0, pen=0, ns=0), aid: dict(raw=0.0, comp=0.0, pen=0, ns=0)}
        for s in m['shots']:
            xg = s.get('xg'); tid = s.get('tid')
            if xg is None or tid not in agg:
                continue
            if s.get('sit') == 'Penalty':
                agg[tid]['pen'] += 1
            else:
                agg[tid]['raw'] += xg; agg[tid]['comp'] += xg * wcomp(xg); agg[tid]['ns'] += 1
        ft = 95; dh = da = 0.0
        for r in m.get('reds', []):
            dur = max(0, ft - (r.get('min') or 0))
            if r['home']: dh += dur
            else: da += dur
        for is_home, tid, opp, gf, ds, do in [(1, hid, aid, m['hs'], dh, da),
                                              (0, aid, hid, m['as'], da, dh)]:
            a = agg[tid]
            red_xg = 0.0083 * do - 0.5 * 0.0083 * ds
            rows.append(dict(dt=dt, team=tid, opp=opp, is_home=is_home, gf=gf,
                             raw=a['raw'], comp=a['comp'], pen=a['pen'], ns=a['ns'], red=red_xg))
    rows.sort(key=lambda r: r['dt'])
    sf_num = sum(r['raw'] for r in rows); sf_den = sum(r['comp'] for r in rows)
    sf = sf_num / max(sf_den, 1e-9)                     # running rescale ολης της σεζον ως τωρα
    hist = {}
    tot_ns = 0.0; tot_xg = 0.0; nrows = 0
    bymatch = {}
    for r in rows:
        bymatch.setdefault((r['dt'], r['team'], r['opp']), r)
    for r in rows:
        xg_model = r['comp'] * sf + 0.25 * r['pen'] + r['red']
        ns_eff = r['ns'] + r['pen'] + abs(r['red']) / 0.10
        opp_r = bymatch.get((r['dt'], r['opp'], r['team']))
        if opp_r is None:
            continue
        xa_model = opp_r['comp'] * sf + 0.25 * opp_r['pen'] + opp_r['red']
        sa_eff = opp_r['ns'] + opp_r['pen'] + abs(opp_r['red']) / 0.10
        h = hist.setdefault(r['team'], dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[], opp=[]))
        h['sf'].append(ns_eff); h['xf'].append(xg_model)
        h['sa'].append(sa_eff); h['xa'].append(xa_model)
        h['gf'].append(r['gf']); h['ga'].append(opp_r['gf']); h['opp'].append(r['opp'])
        tot_ns += ns_eff; tot_xg += xg_model; nrows += 1
    lg_shots = tot_ns / max(nrows, 1)
    lg_xgps = tot_xg / max(tot_ns, 1e-9)
    return hist, lg_shots, lg_xgps


def upcoming():
    d = fot(f'https://www.fotmob.com/api/data/leagues?id=268&season={SEASON}')
    arr = (d.get('matches', {}).get('allMatches') or d.get('fixtures', {}).get('allMatches') or [])
    now = datetime.datetime.now(datetime.timezone.utc)
    out = []
    for m in arr:
        st = m.get('status', {})
        if st.get('finished') or st.get('cancelled'):
            continue
        ut = st.get('utcTime') or m.get('utcTime')
        try:
            ko = datetime.datetime.fromisoformat(str(ut).replace('Z', '+00:00'))
        except Exception:
            continue
        if now < ko <= now + datetime.timedelta(days=HORIZON_DAYS):
            out.append(dict(fid=m.get('id'), ko=ko,
                            hid=int(m['home']['id']), aid=int(m['away']['id']),
                            home=m['home'].get('name'), away=m['away'].get('name')))
    return out


def toa_events():
    key = os.environ.get('TOA_KEY')
    if not key:
        print('brazil_shadow: TOA_KEY λειπει — dry run (μονο μοντελο).')
        return None
    import requests
    r = requests.get(f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds',
                     params=dict(apiKey=key, regions='eu', markets='spreads',
                                 bookmakers='pinnacle', oddsFormat='decimal'), timeout=40)
    if r.status_code != 200:
        print(f'brazil_shadow: TOA HTTP {r.status_code}')
        return None
    return r.json()


def event_odds(events, home, away, ko):
    """Καλυτερο ταιριασμα (οχι πρωτο-τυχαιο): score = overlap και στις 2 πλευρες + jaccard."""
    th = norm(ALIAS_BR.get(home, home)); ta = norm(ALIAS_BR.get(away, away))
    best = None
    for e in events or []:
        try:
            ct = datetime.datetime.fromisoformat(e['commence_time'].replace('Z', '+00:00'))
        except Exception:
            continue
        if abs((ct - ko).total_seconds()) > 6 * 3600:
            continue
        eh, ea = norm(e['home_team']), norm(e['away_team'])
        ovh, ova = len(th & eh), len(ta & ea)
        if ovh == 0 or ova == 0:
            continue
        jac = ovh / max(len(th | eh), 1) + ova / max(len(ta | ea), 1)
        score = (ovh + ova, jac)
        if best is None or score > best[0]:
            best = (score, e)
    if best is None:
        return None
    e = best[1]
    for b in e.get('bookmakers', []):
        if b.get('key') != 'pinnacle':
            continue
        for mk in b.get('markets', []):
            if mk.get('key') != 'spreads' or len(mk.get('outcomes', [])) != 2:
                continue
            o1, o2 = mk['outcomes']
            if norm(o1['name']) & norm(e['home_team']):
                return float(o1['point']), float(o1['price']), float(o2['price'])
            return float(o2['point']), float(o2['price']), float(o1['price'])
    return None


if __name__ == '__main__':
    fx = upcoming()
    if not fx:
        print('brazil_shadow: κανενα ματς στο παραθυρο — 0 credits.')
        raise SystemExit(0)
    hist, lg_shots, lg_xgps = build_hist()
    ready = [f for f in fx if len(hist.get(f['hid'], {}).get('sf', [])) >= MIN_N
             and len(hist.get(f['aid'], {}).get('sf', [])) >= MIN_N]
    if not ready:
        print(f'brazil_shadow: {len(fx)} ματς αλλα καμια πλευρα με n>={MIN_N} — skip.')
        raise SystemExit(0)
    ev = toa_events()
    try:
        state = json.load(open(STATE_F, encoding='utf-8'))
    except Exception:
        state = {}
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='minutes')
    n_new = 0
    with open(OUT, 'a', encoding='utf-8') as fh:
        for f in ready:
            xh, xa = picks.predict(hist[f['hid']], hist[f['aid']], lg_shots, lg_xgps, HFA_BR)
            xh = min(max(xh, 0.05), 6.0); xa = min(max(xa, 0.05), 6.0)
            o = event_odds(ev, f['home'], f['away'], f['ko']) if ev else None
            rec = dict(t=ts, fid=f['fid'], hid=f['hid'], aid=f['aid'],
                       home=f['home'], away=f['away'], ko=f['ko'].isoformat(),
                       nh=len(hist[f['hid']]['sf']), na=len(hist[f['aid']]['sf']),
                       xh=round(xh, 3), xa=round(xa, 3))
            if o:
                line, oh, oa = o
                rec.update(line=line, oh=oh, oa=oa)
                bs = picks.evaluate_bet(xh, xa, line, oh, oa)
                rec['picks'] = [dict(side=b['side'], hcap=b['hcap'], odds=b['odds'],
                                     edge=round(b['edge'], 4)) for b in bs]
            key = f"{f['hid']}_{f['aid']}"
            sig = [rec.get('line'), rec.get('oh'), rec.get('oa'), rec['xh'], rec['xa']]
            if state.get(key) == sig:
                continue
            state[key] = sig
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
            n_new += 1
    with open(STATE_F, 'w', encoding='utf-8') as fh:
        json.dump(state, fh)
    print(f'brazil_shadow: {n_new} νεες εγγραφες / {len(ready)} ετοιμα ματς ({ts})')
