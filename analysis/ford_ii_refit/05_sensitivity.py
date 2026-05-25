#!/usr/bin/env python3
"""
05_sensitivity.py — Six sensitivity analyses for FORD-II (NTDB 2019-2024).

1. Temporal validation (train 2019-2022 / test 2023-2024) — primary temporal
   external-validation story.
2. Comorbidity model (2019-2024 subset, if comorbidity columns available).
3. FORD-II with insurance variables (sensitivity — adds insurance back).
4. Subgroup AUROCs + forest plot (frozen primary weights).
   NOTE: `VERIFICATION_LEVEL` is NOT available in the 2019-2024 compiled pool,
   so the verification-level stratum is dropped. See analysis_subgroups() for
   a placeholder footnote row.
5. Score truncation impact (raw vs clipped 0-10).
6. ISS + GCS extra comparators — supplementary AUROCs for ISS and GCS as sole
   predictors on the test set.

Pipeline position:  03_select_and_fit.py -> 04_validate.py -> [THIS]

DOWNSTREAM_NOTES (for 06_manuscript.py):
    extra_comparators.csv schema:
        columns = ['comparator', 'n', 'auroc', 'auroc_ci_low', 'auroc_ci_high']
        rows    = one per extra comparator (ISS, GCS)

Input:
    data/ford2_model.parquet          — full dataset with split, scores, candidates, outcome
    tables/ford_ii_weights.csv        — FORD-II selected predictors + integer weights

Outputs:
    tables/sensitivity_temporal.csv
    tables/sensitivity_comorbidity.csv
    tables/subgroups.csv
    tables/sensitivity_with_insurance.csv
    tables/sensitivity_truncation.csv
    tables/extra_comparators.csv
    figures/figure_s2_subgroup_forest.png + .pdf

Seed:    42
"""

# ---------------------------------------------------------------------------
# Imports  (matplotlib Agg MUST be set before pyplot)
# ---------------------------------------------------------------------------
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import os
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegressionCV
from sklearn.metrics import roc_auc_score
import statsmodels.api as sm

warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent       # .../analysis/ford_ii_refit/
REPO_ROOT = SCRIPT_DIR.parents[1]                  # public repo root
TABLES_DIR = REPO_ROOT / "tables"
FIGURES_DIR = REPO_ROOT / "figures"
DATA_DIR = SCRIPT_DIR / "data"                     # gitignored
INPUT_PARQUET = DATA_DIR / "ford2_model.parquet"
TABLE3_PATH = TABLES_DIR / "ford_ii_weights.csv"
TABLES_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
N_BOOT = int(os.environ.get('FORD_II_NBOOT', '1000'))

# ---------------------------------------------------------------------------
# Candidate variable pool (must match 03_select_and_fit.py)
# ---------------------------------------------------------------------------
# ED-admission bedside variables only (no ISS, no labs, no tox, no insurance)
# Must match 03_select_and_fit.py — insurance excluded from primary model
ALL_CANDIDATES = [
    'age_45_64', 'age_65_74', 'age_75plus',
    'female',
    'race_black', 'race_asian', 'race_native', 'race_other',
    'ethnicity_hispanic',
    'sbp_hypotensive', 'sbp_hypertensive',
    'hr_bradycardic', 'hr_tachycardic',
    'rr_low', 'rr_high',
    'gcs_moderate', 'gcs_severe',
    'hypoxic',
    'temp_hypothermic', 'temp_hyperthermic',
    'bmi_underweight', 'bmi_overweight', 'bmi_obese_12', 'bmi_obese_3',
    'frac_cervical', 'frac_thoracic', 'frac_lumbar', 'frac_humerus',
    'frac_forearm', 'frac_hand', 'frac_hip_femur', 'frac_leg', 'frac_foot',
    'mech_mvc', 'mech_assault', 'mech_other',
    'trans_auto', 'trans_air', 'trans_other_mode',
    'transfer_in', 'prehospital_arrest',
]

# `ins_medicaid` intentionally omitted: NTDB PAYMENT_SOURCE combines
# Medicare/Medicaid as `MCARE-M`, so Medicaid is not separately
# identifiable. Matches the "Medicaid not separable" caveat in Methods.
INSURANCE_VARS = ['ins_medicare', 'ins_private', 'ins_charity', 'ins_other']

COMORBIDITY_CANDIDATES = [
    'diabetes', 'htn', 'chf', 'copd', 'ckd',
    'dementia', 'cirrhosis', 'bleeding_disorder',
    'anticoagulant', 'functional_dependence',
]

_t0 = time.time()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _banner(msg: str) -> None:
    bar = "=" * 72
    elapsed = time.time() - _t0
    print(f"\n[{elapsed:7.1f}s] {bar}\n         {msg}\n         {bar}", flush=True)


def bootstrap_auc_ci(y_true, scores, n_boot=N_BOOT, seed=SEED):
    """Bootstrap 95% CI for AUROC."""
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    scores = np.asarray(scores)
    n = len(y_true)
    if len(np.unique(y_true)) < 2:
        return np.nan, np.nan, np.nan
    auroc = roc_auc_score(y_true, scores)
    aucs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        if len(np.unique(y_true[idx])) < 2:
            continue
        aucs.append(roc_auc_score(y_true[idx], scores[idx]))
    if aucs:
        lo = float(np.percentile(aucs, 2.5))
        hi = float(np.percentile(aucs, 97.5))
    else:
        lo, hi = np.nan, np.nan
    return float(auroc), lo, hi


def prune_candidates(df: pd.DataFrame, candidates: list[str]) -> list[str]:
    """Keep only candidates present in df with nonzero variance."""
    present = [v for v in candidates if v in df.columns]
    retained = [v for v in present if df[v].nunique() > 1]
    dropped = set(candidates) - set(retained)
    if dropped:
        print(f"    Pruned {len(dropped)} candidates (missing or zero-variance): "
              f"{sorted(dropped)}", flush=True)
    return retained


