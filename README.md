# Do Midseason Manager Replacements Improve Football Results?

**An observational causal-inference project on managerial changes in the English Premier League.**

Football clubs often replace their manager after a run of poor results. If performance improves afterwards, how much of that improvement can be attributed to the new manager? How much reflects an easier fixture list, changes in team circumstances, or a return towards the team's usual level?

This project investigates that question by assembling match and manager-change data, constructing pre/post performance windows, and comparing several approaches to estimating treatment effects.

**Main finding:** the saved results depend substantially on the estimator. The difference-in-differences specification produces a positive estimated change in the project's composite outcome, while most other bootstrap intervals include zero. The analysis provides an exploratory comparison of methods rather than a definitive answer about the benefit of changing managers. So it probably isn't worth the cost, but that's my personal bias. 

**Tools:** Python, pandas, NumPy, scikit-learn, statsmodels, XGBoost, EconML, and Matplotlib.

## Start here

| File | Purpose |
| --- | --- |
| [CI_Analysis.ipynb](CI_Analysis.ipynb) | Estimators, bootstrap analysis, treatment-permutation checks, and saved results |
| [CI_Data_Builder.ipynb](CI_Data_Builder.ipynb) | Fixture enrichment, league-table reconstruction, and construction of team-level analysis windows |
| [data.zip](data.zip) | Packaged project data; extract before running the notebooks |

For a quick review, open the saved outputs in `CI_Analysis.ipynb` and the results table below. Running the full resampling comparison is optional.

## Research question

The question is whether replacing a manager changes a team's subsequent performance relative to what would have happened if the club had retained its manager.

That counterfactual is not directly observable. Managerial changes are also not randomly assigned: struggling teams are more likely to change managers, and the reasons for a dismissal may themselves affect subsequent results. A simple comparison of results before and after a replacement therefore cannot isolate its causal effect.

The project approaches this problem through observed team characteristics, comparison observations, pre/post outcomes, and multiple estimation strategies. Its conclusions remain conditional on the assumptions behind those choices.

## Data and construction

### Coverage and inputs

The fixture data cover seasons ending in **2015–2023**, corresponding to **2014/15–2022/23**. The saved fixture output contains **3,420 matches**. Season labels refer to the year in which the season ends.

The workflow combines:

- Match dates, gameweeks, teams, goals, and results.
- Manually encoded managerial-change information aligned with fixtures.
- FIFA-derived team attributes, including overall rating, domestic/international prestige, and transfer-budget estimates.
- League positions reconstructed from match results, plus previous-season positions.

The analysis notebook reads `full_data_epl_2015-2023_no_interim.csv`, the prepared analysis version excluding interim-manager cases. Its saved output contains **181 observations**. These are constructed team/window observations, not 181 individual matches or 181 replacements.

The data-builder notebook records earlier preparation stages and writes a differently named output, `full_data_epl_2015-2023.csv`. Manual annotations, intermediate files, and the no-interim preparation step should be retained when rebuilding the analysis dataset; the builder is not a single-command raw-to-final pipeline.

### Preparation workflow

1. **Standardise team names.** Reconcile naming differences between fixture and team-attribute sources.
2. **Enrich fixtures.** Associate each team's fixture with its closest available FIFA attribute-update date.
3. **Reconstruct league standings.** Accumulate points, goal difference, and goals scored across fixtures, recording current and previous-season positions.
4. **Align managerial changes.** Use the annotated change information to identify treated observations.
5. **Build comparison windows.** Aggregate team performance before and after each selected reference date.
6. **Create analysis features.** Flatten the window summaries and calculate composite performance and expectation variables.

### Treatment and comparison observations

For treated observations, the reference date comes from a fixture marked with a managerial change. Candidate observations are restricted using date boundaries corresponding to gameweeks **9–30**.

For controls, the builder samples a reference date from eligible fixtures within a team-season. It then removes control observations from team-seasons that also contain treated observations. The candidate-control selection and treatment annotations are part of the exploratory design and warrant review when extending the study.

The window function selects **up to nine matches strictly before** and **up to nine matches strictly after** the reference date. A match on the reference date is excluded. The function does not itself guarantee nine available matches or explicitly restrict each window to the same season.

### Features and outcome

| Group | Variables |
| --- | --- |
| Recent results | Goals scored, goals conceded, points, home-game count |
| Relative strength | Team rating, opponent rating, average rating gap |
| League context | Average league position and previous-season position |
| Club characteristics | Prestige and average transfer-budget estimate |
| Composite variables | `pre_score`, `post_score`, and `expectation` |

