"""dash_slim.py — ελαφρυ αντιγραφο του repo ΜΟΝΟ για το Streamlit dashboard (1/11/2026).
Γιατι: το repo εφτασε ~305 MB ιστορικο (ο scanner ξαναγραφει μεγαλα αρχεια τιμων καθε 5′) και το Streamlit Cloud
δεν προλαβαινε να το κατεβασει στο Reboot («Cloning repository…» ξανα και ξανα).
Τι κανει: απο το HEAD κραταει τα αρχεια που χρειαζεται το dashboard (ολος ο κωδικας + μικρα αρχεια + μεγαλα που
αναφερονται στον κωδικα του dashboard ή στα modules που φορτωνει) και τα βαζει σε commit στο
κλαδι dashboard-live (συνεχες ιστορικο, που ξεκιναει απο την αρχη μια φορα την εβδομαδα). Το main ΔΕΝ αγγιζεται. Μονο git plumbing — δεν αλλαζει working tree/index.
Χρηση: python dash_slim.py [--push] [--list]"""
import os, re, sys, subprocess, fnmatch

ROOT = os.path.dirname(os.path.abspath(__file__))
BRANCH = 'dashboard-live'
SMALL = 300_000                      # bytes: μικρα αρχεια μπαινουν παντα
KEEP_EXT = ('.py', '.toml', '.html', '.js', '.css', '.txt', '.md', '.sh', '.yml', '.cfg', '.ini')
EXTRA_DIRS = ('nba_pbp_full/',)    # διαβαζονται με os.path.join(φακελος, σεζον, '*.jsonl') — δεν πιανονται απο τα ονοματα (nba_boxB)
DROP_DIRS = ('.github/',)            # οχι workflows στο αντιγραφο (να μην τρεχουν Actions απο αυτο το κλαδι)


def git(*a, inp=None, env=None):
    return subprocess.run(['git', *a], cwd=ROOT, input=inp, capture_output=True, check=True,
                          env={**os.environ, **(env or {})}).stdout


def tree():
    out = git('ls-tree', '-r', '-l', '-z', 'HEAD').split(b'\0')
    rows = []
    for x in out:
        if not x:
            continue
        meta, path = x.split(b'\t', 1)
        mode, typ, sha, size = meta.split()
        if typ != b'blob':
            continue
        rows.append((mode.decode(), sha.decode(), int(size) if size != b'-' else 0, path.decode('utf-8')))
    return rows


def reachable(paths):
    """Modules που φορτωνει το dashboard (ριζα: dashboard/*.py), με τα imports τους."""
    have = {p for p in paths if p.endswith('.py')}
    todo = [p for p in have if p.startswith('dashboard/') and p.count('/') == 1]
    seen = set()
    pat = re.compile(r"(?:^|\s|;)(?:from|import)\s+([A-Za-z_][\w]*)|__import__\('(\w+)'\)|import_module\('(\w+)'\)", re.M)
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        src = open(os.path.join(ROOT, p), encoding='utf-8', errors='ignore').read()
        for m in pat.finditer(src):
            name = next(g for g in m.groups() if g)
            for c in (f'{name}.py', f'dashboard/{name}.py'):
                if c in have and c not in seen:
                    todo.append(c)
    return seen


def patterns(mods):
    """Ολα τα string literals με ονομα αρχειου στον κωδικα (f-string {..} → *)."""
    pats = set()
    lit = re.compile(r"""['"]([^'"\n]{2,160}?\.(?:jsonl|json|csv|txt|parquet|pkl|gz|tsv|npz|npy))['"]""")
    for p in mods:
        src = open(os.path.join(ROOT, p), encoding='utf-8', errors='ignore').read()
        for m in lit.finditer(src):
            s = re.sub(r'\{[^}]*\}', '*', m.group(1)).replace('\\', '/')
            pats.add(s.lstrip('./'))
            pats.add(os.path.basename(s))
    # σκετα '*.json' κτλ (απο f'{x}.json') θα επιαναν τα παντα → θελουμε τουλαχιστον 6 σταθερους χαρακτηρες στο ονομα
    return {p for p in pats if len(re.sub(r'\.\w+$', '', p).replace('*', '').replace('/', '')) >= 6}


