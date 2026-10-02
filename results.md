# Results

Round 1 results for the pre-registered analysis plan in [`HYPOTHESES.md`](HYPOTHESES.md).
All numbers come from `results/run_tests_output.txt`. Test period: 2023-01-01 to 2025-12-31,
12 quarterly walk-forward blocks, about 1,095 test days.

Score everywhere is **pinball loss averaged over 7 quantiles** (lower is better).
"Daily" tests use daily means of that loss.

## Summary

- **Supported:** H4 (recent prices matter) and H6 (the model beats the seasonal-naive baseline).
- **Inconclusive:** H2 (German forecasts), H3 (residual load) and H5 (regime probabilities).
  The point estimates for H2 and H5 favour the richer model, but the intervals include zero
  and neither clears the 1% effect-size bar after Holm correction.
- **Main problem found:** the LightGBM quantile bands are badly miscalibrated. The nominal 90%
  interval covers only about 70% of outcomes. The model *rankings* are still valid (pinball loss is a
  proper score), but the bands are too narrow to use as scenarios without a calibration fix.
- **No hypothesis was changed after seeing results.** Anything done after round 1 is labelled
  exploratory below.

## H1: CZ and DE prices are linked (descriptive)

| Year | Hourly price correlation | Share of hours with identical CZ and DE price |
|---|---|---|
| 2022 | 0.974 | 48.3% |
| 2023 | 0.905 | 29.3% |
| 2024 | 0.917 | 14.4% |
| 2025 | 0.922 | 10.4% |

- Correlation of **daily changes**: 0.916, block-bootstrap 95% CI [0.892, 0.935].
- Engle-Granger cointegration (CZ vs DE daily means): p < 0.0001.
- ADF rejects a unit root (p = 0.030) while KPSS rejects stationarity (p <= 0.01, outside the lookup
  table). When the two disagree like this, the usual reading is a series with structural breaks,
  which fits the 2022 to 2023 level shift and is the reason for walk-forward validation.
- The price-equality share falls steadily, so the two markets are still strongly correlated but
  clear at identical prices much less often. Q4 2025 is partly affected by averaging four 15-minute
  prices into one hourly value, so I would not over-read that year.

## Pinball loss, coverage and width

**Pinball loss (mean over 7 quantiles)**

| Model | 2023 | 2024 | 2025 | All |
|---|---|---|---|---|
| naive_bands | 11.24 | 10.12 | 9.30 | 10.22 |
| no_lags | 39.87 | 17.29 | 8.74 | 21.96 |
| base_cz | 7.22 | 6.98 | 5.58 | 6.60 |
| full | 7.39 | 6.50 | 4.67 | 6.19 |
| full_no_resid | 7.17 | 5.91 | 4.70 | 5.93 |
| full_regime | 7.26 | 6.49 | 4.65 | 6.14 |

**Coverage of the nominal 90% interval (target 0.90)**

| Model | 2023 | 2024 | 2025 | All |
|---|---|---|---|---|
| naive_bands | 0.999 | 0.982 | 0.970 | 0.984 |
| no_lags | 0.259 | 0.464 | 0.910 | 0.544 |
| base_cz | 0.781 | 0.727 | 0.833 | 0.780 |
| full | 0.667 | 0.643 | 0.785 | 0.698 |
| full_no_resid | 0.704 | 0.730 | 0.816 | 0.750 |
| full_regime | 0.668 | 0.631 | 0.787 | 0.695 |

**Mean width of the 90% interval (EUR/MWh)**

| Model | 2023 | 2024 | 2025 | All |
|---|---|---|---|---|
| naive_bands | 316.2 | 229.9 | 196.3 | 247.4 |
| no_lags | 123.1 | 141.5 | 142.4 | 135.6 |
| base_cz | 72.0 | 61.5 | 66.2 | 66.5 |
| full | 59.0 | 46.9 | 49.2 | 51.7 |
| full_no_resid | 64.2 | 50.5 | 53.2 | 55.9 |
| full_regime | 56.2 | 45.3 | 49.1 | 50.2 |

## Confirmatory tests (H2 to H6)

Diebold-Mariano on daily losses, HAC errors (7 lags), Holm-adjusted over the five tests.
A negative difference means model A is better. "Supported" needs a Holm-adjusted p < 0.05,
a bootstrap CI that excludes zero, and at least a 1% loss reduction.

