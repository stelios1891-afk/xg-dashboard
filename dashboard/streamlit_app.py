"""
streamlit_app.py — LIVE dashboard προβλεψεων (ιδιωτικο, Streamlit Community Cloud).

Layout (εμπνευσμενο απο TeamsLab):
  - ΠΑΝΩ: μπαρα με league logos (κλικ = επιλογη πρωταθληματος).
  - ΑΡΙΣΤΕΡΑ: μενου σελιδων (Match Projections ενεργο· τα υπολοιπα placeholders).
  - ΚΕΝΤΡΟ: το περιεχομενο της σελιδας.

Τρεξε τοπικα:  streamlit run dashboard/streamlit_app.py
"""
import os, sys, json
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_data
import cards
import goal_stats
import goal_view
import trendline
import trend_view
import scatter_view
import xgstats
import xgstats_view
import value_view

st.set_page_config(page_title="xG Model — Live", page_icon="⚽", layout="wide",
                   initial_sidebar_state="expanded")

# Κουμπι ανακοινωμενων 11αδων: ΠΑΡΚΑΡΙΣΜΕΝΟ (αποφαση Στελιου) μεχρι το πειραμα
# χρονομετρησης (ποσο γρηγορα ανεβαινουν στο FotMob vs Twitter). ΜΗΝ ανοιξει χωρις εντολη.
SHOW_OFFICIAL_XI_BTN = False

LEAGUE_LABELS = {'EPL': 'Premier League', 'LaLiga': 'La Liga', 'SerieA': 'Serie A',
                 'Bundesliga': 'Bundesliga', 'Ligue1': 'Ligue 1', 'Eredivisie': 'Eredivisie',
                 'PrimeiraLiga': 'Primeira Liga'}
LEAGUE_COUNTRY = {'EPL': 'ENGLAND', 'LaLiga': 'SPAIN', 'SerieA': 'ITALY', 'Bundesliga': 'GERMANY',
                  'Ligue1': 'FRANCE', 'Eredivisie': 'NETHERLANDS', 'PrimeiraLiga': 'PORTUGAL'}
LEAGUE_LOGO = 'https://images.fotmob.com/image_resources/logo/leaguelogo/dark/{}.png'  # dark-mode variant (ανοιχτοχρωμο σε σκουρο φοντο)

# (id, label, icon)· ενεργα: projections, goals
PAGES = [('summary', 'Summary', '📊'), ('trend', 'Trendline', '📈'), ('pi', 'Pi Rating', '🔵'),
         ('team', 'Team Rating', '🛡️'), ('scatter', 'Scatter Plots', '✳️'),
         ('ave', 'Actual vs Expected', '🎯'), ('value', 'Value Picks', '💰'),
         ('ledger', 'Pick History', '📒'), ('moves', 'Market Watch', '📡'),
         ('lineup', 'Lineup Lab', '🧪'),
         ('projections', 'Match Projections', '🗓️'),
         ('goals', 'Goal Stats', '⚽'), ('xgstats', 'XG Stats', '📶'),
         ('season', 'Season Projections', '🏆'), ('perf', 'Model Performance', '📐')]
PAGE_LABEL = {p[0]: p[1] for p in PAGES}
ACTIVE_PAGES = {'projections', 'goals', 'trend', 'scatter', 'xgstats', 'value', 'ledger', 'moves', 'lineup'}

@st.cache_data(ttl=6 * 3600, show_spinner="Υπολογισμος προβλεψεων...")
def load_matches():
    return build_data.build_matches()

