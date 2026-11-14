"""Odds, implied probability, de-vigging, sizing. All pure functions, all tested."""
from __future__ import annotations

import math
from statistics import NormalDist

_N = NormalDist()


def american_to_decimal(american: float) -> float:
    """-110 -> 1.909090…, +100 -> 2.0."""
    a = float(american)
    if a == 0:
        raise ValueError("american odds cannot be 0")
    return 1.0 + (100.0 / abs(a) if a < 0 else a / 100.0)


def decimal_to_american(dec: float) -> int:
    if dec <= 1.0:
        raise ValueError("decimal odds must exceed 1.0")
    if dec >= 2.0:
        return int(round(100.0 * (dec - 1.0)))
    return int(round(-100.0 / (dec - 1.0)))


def american_to_implied(american: float) -> float:
    """Bookmaker implied probability *including* the vig (overround)."""
    return 1.0 / american_to_decimal(american)


def prob_to_american(p: float) -> int:
    """Fair price for probability p (no vig)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0,1)")
    return decimal_to_american(1.0 / p)


def break_even(p_american: float) -> float:
    """Hit-rate needed to break even at a price, before vig removal."""
    a = float(p_american)
    return (100.0 / (100.0 + abs(a))) if a > 0 else (abs(a) / (abs(a) + 100.0))


def devig_multiplicative(prices: list[float]) -> list[float]:
    """Normalise implied probabilities across a market (the standard multiplicative
    de-vig). Returns fair probabilities summing to 1; the removed excess is the vig."""
    imp = [american_to_implied(p) for p in prices]
    s = sum(imp)
    return [i / s for i in imp]


def vig_share(prices: list[float]) -> float:
    """Fraction of the market's total stake that the book keeps at equilibrium."""
    imp = [american_to_implied(p) for p in prices]
    s = sum(imp)
    return 1.0 - 1.0 / s if s > 0 else float("nan")


def fair_prob_market(side_prices: list[float], idx: int = 0) -> float:
    """De-vigged probability for outcome `idx` given one market's prices."""
    return devig_multiplicative(side_prices)[idx]


def edge(p_model: float, p_market_novig: float) -> float:
    """Edge in probability points. Measured against a *de-vigged* market only."""
    return p_model - p_market_novig


def expected_value(p: float, american: float) -> float:
    """EV per 1 unit staked, ignoring push handling (callers model pushes)."""
    b = american_to_decimal(american) - 1.0
    return p * b - (1.0 - p)


def kelly_fraction(p: float, american: float, fraction: float = 0.25) -> float:
    """Fractional Kelly on the de-vigged edge; never negative, never > fraction*full."""
    b = american_to_decimal(american) - 1.0
    full = (b * p - (1.0 - p)) / b
    return max(0.0, full) * fraction


def wilson_interval(k: int, n: int, confidence: float = 0.90) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (robust at small n, unlike
    the normal approximation that most bet-tracking spreadsheets use)."""
    if n <= 0:
        return (float("nan"), float("nan"))
    z = _N.inv_cdf(0.5 + confidence / 2.0)
    ph = k / n
    d = 1.0 + z * z / n
    c = ph + z * z / (2.0 * n)
    m = z * math.sqrt(ph * (1.0 - ph) / n + z * z / (4.0 * n * n))
    return ((c - m) / d, (c + m) / d)


def min_bets_to_beat_break_even(hit_rate: float, break_even_p: float,
                                confidence: float = 0.90, step: int = 1,
                                cap: int = 200000) -> int | None:
    """Smallest n for which the *lower* Wilson bound of a hit rate of `hit_rate`
    clears `break_even_p`. This is the 'remove luck' question in one number."""
    k_rate = hit_rate
    n = step
    while n <= cap:
        k = int(round(k_rate * n))
        lo, _ = wilson_interval(k, n, confidence)
        if lo > break_even_p:
            return n
        n += step
    return None


def z_from_p(two_sided_p: float) -> float:
    return _N.inv_cdf(1.0 - two_sided_p / 2.0)
