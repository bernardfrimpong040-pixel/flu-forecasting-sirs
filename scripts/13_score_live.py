"""
13_score_live.py - Stage 5: score the forecasts we actually submitted this season.

Backtests (Stages 1-4b) tell us how the models WOULD have done. This script tells
us how they ARE doing, live, in the 2026-27 FluSight season.

What it does, every week:
  1. Downloads, from the CDC hub, every forecast file our four models submitted
     (the hub's copy is the official record of what was submitted, so practice
     files that were never submitted are never counted). For comparison it also
     downloads the CDC's own FluSight-ensemble and FluSight-baseline forecasts.
  2. Scores every forecast whose target week now has data, with the same WIS and
     interval coverage used in the backtests.
  3. Compares each model with our baseline (relative WIS) on exactly the same
     forecasts, and with the CDC ensemble.
  4. Measures backfill: how much each recent US week changed between the first
     time it was reported and today (uses the dated snapshots in data/raw).

Run it after 01_download_data.py:
    python scripts/13_score_live.py

Writes to results/:
  live_scores.csv            one row per model, reference date, location and horizon
  live_summary.csv           one row per model: relative WIS, coverage, number scored
  live_by_week.csv           relative WIS by reference date (is a model getting better?)
  live_revisions.csv         US weekly values: first reported vs latest
  10_live_us_forecasts.png   US forecasts we submitted vs what happened
"""

from datetime import date, timedelta
import urllib.error
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import common
import scoring

SEASON_START = date(2026, 10, 24)          # our first submission (reference date)
OUR_MODELS = [common.MODEL_ID, common.TREND_MODEL_ID, common.SIRS_MODEL_ID, common.HOLIDAY_MODEL_ID]
CDC_MODELS = ["FluSight-ensemble", "FluSight-baseline"]
HUB_DIR = common.DATA_DIR / "hub"           # local copies of the hub files (they never change)
NAMES = {
    common.MODEL_ID: "Baseline",
    common.TREND_MODEL_ID: "Trend",
    common.SIRS_MODEL_ID: "SIRS",
    common.HOLIDAY_MODEL_ID: "Holiday SIRS",
    "FluSight-ensemble": "CDC ensemble",
    "FluSight-baseline": "CDC baseline",
}


def reference_dates_so_far(today=None):
    """Every Saturday from our first submission up to the latest round that has closed or is open."""
    today = today or date.today()
    last = common.next_reference_date(today)
    dates, d = [], SEASON_START
    while d <= last:
        dates.append(d)
        d += timedelta(weeks=1)
    return dates


def hub_file(model, reference_date):
    """Return the local copy of one hub forecast file, downloading it if needed.

    Returns None if the hub does not have the file (not submitted, or not merged yet).
    """
    name = f"{reference_date.isoformat()}-{model}.csv"
    local = HUB_DIR / model / name
    if local.exists():
        return local
    url = f"{common.HUB_RAW_URL}/model-output/{model}/{name}"
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            content = response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(content)
    return local


def load_forecasts(dates):
    """All submitted forecasts (weekly admissions, quantiles, horizons 0-3) in one table."""
    tables, missing = [], []
    for model in OUR_MODELS + CDC_MODELS:
        for d in dates:
            path = hub_file(model, d)
            if path is None:
                missing.append(f"{model} {d}")
                continue
            table = pd.read_csv(path, dtype={"location": str, "output_type_id": str})
            table = table[(table["target"] == common.TARGET) & (table["output_type"] == "quantile")
                          & (table["horizon"].isin(common.HORIZONS))].copy()
            table["output_type_id"] = table["output_type_id"].astype(float)
            table["model"] = model
            tables.append(table)
    if missing:
        print("Not on the hub (not submitted, or not merged yet):  " + ",  ".join(missing))
    return pd.concat(tables, ignore_index=True)


def matched_relative_wis(scores, model, reference):
    """Mean WIS of `model` divided by that of `reference`, on the forecasts BOTH made."""
    keys = ["reference_date", "location", "horizon"]
    a = scores[scores["model"] == model][keys + ["wis"]]
    b = scores[scores["model"] == reference][keys + ["wis"]]
    both = a.merge(b, on=keys, suffixes=("", "_ref"))
    if both.empty:
        return np.nan, 0
    return both["wis"].mean() / both["wis_ref"].mean(), len(both)


def revisions_table():
    """For each recent US week: the value first reported, the latest value, and the change."""
    snapshots = sorted(common.RAW_DIR.glob("target-hospital-admissions_*.csv"))
    first = {}
    for path in snapshots:
        snap = pd.read_csv(path, dtype={"location": str}, parse_dates=["date"])
        us = snap[(snap["location"] == "US") & (snap["date"] >= pd.Timestamp(2026, 9, 1))]
        snapshot_date = path.stem.split("_")[-1]
        for _, row in us.dropna(subset=["value"]).iterrows():
            first.setdefault(row["date"], (row["value"], snapshot_date))
    latest = common.load_target_data()
    latest = latest[latest["location"] == "US"].set_index("date")["value"]
    rows = []
    for week, (value, snapshot_date) in sorted(first.items()):
        if week in latest.index:
            rows.append({"week_ending": week.date(), "first_reported": int(value),
                         "first_snapshot": snapshot_date, "latest": int(latest[week]),
                         "change_pct": round(100 * (latest[week] - value) / value, 1)})
    return pd.DataFrame(rows)


