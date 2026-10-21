# -*- coding: utf-8 -*-
"""t49_news_on_model.py — ΕΙΔΗΣΗ ΠΑΝΩ ΣΤΟ ΜΟΝΤΕΛΟ (21/10/2026, Στελιος «πες οτι το μοντελο εχει 0% και με την απουσια παει 5%, παιζουμε;»).
Ιδιες ειδησεις με t48 (NBC 2025-26, νεες, παικτες ρολου, ματς ≤36ω) — ΧΩΡΙΣ φιλτρο αξιας (αποφασιζει το μοντελο).
ΜΟΝΤΕΛΟ στο τ = t0+k (k = 1 / 8 / 15′): live αντιγραφο (t22: VNO) − απουσιες απο την επισημη αναφορα ως το τ (μονο Out, οπως το live)
  + η ΕΙΔΗΣΗ: «εκτος» → ο παικτης μετρα Out · «παιζει» → αν ηταν Out στην αναφορα, βγαινει.
  «Πριν» = ιδιο μοντελο ΧΩΡΙΣ την ειδηση, στην ιδια τιμη.
  Συνολα: μ = μηχανη + Φ3 live − 0.5·LO + 1.0·LD (t35), σ 18.
PICK = πλευρα της ειδησης αν edge(μετα) ≥ κατωφλι ∈ {0, 2, 4, 5, 8}% στην τιμη Crown του τ.
ΣΥΓΚΡΙΣΗ: (α) «ειδηση μονη» (t48, αξια ≥1 π.) · (β) ομαδες: pick που ΓΕΝΝΗΘΗΚΕ απο την ειδηση (πριν < κατωφλι) vs ΥΠΗΡΧΕ ηδη (πριν ≥ κατωφλι).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (γραφτηκε πριν το τρεξιμο): «το μοντελο ξεχωριζει» αν σε k=1 ΚΑΙ k=8 το καλυτερο κατωφλι εχει ROI ≥ «ειδηση μονη» + 3pp
  με n ≥ 80 και θετικο ROI και στα 2 μισα της σεζον. Περιγραφικα: γεννημενα-απο-ειδηση picks με edge ≥8% (αυτα που κοβει ο κανονας πρωτης γραμμης).
Εξοδος: t49_news_on_model_out.txt"""
import os, sys, io, contextlib
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't48_news_prices.py'), encoding='utf-8').read().split("KS = (-60")[0]
g = {'__file__': os.path.join(SC, 't48_news_prices.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
for k_ in ('np', 'pd', 'D', 'G', 'dD', 'S', 'ACT', 'TOT', 'VNO', 'abs_cost', 'W_A', 'cover_', 'SIG_', 'at_h', 'at_t', 'status_at', 'K2P', 'mins', 'value', 'odval', 'nkey', 'nt'):
    globals()[k_] = g[k_]
TT = np.asarray(nt['TT'], float); LEV = np.nan_to_num(np.asarray(nt['Llive'], float))
from statistics import NormalDist
N_ = NormalDist()
def cov_t(mu, T, s=18.0):
    if abs(T - round(T)) < 1e-9:
        po = N_.cdf((mu - T - 0.5) / s); pu = N_.cdf((T - mu - 0.5) / s); return po, 1 - po - pu, pu
    po = N_.cdf((mu - T) / s); return po, 0.0, 1 - po
def tot_loss(t, d, tau, skip=None, force=None):
    """LO, LD (επιθεση/αμυνα που λειπει) απο την αναφορα ως το τ (μονο Out) · skip = key που βγαινει · force = (key, pid, m) που μπαινει Out."""
    lo = ld = 0.0
    for k, stt in status_at(t, d, tau).items():
        if stt != 'Out' or k == skip: continue
        pid = K2P.get((k, t, S))
        if pid is None: continue
        m = mins(pid, t, S, d)
        if m is None or m < 20: continue
        o_, d_ = odval(pid, S - 1); lo += (o_ + 0.5) * m / 48; ld += (d_ + 0.5) * m / 48
    if force:
        pid, m = force; o_, d_ = odval(pid, S - 1); lo += (o_ + 0.5) * m / 48; ld += (d_ + 0.5) * m / 48
    return lo, ld
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
THR = (0, .02, .04, .05, .08)
REC = {'h': [], 't': []}
for r in D.itertuples(index=False):
    i = r.i; h_, a_, d = G.home.values[i], G.away.values[i], dD[i]
    if not np.isfinite(VNO[i]): continue
    k_pl = nkey(r.player); pid = K2P.get((k_pl, r.team, S)); m_pl = mins(pid, r.team, S, d)
    news_home_side = (not r.home) if r.kind == 'out' else r.home          # πλευρα που ευνοει η ειδηση
    for k in (1, 8, 15):
        tau = r.t0 + k * 60
        if tau >= r.tip: continue
        # ---- χαντικαπ ----
        x = at_h(i, tau)
        if x is not None:
            ch, _ = abs_cost(h_, d, S, tau, W_A); ca, _ = abs_cost(a_, d, S, tau, W_A)
            mu0 = VNO[i] - ch + ca
            st_tau = status_at(r.team, d, tau).get(k_pl)
            pc = 0.75 * (value(pid, S - 1) + 2.0) * m_pl / 48
            if r.kind == 'out' and st_tau != 'Out': adj = -pc if r.home else pc
            elif r.kind == 'in' and st_tau == 'Out': adj = pc if r.home else -pc
            else: adj = 0.0
            mu1 = mu0 + adj
            def edge(mu):
                pw, pp, pl = cover_(mu, x['L'], SIG_)
                return (pw * x['oh'] + pp - 1) if news_home_side else (pl * x['oa'] + pp - 1)
            L_, od = (x['L'], x['oh']) if news_home_side else (-x['L'], x['oa'])
            res_ = (ACT[i] + x['L']) * (1 if news_home_side else -1)
            REC['h'].append(dict(k=k, mon=r.mon, kind=r.kind, val=abs(r.hc), e0=edge(mu0), e1=edge(mu1), adj=abs(adj),
                                 res=(od - 1) if res_ > 0 else (0.0 if res_ == 0 else -1.0)))
        # ---- συνολα ----
        y = at_t(i, tau)
        if y is not None and np.isfinite(TT[i]):
            st_tau = status_at(r.team, d, tau).get(k_pl)
            loh, ldh = tot_loss(h_, d, tau); loa, lda = tot_loss(a_, d, tau)
            mu0 = TT[i] + LEV[i] - 0.5 * (loh + loa) + 1.0 * (ldh + lda)
            o_, dd_ = odval(pid, S - 1); xo, xd = (o_ + 0.5) * m_pl / 48, (dd_ + 0.5) * m_pl / 48
            if r.kind == 'out' and st_tau != 'Out': adj = -0.5 * xo + 1.0 * xd
            elif r.kind == 'in' and st_tau == 'Out': adj = 0.5 * xo - 1.0 * xd
            else: adj = 0.0
            mu1 = mu0 + adj
            over = (r.tt > 0)                                                  # πλευρα της ειδησης (t48: + = περισσοτεροι ποντοι)
            def edge_t(mu):
                po, pq, pu = cov_t(mu, y['T']); return (po * y['oo'] + pq - 1) if over else (pu * y['ou'] + pq - 1)
            od = y['oo'] if over else y['ou']; res_ = (TOT[i] - y['T']) * (1 if over else -1)
            REC['t'].append(dict(k=k, mon=r.mon, kind=r.kind, val=abs(r.tt), e0=edge_t(mu0), e1=edge_t(mu1), adj=abs(adj),
                                 res=(od - 1) if res_ > 0 else (0.0 if res_ == 0 else -1.0)))
def cell(x):
    if not len(x): return '        —'
    h1, h2 = x[x.mon.isin((10, 11, 12, 1))], x[x.mon.isin((2, 3, 4))]
    return f'{100 * x.res.mean():+6.1f}% ({len(x):4d}, {x.res.sum():+6.1f}μ) · Οκτ-Ιαν {100 * h1.res.mean():+.1f}% / Φεβ-Απρ {100 * h2.res.mean():+.1f}%'
for mk, nm in (('h', 'ΧΑΝΤΙΚΑΠ'), ('t', 'ΣΥΝΟΛΑ')):
    E = pd.DataFrame(REC[mk]); P(''); P(f'################ {nm} · ειδησεις {E[E.k == 1].shape[0]} ################')
    for k in (1, 8, 15):
        x = E[E.k == k]; base = x[x.val >= 1.0]
        P(f'  === +{k}′ ===  «ειδηση μονη» (αξια ≥1 π.) {cell(base)}')
        best = None
        for th in THR:
            p = x[x.e1 >= th]; born = p[p.e0 < th]; had = p[p.e0 >= th]
            P(f'    μοντελο+ειδηση ≥{100 * th:.0f}%: {cell(p)} | ΓΕΝΝΗΘΗΚΕ απο την ειδηση {cell(born)} | ΥΠΗΡΧΕ ηδη {cell(had)}')
            if len(p) >= 80 and (best is None or p.res.mean() > best[1]): best = (th, p.res.mean(), p)
        if best:
            th, roi, p = best; h1, h2 = p[p.mon.isin((10, 11, 12, 1))], p[p.mon.isin((2, 3, 4))]
            ok = roi >= base.res.mean() + .03 and roi > 0 and h1.res.mean() > 0 and h2.res.mean() > 0
            P(f'    καλυτερο κατωφλι (n≥80): {100 * th:.0f}% → {100 * roi:+.1f}% vs «ειδηση μονη» {100 * base.res.mean():+.1f}% → {"ξεχωριζει ✓" if ok else "ΔΕΝ ξεχωριζει"}')
        b8 = x[(x.e1 >= .08) & (x.e0 < .08)]
        P(f'    picks που ΚΟΒΕΙ σημερα ο κανονας πρωτης γραμμης (πριν <8%, μετα ≥8%): {cell(b8)}')
        neg = x[(x.e1 < 0) & (x.val >= 1)]
        P(f'    ειδησεις αξιας ≥1 π. οπου το μοντελο ΔΕΝ θελει την πλευρα της ειδησης (μετα <0%): {cell(neg)}')
open(os.path.join(SC, 't49_news_on_model_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
