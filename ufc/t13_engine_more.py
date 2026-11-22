"""UFC τεστ 13: ό,τι έμεινε ανοιχτό στη μηχανή, απέναντι στην ίδια βάση.

Βάση: αγορά + μηχανή Μ7+επίπεδο, καθαροί μέσοι όροι, walk-forward 2017-26. Παραλλαγές ορισμένες από πριν:
  Τ   τόπος γέννησης (Sherdog locality): γεννήθηκε στην πόλη/περιοχή του αγώνα, χωριστά ΗΠΑ / εκτός ΗΠΑ
  Π3  μέσος όρος μόνο των τελευταίων 3 ετών (ufc_features_recent3.csv)
  Φ2/Φ4 τα στατιστικά του μαχητή με φθορά: παλιός αγώνας χάνει το μισό βάρος κάθε 2 / 4 χρόνια (ufc_features_decayΝ.csv)
  Ν1  γραμμικό με αλληλεπιδράσεις: στατιστικά×εμπειρία, βαριές κατηγορίες, γυναίκες, ηλικία πάνω από 35
  Ν2  δέντρα (gradient boosting): διαφορές + επίπεδα (μέση ηλικία, εμπειρία, κατηγορία), ρυθμίσεις από <2017
Κριτήριο: μίξη με το άνοιγμα, διαφορά log-loss από τη βάση t ≤ −2, κλείσιμο όχι χειρότερο, ROI ≥5 μονάδων όχι χειρότερο.
Θέλει UFC_DATA.
"""
import os

import numpy as np
import pandas as pd

import t3_mechanisms as t3
from t2_age_repl import DATA
from t8_sherdog import nat_norm
from t10_own_engine import BODY, HOME, SHER, STATS, build, roi
from t11_level_select import DLEVEL, LEVEL, Ls, cv_fit, design, engine_wf, level_features, mix_wf, ridge

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
lg, sig = t3.lg, t3.sig
BASE = ["age"] + STATS + BODY + HOME + SHER + LEVEL + DLEVEL
tstat = lambda d: d.mean() / (d.std() / np.sqrt(len(d)))


def load(name):
    os.environ["UFC_FEATURES"] = name
    o, D, w = build()
    return o, level_features(o, D), w


def birthplace(o, D):
    A = pd.read_csv(DATA / "sherdog_fighters.csv").drop_duplicates("fighter").set_index("fighter")
    nat, loc = A.nationality.map(nat_norm), A.locality.fillna("")
    parts = lambda s: {p.strip().lower() for p in str(s).split(",") if p.strip()}
    cty = o.location.fillna("").str.split(",").str[-1].str.strip().replace({"United Kingdom": "UK"})
    place = o.location.fillna("").map(lambda s: parts(",".join(s.split(",")[:-1])))
    same = {}
    for s in ("f1", "f2"):
        same[s] = np.array([nat.get(f) == c and bool(parts(loc.get(f, "")) & pl) for f, c, pl in zip(o[s], cty, place)], float)
    us = (cty == "USA").values
    r = same["f1"] - same["f2"]
    D["born_us"], D["born_nus"] = r * us, r * ~us
    return D


def interactions(o, D):
    e = np.minimum(o.f1_lnexp, o.f2_lnexp).values
    hw = o.weightclass.fillna("").str.contains("Heavyweight").values.astype(float)
    wm = o.women.astype(bool).values.astype(float)
    X = pd.DataFrame(index=D.index)
    for c in ("sdiff_adj", "sapm", "td15"):
        X[c + "_exp"] = D[c] * e
    for c in ("age", "sdiff_adj", "td15"):
        X[c + "_hw"] = D[c] * hw
    for c in ("age", "td15"):
        X[c + "_w"] = D[c] * wm
    X["age_35"] = np.maximum(o.a1 - 35, 0) - np.maximum(o.a2 - 35, 0)
    return X


