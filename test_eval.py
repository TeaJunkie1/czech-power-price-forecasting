import numpy as np, pandas as pd
from scipy import stats
from evaluation import *

rng = np.random.default_rng(0)
idx = pd.date_range("2023-01-01", periods=24 * 600, freq="h", tz="UTC")
y = pd.Series(rng.normal(0, 1, len(idx)), index=idx)

true_q = pd.DataFrame({q: stats.norm.ppf(q) for q in QUANTILES}, index=idx)
perfect = pd.DataFrame({q: y for q in QUANTILES})
print("perfect forecast pinball (expect 0):", pinball(y, perfect).mean())

print("coverage of true quantiles (expect approx. 0.90):", round(central_coverage(y, true_q), 3))
print("calibration of true quantiles (large p-values):", calibration_report(y, true_q))

too_narrow = true_q * 0.5
print("overconfident bands ( Kupiec p approx. 0):", calibration_report(y, too_narrow))

worse = true_q + 0.3
r = dm_test(pinball(y, true_q), pinball(y, worse))
print("true vs shifted (expect mean_diff < 0, tiny p):", {k: round(v, 5) for k, v in r.items()})

up, down = true_q + 0.3, true_q - 0.3          # equally bad by symmetry
r = dm_test(pinball(y, up), pinball(y, down))
print("equally bad forecasts (large p):", {k: round(v, 4) for k, v in r.items()})