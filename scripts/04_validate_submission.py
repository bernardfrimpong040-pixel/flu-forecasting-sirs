"""
04_validate_submission.py - check a submission file against the FluSight rules
BEFORE opening a pull request.

The hub runs its own official checks (an R package called hubValidations) when
you open the pull request. This script repeats the important ones in Python, so
mistakes are caught on your laptop instead of in public.

Usage:
    python scripts/04_validate_submission.py                  # newest file of EVERY model
    python scripts/04_validate_submission.py path/to/file.csv # one chosen file

For each forecast file it also checks that model's metadata file
(model-metadata/<team>-<model>.yml).
"""

import re                                # "regular expressions": pattern matching on text
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml                              # reads .yml files

import common

REQUIRED_COLUMNS = ["reference_date", "target", "horizon", "target_end_date",
                    "location", "output_type", "output_type_id", "value"]
VALID_TARGETS = ["wk inc flu hosp", "wk flu hosp rate change", "wk inc flu prop ed visits",
                 "peak week inc flu hosp", "peak inc flu hosp"]
VALID_LICENSES = ["CC0-1.0", "CC-BY-4.0", "CC-BY_SA-4.0", "PPDL", "ODC-by", "ODbL", "OGL-3.0"]
REQUIRED_METADATA = ["team_name", "team_abbr", "model_name", "model_abbr", "model_contributors",
                     "license", "designated_model", "data_inputs", "methods", "methods_long",
                     "ensemble_of_models", "ensemble_of_hub_models", "website_url"]

failures = []                            # every failed check is added to this list


def check(passed, message):
    """Print PASS or FAIL for one check, and remember the failures."""
    print(("PASS  " if passed else "FAIL  ") + message)
    if not passed:
        failures.append(message)


def validate_forecast(path):
    print(f"\nChecking forecast file: {path.relative_to(common.REPO_DIR)}\n")

    # --- 1. File name and folder -----------------------------------------
    pattern = r"^(\d{4}-\d{2}-\d{2})-([A-Za-z0-9_]+)-([A-Za-z0-9_]+)\.csv$"
    match = re.match(pattern, path.name)
    check(match is not None, "file name looks like YYYY-MM-DD-team-model.csv")
    if match is None:
        return
    file_date = date.fromisoformat(match.group(1))
    model_id = f"{match.group(2)}-{match.group(3)}"
    check(path.parent.name == model_id, f"folder name matches the model id '{model_id}'")
    check(file_date.weekday() == 5, f"reference date {file_date} is a Saturday")

    # --- 2. Columns ---------------------------------------------------------
    df = pd.read_csv(path, dtype={"location": str})
    check(sorted(df.columns) == sorted(REQUIRED_COLUMNS),
          "columns are exactly the 8 required ones (no extras)")
    if sorted(df.columns) != sorted(REQUIRED_COLUMNS):
        return

    # --- 3. Dates, targets, horizons, locations ----------------------------
    check((df["reference_date"] == file_date.isoformat()).all(),
          "every reference_date equals the date in the file name")
    check(df["target"].isin(VALID_TARGETS).all(), "every target is a valid FluSight target")

    hosp = df[df["target"] == common.TARGET].copy()
    check(len(hosp) > 0, f"file contains '{common.TARGET}' rows")
    check(hosp["horizon"].isin([-1, 0, 1, 2, 3]).all(), "horizons are between -1 and 3")

    expected_end = pd.to_datetime(hosp["reference_date"]) + pd.to_timedelta(hosp["horizon"] * 7, unit="D")
    check((pd.to_datetime(hosp["target_end_date"]) == expected_end).all(),
          "target_end_date = reference_date + 7 x horizon")

    locations = common.load_locations()
    check(hosp["location"].isin(locations["location"]).all(),
          "every location code is in the hub's location list (codes kept as text, e.g. '01')")

    # --- 4. Quantiles ---------------------------------------------------------
    check((hosp["output_type"] == "quantile").all(), "output_type is 'quantile'")
    levels_per_group = hosp.groupby(["location", "horizon"])["output_type_id"].apply(
        lambda s: sorted(s.round(3).tolist()))
    check(all(levels == common.QUANTILE_LEVELS for levels in levels_per_group),
          "each location/horizon has exactly the 23 required quantile levels")

    # --- 5. Values --------------------------------------------------------------
    check((hosp["value"] >= 0).all(), "no negative values")
    check((hosp["value"] == hosp["value"].round()).all(), "admission values are whole numbers")

    ordered = hosp.sort_values(["location", "horizon", "output_type_id"])
    never_decreases = ordered.groupby(["location", "horizon"])["value"].apply(
        lambda s: (s.diff().dropna() >= 0).all())
    check(never_decreases.all(), "values never decrease as the quantile level rises")

    with_pop = hosp.merge(locations[["location", "population"]], on="location")
    check((with_pop["value"] <= 0.30 * with_pop["population"]).all(),
          "plausibility: no value above 30% of the location's population")

    # --- 6. Submission window (a warning, not a failure) -------------------
    # The window runs Sunday 00:00 to Wednesday 11 PM Eastern before the reference date.
    opens = file_date - timedelta(days=6)
    closes = file_date - timedelta(days=3)
    today = date.today()
    if opens <= today <= closes:
        print(f"PASS  today ({today}) is inside the submission window {opens} to {closes} "
              "(deadline 11 PM Eastern on the last day)")
    else:
        print(f"NOTE  today ({today}) is outside the window {opens} to {closes}; "
              "the hub would reject this file now. Fine for testing.")

    print(f"\nSummary: {hosp['location'].nunique()} locations, "
          f"horizons {sorted(int(h) for h in hosp['horizon'].unique())}, {len(df):,} rows")
    return model_id


