from pathlib import Path
import numpy as np
import pandas as pd
from evaluation import QUANTILES, save_preds, TZ
from regimes import regime_features, attach_regime
import lightgbm as lgb

def make_model(q):
    return lgb.LGBMRegressor(objective="quantile", alpha=q, n_estimators=300, learning_rate=0.05,
                                num_leaves=31, min_child_samples=50, subsample=0.8, subsample_freq=1,
                                colsample_bytree=0.8, random_state=0, verbose=-1)


X = pd.read_parquet("data/features/features_cz.parquet")
X["is_holiday"] = X["is_holiday"].astype(int)
PRICE_FULL = pd.read_parquet("data/clean/CZ_hourly_final.parquet")["price"]

GROUPS = {
    "calendar": ["hour", "weekday", "month", "is_holiday"],
    "lags":     ["price_lag_24", "price_lag_48", "price_lag_168", "de_price_lag_24",
                 "price_mean_7d", "price_std_7d", "price_mean_30d"],
    "cz_raw":   ["cz_load_fc", "cz_solar_fc"],
    "cz_resid": ["cz_residual_fc"],
    "de_raw":   ["de_load_fc", "de_wind_fc", "de_solar_fc"],
    "de_resid": ["de_residual_fc"],
}
SETS = {   # name -> feature groups
    "base_cz":        ["calendar", "lags", "cz_raw", "cz_resid"],
    "full":           ["calendar", "lags", "cz_raw", "cz_resid", "de_raw", "de_resid"],
    "full_no_resid":  ["calendar", "lags", "cz_raw", "de_raw"],
    "no_lags":        ["calendar", "cz_raw", "cz_resid", "de_raw", "de_resid"],
}
K_STATES = 3  


def blocks(index, test_start="2023-01-01"):
    start = pd.Timestamp(test_start, tz=TZ)
    end = index.max().tz_convert(TZ) + pd.Timedelta(hours=1)
    edges = [e for e in pd.date_range(start, end, freq="QS") if e < end] + [end]
    return list(zip(edges[:-1], edges[1:]))


def naive_bands(train, test):
    resid = train["price"] - train["price_lag_168"]
    return pd.DataFrame({q: test["price_lag_168"] + resid.quantile(q) for q in QUANTILES}, index=test.index)


def gbm_quantiles(train, test, cols):
    out = {}
    for q in QUANTILES:
        m = make_model(q)
        m.fit(train[cols], train["price"])
        out[q] = m.predict(test[cols])
    df = pd.DataFrame(out, index=test.index)
    return pd.DataFrame(np.sort(df.to_numpy(), axis=1), index=df.index, columns=QUANTILES)  # fix quantile crossing


def run(name, groups=None, use_regime=False):
    preds = []
    for start, end in blocks(X.index):
        train = X[X.index < start]
        test = X[(X.index >= start) & (X.index < end)]
        if len(test) == 0:
            continue
        assert train.index.max() < test.index.min(), "train/test overlap"
        print(f"{name}: block {start.date()} to {end.date()} (train {len(train)}, test {len(test)})", flush=True)

        if name == "naive_bands":
            preds.append(naive_bands(train, test))
            continue

        cols = [c for g in groups for c in GROUPS[g]]
        if use_regime:
            reg, _ = regime_features(PRICE_FULL, pd.Timestamp(start.date()), k=K_STATES)
            R = attach_regime(X, reg)
            train, test = train.join(R), test.join(R)
            assert not train[R.columns].isna().any().any() and not test[R.columns].isna().any().any()
            cols = cols + list(R.columns)
        preds.append(gbm_quantiles(train, test, cols))

    out = pd.concat(preds)
    save_preds(out, f"data/results/preds_{name}.parquet")
    return out


if __name__ == "__main__":
    Path("data/results").mkdir(parents=True, exist_ok=True)
    jobs = [("naive_bands", None, False)]
    jobs += [(n, g, False) for n, g in SETS.items()]
    jobs += [("full_regime", SETS["full"], True)]
    for name, groups, reg in jobs:
        if Path(f"data/results/preds_{name}.parquet").exists():
            print("skip", name)
            continue
        run(name, groups, reg)