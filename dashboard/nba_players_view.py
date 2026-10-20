"""nba_players_view.py — 🏀 NBA: ΠΑΙΚΤΕΣ & ΑΠΟΥΣΙΕΣ «ΤΙ ΓΙΝΕΤΑΙ ΑΝ ΛΕΙΨΕΙ» (20/10/2026, Στελιος).
Βαση παικτων ανα ομαδα (λεπτα, αξια, κατασταση ESPN, ποσο κοστιζει) + για καθε επερχομενο ματς: διαλεγεις ποιοι ΔΕΝ παιζουν
→ νεα προβλεψη χαντικαπ & συνολου και edge στην τωρινη γραμμη Pinnacle. Ιδιοι αριθμοι με το live (nba_board / nba_absence).
ΜΟΝΟ ΕΡΓΑΛΕΙΟ — δεν αλλαζει τα picks."""
import os, json, datetime as dt
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(n, d):
    try:
        with open(os.path.join(ROOT, n), encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return d


@st.cache_data(ttl=600)
def _players(_mt):
    import nba_board
    return nba_board.players()


def _mtime():
    try:
        return max(os.path.getmtime(os.path.join(ROOT, f)) for f in ('nba_injuries.json', 'nba_espn_games.json', 'nba_player_values.json', 'nba_roster_live.json'))
    except Exception:
        return 0


def _gr_time(utc):
    try:
        t = dt.datetime.fromisoformat(str(utc).replace('Z', '+00:00'))
        from zoneinfo import ZoneInfo
        t = t.astimezone(ZoneInfo('Europe/Athens'))
        return f"{['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ'][t.weekday()]} {t:%d/%m %H:%M}"
    except Exception:
        return str(utc)[:16]


def _table(rows):
    import nba_board
    return [{'Παικτης': r['name'], 'Χαντικαπ': f"{-r['imp_m']:+.1f}", 'Συνολο': f"{r['imp_t']:+.1f}",
             'Κατασταση': (nba_board.gr_status(r['status']) + (' ✓' if r['in_model'] else '')) if r['status'] else '',
             'Λεπτα': f"{r['min']:.0f}" + ('*' if r['msrc'] == 'περσι' else ''), 'Αξια': f"{r['v']:+.2f}"} for r in rows]


def _edge(e):
    return f"{100 * e:+.1f}%" + (' ✅' if e >= 0.08 else '')


def render(proj):
    """Καλειται απο render_nba."""
    import nba_board
    P = _players(_mtime())
    inj = _load('nba_injuries.json', {})
    odds = _load('nba_odds_latest.json', {}).get('odds', {})
    sm, stt = float(proj.get('sigma_margin', 11.5)), float(proj.get('sigma_total', 16.7))
    st.markdown('#### 🩹 Παικτες & απουσιες — «τι γινεται αν λειψει»')
    st.caption('Ποσο κοστιζει καθε παικτης αν δεν παιξει, με τους ΙΔΙΟΥΣ αριθμους του live μοντελου: χαντικαπ 0.75 × (αξια + 1) × λεπτα/48 · '
               'συνολο: χαμενη επιθεση −0.5, χαμενη αμυνα +1.0. Λεπτα = μεσος φετος (≤10 τελευταια ματς), αλλιως περσινα. '
               'Στηλες «Χαντικαπ / Συνολο» = ποσο αλλαζει η προβλεψη αν ΔΕΝ παιξει. Λεπτα με * = περσινα. '
               '✓ = ΕΚΤΟΣ που το μοντελο ΗΔΗ μετρα (δεν ξαναμετραει). Αμφιβολοι (DTD / Q / D) ΔΕΝ μετρανε — διαλεξε τους παρακατω για να δεις τι θα γινει. '
               f"Λιστα ESPN: **{str(inj.get('fetched', ''))[:16].replace('T', ' ')} UTC**")
    now = dt.datetime.now(dt.timezone.utc)
    up = [g for g in proj.get('games', []) if not g.get('played')
          and dt.datetime.fromisoformat(str(g['utc']).replace('Z', '+00:00')) > now - dt.timedelta(hours=3)]
    up.sort(key=lambda g: g['utc'])
    t1, t2 = st.tabs(['Ματς: τι γινεται αν λειψει', 'Βαση παικτων ανα ομαδα'])
    with t1:
        if not up:
            st.info('Δεν υπαρχουν επερχομενα ματς με προβλεψη.')
        else:
            gi = st.selectbox('Ματς', range(len(up)), key='nba_wi_game',
                              format_func=lambda i: f"{_gr_time(up[i]['utc'])} · {up[i]['home']} - {up[i]['away']}")
            g = up[gi]; pin = (odds.get(str(g['code'])) or {}).get('pin') or {}
            c1, c2 = st.columns(2)
            outs = {}
            for col, code, nm, k in ((c1, g['hcode'], g['home'], 'h'), (c2, g['acode'], g['away'], 'a')):
                rows = P.get(code, [])
                opts = [r['name'] for r in rows if not r['in_model']]
                lab = {r['name']: f"{r['name']} ({nba_board.gr_status(r['status']) + ' · ' if r['status'] else ''}{-r['imp_m']:+.1f} π.)" for r in rows}
                with col:
                    st.markdown(f"**{nm}**")
                    outs[k] = st.multiselect('Δεν παιζουν (επιπλεον)', opts, key=f"nba_wi_{k}_{g['code']}", format_func=lambda n, lab=lab: lab.get(n, n))
                    st.dataframe(_table(rows[:12]), hide_index=True, use_container_width=True)
            w0 = nba_board.whatif(g, pin, [], [], P, sm, stt)
            w1 = nba_board.whatif(g, pin, outs['h'], outs['a'], P, sm, stt)
            hm = lambda m: f"{g['home']} {-m:+.1f}"
            st.markdown('**Χαντικαπ**')
            if 'line' in w1:
                st.markdown(f"Μοντελο τωρα: **{hm(w0['margin'])}** → με τις επιλογες: **{hm(w1['margin'])}** ({w1['dm']:+.1f} π. για {g['home']}) · "
                            f"αγορα Pinnacle: **{g['home']} {w1['line']:+g}** @{float(pin['oh']):.2f} / {g['away']} {-w1['line']:+g} @{float(pin['oa']):.2f}")
                st.markdown(f"edge {g['home']}: {_edge(w0['e_h'])} → **{_edge(w1['e_h'])}** · edge {g['away']}: {_edge(w0['e_a'])} → **{_edge(w1['e_a'])}**")
            else:
                st.markdown(f"Μοντελο: {hm(w0['margin'])} → {hm(w1['margin'])} · δεν υπαρχει ακομα γραμμη Pinnacle")
            st.markdown('**Συνολο**')
            if 'tl' in w1:
                st.markdown(f"Μοντελο τωρα: **{w0['total']:.1f}** → με τις επιλογες: **{w1['total']:.1f}** ({w1['dt']:+.1f}) · αγορα Pinnacle: **{w1['tl']:g}** "
                            f"(Over @{float(pin['to']):.2f} / Under @{float(pin['tu']):.2f})")
                st.markdown(f"edge Over: {_edge(w0['e_o'])} → **{_edge(w1['e_o'])}** · edge Under: {_edge(w0['e_u'])} → **{_edge(w1['e_u'])}**")
            else:
                st.markdown(f"Μοντελο: {w0['total']:.1f} → {w1['total']:.1f} · δεν υπαρχει ακομα γραμμη Pinnacle")
            st.caption('✅ = περνα το κατωφλι 8% του χαντικαπ. Τα συνολα NBA ειναι σε καταγραφη (δεν παιζονται) — το edge συνολου εδω ειναι του μοντελου μονο του, '
                       'χωρις τη μιξη 50/50 με την αγορα. Η αλλαγη γραμμης της αγορας μετα την ειδηση δεν φαινεται εδω — συγκρινε με την τιμη που βλεπεις τη στιγμη εκεινη.')
    with t2:
        teams = sorted(P, key=lambda c: next((g['home'] for g in proj.get('games', []) if g['hcode'] == c),
                                             next((g['away'] for g in proj.get('games', []) if g['acode'] == c), c)))
        names = {}
        for g in proj.get('games', []):
            names[g['hcode']] = g['home']; names[g['acode']] = g['away']
        tc = st.selectbox('Ομαδα', teams, key='nba_board_team', format_func=lambda c: names.get(c, c))
        st.dataframe(_table(P.get(tc, [])), hide_index=True, use_container_width=True)
