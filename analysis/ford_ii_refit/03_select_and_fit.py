#!/usr/bin/env python3
"""
03_select_and_fit.py — LASSO feature selection, unpenalized refit,
                       RAMS Method B integer scoring for FORD-II.

This is the core model-building script for FORD-II, a nationally derived
non-home discharge prediction score using NTDB data (2019–2024).

Pipeline position:  02_features.py -> [THIS] -> 04_validate.py

Input:
    data/ford2_features.parquet   (from 02_features.py)

Outputs:
    data/ford2_model.parquet                   — full dataset with scores
    tables/candidate_pool.csv           — 48 candidates, LASSO selection
    tables/ford_ii_weights.csv                 — selected predictors + integer pts
    figures/figure_s1_lasso_path.png + .pdf    — regularization path

Seed:    42
"""

# ---------------------------------------------------------------------------
# Imports  (matplotlib Agg MUST be set before pyplot)
# ---------------------------------------------------------------------------
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import random
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
import statsmodels.api as sm

warnings.filterwarnings('ignore')
np.random.seed(42)
random.seed(42)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent       # .../analysis/ford_ii_refit/
REPO_ROOT = SCRIPT_DIR.parents[1]                  # public repo root
TABLES_DIR = REPO_ROOT / "tables"
FIGURES_DIR = REPO_ROOT / "figures"
DATA_DIR = SCRIPT_DIR / "data"                     # gitignored
INPUT = DATA_DIR / "ford2_features.parquet"
OUT_PARQUET = DATA_DIR / "ford2_model.parquet"
TABLES_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42

# ---------------------------------------------------------------------------
# Candidate variable pool (41 — v2's 45 minus 4 insurance vars excluded from primary pool per plan)
# ---------------------------------------------------------------------------
# FORD-II candidate variables: ED-admission bedside variables ONLY.
# Excluded by design (not available at ED admission):
#   - ISS bands — requires full injury coding
#   - Toxicology / alcohol — lab results
#   - ins_medicaid — not separable from Medicare in NTDB (MCARE-M = both)
#   - Insurance variables — excluded to produce a purely clinical score
#     without payer/administrative variables. The no-insurance model
#     outperforms the with-insurance model (AUROC 0.834 vs 0.812).
#     See sensitivity analysis (script 05) for with-insurance comparison.
ALL_CANDIDATES = [
    # Age
    'age_45_64', 'age_65_74', 'age_75plus',
    # Sex
    'female',
    # Race
    'race_black', 'race_asian', 'race_native', 'race_other',
    # Ethnicity
    'ethnicity_hispanic',
    # Vitals
    'sbp_hypotensive', 'sbp_hypertensive',
    'hr_bradycardic', 'hr_tachycardic',
    'rr_low', 'rr_high',
    'gcs_moderate', 'gcs_severe',
    'hypoxic',
    'temp_hypothermic', 'temp_hyperthermic',
    # BMI
    'bmi_underweight', 'bmi_overweight', 'bmi_obese_12', 'bmi_obese_3',
    # Fracture site (9 granular)
    'frac_cervical', 'frac_thoracic', 'frac_lumbar', 'frac_humerus',
    'frac_forearm', 'frac_hand', 'frac_hip_femur', 'frac_leg', 'frac_foot',
    # Mechanism
    'mech_mvc', 'mech_assault', 'mech_other',
    # Transport
    'trans_auto', 'trans_air', 'trans_other_mode',
    # Hospital access
    'transfer_in', 'prehospital_arrest',
]

# ---------------------------------------------------------------------------
# FORD comparator weights are loaded and applied in 02_features.py using the
# frozen 15-row FORD V9 published weights (see FORD_V1_WEIGHTS in 02), with
# trans_walk locked to 0 for NTDB rows. The columns `ford_original_score`,
# `FORD_score_raw`, and `FORD_0_10` arrive pre-computed on the features
# parquet; 03 does NOT rebuild them here.
# ---------------------------------------------------------------------------


