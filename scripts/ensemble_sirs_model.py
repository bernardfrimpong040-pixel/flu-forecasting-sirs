"""
ensemble_sirs_model.py - the Stage 4b model: an ensemble of holiday SIRS models.

WHY THIS STAGE EXISTS
---------------------
Stage 4 uses ONE setting of KAPPA (how fast susceptibles run out) and ONE holiday
factor. The tuning grid showed that the best KAPPA changes from season to season
(Stage 3, Figure 6), and the model does not know in advance which kind of season
this one will be. Instead of betting on one setting, the ensemble runs several
versions of the model and combines their forecasts.

HOW THE FORECASTS ARE COMBINED
------------------------------
Each member gives 23 quantiles for each location and week. Two ways to combine:

  "average"  : average each quantile across the members (e.g. the ensemble's
               median = mean of the members' medians). The width of the range stays
               about the same as one member.

  "mixture"  : treat the ensemble as "pick a member at random, then draw from it".
               Its cumulative probability at value x is the average of the members'
               cumulative probabilities at x. When members disagree, the range gets
               WIDER, which is what we want when we are unsure which member is right.

RESULT (12_backtest_rebound.py --ensembles): no ensemble beat the single tuned model
(rebound 0.9) on the tuning seasons, so the ensemble is NOT submitted. It is kept
here because the comparison is part of the paper.
"""

import itertools

import numpy as np
import pandas as pd

import common
import holiday_sirs_model

# The ensemble tested in 12_backtest_rebound.py: one kappa and holiday factor, three
# possible rebounds, because the rebound is the thing we are least sure about.
MEMBER_KAPPAS = [0.3]
MEMBER_FACTORS = [0.8]
MEMBER_REBOUNDS = [0.8, 0.9, 1.0]
METHOD = "mixture"


def combine_quantiles(member_values, method):
    """Combine the members' 23 quantile values (one row per member) into 23 values."""
    levels = np.array(common.QUANTILE_LEVELS)
    member_values = np.sort(np.asarray(member_values, dtype=float), axis=1)
    if method == "average":
        return member_values.mean(axis=0)

    # Mixture: on the log scale, build each member's cumulative probability F_m(x)
    # by joining its quantiles with straight lines, average the F_m, and read off the
    # values where the average reaches each quantile level.
    z = np.log(member_values + 1)
    grid = np.unique(z)
    cdf = np.mean([np.interp(grid, z_m, levels) for z_m in z], axis=0)
    cdf = np.maximum.accumulate(cdf)                      # make sure it never decreases
    z_out = np.interp(levels, cdf, grid)
    return np.exp(z_out) - 1


def make_forecast(data, reference_date, locations, kappas=None, factors=None,
                  rebounds=None, method=METHOD):
    """Ensemble forecasts for every location. Same columns as every other model."""
    kappas = MEMBER_KAPPAS if kappas is None else kappas
    factors = MEMBER_FACTORS if factors is None else factors
    rebounds = MEMBER_REBOUNDS if rebounds is None else rebounds

    # 1. Run every member.
    members = []
    for kappa, factor, rebound in itertools.product(kappas, factors, rebounds):
        members.append(holiday_sirs_model.make_forecast(data, reference_date, locations,
                                                        kappa=kappa, factor=factor,
                                                        rebound=rebound))
    if not members or members[0].empty:
        return members[0] if members else pd.DataFrame()

    # 2. Put the members side by side: one column per member.
    keys = ["reference_date", "target", "horizon", "target_end_date", "location",
            "output_type", "output_type_id"]
    wide = members[0][keys].copy()
    for number, member in enumerate(members):
        wide[f"m{number}"] = member["value"].to_numpy()
    member_columns = [f"m{number}" for number in range(len(members))]

    # 3. Combine the 23 quantiles of each location and week.
    out = []
    for _, group in wide.groupby(["location", "horizon"], sort=False):
        group = group.sort_values("output_type_id")
        values = combine_quantiles(group[member_columns].to_numpy().T, method)
        values = np.maximum.accumulate(np.maximum(np.round(values), 0))
        group = group[keys].copy()
        group["value"] = values.astype(int)
        out.append(group)
    return pd.concat(out, ignore_index=True)
