# -*- coding: utf-8 -*-
"""
clv_ledger.py — Ημερολογιο CLV: καθε pick του scanner κρινεται απεναντι στο κλεισιμο.

Ροη (ολα τοπικα, χωρις νεες πηγες):
  1. Ο scanner (scan_value.scan) γραφει καθε ΝΕΟ alert στο clv_bets.jsonl
     (τιμη/γραμμη Pinnacle τη στιγμη της ειδοποιησης = η τιμη που παιρνουμε).
  2. Το παρον, μετα τη σεντρα: κλεισιμο = τελευταια εγγραφη του ιδιου ματς στο
     odds_history.jsonl πριν τη σεντρα (ιδιο feed, Pinnacle/Matchbook) και
     αποτελεσμα απο FotMob → γραφει μια τελικη γραμμη στο clv_ledger.jsonl.
  3. Εβδομαδιαια συνοψη στο Telegram (καλειται απο scan_value.auto καθε Δευτερα).

CLV = αποδοση που πηραμε − αποδοση κλεισιματος (ιδια γραμμη μονο).
Θετικο CLV = νικησαμε το κλεισιμο = η αγορα ηρθε προς το μερος μας.

Χρηση:  python clv_ledger.py            # settle ο,τι εκκρεμει + συνοψη στο τερματικο
        python clv_ledger.py report 30  # συνοψη τελευταιων 30 ημερων (χωρις Telegram)
"""
import os, sys, json, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
BETS_F = os.path.join(ROOT, 'clv_bets.jsonl')       # entries (τα γραφει ο scanner)
LEDGER_F = os.path.join(ROOT, 'clv_ledger.jsonl')   # settled (τα γραφει το παρον)
HIST_F = os.path.join(ROOT, 'odds_history.jsonl')   # στιγμιοτυπα τιμων (changes-only)
REPORT_STATE = os.path.join(ROOT, 'clv_report_last.txt')

UTC = datetime.timezone.utc


def _dt(s):
    """iso string (με/χωρις tz, με/χωρις 'Z') -> aware UTC datetime, αλλιως None."""
    if not s:
        return None
    try:
        d = datetime.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
        return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)
    except ValueError:
        return None


def _jsonl(path):
    out = []
    if os.path.exists(path):
        for line in open(path, encoding='utf-8'):
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def _bet_key(b):
    return f"{b['lg']}|{b['home']}|{b['away']}|{b['side']}|{b['hcap']:g}|{b.get('ko','')}"


# ---------- κλεισιμο απο το δικο μας odds_history ----------
def _closing_index():
    """{'hid_aid': τελευταια εγγραφη} ανα ματς — μονο εγγραφες ΠΡΙΝ τη σεντρα του."""
    idx = {}
    for r in _jsonl(HIST_F):
        t = _dt(r.get('t')); ko = _dt(r.get('ko'))
        if t is None:
            continue
        if ko is not None and t > ko + datetime.timedelta(minutes=10):
            continue                     # μετα τη σεντρα δεν ειναι κλεισιμο
        key = f"{r.get('hid')}_{r.get('aid')}"
        if key not in idx or t > _dt(idx[key].get('t')):
            idx[key] = r
    return idx


# ---------- αποτελεσματα απο FotMob ----------
_FOT_CACHE = {}

def _league_results(lg):
    if lg in _FOT_CACHE:
        return _FOT_CACHE[lg]
    sys.path.insert(0, os.path.join(ROOT, 'dashboard'))
    import build_data
    res = {}
    try:
        d = build_data._fotmob('https://www.fotmob.com/api/data/leagues?id=%d&season=%s'
                               % (build_data.LEAGUE_FOTMOB[lg], build_data.CURRENT_FOTMOB_SEASON))
        for m in d.get('fixtures', {}).get('allMatches', []):
            st = m.get('status', {})
            if not st.get('finished'):
                continue
            ss = str(st.get('scoreStr') or '')
            parts = ss.replace('–', '-').split('-')
            try:
                gh, ga = int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                continue
            hid = (m.get('home') or {}).get('id'); aid = (m.get('away') or {}).get('id')
            res[f'{hid}_{aid}'] = dict(gd=gh - ga, utc=st.get('utcTime', ''), score=ss.strip())
    except Exception as e:
        print(f'  FotMob {lg}: {type(e).__name__}: {e}')
    _FOT_CACHE[lg] = res
    return res


