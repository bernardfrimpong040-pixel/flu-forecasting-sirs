# Stage 4b Guide — How Much Comes Back After the Winter Break?

**Goal of Stage 4b:** fix the one big weakness of Stage 4. With full transmission back on January 4, the model predicted a second rise in mid-January. That only happened in 2024–25. We also test whether combining several model versions (an *ensemble*) helps.

**Live from Wednesday, November 4, 2026.** The Stage 4b change is built into `BFrimpong-sirs_hol`, which has not been submitted yet, so its first forecast already includes it. You still submit **four** models.

---

## Part 1 — What changed

### The rebound setting

From **January 4 to July 31**, transmission is multiplied by a new setting ρ (rho), the *rebound*:

| ρ | Meaning |
| --- | --- |
| 1.0 | Transmission fully returns after the break (the Stage 4 model) |
| **0.9** | It returns to 90% of its pre-break level (**Stage 4b, tuned**) |
| 0.8 | It stays as low as during the break |

The model measures growth from the last 3 weeks of data. Once all 3 weeks are after the break, the measured growth already includes ρ, and the model divides it back out. So **ρ only changes forecasts that cross January 4**. That's exactly where the false rebound was.

### Results (relative WIS vs baseline, lower is better)

| κ = 0.3, factor 0.8 | 2023–24 | 2024–25 | 2025–26 (test) | Tuning mean |
| --- | --- | --- | --- | --- |
| ρ = 1.0 (Stage 4) | 0.783 | 0.747 | 0.812 | 0.765 |
| **ρ = 0.9 (Stage 4b)** | **0.641** | 0.792 | **0.656** | **0.716** |
| ρ = 0.8 | 0.676 | 0.910 | 0.606 | 0.793 |

| Test season 2025–26 | Stage 4 | **Stage 4b** |
| --- | --- | --- |
| Overall | 0.812 | **0.656** |
| Growth | 0.742 | **0.706** |
| Peak | 0.672 | **0.601** |
| Decline | 0.997 | **0.710** |
| Bias in the decline | +92 | **+34** |

### Ensembles

An ensemble runs several versions of the model and combines them. We used a *mixture*: "pick a version at random, then draw from it". When versions disagree, the range gets wider.

| Ensemble | Members | Tuning mean |
| --- | --- | --- |
| A | κ = 0.3 and 0.4 (ρ = 0.9) | 0.761 |
| B | ρ = 0.8, 0.9 and 1.0 (κ = 0.3) | 0.726 |
| C | κ 0.3/0.4 × factor 0.8/0.9 | 0.769 |
| D | κ 0.3/0.4 × ρ 0.8/0.9/1.0 | 0.769 |
| *Single Stage 4b* | *κ 0.3, factor 0.8, ρ 0.9* | ***0.716*** |

No ensemble beat the single model, so the single model is submitted. This is a real result, and it goes in the paper.

| New or changed file | What it does |
| --- | --- |
| `scripts/holiday_sirs_model.py` | Adds `REBOUND = 0.9` |
| `scripts/ensemble_sirs_model.py` | Ensembles (new; used for testing only) |
| `scripts/12_backtest_rebound.py` | Tunes ρ, compares ensembles, tests Stage 4b (new) |
| `scripts/10_holiday_forecast.py` | Prints the rebound setting |
| `scripts/11_backtest_holiday.py` | Keeps ρ = 1.0 so the Stage 4 results stay the same |
| `model-metadata/BFrimpong-sirs_hol.yml` | Describes the rebound; new test score 0.656 |

---

## Part 2 — Run it

Unzip over your project, then:

```
.venv\Scripts\activate
python scripts/10_holiday_forecast.py
python scripts/04_validate_submission.py
python scripts/12_backtest_rebound.py
python scripts/12_backtest_rebound.py --tune --ensembles
```

`12` alone takes about 5 minutes. With `--tune --ensembles` it takes about 45 minutes, so leave it alone while it runs and don't click in the window.

