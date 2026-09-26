"""
intl_view.py — 🌐 INTERNATIONAL tab (25/9/2026, εντολη Στελιου): προβολες εθνικων (Nations League 2026-27 A-D + προκριματικα
AFCON 2027) σε MATCH CARDS οπως τα Europe / Match Projections tabs (ιδιο CSS απο cards.py).
Διαβαζει intl_projections_dashboard.json (intl_dashboard_build.py — απο 25/9 τρεχει ΚΑΙ στο Actions μεσω scanner_tick.sh).
  Μοντελο 1 = H (rating H3 + στρωμα αξιας ροστερ) · Μοντελο 2 = A (αγκυρα αγορας λ=0.3 χωρις αξια) · Μοντελο 3 = AV (αγκυρα + αξια)
Καθε καρτα: ομαδες + Elo · ΚΑΘΕΤΑ οι 3 εκδοχες (1/Χ/2 %) και απο κατω η ΑΓΟΡΑ (implied % + τιμες) · picks (badges ανα εκδοχη)
· πανελ «Γραμμες & picks» (fair AH/over ανα εκδοχη στη γραμμη της πηγης + αγορα) και «Ratings» (Elo, αξια, xG, T).
ΑΓΟΡΑ (25/9, εντολη Στελιου): TOA Pinnacle (αλλιως Matchbook) απο τον scanner (intl_odds_scan.py) οταν υπαρχει για το ματς —
badge πηγης + ωρα snapshot· αλλιως Nowgoal Crown/SBOBET (fallback). ΣΚΙΑ / ΧΑΡΤΙΝΟ — δεν παιζεται live.
"""
import os, json, re, datetime

import cards  # CARD_CSS / FONTS / _logo / esc — τα κοινα match cards

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_F = os.path.join(ROOT, 'intl_projections_dashboard.json')
LOGO = cards.LOGO

COMPS = ['NL A', 'NL B', 'NL C', 'NL D']      # 25/9: AFCONQ αφαιρεθηκε (Αφρικη κλειστη, αποφαση Στελιου)
COMP_LABEL = {'NL A': 'Nations League A', 'NL B': 'Nations League B', 'NL C': 'Nations League C', 'NL D': 'Nations League D',
              'AFCONQ': 'AFCON 2027 προκριματικα'}
VERS = [('H', 'H + αξια'), ('A', 'Αγκυρα'), ('AV', 'Αγκυρα + αξια')]
VER_NUM = {'H': 'Μοντελο 1', 'A': 'Μοντελο 2', 'AV': 'Μοντελο 3'}
VER_COLOR = {'H': '#7ea2ff', 'A': '#f5b731', 'AV': '#3ec98f'}
OVER_KEY = {'H': 'over', 'A': 'over_A', 'AV': 'over_AV'}
HOWTO = [
    '**Τρια μοντελα, καθετα:** **Μοντελο 1 = H + αξια** (rating H3: Elo+xElo, πραγματικες εδρες, HFA ομοσπονδιας, + στρωμα αξιας ροστερ) · '
    '**Μοντελο 2 = Αγκυρα** (rating δεμενο στην αγορα, λ=0.3, χωρις αξια) · **Μοντελο 3 = Αγκυρα + αξια**. '
    'Απο κατω η **Αγορα** (implied % χωρις γκανιοτα + τιμες). Ολα βλεπουν την ΙΔΙΑ αγορα.',
    '**Αγορα (πηγη ανα ματς, badge):** **Pinnacle** (αλλιως **Matchbook**) απο το Odds API μεσω του scanner (GitHub Actions, οπως το υπολοιπο '
    'dashboard· ~45λεπτο refresh μακρια απο ΚΟ, καθε τικ στο 6ωρο προ ΚΟ)· οταν δεν υπαρχει TOA γραμμη (π.χ. AFCON προκριματικα — δεν εχει '
    'key στο TOA — ή παυση scanner) → **Crown/SBOBET** (Nowgoal, snapshot laptop). Η ωρα του snapshot φαινεται στο badge (hover).',
    '**Γραμμες & picks:** fair AH = τιμη του καθε μοντελου στη γραμμη της πηγης ΜΕ τη γκανιοτα της αγορας (οπως εγχωρια/Ευρωπη, 26/9), edge = αναμενομενη αποδοση στην πραγματικη τιμη· '
    'κανονες pick (ιδιοι σε καθε πηγη): AH dog/φαβορι ≥0.5 σε 1.70-2.10 με edge ≥10% · (1Χ2 φαβορι: αφαιρεθηκε 26/9 — δεν παιζεται) · '
    'νεκρη ομαδα = κανενα pick · OVER edge ≥8% ΚΑΙ κοντινο (|ΔElo| <150) ή νοκ-αουτ. Η «Αγκυρα» δινει μονο AH picks (οπως τρεχει απο 21/9).',
    '**ΣΚΙΑ / ΧΑΡΤΙΝΟ:** τιποτα εδω δεν παιζεται live — καταγραφη για κριση με πραγματικα δεδομενα (ledger). '
    '**Bovada** (NL B-D, 25/9): οπου δεν υπαρχει Pinnacle, 1Χ2 + AH + O/U απο Bovada (Odds API) με **μειωμενη γκανιοτα**: '
    'αφαιρειται η διαφορα γκανιοτας Bovada − Pinnacle ανα αγορα, μετρημενη στα ματς League A της **ιδιας μερας** (κοντα στη σεντρα ~2 μοναδες, '
    '3-5 μερες πριν ~0.5)· ετσι ενα group με ακριβοτερο Bovada κραταει την επιπλεον γκανιοτα του. Hover στο badge = ωμες τιμες & γκανιοτες.',
    '**Betfair (με αστερισκο)** (NL B-D, 25/9): οπου δεν υπαρχει ουτε Pinnacle ουτε Bovada, το **1Χ2** ερχεται απο Betfair Exchange (Odds API) με **προστιθεμενη τη μεση γκανιοτα 1Χ2 '
    'του Pinnacle** (~4.4%) ωστε να συγκρινεται· το Betfair στο Odds API ΔΕΝ εχει handicap/γκολ → AH & O/U μενουν Crown (Nowgoal). '
    'Ρηχες αγορες Betfair (γκανιοτα back >6%) αγνοουνται. Hover στο «Αγορα» δειχνει τις ωμες τιμες.',
]
SRC_LABEL = {'pinnacle': 'Pinnacle', 'matchbook': 'Matchbook', 'crown': 'Crown', 'sbobet': 'SBOBET', 'betfair_ex_eu': 'Betfair', 'bovada': 'Bovada'}
SRC_CLASS = {'pinnacle': 'pin', 'matchbook': 'mbk', 'crown': 'ng', 'sbobet': 'ng', 'betfair_ex_eu': 'bf', 'bovada': 'bov'}

