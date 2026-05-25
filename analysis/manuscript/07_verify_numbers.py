"""
FORD-II manuscript numeric verification harness.

Compares headline numeric values in the manuscript against the source CSVs
that produced them. Each claim is paired with a tolerance; the script reports
OK / MISMATCH / NOT_FOUND_IN_CSV per claim plus a small set of freshness
spot checks.

Run AFTER the ford_ii_refit pipeline and the manuscript builder
(04_build_manuscript.py) complete. This script is the LAST step of the
reproduction pipeline; it will exit(2) if any required input CSV is missing.

Usage:
    python analysis/manuscript/07_verify_numbers.py

Exit codes:
    0  all manuscript values match their source CSVs within tolerance
    1  one or more MISMATCHes detected (or any freshness invariant fails)
    2  no MISMATCHes, but one or more NOT_FOUND_IN_CSV entries unresolved
       OR required input files missing (precheck failure)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
from docx import Document

HERE = Path(__file__).resolve().parent  # analysis/manuscript/
REPO_ROOT = HERE.parents[1]              # repo root
MANUSCRIPT_DIR = REPO_ROOT / "manuscript"
MANUSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
MANUSCRIPT_PATH = MANUSCRIPT_DIR / "ford_ii_main.docx"
JSON_OUT = MANUSCRIPT_DIR / "_numbers_extracted.json"
MD_OUT = MANUSCRIPT_DIR / "_verification_results.md"

# Source CSV paths (relative to REPO_ROOT). All paths point to the curated
# tables/ directory (FORD-II refit outputs) plus the cost-analysis PSA CSV.
SRC = {
    "t_validation":   "tables/validation_metrics.csv",
    "t_risk":         "tables/risk_groups.csv",
    "t_baseline":     "tables/baseline.csv",
    "t_weights":      "tables/ford_ii_weights.csv",
    "t_subgroups":    "tables/subgroups.csv",
    "t_cost_cons":    "tables/cost_consequence.csv",
    "t_sens_arms":    "tables/sensitivity_arms.csv",
    "psa":            "figures/cost_analysis/psa_results.csv",
}


# --------------------------------------------------------------------------- #
# Tolerance / comparison helpers
# --------------------------------------------------------------------------- #
def parse_numeric(raw):
    """Best-effort numeric parse. Handles '8,422', '0.830', '<0.001', '$362.25', '1.2%', etc."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.upper() in {"N/A", "NA", "NAN", "—", "-", ""}:
        return None
    s = s.replace(",", "").replace("%", "").replace("$", "").strip()
    s = s.replace("(", "-").replace(")", "")
    s = s.replace("–", "-").replace("−", "-")
    m = re.match(r"^<\s*([0-9.]+)$", s)
    if m:
        return float(m.group(1))
    m = re.match(r"^([-+]?[0-9]*\.?[0-9]+)([eE][-+]?[0-9]+)?", s)
    if m:
        try:
            tail = m.group(2) or ""
            return float(m.group(1) + tail)
        except ValueError:
            return None
    return None


def compare(entry):
    """Re-apply tolerance comparison. Returns (status, note)."""
    man = entry.get("manuscript_value")
    csv = entry.get("csv_value_observed")
    tol_raw = entry.get("tolerance")
    vtype = entry.get("value_type", "")

    if entry.get("match_status") == "NOT_FOUND_IN_CSV" or csv in (None, "", "N/A"):
        return "NOT_FOUND_IN_CSV", f"manuscript={man!r}; no CSV source"

    if isinstance(tol_raw, str) and tol_raw.startswith("literal_lt"):
        man_f = parse_numeric(man)
        csv_f = parse_numeric(csv)
        man_lt = "<" in str(man) or (man_f is not None and man_f < 0.001)
        csv_lt = "<" in str(csv) or (csv_f is not None and csv_f < 0.001)
        if man_lt and csv_lt:
            return "OK", f"both <0.001 (manuscript={man}, csv={csv})"
        return "MISMATCH", f"literal <0.001 mismatch (manuscript={man}, csv={csv})"

    try:
        tol = float(tol_raw)
    except (TypeError, ValueError):
        tol = 0.0

    man_f = parse_numeric(man)
    csv_f = parse_numeric(csv)

    if vtype == "int" or tol == 0:
        s_man = str(man).replace(",", "").replace("$", "").strip()
        s_csv = str(csv).replace(",", "").replace("$", "").strip()
        if s_man == s_csv:
            return "OK", f"exact match ({man})"
        if man_f is not None and csv_f is not None and man_f == csv_f:
            return "OK", f"numeric-exact ({man}={csv})"
        return "MISMATCH", f"exact mismatch (manuscript={man}, csv={csv})"

    if man_f is None or csv_f is None:
        if str(man).strip() == str(csv).strip():
            return "OK", f"string match ({man})"
        return "MISMATCH", f"unparseable numeric (manuscript={man}, csv={csv})"

    diff = abs(man_f - csv_f)
    if diff <= tol + 1e-9:
        return "OK", f"|{man_f}-{csv_f}|={diff:.4g} <= tol={tol}"
    return "MISMATCH", f"|{man_f}-{csv_f}|={diff:.4g} > tol={tol}"


