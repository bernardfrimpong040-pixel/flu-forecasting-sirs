"""
07_backtest_compare.py - compare the Stage 2 trend model with the baseline.

THE FAIR-TEST RULE
------------------
A model's settings must be chosen WITHOUT looking at the season used to test it.
So:
  * tuning seasons: 2023-24 and 2024-25  -> pick WINDOW and PHI
  * test season:    2025-26              -> score the picked settings once

Usage:
    python scripts/07_backtest_compare.py          # the test (about 1 minute)
    python scripts/07_backtest_compare.py --tune   # also redo the tuning grid (several minutes)

Main score: RELATIVE WIS = WIS(trend) / WIS(baseline) on exactly the same
forecasts. Below 1 means the trend model is better; 0.90 means 10% better.

Writes to results/:
  compare_summary.csv     relative WIS and coverage by level and horizon
  compare_by_phase.csv    relative WIS in the growth, peak and decline phases
  tuning_grid.csv         (with --tune) every setting tried in every season
  04_compare_us_forecasts.png
"""

import argparse
from datetime import date, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import baseline_model
import common
import scoring
import trend_model

SEASONS = {
    "2023-24": (date(2023, 10, 14), date(2024, 6, 1)),
    "2024-25": (date(2024, 10, 12), date(2025, 5, 31)),
    "2025-26": (date(2025, 10, 11), date(2026, 5, 30)),
}
TUNING_SEASONS = ["2023-24", "2024-25"]
TEST_SEASON = "2025-26"
TEST_WINDOW, TEST_PHI = 3, 0.5          # chosen on the tuning seasons only (see --tune)
GRID_WINDOWS = [3, 4]
GRID_PHIS = [0.3, 0.4, 0.5, 0.6]


def backtest(model, data, locations, season, **settings):
    """Forecast every Saturday of a season and score the forecasts."""
    start, end = SEASONS[season]
    forecasts, reference = [], start
    while reference <= end:
        forecasts.append(model.make_forecast(data, reference, locations, **settings))
        reference += timedelta(weeks=1)
    return scoring.score_forecasts(pd.concat(forecasts, ignore_index=True), data)


def paired(trend_scores, base_scores):
    """Put the two models' scores side by side, on exactly the same forecasts."""
    return trend_scores.merge(base_scores, on=["reference_date", "location", "horizon"],
                              suffixes=("_trend", "_base"))


def relative_wis(rows):
    return rows["wis_trend"].mean() / rows["wis_base"].mean()


def add_phase(scores, data, season):
    """Label each target week as growth, peak or decline, using that location's own peak.

    'peak' = within 2 weeks of the location's highest week of the season;
    'growth' = earlier than that; 'decline' = later.
    """
    start, end = SEASONS[season]
    in_season = data[(data["date"] >= pd.Timestamp(start)) & (data["date"] <= pd.Timestamp(end))]
    peaks = in_season.loc[in_season.groupby("location")["value"].idxmax(), ["location", "date"]]
    peaks = peaks.rename(columns={"date": "peak_date"})

    scores = scores.merge(peaks, on="location")
    target = pd.to_datetime(scores["reference_date"]) + pd.to_timedelta(scores["horizon"] * 7, unit="D")
    days_from_peak = (target - scores["peak_date"]).dt.days
    scores["phase"] = np.select([days_from_peak < -14, days_from_peak > 14],
                                ["1 growth", "3 decline"], default="2 peak (+/- 2 wks)")
    return scores


def run_tuning(data, locations):
    print("Tuning grid (relative WIS vs baseline; lower is better). This takes a few minutes ...")
    base = {s: backtest(baseline_model, data, locations, s) for s in SEASONS}
    rows = []
    for window in GRID_WINDOWS:
        for phi in GRID_PHIS:
            row = {"window": window, "phi": phi}
            for season in SEASONS:
                trend = backtest(trend_model, data, locations, season, window=window, phi=phi)
                row[season] = round(relative_wis(paired(trend, base[season])), 3)
            row["tuning_mean"] = round(np.mean([row[s] for s in TUNING_SEASONS]), 3)
            row["all_three_mean"] = round(np.mean([row[s] for s in SEASONS]), 3)
            rows.append(row)
            print(f"  window={window} phi={phi}:  2023-24 {row['2023-24']:.3f}  "
                  f"2024-25 {row['2024-25']:.3f}  2025-26 {row['2025-26']:.3f}  "
                  f"tuning mean {row['tuning_mean']:.3f}  all-three mean {row['all_three_mean']:.3f}")
    grid = pd.DataFrame(rows)
    grid.to_csv(common.RESULTS_DIR / "tuning_grid.csv", index=False)
    best_test = grid.loc[grid["tuning_mean"].idxmin()]
    best_live = grid.loc[grid["all_three_mean"].idxmin()]
    print(f"\nBest on 2023-24 + 2024-25 (used for the 2025-26 test): "
          f"window={int(best_test['window'])}, phi={best_test['phi']}")
    print(f"Best on all three seasons (used for live 2026-27 forecasts): "
          f"window={int(best_live['window'])}, phi={best_live['phi']}\n")


