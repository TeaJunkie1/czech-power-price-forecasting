from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd




from pathlib import Path
import pandas as pd

OUT = Path("data/clean")

for country in ["CZ", "DE"]:
    df = pd.read_parquet(OUT / f"{country}_hourly.parquet")
    df = df.iloc[:-1]                                   # drop the boundary hour
    n_missing = df["price"].isna().sum()

    df["price"] = df["price"].interpolate(method="time", limit=3)   # fill short gaps only
    assert df["price"].isna().sum() == 0, "gap longer than 3 hours"

    df.to_parquet(OUT / f"{country}_hourly_final.parquet")
    print(f"{country}: filled {n_missing} prices, {len(df)} rows, "
          f"{df.index.min()} to {df.index.max()}")


for kind in ["load_fc", "windsolar_fc"]:
    f = pd.read_parquet(f"data/raw/CZ/{kind}_2023.parquet")
    print(kind, f.shape, f.columns.tolist())
    print(f.index.to_series().diff().value_counts().head(3))

import pandas as pd
df = pd.read_parquet("data/clean/CZ_hourly_with_fc.parquet")
print(df[["load", "load_fc"]].dtypes)
print(df[["load", "load_fc"]].describe())
print(df[["load", "load_fc"]].head())
print(df[["load", "load_fc"]].isna().sum())
print(pd.read_parquet("data/clean/CZ_hourly.parquet")["load"].isna().mean())
for c in ["CZ", "DE"]:
    df = pd.read_parquet(f"data/clean/{c}_hourly_with_fc.parquet")
    print(c, df[["load", "load_fc"]].isna().sum().to_dict(),
          " MAE load_fc:", round((df["load_fc"] - df["load"]).abs().mean(), 1), "MW",
          "solar mean:", round(df["solar"].mean(), 1))
import pandas as pd
for name in ["hourly", "hourly_final", "hourly_with_fc"]:
    df = pd.read_parquet(f"data/clean/CZ_{name}.parquet")
    print(name, "load NaN share:", round(df["load"].isna().mean(), 5))

Path("figures").mkdir(exist_ok=True)
df = pd.read_parquet("data/clean/CZ_hourly_final.parquet")
local = df.tz_convert("Europe/Prague")

fig, ax = plt.subplots(2, 2, figsize=(14, 9))

ax[0, 0].plot(local.index, local["price"], lw=0.4)
ax[0, 0].set_title("Day-ahead price (EUR/MWh)")

local["price"].clip(-50, 500).hist(bins=200, ax=ax[0, 1])
ax[0, 1].set_title("Price distribution (clipped to -50..500)")

(local.groupby([local.index.month, local.index.hour])["price"].mean()
      .unstack(0).plot(ax=ax[1, 0]))
ax[1, 0].set_title("Mean price by hour of day, one line per month")
ax[1, 0].set_xlabel("hour (local time)")
ax[1, 0].legend(title="month", ncol=3, fontsize=7)

s = local.sample(6000, random_state=0)
ax[1, 1].scatter(s["residual_load"], s["price"], s=3, alpha=0.4)
ax[1, 1].set_ylim(-100, 600)
ax[1, 1].set_title("Price vs residual load")
ax[1, 1].set_xlabel("residual load (MW)")

plt.tight_layout()
plt.savefig("figures/eda_cz.png", dpi=150)
plt.show()
