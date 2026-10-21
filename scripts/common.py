"""
common.py - settings and small helper functions shared by every script.

Every other script starts with  `import common`  so that the team name,
the quantile levels and the folder paths are written down in ONE place.
If you ever need to change one of them, change it here only.
"""

# --- Python tools we use -------------------------------------------------
from datetime import date, timedelta   # dates and "number of days" objects
from pathlib import Path               # safe way to build folder/file paths

import pandas as pd                    # tables (DataFrames)


# --- Your FluSight names (must match the hub rules) ----------------------
# Letters, numbers and "_" only. No spaces, no hyphens, under 15 characters.
TEAM_ABBR = "BFrimpong"
MODEL_ABBR = "baseline"

# The hub calls the pair "team-model". It names your folder and your files.
MODEL_ID = f"{TEAM_ABBR}-{MODEL_ABBR}"


# --- Folders inside this repository --------------------------------------
# Path(__file__) is this file; .parent is scripts/; .parent again is the repo.
REPO_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_DIR / "data"                       # downloaded data
RAW_DIR = DATA_DIR / "raw"                         # one dated copy per week
RESULTS_DIR = REPO_DIR / "results"                 # plots and score tables
OUTPUT_DIR = REPO_DIR / "model-output" / MODEL_ID  # weekly submission files
METADATA_FILE = REPO_DIR / "model-metadata" / f"{MODEL_ID}.yml"

# The "latest" copies that the other scripts read.
TARGET_FILE = DATA_DIR / "target-hospital-admissions.csv"
LOCATIONS_FILE = DATA_DIR / "locations.csv"


# --- Where the CDC FluSight hub keeps its data ---------------------------
HUB_RAW_URL = "https://raw.githubusercontent.com/cdcepi/FluSight-forecast-hub/main"
TARGET_URL = f"{HUB_RAW_URL}/target-data/target-hospital-admissions.csv"
LOCATIONS_URL = f"{HUB_RAW_URL}/auxiliary-data/locations.csv"


# --- What the hub asks us to predict -------------------------------------
TARGET = "wk inc flu hosp"     # weekly lab-confirmed flu hospital admissions
HORIZONS = [0, 1, 2, 3]        # this week + the next 3 weeks (-1 is optional, not scored)

# The 23 quantile levels the hub requires, exactly as listed in its rules.
QUANTILE_LEVELS = [0.01, 0.025, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4,
                   0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9,
                   0.95, 0.975, 0.99]


# --- Helper functions -----------------------------------------------------
def load_target_data():
    """Read the downloaded admissions table and tidy it up.

    Returns a table with columns: date, location, location_name, value.
    Rows with a missing value are dropped (a few states paused reporting in 2024).
    """
    # dtype={"location": str} keeps codes such as "01" (Alabama) as text,
    # otherwise pandas would turn "01" into the number 1 and lose the zero.
    data = pd.read_csv(TARGET_FILE, dtype={"location": str}, parse_dates=["date"])
    data = data.dropna(subset=["value"])                # remove empty weeks
    data = data[["date", "location", "location_name", "value"]]
    return data.sort_values(["location", "date"]).reset_index(drop=True)


def load_locations():
    """Read the hub's list of locations (code, name, population)."""
    return pd.read_csv(LOCATIONS_FILE, dtype={"location": str})


def next_reference_date(today=None):
    """Work out this week's FluSight reference date (always a Saturday).

    Forecasts are due Wednesday 11 PM Eastern; the reference date is the
    Saturday after that Wednesday. The submission window runs Sunday to
    Wednesday, so on Thursday, Friday or Saturday the current round is closed
    and we move to the following Saturday.
    """
    if today is None:
        today = date.today()
    # weekday(): Monday=0, Tuesday=1, Wednesday=2, Thursday=3, ... Saturday=5, Sunday=6
    days_until_saturday = (5 - today.weekday()) % 7
    reference = today + timedelta(days=days_until_saturday)
    if today.weekday() in (3, 4, 5):            # Thursday, Friday, Saturday
        reference = reference + timedelta(days=7)
    return reference
