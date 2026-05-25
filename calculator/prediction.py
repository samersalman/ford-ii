"""FORD-II scoring: pure functions, no Flask/web deps."""
from __future__ import annotations
import math
from typing import Dict
from config import WEIGHTS, RISK_GROUPS, RECALIBRATION

SCORE_MIN, SCORE_MAX = 0, 10


def features_from_form(form: Dict[str, str]) -> Dict[str, int]:
    """Translate raw form fields into the 16 binary predictor flags."""
    f = {k: 0 for k in WEIGHTS}  # all predictors default to 0
    # Age buckets (mutually exclusive)
    age = _to_float(form.get("age"))
    if age is not None:
        if 45 <= age <= 64: f["age_45_64"] = 1
        elif 65 <= age <= 74: f["age_65_74"] = 1
        elif age >= 75: f["age_75plus"] = 1
    # Continuous thresholds
    gcs = _to_float(form.get("gcs"))
    if gcs is not None and gcs < 9: f["gcs_severe"] = 1
    sbp = _to_float(form.get("sbp"))
    if sbp is not None and sbp < 90: f["sbp_hypotensive"] = 1
    temp = _to_float(form.get("temp_c"))
    if temp is not None and temp < 36: f["temp_hypothermic"] = 1
    bmi = _to_float(form.get("bmi"))
    if bmi is not None and bmi >= 40: f["bmi_obese_3"] = 1
    # Fracture site (one-hot, mutually exclusive)
    site_map = {
        "hip_femur": "frac_hip_femur",
        "lumbar":    "frac_lumbar",
        "leg":       "frac_leg",
        "cervical":  "frac_cervical",
        "humerus":   "frac_humerus",
    }
    site = (form.get("fracture_site") or "").strip().lower()
    if site in site_map: f[site_map[site]] = 1
    # Mechanism (one-hot, mutually exclusive; fall_struck_etc is reference)
    mech_map = {"mvc": "mech_mvc", "assault": "mech_assault", "other": "mech_other"}
    mech = (form.get("mechanism") or "").strip().lower()
    if mech in mech_map: f[mech_map[mech]] = 1
    # Transport (only trans_auto is in the model)
    transport = (form.get("transport") or "").strip().lower()
    if transport == "auto": f["trans_auto"] = 1
    return f


def integer_score(features: Dict[str, int]) -> int:
    """Sum integer points for active predictors, clipped to [0, 10]."""
    raw = sum(WEIGHTS[k] * int(features.get(k, 0)) for k in WEIGHTS)
    return max(SCORE_MIN, min(SCORE_MAX, raw))


def probability(score: int) -> float:
    """Logistic recalibration: prob of non-home discharge given integer score."""
    intercept = RECALIBRATION["intercept"]
    slope = RECALIBRATION["slope"]
    logit = intercept + slope * score
    return 1.0 / (1.0 + math.exp(-logit))


def risk_group(score: int) -> Dict[str, object]:
    """Look up which risk group an integer score falls into."""
    for g in RISK_GROUPS:
        lo, hi = g["score_lo"], g["score_hi"]
        if lo <= score <= hi:
            return g
    return RISK_GROUPS[-1]  # safety fallback


def score_patient(form: Dict[str, str]) -> Dict[str, object]:
    """End-to-end: form -> features -> score -> {score, prob, group}."""
    feats = features_from_form(form)
    s = integer_score(feats)
    return {
        "score": s,
        "probability_pct": round(probability(s) * 100, 1),
        "risk_group": risk_group(s),
        "active_features": [k for k, v in feats.items() if v == 1],
    }


def _to_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None
