"""
02_build_consort_figure.py
==========================
Build the CONSORT-style flow diagram for the FORD-II validation
manuscript.

The figure shows the FORD-II primary cohort flow on NTDB 2019–2024
(7.33M → 1.95M analytic cohort).

Inputs (read-only)
------------------
- analysis/ford_ii_refit/data/consort_flow_ford2_v3.csv
    FORD-II flow: Raw PUF → Adults → Fracture-prefix → Disposition.

Outputs
-------
- figures/figure1_consort.pdf   (vector, 300 dpi)
- figures/figure1_consort.png   (raster, 300 dpi)

Run
---
    python analysis/manuscript/02_build_consort_figure.py

Notes
-----
- Per project conventions: matplotlib Agg backend is set BEFORE pyplot
  import, and figures are written at 300 dpi.
"""

from __future__ import annotations

# Required: set Agg backend BEFORE importing pyplot
import matplotlib
matplotlib.use("Agg")

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# ───────────────────────── Paths ───────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]

# FORD-II refit CONSORT flow (produced by analysis/ford_ii_refit/01_prepare.py).
V3_CONSORT = (
    REPO_ROOT
    / "analysis"
    / "ford_ii_refit"
    / "data"
    / "consort_flow_ford2_v3.csv"
)

OUT_DIR = REPO_ROOT / "figures"
OUT_PDF = OUT_DIR / "figure1_consort.pdf"
OUT_PNG = OUT_DIR / "figure1_consort.png"


# ─────────────────────── CSV loading helpers ───────────────────────────────
def _row_count(df: pd.DataFrame, step: int) -> int:
    """Return n_remaining for the given step number."""
    return int(df.loc[df["step"] == step, "n_remaining"].iloc[0])


def _row_drop(df: pd.DataFrame, step: int) -> int:
    """Return n_dropped for the given step number."""
    return int(df.loc[df["step"] == step, "n_dropped"].iloc[0])


def load_counts() -> dict:
    """Read the FORD-II CONSORT CSV and return a dict of named counts."""
    df_v3 = pd.read_csv(V3_CONSORT)

    counts = {
        # Main flow (FORD-II)
        "raw":           _row_count(df_v3, 0),  # 7,327,714
        "adults":        _row_count(df_v3, 1),  # 6,065,699
        "fracture":      _row_count(df_v3, 2),  # 2,195,426
        "analytic":      _row_count(df_v3, 3),  # 1,952,210
        # Drops
        "drop_pediatric":  _row_drop(df_v3, 1),  # 1,262,015
        "drop_nonfx":      _row_drop(df_v3, 2),  # 3,870,273
        "drop_dispo":      _row_drop(df_v3, 3),  # 243,216
    }
    return counts


# ───────────────────── Figure construction ─────────────────────────────────
PRIMARY_COLOR = "#cfe2f3"    # light blue (main flow boxes)
EXCLUSION_COLOR = "#fff2cc"  # light yellow (exclusion boxes)
EDGE_COLOR = "black"


def _box(ax, x: float, y: float, text: str, *,
         facecolor: str = PRIMARY_COLOR,
         edgecolor: str = EDGE_COLOR,
         fontsize: float = 10.5,
         fontweight: str = "bold",
         pad: float = 0.55) -> None:
    """Draw a rounded rectangle with centered text."""
    ax.text(
        x, y, text,
        ha="center", va="center",
        fontsize=fontsize, fontweight=fontweight,
        bbox=dict(boxstyle=f"round,pad={pad}",
                  facecolor=facecolor,
                  edgecolor=edgecolor,
                  linewidth=1.5),
    )


def _arrow(ax, x1: float, y1: float, x2: float, y2: float,
           lw: float = 1.8, color: str = "black") -> None:
    """Draw a simple arrow from (x1,y1) to (x2,y2)."""
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle="->", lw=lw, color=color),
    )


