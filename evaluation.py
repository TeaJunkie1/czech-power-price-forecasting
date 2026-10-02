import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from scipy.special import xlogy
from statsmodels.stats.multitest import multipletests

QUANTILES = [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
TZ = "Europe/Prague"


def pinball(y, pred, quantiles=QUANTILES):
    """Row-wise pinball loss averaged over quantiles."""
    losses = []
    for q in quantiles:
        e = y - pred[q]
        losses.append(np.maximum(q * e, (q - 1) * e))
    return pd.concat(losses, axis=1).mean(axis=1)


def central_coverage(y, pred, lo=0.05, hi=0.95):
    return ((y >= pred[lo]) & (y <= pred[hi])).mean()


def interval_width(pred, lo=0.05, hi=0.95):
    return (pred[hi] - pred[lo]).mean()


def reliability(y, pred, quantiles=QUANTILES):
    """Observed share of outcomes below each predicted quantile; should equal the quantile level."""
    return pd.Series({q: (y <= pred[q]).mean() for q in quantiles})


def daily(loss):
    """Aggregate hourly losses to local-day means (24 hourly forecasts are made at the same moment)."""
    return loss.groupby(loss.index.tz_convert(TZ).date).mean()


# diebold-Mariano with hac errors
def dm_test(loss_a, loss_b, maxlags=7):
    """Negative mean_diff means model A has lower loss than model B."""
    da, db = daily(loss_a), daily(loss_b)
    d = (da - db).dropna()
    fit = sm.OLS(d.to_numpy(), np.ones(len(d))).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    mean, se, p = float(fit.params[0]), float(fit.bse[0]), float(fit.pvalues[0])
    return {"mean_diff": mean, "se": se, "p": p,
            "ci_lo": mean - 1.96 * se, "ci_hi": mean + 1.96 * se,
            "rel_change": mean / db.mean(), "n_days": len(d)}


def block_bootstrap_mean_ci(d, block=7, B=2000, seed=0):
    """Moving-block bootstrap CI for the mean of a (autocorrelated) daily series."""
    rng = np.random.default_rng(seed)
    d = np.asarray(d, dtype=float)
    n = len(d)
    n_blocks = int(np.ceil(n / block))
    means = np.empty(B)
    for b in range(B):
        starts = rng.integers(0, n - block + 1, n_blocks)
        means[b] = np.concatenate([d[s:s + block] for s in starts])[:n].mean()
    return np.percentile(means, [2.5, 97.5])


def block_bootstrap_corr_ci(a, b, block=7, B=2000, seed=0):
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = len(a)
    n_blocks = int(np.ceil(n / block))
    out = np.empty(B)
    for i in range(B):
        starts = rng.integers(0, n - block + 1, n_blocks)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        out[i] = np.corrcoef(a[idx], b[idx])[0, 1]
    return np.percentile(out, [2.5, 97.5])


def holm(pvals):
    return multipletests(pvals, alpha=0.05, method="holm")[1]


# interval backtests 
def kupiec(hits, p):
    """Unconditional coverage: is the violation rate equal to p?"""
    hits = np.asarray(hits, int)
    n, x = len(hits), hits.sum()
    pi = x / n
    ll0 = xlogy(n - x, 1 - p) + xlogy(x, p)
    ll1 = xlogy(n - x, 1 - pi) + xlogy(x, pi)
    lr = -2 * (ll0 - ll1)
    return lr, stats.chi2.sf(lr, 1)


def christoffersen_ind(hits):
    """Independence: are violations clustered in time?"""
    h = np.asarray(hits, int)
    a, b = h[:-1], h[1:]
    n00, n01 = np.sum((a == 0) & (b == 0)), np.sum((a == 0) & (b == 1))
    n10, n11 = np.sum((a == 1) & (b == 0)), np.sum((a == 1) & (b == 1))
    pi01 = n01 / (n00 + n01) if (n00 + n01) else 0.0
    pi11 = n11 / (n10 + n11) if (n10 + n11) else 0.0
    pi = (n01 + n11) / (n00 + n01 + n10 + n11)
    ll0 = xlogy(n00 + n10, 1 - pi) + xlogy(n01 + n11, pi)
    ll1 = (xlogy(n00, 1 - pi01) + xlogy(n01, pi01) + xlogy(n10, 1 - pi11) + xlogy(n11, pi11))
    lr = -2 * (ll0 - ll1)
    return lr, stats.chi2.sf(lr, 1)


def calibration_report(y, pred, lo=0.05, hi=0.95, hour=12):
    """Kupiec on all hours; Christoffersen on one fixed hour of day so the sequence is one forecast per day."""
    hits = ~((y >= pred[lo]) & (y <= pred[hi]))
    k_lr, k_p = kupiec(hits.to_numpy(), 1 - (hi - lo))
    h_day = hits[hits.index.tz_convert(TZ).hour == hour]
    c_lr, c_p = christoffersen_ind(h_day.to_numpy())
    return {"violation_rate": hits.mean(), "kupiec_p": k_p, "christoffersen_ind_p": c_p}


# parquet needs string column names 
def save_preds(df, path):
    out = df.copy()
    out.columns = [str(c) for c in out.columns]
    out.to_parquet(path)


def load_preds(path):
    df = pd.read_parquet(path)
    df.columns = [float(c) for c in df.columns]
    return df