st.markdown("""
<style>
.stApp{background:#0a0f1e;}
#MainMenu,footer{visibility:hidden;}
header[data-testid="stHeader"]{background:transparent;}
header [data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"]{visibility:hidden;}
.block-container{padding-top:1rem;max-width:1250px;}
section[data-testid="stSidebar"]{background:#0d1426;border-right:1px solid #1a2540;
  display:block !important;visibility:visible !important;transform:none !important;
  min-width:280px !important;margin-left:0 !important;}
[data-testid="stSidebarCollapseButton"],[data-testid="stSidebarCollapsedControl"]{display:none !important;}
h1,h2,h3{color:#e8edf8;font-family:'DM Sans',sans-serif;}
/* league logos bar */
.lgbar{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;padding:6px 0 14px;
       border-bottom:1px solid #1a2540;margin-bottom:16px;}
.lgbtn{width:52px;height:44px;display:flex;align-items:center;justify-content:center;border-radius:11px;
       border:1px solid transparent;background:#0f1830;transition:all .15s;}
.lgbtn:hover{border-color:#2d4470;background:#16203a;}
.lgbtn.active{border-color:#4b7cf3;background:#182444;box-shadow:0 0 0 1px #4b7cf3;}
.lgbtn img{width:28px;height:28px;object-fit:contain;}
/* sidebar menu */
.brand{font-family:'Bebas Neue',sans-serif;font-size:23px;letter-spacing:2px;color:#4b7cf3;padding:2px 0 2px;}
.brand span{color:#e8edf8;opacity:.75;}
.brand-sub{font-size:9px;color:#5a6b8c;letter-spacing:2px;margin-bottom:14px;}
.menu{display:flex;flex-direction:column;gap:3px;}
.menu a{display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:9px;text-decoration:none;
        color:#8fa3c8;font-size:13.5px;font-family:'DM Sans',sans-serif;transition:all .12s;}
.menu a:hover{background:#16203a;color:#cdd8ee;}
.menu a.on{background:#1c2a42;color:#e8edf8;font-weight:600;}
.menu a.soon{opacity:.5;}
.menu a .mi{width:18px;text-align:center;}
.menu a .tag{margin-left:auto;font-size:8px;color:#5a6b8c;border:1px solid #26324e;border-radius:4px;padding:1px 4px;}
.lg-title{display:flex;align-items:center;gap:13px;}
.lg-title img{width:40px;height:40px;object-fit:contain;}
.lg-title .nm{font-family:'Bebas Neue',sans-serif;font-size:30px;letter-spacing:1.5px;color:#e8edf8;line-height:1;}
.lg-title .co{font-size:10px;color:#6b7fa3;letter-spacing:2px;}
</style>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;600;700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

matches, stats = load_matches()
proj = [m for m in matches if m.get('projectable')]
avail_lgs = [lg for lg in build_data.LEAGUE_FOTMOB if any(m['league'] == lg for m in proj)]

qp = st.query_params
league = qp.get('league') or (avail_lgs[0] if avail_lgs else 'EPL')
if league not in avail_lgs:
    league = avail_lgs[0] if avail_lgs else 'EPL'
page = qp.get('page') or 'projections'
# ---------- SIDEBAR: brand + page menu ----------
with st.sidebar:
    st.markdown('<div class="brand">xG<span>MODEL</span></div>'
                '<div class="brand-sub">LIVE PROJECTIONS</div>', unsafe_allow_html=True)
    items = ''
    for pid, label, icon in PAGES:
        cls = 'on' if pid == page else ('soon' if pid not in ACTIVE_PAGES else '')
        tag = '' if pid in ACTIVE_PAGES else '<span class="tag">soon</span>'
        items += f'<a class="{cls}" href="?league={league}&page={pid}" target="_self"><span class="mi">{icon}</span>{label}{tag}</a>'
    st.markdown(f'<div class="menu">{items}</div>', unsafe_allow_html=True)

# ---------- TOP: league logos ----------
bar = '<div class="lgbar">'
for lg in avail_lgs:
    fid = build_data.LEAGUE_FOTMOB[lg]
    cls = 'active' if lg == league else ''
    bar += (f'<a class="lgbtn {cls}" href="?league={lg}&page={page}" target="_self" title="{LEAGUE_LABELS.get(lg, lg)}">'
            f'<img src="{LEAGUE_LOGO.format(fid)}" onerror="this.style.opacity=0"></a>')
bar += '</div>'
st.markdown(bar, unsafe_allow_html=True)

# ---------- MAIN CONTENT ----------
def render_projections(league):
    lg_matches = [m for m in proj if m['league'] == league]
    gws = sorted({m['gw'] for m in lg_matches})
    fid = build_data.LEAGUE_FOTMOB[league]
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(
            f'<div class="lg-title"><img src="{LEAGUE_LOGO.format(fid)}">'
            f'<div><div class="nm">{LEAGUE_LABELS.get(league, league)}</div>'
            f'<div class="co">{LEAGUE_COUNTRY.get(league, "")}</div></div></div>', unsafe_allow_html=True)
    with c2:
        gw = st.selectbox("Αγωνιστικη", gws, format_func=lambda x: f"GW {x}", key=f"gw_{league}")
    sel = sorted([m for m in lg_matches if m['gw'] == gw], key=lambda m: m['utc'])
    ws = [m['warm_cur'] for m in sel if 'warm_cur' in m]
    if ws:
        cur = sum(ws) / len(ws) * 100
        st.caption(f"⚖ Warm-start (K=6): **{cur:.0f}% φετινη 26/27** · **{100-cur:.0f}% περσινη 25/26** "
                   "— το βαρος της φετινης ανεβαινει οσο παιζονται ματς (n/(n+6)).")
    st.components.v1.html(cards.cards_block(sel), height=min(len(sel) * 118 + 40, 6000), scrolling=True)

def _lg_header(league, sub):
    fid = build_data.LEAGUE_FOTMOB[league]
    st.markdown(
        f'<div class="lg-title"><img src="{LEAGUE_LOGO.format(fid)}">'
        f'<div><div class="nm">{LEAGUE_LABELS.get(league, league)}</div>'
        f'<div class="co">{sub}</div></div></div>', unsafe_allow_html=True)

@st.cache_data(ttl=6 * 3600)
def _goal_rows(league, filt):
    return goal_stats.team_stats(league, filt=filt)

@st.cache_data(ttl=6 * 3600)
def _goal_timing(league, filt):
    return goal_stats.team_timing(league, filt=filt)

def render_goals(league):
    _lg_header(league, f"MATCH GOALS STATS · σεζον {goal_stats.SEASON_DEFAULT}")
    st.caption("Υπολογισμενο απο ολα τα αποτελεσματα 2025/26 · ανανεωση μολις τελειωσει η 1η αγωνιστικη 26/27.")
    n = len(_goal_rows(league, 'total'))
    h = n * 40 + 130
    tabs = st.tabs(["Total", "Home", "Away", "Last 8", "Timing (15′)"])
    for tab, filt in zip(tabs[:4], ['total', 'home', 'away', 'last8']):
        with tab:
            st.components.v1.html(goal_view.table_html(_goal_rows(league, filt), filt), height=h, scrolling=True)
    with tabs[4]:
        st.caption("Κατανομη γκολ ανα 15λεπτο — ΥΠΕΡ (αριστερα) & ΚΑΤΑ (δεξια). Χρωμα = ενταση.")
        sub = st.tabs(["Συνολο", "Εντος", "Εκτος"])
        for stab, filt in zip(sub, ['total', 'home', 'away']):
            with stab:
                st.components.v1.html(goal_view.timing_html(_goal_timing(league, filt)), height=h, scrolling=True)

@st.cache_data(ttl=6 * 3600)
def _trend_teams(league):
    return trendline.team_matches(league)

def render_trend(league):
    _lg_header(league, "ROLLING TRENDLINE · σεζον " + trendline.SEASON_DEFAULT)
    st.caption("Rolling average xGF/xGA με linear trend · raw npxG (non-penalty, ασυμπιεστο).")
    data = _trend_teams(league)
    names = sorted(data.keys())
    c1, c2, c3 = st.columns([2, 2, 1.2])
    with c1:
        team = st.selectbox("Ομαδα", names, key=f"tr_team_{league}")
    with c2:
        others = ['— Καμια —'] + [n for n in names if n != team]
        cmp = st.selectbox("Συγκριση με", others, key=f"tr_cmp_{league}")
    with c3:
        window = st.radio("Rolling window", [5, 10], index=1, horizontal=True, key=f"tr_w_{league}")
    s1 = trendline.series(data[team], window)
    s2 = trendline.series(data[cmp], window) if cmp != '— Καμια —' else None
    st.markdown(trend_view.cards_html(team, s1, cmp, s2, window), unsafe_allow_html=True)
    st.plotly_chart(trend_view.make_fig(s1, team, s2, cmp, window),
                    use_container_width=True, config={'displayModeBar': False})

def render_scatter(league):
    _lg_header(league, "SCATTER · npxG For vs Against · σεζον " + trendline.SEASON_DEFAULT)
    st.caption("Μεσο npxG υπερ (x) vs κατα (y). **Πανω-δεξια = καλυτερο** (πολλα υπερ, λιγα κατα).")
    data = _trend_teams(league)
    maxg = scatter_view.max_games(data)
    c1, _ = st.columns([2, 3])
    with c1:
        lo, hi = st.slider("Αγωνιστικες (απο — εως)", 1, maxg, (1, maxg), key=f"sc_gw_{league}")
    st.caption(f"Αγωνιστικες {lo}–{hi}" + ("  ·  full season" if (lo, hi) == (1, maxg) else ""))
    st.plotly_chart(scatter_view.scatter_fig(data, lo, hi),
                    use_container_width=True, config={'displayModeBar': False})

@st.cache_data(ttl=6 * 3600)
def _xgstats(league):
    return xgstats.compute(league)

def render_xgstats(league):
    _lg_header(league, "XG STATS · σεζον " + xgstats.SEASON_DEFAULT + " · all averages per game")
    data = _xgstats(league)
    VLABEL = [('total', 'Overall'), ('home', 'Home'), ('away', 'Away')]
    view = st.tabs(["xG Rankings", "xGD Table"])
    with view[0]:
        subs = st.tabs([l for _, l in VLABEL])
        for stab, (venue, _) in zip(subs, VLABEL):
            with stab:
                rows = data[venue]
                st.components.v1.html(xgstats_view.rankings_html(rows),
                                      height=min(len(rows) * 37 + 60, 1300), scrolling=True)
    with view[1]:
        subs = st.tabs([l for _, l in VLABEL])
        for stab, (venue, _) in zip(subs, VLABEL):
            with stab:
                rows = data[venue]
                c1, c2 = st.columns([5, 6])
                with c1:
                    st.components.v1.html(xgstats_view.xgd_table_html(rows),
                                          height=min(len(rows) * 36 + 70, 1300), scrolling=True)
                with c2:
                    st.plotly_chart(xgstats_view.xgd_bar_fig(rows), use_container_width=True,
                                    config={'displayModeBar': False})

_LATEST_F = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'value_picks_latest.json')

def render_value(league):
    st.markdown('<div class="lg-title"><div><div class="nm" style="color:#34d17a">💰 VALUE PICKS</div>'
                '<div class="co">LIVE · THE ODDS API · PINNACLE/MATCHBOOK AH</div></div></div>', unsafe_allow_html=True)
    st.caption("Μοντελο +handicap value bets · edge ≥10% · odds 1.70–2.10 · staking ⅛ Kelly + cap 20% · "
               "auto-scan (Task Scheduler) → Telegram για νεα/αλλαγες · το dashboard δειχνει το τελευταιο scan.")
    if not os.path.exists(_LATEST_F):
        st.info("Δεν υπαρχει ακομα scan. Τρεξε `python scan_value.py` (η το Task Scheduler) για να γεμισει.")
        return
    with open(_LATEST_F, encoding='utf-8') as fh:
        res = json.load(fh)
    picks = res.get('picks', [])
    if os.environ.get('TOA_KEY'):   # τοπικα μονο· στο cloud σκαναρει το GitHub Actions
        top = st.columns([3, 1])
        top[0].caption(f"🕒 Τελευταιο scan: **{res.get('scanned_at', '—')}**  ·  ratings σεζον {res.get('ratings_season', '')}")
        if top[1].button("🔄 Scan τωρα"):
            try:
                import scan_value
                scan_value.scan(notify_tg=False)
                st.rerun()
            except Exception as e:
                st.error(f"Σφαλμα scan: {e}")
    else:
        st.caption(f"🕒 Τελευταιο scan: **{res.get('scanned_at', '—')}**  ·  ratings σεζον {res.get('ratings_season', '')} "
                   "· auto-scan καθε 30' (GitHub Actions)")
    if not picks:
        st.info("Καμια value pick στο τελευταιο scan (αναμενομενο προεποχικα / χαμηλη ρευστοτητα Betfair).")
        return
    gr, sc, cap = res.get('gross', 0), res.get('scale', 1), res.get('cap', 0.2)
    m1, m2, m3 = st.columns(3)
    m1.metric("Picks", len(picks))
    m2.metric("Συνολικη εκθεση", f"{min(gr, cap)*100:.0f}%", help="⅛ Kelly, μετα το cap 20%")
    m3.metric("Καλυτερο edge", f"{max(p['edge'] for p in picks)*100:.0f}%")
    if res.get('n_new') or res.get('n_changed'):
        st.caption(f"τελευταιο scan: {res.get('n_new', 0)} νεα · {res.get('n_changed', 0)} με αλλαγη odds")
    if sc < 1.0:
        st.caption(f"⚙ Συνολικη εκθεση {gr*100:.0f}% > cap {cap*100:.0f}% → μειωση ολων ×{sc:.2f}.")
    # ---- φιλτρο ανα πρωταθλημα (default: ολα μαζι) ----
    order = list(build_data.LEAGUE_FOTMOB)
    lgs_present = sorted({p['lg'] for p in picks}, key=lambda x: order.index(x) if x in order else 99)
    sel_lg = st.selectbox("Πρωταθλημα", ['Όλα'] + lgs_present,
                          format_func=lambda x: 'Όλα τα πρωταθληματα' if x == 'Όλα' else value_view.LEAGUE_LABELS.get(x, x),
                          key='vp_league')
    shown = picks if sel_lg == 'Όλα' else [p for p in picks if p['lg'] == sel_lg]
    st.components.v1.html(value_view.picks_html(shown), height=min(len(shown) * 150 + 40, 4000), scrolling=True)

@st.cache_data(ttl=15 * 60)
def _ledger_data():
    import ledger_view
    return ledger_view.prepare(build_data.CURRENT_SEASON)

def render_ledger(league):
    import ledger_view
    st.markdown('<div class="lg-title"><div><div class="nm" style="color:#f3c74b">📒 PICK HISTORY</div>'
                '<div class="co">ΟΛΑ ΤΑ PICKS ΤΟΥ SCANNER · CLV vs ΚΛΕΙΣΙΜΟ · ΚΡΙΣΗ ΜΕ ΤΕΛΙΚΑ xG</div></div></div>',
                unsafe_allow_html=True)
    st.caption("Τιμη = Pinnacle/Matchbook τη στιγμη του alert · Κλεισιμο = τελευταια καταγραφη πριν τη σεντρα · "
               "CLV+ = νικησαμε το κλεισιμο · **xG value** = ποσο καλυτερη ηταν η τιμη μας απο τη «δικαιη» "
               "με βαση τα ΤΕΛΙΚΑ xG του ματς (κριση της διαδικασιας, οχι του σκορ).")
    try:
        settled, pending = _ledger_data()
    except Exception as e:
        st.error(f"Σφαλμα φορτωσης: {e}")
        return
    if not settled and not pending:
        st.info("Δεν υπαρχουν ακομα καταγεγραμμενα picks — γεμιζει αυτοματα με τα alerts του scanner (απο 29/8/2026).")
        return
    import ledger_view as lv
    s = lv.summary(settled)
    m = st.columns(5)
    m[0].metric("Settled picks", s['n'], help=f"+{len(pending)} εκκρεμη")
    m[1].metric("Μοναδες", f"{s['units']:+.2f}", f"{s['roi']*100:+.1f}% ROI" if s['n'] else None)
    m[2].metric("Μεσο CLV", f"{s['clv']*100:+.1f}%" if s['clv'] is not None else "—",
                help="+ = παιρνουμε καλυτερη τιμη απο το κλεισιμο (ιδια γραμμη)")
    m[3].metric("Νικες vs κλεισιμο", f"{s['beat']}/{s['nclv']}" if s['nclv'] else "—")
    m[4].metric("Μεσο xG value", f"{s['xgv']*100:+.1f}%" if s['xgv'] is not None else "—",
                help="+ = οι τιμες μας ηταν καλυτερες απο το «δικαιο» των τελικων xG")
    lgs = sorted({r['lg'] for r in settled} | {r['lg'] for r in pending})
    sel = st.selectbox("Πρωταθλημα", ['Όλα'] + lgs, key='led_lg')
    if sel != 'Όλα':
        settled = [r for r in settled if r['lg'] == sel]
        pending = [r for r in pending if r['lg'] == sel]
    fig = lv.cum_fig(settled)
    if fig is not None and len(settled) >= 3:
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.components.v1.html(lv.table_html(settled, pending),
                          height=min((len(settled) + len(pending)) * 52 + 60, 5000), scrolling=True)

@st.cache_data(ttl=15 * 60)
def _moves_hist():
    import moves_view
    return moves_view.load_history()

def render_moves(league):
    import moves_view as mv
    st.markdown('<div class="lg-title"><div><div class="nm" style="color:#7ea2ff">📡 MARKET WATCH</div>'
                '<div class="co">ΚΙΝΗΣΕΙΣ ΑΓΟΡΑΣ · PINNACLE/MATCHBOOK · ΕΠΕΡΧΟΜΕΝΑ ΜΑΤΣ</div></div></div>',
                unsafe_allow_html=True)
    st.caption("Απο τις καταγραφες του scanner (καθε 30′ σε μερα αγωνων, 2h τις τελευταιες 3 μερες, 1×/μερα νωριτερα). "
               "↓ = η αποδοση επεσε (πηρε χρημα). Το βαθος ιστοριας μεγαλωνει μερα με τη μερα — η συλλογη ξεκινησε 28/8/2026.")
    H = _moves_hist()
    if not H:
        st.info("Δεν υπαρχουν καταγραφες ακομα.")
        return
    # ---- 1. Biggest Movers (ολες οι λιγκες, επομενες μερες) ----
    st.markdown("#### 🔥 Biggest Movers — τελευταιες 48 ωρες")
    rows = mv.movers_rows(H, hours=48, top=12)
    if rows:
        st.components.v1.html(mv.movers_html(rows), height=min(len(rows) * 52 + 50, 900), scrolling=True)
    else:
        st.caption("Καμια αξιολογη κινηση ακομα (χρειαζονται ≥2 καταγραφες ανα ματς).")
    # ---- 2. Ανα πρωταθλημα ----
    st.markdown("#### Ολα τα επερχομενα ανα πρωταθλημα")
    lgs = sorted({d['meta']['lg'] for d in H.values() if d['meta'].get('lg')},
                 key=lambda x: list(build_data.LEAGUE_FOTMOB).index(x) if x in build_data.LEAGUE_FOTMOB else 99)
    sel_lg = st.selectbox("Πρωταθλημα", lgs,
                          index=lgs.index(league) if league in lgs else 0, key='mw_lg')
    st.components.v1.html(mv.league_html(H, sel_lg), height=560, scrolling=True)
    # ---- 3. Διαγραμμα ματς ----
    ups = [(k, d, ko) for k, d, ko in mv.upcoming(H) if d['meta']['lg'] == sel_lg and len(d['snaps']) >= 2]
    if not ups:
        return
    st.markdown("#### Διαγραμμα κινησης")
    names = {k: f"{d['meta']['home']} – {d['meta']['away']} ({mv._kofmt(ko)})" for k, d, ko in ups}
    sel_m = st.selectbox("Ματς", [k for k, _, _ in ups], format_func=lambda k: names[k], key='mw_match')
    D = {k: d for k, d, _ in ups}[sel_m]
    st.components.v1.html(mv.outcome_cards_html(D), height=130)
    c1, c2 = st.columns([2, 2])
    with c1:
        mode = st.radio("Προβολη", ['ΑΠΟΔΟΣΕΙΣ', '% ΜΕΤΑΒΟΛΗ', 'IMPLIED %'], horizontal=True, key='mw_mode')
    with c2:
        rng = st.radio("Παραθυρο", ['6H', '12H', '24H', '48H', 'ΟΛΑ'], index=4, horizontal=True, key='mw_rng')
    hrs = {'6H': 6, '12H': 12, '24H': 24, '48H': 48, 'ΟΛΑ': None}[rng]
    tabs = st.tabs(["1Χ2", "Ασιατικο χαντικαπ", "Ιστορικο αλλαγων"])
    with tabs[0]:
        st.plotly_chart(mv.match_fig(D, '1x2', mode, hrs), use_container_width=True, config={'displayModeBar': False})
    with tabs[1]:
        st.components.v1.html(mv.ah_cards_html(D), height=175)
        st.plotly_chart(mv.match_fig(D, 'ah', mode, hrs), use_container_width=True, config={'displayModeBar': False})
    with tabs[2]:
        st.components.v1.html(mv.history_html(D), height=min(len(D['snaps']) * 38 + 90, 700), scrolling=True)

@st.cache_data(ttl=6 * 3600)
def _lab():
    import lineup_view
    return lineup_view.load_lab()

import streamlit.components.v1 as _components
_lineup_pitch = _components.declare_component(
    "lineup_pitch", path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pitch_component'))

def render_lineup(league):
    import lineup_view as lv
    import build_data as bd
    st.markdown('<div class="lg-title"><div><div class="nm" style="color:#b17af3">🧪 LINEUP LAB</div>'
                '<div class="co">PROJECTED LINEUPS → ΔΙΟΡΘΩΜΕΝΑ PROJECTIONS · ΠΡΙΝ ΤΟ ΔΕΙ Η ΑΓΟΡΑ</div></div></div>',
                unsafe_allow_html=True)
    st.caption("Διαλεξε ματς → πειραξε τις 11αδες (πχ οταν πηγη σου λεει ποιος λειπει) → το projection "
               "ανανεωνεται ζωντανα με τη μετρημενη ζυγαρια (0.9 γκολ διαφορας ανα +1.0 Δ ενδεκαδας). "
               "Ρειτινγκ = 2σεζονο ιστορικο + ξενες λιγκες με συντελεστη επιπεδου (validated).")
    try:
        lab = _lab()
    except Exception as e:
        st.error(f"Δεν φορτωθηκε η βαση παικτων: {e}")
        return
    fx = [m for m in proj if m['league'] == league and m.get('projectable')]
    if not fx:
        st.info("Δεν υπαρχουν επερχομενα ματς με projection εδω.")
        return
    names = {i: f"{m['home']} – {m['away']} (GW{m['gw']} · {str(m['utc'])[:16]})" for i, m in enumerate(fx)}
    sel = st.selectbox("Ματς", list(names), format_func=lambda i: names[i], key=f'll_m_{league}')
    m = fx[sel]
    th = lv.team_of(lab, m['home_id']); ta = lv.team_of(lab, m['away_id'])
    if not th or not ta or th.get('base') is None or ta.get('base') is None:
        st.warning("Λειπει η βαση παικτων για καποια απο τις ομαδες.")
        return
    base_key = f"{m['home_id']}_{m['away_id']}"
    saved = lv.load_scenarios().get(base_key) or {}
    sv_h, sv_a = saved.get('home'), saved.get('away')
    keep = st.session_state.pop(f'll_keep_{base_key}', {})
    flist = list(lv.FORMATIONS)
    fc = st.columns(2)
    with fc[0]:
        f_h = st.selectbox(f"Συστημα — {m['home']}", flist,
                           index=flist.index(sv_h['f']) if sv_h and sv_h.get('f') in flist else 0,
                           key=f"llf_h_{m['home_id']}")
    with fc[1]:
        f_a = st.selectbox(f"Συστημα — {m['away']}", flist,
                           index=flist.index(sv_a['f']) if sv_a and sv_a.get('f') in flist else 0,
                           key=f"llf_a_{m['away_id']}")
    if 'home' in keep:
        xi_h = keep['home']
    elif sv_h and sv_h.get('f') == f_h:
        xi_h = sv_h['xi']
    else:
        xi_h = lv.default_xi(th, lv.FORMATIONS[f_h])
    if 'away' in keep:
        xi_a = keep['away']
    elif sv_a and sv_a.get('f') == f_a:
        xi_a = sv_a['xi']
    else:
        xi_a = lv.default_xi(ta, lv.FORMATIONS[f_a])
    nonce = st.session_state.get(f'll_nonce_{base_key}', 0)
    mkey = f"{base_key}_{f_h}_{f_a}_{nonce}"
    prj = lv.load_projected(m['home_id'], m['away_id'])
    pc = st.columns([2.4, 4.6])
    if pc[0].button('📋 Load projected XI', key=f'll_prj_{base_key}', disabled=prj is None,
                    help='Οι προβλεπομενες 11αδες δημοσιογραφων (predicted11) — κατεβαινουν αυτοματα καθε πρωι'):
        xh, okh = lv.fill_xi(th, prj.get('home') or [])
        xa, oka = lv.fill_xi(ta, prj.get('away') or [])
        lv.save_side(base_key, 'home', xh, f_h)
        lv.save_side(base_key, 'away', xa, f_a)
        st.session_state[f'll_nonce_{base_key}'] = nonce + 1
        st.toast(f'Projected 11αδες: ταιριασαν {okh}/11 + {oka}/11'
                 + ('' if okh == 11 and oka == 11 else ' (οι υπολοιποι απο την αναμενομενη)'))
        st.rerun()
    if prj is None:
        pc[1].caption('projected: δεν υπαρχει αποθηκευμενη προβλεψη γι αυτο το ματς '
                      '(καλυπτονται LaLiga + EPL + SerieA + Ligue1 · ανανεωση καθε πρωι ~08:00, Παρασκευη ανα 2ωρο)')
    else:
        pc[1].caption(f"projected snapshot: {str(prj.get('ts'))[:16].replace('T', ' ')} UTC · πηγη {prj.get('src') or 'predicted11'} "
                      f"· πατωντας το αντικαθισταται τυχον αποθηκευμενο σεναριο")
    if SHOW_OFFICIAL_XI_BTN and m.get('fid'):
        oc = st.columns([2.4, 4.6])
        if oc[0].button('⚡ Φορτωσε ΑΝΑΚΟΙΝΩΜΕΝΕΣ ενδεκαδες', key=f'll_off_{base_key}',
                        help='Τραβαει τις επισημες 11αδες (βγαινουν ~60-75 λεπτα πριν τη σεντρα)'):
            off = lv.fetch_official_xi(m['fid'])
            if off:
                known_h = {p['id'] for p in th['players']}; known_a = {p['id'] for p in ta['players']}
                if 'home' in off:
                    lv.save_side(base_key, 'home', off['home'], f_h)
                if 'away' in off:
                    lv.save_side(base_key, 'away', off['away'], f_a)
                miss = len([i for i in off.get('home', []) if i not in known_h]) + \
                       len([i for i in off.get('away', []) if i not in known_a])
                st.session_state[f'll_nonce_{base_key}'] = nonce + 1
                msg = 'Φορτωθηκαν οι επισημες ενδεκαδες' + ('' if len(off) == 2 else ' (μονο της μιας ομαδας)')
                if miss:
                    msg += f' · {miss} παικτες εκτος βασης (αγνοουνται στο Δ)'
                st.toast(msg)
                st.rerun()
            else:
                st.toast('Δεν εχουν ανακοινωθει ακομα — βγαινουν ~60-75 λεπτα πριν τη σεντρα.')
        oc[1].caption(f"οπτικος ελεγχος: [το ματς στο FotMob](https://www.fotmob.com/match/{m['fid']})")
    st.caption("🖐 Σερνεις παικτη απο τον παγκο πανω σε παικτη του γηπεδου για να τον αντικαταστησει. "
               "Αλλαγη συστηματος ξαναστηνει την προτεινομενη 11αδα (χανονται οι χειροκινητες αλλαγες). "
               "Γηπεδουχος αριστερα · φιλοξενουμενη δεξια · στηλες GK → DEF → MID → ATT. ● = χωρις ιστορικο.")
    val = _lineup_pitch(matchKey=mkey,
                        home=dict(name=m['home'], players=th['players'], xi=xi_h),
                        away=dict(name=m['away'], players=ta['players'], xi=xi_a),
                        default={'home': xi_h, 'away': xi_a}, key=f'pitch_{mkey}')
    sel_h = (val or {}).get('home') or xi_h
    sel_a = (val or {}).get('away') or xi_a
    bc = st.columns([0.7, 0.7, 2.3, 2.3, 0.7, 0.7])
    if bc[0].button('Save', key=f'll_sv_h_{base_key}', help=f"Αποθηκευση 11αδας — {m['home']}"):
        lv.save_side(base_key, 'home', sel_h, f_h)
        st.toast(f"Σεναριο {m['home']} αποθηκευτηκε.")
    if bc[1].button('Reset', key=f'll_rs_h_{base_key}', help=f"Επαναφορα αρχικης — {m['home']}"):
        lv.delete_side(base_key, 'home')
        st.session_state[f'll_keep_{base_key}'] = {'away': sel_a}
        st.session_state[f'll_nonce_{base_key}'] = nonce + 1
        st.rerun()
    if sv_h:
        bc[2].caption(f"💾 {m['home']}: {sv_h.get('saved','')}")
    if sv_a:
        bc[3].caption(f"💾 {m['away']}: {sv_a.get('saved','')}")
    if bc[4].button('Save ', key=f'll_sv_a_{base_key}', help=f"Αποθηκευση 11αδας — {m['away']}"):
        lv.save_side(base_key, 'away', sel_a, f_a)
        st.toast(f"Σεναριο {m['away']} αποθηκευτηκε.")
    if bc[5].button('Reset ', key=f'll_rs_a_{base_key}', help=f"Επαναφορα αρχικης — {m['away']}"):
        lv.delete_side(base_key, 'away')
        st.session_state[f'll_keep_{base_key}'] = {'home': sel_h}
        st.session_state[f'll_nonce_{base_key}'] = nonce + 1
        st.rerun()
    xh0, xa0 = m['home_adj_xg'], m['away_adj_xg']
    d_h = (lv.xi_strength(th, sel_h) or th['base']) - th['base']
    d_a = (lv.xi_strength(ta, sel_a) or ta['base']) - ta['base']
    xh, xa = lv.adjust_xg(xh0, xa0, d_h, d_a, lab.get('slope_gd', 0.9))
    st.markdown(lv.strength_bar_html(m['home'], d_h, m['away'], d_a), unsafe_allow_html=True)
    if m.get('promoted'):
        st.caption("⚠ Ματς με νεοφωτιστη: εδω η αβεβαιοτητα ειναι στην ΟΜΑΔΑ, οχι στην 11αδα — "
                   "το Δ προβλεπει λιγοτερα (μετρημενο).")
    p0 = bd.one_x_two(xh0, xa0); p1 = bd.one_x_two(xh, xa)
    mk = lv.latest_market(m['home_id'], m['away_id'])
    mkt_1x2 = None
    if mk and mk.get('h2h'):
        mkt_1x2 = tuple(mk['h2h'])
    elif m.get('mkt_hw_odds'):
        mkt_1x2 = (m.get('mkt_hw_odds'), m.get('mkt_d_odds'), m.get('mkt_aw_odds'))
    st.components.v1.html(lv.results_table_html(m['home'], m['away'], xh0, xa0, xh, xa, p0, p1, mkt_1x2),
                          height=250)
    if mk and mk.get('line') is not None:
        line = float(mk['line'])
        f0h = lv.ah_fair(xh0, xa0, 1, line); f1h = lv.ah_fair(xh, xa, 1, line)
        f0a = lv.ah_fair(xh0, xa0, -1, -line); f1a = lv.ah_fair(xh, xa, -1, -line)
        if f0h and f1h and f0a and f1a:
            st.components.v1.html(
                lv.ah_table_html(m['home'], m['away'], line,
                                 float(mk['oh']) if mk.get('oh') else None,
                                 float(mk['oa']) if mk.get('oa') else None,
                                 f0h, f1h, f0a, f1a, str(mk.get('t', ''))[:16]),
                height=240)
    else:
        st.caption("Δεν υπαρχει ακομα καταγεγραμμενη αγορα για αυτο το ματς (θα φανει μολις το πιασει ο scanner).")

RENDER = {'projections': render_projections, 'goals': render_goals, 'trend': render_trend,
          'scatter': render_scatter, 'xgstats': render_xgstats, 'value': render_value,
          'ledger': render_ledger, 'moves': render_moves, 'lineup': render_lineup}
if page in RENDER:
    RENDER[page](league)
else:
    st.markdown(f"### {PAGE_LABEL.get(page, page)}")
    st.info("🚧 Υπο κατασκευη — θα το φτιαξουμε στη συνεχεια.")

st.caption(f"Ratings warm-start: σεζον {build_data.RATINGS_SEASON_DEFAULT} · ανανεωση δεδομενων καθε 6h · "
           "fair odds απο το μοντελο (οχι αγορας).")