esc = cards.esc


def market_src(m):
    """(label πηγης, εγγραφη γραμμων της πηγης) — TOA πρωτα, αλλιως Nowgoal· ('', {}) αν τιποτα."""
    mk = m.get('market') or {}
    src = mk.get('source')
    if src and mk.get(src):
        return src, mk[src]
    for lab in ('pinnacle', 'matchbook', 'bovada', 'crown', 'sbobet', 'betfair_ex_eu'):      # παλιο json χωρις 'source'
        if mk.get(lab):
            return lab, mk[lab]
    return '', {}


def x12_src(m):
    """(label, εγγραφη) για το 1Χ2: Betfair (+γκανιοτα Pinnacle) οταν η κυρια πηγη δεν ειναι Pinnacle/Matchbook (25/9)."""
    mk = m.get('market') or {}
    lab = mk.get('x12_source')
    if lab and mk.get(lab) and mk[lab].get('o1'):
        return lab, mk[lab]
    return market_src(m)


def _bov_tip(m):
    """hover Bovada: ωμες τιμες + γκανιοτα πριν/μετα + διαφορα Bovada−Pinnacle της μερας (League A)."""
    b = (m.get('market') or {}).get('bovada') or {}
    if not b:
        return ''
    out = ['Bovada (Odds API) με γκανιοτα «σαν Pinnacle»: αφαιρεθηκε η διαφορα Bovada−Pinnacle των ματς League A της ιδιας μερας']
    for mk, lab, fs in (('h2h', '1Χ2', ('h', 'd', 'a')), ('spreads', 'AH', ('oh', 'oa')), ('totals', 'O/U', ('over', 'under'))):
        if b.get(f'gap_{mk}') is None:
            continue
        raw = '/'.join(str(b.get('raw_' + f, '?')) for f in fs)
        day = b.get(f'gap_{mk}_day'); day = 'προεπιλογη' if day == 'default' else day
        out.append(f"{lab}: ωμες {raw} · γκανιοτα {b.get(f'over_{mk}')}% → {b.get(f'over_{mk}_adj')}% (−{b.get(f'gap_{mk}')} μον., μετρηση {day})")
    return ' | '.join(out)


def _x12_tip(m, lab):
    mk = m.get('market') or {}
    if lab == 'bovada':
        return _bov_tip(m)
    if lab != 'betfair_ex_eu':
        return ''
    b = mk.get(lab) or {}
    pm = mk.get('pin_margin')
    return (f'Betfair Exchange 1Χ2 (Odds API, {mk.get("x12_ts") or ""} UTC)· ωμες back {b.get("raw_h", "?")}/{b.get("raw_d", "?")}/{b.get("raw_a", "?")} '
            f'+ μεση γκανιοτα 1Χ2 Pinnacle {pm if pm is not None else "4.4"}%')


def _no_x12(pick):
    """26/9/2026 (Στελιος): χωρις «1Χ2 φαβορι» (κιτρινο σημα) — δεν παιζεται ποτε. Κραταει τα υπολοιπα κομματια (DOG/FAV/OVER…)."""
    if not isinstance(pick, str):
        return pick
    parts = [x.strip() for x in pick.split(' · ') if x.strip() and not x.strip().startswith(('1Χ2', '1X2'))]
    return ' · '.join(parts)


def load():
    try:
        with open(DATA_F, encoding='utf-8') as fh:
            d = json.load(fh)
    except Exception:
        return None
    try:      # 26/9: αποστολες FotMob πριν τη σεντρα (intl_lineups_check.py)
        LU = json.load(open(os.path.join(os.path.dirname(DATA_F), 'intl_lineups.json'), encoding='utf-8'))
    except Exception:
        LU = {}
    led = {}
    try:      # 26/9: τα ανοιχτα picks του ημερολογιου (συναινεση) -> καταστση στην καρτα (🟢 ενεργο / 🟠 επεσε + τιμη που χρειαζεται)
        for ln in open(os.path.join(os.path.dirname(DATA_F), 'intl_picks_ledger.jsonl'), encoding='utf-8'):
            r = json.loads(ln)
            if r.get('stream') == 'ΣΥΝΑΙΝΕΣΗ' and not r.get('removed') and r.get('result') is None:
                led.setdefault((r['comp'], r['home'], r['away'], r['ko']), []).append(r)
    except Exception:
        pass
    for c in d.get('comps', []):
        for m in c.get('matches', []):
            if isinstance(m.get('picks'), dict):
                m['picks'] = {k: _no_x12(v) for k, v in m['picks'].items()}
            m['ledger'] = led.get((c.get('comp'), m.get('home'), m.get('away'), m.get('utc')), [])
            m['lineup'] = LU.get(f"{c.get('comp')}|{m.get('home')}|{m.get('away')}|{m.get('utc')}")
    return d


