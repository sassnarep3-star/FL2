"""Statistics used by the validation gates.

Everything in here exists to answer one question honestly: is this result skill, or
is it what a luck-driven search would have produced anyway? The deflated-Sharpe
machinery (Bailey & López de Prado, SSRN 2460551) is the published answer for
selection bias, so the gates use it rather than inventing a local rule.
"""
from __future__ import annotations

import math
from statistics import NormalDist, pstdev

_N = NormalDist()
EULER_GAMMA = 0.5772156649015329


def skewness(xs: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    m = sum(xs) / n
    s = math.sqrt(sum((x - m) ** 2 for x in xs) / n)
    if s == 0:
        return 0.0
    return sum(((x - m) / s) ** 3 for x in xs) / n


def kurtosis(xs: list[float]) -> float:
    """Non-excess kurtosis (the normal distribution scores 3)."""
    n = len(xs)
    if n < 4:
        return 3.0
    m = sum(xs) / n
    s = math.sqrt(sum((x - m) ** 2 for x in xs) / n)
    if s == 0:
        return 3.0
    return sum(((x - m) / s) ** 4 for x in xs) / n


def sharpe(returns: list[float]) -> float:
    if len(returns) < 2:
        return float("nan")
    sd = pstdev(returns)
    if sd == 0:
        return float("nan")
    return (sum(returns) / len(returns)) / sd


def expected_max_sharpe(n_variants: int, sr_variance: float) -> float:
    """SR*: the Sharpe ratio a *skill-free* search of `n_variants` trials would be
    expected to throw up, given the dispersion of trial Sharpes."""
    if n_variants <= 1:
        return 0.0
    v = max(sr_variance, 0.0)
    q1 = _N.inv_cdf(1.0 - 1.0 / n_variants)
    q2 = _N.inv_cdf(1.0 - 1.0 / (n_variants * math.e))
    return math.sqrt(v) * ((1.0 - EULER_GAMMA) * q1 + EULER_GAMMA * q2)


def deflated_sharpe(returns: list[float], n_variants: int, sr_variance: float) -> dict:
    """DSR: the probability that the observed Sharpe is not the maximum of a
    multiple-testing exercise. Returns a confidence in [0, 1]."""
    t = len(returns)
    sr = sharpe(returns)
    if t < 3 or math.isnan(sr):
        return {"t": t, "sharpe": sr, "sr_star": expected_max_sharpe(n_variants, sr_variance),
                "dsr": float("nan"), "min_trl": float("nan"),
                "note": "too few observations to estimate"}
    g3, g4 = skewness(returns), kurtosis(returns)
    sr_star = expected_max_sharpe(n_variants, sr_variance)
    denom = math.sqrt(max(1e-12, 1.0 - g3 * sr + ((g4 - 1.0) / 4.0) * sr * sr))
    dsr = _N.cdf((sr - sr_star) * math.sqrt(t - 1.0) / denom)
    # Minimum Track Record Length (periods) needed for SR to clear SR* at 95%.
    # Meaningless (infinite) while SR has not yet overtaken SR*: an observed Sharpe
    # below the multiple-testing null can be lengthened forever and still not clear it.
    num = (1.0 - g3 * sr + ((g4 - 1.0) / 4.0) * sr * sr)
    gap = (sr - sr_star) ** 2
    min_trl = (1.0 + num * (_N.inv_cdf(0.975) ** 2) / gap) if (sr > sr_star and gap > 1e-12) else float("inf")
    return {"t": t, "sharpe": sr, "skew": g3, "kurtosis": g4, "sr_star": sr_star,
            "n_variants": n_variants, "dsr": dsr, "min_trl_periods": min_trl,
            "min_trl_multiple_of_sample": (min_trl / t) if t and math.isfinite(min_trl) else float("nan")}


def moving_block_bootstrap_p(returns: list[float], block: int = 1, resamples: int = 4000,
                             seed: int = 20261114) -> dict:
    """One-sided p-value for H0: mean return <= 0, resampled in blocks so that
    serial dependence (a hot streak, a weather-driven week) is preserved rather than
    shuffled away. Deterministic: fixed seed, fixed generator."""
    n = len(returns)
    if n < 4:
        return {"p": float("nan"), "resamples": 0, "note": "sample too small"}
    block = max(1, min(block, n))
    rng = _LCG(seed)
    obs = sum(returns) / n
    # centre the sample at zero so the resampling distribution satisfies H0
    shifted = [x - obs for x in returns]
    count = 0
    n_blocks = int(math.ceil(n / block))
    starts = list(range(0, n - block + 1))
    for _ in range(resamples):
        sample: list[float] = []
        for _b in range(n_blocks):
            i = rng.next_int(len(starts))
            sample.extend(shifted[i:i + block])
        if (sum(sample[:n]) / n) >= obs:
            count += 1
    return {"p": (count + 1) / (resamples + 1), "resamples": resamples,
            "block": block, "mean_return": obs}


def sign_flip_permutation_p(returns: list[float], max_exact: int = 16) -> dict:
    """Exact (small n) or deterministic-random sign-flip test: the distribution of the
    mean under the assumption that each bet's outcome sign carries no information."""
    n = len(returns)
    if n == 0:
        return {"p": float("nan"), "method": "none"}
    obs = sum(returns) / n
    if n <= max_exact:
        worse = 0
        total = 1 << n
        for mask in range(total):
            s = 0.0
            for i in range(n):
                s += returns[i] if (mask >> i) & 1 else -returns[i]
            if s / n >= obs - 1e-15:
                worse += 1
        return {"p": worse / total, "method": "exact", "n": n}
    rng = _LCG(20261114)
    worse = 0
    reps = 20000
    for _ in range(reps):
        s = 0.0
        for x in returns:
            s += x if rng.next_int(2) else -x
        if s / n >= obs - 1e-15:
            worse += 1
    return {"p": (worse + 1) / (reps + 1), "method": "random", "n": n, "reps": reps}


class _LCG:
    """Tiny deterministic generator so tests never depend on platform RNG changes."""
    __slots__ = ("state",)

    def __init__(self, seed: int):
        self.state = seed % (2 ** 31)

    def next_float(self) -> float:
        self.state = (1103515245 * self.state + 12345) % (2 ** 31)
        return self.state / (2 ** 31)

    def next_int(self, bound: int) -> int:
        if bound <= 0:
            return 0
        return min(bound - 1, int(self.next_float() * bound))
