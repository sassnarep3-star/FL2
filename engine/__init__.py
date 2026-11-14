"""FL2 engine — pure-stdlib reference implementation of the pricing, combo and
validation arithmetic used across the site.

Design rules (see also assets/data/strategy.js):
* Every number published on the site that is *ours* comes from this code.
* Nothing here invents market data: no prices, holds or edges are hardcoded.
* Deterministic: tests use fixed seeds; statistical integrals are quadrature,
  not sampling, so they are reproducible on any machine.
"""
from . import odds, parlay, gates, registry, config  # noqa: F401

__all__ = ["odds", "parlay", "gates", "registry", "config"]
