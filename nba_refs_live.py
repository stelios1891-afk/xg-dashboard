# -*- coding: utf-8 -*-
"""nba_refs_live.py — ΔΙΑΙΤΗΤΕΣ NBA ΤΗΣ ΗΜΕΡΑΣ (21/10/2026, Στελιος «τους διαιτητες σε σκια»).
Πηγη: official.nba.com/referee-assignments/ (βγαινει ~9πμ ET τη μερα του ματς· μονο τα σημερινα ματς). Ο ESPN ΔΕΝ τους δειχνει πριν το ματς.
Cache: nba_refs_live.json (ξανα-κατεβαζει το πολυ 1 φορα/60′). crew(home, away) → μεσος δεικτης τριαδας (nba_totals_extra_shadow.json,
t47: μεσο πραγμ − αγορα στα 60 τελευταια ματς του διαιτητη × n/(n+40)) με ≥2 γνωστους, αλλιως None."""
import os, re, json, datetime as dt
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
URL = 'https://official.nba.com/referee-assignments/'
CACHE = 'nba_refs_live.json'
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'}
NICK = {'L.A. Lakers': 'Los Angeles Lakers', 'LA Lakers': 'Los Angeles Lakers', 'L.A. Clippers': 'Los Angeles Clippers', 'LA Clippers': 'Los Angeles Clippers'}

def _load(fn, d):
    try: return json.load(open(F(fn), encoding='utf-8'))
    except Exception: return d

def fetch(now=None, max_age_min=60):
    """→ {'t': ..., 'games': [{'away', 'home', 'refs': [...]}]} (απο cache αν ειναι φρεσκο)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    C = _load(CACHE, {})
    try:
        if C.get('t') and (now - dt.datetime.fromisoformat(C['t'])).total_seconds() < max_age_min * 60: return C
    except Exception: pass
    import urllib.request
    try:
        t = urllib.request.urlopen(urllib.request.Request(URL, headers=H), timeout=30).read().decode('utf-8', 'ignore')
    except Exception as e:
        print('διαιτητες NBA: σφαλμα', str(e)[:80]); return C
    G = []
    for r in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
        c = [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', x)).strip() for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)]
        if len(c) < 4 or ' @ ' not in c[0]: continue
        a, h = [s.strip() for s in c[0].split(' @ ', 1)]
        refs = [re.sub(r'\s*\(#\d+\)\s*$', '', x).strip() for x in c[1:4] if x.strip()]
        G.append(dict(away=a, home=h, refs=refs))
    C = dict(t=now.isoformat(timespec='minutes'), games=G)
    json.dump(C, open(F(CACHE), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return C

def _same(short, full):
    short = NICK.get(short, short)
    return full == short or full.startswith(short + ' ')

def crew(home, away, now=None):
    """(δεικτης τριαδας, ονοματα) ή (None, ονοματα/[]) — home/away = πληρη ονοματα (π.χ. 'Denver Nuggets')."""
    C = fetch(now); J = _load('nba_totals_extra_shadow.json', {}); I = J.get('ref_index') or {}
    for g in C.get('games', []):
        if _same(g['home'], home) and _same(g['away'], away):
            v = [I[n]['v'] for n in g['refs'] if n in I]
            return (round(sum(v) / len(v), 3) if len(v) >= 2 else None), g['refs']
    return None, []

if __name__ == '__main__':
    import sys; sys.stdout.reconfigure(encoding='utf-8')
    C = fetch(max_age_min=0); J = _load('nba_totals_extra_shadow.json', {}); I = J.get('ref_index') or {}
    for g in C['games']:
        print(f"{g['away']} @ {g['home']}: " + ', '.join(f"{n} {I[n]['v']:+.1f}" if n in I else f'{n} (;)' for n in g['refs']))