def comp_matches(data, comp):
    for c in (data or {}).get('comps', []):
        if c.get('comp') == comp:
            return c.get('matches', [])
    return []


def has_anchor(matches):
    return any((m.get('versions') or {}).get('A') for m in matches)


def versions_for(matches):
    return [x for x in VERS if x[0] == 'H' or has_anchor(matches)]


def _real(p):
    return bool(p) and not p.startswith('ΟΧΙ') and not p.startswith('(')


def _edge_class(e):
    if e is None:
        return 'dim'
    return 'g' if e >= 10 else ('y' if e >= 5 else ('n' if e >= 0 else 'r'))


def _edge_span(e):
    if e is None:
        return '<span class="e dim">—</span>'
    return f'<span class="e {_edge_class(e)}">{e:+.0f}%</span>'


def _fmt_line(x):
    if x is None:
        return '—'
    return '0.00' if abs(x) < 1e-9 else f'{x:+.2f}'


_GR_DAYS = ['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ']


def _ko_fmt(utc):
    """ωρα Ελλαδας (26/9: σωστη θερινη/χειμερινη μεσω Europe/Athens, οχι σταθερο +3) — «Σαβ 26/9 19:00»."""
    try:
        d = datetime.datetime.fromisoformat(str(utc).replace('Z', '').replace('+00:00', '')[:16]).replace(tzinfo=datetime.timezone.utc)
        try:
            from zoneinfo import ZoneInfo
            d = d.astimezone(ZoneInfo('Europe/Athens'))
        except Exception:
            d = d + datetime.timedelta(hours=3)
        return f'{_GR_DAYS[d.weekday()]} {d.day}/{d.month} {d:%H:%M}'
    except Exception:
        return str(utc)[:16]


def _badge_parts(pick):
    """pick string -> λιστα (cls, κειμενο, title)."""
    out = []
    for part in [p.strip() for p in str(pick or '').split(' · ') if p.strip()]:
        m = re.match(r'^(.*?)\s*\(([^)]*)\)\s*$', part)
        core, note = (m.group(1), m.group(2)) if m else (part, '')
        if part.startswith('DOG'):
            cls = 'dog'
        elif part.startswith('FAV'):
            cls = 'fav'
        elif part.startswith('1Χ2') or part.startswith('1X2'):
            cls = 'x12'; core = core.replace('≥75%', '').replace('  ', ' ')
        elif part.startswith('OVER'):
            cls = 'over'
        elif part.startswith('ΟΧΙ'):
            cls = 'dead'; core = '✝ νεκρη'
        elif part.startswith('('):
            cls = 'oor'; core = 'εκτος κανονα'; note = part.strip('()')
        else:
            cls = 'oor'
        out.append((cls, core.strip(), note))
    return out


def _badges(*picks, real_only=False):
    h = ''
    for p in picks:
        for cls, core, note in _badge_parts(p):
            if real_only and cls in ('oor', 'dead'):
                continue
            h += f'<span class="bd {cls}" title="{esc(note)}">{esc(core)}</span>'
    return h


def _pick_keys(m, v):
    """συνολο «κλειδιων» pick (τυπος+πλευρα) για συγκριση εκδοχων: DOG 2 / FAV 1 / 1Χ2 γηπ / OVER 2.5."""
    keys = set()
    for p in (m['picks'].get(v, ''), m['picks'].get(OVER_KEY[v], '')):
        for part in [x.strip() for x in str(p or '').split(' · ') if x.strip()]:
            if not _real(part):
                continue
            w = part.split()
            if w[0] in ('DOG', 'FAV', 'OVER'):
                keys.add(f'{w[0]} {w[1]}')
            elif w[0].startswith('1'):
                keys.add('1Χ2 ' + ('γηπ' if 'γηπ' in part else 'εκτος'))
    return keys


def summary(matches):
    vers = [v for v, _ in versions_for(matches)]
    s = {'n': len(matches), 'vers': vers,
         'ah': {v: sum(_real(m['picks'].get(v, '')) for m in matches) for v in vers},
         'over': {v: sum(_real(m['picks'].get(OVER_KEY[v], '')) for m in matches) for v in vers},
         'dead': sum(1 for m in matches if m.get('dead')),
         'with_line': sum(1 for m in matches if market_src(m)[1].get('ah_line') is not None),
         'toa': sum(1 for m in matches if market_src(m)[0] in ('pinnacle', 'matchbook', 'bovada'))}
    keys = {v: [_pick_keys(m, v) for m in matches] for v in vers}
    s['any'] = {v: sum(1 for k in keys[v] if k) for v in vers}
    if len(vers) == 3:
        s['common_all'] = sum(1 for i in range(len(matches)) if keys['H'][i] & keys['A'][i] & keys['AV'][i])
        s['pairs'] = {f'{a}∩{b}': sum(1 for i in range(len(matches)) if keys[a][i] & keys[b][i])
                      for a, b in (('H', 'A'), ('H', 'AV'), ('A', 'AV'))}
    return s