def run_lasso_refit(X_train: pd.DataFrame, y_train: np.ndarray,
                    candidate_names: list[str], label: str = ""):
    """
    Run LASSO feature selection + unpenalized refit + RAMS Method B scoring.

    Returns:
        selected_vars : list[str]
        betas         : pd.Series
        integer_points: dict[str, int]
        weights_df    : pd.DataFrame (one row per selected variable)
        model         : statsmodels Logit result
    """
    prefix = f"  [{label}] " if label else "  "
    print(f"{prefix}Running LASSO on {len(candidate_names)} candidates, "
          f"N={len(y_train):,}", flush=True)

    # ----- LASSO (L1 logistic, 5-fold CV) -----
    lasso_cv = LogisticRegressionCV(
        penalty='l1',
        solver='saga',
        Cs=20,
        cv=5,
        max_iter=5000,
        random_state=SEED,
        scoring='roc_auc',
        n_jobs=-1,
    )
    lasso_cv.fit(X_train[candidate_names].values, y_train)
    print(f"{prefix}Best C: {lasso_cv.C_[0]:.6f}", flush=True)

    lasso_coefs = lasso_cv.coef_[0]
    selected_mask = lasso_coefs != 0
    selected_vars = [v for v, sel in zip(candidate_names, selected_mask) if sel]
    print(f"{prefix}LASSO selected {len(selected_vars)} / {len(candidate_names)}", flush=True)

    if not selected_vars:
        print(f"{prefix}WARNING: LASSO selected 0 features", flush=True)
        return [], pd.Series(dtype=float), {}, pd.DataFrame(), None

    # ----- Unpenalized refit + backward elimination + β pruning -----
    current_vars = list(selected_vars)

    # Backward elimination: drop highest p > 0.05
    while True:
        X_sel = sm.add_constant(X_train[current_vars])
        model = sm.Logit(y_train, X_sel).fit(disp=0, maxiter=200)
        pvals_be = model.pvalues[1:]
        max_p = pvals_be.max()
        if max_p <= 0.05:
            break
        drop_var = pvals_be.idxmax()
        current_vars.remove(drop_var)
        if not current_vars:
            break

    # Clinical significance pruning: |β| >= 0.35 (same as primary model)
    BETA_THRESHOLD = 0.35
    betas_all = model.params[1:]
    weak = [v for v, b in zip(current_vars, betas_all) if abs(b) < BETA_THRESHOLD]
    if weak:
        current_vars = [v for v in current_vars if v not in weak]
        X_sel = sm.add_constant(X_train[current_vars])
        model = sm.Logit(y_train, X_sel).fit(disp=0, maxiter=200)

    selected_vars = current_vars
    betas = model.params[1:]
    ses = model.bse[1:]
    pvals = model.pvalues[1:]
    conf = model.conf_int().iloc[1:]
    print(f"{prefix}After pruning: {len(selected_vars)} variables", flush=True)

    # ----- RAMS Method B integer points -----
    pos_betas = [float(b) for b in betas if float(b) > 0]
    if not pos_betas:
        print(f"{prefix}WARNING: No positive coefficients — cannot compute Method B weights",
              flush=True)
        return selected_vars, betas, {}, pd.DataFrame(), model

    min_pos_coef = min(pos_betas)

    integer_points = {}
    rows = []
    for i, var in enumerate(selected_vars):
        beta = betas.iloc[i]
        se = ses.iloc[i]
        pval = pvals.iloc[i]
        or_val = np.exp(beta)
        ci_low = np.exp(conf.iloc[i, 0])
        ci_high = np.exp(conf.iloc[i, 1])
        raw_weight = beta / min_pos_coef
        points = round(raw_weight)
        if beta > 0 and points < 1:
            points = 1
        integer_points[var] = points
        rows.append({
            'Variable': var,
            'Beta': round(float(beta), 4),
            'SE': round(float(se), 4),
            'OR': round(float(or_val), 2),
            'CI_low': round(float(ci_low), 2),
            'CI_high': round(float(ci_high), 2),
            'P_value': round(float(pval), 4),
            'Raw_weight': round(float(raw_weight), 2),
            'Integer_points': int(points),
        })

    rows.sort(key=lambda r: abs(r['Integer_points']), reverse=True)
    weights_df = pd.DataFrame(rows)

    for r in rows:
        print(f"{prefix}  {r['Variable']:30s}  OR {r['OR']:6.2f}  pts {r['Integer_points']:+3d}",
              flush=True)

    return selected_vars, betas, integer_points, weights_df, model


def compute_score(df: pd.DataFrame, weights: dict, clip: bool = True) -> pd.Series:
    """Compute integer score from weights dict, optionally clipped to [0, 10]."""
    s = pd.Series(0, index=df.index, dtype=int)
    for var, pts in weights.items():
        if var in df.columns:
            s += pts * df[var].astype(int)
    if clip:
        s = s.clip(0, 10)
    return s


def load_primary_weights() -> dict:
    """Load primary FORD-II integer weights from ford_ii_weights.csv."""
    table3 = pd.read_csv(TABLE3_PATH)
    primary_weights = dict(zip(table3['Variable'], table3['Integer_points']))
    print(f"  Loaded {len(primary_weights)} primary FORD-II weights from {TABLE3_PATH}",
          flush=True)
    return primary_weights


