"""Gate thresholds = policy, not fact. Change here, once, with a reason in the commit."""

GATES = {
    "G-01": {"min_bets": 150, "min_seasons": 4},
    "G-02": {"confidence": 0.90},
    "G-03": {"min_share_beat_close": 0.55},
    "G-04": {"min_dsr": 0.95},
    "G-05": {"max_free_params": 3},
    "G-06": {"min_folds_agreeing": 3, "n_folds": 4},
    "G-07": {"vig_multiplier": 1.5, "slippage_prob": 0.02},
    "G-08": {"recent_weeks": 8, "percentile": 10},
    "G-09": {"max_p_null": 0.05, "block_size": 1, "resamples": 4000, "seed": 20261114},
    "G-10": {"min_bets_per_week": 20, "capacity_multiple": 20},
    "G-11": {"max_kelly_fraction": 0.25, "max_cluster_units": 2.0, "max_dd_prob": 0.10,
             "dd_units": 20.0},
    "G-13": {"max_feature_age_hours": 24},
    "G-15": {"max_sign_flip_share": 0.25},
    "G-16": {"max_bets_per_cluster": 1},
}

# break-even for a -110 priced bet, used as the default hurdle in the self-test report
DEFAULT_ODDS_LINE = -110