| Hypothesis | A vs B | Mean diff | Relative change | 95% CI (DM) | 95% CI (bootstrap) | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|---|
| H2 German forecasts help | full vs base_cz | -0.410 | -6.2% | [-0.894, 0.073] | [-0.847, 0.090] | 0.096 | 0.188 | Inconclusive |
| H3 Residual load helps | full vs full_no_resid | +0.259 | +4.4% | [0.018, 0.500] | [0.045, 0.509] | 0.035 | 0.105 | Inconclusive |
| H4 Recent prices matter | full vs no_lags | -15.78 | -71.8% | [-19.40, -12.15] | [-19.22, -12.57] | <0.0001 | <0.0001 | **Supported** |
| H5 Regimes help | full_regime vs full | -0.050 | -0.8% | [-0.109, 0.009] | [-0.105, 0.010] | 0.094 | 0.188 | Inconclusive |
| H6 Beats naive baseline | full vs naive_bands | -4.03 | -39.5% | [-4.64, -3.43] | [-4.60, -3.42] | <0.0001 | <0.0001 | **Supported** |

**Predictions vs outcomes** (predictions as written in `HYPOTHESES.md` before results; edit this
column if your file differs)

| | Predicted | Outcome |
|---|---|---|
| H2 | Modest gain of 2 to 5% | Gain of 6.2% but not significant after correction |
| H3 | Inconclusive | Inconclusive, but the direction is *against* the hypothesis |
| H4 | Supported, 15 to 30% effect | Supported, effect much larger (the no-lags loss is about 3.5x higher) |
| H5 | Little or no gain | Inconclusive, gain of 0.8% |
| H6 | Supported, 10 to 25% effect | Supported, effect larger (39.5%) |

### Reading the results

- **H4.** Without lagged prices the model does very little: 22.0 against 6.2 overall, and 39.9
  against 7.4 in 2023, the year right after the 2022 crisis. The covariates alone cannot tell the
  model what price level it is in (fuel prices are not in the feature set), and the price lags
  carry that information. The gap shrinks each year (-81%, -62%, -47%), consistent with
  the training window gradually containing more post-crisis data.
- **H6.** Large and consistent in every year. Caveat: the naive bands are extremely wide
  (90% width 247 vs 52 for `full`) and cover 98% of outcomes, so part of the gap is the baseline
  being poorly calibrated and not only less accurate. I should also compare the accuracy of the
  median forecast alone (see TODO).
- **H3.** The `full_no_resid` model, which has no residual-load features, has the best overall
  pinball loss (5.93 against 6.19 for `full`). The adjusted p-value does not clear the bar, so this
  is not a confirmed result. The unadjusted p-value of 0.035 and the 2024 breakdown
  (+10.0%, p = 0.002, exploratory) suggest the extra features may add noise. A plausible reason is
  that tree models can already form residual load from its components, so the explicit
  feature is redundant and gives the model more ways to overfit. This is a hypothesis about
  the result, not something I tested.
- **H2 and H5.** Both are inconclusive: the estimates point in the right direction, but the
  uncertainty covers zero. The regime features changed the loss by less than 1% in every year.
- **Nested models.** For H2 to H5 one model contains the other's features, which makes the
  Diebold-Mariano null a boundary case. The bootstrap interval is a cross-check, and it
  agrees with the DM interval in every row.

## Calibration

All models fail the Kupiec test (p < 0.0001), but with more than 30,000 hours that test rejects
small deviations, so the size of the miss matters more than the p-value.

| Model | Share outside the 90% interval (target 0.10) | Kupiec p | Christoffersen p (independence) |
|---|---|---|---|
| naive_bands | 0.017 | <0.0001 | 0.0006 |
| base_cz | 0.220 | <0.0001 | <0.0001 |
| full | 0.302 | <0.0001 | <0.0001 |
| full_no_resid | 0.250 | <0.0001 | <0.0001 |
| full_regime | 0.305 | <0.0001 | <0.0001 |
| no_lags | 0.456 | <0.0001 | <0.0001 |

Christoffersen is evaluated on one hour per day (hour 12), so the sequence has one forecast per day.

**Reliability** (observed share of outcomes below each predicted quantile; target = the level)

| Quantile | naive_bands | full | full_regime |
|---|---|---|---|
| 0.05 | 0.008 | 0.221 | 0.225 |
| 0.10 | 0.031 | 0.315 | 0.331 |
| 0.25 | 0.160 | 0.453 | 0.460 |
| 0.50 | 0.498 | 0.630 | 0.629 |
| 0.75 | 0.844 | 0.766 | 0.766 |
| 0.90 | 0.970 | 0.865 | 0.866 |
| 0.95 | 0.992 | 0.919 | 0.921 |

