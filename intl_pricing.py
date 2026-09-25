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
