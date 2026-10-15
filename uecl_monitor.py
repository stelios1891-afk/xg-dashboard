# -*- coding: utf-8 -*-
"""uecl_monitor.py — ΕΛΕΓΧΟΣ ΑΝΑ ΑΓΩΝΙΣΤΙΚΗ ΤΟΥ CONFERENCE (12/10/2026, Στελιος: «παμε στο −2%, αλλα θελω καθε αγωνιστικη να ελεγχουμε αν η
υποτιμηση της αγορας και του μοντελου μας σε αυτα τα ματς συνεχιζεται»).
Η υποθεση πισω απο το over Α @−2% (uecl_over_low_threshold / uecl_mechanism): στα ματς FotMob+FotMob (κατηγορια Α) του Conference μπαινουν
περισσοτερα γκολ απ οσα λενε μοντελο ΚΑΙ αγορα, και οι ομαδες φτιαχνουν περισσοτερες φασεις (xG) απ οσες λεει το μοντελο.
ΙΣΤΟΡΙΚΑ (4 σεζον, 162 ματς Α): πραγματικα 3.07 · xG 3.10 · μοντελο 2.89 · αγορα 2.87.
Για καθε ΤΕΛΕΙΩΜΕΝΟ ματς της φετινης σεζον: μοντελο = τελευταια εγγραφη euro_shadow.jsonl ΠΡΙΝ τη σεντρα (xgh_ou + xga_ou, ζευγος συνολων),
αγορα = τα γκολ που δικαιολογει η τελευταια τιμη Pinnacle (tl/to/tu) πριν τη σεντρα, πραγματικα & xG = data_Europe_2627.json (FotMob).
Αναφερει ανα αγωνιστικη + αθροιστικα: κατηγορια Α (και Β για τις σκιες: γκολ της ομαδας ΜΕ FotMob vs xG vs μοντελο) + τα over Α του ημερολογιου.
Telegram (info bot) ΜΙΑ φορα οταν τελειωσει ολη η αγωνιστικη (state: uecl_monitor_state.json). --no-tg = μονο εκτυπωση.
"""
import os, sys, json, math, datetime as dt, collections
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
ROOT = os.path.dirname(os.path.abspath(__file__)); F = lambda n: os.path.join(ROOT, n)
SEASON = '2627'
HIST = dict(n=162, g=3.07, xg=3.10, mod=2.89, mkt=2.87)
STATE_F = F('uecl_monitor_state.json')


def _dt(s):
    try:
        d = dt.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except Exception:
        try:
            return dt.datetime.strptime(str(s), '%a, %b %d, %Y, %H:%M UTC').replace(tzinfo=dt.timezone.utc)
        except Exception:
            return None


def _tdist(lh, la):
    """Κατανομη συνολου (Poisson ανεξαρτητα — αρκει για να βρεθει το συνολο που δικαιολογει η τιμη)."""
    P = [0.0] * 25
    for i in range(13):
        pi = math.exp(-lh) * lh ** i / math.factorial(i)
        for j in range(13):
            P[i + j] += pi * math.exp(-la) * la ** j / math.factorial(j)
    return P


def _mkt_total(L, o, u):
    q = (1 / o) / (1 / o + 1 / u); lo, hi = 0.5, 7.0
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]
    for _ in range(30):
        T = (lo + hi) / 2; P = _tdist(T / 2, T / 2); po = pu = 0.0
        for x in parts:
            po += sum(p for k, p in enumerate(P) if k > x + .01) / len(parts); pu += sum(p for k, p in enumerate(P) if k < x - .01) / len(parts)
        if po / max(po + pu, 1e-9) < q: lo = T
        else: hi = T
    return (lo + hi) / 2


def build():
    pre = {}
    for ln in open(F('euro_shadow.jsonl'), encoding='utf-8'):
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r.get('comp') != 'ConferenceLeague' or r.get('xgh_ou') is None:
            continue
        ko, t = _dt(r.get('ko')), _dt(r.get('t'))
        if ko and t and t < ko:
            pre[str(r['mid'])] = r                      # το αρχειο ειναι χρονολογικο → μενει η τελευταια πριν τη σεντρα
    D = json.load(open(F(f'data_Europe_{SEASON}.json'), encoding='utf-8'))
    rows = []
    for mid, m in D.items():
        if m.get('comp') != 'ConferenceLeague' or str(mid) not in pre or m.get('hs') is None or not m.get('shots'):
            continue
        r = pre[str(mid)]
        hid, aid = int(m['home']['id']), int(m['away']['id'])
        xg = lambda t: sum(s['xg'] for s in m['shots'] if s.get('xg') is not None and int(s['tid']) == t)
        fm_h, fm_a = r.get('src_h') == 'FotMob', r.get('src_a') == 'FotMob'
        cat = 'A' if fm_h and fm_a else ('B' if fm_h or fm_a else 'G')
        mk = _mkt_total(float(r['tl']), float(r['to']), float(r['tu'])) if r.get('tl') and r.get('to') and r.get('tu') else None
        rows.append(dict(mid=str(mid), rnd=str(r.get('rnd')), cat=cat, home=m['home']['name'], away=m['away']['name'], gh=int(m['hs']), ga=int(m['as']),
                         xh=xg(hid), xa=xg(aid), mh=float(r['xgh_ou']), ma=float(r['xga_ou']), mkt=mk, fm_h=fm_h, ko=r['ko']))
    return rows