# =====================================================================
# ANALYSIS 1: Temporal validation (v3: train 2019-2022 / test 2023-2024)
# =====================================================================
def analysis_temporal(df: pd.DataFrame, primary_weights: dict) -> None:
    _banner("ANALYSIS 1: Temporal validation (train 2019-2022 / test 2023-2024)")
    t0 = time.time()

    out_path = TABLES_DIR / "sensitivity_temporal.csv"

    # v3 temporal split — 2023/2024 are genuinely unseen years (FORD-II v2 was
    # trained on 2017-2022 and never saw these). This is v3's primary temporal
    # external-validation story.
    train_years = {2019, 2020, 2021, 2022}
    test_years = {2023, 2024}

    train = df[df['PUF_YEAR'].isin([2019, 2020, 2021, 2022])]
    test = df[df['PUF_YEAR'].isin([2023, 2024])]
    df_train = train.copy()
    df_test = test.copy()

    y_train = df_train['outcome_nonhome'].values
    y_test = df_test['outcome_nonhome'].values

    print(f"  Temporal train: N={len(df_train):,}  "
          f"(outcome rate {y_train.mean()*100:.1f}%)", flush=True)
    print(f"  Temporal test:  N={len(df_test):,}  "
          f"(outcome rate {y_test.mean()*100:.1f}%)", flush=True)

    # Prune candidates for temporal train set
    candidates = prune_candidates(df_train, ALL_CANDIDATES)

    # Run LASSO -> refit -> Method B on temporal train
    selected_vars, betas, integer_points, weights_df, model = \
        run_lasso_refit(df_train, y_train, candidates, label="Temporal")

    if not selected_vars:
        placeholder = pd.DataFrame([{
            'analysis': 'temporal',
            'note': 'LASSO selected 0 features on temporal train set',
        }])
        placeholder.to_csv(out_path, index=False)
        print(f"  WARNING: No features selected. Placeholder saved to {out_path}", flush=True)
        return

    # Primary model selected vars (from table3)
    primary_vars = set(primary_weights.keys())
    temporal_vars = set(selected_vars)

    vars_in_both = primary_vars & temporal_vars
    vars_primary_only = primary_vars - temporal_vars
    vars_temporal_only = temporal_vars - primary_vars

    print(f"\n  Variable comparison:", flush=True)
    print(f"    Primary model: {len(primary_vars)} vars", flush=True)
    print(f"    Temporal model: {len(temporal_vars)} vars", flush=True)
    print(f"    In both:        {len(vars_in_both)}", flush=True)
    print(f"    Primary only:   {sorted(vars_primary_only)}", flush=True)
    print(f"    Temporal only:  {sorted(vars_temporal_only)}", flush=True)

    # --- Temporal model AUROC on temporal test set ---
    temporal_score = compute_score(df_test, integer_points, clip=True)
    temp_auroc, temp_lo, temp_hi = bootstrap_auc_ci(y_test, temporal_score)
    print(f"\n  Temporal FORD-II AUROC (temporal test): "
          f"{temp_auroc:.4f} ({temp_lo:.4f}-{temp_hi:.4f})", flush=True)

    # --- Primary FORD-II weights on temporal test set ---
    primary_score = compute_score(df_test, primary_weights, clip=True)
    pri_auroc, pri_lo, pri_hi = bootstrap_auc_ci(y_test, primary_score)
    print(f"  Primary FORD-II AUROC (temporal test):  "
          f"{pri_auroc:.4f} ({pri_lo:.4f}-{pri_hi:.4f})", flush=True)

    delta = temp_auroc - pri_auroc if not np.isnan(temp_auroc) else np.nan
    print(f"  Delta (temporal - primary): {delta:+.4f}", flush=True)

    # --- Build output table ---
    summary_rows = [
        {'metric': 'N_train', 'value': len(df_train)},
        {'metric': 'N_test', 'value': len(df_test)},
        {'metric': 'train_years', 'value': '2019-2022'},
        {'metric': 'test_years', 'value': '2023-2024'},
        {'metric': 'train_outcome_rate_pct', 'value': round(y_train.mean() * 100, 2)},
        {'metric': 'test_outcome_rate_pct', 'value': round(y_test.mean() * 100, 2)},
        {'metric': 'n_selected_temporal', 'value': len(temporal_vars)},
        {'metric': 'n_selected_primary', 'value': len(primary_vars)},
        {'metric': 'vars_primary_only', 'value': '; '.join(sorted(vars_primary_only))},
        {'metric': 'vars_temporal_only', 'value': '; '.join(sorted(vars_temporal_only))},
        {'metric': 'temporal_model_AUROC', 'value': round(temp_auroc, 4)},
        {'metric': 'temporal_model_AUROC_CI_low', 'value': round(temp_lo, 4)},
        {'metric': 'temporal_model_AUROC_CI_high', 'value': round(temp_hi, 4)},
        {'metric': 'primary_weights_AUROC', 'value': round(pri_auroc, 4)},
        {'metric': 'primary_weights_AUROC_CI_low', 'value': round(pri_lo, 4)},
        {'metric': 'primary_weights_AUROC_CI_high', 'value': round(pri_hi, 4)},
        {'metric': 'delta_AUROC_temporal_minus_primary', 'value': round(delta, 4) if not np.isnan(delta) else 'NA'},
    ]

    # Append temporal model weights
    for _, row in weights_df.iterrows():
        summary_rows.append({
            'metric': f'temporal_weight_{row["Variable"]}',
            'value': row['Integer_points'],
        })

    result = pd.DataFrame(summary_rows)
    result.to_csv(out_path, index=False)
    print(f"\n  Saved {out_path}", flush=True)
    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)


