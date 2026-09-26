"""
intl_pricing.py — ΣΩΣΤΗ τιμολογηση OVER για τις εθνικες (25/9/2026, αποφαση Στελιου).

Ο παλιος τυπος (P(συνολο > floor(γραμμη)) × τιμη − 1) αγνοουσε push και μισα:
  x.25 και x.75 μετρουσαν σαν x.5, οι ακεραιες (2.0, 3.0) σαν x.5 με το push ως ηττα.
Τεστ 25/9 (intl_window_test.py OVER_FORMULA=live|proper): closing ROI +11.6→+16.4% (Crown), +12.3→+16.8% (SBOBET), μοναδες ×2·
72ω ROI 14.4→12.0 / 15.8→13.5 με ιδιες περιπου μοναδες. Ο Στελιος διαλεξε τον σωστο τυπο (πραγματικο edge σε καθε γραμμη).

Εκκαθαριση που αντιστοιχει:  x.5 = κερδος/ηττα · ακεραια = push επιστρεφει · x.25 / x.75 = μισο στις δυο διπλανες γραμμες.
"""
import math


def _pk(T, k):
    return math.exp(-T) * T ** k / math.factorial(k)


def over_ev(T, line, odds):
    """Αναμενομενη αποδοση (edge) ενος over στη γραμμη `line` με δεκαδικη τιμη `odds`, οταν το συνολο γκολ ~ Poisson(T)."""
    q = round(float(line) * 4) / 4
    if abs(q * 2 - round(q * 2)) > 1e-9:                      # x.25 / x.75 -> μισο/μισο
        return 0.5 * over_ev(T, q - 0.25, odds) + 0.5 * over_ev(T, q + 0.25, odds)
    pw = 1 - sum(_pk(T, k) for k in range(int(math.floor(q)) + 1))      # κερδιζει: συνολο > γραμμη
    pp = _pk(T, int(q)) if float(q).is_integer() else 0.0               # push: συνολο == ακεραια γραμμη
    return pw * (odds - 1) - (1 - pw - pp)


def over_p_equiv(T, line, odds):
    """«Ισοδυναμη» πιθανοτητα: αυτη που, στην ιδια τιμη, δινει το ιδιο edge με ενα απλο (χωρις push) over. Για προβολη στο dashboard."""
    return (over_ev(T, line, odds) + 1) / odds


