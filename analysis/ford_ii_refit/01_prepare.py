#!/usr/bin/env python
"""
01_prepare.py - Extract adult fracture cohort from compiled NTDB 2019-2024
for FORD-II (nationally derived non-home discharge prediction score).

Output:
    data/ford2_cohort.parquet         - cohort with retained columns + any_position_fracture flag
    data/consort_flow_ford2_v3.csv    - stepwise inclusion counts

Usage: python 01_prepare.py

Requires environment variable NTDB_DATA pointing to the compiled_NTDB_2019_2024
directory (the folder containing compiled_PUF_AY_2019_2024.csv,
ntdb_2019_2024_icd_diagnoses.csv, etc.).
"""

import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
# $NTDB_DATA should point to the compiled_NTDB_2019_2024 directory containing
# files like compiled_PUF_AY_2019_2024.csv and ntdb_2019_2024_icd_diagnoses.csv.
NTDB_ROOT = Path(os.environ["NTDB_DATA"])
PUF_FILE = NTDB_ROOT / "compiled_PUF_AY_2019_2024.csv"
DX_FILE = NTDB_ROOT / "ntdb_2019_2024_icd_diagnoses.csv"

SCRIPT_DIR = Path(__file__).resolve().parent       # .../analysis/ford_ii_refit/
REPO_ROOT = SCRIPT_DIR.parents[1]                  # public repo root
TABLES_DIR = REPO_ROOT / "tables"
FIGURES_DIR = REPO_ROOT / "figures"
DATA_DIR = SCRIPT_DIR / "data"                     # gitignored; intermediate parquet
DATA_DIR.mkdir(parents=True, exist_ok=True)
COHORT_FILE = DATA_DIR / "ford2_cohort.parquet"
CONSORT_FILE = DATA_DIR / "consort_flow_ford2_v3.csv"

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
SENTINELS = [-1, -2, -99]

FRACTURE_PREFIXES = {"S12", "S22", "S32", "S42", "S52", "S62", "S72", "S82", "S92"}

# Dispositions to EXCLUDE entirely (per FORD V8 logic)
DISP_EXCLUDE = {"D", "AMA", "HOSP", "HOSPICE", "POLICE", "PSYCH", "OTHER"}
# Dispositions to KEEP (primary cohort)
DISP_KEEP = {"HOME", "HHS", "REHAB", "SNF", "LTCH", "ICF"}

# Columns to load from the main PUF -- expanded for FORD-II candidate pool
# NOTE: VERIFICATION_LEVEL removed vs v2 (dropped from 2019-2024 compiled pool).
PUF_COLS = [
    "PUF_YEAR", "inc_key",
    "AGE_NUMBER", "SEX",
    "RACE", "ETHNICITY",                       # NEW for FORD-II
    "GCS2", "RR2", "SBP2", "P2",
    "TEMPS2", "OX2",                            # NEW for FORD-II
    "HEIGHTS2_CM", "WEIGHTS2_KG",
    "ICD10",
    "ISS",
    "TRANS", "PAYMENT_SOURCE",
    "CAUSE_E_CODES10",
    "DC_DISPOSITION_CODE",
    "TQIP_HC_BLOOD_4HR",
    "HOSPITAL_TRANSFER", "PREHOSPITAL_ARREST",  # NEW for FORD-II
    "TOX_TEST", "TOX", "ETOH",                  # NEW for FORD-II
]

# Numeric columns -- sentinel-cleaned to NaN before any comparison
NUMERIC_COLS = [
    "AGE_NUMBER", "GCS2", "RR2", "SBP2", "P2",
    "TEMPS2", "OX2",                            # NEW for FORD-II
    "HEIGHTS2_CM", "WEIGHTS2_KG", "ISS", "TQIP_HC_BLOOD_4HR",
    "ETOH",                                     # NEW for FORD-II
]