def plot_us(forecasts, data):
    """One panel per model: what happened (black) and each submitted forecast (blue)."""
    models = [m for m in OUR_MODELS + ["FluSight-ensemble"] if m in set(forecasts["model"])]
    us_truth = data[(data["location"] == "US") & (data["date"] >= pd.Timestamp(2026, 9, 26))]
    ncols = 3
    nrows = (len(models) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 4.2 * nrows), sharey=True)
    axes = np.atleast_1d(axes).ravel()
    for ax in axes[len(models):]:
        ax.axis("off")                                     # unused panels
    x_end = pd.to_datetime(forecasts["target_end_date"]).max() + pd.Timedelta(days=7)
    for ax, model in zip(axes, models):
        us = forecasts[(forecasts["model"] == model) & (forecasts["location"] == "US")]
        for ref, group in us.groupby("reference_date"):
            med = group[np.isclose(group["output_type_id"], 0.5)].sort_values("horizon")
            low = group[np.isclose(group["output_type_id"], 0.025)].sort_values("horizon")
            high = group[np.isclose(group["output_type_id"], 0.975)].sort_values("horizon")
            x = pd.to_datetime(med["target_end_date"])
            ax.fill_between(x, low["value"], high["value"], color="#1f5fbf", alpha=0.08)
            ax.plot(x, med["value"], color="#1f5fbf", linewidth=1.6, marker="o", markersize=2.5)
        # Admission weeks affected by Thanksgiving and the winter break (one-week lag).
        ax.axvspan(pd.Timestamp(2026, 11, 29), pd.Timestamp(2026, 12, 5), color="#f2e6c9", zorder=0)
        ax.axvspan(pd.Timestamp(2026, 12, 27), pd.Timestamp(2027, 1, 9), color="#f2e6c9", zorder=0)
        ax.plot(us_truth["date"], us_truth["value"], color="#1a1a1a", linewidth=1.8, label="What happened")
        ax.set_title(NAMES[model], fontsize=11)
        ax.grid(axis="y", color="#e6e6e6")
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xlim(pd.Timestamp(2026, 9, 26), x_end)
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %d"))
        ax.tick_params(axis="x", rotation=30)
    for ax in axes[::ncols]:
        ax.set_ylabel("US admissions per week")
    axes[0].legend(frameon=False, fontsize=9, loc="upper left")
    fig.suptitle("Live 2026-27 season: every US forecast submitted (blue: median and 95% range)\n"
                 "vs what happened (black, latest data). Shaded: holiday weeks shifted by the 1-week lag")
    fig.tight_layout()
    path = common.RESULTS_DIR / "10_live_us_forecasts.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main():
    common.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    data = common.load_target_data()
    print(f"Latest data: week ending {data['date'].max().date()}")

    dates = reference_dates_so_far()
    forecasts = load_forecasts(dates)

    # 1. Score every forecast that now has an observed value.
    scores = []
    for model, group in forecasts.groupby("model"):
        sc = scoring.score_forecasts(group.drop(columns="model"), data)
        sc["model"] = model
        scores.append(sc)
    scores = pd.concat(scores, ignore_index=True)
    scores.to_csv(common.RESULTS_DIR / "live_scores.csv", index=False)

    # 2. Summary: each model against our baseline and against the CDC ensemble.
    rows = []
    for model in OUR_MODELS + CDC_MODELS:
        mine = scores[scores["model"] == model]
        if mine.empty:
            continue
        rel_base, n_base = matched_relative_wis(scores, model, common.MODEL_ID)
        rel_ens, _ = matched_relative_wis(scores, model, "FluSight-ensemble")
        rows.append({
            "model": NAMES[model],
            "weeks submitted": mine["reference_date"].nunique(),
            "forecasts scored": len(mine),
            "rel. WIS vs our baseline": round(rel_base, 3),
            "rel. WIS vs CDC ensemble": round(rel_ens, 3),
            "coverage 50%": round(mine["in_50"].mean(), 3),
            "coverage 95%": round(mine["in_95"].mean(), 3),
            "US coverage 95%": round(mine[mine["location"] == "US"]["in_95"].mean(), 3),
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(common.RESULTS_DIR / "live_summary.csv", index=False)
    print("\nLive scores so far (relative WIS: below 1 = better than the reference; "
          "each comparison uses only forecasts both models made):")
    print(summary.to_string(index=False))

    # 3. By reference date: relative WIS vs our baseline, all horizons scored so far.
    by_week = []
    for (model, ref), group in scores.groupby(["model", "reference_date"]):
        rel, n = matched_relative_wis(scores[scores["reference_date"] == ref], model, common.MODEL_ID)
        by_week.append({"reference_date": ref, "model": NAMES[model], "rel. WIS vs our baseline": rel,
                        "horizons scored": sorted(group["horizon"].unique().tolist())})
    by_week = pd.DataFrame(by_week)
    by_week.to_csv(common.RESULTS_DIR / "live_by_week.csv", index=False)
    table = by_week.pivot(index="reference_date", columns="model", values="rel. WIS vs our baseline")
    print("\nRelative WIS vs our baseline, by reference date (later weeks have fewer horizons scored yet):")
    print(table.round(3).to_string())

    # 4. Backfill.
    revisions = revisions_table()
    revisions.to_csv(common.RESULTS_DIR / "live_revisions.csv", index=False)
    if not revisions.empty:
        print("\nUS backfill: value first reported vs latest value")
        print(revisions.to_string(index=False))

    print(f"\nSaved: {plot_us(forecasts, data).relative_to(common.REPO_DIR)}")


if __name__ == "__main__":
    main()