The final comparison uses **`post_score`**, a hand-built composite outcome. It combines results with contextual information about opposition, ratings, league position, and venue mix. `expectation` combines club prestige, scaled budget, previous-season position, and team rating.

**Effect estimates below are in composite-score units. They are not additional league points, wins, or percentage improvements.** The historical pre/post score definitions differ in their opponent-rating scaling; this matters especially for change-based estimates and is discussed under limitations.

## Methods

The final notebook loop runs the following seven estimators:

| Method | Implementation |
| --- | --- |
| Inverse-probability weighting (`ipw`) | Logistic-regression propensity scores; difference between normalised weighted outcome means |
| Difference-in-differences (`did`) | Regression of pre/post score change on treatment and season indicators |
| Direct matching (`matching`) | Nearest-neighbour matching on `expectation`, with a default caliper of 0.1 |
| Propensity-score matching (`prop_matching`) | One nearest control per treated observation using logistic propensity scores |
| Linear S-learner (`s_learner_linear`) | One linear outcome model including treatment; average difference between predictions with treatment set to 1 and 0 |
| Linear T-learner (`t_learner_linear`) | Separate linear models for treated and control observations; average predicted outcome difference |
| IPW + DiD (`ipw_did`) | Weighted regression of pre/post score change on treatment and season indicators |

The notebook also defines XGBoost S/T-learners, a matched DiD estimator, and an EconML causal forest. **Those functions are not included in the final saved seven-method comparison.**

The notebook labels estimates as average treatment effects (ATEs). Matching constructs a treated-centred comparison, while the regression learners average predictions over the supplied sample; consequently, the methods should not be assumed to target precisely identical populations or estimands.

### Resampling and diagnostic checks

- **Bootstrap:** 1,000 row-level resamples with replacement per method. The notebook reports the mean estimate across resamples and a percentile interval using the 2.5th and 97.5th percentiles.
- **Treatment permutation:** 1,000 attempted random shuffles of the treatment labels per method. Each shuffled dataset is re-estimated to form a diagnostic null distribution.
- **Plots:** Method-specific bootstrap and permutation distributions, a combined estimate/interval plot, and an interval-width comparison.

These procedures assess sampling variability and sensitivity to shuffled treatment labels within the implemented design. They do not remove unobserved confounding or establish the assumptions needed for causal identification.

## Saved results

The following values are transcribed from the notebook's saved figure legends and printed output. They are historical outputs, not results from a new execution. Bootstrap means and interval endpoints are rounded to three decimals.

| Method | Bootstrap mean estimate | 95% percentile interval | Reported permutation tail fraction |
| --- | ---: | --- | ---: |
| IPW | 0.222 | [−0.859, 1.099] | 0.310 |
| DiD | 3.026 | [2.126, 3.938] | 0.000 |
| Direct matching | 1.022 | [−0.788, 2.974] | 0.138 |
| Propensity-score matching | 0.248 | [−1.295, 1.609] | 0.134 |
| Linear S-learner | 0.601 | [−0.286, 1.527] | 0.116 |
| Linear T-learner | 0.604 | [−0.848, 2.332] | 0.143 |
| IPW + DiD | 1.745 | [−0.148, 3.717] | 0.000 |

The bootstrap mean is the mean across resampled estimates, not necessarily the estimate from the original sample. The permutation calculation uses the original-sample estimate, so it should not be reconstructed from the bootstrap-mean column.

A printed permutation value of `0.000` means that no successful shuffle was at least as extreme under the implemented calculation. It does not mean a true probability of zero. The code uses an empirical tail fraction without a finite-simulation correction.

### Interpretation

All seven saved bootstrap means are positive, but **six of the seven percentile intervals include zero**. DiD yields a larger estimate and an interval entirely above zero. IPW + DiD produces a small permutation tail fraction while its bootstrap interval still includes zero, illustrating that the two procedures give different signals in this implementation.

The results therefore support **method-dependent evidence**, rather than a single settled conclusion. Their variation motivates closer examination of outcome construction, treatment timing, comparison-group selection, and identifying assumptions before interpreting an estimate as the effect of a managerial replacement.

## Running the analysis

### Inspect the existing outputs

Open [CI_Analysis.ipynb](CI_Analysis.ipynb) on GitHub and review the saved tables and figures. This requires no installation or model execution.

