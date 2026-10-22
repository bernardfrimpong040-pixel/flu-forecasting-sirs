"""
sirs_model.py - the Stage 3 mechanistic forecast: an SIRS model solved with RK4.

THE IDEA IN PLAIN WORDS
-----------------------
Stage 2 carried the recent growth rate forward and had to guess how fast it
fades (the damping phi). Here nothing is guessed about fading: an epidemic
model works out WHY growth slows - every infection uses up a susceptible
person, so each infected person finds fewer people left to infect.

The compartments (as fractions of the people susceptible at the start of the season):
    s = susceptible, i = infectious, r = recovered (immune)
and the SIRS equations, with time t in days:
    ds/dt = -beta * s * i + omega * r
    di/dt =  beta * s * i - gamma * i
    dr/dt =  gamma * i    - omega * r
    new infections per day = beta * s * i
    hospital admissions per day = (scale) * beta * s * i

Fixed, from the influenza literature:
    gamma = 1/3 per day   (people stay infectious about 3 days)
    omega = 1/365 per day (immunity fades over about a year; tiny over 4 weeks)

What changes every week, for every location, from the data:
1. The current reproduction number R_t, from the recent growth rate r (the same
   3-week slope as Stage 2). For an SIR model, growth per day = gamma * (R_t - 1), so
        R_t = 1 + (r / 7) / gamma.
   Because R_t is re-estimated each week, the transmission rate beta(t) varies in time.
2. How many susceptibles are left, s_now. This is where the mechanism comes in:
        s_now = 1 - KAPPA * (admissions so far this season) / (a typical season's admissions)
   KAPPA is the fraction of the start-of-season susceptibles that a typical season
   uses up. KAPPA = 0.5 means a typical season infects half of them. It is the ONLY
   parameter tuned on past seasons, with the same rule as Stage 2:
     - chosen on 2023-24 + 2024-25 for the 2025-26 test: KAPPA = 0.3
     - chosen on all three seasons for live 2026-27 forecasts: KAPPA = 0.4 (below)
   "A typical season's admissions" is the average total of this location's complete
   past seasons, so the model assumes this season will be about as big as usual.
3. beta = gamma * R_t / s_now, and i_now is set so that the model reproduces this
   week's admission rate.

Then the equations are solved forward 4 weeks with the 4th-order Runge-Kutta method
(RK4, step 0.5 day), and admissions are added up week by week. As s falls, beta*s
falls, so growth slows and turns WITHOUT being told to - the mechanism that the
Stage 2 trend model was missing.

The uncertainty range is the baseline's (as in Stage 2), centred on the SIRS median,
so differences in score come from the median alone.
"""

from datetime import timedelta

import numpy as np
import pandas as pd

import baseline_model
import common
import trend_model

GAMMA = 1 / 3        # recovery rate per day (about 3 days infectious)
OMEGA = 1 / 365      # loss of immunity per day (about one year)
KAPPA = 0.4          # fraction of season-start susceptibles a typical season uses (tuned; see 09)
WINDOW = 3           # weeks used for the growth rate (same as Stage 2)
DT = 0.5             # RK4 time step, days
R_MIN, R_MAX = 0.3, 3.0      # keep R_t in a plausible range
S_MIN = 0.05                 # never let the susceptible fraction reach zero


def season_start(day):
    """August 1 that begins the flu season containing `day`."""
    year = day.year if day.month >= 8 else day.year - 1
    return pd.Timestamp(year=year, month=8, day=1)


def typical_season_total(location_rows, before):
    """Average total admissions of the complete past seasons (Aug-Jul) before `before`."""
    rows = location_rows[location_rows["date"] < season_start(before)]
    if rows.empty:
        return np.nan
    start_year = rows["date"].dt.year.where(rows["date"].dt.month >= 8, rows["date"].dt.year - 1)
    totals, firsts = rows.groupby(start_year)["value"].sum(), rows.groupby(start_year)["date"].min()
    complete = firsts.dt.month.isin([8, 9])          # season observed from its start
    return totals[complete].mean() if complete.any() else np.nan


def sirs_rates(state, beta):
    """Right-hand side of the SIRS equations. state = [s, i, r, cumulative infections]."""
    s, i, r, _ = state
    infections = beta * s * i
    return np.array([-infections + OMEGA * r,
                     infections - GAMMA * i,
                     GAMMA * i - OMEGA * r,
                     infections])


