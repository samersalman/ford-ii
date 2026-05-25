#!/usr/bin/env python3
"""
04_validate.py — Head-to-head validation of FORD-II vs 3 comparators
                 (FORD, GTOS-II, TRIAGES) on the held-out NTDB 2019-2024
                 test set, plus optional single-center reverse validation.

Pipeline position:  03_select_and_fit.py -> [THIS] -> 05_sensitivity.py

Cohort: NTDB PUF 2019-2024 (FORD-II)

Primary comparator strategy: FORD, GTOS-II, TRIAGES. ISS and GCS are NOT in
the primary Table 4 / Figure 2 here — they appear only in the supplementary
extras table produced by 05_sensitivity.py.

Input:
    data/ford2_model.parquet   (from 03_select_and_fit.py; split, scores, outcome)

Outputs (under repo tables/ and figures/):
    tables/baseline.csv                 — Train vs test baseline, SMDs
    tables/validation_metrics.csv              — FORD-II vs 3 comparators
    tables/risk_groups.csv                     — FORD-II + FORD risk stratification
    tables/sensitivity_bentaub_reverse.csv        — Single-center reverse validation (optional)

    figures/figure1_consort.{png,pdf}      — CONSORT flow diagram
    figures/figure2_roc_curves.{png,pdf}   — ROC: 4 scores overlaid
    figures/figure3_calibration.{png,pdf}  — Calibration plot (decile bins)
    figures/figure4_risk_groups.{png,pdf}  — Risk group bar chart
    figures/figure5_dca.{png,pdf}          — Decision curve analysis

Seed:    42
"""

# ---------------------------------------------------------------------------
# Step 0: Matplotlib Agg backend (MUST be before pyplot import)
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
from scipy.stats import chi2 as chi2_dist, norm
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
import statsmodels.api as sm
from statsmodels.stats.proportion import proportion_confint

warnings.filterwarnings('ignore')
np.random.seed(42)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent       # .../analysis/ford_ii_refit/
REPO_ROOT = SCRIPT_DIR.parents[1]                  # public repo root
TABLES_DIR = REPO_ROOT / "tables"
FIGURES_DIR = REPO_ROOT / "figures"
DATA_DIR = SCRIPT_DIR / "data"                     # gitignored
INPUT_PARQUET = DATA_DIR / "ford2_model.parquet"
CONSORT_CSV = DATA_DIR / "consort_flow_ford2_v3.csv"
WEIGHTS_CSV = TABLES_DIR / "ford_ii_weights.csv"
TABLES_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Optional single-center dataset for reverse validation (NOT shipped in the
# public repo). Set environment variable BEN_TAUB_CSV to a local CSV path to
# enable; otherwise the reverse validation step is skipped.
BEN_TAUB_CSV = Path(os.environ.get("BEN_TAUB_CSV", ""))

SEED = 42
N_BOOT = int(os.environ.get("FORD_II_NBOOT", "1000"))

# ---------------------------------------------------------------------------
# Frozen original FORD-19 weights (from FORD V8 submission)
# ---------------------------------------------------------------------------
FORD_WEIGHTS = {
    'gcs_severe': 6,
    'hip_femur': 5,
    'rr_low': 5,
    'ins_other': 4,
    'ins_medicare': 4,
    'sbp_hypotensive': 4,
    'age_75plus': 3,
    'gcs_moderate': 3,
    'axial_fracture': 3,
    'ins_private': 3,
    'ins_charity': 3,
    'bmi_obese_3': 2,
    'rr_high': 1,
    'female': 1,
    'age_65_74': 1,
    'hr_tachycardic': 1,
    'trans_auto': -2,
    'mech_assault': -3,
    'trans_walk': -4,
}

# Original FORD risk group bins (from FORD V8)
FORD_RISK_BINS = [-1, 1, 3, 6, 10]
FORD_RISK_LABELS = ['Low', 'Low-Mod', 'Mod-High', 'High']

# Ben Taub V8 reference event rates (test set)
V8_BT_RATES = {'Low': 1.2, 'Low-Mod': 3.1, 'Mod-High': 7.0, 'High': 26.4}

# Fracture ICD-10 prefixes
FRACTURE_PREFIXES = {'S12', 'S22', 'S32', 'S42', 'S52', 'S62', 'S72', 'S82', 'S92'}


def _banner(msg: str) -> None:
    bar = "=" * 72
    print(f"\n{bar}\n{msg}\n{bar}", flush=True)


def _save_fig(fig, stem: str) -> None:
    """Save figure as PNG (300 dpi) and PDF."""
    for fmt in ('png', 'pdf'):
        path = FIGURES_DIR / f"{stem}.{fmt}"
        fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved {stem}.png / {stem}.pdf", flush=True)


# =====================================================================
# STATISTICAL HELPERS (reused from ford_ntdb_validate.py)
# =====================================================================

def bootstrap_auc_ci(y_true, scores, n_boot=N_BOOT, seed=SEED):
    """Point AUROC + 2.5/97.5-percentile bootstrap CI."""
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    scores = np.asarray(scores)
    n = len(y_true)
    aucs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        if len(np.unique(y_true[idx])) < 2:
            continue
        aucs.append(roc_auc_score(y_true[idx], scores[idx]))
    auroc = roc_auc_score(y_true, scores)
    lo, hi = np.percentile(aucs, 2.5), np.percentile(aucs, 97.5)
    return auroc, lo, hi


def delong_bootstrap(y_true, pred1, pred2, n_boot=N_BOOT, seed=SEED):
    """Bootstrap DeLong-variant test for two correlated ROC curves."""
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    pred1 = np.asarray(pred1)
    pred2 = np.asarray(pred2)
    n = len(y_true)
    auc1 = roc_auc_score(y_true, pred1)
    auc2 = roc_auc_score(y_true, pred2)
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        if len(np.unique(y_true[idx])) < 2:
            continue
        diffs.append(
            roc_auc_score(y_true[idx], pred1[idx])
            - roc_auc_score(y_true[idx], pred2[idx])
        )
    diffs = np.array(diffs)
    se = diffs.std() if len(diffs) > 0 else 0.0
    z = (auc1 - auc2) / se if se > 0 else 0.0
    p = 2 * (1 - norm.cdf(abs(z)))
    return auc1, auc2, z, p


def hosmer_lemeshow(y_true, p_pred, n_bins=10):
    """Classic Hosmer-Lemeshow test on n_bins quantile groups."""
    df_hl = pd.DataFrame({'y': np.asarray(y_true), 'p': np.asarray(p_pred)})
    df_hl['bin'] = pd.qcut(df_hl['p'], n_bins, duplicates='drop')
    grouped = df_hl.groupby('bin', observed=True).agg(
        obs=('y', 'sum'),
        exp=('p', 'sum'),
        n=('y', 'count'),
    ).reset_index()
    grouped['obs_non'] = grouped['n'] - grouped['obs']
    grouped['exp_non'] = grouped['n'] - grouped['exp']
    chi2 = (
        ((grouped['obs'] - grouped['exp']) ** 2 / grouped['exp'].replace(0, np.nan)).sum()
        + ((grouped['obs_non'] - grouped['exp_non']) ** 2
           / grouped['exp_non'].replace(0, np.nan)).sum()
    )
    dof = max(len(grouped) - 2, 1)
    p = 1 - chi2_dist.cdf(chi2, df=dof)
    return float(chi2), float(p)


def hosmer_lemeshow_bootstrap(y_true, p_pred, n_bins=10, n_boot=N_BOOT, seed=SEED):
    """Bootstrap p-value for HL statistic.
    With huge N the frequentist HL always rejects — the bootstrap version
    (resample y from Bernoulli(p_pred)) is more interpretable."""
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    p_pred = np.asarray(p_pred)
    chi2_obs, _ = hosmer_lemeshow(y_true, p_pred, n_bins=n_bins)
    n = len(y_true)
    chi2_null = []
    for _ in range(n_boot):
        y_sim = (rng.random(n) < p_pred).astype(int)
        try:
            c, _ = hosmer_lemeshow(y_sim, p_pred, n_bins=n_bins)
            chi2_null.append(c)
        except Exception:
            continue
    chi2_null = np.array(chi2_null)
    if len(chi2_null) == 0:
        return chi2_obs, np.nan
    p_boot = float((chi2_null >= chi2_obs).mean())
    return float(chi2_obs), p_boot


def calibration_intercept_slope(y_true, p_pred):
    """Logistic-regression-based calibration-in-the-large (intercept) and slope."""
    eps = 1e-6
    p_clip = np.clip(np.asarray(p_pred, dtype=float), eps, 1 - eps)
    logit_p = np.log(p_clip / (1 - p_clip))
    X_slope = sm.add_constant(logit_p)
    try:
        model = sm.Logit(np.asarray(y_true), X_slope).fit(disp=0, maxiter=200)
        return float(model.params[0]), float(model.params[1])
    except Exception as exc:
        print(f"  [warn] calibration slope model failed: {exc}")
        return np.nan, np.nan


def operating_point_metrics(y_true, scores):
    """Youden's J optimal threshold + confusion-matrix metrics."""
    y_true = np.asarray(y_true)
    scores = np.asarray(scores)
    fpr, tpr, thresholds = roc_curve(y_true, scores)
    J = tpr - fpr
    idx = int(np.argmax(J))
    thr = float(thresholds[idx])
    y_pred = (scores >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    sens = tp / (tp + fn) if (tp + fn) > 0 else np.nan
    spec = tn / (tn + fp) if (tn + fp) > 0 else np.nan
    ppv = tp / (tp + fp) if (tp + fp) > 0 else np.nan
    npv = tn / (tn + fn) if (tn + fn) > 0 else np.nan
    acc = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else np.nan
    return {
        'youden_threshold': thr,
        'sensitivity': sens,
        'specificity': spec,
        'ppv': ppv,
        'npv': npv,
        'accuracy': acc,
    }


def decision_curve(y_true, p_pred, thresholds=None):
    """Compute DCA net benefit for a model across a grid of threshold probabilities."""
    if thresholds is None:
        thresholds = np.arange(0.01, 0.51, 0.01)
    y_true = np.asarray(y_true)
    p_pred = np.asarray(p_pred)
    n = len(y_true)
    out = []
    for t in thresholds:
        y_pred = (p_pred >= t).astype(int)
        tp = int(((y_pred == 1) & (y_true == 1)).sum())
        fp = int(((y_pred == 1) & (y_true == 0)).sum())
        net_benefit = (tp / n) - (fp / n) * (t / (1 - t))
        out.append({'threshold': float(t), 'net_benefit': float(net_benefit)})
    return pd.DataFrame(out)


# =====================================================================
# SMD helper
# =====================================================================

def smd_continuous(mean1, sd1, mean2, sd2):
    """Standardized mean difference for continuous variables."""
    pooled_sd = np.sqrt((sd1 ** 2 + sd2 ** 2) / 2)
    if pooled_sd == 0:
        return 0.0
    return abs(mean1 - mean2) / pooled_sd


def smd_binary(p1, p2):
    """Standardized mean difference for binary variables."""
    pooled = np.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / 2)
    if pooled == 0:
        return 0.0
    return abs(p1 - p2) / pooled


# =====================================================================
# STEP 1: Load and split
# =====================================================================

def load_data():
    _banner("STEP 1: Load data and split")
    t0 = time.time()

    if not INPUT_PARQUET.exists():
        raise FileNotFoundError(f"Input parquet not found: {INPUT_PARQUET}")

    df = pd.read_parquet(INPUT_PARQUET)
    print(f"  Loaded {len(df):,} rows x {df.shape[1]} columns", flush=True)

    # Verify required columns
    required = ['split', 'outcome_nonhome', 'FORD_II_0_10', 'FORD_II_score_raw']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Required columns missing: {missing}")

    # Drop rows with missing outcome
    before = len(df)
    df = df[df['outcome_nonhome'].notna()].copy()
    df['outcome_nonhome'] = df['outcome_nonhome'].astype(int)
    dropped = before - len(df)
    if dropped:
        print(f"  Dropped {dropped:,} rows with missing outcome", flush=True)

    train = df[df['split'] == 'train'].copy()
    test = df[df['split'] == 'test'].copy()

    print(f"  Train: {len(train):,}  |  Test: {len(test):,}", flush=True)
    print(f"  Train outcome rate: {train['outcome_nonhome'].mean() * 100:.2f}%", flush=True)
    print(f"  Test  outcome rate: {test['outcome_nonhome'].mean() * 100:.2f}%", flush=True)
    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)

    return df, train, test