def summary_html(matches):
    s = summary(matches)
    parts = [f'<b style="color:{VER_COLOR[v]}">{VER_NUM[v]}</b> {s["ah"][v]} AH/1Χ2 + {s["over"][v]} over' for v in s['vers']]
    h = (f'<div class="isum">Picks (χαρτινα) σε {s["n"]} ματς · {s["with_line"]} με γραμμη AH · {s["toa"]} με αγορα Odds API (Pinnacle/Bovada), '
         f'{s["with_line"] - min(s["toa"], s["with_line"])} Nowgoal · {s["dead"]} νεκρα &nbsp;|&nbsp; ' + ' · '.join(parts))
    if 'common_all' in s:
        h += (f' &nbsp;|&nbsp; <b>κοινα και στα 3</b>: {s["common_all"]} · '
              + ' · '.join(f'{k.replace("H", "Μ1").replace("AV", "Μ3").replace("A", "Μ2")} {v}' for k, v in s['pairs'].items()))
    return h + '</div>'


# ---------------------------------------------------------------- CSS (συμπληρωμα στο cards.CARD_CSS)
INTL_CSS = """
<style>
.mid{min-width:300px;}
.vrow{display:flex;align-items:center;gap:6px;}
.vrow .vl{width:74px;text-align:right;font-size:8px;letter-spacing:.3px;text-transform:uppercase;color:#5a6b8c;line-height:1.1;}
.vrow .vl b{display:block;font-size:9px;letter-spacing:.5px;}
.vrow .pills .pill{font-size:12px;padding:3px 0;}
.vrow.mk .pill{background:#0f1830;border:1px solid #26324e;color:#cdd8ee;}
.vrow.mk .pill small{display:block;font-size:8.5px;color:#6b7fa3;font-weight:400;line-height:1;}
.vrow.mk .pill.val{color:#34d17a;} .vrow.mk .pill.against{color:#f04f5a;}
.pill.fav{font-weight:800;} .pill.dimp{opacity:.55;}
.vsep{width:100%;border-top:1px dashed #1e2d47;margin:2px 0 1px;}
.flags{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;padding:6px 12px 2px;font-size:10px;}
.flags .dead{color:#ff6b6b;font-weight:700;} .flags .call{color:#f3c74b;cursor:help;text-align:center;}
.kotop{display:flex;justify-content:space-between;padding:7px 15px 0;font-size:10.5px;color:#8fa3c8;font-family:'JetBrains Mono',monospace;}
.kotop b{color:#cdd8ee;font-weight:600;}
.pkrow{display:flex;gap:6px;align-items:center;justify-content:center;flex-wrap:wrap;padding:5px 12px 7px;font-size:9px;color:#5a6b8c;}
.pkrow .vk{font-weight:700;letter-spacing:.4px;}
.bd{display:inline-block;padding:1px 6px;border-radius:8px;font-weight:700;font-size:9.5px;letter-spacing:.3px;margin:1px 2px;color:#0a0f1e;cursor:help;font-family:'DM Sans',sans-serif;}
.lurow{padding:5px 12px;border-top:1px solid #16203a;font-size:10.5px;color:#c7d3ea;} .lurow .lu-t{color:#6b7fa3;margin-left:6px;} .lurow .lu-b{margin-top:3px;line-height:1.45;font-family:'DM Sans',sans-serif;}
.bd.led{background:#1a2233;color:#c7d3ea;border:1px solid #26324e;font-weight:400;white-space:normal;} .bd.led.on{border-color:#1e4a33;} .bd.led.off{border-color:#7a5a1a;color:#f3c74b;}
.bd.dog{background:#34d17a;} .bd.fav{background:#4b7cf3;color:#fff;} .bd.x12{background:#f3c74b;} .bd.over{background:#b17af3;color:#fff;}
.bd.cons{background:#123524;color:#7ee2a8;border:1px solid #34d17a;font-size:10px;padding:2px 8px;} .pkrow.cons{padding-bottom:2px;}
.bd.dead{background:#2a1a1f;color:#ff6b6b;border:1px solid #ff6b6b;font-weight:600;} .bd.oor{background:#151c2e;color:#6b7fa3;border:1px solid #26324e;font-weight:400;}
.e{font-weight:700;font-family:'JetBrains Mono',monospace;} .e.g{color:#34d17a;} .e.y{color:#f3c74b;} .e.n{color:#6b7fa3;font-weight:400;} .e.r{color:#ff6b6b;font-weight:400;} .e.dim{color:#3d4a66;font-weight:400;}
.src{display:inline-block;padding:0 5px;border-radius:6px;font-family:'DM Sans',sans-serif;font-weight:700;font-size:8.5px;letter-spacing:.5px;text-transform:uppercase;cursor:help;vertical-align:middle;}
.src.pin{background:#1d3b6e;color:#9cc0ff;border:1px solid #2f5aa8;} .src.mbk{background:#2a3d1f;color:#a8e07a;border:1px solid #4d7a33;}
.src.ng{background:#3a2a12;color:#f3c74b;border:1px solid #7a5a1a;} .src.bf{background:#3a2412;color:#ffb36b;border:1px solid #8a5a2a;} .src.bov{background:#2e1f3d;color:#c9a3ff;border:1px solid #5e3f8a;} .src.none{background:#151c2e;color:#3d4a66;border:1px solid #26324e;}
table.lt{border-collapse:collapse;margin:8px auto 4px;font-size:11px;font-family:'JetBrains Mono',monospace;}
table.lt th{font-size:8px;color:#5a6b8c;letter-spacing:.8px;text-transform:uppercase;font-weight:600;padding:3px 9px;border-bottom:1px solid #1e2d47;font-family:'DM Sans',sans-serif;}
table.lt td{padding:4px 9px;text-align:center;color:#cdd8ee;border-bottom:1px solid #141d33;white-space:nowrap;}
table.lt td.vn{text-align:left;font-family:'DM Sans',sans-serif;font-weight:700;font-size:10px;letter-spacing:.3px;}
table.lt td.vn small{display:block;font-weight:400;color:#5a6b8c;font-size:8.5px;letter-spacing:0;}
table.lt tr.mkr td{border-top:2px solid #26324e;color:#e8edf8;background:#0d1426;}
table.lt tr.mkr td.vn{color:#cdd8ee;}
table.lt .ln{color:#f5b731;font-weight:700;} table.lt .fair{color:#7ea2ff;}
table.lt .sec{display:block;color:#5a6b8c;font-size:9px;font-weight:400;}
.leg{font-size:8px;color:#5a6b8c;text-align:center;padding:2px 10px 8px;}
.isum{margin-top:4px;padding:7px 10px;background:#0f1830;border:1px solid #26324e;border-radius:9px;color:#8fa3c8;font-size:11px;font-family:'DM Sans',sans-serif;}
.isum b{color:#e8edf8;}
.note{margin:0 0 6px;color:#f3c74b;font-size:11px;font-family:'DM Sans',sans-serif;}
.detail{grid-template-columns:1fr 1fr;}
</style>
"""


