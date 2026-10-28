# Stage 4 Guide — School Holidays and the Turning Point

**Goal of Stage 4:** explain and forecast the turning points that Stages 1–3 all missed. Testing your Stage 3 idea (learn the susceptible pool from "growth vs cumulative admissions") showed that growth does **not** slow gradually before the peak: it accelerates and then collapses at a school break. So Stage 4 adds school holidays to the SIRS model.

**First live submission: Wednesday, November 4, 2026** (reference date Nov 7), together with the Stage 3 SIRS model. On Oct 28 you still submit only the baseline and trend (STAGE2_GUIDE, Part 3).

---

## Part 1 — What we found, and what changed

### Your idea, tested

In an SIR model, growth = γ(R₀ s − 1), and s falls as cumulative admissions H rise, so weekly growth plotted against H should slope down in a straight line. The US data:

| Season | Weekly log growth, 3 weeks before the peak → first week after |
| --- | --- |
| 2023–24 | 0.32, 0.43, 0.32 → **−0.11** |
| 2024–25 | 0.52, 0.58, 0.33 → **−0.22** |
| 2025–26 | 0.64, 0.58, 0.13 → **−0.35** |

Growth stayed high, then fell off a cliff. No gradual slope appears before the turn, so the idea can't predict the peak in time. That's a genuine finding, and the paper reports it.

### What the turns line up with

| Season | Week most states peaked | Follows |
| --- | --- | --- |
| 2022–23 | Dec 3 (24 of 52) | Thanksgiving break |
| 2023–24 | Dec 30 (27 of 52) | Winter break |
| 2024–25 | Feb 8 (20 of 52), after a dip on Jan 4 | Winter-break dip, rebound after schools reopened |
| 2025–26 | Jan 3 (37 of 52) | Winter break |

### The model in plain words

The Stage 3 SIRS model, plus two things:

1. **Less transmission during school breaks.** β(day) = β_school × 0.8 on holiday days (Wednesday–Sunday of Thanksgiving week; December 21 to January 3), and β_school on other days. Children mix much less when schools are closed.
2. **A one-week lag.** People are admitted to hospital about 7 days after infection, so a break starting Dec 21 shows up in admissions from about Dec 28.

Because the last 3 weeks of growth may already include holiday days, the measured R_t is divided by the average holiday factor behind it, which gives the term-time transmission.

| New or changed file | What it does |
| --- | --- |
| `scripts/holiday_sirs_model.py` | The Stage 4 model (new) |
| `scripts/10_holiday_forecast.py` | Weekly file for the Stage 4 model (new) |
| `scripts/11_backtest_holiday.py` | Tunes and tests Stage 4 against Stages 1–3 (new) |
| `model-metadata/BFrimpong-sirs_hol.yml` | Registration, **designated for the CDC ensemble** (new) |
| `scripts/common.py` | Adds the Stage 4 model's name and folders |

---

## Part 2 — Run it

Unzip over your project, then:

```
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/01_download_data.py
python scripts/03_baseline_forecast.py
python scripts/06_trend_forecast.py
python scripts/08_sirs_forecast.py
python scripts/10_holiday_forecast.py
python scripts/04_validate_submission.py
python scripts/11_backtest_holiday.py
python scripts/11_backtest_holiday.py --tune
```

The last command takes about 25 minutes.

**What you should see**

| Script | Expected result |
| --- | --- |
| 10 | `kappa = 0.3, holiday factor = 0.8, lag = 7 days` |
| 04 | Four blocks (baseline, sirs, sirs_hol, trend), all PASS |
| 11, first table | Peak weeks: Dec 3 (24), Dec 30 (27), Feb 8 (20), Jan 3 (37) |
| 11, overall | trend **1.032**, SIRS **0.997**, holiday SIRS **0.812** |
| 11, phases | holiday SIRS: growth **0.742**, peak **0.672**, decline **0.997** |
| 11 --tune | best pair on the tuning seasons and on all three: κ = 0.3, factor 0.8 |

Open `results\07_holiday_us_forecasts.png` and `results\08_peak_weeks.png`.

---

## Part 3 — Weekly routine from Wednesday Nov 4 (four models)

**Step A — forecasts** (after about 1 PM Eastern):
```
.venv\Scripts\activate
python scripts/01_download_data.py
python scripts/03_baseline_forecast.py
python scripts/06_trend_forecast.py
python scripts/08_sirs_forecast.py
python scripts/10_holiday_forecast.py
python scripts/04_validate_submission.py
```
Check: latest week **2026-10-31**, no WARNING, "All checks passed" for all four models.

**Step B — your repo:**
```
git add .
git commit -m "Forecasts for reference date 2026-11-07 (baseline, trend, sirs, sirs_hol)"
git push
```

