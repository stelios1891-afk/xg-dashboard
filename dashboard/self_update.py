# -*- coding: utf-8 -*-
"""self_update.py — το dashboard ενημερωνεται ΜΟΝΟ ΤΟΥ απο το GitHub (3/11/2026, Στελιος: «πρεπει να βρουμε γιατι κολλαει,
δεν μπορω να κανω αυτο το πραγμα καθε τρεις και λιγο»).
Γιατι: το Streamlit Cloud σταματαει καπου-καπου να τραβαει τα νεα commits (31/10 στο main, 2/11 και 4/11 στο dashboard-live,
ενω το κλαδι ειναι φρεσκο) → «⚠ παλια δεδομενα» μεχρι Reboot. Η αιτια ειναι μεσα στο Streamlit (δεν φαινεται).
5/11/2026: η πρωτη εκδοχη (git fetch + reset) εβγαζε «ανενεργο» στο Cloud: το git εκει δεν ειναι αξιοπιστο. Τωρα ΧΩΡΙΣ git:
ενα νημα στο παρασκηνιο (ενα ανα διεργασια) καθε 4′ ζηταει απο το GitHub API τη λιστα αρχειων του dashboard-live, συγκρινει
με τον δισκο (hash οπως το git) και κατεβαζει ΜΟΝΟ οσα διαφερουν (ατομικο γραψιμο). Οι σελιδες διαβαζουν τα αρχεια απο τον
δισκο → φρεσκα στο επομενο ανοιγμα.
ΑΣΦΑΛΕΙΑ: τρεχει ΜΟΝΟ αν υπαρχει το σημαδι .dashboard_live (το βαζει το dash_slim.py μονο στο κλαδι) — στο laptop δεν αγγιζει τιποτα.
Token: GH_TOKEN (Streamlit secrets, ιδιο με το «✅ το έπαιξα»)· χωρις token δουλευει με το οριο 60 κλησεων/ωρα του GitHub.
STATUS: τελευταια κατασταση (φαινεται στη γραμμη «🕒 …» των σελιδων)."""
import os, sys, time, hashlib, threading, datetime
import requests

REPO = os.environ.get('GH_REPO_PLAYED', 'stelios1891-afk/xg-dashboard')
BRANCH = 'dashboard-live'
API = f'https://api.github.com/repos/{REPO}/git'
MARKER = '.dashboard_live'
EVERY_S = 240
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = 'dash-self-update'
# στο sys: το _reload_changed_modules ξαναφορτωνει αυτο το module, το νημα ομως μενει και γραφει στο ιδιο STATUS
STATUS = sys.__dict__.setdefault('_dash_self_update_status', {'state': 'δεν ξεκινησε'})
_HASHES = sys.__dict__.setdefault('_dash_self_update_hashes', {})   # path → (mtime, size, sha): να μη διαβαζει ολο τον δισκο καθε 4′


def _token():
    try:
        import streamlit as st
        t = st.secrets.get('GH_TOKEN')
        if t:
            return t
    except Exception:
        pass
    return os.environ.get('GH_TOKEN')


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def _blob_sha(data):
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def _local_sha(fn):
    try:
        s = os.stat(fn)
    except OSError:
        return None
    c = _HASHES.get(fn)
    if c and c[0] == s.st_mtime and c[1] == s.st_size:
        return c[2]
    with open(fn, 'rb') as fh:
        sha = _blob_sha(fh.read())
    _HASHES[fn] = (s.st_mtime, s.st_size, sha)
    return sha


def _write(fn, data):
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    tmp = f'{fn}.{os.getpid()}.tmp'
    with open(tmp, 'wb') as fh:
        fh.write(data)
    os.replace(tmp, fn)


def is_live_checkout(root=ROOT):
    """Μονο το αντιγραφο του dashboard-live (Streamlit Cloud) — ποτε το repo του laptop."""
    # 5/11: και οποιοδηποτε αντιγραφο στο Streamlit Cloud (/mount/src/…), ακομα κι αν το app τρεχει απο το main (χωρις σημαδι)
    return os.path.exists(os.path.join(root, MARKER)) or os.path.abspath(root).replace(os.sep, '/').startswith('/mount/src/')


def check_once(root=ROOT):
    """Ενας ελεγχος· γυριζει (και γραφει στο STATUS) τι εγινε."""
    STATUS['checked'] = _now()
    head = {'Accept': 'application/vnd.github+json'}
    tok = _token()
    if tok:
        head['Authorization'] = f'Bearer {tok}'
    try:
        r = requests.get(f'{API}/trees/{BRANCH}', params={'recursive': '1'}, headers=head, timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f'λιστα αρχειων: HTTP {r.status_code}')
        tree = r.json()
        if tree.get('truncated'):
            raise RuntimeError('λιστα αρχειων κομμενη')
        n = 0
        for x in tree.get('tree', []):
            p = x.get('path') or ''
            if x.get('type') != 'blob' or p.startswith('.git/') or '..' in p.split('/'):
                continue
            fn = os.path.join(root, *p.split('/'))
            if _local_sha(fn) == x['sha']:
                continue
            b = requests.get(f"{API}/blobs/{x['sha']}", headers={**head, 'Accept': 'application/vnd.github.raw+json'}, timeout=120)
            if b.status_code != 200:
                raise RuntimeError(f'{p}: HTTP {b.status_code}')
            if _blob_sha(b.content) != x['sha']:
                raise RuntimeError(f'{p}: λαθος περιεχομενο')
            _write(fn, b.content)
            n += 1
        STATUS.update(state='ενημερωθηκε' if n else 'ενημερο', files=n, err='', ok=_now())
        if n:
            STATUS['updated'] = _now()
    except Exception as e:
        msg = f'{type(e).__name__}: {e}'
        STATUS.update(state='σφαλμα', err=(msg.replace(tok, '***') if tok else msg)[:300])
    return STATUS


def _loop():
    while True:
        check_once()
        time.sleep(EVERY_S)


def start():
    """Ξεκιναει το νημα μια φορα ανα διεργασια (και μετα απο reload του module)."""
    if not is_live_checkout():
        STATUS['state'] = 'ανενεργο (οχι αντιγραφο dashboard-live)'
        return
    if any(t.name == NAME for t in threading.enumerate()):
        return
    STATUS['state'] = 'ξεκινησε'
    threading.Thread(target=_loop, name=NAME, daemon=True).start()


def active():
    return is_live_checkout()


def note():
    """Μια γραμμη για τη σελιδα."""
    s = STATUS
    if s.get('state') == 'σφαλμα':
        return f"αυτοματη ενημερωση: ΣΦΑΛΜΑ ({s.get('err', '')[:160]})"
    import gr_time
    return f"αυτοματη ενημερωση: {s.get('state')}" + (f" · ελεγχος {gr_time.stamp(s['ok'])[-5:]}" if s.get('ok') else '')