class Boost:
    """Λογιστικά δέντρα με ιστογράμματα (numpy)· φυλάει τις προβλέψεις σε όποιους γύρους ζητηθούν."""

    def __init__(self, depth, rounds, lr=.03, min_leaf=50, l2=1.0, bins=32):
        self.depth, self.rounds, self.lr, self.min_leaf, self.l2, self.bins = depth, rounds, lr, min_leaf, l2, bins

    def bin(self, X):
        B = np.zeros(X.shape, np.int64)
        for j, e in enumerate(self.edges):
            B[:, j] = np.searchsorted(e, X[:, j], side="left")
        return np.where(np.isnan(X), self.bins, B)  # λείπει = δικό του κουτί

    def grow(self, B, idx, g, h, depth):
        leaf = lambda: ("L", self.lr * g[idx].sum() / (h[idx].sum() + self.l2))
        if depth == 0 or len(idx) < 2 * self.min_leaf:
            return leaf()
        nb, nf = self.bins + 1, B.shape[1]
        flat = (B[idx] + np.arange(nf) * nb).ravel()
        G = np.bincount(flat, np.repeat(g[idx], nf), nb * nf).reshape(nf, nb).cumsum(1)
        H = np.bincount(flat, np.repeat(h[idx], nf), nb * nf).reshape(nf, nb).cumsum(1)
        C = np.bincount(flat, minlength=nb * nf).reshape(nf, nb).cumsum(1)
        Gt, Ht, n = G[0, -1], H[0, -1], len(idx)
        gain = G ** 2 / (H + self.l2) + (Gt - G) ** 2 / (Ht - H + self.l2) - Gt ** 2 / (Ht + self.l2)
        gain[(C < self.min_leaf) | (n - C < self.min_leaf)] = -1
        j, t = np.unravel_index(gain.argmax(), gain.shape)
        if gain[j, t] <= 0:
            return leaf()
        left = B[idx, j] <= t
        return ("N", j, t, self.grow(B, idx[left], g, h, depth - 1), self.grow(B, idx[~left], g, h, depth - 1))

    def add(self, tree, B, idx, F):
        if tree[0] == "L":
            F[idx] += tree[1]
            return
        left = B[idx, tree[1]] <= tree[2]
        self.add(tree[3], B, idx[left], F); self.add(tree[4], B, idx[~left], F)

    def run(self, X, y, tests, keep):
        """tests = πίνακες πρόβλεψης· επιστρέφει {γύρος: [logit ανά πίνακα]}."""
        self.edges = [np.unique(np.nanquantile(X[:, j], np.linspace(0, 1, self.bins + 1)[1:-1])) for j in range(X.shape[1])]
        B = self.bin(X); Bt = [self.bin(T) for T in tests]
        F, Ft, out, all_ = np.zeros(len(y)), [np.zeros(len(T)) for T in tests], {}, np.arange(len(y))
        for r in range(1, self.rounds + 1):
            p = sig(F)
            tree = self.grow(B, all_, y - p, p * (1 - p), self.depth)
            self.add(tree, B, all_, F)
            for bt, ft in zip(Bt, Ft):
                self.add(tree, bt, np.arange(len(ft)), ft)
            if r in keep:
                out[r] = [ft.copy() for ft in Ft]
        return out


