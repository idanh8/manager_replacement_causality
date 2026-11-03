# Seeded rerun of the manager-replacement analysis

Reruns the estimators from `CI_Analysis.ipynb` (the functions are loaded unchanged from the notebook) and adds the
following. The notebook and its original saved outputs are not modified.

- **Consistent outcome.** The original post score scaled the opponent-rating term by 4 where the pre score used 5.
  The rerun recomputes both windows with the same scaling. It shifts treated and control windows almost equally
  (0.894 vs 0.888) and changes no conclusion.
- **League points as a third outcome.** Points over the nine-match window, in directly interpretable units.
- **Well-posed design matrix.** The original covariates were rank-deficient (`pre_score` and `pre_avg_rating_gap`
  are exact linear combinations of other columns) and `avg_budget` is on a 1e8 scale, which made the linear learners
  numerically fragile. The rerun standardises covariates and drops those two columns.
- **Regression on starting form** (`ancova`): post outcome on treatment, pre outcome, expectation and season.
- **Fixed seeds and two bootstraps.** 1,000 resamples, seed 12345, with row-level and team-level (cluster)
  intervals. The website figure uses the team-level intervals.

## Run

Requires Python 3.12 or later (the pinned numpy 2.5.3 does not install on 3.11). The published run used Python 3.13
with the exact versions in `requirements.txt`.

From the repository root:

    python -m venv .venv
    source .venv/bin/activate          # Windows: .venv\Scripts\activate
    pip install -r rerun/requirements.txt
    unzip data.zip -d data             # or extract data.zip into a folder named data
    cd rerun
    python rerun.py ../data ../CI_Analysis.ipynb 1000

`rerun.py` takes about five minutes. It writes `out/results.csv` and prints the descriptive checks (group means, the
rebound among comparison windows that also started badly, and the team-clustered regression).

To redraw the figure from your own run, copy `out/results.csv` over the committed `results.csv` (they should be
identical), then:

    python plot_forest.py

This writes `forest-points.png` next to the script.

Verified on 3 November 2026 from a clean checkout with the pinned versions: all 48 rows of `out/results.csv` matched
the committed `results.csv` exactly, and the redrawn figure was pixel-identical to the committed `forest-points.png`.

## Files

| File | Purpose |
| --- | --- |
| `rerun.py` | Reruns all estimators for three outcomes and two bootstrap schemes |
| `plot_forest.py` | Draws the forest plot of the points-only, team-level results |
| `results.csv` | Output of the published run: one row per outcome, method and bootstrap scheme |
| `forest-points.png` | The resulting figure |
| `requirements.txt` | Package versions used |

`results.csv` columns: `spec` (outcome definition), `method`, `bootstrap` (`row` or `cluster`), `point` (estimate in
the full sample), `boot_mean`, `lo` and `hi` (95% percentile interval), `n_ok` (successful resamples), `excludes_zero`.

## Known limits

- 181 team windows, 50 treated, 33 distinct teams. Controls are random windows from team-seasons without a change.
- The saved composite score in the CSV differs from the builder notebook's formula by up to 0.5, so the builder
  alone does not reproduce the saved file exactly.
- The composite score adds 0.25 times league position (1 is best), so a worse position raises the score. League
  points avoid this and are the headline outcome.
- Matching uses `expectation` only, so it does not adjust for starting form.
- No unmeasured-confounding adjustment: injuries, board decisions and media pressure are not in the data.
