# Data availability

## What's in this repository

This repository ships only **aggregated, non-patient-level outputs** plus the scoring code:

- **`tables/`** — every numeric result reported in the manuscript, as CSV. Counts are reported only at the cohort or risk-group level. Every cell summarizes ≥1,000 patients; no row corresponds to an individual or to a small re-identifiable subgroup. Files include:
  - `baseline.csv` — Table 1, cohort baseline characteristics
  - `candidate_pool.csv` — candidate predictor pool considered before final selection
  - `ford_ii_weights.csv` — 16 final predictors with β, OR, 95% CI, raw weight, and integer points
  - `ford_ii_score_to_prob.csv` — logistic intercept/slope mapping integer score to risk
  - `risk_groups.csv` — Low / Low-Mod / Mod-High / High thresholds and event rates
  - `validation_metrics.csv` — AUROC, Brier, calibration for FORD-II, FORD, GTOS-II, TRIAGES
  - `extra_comparators.csv` — additional comparator score performance
  - `subgroups.csv` — subgroup performance breakdown
  - `cost_consequence.csv` — cost-consequence analysis rows
  - `sensitivity_arms.csv` — cost-analysis treatment-arms sensitivity
  - `sensitivity_bentaub_reverse.csv` — Ben Taub reverse validation sensitivity
  - `sensitivity_comorbidity.csv` — comorbidity sensitivity
  - `sensitivity_temporal.csv` — temporal sensitivity (year strata)
  - `sensitivity_truncation.csv` — score-range truncation sensitivity
  - `sensitivity_with_insurance.csv` — insurance-inclusive sensitivity
- **`figures/`** — manuscript figures as PNG. Includes `figures/cost_analysis/` containing the cost-decision-tree diagram, tornado plot, PSA scatter, CEAC, and PSA iteration results (`psa_results.csv`, 10,000 Monte Carlo iterations).
- **`analysis/`** — the analysis code (Python scripts) needed to reproduce the tables and figures from the NTDB PUF.
- **`calculator/`** — Flask bedside calculator that scores a single patient from 16 inputs.
- **`checklists/`** — completed TRIPOD, STROBE, and CHEERS reporting checklists.

**No patient-level data are stored in this repository.** None.

## What's NOT in this repository

The following inputs are required to rerun the analysis from scratch and are not redistributable here:

1. **NTDB Public Use Files (PUF), admission years 2019-2024.** This includes the per-year raw `PUF_TRAUMA.csv` files and the compiled multi-year files (`compiled_PUF_AY_2019_2024.csv`, `ntdb_2019_2024_*.csv`) that the upstream NTDB compilation pipeline produces.
2. **`tables/ford_v1_weights.csv`** — the original FORD score integer weights used as a comparator and to compute the FORD v1 score on the NTDB cohort. The integer weights themselves are published; the small CSV is not redistributed here.

## How to obtain the NTDB PUF

The NTDB PUF is distributed by the American College of Surgeons (ACS) under a Research Data Use Agreement.

1. Visit the ACS NTDB program page: <https://www.facs.org/quality-programs/trauma/quality/national-trauma-data-bank/>
2. Submit an NTDB Research Data Application. A signed Data Use Agreement is required.
3. Request **admission years 2019-2024** to match the cohort used in this study.
4. Turnaround is typically several weeks.

Once you receive the data, point `NTDB_DATA` at the directory containing the compiled multi-year files. See [`REPRODUCE.md`](REPRODUCE.md), Section 3.

## How to obtain `tables/ford_v1_weights.csv`

The integer weights for the original FORD score are published in Table 3 of:

> Salman S, et al. The FORD score: predicting non-home discharge in adult trauma patients with fractures. *Injury*. 2026.

Transcribe Table 3 of that paper into a CSV with the following two-column schema:

```
predictor,integer_points
```

Save the file as `tables/ford_v1_weights.csv`. The columns are case-sensitive. Predictor names must match the variable names emitted by `analysis/ford_ii_refit/01_prepare.py` (run that script first to see the expected names in the prepared cohort).

## Privacy, IRB, and de-identification

- Original FORD development cohort assembly at Ben Taub Hospital was approved by the Baylor College of Medicine Institutional Review Board (protocol H-53551).
- The NTDB PUF is **fully de-identified at source** by the ACS prior to release to investigators; no protected health information flows through this repository or through the analysis pipeline.
- No record-level data, no free-text fields, and no small-cell counts are committed to this repository. The smallest reported denominator in `tables/` is at the risk-group level.
