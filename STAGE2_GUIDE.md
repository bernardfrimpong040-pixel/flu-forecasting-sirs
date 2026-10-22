# Stage 2 Guide — The Damped Growth Model

**Goal of Stage 2:** fix the baseline's two-week lag by following how fast admissions are rising or falling, test the fix fairly on a season it never saw, and start submitting it live.

**First live submission of the trend model: Wednesday, October 28, 2026, by 11 PM Eastern** (reference date Saturday, October 31), alongside the baseline.

---

## Part 1 — What changed

| New or changed file | What it does |
| --- | --- |
| `scripts/trend_model.py` | The Stage 2 model (new) |
| `scripts/scoring.py` | WIS and coverage in one shared place (new) |
| `scripts/06_trend_forecast.py` | Makes the weekly trend file (new) |
| `scripts/07_backtest_compare.py` | Tunes and tests trend vs baseline (new) |
| `model-metadata/BFrimpong-trend.yml` | The trend model's registration for the hub (new) |
| `scripts/04_validate_submission.py` | Now checks the newest file of **every** model and each one's own metadata |
| `scripts/common.py` | Adds the trend model's name and folders |
| `README.md` | Stage 2 results |

Nothing in the Stage 1 scripts' behaviour changed. The baseline still produces exactly the same files.

### The model in plain words

1. **Measure the current growth rate.** On the log scale, steady growth is a straight line. Fit the best straight line through the last 3 weeks of log(admissions + 1). With weeks at positions −1, 0, 1, the slope is simply

   *r* = (*z*_newest − *z*_oldest) ÷ 2.

   Example with this week's data: the national series was 3,494 → 4,044 → 4,698, so
   *r* = (ln 4,699 − ln 3,495) ÷ 2 = (8.455 − 8.159) ÷ 2 = 0.148, which is about 16% growth per week (e^0.148 = 1.160).

2. **Carry it forward, damped.** Each extra week keeps only φ = 0.4 of the previous week's growth. The median *k* weeks after the last data point moves by

   *r* × (φ + φ² + … + φᵏ).

   For *k* = 1, 2, 3, 4 that is *r* × 0.40, 0.56, 0.62, 0.65. Growth adds up quickly at first and then levels off, because the series 0.4 + 0.16 + 0.064 + … can never exceed 0.4 ÷ (1 − 0.4) = 0.67.

3. **Same range as the baseline,** centred on the new median. So any difference in score between the two models comes from the trend alone.

---

## Part 2 — Run it

In the project folder, after unzipping over your existing files:

```
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/01_download_data.py
python scripts/03_baseline_forecast.py
python scripts/06_trend_forecast.py
python scripts/04_validate_submission.py
python scripts/07_backtest_compare.py
python scripts/07_backtest_compare.py --tune
```

The last command redoes the whole tuning grid. It takes several minutes; let it run.

**What you should see**

| Script | Expected result |
| --- | --- |
| 06 | `Model settings: window = 3 weeks, phi = 0.4`. Tonight's US median for the week ending Oct 31 is about 5,100, above the baseline's 4,698, because admissions are still rising. |
| 04 | Two blocks, one per model, every line PASS, ending "All checks passed" |
| 07 | Overall relative WIS **1.032**; by phase: growth **0.831**, peak **1.009**, decline **1.110** |
| 07 --tune | Eight settings; best on the tuning seasons is window 3, phi 0.5; best on all three seasons is window 3, phi 0.4 |

Then open `results/04_compare_us_forecasts.png` and look closely at early January 2026.

Tonight's files use reference date Oct 24. They are practice only; next Wednesday the scripts produce the Oct 31 files from the new data.

---

## Part 3 — Weekly routine from Wednesday Oct 28 (two models)

**Step A — forecasts** (after about 1 PM Eastern):
```
.venv\Scripts\activate
python scripts/01_download_data.py
python scripts/03_baseline_forecast.py
python scripts/06_trend_forecast.py
python scripts/04_validate_submission.py
```
Check: latest week **2026-10-24**, no WARNING, and "All checks passed" for both models.

**Step B — save to your own repo:**
```
git add .
git commit -m "Forecasts for reference date 2026-10-31 (baseline and trend)"
git push
```

