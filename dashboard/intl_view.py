"""
intl_view.py — 🌐 INTERNATIONAL tab (25/9/2026, εντολη Στελιου): προβολες εθνικων (Nations League 2026-27 A-D + προκριματικα
AFCON 2027) με ΤΡΕΙΣ εκδοχες μοντελου διπλα-διπλα και την αγορα (Nowgoal Crown/SBOBET). ΣΚΙΑ / ΧΑΡΤΙΝΟ — δεν παιζεται live.
Διαβαζει intl_projections_dashboard.json (intl_dashboard_build.py, τρεχει τοπικα — ΟΧΙ στο Actions).
  H  = rating H3 + στρωμα αξιας ροστερ  ·  A = αγκυρα αγορας (λ=0.3) ΧΩΡΙΣ αξια  ·  AV = αγκυρα + αξια
Ενας πινακας ανα διοργανωση: ματς (λογοτυπα, ωρα UTC, ✝ νεκρη, ⚠ κλησεις) · ΑΓΟΡΑ Crown (1Χ2, AH, O/U) · ανα εκδοχη: 1/Χ/2 %, xG,
fair AH στη γραμμη Crown με edge χρωματιστο, badge pick · συνοψη picks ανα εκδοχη + κοινα.
"""
import os, json, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_F = os.path.join(ROOT, 'intl_projections_dashboard.json')
LOGO = 'https://images.fotmob.com/image_resources/logo/teamlogo/{}.png'

COMPS = ['NL A', 'NL B', 'NL C', 'NL D', 'AFCONQ']
COMP_LABEL = {'NL A': 'Nations League A', 'NL B': 'Nations League B', 'NL C': 'Nations League C', 'NL D': 'Nations League D',
              'AFCONQ': 'AFCON 2027 προκριματικα'}
VERS = [('H', 'H + αξια'), ('A', 'Αγκυρα'), ('AV', 'Αγκυρα + αξια')]
OVER_KEY = {'H': 'over', 'A': 'over_A', 'AV': 'over_AV'}
HOWTO = [
    '**Τρεις εκδοχες:** **H + αξια** = rating H3 (Elo+xElo, πραγματικες εδρες, HFA ομοσπονδιας) + στρωμα αξιας ροστερ · '
    '**Αγκυρα** = rating δεμενο στην αγορα (λ=0.3) χωρις αξια · **Αγκυρα + αξια** = αγκυρα + το ιδιο στρωμα αξιας. '
    'Ολες βλεπουν την ΙΔΙΑ αγορα (Crown/SBOBET, Nowgoal)· fair AH = τιμη μοντελου στη γραμμη Crown, edge = αναμενομενη αποδοση.',
    '**ΣΚΙΑ / ΧΑΡΤΙΝΟ:** τιποτα εδω δεν παιζεται live — καταγραφη για κριση με πραγματικα δεδομενα (ledger). '
    'Κανονες pick: AH dog/φαβορι ≥0.5 σε 1.70-2.10 με edge ≥10% · 1Χ2 φαβορι ≥75% · νεκρη ομαδα = κανενα pick · '
    'OVER edge ≥8% ΚΑΙ κοντινο (|ΔElo| <150) ή νοκ-αουτ. Η εκδοχη «Αγκυρα» δινει μονο AH picks (οπως τρεχει απο 21/9).',
    '**Snapshot:** οι γραμμες ειναι στιγμιοτυπο Nowgoal απο laptop (ημερομηνια στο caption) — δεν ανανεωνονται αυτοματα· '
    'AFCONQ: αγκυρα μη διαθεσιμη για CAF → μονο εκδοχη H (HFA 80).',
]