# =====================================================================
# ANALYSIS 2: Comorbidity model
# =====================================================================
def analysis_comorbidity(df: pd.DataFrame, primary_weights: dict) -> None:
    _banner("ANALYSIS 2: Comorbidity model (2019-2024 subset)")
    t0 = time.time()

    out_path = TABLES_DIR / "sensitivity_comorbidity.csv"

    # Check which comorbidity columns exist
    available_comorb = [c for c in COMORBIDITY_CANDIDATES if c in df.columns]
    print(f"  Comorbidity candidates checked: {COMORBIDITY_CANDIDATES}", flush=True)
    print(f"  Available in parquet: {available_comorb}", flush=True)

    if not available_comorb:
        print("  WARNING: No comorbidity columns found in feature set.", flush=True)
        print("  Comorbidity data was not included in the feature engineering step (02).",
              flush=True)
        print("  Creating placeholder table.", flush=True)
        placeholder = pd.DataFrame([{
            'metric': 'status',
            'value': 'Comorbidity columns not available in ford2_model.parquet. '
                     'Comorbidity data was not included in the feature engineering step '
                     '(02_features.py). To enable this analysis, add comorbidity '
                     'variable engineering to script 02 using NTDB comorbidity fields '
                     '(available from ~2019 onward).',
        }, {
            'metric': 'comorbidity_candidates_checked',
            'value': '; '.join(COMORBIDITY_CANDIDATES),
        }, {
            'metric': 'available_in_parquet',
            'value': 'None',
        }])
        placeholder.to_csv(out_path, index=False)
        print(f"  Saved placeholder to {out_path}", flush=True)
        print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)
        return

    # Restrict to 2019-2024 (comorbidity data availability — v3 pool)
    df_sub = df[df['PUF_YEAR'].isin({2019, 2020, 2021, 2022, 2023, 2024})].copy()
    print(f"  Subset 2019-2024: N={len(df_sub):,}", flush=True)

    if len(df_sub) < 1000:
        print("  WARNING: Subset too small (<1000). Skipping comorbidity analysis.", flush=True)
        placeholder = pd.DataFrame([{
            'metric': 'status',
            'value': f'2019-2024 subset too small (N={len(df_sub)}). Skipped.',
        }])
        placeholder.to_csv(out_path, index=False)
        return

    y_sub = df_sub['outcome_nonhome'].values
    print(f"  Outcome rate: {y_sub.mean()*100:.1f}%", flush=True)

    # Use the primary random split column to split this subset
    train_mask = df_sub['split'] == 'train'
    test_mask = df_sub['split'] == 'test'
    df_sub_train = df_sub[train_mask]
    df_sub_test = df_sub[test_mask]
    y_sub_train = df_sub_train['outcome_nonhome'].values
    y_sub_test = df_sub_test['outcome_nonhome'].values

    print(f"  Train (2019-2024): N={len(df_sub_train):,}", flush=True)
    print(f"  Test  (2019-2024): N={len(df_sub_test):,}", flush=True)

    # --- Model A: Primary candidates only (no comorbidities), on 2019-2024 subset ---
    candidates_base = prune_candidates(df_sub_train, ALL_CANDIDATES)
    print(f"\n  --- Model A: Base candidates (no comorbidities) ---", flush=True)
    sel_a, _, pts_a, wdf_a, _ = run_lasso_refit(
        df_sub_train, y_sub_train, candidates_base, label="Comorb-Base")

    if sel_a:
        score_a = compute_score(df_sub_test, pts_a, clip=True)
        auroc_a, lo_a, hi_a = bootstrap_auc_ci(y_sub_test, score_a)
        print(f"  Model A AUROC: {auroc_a:.4f} ({lo_a:.4f}-{hi_a:.4f})", flush=True)
    else:
        auroc_a, lo_a, hi_a = np.nan, np.nan, np.nan

    # --- Model B: Base + comorbidity candidates ---
    candidates_plus = candidates_base + [c for c in available_comorb if c not in candidates_base]
    candidates_plus = prune_candidates(df_sub_train, candidates_plus)
    print(f"\n  --- Model B: Base + comorbidities ({len(available_comorb)} added) ---", flush=True)
    sel_b, _, pts_b, wdf_b, _ = run_lasso_refit(
        df_sub_train, y_sub_train, candidates_plus, label="Comorb-Plus")

    if sel_b:
        score_b = compute_score(df_sub_test, pts_b, clip=True)
        auroc_b, lo_b, hi_b = bootstrap_auc_ci(y_sub_test, score_b)
        print(f"  Model B AUROC: {auroc_b:.4f} ({lo_b:.4f}-{hi_b:.4f})", flush=True)
    else:
        auroc_b, lo_b, hi_b = np.nan, np.nan, np.nan

    delta = auroc_b - auroc_a if not (np.isnan(auroc_a) or np.isnan(auroc_b)) else np.nan

    # Also apply primary FORD-II weights to this subset for reference
    primary_score_sub = compute_score(df_sub_test, primary_weights, clip=True)
    pri_auroc, pri_lo, pri_hi = bootstrap_auc_ci(y_sub_test, primary_score_sub)

    # Comorbidity prevalence in 2019-2024 subset
    comorb_prev = {}
    for c in available_comorb:
        prev = df_sub[c].mean() * 100
        comorb_prev[c] = round(prev, 2)

    # Comorbidities selected by LASSO in Model B
    comorb_selected = [v for v in sel_b if v in available_comorb] if sel_b else []

    # Build output
    summary_rows = [
        {'metric': 'subset_years', 'value': '2019-2024'},
        {'metric': 'N_subset', 'value': len(df_sub)},
        {'metric': 'N_train', 'value': len(df_sub_train)},
        {'metric': 'N_test', 'value': len(df_sub_test)},
        {'metric': 'outcome_rate_pct', 'value': round(y_sub.mean() * 100, 2)},
        {'metric': 'comorbidities_available', 'value': '; '.join(available_comorb)},
        {'metric': 'comorbidities_selected_by_lasso', 'value': '; '.join(comorb_selected) if comorb_selected else 'None'},
        {'metric': 'model_A_n_selected', 'value': len(sel_a) if sel_a else 0},
        {'metric': 'model_A_AUROC', 'value': round(auroc_a, 4) if not np.isnan(auroc_a) else 'NA'},
        {'metric': 'model_A_AUROC_CI', 'value': f"{lo_a:.4f}-{hi_a:.4f}" if not np.isnan(lo_a) else 'NA'},
        {'metric': 'model_B_n_selected', 'value': len(sel_b) if sel_b else 0},
        {'metric': 'model_B_AUROC', 'value': round(auroc_b, 4) if not np.isnan(auroc_b) else 'NA'},
        {'metric': 'model_B_AUROC_CI', 'value': f"{lo_b:.4f}-{hi_b:.4f}" if not np.isnan(lo_b) else 'NA'},
        {'metric': 'delta_AUROC_B_minus_A', 'value': round(delta, 4) if not np.isnan(delta) else 'NA'},
        {'metric': 'primary_FORD2_AUROC_on_subset', 'value': round(pri_auroc, 4) if not np.isnan(pri_auroc) else 'NA'},
        {'metric': 'primary_FORD2_AUROC_CI', 'value': f"{pri_lo:.4f}-{pri_hi:.4f}" if not np.isnan(pri_lo) else 'NA'},
    ]

    for c, prev in comorb_prev.items():
        summary_rows.append({'metric': f'prevalence_{c}_pct', 'value': prev})

    result = pd.DataFrame(summary_rows)
    result.to_csv(out_path, index=False)
    print(f"\n  Saved {out_path}", flush=True)
    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)


