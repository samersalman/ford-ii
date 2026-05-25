#!/usr/bin/env python
"""
02_features.py — FORD-II (NTDB 2019–2024) feature engineering.

Engineer the 42-variable candidate pool + primary comparator scores
(FORD [V9 published, 15-var], GTOS-II, TRIAGES) for the national FORD-II
non-home discharge validation on NTDB 2019–2024.

  * FORD weights: load the frozen V9 published 15-row weights from
    TABLES_DIR / "ford_v1_weights.csv". This file is NOT shipped in the
    public repo; supply your own CSV with columns Variable / FORD_Points.
    Each row's `FORD_Points` integer is applied to the matching engineered
    binary column. trans_walk is LOCKED to 0 for all NTDB rows (NTDB has
    no 'WALK' transport category), so the negative walk credit never fires.
  * Primary comparators: FORD + GTOS-II + TRIAGES.
    ISS and GCS2 are retained as RAW columns (needed for GTOS-II, TRIAGES,
    and the supplementary extra_comparators.csv produced by 05),
    but are no longer emitted as standalone comparator score columns.
  * Insurance, ISS bands, tox, alcohol remain excluded from the primary
    42-var candidate pool but are retained as raw/engineered columns for
    sensitivity analysis in 05_sensitivity.py.

DOWNSTREAM_NOTES (column-naming contract for scripts 03–06):
  * Outcome column: `outcome_nonhome` (0/1 integer).
  * FORD comparator columns: `ford_original_score` and `FORD_score_raw`
      (both hold the same raw integer sum of the 15-row V9 weights applied
      to the engineered binaries; two names for downstream compatibility —
      03 references `ford_original_score`, 04 references `FORD_score_raw`).
      `FORD_0_10` is the Method-B clip to 0–10.
  * GTOS-II column: `GTOS_II`.
  * TRIAGES column: `triages_total`. `triages_age_pts`, `triages_gcs_pts`,
      `triages_rr_pts`, `triages_sbp_pts` are also emitted for QA.
  * ISS / GCS raw columns: `ISS`, `GCS2` (raw). Also emitted:
      `ISS_filled` = ISS coerced to numeric with NaN->0, and
      `GCS_REF` = (15 - GCS2) with NaN->0 (reference GCS for 03 diagnostics).
  * Insurance: `ins_medicare`, `ins_medicaid`, `ins_private`,
      `ins_charity`, `ins_other` retained as raw engineered columns
      (excluded from 42-var primary pool but used by 05).
  * `transfused_24h` retained for GTOS-II and sensitivity.

Input:  data/ford2_cohort.parquet   (from 01_prepare.py)
Output: data/ford2_features.parquet (all original cols + 42 candidates
        + comparators + outcome `outcome_nonhome`)

Usage: python 02_features.py

Requires environment variable NTDB_DATA pointing to the compiled_NTDB_2019_2024
directory.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ------------------------------------------------------------------ paths
SCRIPT_DIR = Path(__file__).resolve().parent       # .../analysis/ford_ii_refit/
REPO_ROOT = SCRIPT_DIR.parents[1]                  # public repo root
TABLES_DIR = REPO_ROOT / "tables"
FIGURES_DIR = REPO_ROOT / "figures"
DATA_DIR = SCRIPT_DIR / "data"                     # gitignored

COHORT_PARQUET = DATA_DIR / "ford2_cohort.parquet"
OUT_PARQUET = DATA_DIR / "ford2_features.parquet"

# $NTDB_DATA should point to the compiled_NTDB_2019_2024 directory.
NTDB_ROOT = Path(os.environ["NTDB_DATA"])
PROC_FILE = NTDB_ROOT / "ntdb_2019_2024_icd_procedures.csv"
PREEX_FILE = NTDB_ROOT / "ntdb_2019_2024_preexisting.csv"

# Original published FORD V9 weights (15 rows: Variable + FORD_Points columns).
# NOT shipped in the public repo. Supply your own CSV here, or override the
# path by setting FORD_V1_WEIGHTS to a local path before running.
FORD_V1_WEIGHTS = TABLES_DIR / "ford_v1_weights.csv"
FORD_WEIGHTS_CSV = FORD_V1_WEIGHTS  # alias retained for downstream readability

# ------------------------------------------------------------------ constants
SENTINELS = [-1, -2, -99]

# FORD-II v3 42-variable candidate pool (ED-admission bedside variables ONLY).
#
# Excluded by design from the primary candidate pool (but retained as raw
# columns for sensitivity in script 05):
#   - ISS bands (iss_9_15, iss_16_24, iss_25plus) — requires full injury coding
#   - Toxicology (tox_positive) — lab result
#   - Alcohol level (alcohol_positive) — lab result
#   - Insurance (ins_*) — not an ED-admission bedside variable
ALL_CANDIDATES = [
    # Age (ref: 18-44)            3
    "age_45_64",
    "age_65_74",
    "age_75plus",
    # Sex (ref: male)             1
    "female",
    # Race (ref: white)           4
    "race_black",
    "race_asian",
    "race_native",
    "race_other",
    # Ethnicity                   1
    "ethnicity_hispanic",
    # SBP (ref: normal)           2
    "sbp_hypotensive",
    "sbp_hypertensive",
    # HR (ref: normal)            2
    "hr_bradycardic",
    "hr_tachycardic",
    # RR (ref: normal)            2
    "rr_low",
    "rr_high",
    # GCS (ref: mild)             2
    "gcs_moderate",
    "gcs_severe",
    # O2 sat                      1
    "hypoxic",
    # Temperature                 2
    "temp_hypothermic",
    "temp_hyperthermic",
    # BMI (ref: normal)           4
    "bmi_underweight",
    "bmi_overweight",
    "bmi_obese_12",
    "bmi_obese_3",
    # Fracture site               9
    "frac_cervical",
    "frac_thoracic",
    "frac_lumbar",
    "frac_humerus",
    "frac_forearm",
    "frac_hand",
    "frac_hip_femur",
    "frac_leg",
    "frac_foot",
    # Mechanism (ref: fall)       3
    "mech_mvc",
    "mech_assault",
    "mech_other",
    # Transport (ref: ambulance)  4
    #   (trans_walk is ALWAYS 0 in NTDB and therefore not a candidate)
    "trans_auto",
    "trans_air",
    "trans_other_mode",
    # Hospital access             2
    "transfer_in",
    "prehospital_arrest",
]
assert len(ALL_CANDIDATES) == 41, f"expected 41 candidates (v2's 45 minus 4 insurance vars excluded from v3 primary pool), got {len(ALL_CANDIDATES)}"

# Insurance columns: excluded from primary pool; retained for script 05.
INSURANCE_VARS = [
    "ins_medicare",
    "ins_medicaid",
    "ins_private",
    "ins_charity",
    "ins_other",
]


# ------------------------------------------------------------------ helpers
_t0 = time.time()


def banner(msg: str) -> None:
    bar = "=" * 72
    elapsed = time.time() - _t0
    print(f"\n[{elapsed:7.1f}s] {bar}\n         {msg}\n         {bar}", flush=True)


def _clean_numeric(s: pd.Series) -> pd.Series:
    """Coerce to numeric and mask sentinel codes."""
    s = pd.to_numeric(s, errors="coerce")
    return s.where(~s.isin(SENTINELS))


# =====================================================================
# FORD V9 PUBLISHED WEIGHTS LOADER
# =====================================================================
def load_ford_v9_weights() -> dict[str, int]:
    """Load the frozen 15-var FORD integer weights from the V9 CSV.

    Returns a dict mapping engineered binary variable name -> integer points.
    """
    if not FORD_V1_WEIGHTS.exists():
        raise FileNotFoundError(
            f"Original FORD weights expected at {FORD_V1_WEIGHTS}. "
            "Place a two-column CSV (predictor, integer_points) with the original FORD weights "
            "there, or set FORD_V1_WEIGHTS to your local path."
        )
    wdf = pd.read_csv(FORD_V1_WEIGHTS)
    if "Variable" not in wdf.columns or "FORD_Points" not in wdf.columns:
        raise ValueError(
            f"FORD weights CSV missing required columns 'Variable' / 'FORD_Points': "
            f"found {list(wdf.columns)}"
        )
    weights = {
        str(row["Variable"]).strip(): int(row["FORD_Points"])
        for _, row in wdf.iterrows()
    }
    print(f"  loaded {len(weights)} FORD V9 weight rows from {FORD_V1_WEIGHTS.name}", flush=True)
    for k, v in weights.items():
        print(f"    {k:<25} {v:+d}", flush=True)
    return weights


# =====================================================================
# CANDIDATE VARIABLE ENGINEERING (42 primary + insurance [sensitivity])
# =====================================================================
def engineer_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Build the 41 FORD-II v3 candidate binaries + insurance + ISS bands."""
    df = df.copy()

    # ------------------------------------------------------------------
    # Age (ref: 18-44)
    # ------------------------------------------------------------------
    age = pd.to_numeric(df["AGE_NUMBER"], errors="coerce")
    df["age_45_64"] = ((age >= 45) & (age <= 64)).fillna(False).astype(int)
    df["age_65_74"] = ((age >= 65) & (age <= 74)).fillna(False).astype(int)
    df["age_75plus"] = (age >= 75).fillna(False).astype(int)

    # ------------------------------------------------------------------
    # Sex (ref: male)
    # ------------------------------------------------------------------
    sex = df["SEX"].astype(str).str.strip().str.upper()
    df["female"] = (sex == "F").astype(int)

    # ------------------------------------------------------------------
    # Race (ref: white)
    # NTDB codes: W, B, A, NAT, O, NOT
    # ------------------------------------------------------------------
    race = df["RACE"].astype(str).str.strip().str.upper()
    race_valid = (
        (race != "") & (race != "NAN") & (race != "<NA>") & (race != "NOT")
        & df["RACE"].notna()
    )
    is_white = (race == "W") | race.str.contains("WHITE", na=False)
    is_black = (race == "B") | race.str.contains("BLACK", na=False)
    is_asian = (race == "A") | race.str.contains("ASIAN", na=False)
    is_native = (race == "NAT") | race.str.contains("NATIVE", na=False) | race.str.contains("INDIAN", na=False)

    df["race_black"] = (is_black & race_valid).astype(int)
    df["race_asian"] = (is_asian & race_valid).astype(int)
    df["race_native"] = (is_native & race_valid).astype(int)
    df["race_other"] = (
        race_valid & ~is_white & ~is_black & ~is_asian & ~is_native
    ).astype(int)

    # ------------------------------------------------------------------
    # Ethnicity (NTDB codes: H, N, NOT)
    # ------------------------------------------------------------------
    eth = df["ETHNICITY"].astype(str).str.strip().str.upper()
    df["ethnicity_hispanic"] = (
        (eth == "H") | eth.str.contains("HISPANIC", na=False)
    ).astype(int)

    # ------------------------------------------------------------------
    # SBP (ref: normal 90-139)
    # ------------------------------------------------------------------
    sbp = pd.to_numeric(df["SBP2"], errors="coerce")
    df["sbp_hypotensive"] = (sbp < 90).fillna(False).astype(int)
    df["sbp_hypertensive"] = (sbp >= 140).fillna(False).astype(int)

    # ------------------------------------------------------------------
    # HR (ref: normal 60-99)
    # ------------------------------------------------------------------
    hr = pd.to_numeric(df["P2"], errors="coerce")
    df["hr_bradycardic"] = (hr < 60).fillna(False).astype(int)
    df["hr_tachycardic"] = (hr >= 100).fillna(False).astype(int)

    # ------------------------------------------------------------------
    # RR (ref: normal 12-20)
    # ------------------------------------------------------------------
    rr = pd.to_numeric(df["RR2"], errors="coerce")
    df["rr_low"] = (rr < 12).fillna(False).astype(int)
    df["rr_high"] = (rr > 20).fillna(False).astype(int)

    # ------------------------------------------------------------------
    # GCS (ref: mild 13-15)
    # ------------------------------------------------------------------
    gcs = pd.to_numeric(df["GCS2"], errors="coerce")
    df["gcs_moderate"] = ((gcs >= 9) & (gcs <= 12)).fillna(False).astype(int)
    df["gcs_severe"] = (gcs <= 8).fillna(False).astype(int)

    # ------------------------------------------------------------------
    # O2 saturation (OX2) — valid 0-100
    # ------------------------------------------------------------------
    ox = pd.to_numeric(df["OX2"], errors="coerce")
    ox = ox.where((ox >= 0) & (ox <= 100))
    df["hypoxic"] = (ox <= 92).fillna(False).astype(int)

    # ------------------------------------------------------------------
    # Temperature (Celsius, plausible 25-45)
    # ------------------------------------------------------------------
    temp = pd.to_numeric(df["TEMPS2"], errors="coerce")
    temp = temp.where((temp >= 25) & (temp <= 45))
    df["temp_hypothermic"] = (temp < 35).fillna(False).astype(int)
    df["temp_hyperthermic"] = (temp > 38).fillna(False).astype(int)

    # ------------------------------------------------------------------
    # BMI (ref: normal 18.5-25), plausible 10-80
    # ------------------------------------------------------------------
    h_cm = pd.to_numeric(df["HEIGHTS2_CM"], errors="coerce")
    w_kg = pd.to_numeric(df["WEIGHTS2_KG"], errors="coerce")
    with np.errstate(divide="ignore", invalid="ignore"):
        bmi = w_kg / ((h_cm / 100.0) ** 2)
    bmi = bmi.where((bmi >= 10) & (bmi <= 80))
    df["bmi_underweight"] = (bmi < 18.5).fillna(False).astype(int)
    df["bmi_overweight"] = ((bmi >= 25) & (bmi < 30)).fillna(False).astype(int)
    df["bmi_obese_12"] = ((bmi >= 30) & (bmi < 40)).fillna(False).astype(int)
    df["bmi_obese_3"] = (bmi >= 40).fillna(False).astype(int)

    # ------------------------------------------------------------------
    # ISS bands (retained for sensitivity in script 05; NOT in primary pool)
    # ------------------------------------------------------------------
    iss = pd.to_numeric(df["ISS"], errors="coerce")
    df["iss_9_15"] = ((iss >= 9) & (iss <= 15)).fillna(False).astype(int)
    df["iss_16_24"] = ((iss >= 16) & (iss <= 24)).fillna(False).astype(int)
    df["iss_25plus"] = (iss >= 25).fillna(False).astype(int)

    # ------------------------------------------------------------------
    # Fracture site (9 granular, from 01_ford2_prepare dx_frac_* columns)
    # ------------------------------------------------------------------
    frac_rename = {
        "dx_frac_cervical": "frac_cervical",
        "dx_frac_thoracic": "frac_thoracic",
        "dx_frac_lumbar": "frac_lumbar",
        "dx_frac_humerus": "frac_humerus",
        "dx_frac_forearm": "frac_forearm",
        "dx_frac_hand": "frac_hand",
        "dx_frac_hip_femur": "frac_hip_femur",
        "dx_frac_leg": "frac_leg",
        "dx_frac_foot": "frac_foot",
    }
    pfx_map = {
        "cervical": "S12", "thoracic": "S22", "lumbar": "S32",
        "humerus": "S42", "forearm": "S52", "hand": "S62",
        "hip_femur": "S72", "leg": "S82", "foot": "S92",
    }
    for src, dst in frac_rename.items():
        if src in df.columns:
            df[dst] = df[src].astype(int)
        else:
            print(
                f"  WARNING: {src} not found in cohort; deriving {dst} from "
                f"primary ICD10 only",
                flush=True,
            )
            icd = (
                df["ICD10"].astype(str).str.strip().str.upper()
                .str.replace(".", "", regex=False)
            )
            prefix = icd.str[:3]
            key = src.replace("dx_frac_", "")
            df[dst] = (prefix == pfx_map.get(key, "")).astype(int)

    # ------------------------------------------------------------------
    # Mechanism (ref: fall = W*)
    # ------------------------------------------------------------------
    ecode = df["CAUSE_E_CODES10"].astype(str).str.strip().str.upper()
    ecode_valid = (
        (ecode != "") & (ecode != "NAN") & (ecode != "<NA>")
        & df["CAUSE_E_CODES10"].notna()
    )
    is_fall = ecode.str.startswith("W")
    is_mvc = ecode.str.startswith("V")
    is_assault = ecode.str.startswith("X")

    df["mech_mvc"] = (is_mvc & ecode_valid).astype(int)
    df["mech_assault"] = (is_assault & ecode_valid).astype(int)
    df["mech_other"] = (
        ecode_valid & ~is_fall & ~is_mvc & ~is_assault
    ).astype(int)

    # ------------------------------------------------------------------
    # Transport (ref: ambulance = AMB). NTDB has NO 'WALK' category —
    # trans_walk is forced to 0 below (see engineer_ford_v9_predictors).
    # ------------------------------------------------------------------
    trans = df["TRANS"].astype(str).str.strip().str.upper()
    trans_valid = (
        (trans != "") & (trans != "NAN") & (trans != "<NA>")
        & df["TRANS"].notna()
    )

    df["trans_auto"] = (trans == "AUTO").astype(int)
    df["trans_air"] = (trans.isin(["AIR-H", "AIR-FW"])).astype(int)
    df["trans_other_mode"] = (
        trans_valid
        & ~trans.eq("AMB")
        & ~trans.eq("AUTO")
        & ~trans.isin(["AIR-H", "AIR-FW"])
    ).astype(int)

    # ------------------------------------------------------------------
    # Insurance (retained for sensitivity in script 05; NOT in primary pool).
    # NTDB codes: MCARE, MCARE-M, MCAID / MCAID-M, COMM / COMM-C, CHARITY,
    # SELF, AGENCY, PENDING, CVP, OTHER.
    # ------------------------------------------------------------------
    pay = df["PAYMENT_SOURCE"].astype(str).str.strip().str.upper()
    pay_valid = (
        (pay != "") & (pay != "NAN") & (pay != "<NA>")
        & df["PAYMENT_SOURCE"].notna()
    )
    df["ins_medicare"] = pay.str.contains("MCARE", na=False).astype(int)
    df["ins_medicaid"] = pay.str.contains("MCAID", na=False).astype(int)
    df["ins_private"] = pay.str.contains("COMM", na=False).astype(int)
    df["ins_charity"] = pay.str.contains("CHARITY", na=False).astype(int)
    df["ins_other"] = (
        pay_valid
        & ~pay.eq("SELF")
        & ~pay.str.contains("MCARE", na=False)
        & ~pay.str.contains("MCAID", na=False)
        & ~pay.str.contains("COMM", na=False)
        & ~pay.str.contains("CHARITY", na=False)
    ).astype(int)

    # ------------------------------------------------------------------
    # Hospital access
    # ------------------------------------------------------------------
    hosp_trans = df["HOSPITAL_TRANSFER"].astype(str).str.strip().str.upper()
    df["transfer_in"] = (
        hosp_trans.isin(["1", "YES", "TRUE", "Y"])
    ).astype(int)

    prehosp_arr = df["PREHOSPITAL_ARREST"].astype(str).str.strip().str.upper()
    df["prehospital_arrest"] = (
        prehosp_arr.isin(["1", "YES", "TRUE", "Y"])
    ).astype(int)

    # ------------------------------------------------------------------
    # Substance use (retained for sensitivity; NOT in primary pool)
    # ------------------------------------------------------------------
    etoh = pd.to_numeric(df["ETOH"], errors="coerce")
    etoh_pos = (etoh > 0).fillna(False)
    tox_str = df["TOX"].astype(str).str.strip().str.upper()
    tox_has_alcohol = tox_str.str.contains(
        "ALCOHOL|ETOH|ETHANOL", na=False, regex=True
    )
    df["alcohol_positive"] = (etoh_pos | tox_has_alcohol).astype(int)

    tox_test_str = df["TOX_TEST"].astype(str).str.strip().str.upper()
    tox_test_pos = tox_test_str.isin(
        ["YP", "1", "YES", "TRUE", "POSITIVE", "Y", "POS"]
    )
    tox_valid = (
        (tox_str != "") & (tox_str != "NAN") & (tox_str != "<NA>")
        & (tox_str != "NEG") & (tox_str != "NOT") & df["TOX"].notna()
    )
    tox_has_substance = tox_str.str.contains(
        "MARI|AMP|OPIA|COC|BENZ|METH|OXY|OTHER"
        "|COCAINE|MARIJUANA|THC|AMPHET|OPIAT|OPIOID|BARBIT|PCP|CANNABIS",
        na=False, regex=True,
    )
    df["tox_positive"] = (
        tox_test_pos | (tox_valid & tox_has_substance)
    ).astype(int)

    return df


