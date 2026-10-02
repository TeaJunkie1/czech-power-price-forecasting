import pandas as pd
from evaluation import load_preds, pinball, TZ

X = pd.read_parquet("data/features/features_cz.parquet")
p = load_preds("data/results/preds_full.parquet")
y = X["price"].loc[p.index]
q = p.index.tz_convert(TZ).to_period("Q")

out = pd.DataFrame({
    "y_mean": y.groupby(q).mean(),
    "bias_median": (p[0.5] - y).groupby(q).mean(),
    "cov90": ((y >= p[0.05]) & (y <= p[0.95])).groupby(q).mean(),
    "width90": (p[0.95] - p[0.05]).groupby(q).mean(),
    "pinball": pinball(y, p).groupby(q).mean(),
})
print(out.round(2))