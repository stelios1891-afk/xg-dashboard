"""nba_players_view.py — 🏀 NBA PLAYERS: δικη σελιδα (20/10/2026, Στελιος «βγαλε τη βαση παικτων απο το NBA, νεο tab, πιο ομορφο,
πανω τα projections του ματς με νικη & χαντικαπ, ποσο κινειται η τιμη ολων»).
  • Ματς: καρτα προβλεψης (νικη / χαντικαπ / συνολο) ΠΡΙΝ → ΜΕΤΑ τις απουσιες που επιλεγεις, με δικαιες αποδοσεις, Pinnacle & edge.
  • Πινακες ομαδων με κουτακι «Εκτος»: τσεκαρεις αμφιβολο → μετραει · ξετσεκαρεις Out που ηδη μετρα → «επιστρεφει».
  • Ροστερ: ολη η βαση ανα ομαδα.
Ιδιοι αριθμοι με το live (nba_board / nba_absence). ΜΟΝΟ ΕΡΓΑΛΕΙΟ — δεν αλλαζει τα picks."""
import os, json, html as _h, datetime as dt
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HC_MIN = 0.08


def _load(n, d):
    try:
        with open(os.path.join(ROOT, n), encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return d


def _mtime():
    try:
        return max(os.path.getmtime(os.path.join(ROOT, f)) for f in
                   ('nba_injuries.json', 'nba_espn_games.json', 'nba_player_values.json', 'nba_roster_live.json'))
    except Exception:
        return 0


@st.cache_data(ttl=600)
def _players(_mt):
    import nba_board
    return nba_board.players()


def _gr_time(utc):
    try:
        t = dt.datetime.fromisoformat(str(utc).replace('Z', '+00:00'))
        from zoneinfo import ZoneInfo
        t = t.astimezone(ZoneInfo('Europe/Athens'))
        return f"{['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ'][t.weekday()]} {t:%d/%m · %H:%M}"
    except Exception:
        return str(utc)[:16]


def _status(r):
    s = str(r.get('status') or '').strip().lower()
    if not s:
        return ''
    lab = {'out': '🔴 Εκτος', 'doubtful': '🟠 Μαλλον εκτος (D)', 'day-to-day': '🟡 Αμφιβολος (DTD)',
           'questionable': '🟡 Αμφιβολος (Q)', 'probable': '🟢 Πιθανον παιζει'}.get(s, s)
    return lab + (' · στο μοντελο' if r.get('in_model') else '')


# ------------------------------ καρτα ματς ------------------------------
CSS = """
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:transparent;font-family:'DM Sans','Segoe UI',sans-serif;color:#e8edf8;padding:2px}
.card{background:linear-gradient(180deg,#131c30 0%,#0f1626 100%);border:1px solid #1e2d47;border-radius:14px;overflow:hidden}
.top{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:16px 20px 10px;gap:10px}
.tm{display:flex;align-items:center;gap:12px}.tm.a{flex-direction:row-reverse;text-align:right}
.tm img{width:46px;height:46px;object-fit:contain}
.tn{font-family:'Bebas Neue',sans-serif;font-size:24px;letter-spacing:.8px;line-height:1}
.ts{font-size:10px;color:#6b7fa3;letter-spacing:1.5px;text-transform:uppercase;margin-top:3px}
.mid{text-align:center}.when{font-size:11px;color:#8fa3c8;letter-spacing:1px}
.vs{font-family:'Bebas Neue',sans-serif;font-size:15px;color:#4b5d80;letter-spacing:2px;margin-top:2px}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:6px 20px 14px}
.kpi{background:#0b1220;border:1px solid #1a2740;border-radius:10px;padding:10px 12px}
.kl{font-size:9.5px;color:#6b7fa3;letter-spacing:1.4px;text-transform:uppercase}
.kv{font-family:'JetBrains Mono',monospace;font-size:17px;font-weight:700;margin-top:4px;white-space:nowrap}
.kv .ar{color:#4b5d80;margin:0 5px;font-weight:400}
.kv .new{color:#f5a623}.kd{font-size:10.5px;margin-top:3px;font-family:'JetBrains Mono',monospace}
table{width:100%;border-collapse:collapse;font-size:12px}
th{font-size:9.5px;color:#6b7fa3;letter-spacing:1.2px;text-transform:uppercase;font-weight:600;text-align:center;padding:7px 6px;border-top:1px solid #1a2740;border-bottom:1px solid #1a2740;background:#0d1424}
th:first-child,td:first-child{text-align:left;padding-left:20px}
td{padding:7px 6px;text-align:center;border-bottom:1px solid #152036;font-family:'JetBrains Mono',monospace}
td.lab{font-family:'DM Sans',sans-serif;font-weight:600}
.mk{display:inline-block;font-size:8.5px;letter-spacing:1px;color:#8fa3c8;background:#1a2740;border-radius:4px;padding:2px 5px;margin-right:7px;font-family:'DM Sans',sans-serif;font-weight:700}
.pin{color:#e8edf8;font-weight:700}.mut{color:#6b7fa3}.sub{color:#6b7fa3;font-size:10px;margin-left:3px}
.up{color:#34d17a}.dn{color:#f04f5a}.zero{color:#4b5d80}
.eg{display:inline-block;min-width:54px;padding:2px 6px;border-radius:6px;font-weight:700}
.eg.pos{background:rgba(52,209,122,.13);color:#34d17a}.eg.neg{color:#6b7fa3}.eg.hot{background:rgba(52,209,122,.25);color:#5cf09b;border:1px solid rgba(52,209,122,.45)}
.sep td{border-bottom:1px solid #22324f}
.chg{padding:10px 20px 14px;font-size:11.5px;color:#8fa3c8;line-height:1.7}
.chip{display:inline-block;background:#1a2740;border-radius:20px;padding:2px 10px;margin:2px 4px 2px 0;color:#e8edf8;font-size:11px}
.chip.ret{background:rgba(52,209,122,.13);color:#34d17a}
@media (max-width:640px){.kpis{grid-template-columns:1fr}.tn{font-size:18px}.tm img{width:32px;height:32px}th:nth-child(5),td:nth-child(5){display:none}}
</style>"""


def _md(t):
    import re
    return re.sub(r'\*\*(.+?)\*\*', lambda m: '<b style="color:#e8edf8">' + m.group(1) + '</b>', _h.escape(t))

def _fo(p):
    return f"{1 / p:.2f}" if p and p > 0.005 else '—'


def _mv(p0, p1):
    """Κινηση δικαιης αποδοσης (αρνητικο = πιο πιθανο = πρασινο)."""
    if not p0 or not p1:
        return '<span class="zero">—</span>'
    d = 1 / p1 - 1 / p0
    if abs(d) < 0.005:
        return '<span class="zero">·</span>'
    return f'<span class="{"up" if d < 0 else "dn"}">{"▼" if d < 0 else "▲"} {abs(d):.2f}</span>'


def _eg(e, thr=None):
    if e is None:
        return '<span class="mut">—</span>'
    cls = 'hot' if (thr is not None and e >= thr) else ('pos' if e > 0 else 'neg')
    return f'<span class="eg {cls}">{100 * e:+.1f}%</span>'


def card(g, pin, b, a, offs, backs):
    hm = lambda m: f"{-m:+.1f}"                       # γραμμη γηπεδουχου (− = φαβορι)
    ch = lambda x, y, f: (f'{f(x)}' if abs(x - y) < 1e-6 else f'{f(x)}<span class="ar">→</span><span class="new">{f(y)}</span>')
    dm, dt_ = a['dm'], a['dt']
    mk_l = f' · αγορα {float(pin["line"]):+g}' if pin.get('line') is not None else ''
    mk_t = f' · αγορα {float(pin["tl"]):g}' if pin.get('tl') is not None else ''
    k1 = (f'<div class="kpi"><div class="kl">Χαντικαπ {_h.escape(g["home"].split()[-1])} (μοντελο){mk_l}</div><div class="kv">{ch(b["margin"], a["margin"], hm)}</div>'
          f'<div class="kd {"up" if dm > 0 else "dn" if dm < 0 else "zero"}">{dm:+.1f} π. για {_h.escape(g["home"].split()[-1])}</div></div>')
    k2 = (f'<div class="kpi"><div class="kl">Νικη {_h.escape(g["home"].split()[-1])} / {_h.escape(g["away"].split()[-1])}</div>'
          f'<div class="kv">{ch(b["p_h"], a["p_h"], lambda p: f"{100 * p:.0f}%")}<span class="mut" style="font-size:12px"> / {100 * a["p_a"]:.0f}%</span></div>'
          f'<div class="kd {"up" if a["p_h"] > b["p_h"] + 1e-6 else "dn" if a["p_h"] < b["p_h"] - 1e-6 else "zero"}">{100 * (a["p_h"] - b["p_h"]):+.1f} ποσοστιαιες μοναδες</div></div>')
    k3 = (f'<div class="kpi"><div class="kl">Συνολο ποντων (μοντελο){mk_t}</div><div class="kv">{ch(b["total"], a["total"], lambda x: f"{x:.1f}")}</div>'
          f'<div class="kd {"up" if dt_ > 0 else "dn" if dt_ < 0 else "zero"}">{dt_:+.1f} ποντοι</div></div>')
    rows = []
    sh, sa = g['home'].split()[-1], g['away'].split()[-1]
    if pin.get('mh') and pin.get('ma'):
        for lab, p0, p1, od in ((sh, b['p_h'], a['p_h'], pin['mh']), (sa, b['p_a'], a['p_a'], pin['ma'])):
            rows.append((f'<span class="mk">ΝΙΚΗ</span>{_h.escape(lab)}', float(od), p0, p1, 1.0, None))
    if 'line' in a:
        L = a['line']
        for lab, p0, p1, od in ((f"{sh} {L:+g}", b['c_h'], a['c_h'], pin['oh']), (f"{sa} {-L:+g}", b['c_a'], a['c_a'], pin['oa'])):
            rows.append((f'<span class="mk">ΧΑΝΤ.</span>{_h.escape(lab)}', float(od), p0, p1, 1 - a['c_p'], HC_MIN))
    if 'tl' in a:
        for lab, p0, p1, od in ((f"Over {a['tl']:g}", b['o'], a['o'], pin['to']), (f"Under {a['tl']:g}", b['u'], a['u'], pin['tu'])):
            rows.append((f'<span class="mk">ΣΥΝ.</span>{_h.escape(lab)}', float(od), p0, p1, 1 - a['t_p'], None))
    body = ''
    for i, (lab, od, p0, p1, nopush, thr) in enumerate(rows):
        f0 = nopush / p0 if p0 > 0.005 else None; f1 = nopush / p1 if p1 > 0.005 else None
        e0 = p0 * od + (1 - nopush) - 1; e1 = p1 * od + (1 - nopush) - 1
        sep = ' class="sep"' if i % 2 == 1 else ''
        body += (f'<tr{sep}><td class="lab">{lab}</td><td class="pin">{od:.2f}</td>'
                 f'<td>{f0:.2f}<span class="sub">{100 * p0:.0f}%</span></td>' if f0 else f'<tr{sep}><td class="lab">{lab}</td><td class="pin">{od:.2f}</td><td>—</td>')
        body += (f'<td><b>{f1:.2f}</b><span class="sub">{100 * p1:.0f}%</span></td>' if f1 else '<td>—</td>')
        body += f'<td>{_mv(p0 / nopush, p1 / nopush)}</td><td>{_eg(e0, thr)}</td><td>{_eg(e1, thr)}</td></tr>'
    tbl = ('<table><tr><th>Αγορα</th><th>Pinnacle</th><th>Μοντελο τωρα</th><th>Με τις επιλογες</th><th>Κινηση τιμης</th><th>Edge τωρα</th><th>Edge μετα</th></tr>'
           + body + '</table>') if rows else '<div class="chg">Δεν υπαρχει ακομα γραμμη Pinnacle για το ματς.</div>'
    chips = ''.join(f'<span class="chip">✕ {_h.escape(n)} {v:+.1f}</span>' for n, v in offs)
    chips += ''.join(f'<span class="chip ret">↩ {_h.escape(n)} {v:+.1f}</span>' for n, v in backs)
    chg = (f'<div class="chg">Επιλογες: {chips}</div>' if chips else
           '<div class="chg">Τσεκαρε «Εκτος» στους πινακες απο κατω (π.χ. αμφιβολους) για να δεις πως αλλαζουν ολες οι τιμες. '
           'Ξετσεκαρε εναν «στο μοντελο» για να δεις τι γινεται αν επιστρεψει.</div>')
    logo = lambda u: f'<img src="{_h.escape(u)}">' if u else ''
    return (CSS + '<div class="card"><div class="top">'
            f'<div class="tm">{logo(g.get("hcrest"))}<div><div class="tn">{_h.escape(g["home"])}</div><div class="ts">Γηπεδουχος</div></div></div>'
            f'<div class="mid"><div class="when">{_gr_time(g["utc"])}</div><div class="vs">VS</div></div>'
            f'<div class="tm a">{logo(g.get("acrest"))}<div><div class="tn">{_h.escape(g["away"])}</div><div class="ts">Φιλοξενουμενος</div></div></div></div>'
            f'<div class="kpis">{k1}{k2}{k3}</div>{tbl}{chg}</div>')


# ------------------------------ πινακες παικτων ------------------------------
def _df(rows, with_box):
    import pandas as pd
    ic = lambda r: {'out': '🔴 ', 'doubtful': '🟠 ', 'day-to-day': '🟡 ', 'questionable': '🟡 ', 'probable': '🟢 '}.get(str(r.get('status') or '').strip().lower(), '')
    d = pd.DataFrame([{'Εκτος': bool(r['in_model']), 'Παικτης': ic(r) + r['name'], 'Κατασταση': _status(r),
                       'Χαντικαπ': -r['imp_m'], 'Κοστος': r['imp_m'], 'Συνολο': r['imp_t'],
                       'Λεπτα': r['min'], 'Πηγη λεπτων': 'φετος' if r['msrc'] == 'φετος' else ('περσι' if r['msrc'] == 'περσι' else '—'),
                       'Αξια': r['v']} for r in rows])
    if not with_box and len(d):
        d = d.drop(columns=['Εκτος'])
    return d


def _colcfg(mx):
    cc = st.column_config
    return {'Εκτος': cc.CheckboxColumn('Εκτος', help='Τσεκαρισμενο = δεν παιζει', width='small'),
            'Παικτης': cc.TextColumn('Παικτης', width='medium'),
            'Κατασταση': cc.TextColumn('Κατασταση ESPN', width='medium'),
            'Χαντικαπ': cc.NumberColumn('Χαντ. αν λειψει', format='%+.1f', help='Ποσους ποντους χανει η ομαδα στο χαντικαπ αν δεν παιξει'),
            'Κοστος': cc.ProgressColumn('Βαρος', min_value=0.0, max_value=mx, format=' '),
            'Συνολο': cc.NumberColumn('Συνολο αν λειψει', format='%+.1f', help='Αλλαγη στο συνολο ποντων του ματς'),
            'Λεπτα': cc.NumberColumn('Λεπτα', format='%.0f′'),
            'Πηγη λεπτων': cc.TextColumn('Λεπτα απο', width='small'),
            'Αξια': cc.NumberColumn('Αξια', format='%+.2f', help='Αξια παικτη (ποντοι/100 κατοχες πανω απο μεσο ροταρισμα)')}


def _team_head(name, crest, sub):
    st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin:6px 0 4px">'
                + (f'<img src="{_h.escape(crest)}" style="width:30px;height:30px;object-fit:contain">' if crest else '')
                + f'<div><div style="font-family:Bebas Neue,sans-serif;font-size:21px;letter-spacing:.8px;line-height:1">{_h.escape(name)}</div>'
                  f'<div style="font-size:10px;color:#6b7fa3;letter-spacing:1.3px">{_h.escape(sub)}</div></div></div>', unsafe_allow_html=True)


