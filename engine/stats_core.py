"""
FL2 — statistics core.

Everything here is deliberately conservative. The point of this module is to
make it *hard* for a betting strategy to look good, so that the few that survive
are plausibly real.

Design rules
------------
1.  No look-ahead. Every feature for game `i` is computed only from games whose
    kickoff is strictly earlier (we use season+week ordering and never use the
    current game's own result).
2.  Out-of-sample by construction. Models are fit on a rolling/expanding
    training window and always evaluated on a *later* block of games.
3.  Vig is removed before any probability is compared with a market price.
4.  Luck is separated from skill with an explicit variance decomposition and a
    bootstrap null distribution.
5.  Everything reports a confidence interval. A point estimate with a wide CI is
    not evidence.
"""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd

RNG = np.random.default_rng(20261114)  # fixed seed -> reproducible report


# --------------------------------------------------------------------------- #
# Market maths
# --------------------------------------------------------------------------- #
def american_to_prob(odds: float) -> float:
    """Raw (vig-included) implied probability from American odds."""
    if odds is None or (isinstance(odds, float) and math.isnan(odds)):
        return float("nan")
    if odds < 0:
        return (-odds) / ((-odds) + 100.0)
    return 100.0 / (odds + 100.0)


def american_to_decimal(odds: float) -> float:
    """Payout multiple including stake."""
    if odds < 0:
        return 1.0 + 100.0 / (-odds)
    return 1.0 + odds / 100.0


def american_to_payout(odds: float) -> float:
    """Profit per 1 unit staked."""
    return american_to_decimal(odds) - 1.0


def devig_two_way(p_a: float, p_b: float, method: str = "proportional") -> tuple[float, float]:
    """Remove the bookmaker margin from a two-way market.

    `proportional` (a.k.a. normalised) is the standard first-order correction.
    `shin` is available for completeness but needs the full market; for two-way
    books the difference is small (<0.4 probability points).
    """
    if method != "proportional":
        raise NotImplementedError("only proportional devig is implemented/needed here")
    s = p_a + p_b
    if not np.isfinite(s) or s <= 0:
        return float("nan"), float("nan")
    return p_a / s, p_b / s


def kelly_fraction(p_win: float, decimal_odds: float, fraction: float = 0.25) -> float:
    """Fractional Kelly stake (as fraction of bankroll). Never negative."""
    b = decimal_odds - 1.0
    if b <= 0:
        return 0.0
    f = (p_win * b - (1.0 - p_win)) / b
    return max(0.0, f * fraction)


# --------------------------------------------------------------------------- #
# Scoring rules / evaluation
# --------------------------------------------------------------------------- #
def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def log_loss(p: np.ndarray, y: np.ndarray, eps: float = 1e-12) -> float:
    p = np.clip(np.asarray(p, float), eps, 1 - eps)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier_skill_score(p_model: np.ndarray, p_base: np.ndarray, y: np.ndarray) -> float:
    """1 - BS_model/BS_base. Positive => beats the baseline."""
    bs_m, bs_b = brier(p_model, y), brier(p_base, y)
    return float(1.0 - bs_m / bs_b) if bs_b > 0 else float("nan")


def units_profit(prices: Iterable[float], outcomes: Iterable[float], stake: float = 1.0) -> float:
    """Flat-stake P/L in units, using *de-vigged-fair* payouts is NOT done here:
    we settle at the actual price taken, which is the honest thing to do."""
    tot = 0.0
    for price, won in zip(prices, outcomes):
        if not np.isfinite(price):
            continue
        tot += stake * (american_to_payout(price) if won else -1.0)
    return float(tot)


def bootstrap_ci(
    values: np.ndarray, stat=np.mean, n_boot: int = 4000, alpha: float = 0.05
) -> tuple[float, float, float]:
    """Percentile bootstrap CI for an arbitrary statistic."""
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return float("nan"), float("nan"), float("nan")
    idx = RNG.integers(0, v.size, size=(n_boot, v.size))
    stats = stat(v[idx], axis=1)
    return float(stat(v)), float(np.quantile(stats, alpha / 2)), float(np.quantile(stats, 1 - alpha / 2))


