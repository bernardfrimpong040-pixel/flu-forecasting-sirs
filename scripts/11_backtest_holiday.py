"""
11_backtest_holiday.py - test the Stage 4 holiday SIRS model against Stages 1-3.

Same fair-test rule as before:
  * tuning seasons: 2023-24 and 2024-25 -> pick KAPPA and HOLIDAY_FACTOR together
  * test season:    2025-26             -> score the picked pair once

Usage:
    python scripts/11_backtest_holiday.py          # the test (about 3 minutes)
    python scripts/11_backtest_holiday.py --tune   # also redo the grid (about 20 minutes)

Writes to results/:
  holiday_summary.csv         relative WIS by level and horizon, all models
  holiday_by_phase.csv        relative WIS and bias in growth, peak and decline
  peak_calendar.csv           for each season, the week most states peaked
  tuning_grid_holiday.csv     (with --tune) every pair in every season
  07_holiday_us_forecasts.png
  08_peak_weeks.png
"""

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import baseline_model
import common
import holiday_sirs_model
import scoring
import sirs_model
import trend_model

TEST_SEASON = "2025-26"
TUNING_SEASONS = ["2023-24", "2024-25"]
TEST_KAPPA, TEST_FACTOR = 0.3, 0.8        # chosen on the tuning seasons only (see --tune)
STAGE2_TEST = {"window": 3, "phi": 0.5}
STAGE3_TEST = {"kappa": 0.3}
GRID_KAPPAS = [0.3, 0.4, 0.5]
GRID_FACTORS = [0.6, 0.7, 0.8, 1.0]       # 1.0 = no holiday effect (the Stage 3 model)


def peak_calendar(data):
    """For each season: the week in which the most states reached their peak."""
    states = data[data["location"] != "US"].copy()
    start_year = states["date"].dt.year.where(states["date"].dt.month >= 8, states["date"].dt.year - 1)
    states["season"] = start_year.astype(str) + "-" + (start_year + 1).astype(str).str[-2:]
    rows = []
    for season, group in states[start_year.between(2022, 2025)].groupby("season"):
        peaks = group.loc[group.groupby("location")["value"].idxmax(), "date"]
        counts = peaks.value_counts()
        rows.append({"season": season, "most_common_peak_week": counts.index[0].date(),
                     "states_peaking_that_week": int(counts.iloc[0]),
                     "states_total": int(len(peaks))})
    return pd.DataFrame(rows)


