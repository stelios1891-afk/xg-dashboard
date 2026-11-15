"""southam_common.py — κοινα εργαλεια Βραζιλιας/MLS (5/10/2026): ταιριασμα ονοματων/ημερομηνιας, αγορα 1Χ2 → λ, πιθανοτητες απο λ."""
import re, unicodedata
import numpy as np, pandas as pd
import picks

ALIAS = {  # FotMob / Nowgoal / football-data → κοινο κλειδι
    'atletico mg': 'atleticomineiro', 'atletico-mg': 'atleticomineiro', 'atletico mineiro': 'atleticomineiro',
    'athletico-pr': 'athleticoparanaense', 'athletico paranaense': 'athleticoparanaense', 'atletico pr': 'athleticoparanaense', 'athletico pr': 'athleticoparanaense',
    'atletico go': 'atleticogoianiense', 'atletico goianiense': 'atleticogoianiense',
    'america mg': 'americamineiro', 'america mineiro': 'americamineiro',
    'botafogo rj': 'botafogo', 'botafogo': 'botafogo', 'flamengo rj': 'flamengo', 'flamengo': 'flamengo',
    'red bull bragantino': 'bragantino', 'bragantino': 'bragantino', 'rb bragantino': 'bragantino', 'bragantino-sp': 'bragantino',
    'santos fc': 'santos', 'santos': 'santos', 'vasco da gama': 'vasco', 'vasco': 'vasco',
    'chapecoense-sc': 'chapecoense', 'chapecoense af': 'chapecoense', 'chapecoense': 'chapecoense',
    'sport recife': 'sport', 'sport': 'sport', 'cuiaba': 'cuiaba', 'ceara': 'ceara', 'criciuma': 'criciuma',
    'atlanta utd': 'atlanta', 'atlanta united': 'atlanta', 'charlotte': 'charlotte', 'charlotte fc': 'charlotte',
    'chicago fire': 'chicago', 'chicago fire fc': 'chicago', 'houston dynamo': 'houston', 'houston dynamo fc': 'houston',
    'inter miami': 'miami', 'inter miami cf': 'miami', 'los angeles galaxy': 'lagalaxy', 'la galaxy': 'lagalaxy',
    'los angeles fc': 'lafc', 'new york city': 'nycfc', 'new york city fc': 'nycfc',
    'new york red bulls': 'nyrb', 'red bull new york': 'nyrb', 'seattle sounders': 'seattle', 'seattle sounders fc': 'seattle',
    'st. louis city': 'stlouis', 'st louis city': 'stlouis', 'st. louis city sc': 'stlouis',
    'cf montreal': 'montreal', 'montreal impact': 'montreal', 'dc united': 'dcunited', 'd.c. united': 'dcunited',
    'minnesota united': 'minnesota', 'minnesota utd': 'minnesota', 'sporting kansas city': 'skc', 'sporting kc': 'skc',
    'new england revolution': 'newengland', 'new england': 'newengland', 'columbus crew': 'columbus', 'columbus crew sc': 'columbus',
    'san jose earthquakes': 'sanjose', 'san jose': 'sanjose', 'vancouver whitecaps': 'vancouver', 'vancouver whitecaps fc': 'vancouver',
    'real salt lake': 'rsl', 'portland timbers': 'portland', 'toronto fc': 'toronto', 'orlando city': 'orlando', 'orlando city sc': 'orlando',
    'philadelphia union': 'philadelphia', 'nashville sc': 'nashville', 'austin fc': 'austin', 'fc dallas': 'dallas',
    'fc cincinnati': 'cincinnati', 'colorado rapids': 'colorado', 'san diego fc': 'sandiego', 'san diego': 'sandiego',
}

def key(name):
    s = unicodedata.normalize('NFKD', str(name)).encode('ascii', 'ignore').decode().lower().strip()
    s = re.sub(r'\s+', ' ', s)
    if s in ALIAS: return ALIAS[s]
    s2 = re.sub(r'\b(fc|sc|ec|cf|afc|club|de|futebol)\b', '', s)
    return re.sub(r'[^a-z]', '', s2)

def fd_load(code, lg):
    d = pd.read_csv(f'southam/fd_{code}.csv', encoding='utf-8-sig')
    d['date'] = pd.to_datetime(d.Date, dayfirst=True)
    d['kh'] = d.Home.map(key); d['ka'] = d.Away.map(key); d['league'] = lg
    return d

def attach_fd(P):
    """P: southam_preds (home_name/away_name/date) → προσθετει PSCH/PSCD/PSCA/AvgC*/MaxC* (τελικες 1Χ2)."""
    F = pd.concat([fd_load('BRA', 'Brazil'), fd_load('USA', 'MLS')], ignore_index=True)
    idx = {}
    for i, r in F.iterrows():
        for dd in (-1, 0, 1):
            idx.setdefault((r.league, r.kh, r.ka, (r.date + pd.Timedelta(days=dd)).strftime('%Y-%m-%d')), i)
    cols = ['PSCH', 'PSCD', 'PSCA', 'AvgCH', 'AvgCD', 'AvgCA', 'MaxCH', 'MaxCD', 'MaxCA', 'B365CH', 'B365CD', 'B365CA']
    hit = [idx.get((r.league, key(r.home_name), key(r.away_name), r.date)) for r in P.itertuples()]
    for c in cols:
        P[c] = [F.at[i, c] if i is not None else np.nan for i in hit]
    return P

# ---- λ απο αγορα 1Χ2 (πλεγμα Dixon-Coles) ----
_G = np.arange(0.15, 4.01, 0.025)
_TAB = None
def _table():
    global _TAB
    if _TAB is None:
        rows = []
        for lh in _G:
            for la in _G:
                Pm = picks.score_matrix_dom(lh, la)
                rows.append((lh, la, np.tril(Pm, -1).sum(), np.trace(Pm), np.triu(Pm, 1).sum()))
        _TAB = np.array(rows)
    return _TAB

def market_lambdas(pH, pD, pA):
    """πλησιεστερο (λh, λa) που αναπαραγει τις (χωρις γκανιοτα) πιθανοτητες 1Χ2."""
    T = _table(); out = []
    for h, d, a in zip(pH, pD, pA):
        if not np.isfinite(h): out.append((np.nan, np.nan)); continue
        e = (T[:, 2] - h) ** 2 + (T[:, 3] - d) ** 2 + (T[:, 4] - a) ** 2
        k = int(np.argmin(e)); out.append((T[k, 0], T[k, 1]))
    return np.array(out)

def probs_1x2(lh, la):
    Pm = picks.score_matrix_dom(max(lh, .05), max(la, .05))
    return np.tril(Pm, -1).sum(), np.trace(Pm), np.triu(Pm, 1).sum()

def rps(p, res):
    """p = (pH, pD, pA), res ∈ {1,0,−1} (γηπεδουχος/ισοπαλια/φιλοξ)."""
    o = {1: (1, 0, 0), 0: (0, 1, 0), -1: (0, 0, 1)}[res]
    c1 = p[0] - o[0]; c2 = p[0] + p[1] - o[0] - o[1]
    return (c1 ** 2 + c2 ** 2) / 2
