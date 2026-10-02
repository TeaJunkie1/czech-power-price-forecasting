# Hypotheses and analysis plan

I'm writing this before I look at any result.

## What I'm trying to do
Forecast the hourly day-ahead electricity price in Czechia for day D, using only what's known on the
morning of D-1: prices up to D-1, calendar effects, and the published day-ahead forecasts for load and
solar (CZ) and load, wind and solar (DE).

## How I'll test it
- **Validation:** walk-forward with an expanding window and quarterly test blocks, from 2023-01-01 to
  2025-12-31. Each model only ever trains on the past. Hyperparameters are fixed up front and I won't
  tune them on the test blocks.
- **Forecasts:** 7 quantiles (5, 10, 25, 50, 75, 90, 95%). If the quantiles cross, I fix it by sorting.
- **Score:** pinball loss averaged over the 7 quantiles, then averaged per local day. I use daily
  averages because the 24 hours of one day are forecast together and their errors are correlated.
- **Comparing models:** Diebold-Mariano test on the daily losses, with HAC standard errors (7 lags),
  two-sided. As a cross-check I also compute a block-bootstrap interval for the mean difference
  (7-day blocks, 2000 resamples), because the DM test is only approximate when one model contains
  the other's features.
- **Multiple testing:** Holm correction across H2 to H6, alpha = 0.05. H1 is descriptive and sits outside
  that family.
- **Regime model (H5):** a 3-state HMM fitted on daily data (the mean and the intraday range of
  asinh(price/100)), with Gaussian emissions and 10 random restarts. States are sorted by mean to avoid
  label switching. It's fitted on training days only, uses filtering (never smoothing), and the regime
  probabilities are pushed one step ahead. K = 3 is fixed now and I won't pick it after the fact.

## When I'll call something supported
A hypothesis counts as **supported** only if all of these hold:
1. The named model has the lower loss.
2. The Holm-adjusted p-value is below 0.05.
3. The bootstrap interval excludes zero.
4. The loss is at least 1% lower. With about 1,100 test days, tiny improvements can look significant,
   so I want it to be big enough to matter.

It's **contradicted** if the result is significant in the opposite direction. Anything else is
**inconclusive**, and I'll report the effect size and interval either way.

## The hypotheses
- **H1:** CZ and DE prices are linked. The bootstrap CI of the correlation of daily changes excludes zero,
  and I report a cointegration test. Descriptive only.
- **H2:** German forecasts of load, wind and solar improve CZ forecasts (`full` beats `base_cz`).
  Note that `base_cz` still has the lagged German price, so this tests German fundamentals, not all
  German information.
- **H3:** Residual-load features help (`full` beats `full_no_resid`).
- **H4:** Recent prices matter (`full` beats `no_lags`).
- **H5:** Regime probabilities help (`full_regime` beats `full`).
- **H6:** The model beats the seasonal-naive baseline (`full` beats `naive_bands`).

## What I expect (written before seeing results)
- **H1:** Strongly linked: the CI of the daily-change correlation will be well above zero, and cointegration probably holds (~75%).
- **H2:** A modest gain of about 2-5% (~60% to clear the 1% bar), because the German price lag already carries a lot of the information.
- **H3:** Inconclusive (~75%), since the trees can rebuild residual load from load and solar.
- **H4:** Strongly supported (~95%), with a big effect, probably 15-30% worse without lags, mostly in 2023.
- **H5:** Little or no gain overall (~70% inconclusive), because the rolling price features already show the regime; if it helps, it'll be around the 2022-to-2023 transition.
- **H6:** Supported (~95%), beating the naive baseline by roughly 10-25%.

## Exploratory (I won't make adjusted claims about these)
Breakdowns by year and hour, trying 2 or 4 states, a rolling instead of expanding window, dropping the
German price lag, and anything else I think of after seeing results. If I add an analysis later, I'll
say so in the write-up.