# =====================================================================
# STEP 2: Table 1 — Baseline characteristics (train vs test with SMDs)
# =====================================================================

def build_table1(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    _banner("STEP 2: Table 1 — Baseline characteristics (train vs test)")
    t0 = time.time()

    rows = []

    def _add_n(label, tr, te):
        rows.append({
            'Variable': label,
            'Train': f"{len(tr):,}",
            'Test': f"{len(te):,}",
            'SMD': '',
        })

    def _add_continuous(label, col_name, tr, te):
        tr_vals = pd.to_numeric(tr[col_name], errors='coerce') if col_name in tr.columns else pd.Series(dtype=float)
        te_vals = pd.to_numeric(te[col_name], errors='coerce') if col_name in te.columns else pd.Series(dtype=float)
        if tr_vals.dropna().empty and te_vals.dropna().empty:
            return
        tr_mean, tr_sd = tr_vals.mean(), tr_vals.std()
        te_mean, te_sd = te_vals.mean(), te_vals.std()
        smd = smd_continuous(tr_mean, tr_sd, te_mean, te_sd)
        rows.append({
            'Variable': f"{label}, mean (SD)",
            'Train': f"{tr_mean:.1f} ({tr_sd:.1f})",
            'Test': f"{te_mean:.1f} ({te_sd:.1f})",
            'SMD': f"{smd:.3f}",
        })
        # Also add median [IQR] for age
        if 'age' in label.lower():
            tr_med = tr_vals.median()
            tr_q25, tr_q75 = tr_vals.quantile(0.25), tr_vals.quantile(0.75)
            te_med = te_vals.median()
            te_q25, te_q75 = te_vals.quantile(0.25), te_vals.quantile(0.75)
            rows.append({
                'Variable': f"{label}, median [IQR]",
                'Train': f"{tr_med:.0f} [{tr_q25:.0f}-{tr_q75:.0f}]",
                'Test': f"{te_med:.0f} [{te_q25:.0f}-{te_q75:.0f}]",
                'SMD': '',
            })

    def _add_binary(label, col_name, tr, te):
        if col_name not in tr.columns or col_name not in te.columns:
            return
        tr_n = int(tr[col_name].sum())
        te_n = int(te[col_name].sum())
        tr_pct = tr[col_name].mean()
        te_pct = te[col_name].mean()
        smd_val = smd_binary(tr_pct, te_pct)
        rows.append({
            'Variable': label,
            'Train': f"{tr_n:,} ({tr_pct * 100:.1f}%)",
            'Test': f"{te_n:,} ({te_pct * 100:.1f}%)",
            'SMD': f"{smd_val:.3f}",
        })

    # --- N ---
    _add_n('N', train, test)

    # --- Age ---
    _add_continuous('Age', 'AGE_NUMBER', train, test)

    # --- Sex ---
    _add_binary('Female, n (%)', 'female', train, test)

    # --- Race ---
    race_vars = [
        ('Race: Black, n (%)', 'race_black'),
        ('Race: Asian, n (%)', 'race_asian'),
        ('Race: Native, n (%)', 'race_native'),
        ('Race: Other, n (%)', 'race_other'),
    ]
    for label, col in race_vars:
        _add_binary(label, col, train, test)

    # --- Ethnicity ---
    _add_binary('Ethnicity: Hispanic, n (%)', 'ethnicity_hispanic', train, test)

    # --- Vitals ---
    vitals = [
        ('GCS', 'GCS2'),
        ('ISS', 'ISS'),
        ('SBP', 'SBP2'),
        ('HR', 'P2'),
        ('RR', 'RR2'),
    ]
    for label, col in vitals:
        _add_continuous(label, col, train, test)

    # --- Insurance ---
    ins_vars = [
        ('Insurance: Medicare, n (%)', 'ins_medicare'),
        ('Insurance: Medicaid, n (%)', 'ins_medicaid'),
        ('Insurance: Private, n (%)', 'ins_private'),
        ('Insurance: Charity, n (%)', 'ins_charity'),
        ('Insurance: Other, n (%)', 'ins_other'),
    ]
    for label, col in ins_vars:
        _add_binary(label, col, train, test)

    # --- Mechanism ---
    mech_vars = [
        ('Mechanism: MVC, n (%)', 'mech_mvc'),
        ('Mechanism: Assault, n (%)', 'mech_assault'),
        ('Mechanism: Other, n (%)', 'mech_other'),
    ]
    for label, col in mech_vars:
        _add_binary(label, col, train, test)

    # --- Transport ---
    trans_vars = [
        ('Transport: Private vehicle, n (%)', 'trans_auto'),
        ('Transport: Air, n (%)', 'trans_air'),
        ('Transport: Other, n (%)', 'trans_other_mode'),
    ]
    for label, col in trans_vars:
        _add_binary(label, col, train, test)

    # --- Fracture sites ---
    frac_vars = [
        ('Fracture: Cervical (S12), n (%)', 'frac_cervical'),
        ('Fracture: Thoracic (S22), n (%)', 'frac_thoracic'),
        ('Fracture: Lumbar (S32), n (%)', 'frac_lumbar'),
        ('Fracture: Hip/Femur (S72), n (%)', 'frac_hip_femur'),
        ('Fracture: Leg (S82), n (%)', 'frac_leg'),
        ('Fracture: Foot (S92), n (%)', 'frac_foot'),
    ]
    for label, col in frac_vars:
        _add_binary(label, col, train, test)

    # --- Outcome ---
    _add_binary('Non-home discharge, n (%)', 'outcome_nonhome', train, test)

    table1 = pd.DataFrame(rows)
    outpath = TABLES_DIR / "baseline.csv"
    table1.to_csv(outpath, index=False)
    print(f"  Saved {outpath.name} ({len(table1)} rows)", flush=True)
    print(table1.to_string(index=False), flush=True)
    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)

    return table1