**What you should see**

| Script | Expected result |
| --- | --- |
| 10 | `kappa = 0.3, holiday factor = 0.8, rebound = 0.9, lag = 7 days` |
| 04 | All checks passed |
| 12, overall | `Stage 4 (rebound 1.0) 0.812   Stage 4b (rebound 0.9) 0.656   Ensemble B 0.661` |
| 12, phases | Stage 4b: growth **0.706**, peak **0.601**, decline **0.710** |
| 12 --tune | best on tuning and on all three: κ = 0.3, factor = 0.8, rebound = 0.9 |
| 12 --ensembles | A 0.761, B 0.726, C 0.769, D 0.769 (tuning means) |

Open `results\09_rebound_us_forecasts.png`.

---

## Part 3 — Weekly routine with direct links (Wednesday Nov 4, reference date 2026-11-07)

**Before you start:** PR #3928 should show **Merged**: https://github.com/cdcepi/FluSight-forecast-hub/pull/3928

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
Check: latest week **2026-10-31**, no WARNING, all four models pass.

**Step B — your repo:**
```
git add .
git commit -m "Forecasts for reference date 2026-11-07 (baseline, trend, sirs, sirs_hol)"
git push
```

**Step C — submit, one link at a time:**

1. Sync: open https://github.com/bernardfrimpong040-pixel/FluSight-forecast-hub → **Sync fork** → **Update branch** (or **Discard commits**).
2. Branch: open https://github.com/bernardfrimpong040-pixel/FluSight-forecast-hub/branches → **New branch** → `BFrimpong-2026-11-07` from `main` → **Create**.
3. Metadata: open the link below. Check that the path reads `model-metadata /`, drag in `BFrimpong-sirs.yml` and `BFrimpong-sirs_hol.yml`, then **Commit changes**.
   https://github.com/bernardfrimpong040-pixel/FluSight-forecast-hub/upload/BFrimpong-2026-11-07/model-metadata
4. Baseline: open the link below, drag in only `2026-11-07-BFrimpong-baseline.csv`, then commit.
   https://github.com/bernardfrimpong040-pixel/FluSight-forecast-hub/upload/BFrimpong-2026-11-07/model-output/BFrimpong-baseline
5. Trend: open the link below, drag in only `2026-11-07-BFrimpong-trend.csv`, then commit.
   https://github.com/bernardfrimpong040-pixel/FluSight-forecast-hub/upload/BFrimpong-2026-11-07/model-output/BFrimpong-trend
6. New folders: open the link below and check that the path reads `model-output /`. Drag in the **folders** `BFrimpong-sirs` and `BFrimpong-sirs_hol`; each must contain **only** its `2026-11-07-...csv` file. Then commit.
   https://github.com/bernardfrimpong040-pixel/FluSight-forecast-hub/upload/BFrimpong-2026-11-07/model-output
7. Pull request: open the link below → **Create pull request**. Title: `BFrimpong submissions 2026-11-07`.
   https://github.com/cdcepi/FluSight-forecast-hub/compare/main...bernardfrimpong040-pixel:FluSight-forecast-hub:BFrimpong-2026-11-07

   Description:
```
Weekly forecasts for reference date 2026-11-07.
Adds two models with their metadata:
- BFrimpong-sirs: SIRS with susceptible depletion (RK4), non-designated
- BFrimpong-sirs_hol: SIRS with school-holiday transmission, a 7-day admission lag and partial rebound after the winter break, designated for the ensemble
Retrospective relative WIS of BFrimpong-sirs_hol vs our baseline: 0.641 (2023-24), 0.792 (2024-25), 0.656 (2025-26, held out).
```
8. **Files changed** must show **6 files**: `model-metadata` with 2 yml files, and `model-output` with 4 csv files, one in each folder. Then wait for the green ✅.

