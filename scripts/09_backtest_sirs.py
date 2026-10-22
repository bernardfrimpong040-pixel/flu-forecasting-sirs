"""
09_backtest_sirs.py - test the Stage 3 SIRS model against the baseline and the trend model.

Same fair-test rule as Stage 2:
  * tuning seasons: 2023-24 and 2024-25 -> pick KAPPA
  * test season:    2025-26             -> score the picked KAPPA once

Usage:
    python scripts/09_backtest_sirs.py          # the test (about 2 minutes)
    python scripts/09_backtest_sirs.py --tune   # also redo the KAPPA grid (about 8 minutes)

Writes to results/:
  sirs_summary.csv        relative WIS (vs baseline) by level and horizon, trend and SIRS
  sirs_by_phase.csv       relative WIS and bias in the growth, peak and decline phases
  season_size.csv         each season's real size vs the "typical season" the model assumed
  tuning_grid_sirs.csv    (with --tune) every KAPPA in every season
  05_sirs_us_forecasts.png
"""

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import baseline_model
import common
import scoring
import sirs_model
import trend_model

TEST_SEASON = "2025-26"
TUNING_SEASONS = ["2023-24", "2024-25"]
TEST_KAPPA = 0.3                         # chosen on the tuning seasons only (see --tune)
TEST_TREND = {"window": 3, "phi": 0.5}   # the Stage 2 test settings
GRID_KAPPAS = [0.2, 0.3, 0.4, 0.5, 0.6]


def season_size_table(data):
    """For each season: total US admissions vs the 'typical season' the model assumed."""
    us = data[data["location"] == "US"]
    rows = []
    for season, (start, _) in scoring.SEASONS.items():
        day = pd.Timestamp(start)
        typical = sirs_model.typical_season_total(us, day)
        begin = sirs_model.season_start(day)
        actual = us[(us["date"] >= begin) & (us["date"] < begin + pd.DateOffset(years=1))]["value"].sum()
        rows.append({"season": season, "typical_assumed": typical, "actual": actual,
                     "actual_over_typical": actual / typical})
    return pd.DataFrame(rows)


def run_tuning(data, locations):
    print("KAPPA grid (relative WIS vs baseline; lower is better). This takes several minutes ...")
    base = {s: scoring.backtest(baseline_model, data, locations, s) for s in scoring.SEASONS}
    rows = []
    for kappa in GRID_KAPPAS:
        row = {"kappa": kappa}
        for season in scoring.SEASONS:
            sirs = scoring.backtest(sirs_model, data, locations, season, kappa=kappa)
            row[season] = round(scoring.relative_wis(sirs, base[season]), 3)
        row["tuning_mean"] = round(np.mean([row[s] for s in TUNING_SEASONS]), 3)
        row["all_three_mean"] = round(np.mean([row[s] for s in scoring.SEASONS]), 3)
        rows.append(row)
        print(f"  kappa={kappa}:  2023-24 {row['2023-24']:.3f}  2024-25 {row['2024-25']:.3f}  "
              f"2025-26 {row['2025-26']:.3f}  tuning mean {row['tuning_mean']:.3f}  "
              f"all-three mean {row['all_three_mean']:.3f}")
    grid = pd.DataFrame(rows)
    grid.to_csv(common.RESULTS_DIR / "tuning_grid_sirs.csv", index=False)
    print(f"Saved: {plot_kappa_grid(grid).relative_to(common.REPO_DIR)}")
    print(f"\nBest on 2023-24 + 2024-25 (used for the 2025-26 test): "
          f"kappa={grid.loc[grid['tuning_mean'].idxmin(), 'kappa']}")
    print(f"Best on all three seasons (used for live 2026-27 forecasts): "
          f"kappa={grid.loc[grid['all_three_mean'].idxmin(), 'kappa']}\n")


