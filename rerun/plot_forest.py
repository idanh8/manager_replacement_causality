import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import os
BASE = os.path.dirname(os.path.abspath(__file__)) + os.sep
r = pd.read_csv(BASE + "results.csv")
r = r[(r.spec == "points only") & (r.bootstrap == "cluster")].copy()

label = {
    "did": "Difference-in-differences",
    "ipw_did": "IPW + difference-in-differences",
    "ipw": "Inverse-probability weighting",
    "matching": "Matching on expectation",
    "prop_matching": "Propensity-score matching",
    "s_learner_linear": "S-learner (linear)",
    "t_learner_linear": "T-learner (linear)",
    "ancova": "Regression on starting form",
}
order = ["did", "ipw_did", "matching", "prop_matching", "ipw", "s_learner_linear", "t_learner_linear", "ancova"]
change = {"did", "ipw_did"}
r = r.set_index("method").loc[order].reset_index()

C_CHANGE, C_LEVEL, INK, MUTED = "#b4532a", "#2a5d84", "#222222", "#6b6b6b"
fig, ax = plt.subplots(figsize=(8.2, 4.9), dpi=200)
ys = list(range(len(r)))[::-1]
for y, (_, row) in zip(ys, r.iterrows()):
    col = C_CHANGE if row.method in change else C_LEVEL
    ax.plot([row.lo, row.hi], [y, y], color=col, lw=2.2, solid_capstyle="round")
    ax.plot(row.point, y, "o", color=col, ms=6.5, mfc="white" if False else col)
ax.axvline(0, color=INK, lw=1, ls=(0, (4, 3)))
ax.set_yticks(ys)
ax.set_yticklabels([label[m] for m in r.method], fontsize=9.5, color=INK)
ax.set_xlabel("Estimated effect of replacing the manager, league points over the next 9 matches", fontsize=9.5, color=INK)
ax.tick_params(axis="x", labelsize=9, colors=INK)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.grid(axis="x", color="#dddddd", lw=0.7)
ax.set_axisbelow(True)
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([0], [0], color=C_CHANGE, lw=2.2, marker="o", label="Compares the change in points (before to after)"),
                   Line2D([0], [0], color=C_LEVEL, lw=2.2, marker="o", label="Compares points afterwards (level estimators)")],
          loc="upper center", bbox_to_anchor=(0.40, -0.17), ncol=2, fontsize=8.3, frameon=False, columnspacing=1.6, handlelength=1.6)
ax.set_title("Estimates depend on how the poor start is handled", fontsize=11, color=INK, loc="left", pad=10)
fig.text(0.01, 0.005, "Dot = point estimate in the full sample; bar = 95% percentile interval, team-level bootstrap (1,000 resamples, fixed seed). n = 181 team windows, 50 treated.",
         fontsize=7.2, color=MUTED)
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(BASE + "forest-points.png", facecolor="white")
print(r[["method", "point", "lo", "hi"]].round(2))
