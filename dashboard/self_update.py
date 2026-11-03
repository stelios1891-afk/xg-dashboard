# -*- coding: utf-8 -*-
"""self_update.py — το dashboard ενημερωνεται ΜΟΝΟ ΤΟΥ απο το GitHub (3/11/2026, Στελιος: «πρεπει να βρουμε γιατι κολλαει,
δεν μπορω να κανω αυτο το πραγμα καθε τρεις και λιγο»).
Γιατι: το Streamlit Cloud σταματαει καπου-καπου να τραβαει τα νεα commits (31/10 στο main, 2/11 08:41 UTC στο dashboard-live,
ενω το κλαδι ειχε καθαρο, συνεχες ιστορικο) → «⚠ παλια δεδομενα» μεχρι Reboot. Η αιτια ειναι μεσα στο Streamlit (δεν φαινεται).
Τι κανει: ενα νημα στο παρασκηνιο (ενα ανα διεργασια) καθε 4′ ρωταει το GitHub ποιο ειναι το τελευταιο commit του κλαδιου
dashboard-live (ls-remote, φθηνο)· αν διαφερει απο το δικο μας → git fetch + git reset --hard (ιδιο αποτελεσμα με το «pull»
του Streamlit — μετα το δικο του pull βρισκει «τιποτα νεο»). Οι σελιδες διαβαζουν τα αρχεια απο τον δισκο → φρεσκα στο επομενο ανοιγμα.
ΑΣΦΑΛΕΙΑ: τρεχει ΜΟΝΟ αν το τρεχον commit ειναι του dashboard-live (μηνυμα «dashboard-live: …») — στο laptop (main) δεν αγγιζει τιποτα.
Token: GH_TOKEN (Streamlit secrets, ιδιο με το «✅ το έπαιξα»)· χωρις token → ο remote «origin».
STATUS: τελευταια κατασταση (εμφανιζεται διπλα στο «⚠ παλια δεδομενα»)."""
import os, time, threading, subprocess, datetime

REPO = os.environ.get('GH_REPO_PLAYED', 'stelios1891-afk/xg-dashboard')
BRANCH = 'dashboard-live'
EVERY_S = 240
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = 'dash-self-update'
STATUS = {'state': 'δεν ξεκινησε'}


def _token():
    try:
        import streamlit as st
        t = st.secrets.get('GH_TOKEN')
        if t:
            return t
    except Exception:
        pass
    return os.environ.get('GH_TOKEN')


def _git(root, *a, timeout=60):
    r = subprocess.run(['git', *a], cwd=root, capture_output=True, timeout=timeout,
                       env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).decode('utf-8', 'ignore').strip()[-300:])
    return r.stdout.decode('utf-8', 'ignore').strip()


def _clean(s, tok):
    return s.replace(tok, '***') if tok else s


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def is_live_checkout(root=ROOT):
    """Μονο το αντιγραφο του dashboard-live (Streamlit Cloud) — ποτε το repo του laptop."""
    try:
        return os.path.isdir(os.path.join(root, '.git')) and _git(root, 'log', '-1', '--format=%s').startswith('dashboard-live:')
    except Exception:
        return False


def check_once(root=ROOT):
    """Ενας ελεγχος· γυριζει (και γραφει στο STATUS) τι εγινε."""
    tok = _token()
    url = f'https://x-access-token:{tok}@github.com/{REPO}.git' if tok else 'origin'
    STATUS['checked'] = _now()
    try:
        out = _git(root, 'ls-remote', url, f'refs/heads/{BRANCH}', timeout=40)
        remote = out.split()[0] if out else ''
        local = _git(root, 'rev-parse', 'HEAD')
        if not remote:
            raise RuntimeError(f'το κλαδι {BRANCH} δεν βρεθηκε')
        if remote == local:
            STATUS.update(state='ενημερο', sha=local[:9], err='')
            return STATUS
        _git(root, 'fetch', '-q', '--no-tags', url, f'+refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}', timeout=180)
        lock = os.path.join(root, '.git', 'index.lock')          # κλειδαρια απο κολλημενο pull του Streamlit (>10′) → εκτος
        if os.path.exists(lock) and time.time() - os.path.getmtime(lock) > 600:
            os.remove(lock)
        _git(root, 'reset', '-q', '--hard', remote, timeout=120)
        STATUS.update(state='ενημερωθηκε', sha=remote[:9], updated=_now(), err='')
    except Exception as e:
        STATUS.update(state='σφαλμα', err=_clean(f'{type(e).__name__}: {e}', tok)[:300])
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


def note():
    """Μια γραμμη για τη σελιδα."""
    s = STATUS
    if s.get('state') == 'σφαλμα':
        return f"αυτοματη ενημερωση: ΣΦΑΛΜΑ ({s.get('err', '')[:160]})"
    return f"αυτοματη ενημερωση: {s.get('state')}" + (f" · commit {s['sha']}" if s.get('sha') else '')
