"""
10_holiday_forecast.py - make this week's FluSight file for the Stage 4 holiday SIRS model.

Same steps as 08_sirs_forecast.py, but with the SIRS model whose transmission
drops during school holidays (scripts/holiday_sirs_model.py).

Usage (normal weekly run):
    python scripts/10_holiday_forecast.py

Usage (choose the reference date yourself, e.g. for testing):
    python scripts/10_holiday_forecast.py --reference-date 2026-10-31

Writes:  model-output/BFrimpong-sirs_hol/<reference_date>-BFrimpong-sirs_hol.csv
"""

import argparse
from datetime import date, timedelta

import common
import holiday_sirs_model              # the model itself (scripts/holiday_sirs_model.py)


def main():
    # 1. Read the optional --reference-date option.
    parser = argparse.ArgumentParser(description="Make the weekly holiday-SIRS forecast file.")
    parser.add_argument("--reference-date", help="Saturday in YYYY-MM-DD format")
    args = parser.parse_args()

    if args.reference_date:
        reference_date = date.fromisoformat(args.reference_date)
    else:
        reference_date = common.next_reference_date()

    if reference_date.weekday() != 5:
        raise SystemExit(f"{reference_date} is not a Saturday. FluSight reference dates are Saturdays.")

    # 2. Load the data and check it is up to date.
    data = common.load_target_data()
    latest = data["date"].max().date()
    expected = reference_date - timedelta(weeks=1)
    print(f"Reference date:            {reference_date}  (forecasts due Wednesday "
          f"{reference_date - timedelta(days=3)}, 11 PM Eastern)")
    print(f"Latest week in the data:   {latest}")
    print(f"Model settings:            kappa = {holiday_sirs_model.KAPPA}, "
          f"holiday factor = {holiday_sirs_model.HOLIDAY_FACTOR}, lag = {holiday_sirs_model.LAG_DAYS} days")
    if latest < expected:
        print(f"WARNING: expected data through {expected}. Run 01_download_data.py after "
              "the hub updates on Wednesday, or the forecast will be one week stale.")

    # 3. Make the forecast for every location in the hub's list.
    locations = common.load_locations()["location"].tolist()
    forecast = holiday_sirs_model.make_forecast(data, reference_date, locations)

    # 4. Save it with the exact file name the hub requires.
    common.HOLIDAY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = common.HOLIDAY_OUTPUT_DIR / f"{reference_date.isoformat()}-{common.HOLIDAY_MODEL_ID}.csv"
    forecast.to_csv(out_file, index=False)

    # 5. Show the national forecast: median and 95% range.
    us = forecast[forecast["location"] == "US"]
    table = us.pivot(index="target_end_date", columns="output_type_id", values="value")
    print("\nUS forecast (admissions per week):")
    print(table[[0.025, 0.5, 0.975]].rename(columns={0.025: "low (2.5%)", 0.5: "median",
                                                    0.975: "high (97.5%)"}).to_string())
    print(f"\nLocations forecast: {forecast['location'].nunique()}   Rows: {len(forecast):,}")
    print(f"Saved: {out_file.relative_to(common.REPO_DIR)}")
    print("Next: python scripts/04_validate_submission.py")


if __name__ == "__main__":
    main()
