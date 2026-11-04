"""
12_backtest_rebound.py - Stage 4b: the rebound after the winter break, and ensembles.

Same fair-test rule as before:
  * tuning seasons: 2023-24 and 2024-25 -> pick the settings
  * test season:    2025-26             -> score the picked settings once

Usage:
    python scripts/12_backtest_rebound.py               # the test (about 5 minutes)
    python scripts/12_backtest_rebound.py --tune        # also redo the rebound grid (about 20 minutes)
    python scripts/12_backtest_rebound.py --ensembles   # also compare 4 ensembles (about 25 minutes)

Writes to results/:
  rebound_summary.csv          relative WIS by level and horizon, test season
  rebound_by_phase.csv         relative WIS and bias in growth, peak and decline
  tuning_grid_rebound.csv      (with --tune) every (kappa, factor, rebound) in every season
  ensemble_comparison.csv      (with --ensembles) four ensembles in every season
  09_rebound_us_forecasts.png  Stage 4 vs Stage 4b, US, in a rebound season and the test season
"""

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import baseline_model
import common
import ensemble_sirs_model
import holiday_sirs_model
import scoring

TEST_SEASON = "2025-26"
TUNING_SEASONS = ["2023-24", "2024-25"]
STAGE4 = {"kappa": 0.3, "factor": 0.8, "rebound": 1.0}     # Stage 4: transmission fully returns
STAGE4B = {"kappa": 0.3, "factor": 0.8, "rebound": 0.9}    # chosen on the tuning seasons only (--tune)

GRID_KAPPAS = [0.3, 0.4]
GRID_FACTORS = [0.8, 0.9]
GRID_REBOUNDS = [1.0, 0.9, 0.8]

# Ensembles compared with --ensembles: (name, kappas, factors, rebounds). All use "mixture".
ENSEMBLES = [
    ("A: two kappas", [0.3, 0.4], [0.8], [0.9]),
    ("B: three rebounds", [0.3], [0.8], [0.8, 0.9, 1.0]),
    ("C: two kappas x two factors", [0.3, 0.4], [0.8, 0.9], [0.9]),
    ("D: two kappas x three rebounds", [0.3, 0.4], [0.8], [0.8, 0.9, 1.0]),
]


def season_row(model, data, locations, base, label, **settings):
    """Relative WIS of one model in every season, plus the tuning and all-three means."""
    row = dict(label)
    for season in scoring.SEASONS:
        sc = scoring.backtest(model, data, locations, season, **settings)
        row[season] = round(scoring.relative_wis(sc, base[season]), 3)
        row[f"cov95 {season}"] = round(sc["in_95"].mean(), 3)
    row["tuning_mean"] = round(np.mean([row[s] for s in TUNING_SEASONS]), 3)
    row["all_three_mean"] = round(np.mean([row[s] for s in scoring.SEASONS]), 3)
    return row


def print_row(row, keys):
    names = "  ".join(f"{k}={row[k]}" for k in keys)
    print(f"  {names}:  2023-24 {row['2023-24']:.3f}  2024-25 {row['2024-25']:.3f}  "
          f"2025-26 {row['2025-26']:.3f}  tuning mean {row['tuning_mean']:.3f}  "
          f"all-three mean {row['all_three_mean']:.3f}", flush=True)


def run_tuning(data, locations, base):
    print("Grid of (KAPPA, HOLIDAY_FACTOR, REBOUND), relative WIS vs baseline. About 20 minutes ...")
    rows = []
    for kappa in GRID_KAPPAS:
        for factor in GRID_FACTORS:
            for rebound in GRID_REBOUNDS:
                row = season_row(holiday_sirs_model, data, locations, base,
                                 {"kappa": kappa, "factor": factor, "rebound": rebound},
                                 kappa=kappa, factor=factor, rebound=rebound)
                print_row(row, ["kappa", "factor", "rebound"])
                rows.append(row)
    grid = pd.DataFrame(rows)
    grid.to_csv(common.RESULTS_DIR / "tuning_grid_rebound.csv", index=False)
    best_test = grid.loc[grid["tuning_mean"].idxmin()]
    best_live = grid.loc[grid["all_three_mean"].idxmin()]
    print(f"\nBest on 2023-24 + 2024-25 (used for the 2025-26 test): kappa={best_test['kappa']}, "
          f"factor={best_test['factor']}, rebound={best_test['rebound']}")
    print(f"Best on all three seasons (used for live 2026-27 forecasts): kappa={best_live['kappa']}, "
          f"factor={best_live['factor']}, rebound={best_live['rebound']}\n")
    return grid


def run_ensembles(data, locations, base):
    print("Ensembles (mixture of members), relative WIS vs baseline. About 25 minutes ...")
    rows = []
    for name, kappas, factors, rebounds in ENSEMBLES:
        row = season_row(ensemble_sirs_model, data, locations, base, {"ensemble": name},
                         kappas=kappas, factors=factors, rebounds=rebounds, method="mixture")
        print_row(row, ["ensemble"])
        rows.append(row)
    table = pd.DataFrame(rows)
    table.to_csv(common.RESULTS_DIR / "ensemble_comparison.csv", index=False)
    print("Compare the tuning means with the single Stage 4b model (0.716).\n")