Findings:

1. **The LightGBM bands are too narrow.** `full` covers about 70% in its 90% interval, and
   22% of outcomes fall below its 5% quantile.
2. **The forecasts are biased upward.** 63% of outcomes fall below the predicted median.
   The lower quantiles are the worst, so the model overestimates prices more at the low end.
3. **More features gave narrower, less honest bands.** From `base_cz` to `full_regime`, width falls from
   66.5 to 50.2 while coverage drops from 0.78 to 0.70.
4. **Coverage is worst in 2023 and 2024** (0.67 and 0.64 for `full`) and better in 2025 (0.79).
   Two explanations fit this and have not been separated yet: overfitting, and a legacy of 2022
   crisis prices in early training windows (see the diagnostic below).
5. **The naive bands fail in the opposite direction:** 98% coverage and very wide, so neither
   approach is usable as-is for decision-making.
6. **Misses are clustered** (Christoffersen rejects independence for every model), which is
   expected if errors concentrate in volatile stretches.

## By-year breakdown (exploratory, unadjusted p-values)

Relative change in loss for model A against model B, and the unadjusted DM p-value.
These slices were not pre-registered and are not corrected for multiple comparisons,
so treat them as descriptive.

| Hypothesis | 2023 | 2024 | 2025 | p 2023 | p 2024 | p 2025 |
|---|---|---|---|---|---|---|
| H2 German forecasts help | +2.3% | -6.9% | -16.3% | 0.779 | 0.232 | <0.001 |
| H3 Residual load helps | +3.0% | +10.0% | -0.7% | 0.478 | 0.002 | 0.542 |
| H4 Recent prices matter | -81.5% | -62.4% | -46.5% | <0.001 | <0.001 | <0.001 |
| H5 Regimes help | -1.7% | -0.2% | -0.3% | 0.084 | 0.819 | 0.470 |
| H6 Beats naive baseline | -34.3% | -35.8% | -49.8% | <0.001 | <0.001 | <0.001 |

- The only pattern worth following up is H2: the German forecasts do nothing in 2023, and
  show a 16% improvement in 2025. This could mean the coupling matters more in the
  recent market structure, but with unadjusted p-values and three years it is a suspicion.

## Exploratory follow-ups

### Calibration diagnostic (TODO)
Bias, coverage and width of `full` by quarter, to separate overfitting from the 2022 legacy.

*Result: to be added.*

### Round 2: calibration fix (TODO)
Post hoc, planned in the dated addendum to `HYPOTHESES.md`: conformalized quantile regression
with the last 90 days of each training window held out for calibration.
Target: coverage of the 90% interval within +/-3 points in each test year; compared on the
interval (Winkler) score.

*Result: to be added.*

### What the regimes look like (TODO)
Fitted HMM states, their means and durations, and how they line up with 2022 to 2025.

*Result: to be added.*

### Median-forecast accuracy (TODO)
MAE of the median forecast for `full` vs `naive_bands`, to separate accuracy from calibration in H6.

*Result: to be added.*

### Battery dispatch and value of information (TODO)
LP schedule using (a) a naive rule, (b) the forecast, (c) perfect foresight; revenue as a share of
perfect foresight.

*Result: to be added.*

## Limitations

- **Calibration.** The probabilistic bands are overconfident, so the quantile forecasts should not be
  read as honest predictive intervals until the round-2 fix is evaluated.
- **Nested model comparisons.** The DM test is approximate when one model contains another's
  features. A bootstrap interval is reported next to every DM result, and the Clark-West test would be
  the more formal choice.
- **Regime features are mildly optimistic in training.** The training rows use regime
  probabilities from an HMM fitted on those same days, while test rows get out-of-sample
  probabilities. This could weaken the regime model, not inflate its test results.
- **Fixed hyperparameters.** The LightGBM settings were fixed in advance and never tuned,
  which protects against test leakage but means none of the models is at its best.
- **Quarterly refits.** Models are refitted once per quarter, not daily as a live system would.
- **Resolution change.** Hourly prices after 2025-10-01 are means of four 15-minute prices.
- **No fuel prices.** Gas and carbon prices are not features, which probably explains much of H4.
- **Single market, one period.** Results cover Czechia in 2023 to 2025, following a crisis year in training.
- **Multiple comparisons.** Holm correction applies to H2 to H6 only. By-year results are unadjusted.