# ---------- ισοδυναμο κλεισιμο οταν αλλαξε η γραμμη ----------
def _equiv_close_odds(mxh, mxa, side, our_line, close_line_our, co_our, co_opp):
    """Η γραμμη εκλεισε αλλου (πχ παιξαμε +0.5, εκλεισε +0.25): βρες ποια «δυναμη»
    (goal supremacy) δικαιολογει το κλεισιμο, και τιμολογησε τη ΔΙΚΗ μας γραμμη απο
    την ιδια κατανομη — με τη γκανιοτα του κλεισιματος. Επιστρεφει εκτιμωμενη αποδοση."""
    import picks as engine

    def pq(dist, sd, line):
        """p_cover με ΣΩΣΤΟ χειρισμο quarter-γραμμων (μεσος ορος των δυο μισων)."""
        parts = [line] if (line * 4) % 2 == 0 else [line - 0.25, line + 0.25]
        pw = pp = 0.0
        for L in parts:
            w, p = engine.p_cover(dist, sd, L)
            pw += w / len(parts); pp += p / len(parts)
        return pw, pp

    T = max(float(mxh) + float(mxa), 0.4)      # συνολο γκολ: απο το μοντελο τη στιγμη του bet
    imp = (1 / co_our) / (1 / co_our + 1 / co_opp)

    def f(d):
        lh = max((T + d) / 2, 0.05); la = max((T - d) / 2, 0.05)
        dist = engine.gd_dist(lh, la)
        pw, pp = pq(dist, side, close_line_our)
        return pw / max(pw + (1 - pw - pp), 1e-9)

    lo, hi = -6.0, 6.0
    flo, fhi = f(lo), f(hi)
    if not (min(flo, fhi) <= imp <= max(flo, fhi)):
        return None
    inc = fhi > flo
    for _ in range(40):
        mid = (lo + hi) / 2
        if (f(mid) < imp) == inc:
            lo = mid
        else:
            hi = mid
    d = (lo + hi) / 2
    lh = max((T + d) / 2, 0.05); la = max((T - d) / 2, 0.05)
    dist = engine.gd_dist(lh, la)
    pw2, pp2 = pq(dist, side, our_line)
    pwc, ppc = pq(dist, side, close_line_our)
    if pw2 <= 0 or pwc <= 0:
        return None
    fair_our = (1 - pp2) / pw2
    fair_close = (1 - ppc) / pwc
    return co_our * fair_our / fair_close      # ιδια γκανιοτα με το πραγματικο κλεισιμο


# ---------- settle ----------
def settle_pending(verbose=True):
    import picks
    done = {_bet_key(b) for b in _jsonl(LEDGER_F)}
    now = datetime.datetime.now(UTC)
    pend = []
    for b in _jsonl(BETS_F):
        k = _bet_key(b)
        if k in done:
            continue
        ko = _dt(b.get('ko'))
        if ko is None or now < ko + datetime.timedelta(hours=3):
            continue                     # δεν εχει τελειωσει ακομα
        pend.append(b)
        done.add(k)                      # μην το ξαναδουμε δυο φορες στο ιδιο τρεξιμο
    if not pend:
        return 0
    cidx = _closing_index()
    n = 0
    with open(LEDGER_F, 'a', encoding='utf-8') as fh:
        for b in pend:
            rec = dict(b)                # lg,home,away,hid,aid,ko,side,hcap,odds,edge,seen
            # --- κλεισιμο (ιδιο feed) ---
            c = cidx.get(f"{b.get('hid')}_{b.get('aid')}")
            if c and c.get('line') is not None and c.get('oh') and c.get('oa'):
                cl = float(c['line'])
                our_close_line = cl if b['side'] == 1 else -cl
                co = float(c['oh'] if b['side'] == 1 else c['oa'])
                rec['close_line'] = round(our_close_line, 2)
                rec['close_odds'] = round(co, 3)
                rec['close_t'] = c.get('t')
                if abs(our_close_line - b['hcap']) < 0.01:
                    rec['clv'] = round(b['odds'] - co, 3)          # + = νικησαμε το κλεισιμο
                    rec['clv_pct'] = round(b['odds'] / co - 1, 4)
                else:
                    rec['clv'] = None                              # αλλαξε γραμμη — οχι ευθεια συγκριση
                    if b.get('mxh') is not None and b.get('mxa') is not None:
                        co_opp = float(c['oa'] if b['side'] == 1 else c['oh'])
                        try:
                            eq = _equiv_close_odds(b['mxh'], b['mxa'], b['side'], b['hcap'],
                                                   our_close_line, co, co_opp)
                        except Exception:
                            eq = None
                        if eq:
                            rec['close_eq'] = round(eq, 3)         # εκτιμωμενο κλεισιμο ΣΤΗ γραμμη μας
                            rec['clv_est'] = round(b['odds'] - eq, 3)
                            rec['clv_est_pct'] = round(b['odds'] / eq - 1, 4)
            else:
                rec['close_odds'] = None; rec['clv'] = None
            # --- αποτελεσμα ---
            r = _league_results(b['lg']).get(f"{b.get('hid')}_{b.get('aid')}")
            if r is not None:
                ko = _dt(b.get('ko')); mu = _dt(r.get('utc'))
                if ko and mu and abs((mu - ko).total_seconds()) > 3 * 86400:
                    r = None             # αλλο παιχνιδι των ιδιων ομαδων
            if r is not None:
                rec['gd'] = r['gd']; rec['score'] = r['score']
                rec['pnl'] = round(picks.settle(r['gd'], b['side'], b['hcap'], b['odds']), 4)
                if rec.get('clv') is not None:
                    rec['pnl_close'] = round(picks.settle(r['gd'], b['side'], b['hcap'], rec['close_odds']), 4)
            else:
                rec['gd'] = None; rec['pnl'] = None
            rec['settled_at'] = now.isoformat(timespec='minutes')
            fh.write(json.dumps(rec, ensure_ascii=False) + chr(10))
            n += 1
    if verbose:
        print(f'clv_ledger: settled {n} bets')
    return n


