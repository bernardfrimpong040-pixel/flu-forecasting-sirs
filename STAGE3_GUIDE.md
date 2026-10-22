# Stage 3 Guide — The SIRS Model

**Goal of Stage 3:** replace "guess how fast growth fades" (Stage 2's damping) with a mechanism: an SIRS differential-equation model in which growth slows because susceptible people are used up. Test it fairly, and start submitting it live.

**First live submission of the SIRS model: Wednesday, November 4, 2026** (reference date Nov 7). On Oct 28 you submit the baseline and trend as planned in STAGE2_GUIDE; the SIRS model joins the week after, so Wednesday stays simple.

---

## Part 1 — What changed

| New or changed file | What it does |
| --- | --- |
| `scripts/sirs_model.py` | The Stage 3 model: SIRS equations solved with RK4 (new) |
| `scripts/08_sirs_forecast.py` | Makes the weekly SIRS file (new) |
| `scripts/09_backtest_sirs.py` | Tunes and tests SIRS against the baseline and trend (new) |
| `model-metadata/BFrimpong-sirs.yml` | The SIRS model's registration (new) |
| `scripts/scoring.py` | Now also holds the shared backtest helpers |
| `scripts/common.py` | Adds the SIRS model's name and folders |
| `scripts/trend_model.py` | Can now forecast more than 4 weeks after the last data (only matters if data are late) |
| `README.md` | Stage 3 results |

### The model in plain words

Think of the people who could catch flu at the start of the season as a pool, and measure everything as a fraction of that pool.

| Symbol | Meaning |
| --- | --- |
| *s* | fraction of the pool still susceptible |
| *i* | fraction currently infectious |
| *r* | fraction recovered (immune) |
| β | transmission rate: how many new infections each infectious person causes per day, per unit of *s* |
| γ = 1/3 per day | recovery rate: people stay infectious about 3 days |
| ω = 1/365 per day | immunity fades over about a year |

The SIRS equations:

  ds/dt = −β s i + ω r  
  di/dt = β s i − γ i  
  dr/dt = γ i − ω r

New infections per day = β *s* *i*. Hospital admissions are a fixed share of new infections.

**Every week, for every location, three things are set from the data:**

1. **R_t, the reproduction number**, from the same 3-week growth rate *r* as Stage 2. For an SIR model, the daily growth rate is γ(R_t − 1), so

   R_t = 1 + (*r* ÷ 7) ÷ γ.

2. **s_now, the susceptibles left.** This season's admissions so far, compared with a typical past season's total, tell us how much of the pool has been used:

   s_now = 1 − κ × (admissions so far this season) ÷ (typical season total).

   κ (KAPPA) is the share of the season-start pool that a typical season uses. It is the **only** tuned parameter.

3. **β = γ R_t ÷ s_now**, and *i* is set so the model reproduces this week's admissions.

Then the equations are solved forward 4 weeks with **RK4** (4th-order Runge–Kutta, step 0.5 day), the same method you used in your thesis work, and the new infections are added up week by week. As *s* falls, β*s* falls, so growth slows and turns by itself.

The forecast range is the baseline's, centred on the SIRS median, exactly as in Stage 2.

---

## Part 2 — Run it

Unzip over your project as before, then:

```
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/01_download_data.py
python scripts/03_baseline_forecast.py
python scripts/06_trend_forecast.py
python scripts/08_sirs_forecast.py
python scripts/04_validate_submission.py
python scripts/09_backtest_sirs.py
python scripts/09_backtest_sirs.py --tune
```

The last command takes about 10 minutes.

**What you should see**

| Script | Expected result |
| --- | --- |
| 08 | `kappa = 0.4, gamma = 1/3 per day, window = 3 weeks` |
| 04 | Three blocks (baseline, sirs, trend), all PASS, ending "All checks passed" |
| 09, first table | Season size: 2023–24 = 1.11 × typical, **2024–25 = 2.31 × typical**, 2025–26 = 0.97 × typical |
| 09, overall | trend **1.032**, SIRS **0.997**, SIRS vs trend **0.966** |
| 09, phases | SIRS vs baseline: growth **0.788**, peak **1.049**, decline **0.987** |
| 09, worked example | R_t = 1.260, s_now = 0.910 |
| 09 --tune | best on tuning seasons κ = 0.3; best on all three κ = 0.4 |

Open the two new pictures: `results\05_sirs_us_forecasts.png` and `results\06_kappa_by_season.png`.

---

## Part 3 — Weekly routine from Wednesday Nov 4 (three models)

**Step A — forecasts** (after about 1 PM Eastern):
```
.venv\Scripts\activate
python scripts/01_download_data.py
python scripts/03_baseline_forecast.py
python scripts/06_trend_forecast.py
python scripts/08_sirs_forecast.py
python scripts/04_validate_submission.py
```
Check: latest week **2026-10-31**, no WARNING, and "All checks passed" for all three models.

**Step B — save to your repo:**
```
git add .
git commit -m "Forecasts for reference date 2026-11-07 (baseline, trend, sirs)"
git push
```

**Step C — submit in the browser:**
1. On your fork: **Sync fork** (click **Discard commits** if offered).
2. Branch dropdown → type `BFrimpong-2026-11-07` → **Create branch from main**.
3. **First SIRS week only:** **model-metadata** → **Upload files** → `model-metadata\BFrimpong-sirs.yml` → commit to the branch.
4. Top level → **model-output** → **Upload files** → drag in the **folder** `model-output\BFrimpong-sirs` → commit to the branch.
5. **model-output/BFrimpong-baseline** → upload only `2026-11-07-BFrimpong-baseline.csv` → commit.
6. **model-output/BFrimpong-trend** → upload only `2026-11-07-BFrimpong-trend.csv` → commit.
7. **Contribute** → **Open pull request**. Title: `BFrimpong submissions 2026-11-07`. Description:
```
Weekly forecasts for reference date 2026-11-07.
Adds a third model, BFrimpong-sirs (SIRS with susceptible depletion, RK4), with its metadata.
All three models are non-designated (designated_model: false).
```
8. **Files changed** must show exactly 4 files: the SIRS metadata and three forecast files.

From Nov 11 on, skip step 3 and upload the three new forecast files only.

---

## Part 4 — Check your understanding

### Question 1: Compute the SIRS starting point by hand (show every step)

The worked example from script 09: US, data to Dec 27, 2025, κ = 0.3 (the test value).

| Quantity | Value |
| --- | --- |
| Growth rate *r* (from Stage 2) | 0.607 per week |
| γ | 1/3 per day |
| Admissions so far this season | 103,850 |
| Typical season total | 347,693 |

**Step 1: R_t.** Daily growth = *r* ÷ 7 = 0.607 ÷ 7 = ____. Then R_t = 1 + (daily growth) ÷ γ = 1 + ____ × 3 = ____.
In words: each infected person was infecting about ____ others.

**Step 2: s_now.** Share of a typical season already used = 103,850 ÷ 347,693 = ____.
s_now = 1 − 0.3 × ____ = ____.
In words: ____% of the season-start pool was still susceptible.

**Step 3: β.** β = γ R_t ÷ s_now = (1/3) × ____ ÷ ____ = ____ per day.

**Step 4: The turning point.** The epidemic stops growing when R_eff = R_t × (s ÷ s_now) falls to 1, that is when *s* = s_now ÷ R_t. Compute s_now ÷ R_t = ____ ÷ ____ = ____.
How far does *s* have to fall from s_now? ____. Compare that with the 0.09 used in the whole season so far. Does the model expect the turn soon, or weeks away?

**Step 5: Compare with what happened.** Script 09 printed the SIRS medians: 61,835, then 83,550, then 89,198, then 75,862. The actual numbers were 42,500, 29,909, 19,731, 16,816. In which week did the model put the peak, and in which week did it really happen?

### Question 2: Why does the best κ change from season to season?

**Step 1: Read the picture.** In `06_kappa_by_season.png`, find the κ where each season's line is lowest. Write them down: 2023–24 ≈ ____, 2024–25 ≈ ____, 2025–26 ≈ ____.

**Step 2: Read the season-size table** (first output of script 09). Copy the "actual over typical" column for each season.

**Step 3: Connect them.** Which season was much bigger than the model expected? For that season, was a small or a large κ better?

**Step 4: Think it through.** In s_now = 1 − κ × (so far ÷ typical), what happens to s_now when a season is unusually big and "so far" keeps growing past the typical total? With a large κ, does the model predict the turn too early or too late? Why does a small κ protect against that?

**Step 5: The honest result.** The rule chose κ = 0.3 on the tuning seasons, and it scored 0.997 on 2025–26. κ = 0.6 would have scored 0.658, which is 34% better than the baseline. Why can't we report 0.658 as our result? (Same principle as Stage 2, Question 1.)

### Question 3: What did the mechanism fix, and what is still missing?

**Step 1: Read the phase table** from script 09 and turn the bias numbers into words:

| Phase | Bias, baseline | Bias, trend | Bias, SIRS |
| --- | --- | --- | --- |
| Growth | −79 | −61 | −8 |
| Peak | −416 | −130 | +320 |
| Decline | +138 | +137 | +56 |

For each phase: which model's median was closest to the truth on average? Which went from too low to too high?

**Step 2: Growth.** Why does the SIRS model have almost no bias in the growth phase? Hint: compare how Stage 2 and Stage 3 carry growth forward when *s* is still close to 1.

**Step 3: Peak.** Look at the right-hand panel of `05_sirs_us_forecasts.png`. Why did it overshoot the 2025–26 peak even more than the trend model? Use your Question 1, Step 4 answer.

**Step 4: Decline.** SIRS was about the same as the baseline in the decline (0.987), while the trend model was 11% worse (1.110). Once R_t is below 1, what does the SIRS model do to admissions week after week?

**Step 5: What's missing.** The mechanism only works if the model knows how big the susceptible pool is, and κ is fixed in advance from past seasons. In one or two sentences: how could the model learn the pool size from **this** season's data as it unfolds? Hint: in an SIR model, the growth rate falls as cumulative admissions rise. What could you measure week by week? This is the idea for Stage 4.

Write each answer as a short paragraph, with full working for Question 1, and send them for feedback.

---

## Next: Stage 4

Learning the size of the susceptible pool from the current season, and turning uncertainty about it into honest forecast ranges, in place of a single fixed κ.