# =====================================================================
# STEP 3: Validation metrics (Table 4)
# =====================================================================

def build_table4(test: pd.DataFrame) -> pd.DataFrame:
    _banner("STEP 3: Table 4 — Validation metrics (FORD-II v3 vs 3 comparators)")
    t0 = time.time()

    y = test['outcome_nonhome'].astype(int).values

    # Define scores to evaluate — primary comparator set trimmed to V9-aligned 3:
    # FORD, GTOS-II, TRIAGES.  ISS and GCS are deferred to supplementary extras
    # (handled in script 05).
    score_defs = [
        ('FORD-II', 'FORD_II_0_10', False),
        ('FORD', 'FORD_0_10', False),
        ('GTOS-II', 'GTOS_II', False),
        ('TRIAGES', 'triages_total', False),
    ]

    # FORD-II is the reference for DeLong comparisons
    ford2_scores = test['FORD_II_0_10'].astype(float).values

    metric_rows = []
    for name, col, negate in score_defs:
        if col not in test.columns:
            print(f"  SKIPPING {name}: column '{col}' not found", flush=True)
            continue

        s = pd.to_numeric(test[col], errors='coerce').values
        if negate:
            s = -s

        mask = ~np.isnan(s)
        y_i = y[mask]
        s_i = s[mask]
        n_used = int(mask.sum())
        print(f"  Computing metrics for {name} (n={n_used:,}) ...", flush=True)

        # AUROC + bootstrap CI
        try:
            auroc, lo, hi = bootstrap_auc_ci(y_i, s_i, n_boot=N_BOOT, seed=SEED)
        except Exception as exc:
            print(f"    [warn] AUROC failed: {exc}", flush=True)
            auroc, lo, hi = np.nan, np.nan, np.nan

        # Logistic score -> predicted probability for Brier/HL/calibration
        brier = scaled_brier = hl_chi2 = hl_p = hl_p_boot = citl = cslope = np.nan
        try:
            lr = LogisticRegression(max_iter=1000)
            lr.fit(s_i.reshape(-1, 1), y_i)
            p_pred = lr.predict_proba(s_i.reshape(-1, 1))[:, 1]
            brier = brier_score_loss(y_i, p_pred)
            brier_null = brier_score_loss(y_i, np.full_like(y_i, y_i.mean(), dtype=float))
            scaled_brier = 1 - brier / brier_null if brier_null > 0 else np.nan
            hl_chi2, hl_p = hosmer_lemeshow(y_i, p_pred)
            _, hl_p_boot = hosmer_lemeshow_bootstrap(
                y_i, p_pred, n_bins=10, n_boot=N_BOOT, seed=SEED
            )
            citl, cslope = calibration_intercept_slope(y_i, p_pred)
        except Exception as exc:
            print(f"    [warn] calibration metrics failed: {exc}", flush=True)

        # Operating point (Youden's J)
        try:
            op = operating_point_metrics(y_i, s_i)
        except Exception as exc:
            print(f"    [warn] operating point failed: {exc}", flush=True)
            op = {k: np.nan for k in
                  ['youden_threshold', 'sensitivity', 'specificity', 'ppv', 'npv', 'accuracy']}

        # DeLong: FORD-II vs this comparator
        delong_p = ''
        if name != 'FORD-II':
            try:
                ford2_masked = ford2_scores[mask]
                _, _, _, dp = delong_bootstrap(
                    y_i, ford2_masked, s_i, n_boot=N_BOOT, seed=SEED
                )
                delong_p = f"{dp:.4g}"
            except Exception as exc:
                print(f"    [warn] DeLong failed for FORD-II vs {name}: {exc}", flush=True)
                delong_p = 'NA'

        metric_rows.append({
            'score': name,
            'n': n_used,
            'auroc': round(auroc, 4) if not np.isnan(auroc) else np.nan,
            'auroc_ci_lo': round(lo, 4) if not np.isnan(lo) else np.nan,
            'auroc_ci_hi': round(hi, 4) if not np.isnan(hi) else np.nan,
            'brier': round(brier, 4) if not np.isnan(brier) else np.nan,
            'scaled_brier': round(scaled_brier, 4) if not np.isnan(scaled_brier) else np.nan,
            'hl_chi2': round(hl_chi2, 2) if not np.isnan(hl_chi2) else np.nan,
            'hl_p_frequentist': hl_p,
            'hl_p_bootstrap': hl_p_boot,
            'cal_intercept': round(citl, 4) if not np.isnan(citl) else np.nan,
            'cal_slope': round(cslope, 4) if not np.isnan(cslope) else np.nan,
            'youden_threshold': round(op['youden_threshold'], 3),
            'sensitivity': round(op['sensitivity'], 4),
            'specificity': round(op['specificity'], 4),
            'ppv': round(op['ppv'], 4),
            'npv': round(op['npv'], 4),
            'accuracy': round(op['accuracy'], 4),
            'delong_p_vs_ford2': delong_p,
        })

    table4 = pd.DataFrame(metric_rows)
    table4.attrs['note'] = (
        "HL p-values are frequentist (always ~0 at very large N) and bootstrap "
        "(re-simulating y from the predicted probabilities; more interpretable at large N). "
        "DeLong p-values are FORD-II vs each comparator."
    )

    outpath = TABLES_DIR / "validation_metrics.csv"
    table4.to_csv(outpath, index=False)
    print(f"\n  Saved {outpath.name}", flush=True)
    print(table4.to_string(index=False), flush=True)
    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)

    return table4