# =====================================================================
# ANALYSIS 3: FORD-II with insurance (sensitivity — adds insurance back)
# =====================================================================
def analysis_with_insurance(df: pd.DataFrame, primary_weights: dict) -> None:
    _banner("ANALYSIS 3: FORD-II WITH insurance variables (sensitivity)")
    t0 = time.time()

    out_path = TABLES_DIR / "sensitivity_with_insurance.csv"

    # Use the primary random split
    train_mask = df['split'] == 'train'
    test_mask = df['split'] == 'test'
    df_train = df[train_mask]
    df_test = df[test_mask]
    y_train = df_train['outcome_nonhome'].values
    y_test = df_test['outcome_nonhome'].values

    # Add insurance variables back to the candidate pool
    candidates_with_ins = list(ALL_CANDIDATES) + INSURANCE_VARS
    candidates_with_ins = prune_candidates(df_train, candidates_with_ins)
    print(f"  Candidates (with insurance): {len(candidates_with_ins)}", flush=True)
    print(f"  Added: {INSURANCE_VARS}", flush=True)

    # Run LASSO -> refit -> Method B
    selected_vars, betas, integer_points, weights_df, model = \
        run_lasso_refit(df_train, y_train, candidates_with_ins, label="With-Ins")

    if not selected_vars:
        placeholder = pd.DataFrame([{
            'metric': 'status',
            'value': 'LASSO selected 0 features. Analysis could not be completed.',
        }])
        placeholder.to_csv(out_path, index=False)
        print(f"  WARNING: No features selected. Placeholder saved.", flush=True)
        return

    # Compute with-insurance score on test set
    with_ins_score = compute_score(df_test, integer_points, clip=True)
    auroc_wi, lo_wi, hi_wi = bootstrap_auc_ci(y_test, with_ins_score)
    print(f"\n  With-insurance FORD-II AUROC (test): "
          f"{auroc_wi:.4f} ({lo_wi:.4f}-{hi_wi:.4f})", flush=True)

    # Primary FORD-II (no insurance) on same test set
    primary_score = compute_score(df_test, primary_weights, clip=True)
    pri_auroc, pri_lo, pri_hi = bootstrap_auc_ci(y_test, primary_score)
    print(f"  Primary FORD-II AUROC (test):        "
          f"{pri_auroc:.4f} ({pri_lo:.4f}-{pri_hi:.4f})", flush=True)

    delta = auroc_wi - pri_auroc if not (np.isnan(auroc_wi) or np.isnan(pri_auroc)) else np.nan
    print(f"  Delta (with-ins - primary): {delta:+.4f}", flush=True)

    # Insurance vars selected?
    ins_selected = [v for v in selected_vars if v in INSURANCE_VARS]
    print(f"  Insurance vars selected by LASSO: {ins_selected}", flush=True)

    # Build output table
    summary_rows = [
        {'metric': 'N_train', 'value': len(df_train)},
        {'metric': 'N_test', 'value': len(df_test)},
        {'metric': 'n_candidates', 'value': len(candidates_with_ins)},
        {'metric': 'insurance_vars_added', 'value': '; '.join(INSURANCE_VARS)},
        {'metric': 'insurance_vars_selected', 'value': '; '.join(ins_selected) if ins_selected else 'None'},
        {'metric': 'n_selected', 'value': len(selected_vars)},
        {'metric': 'selected_vars', 'value': '; '.join(selected_vars)},
        {'metric': 'with_ins_AUROC', 'value': round(auroc_wi, 4)},
        {'metric': 'with_ins_AUROC_CI_low', 'value': round(lo_wi, 4)},
        {'metric': 'with_ins_AUROC_CI_high', 'value': round(hi_wi, 4)},
        {'metric': 'primary_AUROC', 'value': round(pri_auroc, 4)},
        {'metric': 'primary_AUROC_CI_low', 'value': round(pri_lo, 4)},
        {'metric': 'primary_AUROC_CI_high', 'value': round(pri_hi, 4)},
        {'metric': 'delta_AUROC', 'value': round(delta, 4) if not np.isnan(delta) else 'NA'},
    ]

    # Append weights
    for _, row in weights_df.iterrows():
        summary_rows.append({
            'metric': f'weight_{row["Variable"]}',
            'value': row['Integer_points'],
        })

    result = pd.DataFrame(summary_rows)
    result.to_csv(out_path, index=False)
    print(f"\n  Saved {out_path}", flush=True)
    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)


# =====================================================================
# ANALYSIS 4: Subgroup AUROCs + forest plot
# =====================================================================
# NOTE (v3): v2 included a trauma-center VERIFICATION_LEVEL stratum. That column
# is NOT present in the 2019-2024 compiled NTDB pool, so the verification-level
# subgroup has been DROPPED from the subgroup loop. A placeholder footnote row
# with metric='verification_level' value='NOT_AVAILABLE_2019_2024_POOL' is
# appended to subgroups.csv so the manuscript can document the drop.
def build_subgroups(df: pd.DataFrame) -> pd.DataFrame:
    """Assign subgroup labels for stratified AUROC analysis."""
    df = df.copy()

    # Age bands
    age = pd.to_numeric(df['AGE_NUMBER'], errors='coerce')
    df['sg_age'] = pd.cut(age, bins=[-1, 64, 74, 200], labels=['<65', '65-74', '75+'])

    # Sex
    sex = df['SEX'].astype(str).str.strip().str.upper()
    df['sg_sex'] = np.where(sex == 'M', 'M', np.where(sex == 'F', 'F', None))

    # Fracture site
    icd = df['ICD10'].astype(str).str.strip().str.upper().str.replace('.', '', regex=False)
    prefix = icd.str[:3]
    df['sg_fracture'] = np.select(
        [
            prefix == 'S72',
            prefix.isin(['S12', 'S22', 'S32']),
        ],
        ['Hip (S72)', 'Axial (S12/S22/S32)'],
        default='Other',
    )

    # Mechanism
    ecode = df['CAUSE_E_CODES10'].astype(str).str.strip().str.upper()
    df['sg_mechanism'] = np.select(
        [
            ecode.str.startswith('W'),
            ecode.str.startswith('V'),
            ecode.str.startswith('X'),
        ],
        ['Fall (W)', 'MVC (V)', 'Assault (X)'],
        default='Other',
    )

    # v3: VERIFICATION_LEVEL is NOT available in the 2019-2024 pool — stratum dropped.

    # Year
    df['sg_year'] = df['PUF_YEAR'].astype(str)

    return df


