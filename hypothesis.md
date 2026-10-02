# Hypotheses (pre-registered, tests fixed before results)
Forecast made on the morning of D-1 for day D. Score: pinball loss averaged over 7 quantiles,
aggregated to daily means. Test: Diebold-Mariano with HAC (7 lags), two-sided, Holm-adjusted over H2-H6, alpha = 0.05.
A hypothesis is "supported" only if the mean loss difference favours the named model AND adjusted p < 0.05.

H1  CZ and DE prices are linked (daily-change correlation CI excludes 0; cointegration test). Descriptive.
H2  German forecasts help:      full            beats  base_cz
H3  Residual load helps:        full            beats  full_no_resid
H4  Recent prices matter:       full            beats  no_lags
H5  Regimes help:               full_regime     beats  full        (K=3 fixed in advance)
H6  Model beats the baseline:   full            beats  naive_bands
Anything not listed here is exploratory and will be labelled as such.