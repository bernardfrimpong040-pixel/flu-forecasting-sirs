"""
01_download_data.py - download the latest flu hospital admissions data.

Run it every Wednesday afternoon, after the CDC updates the hub (by midday).

It saves two copies of the admissions table:
  data/target-hospital-admissions.csv               <- the "latest" copy the other scripts read
  data/raw/target-hospital-admissions_<today>.csv   <- a dated snapshot, kept forever

Why keep dated snapshots? Recent weeks get revised as late hospital reports
arrive. To judge our forecasts fairly in the paper, we must know what the data
looked like on the day we made each forecast. These snapshots are that record.
"""

from datetime import date      # today's date, for the snapshot file name

import pandas as pd            # reads a CSV straight from a web address

import common                  # our shared settings (scripts/common.py)


def main():
    # 1. Make sure the folders exist (exist_ok=True: no error if they already do).
    common.RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Download the admissions table from the CDC hub on GitHub.
    print("Downloading admissions data from the FluSight hub ...")
    admissions = pd.read_csv(common.TARGET_URL, dtype={"location": str})

    # 3. Download the list of locations (needed for populations and names).
    locations = pd.read_csv(common.LOCATIONS_URL, dtype={"location": str})

    # 4. Save the latest copies (index=False: don't write pandas' row numbers).
    admissions.to_csv(common.TARGET_FILE, index=False)
    locations.to_csv(common.LOCATIONS_FILE, index=False)

    # 5. Save today's dated snapshot.
    snapshot = common.RAW_DIR / f"target-hospital-admissions_{date.today().isoformat()}.csv"
    admissions.to_csv(snapshot, index=False)

    # 6. Print a short report so you can check the download worked.
    latest_week = admissions["date"].max()
    national = admissions[admissions["location"] == "US"].sort_values("date")
    print(f"Rows downloaded:      {len(admissions):,}")
    print(f"Locations:            {admissions['location'].nunique()}")
    print(f"Latest week ending:   {latest_week}")
    print("National admissions, last 6 weeks:")
    print(national[["date", "value"]].tail(6).to_string(index=False))
    print(f"Snapshot saved to:    {snapshot.relative_to(common.REPO_DIR)}")


# This line means: run main() only when this file is run directly
# (python scripts/01_download_data.py), not when another script imports it.
if __name__ == "__main__":
    main()