def rk4_step(state, beta, dt):
    """One step of the classical 4th-order Runge-Kutta method."""
    k1 = sirs_rates(state, beta)
    k2 = sirs_rates(state + dt / 2 * k1, beta)
    k3 = sirs_rates(state + dt / 2 * k2, beta)
    k4 = sirs_rates(state + dt * k3, beta)
    return state + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)


def simulate_weekly_admissions(admissions_last_week, growth_rate, season_so_far,
                               typical_total, kappa, weeks=4):
    """Median admissions for the next `weeks` weeks from the SIRS model.

    The simulation starts at the MIDDLE of the last observed week (where the
    weekly average rate actually applies) and adds admissions over each later week.
    """
    rate_now = max(admissions_last_week, 0.5) / 7                 # admissions per day
    r_t = np.clip(1 + (growth_rate / 7) / GAMMA, R_MIN, R_MAX)    # reproduction number
    s_now = max(1 - kappa * season_so_far / typical_total, S_MIN)
    beta = GAMMA * r_t / s_now
    scale = typical_total / kappa          # admissions per unit of "season-start susceptibles"
    i_now = rate_now / (scale * beta * s_now)
    state = np.array([s_now, i_now, max(1 - s_now - i_now, 0.0), 0.0])

    # Half a week to reach the end of the last observed week (no admissions counted yet).
    for _ in range(int(round(3.5 / DT))):
        state = rk4_step(state, beta, DT)

    # Then each forecast week: 7 days of steps, counting the new infections.
    totals = []
    for _ in range(weeks):
        infections_before = state[3]
        for _ in range(int(round(7 / DT))):
            state = rk4_step(state, beta, DT)
        totals.append(scale * (state[3] - infections_before))
    return np.array(totals)


def forecast_one_location(location_rows, reference_date, kappa=KAPPA, window=WINDOW):
    """Quantile forecasts for one location. Returns a list of row dictionaries."""
    rows_sorted = location_rows.sort_values("date")
    last = rows_sorted.iloc[-1]
    last_date = last["date"].date()

    typical_total = typical_season_total(rows_sorted, last["date"])
    in_season = rows_sorted[rows_sorted["date"] >= season_start(last["date"])]
    season_so_far = in_season["value"].sum()
    rate = trend_model.growth_rate(rows_sorted, window)

    # How many weeks to simulate: normally 4 (horizon 3 is 4 weeks after the last data).
    weeks_needed = (reference_date + timedelta(weeks=max(common.HORIZONS)) - last_date).days // 7
    if np.isnan(typical_total) or typical_total <= 0:
        medians = np.full(weeks_needed, last["value"])      # no history: fall back to flat
    else:
        medians = simulate_weekly_admissions(last["value"], rate, season_so_far,
                                             typical_total, kappa, weeks=weeks_needed)
    z_medians = np.log(medians + 1)

    # The spread: exactly the baseline's (symmetric in-season weekly changes).
    recent = rows_sorted[rows_sorted["date"] > last["date"] - timedelta(weeks=baseline_model.HISTORY_WEEKS)]
    changes = baseline_model.log_changes(recent)
    one_week_quantiles = np.quantile(np.concatenate([changes, -changes]), common.QUANTILE_LEVELS)

    out = []
    for horizon in common.HORIZONS:
        target_end_date = reference_date + timedelta(weeks=horizon)
        steps = (target_end_date - last_date).days // 7            # 1 to 4 normally
        centre = z_medians[steps - 1]
        values = np.exp(centre + np.sqrt(steps) * one_week_quantiles) - 1
        values = np.maximum(np.round(values), 0)
        values = np.maximum.accumulate(values)
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


def make_forecast(data, reference_date, locations, kappa=KAPPA, window=WINDOW):
    """Forecasts for every location, using only data dated before the reference week."""
    cutoff = pd.Timestamp(reference_date - timedelta(weeks=1))
    usable = data[data["date"] <= cutoff]
    all_rows = []
    for location in locations:
        location_rows = usable[usable["location"] == location]
        if len(location_rows) < 10:
            continue
        all_rows.extend(forecast_one_location(location_rows, reference_date, kappa, window))
    return pd.DataFrame(all_rows)
