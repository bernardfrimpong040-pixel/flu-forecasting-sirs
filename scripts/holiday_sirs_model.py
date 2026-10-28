"""
holiday_sirs_model.py - the Stage 4 model: SIRS with school-holiday transmission.

WHY THIS STAGE EXISTS
---------------------
In every season since 2022 the national epidemic turned right after a school
holiday: Thanksgiving in 2022-23, the Christmas break in 2023-24 and 2025-26, and
in 2024-25 a dip over Christmas followed by a second rise once schools reopened.
Weekly growth kept ACCELERATING right up to those turns, so the gradual
"susceptibles run out" effect of Stage 3 cannot explain them. A sudden drop in
contacts between children when schools close can.

THE MODEL IN PLAIN WORDS
------------------------
Exactly the Stage 3 SIRS model, with two additions:

1. Transmission is lower during school holidays:
        beta(day) = beta_school * (HOLIDAY_FACTOR if the day is a holiday else 1)
   Holidays used (typical US K-12 calendar):
        Thanksgiving: Wednesday before to the Sunday after the 4th Thursday of November
        Winter break: December 21 to January 3
   HOLIDAY_FACTOR = 0.8 means 20% less transmission during the break.

2. Hospital admissions lag infections by LAG_DAYS = 7 days (a few days of
   incubation, then a few days of illness before admission). So a break that
   starts on December 21 shows up in admissions from about December 28.

How beta_school is found: the 3-week growth rate gives R_t as in Stage 3, but that
growth happened while the holiday factor may already have applied. So the
measured R_t is divided by the average holiday factor over the infection days
behind those 3 weeks of admissions, giving the "school-term" transmission.

Tuned on past seasons with the same rule as Stages 2 and 3 (see 11_backtest_holiday.py):
KAPPA and HOLIDAY_FACTOR.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd

import baseline_model
import common
import sirs_model
import trend_model

GAMMA, OMEGA, DT = sirs_model.GAMMA, sirs_model.OMEGA, sirs_model.DT
KAPPA = 0.3              # share of season-start susceptibles a typical season uses (tuned)
HOLIDAY_FACTOR = 0.8     # transmission during school holidays, relative to term time (tuned)
LAG_DAYS = 7             # days from infection to hospital admission
WINDOW = 3               # weeks used for the growth rate (same as Stages 2 and 3)


def thanksgiving_day(year):
    """US Thanksgiving: the 4th Thursday of November (as a pandas Timestamp)."""
    first = date(year, 11, 1)
    return pd.Timestamp(first + timedelta(days=(3 - first.weekday()) % 7 + 21))


def is_school_holiday(day):
    """True on Thanksgiving break days and winter-break days (typical US K-12 calendar)."""
    if (day.month == 12 and day.day >= 21) or (day.month == 1 and day.day <= 3):
        return True                                            # winter break
    if day.month == 11:
        thursday = thanksgiving_day(day.year).date()
        if thursday - timedelta(days=1) <= day <= thursday + timedelta(days=3):
            return True                                        # Thanksgiving break (Wed-Sun)
    return False


def holiday_multiplier(day, factor):
    return factor if is_school_holiday(day) else 1.0


def simulate_weekly_admissions(last_week_end, admissions_last_week, growth_rate, season_so_far,
                               typical_total, kappa, factor, weeks=4):
    """Median admissions for the next `weeks` weeks from the holiday SIRS model.

    Time in the simulation is INFECTION time. Admissions on a calendar day are the
    infections from LAG_DAYS earlier, so the simulation starts LAG_DAYS before the
    middle of the last observed week.
    """
    mid_week = last_week_end - timedelta(days=3.5)
    start = mid_week - timedelta(days=LAG_DAYS)               # infection-time origin

    # Average holiday factor behind the measured growth: infections that produced the
    # last 3 weeks of admissions happened about LAG_DAYS earlier.
    recent_days = [last_week_end - timedelta(days=LAG_DAYS + k) for k in range(7 * WINDOW)]
    recent_factor = np.mean([holiday_multiplier(d.date(), factor) for d in recent_days])

    r_t = np.clip(1 + (growth_rate / 7) / GAMMA, sirs_model.R_MIN, sirs_model.R_MAX)
    s_now = max(1 - kappa * season_so_far / typical_total, sirs_model.S_MIN)
    beta_now = GAMMA * r_t / s_now                    # transmission behind recent growth
    beta_school = beta_now / recent_factor            # term-time transmission
    scale = typical_total / kappa
    rate_now = max(admissions_last_week, 0.5) / 7
    beta_at_start = beta_school * holiday_multiplier(start.date(), factor)
    i_now = rate_now / (scale * beta_at_start * s_now)
    state = np.array([s_now, i_now, max(1 - s_now - i_now, 0.0), 0.0])

    def advance(state, t):
        today = (start + timedelta(days=t)).date()
        return sirs_model.rk4_step(state, beta_school * holiday_multiplier(today, factor), DT)

    t = 0.0
    for _ in range(int(round(3.5 / DT))):             # to the end of the last observed week
        state = advance(state, t)
        t += DT
    totals = []
    for _ in range(weeks):
        before = state[3]
        for _ in range(int(round(7 / DT))):
            state = advance(state, t)
            t += DT
        totals.append(scale * (state[3] - before))
    return np.array(totals)


def forecast_one_location(location_rows, reference_date, kappa=KAPPA, factor=HOLIDAY_FACTOR):
    """Quantile forecasts for one location. Returns a list of row dictionaries."""
    rows_sorted = location_rows.sort_values("date")
    last = rows_sorted.iloc[-1]
    last_date = last["date"].date()

    typical_total = sirs_model.typical_season_total(rows_sorted, last["date"])
    in_season = rows_sorted[rows_sorted["date"] >= sirs_model.season_start(last["date"])]
    season_so_far = in_season["value"].sum()
    rate = trend_model.growth_rate(rows_sorted, WINDOW)

    weeks_needed = (reference_date + timedelta(weeks=max(common.HORIZONS)) - last_date).days // 7
    if np.isnan(typical_total) or typical_total <= 0:
        medians = np.full(weeks_needed, last["value"])
    else:
        medians = simulate_weekly_admissions(last["date"], last["value"], rate, season_so_far,
                                             typical_total, kappa, factor, weeks=weeks_needed)
    z_medians = np.log(medians + 1)

    recent = rows_sorted[rows_sorted["date"] > last["date"] - timedelta(weeks=baseline_model.HISTORY_WEEKS)]
    changes = baseline_model.log_changes(recent)
    one_week_quantiles = np.quantile(np.concatenate([changes, -changes]), common.QUANTILE_LEVELS)

    out = []
    for horizon in common.HORIZONS:
        target_end_date = reference_date + timedelta(weeks=horizon)
        steps = (target_end_date - last_date).days // 7
        values = np.exp(z_medians[steps - 1] + np.sqrt(steps) * one_week_quantiles) - 1
        values = np.maximum.accumulate(np.maximum(np.round(values), 0))
        for level, value in zip(common.QUANTILE_LEVELS, values):
            out.append({
                "reference_date": reference_date.isoformat(),
                "target": common.TARGET,
                "horizon": horizon,
                "target_end_date": target_end_date.isoformat(),
                "location": location_rows["location"].iloc[0],
                "output_type": "quantile",
                "output_type_id": level,
                "value": int(value),
            })
    return out


def make_forecast(data, reference_date, locations, kappa=KAPPA, factor=HOLIDAY_FACTOR):
    """Forecasts for every location, using only data dated before the reference week."""
    cutoff = pd.Timestamp(reference_date - timedelta(weeks=1))
    usable = data[data["date"] <= cutoff]
    all_rows = []
    for location in locations:
        location_rows = usable[usable["location"] == location]
        if len(location_rows) < 10:
            continue
        all_rows.extend(forecast_one_location(location_rows, reference_date, kappa, factor))
    return pd.DataFrame(all_rows)