def compute_subgroup_row(name: str, level: str, sub_df: pd.DataFrame,
                         score_col: str) -> dict:
    """Compute AUROC + bootstrap CI for a single subgroup level."""
    y = sub_df['outcome_nonhome'].astype(int).values
    s = sub_df[score_col].values
    n = len(sub_df)
    events = int(y.sum())

    base = dict(
        subgroup=name,
        level=level,
        n=n,
        events=events,
        event_rate_pct=round(100 * y.mean(), 2) if n else np.nan,
        auroc=np.nan,
        auroc_ci_lo=np.nan,
        auroc_ci_hi=np.nan,
    )

    if events < 10 or len(np.unique(y)) < 2:
        return base

    auroc, lo, hi = bootstrap_auc_ci(y, s)
    base.update(auroc=auroc, auroc_ci_lo=lo, auroc_ci_hi=hi)
    return base


def make_forest(out: pd.DataFrame, out_png: Path, out_pdf: Path) -> None:
    """Create a horizontal forest plot of subgroup AUROCs."""
    rows = out.dropna(subset=['auroc']).reset_index(drop=True)
    if rows.empty:
        print("  No rows with valid AUROC — skipping forest plot.", flush=True)
        return

    fig, ax = plt.subplots(figsize=(8, max(4, 0.3 * len(rows))))
    y_pos = np.arange(len(rows))[::-1]

    xerr_lo = rows['auroc'].values - rows['auroc_ci_lo'].values
    xerr_hi = rows['auroc_ci_hi'].values - rows['auroc'].values

    ax.errorbar(
        rows['auroc'].values,
        y_pos,
        xerr=[xerr_lo, xerr_hi],
        fmt='o',
        color='black',
        capsize=3,
        markersize=5,
        linewidth=1,
    )
    ax.axvline(0.5, color='gray', linestyle='--', linewidth=0.5)

    ax.set_yticks(y_pos)
    labels = [f"{r.subgroup}: {r.level} (n={r.n:,})" for r in rows.itertuples()]
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel('AUROC (95% CI)')
    ax.set_xlim(0.4, 1.0)
    ax.set_title('FORD-II AUROC by subgroup (test set)')

    plt.tight_layout()
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)
    print(f"  Saved {out_png}", flush=True)
    print(f"  Saved {out_pdf}", flush=True)


def analysis_subgroups(df: pd.DataFrame, primary_weights: dict) -> None:
    _banner("ANALYSIS 4: Subgroup AUROCs (primary frozen weights, test set)")
    t0 = time.time()

    out_table = TABLES_DIR / "subgroups.csv"
    out_fig_png = FIGURES_DIR / "figure_s2_subgroup_forest.png"
    out_fig_pdf = FIGURES_DIR / "figure_s2_subgroup_forest.pdf"

    # Use only the test set
    df_test = df[df['split'] == 'test'].copy()
    print(f"  Test set: N={len(df_test):,}", flush=True)

    # Compute primary FORD-II score on test set
    df_test['FORD_II_primary'] = compute_score(df_test, primary_weights, clip=True)

    # Build subgroup labels
    df_test = build_subgroups(df_test)

    # v3: 'Verification level' stratum dropped — VERIFICATION_LEVEL is not available
    # in the 2019-2024 compiled NTDB pool. Other strata retained.
    subgroup_cols = {
        'Age': 'sg_age',
        'Sex': 'sg_sex',
        'Fracture site': 'sg_fracture',
        'Mechanism': 'sg_mechanism',
        'Year': 'sg_year',
    }

    rows = []
    for sg_name, col in subgroup_cols.items():
        levels = pd.Series(df_test[col]).dropna().unique().tolist()
        try:
            levels = sorted(levels)
        except TypeError:
            pass
        for lvl in levels:
            sub = df_test[df_test[col] == lvl]
            row = compute_subgroup_row(sg_name, str(lvl), sub, 'FORD_II_primary')
            rows.append(row)
            status = f"AUROC {row['auroc']:.4f}" if not np.isnan(row['auroc']) else "skipped"
            print(f"    {sg_name}: {lvl:20s}  N={row['n']:>8,}  "
                  f"events={row['events']:>6,}  {status}", flush=True)

    # v3 footnote placeholder: verification_level not available in 2019-2024 pool
    rows.append({
        'subgroup': 'Verification level',
        'level': 'NOT_AVAILABLE_2019_2024_POOL',
        'n': 0,
        'events': 0,
        'event_rate_pct': np.nan,
        'auroc': np.nan,
        'auroc_ci_lo': np.nan,
        'auroc_ci_hi': np.nan,
    })
    print(f"    Verification level: dropped (not available in 2019-2024 NTDB pool)",
          flush=True)

    result = pd.DataFrame(rows)
    result.to_csv(out_table, index=False)
    print(f"\n  Saved {out_table}", flush=True)

    # Forest plot
    make_forest(result, out_fig_png, out_fig_pdf)

    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)