**Step C — submit in the browser** (same method as week 1):
1. On your fork, click **Sync fork**. If GitHub offers **Discard commits**, click it. Your week-1 files are already in the CDC hub, so nothing is lost.
2. Branch dropdown → type `BFrimpong-2026-10-31` → **Create branch from main**.
3. **First week of the trend model only:** go into the **model-metadata** folder → **Upload files** → `model-metadata\BFrimpong-trend.yml` → commit to the branch.
4. Back to the **top level** → **model-output** → **Upload files** → drag in the folder `model-output\BFrimpong-trend`. This creates it. Commit to the branch.
5. Back to **model-output** → open **BFrimpong-baseline** → **Upload files** → drag in only `2026-10-31-BFrimpong-baseline.csv`. Commit to the branch.
6. **Contribute** → **Open pull request**. Title: `BFrimpong submissions 2026-10-31`. Description:
```
Weekly forecasts for reference date 2026-10-31.
Adds a second model, BFrimpong-trend (damped log-linear growth), with its metadata.
Both models are non-designated (designated_model: false).
```
7. Before creating it, open **Files changed** and check for exactly 3 files:
   - `model-metadata/BFrimpong-trend.yml`
   - `model-output/BFrimpong-trend/2026-10-31-BFrimpong-trend.csv`
   - `model-output/BFrimpong-baseline/2026-10-31-BFrimpong-baseline.csv`

From Nov 4 onwards, skip step 3 and upload just the two new forecast files.

---

## Part 4 — Check your understanding

Work through these the same way as Stage 1. They become the Stage 2 discussion in the paper.

### Question 1: Why did the trend model win on the tuning seasons but lose on the test season?

**Step 1: Read the numbers.** Relative WIS was 0.935 (2023–24) and 0.930 (2024–25), but 1.032 on 2025–26. Say in plain words what each number means: how many percent better or worse than the baseline?

**Step 2: Look at the shapes.** In `01_national_seasons.png`, compare how fast 2025–26 rose and fell around its peak with 2023–24 and 2024–25. Which season turned most sharply?

**Step 3: Look at the data around the 2025–26 peak.**

| Week ending | Admissions |
| --- | --- |
| Dec 13 | 11,135 |
| Dec 20 | 21,057 |
| Dec 27 | 37,502 |
| Jan 3 (peak) | 42,500 |
| Jan 10 | 29,909 |
| Jan 17 | 19,731 |

Compute the weekly growth factors, as in Stage 1. How big was the jump from fast rising to fast falling in a single week?

**Step 4: Think it through.** A model whose settings are tuned on some seasons is betting that future seasons behave like them. What does the 2025–26 result tell you about that bet? Should we have picked the settings that happened to score best on 2025–26 instead? Why would that be cheating?

### Question 2: Why does the trend help most in the growth phase and hurt in the decline?

**Step 1: Read the phase table** from script 07. Growth 0.831, peak 1.009, decline 1.110. Turn each into "x% better" or "x% worse".

**Step 2: Growth phase.** Look at the "average error of the median" column: −79 for the baseline, −61 for the trend. What does a negative number mean? Which problem from Stage 1, Question 2, is this improvement fixing?

**Step 3: Decline phase.** Most decline weeks happen in March–May, when many states have small counts (often under 50 a week). Open `02_largest_states.png` and look at the right-hand side of last season's curves. Are they smooth, or bumpy? What does a 3-week slope measure on a bumpy, small-count series: the real trend, or the random bumps?

**Step 4: Connect it to Stage 1.** In Stage 1, Question 1, you found that state series carry more random noise than the national series. How does that same fact explain why the trend model struggles in the decline?

### Question 3: What exactly goes wrong at the peak?

**Step 1: Open `04_compare_us_forecasts.png`** and find early January 2026 in the right-hand panel.

**Step 2: The numbers.** The forecast made with data up to Dec 27 (for the week ending Jan 10):

| Model | Forecast median | What happened |
| --- | --- | --- |
| Baseline | 37,502 | 29,909 |
| Trend | **59,130** | 29,909 |

Where did 59,130 come from? Use the formula from Part 1: the last three weeks were 11,135, 21,057 and 37,502, and this forecast is 2 weeks after the last data point, so the damping factor is 0.5 + 0.5² = 0.75 (the test season used φ = 0.5). Work out *r*, then the median. Show every step.

**Step 3: Think it through.** On Dec 27, was there anything in the last three weeks of data that warned the peak was one week away? What would a model need to know, that the data's slope cannot tell it, to predict the turn?

**Step 4: Link to Stage 3.** In one or two sentences: what does the SIRS model contain that the trend model does not, and why should that help exactly here?

Write each answer as a short paragraph, rough is fine, and send them for feedback.

---

## Next: Stage 3

The SIRS model: susceptible people become infected, recover, and slowly lose immunity. Fitted to each state's recent admissions, it can predict a turn that the trend model cannot see, because growth must slow as susceptible people run out.