def _banner(msg: str) -> None:
    bar = "=" * 72
    print(f"\n{bar}\n{msg}\n{bar}", flush=True)


# =====================================================================
# STEP 1: Load data
# =====================================================================
def load_data() -> pd.DataFrame:
    _banner("STEP 1: Load features parquet")
    t0 = time.time()
    df = pd.read_parquet(INPUT)
    print(f"  Loaded {len(df):,} rows x {df.shape[1]} columns", flush=True)
    print(f"  outcome_nonhome rate: {df['outcome_nonhome'].mean() * 100:.1f}%", flush=True)
    print(f"  Elapsed {time.time() - t0:.1f}s", flush=True)
    return df


# =====================================================================
# STEP 2: Validate and prune candidate variables
# =====================================================================
def validate_candidates(df: pd.DataFrame) -> list[str]:
    _banner("STEP 2: Validate candidate variables")

    # Check which candidates exist in the dataframe
    missing = [v for v in ALL_CANDIDATES if v not in df.columns]
    present = [v for v in ALL_CANDIDATES if v in df.columns]

    if missing:
        print(f"  DROPPED (not in dataframe): {missing}", flush=True)

    # Check for zero variance (prevalence 0% or 100%)
    zero_var = []
    for v in present:
        col = df[v]
        if col.nunique() <= 1:
            zero_var.append(v)

    if zero_var:
        print(f"  DROPPED (zero variance): {zero_var}", flush=True)

    candidates = [v for v in present if v not in zero_var]
    print(f"  {len(candidates)} candidates retained out of {len(ALL_CANDIDATES)} total", flush=True)
    return candidates


# =====================================================================
# STEP 3: Train/test split (2/3 derivation, 1/3 validation)
# =====================================================================
def split_data(df: pd.DataFrame, candidates: list[str]):
    _banner("STEP 3: Train/test split (2/3 - 1/3, stratified)")

    X = df[candidates].values
    y = df['outcome_nonhome'].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=1/3, stratify=y, random_state=SEED
    )

    # Also track indices for the split column
    idx = np.arange(len(df))
    idx_train, idx_test = train_test_split(
        idx, test_size=1/3, stratify=y, random_state=SEED
    )

    split = np.empty(len(df), dtype=object)
    split[idx_train] = 'train'
    split[idx_test] = 'test'

    print(f"  Train: {len(idx_train):,}  |  Test: {len(idx_test):,}", flush=True)
    print(f"  Train outcome rate: {y_train.mean() * 100:.1f}%", flush=True)
    print(f"  Test  outcome rate: {y_test.mean() * 100:.1f}%", flush=True)

    # Create DataFrames for statsmodels
    X_train_df = pd.DataFrame(X_train, columns=candidates)
    X_test_df = pd.DataFrame(X_test, columns=candidates)

    return X_train, X_test, y_train, y_test, X_train_df, X_test_df, split


# =====================================================================
# STEP 4: LASSO (L1 logistic) feature selection
# =====================================================================
def run_lasso(X_train, y_train, candidates: list[str]):
    _banner("STEP 4: LASSO feature selection (L1 logistic, 5-fold CV)")
    t0 = time.time()

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
    lasso_cv.fit(X_train, y_train)

    elapsed = time.time() - t0
    print(f"  Elapsed: {elapsed:.1f}s", flush=True)
    print(f"  Best C: {lasso_cv.C_[0]:.6f}", flush=True)
    print(f"  n_iter_: {lasso_cv.n_iter_}", flush=True)

    # Extract LASSO coefficients
    lasso_coefs = lasso_cv.coef_[0]
    selected_mask = lasso_coefs != 0
    selected_vars = [v for v, sel in zip(candidates, selected_mask) if sel]

    print(f"\n  Selected {len(selected_vars)} / {len(candidates)} features:", flush=True)
    for v, c in sorted(zip(candidates, lasso_coefs), key=lambda x: abs(x[1]), reverse=True):
        if c != 0:
            print(f"    {v:25s}  LASSO coef = {c:+.4f}", flush=True)

    return lasso_cv, lasso_coefs, selected_vars