# =====================================================================
# ANALYSIS 5: Score truncation impact
# =====================================================================
def analysis_truncation(df: pd.DataFrame, primary_weights: dict) -> None:
    _banner("ANALYSIS 5: Score truncation impact (raw vs clipped 0-10)")
    t0 = time.time()

    out_path = TABLES_DIR / "sensitivity_truncation.csv"

    # Use only the test set
    df_test = df[df['split'] == 'test'].copy()
    y_test = df_test['outcome_nonhome'].values

    # Raw (unclipped) score
    score_raw = compute_score(df_test, primary_weights, clip=False)
    # Clipped [0, 10] score
    score_clipped = compute_score(df_test, primary_weights, clip=True)

    auroc_raw, lo_raw, hi_raw = bootstrap_auc_ci(y_test, score_raw)
    auroc_clip, lo_clip, hi_clip = bootstrap_auc_ci(y_test, score_clipped)

    delta = auroc_raw - auroc_clip if not (np.isnan(auroc_raw) or np.isnan(auroc_clip)) else np.nan

    print(f"  Test N: {len(df_test):,}", flush=True)
    print(f"  Raw score range: {score_raw.min()} to {score_raw.max()}", flush=True)
    print(f"  Clipped score range: {score_clipped.min()} to {score_clipped.max()}", flush=True)
    print(f"  AUROC (raw):     {auroc_raw:.4f} ({lo_raw:.4f}-{hi_raw:.4f})", flush=True)
    print(f"  AUROC (clipped): {auroc_clip:.4f} ({lo_clip:.4f}-{hi_clip:.4f})", flush=True)
    print(f"  Delta (raw - clipped): {delta:+.4f}", flush=True)

    # How many patients are affected by clipping?
    n_clipped_below = int((score_raw < 0).sum())
    n_clipped_above = int((score_raw > 10).sum())
    n_affected = n_clipped_below + n_clipped_above
    pct_affected = n_affected / len(df_test) * 100

    print(f"  N clipped below 0: {n_clipped_below:,}", flush=True)
    print(f"  N clipped above 10: {n_clipped_above:,}", flush=True)
    print(f"  Total affected: {n_affected:,} ({pct_affected:.1f}%)", flush=True)

    result = pd.DataFrame([
        {'metric': 'N_test', 'value': len(df_test)},
        {'metric': 'raw_score_min', 'value': int(score_raw.min())},
        {'metric': 'raw_score_max', 'value': int(score_raw.max())},
        {'metric': 'raw_score_mean', 'value': round(float(score_raw.mean()), 2)},
        {'metric': 'clipped_score_min', 'value': int(score_clipped.min())},
        {'metric': 'clipped_score_max', 'value': int(score_clipped.max())},
        {'metric': 'clipped_score_mean', 'value': round(float(score_clipped.mean()), 2)},
        {'metric': 'AUROC_raw', 'value': round(auroc_raw, 4)},
        {'metric': 'AUROC_raw_CI_low', 'value': round(lo_raw, 4)},
        {'metric': 'AUROC_raw_CI_high', 'value': round(hi_raw, 4)},
        {'metric': 'AUROC_clipped', 'value': round(auroc_clip, 4)},
        {'metric': 'AUROC_clipped_CI_low', 'value': round(lo_clip, 4)},
        {'metric': 'AUROC_clipped_CI_high', 'value': round(hi_clip, 4)},
        {'metric': 'delta_AUROC_raw_minus_clipped', 'value': round(delta, 4) if not np.isnan(delta) else 'NA'},
        {'metric': 'n_clipped_below_0', 'value': n_clipped_below},
        {'metric': 'n_clipped_above_10', 'value': n_clipped_above},
        {'metric': 'n_affected_total', 'value': n_affected},
        {'metric': 'pct_affected', 'value': round(pct_affected, 2)},
    ])
    result.to_csv(out_path, index=False)
    print(f"\n  Saved {out_path}", flush=True)
    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)


