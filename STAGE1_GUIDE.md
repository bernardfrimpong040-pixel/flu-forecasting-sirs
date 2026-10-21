# Stage 1 Guide — Data, Baseline Model and First FluSight Submission

**Goal of Stage 1:** get a valid forecast into the CDC FluSight hub as early as possible, with a baseline model that every later model must beat.

**First possible submission: Wednesday, October 21, 2026, by 11 PM Eastern** (reference date Saturday, October 24). If that is too tight, the next one is Wednesday, October 28 (reference date October 31). Late forecasts are never accepted, so a missed week is simply skipped.

---

## Part 1 — Set up and run (tonight)

1. Unzip `flu-forecasting-sirs.zip` into your Documents folder, so you have `Documents\flu-forecasting-sirs\`.
2. Open that folder in VS Code, then open a terminal (**Terminal → New Terminal**).
3. Run these commands one at a time:

```
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/01_download_data.py
python scripts/02_explore_data.py
python scripts/03_baseline_forecast.py
python scripts/04_validate_submission.py
python scripts/05_backtest_baseline.py
```

**What you should see**

| Script | Expected result |
| --- | --- |
| 01 | About 13,000 rows, 53 locations, latest week 2026-10-10 (tonight) or 2026-10-17 (after Wednesday's update) |
| 02 | A table of season peaks (2024–25: 55,544; 2025–26: 42,500) and two pictures in `results/` |
| 03 | Reference date 2026-10-24. Tonight it prints a WARNING that the data ends 2026-10-10 — that is expected; Wednesday's data fixes it |
| 04 | Every line PASS, ending with "All checks passed" |
| 05 | The backtest table (the same numbers as in the README) and `results/03_backtest_us_forecasts.png` |

Open the three pictures in `results/` and look at them before moving on.

---

## Part 2 — Put the project on GitHub (tonight)

1. On github.com, click **New repository**. Name: `flu-forecasting-sirs`. Public. Do **not** add a README (we already have one). Click **Create repository**.
2. In the VS Code terminal (inside the project folder):

```
git init
git add .
git commit -m "Stage 1: data pipeline, baseline model, validator and backtest"
git branch -M main
git remote add origin https://github.com/bernardfrimpong040-pixel/flu-forecasting-sirs.git
git push -u origin main
```

The metadata file points to this repository, so it must exist before the first submission.

---

## Part 3 — Check your understanding (5 minutes, write the answers in your notes)

Answer these in your own words before reading on. They are the kind of reasoning the paper's discussion section needs.

1. In the backtest, 95% coverage for the US is 0.91 one week out but 0.74 four weeks out. What assumption in the model breaks down further ahead? *(Hint: is this week's change in admissions independent of last week's change during an epidemic?)*
2. Look at `03_backtest_us_forecasts.png`. Why is the blue median always one or two weeks behind the black line?
3. Why does `01_download_data.py` save a dated copy of the data every week, instead of just overwriting one file?

Send me your answers and I'll give you feedback, like we did with the earlier projects.

---

## Part 4 — Submit to FluSight

### One-time setup (tonight)

1. Go to https://github.com/cdcepi/FluSight-forecast-hub and click **Fork** (top right) → **Create fork**. You now have your own copy at `github.com/bernardfrimpong040-pixel/FluSight-forecast-hub`.
2. In a terminal opened in your **Documents** folder (not inside the project), download your fork. `--depth 1` downloads only the latest version, which is much smaller:

```
cd $HOME\Documents
git clone --depth 1 https://github.com/bernardfrimpong040-pixel/FluSight-forecast-hub.git
```

You now have two folders side by side: `flu-forecasting-sirs` (your project) and `FluSight-forecast-hub` (your fork of the CDC hub).

### Wednesday (after about 1 PM Eastern, before 11 PM Eastern)

**Step A — make the forecast with the new data.** In the project folder:

```
.venv\Scripts\activate
python scripts/01_download_data.py
python scripts/03_baseline_forecast.py
python scripts/04_validate_submission.py
```

Check that script 01 shows the latest week as **2026-10-17**, that script 03 prints **no WARNING**, and that script 04 ends with "All checks passed".

**Step B — save the week's work to your own repo:**

```
git add .
git commit -m "Forecast for reference date 2026-10-24"
git push
```

**Step C — bring your fork up to date.** On your fork's GitHub page, click **Sync fork** → **Update branch**. Then:

```
cd $HOME\Documents\FluSight-forecast-hub
git pull
```

**Step D — copy the files into the fork on a new branch:**

```
git checkout -b BFrimpong-2026-10-24
New-Item -ItemType Directory -Force model-output\BFrimpong-baseline
Copy-Item ..\flu-forecasting-sirs\model-output\BFrimpong-baseline\2026-10-24-BFrimpong-baseline.csv model-output\BFrimpong-baseline\
Copy-Item ..\flu-forecasting-sirs\model-metadata\BFrimpong-baseline.yml model-metadata\
git add model-output\BFrimpong-baseline model-metadata\BFrimpong-baseline.yml
git commit -m "BFrimpong-baseline: metadata and forecast for 2026-10-24"
git push -u origin BFrimpong-2026-10-24
```

(The metadata file is copied only in the first week. From the second week on, copy just the new forecast file.)

**Step E — open the pull request.** On your fork's GitHub page a yellow banner appears: **Compare & pull request**. Click it, check that the base is `cdcepi/FluSight-forecast-hub` / `main`, and use:

- **Title:** `BFrimpong-baseline submission 2026-10-24`
- **Description:**

```
New team: BFrimpong (Bernard Frimpong, independent).
This PR adds model metadata for BFrimpong-baseline and its first forecast
(reference date 2026-10-24, target wk inc flu hosp, horizons 0-3, all 53 locations).
BFrimpong-baseline is a reference model (baseline_model: true, designated_model: false).
A mechanistic SIRS model from the same team will follow in later weeks.
```

Click **Create pull request**. The hub's automatic checks start within a minute and post their result as a comment on the pull request. Green means valid. If anything fails, copy the message to me.

---

## Part 5 — The weekly routine (every Wednesday until May 26, 2027)

| Time (Eastern) | Action |
| --- | --- |
| After ~1 PM | Project folder: run scripts 01, 03, 04 |
| | `git add .` → `git commit -m "Forecast for reference date YYYY-MM-DD"` → `git push` |
| | Fork: **Sync fork** on GitHub → `git pull` → new branch `BFrimpong-YYYY-MM-DD` |
| | Copy the new forecast file only → commit → push → open pull request |
| Before 11 PM | Confirm the pull request checks are green |

The reference date is always the Saturday after the Wednesday. Script 03 prints it for you.

---

## Next: Stage 2

A statistical growth model: instead of assuming next week equals this week, it estimates whether admissions are growing or shrinking and by how much. The backtest above shows exactly why this matters — the flat baseline misses every rise and every fall.
