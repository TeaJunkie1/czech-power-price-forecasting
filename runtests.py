import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss, coint
from evaluation import *
import warnings

warnings.filterwarnings('ignore')
pd.set_option("display.width", 200)

#  H1: are CZ and DE prices linked 
cz = pd.read_parquet("data/clean/CZ_hourly_final.parquet")["price"]
de = pd.read_parquet("data/clean/DE_hourly_final.parquet")["price"]
h = pd.DataFrame({"cz": cz, "de": de})
h["yr"] = h.index.tz_convert(TZ).year
rows = []
for yr, g in h.groupby("yr"):
    rows.append({"year": yr, "corr_level": g.cz.corr(g.de), "share_equal_price": ((g.cz - g.de).abs() < 0.01).mean()})
print("H1 hourly price relationship by year\n", pd.DataFrame(rows).set_index("year").round(3))

dm_ = h[["cz", "de"]].groupby(h.index.tz_convert(TZ).date).mean()
dd = dm_.diff().dropna()
lo, hi = block_bootstrap_corr_ci(dd["cz"], dd["de"])
print(f"H1 correlation of DAILY CHANGES: {dd['cz'].corr(dd['de']):.3f}  block-bootstrap 95% CI [{lo:.3f}, {hi:.3f}]")
print(f"ADF p (CZ daily mean, H0 = unit root): {adfuller(dm_['cz'])[1]:.4f}")
print(f"KPSS p (CZ daily mean, H0 = stationary): {kpss(dm_['cz'], regression='c', nlags='auto')[1]:.4f}")
print(f"Engle-Granger cointegration p (CZ vs DE daily means): {coint(dm_['cz'], dm_['de'])[1]:.4f}")

#load forecasts
X = pd.read_parquet("data/features/features_cz.parquet")
names = ["naive_bands", "base_cz", "full", "full_no_resid", "no_lags", "full_regime"]
P = {n: load_preds(f"data/results/preds_{n}.parquet") for n in names}
common = P["full"].index
for n in names:
    common = common.intersection(P[n].index)
y = X["price"].loc[common]
P = {n: p.loc[common] for n, p in P.items()}
L = {n: pinball(y, P[n]) for n in names}
yr_idx = common.tz_convert(TZ).year

#  scores and calibration 
rows = []
for n in names:
    for label, mask in [("all", np.ones(len(common), bool))] + [(str(v), yr_idx == v) for v in sorted(set(yr_idx))]:
        rows.append({"model": n, "period": label, "pinball": L[n][mask].mean(),
                     "cov90": central_coverage(y[mask], P[n][mask]),
                     "cov50": central_coverage(y[mask], P[n][mask], 0.25, 0.75),
                     "width90": interval_width(P[n][mask])})
summary = pd.DataFrame(rows)
print("SCORES", summary.pivot(index="model", columns="period", values="pinball").round(2))
print("90% COVERAGE", summary.pivot(index="model", columns="period", values="cov90").round(3))
print("90% WIDTH", summary.pivot(index="model", columns="period", values="width90").round(1))

print("CALIBRATION TESTS (90% interval)")
print(pd.DataFrame({n: calibration_report(y, P[n]) for n in names}).T.round(4))

print("RELIABILITY (observed share below each quantile; target = the quantile level)")
print(pd.DataFrame({n: reliability(y, P[n]) for n in ["naive_bands", "full", "full_regime"]}).round(3))

# confirmatory hypotheses H2-H6 
HYP = [("H2 German forecasts help", "full", "base_cz"),
       ("H3 Residual load helps",   "full", "full_no_resid"),
       ("H4 Recent prices matter",  "full", "no_lags"),
       ("H5 Regimes help",          "full_regime", "full"),
       ("H6 Beats naive baseline",  "full", "naive_bands")]
res = []
for label, a, b in HYP:
    r = dm_test(L[a], L[b])
    d = (daily(L[a]) - daily(L[b])).dropna()
    r["boot_lo"], r["boot_hi"] = block_bootstrap_mean_ci(d)
    r.update({"hypothesis": label, "A": a, "B": b})
    res.append(r)
res = pd.DataFrame(res).set_index("hypothesis")
res["p_holm"] = holm(res["p"].to_numpy())
res["supported"] = ((res["mean_diff"] < 0) & (res["p_holm"] < 0.05)
                    & (res["boot_hi"] < 0) & (res["rel_change"] <= -0.01))
res["contradicted"] = (res["mean_diff"] > 0) & (res["p_holm"] < 0.05)
print("CONFIRMATORY (negative mean_diff = A better; Holm-adjusted over 5 tests)")
print(res[["A", "B", "mean_diff", "rel_change", "ci_lo", "ci_hi", "boot_lo", "boot_hi", "p", "p_holm", "supported"]].round(4))

print("BY YEAR (exploratory, unadjusted p-values)")
rows = []
for label, a, b in HYP:
    for v in sorted(set(yr_idx)):
        m = yr_idx == v
        r = dm_test(L[a][m], L[b][m])
        rows.append({"hypothesis": label, "year": v, "rel_change": r["rel_change"], "p": r["p"]})
print(pd.DataFrame(rows).pivot(index="hypothesis", columns="year", values=["rel_change", "p"]).round(3))