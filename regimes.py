import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from scipy.special import logsumexp
from scipy.stats import multivariate_normal

TZ = "Europe/Prague"


def daily_obs(price_hourly):
    """Daily observation vector: mean and intraday range of asinh(price/100). asinh handles negative prices."""
    p = price_hourly.tz_convert(TZ)
    z = np.arcsinh(p / 100.0)
    g = z.groupby(p.index.date)
    d = pd.DataFrame({"mean": g.mean(), "range": g.max() - g.min()})
    d.index = pd.to_datetime(d.index)
    return d


def _full_covars(cov):
    cov = np.asarray(cov)
    return np.array([np.diag(c) for c in cov]) if cov.ndim == 2 else cov


def fit_hmm(obs, k=3, n_init=10, seed=0):
    """EM with random restarts; states sorted by mean of the first feature to avoid label switching."""
    best, best_ll = None, -np.inf
    for i in range(n_init):
        m = GaussianHMM(n_components=k, covariance_type="diag", n_iter=300, tol=1e-4, random_state=seed + i)
        try:
            m.fit(obs)
            ll = m.score(obs)
        except Exception:
            continue
        if ll > best_ll:
            best, best_ll = m, ll
    assert best is not None, "HMM fit failed for all restarts"
    order = np.argsort(best.means_[:, 0])
    cov = _full_covars(best.covars_)
    return {"pi": best.startprob_[order],
            "A": best.transmat_[np.ix_(order, order)],
            "mu": best.means_[order],
            "cov": cov[order],
            "loglik": best_ll, "n_obs": len(obs)}


def filter_probs(obs, params):
    """Forward algorithm only: P(S_t | x_1..x_t). No smoothing, so no information from the future."""
    K = len(params["pi"])
    logB = np.column_stack([multivariate_normal.logpdf(obs, params["mu"][k], params["cov"][k]) for k in range(K)])
    logA = np.log(np.clip(params["A"], 1e-300, None))
    T = len(obs)
    alpha = np.empty((T, K))
    la = np.log(np.clip(params["pi"], 1e-300, None)) + logB[0]
    alpha[0] = np.exp(la - logsumexp(la))
    for t in range(1, T):
        pred = logsumexp(np.log(np.clip(alpha[t - 1], 1e-300, None))[:, None] + logA, axis=0)
        la = pred + logB[t]
        alpha[t] = np.exp(la - logsumexp(la))
    return alpha


def regime_features(price_hourly, train_end_date, k=3, n_init=10):
    """
    Fit on days strictly before train_end_date. Return, per local day D, P(S_D | data up to day D-1):
    the filtered probability of the last known day, propagated one step with the transition matrix.
    """
    obs = daily_obs(price_hourly)
    train = obs[obs.index < train_end_date]
    params = fit_hmm(train.to_numpy(), k=k, n_init=n_init)
    alpha = filter_probs(obs.to_numpy(), params)          # causal, fixed parameters
    nxt = alpha @ params["A"]                              # P(S_{d+1} | x_1..x_d)
    reg = pd.DataFrame(nxt, index=obs.index, columns=[f"regime_{i}" for i in range(k)]).shift(1)
    return reg, params


def attach_regime(X, reg):
    local_date = pd.to_datetime(X.index.tz_convert(TZ).date)
    return pd.DataFrame(reg.reindex(local_date).to_numpy(), index=X.index, columns=reg.columns)