# ---------- αναφορα ----------
def report(days=7):
    now = datetime.datetime.now(UTC)
    cut = now - datetime.timedelta(days=days)
    rows = [r for r in _jsonl(LEDGER_F) if (_dt(r.get('ko')) or now) >= cut]
    if not rows:
        return f'CLV: κανενα settled pick τις τελευταιες {days} μερες.'
    n = len(rows)
    withclv = [r for r in rows if r.get('clv') is not None]
    beat = sum(1 for r in withclv if r['clv'] > 0)
    tie = sum(1 for r in withclv if r['clv'] == 0)
    moved = [r for r in rows if r.get('close_odds') is not None and r.get('clv') is None]
    pnl = [r['pnl'] for r in rows if r.get('pnl') is not None]
    pnlc = [(r['pnl'], r['pnl_close']) for r in rows if r.get('pnl_close') is not None]
    L = [f'📒 CLV αναφορα ({days}μερο): {n} picks']
    if withclv:
        mclv = sum(r['clv'] for r in withclv) / len(withclv)
        mpct = sum(r['clv_pct'] for r in withclv) / len(withclv) * 100
        L.append(f'ιδια γραμμη {len(withclv)}: νικησαμε το κλεισιμο {beat}/{len(withclv)}'
                 + (f' (+{tie} ισοπαλιες)' if tie else '')
                 + f' · μεσο CLV {mclv:+.3f} ({mpct:+.1f}%)')
    if moved:
        est = [r['clv_est_pct'] for r in moved if r.get('clv_est_pct') is not None]
        extra = (f' · εκτιμωμενο ≈CLV {sum(est)/len(est)*100:+.1f}% ({len(est)})' if est else '')
        L.append(f'γραμμη αλλαξε ως τη σεντρα: {len(moved)} picks{extra}')
    if pnl:
        L.append(f'αποτελεσμα: {sum(pnl):+.2f} μοναδες σε {len(pnl)} bets ({sum(pnl)/len(pnl)*100:+.1f}%)')
    if pnlc:
        de = sum(a - b for a, b in pnlc) / len(pnlc) * 100
        L.append(f'κερδος timing vs κλεισιμο: {de:+.2f} μον./bet ({len(pnlc)} συγκρισιμα)')
    return chr(10).join(L)


def maybe_weekly(notify_tg=True):
    """Καλειται απο scan_value.auto(): settle παντα· Telegram συνοψη καθε Δευτερα."""
    try:
        settle_pending(verbose=False)
    except Exception as e:
        print(f'clv_ledger settle σφαλμα (μη κρισιμο): {type(e).__name__}: {e}')
        return
    try:
        now = datetime.datetime.now(UTC)
        last = ''
        if os.path.exists(REPORT_STATE):
            last = open(REPORT_STATE, encoding='utf-8').read().strip()
        if now.weekday() == 0 and last != now.strftime('%Y-%m-%d'):
            msg = report(7)
            if notify_tg and 'κανενα settled' not in msg:
                import notify
                notify.send(msg)
            with open(REPORT_STATE, 'w', encoding='utf-8') as fh:
                fh.write(now.strftime('%Y-%m-%d'))
            print(msg)
    except Exception as e:
        print(f'clv_ledger report σφαλμα (μη κρισιμο): {type(e).__name__}: {e}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if 'report' in sys.argv:
        d = int(sys.argv[sys.argv.index('report') + 1]) if len(sys.argv) > sys.argv.index('report') + 1 else 7
        print(report(d))
    else:
        settle_pending()
        print(report(7))