def plot_us(data, locations, base_test, scores_test):
    """2 x 2 panels: rows = a rebound season (2024-25) and the test season; columns = Stage 4, 4b."""
    other = "2024-25"
    base_other = scoring.backtest(baseline_model, data, locations, other)
    scores_other = {
        "Stage 4 (rebound 1.0)": scoring.backtest(holiday_sirs_model, data, locations, other, **STAGE4),
        "Stage 4b (rebound 0.9)": scoring.backtest(holiday_sirs_model, data, locations, other, **STAGE4B),
    }
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for row, (season, base, scores) in enumerate([(other, base_other, scores_other),
                                                  (TEST_SEASON, base_test, scores_test)]):
        start_year = int(season[:4])
        for col, name in enumerate(["Stage 4 (rebound 1.0)", "Stage 4b (rebound 0.9)"]):
            ax = axes[row, col]
            sc = scores[name]
            us = sc[(sc["location"] == "US") & (sc["horizon"] == 1)].copy()
            us["target"] = pd.to_datetime(us["reference_date"]) + pd.Timedelta(days=7)
            # shade the admission weeks affected by the winter break (one-week lag)
            ax.axvspan(pd.Timestamp(start_year, 12, 28), pd.Timestamp(start_year + 1, 1, 10),
                       color="#f2e6c9", zorder=0)
            ax.plot(us["target"], us["truth"], color="#1a1a1a", linewidth=1.5, marker="o",
                    markersize=3, label="What happened")
            ax.plot(us["target"], us["median"], color="#1f5fbf", linewidth=2, label="Forecast median")
            rel = scoring.relative_wis(sc[sc["location"] == "US"], base[base["location"] == "US"])
            ax.set_title(f"{season}: {name}  (US rel. WIS {rel:.2f})", fontsize=10)
            ax.grid(axis="y", color="#e6e6e6")
            ax.spines[["top", "right"]].set_visible(False)
            ax.tick_params(axis="x", rotation=30)
    axes[0, 0].set_ylabel("Admissions per week")
    axes[1, 0].set_ylabel("Admissions per week")
    axes[0, 0].legend(frameon=False, fontsize=9)
    fig.suptitle("US forecasts 2 weeks after the last data (horizon 1). Shaded: winter break, "
                 "shifted by the 1-week lag")
    fig.tight_layout()
    path = common.RESULTS_DIR / "09_rebound_us_forecasts.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tune", action="store_true", help="also redo the rebound grid")
    parser.add_argument("--ensembles", action="store_true", help="also compare the ensembles")
    args = parser.parse_args()

    common.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    data = common.load_target_data()
    locations = common.load_locations()["location"].tolist()

    if args.tune or args.ensembles:
        print("Baseline forecasts for all three seasons ...")
        base_all = {s: scoring.backtest(baseline_model, data, locations, s) for s in scoring.SEASONS}
        if args.tune:
            run_tuning(data, locations, base_all)
        if args.ensembles:
            run_ensembles(data, locations, base_all)

    print(f"Test season {TEST_SEASON}: Stage 4 vs Stage 4b vs ensemble B (about 5 minutes)")
    base = scoring.backtest(baseline_model, data, locations, TEST_SEASON)
    scores = {
        "Stage 4 (rebound 1.0)": scoring.backtest(holiday_sirs_model, data, locations, TEST_SEASON, **STAGE4),
        "Stage 4b (rebound 0.9)": scoring.backtest(holiday_sirs_model, data, locations, TEST_SEASON, **STAGE4B),
        "Ensemble B": scoring.backtest(ensemble_sirs_model, data, locations, TEST_SEASON),
    }
    names = list(scores)

    rows = []
    for level, keep in [("States", lambda s: s[s["location"] != "US"]),
                        ("US national", lambda s: s[s["location"] == "US"])]:
        for h in common.HORIZONS:
            pick = lambda s: keep(s)[keep(s)["horizon"] == h]
            row = {"level": level, "horizon": h}
            for name in names:
                row[name] = scoring.relative_wis(pick(scores[name]), pick(base))
            row["cov95 Stage 4b"] = pick(scores["Stage 4b (rebound 0.9)"])["in_95"].mean()
            rows.append(row)
    summary = pd.DataFrame(rows)
    summary.to_csv(common.RESULTS_DIR / "rebound_summary.csv", index=False)
    print(summary.round(3).to_string(index=False))
    print("\nOverall relative WIS vs baseline:  " + "   ".join(
        f"{name} {scoring.relative_wis(scores[name], base):.3f}" for name in names))

    # By epidemic phase.
    keys = ["reference_date", "location", "horizon"]
    merged = base.rename(columns={"wis": "wis_base", "median": "median_base"})
    for name, tag in zip(names, ["stage4", "stage4b", "ensemble"]):
        merged = merged.merge(scores[name][keys + ["wis", "median"]].rename(
            columns={"wis": f"wis_{tag}", "median": f"median_{tag}"}), on=keys)
    phased = scoring.add_phase(merged, data, TEST_SEASON)
    by_phase = phased.groupby("phase").apply(lambda g: pd.Series({
        "forecasts": len(g),
        "stage4": g["wis_stage4"].mean() / g["wis_base"].mean(),
        "stage4b": g["wis_stage4b"].mean() / g["wis_base"].mean(),
        "ensemble": g["wis_ensemble"].mean() / g["wis_base"].mean(),
        "bias_stage4": (g["median_stage4"] - g["truth"]).mean(),
        "bias_stage4b": (g["median_stage4b"] - g["truth"]).mean(),
    }), include_groups=False).reset_index()
    by_phase.to_csv(common.RESULTS_DIR / "rebound_by_phase.csv", index=False)
    print("\nBy epidemic phase (relative WIS vs baseline; bias = median minus truth):")
    print(by_phase.round(3).to_string(index=False))

    print(f"\nSaved: {plot_us(data, locations, base, scores).relative_to(common.REPO_DIR)}")


if __name__ == "__main__":
    main()
