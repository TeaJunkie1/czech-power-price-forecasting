import os, pandas as pd
from dotenv import load_dotenv
from entsoe import EntsoePandasClient
import time
from pathlib import Path

load_dotenv()
years = range(2022, 2026)
countries = {"CZ": "CZ", "DE": "DE_LU"}

client = EntsoePandasClient(api_key=os.environ["ENTSOE_API_KEY"])

raw = Path("data/raw")

def try_fetch(fn,*args,retries=3,**kwargs):
    for att in range(retries):
        try:
            return fn(*args,**kwargs)
        except Exception as e:
            print(f'Attempt {att} failed on {e}')
            time.sleep(5 * (att+1))

def to_frame(data,name):
    if data is None:
        return None
    if isinstance(data ,pd.Series):
        data=data.to_frame(name)
    if isinstance(data.columns,pd.MultiIndex):
        data.columns = ["__".join(map(str,c)) for c in data.columns]
    data.columns = [str(c) for c in data.columns]
    data.index = data.index.tz_convert("UTC")
    return data

fetchers = {
    "prices" : lambda zone,start,end : client.query_day_ahead_prices(zone,start=start,end=end),
    "load" : lambda zone,start,end : client.query_load(zone,start=start,end=end),
    "gen" : lambda zone,start,end : client.query_generation(zone,start=start,end=end),
    "load_fc": lambda zone, s, e: client.query_load_forecast(zone, start=s, end=e),
    "windsolar_fc": lambda zone, s, e: client.query_wind_and_solar_forecast(zone, start=s, end=e, psr_type=None),

}

for country,zone in countries.items():
    out_dir = raw / country
    os.mkdir(out_dir)

    for year in years:
        start = pd.Timestamp(f'{year}-01-01', tz="Europe/Prague")
        end = pd.Timestamp(f'{year + 1}-01-01', tz="Europe/Prague")
    
        for kind, query in fetchers.items():
                path = out_dir / f"{kind}_{year}.parquet"
                if path.exists():
                    print(f"skip   {path}")
                    continue

                print(f"fetch  {country} {kind} {year}")
                data = to_frame(try_fetch(query, zone, start, end), kind)
                if data is None or data.empty:
                    print(f"   no data for {country} {kind} {year}")
                    continue
                data.to_parquet(path)