def plot_us(pairs, data):
    """Two panels: baseline vs trend, US forecasts made 2 weeks after the last data."""
    us = pairs[(pairs["location"] == "US") & (pairs["horizon"] == 1)].copy()
    us["target"] = pd.to_datetime(us["reference_date"]) + pd.Timedelta(days=7)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    for ax, name, label in [(axes[0], "base", "Stage 1 baseline"), (axes[1], "trend", "Stage 2 trend")]:
        ax.plot(us["target"], us["truth_base"], color="#1a1a1a", linewidth=1.5,
                marker="o", markersize=3, label="What happened")
        ax.plot(us["target"], us[f"median_{name}"], color="#1f5fbf", linewidth=2,
                label="Forecast median")
        rel = us[f"wis_{name}"].mean() / us["wis_base"].mean()
        ax.set_title(f"{label}  (relative WIS {rel:.2f})", fontsize=11)
        ax.grid(axis="y", color="#e6e6e6")
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", rotation=30)
    axes[0].set_ylabel("Admissions per week")
    axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("US forecasts made 2 weeks after the last data (horizon 1), 2025-26 test season")
    fig.tight_layout()
    path = common.RESULTS_DIR / "04_compare_us_forecasts.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tune", action="store_true", help="also redo the tuning grid")
    args = parser.parse_args()

    common.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    data = common.load_target_data()
    locations = common.load_locations()["location"].tolist()

    if args.tune:
        run_tuning(data, locations)

    # The test: 2025-26, settings chosen on earlier seasons.
    print(f"Test season {TEST_SEASON}: trend (window={TEST_WINDOW}, phi={TEST_PHI}) vs baseline")
    base = backtest(baseline_model, data, locations, TEST_SEASON)
    trend = backtest(trend_model, data, locations, TEST_SEASON, window=TEST_WINDOW, phi=TEST_PHI)
    pairs = paired(trend, base)
    pairs["level"] = np.where(pairs["location"] == "US", "US national", "States")

    summary = pairs.groupby(["level", "horizon"]).apply(lambda g: pd.Series({
        "wis_baseline": g["wis_base"].mean(),
        "wis_trend": g["wis_trend"].mean(),
        "relative_wis": relative_wis(g),
        "cov50_baseline": g["in_50_base"].mean(), "cov50_trend": g["in_50_trend"].mean(),
        "cov95_baseline": g["in_95_base"].mean(), "cov95_trend": g["in_95_trend"].mean(),
    }), include_groups=False).reset_index()
    summary.to_csv(common.RESULTS_DIR / "compare_summary.csv", index=False)
    print(summary.round(3).to_string(index=False))
    print(f"\nOverall relative WIS: {relative_wis(pairs):.3f}   "
          f"(states {relative_wis(pairs[pairs['level'] == 'States']):.3f}, "
          f"US {relative_wis(pairs[pairs['level'] == 'US national']):.3f})")

    # Where does the trend help or hurt? Split by epidemic phase.
    phased = add_phase(pairs, data, TEST_SEASON)
    by_phase = phased.groupby("phase").apply(lambda g: pd.Series({
        "forecasts": len(g),
        "relative_wis": relative_wis(g),
        "median_bias_baseline": (g["median_base"] - g["truth_base"]).mean(),
        "median_bias_trend": (g["median_trend"] - g["truth_base"]).mean(),
    }), include_groups=False).reset_index()
    by_phase.to_csv(common.RESULTS_DIR / "compare_by_phase.csv", index=False)
    print("\nBy epidemic phase (bias = average forecast median minus truth; negative = too low):")
    print(by_phase.round(3).to_string(index=False))

    print(f"\nSaved: {plot_us(pairs, data).relative_to(common.REPO_DIR)}")


if __name__ == "__main__":
    main()
