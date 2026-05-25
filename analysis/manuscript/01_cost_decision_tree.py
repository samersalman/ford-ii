#!/usr/bin/env python
"""
01_cost_decision_tree.py — FORD-II cost-effectiveness decision tree.

Project : FORD-II external validation manuscript

What this does
    Builds a 30-day-horizon cost-consequence decision tree for FORD-II. Loads
    the 9-row `cost_model_inputs.csv`, derives the IRF/SNF/LTCH non-home mix
    from the FORD-II refit test parquet, runs the deterministic base case +
    tornado one-way SA + 10,000-iteration PSA + mandatory sensitivity arms
    (A-F) + threshold analysis + per-center / national scaling, validates
    against a hand-computable 100-patient toy cohort, draws the decision-tree
    diagram programmatically in matplotlib, and renders the CHEERS-2022 28-item
    checklist via `_cheers_data.py`.

    Hospital perspective is primary; payer perspective treated as equal under
    the marginal-beta inpatient framing (Coaston 2025 PMID 40986303). All
    cost outputs in 2024 USD; CPI-MED multipliers per methodology lock § 3.

Pipeline (10 banner-printed steps)
    1. Load + audit cost_model_inputs.csv (9 rows, transparency check).
    2. Derive non-home destination mix from FORD-II ford2_model.parquet (test split).
    3. Deterministic base case (hospital + payer perspectives).
    4. Cost-consequence display (per-flagged-patient breakdown).
    5. One-way deterministic SA -> tornado plot.
    6. Probabilistic SA (10K iter, seed=42) + scatter + CEAC.
    7. Mandatory sensitivity arms (A-F).
    8. Threshold analysis (bisection on los_reduction_days).
    9. Scaling (per-center + national rollout).
    10. CHEERS markdown + toy-cohort validator + decision-tree diagram.

On-script asserts
    1. cost_model_inputs.csv parses cleanly with 9 expected param_name rows.
    2. Toy-cohort hand-calc matches engine output to +/- $0.01.
    3. PSA 95% CrI brackets the deterministic point estimate.
    4. Zero negative los_reduction_days draws survive into the cost engine.
    5. Non-home destination mix sums to 1.0 +/- 1e-6.
    6. Threshold-search converged within tolerance and matches analytical.
    7. CHEERS checklist has all 28 items via _cheers_data.assert_complete().
    8. All file outputs exist with non-zero size.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import os
import sys
import warnings

import matplotlib
matplotlib.use('Agg')  # MUST precede pyplot import
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

import numpy as np
import pandas as pd
from scipy.stats import beta as beta_dist
from scipy.stats import gamma as gamma_dist
from scipy.stats import norm as norm_dist

warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------
# CHEERS data (companion module written in parallel)
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
from _cheers_data import CHEERS_ITEMS, assert_complete  # noqa: E402

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]

# FORD-II refit model parquet is produced by analysis/ford_ii_refit/03_select_and_fit.py.
FORD2_MODEL_PARQUET = REPO_ROOT / "analysis" / "ford_ii_refit" / "data" / "ford2_model.parquet"
if not FORD2_MODEL_PARQUET.exists():
    raise FileNotFoundError(
        f"Expected {FORD2_MODEL_PARQUET}. Run analysis/ford_ii_refit/03_select_and_fit.py first."
    )
V3_MODEL_PQ = str(FORD2_MODEL_PARQUET)

DATA_DIR = str(SCRIPT_DIR / "data")
COHORT_INTERMEDIATE = os.path.join(DATA_DIR, "_cohort_intermediate.csv")
TABLES_DIR = str(REPO_ROOT / "tables")
COST_DIR = str(REPO_ROOT / "figures" / "cost_analysis")
for _d in (DATA_DIR, TABLES_DIR, COST_DIR):
    os.makedirs(_d, exist_ok=True)

COST_INPUTS_CSV = os.path.join(DATA_DIR, "cost_model_inputs.csv")
NON_HOME_MIX_CSV = os.path.join(DATA_DIR, "non_home_destination_mix.csv")

OUT_BASE = os.path.join(TABLES_DIR, "table_base_case.csv")
OUT_CC = os.path.join(TABLES_DIR, "cost_consequence.csv")
OUT_TORNADO = os.path.join(TABLES_DIR, "table_tornado.csv")
OUT_ARMS = os.path.join(TABLES_DIR, "sensitivity_arms.csv")
OUT_THRESH = os.path.join(TABLES_DIR, "table_threshold.csv")
OUT_SCALE = os.path.join(TABLES_DIR, "table_scaling.csv")
OUT_PSA = os.path.join(COST_DIR, "psa_results.csv")
OUT_CHEERS_MD = os.path.join(COST_DIR, "cheers_2022_checklist.md")

SEED = 42
N_PSA = 10_000

EXPECTED_PARAMS = {
    'los_reduction_days',
    'cost_per_day_inpatient',
    'cost_per_day_irf',
    'cost_per_day_snf',
    'cost_per_day_ltch',
    'cost_intervention_per_patient',
    'prevalence_topquartile',
    'prob_topquartile_nonhome',
    'discount_rate',
}

# Facility ALOS divisors used in cost-consequence display + LOS-shift arm.
# IRF 12.5d (MedPAC IRF Payment Basics 2024); SNF 27d (CMS SNF norm; PDPM is
# already per-diem); ICF 27d (proxy = SNF per-diem and ALOS — methodology
# lock § Gotcha 5 rolls ICF under non-home and we apply SNF as the closest
# facility-cost analogue); LTCH 26d (statutory >25 d, MedPAC 2024).
ALOS_FACILITY = {'REHAB': 12.5, 'SNF': 27.0, 'ICF': 27.0, 'LTCH': 26.0}

# Map non-home destination -> which cost_per_day param drives its per-diem.
# ICF rolls up to SNF per CLAUDE.md gotcha #5 (no separate ICF payment series).
DEST_TO_PERDIEM_PARAM = {
    'REHAB': 'cost_per_day_irf',
    'SNF': 'cost_per_day_snf',
    'ICF': 'cost_per_day_snf',  # ICF -> SNF proxy; documented explicitly
    'LTCH': 'cost_per_day_ltch',
}

# NIS HCUP norm flagged in cost_model_inputs.csv notes for Coaston average-
# per-day derivation; used here only for the cost-consequence display + LOS-
# shift sensitivity arm. NOT used in primary delta-cost (marginal beta only).
ALOS_BASELINE = 4.67

# Average inpatient per-day for sensitivity Arm D (Coaston Option C anchor).
AVG_INPATIENT_PER_DAY_2024 = 3239.56

# CPI-MED 2021 -> 2024 multiplier (locked in methodology_lock.md § 3).
CPI_MED_2021_TO_2024 = 1.0710

# PHCE 2021 -> 2024 multiplier for Arm F (sensitivity vs CPI-MED). Derived from
# AHRQ MEPS Price Index Table 3 (Personal Health Care, base 2017=100):
#   PHCE[2021] = 107.2, PHCE[2024] = 116.0  =>  116.0 / 107.2 = 1.0821
# Source: https://meps.ahrq.gov/about_meps/Price_Index.shtml (AHRQ 2024 update,
# fetched 2026-05-02). Coaston 2025 (PMID 40986303) used PHCE for their 2012->
# 2021 normalization, so PHCE-consistent inflation is the methodologically
# matched alternative to BLS CPI-MED for Arm F.
PHCE_2021_TO_2024 = 1.0821


def banner(step_no, title):
    print("=" * 80)
    print(f"STEP {step_no}: {title}")
    print("=" * 80)


def save_fig(fig, stem):
    """Dual-save PNG (300 dpi) + PDF; close fig."""
    png = os.path.join(COST_DIR, f"{stem}.png")
    pdf = os.path.join(COST_DIR, f"{stem}.pdf")
    fig.savefig(png, dpi=300, bbox_inches='tight')
    fig.savefig(pdf, bbox_inches='tight')
    plt.close(fig)
    print(f"  saved {os.path.basename(png)} and {os.path.basename(pdf)}")


# ---------------------------------------------------------------------------
# STEP 1 — Load + audit cost_model_inputs.csv
# ---------------------------------------------------------------------------
def load_and_audit_params():
    banner(1, "Load + audit cost_model_inputs.csv (transparency check)")
    if not os.path.exists(COST_INPUTS_CSV):
        raise FileNotFoundError(f"Missing: {COST_INPUTS_CSV}")
    df = pd.read_csv(COST_INPUTS_CSV)
    print(f"  loaded {len(df)} rows x {df.shape[1]} cols")

    actual = set(df['param_name'].astype(str))
    missing = EXPECTED_PARAMS - actual
    extra = actual - EXPECTED_PARAMS
    if missing or extra:
        print("  [FATAL] cost_model_inputs.csv param_name mismatch.")
        if missing:
            print(f"    missing : {sorted(missing)}")
        if extra:
            print(f"    extra   : {sorted(extra)}")
        sys.exit(2)

    # Transparency: every row must have (source_doi OR source_url) AND notes.
    failures = []
    for _, row in df.iterrows():
        doi = str(row.get('source_doi', '')).strip()
        url = str(row.get('source_url', '')).strip()
        notes = str(row.get('notes', '')).strip()
        has_source = (doi and doi.lower() != 'nan') or (url and url.lower() != 'nan')
        has_notes = bool(notes) and notes.lower() != 'nan'
        if not (has_source and has_notes):
            failures.append({
                'param_name': row['param_name'],
                'has_doi': bool(doi and doi.lower() != 'nan'),
                'has_url': bool(url and url.lower() != 'nan'),
                'has_notes': has_notes,
            })
    if failures:
        print("  [FATAL] transparency check failed for:")
        for f in failures:
            print(f"    {f}")
        sys.exit(3)
    print(f"  transparency check PASSED for all {len(df)} rows")

    # Build dict keyed by param_name
    params = {}
    for _, row in df.iterrows():
        params[row['param_name']] = {
            'point_estimate': float(row['point_estimate']),
            'distribution': str(row['distribution']),
            # dist_param2 may be NaN for Fixed
            'dist_param1': float(row['dist_param1']) if pd.notna(row['dist_param1']) else float('nan'),
            'dist_param2': float(row['dist_param2']) if pd.notna(row['dist_param2']) else float('nan'),
            'evidence_quality': str(row.get('evidence_quality', '')),
        }
    print("  params:")
    for k in sorted(params.keys()):
        p = params[k]
        print(f"    {k:>32s}  point={p['point_estimate']:.6g}  "
              f"dist={p['distribution']}  ({p['dist_param1']:.6g}, {p['dist_param2']:.6g})")
    return params


# ---------------------------------------------------------------------------
# STEP 2 — Derive non-home destination mix
# ---------------------------------------------------------------------------
def derive_non_home_mix(params):
    banner(2, "Derive non-home destination mix (REHAB/SNF/LTCH/ICF)")
    used_v3_parquet = False
    if os.path.exists(V3_MODEL_PQ):
        try:
            mdl = pd.read_parquet(
                V3_MODEL_PQ,
                columns=['split', 'outcome_nonhome', 'DC_DISPOSITION_CODE'],
            )
            test = mdl[mdl['split'] == 'test'].copy()
            print(f"  v3 ford2_model.parquet test split: {len(test):,} rows")
            assert len(test) == 650_737, (
                f"v3 test split row count drift: {len(test)} != 650,737"
            )
            nh = test[test['outcome_nonhome'] == 1].copy()
            print(f"  non-home rows in test: {len(nh):,}")
            counts = nh['DC_DISPOSITION_CODE'].value_counts()
            used_v3_parquet = True
        except Exception as exc:
            print(f"  [WARN] v3 parquet read failed ({exc}); falling back.")
            counts = None
    else:
        counts = None

    if counts is None:
        if not os.path.exists(COHORT_INTERMEDIATE):
            raise FileNotFoundError(
                f"FORD-II parquet missing AND fallback {COHORT_INTERMEDIATE} missing"
            )
        print(f"  FALLBACK: reading {COHORT_INTERMEDIATE} (analytic cohort)")
        df = pd.read_csv(COHORT_INTERMEDIATE)
        # Restrict to non-home dispositions (per CLAUDE.md gotcha 5)
        nh_codes = {'REHAB', 'SNF', 'LTCH', 'ICF'}
        nh = df[df['DC_DISPOSITION_CODE'].isin(nh_codes)].copy()
        counts = nh['DC_DISPOSITION_CODE'].value_counts()
        print(f"  fallback non-home rows: {len(nh):,}")

    # Restrict to the 4 expected non-home codes; assert no other codes leak in
    keep = ['REHAB', 'SNF', 'LTCH', 'ICF']
    counts = counts.reindex(keep).fillna(0).astype(int)
    total = int(counts.sum())
    print(f"  total non-home (REHAB+SNF+LTCH+ICF): {total:,}")
    rows = []
    for dest in keep:
        n = int(counts.loc[dest])
        prop = n / total if total > 0 else 0.0
        rows.append({
            'destination': dest,
            'n': n,
            'proportion_of_nonhome': prop,
            'facility_perdiem_param': DEST_TO_PERDIEM_PARAM[dest],
        })
    mix_df = pd.DataFrame(rows)

    # Round only for CSV display; keep full precision in returned dict
    mix_df_csv = mix_df.copy()
    mix_df_csv['proportion_of_nonhome'] = mix_df_csv['proportion_of_nonhome'].round(8)
    mix_df_csv.to_csv(NON_HOME_MIX_CSV, index=False)
    print(f"  wrote {NON_HOME_MIX_CSV}")
    print(mix_df_csv.to_string(index=False))

    sum_check = float(mix_df['proportion_of_nonhome'].sum())
    print(f"  proportions sum = {sum_check:.10f}")
    assert abs(sum_check - 1.0) < 1e-6, (
        f"Non-home mix proportions sum to {sum_check}; expected 1.0 +/- 1e-6"
    )

    mix = {r['destination']: r['proportion_of_nonhome'] for _, r in mix_df.iterrows()}
    print(f"  used_v3_parquet = {used_v3_parquet}")
    return mix, used_v3_parquet


# ---------------------------------------------------------------------------
# STEP 3 — Deterministic base case
# ---------------------------------------------------------------------------
def delta_cost_per_patient(prevalence, los_red, cost_inpt_pd, cost_intervention):
    """Hospital-perspective per-patient Δcost (positive = savings).

    Δcost = prevalence × (los_red × cost_inpt − cost_intervention)
    LOS truncated at 0 by caller per Briggs TF-6 (no negative LOS effect).
    """
    return prevalence * (los_red * cost_inpt_pd - cost_intervention)


def deterministic_base_case(params):
    banner(3, "Deterministic base case (hospital + payer perspectives)")
    prev = params['prevalence_topquartile']['point_estimate']
    los_red = params['los_reduction_days']['point_estimate']
    cost_inpt = params['cost_per_day_inpatient']['point_estimate']
    cost_int = params['cost_intervention_per_patient']['point_estimate']

    delta_pp = delta_cost_per_patient(prev, los_red, cost_inpt, cost_int)
    bed_days_pp = prev * los_red
    intervention_cost_pp = prev * cost_int
    inpatient_savings_pp = prev * los_red * cost_inpt

    N = 10_000
    rows = []
    # Hospital perspective primary; payer perspective treated as equal under
    # the marginal-beta inpatient framing (avoided inpatient day saves the
    # same dollar from hospital cost-of-production and Medicare/payer
    # reimbursement at the margin). Documented explicitly here.
    for perspective in ('hospital', 'payer'):
        rows.append({
            'perspective': perspective,
            'unit': 'per_patient',
            'prevalence_topquartile': prev,
            'los_reduction_days': los_red,
            'cost_per_day_inpatient': cost_inpt,
            'cost_intervention_per_patient': cost_int,
            'bed_days_saved': bed_days_pp,
            'intervention_cost': intervention_cost_pp,
            'inpatient_savings': inpatient_savings_pp,
            'delta_cost_per_patient': delta_pp,
            'note': ('Hospital primary; payer = hospital under marginal-beta '
                     'inpatient framing (Coaston 2025 PMID 40986303)'),
        })
        rows.append({
            'perspective': perspective,
            'unit': f'per_{N}_cohort',
            'prevalence_topquartile': prev,
            'los_reduction_days': los_red,
            'cost_per_day_inpatient': cost_inpt,
            'cost_intervention_per_patient': cost_int,
            'bed_days_saved': bed_days_pp * N,
            'intervention_cost': intervention_cost_pp * N,
            'inpatient_savings': inpatient_savings_pp * N,
            'delta_cost_per_patient': delta_pp * N,
            'note': f'Aggregated to N={N:,}',
        })
    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT_BASE, index=False)
    print(f"  wrote {OUT_BASE}")
    print(out_df.to_string(index=False))
    print(f"  Δcost per patient = ${delta_pp:.4f}  "
          f"(positive = net savings)")
    return delta_pp, bed_days_pp


# ---------------------------------------------------------------------------
# STEP 4 — Cost-consequence display
# ---------------------------------------------------------------------------
def cost_consequence(params, mix):
    banner(4, "Cost-consequence display (per-flagged-patient breakdown)")
    cost_inpt = params['cost_per_day_inpatient']['point_estimate']
    cost_int = params['cost_intervention_per_patient']['point_estimate']
    prob_nh = params['prob_topquartile_nonhome']['point_estimate']

    # (a) Baseline inpatient cost (per flagged patient)
    a_baseline_inpt = ALOS_BASELINE * cost_inpt

    # (b) Intervention cost (incurred only for flagged patients)
    b_intervention = cost_int

    # (c) Downstream weighted facility cost = prob_nh × Σ(prop[d] × perdiem[d] × ALOS[d])
    perdiem = {
        'REHAB': params['cost_per_day_irf']['point_estimate'],
        'SNF': params['cost_per_day_snf']['point_estimate'],
        'ICF': params['cost_per_day_snf']['point_estimate'],  # SNF proxy
        'LTCH': params['cost_per_day_ltch']['point_estimate'],
    }
    weighted_facility_cost_per_flagged = 0.0
    weighted_facility_perdiem_per_facday = 0.0
    breakdown_rows = []
    for dest in ('REHAB', 'SNF', 'ICF', 'LTCH'):
        prop = mix[dest]
        pd_d = perdiem[dest]
        alos_d = ALOS_FACILITY[dest]
        contrib_per_facday = prop * pd_d
        contrib_full = prob_nh * prop * pd_d * alos_d
        weighted_facility_cost_per_flagged += contrib_full
        weighted_facility_perdiem_per_facday += contrib_per_facday
        breakdown_rows.append({
            'component': f'downstream_{dest}',
            'destination': dest,
            'proportion_of_nonhome': prop,
            'facility_per_diem_2024_USD': pd_d,
            'facility_ALOS_days': alos_d,
            'cost_per_flagged_patient': contrib_full,
            'notes': (f"ALOS source: REHAB=12.5d MedPAC IRF, SNF/ICF=27d "
                      f"(SNF norm; ICF -> SNF per CLAUDE.md gotcha #5), "
                      f"LTCH=26d (statutory >25 d, MedPAC)"),
        })

    rows = [
        {
            'component': 'baseline_inpatient_cost',
            'destination': '',
            'proportion_of_nonhome': float('nan'),
            'facility_per_diem_2024_USD': cost_inpt,
            'facility_ALOS_days': ALOS_BASELINE,
            'cost_per_flagged_patient': a_baseline_inpt,
            'notes': (f"ALOS_baseline = {ALOS_BASELINE} d (NIS HCUP norm flagged "
                      f"in cost_model_inputs.csv notes; cost_per_day_inpatient "
                      f"= ${cost_inpt:.2f}/d marginal beta)"),
        },
        {
            'component': 'intervention_cost',
            'destination': '',
            'proportion_of_nonhome': float('nan'),
            'facility_per_diem_2024_USD': float('nan'),
            'facility_ALOS_days': float('nan'),
            'cost_per_flagged_patient': b_intervention,
            'notes': (f"Per-patient case-management cost (Salgado 2023 PMID "
                      f"PMC10752096; inflated 2020->2024 USD)"),
        },
    ]
    rows.extend(breakdown_rows)
    rows.append({
        'component': 'downstream_TOTAL_weighted',
        'destination': 'ALL_NON_HOME',
        'proportion_of_nonhome': 1.0,
        'facility_per_diem_2024_USD': weighted_facility_perdiem_per_facday,
        'facility_ALOS_days': float('nan'),
        'cost_per_flagged_patient': weighted_facility_cost_per_flagged,
        'notes': (f"Sum across REHAB+SNF+ICF+LTCH; weighted_perdiem reported "
                  f"as Σ(prop×perdiem) per facility-day (no ALOS in this row)"),
    })
    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT_CC, index=False)
    print(f"  wrote {OUT_CC}")
    print(out_df.to_string(index=False))
    return weighted_facility_perdiem_per_facday


# ---------------------------------------------------------------------------
# STEP 5 — One-way deterministic SA -> tornado plot
# ---------------------------------------------------------------------------
def param_95_ci(spec):
    """Return (low, high) at 2.5/97.5 quantiles for a parameter spec dict.

    Distributions parameterized per cost_model_inputs.csv schema:
        Normal: dist_param1=mu, dist_param2=sigma
        Gamma:  dist_param1=shape, dist_param2=rate (scale = 1/rate)
        Beta:   dist_param1=alpha, dist_param2=beta
        Fixed:  no CI (returns point, point)
    """
    d = spec['distribution']
    p1 = spec['dist_param1']
    p2 = spec['dist_param2']
    pe = spec['point_estimate']
    if d == 'Normal':
        lo = norm_dist.ppf(0.025, loc=p1, scale=p2)
        hi = norm_dist.ppf(0.975, loc=p1, scale=p2)
    elif d == 'Gamma':
        scale = 1.0 / p2
        lo = gamma_dist.ppf(0.025, p1, scale=scale)
        hi = gamma_dist.ppf(0.975, p1, scale=scale)
    elif d == 'Beta':
        lo = beta_dist.ppf(0.025, p1, p2)
        hi = beta_dist.ppf(0.975, p1, p2)
    elif d == 'Fixed':
        lo = pe
        hi = pe
    else:
        raise ValueError(f"Unknown distribution '{d}'")
    return float(lo), float(hi)


def tornado_sa(params, base_delta):
    banner(5, "One-way deterministic SA -> tornado plot")

    # Active SA params: all 6 cost/effect/prev rows + the 2 v3-artifact Beta
    # priors (per spec: "actually DO include them with Beta 95% CI as the SA
    # range"). Skip discount_rate (Fixed=0).
    sa_params = [
        'los_reduction_days',
        'cost_per_day_inpatient',
        'cost_intervention_per_patient',
        'prevalence_topquartile',
        'prob_topquartile_nonhome',
        'cost_per_day_irf',
        'cost_per_day_snf',
        'cost_per_day_ltch',
    ]

    base_prev = params['prevalence_topquartile']['point_estimate']
    base_los = params['los_reduction_days']['point_estimate']
    base_inpt = params['cost_per_day_inpatient']['point_estimate']
    base_int = params['cost_intervention_per_patient']['point_estimate']

    rows = []
    for pname in sa_params:
        lo, hi = param_95_ci(params[pname])
        # Briggs TF-6: clamp negative LOS at 0 (zero-effect, not cost increase)
        if pname == 'los_reduction_days':
            lo = max(lo, 0.0)
            hi = max(hi, 0.0)

        # Cost params don't drive primary Δcost EXCEPT inpatient/intervention.
        # IRF/SNF/LTCH per-diems do not enter the primary delta in a marginal-
        # beta framing (they enter the cost-consequence display only). For the
        # tornado, vary them anyway so the user sees they have zero swing on
        # primary delta (this is informative, not a bug).
        def _eval(prev_v, los_v, inpt_v, int_v):
            return delta_cost_per_patient(prev_v, los_v, inpt_v, int_v)

        if pname == 'prevalence_topquartile':
            d_lo = _eval(lo, base_los, base_inpt, base_int)
            d_hi = _eval(hi, base_los, base_inpt, base_int)
        elif pname == 'los_reduction_days':
            d_lo = _eval(base_prev, lo, base_inpt, base_int)
            d_hi = _eval(base_prev, hi, base_inpt, base_int)
        elif pname == 'cost_per_day_inpatient':
            d_lo = _eval(base_prev, base_los, lo, base_int)
            d_hi = _eval(base_prev, base_los, hi, base_int)
        elif pname == 'cost_intervention_per_patient':
            d_lo = _eval(base_prev, base_los, base_inpt, lo)
            d_hi = _eval(base_prev, base_los, base_inpt, hi)
        else:
            # prob_topquartile_nonhome and IRF/SNF/LTCH per-diems: zero swing
            # on primary delta (documented per spec).
            d_lo = base_delta
            d_hi = base_delta
        swing = abs(d_hi - d_lo)
        rows.append({
            'param_name': pname,
            'low_value': lo,
            'high_value': hi,
            'delta_cost_low': d_lo,
            'delta_cost_high': d_hi,
            'swing_abs': swing,
        })
    df = pd.DataFrame(rows).sort_values('swing_abs', ascending=False).reset_index(drop=True)
    df.to_csv(OUT_TORNADO, index=False)
    print(f"  wrote {OUT_TORNADO}")
    print(df.to_string(index=False))

    # Render tornado figure (only nonzero-swing rows; keep the rest in CSV).
    plot_df = df[df['swing_abs'] > 1e-9].copy().sort_values('swing_abs', ascending=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    yticks = np.arange(len(plot_df))
    for i, r in enumerate(plot_df.itertuples(index=False)):
        left = min(r.delta_cost_low, r.delta_cost_high)
        width = abs(r.delta_cost_high - r.delta_cost_low)
        ax.barh(i, width, left=left, color='steelblue', alpha=0.85, edgecolor='black')
    ax.axvline(base_delta, color='red', linestyle='--', linewidth=1.5,
               label=f'Base case Δ = ${base_delta:.2f}')
    ax.set_yticks(yticks)
    ax.set_yticklabels(plot_df['param_name'].tolist())
    ax.set_xlabel('Δcost per patient (2024 USD; positive = net savings)')
    ax.set_title('Tornado: one-way SA on FORD-II Δcost per patient (95% CI ranges)')
    ax.legend(loc='lower right')
    ax.grid(True, axis='x', alpha=0.3)
    save_fig(fig, 'figure_tornado')
    return df


# ---------------------------------------------------------------------------
# STEP 6 — PSA (10K iter, seed=42)
# ---------------------------------------------------------------------------
def psa(params, base_delta):
    banner(6, f"PSA (n={N_PSA:,} iterations, seed={SEED})")
    rng = np.random.default_rng(SEED)

    def beta_draw(spec):
        return rng.beta(spec['dist_param1'], spec['dist_param2'], size=N_PSA)

    def gamma_draw(spec):
        # cost_model_inputs.csv parameterizes Gamma as (shape, rate);
        # numpy uses scale = 1/rate. Critical bug-trap (Session 5 lock).
        scale = 1.0 / spec['dist_param2']
        return rng.gamma(spec['dist_param1'], scale=scale, size=N_PSA)

    def normal_draw(spec):
        return rng.normal(spec['dist_param1'], spec['dist_param2'], size=N_PSA)

    prev_d = beta_draw(params['prevalence_topquartile'])
    prob_nh_d = beta_draw(params['prob_topquartile_nonhome'])
    los_d_raw = normal_draw(params['los_reduction_days'])
    n_negative_pre = int(np.sum(los_d_raw < 0))
    los_d = np.maximum(los_d_raw, 0.0)  # Briggs TF-6: zero-effect floor
    cost_inpt_d = gamma_draw(params['cost_per_day_inpatient'])
    cost_irf_d = gamma_draw(params['cost_per_day_irf'])
    cost_snf_d = gamma_draw(params['cost_per_day_snf'])
    cost_ltch_d = gamma_draw(params['cost_per_day_ltch'])
    cost_int_d = gamma_draw(params['cost_intervention_per_patient'])

    # Per-iteration Δcost per patient + bed-days saved per 10K patients
    delta_pp = prev_d * (los_d * cost_inpt_d - cost_int_d)
    bed_days_per_10K = 10_000 * prev_d * los_d

    # Verification: zero negatives in final cost-engine input
    n_negative_post = int(np.sum(los_d < 0))
    print(f"  los_reduction_days draws: {n_negative_pre:,} negative (pre-clamp); "
          f"{n_negative_post:,} negative (post-clamp)")
    assert n_negative_post == 0, (
        f"Bug: {n_negative_post} negative LOS draws survived clamp"
    )

    # Stats
    det_point = base_delta
    psa_mean = float(delta_pp.mean())
    p25 = float(np.percentile(delta_pp, 2.5))
    p975 = float(np.percentile(delta_pp, 97.5))
    p_savings = float((delta_pp > 0).mean())
    print(f"  deterministic Δcost per patient = ${det_point:.4f}")
    print(f"  PSA mean                        = ${psa_mean:.4f}")
    print(f"  PSA 95% CrI                     = (${p25:.4f}, ${p975:.4f})")
    print(f"  P(net savings > $0)             = {p_savings:.4f}")

    # Sanity: deterministic point inside 95% CrI
    assert p25 <= det_point <= p975, (
        f"PSA 95% CrI ({p25:.4f}, {p975:.4f}) does NOT bracket deterministic "
        f"point ({det_point:.4f})"
    )

    # Write PSA CSV (round inputs for display; keep full precision in arrays)
    psa_df = pd.DataFrame({
        'iter': np.arange(1, N_PSA + 1),
        'prevalence': np.round(prev_d, 6),
        'prob_nonhome': np.round(prob_nh_d, 6),
        'los_red': np.round(los_d, 6),
        'cost_inpt': np.round(cost_inpt_d, 6),
        'cost_irf': np.round(cost_irf_d, 6),
        'cost_snf': np.round(cost_snf_d, 6),
        'cost_ltch': np.round(cost_ltch_d, 6),
        'cost_intervention': np.round(cost_int_d, 6),
        'delta_cost_per_patient': delta_pp,
        'bed_days_saved_per_10K': bed_days_per_10K,
    })
    psa_df.to_csv(OUT_PSA, index=False)
    print(f"  wrote {OUT_PSA}")

    # PSA scatter (cost-effectiveness plane)
    fig, ax = plt.subplots(figsize=(9, 7))
    delta_per_10K = delta_pp * 10_000
    ax.scatter(bed_days_per_10K, delta_per_10K, s=4, alpha=0.25, color='steelblue')
    ax.axhline(0, color='black', linewidth=0.5)
    ax.axvline(0, color='black', linewidth=0.5)
    ax.set_xlabel('Bed-days saved per 10,000 patients')
    ax.set_ylabel('Δcost per 10,000 patients (2024 USD; positive = savings)')
    ax.set_title(f'PSA cost-effectiveness plane (n={N_PSA:,})')
    ax.grid(True, alpha=0.3)
    save_fig(fig, 'figure_psa_scatter')

    # CEAC (continuous WTP grid 0..1000 step 25)
    wtp_grid = np.arange(0, 1001, 25)
    ceac = [(delta_pp >= w).mean() for w in wtp_grid]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(wtp_grid, ceac, color='steelblue', linewidth=2)
    ax.axhline(0.95, color='gray', linestyle=':', linewidth=1, alpha=0.7)
    ax.axhline(0.50, color='gray', linestyle=':', linewidth=1, alpha=0.7)
    ax.set_xlabel('WTP threshold ($ per patient)')
    ax.set_ylabel('P(net savings >= WTP)')
    ax.set_title('Cost-effectiveness acceptability curve (CEAC)')
    ax.set_xlim(0, 1000)
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.3)
    save_fig(fig, 'figure_ceac')

    return {
        'mean': psa_mean,
        'p25': p25,
        'p975': p975,
        'p_savings': p_savings,
        'n_neg_pre': n_negative_pre,
        'n_neg_post': n_negative_post,
    }


# ---------------------------------------------------------------------------
# STEP 7 — Mandatory sensitivity arms (A-F)
# ---------------------------------------------------------------------------
def sensitivity_arms(params, mix, base_delta, weighted_perdiem_per_facday):
    banner(7, "Mandatory sensitivity arms (A-F)")
    prev = params['prevalence_topquartile']['point_estimate']
    los_red = params['los_reduction_days']['point_estimate']
    cost_inpt = params['cost_per_day_inpatient']['point_estimate']
    cost_int = params['cost_intervention_per_patient']['point_estimate']
    prob_nh = params['prob_topquartile_nonhome']['point_estimate']

    perdiem = {
        'REHAB': params['cost_per_day_irf']['point_estimate'],
        'SNF': params['cost_per_day_snf']['point_estimate'],
        'ICF': params['cost_per_day_snf']['point_estimate'],
        'LTCH': params['cost_per_day_ltch']['point_estimate'],
    }

    rows = []

    def add(arm, variant, description, delta):
        pct = 100.0 * (delta - base_delta) / abs(base_delta) if abs(base_delta) > 0 else float('nan')
        rows.append({
            'arm': arm,
            'variant': variant,
            'description': description,
            'delta_cost_per_patient': delta,
            'pct_change_vs_base': pct,
        })

    # Arm A: cost_per_day_inpatient multipliers
    for mult in (1.3, 1.5):
        d = delta_cost_per_patient(prev, los_red, cost_inpt * mult, cost_int)
        add('A', f'inpt_perdiem_x{mult}',
            f'High-acuity readiness flag (Ashley/Knowlton); inpatient per-diem × {mult}', d)

    # Arm B: IRF/SNF/LTCH per-diem deflated 10% / 15% (cost-consequence
    # display impact only; primary Δcost unaffected per marginal-beta framing.
    # Reported as Δ(weighted-facility cost per flagged TP)).
    base_wfc = prob_nh * sum(
        mix[d_] * perdiem[d_] * ALOS_FACILITY[d_] for d_ in ('REHAB', 'SNF', 'ICF', 'LTCH')
    )
    for defl in (0.10, 0.15):
        defl_wfc = prob_nh * sum(
            mix[d_] * perdiem[d_] * (1 - defl) * ALOS_FACILITY[d_]
            for d_ in ('REHAB', 'SNF', 'ICF', 'LTCH')
        )
        d_change = defl_wfc - base_wfc
        rows.append({
            'arm': 'B',
            'variant': f'facility_perdiem_-{int(defl*100)}pct',
            'description': (f'MedPAC margin adjustment: IRF+SNF+LTCH per-diem '
                            f'deflated {int(defl*100)}%; reports Δ(weighted-'
                            f'facility cost per flagged TP) only (primary Δ '
                            f'unchanged under marginal-beta framing)'),
            'delta_cost_per_patient': d_change,
            'pct_change_vs_base': float('nan'),
        })

    # Arm C: intervention cost sweep $45 (BLS lower) / $200 (Brigham upper)
    for ic in (45.0, 200.0):
        d = delta_cost_per_patient(prev, los_red, cost_inpt, ic)
        add('C', f'cost_intervention_${int(ic)}',
            f'Intervention cost = ${ic:.0f} (BLS SOC 21-1022 / Brigham anchor)', d)

    # Arm D: average inpatient per-day instead of marginal beta
    d = delta_cost_per_patient(prev, los_red, AVG_INPATIENT_PER_DAY_2024, cost_int)
    add('D', f'avg_inpatient_${AVG_INPATIENT_PER_DAY_2024:.2f}',
        (f'Average inpatient per-day = ${AVG_INPATIENT_PER_DAY_2024:.2f}/d '
         f'instead of marginal β ${cost_inpt:.2f}/d (Coaston Option C)'), d)

    # Arm E: LOS-shift — saved inpatient day shifts to 1 weighted-facility day
    weighted_facility_perdiem = weighted_perdiem_per_facday  # already $/facility-day
    d_shift = prev * (los_red * (cost_inpt - weighted_facility_perdiem) - cost_int)
    add('E', 'los_shift_to_facility',
        (f'Saved inpatient day shifts to 1 weighted-facility day; '
         f'weighted_facility_perdiem = ${weighted_facility_perdiem:.2f}/d'),
        d_shift)

    # Arm F: PHCE NHEA inflator vs BLS CPI-MED.
    # Re-deflate Coaston's $2187.75/d (2021 USD) using AHRQ MEPS Price Index
    # PHCE (Personal Health Care, base 2017=100): PHCE[2021]=107.2,
    # PHCE[2024]=116.0  =>  multiplier = 116.0/107.2 = 1.0821.
    # Source: https://meps.ahrq.gov/about_meps/Price_Index.shtml (Table 3,
    # AHRQ 2024 update, fetched 2026-05-02). Index-consistent with Coaston
    # 2025 (PMID 40986303) which used PHCE for 2012->2021 normalization.
    cost_inpt_phce = 2187.75 * PHCE_2021_TO_2024
    d_phce = delta_cost_per_patient(prev, los_red, cost_inpt_phce, cost_int)
    add('F', f'phce_inflator_{PHCE_2021_TO_2024:.4f}',
        (f'PHCE NHEA inflator (AHRQ MEPS Price Index Table 3, base 2017=100): '
         f'PHCE 2021->2024 = 116.0/107.2 = {PHCE_2021_TO_2024:.4f}; inpt '
         f'${cost_inpt_phce:.2f}/d (vs CPI-MED 1.0710->$2343.08/d). '
         f'Index-consistent with Coaston 2025 (PMID 40986303) which used PHCE '
         f'for 2012->2021 normalization. CHEERS Item 15.'),
        d_phce)

    df = pd.DataFrame(rows)
    df.to_csv(OUT_ARMS, index=False)
    print(f"  wrote {OUT_ARMS}")
    print(df.to_string(index=False))
    return df


# ---------------------------------------------------------------------------
# STEP 8 — Threshold analysis
# ---------------------------------------------------------------------------
def threshold_analysis(params):
    banner(8, "Threshold analysis (bisection on los_reduction_days)")
    prev = params['prevalence_topquartile']['point_estimate']
    cost_inpt = params['cost_per_day_inpatient']['point_estimate']
    cost_int = params['cost_intervention_per_patient']['point_estimate']

    # Analytical: Δ = 0  =>  los_red = cost_int / cost_inpt (prev cancels)
    analytical = cost_int / cost_inpt

    # Bisection
    lo, hi = 0.0, 5.0
    tol = 1e-4
    converged = False
    los_mid = float('nan')
    for _ in range(200):
        los_mid = 0.5 * (lo + hi)
        d_mid = delta_cost_per_patient(prev, los_mid, cost_inpt, cost_int)
        if abs(d_mid) < tol * abs(prev * cost_inpt):
            converged = True
            break
        # Δ is increasing in los_red (positive coefficient prev*cost_inpt)
        if d_mid < 0:
            lo = los_mid
        else:
            hi = los_mid
    if abs(los_mid - analytical) > tol:
        # Tighten further if needed
        for _ in range(200):
            los_mid = 0.5 * (lo + hi)
            d_mid = delta_cost_per_patient(prev, los_mid, cost_inpt, cost_int)
            if abs(los_mid - analytical) < tol:
                converged = True
                break
            if d_mid < 0:
                lo = los_mid
            else:
                hi = los_mid

    print(f"  analytical solution = {analytical:.6f} d "
          f"(= ${cost_int:.2f} / ${cost_inpt:.2f})")
    print(f"  bisection solution  = {los_mid:.6f} d")
    print(f"  |bisect − analytical| = {abs(los_mid - analytical):.2e}  "
          f"(tol = {tol})")
    converged = converged and (abs(los_mid - analytical) < tol)
    print(f"  converged = {converged}")
    assert converged, (
        f"Threshold bisection did not converge to analytical "
        f"({analytical:.6f}); got {los_mid:.6f}"
    )

    df = pd.DataFrame([{
        'threshold_los_reduction_days': los_mid,
        'analytical_solution': analytical,
        'bisection_solution': los_mid,
        'tolerance': tol,
        'converged': bool(converged),
    }])
    df.to_csv(OUT_THRESH, index=False)
    print(f"  wrote {OUT_THRESH}")
    print(df.to_string(index=False))
    return analytical, los_mid


# ---------------------------------------------------------------------------
# STEP 9 — Scaling
# ---------------------------------------------------------------------------
def scaling(params, base_delta):
    banner(9, "Scaling (per-center + national rollout)")
    prev = params['prevalence_topquartile']['point_estimate']
    los_red = params['los_reduction_days']['point_estimate']

    # Bed-days saved per patient (across all patients, not just flagged)
    # = prevalence × los_red (prevalence × LOS-shift restricted to flagged)
    bed_days_per_patient = prev * los_red

    rows = [
        {
            'scenario': 'single_hospitalization',
            'n_patients': 1,
            'delta_cost_total_2024_USD': base_delta * 1,
            'bed_days_saved': bed_days_per_patient * 1,
            'notes': 'Per-patient Δcost (1 admission)',
        },
    ]
    # Per-center: 800/1150/1500 fractures/yr (annual-volume anchor)
    for label, n in (('per_center_low', 800), ('per_center_mid', 1150),
                     ('per_center_high', 1500)):
        rows.append({
            'scenario': label,
            'n_patients': n,
            'delta_cost_total_2024_USD': base_delta * n,
            'bed_days_saved': bed_days_per_patient * n,
            'notes': (f'Per-center annual fracture volume = {n} '
                      f'(range 800–1500/yr)'),
        })
    # National rollout: 580 ACS-verified trauma centers × midpoint volume
    n_national = 580 * 1150
    rows.append({
        'scenario': 'national_rollout_580_centers_x_1150_pts',
        'n_patients': n_national,
        'delta_cost_total_2024_USD': base_delta * n_national,
        'bed_days_saved': bed_days_per_patient * n_national,
        'notes': '580 ACS-verified trauma centers × 1150 fractures/center/yr (midpoint)',
    })
    df = pd.DataFrame(rows)
    df.to_csv(OUT_SCALE, index=False)
    print(f"  wrote {OUT_SCALE}")
    print(df.to_string(index=False))
    return df


# ---------------------------------------------------------------------------
# STEP 10 — CHEERS markdown + toy cohort + decision-tree diagram
# ---------------------------------------------------------------------------
def render_cheers_md():
    """Render CHEERS_ITEMS list as a markdown table."""
    assert_complete()  # raises if not 28 items / schema invalid

    def _esc(s):
        return str(s).replace('|', '\\|').replace('\n', ' ').strip()

    header = ("| Item # | Section | Item | Description | Status | "
              "Cross-reference |\n"
              "|---|---|---|---|---|---|\n")
    lines = [header]
    for it in CHEERS_ITEMS:
        lines.append(
            f"| {it['item_no']} | {_esc(it['section'])} | "
            f"{_esc(it['item_name'])} | {_esc(it['description'])} | "
            f"{_esc(it['address_status'])} | "
            f"{_esc(it['cross_reference'])} |\n"
        )
    md = (
        "# CHEERS 2022 reporting checklist — FORD-II cost-effectiveness analysis\n\n"
        "Source-of-truth: Husereau D, Drummond M, Augustovski F, et al. "
        "*Consolidated Health Economic Evaluation Reporting Standards 2022 "
        "(CHEERS 2022) Statement.* BMJ 2022;376:e067975. "
        "PMID 35017145; doi:10.1136/bmj-2021-067975.\n\n"
        "Generated by `analysis/manuscript/01_cost_decision_tree.py` from "
        "`analysis/manuscript/_cheers_data.py` (28 items).\n\n"
    )
    md += ''.join(lines)
    with open(OUT_CHEERS_MD, 'w') as f:
        f.write(md)
    print(f"  wrote {OUT_CHEERS_MD} ({len(CHEERS_ITEMS)} items)")


def toy_cohort_validator(params):
    """100-patient deterministic engine validator. Hand-calc must match
    engine application of delta_cost_per_patient_total within $0.01."""
    print("  toy cohort: N=100; flag round(100 × 0.1622) = 16; los_red=1.0 d")
    prev_for_toy = params['prevalence_topquartile']['point_estimate']
    cost_inpt = params['cost_per_day_inpatient']['point_estimate']
    cost_int = params['cost_intervention_per_patient']['point_estimate']

    n_total = 100
    n_flagged = int(round(n_total * prev_for_toy))
    los_per_flagged = 1.0
    print(f"  n_flagged = {n_flagged}; cost_inpt = ${cost_inpt:.2f}/d; "
          f"cost_int = ${cost_int:.2f}")

    # Hand-calc per-flagged net savings = 1.0 × 2343.08 − 109.70
    hand_per_flagged = los_per_flagged * cost_inpt - cost_int
    hand_total = n_flagged * hand_per_flagged
    print(f"  hand-calc per-flagged Δcost = ${hand_per_flagged:.4f}")
    print(f"  hand-calc total Δcost (16 flagged) = ${hand_total:.4f}")

    # Engine: apply the same formula via delta_cost_per_patient with prev set
    # to flagged-fraction 16/100 (so engine_per_patient × N = total).
    engine_prev = n_flagged / n_total
    engine_per_patient = delta_cost_per_patient(
        engine_prev, los_per_flagged, cost_inpt, cost_int
    )
    engine_total = engine_per_patient * n_total
    print(f"  engine per-patient Δcost (prev={engine_prev}) = ${engine_per_patient:.4f}")
    print(f"  engine total Δcost = ${engine_total:.4f}")

    diff = abs(engine_total - hand_total)
    print(f"  |engine_total − hand_total| = ${diff:.6f}")
    assert diff <= 0.01, (
        f"Toy-cohort hand-calc mismatch: hand=${hand_total:.4f} vs "
        f"engine=${engine_total:.4f} (|diff|=${diff:.6f} > $0.01)"
    )


def decision_tree_diagram(params, mix):
    """Programmatic matplotlib decision tree (no graphviz dep)."""
    cost_inpt = params['cost_per_day_inpatient']['point_estimate']
    cost_int = params['cost_intervention_per_patient']['point_estimate']
    los_red = params['los_reduction_days']['point_estimate']
    prev = params['prevalence_topquartile']['point_estimate']
    prob_nh = params['prob_topquartile_nonhome']['point_estimate']

    # Costs to annotate at terminal nodes
    usual_inpt = ALOS_BASELINE * cost_inpt
    weighted_facility_cost = prob_nh * sum(
        mix[d] * params[DEST_TO_PERDIEM_PARAM[d]]['point_estimate'] * ALOS_FACILITY[d]
        for d in ('REHAB', 'SNF', 'ICF', 'LTCH')
    )
    flagged_inpt = (ALOS_BASELINE - los_red) * cost_inpt
    flagged_total = flagged_inpt + cost_int

    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis('off')

    def node(x, y, w, h, label, fc='#e6f0fa'):
        rect = Rectangle((x - w / 2, y - h / 2), w, h,
                         facecolor=fc, edgecolor='black', linewidth=1.2)
        ax.add_patch(rect)
        ax.text(x, y, label, ha='center', va='center', fontsize=9, wrap=True)

    def arrow(x1, y1, x2, y2, label=None):
        a = FancyArrowPatch((x1, y1), (x2, y2),
                            arrowstyle='->', mutation_scale=14,
                            linewidth=1.0, color='black')
        ax.add_patch(a)
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.15, label,
                    ha='center', va='bottom', fontsize=8, color='darkblue')

    # Root
    node(7, 8, 4.0, 0.7, 'Adult fracture, ED admission', fc='#fff2cc')

    # Two arms
    node(3, 6.4, 3.4, 0.6, 'Usual care', fc='#d9ead3')
    node(11, 6.4, 3.4, 0.6, 'FORD-II', fc='#cfe2f3')
    arrow(7, 7.65, 3, 6.7)
    arrow(7, 7.65, 11, 6.7)

    # Usual-care arm: inpatient stay -> downstream non-home (cost-consequence)
    node(3, 4.8, 3.6, 0.9,
         f'Inpatient stay\nALOS={ALOS_BASELINE} d × ${cost_inpt:,.0f}/d\n= ${usual_inpt:,.0f}',
         fc='#f4cccc')
    arrow(3, 6.1, 3, 5.25)

    node(3, 2.8, 4.0, 1.1,
         (f'Downstream (non-home, P={prob_nh:.2f})\n'
          f'Weighted facility cost\n= ${weighted_facility_cost:,.0f}\n'
          f'(REHAB/SNF/ICF/LTCH)'),
         fc='#fce5cd')
    arrow(3, 4.35, 3, 3.35)

    # FORD-II arm splits by prevalence
    node(8.5, 4.8, 3.0, 0.7,
         f'Non-flagged ({1-prev:.2%})\n= usual care',
         fc='#d9ead3')
    node(13, 4.8, 2.8, 0.7,
         f'Flagged ({prev:.2%})',
         fc='#cfe2f3')
    arrow(11, 6.1, 8.5, 5.15, f'{1-prev:.2%}')
    arrow(11, 6.1, 13, 5.15, f'{prev:.2%}')

    # Non-flagged terminal node = same as usual-care inpatient
    node(8.5, 3.2, 3.0, 0.9,
         f'Inpatient stay\n${usual_inpt:,.0f}\n(same as usual care)',
         fc='#f4cccc')
    arrow(8.5, 4.45, 8.5, 3.65)

    # Flagged sub-tree: shorter inpatient + intervention
    node(13, 3.2, 3.0, 1.1,
         (f'Inpatient stay\n({ALOS_BASELINE}−{los_red:.1f}) d × '
          f'${cost_inpt:,.0f}/d\n= ${flagged_inpt:,.0f}'),
         fc='#f4cccc')
    arrow(13, 4.45, 13, 3.75)

    node(13, 1.4, 3.0, 1.1,
         (f'+ Intervention cost\n${cost_int:,.2f}\n'
          f'Total: ${flagged_total:,.0f}'),
         fc='#cfe2f3')
    arrow(13, 2.65, 13, 1.95)

    ax.set_title('FORD-II decision tree (30-d horizon, hospital perspective)',
                 fontsize=12, pad=12)
    save_fig(fig, 'decision_tree_diagram')


def step_10_cheers_toy_diagram(params, mix):
    banner(10, "CHEERS markdown + toy-cohort validator + decision-tree diagram")
    render_cheers_md()
    toy_cohort_validator(params)
    decision_tree_diagram(params, mix)


# ---------------------------------------------------------------------------
# Verification gate
# ---------------------------------------------------------------------------
def verify_outputs(psa_stats, threshold_analytical, threshold_bisect):
    print()
    print("-" * 80)
    print("VERIFICATION BLOCK")
    print("-" * 80)

    checks = []

    # 1. cost_model_inputs.csv parsed (already enforced upstream; re-test file)
    chk1 = os.path.exists(COST_INPUTS_CSV) and os.path.getsize(COST_INPUTS_CSV) > 0
    checks.append(('1. cost_model_inputs.csv exists + non-empty', chk1, ''))

    # 2. Toy-cohort: handled inline; if we got here it passed
    checks.append(('2. Toy-cohort hand-calc within $0.01', True,
                   '(asserted inline at step 10)'))

    # 3. PSA brackets deterministic
    chk3 = (psa_stats['p25'] <= psa_stats['mean']  # placeholder
            and True)  # bracket-check asserted in psa(); reaching here = PASS
    checks.append(('3. PSA 95% CrI brackets deterministic', True,
                   f"CrI=({psa_stats['p25']:.4f},{psa_stats['p975']:.4f}); "
                   f"mean={psa_stats['mean']:.4f}"))

    # 4. Zero negative LOS draws survived clamp
    chk4 = (psa_stats['n_neg_post'] == 0)
    checks.append(('4. Zero negative los_reduction_days draws in cost engine',
                   chk4,
                   f"pre={psa_stats['n_neg_pre']}, post={psa_stats['n_neg_post']}"))

    # 5. Non-home mix sums to 1 (asserted upstream)
    checks.append(('5. Non-home destination mix sums to 1.0 +/- 1e-6', True,
                   '(asserted inline at step 2)'))

    # 6. Threshold convergence
    chk6 = abs(threshold_bisect - threshold_analytical) < 1e-4
    checks.append(('6. Threshold-search converged + matches analytical', chk6,
                   f"|bisect−analytical|={abs(threshold_bisect-threshold_analytical):.2e}"))

    # 7. CHEERS 28 items
    try:
        assert_complete()
        chk7 = True
    except Exception as exc:
        chk7 = False
        print(f"  CHEERS assert_complete failed: {exc}")
    checks.append(('7. CHEERS checklist 28 items / schema OK', chk7, ''))

    # 8. All file outputs exist with non-zero size
    expected_files = [
        NON_HOME_MIX_CSV, OUT_BASE, OUT_CC, OUT_TORNADO, OUT_ARMS,
        OUT_THRESH, OUT_SCALE, OUT_PSA, OUT_CHEERS_MD,
        os.path.join(COST_DIR, 'figure_tornado.png'),
        os.path.join(COST_DIR, 'figure_tornado.pdf'),
        os.path.join(COST_DIR, 'figure_psa_scatter.png'),
        os.path.join(COST_DIR, 'figure_psa_scatter.pdf'),
        os.path.join(COST_DIR, 'figure_ceac.png'),
        os.path.join(COST_DIR, 'figure_ceac.pdf'),
        os.path.join(COST_DIR, 'decision_tree_diagram.png'),
        os.path.join(COST_DIR, 'decision_tree_diagram.pdf'),
    ]
    missing_files = [
        p for p in expected_files
        if not (os.path.exists(p) and os.path.getsize(p) > 0)
    ]
    chk8 = (len(missing_files) == 0)
    checks.append(('8. All file outputs exist + non-zero size', chk8,
                   f"missing={missing_files}" if missing_files else ''))

    for label, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {label}  ({detail})" if detail
              else f"  [{status}] {label}")

    all_pass = all(c[1] for c in checks)
    print()
    if all_pass:
        print("ALL VERIFICATION CHECKS PASSED")
    else:
        print("VERIFICATION FAILURES — see above")
    print("-" * 80)
    return all_pass


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------
def main():
    print("=" * 80)
    print("FORD-II - COST-EFFECTIVENESS DECISION TREE")
    print(f"Seed: {SEED}    PSA iters: {N_PSA:,}")
    print("=" * 80)

    params = load_and_audit_params()
    mix, _used_v3 = derive_non_home_mix(params)
    base_delta, _bed_days_pp = deterministic_base_case(params)
    weighted_perdiem_per_facday = cost_consequence(params, mix)
    _tornado_df = tornado_sa(params, base_delta)
    psa_stats = psa(params, base_delta)
    _arms_df = sensitivity_arms(params, mix, base_delta, weighted_perdiem_per_facday)
    threshold_analytical, threshold_bisect = threshold_analysis(params)
    _scale_df = scaling(params, base_delta)
    step_10_cheers_toy_diagram(params, mix)

    all_pass = verify_outputs(psa_stats, threshold_analytical, threshold_bisect)

    print()
    print("#" * 80)
    print("# COST-EFFECTIVENESS HEADLINE")
    print("#" * 80)
    print(f"#  Δcost per patient (deterministic)  = ${base_delta:.4f}")
    print(f"#  PSA mean                            = ${psa_stats['mean']:.4f}")
    print(f"#  PSA 95% CrI                         = "
          f"(${psa_stats['p25']:.4f}, ${psa_stats['p975']:.4f})")
    print(f"#  P(net savings > $0)                 = {psa_stats['p_savings']:.4f}")
    print(f"#  Threshold los_reduction (Δ=0)       = {threshold_analytical:.6f} d")
    print("#" * 80)

    if not all_pass:
        sys.exit(1)
    print("DONE.")


if __name__ == "__main__":
    main()
