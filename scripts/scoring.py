"""
scoring.py - shared scoring tools (WIS and interval coverage) for comparing models.

Same formulas as 05_backtest_baseline.py, kept in one importable place so every
later stage scores its forecasts in exactly the same way.
"""

from datetime import date, timedelta

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


# ---------------------------------------------------------------------------
# Backtest helpers shared from Stage 3 on (07_backtest_compare.py keeps its own copy).
# ---------------------------------------------------------------------------

SEASONS = {
    "2023-24": (date(2023, 10, 14), date(2024, 6, 1)),
    "2024-25": (date(2024, 10, 12), date(2025, 5, 31)),
    "2025-26": (date(2025, 10, 11), date(2026, 5, 30)),
}


def backtest(model, data, locations, season, **settings):
    """Forecast every Saturday of a season with `model` and score the forecasts."""
    start, end = SEASONS[season]
    forecasts, reference = [], start
    while reference <= end:
        forecasts.append(model.make_forecast(data, reference, locations, **settings))
        reference += timedelta(weeks=1)
    return score_forecasts(pd.concat(forecasts, ignore_index=True), data)


def relative_wis(model_scores, base_scores):
    """Mean WIS of a model divided by mean WIS of the baseline, on the SAME forecasts."""
    keys = ["reference_date", "location", "horizon"]
    both = model_scores.merge(base_scores, on=keys, suffixes=("", "_base"))
    return both["wis"].mean() / both["wis_base"].mean()


def add_phase(scores, data, season):
    """Label each target week 'growth', 'peak' or 'decline' using its location's own peak.

    'peak' = within 2 weeks of the location's highest week of the season;
    'growth' = earlier; 'decline' = later.
    """
    start, end = SEASONS[season]
    in_season = data[(data["date"] >= pd.Timestamp(start)) & (data["date"] <= pd.Timestamp(end))]
    peaks = in_season.loc[in_season.groupby("location")["value"].idxmax(), ["location", "date"]]
    scores = scores.merge(peaks.rename(columns={"date": "peak_date"}), on="location")
    target = pd.to_datetime(scores["reference_date"]) + pd.to_timedelta(scores["horizon"] * 7, unit="D")
    days_from_peak = (target - scores["peak_date"]).dt.days
    scores["phase"] = np.select([days_from_peak < -14, days_from_peak > 14],
                                ["1 growth", "3 decline"], default="2 peak (+/- 2 wks)")
    return scores