# String/categorical columns to uppercase+strip
# NOTE: VERIFICATION_LEVEL removed vs v2 (dropped from 2019-2024 compiled pool).
STRING_COLS = [
    "SEX", "RACE", "ETHNICITY",
    "ICD10", "TRANS", "PAYMENT_SOURCE",
    "CAUSE_E_CODES10", "DC_DISPOSITION_CODE",
    "HOSPITAL_TRANSFER", "PREHOSPITAL_ARREST",
    "TOX_TEST", "TOX",
]

# Dtype hints to reduce memory
PUF_DTYPES = {
    "PUF_YEAR": "Int16",
    "SEX": "object",
    "RACE": "object",
    "ETHNICITY": "object",
    "ICD10": "object",
    "TRANS": "object",
    "PAYMENT_SOURCE": "object",
    "CAUSE_E_CODES10": "object",
    "DC_DISPOSITION_CODE": "object",
    "HOSPITAL_TRANSFER": "object",
    "PREHOSPITAL_ARREST": "object",
    "TOX_TEST": "object",
    "TOX": "object",
}

# Map fracture prefix to column name for per-site flags
PREFIX_TO_COL = {
    "S12": "dx_frac_cervical",
    "S22": "dx_frac_thoracic",
    "S32": "dx_frac_lumbar",
    "S42": "dx_frac_humerus",
    "S52": "dx_frac_forearm",
    "S62": "dx_frac_hand",
    "S72": "dx_frac_hip_femur",
    "S82": "dx_frac_leg",
    "S92": "dx_frac_foot",
}

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
_t0 = time.time()


def banner(msg: str) -> None:
    elapsed = time.time() - _t0
    print(f"\n[{elapsed:7.1f}s] === {msg} ===", flush=True)


def clean_sentinel(s: pd.Series) -> pd.Series:
    """Coerce to numeric and mask NTDB sentinel codes (-1, -2, -99) to NaN."""
    s = pd.to_numeric(s, errors="coerce")
    return s.where(~s.isin(SENTINELS))


def clean_str(s: pd.Series) -> pd.Series:
    """Uppercase + strip; preserve NaN."""
    return s.astype("string").str.strip().str.upper()


# ============================================================================
# Step 0: Load main PUF (only needed columns)
# ============================================================================
banner("STEP 0: Loading compiled PUF (usecols-only)")
print(f"  file: {PUF_FILE}", flush=True)
df = pd.read_csv(
    PUF_FILE,
    usecols=PUF_COLS,
    dtype=PUF_DTYPES,
    low_memory=False,
)
print(f"  loaded shape: {df.shape}", flush=True)

consort_rows = []
n = len(df)
consort_rows.append({
    "step": 0, "criterion": "Raw PUF rows loaded",
    "n_remaining": n, "n_dropped": 0,
})

# Sentinel-clean numeric columns up-front (BEFORE any numeric comparison)
banner("Sentinel-cleaning numeric columns")
for col in NUMERIC_COLS:
    if col in df.columns:
        df[col] = clean_sentinel(df[col])

# Also strip/upper string columns up-front
banner("Cleaning string columns")
for col in STRING_COLS:
    if col in df.columns:
        df[col] = clean_str(df[col])

# ============================================================================
# Step 1: Adults only (AGE_NUMBER >= 18, non-missing)
# ============================================================================
banner("STEP 1: Restrict to adults (AGE_NUMBER >= 18)")
prev = len(df)
df = df[df["AGE_NUMBER"].notna() & (df["AGE_NUMBER"] >= 18)].copy()
n = len(df)
print(f"  kept {n:,} / dropped {prev - n:,}", flush=True)
consort_rows.append({
    "step": 1, "criterion": "Adults (AGE_NUMBER >= 18, non-missing, non-sentinel)",
    "n_remaining": n, "n_dropped": prev - n,
})