# =====================================================================
# FORD V9 PREDICTORS (needed by the 15-var V9 score)
# =====================================================================
def engineer_ford_v9_predictors(df: pd.DataFrame) -> pd.DataFrame:
    """Build the V9-published FORD predictors not already in the 42-var pool.

    The V9 15-var table includes `axial_fracture`, `hip_femur`, and
    `trans_walk` — these are FORD-specific composites, not part of the 42
    primary candidates. We add them here so the FORD score can be applied.
    `trans_walk` is LOCKED to 0 (NTDB has no WALK category) — documented.
    """
    df = df.copy()

    icd = (
        df["ICD10"].astype(str).str.strip().str.upper()
        .str.replace(".", "", regex=False)
    )
    prefix = icd.str[:3]
    df["axial_fracture"] = prefix.isin(["S12", "S22", "S32"]).astype(int)
    df["hip_femur"] = (prefix == "S72").astype(int)

    # NTDB lacks a WALK transport category -> trans_walk always 0.
    # This means NTDB FORD scores never receive the -5 walk credit; document
    # as a limitation and a systematic upward shift in the NTDB score
    # distribution (trans_walk is FORD's largest negative weight).
    df["trans_walk"] = 0

    return df


# =====================================================================
# TRANSFUSION FALLBACK (procedure 30233N1 = packed RBC)
# =====================================================================
def load_transfusion_procedure_keys() -> pd.DataFrame:
    """Chunked scan of ICD procedures file for transfusion code 30233N1."""
    print(
        f"  Reading procedures file (filtering to 30233N1)\n    {PROC_FILE}",
        flush=True,
    )
    if not PROC_FILE.exists():
        print(
            "  WARNING: procedures file not found -- returning empty key set",
            flush=True,
        )
        return pd.DataFrame(
            columns=["PUF_YEAR", "inc_key", "has_transfusion_proc"]
        )

    proc_iter = pd.read_csv(
        PROC_FILE,
        usecols=["PUF_YEAR", "inc_key", "ICDPROCEDURECODE"],
        dtype={
            "PUF_YEAR": "Int16",
            "inc_key": "Int64",
            "ICDPROCEDURECODE": "string",
        },
        chunksize=2_000_000,
    )
    proc_keys: list[pd.DataFrame] = []
    total_rows = 0
    for i, chunk in enumerate(proc_iter, start=1):
        total_rows += len(chunk)
        code = (
            chunk["ICDPROCEDURECODE"].astype("string").str.strip().str.upper()
        )
        keep = chunk.loc[
            code == "30233N1", ["PUF_YEAR", "inc_key"]
        ].drop_duplicates()
        if len(keep):
            proc_keys.append(keep)
        if i % 5 == 0:
            print(
                f"    chunk {i}: scanned {total_rows:,} rows, "
                f"kept {sum(len(k) for k in proc_keys):,}",
                flush=True,
            )

    if not proc_keys:
        return pd.DataFrame(
            columns=["PUF_YEAR", "inc_key", "has_transfusion_proc"]
        )

    out = pd.concat(proc_keys, ignore_index=True).drop_duplicates()
    out["has_transfusion_proc"] = 1
    print(
        f"    total proc rows scanned: {total_rows:,}, "
        f"transfusion keys found: {len(out):,}",
        flush=True,
    )
    return out


