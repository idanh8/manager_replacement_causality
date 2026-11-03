"""Seeded rerun of the manager-replacement analysis.

Reuses the estimator functions from CI_Analysis.ipynb verbatim (exec of their cells), then:
  1. checks the pre/post score definition and recomputes it consistently,
  2. adds an ANCOVA estimator (adjusts for the pre-period level),
  3. reports row-level and team-clustered bootstrap intervals with fixed seeds,
  4. runs three outcome definitions: stored composite, consistent composite, points only.
"""
import json
import re
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.neighbors import NearestNeighbors

warnings.filterwarnings("ignore")
import os
# Usage: python rerun.py <folder with the extracted data.zip csvs> <path to CI_Analysis.ipynb> [n_bootstrap]
DATA = sys.argv[1].rstrip("/\\") + os.sep
NOTEBOOK = sys.argv[2]
N_BOOT = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out") + os.sep
os.makedirs(OUT, exist_ok=True)

# ---- load estimator functions verbatim from the notebook -------------------
nb = json.load(open(NOTEBOOK, encoding="utf-8"))
WANTED = {"ipw", "did", "s_learner_linear", "t_learner_linear", "prop_matching", "matching", "did_matching", "ipw_did"}
ns = dict(pd=pd, np=np, LogisticRegression=LogisticRegression, LinearRegression=LinearRegression,
          NearestNeighbors=NearestNeighbors, sm=sm, smf=smf)
for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    code = "".join(cell["source"])
    m = re.match(r"\s*def (\w+)\(", code)
    if m and m.group(1) in WANTED:
        exec(code, ns)

def ancova(df, treatment, outcome, covariates, plot=False):
    pre = "pre_score" if outcome == "post_score" else "pre_points"
    m = smf.ols(f"{outcome} ~ {treatment} + {pre} + expectation + C(season)", data=df).fit()
    return m.params[treatment]

METHODS = {k: ns[k] for k in ["ipw", "did", "matching", "prop_matching", "s_learner_linear", "t_learner_linear", "ipw_did"]}
METHODS["ancova"] = ancova

# ---- data ------------------------------------------------------------------
raw = pd.read_csv(DATA + "full_data_epl_2015-2023_no_interim.csv")

def recompute(d, post_opp_div):
    d = d.copy()
    for w, div in (("pre", 5), ("post", post_opp_div)):
        d[f"{w}_score"] = (0.3 * d[f"{w}_goals_scored"] - 0.2 * d[f"{w}_goals_conceded"] + 0.25 * d[f"{w}_points"]
                           + 0.25 * d[f"{w}_avg_league_position"] + 0.2 * (d[f"{w}_opponent_rating"] / div)
                           + 0.1 * (20 - d[f"{w}_rating"] / 5) + 0.1 * 2 * (10 - d[f"{w}_home_games"]))
    return d

# 1. does the stored score match the builder code (opp /5 pre, /4 post)?
chk = recompute(raw, 4)
print("stored vs builder-formula max abs diff (pre, post):",
      float((chk.pre_score - raw.pre_score).abs().max()), float((chk.post_score - raw.post_score).abs().max()))
cons = recompute(raw, 5)
shift = (raw.post_score - cons.post_score)
print("post_score inflation from /4 vs /5: mean %.3f (min %.3f max %.3f)" % (shift.mean(), shift.min(), shift.max()))
print("   same shift applied to treated and control alike? treated %.3f control %.3f" %
      (shift[raw.treatment == 1].mean(), shift[raw.treatment == 0].mean()))

COV = ['pre_goals_scored', 'pre_goals_conceded', 'pre_points', 'pre_home_games', 'pre_rating', 'pre_opponent_rating',
       'pre_avg_rating_gap', 'pre_avg_league_position', 'pre_score', 'prev_season_position', 'total_prestige',
       'avg_budget', 'expectation']

# Linear learners in the notebook are ill-posed: avg_budget is on a 1e8 scale and pre_score / pre_avg_rating_gap are exact
# linear combinations of other covariates (rank-deficient design). Rerun uses standardised, de-collinearised covariates.
DROP = ["pre_avg_rating_gap", "pre_score"]
BASE_COV = [c for c in COV if c not in DROP]
def add_z(d):
    d = d.copy()
    for c in BASE_COV:
        d["z_" + c] = (d[c] - d[c].mean()) / d[c].std()
    return d
COV_Z = ["z_" + c for c in BASE_COV]
_chk = add_z(raw)[COV_Z + ["treatment"]].values
print("design rank / columns after cleaning:", np.linalg.matrix_rank(_chk), _chk.shape[1])
raw_z, cons_z = add_z(raw), add_z(cons)

