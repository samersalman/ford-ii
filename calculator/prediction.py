"""FORD-II scoring and presentation payload helpers."""
from __future__ import annotations

import math
from typing import Any

from config import RISK_GROUPS, RECALIBRATION, WEIGHTS

SCORE_MIN, SCORE_MAX = 0, 10

PREDICTOR_METADATA = {
    "age_45_64": {
        "label": "Age 45-64",
        "condition": "Age 45-64 years",
        "group": "Demographics",
        "order": 10,
    },
    "age_65_74": {
        "label": "Age 65-74",
        "condition": "Age 65-74 years",
        "group": "Demographics",
        "order": 20,
    },
    "age_75plus": {
        "label": "Age 75+",
        "condition": "Age 75 years or older",
        "group": "Demographics",
        "order": 30,
    },
    "gcs_severe": {
        "label": "Severe GCS",
        "condition": "GCS below 9",
        "group": "Presentation / vitals",
        "order": 40,
    },
    "sbp_hypotensive": {
        "label": "Hypotension",
        "condition": "Systolic blood pressure below 90 mmHg",
        "group": "Presentation / vitals",
        "order": 50,
    },
    "temp_hypothermic": {
        "label": "Hypothermia",
        "condition": "Temperature below 36 C",
        "group": "Presentation / vitals",
        "order": 60,
    },
    "bmi_obese_3": {
        "label": "BMI 40+",
        "condition": "BMI 40 kg/m2 or higher",
        "group": "Presentation / vitals",
        "order": 70,
    },
    "frac_hip_femur": {
        "label": "Hip/femur fracture",
        "condition": "Primary fracture site is hip or femur",
        "group": "Fracture characteristics",
        "order": 80,
    },
    "frac_lumbar": {
        "label": "Lumbar spine fracture",
        "condition": "Primary fracture site is lumbar spine",
        "group": "Fracture characteristics",
        "order": 90,
    },
    "frac_leg": {
        "label": "Leg fracture",
        "condition": "Primary fracture site is leg (tibia/fibula)",
        "group": "Fracture characteristics",
        "order": 100,
    },
    "frac_cervical": {
        "label": "Cervical spine fracture",
        "condition": "Primary fracture site is cervical spine",
        "group": "Fracture characteristics",
        "order": 110,
    },
    "frac_humerus": {
        "label": "Humerus fracture",
        "condition": "Primary fracture site is humerus",
        "group": "Fracture characteristics",
        "order": 120,
    },
    "mech_mvc": {
        "label": "Motor vehicle crash",
        "condition": "Mechanism is motor vehicle crash",
        "group": "Mechanism / transport",
        "order": 130,
    },
    "mech_assault": {
        "label": "Assault",
        "condition": "Mechanism is assault",
        "group": "Mechanism / transport",
        "order": 140,
    },
    "mech_other": {
        "label": "Other mechanism",
        "condition": "Mechanism is other",
        "group": "Mechanism / transport",
        "order": 150,
    },
    "trans_auto": {
        "label": "Private auto transport",
        "condition": "Arrival by private auto",
        "group": "Mechanism / transport",
        "order": 160,
    },
}


def features_from_form(form: dict[str, Any]) -> dict[str, int]:
    """Translate raw form fields into the 16 binary predictor flags."""
    features = {key: 0 for key in WEIGHTS}

    age = _to_float(form.get("age"))
    if age is not None:
        if 45 <= age <= 64:
            features["age_45_64"] = 1
        elif 65 <= age <= 74:
            features["age_65_74"] = 1
        elif age >= 75:
            features["age_75plus"] = 1

    gcs = _to_float(form.get("gcs"))
    if gcs is not None and gcs < 9:
        features["gcs_severe"] = 1

    sbp = _to_float(form.get("sbp"))
    if sbp is not None and sbp < 90:
        features["sbp_hypotensive"] = 1

    temp = _to_float(form.get("temp_c"))
    if temp is not None and temp < 36:
        features["temp_hypothermic"] = 1

    bmi = _to_float(form.get("bmi"))
    if bmi is not None and bmi >= 40:
        features["bmi_obese_3"] = 1

    site_map = {
        "hip_femur": "frac_hip_femur",
        "lumbar": "frac_lumbar",
        "leg": "frac_leg",
        "cervical": "frac_cervical",
        "humerus": "frac_humerus",
    }
    site = _normalized_value(form.get("fracture_site"))
    if site in site_map:
        features[site_map[site]] = 1

    mech_map = {
        "mvc": "mech_mvc",
        "assault": "mech_assault",
        "other": "mech_other",
    }
    mechanism = _normalized_value(form.get("mechanism"))
    if mechanism in mech_map:
        features[mech_map[mechanism]] = 1

    if _normalized_value(form.get("transport")) == "auto":
        features["trans_auto"] = 1

    return features


def raw_score(features: dict[str, int]) -> int:
    """Unclipped integer-point total."""
    return sum(WEIGHTS[key] * int(features.get(key, 0)) for key in WEIGHTS)


def integer_score(features: dict[str, int]) -> int:
    """Clipped FORD-II integer score."""
    return _clip_score(raw_score(features))


def probability(score: int) -> float:
    """Probability of non-home discharge from the clipped score."""
    intercept = RECALIBRATION["intercept"]
    slope = RECALIBRATION["slope"]
    logit = intercept + slope * score
    return 1.0 / (1.0 + math.exp(-logit))


def risk_group(score: int) -> dict[str, object]:
    """Look up the risk-group row for a clipped score."""
    for group in RISK_GROUPS:
        if group["score_lo"] <= score <= group["score_hi"]:
            return group
    return RISK_GROUPS[-1]


def score_patient(form: dict[str, Any]) -> dict[str, object]:
    """Return the UI-facing FORD-II result payload."""
    features = features_from_form(form)
    raw = raw_score(features)
    score = _clip_score(raw)
    groups = risk_group(score)
    contributions = _build_contributions(features)

    return {
        "score": score,
        "raw_score": raw,
        "probability_pct": round(probability(score) * 100, 1),
        "risk_group": groups,
        "active_contributions": [item for item in contributions if item["met"]],
        "all_contributions": contributions,
        "active_features": [key for key, value in features.items() if value == 1],
        "score_was_clipped": raw != score,
        "score_limits": {"min": SCORE_MIN, "max": SCORE_MAX},
    }


def _build_contributions(features: dict[str, int]) -> list[dict[str, object]]:
    items = []
    for key, points in WEIGHTS.items():
        meta = PREDICTOR_METADATA[key]
        met = bool(features.get(key, 0))
        items.append(
            {
                "key": key,
                "label": meta["label"],
                "condition": meta["condition"],
                "group": meta["group"],
                "met": met,
                "points": points,
                "signed_points": _format_signed(points),
                "display_text": f"{meta['label']}: {_format_signed(points)}",
                "order": meta["order"],
            }
        )

    return sorted(items, key=lambda item: item["order"])


def _clip_score(score: int) -> int:
    return max(SCORE_MIN, min(SCORE_MAX, score))


def _format_signed(value: int) -> str:
    return f"{value:+d}"


def _normalized_value(value: Any) -> str:
    return str(value or "").strip().lower()


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