def boosted(o, D, w, y):
    lvl = pd.DataFrame(dict(age_m=(o.a1 + o.a2) / 2, exp_min=np.minimum(o.f1_lnexp, o.f2_lnexp), exp_max=np.maximum(o.f1_lnexp, o.f2_lnexp),
                            pro_m=(o.f1_lnpro + o.f2_lnpro) / 2, hw=o.weightclass.fillna("").str.contains("Heavyweight").astype(float),
                            wm=o.women.astype(bool).astype(float))).values
    d = D[BASE].values
    KEEP = (100, 200, 400)

    def fit_pred(tr, te, depth, rounds, keep):
        """Κάθε αγώνας δύο φορές (f1−f2 και f2−f1)· η πρόβλεψη αντισυμμετρική, ώστε η θέση f1/f2 να μη μετράει."""
        Xt = np.r_[np.c_[d[tr], lvl[tr]], np.c_[-d[tr], lvl[tr]]]
        out = Boost(depth, rounds).run(Xt, np.r_[w[tr], 1 - w[tr]], [np.c_[d[te], lvl[te]], np.c_[-d[te], lvl[te]]], keep)
        return {r: sig((a - b) / 2) for r, (a, b) in out.items()}

    pre = np.where(y < 2017)[0]
    blocks = (y[pre] - y[pre].min()) // 3
    best = (9, None)
    for depth in (2, 3):
        L = {r: [] for r in KEEP}
        for b in np.unique(blocks):
            te_ = pre[blocks == b]
            for r, q in fit_pred(pre[blocks != b], te_, depth, max(KEEP), KEEP).items():
                L[r].append(Ls(q, w[te_]))
        for r in KEEP:
            s = np.concatenate(L[r]).mean()
            print(f"  δέντρα βάθος {depth}, {r} γύροι: CV log-loss {s:.4f}", flush=True)
            best = min(best, (s, (depth, r)), key=lambda t: t[0])
    depth, rounds = best[1]
    print(f"  επιλογή (μόνο <2017): βάθος {depth}, {rounds} γύροι", flush=True)
    q = np.full(len(y), np.nan)
    for Y in range(2012, 2027):
        q[y == Y] = fit_pred(np.where(y < Y)[0], np.where(y == Y)[0], depth, rounds, (rounds,))[rounds]
        print(f"  δέντρα {Y} έτοιμο", flush=True)
    return q