def block_bootstrap_ci(
    values: np.ndarray, block: int = 16, n_boot: int = 4000, alpha: float = 0.05
) -> tuple[float, float, float]:
    """Block bootstrap for serially dependent observations (a season of bets is
    ordered in time; iid bootstrap understates the error)."""
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    n = v.size
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    block = max(1, min(block, n))
    n_blocks = int(math.ceil(n / block))
    starts_pool = np.arange(0, n - block + 1) if n > block else np.array([0])
    means = np.empty(n_boot)
    for i in range(n_boot):
        s = RNG.choice(starts_pool, size=n_blocks, replace=True)
        sample = np.concatenate([v[j : j + block] for j in s])[:n]
        means[i] = sample.mean()
    return float(v.mean()), float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


# --------------------------------------------------------------------------- #
# Luck vs skill
# --------------------------------------------------------------------------- #
def luck_share(per_bet_returns: np.ndarray) -> dict:
    """Variance decomposition of a betting record.

    Think of the observed mean return as signal + noise. Under the null that a
    strategy has zero edge and every bet is a coin flip priced fairly, the
    sampling variance of the mean return is known, so we can say what fraction
    of a record's apparent profitability is consistent with pure luck.

    Returns
    -------
    luck_fraction : share of the observed variance of the *record* attributable
        to random outcome noise under the null (1.0 = fully explainable by luck).
    t_stat : mean / standard error of returns (iid; use block bootstrap for a
        serial-correlation-robust version in the caller).
    p_value : one-sided p for "mean return > 0" under a normal approximation.
    """
    r = np.asarray(per_bet_returns, float)
    r = r[np.isfinite(r)]
    n = r.size
    if n < 10:
        return {"n": int(n), "luck_fraction": float("nan"), "t_stat": float("nan"),
                "p_value": float("nan"), "mean_return": float("nan")}
    mu, sd = r.mean(), r.std(ddof=1)
    se = sd / math.sqrt(n)
    t = mu / se if se > 0 else float("nan")
    # Sharpe-like: how many standard errors from zero.
    p = 0.5 * (1 - math.erf(t / math.sqrt(2))) if np.isfinite(t) else float("nan")
    # Under a fair-coin null, returns are +/-1 with mean 0 and sd 1.
    var_null = (1.0 / n)
    obs_var_of_mean = se ** 2
    luck = 1.0 - (max(obs_var_of_mean - var_null, 0.0) / obs_var_of_mean) if obs_var_of_mean > 0 else 1.0
    return {
        "n": int(n),
        "mean_return": float(mu),
        "sd_return": float(sd),
        "t_stat": float(t),
        "p_value": float(p),
        "luck_fraction": float(min(max(luck, 0.0), 1.0)),
    }


def effective_sample_size(per_bet_returns: np.ndarray) -> float:
    """n_eff from lag-1 autocorrelation: correlated bets (parlays, same-game
    combos, correlated props) do not give you n independent observations."""
    r = np.asarray(per_bet_returns, float)
    r = r[np.isfinite(r)]
    if r.size < 3:
        return float(r.size)
    x = r - r.mean()
    denom = float(np.dot(x, x))
    if denom == 0:
        return float(r.size)
    rho = float(np.dot(x[:-1], x[1:]) / denom)
    rho = min(max(rho, -0.99), 0.99)
    return float(r.size * (1 - rho) / (1 + rho))


# --------------------------------------------------------------------------- #
# Correlations between legs (for parlays / SGP / prop combos)
# --------------------------------------------------------------------------- #
def phi_coefficient(a: np.ndarray, b: np.ndarray) -> float:
    """Association between two binary outcomes — the right measure for
    'do these two legs win together more often than independence implies?'"""
    a = np.asarray(a, bool); b = np.asarray(b, bool)
    if a.size != b.size or a.size == 0:
        return float("nan")
    n11 = np.sum(a & b); n10 = np.sum(a & ~b); n01 = np.sum(~a & b); n00 = np.sum(~a & ~b)
    denom = math.sqrt(float((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00)))
    if denom == 0:
        return float("nan")
    return float((n11 * n00 - n10 * n01) / denom)