def _started(m):
    """True αν το ΚΟ περασε (UTC) — τοτε η γραμμη που δειχνουμε ειναι η ΠΑΓΩΜΕΝΗ προ-ΚΟ = closing (καμια in-play τιμη)."""
    try:
        ko = datetime.datetime.fromisoformat(str(m.get('utc'))[:16]).replace(tzinfo=datetime.timezone.utc)
        return datetime.datetime.now(datetime.timezone.utc) >= ko
    except Exception:
        return False


def _src_badge(m):
    src, rec = market_src(m)
    mk = m.get('market') or {}
    ts = mk.get('ts') or ''
    if not src:
        return '<span class="src none" title="χωρις γραμμη">—</span>'
    tip = f'{SRC_LABEL[src]} · snapshot {ts} UTC' if ts else SRC_LABEL[src]
    tip += ' · Odds API (scanner)' if src in ('pinnacle', 'matchbook', 'bovada') else ' · Nowgoal (laptop)'
    if src == 'bovada':
        tip += ' · ' + _bov_tip(m)
    lab = SRC_LABEL[src]
    if _started(m):
        tip += ' · ΚΟ περασε: τελευταια προ-ΚΟ γραμμη (closing), οχι in-play'
        lab += ' · closing'
    return f'<span class="src {SRC_CLASS[src]}" title="{esc(tip)}">{lab}</span>'


def _pill(v, fav, color=None):
    """pill πιθανοτητας μοντελου: χρωμα φαβορι (πρασινο/κοκκινο οπως cards) στο μεγαλυτερο."""
    if v is None:
        return '<div class="pill dimp" style="background:#0f1830;color:#3d4a66">—</div>'
    if color:
        bg = cards._BG.get(color, 'rgba(143,163,200,.10)')
        cls = 'pill fav' if fav else 'pill'
        return f'<div class="{cls}" style="background:{bg};color:{color};border:1px solid {color}44">{v:.0f}%</div>'
    return f'<div class="pill pd">{v:.0f}%</div>'


def _model_row(v, V, lead=None):
    """μια καθετη σειρα μοντελου: ετικετα αριστερα + 3 pills 1/Χ/2 (%)."""
    lab = f'<span class="vl" style="color:{VER_COLOR[v]}"><b>{VER_NUM[v]}</b>{dict(VERS)[v]}</span>'
    if not V:
        return f'<div class="vrow">{lab}<div class="pills">{_pill(None, False)}{_pill(None, False)}{_pill(None, False)}</div></div>'
    p1, px, p2 = V['p1'], V['px'], V['p2']
    hc = '#34d17a' if p1 > p2 else ('#f04f5a' if p1 < p2 else '#8fa3c8')
    ac = '#34d17a' if p2 > p1 else ('#f04f5a' if p2 < p1 else '#8fa3c8')
    fav = max(p1, px, p2)
    return (f'<div class="vrow">{lab}<div class="pills">{_pill(p1, p1 == fav, hc)}{_pill(px, px == fav)}'
            f'{_pill(p2, p2 == fav, ac)}</div></div>')


def _market_row(m, ref):
    """σειρα ΑΓΟΡΑΣ: implied % (χωρις γκανιοτα) + τιμη· χρωμα vs Μοντελο 1 (πρασινο = αγορα πληρωνει καλυτερα)."""
    src, c = x12_src(m)
    tip = _x12_tip(m, src)
    lab = (f'<span class="vl" style="color:#cdd8ee" title="{esc(tip)}"><b>Αγορα</b>{SRC_LABEL.get(src, "—")}'
           f'{"*" if src == "betfair_ex_eu" else ""}{" · closing" if src and _started(m) else ""}</span>')
    if not c.get('o1'):
        return f'<div class="vrow mk">{lab}<div class="pills">{_pill(None, False)}{_pill(None, False)}{_pill(None, False)}</div></div>'
    o = (c['o1'], c['ox'], c['o2'])
    s3 = sum(1.0 / x for x in o)
    imp = [100.0 / x / s3 for x in o]
    pills = ''
    for i, (pr, od) in enumerate(zip(imp, o)):
        cls = ''
        if ref:
            our = (ref['p1'], ref['px'], ref['p2'])[i]
            cls = 'val' if pr < our * 0.9 else ('against' if pr > our * 1.1 else '')
        pills += f'<div class="pill {cls}">{pr:.0f}%<small>{od:.2f}</small></div>'
    return f'<div class="vrow mk">{lab}<div class="pills">{pills}</div></div>'


