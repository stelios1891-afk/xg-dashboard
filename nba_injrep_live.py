# -*- coding: utf-8 -*-
"""nba_injrep_live.py — ΕΠΙΣΗΜΗ ΑΝΑΦΟΡΑ ΤΡΑΥΜΑΤΙΩΝ NBA ΣΤΟ LIVE (21/10/2026, Στελιος «καντο ετσι» — ΚΛΕΙΣΤΟ μεχρι «περνα το»).
Πηγη: PDF του NBA (ak-static.cms.nba.com/referee/injury/Injury-Report_YYYY-MM-DD_HH_MMAM.pdf), νεα αναφορα ανα 15′. Διαβαζεται με
nba_injrep_fetch.parse (ιδιο με τα 5 χρονια ιστορικου). Σε καθε scan: ελεγχος ΜΟΝΟ των νεων 15λεπτων απο την τελευταια που βρεθηκε
(λιγα αιτηματα, ο CDN μπλοκαρει) → nba_injrep_live.json (τελευταια αναφορα) + nba_injrep_live_hist.jsonl (καθε νεα αναφορα, για ελεγχο).
24/10: + RotoWire για ομαδες που δεν εχουν δηλωσει ακομα (nba_rw_lineups.py, βλ. Official).
ΔΙΑΚΟΠΤΗΣ: nba_injury_source.json {"source": "espn" | "official"}. Με «espn» το αρχειο ΚΑΤΕΒΑΙΝΕΙ και ΚΑΤΑΓΡΑΦΕΤΑΙ αλλα ΔΕΝ χρησιμοποιειται.
Με «official»: για καθε ομαδα που εχει ματς στην αναφορα, οι καταστασεις της αναφορας αντικαθιστουν το ESPN (nba_absence, nba_roster_now,
nba_trades)· ομαδες/ματς εκτος αναφορας → ESPN. Παλια αναφορα (>3ω) → ESPN + ειδοποιηση info bot.
ΠΙΘΑΝΟΤΗΤΑ ΑΠΟΥΣΙΑΣ (t21, Τ−6ω· t34 «ανα ρολο» ΠΕΡΝΑ: ανοιγμα +4.8 → +5.2%, RMSE 13.718 → 13.698):
  σταρ ≥30′: Out 1 · Doubtful .965 · Questionable .42 · Probable .04 · βασικος 20-30′: .963 / .46 / .07 · ρολιστας <20′ (μονο ρόστερ 1ου ματς): .962 / .547 / .195
  Available = 0. Λογοι G-League (two-way) αγνοουνται (οπως στα τεστ)."""
import os, re, json, datetime as dt, urllib.request, urllib.error, tempfile, unicodedata
from zoneinfo import ZoneInfo
ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, n)
ET = ZoneInfo('America/New_York')
STATE, HIST, SWITCH = 'nba_injrep_live.json', 'nba_injrep_live_hist.jsonl', 'nba_injury_source.json'
URL = 'https://ak-static.cms.nba.com/referee/injury/Injury-Report_{d}_{h}.pdf'
STALE_MIN = 180
_H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0'}
PROB = {'star': {'Out': 1.0, 'Doubtful': .965, 'Questionable': .42, 'Probable': .04},
        'starter': {'Out': 1.0, 'Doubtful': .963, 'Questionable': .46, 'Probable': .07},
        'role': {'Out': 1.0, 'Doubtful': .962, 'Questionable': .547, 'Probable': .195}}


def _load(n, d):
    try:
        with open(F(n), encoding='utf-8') as fh: return json.load(fh)
    except Exception: return d


def enabled():
    return str(_load(SWITCH, {}).get('source', 'espn')).lower() == 'official'


