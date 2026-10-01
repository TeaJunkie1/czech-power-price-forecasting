from pathlib import Path
import pandas as pd

RAW, OUT = Path("data/raw"), Path("data/clean")
OUT.mkdir(parents=True, exist_ok=True)

def read_kind(country, kind):
    files = sorted((RAW / country).glob(f"{kind}_[0-9]*.parquet"))
    assert files, f"no files for {country} {kind}"
    df = pd.concat([pd.read_parquet(f) for f in files])
    return df[~df.index.duplicated(keep="last")].sort_index()

def build(country):
    prices = read_kind(country, "prices").iloc[:, 0].resample("1h").mean().rename("price")

    load_df = read_kind(country, "load")
    actual_cols = [c for c in load_df.columns if "Actual" in c]
    load = load_df[actual_cols[0]].resample("1h").mean().rename("load")

    gen = read_kind(country, "gen")
    gen = gen[[c for c in gen.columns if "Aggregated" in c]]   # drop consumption columns
    gen_h = gen.resample("1h").mean()
    wind = gen_h[[c for c in gen_h.columns if c.startswith("Wind")]].sum(axis=1, min_count=1).rename("wind")
    solar = gen_h[[c for c in gen_h.columns if c.startswith("Solar")]].sum(axis=1, min_count=1).rename("solar")

    df = pd.concat([prices, load, wind, solar], axis=1)
    df["residual_load"] = df["load"] - df["wind"].fillna(0) - df["solar"].fillna(0)
    df.index.name = "timestamp_utc"
    return df

for country in ["CZ", "DE"]:
    df = build(country)
    df.to_parquet(OUT / f"{country}_hourly.parquet")
    print(f"\n{country}: {df.shape}, {df.index.min()} to {df.index.max()}")
    print("missing share:\n", df.isna().mean().round(3))
    print("negative prices:", (df["price"] < 0).sum())