**Step C — submit in the browser:**
1. Fork → **Sync fork** (click **Discard commits** if offered).
2. Branch dropdown → `BFrimpong-2026-11-07` → **Create branch from main**.
3. **First week only:** **model-metadata** → **Upload files** → both `BFrimpong-sirs.yml` and `BFrimpong-sirs_hol.yml` → commit to the branch.
4. Top level → **model-output** → **Upload files** → drag in the **folders** `BFrimpong-sirs` and `BFrimpong-sirs_hol` → commit.
5. **model-output/BFrimpong-baseline** → upload only `2026-11-07-BFrimpong-baseline.csv` → commit.
6. **model-output/BFrimpong-trend** → upload only `2026-11-07-BFrimpong-trend.csv` → commit.
7. **Contribute** → **Open pull request**. Title: `BFrimpong submissions 2026-11-07`. Description:
```
Weekly forecasts for reference date 2026-11-07.
Adds two models with their metadata:
- BFrimpong-sirs: SIRS with susceptible depletion (RK4), non-designated
- BFrimpong-sirs_hol: SIRS with school-holiday transmission and a 7-day admission lag, designated for the ensemble
Retrospective relative WIS of BFrimpong-sirs_hol vs our baseline: 0.783 (2023-24), 0.747 (2024-25), 0.812 (2025-26, held out).
```
8. **Files changed** must show exactly 6 files: 2 metadata files and 4 forecast files.

From Nov 11 on, skip step 3 and upload the four new forecast files only, each into its own folder.

**Important for the folders in step 4:** check each folder contains **only** `2026-11-07-...csv`. Delete any older practice files (for example `2026-10-31-...`) from your local `BFrimpong-sirs` and `BFrimpong-sirs_hol` folders before dragging them in. The hub rejects files for closed rounds.

---

## Part 4 — Check your understanding

### Question 1: Why did testing "growth vs cumulative admissions" fail, and what did it reveal?

**Step 1: The theory.** In SIR, growth = γ(R₀ s − 1), and s = 1 − κH/H̄. Substitute the second into the first and expand: growth = γ(R₀ − 1) − γR₀κ (H/H̄). Is this a straight line in H? What is its slope, and is it positive or negative?

**Step 2: The data.** In the Part 1 table, as H rises towards the peak, does weekly growth go down steadily, stay level, or go up? Write the three seasons' numbers in order.

**Step 3: Compare.** Does the data match the line from Step 1 before the peak? What happens right after the peak?

**Step 4: Think it through.** For growth to rise while susceptibles are being used up, something else in growth = γ(R₀ s − 1) must be increasing. Which symbol, and what real-world things could make it rise in November and December (think weather, schools, travel)?

**Step 5: Why it matters.** Why can't a method that only measures the slope of growth against H give a warning in time, if the turn happens in one week?

### Question 2: How does the holiday factor turn the epidemic? (Show every step)

Use the US numbers from Stage 3 at Dec 27, 2025: R_t = 1.260 and s_now = 0.910 (with κ = 0.3).

**Step 1: R during the break.** On holiday days transmission is multiplied by 0.8. The effective reproduction number on a holiday is roughly R_holiday = R_term × 0.8 × (s ÷ s_now).
Assume, for a rough calculation, that the measured R_t = 1.260 is term-time transmission and s ≈ s_now. R_holiday = 1.260 × 0.8 = ____.
Is that above or below 1? So during the break, do infections grow or shrink?

**Step 2: How much factor would be needed** to bring R exactly to 1? factor = 1 ÷ 1.260 = ____. Compare it with 0.8.

**Step 3: The lag.** The break starts Dec 21. With a 7-day lag, from which date do admissions start to fall? Which reported week is the first to show it? Compare with the real peak week (ending Jan 3).

**Step 4: After the break.** On Jan 4 the factor returns to 1. If s has hardly changed, what happens to R, and what does the model predict for mid-January? Look at the right-hand panel of `07_holiday_us_forecasts.png` and find that bump.

**Step 5: Which seasons rebounded?** Use the peak-week table: in which season did the epidemic really rise again after the break? In which did it not?

### Question 3: Is the holiday effect believable, or did we overfit?

**Step 1: Count the evidence.** How many settings were tuned in Stage 4, and how many seasons were they tuned on?

**Step 2: The test.** The chosen pair (0.3, 0.8) scored 0.812 on 2025–26, a season never used for tuning. Turn that into "% better than baseline". Compare with Stage 3 (0.997) on the same season.

**Step 3: Robustness.** Look at the full grid in `results\tuning_grid_holiday.csv`. For each κ (0.3, 0.4, 0.5) and each season, which holiday factor was best? Is the answer always the same? Why does that make overfitting less likely?

**Step 4: The prospective test.** Thanksgiving 2026 is November 26 and the winter break starts December 21. If the holiday effect is real, what should happen to admissions in the weeks ending Dec 5 and Jan 2? Write a one-sentence prediction now. It's timestamped in your repo before the data exist.

**Step 5: Limitations.** Real school calendars vary by state and district, and holidays also change travel, testing and hospital behaviour. Name one way the paper could check that schools, not something else, cause the drop.

Write each answer as a short paragraph, with full working for Question 2, and send them for feedback.

---

## Next

- **Learning the rebound:** how much growth returns after the break (it did in 2024–25, not in 2025–26).
- **Uncertainty:** ensemble forecasts across plausible κ and holiday factors, so the ranges reflect what we don't know.
