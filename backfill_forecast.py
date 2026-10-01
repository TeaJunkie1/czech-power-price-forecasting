from pathlib import Path
import pandas as pd

RAW, OUT = Path("data/raw"), Path("data/clean")


def read_kind(country, kind):
       files = sorted((RAW / country).glob(f"{kind}_[0-9]*.parquet"))
       assert files, f"no files for {country} {kind}"
       df = pd.concat([pd.read_parquet(f) for f in files])
       return df[~df.index.duplicated(keep="last")].sort_index()


def build_fc(country):
    load_fc = read_kind(country, "load_fc").iloc[:, 0].resample("1h").mean().rename("load_fc")

    ws = read_kind(country, "windsolar_fc").resample("1h").mean()
    solar_fc = ws[[c for c in ws.columns if c.startswith("Solar")]].sum(axis=1, min_count=1).rename("solar_fc")
    wind_cols = [c for c in ws.columns if c.startswith("Wind")]
    if wind_cols:
        wind_fc = ws[wind_cols].sum(axis=1, min_count=1).rename("wind_fc")
    else:
        wind_fc = pd.Series(0.0, index=ws.index, name="wind_fc")   # CZ: no wind forecast published

    fc = pd.concat([load_fc, wind_fc, solar_fc], axis=1)
    fc["residual_load_fc"] = fc["load_fc"] - fc["wind_fc"].fillna(0) - fc["solar_fc"].fillna(0)
    return fc


for country in ["CZ", "DE"]:
    final = pd.read_parquet(OUT / f"{country}_hourly_final.parquet")
    fc = build_fc(country)
    df = final.join(fc, how="left")
    df.to_parquet(OUT / f"{country}_hourly_with_fc.parquet")

    print(f"\n{country}: {df.shape}")
    print("missing share:\n", df[["load_fc", "wind_fc", "solar_fc"]].isna().mean().round(4))
    print("rows per local year:\n", df.tz_convert("Europe/Prague").groupby(lambda t: t.year).size())
    # sanity check: how close are the forecasts to the actuals?
    load_mae = (df["load_fc"] - df["load"]).abs().mean()
    solar_mae = (df["solar_fc"] - df["solar"]).abs().mean()

    print(f"MAE load_fc vs load: {load_mae:.1f} MW")
    print(f"MAE solar_fc vs solar: {solar_mae:.1f} MW")