LEGEND = ('**Χρωματα (λιστα τραυματιων ESPN):** 🔴 **Εκτος** (Out) — δεν παιζει · 🟠 **Μαλλον εκτος** (Doubtful) · '
          '🟡 **Αμφιβολος** (Questionable / Day-To-Day) — αποφαση την ημερα του αγωνα · 🟢 **Πιθανον παιζει** (Probable) · χωρις σημα = δεν ειναι στη λιστα. '
          '«στο μοντελο» = Εκτος που η προβλεψη ΗΔΗ αφαιρει (παικτης ρολου ≥20′ που επαιξε φετος, ή εκτος απο την αρχη της σεζον). '
          'Ολοι οι υπολοιποι (και οι 🟠/🟡) ΔΕΝ μετρανε μεχρι να τους τσεκαρεις «Εκτος».')


def render(league=None):
    import nba_board
    st.markdown('<div class="lg-title"><div><div class="nm" style="color:#f5a623">🏀 NBA PLAYERS</div>'
                '<div class="co">ΠΑΙΚΤΕΣ · ΑΠΟΥΣΙΕΣ · «ΤΙ ΓΙΝΕΤΑΙ ΑΝ ΛΕΙΨΕΙ» — ΙΔΙΟΙ ΑΡΙΘΜΟΙ ΜΕ ΤΟ LIVE ΜΟΝΤΕΛΟ</div></div></div>', unsafe_allow_html=True)
    proj = _load('nba_projections.json', {})
    if not proj.get('games'):
        st.info('Δεν υπαρχουν ακομα προβλεψεις NBA.'); return
    P = _players(_mtime())
    inj = _load('nba_injuries.json', {})
    odds = _load('nba_odds_latest.json', {}).get('odds', {})
    sm, stt = float(proj.get('sigma_margin', 11.5)), float(proj.get('sigma_total', 16.7))
    crest, names = {}, {}
    for g in proj['games']:
        crest[g['hcode']], crest[g['acode']] = g.get('hcrest'), g.get('acrest'); names[g['hcode']], names[g['acode']] = g['home'], g['away']
    mx = max([r['imp_m'] for rs in P.values() for r in rs] + [1.0])
    now = dt.datetime.now(dt.timezone.utc)
    up = sorted([g for g in proj['games'] if not g.get('played')
                 and dt.datetime.fromisoformat(str(g['utc']).replace('Z', '+00:00')) > now - dt.timedelta(hours=3)], key=lambda g: g['utc'])
    view = st.radio('Προβολη', ['🎯  Ματς — τι γινεται αν λειψει', '📋  Ροστερ ομαδων'], horizontal=True, key='nbp_view', label_visibility='collapsed')
    if view.startswith('🎯'):         # οχι st.tabs: πινακας σε κρυφη καρτελα αποδιδεται στενος
        if not up:
            st.info('Δεν υπαρχουν επερχομενα ματς με προβλεψη.')
        else:
            gi = st.selectbox('Ματς', range(len(up)), key='nbp_game', label_visibility='collapsed',
                              format_func=lambda i: f"{_gr_time(up[i]['utc'])}   ·   {up[i]['home']}  –  {up[i]['away']}")
            g = up[gi]; pin = (odds.get(str(g['code'])) or {}).get('pin') or {}
            slot = st.container()
            st.caption('Τσεκαρε **Εκτος** σε οποιον δεν παιζει — η καρτα πανω ενημερωνεται αμεσως. Οσοι λενε «στο μοντελο» ειναι ηδη μεσα στην προβλεψη '
                       '(ξετσεκαρε τους αν επιστρεφουν). Αμφιβολοι (DTD / Q / D) ΔΕΝ μετρανε μεχρι να τους τσεκαρεις.')
            c1, c2 = st.columns(2, gap='medium')
            off, sel = {}, {}
            for col, code, nm, k, sub in ((c1, g['hcode'], g['home'], 'h', 'ΓΗΠΕΔΟΥΧΟΣ'), (c2, g['acode'], g['away'], 'a', 'ΦΙΛΟΞΕΝΟΥΜΕΝΟΣ')):
                rows = P.get(code, [])
                with col:
                    _team_head(nm, g.get('hcrest' if k == 'h' else 'acrest'), sub)
                    ed = st.data_editor(_df(rows, True)[['Εκτος', 'Παικτης', 'Χαντικαπ', 'Κοστος', 'Συνολο', 'Λεπτα', 'Κατασταση']] if rows else _df(rows, True),
                                        column_config=_colcfg(mx), disabled=['Παικτης', 'Κατασταση', 'Χαντικαπ', 'Κοστος', 'Συνολο', 'Λεπτα'],
                                        hide_index=True, use_container_width=True, key=f"nbp_ed_{k}_{g['code']}", height=min(36 * len(rows) + 40, 560))
                    off[k] = {n.split(' ', 1)[1] if n[:1] in '🔴🟠🟡🟢' else n for n in ed.loc[ed['Εκτος'], 'Παικτης']} if len(ed) else set()
                    sel[k] = rows
            st.markdown(f'<div style="font-size:12px;color:#8fa3c8;line-height:1.6;margin-top:4px">{_md(LEGEND)}</div>', unsafe_allow_html=True)
            b, a = nba_board.whatif(g, pin, off['h'], off['a'], P, sm, stt)
            offs, backs = [], []
            for k, sg in (('h', 1), ('a', 1)):
                for r in sel[k]:
                    if r['name'] in off[k] and not r['in_model']:
                        offs.append((r['name'], -r['imp_m']))
                    elif r['name'] not in off[k] and r['in_model']:
                        backs.append((r['name'], r['imp_m']))
            with slot:
                nr = 2 * (('line' in a) + ('tl' in a) + bool(pin.get('mh') and pin.get('ma')))
                st.components.v1.html(card(g, pin, b, a, offs, backs), height=(250 + 34 * nr + 64) if nr else 300, scrolling=False)
            st.caption('Δικαιη αποδοση = 1 / πιθανοτητα μοντελου (στο χαντικαπ/συνολο χωρις το push). Κινηση τιμης ▼ πρασινο = η πλευρα γινεται πιο πιθανη. '
                       f'Πρασινο πλαισιο στο edge χαντικαπ = περνα το 8%. Τα συνολα NBA ειναι σε καταγραφη και εδω ειναι του μοντελου μονο του (χωρις μιξη 50/50). '
                       f"Η γραμμη της αγορας μετα την ειδηση θα κινηθει — συγκρινε με την τιμη της στιγμης. Λιστα ESPN: {str(inj.get('fetched', ''))[:16].replace('T', ' ')} UTC")
    else:
        teams = sorted(P, key=lambda c: names.get(c, c))
        tc = st.selectbox('Ομαδα', teams, key='nbp_team', format_func=lambda c: names.get(c, c), label_visibility='collapsed')
        rows = P.get(tc, [])
        nout = sum(1 for r in rows if r['status'])
        _team_head(names.get(tc, tc), crest.get(tc), f"{len(rows)} ΠΑΙΚΤΕΣ · {nout} ΣΤΗ ΛΙΣΤΑ ESPN")
        st.dataframe(_df(rows, False)[['Παικτης', 'Χαντικαπ', 'Κοστος', 'Συνολο', 'Λεπτα', 'Πηγη λεπτων', 'Αξια', 'Κατασταση']] if rows else _df(rows, False), column_config=_colcfg(mx), hide_index=True, use_container_width=True, height=min(36 * len(rows) + 40, 760))
        st.markdown(f'<div style="font-size:12px;color:#8fa3c8;line-height:1.6;margin-top:4px">{_md(LEGEND)}</div>', unsafe_allow_html=True)
        st.caption('Χαντ. αν λειψει = 0.75 × (αξια + 1) × λεπτα / 48 (ιδιο με τις live απουσιες) · Συνολο: χαμενη επιθεση −0.5, χαμενη αμυνα +1.0 · '
                   'Λεπτα = μεσος στα ≤10 τελευταια φετινα ματς, αλλιως περσινα.')
