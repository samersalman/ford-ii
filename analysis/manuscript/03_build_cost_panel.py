"""
FORD-II cost-effectiveness composite figure.

Composes the tornado diagram and PSA scatter PNGs into a single 2-panel
figure for the manuscript.

Inputs (read-only):
    figures/cost_analysis/figure_tornado.png
    figures/cost_analysis/figure_psa_scatter.png

Outputs:
    figures/figure5_cost_panel.png  (300 dpi raster)
    figures/figure5_cost_panel.pdf  (300 dpi vector wrapper)

Layout: 1x2 side-by-side. Both source PNGs are landscape (tornado 1.85:1,
PSA scatter 1.23:1) so a horizontal arrangement preserves readability of the
tornado bar labels without forcing extreme vertical compression on the PSA
cloud. Each panel is shown via imshow with axis('off').
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # set backend BEFORE pyplot import

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from pathlib import Path


# Resolve paths relative to this script so it works from any cwd.
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
COST_DIR = REPO_ROOT / "figures" / "cost_analysis"
OUT_DIR = REPO_ROOT / "figures"

TORNADO_PNG = COST_DIR / "figure_tornado.png"
PSA_PNG = COST_DIR / "figure_psa_scatter.png"

OUT_PNG = OUT_DIR / "figure5_cost_panel.png"
OUT_PDF = OUT_DIR / "figure5_cost_panel.pdf"

SUPTITLE = "Cost-effectiveness analysis (10,000-iteration PSA, hospital perspective)"


def build_panel() -> None:
    # Verify inputs exist.
    for p in (TORNADO_PNG, PSA_PNG):
        if not p.is_file():
            raise FileNotFoundError(f"Input figure missing: {p}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    tornado_img = mpimg.imread(str(TORNADO_PNG))
    psa_img = mpimg.imread(str(PSA_PNG))

    # 1x2 layout. Figure size chosen so each panel has roughly square-ish
    # canvas room (~7 in wide each) plus margin for suptitle.
    fig, (ax_a, ax_b) = plt.subplots(
        nrows=1,
        ncols=2,
        figsize=(14.0, 6.5),
        gridspec_kw={"width_ratios": [1.0, 1.0], "wspace": 0.05},
    )

    ax_a.imshow(tornado_img)
    ax_a.set_axis_off()
    ax_a.set_title("A) Tornado diagram", loc="left", fontsize=13, fontweight="bold")

    ax_b.imshow(psa_img)
    ax_b.set_axis_off()
    ax_b.set_title("B) PSA scatter", loc="left", fontsize=13, fontweight="bold")

    fig.suptitle(SUPTITLE, fontsize=14, fontweight="bold", y=0.98)

    # imshow axes with axis('off') aren't compatible with tight_layout;
    # use explicit subplots_adjust to leave room for the suptitle.
    fig.subplots_adjust(left=0.02, right=0.98, top=0.90, bottom=0.02, wspace=0.05)

    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_PDF, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # Report.
    png_kb = OUT_PNG.stat().st_size / 1024
    pdf_kb = OUT_PDF.stat().st_size / 1024
    print(f"Wrote {OUT_PNG} ({png_kb:,.1f} KB)")
    print(f"Wrote {OUT_PDF} ({pdf_kb:,.1f} KB)")


if __name__ == "__main__":
    build_panel()
