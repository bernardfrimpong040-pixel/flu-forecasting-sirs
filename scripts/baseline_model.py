"""
baseline_model.py - the Stage 1 "flat" baseline forecast.

THE IDEA IN PLAIN WORDS
-----------------------
Our best guess (the median) for every future week is simply the last value we
observed: "next week looks like this week". The skill is in the RANGE around
that guess. We learn the range from history:

1. Take the log of admissions, log(value + 1). On the log scale, a jump from
   100 to 120 and a jump from 1,000 to 1,200 are the same size (both +20%),
   which is how epidemics behave. The "+1" avoids log(0) for weeks with zero.
2. Collect every past week-to-week change on that log scale (in-season weeks,
   October to May, over the last three years). Also include each change with
   its sign flipped, so ups and downs are treated equally and the median stays
   at the last observed value.
3. For a forecast k weeks ahead, the spread grows like sqrt(k). This is the
   random-walk rule: if each week adds an independent random change, the
   variance after k weeks is k times bigger, so the standard deviation is
   sqrt(k) times bigger.
4. The q-th quantile of the forecast is then
        exp( log(last + 1) + sqrt(k) * (q-th quantile of the changes) ) - 1,
   rounded to a whole number and never below zero.

This is deliberately simple. It is the yardstick every later model (regression,
SIRS) must beat, and the paper will report every model relative to it.

Both 03_baseline_forecast.py (live forecasts) and 05_backtest_baseline.py
(scoring on last season) use the functions below, so the model lives in one place.
"""

from datetime import timedelta

import numpy as np
import pandas as pd

import common

HISTORY_WEEKS = 156              # look back about three years for week-to-week changes
SEASON_MONTHS = [10, 11, 12, 1, 2, 3, 4, 5]   # October to May: the forecasting season


def log_changes(location_rows):
    """Week-to-week changes of log(value + 1) for one location.

    Only pairs of weeks exactly 7 days apart are used, so a gap in reporting
    never gets counted as a single week's change.
    """
    rows = location_rows.sort_values("date")
    log_values = np.log(rows["value"].to_numpy() + 1)
    dates = rows["date"].to_numpy()

    changes = np.diff(log_values)                                 # this week minus last week
    days_apart = np.diff(dates).astype("timedelta64[D]").astype(int)
    in_season = rows["date"].dt.month.isin(SEASON_MONTHS).to_numpy()[1:]

    keep = (days_apart == 7) & in_season
    return changes[keep]


def forecast_one_location(location_rows, reference_date):
    """Quantile forecasts for one location. Returns a list of row dictionaries."""
    last = location_rows.sort_values("date").iloc[-1]
    last_date = last["date"].date()
    last_value = last["value"]

    # Changes from the recent history only (the last HISTORY_WEEKS weeks).
    recent = location_rows[location_rows["date"] > last["date"] - timedelta(weeks=HISTORY_WEEKS)]
    changes = log_changes(recent)
    symmetric = np.concatenate([changes, -changes])      # treat rises and falls the same

    # The quantiles of one week's change, one number per quantile level.
    one_week_quantiles = np.quantile(symmetric, common.QUANTILE_LEVELS)

    rows = []
    for horizon in common.HORIZONS:
        target_end_date = reference_date + timedelta(weeks=horizon)
        # How many weeks after our last data point is the target week?
        steps = (target_end_date - last_date).days // 7
        spread = np.sqrt(steps) * one_week_quantiles
        values = np.exp(np.log(last_value + 1) + spread) - 1
        values = np.maximum(np.round(values), 0)          # whole numbers, never negative
        values = np.maximum.accumulate(values)            # quantiles must never decrease

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


def make_forecast(data, reference_date, locations):
    """Forecasts for every location, using only data dated before the reference week.

    The hub's newest data on a Wednesday ends one week before the reference date
    (horizon -1). Cutting the data there also makes backtests honest: the model
    never sees the weeks it is predicting.
    """
    cutoff = pd.Timestamp(reference_date - timedelta(weeks=1))
    usable = data[data["date"] <= cutoff]

    all_rows = []
    for location in locations:
        location_rows = usable[usable["location"] == location]
        if len(location_rows) < 10:          # too little history: skip this location
            continue
        all_rows.extend(forecast_one_location(location_rows, reference_date))
    return pd.DataFrame(all_rows)
