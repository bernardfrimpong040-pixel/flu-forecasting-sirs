"""
trend_model.py - the Stage 2 "damped growth" forecast.

THE IDEA IN PLAIN WORDS
-----------------------
The baseline assumed next week looks like this week. This model asks instead:
"how fast is it growing (or shrinking) right now?" and carries that forward.

1. Work on the log scale, z = log(admissions + 1), so steady growth is a straight
   line. (If admissions grow 25% a week, z goes up by log(1.25) = 0.22 every week.)

2. The current growth rate r is the slope of the best straight line through the
   last WINDOW weeks of z (ordinary least squares, like a trendline in Excel).
   For WINDOW = 3 the weeks sit at x = -1, 0, 1 and the slope is
        r = (z_newest - z_oldest) / 2.

3. Carry the growth forward, but DAMPED: each week ahead keeps only a fraction
   PHI of the previous week's growth, because epidemics slow down rather than
   grow forever. The median k weeks after the last data point is
        z_hat(k) = z_last + r * (PHI + PHI^2 + ... + PHI^k).
   PHI = 0 gives back the baseline; PHI = 1 is undamped straight-line growth.

4. The range around the median is built exactly like the baseline's (symmetric
   in-season weekly changes, widened by sqrt(k)). Only the centre moves. That
   way, any difference in score between the two models comes from the trend alone.

HOW WINDOW AND PHI WERE CHOSEN (see 07_backtest_compare.py)
- For the 2025-26 test, they were picked on the 2023-24 and 2024-25 seasons only:
  WINDOW = 3, PHI = 0.5.
- For live 2026-27 forecasts, the same rule is applied to all three past seasons
  (2023-24, 2024-25, 2025-26), which gives WINDOW = 3, PHI = 0.4 (the values below).
"""

from datetime import timedelta

import numpy as np
import pandas as pd

import baseline_model          # re-use the baseline's spread calculation
import common

WINDOW = 3          # weeks used to measure the current growth rate
PHI = 0.4           # damping: fraction of growth kept for each extra week ahead
MAX_STEPS = 4       # forecasts are 1 to 4 weeks after the last data point


def growth_rate(location_rows, window):
    """Least-squares slope of log(admissions + 1) over the last `window` weeks.

    Returns 0 (no trend) if any of those weeks is missing, because a slope over
    a gap would mix two different moments of the season.
    """
    recent = location_rows.sort_values("date").tail(window)
    days_apart = recent["date"].diff().dt.days.dropna()
    if len(recent) < window or (days_apart != 7).any():
        return 0.0
    z = np.log(recent["value"].to_numpy() + 1)
    x = np.arange(window) - (window - 1) / 2        # centred positions, e.g. -1, 0, 1
    return float(np.sum(x * z) / np.sum(x ** 2))    # least-squares slope


def forecast_one_location(location_rows, reference_date, window=WINDOW, phi=PHI):
    """Quantile forecasts for one location. Returns a list of row dictionaries."""
    rows_sorted = location_rows.sort_values("date")
    last = rows_sorted.iloc[-1]
    last_date = last["date"].date()
    z_last = np.log(last["value"] + 1)

    # The trend: current growth rate, damped for each week ahead.
    rate = growth_rate(rows_sorted, window)
    weeks_needed = max(MAX_STEPS, (reference_date + timedelta(weeks=max(common.HORIZONS)) - last_date).days // 7)
    damping = np.cumsum([phi ** j for j in range(1, weeks_needed + 1)])  # PHI, PHI+PHI^2, ...

    # The spread: exactly the baseline's (symmetric in-season weekly changes).
    recent = rows_sorted[rows_sorted["date"] > last["date"] - timedelta(weeks=baseline_model.HISTORY_WEEKS)]
    changes = baseline_model.log_changes(recent)
    one_week_quantiles = np.quantile(np.concatenate([changes, -changes]), common.QUANTILE_LEVELS)

    rows = []
    for horizon in common.HORIZONS:
        target_end_date = reference_date + timedelta(weeks=horizon)
        steps = (target_end_date - last_date).days // 7            # 1 to 4 normally
        trend = rate * damping[steps - 1]                          # how far the centre moves
        values = np.exp(z_last + trend + np.sqrt(steps) * one_week_quantiles) - 1
        values = np.maximum(np.round(values), 0)                   # whole numbers, never negative
        values = np.maximum.accumulate(values)                     # quantiles never decrease

        for level, value in zip(common.QUANTILE_LEVELS, values):
            rows.append({
                "reference_date": reference_date.isoformat(),
                "target": common.TARGET,
                "horizon": horizon,
                "target_end_date": target_end_date.isoformat(),
                "location": location_rows["location"].iloc[0],
                "output_type": "quantile",
                "output_type_id": level,
                "value": int(value),
            })
    return rows


def make_forecast(data, reference_date, locations, window=WINDOW, phi=PHI):
    """Forecasts for every location, using only data dated before the reference week
    (the same rule as the baseline, so backtests never see the weeks they predict)."""
    cutoff = pd.Timestamp(reference_date - timedelta(weeks=1))
    usable = data[data["date"] <= cutoff]

    all_rows = []
    for location in locations:
        location_rows = usable[usable["location"] == location]
        if len(location_rows) < 10:          # too little history: skip this location
            continue
        all_rows.extend(forecast_one_location(location_rows, reference_date, window, phi))
    return pd.DataFrame(all_rows)