def load():
    try:
        with open(DATA_F, encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return None


def comp_matches(data, comp):
    for c in (data or {}).get('comps', []):
        if c.get('comp') == comp:
            return c.get('matches', [])
    return []


def has_anchor(matches):
    return any((m.get('versions') or {}).get('A') for m in matches)


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
            cls = 'x12'; core = core.replace(' φαβ ', ' φαβ ').replace('≥75%', '').replace('  ', ' ')
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


def _badges(*picks):
    h = ''
    for p in picks:
        for cls, core, note in _badge_parts(p):
            h += f'<span class="bd {cls}" title="{note}">{core}</span>'
    return h or '<span class="e dim">—</span>'


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
    vers = [v for v, _ in VERS if (v == 'H' or has_anchor(matches))]
    s = {'n': len(matches), 'vers': vers,
         'ah': {v: sum(_real(m['picks'].get(v, '')) for m in matches) for v in vers},
         'over': {v: sum(_real(m['picks'].get(OVER_KEY[v], '')) for m in matches) for v in vers},
         'dead': sum(1 for m in matches if m.get('dead')),
         'with_line': sum(1 for m in matches if (m.get('market', {}).get('crown') or {}).get('ah_line') is not None)}
    keys = {v: [_pick_keys(m, v) for m in matches] for v in vers}
    s['any'] = {v: sum(1 for k in keys[v] if k) for v in vers}
    if len(vers) == 3:
        s['common_all'] = sum(1 for i in range(len(matches)) if keys['H'][i] & keys['A'][i] & keys['AV'][i])
        s['pairs'] = {f'{a}∩{b}': sum(1 for i in range(len(matches)) if keys[a][i] & keys[b][i])
                      for a, b in (('H', 'A'), ('H', 'AV'), ('A', 'AV'))}
    return s


def summary_html(matches):
    s = summary(matches)
    lab = dict(VERS)
    parts = [f'<b>{lab[v]}</b>: {s["ah"][v]} AH/1Χ2 + {s["over"][v]} over' for v in s['vers']]
    h = f'<div class="sum">Picks (χαρτινα) σε {s["n"]} ματς ({s["with_line"]} με γραμμη Crown, {s["dead"]} νεκρα): ' + ' · '.join(parts)
    if 'common_all' in s:
        h += (f' &nbsp;|&nbsp; <b>κοινα και στις 3</b> (ιδιο pick): {s["common_all"]} · '
              + ' · '.join(f'{k} {v}' for k, v in s['pairs'].items()))
    return h + '</div>'


CSS = """<meta charset="utf-8"><style>
body{margin:0;background:#0a0f1e;font-family:'DM Sans',sans-serif;color:#cdd8ee;}
table{border-collapse:collapse;width:100%;font-size:11px;table-layout:auto;}
th{background:#16203a;color:#8fa3c8;font-weight:600;padding:4px 3px;text-align:center;font-size:9px;letter-spacing:.4px;text-transform:uppercase;border-bottom:1px solid #26324e;white-space:nowrap;}
th.l{text-align:left;} th.grp{background:#0f1830;color:#6b7fa3;border-bottom:none;font-size:9px;letter-spacing:1.2px;border-left:2px solid #26324e;}
th.grp.h{color:#7ea2ff;} th.grp.a{color:#f3c74b;} th.grp.av{color:#34d17a;} th.grp.mk{color:#cdd8ee;}
td{padding:3px 4px;border-bottom:1px solid #1a2540;text-align:center;font-family:monospace;white-space:nowrap;vertical-align:middle;}
td.sep{border-left:2px solid #26324e;}
td.t{text-align:left;font-family:'DM Sans',sans-serif;font-weight:600;color:#e8edf8;padding-right:8px;}
td.t img{width:16px;height:16px;vertical-align:middle;margin-right:4px;}
td.t .vs{color:#5a6b8c;font-weight:400;margin:0 4px;}
td.t .meta{display:block;color:#6b7fa3;font-weight:400;font-size:9.5px;margin-top:1px;}
td.t .dead{color:#ff6b6b;font-weight:700;} td.t .call{color:#f3c74b;cursor:help;}
td.mk{color:#cdd8ee;} td.mk .ln{color:#e8edf8;font-weight:700;} td.mk .sub{display:block;color:#6b7fa3;font-size:9.5px;}
td.p{color:#e8edf8;} td.p .b{font-weight:700;}
td.xg .sub{display:block;color:#6b7fa3;font-size:9.5px;}
.e{font-weight:700;} .e.g{color:#34d17a;} .e.y{color:#f3c74b;} .e.n{color:#6b7fa3;font-weight:400;} .e.r{color:#ff6b6b;font-weight:400;} .e.dim{color:#3d4a66;font-weight:400;}
.fair{color:#cdd8ee;} .fair small{color:#6b7fa3;}
.bd{display:inline-block;padding:1px 6px;border-radius:8px;font-weight:700;font-size:9.5px;letter-spacing:.3px;margin:1px 2px;color:#0a0f1e;cursor:help;}
.bd.dog{background:#34d17a;} .bd.fav{background:#4b7cf3;color:#fff;} .bd.x12{background:#f3c74b;} .bd.over{background:#b17af3;color:#fff;}
.bd.dead{background:#2a1a1f;color:#ff6b6b;border:1px solid #ff6b6b;font-weight:600;} .bd.oor{background:#151c2e;color:#6b7fa3;border:1px solid #26324e;font-weight:400;}
.sum{margin-top:8px;padding:7px 10px;background:#0f1830;border:1px solid #26324e;border-radius:9px;color:#8fa3c8;font-size:11px;}
.sum b{color:#e8edf8;}
.note{margin:6px 0;color:#f3c74b;font-size:11px;}
</style>"""


def _match_cell(m):
    lh = f'<img src="{LOGO.format(m["hid"])}" onerror="this.style.display=\'none\'">' if m.get('hid') else ''
    la = f'<img src="{LOGO.format(m["aid"])}" onerror="this.style.display=\'none\'">' if m.get('aid') else ''
    meta = f'{m["utc"][5:]} UTC'
    if m.get('dead'):
        meta += f' <span class="dead" title="νεκρη: {m["dead"]}">✝ νεκρη {m["dead"]}</span>'
    if m.get('callups'):
        meta += f' <span class="call" title="{m["callups"]}">⚠ κλησεις</span>'
    return f'<td class="t">{lh}{m["home"]}<span class="vs">v</span>{la}{m["away"]}<span class="meta">{meta}</span></td>'


def _market_cells(m):
    c = (m.get('market') or {}).get('crown') or {}
    x12 = f'{c["o1"]:.2f} / {c["ox"]:.2f} / {c["o2"]:.2f}' if c.get('o1') else '—'
    ah = f'<span class="ln">{_fmt_line(c.get("ah_line"))}</span> {c["oh"]:.2f}/{c["oa"]:.2f}' if c.get('ah_line') is not None else '—'
    ah_sub = f'<span class="sub">αρχ. {m["init_ah"]}</span>' if m.get('init_ah') and m['init_ah'] not in ('—', 'nan') else ''
    ou = f'<span class="ln">{c["ou_line"]:g}</span> {c["over"]:.2f}/{c["under"]:.2f}' if c.get('ou_line') is not None else '—'
    return f'<td class="mk sep">{x12}</td><td class="mk">{ah}{ah_sub}</td><td class="mk">{ou}</td>'


def _version_cells(m, v):
    V = (m.get('versions') or {}).get(v)
    if not V:
        return '<td class="sep e dim">—</td><td class="e dim">—</td><td class="e dim">—</td><td class="e dim">—</td>'
    fav = max(V['p1'], V['px'], V['p2'])
    p = ' / '.join(f'<span class="b">{x}</span>' if x == fav and x >= 50 else f'{x}' for x in (V['p1'], V['px'], V['p2']))
    e = ((m.get('edges') or {}).get(v) or {}).get('crown') or {}
    ov = _edge_span(e.get('over')) if e.get('over') is not None else '<span class="e dim">—</span>'
    xg = f'<td class="xg">{V["xg_h"]:.2f}-{V["xg_a"]:.2f}<span class="sub">T {V["T"]:.2f} · O {ov}</span></td>' if V.get('T') is not None \
        else f'<td class="xg">{V["xg_h"]:.2f}-{V["xg_a"]:.2f}<span class="sub">O {ov}</span></td>'
    if e.get('fair_h') is not None:
        fair = (f'<span class="fair">{e["fair_h"]:.2f}</span> {_edge_span(e["ah_home"])} <small>|</small> '
                f'<span class="fair">{e["fair_a"]:.2f}</span> {_edge_span(e["ah_away"])}')
    else:
        fair = '<span class="e dim">—</span>'
    badges = _badges(m['picks'].get(v, ''), m['picks'].get(OVER_KEY[v], ''))
    return f'<td class="p sep">{p}</td>{xg}<td>{fair}</td><td>{badges}</td>'


def table_html(comp, matches):
    vers = [x for x in VERS if x[0] == 'H' or has_anchor(matches)]
    h = CSS
    if not matches:
        return h + '<div class="sum">Δεν βρεθηκαν ματς.</div>'
    if len(vers) == 1:
        h += '<div class="note">Αγκυρα: μη διαθεσιμη για CAF (δεν εχει τρεξει intl_mkt_anchor) — μονο εκδοχη H + αξια, HFA 80.</div>'
    h += '<table><tr><th class="grp"></th><th class="grp mk" colspan="3">Αγορα · Crown (Nowgoal)</th>'
    for v, lab in vers:
        h += f'<th class="grp {v.lower()}" colspan="4">{lab}</th>'
    h += '</tr><tr><th class="l">Ματς</th><th>1 / Χ / 2</th><th>AH γραμμη · τιμες</th><th>O/U · over/under</th>'
    for v, _ in vers:
        h += '<th>1 / Χ / 2 %</th><th>xG · T</th><th>fair AH @Crown · edge</th><th>Pick</th>'
    h += '</tr>'
    for m in matches:
        h += '<tr>' + _match_cell(m) + _market_cells(m)
        for v, _ in vers:
            h += _version_cells(m, v)
        h += '</tr>'
    h += '</table>' + summary_html(matches)
    return h


def table_height(matches):
    return min(len(matches) * 40 + 130, 6000)