# =====================================================================
# ANALYSIS 6 (v3 NEW): ISS + GCS extra comparators
# =====================================================================
def analysis_extra_comparators(df: pd.DataFrame) -> None:
    """
    v3 supplementary comparator table.

    Reports AUROC + bootstrap 95% CI for ISS and GCS (raw continuous columns,
    higher=worse for both) as sole predictors on the v3 test set. Provides
    transparency / v2 continuity even though ISS and GCS are no longer in the
    primary comparator table.

    Output: extra_comparators.csv
        columns: comparator, n, auroc, auroc_ci_low, auroc_ci_high
    """
    _banner("ANALYSIS 6 (v3 NEW): ISS + GCS extra comparators")
    t0 = time.time()

    out_path = TABLES_DIR / "extra_comparators.csv"

    # Test set only
    df_test = df[df['split'] == 'test'].copy()
    y_test = df_test['outcome_nonhome'].values
    print(f"  Test N: {len(df_test):,}  (outcome rate {y_test.mean()*100:.1f}%)",
          flush=True)

    # ISS (higher = worse). GCS: use GCS2 if present, else GCS. For AUROC
    # direction we want higher=worse — the raw GCS scale is inverted (lower =
    # worse), so negate to align with "higher predicts non-home discharge".
    rows = []

    # ---------- ISS ----------
    iss_col = 'ISS' if 'ISS' in df_test.columns else None
    if iss_col is None:
        print("  WARNING: ISS column not found. Row will be NA.", flush=True)
        rows.append({
            'comparator': 'ISS',
            'n': 0,
            'auroc': np.nan,
            'auroc_ci_low': np.nan,
            'auroc_ci_high': np.nan,
        })
    else:
        iss_vals = pd.to_numeric(df_test[iss_col], errors='coerce')
        valid = iss_vals.notna() & pd.Series(y_test, index=df_test.index).notna()
        n_iss = int(valid.sum())
        if n_iss > 0 and len(np.unique(y_test[valid.values])) >= 2:
            iss_auroc, iss_lo, iss_hi = bootstrap_auc_ci(
                y_test[valid.values], iss_vals[valid].values)
        else:
            iss_auroc, iss_lo, iss_hi = np.nan, np.nan, np.nan
        print(f"  ISS: n={n_iss:,}  AUROC={iss_auroc:.4f} "
              f"({iss_lo:.4f}-{iss_hi:.4f})", flush=True)
        rows.append({
            'comparator': 'ISS',
            'n': n_iss,
            'auroc': round(iss_auroc, 4) if not np.isnan(iss_auroc) else np.nan,
            'auroc_ci_low': round(iss_lo, 4) if not np.isnan(iss_lo) else np.nan,
            'auroc_ci_high': round(iss_hi, 4) if not np.isnan(iss_hi) else np.nan,
        })

    # ---------- GCS ----------
    # Prefer GCS2 (total, higher=worse when negated) then GCS. Column name is
    # recorded in the output comparator label to match whichever is used.
    gcs_col = None
    for candidate in ('GCS2', 'GCS'):
        if candidate in df_test.columns:
            gcs_col = candidate
            break

    if gcs_col is None:
        print("  WARNING: neither GCS2 nor GCS column found. Row will be NA.",
              flush=True)
        rows.append({
            'comparator': 'GCS',
            'n': 0,
            'auroc': np.nan,
            'auroc_ci_low': np.nan,
            'auroc_ci_high': np.nan,
        })
    else:
        gcs_vals = pd.to_numeric(df_test[gcs_col], errors='coerce')
        # higher=worse: raw GCS is lower=worse, so negate for AUROC so that
        # higher predicted score corresponds to higher risk of non-home.
        score_gcs = -gcs_vals
        valid = gcs_vals.notna() & pd.Series(y_test, index=df_test.index).notna()
        n_gcs = int(valid.sum())
        if n_gcs > 0 and len(np.unique(y_test[valid.values])) >= 2:
            gcs_auroc, gcs_lo, gcs_hi = bootstrap_auc_ci(
                y_test[valid.values], score_gcs[valid].values)
        else:
            gcs_auroc, gcs_lo, gcs_hi = np.nan, np.nan, np.nan
        print(f"  {gcs_col} (higher=worse via negation): n={n_gcs:,}  "
              f"AUROC={gcs_auroc:.4f} ({gcs_lo:.4f}-{gcs_hi:.4f})", flush=True)
        rows.append({
            'comparator': gcs_col,
            'n': n_gcs,
            'auroc': round(gcs_auroc, 4) if not np.isnan(gcs_auroc) else np.nan,
            'auroc_ci_low': round(gcs_lo, 4) if not np.isnan(gcs_lo) else np.nan,
            'auroc_ci_high': round(gcs_hi, 4) if not np.isnan(gcs_hi) else np.nan,
        })

    result = pd.DataFrame(rows, columns=[
        'comparator', 'n', 'auroc', 'auroc_ci_low', 'auroc_ci_high'])
    result.to_csv(out_path, index=False)
    print(f"\n  Saved {out_path}", flush=True)
    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)


# =====================================================================
# MAIN
# =====================================================================
def main() -> None:
    t_start = time.time()

    _banner("05_ford2_v3_sensitivity.py — FORD-II v3 Sensitivity Analyses")

    # --- Load data ---
    print(f"  Loading {INPUT_PARQUET}", flush=True)
    df = pd.read_parquet(INPUT_PARQUET)
    print(f"  Loaded {len(df):,} rows x {df.shape[1]} columns", flush=True)
    print(f"  Split distribution: {df['split'].value_counts().to_dict()}", flush=True)
    print(f"  Outcome rate: {df['outcome_nonhome'].mean()*100:.1f}%", flush=True)

    # --- Load primary FORD-II weights ---
    primary_weights = load_primary_weights()

    # --- Run sensitivity analyses ---
    try:
        analysis_temporal(df, primary_weights)
    except Exception as e:
        print(f"\n  ERROR in Analysis 1 (Temporal): {e}", flush=True)
        pd.DataFrame([{'metric': 'error', 'value': str(e)}]).to_csv(
            TABLES_DIR / "sensitivity_temporal.csv", index=False)

    try:
        analysis_comorbidity(df, primary_weights)
    except Exception as e:
        print(f"\n  ERROR in Analysis 2 (Comorbidity): {e}", flush=True)
        pd.DataFrame([{'metric': 'error', 'value': str(e)}]).to_csv(
            TABLES_DIR / "sensitivity_comorbidity.csv", index=False)

    try:
        analysis_with_insurance(df, primary_weights)
    except Exception as e:
        print(f"\n  ERROR in Analysis 3 (With Insurance): {e}", flush=True)
        pd.DataFrame([{'metric': 'error', 'value': str(e)}]).to_csv(
            TABLES_DIR / "sensitivity_with_insurance.csv", index=False)

    try:
        analysis_subgroups(df, primary_weights)
    except Exception as e:
        print(f"\n  ERROR in Analysis 4 (Subgroups): {e}", flush=True)
        pd.DataFrame([{'metric': 'error', 'value': str(e)}]).to_csv(
            TABLES_DIR / "subgroups.csv", index=False)

    try:
        analysis_truncation(df, primary_weights)
    except Exception as e:
        print(f"\n  ERROR in Analysis 5 (Truncation): {e}", flush=True)
        pd.DataFrame([{'metric': 'error', 'value': str(e)}]).to_csv(
            TABLES_DIR / "sensitivity_truncation.csv", index=False)

    try:
        analysis_extra_comparators(df)
    except Exception as e:
        print(f"\n  ERROR in Analysis 6 (Extra Comparators): {e}", flush=True)
        pd.DataFrame([{
            'comparator': 'ERROR',
            'n': 0,
            'auroc': np.nan,
            'auroc_ci_low': np.nan,
            'auroc_ci_high': np.nan,
        }]).to_csv(TABLES_DIR / "extra_comparators.csv", index=False)

    # --- Final summary ---
    elapsed = time.time() - t_start
    _banner("COMPLETE")
    print(f"  Total elapsed: {elapsed:.1f}s", flush=True)
    print(f"  Outputs:", flush=True)
    for f in sorted(TABLES_DIR.glob("table_s*.csv")):
        print(f"    {f}", flush=True)
    for f in sorted(FIGURES_DIR.glob("figure_s2*")):
        print(f"    {f}", flush=True)


if __name__ == "__main__":
    main()
