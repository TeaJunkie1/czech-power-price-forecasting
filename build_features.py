from pathlib import Path
import numpy as np
import pandas as pd
import holidays 

CLEAN, OUT = Path("data/clean"), Path("data/features")
OUT.mkdir(parents=True, exist_ok=True)

cz = pd.read_parquet(CLEAN / "CZ_hourly_with_fc.parquet")
de = pd.read_parquet(CLEAN / "DE_hourly_with_fc.parquet")

# fill short gaps in the DE forecasts (document in DECISIONS.md)
de_cols = ["load_fc", "wind_fc", "solar_fc", "residual_load_fc"]
de[de_cols] = de[de_cols].interpolate(method="time", limit=6)
assert de[de_cols].isna().sum().sum() == 0, "DE forecast gap longer than 6 hours, inspect manually"

X = pd.DataFrame(index=cz.index)
X["price"] = cz["price"]                                    # target

# CZ forecast covariates (no wind: Czech wind forecast is not published)
X["cz_load_fc"] = cz["load_fc"]
X["cz_solar_fc"] = cz["solar_fc"]
X["cz_residual_fc"] = cz["load_fc"] - cz["solar_fc"]

# DE forecast covariates
X["de_load_fc"] = de["load_fc"]
X["de_wind_fc"] = de["wind_fc"]
X["de_solar_fc"] = de["solar_fc"]
X["de_residual_fc"] = de["residual_load_fc"]

# price lags, all >= 24h so they are known when the forecast is made
for lag in (24, 48, 168):
    X[f"price_lag_{lag}"] = cz["price"].shift(lag)
X["de_price_lag_24"] = de["price"].shift(24)

# rolling stats, computed on the 24h-shifted series so no unknown prices leak in
known = cz["price"].shift(24)
X["price_mean_7d"] = known.rolling(24 * 7).mean()
X["price_std_7d"] = known.rolling(24 * 7).std()
X["price_mean_30d"] = known.rolling(24 * 30).mean()

# calendar features in local time
local = X.index.tz_convert("Europe/Prague")
cz_holidays = holidays.CZ(years=range(2021, 2027))
X["hour"] = local.hour
X["weekday"] = local.dayofweek
X["month"] = local.month
X["is_holiday"] = [d in cz_holidays for d in local.date]

X = X.dropna()          # drops the first 30 days (rolling window warm-up)
X.to_parquet(OUT / "features_cz.parquet")

print(X.shape, X.index.min(), "to", X.index.max())
print(X.isna().sum().sum(), "NaN left")
print(X.describe().T[["mean", "std", "min", "max"]].round(1))