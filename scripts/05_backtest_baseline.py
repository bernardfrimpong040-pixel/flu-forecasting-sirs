"""
05_backtest_baseline.py - test the baseline on last season (2025-2026).

We pretend to stand on each Saturday of last season, make the forecast using
only data available before that week, and compare it with what really happened.
This tells us how good (and how honest) the baseline is before we rely on it.

Two scores, both standard in FluSight:

1. WIS (weighted interval score) - lower is better. It rewards a forecast for
   being close to the truth AND for having a range that is no wider than needed.
   For a set of quantiles it equals 2 / (number of quantiles) times the sum of
   the "pinball losses":
        pinball(q) = (1 if truth < x_q else 0  -  q) * (x_q - truth)
   where x_q is the forecast at level q. A forecast that is wrong but admits a
   wide range is punished less than one that is wrong and over-confident.

2. Coverage - how often the truth fell inside the 50% and 95% ranges.
   An honest forecast covers about 50% and 95% of the time. Much lower means
   over-confident; much higher means the ranges are wider than they need to be.

Caveat: the backtest uses today's (revised) data, not the data as it looked at
the time. Live forecasts face early, incomplete numbers, so real scores will be
a little worse. That is why 01_download_data.py keeps dated snapshots.

Writes: results/backtest_scores.csv, results/backtest_summary.csv,
        results/03_backtest_us_forecasts.png
"""

from datetime import date, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import baseline_model
import common

FIRST_REFERENCE = date(2025, 10, 11)    # first Saturday tested
LAST_REFERENCE = date(2026, 5, 30)      # last Saturday tested


def weighted_interval_score(quantile_levels, quantile_values, truth):
    """WIS for one forecast (23 quantiles) against one true value."""
    q = np.asarray(quantile_levels)
    x = np.asarray(quantile_values)
    pinball = ((truth < x).astype(float) - q) * (x - truth)
    return 2 * pinball.sum() / len(q)


def main():
    common.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    data = common.load_target_data()
    locations = common.load_locations()["location"].tolist()

    # 1. Make a forecast for every Saturday of last season.
    forecasts = []
    reference = FIRST_REFERENCE
    while reference <= LAST_REFERENCE:
        forecasts.append(baseline_model.make_forecast(data, reference, locations))
        reference += timedelta(weeks=1)
    forecasts = pd.concat(forecasts, ignore_index=True)
    print(f"Forecasts made: {forecasts['reference_date'].nunique()} weeks x "
          f"{forecasts['location'].nunique()} locations")

    # 2. Attach the true value for each target week.
    truth = data[["date", "location", "value"]].rename(
        columns={"date": "target_end_date", "value": "truth"})
    truth["target_end_date"] = truth["target_end_date"].dt.strftime("%Y-%m-%d")
    merged = forecasts.merge(truth, on=["location", "target_end_date"], how="inner")

    # 3. Score each forecast (one location, one reference date, one horizon).
    scores = []
    for (ref, loc, h), group in merged.groupby(["reference_date", "location", "horizon"]):
        group = group.sort_values("output_type_id")
        q = group.set_index("output_type_id")["value"]
        y = group["truth"].iloc[0]
        scores.append({
            "reference_date": ref, "location": loc, "horizon": h, "truth": y,
            "median": q[0.5],
            "wis": weighted_interval_score(q.index, q.values, y),
            "in_50": q[0.25] <= y <= q[0.75],
            "in_95": q[0.025] <= y <= q[0.975],
        })
    scores = pd.DataFrame(scores)
    scores.to_csv(common.RESULTS_DIR / "backtest_scores.csv", index=False)

    # 4. Summaries: national, and all states together, by horizon.
    scores["level"] = np.where(scores["location"] == "US", "US national", "States (average)")
    summary = scores.groupby(["level", "horizon"]).agg(
        mean_wis=("wis", "mean"),
        coverage_50=("in_50", "mean"),
        coverage_95=("in_95", "mean"),
        forecasts=("wis", "size")).reset_index()
    summary.to_csv(common.RESULTS_DIR / "backtest_summary.csv", index=False)
    print("\nBaseline backtest, 2025-2026 season (aim: coverage near 0.50 and 0.95):")
    print(summary.round({"mean_wis": 1, "coverage_50": 2, "coverage_95": 2}).to_string(index=False))

    # 5. Picture: national forecasts made 2 weeks ahead of the last data (horizon 1).
    us = merged[(merged["location"] == "US") & (merged["horizon"] == 1)]
    wide = us.pivot(index="target_end_date", columns="output_type_id", values="value")
    wide.index = pd.to_datetime(wide.index)
    actual = data[(data["location"] == "US") & (data["date"] >= wide.index.min())
                  & (data["date"] <= wide.index.max())]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.fill_between(wide.index, wide[0.025], wide[0.975], color="#c9d8f0", label="95% range")
    ax.fill_between(wide.index, wide[0.25], wide[0.75], color="#8fb0e3", label="50% range")
    ax.plot(wide.index, wide[0.5], color="#1f5fbf", linewidth=2, label="Forecast median")
    ax.plot(actual["date"], actual["value"], color="#1a1a1a", linewidth=1.5,
            marker="o", markersize=3, label="What happened")
    ax.set_title("Baseline backtest: US forecasts made 2 weeks ahead, 2025-2026 season")
    ax.set_ylabel("Admissions per week")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(axis="y", color="#e6e6e6")
    ax.spines[["top", "right"]].set_visible(False)
    fig.autofmt_xdate()
    fig.tight_layout()
    path = common.RESULTS_DIR / "03_backtest_us_forecasts.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nSaved: {path.relative_to(common.REPO_DIR)}")


if __name__ == "__main__":
    main()
