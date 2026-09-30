# -*- coding: utf-8 -*-
"""el_coach_live.py — ΑΛΛΑΓΗ ΠΡΟΠΟΝΗΤΗ μεσα στη σεζον: ΣΗΜΕΙΩΣΗ στα picks (1/10/2026, Στελιος «προσθεσε σημειωση οταν αλλαζει ο προπονητης»).
ΜΟΝΟ ενδειξη — δεν αλλαζει το μοντελο ουτε ποια picks παιζονται. el_coach_change_test.py (51 αλλαγες 2017-25, 28 με αγορα):
  πριν την αλλαγη η ομαδα −3.6 vs μοντελο· μετα: 1-3 ματς ~0, 4-10 +2 (οχι σταθερο, 3/5 σεζον)· το μοντελο εκτιμα την ομαδα ΛΙΓΟ ΠΕΡΙΣΣΟΤΕΡΟ
  απο την αγορα (+0.4…+0.8)· picks ΥΠΕΡ της στα 10 ματς μετα +35.6% (78, 5/5 σεζον) · ΚΑΤΑ +4.8% (53, αρνητικα 4/5).
Πηγη: επισημο API v2 .../seasons/{SEASON}/clubs/{club}/people (τυπος 'E' = πρωτος προπονητης, startDate).
Αλλαγη = προπονητης με εναρξη ΜΕΤΑ την πρεμιερα· αλλαγες της ιδιας ομαδας σε ≤14 μερες (υπηρεσιακος → μονιμος) = μια, ημερομηνια η πρωτη.
Σημειωση για τα ΕΠΟΜΕΝΑ 10 ματς Ευρωλιγκας της ομαδας μετα την αλλαγη."""
import json, datetime as dt
import requests
H = {'User-Agent': 'Mozilla/5.0'}
WINDOW = 10
def changes(season, sched, timeout=30):
    """{club: dict(date='YYYY-MM-DD', name=νεος προπονητης)} — η τελευταια αλλαγη καθε ομαδας μεσα στη σεζον."""
    if not sched: return {}
    d0 = min(x['utc'][:10] for x in sched); out = {}
    for c in sorted({x['hcode'] for x in sched} | {x['acode'] for x in sched}):
        try:
            L = requests.get(f'https://api-live.euroleague.net/v2/competitions/E/seasons/{season}/clubs/{c}/people', headers=H, timeout=timeout).json()
            L = L.get('data', L) if isinstance(L, dict) else L
        except Exception:
            continue
        co = sorted([((p.get('startDate') or '')[:10], (p.get('person') or {}).get('name', '')) for p in L if p.get('type') == 'E' and (p.get('startDate') or '')[:10] > d0])
        grp = []
        for d, n in co:
            if grp and (dt.date.fromisoformat(d) - dt.date.fromisoformat(grp[-1][-1][0])).days <= 14: grp[-1].append((d, n))
            else: grp.append([(d, n)])
        if grp: out[c] = dict(date=grp[-1][0][0], name=grp[-1][-1][1])
    return out
def notes(sched, ch):
    """{game code: [σημειωση, ...]} για ματς εως WINDOW μετα την αλλαγη προπονητη καθε ομαδας."""
    res = {}
    S = sorted(sched, key=lambda x: x['utc'])
    for c, info in ch.items():
        n = 0
        for x in S:
            if c not in (x['hcode'], x['acode']) or x['utc'][:10] < info['date']: continue
            n += 1
            if n > WINDOW: break
            team = x['home'] if x['hcode'] == c else x['away']
            dd = dt.date.fromisoformat(info['date'])
            res.setdefault(x['code'], []).append(
                f"🔄 νεος προπονητης {team}: {info['name'].title()} (απο {dd:%d/%m}) · {n}ο ματς — ιστορικα picks ΥΠΕΡ της +36% (78) / ΚΑΤΑ +5% (53)· μονο ενδειξη")
    return res
