# Stage 5 Guide — Scoring the Live Season

**Goal of Stage 5:** find out how our models are doing **live**, on the forecasts we actually submitted, and compare them with the CDC's own ensemble. The paper's main result will come from this, not from the backtests.

---

## Part 1 — What changed

| New or changed file | What it does |
| --- | --- |
| `scripts/13_score_live.py` | Downloads our submitted forecasts (and the CDC ensemble and baseline) from the hub, scores them, and measures backfill (new) |
| `scripts/common.py` | Caps every forecast at 0.1% of the location's population (the hub's new rule) |
| `scripts/03, 06, 08, 10` | Apply the cap before saving |
| `scripts/04_validate_submission.py` | Checks the 0.1% rule |

The script scores the **hub's copy** of our files. That copy is the official record of what we submitted, so practice files on your computer are never counted. Downloads are saved in `data/hub/`, and each file is downloaded only once.

### Results so far (data through the week ending Nov 14)

| Model | Weeks | Forecasts scored | vs our baseline | vs CDC ensemble |
| --- | --- | --- | --- | --- |
| Baseline | 4 | 530 | 1.000 | 2.114 |
| Trend | 3 | 318 | **0.824** | 1.601 |
| SIRS | 2 | 159 | 0.972 | 1.485 |
| Holiday SIRS | 2 | 159 | 0.992 | 1.516 |
| CDC ensemble | 4 | 530 | 0.473 | 1.000 |

**What it means:**
- **The CDC ensemble is well ahead of all our models** so far: our WIS is 1.5–2.1 times larger on the same forecasts.
- **Our forecasts start too low.** The epidemic grew 15–30% a week, and every forecast started below where the data now are.
- **Backfill is part of the reason.** The newest week we forecast from has later been revised **up by 6–9%** every time (4,698 → 5,100; 6,006 → 6,529; 8,245 → 8,711; 9,395 → 10,112).
- **The SIRS models have barely been tested.** They have only two weeks of forecasts, all during steady growth. Their real test is the turning points.

---

## Part 2 — Run it

Unzip over your project, then:
```
.venv\Scripts\activate
python scripts/01_download_data.py
python scripts/13_score_live.py
```
It takes about 1 minute the first time, because it downloads around 25 files, and seconds after that.

**What you should see:**
- A "Not on the hub" line listing weeks a model didn't submit (for example trend 2026-10-24) or that aren't merged yet. That's normal.
- The live table above. The numbers grow as more weeks are scored.
- The backfill table.
- `Saved: results\10_live_us_forecasts.png`

---

## Part 3 — The weekly routine from now on

Every Wednesday, after the reminder arrives:
```
.venv\Scripts\activate
python scripts/01_download_data.py
python scripts/03_baseline_forecast.py --reference-date YYYY-MM-DD
python scripts/06_trend_forecast.py --reference-date YYYY-MM-DD
python scripts/08_sirs_forecast.py --reference-date YYYY-MM-DD
python scripts/10_holiday_forecast.py --reference-date YYYY-MM-DD
python scripts/04_validate_submission.py
python scripts/13_score_live.py
git add .
git commit -m "Forecasts for reference date YYYY-MM-DD (baseline, trend, sirs, sirs_hol)"
git push
```
`YYYY-MM-DD` is that week's Saturday. The reminder fills it in, together with the four upload links and the pull-request link.

**Coming dates:**

| Wednesday | Reference date | Note |
| --- | --- | --- |
| Nov 25 | 2026-11-28 | Day before Thanksgiving |
| Dec 2 | 2026-12-05 | |
| Dec 9 | 2026-12-12 | First data for the week ending Dec 5, **the Thanksgiving test** |

---

## Part 4 — Check your understanding

### Question 1: Reading the live table
**Step 1.** Relative WIS of the trend model vs our baseline = 0.824. % better = (1 − 0.824) × 100 = ____ %.
**Step 2.** The CDC ensemble vs our baseline = 0.473. % better = ____ %. Which is better, the trend model or the ensemble? ____
**Step 3.** Holiday SIRS vs CDC ensemble = 1.516. In words: what does a number above 1 mean here?
**Step 4.** Holiday SIRS has 159 forecasts scored; the baseline has 530. Why fewer? (Hint: when did the SIRS models start, and which horizons of a recent forecast already have data?)
**Step 5.** In words: why is it too early to say the mechanism does not help?

### Question 2: Backfill (show every step)
**Step 1.** Week ending Nov 7: first reported 9,395, now 10,112. Change = 10,112 − 9,395 = ____. % change = ____ ÷ 9,395 × 100 = ____ %.
**Step 2.** Do the same for Oct 24 (6,006 → 6,529): ____ %.
**Step 3.** Average of the four revisions (8.6, 8.7, 5.7 and your Step 1 answer): (8.6 + 8.7 + 5.7 + ____) ÷ 4 = ____ %.
**Step 4.** Our baseline's median = the last reported value. If the last reported value is 11,513 and it will be revised up by the average from Step 3, the "true" current value is about 11,513 × (1 + ____ ÷ 100) = ____.
**Step 5.** In words: if every forecast starts from a value that is too low, what happens to WIS? Could you correct for it, and what is the risk if revisions turn out smaller in some weeks?

### Question 3: The Thanksgiving test
**Step 1.** Thanksgiving is Thursday, Nov 26. The holiday break runs Wednesday Nov 25 to Sunday Nov 29. With the 7-day lag, admissions are affected from ____ to ____.
**Step 2.** Which reported week (weeks end on Saturday) contains most of those days? The week ending ____.
**Step 3.** Your Nov 12 holiday-SIRS forecast: week ending Nov 28 = 14,428, week ending Dec 5 = 13,809. Change = ____ (%). The plain SIRS: 13,782 → 14,532. Change = ____ (%).
**Step 4.** Write your prediction in one sentence before the data arrive on Dec 9: will the US week ending Dec 5 be lower, about the same, or higher than the week ending Nov 28?
**Step 5.** In words: if admissions keep rising through Dec 5, does that disprove the holiday effect? Name one other thing that could hide it, such as backfill or a growing epidemic.

Send your answers here or as a PDF, with full working for Question 2.

---

## Next

- **Stage 5b:** backfill correction. Estimate how much the newest week is usually revised, and adjust it before forecasting.
- **Dec 9:** the first live check of the holiday effect.