# ============================================================================
# Step 1b: Single-pass diagnoses-file scan
# ----------------------------------------------------------------------------
# The 2019-2024 compiled PUF ships with the ICD10 column entirely NaN (the
# 2019-2024 compile pipeline skipped the "primary diagnosis = first-row-per-
# inc_key" enrichment that build_ntdb_2017_2022.py applied at line 118). We
# replicate that enrichment here, AND in the same pass we gather the per-site
# and any-position fracture sets used by STEP 4/5 below. One I/O pass instead
# of three.
# ============================================================================
banner("STEP 1b: One-pass diagnoses scan (primary ICD10 enrichment + any/per-site fracture sets)")
print(f"  file: {DX_FILE}", flush=True)

first_icd_map: dict[tuple, str] = {}      # (PUF_YEAR, inc_key) -> first ICDDIAGNOSISCODE
keep_keys: set[tuple] = set()              # any-position S12-S92
site_keys: dict[str, set] = {pfx: set() for pfx in FRACTURE_PREFIXES}

chunk_iter = pd.read_csv(
    DX_FILE,
    usecols=["PUF_YEAR", "inc_key", "ICDDIAGNOSISCODE"],
    dtype={"PUF_YEAR": "Int16", "ICDDIAGNOSISCODE": "object"},
    chunksize=2_000_000,
    low_memory=False,
)
total_dx_rows = 0
for i, chunk in enumerate(chunk_iter):
    total_dx_rows += len(chunk)
    code = chunk["ICDDIAGNOSISCODE"].astype("string").str.strip().str.upper()
    code_nodot = code.str.replace(".", "", regex=False)
    prefix = code_nodot.str.slice(0, 3)

    # --- first-ICD per key (primary diagnosis surrogate) ---
    # A row wins over an earlier-chunk row ONLY if the key is not yet mapped,
    # so we keep the first occurrence across all chunks.
    for yr, key, raw_code in zip(chunk["PUF_YEAR"].tolist(),
                                  chunk["inc_key"].tolist(),
                                  code_nodot.tolist()):
        t = (yr, key)
        if t not in first_icd_map and isinstance(raw_code, str):
            first_icd_map[t] = raw_code

    # --- any-position fracture set ---
    frac_mask = prefix.isin(FRACTURE_PREFIXES)
    sub = chunk.loc[frac_mask, ["PUF_YEAR", "inc_key"]]
    keep_keys.update(zip(sub["PUF_YEAR"].tolist(), sub["inc_key"].tolist()))

    # --- per-site fracture sets ---
    for pfx in FRACTURE_PREFIXES:
        pfx_mask = prefix == pfx
        if pfx_mask.any():
            ssub = chunk.loc[pfx_mask, ["PUF_YEAR", "inc_key"]]
            site_keys[pfx].update(zip(ssub["PUF_YEAR"].tolist(), ssub["inc_key"].tolist()))

    print(f"    chunk {i}: {len(chunk):,} rows, first-ICD map = {len(first_icd_map):,}, "
          f"any-frac keys = {len(keep_keys):,}", flush=True)

print(f"  total dx rows scanned: {total_dx_rows:,}", flush=True)
print(f"  unique (PUF_YEAR, inc_key) in diagnoses file: {len(first_icd_map):,}", flush=True)
print(f"  unique (PUF_YEAR, inc_key) with any S12-S92: {len(keep_keys):,}", flush=True)

# Populate ICD10 column from first_icd_map
cohort_tuples = list(zip(df["PUF_YEAR"].tolist(), df["inc_key"].tolist()))
df["ICD10"] = pd.Series(
    [first_icd_map.get(t) for t in cohort_tuples],
    index=df.index,
    dtype="object",
)
print(f"  ICD10 populated: {df['ICD10'].notna().sum():,}/{len(df):,} "
      f"({df['ICD10'].notna().mean() * 100:.1f}%)", flush=True)

# ============================================================================
# Step 2: Primary fracture diagnosis S12-S92
# ============================================================================
banner("STEP 2: Primary ICD10 fracture diagnosis S12-S92")
df["fracture_prefix"] = df["ICD10"].astype("string").str.slice(0, 3)
prev = len(df)
df = df[df["fracture_prefix"].isin(FRACTURE_PREFIXES)].copy()
n = len(df)
print(f"  kept {n:,} / dropped {prev - n:,}", flush=True)
consort_rows.append({
    "step": 2, "criterion": "Primary ICD10 in S12-S92 (any fracture prefix)",
    "n_remaining": n, "n_dropped": prev - n,
})

