# -*- coding: utf-8 -*-
"""played_store.py — «✅ το έπαιξα» ΚΟΙΝΟ σε ολες τις συσκευες (12/10/2026, Στελιος: «να εμφανιζεται σε ολες τις συσκευες οταν το παταω»).
Αποθηκευση: αρχειο played_picks.json στο repo (GitHub contents API) = {κλειδι καρτας: χρονος σε ms}. Κλειδι = data-k της καρτας Value Picks
(λιγκα|γηπ|φιλ|αγορα|πλευρα|μερα). Χρειαζεται GitHub token με δικαιωμα Contents read/write στο repo: Streamlit secrets «GH_TOKEN»
(ή μεταβλητη περιβαλλοντος GH_TOKEN). Χωρις token → None (η σελιδα γυριζει στη μνημη του browser, οπως πριν).
Εγγραφες παλιοτερες απο 14 μερες σβηνονται σε καθε αποθηκευση."""
import os, json, time, base64
import requests

REPO = os.environ.get('GH_REPO_PLAYED', 'stelios1891-afk/xg-dashboard')
PATH = 'played_picks.json'
API = f'https://api.github.com/repos/{REPO}/contents/{PATH}'
KEEP_MS = 14 * 86400 * 1000
LAST_ERR = ''          # 13/10: τι απαντησε το GitHub στο τελευταιο σφαλμα (εμφανιζεται στη σελιδα)


def _token():
    try:
        import streamlit as st
        t = st.secrets.get('GH_TOKEN')
        if t:
            return t
    except Exception:
        pass
    return os.environ.get('GH_TOKEN')


FAKE = os.environ.get('PLAYED_FAKE')        # τοπικη δοκιμη: τοπικο αρχειο αντι για GitHub


def enabled():
    return bool(FAKE) or bool(_token())


def _get():
    t = _token()
    if not t:
        return None, None
    global LAST_ERR
    r = requests.get(API, headers={'Authorization': f'Bearer {t}', 'Accept': 'application/vnd.github+json'}, params={'ref': 'main'}, timeout=15)
    if r.status_code == 404:
        return {}, None
    if r.status_code != 200:
        LAST_ERR = f'ανάγνωση HTTP {r.status_code}: {r.text[:160]}'
    r.raise_for_status()
    j = r.json()
    try:
        data = json.loads(base64.b64decode(j.get('content') or b'').decode('utf-8') or '{}')
    except Exception:
        data = {}
    return data, j.get('sha')


def load():
    """→ dict {κλειδι: ms} ή None (χωρις token / σφαλμα)."""
    if FAKE:
        try: return json.load(open(FAKE, encoding='utf-8'))
        except Exception: return {}
    try:
        d, _ = _get()
        return d
    except Exception:
        return None


def toggle(key, on, tries=3):
    """Σημειωνει/ξεσημειωνει ενα pick. → νεο dict ή None αν απετυχε."""
    global LAST_ERR
    LAST_ERR = ''
    if FAKE and key:
        d = load(); d = dict(d or {})
        if on: d[key] = int(time.time() * 1000)
        else: d.pop(key, None)
        json.dump(d, open(FAKE, 'w', encoding='utf-8'), ensure_ascii=False); return d
    t = _token()
    if not t or not key:
        return None
    for _ in range(tries):
        try:
            data, sha = _get()
            data = dict(data or {})
            now = int(time.time() * 1000)
            data = {k: v for k, v in data.items() if now - int(v or 0) <= KEEP_MS}
            if on:
                data[key] = now
            else:
                data.pop(key, None)
            body = {'message': f'played: {"+" if on else "−"} {key[:60]} [skip ci]', 'branch': 'main',
                    'content': base64.b64encode(json.dumps(data, ensure_ascii=False, indent=0).encode('utf-8')).decode()}
            if sha:
                body['sha'] = sha
            r = requests.put(API, headers={'Authorization': f'Bearer {t}', 'Accept': 'application/vnd.github+json'}, json=body, timeout=20)
            if r.status_code in (200, 201):
                return data
            if r.status_code == 409:          # αλλαξε στο μεταξυ (αλλη συσκευη / scanner) → ξαναδιαβαζω
                continue
            LAST_ERR = f'εγγραφή HTTP {r.status_code}: {r.text[:160]}'
            return None
        except Exception as e:
            if not LAST_ERR:
                LAST_ERR = f'{type(e).__name__}: {str(e)[:160]}'
            time.sleep(1)
    return None