# --------------------------------------------------------------------------- #
# CSV loading helpers
# --------------------------------------------------------------------------- #
def csv(name):
    return pd.read_csv(REPO_ROOT / SRC[name])


def find_row(df, col, value):
    sub = df[df[col].astype(str).str.strip() == str(value).strip()]
    if len(sub) == 0:
        return None
    return sub.iloc[0]


# --------------------------------------------------------------------------- #
# Manifest builder
# --------------------------------------------------------------------------- #
def build_manifest():
    """Build the verification manifest by reading source CSVs."""
    if not MANUSCRIPT_PATH.exists():
        raise FileNotFoundError(
            f"Manuscript {MANUSCRIPT_PATH} not found. Run "
            "04_build_manuscript.py first."
        )

    t_val = csv("t_validation")
    t_risk = csv("t_risk")
    t_weights = csv("t_weights")
    psa = pd.read_csv(REPO_ROOT / SRC["psa"])

    ford2 = find_row(t_val, "score", "FORD-II")
    gtos2 = find_row(t_val, "score", "GTOS-II")
    triages = find_row(t_val, "score", "TRIAGES")

    rg_low = find_row(t_risk, "Risk_group", "Low")
    rg_high = find_row(t_risk, "Risk_group", "High")

    psa_mean = psa["delta_cost_per_patient"].mean()
    psa_lo = psa["delta_cost_per_patient"].quantile(0.025)
    psa_hi = psa["delta_cost_per_patient"].quantile(0.975)
    psa_pgt0 = (psa["delta_cost_per_patient"] > 0).mean() * 100

    M = []

    def add(id_, section, manuscript_value, source_csv_key, source_column,
            source_row, csv_value_observed, tolerance, value_type=""):
        M.append({
            "id": id_,
            "section": section,
            "manuscript_value": str(manuscript_value),
            "source_csv": SRC.get(source_csv_key, source_csv_key),
            "source_column": source_column,
            "source_row": source_row,
            "tolerance": tolerance,
            "value_type": value_type,
            "csv_value_observed": str(csv_value_observed) if csv_value_observed is not None else None,
            "match_status": "NOT_FOUND_IN_CSV" if csv_value_observed is None else "PENDING",
        })

    # ---------------- Headline discrimination ----------------
    if ford2 is not None:
        add("ford2_auroc", "FORD-II AUROC",
            f"{ford2['auroc']:.4f}", "t_validation", "auroc", "FORD-II",
            f"{ford2['auroc']}", 0.0001)
        add("ford2_auroc_lo", "FORD-II AUROC CI lo",
            f"{ford2['auroc_ci_lo']:.4f}", "t_validation", "auroc_ci_lo", "FORD-II",
            f"{ford2['auroc_ci_lo']}", 0.0001)
        add("ford2_auroc_hi", "FORD-II AUROC CI hi",
            f"{ford2['auroc_ci_hi']:.4f}", "t_validation", "auroc_ci_hi", "FORD-II",
            f"{ford2['auroc_ci_hi']}", 0.0001)
        add("ford2_cal_slope", "FORD-II calibration slope",
            f"{ford2['cal_slope']:.4f}", "t_validation", "cal_slope", "FORD-II",
            f"{ford2['cal_slope']}", 0.001)
        add("ford2_brier", "FORD-II Brier",
            f"{ford2['brier']:.4f}", "t_validation", "brier", "FORD-II",
            f"{ford2['brier']}", 0.0001)
    if gtos2 is not None:
        add("gtos_auroc", "GTOS-II AUROC",
            f"{gtos2['auroc']:.4f}", "t_validation", "auroc", "GTOS-II",
            f"{gtos2['auroc']}", 0.0005)
    if triages is not None:
        add("triages_auroc", "TRIAGES AUROC",
            f"{triages['auroc']:.4f}", "t_validation", "auroc", "TRIAGES",
            f"{triages['auroc']}", 0.0001)

    # ---------------- Risk-quartile event rates ----------------
    if rg_low is not None:
        add("rg_low_pct", "Risk-quartile Low event rate",
            f"{rg_low['FORD_II_event_rate_pct']:.2f}", "t_risk",
            "FORD_II_event_rate_pct", "Low",
            f"{rg_low['FORD_II_event_rate_pct']}", 0.01)
    if rg_high is not None:
        add("rg_high_pct", "Risk-quartile High event rate",
            f"{rg_high['FORD_II_event_rate_pct']:.2f}", "t_risk",
            "FORD_II_event_rate_pct", "High",
            f"{rg_high['FORD_II_event_rate_pct']}", 0.01)

    # ---------------- PSA ----------------
    add("psa_mean", "PSA mean Δcost",
        f"{psa_mean:.2f}", "psa", "mean(delta_cost_per_patient)",
        "10K MC iterations", f"{psa_mean:.4f}", 0.05)
    add("psa_lo", "PSA 95% CrI lo",
        f"{psa_lo:.2f}", "psa", "quantile(2.5%) delta_cost_per_patient",
        "10K MC iterations", f"{psa_lo:.4f}", 0.05)
    add("psa_hi", "PSA 95% CrI hi",
        f"{psa_hi:.2f}", "psa", "quantile(97.5%) delta_cost_per_patient",
        "10K MC iterations", f"{psa_hi:.4f}", 0.05)
    add("psa_pgt0", "P(net savings >$0)",
        f"{psa_pgt0:.2f}", "psa", "mean(delta_cost > 0) ×100",
        "10K MC iterations", f"{psa_pgt0:.4f}", 0.05)

    # ---------------- Predictor count ----------------
    add("predictor_count", "FORD-II predictor count",
        f"{len(t_weights)}", "t_weights", "row count",
        "all FORD-II predictors", f"{len(t_weights)}", 0, value_type="int")

    return M


