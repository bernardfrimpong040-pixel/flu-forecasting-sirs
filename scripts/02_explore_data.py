"""
02_explore_data.py - look at the data before modelling it.

Makes two pictures in results/:
  01_national_seasons.png  - each flu season's national curve, lined up by week of season
  02_largest_states.png    - this season vs last season in the six largest states
and prints the peak of every past season.

A "season" here runs from August 1 to July 31, so the 2025-2026 season is
Aug 2025 - Jul 2026. Lining seasons up by "weeks since Aug 1" lets you compare
their shapes directly.
"""

import matplotlib
matplotlib.use("Agg")              # draw to files only (no pop-up windows needed)
import matplotlib.pyplot as plt    # the plotting library

import common

CURRENT_COLOR = "#1f5fbf"          # strong blue: the season we are forecasting
PAST_COLOR = "#a6abb3"             # muted grey: earlier seasons, for context


def add_season_columns(data):
    """Add 'season' (e.g. '2025-2026') and 'season_week' (0 = first week of August)."""
    data = data.copy()
    # Months Aug-Dec belong to the season that starts that year; Jan-Jul to the one before.
    start_year = data["date"].dt.year.where(data["date"].dt.month >= 8, data["date"].dt.year - 1)
    data["season"] = start_year.astype(str) + "-" + (start_year + 1).astype(str)
    season_start = start_year.astype(str) + "-08-01"
    data["season_week"] = (data["date"] - season_start.astype("datetime64[ns]")).dt.days // 7
    return data


def plot_national(data, current_season):
    national = data[data["location"] == "US"]
    fig, ax = plt.subplots(figsize=(9, 5))
    for season, rows in national.groupby("season"):
        is_current = season == current_season
        ax.plot(rows["season_week"], rows["value"],
                color=CURRENT_COLOR if is_current else PAST_COLOR,
                linewidth=2.5 if is_current else 1.5)
        # Label each line directly instead of using a colour legend:
        # past seasons at their peak, the current season at its newest point.
        spot = rows.iloc[-1] if is_current else rows.loc[rows["value"].idxmax()]
        ax.annotate(season, (spot["season_week"], spot["value"]),
                    xytext=(4, 0), textcoords="offset points", fontsize=8,
                    color="#1a1a1a" if is_current else "#555555")
    ax.set_title("US weekly flu hospital admissions, by season")
    ax.set_xlabel("Weeks since August 1")
    ax.set_ylabel("Admissions per week")
    ax.grid(axis="y", color="#e6e6e6")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = common.RESULTS_DIR / "01_national_seasons.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_largest_states(data, locations, current_season, previous_season):
    # The six states with the largest populations ("US" itself is excluded).
    states = locations[locations["location"] != "US"].nlargest(6, "population")
    fig, axes = plt.subplots(2, 3, figsize=(11, 6), sharex=True)
    for ax, (_, state) in zip(axes.flat, states.iterrows()):
        rows = data[data["location"] == state["location"]]
        for season, color, width in [(previous_season, PAST_COLOR, 1.5),
                                     (current_season, CURRENT_COLOR, 2.5)]:
            part = rows[rows["season"] == season]
            ax.plot(part["season_week"], part["value"], color=color, linewidth=width,
                    label=season)
        ax.set_title(state["location_name"], fontsize=10)
        ax.grid(axis="y", color="#e6e6e6")
        ax.spines[["top", "right"]].set_visible(False)
    axes.flat[0].legend(fontsize=8, frameon=False)
    fig.supxlabel("Weeks since August 1")
    fig.supylabel("Admissions per week")
    fig.suptitle("This season vs last season, six largest states")
    fig.tight_layout()
    path = common.RESULTS_DIR / "02_largest_states.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main():
    common.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    data = add_season_columns(common.load_target_data())
    locations = common.load_locations()

    seasons = sorted(data["season"].unique())
    current_season, previous_season = seasons[-1], seasons[-2]

    # Peak of every season, nationally.
    national = data[data["location"] == "US"]
    peaks = national.loc[national.groupby("season")["value"].idxmax(), ["season", "date", "value"]]
    peaks.columns = ["season", "peak week ending", "peak admissions"]
    print("National peak of each season (the current season is still in progress):")
    print(peaks.to_string(index=False))

    print("Saved:", plot_national(data, current_season).relative_to(common.REPO_DIR))
    print("Saved:", plot_largest_states(data, locations, current_season,
                                        previous_season).relative_to(common.REPO_DIR))


if __name__ == "__main__":
    main()