### Run in Google Colab

The notebooks were written for Colab and use `/content/` paths.

1. Open [CI_Analysis.ipynb in Colab](https://colab.research.google.com/github/idanh8/manager_replacement_causality/blob/main/CI_Analysis.ipynb).
2. Upload `data.zip`, extract it, and locate `full_data_epl_2015-2023_no_interim.csv`.
3. If the extracted location differs from the hard-coded path in the data-loading cell, point `pd.read_csv(...)` to the actual file. If that prepared CSV is absent, supply it before running the analysis; the data-builder's output has a different filename and preparation history.
4. Run the EconML installation and import cells. Create the plotting directory before the resampling cells:

```python
from pathlib import Path

Path('/content/plots').mkdir(parents=True, exist_ok=True)
```

5. Run the estimator definitions, resampling helpers, and configuration cells in order.
6. Run the comparison loop. The final Colab-specific cell packages the plot directory for download.

For a shorter exploratory run, pass smaller `n_bootstrap` and `n_permutations` values in the two helper calls, for example 100. Those runs are useful for checking the workflow; they will not reproduce the saved 1,000-repetition outputs.

### Run locally

Clone the repository and install the packages used by the notebooks in a virtual environment:

```bash
git clone https://github.com/idanh8/manager_replacement_causality.git
cd manager_replacement_causality
python -m venv .venv
```

Activate it using the command appropriate to your shell:

```bash
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
python -m pip install jupyterlab pandas numpy scikit-learn statsmodels xgboost econml matplotlib
python -m jupyterlab
```

The dependency list is inferred from notebook imports; the repository does not provide a pinned environment. After extracting `data.zip`, update the data-loading path and every `/content/plots/...` save path to valid local paths, create the plot directory, and skip the final `google.colab` download cell.

### Rebuild the data

Use [CI_Data_Builder.ipynb](CI_Data_Builder.ipynb) to follow the preparation stages. Important inputs and intermediate files referenced by the code include:

| Filename | Role |
| --- | --- |
| `premier-league-matches.csv` | Fixture results |
| `teams.csv` | FIFA-derived attributes; the uploaded version is already filtered to Premier League teams |
| `merged-fixtures-draft.csv` | Intermediate enriched/annotated fixtures |
| `fixtures_data_epl_2015-2023.csv` | Fixtures used to construct team windows, including manager-change fields |
| `full_data_epl_2015-2023.csv` | Builder output |
| `full_data_epl_2015-2023_no_interim.csv` | Prepared input used by the analysis notebook |

Review file locations, date formats, annotations, and intermediate transitions before running all cells. The builder's saved outputs and the analysis input represent different preparation stages, so rebuilding may produce a different observation count.

## Limitations and reproducibility

- **Non-random treatment and unobserved confounding.** Injuries, dressing-room dynamics, board decisions, media pressure, and other unmeasured circumstances can influence both managerial changes and performance.
- **Outcome definition.** The composite score is hand-built and mixes performance with context. In the builder, the opponent-rating term is divided by 5 before treatment and by 4 afterwards. A consistent pre/post definition and a points-only outcome are important sensitivity checks before interpreting change-based effects.
- **Temporal alignment.** FIFA attributes are joined by closest update date, which may be after the fixture. Window construction also needs checks for season boundaries, repeated replacements, and sufficient matches on both sides of the reference date.
- **Comparison-group assumptions.** Propensity weighting and matching depend on observed covariates and adequate overlap; DiD additionally requires a credible parallel-trends argument. Comparing several estimators does not itself validate these assumptions.
- **Dependence between observations.** The bootstrap resamples rows rather than clubs or seasons, and label shuffling is unrestricted. Neither procedure explicitly preserves the team/season dependence structure.
- **Stochastic workflow.** Control-date sampling, bootstrapping, and permutations are not assigned fixed seeds. Exact outputs can change between runs. The permutation helper skips failed fits, so its tail fraction is based on successful shuffles.
- **Historical environment.** The notebooks retain Colab-specific paths and outputs without a locked dependency environment. The displayed results are useful for inspection, but a fresh end-to-end reproduction requires the path and data-preparation steps above.

## Project contribution

I proposed the research question and independently completed the data assembly, managerial-change annotation, feature construction, implementation, and analysis as a Technion Causal Inference course project.

**Idan Horowitz** · [GitHub](https://github.com/idanh8) · [LinkedIn](https://www.linkedin.com/in/idanho/)