# =====================================================================
# STEP 5: Unpenalized refit + backward elimination (p < 0.05)
# =====================================================================
def refit_unpenalized(X_train_df: pd.DataFrame, y_train, selected_vars: list[str]):
    _banner("STEP 5: Unpenalized logistic regression + backward elimination")
    t0 = time.time()

    # Step 5a: Initial refit on all LASSO-selected features
    current_vars = list(selected_vars)
    print(f"  Initial model: {len(current_vars)} variables", flush=True)

    # Step 5b: Backward elimination — drop highest p > 0.05, refit, repeat
    iteration = 0
    while True:
        X_sel = sm.add_constant(X_train_df[current_vars])
        model = sm.Logit(y_train, X_sel).fit(disp=0, maxiter=200)

        pvals = model.pvalues[1:]  # exclude intercept
        max_p = pvals.max()
        max_p_var = pvals.idxmax()

        if max_p <= 0.05:
            break

        iteration += 1
        print(f"  Iter {iteration}: dropping {max_p_var} (p = {max_p:.4f})", flush=True)
        current_vars.remove(max_p_var)

        if len(current_vars) == 0:
            raise ValueError("All variables eliminated — backward elimination failed")

    n_after_p = len(current_vars)
    print(f"\n  After p-value elimination: {n_after_p} variables", flush=True)

    # Step 5c: Clinical significance pruning — drop variables with |β| < 0.35
    # At N=1.85M, many tiny effects are statistically significant but clinically
    # negligible. The original FORD's smallest β was ~0.355 (hr_tachycardic).
    # We use the same threshold to ensure FORD-II predictors are clinically
    # meaningful AND to produce differentiated integer weights in Method B.
    BETA_THRESHOLD = 0.35
    betas_current = model.params[1:]  # exclude intercept
    weak_vars = [v for v, b in zip(current_vars, betas_current) if abs(b) < BETA_THRESHOLD]
    if weak_vars:
        print(f"\n  Pruning {len(weak_vars)} variables with |β| < {BETA_THRESHOLD}:", flush=True)
        for v in weak_vars:
            b = float(betas_current[current_vars.index(v)])
            print(f"    {v:30s}  β = {b:+.4f}  (OR = {np.exp(b):.2f})", flush=True)
        current_vars = [v for v in current_vars if v not in weak_vars]

        # Refit with pruned variable set
        X_sel = sm.add_constant(X_train_df[current_vars])
        model = sm.Logit(y_train, X_sel).fit(disp=0, maxiter=200)

    print(f"\n  Final model: {len(current_vars)} variables "
          f"(dropped {len(selected_vars) - len(current_vars)} total: "
          f"{len(selected_vars) - n_after_p} by p-value, "
          f"{n_after_p - len(current_vars)} by |β| < {BETA_THRESHOLD})", flush=True)
    print(model.summary2().tables[1].to_string(), flush=True)
    print(f"\n  Pseudo R-squared: {model.prsquared:.4f}", flush=True)
    print(f"  Log-Likelihood:   {model.llf:.1f}", flush=True)
    print(f"  AIC:              {model.aic:.1f}", flush=True)
    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)

    return model, current_vars