**From Nov 11 on:** skip step 3, replace `2026-11-07` with that week's Saturday everywhere, and upload each csv through its own folder link (`.../model-output/BFrimpong-sirs` and `.../model-output/BFrimpong-sirs_hol`).

---

## Part 4 — Check your understanding

### Question 1: What does the rebound do, and why does it only matter around January 4?

Use the Stage 4 trace for the US (data to Dec 27, 2025): R_t = 1.260, s_now = 0.910, and on Jan 7, s = 0.808.

**Step 1: R after schools reopen.** R_after = 1.260 × ρ × (s ÷ s_now).
- s ÷ s_now = 0.808 ÷ 0.910 = ____
- ρ = 1.0: R_after = 1.260 × 1.0 × ____ = ____
- ρ = 0.9: R_after = 1.260 × 0.9 × ____ = ____
- ρ = 0.8: R_after = 1.260 × 0.8 × ____ = ____
- Which values of ρ give a rebound (R above 1)? ____

**Step 2: The cancelling.** In February, all of the last 3 weeks are after the break, so every recent day has multiplier ρ.
- The model computes β_school = β_now ÷ (average multiplier) = β_now ÷ ____
- For future days it uses β_school × ρ = (β_now ÷ ρ) × ρ = ____
- In words: why does ρ make no difference to a forecast made in February?

**Step 3: Look at the figure.** In `09_rebound_us_forecasts.png`, bottom row (2025–26): how high does the mid-January bump go with ρ = 1.0? ____ With ρ = 0.9? ____ Is the bump completely gone? ____

### Question 2: Who wins and who loses?

**Step 1: % change for each season** (Stage 4 → Stage 4b). % change = (new − old) ÷ old × 100.
- 2023–24: (0.641 − 0.783) ÷ 0.783 × 100 = ____ %
- 2024–25: (0.792 − 0.747) ÷ 0.747 × 100 = ____ %
- 2025–26: (0.656 − 0.812) ÷ 0.812 × 100 = ____ %

**Step 2: Why does 2024–25 get worse?** Look at the top row of the figure. In which month did 2024–25 reach its real peak? ____ What does ρ = 0.9 do to transmission in that month? ____

**Step 3: The fair-test rule.** ρ = 0.8 scored **0.606** on the test season, better than ρ = 0.9 (0.656). Why do we still report ρ = 0.9? Which seasons were used to choose? ____ What would it mean for the paper if we switched to 0.8 after seeing the test score?

**Step 4: The decline.** Bias in the decline went from +92 to +34. In words: what does a positive bias mean (forecast too high or too low), and why does a smaller rebound shrink it?

### Question 3: Why didn't the ensembles help?

**Step 1: Read the table.** Write the tuning mean of each ensemble and of the single model. Which is lowest? ____

**Step 2: Ensembles A, C and D include κ = 0.4.** From the Stage 4b grid, κ = 0.4 (factor 0.8, ρ 0.9) scored ____ in 2024–25, compared with ____ for κ = 0.3. From the Stage 3 table, 2024–25 was ____ times a typical season. In words: why does a large κ do badly in a large season?

**Step 3: Coverage.** In the test season the Stage 4b US 95% intervals contained the truth **100%** of the time (aim: 95%).
- Is 100% a sign the intervals are too narrow or too wide? ____
- A mixture makes intervals wider still. Would that help or hurt WIS here? ____

**Step 4: When would an ensemble help?** In words: think of a season where we really don't know which κ is right (Stage 3 showed it changes by season). Why might the ensemble still be worth trying live, as a non-designated model, in a later stage?

Write each answer as a short paragraph, with full working for Questions 1 and 2, and send them for feedback.

---

## Next

- **Weekly submissions** with four models from Nov 4.
- **Thanksgiving (Nov 26)** and the **winter break (Dec 21)**: the first live test of the holiday effect.
- **Possible Stage 5:** state-specific school calendars, or tighter intervals for the national forecast (US coverage was 100%).