def ckey(name):
    """συμπαγες κλειδι ονοματος ιδιο με nba_injrep_fetch.key: ονομα+επωνυμο, μονο γραμματα, χωρις Jr/Sr/II/III/IV"""
    s = unicodedata.normalize('NFD', str(name)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b\.?', '', s)
    return re.sub(r'[^a-z]', '', s)


def prob(status, minutes):
    role = 'star' if (minutes or 0) >= 30 else ('starter' if (minutes or 0) >= 20 else 'role')
    return PROB[role].get(status, 0.0)


def _url(t): return URL.format(d=t.strftime('%Y-%m-%d'), h=t.strftime('%I_%M%p'))


def _head(u):
    try:
        urllib.request.urlopen(urllib.request.Request(u, method='HEAD', headers=_H), timeout=20); return 200
    except urllib.error.HTTPError as e: return e.code
    except Exception: return -1


def refresh(now=None):
    """Ψαχνει νεα αναφορα (μονο τα 15λεπτα μετα την τελευταια)· αν βρει, την κατεβαζει/διαβαζει/αποθηκευει. → κειμενο κατασταστασης."""
    now = now or dt.datetime.now(dt.timezone.utc); now_et = now.astimezone(ET)
    S = _load(STATE, {})
    # 22/10/2026 ΔΙΑΓΝΩΣΗ: στο cloud το αρχειο δεν γραφοταν ποτε → γραφεται ΑΜΕΣΩΣ + κωδικοι απαντησης/διαρκεια/σφαλμα (για να φαινεται τι γινεται)
    S['start'] = now.isoformat(timespec='minutes'); S.pop('error', None)
    json.dump(S, open(F(STATE), 'w', encoding='utf-8'), ensure_ascii=False)
    import time as _t; t0 = _t.time()
    last = dt.datetime.fromisoformat(S['slot']) if S.get('slot') else None
    s = now_et.replace(minute=(now_et.minute // 15) * 15, second=0, microsecond=0)
    lo = (last + dt.timedelta(minutes=15)) if last and (s - last) < dt.timedelta(hours=6) else s - dt.timedelta(hours=3)
    found = None; codes = []
    while s >= lo:
        c = _head(_url(s)); codes.append(c)
        if c == 200: found = s; break
        s -= dt.timedelta(minutes=15)
    S['checked'] = now.isoformat(timespec='minutes'); S['codes'] = codes[-12:]; S['secs'] = round(_t.time() - t0, 1)
    if not found:
        json.dump(S, open(F(STATE), 'w', encoding='utf-8'), ensure_ascii=False)
        return f"καμια νεα (τελευταια {S.get('file', '—')}) · απαντησεις {codes[-6:]} · {S['secs']}″"
    try:
        import nba_injrep_fetch as N
        p = os.path.join(tempfile.gettempdir(), 'nba_injrep_live.pdf')
        open(p, 'wb').write(urllib.request.urlopen(urllib.request.Request(_url(found), headers=_H), timeout=40).read())
        rows = N.parse(p)
    except Exception as e:
        S['error'] = f'{type(e).__name__}: {str(e)[:200]}'
        json.dump(S, open(F(STATE), 'w', encoding='utf-8'), ensure_ascii=False)
        return f"σφαλμα: {S['error']}"
    if not rows:
        json.dump(S, open(F(STATE), 'w', encoding='utf-8'), ensure_ascii=False)
        return f'{os.path.basename(_url(found))}: 0 γραμμες (κραταω την προηγουμενη)'
    keep = [dict(gd=r[1], gt=r[2], mu=r[3], team=r[4], raw=r[5], key=r[6], status=r[7], reason=r[8]) for r in rows]
    S.update(slot=found.isoformat(), file=os.path.basename(_url(found)), fetched=now.isoformat(timespec='minutes'), rep=rows[0][0], rows=keep)
    json.dump(S, open(F(STATE), 'w', encoding='utf-8'), ensure_ascii=False)
    with open(F(HIST), 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(dict(fetched=S['fetched'], file=S['file'], rep=S['rep'], rows=[[x['gd'], x['team'], x['raw'], x['status'], x['reason']] for x in keep]),
                            ensure_ascii=False) + '\n')
    return f"{S['file']}: {len(keep)} γραμμες"


def age_min(now=None):
    S = _load(STATE, {})
    if not S.get('slot'): return None
    now = now or dt.datetime.now(dt.timezone.utc)
    return (now - dt.datetime.fromisoformat(S['slot'])).total_seconds() / 60


class Official:
    """Καταστασεις ανα (ομαδα, ημερα ματς ΗΠΑ) → {κλειδι: (κατασταση, λογος, ονομα)}.
    24/10/2026 (Στελιος «ναι ετσι μετρα το»): ΣΕΙΡΑ ΠΗΓΩΝ επισημη αναφορα (ομαδα που εχει δηλωσει) → RotoWire (nba_rw_lineups, ιδιες
    πιθανοτητες ανα σημα) → ESPN (εξω απο την κλαση). Στο RotoWire: καθε «Out» του ESPN που το RotoWire ΔΕΝ αναφερει μενει Out (ασφαλεια).
    self.src[(ομαδα, ημερα)] = 'official' | 'rotowire' · self.ok_off = φρεσκια επισημη αναφορα (για την ειδοποιηση «παλια αναφορα»)."""
    def __init__(self, now=None):
        self.S = _load(STATE, {}); self.ok_off = bool(self.S.get('rows')) and (age_min(now) or 1e9) <= STALE_MIN
        self.by = {}; self.teams_dates = set(); self.src = {}
        for x in (self.S.get('rows', []) if self.ok_off else []):
            try: gd = dt.datetime.strptime(x['gd'], '%m/%d/%Y').date().isoformat()
            except Exception: continue
            # 24/10/2026: ομαδα με ΜΟΝΟ G-League γραμμες ειναι ΚΑΛΥΜΜΕΝΗ (ως τωρα επεφτε στη λιστα ESPN, π.χ. NOP 23/10)
            self.teams_dates.add((x['team'], gd)); self.src[(x['team'], gd)] = 'official'
            if 'gleague' in str(x.get('reason') or '').replace(' ', '').lower(): continue
            self.by.setdefault((x['team'], gd), {})[x['key']] = (x['status'], x.get('reason'), x['raw'])
        try:
            import nba_rw_lineups as RW
            esp = {}
            for v in _load('nba_injuries.json', {}).get('teams', {}).values():
                for y in v.get('players', []):
                    if v.get('code') and str(y[1] or '').strip().lower() == 'out': esp.setdefault(v['code'], []).append(y[0])
            for (t, gd), d in RW.by_team(now, STALE_MIN).items():
                if (t, gd) in self.teams_dates: continue                 # η επισημη αναφορα προηγειται
                self.teams_dates.add((t, gd)); self.src[(t, gd)] = 'rotowire'
                D = self.by.setdefault((t, gd), {})
                for nm, (stt, tag, pct) in d.items(): D[ckey(nm)] = (stt, f'RotoWire {tag} · τελεια {pct}%', nm)
                for nm in esp.get(t, []): D.setdefault(ckey(nm), ('Out', 'ESPN Out (οχι στο RotoWire)', nm))
        except Exception as e: print('RotoWire: απενεργο —', e)
        self.ok = bool(self.teams_dates)

    def covers(self, team, gdate):
        return self.ok and (team, gdate) in self.teams_dates

    def status(self, team, gdate):
        return self.by.get((team, gdate), {}) if self.ok else {}
