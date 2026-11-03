"""UFC: μεταβλητές μαχητή ΠΡΙΝ από κάθε αγώνα (μόνο προηγούμενοι αγώνες UFC).

Έξοδος UFC_DATA/ufc_features.csv: μία γραμμή ανά αγώνα, στήλες f1_*/f2_*:
  n_prev          αγώνες UFC πριν
  layoff_d        μέρες από τον προηγούμενο αγώνα
  slpm / sapm     καθαρά χτυπήματα που ρίχνει / δέχεται ανά λεπτό (συρρίκνωση 15′ προς μέσο όρο)
  sdiff           slpm − sapm
  sdiff_adj       ίδιο, διορθωμένο για αντιπάλους (πόσο παραπάνω από ό,τι συνήθως επιτρέπει/ρίχνει ο αντίπαλος)
  td15 / tdd      takedowns ανά 15′ / άμυνα takedown (ποσοστό αποκρούσεων)
  ctrl_share      μερίδιο χρόνου ελέγχου
  kd_abs15        νοκ-ντάουν που δέχεται ανά 15′
  ko_losses       ήττες με KO/TKO στην καριέρα UFC
  last_ko_loss    ο προηγούμενος αγώνας ήταν ήττα με KO
  last_robbed     ο προηγούμενος ήταν ήττα με διχασμένη/πλειοψηφίας απόφαση ενώ είχε περισσότερα καθαρά χτυπήματα
  last_lucky      νίκη με διχασμένη/πλειοψηφίας απόφαση ενώ είχε λιγότερα
  streak          σερί (+ νίκες / − ήττες)
  fade            χτυπήματα 3ου γύρου / μέσος 1ου-2ου (αγώνες που έφτασαν στον 3ο)
  wc_move         αλλαγή κατηγορίας από τον προηγούμενο αγώνα (λίβρες, + = ανεβαίνει)
  reach / height / southpaw
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(os.environ.get("UFC_DATA", Path(__file__).parent / "data"))
LBS = {"Strawweight": 115, "Flyweight": 125, "Bantamweight": 135, "Featherweight": 145, "Lightweight": 155,
       "Welterweight": 170, "Middleweight": 185, "Light Heavyweight": 205, "Heavyweight": 265}
T0 = 900.0  # συρρίκνωση: 15 λεπτά «μέσου» μαχητή


def wc_lbs(s):
    s = str(s)
    for k in sorted(LBS, key=len, reverse=True):
        if k in s:
            return LBS[k]
    return np.nan


def fade_table():
    s = pd.read_csv(DATA / "raw" / "ufc_fight_stats.csv").dropna(subset=["FIGHTER"])
    s["sig"] = s["SIG.STR."].str.extract(r"^(\d+)").astype(float)
    s["r"] = s.ROUND.str.extract(r"(\d+)").astype(float)
    p = s.pivot_table(index=["EVENT", "BOUT", "FIGHTER"], columns="r", values="sig", aggfunc="sum")
    p = p[p.get(3).notna()] if 3 in p.columns else p.iloc[0:0]
    f = (p[3] / ((p[1] + p[2]) / 2).replace(0, np.nan)).rename("fade").reset_index()
    for c in ("EVENT", "BOUT", "FIGHTER"):
        f[c] = f[c].str.strip()
    return f


def main():
    F = pd.read_csv(DATA / "ufc_fights.csv")
    F["d"] = pd.to_datetime(F.date)
    F["lbs"] = F.weightclass.map(wc_lbs)
    F["split"] = F.method.str.contains("Split|Majority", na=False)
    F["bout"] = F.f1 + " vs. " + F.f2
    fd = fade_table()

    # μακρύ φορμάτ: μία γραμμή ανά μαχητή-αγώνα
    rows = []
    for me, op in (("f1", "f2"), ("f2", "f1")):
        x = pd.DataFrame({
            "fid": F.index, "d": F.d, "event": F.event, "bout": F.bout, "fighter": F[me], "opp": F[op],
            "res": F.f1_result.map({"W": "W", "L": "L", "D": "D"}) if me == "f1" else F.f1_result.map({"W": "L", "L": "W", "D": "D"}),
            "method": F.method_grp, "split": F.split, "t": F.fight_time_s, "lbs": F.lbs,
            "sig": F[f"{me}_sig"], "sig_ab": F[f"{op}_sig"], "td": F[f"{me}_td"], "td_att_ab": F[f"{op}_td_att"],
            "td_ab": F[f"{op}_td"], "ctrl": F[f"{me}_ctrl_s"], "ctrl_ab": F[f"{op}_ctrl_s"], "kd_ab": F[f"{op}_kd"],
        })
        rows.append(x)
    L = pd.concat(rows, ignore_index=True)
    L = L.merge(fd.rename(columns={"EVENT": "event", "BOUT": "bout", "FIGHTER": "fighter"}),
                on=["event", "bout", "fighter"], how="left")
    L = L.sort_values(["d", "fid"], kind="stable").reset_index(drop=True)
    ok = L.sig.notna() & L.t.notna() & (L.t > 0)
    for c in ("sig", "sig_ab", "td", "td_att_ab", "td_ab", "ctrl", "ctrl_ab", "kd_ab", "t"):
        L[c + "_v"] = L[c].where(ok, 0.0).fillna(0.0)
    tot_t = L.t_v.sum()
    mu_sl = L.sig_v.sum() / tot_t  # ανά δευτερόλεπτο, μέσος όρος

    g = L.groupby("fighter", sort=False)
    prev = lambda c: g[c].cumsum() - L[c]  # άθροισμα ΠΡΙΝ από τον αγώνα
    L["n_prev"] = g.cumcount()
    L["layoff_d"] = (L.d - g.d.shift()).dt.days
    T = prev("t_v")
    L["slpm"] = 60 * (prev("sig_v") + mu_sl * T0) / (T + T0)
    L["sapm"] = 60 * (prev("sig_ab_v") + mu_sl * T0) / (T + T0)
    L["sdiff"] = L.slpm - L.sapm
    L["td15"] = 900 * (prev("td_v") + (L.td_v.sum() / tot_t) * T0) / (T + T0)
    mu_tdd = 1 - L.td_ab_v.sum() / L.td_att_ab_v.sum()
    L["tdd"] = 1 - (prev("td_ab_v") + (1 - mu_tdd) * 5) / (prev("td_att_ab_v") + 5)
    L["ctrl_share"] = (prev("ctrl_v") + 0.15 * T0) / (prev("ctrl_v") + prev("ctrl_ab_v") + T0 * 0.3 + 1e-9)
    L["kd_abs15"] = 900 * (prev("kd_ab_v") + (L.kd_ab_v.sum() / tot_t) * T0) / (T + T0)
    L["ko_loss"] = ((L.res == "L") & (L.method == "KO")).astype(int)
    L["ko_losses"] = prev("ko_loss")
    L["last_ko_loss"] = g.ko_loss.shift().fillna(0)
    rob = (L.res == "L") & L.split & (L.sig > L.sig_ab)
    luck = (L.res == "W") & L.split & (L.sig < L.sig_ab)
    L["last_robbed"] = rob.groupby(L.fighter).shift().fillna(False).astype(int)
    L["last_lucky"] = luck.groupby(L.fighter).shift().fillna(False).astype(int)
    # σερί πριν τον αγώνα
    st, cur = [], {}
    for f, r in zip(L.fighter, L.res):
        s = cur.get(f, 0)
        st.append(s)
        cur[f] = (s + 1 if s > 0 else 1) if r == "W" else (s - 1 if s < 0 else -1) if r == "L" else 0
    L["streak"] = st
    fv = L.fade.copy()
    L["fade_n"] = fv.notna().groupby(L.fighter).cumsum() - fv.notna()
    L["fade_s"] = fv.fillna(0).groupby(L.fighter).cumsum() - fv.fillna(0)
    mu_f = fv.median()
    L["fade"] = (L.fade_s + mu_f * 2) / (L.fade_n + 2)
    L["wc_move"] = L.lbs - g.lbs.shift()

    # διόρθωση αντιπάλου: σε κάθε αγώνα, ό,τι έριξα/δέχτηκα vs ό,τι συνήθως δέχεται/ρίχνει ο αντίπαλος (πριν)
    key = L.set_index(["fid", "fighter"])
    opp_sapm = key.loc[list(zip(L.fid, L.opp)), "sapm"].values
    opp_slpm = key.loc[list(zip(L.fid, L.opp)), "slpm"].values
    exc_land = np.where(ok, 60 * L.sig / L.t - opp_sapm, 0.0)
    exc_abs = np.where(ok, 60 * L.sig_ab / L.t - opp_slpm, 0.0)
    wt = np.where(ok, L.t, 0.0)
    L["_el"], L["_ea"], L["_w"] = exc_land * wt, exc_abs * wt, wt
    L["sdiff_adj"] = ((prev("_el") - prev("_ea")) / (prev("_w") + T0))

    fi = pd.read_csv(DATA / "ufc_fighters.csv")
    fi = fi[~fi.dup_name].set_index("fighter")
    L["reach"] = L.fighter.map(fi.reach_cm)
    L["height"] = L.fighter.map(fi.height_cm)
    L["southpaw"] = (L.fighter.map(fi.stance) == "Southpaw").astype(int)

    feats = ["n_prev", "layoff_d", "slpm", "sapm", "sdiff", "sdiff_adj", "td15", "tdd", "ctrl_share", "kd_abs15",
             "ko_losses", "last_ko_loss", "last_robbed", "last_lucky", "streak", "fade", "fade_n", "wc_move",
             "reach", "height", "southpaw"]
    out = F[["fight_url", "date", "event", "f1", "f2"]].copy()
    for me in ("f1", "f2"):
        sub = L.merge(F[[me]].rename(columns={me: "fighter"}).reset_index().rename(columns={"index": "fid"}),
                      on=["fid", "fighter"])
        sub = sub.drop_duplicates("fid").set_index("fid")[feats]
        out = out.join(sub.add_prefix(me + "_"))
    out.to_csv(DATA / "ufc_features.csv", index=False)
    print(f"ufc_features.csv: {len(out)} αγώνες · stats-λίγκας: {60 * mu_sl:.2f} καθαρά/λεπτό, άμυνα TD {mu_tdd:.2f}")


if __name__ == "__main__":
    main()