# =====================================================================
# STEP 6: Integer score construction (RAMS Method B)
# =====================================================================
def build_integer_score(model, selected_vars: list[str]):
    _banner("STEP 6: Integer score construction (RAMS Method B)")

    betas = model.params[1:]       # exclude intercept
    ses = model.bse[1:]
    pvals = model.pvalues[1:]
    conf = model.conf_int().iloc[1:]  # rows for predictors only

    # Identify smallest positive coefficient for Method B denominator
    pos_betas = [float(betas.iloc[i]) for i in range(len(selected_vars))
                 if float(betas.iloc[i]) > 0]
    if not pos_betas:
        raise ValueError("No positive coefficients found — cannot compute Method B weights")
    min_pos_coef = min(pos_betas)
    print(f"  min positive beta: {min_pos_coef:.4f}", flush=True)

    # Standard Method B: divide by min_pos_coef
    # After clinical significance pruning (|β| >= 0.35), the predictor set
    # should be small enough (~15-25) that this produces reasonable weights.
    effective_divisor = min_pos_coef
    raw_weights_test = [float(betas.iloc[i]) / effective_divisor for i in range(len(selected_vars))]
    raw_pos = sum(max(round(w), 1) if w > 0 else round(w) for w in raw_weights_test)
    raw_neg = sum(round(w) for w in raw_weights_test if round(w) < 0)
    print(f"  Method B theoretical range: {raw_neg} to {raw_pos} (span = {raw_pos - raw_neg})", flush=True)

    weights = {}
    rows = []
    for i, var in enumerate(selected_vars):
        beta = float(betas.iloc[i])
        se = float(ses.iloc[i])
        pval = float(pvals.iloc[i])
        or_val = np.exp(beta)
        ci_low = np.exp(float(conf.iloc[i, 0]))
        ci_high = np.exp(float(conf.iloc[i, 1]))

        raw_weight = beta / effective_divisor
        points = round(raw_weight)
        # Floor positive at 1
        if beta > 0 and points < 1:
            points = 1

        weights[var] = points

        rows.append({
            'Variable': var,
            'Beta': round(beta, 4),
            'SE': round(se, 4),
            'OR': round(or_val, 2),
            'CI_low': round(ci_low, 2),
            'CI_high': round(ci_high, 2),
            'P_value': round(pval, 4),
            'Raw_weight': round(raw_weight, 2),
            'Integer_points': points,
        })

    # Sort by absolute points descending
    rows.sort(key=lambda r: abs(r['Integer_points']), reverse=True)

    print(f"\n  {'Variable':30s} {'OR':>7s} {'95% CI':>16s} {'p':>8s} {'Pts':>5s}")
    print("  " + "-" * 70)
    for r in rows:
        print(f"  {r['Variable']:30s} {r['OR']:7.2f} "
              f"({r['CI_low']:5.2f}-{r['CI_high']:5.2f}) "
              f"{r['P_value']:8.4f} {r['Integer_points']:5d}", flush=True)

    total_pos = sum(p for p in weights.values() if p > 0)
    total_neg = sum(p for p in weights.values() if p < 0)
    print(f"\n  Theoretical max score (all positive): {total_pos}")
    print(f"  Theoretical min score (all negative): {total_neg}")
    print(f"  Clipped to 0-10 for final FORD-II score")

    return weights, pd.DataFrame(rows)


