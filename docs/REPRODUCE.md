# Reproducing FORD-II

This guide walks through a full rebuild of the FORD-II analysis from the NTDB Public Use Files. If you only want to inspect the tables and figures reported in the manuscript, you do not need any of this — they are committed under `tables/` and `figures/` and can be opened directly.

## 1. Prerequisites

- **Python 3.10 or newer.**
- **NTDB Public Use Files, admission years 2019-2024.** Access requires an executed ACS NTDB Research Data Use Agreement. See [`DATA_AVAILABILITY.md`](DATA_AVAILABILITY.md) for the request workflow.
- **Original FORD v1 integer weights** as `tables/ford_v1_weights.csv`. Not redistributed here. See [`DATA_AVAILABILITY.md`](DATA_AVAILABILITY.md) for how to reconstruct this file from the published FORD paper (Salman et al., *Injury*, 2026).
- Approximately 8 GB free disk space for intermediate cohort files.

## 2. Setup

```bash
git clone https://github.com/samersalman/ford-ii.git
cd ford-ii

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Environment variables

The analysis scripts read the NTDB file location from a single environment variable. Set it before running any script:

```bash
export NTDB_DATA="/path/to/compiled_NTDB_2019_2024"
```

`NTDB_DATA` should point at the directory containing the compiled, multi-year cohort files (the output of the upstream NTDB compilation pipeline) for admission years 2019-2024.

## 4. Pipeline order

There are two pipelines. The **FORD-II refit pipeline** derives the 16-predictor FORD-II score and produces the validation tables. The **manuscript pipeline** consumes those tables, builds the figures, assembles the manuscript .docx, and verifies that every reported number reproduces.

### Step 1 — FORD-II refit (derivation + validation)

```bash
cd analysis/ford_ii_refit

python 01_prepare.py          # cohort prep from NTDB 2019-2024, 2:1 train/test split
python 02_features.py         # builds the 16-predictor candidate feature matrix
python 03_select_and_fit.py   # writes tables/ford_ii_weights.csv
python 04_validate.py         # writes tables/validation_metrics.csv, tables/risk_groups.csv
python 05_sensitivity.py      # writes tables/sensitivity_*.csv, subgroups.csv, extra_comparators.csv
```

### Step 2 — Manuscript builder

```bash
cd ../manuscript

python 01_cost_decision_tree.py     # writes tables/cost_consequence.csv
python 02_build_consort_figure.py
python 03_build_cost_panel.py
python 04_build_manuscript.py       # writes the manuscript .docx
python 05_build_cheers_supplement.py
python 06_build_tripod_supplement.py
python 07_verify_numbers.py         # PASS = all manuscript numbers reproduce
python 08_build_cover_letter.py
```

`07_verify_numbers.py` is the gate: it re-reads the committed CSVs in `tables/` and asserts every numeric claim in the manuscript reproduces exactly. If any assertion fails, do not trust the rebuild.

## 5. Expected runtimes

Rough estimates on a single-core MacBook (modern Apple Silicon). YMMV depending on disk speed and how the NTDB files are stored.

| Pipeline | Total | Slowest step |
|---|---|---|
| FORD-II refit | ~30-45 min | `01_prepare.py`, `02_features.py` (large CSV joins) |
| Manuscript builder | ~5-10 min | `04_build_manuscript.py` |

Most wall time is spent reading and joining the NTDB PUF CSVs. A warm filesystem cache helps substantially on reruns.

## 6. Common errors

| Symptom | Cause | Fix |
|---|---|---|
| `KeyError: 'NTDB_DATA'` | Environment variable not set in the current shell | `export NTDB_DATA=...` (Section 3) |
| `FileNotFoundError: tables/ford_v1_weights.csv` | Original FORD v1 weights not provided | See `DATA_AVAILABILITY.md` |
| `MemoryError` during `01_prepare.py` | Insufficient RAM for the full NTDB join | Run on a machine with ≥16 GB; or batch by admission year |
| Assertion failures in `07_verify_numbers.py` | Pipeline ran on a different NTDB extract, or a script was modified | Confirm you are using the ACS PUF for AY 2019-2024 unmodified; rerun from `01_prepare.py` |