def select():
    rows = tree()
    mods = reachable([r[3] for r in rows])
    pats = patterns(mods)
    keep, drop = [], []
    for mode, sha, size, path in rows:
        base = os.path.basename(path)
        if path.startswith(DROP_DIRS):
            ok = False
        elif path.startswith(('dashboard/', '.streamlit/') + EXTRA_DIRS) or path.endswith(KEEP_EXT) or size <= SMALL:
            ok = True
        else:
            ok = any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(base, p) for p in pats)
        (keep if ok else drop).append((mode, sha, size, path))
    return keep, drop


def build(keep):
    idx = os.path.join(ROOT, '.git_dash_slim_index') if not os.path.isdir(os.path.join(ROOT, '.git')) else \
        os.path.join(ROOT, '.git', 'dash_slim_index')
    env = {'GIT_INDEX_FILE': idx}
    try:
        os.remove(idx)
    except OSError:
        pass
    info = ''.join(f'{m} {s}\t{p}\n' for m, s, _, p in keep).encode('utf-8')
    git('update-index', '--add', '--index-info', inp=info, env=env)
    t = git('write-tree', env=env).decode().strip()
    os.remove(idx)
    return t


def remote_tip():
    """(commit, tree, ημερα αρχης) του dashboard-live στο GitHub· None αν δεν υπαρχει. Μονο η κορυφη (--depth=1)."""
    try:
        git('fetch', '-q', '--depth=1', 'origin', f'+refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}')
        c = git('rev-parse', f'refs/remotes/origin/{BRANCH}').decode().strip()
        t = git('rev-parse', f'{c}^{{tree}}').decode().strip()
        m = re.search(r'αρχη:(\d{4}-\d{2}-\d{2})', git('log', '-1', '--format=%B', c).decode('utf-8'))
        return c, t, (m.group(1) if m else '2000-01-01')
    except subprocess.CalledProcessError:
        return None


if __name__ == '__main__':
    keep, drop = select()
    mb = lambda L: sum(r[2] for r in L) / 1e6
    print(f'κραταω {len(keep)} αρχεια {mb(keep):.1f} MB · αφηνω {len(drop)} αρχεια {mb(drop):.1f} MB')
    if '--list' in sys.argv:
        for r in sorted(drop, key=lambda r: -r[2])[:40]:
            print(f'  ΕΞΩ {r[2] / 1e6:6.2f} MB {r[3]}')
        for r in sorted(keep, key=lambda r: -r[2])[:25]:
            print(f'  ΜΕΣΑ {r[2] / 1e6:6.2f} MB {r[3]}')
    t = build(keep)
    if '--push' in sys.argv:
        # Συνεχες ιστορικο (κανονικο «pull» για το Streamlit)· μια φορα την εβδομαδα, νυχτα, ξεκιναει απο την αρχη
        # (νεο commit χωρις γονεα) για να μη φουσκωσει ξανα. Αν το Streamlit δεν παρει μονο του εκεινο το αλμα → ενα Reboot (13″).
        tip = remote_tip()
        if tip and t == tip[1]:                    # τιποτα καινουργιο → κανενα push (να μη χτυπαει το Streamlit αδικα)
            print('dashboard-live ηδη ενημερο')
            sys.exit(0)
        import datetime as dt
        now = dt.datetime.now(dt.timezone.utc)
        fresh = (not tip or (now.date() - dt.date.fromisoformat(tip[2])).days >= 7 and 1 <= now.hour <= 3)
        start = now.date().isoformat() if fresh else tip[2]
        head = git('rev-parse', '--short', 'HEAD').decode().strip()
        par = [] if fresh else ['-p', tip[0]]
        c = git('commit-tree', t, *par, '-m', f'dashboard-live: main {head} (μονο αρχεια dashboard) αρχη:{start} [skip ci]').decode().strip()
        git('push', '-q', '-f', 'origin', f'{c}:refs/heads/{BRANCH}')
        print('push →', BRANCH, c[:9], 'απο', head, '(ΝΕΑ ΑΡΧΗ)' if fresh else '')
    else:
        print('tree', t, '(χωρις push)')