# =====================================================================
# COMPARATOR SCORES — FORD (V9 15-var), GTOS-II, TRIAGES
# =====================================================================
def _triages_age_pts(age: float) -> float:
    if pd.isna(age):
        return np.nan
    if age < 55:
        return 0
    if age < 75:
        return 1
    return 2


def _triages_gcs_pts(g: float) -> float:
    if pd.isna(g):
        return np.nan
    g = int(g)
    if g >= 15:
        return 0
    if g == 14:
        return 1
    if g >= 12:
        return 2
    if g >= 8:
        return 3
    if g >= 5:
        return 4
    if g == 4:
        return 5
    return 6


def _triages_rr_pts(r: float) -> float:
    if pd.isna(r):
        return np.nan
    r = float(r)
    if 12 <= r <= 27:
        return 0
    if (4 <= r <= 11) or r >= 28:
        return 1
    if 0 <= r <= 3:
        return 2
    return np.nan


def _triages_sbp_pts(s: float) -> float:
    if pd.isna(s):
        return np.nan
    s = float(s)
    if 100 <= s <= 199:
        return 0
    if (80 <= s <= 99) or s >= 200:
        return 1
    if 50 <= s <= 79:
        return 2
    if 0 <= s <= 49:
        return 4
    return np.nan


def compute_comparators(
    df: pd.DataFrame,
    proc_keys: pd.DataFrame,
    ford_weights: dict[str, int],
) -> pd.DataFrame:
    """Compute FORD (V9 15-var) + GTOS-II + TRIAGES.

    Applies each V9 integer point to the engineered binary column of the
    same name. Missing columns are warned and treated as 0.
    """
    df = df.copy()

    # --- FORD score (V9 published 15-var integer weights) ---
    ford_score = pd.Series(0, index=df.index, dtype="float64")
    for pred, weight in ford_weights.items():
        if pred in df.columns:
            ford_score += df[pred].fillna(0).astype(float) * weight
        else:
            print(
                f"  WARNING: FORD V9 predictor '{pred}' not found -- using 0",
                flush=True,
            )
    # Raw integer sum (may go negative). Emit under BOTH v2-canonical names:
    # `ford_original_score` (read by script 03) and `FORD_score_raw` (read by
    # script 04). Both hold the same series.
    df["ford_original_score"] = ford_score.astype("int64")
    df["FORD_score_raw"] = df["ford_original_score"]
    # V9 Method B rescaling: truncate to 0-10 (v2-canonical name: FORD_0_10).
    df["FORD_0_10"] = df["FORD_score_raw"].clip(0, 10).astype("int64")

    # --- Transfusion: TQIP_HC_BLOOD_4HR > 0 OR ICD proc 30233N1 ---
    blood_4hr = pd.to_numeric(df["TQIP_HC_BLOOD_4HR"], errors="coerce")
    trans_from_blood = (blood_4hr > 0).fillna(False)

    if len(proc_keys):
        df = df.merge(
            proc_keys[["PUF_YEAR", "inc_key", "has_transfusion_proc"]],
            on=["PUF_YEAR", "inc_key"],
            how="left",
        )
    else:
        df["has_transfusion_proc"] = 0
    df["has_transfusion_proc"] = (
        df["has_transfusion_proc"].fillna(0).astype(int)
    )

    df["transfused_24h"] = (
        trans_from_blood | (df["has_transfusion_proc"] == 1)
    ).astype(int)

    # --- GTOS-II = AGE + 0.71 * ISS + 8.79 * transfused (V9 verbatim) ---
    age = pd.to_numeric(df["AGE_NUMBER"], errors="coerce")
    iss_numeric = pd.to_numeric(df["ISS"], errors="coerce").fillna(0)
    df["GTOS_II"] = (
        age.fillna(0) + 0.71 * iss_numeric + 8.79 * df["transfused_24h"]
    )

    # --- TRIAGES (V9 cut-points, lines 930-993) ---
    rr = pd.to_numeric(df["RR2"], errors="coerce")
    sbp = pd.to_numeric(df["SBP2"], errors="coerce")
    gcs = pd.to_numeric(df["GCS2"], errors="coerce")
    df["triages_age_pts"] = age.apply(_triages_age_pts)
    df["triages_gcs_pts"] = gcs.apply(_triages_gcs_pts)
    df["triages_rr_pts"] = rr.apply(_triages_rr_pts)
    df["triages_sbp_pts"] = sbp.apply(_triages_sbp_pts)
    df["triages_total"] = df[
        [
            "triages_age_pts",
            "triages_gcs_pts",
            "triages_rr_pts",
            "triages_sbp_pts",
        ]
    ].sum(axis=1, min_count=4)

    # --- ISS_filled / GCS_REF (downstream diagnostic comparators) ---
    df["ISS_filled"] = pd.to_numeric(df["ISS"], errors="coerce").fillna(0)
    df["GCS_REF"] = (
        15 - pd.to_numeric(df["GCS2"], errors="coerce")
    ).fillna(0)

    return df