def main():
    o, D, w = load("ufc_features_causal.csv")
    y = o.y.values
    te = y >= 2017
    D = birthplace(o, D)
    print(f"αγώνες {len(o)} · 2017-26 {te.sum()}")
    b_us, b_nus = D.born_us.values, D.born_nus.values
    print(f"γεννημένος στην περιοχή του αγώνα, 2017-26: ΗΠΑ {int((b_us[te] != 0).sum())} · εκτός ΗΠΑ {int((b_nus[te] != 0).sum())}")
    print("παραδείγματα:")
    ex = o[te & ((b_us != 0) | (b_nus != 0))].sample(6, random_state=3)
    for i, r in ex.iterrows():
        print(f"  {r.date} {r.location}: {r.f1} vs {r.f2} · ΗΠΑ {b_us[i]:+.0f} εκτός {b_nus[i]:+.0f}")

    Q = {"βάση": engine_wf(D, BASE, w, y)}
    print("βάση έτοιμη", flush=True)
    Q["Τ τόπος γέννησης"] = engine_wf(D, BASE + ["born_us", "born_nus"], w, y)
    Z = design(D, BASE + ["born_us", "born_nus"], y, 2027)
    b = ridge(Z, w, cv_fit(Z, w, y))
    print("  βάρη ανά 1 τυπική απόκλιση: " + str(dict(zip(["home_nus", "home_us", "born_us", "born_nus"], np.round([b[BASE.index("home_nus")], b[BASE.index("home_us")], b[-2], b[-1]], 3)))), flush=True)
    for nm, f in (("Π3 μέσος 3 ετών", "ufc_features_recent3.csv"), ("Φ2 φθορά 2 ετών", "ufc_features_decay2.csv"), ("Φ4 φθορά 4 ετών", "ufc_features_decay4.csv")):
        o2, D2, w2 = load(f)
        assert (o2.fight_url.values == o.fight_url.values).all()
        Q[nm] = engine_wf(D2, BASE, w2, y)
        print(nm, "έτοιμη", flush=True)
    X = interactions(o, D)
    D3 = pd.concat([D[BASE], X], axis=1)
    Q["Ν1 αλληλεπιδράσεις"] = engine_wf(D3, BASE + list(X.columns), w, y)
    Z = design(D3, BASE + list(X.columns), y, 2027)
    b = ridge(Z, w, cv_fit(Z, w, y))
    print("  βάρη αλληλεπιδράσεων: " + str(dict(zip(X.columns, np.round(b[len(BASE):], 3)))), flush=True)
    Q["Ν2 δέντρα"] = boosted(o, D, w, y)

    mn = np.minimum(o.f1_n_prev, o.f2_n_prev).values
    deb, exp = te & (mn == 0), te & (mn > 0)
    print("\n=== Α. Μηχανή μόνη, log-loss 2017-26 (άνοιγμα / κλείσιμο στους ίδιους αγώνες) ===")
    print("  αγορά: " + " · ".join(f"{nm} {Ls(o.f1_p_open.values[m], w[m]).mean():.4f} / {Ls(o.f1_p_close.values[m], w[m]).mean():.4f}"
                                   for nm, m in (("όλοι", te), ("με πρωτοεμφ.", deb), ("χωρίς", exp))))
    rows = []
    for nm, q in Q.items():
        r = dict(φόρμουλα=nm)
        for tag, m in (("όλοι", te), ("πρωτοεμφ", deb), ("χωρίς", exp)):
            d = Ls(q[m], w[m]) - Ls(Q["βάση"][m], w[m])
            r[f"LL_{tag}"] = Ls(q[m], w[m]).mean()
            r[f"t_{tag}"] = tstat(d) if nm != "βάση" else np.nan
        rows.append(r)
    print(pd.DataFrame(rows).round(4).to_string(index=False))

    for k, p in (("open", o.f1_p_open.values), ("close", o.f1_p_close.values)):
        M = {nm: mix_wf(p, q, w, y) for nm, q in Q.items()}
        print(f"\n=== Β. Μίξη με αγορά, τιμή {k} (διαφ = log-loss έναντι βάσης, αρνητικό = καλύτερο) ===")
        rows = []
        for nm, q in M.items():
            r = dict(φόρμουλα=nm)
            d = Ls(q[te], w[te]) - Ls(M["βάση"][te], w[te])
            by = pd.Series(d).groupby(y[te]).mean()
            r.update(LL=Ls(q[te], w[te]).mean(), διαφ=d.mean(), t=tstat(d) if nm != "βάση" else np.nan, χρ_καλ=f"{(by < 0).sum()}/10")
            dd = Ls(q[deb], w[deb]) - Ls(M["βάση"][deb], w[deb])
            r.update(διαφ_πρωτ=dd.mean(), t_πρωτ=tstat(dd) if nm != "βάση" else np.nan)
            x = roi(q, o, k, te, w, .05)
            r.update(ROI5=x["ROI"], SE=x["SE"], n=x["n"], χρ=x["χρ"])
            x = roi(q, o, k, y >= 2022, w, .05)
            r.update(ROI5_22=x["ROI"], SE_22=x["SE"], n_22=x["n"], χρ_22=x["χρ"])
            x = roi(q, o, k, deb, w, .05)
            r.update(ROI5_πρωτ=x.get("ROI"), n_πρωτ=x.get("n"))
            rows.append(r)
        print(pd.DataFrame(rows).round(4).to_string(index=False))
        tr = (y >= 2012)
        print("βάρη μίξης 2012-26 (αγορά, μηχανή):")
        for nm, q in Q.items():
            bb, se = t3.fit(np.c_[lg(p), lg(np.clip(q, 1e-4, 1 - 1e-4))][tr], w[tr])
            print(f"  {nm}: {bb[0]:+.3f} (t {bb[0] / se[0]:+.1f}) · {bb[1]:+.3f} (t {bb[1] / se[1]:+.1f})")


if __name__ == "__main__":
    main()