# =====================================================================
# STEP 7: Build Table 2 — candidate pool overview
# =====================================================================
def build_table2(X_train_df: pd.DataFrame, y_train, candidates: list[str],
                 lasso_coefs, selected_vars: list[str]):
    _banner("STEP 7: Table 2 — candidate pool (all ~48)")
    t0 = time.time()

    rows = []
    for i, var in enumerate(candidates):
        col = X_train_df[var]
        prevalence = col.mean() * 100

        # Univariate logistic regression
        try:
            X_uni = sm.add_constant(col)
            uni_model = sm.Logit(y_train, X_uni).fit(disp=0, maxiter=100)
            uni_or = np.exp(uni_model.params.iloc[1])
            uni_ci_low = np.exp(uni_model.conf_int().iloc[1, 0])
            uni_ci_high = np.exp(uni_model.conf_int().iloc[1, 1])
            uni_p = uni_model.pvalues.iloc[1]
        except Exception:
            uni_or = np.nan
            uni_ci_low = np.nan
            uni_ci_high = np.nan
            uni_p = np.nan

        lasso_c = lasso_coefs[i]
        selected = "Selected" if var in selected_vars else "Not selected"

        rows.append({
            'Variable': var,
            'Prevalence_pct': round(prevalence, 1),
            'Univariate_OR': round(uni_or, 2) if not np.isnan(uni_or) else np.nan,
            'Univariate_CI_low': round(uni_ci_low, 2) if not np.isnan(uni_ci_low) else np.nan,
            'Univariate_CI_high': round(uni_ci_high, 2) if not np.isnan(uni_ci_high) else np.nan,
            'Univariate_p': round(uni_p, 4) if not np.isnan(uni_p) else np.nan,
            'LASSO_coef': round(lasso_c, 4),
            'Selection_status': selected,
        })

    table2 = pd.DataFrame(rows)
    outpath = TABLES_DIR / "candidate_pool.csv"
    table2.to_csv(outpath, index=False)
    print(f"  Saved {outpath}", flush=True)
    print(f"  Selected: {sum(1 for r in rows if r['Selection_status'] == 'Selected')}", flush=True)
    print(f"  Not selected: {sum(1 for r in rows if r['Selection_status'] == 'Not selected')}", flush=True)
    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)

    return table2


# =====================================================================
# STEP 8: Save Table 3 — FORD-II weights
# =====================================================================
def save_table3(weights_df: pd.DataFrame):
    _banner("STEP 8: Table 3 — FORD-II weights")
    outpath = TABLES_DIR / "ford_ii_weights.csv"
    weights_df.to_csv(outpath, index=False)
    print(f"  Saved {outpath}  ({len(weights_df)} predictors)", flush=True)


# =====================================================================
# STEP 9: LASSO path figure
# =====================================================================
def plot_lasso_path(X_train, y_train, candidates: list[str]):
    _banner("STEP 9: LASSO regularization path figure")
    t0 = time.time()

    # Generate a range of C values (inverse regularization strength)
    Cs = np.logspace(-4, 2, 50)
    coefs_path = []

    for c in Cs:
        lr = LogisticRegression(
            penalty='l1', solver='saga', C=c,
            max_iter=3000, random_state=SEED,
        )
        lr.fit(X_train, y_train)
        coefs_path.append(lr.coef_[0].copy())

    coefs_path = np.array(coefs_path)  # shape (n_Cs, n_features)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    # Only label features that are nonzero at the strongest regularization (largest C)
    final_nonzero = np.where(coefs_path[-1] != 0)[0]

    for j in range(coefs_path.shape[1]):
        if j in final_nonzero:
            ax.plot(np.log10(Cs), coefs_path[:, j], linewidth=1.2, label=candidates[j])
        else:
            ax.plot(np.log10(Cs), coefs_path[:, j], linewidth=0.5, color='lightgray',
                    alpha=0.5)

    ax.axhline(0, color='black', linewidth=0.5, linestyle='--')
    ax.set_xlabel('log10(C)  [stronger regularization ← → weaker]', fontsize=12)
    ax.set_ylabel('Coefficient value', fontsize=12)
    ax.set_title('FORD-II: LASSO Regularization Path', fontsize=14)

    # Legend outside plot if many features
    if len(final_nonzero) <= 25:
        ax.legend(fontsize=7, loc='upper left', bbox_to_anchor=(1.02, 1.0),
                  borderaxespad=0)
        fig.subplots_adjust(right=0.72)
    else:
        ax.legend(fontsize=6, loc='upper left', bbox_to_anchor=(1.02, 1.0),
                  borderaxespad=0, ncol=2)
        fig.subplots_adjust(right=0.60)

    ax.grid(True, alpha=0.3)

    for fmt in ['png', 'pdf']:
        outpath = FIGURES_DIR / f"figure_s1_lasso_path.{fmt}"
        fig.savefig(outpath, dpi=300, bbox_inches='tight')
    plt.close(fig)

    print(f"  Saved figure_s1_lasso_path.{{png,pdf}}", flush=True)
    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)


