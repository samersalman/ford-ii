"""Load FORD-II weights, risk groups, and recalibration constants from ../tables/."""
from pathlib import Path
import csv

_TABLES_DIR = Path(__file__).resolve().parent.parent / "tables"

def _load_weights() -> dict[str, int]:
    path = _TABLES_DIR / "ford_ii_weights.csv"
    with open(path, newline="") as f:
        return {row["Variable"]: int(row["Integer_points"]) for row in csv.DictReader(f)}

def _load_risk_groups() -> list[dict]:
    path = _TABLES_DIR / "risk_groups.csv"
    out = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            lo, hi = (int(x) for x in row["FORD_II_score_range"].split("-"))
            out.append({
                "label": row["Risk_group"],
                "score_lo": lo,
                "score_hi": hi,
                "score_range": row["FORD_II_score_range"],
                "event_rate_pct": float(row["FORD_II_event_rate_pct"]),
                "ci_lo_pct": float(row["FORD_II_ci_lo_pct"]),
                "ci_hi_pct": float(row["FORD_II_ci_hi_pct"]),
            })
    return sorted(out, key=lambda g: g["score_lo"])

def _load_recalibration() -> dict[str, float]:
    path = _TABLES_DIR / "ford_ii_score_to_prob.csv"
    with open(path, newline="") as f:
        row = next(csv.DictReader(f))
        return {"intercept": float(row["intercept"]), "slope": float(row["slope"])}

WEIGHTS = _load_weights()
RISK_GROUPS = _load_risk_groups()
RECALIBRATION = _load_recalibration()