# =====================================================================
# STEP 4: Risk groups (Table 5)
# =====================================================================

def build_table5(test: pd.DataFrame) -> pd.DataFrame:
    _banner("STEP 4: Table 5 — Risk stratification (FORD-II v3 and original FORD)")
    t0 = time.time()

    y = test['outcome_nonhome'].astype(int)

    # --- FORD-II quartile-based risk groups ---
    ford2_scores = test['FORD_II_0_10']
    try:
        ford2_bins = pd.qcut(ford2_scores, q=4, duplicates='drop')
        n_groups = ford2_bins.nunique()
    except ValueError:
        n_groups = 0

    # If quartile-based cut produces fewer than 4 groups (due to ties at integer
    # boundaries), fall back to manually chosen bins from distribution
    if n_groups < 4:
        print(f"  Quartile cut produced {n_groups} groups; using percentile-based boundaries", flush=True)
        boundaries = np.unique(np.percentile(ford2_scores.dropna(), [0, 25, 50, 75, 100]))
        if len(boundaries) < 3:
            # Extreme fallback: equal-width bins
            boundaries = np.linspace(ford2_scores.min() - 0.5, ford2_scores.max() + 0.5, 5)
        ford2_cuts = pd.cut(ford2_scores, bins=boundaries, include_lowest=True)
    else:
        ford2_cuts = ford2_bins

    # Build risk group table for FORD-II
    ford2_rg = pd.DataFrame({
        'score': ford2_scores,
        'outcome': y,
        'risk_group': ford2_cuts,
    })
    ford2_grouped = ford2_rg.groupby('risk_group', observed=True).agg(
        score_min=('score', 'min'),
        score_max=('score', 'max'),
        n=('outcome', 'size'),
        events=('outcome', 'sum'),
    ).reset_index()
    ford2_grouped['event_rate_pct'] = 100 * ford2_grouped['events'] / ford2_grouped['n']

    # Wilson CI for event rates
    cis = [
        proportion_confint(int(r.events), int(r.n), method='wilson')
        for r in ford2_grouped.itertuples()
    ]
    ford2_grouped['ci_lo_pct'] = [100 * x[0] for x in cis]
    ford2_grouped['ci_hi_pct'] = [100 * x[1] for x in cis]

    # Label the groups
    n_grps = len(ford2_grouped)
    grp_labels = ['Low', 'Low-Mod', 'Mod-High', 'High'][:n_grps]
    if n_grps > 4:
        grp_labels = [f"Group {i+1}" for i in range(n_grps)]
    ford2_grouped['label'] = grp_labels
    ford2_grouped['score_range'] = ford2_grouped.apply(
        lambda r: f"{int(r.score_min)}-{int(r.score_max)}", axis=1
    )

    # --- Original FORD risk groups (fixed bins) ---
    ford_scores = test['FORD_0_10'] if 'FORD_0_10' in test.columns else None
    ford_grouped = None
    if ford_scores is not None:
        ford_rg = pd.DataFrame({'score': ford_scores, 'outcome': y})
        ford_rg['risk_group'] = pd.cut(
            ford_rg['score'], bins=FORD_RISK_BINS, labels=FORD_RISK_LABELS,
        )
        ford_grouped = ford_rg.groupby('risk_group', observed=True).agg(
            n_ford=('outcome', 'size'),
            events_ford=('outcome', 'sum'),
        ).reset_index()
        ford_grouped['ford_event_rate_pct'] = 100 * ford_grouped['events_ford'] / ford_grouped['n_ford']

        ford_cis = [
            proportion_confint(int(r.events_ford), int(r.n_ford), method='wilson')
            for r in ford_grouped.itertuples()
        ]
        ford_grouped['ford_ci_lo_pct'] = [100 * x[0] for x in ford_cis]
        ford_grouped['ford_ci_hi_pct'] = [100 * x[1] for x in ford_cis]

    # --- Merge into single table ---
    out_rows = []
    for i, row in ford2_grouped.iterrows():
        entry = {
            'Risk_group': row['label'],
            'FORD_II_score_range': row['score_range'],
            'FORD_II_n': int(row['n']),
            'FORD_II_events': int(row['events']),
            'FORD_II_event_rate_pct': round(row['event_rate_pct'], 2),
            'FORD_II_ci_lo_pct': round(row['ci_lo_pct'], 2),
            'FORD_II_ci_hi_pct': round(row['ci_hi_pct'], 2),
        }
        # Add FORD columns if available and label matches
        if ford_grouped is not None and row['label'] in FORD_RISK_LABELS:
            frow = ford_grouped[ford_grouped['risk_group'] == row['label']]
            if not frow.empty:
                frow = frow.iloc[0]
                entry['FORD_score_range'] = dict(zip(FORD_RISK_LABELS,
                    ['0-1', '2-3', '4-6', '7-10'])).get(row['label'], '')
                entry['FORD_n'] = int(frow['n_ford'])
                entry['FORD_events'] = int(frow['events_ford'])
                entry['FORD_event_rate_pct'] = round(frow['ford_event_rate_pct'], 2)
                entry['FORD_ci_lo_pct'] = round(frow['ford_ci_lo_pct'], 2)
                entry['FORD_ci_hi_pct'] = round(frow['ford_ci_hi_pct'], 2)
                entry['V8_BT_event_rate_pct'] = V8_BT_RATES.get(row['label'], np.nan)
        out_rows.append(entry)

    table5 = pd.DataFrame(out_rows)
    outpath = TABLES_DIR / "risk_groups.csv"
    table5.to_csv(outpath, index=False)
    print(f"  Saved {outpath.name}", flush=True)
    print(table5.to_string(index=False), flush=True)
    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)

    return table5


# =====================================================================
# STEP 5: Figures
# =====================================================================

def plot_consort(consort_csv: Path) -> None:
    """Figure 1: CONSORT flow diagram from consort_flow_ford2_v3.csv."""
    _banner("Figure 1: CONSORT flow diagram")

    if not consort_csv.exists():
        print(f"  SKIPPING: {consort_csv} not found", flush=True)
        return

    consort = pd.read_csv(consort_csv)
    print(f"  Loaded consort CSV with {len(consort)} rows", flush=True)

    # Build step list from CSV
    steps = []
    for _, row in consort.iterrows():
        label = str(row.get('step', row.get('label', '')))
        n = row.get('n', row.get('N', ''))
        excluded = row.get('excluded', row.get('dropped', ''))
        steps.append((label, n, excluded))

    n_steps = len(steps)
    fig_height = max(6, 1.2 * n_steps + 2)
    fig, ax = plt.subplots(figsize=(10, fig_height))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, n_steps + 1)
    ax.axis('off')

    box_w = 5.0
    box_h = 0.7
    x_center = 5.0
    x_left = x_center - box_w / 2
    excl_x = x_center + box_w / 2 + 0.8

    for i, (label, n, excluded) in enumerate(steps):
        y = n_steps - i
        # Main box
        rect = plt.Rectangle((x_left, y - box_h / 2), box_w, box_h,
                              facecolor='#E8F0FE', edgecolor='#2C5F8A',
                              linewidth=1.5, zorder=2)
        ax.add_patch(rect)
        n_str = f"N = {int(n):,}" if pd.notna(n) and str(n).strip() != '' else ''
        ax.text(x_center, y, f"{label}\n{n_str}",
                ha='center', va='center', fontsize=8, fontweight='bold', zorder=3)

        # Arrow to next
        if i < n_steps - 1:
            ax.annotate('', xy=(x_center, (n_steps - i - 1) + box_h / 2),
                        xytext=(x_center, y - box_h / 2),
                        arrowprops=dict(arrowstyle='->', color='#2C5F8A', lw=1.5))

        # Exclusion annotation
        if pd.notna(excluded) and str(excluded).strip() not in ('', '0', 'nan'):
            excl_str = f"Excluded: {int(float(excluded)):,}" if str(excluded).replace('.', '').isdigit() else str(excluded)
            ax.text(excl_x, y, excl_str, ha='left', va='center', fontsize=7,
                    color='#CC0000', fontstyle='italic')

    ax.set_title('FORD-II v3: CONSORT Flow Diagram', fontsize=13, fontweight='bold', pad=10)
    _save_fig(fig, 'figure1_consort')


