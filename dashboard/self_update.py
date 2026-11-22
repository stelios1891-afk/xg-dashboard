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
import os, sys, time, json, base64, shutil, hashlib, threading, datetime
import requests

REPO = os.environ.get('GH_REPO_PLAYED', 'stelios1891-afk/xg-dashboard')
BRANCH = 'dashboard-live'
API = f'https://api.github.com/repos/{REPO}/git'
MARKER = '.dashboard_live'
EVERY_S = 240
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = 'dash-self-update'
HEALTH_BRANCH, HEALTH_FILE = 'dash-health', 'dash_health.jsonl'   # 5/11: δελτιο υγειας, για να βλεπουμε το app απο μεσα (το Streamlit δεν δινει logs εξω)
HEALTH_EVERY_S, HEALTH_KEEP = 900, 700                            # καθε 15′, ~1 εβδομαδα
STARTED = sys.__dict__.setdefault('_dash_self_update_started', datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'))
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
    _maybe_report()   # εδω και οχι στο _loop: το νημα που ηδη τρεχει το παιρνει με το reload, χωρις Reboot
    return STATUS


def _read(fn, limit=200):
    try:
        with open(fn, encoding='utf-8', errors='replace') as fh:
            return fh.read(limit).strip()
    except OSError:
        return None


def _mtime(fn):
    try:
        return datetime.datetime.fromtimestamp(os.path.getmtime(fn), datetime.timezone.utc).isoformat(timespec='seconds')
    except OSError:
        return None


def _snapshot(root=ROOT):
    """Τι βλεπει το app απο μεσα (5/11): κλαδι, τελευταιο pull του Streamlit, φρεσκαδα δεδομενων, μνημη, δισκος. Χωρις μυστικα."""
    git = os.path.join(root, '.git')
    head = _read(os.path.join(git, 'HEAD')) or ''
    ref = head[5:] if head.startswith('ref: ') else ''
    du = shutil.disk_usage(root)
    vm = dict(x.split(':', 1) for x in (_read('/proc/self/status', 4000) or '').splitlines() if ':' in x)
    return {'t': _now(), 'pid': os.getpid(), 'root': root, 'py_started': STARTED,
            'head': head, 'commit': _read(os.path.join(git, ref)) if ref else None,
            'streamlit_fetch': _mtime(os.path.join(git, 'FETCH_HEAD')), 'streamlit_pull': _mtime(os.path.join(git, 'ORIG_HEAD')),
            'git_index': _mtime(os.path.join(git, 'index')), 'marker': os.path.exists(os.path.join(root, MARKER)),
            'odds_file': _mtime(os.path.join(root, 'odds_history.jsonl')),
            'rss': (vm.get('VmRSS') or '').strip() or None, 'cg_mem': _read('/sys/fs/cgroup/memory.current'), 'cg_max': _read('/sys/fs/cgroup/memory.max'),
            'disk_free_gb': round(du.free / 1e9, 1), 'threads': threading.active_count(),
            'state': STATUS.get('state'), 'files': STATUS.get('files'), 'err': STATUS.get('err'), 'ok': STATUS.get('ok'), 'updated': STATUS.get('updated')}


def report_health():
    """Προσθετει μια γραμμη στο dash_health.jsonl του κλαδιου dash-health· σφαλμα εδω δεν αγγιζει ποτε την ενημερωση."""
    tok = _token()
    if not tok:
        return
    url = f'https://api.github.com/repos/{REPO}/contents/{HEALTH_FILE}'
    head = {'Accept': 'application/vnd.github+json', 'Authorization': f'Bearer {tok}'}
    r = requests.get(url, params={'ref': HEALTH_BRANCH}, headers=head, timeout=30)
    r.raise_for_status()
    cur = r.json()
    lines = base64.b64decode(cur.get('content') or '').decode('utf-8').splitlines()[-(HEALTH_KEEP - 1):]
    lines.append(json.dumps(_snapshot(), ensure_ascii=False))
    body = {'message': 'dash health [skip ci]', 'branch': HEALTH_BRANCH, 'sha': cur['sha'],
            'content': base64.b64encode(('\n'.join(lines) + '\n').encode('utf-8')).decode('ascii')}
    requests.put(url, json=body, headers=head, timeout=30).raise_for_status()


def _maybe_report():
    if time.time() - STATUS.get('health_t', 0) < HEALTH_EVERY_S:
        return
    STATUS['health_t'] = time.time()
    try:
        report_health()
        STATUS.pop('health_err', None)
    except Exception as e:
        STATUS['health_err'] = type(e).__name__


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