# =====================================================================
# STEP 10: Compute FORD-II score for all patients
# =====================================================================
def compute_ford2_score(df: pd.DataFrame, weights: dict[str, int]) -> pd.DataFrame:
    _banner("STEP 10: Compute FORD-II score for all patients")

    # Vectorized score computation
    score_raw = pd.Series(0, index=df.index, dtype=int)
    for var, pts in weights.items():
        if var in df.columns:
            score_raw += pts * df[var].astype(int)
        else:
            print(f"  WARNING: {var} not in dataframe, skipping", flush=True)

    df['FORD_II_score_raw'] = score_raw
    df['FORD_II_0_10'] = score_raw.clip(0, 10)

    print(f"  Raw score range: {score_raw.min()} to {score_raw.max()}", flush=True)
    print(f"  Clipped (0-10) distribution:", flush=True)
    dist = df['FORD_II_0_10'].value_counts().sort_index()
    for val, cnt in dist.items():
        pct = cnt / len(df) * 100
        print(f"    Score {val:3d}: {cnt:>8,}  ({pct:5.1f}%)", flush=True)

    return df


# =====================================================================
# STEP 11: Compute comparator scores (original FORD, GTOS-II, TRIAGES, ISS, GCS)
# =====================================================================
def compute_comparators(df: pd.DataFrame) -> pd.DataFrame:
    _banner("STEP 11: Compute comparator scores")

    # FORD comparator columns (ford_original_score, FORD_score_raw, FORD_0_10)
    # are computed in 02_features.py using the frozen V9 15-row weights from
    # ford_v1_weights.csv (see FORD_V1_WEIGHTS in 02) with trans_walk locked to 0.

    # --- Comparators: GTOS_II, triages_total ---
    # These should already exist from script 02. Verify and pass through.
    # (ISS and GCS are handled as sole-predictor raw-column AUROCs in script 05
    # table S8, per plan.)
    comparators = ['GTOS_II', 'triages_total']
    for comp in comparators:
        if comp in df.columns:
            valid = df[comp].notna().sum()
            print(f"  {comp}: present, {valid:,} valid values "
                  f"(range {df[comp].min():.1f} - {df[comp].max():.1f})", flush=True)
        else:
            print(f"  WARNING: {comp} not found in features parquet", flush=True)

    return df