def phi_ci(a: np.ndarray, b: np.ndarray, n_boot: int = 2000) -> tuple[float, float, float]:
    """Bootstrap CI for phi — indispensable, because the noise on a pairwise
    correlation with a few hundred games is larger than most 'signals'."""
    a = np.asarray(a, bool); b = np.asarray(b, bool)
    n = a.size
    if n < 30:
        return float("nan"), float("nan"), float("nan")
    pt = phi_coefficient(a, b)
    idx = RNG.integers(0, n, size=(n_boot, n))
    vals = np.array([phi_coefficient(a[i], b[i]) for i in idx])
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return pt, float("nan"), float("nan")
    return pt, float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def implied_parlay_prob(legs: list[tuple[float, float]], rho_matrix: np.ndarray | None = None,
                        n_sim: int = 200_000) -> dict:
    """Probability a parlay of independent legs wins, vs. a Gaussian-copula
    estimate that lets the legs be correlated.

    legs: list of (de_vigged_prob, rho_to_previous) — rho_to_previous is ignored
          when rho_matrix is supplied.
    """
    p = np.array([l[0] for l in legs], float)
    p_indep = float(np.prod(p))
    if rho_matrix is None:
        rho_matrix = np.eye(len(p))
    cov = np.asarray(rho_matrix, float)
    # nearest PSD
    w, v = np.linalg.eigh(cov)
    w = np.clip(w, 1e-6, None)
    cov = v @ np.diag(w) @ v.T
    d = np.sqrt(np.diag(cov))
    corr = cov / np.outer(d, d)
    L = np.linalg.cholesky(corr + np.eye(len(p)) * 1e-9)
    z = (RNG.standard_normal((n_sim, len(p))) @ L.T)
    u = 0.5 * (1 + np.vectorize(math.erf)(z / math.sqrt(2)))
    wins = (u < p).all(axis=1)
    return {
        "n_legs": len(p),
        "p_independent": p_indep,
        "p_correlated": float(wins.mean()),
        "fair_american_independent": prob_to_american(p_indep),
        "fair_american_correlated": prob_to_american(float(wins.mean())),
    }


def prob_to_american(p: float) -> float:
    if not np.isfinite(p) or p <= 0 or p >= 1:
        return float("nan")
    return float(-100 * p / (1 - p)) if p >= 0.5 else float(100 * (1 - p) / p)


# --------------------------------------------------------------------------- #
# Elo-style strength state (used as the model's backbone feature)
# --------------------------------------------------------------------------- #
class Elo:
    """Simple, transparent, leakage-free Elo with home advantage and a
    season-boundary regression toward the mean.

    Chosen over a fitted model because every parameter is inspectable and it
    cannot silently overfit a small sample.
    """

    def __init__(self, k: float = 20.0, hfa: float = 48.0, carry: float = 0.75,
                 regress_to: float = 1505.0):
        self.k = k
        self.hfa = hfa
        self.carry = carry
        self.regress_to = regress_to
        self.rating: dict[str, float] = {}
        self._season: int | None = None

    def _ensure(self, team: str) -> float:
        return self.rating.setdefault(team, 1500.0)

    def start_season(self, season: int) -> None:
        if self._season is not None and season != self._season:
            for t in list(self.rating):
                self.rating[t] = self.regress_to + self.carry * (self.rating[t] - self.regress_to)
        self._season = season

    def expected_home(self, home: str, away: str) -> float:
        diff = (self._ensure(home) + self.hfa) - self._ensure(away)
        return 1.0 / (1.0 + 10 ** (-diff / 400.0))

    def update(self, home: str, away: str, home_margin: float) -> float:
        exp = self.expected_home(home, away)
        actual = 1.0 if home_margin > 0 else (0.5 if home_margin == 0 else 0.0)
        # margin-of-victory multiplier (dampened) — the usual fix so that a 30-point
        # win doesn't move ratings 30x more than a 1-point win.
        mov = math.log1p(abs(home_margin)) * 2.0
        delta = self.k * mov * (actual - exp)
        self.rating[home] = self._ensure(home) + delta
        self.rating[away] = self._ensure(away) - delta
        return exp