def plot_peak_weeks(data):
    """How many states peaked in each week, by season, with the school breaks shaded."""
    states = data[data["location"] != "US"].copy()
    start_year = states["date"].dt.year.where(states["date"].dt.month >= 8, states["date"].dt.year - 1)
    fig, axes = plt.subplots(4, 1, figsize=(9, 9), sharex=True)
    for ax, year in zip(axes, [2022, 2023, 2024, 2025]):
        group = states[start_year == year]
        peaks = group.loc[group.groupby("location")["value"].idxmax(), "date"]
        # Position of each week = days since November 1 of that season.
        origin = pd.Timestamp(year=year, month=11, day=1)
        counts = ((peaks - origin).dt.days).value_counts().sort_index()
        thanksgiving = holiday_sirs_model.thanksgiving_day(year)
        for first, last in [(thanksgiving - pd.Timedelta(days=1), thanksgiving + pd.Timedelta(days=3)),
                            (pd.Timestamp(year=year, month=12, day=21), pd.Timestamp(year=year + 1, month=1, day=3))]:
            ax.axvspan((first - origin).days, (last - origin).days + 1, color="#f2e6c9", zorder=0)
        ax.bar(counts.index, counts.values, width=5, color="#1f5fbf")
        ax.set_ylabel("States", fontsize=9)
        ax.set_title(f"{year}-{str(year + 1)[-2:]} season: week in which each state peaked", fontsize=10, loc="left")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#e6e6e6")
    ticks = [0, 30, 61, 92, 120, 151]
    axes[-1].set_xticks(ticks, ["Nov 1", "Dec 1", "Jan 1", "Feb 1", "Mar 1", "Apr 1"])
    axes[-1].set_xlim(-5, 160)
    fig.suptitle("State peak weeks cluster just after school breaks (shaded: Thanksgiving and winter break)")
    fig.tight_layout()
    path = common.RESULTS_DIR / "08_peak_weeks.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def run_tuning(data, locations):
    print("Grid of (KAPPA, HOLIDAY_FACTOR), relative WIS vs baseline. This takes about 20 minutes ...")
    base = {s: scoring.backtest(baseline_model, data, locations, s) for s in scoring.SEASONS}
    rows = []
    for kappa in GRID_KAPPAS:
        for factor in GRID_FACTORS:
            row = {"kappa": kappa, "holiday_factor": factor}
            for season in scoring.SEASONS:
                sc = scoring.backtest(holiday_sirs_model, data, locations, season,
                                      kappa=kappa, factor=factor)
                row[season] = round(scoring.relative_wis(sc, base[season]), 3)
            row["tuning_mean"] = round(np.mean([row[s] for s in TUNING_SEASONS]), 3)
            row["all_three_mean"] = round(np.mean([row[s] for s in scoring.SEASONS]), 3)
            rows.append(row)
            print(f"  kappa={kappa} factor={factor}:  2023-24 {row['2023-24']:.3f}  "
                  f"2024-25 {row['2024-25']:.3f}  2025-26 {row['2025-26']:.3f}  "
                  f"tuning mean {row['tuning_mean']:.3f}  all-three mean {row['all_three_mean']:.3f}",
                  flush=True)
    grid = pd.DataFrame(rows)
    grid.to_csv(common.RESULTS_DIR / "tuning_grid_holiday.csv", index=False)
    best_test = grid.loc[grid["tuning_mean"].idxmin()]
    best_live = grid.loc[grid["all_three_mean"].idxmin()]
    print(f"\nBest on 2023-24 + 2024-25 (used for the 2025-26 test): "
          f"kappa={best_test['kappa']}, factor={best_test['holiday_factor']}")
    print(f"Best on all three seasons (used for live 2026-27 forecasts): "
          f"kappa={best_live['kappa']}, factor={best_live['holiday_factor']}\n")