def _flags(m):
    out = []
    if m.get('dead'):
        out.append(f'<span class="dead" title="{esc(m["dead"])}">✝ νεκρη: {esc(m["dead"])}</span>')
    if m.get('callups'):
        # 26/9 (Στελιος: «τι ειναι το κλησεις hover;»): ΟΡΑΤΟ — οι πιο πολυτιμοι ΤΑΚΤΙΚΟΙ παικτες που λειπουν απο την τρεχουσα κληση TM
        # (αξια SciSports)· ηδη μεσα στην αξια ροστερ (Μ1/Μ3), δεν χρειαζεται χειροκινητη διορθωση.
        out.append('<span class="call" title="Παίκτες με ≥2 βασικές συμμετοχές στην εθνική και αξία ≥30% του πιο ακριβού της ομάδας, που ΔΕΝ είναι στην τρέχουσα κλήση '
                   'του Transfermarkt (και χειροκίνητες απουσίες) · αξία παίκτη σε εκ. € · ήδη μέσα στην αξία ρόστερ των Μ1/Μ3">🚑 Απουσίες: ' + esc(m['callups']).replace(' | ', ' · ') + '</span>')
    return f'<div class="flags">{"".join(out)}</div>' if out else ''


def _lineup_row(m):
    """26/9/2026: επισημες αποστολες FotMob (~60′ πριν) → αξια των 23 που ντυθηκαν, απουσιες, νεοι, edge Μ1/Μ3 πριν→μετα, συναινεση."""
    L = m.get('lineup')
    if not L or not L.get('text'):
        return ''
    body = '<br>'.join(esc(x) for x in L['text'].splitlines()[1:])
    return (f'<div class="lurow"><span class="vk" style="color:#7ea2ff">📋 ΑΠΟΣΤΟΛΕΣ</span>'
            f'<span class="lu-t">({L.get("min_before", "?")}′ πριν{" · ενημερωση" if L.get("update") else ""})</span><div class="lu-b">{body}</div></div>')


def _consensus_row(m):
    """25/9 (αποφαση Στελιου): το ΚΑΝΟΝΙΚΟ pick = συναινεση ≥2 απο 3 μοντελα (handicap + over)."""
    cs = m.get('consensus') or []
    led = _ledger_items(m)
    if not cs:
        return (f'<div class="pkrow cons"><span class="vk" style="color:#f5b731">ΗΜΕΡΟΛΟΓΙΟ</span>{led}</div>' if led else '')
    items = []
    for c in cs:
        if c['mkt'] == 'OVER':
            txt = f"Over {c['line']:g} @{c['odds']:.2f}"
        else:
            team = m['home'] if c['side'] == 1 else m['away']
            txt = f"{esc(team)} {c['line']:+g} @{c['odds']:.2f}"
        items.append(f'<span class="bd cons" title="edge ανα μοντελο: ' + esc(', '.join(f"{k} {v*100:+.0f}%" for k, v in (c.get('edges') or {}).items()))
                     + f'">✅ {txt} · edge ≥{c["edge"]*100:.0f}% · {esc(c.get("models", ""))}</span>')
    return f'<div class="pkrow cons"><span class="vk" style="color:#34d17a">PICK (συναινεση)</span>{"".join(items)}{led}</div>'


def _ledger_items(m):
    """26/9/2026: καθε ανοιχτο pick του ημερολογιου για το ματς — 🟢 ισχυει ακομα / 🟠 επεσε (τωρινη τιμη, edge ανα μοντελο,
    τιμη για να ξαναγινει pick). Ιδια λογικη με τα Telegram «επεσε / ξανα pick» (intl_pick_status)."""
    try:
        import intl_pick_status as ps
    except Exception:
        return ''
    out = []
    try:
        if datetime.datetime.fromisoformat(str(m['utc'])).replace(tzinfo=datetime.timezone.utc) <= datetime.datetime.now(datetime.timezone.utc):
            return ''          # αρχισε — η κατασταση δεν εχει πια νοημα
    except Exception:
        pass
    for r in m.get('ledger') or []:
        st = ps.status(r, m)
        if st is None:
            continue
        fs = str(r.get('first_seen', ''))
        when = f'{int(fs[8:10])}/{int(fs[5:7])} {fs[11:16]}' if len(fs) >= 16 else fs
        if st['active']:
            out.append(f'<span class="bd led on" title="{esc(ps.describe(r, st, m["home"], m["away"]))}">📒 μπηκε {esc(r["label"])} ({when}) · 🟢 ισχυει</span>')
        else:
            out.append(f'<span class="bd led off">📒 μπηκε {esc(r["label"])} ({when}) · 🟠 επεσε — {esc(ps.describe(r, st, m["home"], m["away"]))}</span>')
    return ''.join(out)


def _picks_row(m, vers):
    parts = []
    for v, _ in vers:
        b = _badges(m['picks'].get(v, ''), m['picks'].get(OVER_KEY[v], ''), real_only=True)
        if b:
            parts.append(f'<span class="vk" style="color:{VER_COLOR[v]}">Μ{list(VER_NUM).index(v) + 1}</span>{b}')
    dead = _badges(m['picks'].get('H', '')) if m.get('dead') else ''
    if not parts:
        return f'<div class="pkrow">{dead or "κανενα pick"}</div>'
    return f'<div class="pkrow">{"".join(parts)}</div>'


