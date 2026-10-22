"""
scoring.py - shared scoring tools (WIS and interval coverage) for comparing models.

Same formulas as 05_backtest_baseline.py, kept in one importable place so every
later stage scores its forecasts in exactly the same way.
"""

import numpy as np
import pandas as pd


def weighted_interval_score(quantile_levels, quantile_values, truth):
    """WIS for one forecast (23 quantiles) against one true value. Lower is better.

    WIS = 2 / (number of quantiles) * sum over levels q of
          (1 if truth < x_q else 0  -  q) * (x_q - truth)
    """
    q = np.asarray(quantile_levels)
    x = np.asarray(quantile_values)
    pinball = ((truth < x).astype(float) - q) * (x - truth)
    return 2 * pinball.sum() / len(q)


def score_forecasts(forecasts, data):
    """Score a table of forecasts against the observed data.

    Returns one row per (reference_date, location, horizon) with the truth,
    the forecast median, WIS, and whether the truth fell in the 50% / 95% ranges.
    """
    truth = data[["date", "location", "value"]].rename(
        columns={"date": "target_end_date", "value": "truth"})
    truth["target_end_date"] = truth["target_end_date"].dt.strftime("%Y-%m-%d")
    merged = forecasts.merge(truth, on=["location", "target_end_date"], how="inner")

    rows = []
    for (ref, loc, h), group in merged.groupby(["reference_date", "location", "horizon"]):
        q = group.sort_values("output_type_id").set_index("output_type_id")["value"]
        y = group["truth"].iloc[0]
        rows.append({
            "reference_date": ref, "location": loc, "horizon": h, "truth": y,
            "median": q[0.5],
            "wis": weighted_interval_score(q.index, q.values, y),
            "in_50": q[0.25] <= y <= q[0.75],
            "in_95": q[0.025] <= y <= q[0.975],
        })
    return pd.DataFrame(rows)