# ============================================================================
# Step 3: Disposition filter (FORD V8 exclusion logic)
# ============================================================================
banner("STEP 3: Disposition filter (exclude D/AMA/HOSP/HOSPICE/POLICE/PSYCH/OTHER/missing)")
prev = len(df)
disp = df["DC_DISPOSITION_CODE"]
# Drop excluded codes AND missing
mask_exclude = disp.isna() | disp.isin(DISP_EXCLUDE)
df = df[~mask_exclude].copy()
# Keep only allowed dispositions
df = df[df["DC_DISPOSITION_CODE"].isin(DISP_KEEP)].copy()
n = len(df)
print(f"  kept {n:,} / dropped {prev - n:,}", flush=True)
consort_rows.append({
    "step": 3, "criterion": "DC_DISPOSITION in {HOME,HHS,REHAB,SNF,LTCH,ICF}",
    "n_remaining": n, "n_dropped": prev - n,
})

# ============================================================================
# Step 4: any_position_fracture flag — already computed in STEP 1b scan
# ============================================================================
banner("STEP 4: Applying any_position_fracture flag (from STEP 1b scan)")
cohort_tuples = list(zip(df["PUF_YEAR"].tolist(), df["inc_key"].tolist()))
df["any_position_fracture"] = np.fromiter(
    (1 if t in keep_keys else 0 for t in cohort_tuples),
    dtype="int8",
    count=len(cohort_tuples),
)
missing_flag = int((df["any_position_fracture"] == 0).sum())
if missing_flag > 0:
    print(f"  WARNING: {missing_flag:,} primary-fracture rows not matched in any-fracture set "
          f"(possible key mismatch)", flush=True)
else:
    print(f"  all {len(df):,} cohort rows flagged as any_position_fracture=1 (expected)", flush=True)

# ============================================================================
# Step 5: Per-site fracture flags — already computed in STEP 1b scan
# ============================================================================
banner("STEP 5: Applying per-site fracture flags (from STEP 1b scan)")

print("  per-site fracture key counts:", flush=True)

# Apply per-site flags to the cohort
for pfx in sorted(FRACTURE_PREFIXES):
    col_name = PREFIX_TO_COL[pfx]
    n_keys = len(site_keys[pfx])
    print(f"    {pfx} ({col_name}): {n_keys:,} patients in dx file", flush=True)
    tuples = list(zip(df["PUF_YEAR"].tolist(), df["inc_key"].tolist()))
    df[col_name] = np.fromiter(
        (1 if t in site_keys[pfx] else 0 for t in tuples),
        dtype="int8",
        count=len(tuples),
    )

# ============================================================================
# Step 6: Write outputs
# ============================================================================
banner("STEP 6: Writing outputs")
# Drop helper column
df = df.drop(columns=["fracture_prefix"])

df.to_parquet(COHORT_FILE, index=False)
print(f"  wrote {COHORT_FILE}  ({df.shape[0]:,} x {df.shape[1]})", flush=True)

consort_df = pd.DataFrame(consort_rows,
                          columns=["step", "criterion", "n_remaining", "n_dropped"])
consort_df.to_csv(CONSORT_FILE, index=False)
print(f"  wrote {CONSORT_FILE}", flush=True)

# ============================================================================
# Final summary
# ============================================================================
banner("DONE")
print(f"Final cohort: N={len(df):,}  "
      f"any_position_frac={df['any_position_fracture'].sum():,}")
print(f"Columns: {df.shape[1]}")
print(f"Per-site fracture prevalences (any dx position):")
for pfx in sorted(FRACTURE_PREFIXES):
    col_name = PREFIX_TO_COL[pfx]
    prev_pct = df[col_name].mean() * 100.0
    print(f"  {col_name}: {prev_pct:.1f}%")