def _lines_pane(m, vers):
    """Πανελ «Γραμμες & picks»: μια σειρα ανα μοντελο (xG, fair AH @γραμμη πηγης + edge, over edge, picks) και απο κατω η αγορα."""
    src, c = market_src(m)
    ln = c.get('ah_line')
    ou = c.get('ou_line')
    try:
        S_AH = (1.0 / c['oh'] + 1.0 / c['oa']) if (c.get('oh') and c.get('oa')) else 1.0
    except Exception:
        S_AH = 1.0
    h = ('<table class="lt"><tr><th></th><th>xG · T</th>'
         f'<th>fair γηπ {_fmt_line(ln)}</th><th>fair φιλοξ {_fmt_line(-ln) if ln is not None else "—"}</th>'
         f'<th>over {ou:g}</th><th>pick</th></tr>' if ou is not None else
         '<table class="lt"><tr><th></th><th>xG · T</th>'
         f'<th>fair γηπ {_fmt_line(ln)}</th><th>fair φιλοξ {_fmt_line(-ln) if ln is not None else "—"}</th>'
         '<th>over</th><th>pick</th></tr>')
    for v, lab in vers:
        V = (m.get('versions') or {}).get(v)
        name = f'<td class="vn" style="color:{VER_COLOR[v]}">{VER_NUM[v]}<small>{lab}</small></td>'
        if not V:
            h += f'<tr>{name}<td colspan="5" class="e dim">—</td></tr>'
            continue
        e = ((m.get('edges') or {}).get(v) or {}).get(src) or {}
        xg = f'{V["xg_h"]:.2f}-{V["xg_a"]:.2f}' + (f' <span class="sec">T {V["T"]:.2f}</span>' if V.get('T') is not None else '')
        if e.get('fair_h') is not None:
            # 26/9 (Στελιος): fair ΜΕ τη γκανιοτα της αγορας (ιδιο ζευγος AH της πηγης, ισομερως — οπως εγχωρια/Ευρωπη) ωστε να
            # συγκρινεται αμεσα με την τιμη της αγορας· το edge μενει οπως ηταν (υπολογιζεται στην πραγματικη τιμη). Hover = χωρις γκανιοτα.
            fvh, fva = e['fair_h'] / S_AH, e['fair_a'] / S_AH
            fh = (f'<span class="fair" title="χωρις γκανιοτα {e["fair_h"]:.2f}">{fvh:.2f}</span> {_edge_span(e["ah_home"])}')
            fa = (f'<span class="fair" title="χωρις γκανιοτα {e["fair_a"]:.2f}">{fva:.2f}</span> {_edge_span(e["ah_away"])}')
        else:
            fh = fa = '<span class="e dim">—</span>'
        ov = _edge_span(e.get('over')) if e.get('over') is not None else '<span class="e dim">—</span>'
        if e.get('p_over') is not None:
            ov = f'{e["p_over"]:.0f}% {ov}'
        b = _badges(m['picks'].get(v, ''), m['picks'].get(OVER_KEY[v], '')) or '<span class="e dim">—</span>'
        h += f'<tr>{name}<td>{xg}</td><td>{fh}</td><td>{fa}</td><td>{ov}</td><td>{b}</td></tr>'
    # αγορα απο κατω
    xs, xc = x12_src(m)
    x12 = f'{xc["o1"]:.2f} / {xc["ox"]:.2f} / {xc["o2"]:.2f}' if xc.get('o1') else '—'
    if xs != src and xc.get('o1'):
        x12 += f'<span class="sec" title="{esc(_x12_tip(m, xs))}">{SRC_LABEL.get(xs, xs)}* · AH/OU {SRC_LABEL.get(src, "—")}</span>'
    ah = f'<span class="ln">{_fmt_line(ln)}</span> {c["oh"]:.2f} / {c["oa"]:.2f}' if ln is not None else '—'
    if m.get('init_ah') and m['init_ah'] not in ('—', 'nan'):
        ah += f'<span class="sec">αρχικη {esc(m["init_ah"])}</span>'
    out = f'<span class="ln">{ou:g}</span> {c["over"]:.2f} / {c["under"]:.2f}' if ou is not None else '—'
    sec = ''
    if src in ('pinnacle', 'matchbook', 'bovada'):
        n = (m.get('market') or {}).get('crown') or {}
        if n.get('ah_line') is not None:
            sec = (f'<span class="sec">Crown {_fmt_line(n["ah_line"])} {n["oh"]:.2f}/{n["oa"]:.2f}'
                   + (f' · O/U {n["ou_line"]:g} {n["over"]:.2f}/{n["under"]:.2f}' if n.get('ou_line') is not None else '') + '</span>')
    h += (f'<tr class="mkr"><td class="vn">Αγορα {_src_badge(m)}<small>1 / Χ / 2 · AH · O/U</small></td>'
          f'<td>{x12}</td><td colspan="2">{ah}{sec}</td><td>{out}</td><td></td></tr></table>')
    h += ('<div class="leg">fair = τιμη μοντελου στη γραμμη της πηγης <b>με τη γκανιοτα της αγορας</b> (αμεσα συγκρισιμη· hover = χωρις γκανιοτα) · edge = αναμενομενη αποδοση (πρασινο ≥10%, κιτρινο ≥5%) · '
          'over: P(over) μοντελου + edge</div>')
    return h