def plot_us(scores):
    """Four panels: US forecasts made 2 weeks after the last data, by model."""
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.6), sharey=True)
    base = scores["Stage 1 baseline"]
    for ax, (name, sc) in zip(axes, scores.items()):
        us = sc[(sc["location"] == "US") & (sc["horizon"] == 1)].copy()
        us["target"] = pd.to_datetime(us["reference_date"]) + pd.Timedelta(days=7)
        for start, end in [("2025-11-26", "2025-11-30"), ("2025-12-21", "2026-01-03")]:
            # shade the admission weeks affected by the breaks (one-week lag)
            ax.axvspan(pd.Timestamp(start) + pd.Timedelta(days=7), pd.Timestamp(end) + pd.Timedelta(days=7),
                       color="#f2e6c9", zorder=0)
        ax.plot(us["target"], us["truth"], color="#1a1a1a", linewidth=1.5, marker="o",
                markersize=3, label="What happened")
        ax.plot(us["target"], us["median"], color="#1f5fbf", linewidth=2, label="Forecast median")
        rel = scoring.relative_wis(sc[sc["location"] == "US"], base[base["location"] == "US"])
        ax.set_title(f"{name}  (US rel. WIS {rel:.2f})", fontsize=10)
        ax.grid(axis="y", color="#e6e6e6")
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", rotation=30)
    axes[0].set_ylabel("Admissions per week")
    axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("US forecasts made 2 weeks after the last data (horizon 1), 2025-26 test season "
                 "(shaded: school breaks, shifted by the 1-week admission lag)")
    fig.tight_layout()
    path = common.RESULTS_DIR / "07_holiday_us_forecasts.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tune", action="store_true", help="also redo the grid")
    args = parser.parse_args()

    common.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    data = common.load_target_data()
    locations = common.load_locations()["location"].tolist()

    calendar = peak_calendar(data)
    calendar.to_csv(common.RESULTS_DIR / "peak_calendar.csv", index=False)
    print("Week in which the most states peaked, by season:")
    print(calendar.to_string(index=False))
    print(f"Saved: {plot_peak_weeks(data).relative_to(common.REPO_DIR)}\n")

    if args.tune:
        run_tuning(data, locations)

    print(f"Test season {TEST_SEASON}: holiday SIRS (kappa={TEST_KAPPA}, factor={TEST_FACTOR})")
    scores = {
        "Stage 1 baseline": scoring.backtest(baseline_model, data, locations, TEST_SEASON),
        "Stage 2 trend": scoring.backtest(trend_model, data, locations, TEST_SEASON, **STAGE2_TEST),
        "Stage 3 SIRS": scoring.backtest(sirs_model, data, locations, TEST_SEASON, **STAGE3_TEST),
        "Stage 4 holiday SIRS": scoring.backtest(holiday_sirs_model, data, locations, TEST_SEASON,
                                                 kappa=TEST_KAPPA, factor=TEST_FACTOR),
    }
    base = scores["Stage 1 baseline"]
    others = ["Stage 2 trend", "Stage 3 SIRS", "Stage 4 holiday SIRS"]

    rows = []
    for level, keep in [("States", lambda s: s[s["location"] != "US"]),
                        ("US national", lambda s: s[s["location"] == "US"])]:
        for h in common.HORIZONS:
            pick = lambda s: keep(s)[keep(s)["horizon"] == h]
            row = {"level": level, "horizon": h}
            for name in others:
                row[name] = scoring.relative_wis(pick(scores[name]), pick(base))
            row["cov95 Stage 4"] = pick(scores["Stage 4 holiday SIRS"])["in_95"].mean()
            rows.append(row)
    summary = pd.DataFrame(rows)
    summary.to_csv(common.RESULTS_DIR / "holiday_summary.csv", index=False)
    print(summary.round(3).to_string(index=False))
    print("\nOverall relative WIS vs baseline:  " + "   ".join(
        f"{name.split(' ', 2)[2]} {scoring.relative_wis(scores[name], base):.3f}" for name in others))

    # By epidemic phase, all models side by side.
    keys = ["reference_date", "location", "horizon"]
    merged = base.rename(columns={"wis": "wis_base", "median": "median_base"})
    for name, tag in zip(others, ["trend", "sirs", "holiday"]):
        merged = merged.merge(scores[name][keys + ["wis", "median"]].rename(
            columns={"wis": f"wis_{tag}", "median": f"median_{tag}"}), on=keys)
    phased = scoring.add_phase(merged, data, TEST_SEASON)
    by_phase = phased.groupby("phase").apply(lambda g: pd.Series({
        "forecasts": len(g),
        "trend": g["wis_trend"].mean() / g["wis_base"].mean(),
        "sirs": g["wis_sirs"].mean() / g["wis_base"].mean(),
        "holiday": g["wis_holiday"].mean() / g["wis_base"].mean(),
        "bias_base": (g["median_base"] - g["truth"]).mean(),
        "bias_sirs": (g["median_sirs"] - g["truth"]).mean(),
        "bias_holiday": (g["median_holiday"] - g["truth"]).mean(),
    }), include_groups=False).reset_index()
    by_phase.to_csv(common.RESULTS_DIR / "holiday_by_phase.csv", index=False)
    print("\nBy epidemic phase (relative WIS vs baseline; bias = median minus truth):")
    print(by_phase.round(3).to_string(index=False))

    print(f"\nSaved: {plot_us(scores).relative_to(common.REPO_DIR)}")


if __name__ == "__main__":
    main()