# =====================================================================
# OUTCOME
# =====================================================================
def compute_outcome(df: pd.DataFrame) -> pd.DataFrame:
    """outcome_nonhome = 1 if non-home (REHAB/SNF/LTCH/ICF), 0 if home (HOME/HHS), drop other."""
    dc = df["DC_DISPOSITION_CODE"].astype(str).str.strip().str.upper()
    home_codes = {"HOME", "HHS"}
    nonhome_codes = {"REHAB", "SNF", "LTCH", "ICF"}
    outcome = np.where(
        dc.isin(nonhome_codes), 1,
        np.where(dc.isin(home_codes), 0, np.nan),
    )
    df = df.assign(outcome_nonhome=outcome)
    n_before = len(df)
    df = df[df["outcome_nonhome"].notna()].copy()
    n_after = len(df)
    if n_before != n_after:
        print(
            f"  dropped {n_before - n_after:,} rows with unmapped disposition",
            flush=True,
        )
    df["outcome_nonhome"] = df["outcome_nonhome"].astype(int)
    return df


# =====================================================================
# DIAGNOSTIC SUMMARY
# =====================================================================
def print_diagnostic_summary(df: pd.DataFrame) -> None:
    n = len(df)
    rate = float(df["outcome_nonhome"].mean() * 100.0)
    print(f"\n  Total N:              {n:,}", flush=True)
    print(f"  Outcome rate (outcome_nonhome=1):   {rate:.2f}%", flush=True)
    print(f"  Candidate variables:  {len(ALL_CANDIDATES)}", flush=True)

    print(f"\n  {'Variable':<25} {'N (=1)':>12} {'Prevalence':>12}", flush=True)
    print(f"  {'-'*25} {'-'*12} {'-'*12}", flush=True)

    warn_zero, warn_full = [], []
    for var in ALL_CANDIDATES:
        if var not in df.columns:
            print(f"  {var:<25} {'MISSING':>12} {'N/A':>12}", flush=True)
            continue
        n_pos = int(df[var].sum())
        prev = float(df[var].mean() * 100.0)
        print(f"  {var:<25} {n_pos:>12,} {prev:>11.2f}%", flush=True)
        if prev == 0.0:
            warn_zero.append(var)
        if prev == 100.0:
            warn_full.append(var)

    if warn_zero:
        print(
            f"\n  WARNING: Variables with 0% prevalence: {', '.join(warn_zero)}",
            flush=True,
        )
    if warn_full:
        print(
            f"\n  WARNING: Variables with 100% prevalence: {', '.join(warn_full)}",
            flush=True,
        )

    # Comparator score summaries
    print("\n  Comparator score summaries:", flush=True)
    for score_col in ["ford_original_score", "FORD_score_raw", "FORD_0_10", "GTOS_II", "triages_total"]:
        if score_col in df.columns:
            vals = df[score_col].dropna()
            print(
                f"    {score_col}: mean={vals.mean():.2f}, "
                f"median={vals.median():.1f}, "
                f"range=[{vals.min():.0f}, {vals.max():.0f}], "
                f"N_valid={len(vals):,}",
                flush=True,
            )

    # Raw ISS / GCS2 summaries (retained for GTOS-II, TRIAGES, supplementary)
    print("\n  Raw comparator inputs (retained; not primary comparators):",
          flush=True)
    for raw_col in ["ISS", "GCS2"]:
        if raw_col in df.columns:
            vals = pd.to_numeric(df[raw_col], errors="coerce").dropna()
            print(
                f"    {raw_col}: mean={vals.mean():.2f}, "
                f"median={vals.median():.1f}, "
                f"range=[{vals.min():.0f}, {vals.max():.0f}], "
                f"N_valid={len(vals):,}",
                flush=True,
            )