def summary(rows):
    out = []
    A = [r for r in rows if r['cat'] == 'A']
    def agg(x):
        n = len(x)
        g = sum(r['gh'] + r['ga'] for r in x) / n; xg_ = sum(r['xh'] + r['xa'] for r in x) / n; mo = sum(r['mh'] + r['ma'] for r in x) / n
        km = [r['mkt'] for r in x if r['mkt'] is not None]; mk = sum(km) / len(km) if km else float('nan')
        sd = (sum(((r['xh'] + r['xa']) - (r['mh'] + r['ma']) - (xg_ - mo)) ** 2 for r in x) / max(n - 1, 1)) ** .5 / max(n ** .5, 1)
        return n, g, xg_, mo, mk, sd
    for rnd in sorted({r['rnd'] for r in A}, key=lambda s: int(s) if s.isdigit() else 99):
        n, g, xg_, mo, mk, _ = agg([r for r in A if r['rnd'] == rnd])
        out.append(f'αγων. {rnd}: {n} ματς · γκολ {g:.2f} · xG {xg_:.2f} · μοντέλο {mo:.2f} · αγορά {mk:.2f}')
    if A:
        n, g, xg_, mo, mk, sd = agg(A)
        out.append(f'ΣΥΝΟΛΟ φέτος: {n} ματς · γκολ {g:.2f} · xG {xg_:.2f} · μοντέλο {mo:.2f} · αγορά {mk:.2f}')
        out.append(f'→ xG − μοντέλο {xg_ - mo:+.2f} (±{sd:.2f}) · γκολ − μοντέλο {g - mo:+.2f} · γκολ − αγορά {g - mk:+.2f}')
        out.append(f'(ιστορικά {HIST["n"]} ματς: γκολ {HIST["g"]} · xG {HIST["xg"]} · μοντέλο {HIST["mod"]} · αγορά {HIST["mkt"]} → xG − μοντέλο +0.21)')
    B = [r for r in rows if r['cat'] == 'B']
    if B:
        fg = sum(r['gh'] if r['fm_h'] else r['ga'] for r in B) / len(B); fx = sum(r['xh'] if r['fm_h'] else r['xa'] for r in B) / len(B)
        fmo = sum(r['mh'] if r['fm_h'] else r['ma'] for r in B) / len(B)
        out.append(f'Κατηγορία Β ({len(B)} ματς) — η ομάδα ΜΕ FotMob: γκολ {fg:.2f} · xG {fx:.2f} · μοντέλο {fmo:.2f} (ιστορικά 1.58 / 1.84 / 1.75)')
    try:
        L = [json.loads(l) for l in open(F('euro_picks_ledger.jsonl'), encoding='utf-8') if l.strip()]
        ov = [r for r in L if r.get('comp') == 'ConferenceLeague' and r.get('mkt') == 'OVER' and not r.get('no_play') and r.get('pnl') is not None]
        if ov:
            out.append(f'Over Α (ημερολόγιο): {len(ov)} picks · {sum(r["pnl"] for r in ov):+.2f} μονάδες')
    except Exception:
        pass
    try:
        out.extend(dog_moves())
    except Exception as e:
        print('dog_moves:', e)
    return out


def _gd_dist(lh, la):
    P = collections.defaultdict(float)
    for i in range(13):
        pi = math.exp(-lh) * lh ** i / math.factorial(i)
        for j in range(13):
            P[i - j] += pi * math.exp(-la) * la ** j / math.factorial(j)
    return P


def _imp_margin(T, L, oh, oa):
    """Διαφορα γκολ (σκοπια γηπεδουχου) που δικαιολογει η τιμη χαντικαπ (γραμμη L γηπεδουχου, αποδοσεις oh/oa)."""
    q = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -6.0, 6.0
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]
    for _ in range(36):
        M = (lo + hi) / 2; D = _gd_dist(max((T + M) / 2, .05), max((T - M) / 2, .05)); pw = pp = 0.0
        for x in parts:
            for k, p in D.items():
                v = k + x
                if v > .01: pw += p / len(parts)
                elif abs(v) <= .01: pp += p / len(parts)
        if pw / max(1 - pp, 1e-9) < q: lo = M
        else: hi = M
    return (lo + hi) / 2