def _ratings_pane(m, vers):
    Vh = (m.get('versions') or {}).get('H') or {}
    Va = (m.get('versions') or {}).get('A') or {}
    def col(side, name):
        rows = ''
        rh = f'R_{side}'
        rows += f'<div class="row"><span>Elo (H3)</span><b class="acc">{Vh.get(rh, 0):.0f}</b></div>'
        if Va:
            rows += f'<div class="row"><span>Elo αγκυρας</span><b>{Va.get(rh, 0):.0f}</b></div>'
        for v, lab in vers:
            V = (m.get('versions') or {}).get(v) or {}
            if V:
                rows += (f'<div class="row"><span style="color:{VER_COLOR[v]}">xG {VER_NUM[v][-1]}</span>'
                         f'<b>{V.get("xg_h" if side == "h" else "xg_a", 0):.2f}</b></div>')
        return f'<div class="inp"><div class="h">{esc(name)} ({"home" if side == "h" else "away"})</div>{rows}</div>'
    diff = ''.join(f'<span style="color:{VER_COLOR[v]}">{VER_NUM[v][-1]}: {((m.get("versions") or {}).get(v) or {}).get("diff", 0):+.0f}</span>&nbsp; '
                   for v, _ in vers if (m.get('versions') or {}).get(v))
    vadj = Vh.get('vadj')
    extra = (f'<div class="time" style="padding:0 12px 4px">Δ Elo (γηπ−φιλοξ, με εδρα): {diff}'
             + (f' · στρωμα αξιας {vadj:+.0f} Elo' if vadj is not None else '') + '</div>')
    return f'<div class="detail">{col("h", m["home"])}{col("a", m["away"])}</div>{extra}'


def card_html(m, vers, key):
    Vh = (m.get('versions') or {}).get('H') or {}
    hw, dw, aw = Vh.get('p1', 0), Vh.get('px', 0), Vh.get('p2', 0)
    rows = ''.join(_model_row(v, (m.get('versions') or {}).get(v)) for v, _ in vers)
    rows += '<div class="vsep"></div>' + _market_row(m, Vh)
    return f"""
<div class="card"><div class="kotop"><b>📅 {_ko_fmt(m.get('utc'))}</b><span>{'⏱ σε εξελιξη / τελος' if _started(m) else ''}</span></div><div class="sum">
  <div class="team">
    <div class="thead">{cards._logo(m.get('hid'))}<div class="tn">{esc(m['home'])}</div></div>
    <div class="meta"><span class="xg">Elo {Vh.get('R_h', 0):.0f}</span><span>xG {Vh.get('xg_h', 0):.2f}</span></div></div>
  <div class="mid">
    <div class="lbls"><span style="flex:none;width:80px"></span><span>Home</span><span>Draw</span><span>Away</span></div>
    {rows}
  </div>
  <div class="team away">
    <div class="thead">{cards._logo(m.get('aid'))}<div class="tn">{esc(m['away'])}</div></div>
    <div class="meta"><span>xG {Vh.get('xg_a', 0):.2f}</span><span class="xg">Elo {Vh.get('R_a', 0):.0f}</span></div></div>
</div>
<div class="pbar"><div style="width:{hw}%"></div><div style="width:{dw}%"></div><div style="width:{aw}%"></div></div>
{_flags(m)}{_lineup_row(m)}{_consensus_row(m)}{_picks_row(m, vers)}
<div class="tabs2">
  <button class="tbtn" onclick="tg('{key}','od',this)">Γραμμες &amp; picks</button>
  <button class="tbtn" onclick="tg('{key}','su',this)">Ratings</button>
</div>
<div id="od_{key}" class="pane" hidden>{_lines_pane(m, vers)}</div>
<div id="su_{key}" class="pane" hidden>{_ratings_pane(m, vers)}<div class="time">{_ko_fmt(m.get('utc'))}</div></div></div>"""


_TABS_CSS = """
<style>
.tabs2{display:flex;border-top:1px solid #1e2d47;}
.tbtn{flex:1;background:none;border:none;cursor:pointer;padding:5px;font-size:9px;color:#6b7fa3;
      letter-spacing:1px;text-transform:uppercase;font-family:'DM Sans',sans-serif;transition:all .12s;}
.tbtn:hover{color:#cdd8ee;background:#131c31;}
.tbtn.on{color:#e8edf8;background:#16203a;font-weight:600;}
.tbtn+.tbtn{border-left:1px solid #1e2d47;}
.pane{border-top:1px solid #16203a;}
</style>
<script>
function tg(mid, which, btn){
  var other = (which === 'od') ? 'su' : 'od';
  var me = document.getElementById(which + '_' + mid);
  var ot = document.getElementById(other + '_' + mid);
  var open = me.hidden;
  me.hidden = !open;
  if (ot) ot.hidden = true;
  var row = btn.parentElement;
  Array.prototype.forEach.call(row.children, function(b){ b.classList.remove('on'); });
  if (open) btn.classList.add('on');
}
</script>
"""


def cards_block(comp, matches):
    """CSS + fonts + ολες οι καρτες της διοργανωσης (για components.html)."""
    vers = versions_for(matches)
    h = cards.CARD_CSS + cards.FONTS + _TABS_CSS + INTL_CSS
    if not matches:
        return h + '<div class="isum">Δεν βρεθηκαν ματς.</div>'
    if len(vers) == 1:
        h += '<div class="note">Αγκυρα: μη διαθεσιμη για CAF (δεν εχει τρεξει intl_mkt_anchor) — μονο Μοντελο 1 (H + αξια, HFA 80).</div>'
    ck = re.sub(r'\W+', '_', comp)
    h += '<div class="wrap">' + ''.join(card_html(m, vers, f'{ck}_{i}') for i, m in enumerate(matches)) + '</div>'
    return h + summary_html(matches)


def table_html(comp, matches):
    """συμβατοτητα: παλιο ονομα → καρτες."""
    return cards_block(comp, matches)


def table_height(matches):
    vers = 1 if not has_anchor(matches) else 3
    return min(len(matches) * (150 + 26 * vers) + 90, 8000)
