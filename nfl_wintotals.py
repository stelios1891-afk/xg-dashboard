"""NFL win totals πριν τη σεζον (sportsoddshistory.com) → nfl_data/win_totals.csv

  python nfl_wintotals.py            → ολες οι σεζον 2015..φετος
  python nfl_wintotals.py 2027       → μια σεζον

Αναμενομενες νικες (E) απο γραμμη + αποδοσεις over/under χωρις γκανιοτα:
  P(over) = Φ((E − γραμμη)/σ), σ = 2.3 νικες → E = γραμμη + σ·Φ⁻¹(P(over)).  wpct = E / ματς σεζον (16 ως 2020, 17 μετα).
"""
import html, os, re, sys, time, urllib.request
from statistics import NormalDist
import pandas as pd

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nfl_data')
URL = 'https://www.sportsoddshistory.com/nfl-win/?y={y}&sa=nfl&t=win&o=t'
SIG = 2.3
NAMES = {
    'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL', 'Buffalo Bills': 'BUF',
    'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI', 'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE',
    'Dallas Cowboys': 'DAL', 'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
    'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX', 'Kansas City Chiefs': 'KC',
    'Las Vegas Raiders': 'LV', 'Oakland Raiders': 'LV', 'Los Angeles Chargers': 'LAC', 'San Diego Chargers': 'LAC',
    'Los Angeles Rams': 'LA', 'St. Louis Rams': 'LA', 'St Louis Rams': 'LA', 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN',
    'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG', 'New York Jets': 'NYJ',
    'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT', 'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA',
    'Tampa Bay Buccaneers': 'TB', 'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS',
    'Washington Redskins': 'WAS', 'Washington Football Team': 'WAS', 'Washington': 'WAS',
}


def am2p(a):
    a = float(a)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def parse(s, y):
    t = re.findall(r'<table.*?</table>', s, re.S)[0]
    out = []
    for r in re.findall(r'<tr.*?</tr>', t, re.S)[1:]:
        c = [html.unescape(re.sub(r'<[^>]+>', '', x)).strip() for x in re.findall(r'<t[dh].*?</t[dh]>', r, re.S)]
        if len(c) < 4 or c[0] not in NAMES:
            if c and c[0]:
                print('  αγνωστη ομαδα:', c[0])
            continue
        line = float(c[1])
        po, pu = am2p(c[2]), am2p(c[3])
        p = po / (po + pu)
        E = line + SIG * NormalDist().inv_cdf(min(max(p, 0.02), 0.98))
        n = 16 if y <= 2020 else 17
        out.append(dict(season=y, team=NAMES[c[0]], line=line, over=c[2], under=c[3], p_over=round(p, 4),
                        E=round(E, 3), wpct=round(E / n, 4), actual=c[5] if len(c) > 5 else ''))
    return out


def main():
    f = os.path.join(D, 'win_totals.csv')
    years = [int(sys.argv[1])] if len(sys.argv) > 1 else list(range(2015, pd.Timestamp.now().year + 1))
    old = pd.read_csv(f) if os.path.exists(f) else pd.DataFrame()
    rows = []
    for y in years:
        req = urllib.request.Request(URL.format(y=y), headers={'User-Agent': 'Mozilla/5.0'})
        s = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'ignore')
        r = parse(s, y)
        print(y, len(r), 'ομαδες')
        rows += r
        time.sleep(2)
    new = pd.DataFrame(rows)
    if len(old):
        new = pd.concat([old[~old.season.isin(years)], new])
    new.sort_values(['season', 'team']).to_csv(f, index=False)


if __name__ == '__main__':
    main()