# =====================================================================
# STEP 13: Diagnostic summary
# =====================================================================
def print_diagnostics(df: pd.DataFrame, selected_vars: list[str],
                      weights: dict[str, int]):
    _banner("STEP 13: Diagnostic summary for downstream scripts")

    # Split back to train/test
    train_mask = df['split'] == 'train'
    test_mask = df['split'] == 'test'
    y = df['outcome_nonhome']

    # --- FORD-II AUROC ---
    ford2_auroc_train = roc_auc_score(y[train_mask], df.loc[train_mask, 'FORD_II_0_10'])
    ford2_auroc_test = roc_auc_score(y[test_mask], df.loc[test_mask, 'FORD_II_0_10'])

    print(f"  FORD-II selected features: {len(selected_vars)}", flush=True)
    print(f"  FORD-II score range (0-10): "
          f"min={df['FORD_II_0_10'].min()}, max={df['FORD_II_0_10'].max()}, "
          f"mean={df['FORD_II_0_10'].mean():.2f}", flush=True)
    print(f"  FORD-II AUROC (train): {ford2_auroc_train:.4f}", flush=True)
    print(f"  FORD-II AUROC (test):  {ford2_auroc_test:.4f}", flush=True)

    if ford2_auroc_test < 0.80:
        print("  *** WARNING: FORD-II test AUROC < 0.80 — review model ***", flush=True)

    # --- Original FORD AUROC ---
    if 'FORD_0_10' in df.columns:
        ford_auroc_train = roc_auc_score(y[train_mask], df.loc[train_mask, 'FORD_0_10'])
        ford_auroc_test = roc_auc_score(y[test_mask], df.loc[test_mask, 'FORD_0_10'])
        print(f"  Original FORD AUROC (train): {ford_auroc_train:.4f}", flush=True)
        print(f"  Original FORD AUROC (test):  {ford_auroc_test:.4f}", flush=True)

    # --- Other comparators ---
    for comp in ['GTOS_II', 'triages_total']:
        if comp in df.columns:
            valid = df[comp].notna() & test_mask
            if valid.sum() > 100:
                auroc = roc_auc_score(y[valid], df.loc[valid, comp])
                print(f"  {comp} AUROC (test, N={valid.sum():,}): {auroc:.4f}", flush=True)

    # --- FORD-II score histogram ---
    print(f"\n  FORD-II (0-10) histogram on full cohort:", flush=True)
    for score_val in range(11):
        n = (df['FORD_II_0_10'] == score_val).sum()
        pct = n / len(df) * 100
        bar = "#" * max(1, int(pct))
        print(f"    {score_val:2d}: {n:>9,} ({pct:5.1f}%) {bar}", flush=True)

    # --- Key info for downstream scripts ---
    print(f"\n  === INFO FOR DOWNSTREAM SCRIPTS (04, 05) ===", flush=True)
    print(f"  Output parquet: {OUT_PARQUET}", flush=True)
    print(f"  Weights table:  {TABLES_DIR / 'ford_ii_weights.csv'}", flush=True)
    print(f"  Score columns:  FORD_II_score_raw, FORD_II_0_10", flush=True)
    print(f"  Comparators:    FORD_score_raw, FORD_0_10, GTOS_II, triages_total (ISS and GCS deferred to script 05 table S8)", flush=True)
    print(f"  Split column:   'split' ('train' / 'test')", flush=True)
    print(f"  Outcome column: 'outcome_nonhome'", flush=True)
    print(f"  Selected vars:  {selected_vars}", flush=True)
    print(f"  Integer weights: {weights}", flush=True)


# =====================================================================
# MAIN
# =====================================================================
def main() -> None:
    t_start = time.time()

    # Step 1: Load
    df = load_data()

    # Step 2: Validate candidates
    candidates = validate_candidates(df)

    # Step 3: Split
    X_train, X_test, y_train, y_test, X_train_df, X_test_df, split = \
        split_data(df, candidates)
    df['split'] = split

    # Step 4: LASSO
    lasso_cv, lasso_coefs, selected_vars = run_lasso(X_train, y_train, candidates)

    if len(selected_vars) == 0:
        raise RuntimeError("LASSO selected 0 features — check data quality or Cs range")

    # Step 5: Unpenalized refit + backward elimination
    model, final_vars = refit_unpenalized(X_train_df, y_train, selected_vars)

    # Step 6: Integer score (RAMS Method B)
    weights, weights_df = build_integer_score(model, final_vars)

    # Step 7: Table 2 (candidate pool)
    table2 = build_table2(X_train_df, y_train, candidates, lasso_coefs, selected_vars)

    # Step 8: Table 3 (FORD-II weights)
    save_table3(weights_df)

    # Step 9: LASSO path figure
    plot_lasso_path(X_train, y_train, candidates)

    # Step 10: Compute FORD-II score
    df = compute_ford2_score(df, weights)

    # Step 11: Comparator scores
    df = compute_comparators(df)

    # Step 12: Save output parquet
    _banner("STEP 12: Save output parquet")
    t0 = time.time()
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)
    print(f"  Saved {OUT_PARQUET}", flush=True)
    print(f"  {len(df):,} rows x {df.shape[1]} columns", flush=True)
    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)

    # Step 13: Diagnostics
    print_diagnostics(df, selected_vars, weights)

    print(f"\n{'=' * 72}")
    print(f"FORD-II model build complete.  Total elapsed: {time.time() - t_start:.1f}s")
    print(f"{'=' * 72}\n", flush=True)


if __name__ == "__main__":
    main()