def plot_roc_curves(test: pd.DataFrame) -> None:
    """Figure 2: ROC curves for 4 scores overlaid on test set
    (FORD-II v3, FORD, GTOS-II, TRIAGES)."""
    _banner("Figure 2: ROC curves")

    y = test['outcome_nonhome'].astype(int).values

    # Primary figure mirrors Table 4 comparator set (trimmed to 4 curves).
    # ISS and GCS are deferred to supplementary extras (script 05).
    score_defs = [
        ('FORD-II', 'FORD_II_0_10', False, 'steelblue', 2.5),
        ('FORD', 'FORD_0_10', False, 'coral', 1.5),
        ('GTOS-II', 'GTOS_II', False, 'green', 1.5),
        ('TRIAGES', 'triages_total', False, 'purple', 1.5),
    ]

    fig, ax = plt.subplots(figsize=(7, 7))

    for name, col, negate, color, lw in score_defs:
        if col not in test.columns:
            continue
        s = pd.to_numeric(test[col], errors='coerce').values
        if negate:
            s = -s
        mask = ~np.isnan(s)
        if mask.sum() < 10:
            continue
        fpr, tpr, _ = roc_curve(y[mask], s[mask])
        auc = roc_auc_score(y[mask], s[mask])
        ax.plot(fpr, tpr, label=f"{name} (AUROC = {auc:.3f})",
                color=color, linewidth=lw)

    ax.plot([0, 1], [0, 1], 'k--', alpha=0.5, linewidth=1)
    ax.set_xlabel('1 - Specificity (False Positive Rate)', fontsize=11)
    ax.set_ylabel('Sensitivity (True Positive Rate)', fontsize=11)
    ax.set_title('ROC Curves: FORD-II v3 vs Comparators (NTDB Test Set)', fontsize=12)
    ax.legend(loc='lower right', framealpha=0.95, fontsize=9)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    _save_fig(fig, 'figure2_roc_curves')


def plot_calibration(test: pd.DataFrame) -> None:
    """Figure 3: Calibration plot for FORD-II (decile bins)."""
    _banner("Figure 3: Calibration plot")

    y = test['outcome_nonhome'].astype(int).values
    s = test['FORD_II_0_10'].astype(float).values

    # Fit logistic regression for probability mapping
    lr = LogisticRegression(max_iter=1000)
    lr.fit(s.reshape(-1, 1), y)
    p_ford2 = lr.predict_proba(s.reshape(-1, 1))[:, 1]

    df_cal = pd.DataFrame({'y': y, 'p': p_ford2})
    df_cal['bin'] = pd.qcut(df_cal['p'], 10, duplicates='drop')
    grouped = df_cal.groupby('bin', observed=True).agg(
        obs=('y', 'mean'),
        pred=('p', 'mean'),
        n=('y', 'count'),
    ).reset_index()

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Perfect calibration')
    ax.plot(grouped['pred'], grouped['obs'], 'o-', color='steelblue',
            linewidth=2, markersize=9, label='FORD-II (deciles)')
    ax.set_xlabel('Mean predicted probability', fontsize=11)
    ax.set_ylabel('Observed event rate', fontsize=11)
    ax.set_title('Calibration Plot: FORD-II on NTDB Test Set (decile bins)', fontsize=12)
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    lim = max(grouped['pred'].max(), grouped['obs'].max(), 0.01) * 1.1
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    _save_fig(fig, 'figure3_calibration')


