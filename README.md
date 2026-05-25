# FORD-II: External Validation and Refinement of the FORD Score on NTDB 2019-2024

FORD-II is a 16-predictor integer (0-10) clinical prediction score for non-home discharge in adult trauma patients with fractures. Derived and validated on the ACS National Trauma Data Bank Public Use Files, admission years 2019-2024, using a 2:1 train/test split (training n=1,301,473; held-out test n=650,737). This repository contains the full analysis pipeline, aggregated result tables, manuscript figures, completed reporting checklists, and a deployable bedside calculator. Headline performance on the held-out test set: AUROC 0.8285 (95% CI 0.8275-0.8296).

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Calculator](https://img.shields.io/badge/calculator-live-brightgreen)](https://ford-ii-calculator.onrender.com)

> Note: DOI badges above are PLACEHOLDERS. The Zenodo concept and version DOIs will be patched in after the first tagged release.

## Citation

If you use FORD-II in your work, please cite both the software and the associated manuscript.

**Manuscript (under review at *JAMA Surgery*, 2026):**

> Salman S. FORD-II: External Validation and Refinement of the FORD Score for Non-home Discharge in U.S. Trauma Patients. *JAMA Surgery*. 2026 (under review).

**BibTeX:**

```bibtex
@article{salman2026fordii,
  author  = {Salman, Samer},
  title   = {{FORD-II}: External Validation and Refinement of the {FORD} Score for Non-home Discharge in U.S. Trauma Patients},
  journal = {JAMA Surgery},
  year    = {2026},
  note    = {Under review}
}

@software{salman2026fordii_software,
  author    = {Salman, Samer},
  title     = {{FORD-II}: External Validation and Refinement of the {FORD} Score on NTDB 2019-2024},
  year      = {2026},
  publisher = {Zenodo},
  version   = {0.1.0},
  doi       = {10.5281/zenodo.XXXXXXX},
  url       = {https://github.com/samersalman/ford-ii}
}
```

A machine-readable citation is also provided in [`CITATION.cff`](CITATION.cff).

## Repository structure

```
ford-ii/
├── README.md
├── LICENSE
├── CITATION.cff
├── requirements.txt
├── .gitignore
├── analysis/
│   ├── ford_ii_refit/        # FORD-II refit pipeline (scripts 01-06)
│   └── manuscript/           # manuscript-builder pipeline (scripts 01-08)
├── tables/                   # aggregated result tables (CSV) reported in the manuscript
├── figures/                  # manuscript figures (PNG only)
├── checklists/               # completed TRIPOD, STROBE, CHEERS .docx
├── calculator/               # Flask bedside calculator (deploys to Render)
└── docs/
    ├── REPRODUCE.md          # step-by-step reproduction guide
    └── DATA_AVAILABILITY.md  # what's shipped, what's not, how to get NTDB
```

## Reproduction

Three tiers, depending on how deep you want to go.

### Tier 1 — Run the calculator only

No NTDB access required. Spins up the bedside web calculator locally.

```bash
cd calculator
pip install -r requirements.txt
flask run
```

A hosted instance is live at <https://ford-ii-calculator.onrender.com>.

### Tier 2 — Inspect tables and figures (no NTDB needed)

Every number reported in the manuscript is committed to this repo as a CSV under `tables/`, with the corresponding figures in `figures/`. Open them directly — no code required.

Key tables:
- `tables/ford_ii_weights.csv` — 16 final predictors with β, OR, 95% CI, raw weight, and integer points
- `tables/ford_ii_score_to_prob.csv` — logistic intercept/slope mapping integer score to risk
- `tables/risk_groups.csv` — Low / Low-Mod / Mod-High / High thresholds and event rates
- `tables/validation_metrics.csv` — AUROC, Brier, calibration for FORD-II, FORD, GTOS-II, TRIAGES
- `tables/subgroups.csv` — subgroup performance breakdown
- `tables/cost_consequence.csv` — cost-consequence analysis rows
- `tables/sensitivity_*.csv` — prespecified sensitivity analyses

### Tier 3 — Full rebuild from NTDB

Requires an executed NTDB Research Data Use Agreement and the PUF files. See [`docs/REPRODUCE.md`](docs/REPRODUCE.md) for the full pipeline order, environment variables, and expected runtimes.

Quick sketch:

```bash
export NTDB_DATA="/path/to/compiled_NTDB_2019_2024"

# 1) FORD-II refit pipeline
cd analysis/ford_ii_refit
python 01_prepare.py        # cohort prep from NTDB
python 02_features.py
python 03_select_and_fit.py # writes tables/ford_ii_weights.csv
python 04_validate.py       # writes tables/validation_metrics.csv, risk_groups.csv
python 05_sensitivity.py    # writes sensitivity_*.csv, subgroups.csv, extra_comparators.csv

# 2) Manuscript pipeline
cd ../manuscript
python 01_cost_decision_tree.py
python 02_build_consort_figure.py
python 03_build_cost_panel.py
python 04_build_manuscript.py
python 05_build_cheers_supplement.py
python 06_build_tripod_supplement.py
python 07_verify_numbers.py     # PASS = all manuscript numbers reproduce
python 08_build_cover_letter.py
```

## Data availability

This repository ships only aggregated, non-patient-level outputs. The NTDB PUF files and the original FORD v1 integer weights are not redistributable here. See [`docs/DATA_AVAILABILITY.md`](docs/DATA_AVAILABILITY.md) for how to request them.

## Reporting checklists

Completed reporting checklists are bundled in [`checklists/`](checklists/) as `.docx` files for reviewer convenience:

- **TRIPOD** — prediction model development and validation
- **STROBE** — observational cohort
- **CHEERS** — cost-consequence analysis

## Contact

**Samer Salman**
Baylor College of Medicine
<samer.salman2021@gmail.com>

IRB cohort assembly (original FORD development): Baylor College of Medicine protocol H-53551. NTDB external validation uses fully de-identified data and does not require additional IRB approval at the analyst's institution.