def over_fair(T, line):
    """Fair τιμη (edge 0) του over στη γραμμη — λυση της over_ev(T, line, o) = 0."""
    lo, hi = 1.01, 50.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if over_ev(T, line, mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---------------- HANDICAP (25/9/2026, αποφαση Στελιου: σωστα τεταρτα και στο AH των εθνικων) ----------------
# Παλια: picks.p_cover στη γραμμη → +x.25 μετρουσε σαν +x.5, −x.75 σαν −x.5 κλπ (τεταρτα = κοντινοτερη μιση).
# Σωστα: x.25 / x.75 = μισο πονταρισμα σε καθε διπλανη γραμμη (οπως πληρωνει το βιβλιο και οπως εκκαθαριζει το picks.settle).
# Τεστ 25/9 (intl_window_test.py AH_FORMULA=proper, intl_ah_quarter_out.txt): ROI 72ω +3.6→+5.3% (Crown), +4.2→+5.2% (SBOBET)·
# κερδιζει φαβορι −x.25, κοβει φαβορι −x.75· ΧΑΝΕΙ dog +x.25 (αντισταθμιστικο λαθος: το μοντελο υποτιμα «φαβορι +1»).
# ΕΚΚΡΕΜΕΙ: διορθωση του μοντελου στα στενα αποτελεσματα· αν δεν δουλεψει → εξεταση dog +x.25 με τον παλιο τροπο.
# Τα ΕΓΧΩΡΙΑ μενουν με picks.p_cover (τεστ 21/9 εκει ❌).
def _parts(ud):
    """25/9/2026 (β) ΣΧΕΔΙΟ Β (αποφαση Στελιου): dog +x.25 (+0.25/+1.25/+2.25…) τιμολογειται με τον ΠΑΛΙΟ τροπο (σαν +x.5, p_cover στη γραμμη)·
    ολα τα αλλα τεταρτα σωστα (μισο/μισο). Τεστ intl_window_test.py AH_FORMULA=hybrid: συναινεση dogs +4.5→~+12%, φαβορι ιδια, συνολο +10.5→+11.3%
    (μεσος Crown/SBOBET). Λογος: το μοντελο υποτιμα τη «νικη φαβορι με 1» (ολα τα μοντελα μας, εθνικες 20.5 vs 22.8%) και ο παλιος τροπος το αντισταθμιζει
    ακριβως στα +x.25 — ιδιο ευρημα με τα εγχωρια (21/9). ΑΝ ΑΛΛΑΞΕΙ Η ΚΑΤΑΝΟΜΗ ΤΟΥ ΜΟΝΤΕΛΟΥ → ξαναμετρηση. Η εκκαθαριση (settle) μενει σωστη."""
    if ud > 0 and abs(ud % 1 - 0.25) < 1e-9:
        return [ud]
    return [ud] if (ud * 4) % 2 == 0 else [ud - 0.25, ud + 0.25]


# ---------------- 25/9/2026 (γ) ΒΑΘΙΑ ΦΑΒΟΡΙ (αποφαση Στελιου): σωστη υπεροχη μονο για φαβορι −2 και βαθυτερα ----------------
# Η υπεροχη του live (a·diff, a μετρημενο χωρις αξια) φουσκωνει τη νικη φαβορι με 3+ στα Μ1/Μ3. Για πλευρα με handicap ≤ −2 το edge υπολογιζεται
# με κατανομη απο a_deep (intl_deepfav_config.json· intl_project → στηλες xg_*_D). Τεστ GD_FIX=deepfav: βαθια φαβορι +6.1→+15.6%, 93→46 picks.
DEEP_LINE = -2.0


def dist_for(dist, dist_deep, ud):
    """η κατανομη που τιμολογει τη γραμμη ud: η «βαθια» για φαβορι ≤ −2 (αν υπαρχει), αλλιως η κανονικη."""
    return dist_deep if (dist_deep is not None and ud <= DEEP_LINE + 1e-9) else dist


def ah_ev(dist, side, ud, odds, margin=0.0):
    """Edge AH με σωστα τεταρτα. dist = κατανομη διαφορας γκολ (picks.gd_dist), side 1 γηπεδουχος / −1 φιλοξενουμενος,
    ud = handicap της πλευρας, margin = ποσοστο που αφαιρειται απο το κερδος (picks.MARGIN στο live)."""
    import picks
    e = 0.0
    for L in _parts(ud):
        pw, pp = picks.p_cover(dist, side, L)
        e += (pw * (odds - 1) * (1 - margin) - (1 - pw - pp)) / len(_parts(ud))
    return e


def ah_fair(dist, side, ud):
    """Fair τιμη (edge 0, χωρις margin) της πλευρας στη γραμμη ud, με σωστα τεταρτα. None αν δεν οριζεται."""
    import picks
    sw = sl = 0.0
    for L in _parts(ud):
        pw, pp = picks.p_cover(dist, side, L); sw += pw; sl += 1 - pw - pp
    return round(1 + sl / sw, 2) if sw > 0 else None


def settle_over(total, line, odds):
    """Αποτελεσμα (μοναδες ανα 1 πονταρισμα) ενος over: x.5 κερδος/ηττα, ακεραια push = 0, x.25/x.75 μισο/μισο."""
    q = round(float(line) * 4) / 4
    if abs(q * 2 - round(q * 2)) > 1e-9:
        return 0.5 * settle_over(total, q - 0.25, odds) + 0.5 * settle_over(total, q + 0.25, odds)
    if total > q:
        return odds - 1
    return 0.0 if abs(total - q) < 1e-9 else -1.0


# ---------------- 26/9/2026 (δ) ΝΕΟ T ΓΙΑ ΤΑ OVER (αποφαση Στελιου): T + xG επιθεσης/αμυνας ομαδων ----------------
# Το T «καταστασης» (διαφορα/κοντινο/επιπεδο) δεν ηξερε ΠΩΣ παιζουν οι ομαδες (π.χ. Βουλγαρια−Λουξεμβουργο: 0.3-0.5 γκολ υπερ ανα ματς).
# T_over = b0 + b1·T + b2·(λh_xG + λa_xG) (intl_tmix_config.json· xG ομαδων intl_xg_attdef.json, 12 αγωνιστικα, διορθωση αντιπαλου).
# Τεστ 72ω: over συναινεσης +13.2→+17.5% (5/5), «στεγνες» ομαδες +7.9→+22.9%· ακριβεια γκολ MAE 1.383→1.344. ΜΟΝΟ στα over (τα handicap μενουν).
def team_xg_sum(AD, hid, aid, neutral=False, nmin=3):
    """λ_h + λ_a (αναμενομενο xG ματς απο επιθεση/αμυνα των 2 ομαδων) ή None αν λειπει ιστορικο (< nmin ματς με xG)."""
    if not AD or hid is None or aid is None:
        return None
    meta = AD.get('_meta') or {}; MU = meta.get('mu', 1.231); HF = meta.get('hf', 1.15)
    h, a = AD.get(str(int(hid))), AD.get(str(int(aid)))
    if not h or not a or h.get('n', 0) < nmin or a.get('n', 0) < nmin:
        return None
    hf = 1.0 if neutral else HF
    return MU * (h['att'] / MU) * (a['dfn'] / MU) * hf + MU * (a['att'] / MU) * (h['dfn'] / MU) / hf


def t_over(T, ver, xgsum, cfg):
    """ΝΕΟ T για τα over (εκδοχη ver = H/A/AV)· χωρις xG ομαδων ή config → το T της καταστασης."""
    if T is None or xgsum is None or not cfg or ver not in cfg:
        return T
    b = cfg[ver]
    return max(b[0] + b[1] * T + b[2] * xgsum, 0.8)


# ---------------- 26/9/2026 (ε) BTTS — ΜΟΝΟ ΕΝΗΜΕΡΩΤΙΚΟ στο dashboard (αποφαση Στελιου: «θα το δουμε», οχι picks) ----------------
# Τεστ btts_test.py (26/9): εθνικες 972 ματς — P_mod(BTTS) εχει πληροφορια περα απο την αγορα (Μ1 b +0.83 t 3.9, 5/5 σεζον· υποθ. ROI@8%
# +15%)· εγχωρια FAIL. Επιφυλαξεις: T in-sample, πιθανη επικαλυψη με τσεπη over, «αγορα» = proxy απο AH+O/U (οχι πραγματικη τιμη BTTS).
def btts_p(lh, la):
    """P(σκοραρουν και οι δυο) με ανεξαρτητο Poisson (ιδιο με το τεστ)."""
    return (1 - math.exp(-lh)) * (1 - math.exp(-la))


def _pois(l, k):
    return math.exp(-l) * l ** k / math.factorial(k)


def _cover_q(lh, la, line, total=False, K=11):
    """P(καλυψη | οχι push) για γηπεδουχο στο AH line (ή over στο line αν total) — τεταρτα μισο/μισο."""
    q = round(float(line) * 4) / 4
    parts = [q] if abs(q * 2 - round(q * 2)) < 1e-9 else [q - 0.25, q + 0.25]
    W = Ls = 0.0
    for i in range(K):
        pi = _pois(lh, i)
        for j in range(K):
            p = pi * _pois(la, j)
            for L in parts:
                m = (i + j - L) if total else (i - j + L)
                if m > 1e-9:
                    W += p
                elif m < -1e-9:
                    Ls += p
    return W / max(W + Ls, 1e-12)


def market_lambdas(ah_line, oh, oa, ou_line, over, under):
    """λ_h, λ_a της ΑΓΟΡΑΣ απο το AH (γραμμη γηπεδουχου) και το O/U χωρις γκανιοτα — εμφωλευμενη διχοτομηση (T απο O/U, s απο AH)."""
    qh = (1 / oh) / (1 / oh + 1 / oa); qo = (1 / over) / (1 / over + 1 / under)

    def s_for(T):
        lo, hi = -T + 0.04, T - 0.04
        for _ in range(30):
            s = (lo + hi) / 2
            if _cover_q((T + s) / 2, (T - s) / 2, ah_line) < qh:
                lo = s
            else:
                hi = s
        return (lo + hi) / 2
    Tlo, Thi = 0.4, 7.0
    for _ in range(26):
        T = (Tlo + Thi) / 2; s = s_for(T)
        if _cover_q((T + s) / 2, (T - s) / 2, ou_line, total=True) < qo:
            Tlo = T
        else:
            Thi = T
    T = (Tlo + Thi) / 2; s = s_for(T)
    return (T + s) / 2, (T - s) / 2