def dog_moves():
    """15/10/2026 (Στελιος: «αξιζει να το παρακολουθουμε φετος — πως κινουνται τα αουτσαιντερ»): για καθε pick ΑΟΥΤΣΑΙΝΤΕΡ του Conference στο
    ημερολογιο, ποσο κινηθηκε η αγορα (Pinnacle, euro_odds_hist) απο την ΤΙΜΗ ΠΟΥ ΠΑΙΞΑΜΕ ως την τελευταια τιμη πριν τη σεντρα (γκολ διαφορας,
    + = προς εμας). Ιστορικα (Β χωρις FotMob, 4 σεζον): +0.03 — δηλ. η αγορα δεν ερχοταν προς τα dogs."""
    L = [json.loads(l) for l in open(F('euro_picks_ledger.jsonl'), encoding='utf-8') if l.strip()]
    dg = [r for r in L if r.get('comp') == 'ConferenceLeague' and r.get('role') == 'dog' and not r.get('no_play')]
    if not dg:
        return []
    ids = {str(r['mid']) for r in dg}
    H = collections.defaultdict(list)
    for ln in open(F('euro_odds_hist.jsonl'), encoding='utf-8'):
        try:
            z = json.loads(ln)
        except Exception:
            continue
        if str(z.get('mid')) in ids and z.get('line') is not None and z.get('oh') and z.get('oa'):
            H[str(z['mid'])].append(z)
    T_ = {}
    try:
        for m in json.load(open(F('euro_projections.json'), encoding='utf-8')).get('matches', []):
            T_[str(m['mid'])] = float(m.get('xgh', 1.3)) + float(m.get('xga', 1.3))
    except Exception:
        pass
    mv = []
    for r in dg:
        mid = str(r['mid']); ko = _dt(r.get('ko')); seen = _dt(r.get('seen'))
        hs = sorted((z for z in H.get(mid, []) if _dt(z['t']) and ko and _dt(z['t']).replace(tzinfo=dt.timezone.utc) <= ko), key=lambda z: z['t'])
        if not hs or not seen or ko > dt.datetime.now(dt.timezone.utc):
            continue                                      # μονο ματς που ξεκινησαν (η τελευταια τιμη = κλεισιμο)
        T = T_.get(mid, 2.6); side = int(r['side']); last = hs[-1]
        ent = [z for z in hs if _dt(z['t']).replace(tzinfo=dt.timezone.utc) <= seen] or hs[:1]
        ze = ent[-1]
        m_e = _imp_margin(T, float(ze['line']), float(ze['oh']), float(ze['oa']))
        m_c = _imp_margin(T, float(last['line']), float(last['oh']), float(last['oa']))
        mv.append(dict(mv=side * (m_c - m_e), pnl=r.get('pnl')))
    if not mv:
        return []
    n = len(mv); avg = sum(x['mv'] for x in mv) / n; up = sum(x['mv'] >= .05 for x in mv); dn = sum(x['mv'] <= -.05 for x in mv)
    pn = [x['pnl'] for x in mv if x['pnl'] is not None]
    s = f'Αουτσάιντερ (κίνηση αγοράς από την τιμή μας ως το κλείσιμο): {n} picks · μέσος {avg:+.2f} γκολ (+ = προς εμάς) · προς εμάς {up} / κόντρα {dn} / ίδια {n - up - dn}'
    if pn:
        s += f' · αποτέλεσμα {sum(pn):+.2f} μονάδες ({len(pn)})'
    return [s + ' (ιστορικά +0.03)']


def main(notify_tg=True):
    rows = build()
    lines = summary(rows)
    print('CONFERENCE — ΕΛΕΓΧΟΣ ΥΠΟΘΕΣΗΣ OVER Α (−2%)'); print('\n'.join(lines) if lines else 'κανένα τελειωμένο ματς ακόμα')
    # αγωνιστικη ολοκληρωμενη = κανενα ματς της (στο euro_projections) χωρις αποτελεσμα
    try:
        P = json.load(open(F('euro_projections.json'), encoding='utf-8'))
        by = collections.defaultdict(list)
        for m in P.get('matches', []):
            if m.get('comp') == 'ConferenceLeague':
                by[str(m.get('round'))].append(bool(m.get('finished')))
        done = sorted((r for r, v in by.items() if v and all(v)), key=lambda s: int(s) if s.isdigit() else 99)
    except Exception:
        done = []
    st = {}
    try:
        st = json.load(open(STATE_F, encoding='utf-8'))
    except Exception:
        pass
    new = [r for r in done if r not in st.get('reported', [])]
    if new and lines and notify_tg and os.environ.get('TELEGRAM_TOKEN'):
        try:
            import notify
            notify.send('📊 CONFERENCE — έλεγχος over Α μετά την αγωνιστική ' + ', '.join(new) + '\n' + '\n'.join(lines), channel='info')
            st['reported'] = sorted(set(st.get('reported', [])) | set(new), key=lambda s: int(s) if s.isdigit() else 99)
            json.dump(st, open(STATE_F, 'w', encoding='utf-8'), ensure_ascii=False)
        except Exception as e:
            print('telegram:', e)


if __name__ == '__main__':
    main(notify_tg='--no-tg' not in sys.argv)