SPECS = {
    "stored composite (as published)": (raw_z, "post_score"),
    "consistent composite (opp. rating /5 both windows)": (cons_z, "post_score"),
    "points only": (raw_z, "post_points"),
}

def boot(df, fn, outcome, mode, seed):
    rng = np.random.default_rng(seed)
    est = []
    if mode == "cluster":
        groups = {t: g for t, g in df.groupby("team")}
        teams = np.array(list(groups))
    for _ in range(N_BOOT):
        if mode == "row":
            s = df.iloc[rng.integers(0, len(df), len(df))].reset_index(drop=True)
        else:
            pick = rng.choice(teams, size=len(teams), replace=True)
            s = pd.concat([groups[t] for t in pick]).reset_index(drop=True)
        try:
            est.append(fn(s, "treatment", outcome, COV_Z))
        except Exception:
            pass
    est = np.array(est)
    return est.mean(), *np.percentile(est, [2.5, 97.5]), len(est)

rows = []
for spec, (df, outcome) in SPECS.items():
    for name, fn in METHODS.items():
        point = fn(df.copy(), "treatment", outcome, COV_Z)
        for mode in ("row", "cluster"):
            m, lo, hi, n = boot(df, fn, outcome, mode, seed=12345)
            rows.append(dict(spec=spec, method=name, bootstrap=mode, point=point, boot_mean=m, lo=lo, hi=hi, n_ok=n,
                             excludes_zero=bool(lo > 0 or hi < 0)))
    print("done", spec, flush=True)
res = pd.DataFrame(rows)
res.to_csv(OUT + "results.csv", index=False)
pd.set_option("display.width", 250)
print(res.round(3).to_string())

# ---- descriptive checks -------------------------------------------------------
t, c = raw[raw.treatment == 1], raw[raw.treatment == 0]
print("\nGroup means (stored): pre_points T %.2f C %.2f | post_points T %.2f C %.2f" %
      (t.pre_points.mean(), c.pre_points.mean(), t.post_points.mean(), c.post_points.mean()))
print("pre_score T %.2f C %.2f | post_score T %.2f C %.2f" % (t.pre_score.mean(), c.pre_score.mean(), t.post_score.mean(), c.post_score.mean()))
print("naive DiD on stored composite = %.3f ; pre-gap (C-T) = %.3f" %
      ((t.post_score - t.pre_score).mean() - (c.post_score - c.pre_score).mean(), c.pre_score.mean() - t.pre_score.mean()))

# controls that started as badly as treated teams: how much do THEY rebound with no manager change?
lowc = c[c.pre_points <= 8]
print("\nControls with pre_points <= 8: n=%d, pre %.2f -> post %.2f (change %.2f)" %
      (len(lowc), lowc.pre_points.mean(), lowc.post_points.mean(), (lowc.post_points - lowc.pre_points).mean()))
lowt = t[t.pre_points <= 8]
print("Treated with pre_points <= 8: n=%d, pre %.2f -> post %.2f (change %.2f)" %
      (len(lowt), lowt.pre_points.mean(), lowt.post_points.mean(), (lowt.post_points - lowt.pre_points).mean()))
print("Treated overall: n=%d change %.2f ; Controls overall: change %.2f" %
      (len(t), (t.post_points - t.pre_points).mean(), (c.post_points - c.pre_points).mean()))

# clustered-SE regression, points only
raw2 = raw.copy()
m = smf.ols("post_points ~ treatment + pre_points + expectation + C(season)", data=raw2).fit(
    cov_type="cluster", cov_kwds={"groups": pd.factorize(raw2.team)[0]})
print("\nANCOVA points-only, team-clustered SE: treat coef %.3f  95%% CI [%.3f, %.3f]  p=%.3f" %
      (m.params["treatment"], *m.conf_int().loc["treatment"], m.pvalues["treatment"]))
m = smf.ols("post_points ~ treatment + C(season)", data=raw2.assign(d=raw2.post_points - raw2.pre_points)).fit()
d = smf.ols("d ~ treatment + C(season)", data=raw2.assign(d=raw2.post_points - raw2.pre_points)).fit(
    cov_type="cluster", cov_kwds={"groups": pd.factorize(raw2.team)[0]})
print("Naive DiD points-only (change in points), clustered SE: %.3f CI [%.3f, %.3f]" %
      (d.params["treatment"], *d.conf_int().loc["treatment"]))
print("Unique teams:", raw.team.nunique(), " treated teams:", t.team.nunique())