def validate_metadata(model_id):
    metadata_file = common.REPO_DIR / "model-metadata" / f"{model_id}.yml"
    print(f"\nChecking metadata file: {metadata_file.relative_to(common.REPO_DIR)}\n")
    check(metadata_file.exists(), "metadata file exists")
    if not metadata_file.exists():
        return
    with open(metadata_file, encoding="utf-8") as f:
        meta = yaml.safe_load(f)

    missing = [key for key in REQUIRED_METADATA if key not in meta]
    check(not missing, f"all required fields present {'(missing: ' + ', '.join(missing) + ')' if missing else ''}")
    name_ok = re.fullmatch(r"[A-Za-z0-9_+]{1,15}", str(meta.get("team_abbr", ""))) and \
        re.fullmatch(r"[A-Za-z0-9_+]{1,15}", str(meta.get("model_abbr", "")))
    check(bool(name_ok), "team_abbr and model_abbr use only letters, numbers, '_' (max 15)")
    check(f"{meta.get('team_abbr')}-{meta.get('model_abbr')}" == model_id,
          f"team_abbr-model_abbr matches '{model_id}' (the file and folder name)")
    check(len(str(meta.get("methods", ""))) <= 200, "methods is 200 characters or fewer")
    check(meta.get("license") in VALID_LICENSES, "license is one of the accepted licenses")
    for key in ["designated_model", "ensemble_of_models", "ensemble_of_hub_models"]:
        check(isinstance(meta.get(key), bool), f"{key} is true or false")
    contributors = meta.get("model_contributors") or []
    check(all({"name", "affiliation", "email"} <= set(c) for c in contributors) and contributors,
          "every contributor has a name, affiliation and email")
    if meta.get("baseline_model") is True:
        check(meta.get("designated_model") is False,
              "a baseline model is not designated for the ensemble")


def main():
    if len(sys.argv) > 1:
        paths = [Path(sys.argv[1]).resolve()]    # the file you named, as a full path
    else:
        # The newest file (names sort by date) in every model's folder.
        paths = []
        for model_dir in sorted((common.REPO_DIR / "model-output").glob("*")):
            files = sorted(model_dir.glob("*.csv"))
            if files:
                paths.append(files[-1])
        if not paths:
            raise SystemExit("No forecast files yet. Run 03_baseline_forecast.py first.")

    for path in paths:
        print("=" * 70)
        model_id = validate_forecast(path)
        if model_id:
            validate_metadata(model_id)

    print()
    if failures:
        print(f"{len(failures)} check(s) FAILED. Fix them before opening a pull request.")
        sys.exit(1)
    print(f"All checks passed ({datetime.now():%Y-%m-%d %H:%M}). Ready to submit.")


if __name__ == "__main__":
    main()
