"""
Expansion-league name aliases (μοντελο/FotMob ονομα -> football-data odds ονομα).
Το picks.py ειναι ΚΛΕΙΔΩΜΕΝΟ· αυτα τα aliases ζουν εδω και εφαρμοζονται RUNTIME
στα research/backtest scripts:

    import picks as E, league_aliases
    league_aliases.apply(E)                       # προσθετει τα aliases στο E.ALIAS
    name = league_aliases.fix_mojibake(raw_name)  # για odds ονοματα απο hist/ αρχεια

Αναγκαια για να φτασει 100% coverage στις υπο-αξιολογηση λιγκες (χωρις 100% + 0 collisions
τα αποτελεσματα ειναι selection artifacts — ΜΗΝ τα εμπιστευεσαι).
"""

EXPANSION_ALIAS = {
    'Sheffield Wednesday': 'Sheffield Weds',   # αλλιως COLLISION -> Sheffield United (Championship)
    'Queens Park Rangers': 'QPR',              # Championship
    'Heart of Midlothian': 'Hearts',           # ScottishPrem
    'Karlsruher SC': 'Karlsruhe',              # Bundesliga2
    'AE Larissa': 'Larisa',                    # GreeceSL
    'Levadiakos': 'Levadeiakos',               # GreeceSL
    'Olympiacos': 'Olympiakos',                # GreeceSL
    # Preussen Münster -> λυνεται με fix_mojibake (το odds ονομα ειναι UTF-8-ως-latin-1)
}

def fix_mojibake(s):
    """football-data hist αρχεια καποιες φορες UTF-8 διαβασμενα ως latin-1 (π.χ. 'PreuÃen MÃ¼nster').
    Το ξαναφτιαχνει· αν το ονομα ειναι ηδη σωστο, το επιστρεφει αναλλοιωτο."""
    try:
        return s.encode('latin-1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError, AttributeError):
        return s

def apply(E):
    """Προσθετει τα expansion aliases στο in-memory E.ALIAS (ΔΕΝ αγγιζει το locked picks.py)."""
    E.ALIAS.update(EXPANSION_ALIAS)
    return E.ALIAS