def build_figure(counts: dict) -> plt.Figure:
    """Render the CONSORT figure and return the Figure object."""
    fig, ax = plt.subplots(figsize=(11, 12))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 16)
    ax.axis("off")

    # ── Title bar ──────────────────────────────────────────────────────────
    ax.text(
        6, 15.4,
        "FORD-II Validation Cohort (NTDB 2019–2024)",
        ha="center", va="center",
        fontsize=15, fontweight="bold",
    )
    ax.text(
        6, 14.85,
        "CONSORT-style flow diagram",
        ha="center", va="center",
        fontsize=11, fontstyle="italic", color="#444",
    )

    # ── Main-flow boxes (left/center column at x = 4.5) ────────────────────
    main_x = 4.5
    main_boxes = [
        (13.5, f"NTDB 2019–2024 raw PUF\nN = {counts['raw']:,}"),
        (10.8, f"Adults (age ≥ 18)\nN = {counts['adults']:,}"),
        (8.1,  f"Primary ICD-10 fracture\n(S12–S92)\nN = {counts['fracture']:,}"),
        (5.4,  f"Analytic cohort\n(disposition in HOME/HHS/REHAB/\nSNF/LTCH/ICF)\nN = {counts['analytic']:,}"),
    ]
    for y, text in main_boxes:
        _box(ax, main_x, y, text, facecolor=PRIMARY_COLOR)

    # ── Exclusion boxes (right column at x = 9.0) ──────────────────────────
    excl_x = 9.0
    exclusions = [
        (12.15, f"Excluded: pediatric\n(age < 18 or missing)\nn = {counts['drop_pediatric']:,}"),
        (9.45,  f"Excluded: non-fracture\nprimary diagnosis\nn = {counts['drop_nonfx']:,}"),
        (6.75,  f"Excluded: non-clinical\ndisposition (death, AMA,\nhospice, etc.)\nn = {counts['drop_dispo']:,}"),
    ]
    for y, text in exclusions:
        _box(ax, excl_x, y, text,
             facecolor=EXCLUSION_COLOR, edgecolor="#888",
             fontsize=9.5, fontweight="normal", pad=0.45)

    # ── Vertical arrows down the main flow ─────────────────────────────────
    main_arrow_pairs = [
        (12.95, 11.40),  # raw → adults
        (10.25, 8.75),   # adults → fracture
        (7.45,  6.10),   # fracture → analytic
    ]
    for y1, y2 in main_arrow_pairs:
        _arrow(ax, main_x, y1, main_x, y2, lw=2.0)

    # ── Side arrows to exclusions ──────────────────────────────────────────
    side_arrow_ys = [12.15, 9.45, 6.75]
    for y in side_arrow_ys:
        _arrow(ax, main_x + 0.95, y, excl_x - 1.45, y,
               lw=1.4, color="#666")

    # ── Footer note ────────────────────────────────────────────────────────
    ax.text(
        6, 2.5,
        "Primary FORD-II analysis uses the full analytic cohort "
        f"(N = {counts['analytic']:,}).",
        ha="center", va="center",
        fontsize=9.5, fontstyle="italic", color="#333",
    )

    fig.tight_layout()
    return fig


# ────────────────────────── Main entry ────────────────────────────────────
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("FORD-II — Build CONSORT figure (figure1_consort)")
    print("=" * 72)
    print(f"  CONSORT flow CSV : {V3_CONSORT}")
    print(f"  Output dir       : {OUT_DIR}")
    print()

    counts = load_counts()

    # Print counts at each CONSORT level
    print("Counts at each CONSORT level:")
    print(f"  Raw NTDB 2019–2024 PUF rows         : {counts['raw']:>10,}")
    print(f"  Adults (age ≥ 18)                   : {counts['adults']:>10,} "
          f"(− {counts['drop_pediatric']:,} pediatric)")
    print(f"  Primary ICD-10 fracture (S12–S92)   : {counts['fracture']:>10,} "
          f"(− {counts['drop_nonfx']:,} non-fracture)")
    print(f"  Analytic cohort (eligible dispo)    : {counts['analytic']:>10,} "
          f"(− {counts['drop_dispo']:,} non-clinical)")
    print()

    fig = build_figure(counts)

    fig.savefig(OUT_PDF, dpi=300, bbox_inches="tight")
    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight")
    plt.close(fig)

    pdf_size = OUT_PDF.stat().st_size
    png_size = OUT_PNG.stat().st_size
    print("Wrote:")
    print(f"  {OUT_PDF}  ({pdf_size:,} bytes)")
    print(f"  {OUT_PNG}  ({png_size:,} bytes)")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