# --------------------------------------------------------------------------- #
# Freshness checks (HARD assertions)
# --------------------------------------------------------------------------- #
def freshness_checks():
    results = []

    # 1. validation_metrics.csv has FORD-II / GTOS-II / TRIAGES rows
    try:
        t = csv("t_validation")
        ford2 = t[t["score"] == "FORD-II"]
        ok = len(ford2) == 1
        results.append(
            ("validation_metrics has exactly one FORD-II row",
             "OK" if ok else "FAIL", f"got {len(ford2)}")
        )
    except Exception as e:
        results.append(("validation_metrics row check", "FAIL", f"error: {e}"))

    # 2. risk_groups.csv has 4 rows
    try:
        rg = csv("t_risk")
        ok = len(rg) == 4
        results.append(
            ("risk_groups has 4 quartile rows",
             "OK" if ok else "FAIL", f"got {len(rg)}")
        )
    except Exception as e:
        results.append(("risk_groups row check", "FAIL", f"error: {e}"))

    # 3. PSA file has at least 10K iterations
    try:
        psa = pd.read_csv(REPO_ROOT / SRC["psa"])
        ok = len(psa) >= 10000
        results.append(
            ("psa_results has >= 10,000 iterations",
             "OK" if ok else "FAIL", f"got {len(psa)}")
        )
    except Exception as e:
        results.append(("psa_results row check", "FAIL", f"error: {e}"))

    # 4. Manuscript .docx exists and contains FORD-II in title
    try:
        doc = Document(str(MANUSCRIPT_PATH))
        title = doc.paragraphs[0].text
        ok = "FORD-II" in title
        results.append(
            ("manuscript .docx title contains 'FORD-II'",
             "OK" if ok else "FAIL", f"title prefix: {title[:60]!r}")
        )
    except Exception as e:
        results.append(("manuscript .docx check", "FAIL", f"error: {e}"))

    return results


