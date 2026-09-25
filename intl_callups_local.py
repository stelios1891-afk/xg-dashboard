"""
intl_callups_local.py — ΚΛΗΣΕΙΣ ΕΘΝΙΚΩΝ ΑΠΟ ΤΟ LAPTOP (25/9/2026, επιλογη Στελιου «το 2»).
Το Transfermarkt μπλοκαρει τους servers του GitHub → το τραβηγμα της κλησης τρεχει εδω, απο Προγραμματισμενη Εργασια των Windows
«BettingModel_IntlCallups» (καθε 4 ωρες). Κανει δουλεια ΜΟΝΟ οταν υπαρχει ματς εθνικων στις επομενες 72 ωρες.

Βηματα: git pull → intl_callups_tm.py (κληση TM, αξια κλησης· προστασια: <80% ομαδων → τιποτα δεν αλλαζει) → intl_project.py (αξια κλησης στο Μ1/Μ3)
→ intl_nl_shadow / intl_nl_overs → intl_dashboard_build → intl_callups_validate → sanity tests → commit ΜΟΝΟ αυτων των αρχειων → push.
Αν σπασουν τα τεστ: τα αρχεια γυριζουν πισω, κανενα commit. Καταγραφη: intl_callups_local.log (τοπικα).
Χειροκινητα: python intl_callups_local.py --force   (και χωρις ματς στις 72ω)
Αφαιρεση εργασιας: schtasks /delete /tn BettingModel_IntlCallups /f
"""
import os, sys, subprocess, datetime as dt, time

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
PY = sys.executable.replace('pythonw.exe', 'python.exe')      # τα παιδια με python.exe (κρυφα, CREATE_NO_WINDOW)
LOG = os.path.join(ROOT, 'intl_callups_local.log')
FILES = ['intl_vcall_tm.json', 'intl_projections.csv', 'intl_nl_shadow_2627.csv', 'intl_nl_overs_2627.csv',
         'intl_projections_dashboard.json', 'intl_callups_validate_out.txt']
ENV = dict(os.environ, PYTHONIOENCODING='utf-8')


def log(msg):
    line = f"[{dt.datetime.now().strftime('%Y-%m-%d %H:%M')}] {msg}"
    try:
        print(line, flush=True)
    except Exception:          # pythonw (χωρις κονσολα): δεν υπαρχει stdout
        pass
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(line + '\n')


def run(args, timeout=900):
    r = subprocess.run(args, cwd=ROOT, env=ENV, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout,
                       creationflags=(0x08000000 if os.name == 'nt' else 0))      # CREATE_NO_WINDOW: χωρις παραθυρα στην οθονη
    return r.returncode, ((r.stdout or '') + (r.stderr or '')).strip()


def git(*a):
    return run(['git', *a], timeout=300)


def match_soon(hours=72):
    import pandas as pd
    try:
        P = pd.read_csv('intl_projections.csv')
    except Exception:
        return False
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    t = pd.to_datetime(P.utc)
    return bool(((t > now) & (t <= now + dt.timedelta(hours=hours))).any())


def main(force=False):
    rc, out = git('pull', '--rebase', '--autostash', 'origin', 'main')
    if rc != 0:
        git('rebase', '--abort')
        log(f'git pull απετυχε — σταματω (τιποτα δεν αλλαξε): {out[-200:]}'); return 1
    if not force and not match_soon():
        log('κανενα ματς εθνικων στις επομενες 72 ωρες — τιποτα'); return 0
    rc, out = run([PY, 'intl_callups_tm.py'])
    tail = [l for l in out.splitlines() if l.startswith(('ΟΚ', 'ΣΦΑΛΜΑ', 'K ('))]
    if rc != 0:
        log('Transfermarkt απετυχε — κρατιεται η προηγουμενη κληση · ' + ' | '.join(tail)); return 1
    log('κληση TM: ' + ' | '.join(tail))
    rc, out = run([PY, 'intl_project.py'])
    if rc != 0:
        git('checkout', '--', *FILES); log('intl_project απετυχε — επαναφορα αρχειων: ' + out[-300:]); return 1
    for s in ('intl_nl_shadow.py', 'intl_nl_overs.py', 'intl_dashboard_build.py', 'intl_callups_validate.py'):
        rc, out = run([PY, s])
        if rc != 0:
            log(f'{s}: σφαλμα (μη κρισιμο) {out[-150:]}')
    try:
        v = [l for l in open('intl_callups_validate_out.txt', encoding='utf-8') if l.startswith('ΣΥΝΟΛΟ')]
        if v:
            log('επαληθευση: ' + v[0].strip())
    except Exception:
        pass
    rc, out = run([PY, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', 'tests/test_scanner_sanity.py'])
    if rc != 0:
        git('checkout', '--', *FILES); log('ΤΕΣΤ ΑΠΕΤΥΧΑΝ — επαναφορα αρχειων, κανενα commit: ' + out[-300:]); return 1
    git('add', '-f', *FILES)
    rc, out = git('diff', '--cached', '--quiet', '--', *FILES)
    if rc == 0:
        log('καμια αλλαγη για commit'); return 0
    rc, out = git('commit', '-m', 'intl κλησεις TM (laptop) → αξια κλησης/προβολες [skip ci]', '--', *FILES)
    if rc != 0:
        log('commit απετυχε: ' + out[-200:]); return 1
    for i in range(5):
        rc, out = git('push', 'origin', 'HEAD:main')
        if rc == 0:
            log('push OK'); return 0
        git('pull', '--rebase', '--autostash', '-X', 'theirs', 'origin', 'main')
        time.sleep(10)
    log('push απετυχε 5 φορες: ' + out[-200:]); return 1


if __name__ == '__main__':
    try:
        sys.exit(main(force='--force' in sys.argv))
    except Exception as e:
        log(f'ΑΠΡΟΣΜΕΝΟ ΣΦΑΛΜΑ: {type(e).__name__}: {e}'); sys.exit(1)