def plot_kappa_grid(grid):
    """Relative WIS against KAPPA, one line per season (labelled directly, no legend box)."""
    colours = {"2023-24": "#7a8794", "2024-25": "#c0504d", "2025-26": "#1f5fbf"}
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.axhline(1.0, color="#999999", linewidth=1, linestyle="--")
    ax.text(GRID_KAPPAS[-1] + 0.015, 1.0, "baseline", fontsize=9, color="#666666", va="center")
    for season, colour in colours.items():
        ax.plot(grid["kappa"], grid[season], color=colour, linewidth=2, marker="o", markersize=5)
        ax.annotate(season, (grid["kappa"].iloc[-1], grid[season].iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", fontsize=9, color=colour, va="center")
    ax.set_xlabel("KAPPA (share of season-start susceptibles a typical season uses)")
    ax.set_ylabel("Relative WIS vs baseline (lower is better)")
    ax.set_title("SIRS model: the best KAPPA depends on the season")
    ax.set_xlim(GRID_KAPPAS[0] - 0.03, GRID_KAPPAS[-1] + 0.1)
    ax.grid(axis="y", color="#e6e6e6")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = common.RESULTS_DIR / "06_kappa_by_season.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def worked_example(data):
    """The US forecast made with data to Dec 27, 2025 - the peak example from Stage 2."""
    rows = data[(data["location"] == "US") & (data["date"] <= "2025-12-27")].sort_values("date")
    typical = sirs_model.typical_season_total(rows, rows["date"].iloc[-1])
    so_far = rows[rows["date"] >= sirs_model.season_start(rows["date"].iloc[-1])]["value"].sum()
    rate = trend_model.growth_rate(rows, 3)
    r_t = 1 + (rate / 7) / sirs_model.GAMMA
    s_now = 1 - TEST_KAPPA * so_far / typical
    medians = sirs_model.simulate_weekly_admissions(rows["value"].iloc[-1], rate, so_far,
                                                    typical, TEST_KAPPA)
    print("\nWorked example: US, data to 2025-12-27, kappa = 0.3")
    print(f"  typical season total     {typical:,.0f} admissions")
    print(f"  admissions so far        {so_far:,.0f}  (since Aug 1, 2025)")
    print(f"  growth rate r            {rate:.3f} per week  ->  R_t = {r_t:.3f}")
    print(f"  susceptibles left s_now  {s_now:.3f} of the season-start pool")
    weeks = ["Jan 3", "Jan 10", "Jan 17", "Jan 24"]
    truth = data[(data["location"] == "US") & (data["date"].between("2026-01-03", "2026-01-24"))]
    for week, median, actual in zip(weeks, medians, truth.sort_values("date")["value"]):
        print(f"  week ending {week}: SIRS median {median:,.0f}   actual {actual:,.0f}")


def plot_us(scores, data):
    """Three panels: US forecasts made 2 weeks after the last data, by model."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
    base = scores["Stage 1 baseline"]
    for ax, (name, sc) in zip(axes, scores.items()):
        us = sc[(sc["location"] == "US") & (sc["horizon"] == 1)].copy()
        us["target"] = pd.to_datetime(us["reference_date"]) + pd.Timedelta(days=7)
        ax.plot(us["target"], us["truth"], color="#1a1a1a", linewidth=1.5, marker="o",
                markersize=3, label="What happened")
        ax.plot(us["target"], us["median"], color="#1f5fbf", linewidth=2, label="Forecast median")
        rel = scoring.relative_wis(sc[sc["location"] == "US"], base[base["location"] == "US"])
        ax.set_title(f"{name}  (US relative WIS {rel:.2f})", fontsize=10)
        ax.grid(axis="y", color="#e6e6e6")
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", rotation=30)
    axes[0].set_ylabel("Admissions per week")
    axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("US forecasts made 2 weeks after the last data (horizon 1), 2025-26 test season")
    fig.tight_layout()
    path = common.RESULTS_DIR / "05_sirs_us_forecasts.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tune", action="store_true", help="also redo the KAPPA grid")
    args = parser.parse_args()

    common.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    data = common.load_target_data()
    locations = common.load_locations()["location"].tolist()

    sizes = season_size_table(data)
    sizes.to_csv(common.RESULTS_DIR / "season_size.csv", index=False)
    print("US season size vs the 'typical season' the model assumes:")
    print(sizes.round(2).to_string(index=False), "\n")

    if args.tune:
        run_tuning(data, locations)

    print(f"Test season {TEST_SEASON}: SIRS (kappa={TEST_KAPPA}) and trend vs baseline")
    scores = {
        "Stage 1 baseline": scoring.backtest(baseline_model, data, locations, TEST_SEASON),
        "Stage 2 trend": scoring.backtest(trend_model, data, locations, TEST_SEASON, **TEST_TREND),
        "Stage 3 SIRS": scoring.backtest(sirs_model, data, locations, TEST_SEASON, kappa=TEST_KAPPA),
    }
    base = scores["Stage 1 baseline"]

    # Relative WIS by level and horizon.
    rows = []
    for level, pick in [("States", lambda s: s[s["location"] != "US"]),
                        ("US national", lambda s: s[s["location"] == "US"])]:
        for h in common.HORIZONS:
            at_h = lambda s: pick(s)[pick(s)["horizon"] == h]
            rows.append({"level": level, "horizon": h,
                         "trend_vs_baseline": scoring.relative_wis(at_h(scores["Stage 2 trend"]), at_h(base)),
                         "sirs_vs_baseline": scoring.relative_wis(at_h(scores["Stage 3 SIRS"]), at_h(base)),
                         "cov95_sirs": at_h(scores["Stage 3 SIRS"])["in_95"].mean()})
    summary = pd.DataFrame(rows)
    summary.to_csv(common.RESULTS_DIR / "sirs_summary.csv", index=False)
    print(summary.round(3).to_string(index=False))
    print(f"\nOverall relative WIS:  trend {scoring.relative_wis(scores['Stage 2 trend'], base):.3f}   "
          f"SIRS {scoring.relative_wis(scores['Stage 3 SIRS'], base):.3f}   "
          f"SIRS vs trend {scoring.relative_wis(scores['Stage 3 SIRS'], scores['Stage 2 trend']):.3f}")

    # By epidemic phase.
    keys = ["reference_date", "location", "horizon"]
    merged = scores["Stage 3 SIRS"].merge(base, on=keys, suffixes=("_sirs", "_base")).merge(
        scores["Stage 2 trend"][keys + ["wis", "median"]].rename(
            columns={"wis": "wis_trend", "median": "median_trend"}), on=keys)
    phased = scoring.add_phase(merged, data, TEST_SEASON)
    by_phase = phased.groupby("phase").apply(lambda g: pd.Series({
        "forecasts": len(g),
        "trend_vs_baseline": g["wis_trend"].mean() / g["wis_base"].mean(),
        "sirs_vs_baseline": g["wis_sirs"].mean() / g["wis_base"].mean(),
        "bias_baseline": (g["median_base"] - g["truth_base"]).mean(),
        "bias_trend": (g["median_trend"] - g["truth_base"]).mean(),
        "bias_sirs": (g["median_sirs"] - g["truth_base"]).mean(),
    }), include_groups=False).reset_index()
    by_phase.to_csv(common.RESULTS_DIR / "sirs_by_phase.csv", index=False)
    print("\nBy epidemic phase (bias = average forecast median minus truth):")
    print(by_phase.round(3).to_string(index=False))

    worked_example(data)
    print(f"\nSaved: {plot_us(scores, data).relative_to(common.REPO_DIR)}")


if __name__ == "__main__":
    main()