def plot_risk_groups(table5: pd.DataFrame) -> None:
    """Figure 4: Risk group bar chart (FORD-II vs original FORD event rates)."""
    _banner("Figure 4: Risk group bar chart")

    labels = table5['Risk_group'].tolist()
    x = np.arange(len(labels))
    width = 0.35

    ford2_rates = table5['FORD_II_event_rate_pct'].values

    has_ford = 'FORD_event_rate_pct' in table5.columns and table5['FORD_event_rate_pct'].notna().any()

    fig, ax = plt.subplots(figsize=(9, 6))

    if has_ford:
        ford_rates = table5['FORD_event_rate_pct'].fillna(0).values
        ax.bar(x - width / 2, ford2_rates, width, label='FORD-II v3 (NTDB)',
               color='#4C72B0')
        ax.bar(x + width / 2, ford_rates, width, label='FORD (NTDB)',
               color='#DD8452')
        for i in range(len(labels)):
            ax.text(i - width / 2, ford2_rates[i] + 0.3, f"{ford2_rates[i]:.1f}%",
                    ha='center', fontsize=8)
            if ford_rates[i] > 0:
                ax.text(i + width / 2, ford_rates[i] + 0.3, f"{ford_rates[i]:.1f}%",
                        ha='center', fontsize=8)
    else:
        ax.bar(x, ford2_rates, width * 1.5, label='FORD-II v3 (NTDB)',
               color='#4C72B0')
        for i in range(len(labels)):
            ax.text(i, ford2_rates[i] + 0.3, f"{ford2_rates[i]:.1f}%",
                    ha='center', fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Non-home discharge rate (%)', fontsize=11)
    ax.set_title('FORD-II v3 Risk Stratification: NTDB Test Set', fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    _save_fig(fig, 'figure4_risk_groups')


def plot_dca(test: pd.DataFrame) -> None:
    """Figure 5: Decision curve analysis (net benefit)."""
    _banner("Figure 5: Decision curve analysis")

    y = test['outcome_nonhome'].astype(int).values
    s = test['FORD_II_0_10'].astype(float).values

    # Fit logistic regression for probability mapping
    lr = LogisticRegression(max_iter=1000)
    lr.fit(s.reshape(-1, 1), y)
    p_ford2 = lr.predict_proba(s.reshape(-1, 1))[:, 1]

    prev = float(y.mean())
    thresholds = np.arange(0.01, 0.51, 0.01)
    dca_ford2 = decision_curve(y, p_ford2, thresholds=thresholds)

    nb_all = prev - (1 - prev) * (thresholds / (1 - thresholds))
    nb_none = np.zeros_like(thresholds)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(dca_ford2['threshold'], dca_ford2['net_benefit'],
            label='FORD-II', color='steelblue', linewidth=2)
    ax.plot(thresholds, nb_all, label='Treat all', color='gray',
            linewidth=1.5, linestyle='--')
    ax.plot(thresholds, nb_none, label='Treat none', color='black',
            linewidth=1.5, linestyle=':')
    ax.set_xlabel('Threshold probability', fontsize=11)
    ax.set_ylabel('Net benefit', fontsize=11)
    ax.set_title('Decision Curve Analysis: FORD-II on NTDB Test Set', fontsize=12)
    ymin = min(nb_all.min(), dca_ford2['net_benefit'].min()) - 0.02
    ymax = max(dca_ford2['net_benefit'].max(), prev) + 0.02
    ax.set_ylim(ymin, ymax)
    ax.set_xlim(0, 0.5)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    _save_fig(fig, 'figure5_dca')


# =====================================================================
# STEP 6: Ben Taub reverse validation
# =====================================================================

def bentaub_reverse_validation() -> pd.DataFrame | None:
    _banner("STEP 6: Ben Taub reverse validation")
    t0 = time.time()

    if not BEN_TAUB_CSV.exists():
        print(f"  SKIPPING: {BEN_TAUB_CSV} not found", flush=True)
        return None

    if not WEIGHTS_CSV.exists():
        print(f"  SKIPPING: {WEIGHTS_CSV} not found (run script 03 first)", flush=True)
        return None

    # Load FORD-II weights from table3
    weights_df = pd.read_csv(WEIGHTS_CSV)
    ford2_weights = dict(zip(weights_df['Variable'], weights_df['Integer_points']))
    print(f"  FORD-II weights loaded: {len(ford2_weights)} predictors", flush=True)
    for var, pts in sorted(ford2_weights.items(), key=lambda x: abs(x[1]), reverse=True):
        print(f"    {var:30s} -> {pts:+d}", flush=True)

    # Load Ben Taub data
    print(f"\n  Loading Ben Taub data: {BEN_TAUB_CSV}", flush=True)
    bt = pd.read_csv(BEN_TAUB_CSV, low_memory=False)
    n_raw = len(bt)
    print(f"  Raw rows: {n_raw:,}", flush=True)

    # --- Apply FORD cohort filters: adults, fracture, valid disposition ---

    # Adults (age >= 18)
    bt['AGE_NUMBER'] = pd.to_numeric(bt['AGE_NUMBER'], errors='coerce')
    bt = bt[bt['AGE_NUMBER'] >= 18].copy()
    print(f"  Adults (>=18): {len(bt):,}", flush=True)

    # Primary fracture (S12-S92)
    bt = bt.dropna(subset=['ICD10'])
    icd = bt['ICD10'].astype(str).str.strip().str.upper().str.replace('.', '', regex=False)
    prefix = icd.str[:3]
    frac_mask = prefix.isin(FRACTURE_PREFIXES)
    bt = bt[frac_mask].copy()
    bt['_icd_prefix'] = prefix[frac_mask]
    print(f"  Fracture patients (primary ICD S12-S92): {len(bt):,}", flush=True)

    # Valid disposition -> outcome
    home_codes = {'HOME', 'HH'}
    nonhome_codes = {'REHAB', 'SNF', 'LTCH', 'NH', 'ICF', 'RESIDENTIAL INSTITUTION'}
    exclude_codes = {'D', 'AMA', 'JAIL', 'POLICE', 'HOSP', 'HOSPICE', 'PC', 'OTHER', 'NOT'}

    dc_col = 'DC_DISPOSITION_CODE' if 'DC_DISPOSITION_CODE' in bt.columns else 'DC_DISPOSITION'
    dc = bt[dc_col].astype(str).str.strip().str.upper()
    bt['outcome_nonhome'] = np.where(
        dc.isin(nonhome_codes), 1,
        np.where(dc.isin(home_codes), 0, np.nan)
    )
    bt = bt[bt['outcome_nonhome'].notna()].copy()
    bt['outcome_nonhome'] = bt['outcome_nonhome'].astype(int)
    print(f"  After valid disposition filter: {len(bt):,}", flush=True)
    print(f"  Outcome rate: {bt['outcome_nonhome'].mean() * 100:.1f}%", flush=True)

    # --- Engineer FORD-II predictor variables on Ben Taub data ---
    # Use the same thresholds as NTDB (from 02_ford2_features.py)

    age = bt['AGE_NUMBER']
    bt['age_45_64'] = ((age >= 45) & (age <= 64)).fillna(False).astype(int)
    bt['age_65_74'] = ((age >= 65) & (age <= 74)).fillna(False).astype(int)
    bt['age_75plus'] = (age >= 75).fillna(False).astype(int)

    sex = bt['SEX'].astype(str).str.strip().str.upper()
    bt['female'] = (sex == 'F').astype(int)

    # Race — Ben Taub may use different coding than NTDB
    if 'RACE' in bt.columns:
        race = bt['RACE'].astype(str).str.strip().str.upper()
        race_valid = (race != '') & (race != 'NAN') & bt['RACE'].notna()
        bt['race_black'] = (race.str.contains('BLACK', na=False) & race_valid).astype(int)
        bt['race_asian'] = (race.str.contains('ASIAN', na=False) & race_valid).astype(int)
        bt['race_native'] = ((race.str.contains('NATIVE', na=False) | race.str.contains('INDIAN', na=False)) & race_valid).astype(int)
        is_white = race.str.contains('WHITE', na=False)
        bt['race_other'] = (race_valid & ~is_white & ~bt['race_black'].astype(bool) & ~bt['race_asian'].astype(bool) & ~bt['race_native'].astype(bool)).astype(int)
    else:
        for col in ['race_black', 'race_asian', 'race_native', 'race_other']:
            bt[col] = 0

    # Ethnicity
    if 'ETHNICITY' in bt.columns:
        eth = bt['ETHNICITY'].astype(str).str.strip().str.upper()
        bt['ethnicity_hispanic'] = eth.str.contains('HISPANIC', na=False).astype(int)
    else:
        bt['ethnicity_hispanic'] = 0

    # Vitals
    sbp = pd.to_numeric(bt['SBP2'], errors='coerce') if 'SBP2' in bt.columns else pd.Series(np.nan, index=bt.index)
    bt['sbp_hypotensive'] = (sbp < 90).fillna(False).astype(int)
    bt['sbp_hypertensive'] = (sbp >= 140).fillna(False).astype(int)

    hr = pd.to_numeric(bt['P2'], errors='coerce') if 'P2' in bt.columns else pd.Series(np.nan, index=bt.index)
    bt['hr_bradycardic'] = (hr < 60).fillna(False).astype(int)
    bt['hr_tachycardic'] = (hr >= 100).fillna(False).astype(int)

    rr = pd.to_numeric(bt['RR2'], errors='coerce') if 'RR2' in bt.columns else pd.Series(np.nan, index=bt.index)
    bt['rr_low'] = (rr < 12).fillna(False).astype(int)
    bt['rr_high'] = (rr > 20).fillna(False).astype(int)

    gcs = pd.to_numeric(bt['GCS2'], errors='coerce') if 'GCS2' in bt.columns else pd.Series(np.nan, index=bt.index)
    bt['gcs_moderate'] = ((gcs >= 9) & (gcs <= 12)).fillna(False).astype(int)
    bt['gcs_severe'] = (gcs <= 8).fillna(False).astype(int)

    # O2 saturation
    if 'OX2' in bt.columns:
        ox = pd.to_numeric(bt['OX2'], errors='coerce')
        ox = ox.where((ox >= 0) & (ox <= 100))
        bt['hypoxic'] = (ox <= 92).fillna(False).astype(int)
    else:
        bt['hypoxic'] = 0

    # Temperature
    if 'TEMPS2' in bt.columns:
        temp = pd.to_numeric(bt['TEMPS2'], errors='coerce')
        temp = temp.where((temp >= 25) & (temp <= 45))
        bt['temp_hypothermic'] = (temp < 35).fillna(False).astype(int)
        bt['temp_hyperthermic'] = (temp > 38).fillna(False).astype(int)
    else:
        bt['temp_hypothermic'] = 0
        bt['temp_hyperthermic'] = 0

    # BMI
    if 'BMI' in bt.columns:
        bmi = pd.to_numeric(bt['BMI'], errors='coerce')
    elif 'HEIGHTS2_CM' in bt.columns and 'WEIGHTS2_KG' in bt.columns:
        h_cm = pd.to_numeric(bt['HEIGHTS2_CM'], errors='coerce')
        w_kg = pd.to_numeric(bt['WEIGHTS2_KG'], errors='coerce')
        with np.errstate(divide='ignore', invalid='ignore'):
            bmi = w_kg / ((h_cm / 100.0) ** 2)
    else:
        bmi = pd.Series(np.nan, index=bt.index)
    bmi = bmi.where((bmi >= 10) & (bmi <= 80))
    bt['bmi_underweight'] = (bmi < 18.5).fillna(False).astype(int)
    bt['bmi_overweight'] = ((bmi >= 25) & (bmi < 30)).fillna(False).astype(int)
    bt['bmi_obese_12'] = ((bmi >= 30) & (bmi < 40)).fillna(False).astype(int)
    bt['bmi_obese_3'] = (bmi >= 40).fillna(False).astype(int)

    # ISS bands
    iss = pd.to_numeric(bt['ISS'], errors='coerce') if 'ISS' in bt.columns else pd.Series(np.nan, index=bt.index)
    bt['iss_9_15'] = ((iss >= 9) & (iss <= 15)).fillna(False).astype(int)
    bt['iss_16_24'] = ((iss >= 16) & (iss <= 24)).fillna(False).astype(int)
    bt['iss_25plus'] = (iss >= 25).fillna(False).astype(int)

    # Fracture site (primary ICD only for Ben Taub)
    pfx = bt['_icd_prefix']
    bt['frac_cervical'] = (pfx == 'S12').astype(int)
    bt['frac_thoracic'] = (pfx == 'S22').astype(int)
    bt['frac_lumbar'] = (pfx == 'S32').astype(int)
    bt['frac_humerus'] = (pfx == 'S42').astype(int)
    bt['frac_forearm'] = (pfx == 'S52').astype(int)
    bt['frac_hand'] = (pfx == 'S62').astype(int)
    bt['frac_hip_femur'] = (pfx == 'S72').astype(int)
    bt['frac_leg'] = (pfx == 'S82').astype(int)
    bt['frac_foot'] = (pfx == 'S92').astype(int)

    # Also create original FORD predictor aliases
    bt['hip_femur'] = bt['frac_hip_femur']
    bt['axial_fracture'] = pfx.isin(['S12', 'S22', 'S32']).astype(int)

    # Mechanism
    if 'MECHANISM' in bt.columns:
        mech = bt['MECHANISM'].astype(str).str.strip().str.upper()
        bt['mech_mvc'] = mech.str.contains('MVC|MOTOR VEHICLE|MVA', na=False, regex=True).astype(int)
        bt['mech_assault'] = mech.str.contains('ASSAULT', na=False).astype(int)
        bt['mech_other'] = (~mech.str.contains('FALL|MVC|MOTOR VEHICLE|MVA|ASSAULT', na=False, regex=True) & mech.notna()).astype(int)
    elif 'CAUSE_E_CODES10' in bt.columns:
        ecode = bt['CAUSE_E_CODES10'].astype(str).str.strip().str.upper()
        bt['mech_mvc'] = ecode.str.startswith('V').astype(int)
        bt['mech_assault'] = ecode.str.startswith('X').astype(int)
        bt['mech_other'] = (~ecode.str.startswith('W') & ~ecode.str.startswith('V') & ~ecode.str.startswith('X') & ecode.notna()).astype(int)
    else:
        bt['mech_mvc'] = 0
        bt['mech_assault'] = 0
        bt['mech_other'] = 0

    # Transport
    if 'TRANS' in bt.columns:
        trans = bt['TRANS'].astype(str).str.strip().str.upper()
        bt['trans_auto'] = trans.isin(['AUTO', 'BUS']).astype(int)
        bt['trans_air'] = trans.isin(['AIR-H', 'AIR-FW']).astype(int)
        bt['trans_walk'] = (trans == 'WALK').astype(int)
        bt['trans_other_mode'] = (~trans.isin(['AMB', 'AUTO', 'BUS', 'AIR-H', 'AIR-FW', 'WALK']) & trans.notna()).astype(int)
    else:
        bt['trans_auto'] = 0
        bt['trans_air'] = 0
        bt['trans_walk'] = 0
        bt['trans_other_mode'] = 0

    # Insurance
    if 'PAYMENT_SOURCE' in bt.columns:
        pay = bt['PAYMENT_SOURCE'].astype(str).str.strip().str.upper()
        pay_valid = (pay != '') & (pay != 'NAN') & bt['PAYMENT_SOURCE'].notna()
        bt['ins_medicare'] = pay.str.contains('MCARE', na=False).astype(int)
        bt['ins_medicaid'] = pay.str.contains('MCAID', na=False).astype(int)
        bt['ins_private'] = pay.str.contains('COMM', na=False).astype(int)
        bt['ins_charity'] = pay.str.contains('CHARITY', na=False).astype(int)
        bt['ins_other'] = (pay_valid & ~pay.eq('SELF') & ~pay.str.contains('MCARE', na=False) & ~pay.str.contains('MCAID', na=False) & ~pay.str.contains('COMM', na=False) & ~pay.str.contains('CHARITY', na=False)).astype(int)
    else:
        for col in ['ins_medicare', 'ins_medicaid', 'ins_private', 'ins_charity', 'ins_other']:
            bt[col] = 0

    # Hospital access
    if 'HOSPITAL_TRANSFER' in bt.columns:
        ht = bt['HOSPITAL_TRANSFER'].astype(str).str.strip().str.upper()
        bt['transfer_in'] = ht.isin(['1', 'YES', 'TRUE', 'Y']).astype(int)
    else:
        bt['transfer_in'] = 0

    if 'PREHOSPITAL_ARREST' in bt.columns:
        pa = bt['PREHOSPITAL_ARREST'].astype(str).str.strip().str.upper()
        bt['prehospital_arrest'] = pa.isin(['1', 'YES', 'TRUE', 'Y']).astype(int)
    else:
        bt['prehospital_arrest'] = 0

    # Substance
    if 'ETOH' in bt.columns:
        etoh = pd.to_numeric(bt['ETOH'], errors='coerce')
        bt['alcohol_positive'] = (etoh > 0).fillna(False).astype(int)
    else:
        bt['alcohol_positive'] = 0

    if 'TOX' in bt.columns:
        tox = bt['TOX'].astype(str).str.strip().str.upper()
        bt['tox_positive'] = tox.str.contains(
            'POSITIVE|POS|COCAINE|MARIJUANA|THC|AMPHET|BENZO|OPIAT|OPIOID|METH',
            na=False, regex=True
        ).astype(int)
    else:
        bt['tox_positive'] = 0

    # --- Apply frozen FORD-II integer weights (no refitting) ---
    ford2_score_raw = pd.Series(0, index=bt.index, dtype=int)
    missing_vars = []
    for var, pts in ford2_weights.items():
        if var in bt.columns:
            ford2_score_raw += pts * bt[var].astype(int)
        else:
            missing_vars.append(var)

    if missing_vars:
        print(f"\n  WARNING: {len(missing_vars)} FORD-II predictors unavailable in BT (set to 0):", flush=True)
        for v in missing_vars:
            print(f"    - {v}", flush=True)

    bt['FORD_II_score_raw'] = ford2_score_raw
    bt['FORD_II_0_10'] = ford2_score_raw.clip(0, 10)

    print(f"\n  FORD-II score on Ben Taub: min={bt['FORD_II_0_10'].min()}, "
          f"max={bt['FORD_II_0_10'].max()}, mean={bt['FORD_II_0_10'].mean():.2f}", flush=True)

    # --- Also compute original FORD score for comparison ---
    ford_raw = pd.Series(0, index=bt.index, dtype=int)
    for var, pts in FORD_WEIGHTS.items():
        if var in bt.columns:
            ford_raw += pts * bt[var].astype(int)
    bt['FORD_0_10'] = ford_raw.clip(0, 10)

    # --- Compute metrics ---
    y = bt['outcome_nonhome'].values
    results = []

    # FORD-II
    ford2_s = bt['FORD_II_0_10'].values
    try:
        ford2_auroc, ford2_lo, ford2_hi = bootstrap_auc_ci(y, ford2_s, n_boot=N_BOOT, seed=SEED)
        lr = LogisticRegression(max_iter=1000)
        lr.fit(ford2_s.reshape(-1, 1), y)
        p_ford2 = lr.predict_proba(ford2_s.reshape(-1, 1))[:, 1]
        ford2_brier = brier_score_loss(y, p_ford2)
        ford2_citl, ford2_cslope = calibration_intercept_slope(y, p_ford2)
    except Exception as exc:
        print(f"  [warn] FORD-II metrics failed: {exc}", flush=True)
        ford2_auroc, ford2_lo, ford2_hi = np.nan, np.nan, np.nan
        ford2_brier, ford2_citl, ford2_cslope = np.nan, np.nan, np.nan

    results.append({
        'score': 'FORD-II',
        'n': len(bt),
        'auroc': round(ford2_auroc, 4) if not np.isnan(ford2_auroc) else np.nan,
        'auroc_ci_lo': round(ford2_lo, 4) if not np.isnan(ford2_lo) else np.nan,
        'auroc_ci_hi': round(ford2_hi, 4) if not np.isnan(ford2_hi) else np.nan,
        'brier': round(ford2_brier, 4) if not np.isnan(ford2_brier) else np.nan,
        'cal_intercept': round(ford2_citl, 4) if not np.isnan(ford2_citl) else np.nan,
        'cal_slope': round(ford2_cslope, 4) if not np.isnan(ford2_cslope) else np.nan,
        'missing_predictors': ', '.join(missing_vars) if missing_vars else 'None',
    })

    # Original FORD
    ford_s = bt['FORD_0_10'].values
    try:
        ford_auroc, ford_lo, ford_hi = bootstrap_auc_ci(y, ford_s, n_boot=N_BOOT, seed=SEED)
        lr2 = LogisticRegression(max_iter=1000)
        lr2.fit(ford_s.reshape(-1, 1), y)
        p_ford = lr2.predict_proba(ford_s.reshape(-1, 1))[:, 1]
        ford_brier = brier_score_loss(y, p_ford)
        ford_citl, ford_cslope = calibration_intercept_slope(y, p_ford)
    except Exception as exc:
        print(f"  [warn] FORD metrics failed: {exc}", flush=True)
        ford_auroc, ford_lo, ford_hi = np.nan, np.nan, np.nan
        ford_brier, ford_citl, ford_cslope = np.nan, np.nan, np.nan

    results.append({
        'score': 'FORD (original)',
        'n': len(bt),
        'auroc': round(ford_auroc, 4) if not np.isnan(ford_auroc) else np.nan,
        'auroc_ci_lo': round(ford_lo, 4) if not np.isnan(ford_lo) else np.nan,
        'auroc_ci_hi': round(ford_hi, 4) if not np.isnan(ford_hi) else np.nan,
        'brier': round(ford_brier, 4) if not np.isnan(ford_brier) else np.nan,
        'cal_intercept': round(ford_citl, 4) if not np.isnan(ford_citl) else np.nan,
        'cal_slope': round(ford_cslope, 4) if not np.isnan(ford_cslope) else np.nan,
        'missing_predictors': 'None',
    })

    # DeLong: FORD-II vs FORD on BT
    try:
        _, _, _, delong_p = delong_bootstrap(y, ford2_s, ford_s, n_boot=N_BOOT, seed=SEED)
        results[0]['delong_p_vs_ford'] = f"{delong_p:.4g}"
    except Exception:
        results[0]['delong_p_vs_ford'] = 'NA'
    results[1]['delong_p_vs_ford'] = ''

    table_s5 = pd.DataFrame(results)
    outpath = TABLES_DIR / "sensitivity_bentaub_reverse.csv"
    table_s5.to_csv(outpath, index=False)
    print(f"\n  Saved {outpath.name}", flush=True)
    print(table_s5.to_string(index=False), flush=True)
    print(f"\n  Comparison: FORD-II AUROC on BT = {ford2_auroc:.4f} vs "
          f"FORD (original) AUROC on BT = {ford_auroc:.4f}", flush=True)
    print(f"  Reference: FORD V8 test-set AUROC = 0.830", flush=True)
    print(f"  Elapsed: {time.time() - t0:.1f}s", flush=True)

    return table_s5


# =====================================================================
# STEP 7: Print comprehensive summary
# =====================================================================

def print_summary(table4: pd.DataFrame, table5: pd.DataFrame,
                  table_s5: pd.DataFrame | None) -> None:
    _banner("COMPREHENSIVE SUMMARY")

    # FORD-II test AUROC
    ford2_row = table4[table4['score'] == 'FORD-II']
    if not ford2_row.empty:
        r = ford2_row.iloc[0]
        print(f"  FORD-II v3 Test AUROC: {r['auroc']:.4f} "
              f"(95% CI: {r['auroc_ci_lo']:.4f} - {r['auroc_ci_hi']:.4f})", flush=True)

    # All comparator AUROCs
    print(f"\n  Comparator AUROCs (test set):", flush=True)
    for _, r in table4.iterrows():
        auroc_str = f"{r['auroc']:.4f}" if not pd.isna(r['auroc']) else 'NA'
        ci_str = f"({r['auroc_ci_lo']:.4f} - {r['auroc_ci_hi']:.4f})" if not pd.isna(r['auroc_ci_lo']) else ''
        delong_str = f"  DeLong p = {r['delong_p_vs_ford2']}" if r['delong_p_vs_ford2'] else ''
        print(f"    {r['score']:10s}: AUROC = {auroc_str} {ci_str}{delong_str}", flush=True)

    # Risk group event rates
    print(f"\n  FORD-II v3 Risk Group Event Rates:", flush=True)
    for _, r in table5.iterrows():
        print(f"    {r['Risk_group']:10s}: {r['FORD_II_event_rate_pct']:.1f}% "
              f"(N={r['FORD_II_n']:,}, events={r['FORD_II_events']:,})", flush=True)

    # Ben Taub reverse validation
    if table_s5 is not None:
        print(f"\n  Ben Taub Reverse Validation:", flush=True)
        for _, r in table_s5.iterrows():
            auroc_str = f"{r['auroc']:.4f}" if not pd.isna(r['auroc']) else 'NA'
            ci_str = f"({r['auroc_ci_lo']:.4f} - {r['auroc_ci_hi']:.4f})" if not pd.isna(r['auroc_ci_lo']) else ''
            print(f"    {r['score']:20s}: AUROC = {auroc_str} {ci_str}", flush=True)

    # Warnings
    print(f"\n  Warnings:", flush=True)
    if not ford2_row.empty and ford2_row.iloc[0]['auroc'] < 0.80:
        print(f"    *** FORD-II v3 test AUROC < 0.80 — review model ***", flush=True)
    else:
        print(f"    None", flush=True)


# =====================================================================
# MAIN
# =====================================================================

def main() -> None:
    t_start = time.time()

    print("=" * 72)
    print("FORD-II v3 Validation Pipeline (NTDB 2019-2024)")
    print(f"Bootstrap iterations: {N_BOOT}")
    print(f"Seed: {SEED}")
    print("=" * 72, flush=True)

    # Step 1: Load data
    df, train, test = load_data()

    # Step 2: Table 1
    table1 = build_table1(train, test)

    # Step 3: Table 4 (validation metrics)
    table4 = build_table4(test)

    # Step 4: Table 5 (risk groups)
    table5 = build_table5(test)

    # Step 5: Figures
    plot_consort(CONSORT_CSV)
    plot_roc_curves(test)
    plot_calibration(test)
    plot_risk_groups(table5)
    plot_dca(test)

    # Step 6: Ben Taub reverse validation
    table_s5 = bentaub_reverse_validation()

    # Step 7: Summary
    print_summary(table4, table5, table_s5)

    elapsed = time.time() - t_start
    print(f"\n{'=' * 72}")
    print(f"FORD-II v3 validation pipeline complete.  Total elapsed: {elapsed:.1f}s")
    print(f"{'=' * 72}\n", flush=True)


if __name__ == "__main__":
    main()
