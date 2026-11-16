"""Small, dependency-free statistics helpers for FL2 line origination.

Everything here is deterministic: every bootstrap takes an explicit seed, and the
seed is published next to every interval so a reviewer can re-run it.
Only Python stdlib is used, so the CI rebuild is byte-reproducible.
"""
from __future__ import annotations

import math
import random
from typing import Iterable, Sequence

SQRT2 = math.sqrt(2.0)


def norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / SQRT2))


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def sd(xs: Sequence[float]) -> float:
    n = len(xs)
    if n < 2:
        return float("nan")
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    n = len(xs)
    if n < 3 or len(ys) != n:
        return float("nan")
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx <= 0 or syy <= 0:
        return float("nan")
    return sxy / math.sqrt(sxx * syy)


def fisher_ci(r: float, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Fisher z 95% CI for a Pearson correlation. Returns (lo, hi) rounded to 4dp."""
    if n < 4 or math.isnan(r):
        return (float("nan"), float("nan"))
    r = max(-0.999999, min(0.999999, r))
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    crit = 1.959963985  # z_{0.975}
    lo, hi = z - crit * se, z + crit * se
    inv = lambda t: (math.exp(2 * t) - 1) / (math.exp(2 * t) + 1)
    return (round(inv(lo), 4), round(inv(hi), 4))


def wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion, as percentages."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    z = 1.959963985
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (round(100 * max(0.0, c - half), 2), round(100 * min(1.0, c + half), 2))


def cluster_bootstrap_mean_ci(
    values: Sequence[float], clusters: Sequence[object], seed: int, reps: int = 4000, alpha: float = 0.05
) -> tuple[float, float]:
    """Resample *clusters* (e.g. games), not rows, so two legs from one game cannot
    be treated as independent. Returns (lo, hi) percentile interval of the mean."""
    if not values:
        return (float("nan"), float("nan"))
    by_cluster: dict[object, list[float]] = {}
    for v, c in zip(values, clusters):
        by_cluster.setdefault(c, []).append(v)
    keys = sorted(by_cluster, key=lambda k: str(k))
    rng = random.Random(seed)
    stats: list[float] = []
    for _ in range(reps):
        sample: list[float] = []
        for _ in keys:
            sample.extend(by_cluster[keys[rng.randrange(len(keys))]])
        stats.append(mean(sample))
    stats.sort()
    lo = stats[int(round((alpha / 2) * (len(stats) - 1)))]
    hi = stats[int(round((1 - alpha / 2) * (len(stats) - 1)))]
    return (round(lo, 4), round(hi, 4))


def benjamini_hochberg(pvals: Sequence[tuple[str, float]], q: float) -> dict[str, bool]:
    """Return {id: reject} for the BH step-up procedure at false-discovery rate q."""
    items = sorted(((pid, p) for pid, p in pvals), key=lambda t: t[1])
    m = len(items)
    thresh = {items[i][0]: q * (i + 1) / m for i in range(m)}
    rejected = {pid: (p <= thresh[pid]) for pid, p in items}
    # step-up: once one passes, all with larger p are also rejected
    seen = False
    out = {}
    for pid, p in reversed(items):
        if rejected[pid] or seen:
            seen = True
            out[pid] = True
        else:
            out[pid] = False
    return out


def brier(probs: Iterable[float], outcomes: Iterable[int]) -> float:
    s, n = 0.0, 0
    for p, y in zip(probs, outcomes):
        s += (p - y) ** 2
        n += 1
    return s / n if n else float("nan")


def log_loss(probs: Iterable[float], outcomes: Iterable[int], eps: float = 1e-6) -> float:
    s, n = 0.0, 0
    for p, y in zip(probs, outcomes):
        p = min(1 - eps, max(eps, p))
        s += -(y * math.log(p) + (1 - y) * math.log(1 - p))
        n += 1
    return s / n if n else float("nan")


def american_to_prob(odds: float) -> float:
    if odds <= 0:
        return -odds / (-odds + 100.0)
    return odds / (odds + 100.0)


def prob_to_american(p: float) -> float:
    p = min(0.999999, max(0.000001, p))
    if p >= 0.5:
        return round(-100.0 * p / (1 - p))
    return round(100.0 * (1 - p) / p)


def implied_margin(home_odds: float, away_odds: float) -> float:
    """Two-way book margin (overround), as a fraction. >0 means vig was taken."""
    return american_to_prob(home_odds) + american_to_prob(away_odds) - 1.0


def fmt(x, dp: int = 2, blank: str = "") -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return blank
    return f"{x:.{dp}f}"