# =====================================================================
# MAIN
# =====================================================================
def main() -> None:
    t_start = time.time()

    banner("STAGE 0: Load FORD V9 published weights")
    ford_weights = load_ford_v9_weights()

    banner("STAGE 1: Load cohort parquet")
    t0 = time.time()
    df = pd.read_parquet(COHORT_PARQUET)
    print(
        f"  loaded {len(df):,} rows, {df.shape[1]} columns "
        f"(elapsed {time.time() - t0:.1f}s)",
        flush=True,
    )

    banner("STAGE 2: Engineer 41 FORD-II v3 candidate variables")
    t0 = time.time()
    df = engineer_candidates(df)
    print(f"  elapsed {time.time() - t0:.1f}s", flush=True)

    banner("STAGE 3: Engineer FORD V9 composite predictors (axial_fracture, hip_femur, trans_walk=0)")
    t0 = time.time()
    df = engineer_ford_v9_predictors(df)
    print(f"  elapsed {time.time() - t0:.1f}s", flush=True)

    banner("STAGE 4: Load transfusion procedure keys (chunked scan)")
    t0 = time.time()
    proc_keys = load_transfusion_procedure_keys()
    print(
        f"  {len(proc_keys):,} unique transfusion keys "
        f"(elapsed {time.time() - t0:.1f}s)",
        flush=True,
    )

    banner("STAGE 5: Compute comparator scores (FORD V9 / GTOS-II / TRIAGES)")
    t0 = time.time()
    df = compute_comparators(df, proc_keys, ford_weights)
    print(f"  elapsed {time.time() - t0:.1f}s", flush=True)

    banner("STAGE 6: Compute outcome outcome_nonhome (non-home discharge)")
    t0 = time.time()
    df = compute_outcome(df)
    print(
        f"  N after outcome mapping: {len(df):,}  "
        f"(elapsed {time.time() - t0:.1f}s)",
        flush=True,
    )

    banner("STAGE 7: Write features parquet")
    t0 = time.time()
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)
    print(
        f"  wrote {OUT_PARQUET}  ({len(df):,} rows, {df.shape[1]} cols)  "
        f"elapsed {time.time() - t0:.1f}s",
        flush=True,
    )

    banner("DIAGNOSTIC SUMMARY")
    print_diagnostic_summary(df)

    elapsed_total = time.time() - t_start
    print(f"\n  Total elapsed: {elapsed_total:.1f}s", flush=True)


if __name__ == "__main__":
    main()