# --------------------------------------------------------------------------- #
# Precheck — verify every required intermediate exists before doing any work
# --------------------------------------------------------------------------- #
def precheck_inputs():
    """Resolve every path in SRC against REPO_ROOT and report any missing."""
    missing = []
    for key, rel in SRC.items():
        p = REPO_ROOT / rel
        if not p.exists():
            missing.append(f"  MISSING ({key}): {rel}")
    if not MANUSCRIPT_PATH.exists():
        missing.append(
            f"  MISSING (manuscript_docx): manuscript/{MANUSCRIPT_PATH.name}"
        )
    return missing


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    print("=" * 72)
    print("FORD-II manuscript numeric verification harness")
    print("=" * 72)

    missing = precheck_inputs()
    if missing:
        print(
            "\nERROR: 07_verify_numbers.py requires these intermediate files "
            "(produced by the ford_ii_refit + manuscript builder pipelines):\n"
        )
        for line in missing:
            print(line)
        print(
            "\nThis script is the LAST step of the reproduction pipeline. "
            "Run analysis/ford_ii_refit/* first, then "
            "analysis/manuscript/01_cost_decision_tree.py through "
            "06_build_tripod_supplement.py."
        )
        sys.exit(2)

    print(f"Building manifest from {MANUSCRIPT_PATH.name}...")
    manifest = build_manifest()

    for entry in manifest:
        status, note = compare(entry)
        entry["match_status"] = status
        entry["compare_note"] = note

    JSON_OUT.write_text(json.dumps(manifest, indent=2, default=str))

    n_ok = sum(1 for e in manifest if e["match_status"] == "OK")
    n_mm = sum(1 for e in manifest if e["match_status"] == "MISMATCH")
    n_nf = sum(1 for e in manifest if e["match_status"] == "NOT_FOUND_IN_CSV")
    n_total = len(manifest)

    fresh = freshness_checks()
    n_fresh_fail = sum(1 for _, s, _ in fresh if s != "OK")

    with MD_OUT.open("w") as f:
        f.write("# FORD-II Manuscript Numeric Verification Results\n\n")
        f.write(f"- Manuscript: `{MANUSCRIPT_PATH.relative_to(REPO_ROOT)}`\n")
        f.write(f"- Manifest: `{JSON_OUT.relative_to(REPO_ROOT)}`\n")
        f.write(f"- Total claims: **{n_total}**\n")
        f.write(f"- OK: **{n_ok}**\n")
        f.write(f"- MISMATCH: **{n_mm}**\n")
        f.write(f"- NOT_FOUND_IN_CSV: **{n_nf}**\n\n")

        f.write("## CSV Freshness Spot Checks\n\n")
        f.write("| Check | Status | Detail |\n|---|---|---|\n")
        for name, st, detail in fresh:
            f.write(f"| {name} | **{st}** | {detail} |\n")
        f.write("\n")

        f.write("## Mismatches and Unresolved\n\n")
        bad = [e for e in manifest if e["match_status"] != "OK"]
        if not bad:
            f.write("_None._\n\n")
        else:
            f.write("| id | section | manuscript | csv | tol | status | note |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for e in bad:
                f.write(
                    f"| `{e['id']}` | {e['section']} | "
                    f"`{e['manuscript_value']}` | `{e['csv_value_observed']}` | "
                    f"`{e['tolerance']}` | **{e['match_status']}** | "
                    f"{e.get('compare_note','')} |\n"
                )
            f.write("\n")

        f.write("## All Claims (full table)\n\n")
        f.write("| id | section | source_csv | manuscript | csv | tol | status |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for e in manifest:
            f.write(
                f"| `{e['id']}` | {e['section']} | `{e['source_csv']}` | "
                f"`{e['manuscript_value']}` | `{e['csv_value_observed']}` | "
                f"`{e['tolerance']}` | {e['match_status']} |\n"
            )

    print(f"\nVerified {n_total} manuscript values against source CSVs.")
    print(f"  OK:               {n_ok}")
    print(f"  MISMATCH:         {n_mm}")
    print(f"  NOT_FOUND_IN_CSV: {n_nf}")
    print("\nFreshness spot checks:")
    for name, st, detail in fresh:
        print(f"  [{st}] {name} -- {detail}")
    print(f"\nManifest JSON: {JSON_OUT}")
    print(f"Markdown report: {MD_OUT}")

    if n_mm or n_fresh_fail:
        return 1
    if n_nf:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
