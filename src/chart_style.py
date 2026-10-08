"""
Shared "research report" visual style for the Step 9 analysis charts
(notebooks/02_analysis.ipynb).

This module is presentation code only - it holds colors, fonts and small
layout helpers so every chart in the notebook looks like it belongs to the
same report. It does not read, compute or touch any financial data.
"""

import textwrap

import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Figure size and resolution
# ---------------------------------------------------------------------------

FIGSIZE = (12, 7)  # 16:9-ish, the standard single-panel chart size
SAVE_DPI = 200

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

# Traffic-light status colors. The same three colors are reused for
# risk_band, altman_zone and beneish_zone, because "good / caution / bad"
# means the same thing regardless of which column it comes from.
STATUS_GOOD = "#0ca30c"
STATUS_CAUTION = "#fab219"
STATUS_BAD = "#d03b3b"
NEUTRAL_COLOR = "#c9c8c3"  # de-emphasised marks, e.g. a non-noteworthy group

TEXT_DARK = "#0b0b0b"  # titles, value labels, direct annotations
TEXT_GREY = "#52514e"  # subtitles, axis labels, source line
GRID_COLOR = "#e3e2de"

RISK_BAND_COLORS = {"Low": STATUS_GOOD, "Watch": STATUS_CAUTION, "High": STATUS_BAD}
ALTMAN_ZONE_COLORS = {"Safe": STATUS_GOOD, "Grey": STATUS_CAUTION, "Distress": STATUS_BAD}
BENEISH_ZONE_COLORS = {"Unlikely": STATUS_GOOD, "Watch": STATUS_CAUTION, "Likely": STATUS_BAD}

# Fixed per-company colors for the debt case study, so Torrent/Zydus/Piramal
# are always the same color wherever their debt line appears.
DEBT_LINE_COLORS = {
    "TORNTPHARM.NS": "#2a78d6",
    "ZYDUSLIFE.NS": "#eb6834",
    "PPLPHARMA.NS": "#1baf7a",
}


def apply_house_style():
    """
    Set the matplotlib rcParams every chart in the notebook shares: white
    background, no top/right border, consistent text colors and sizes.
    Call this once, before building any figure.
    """
    plt.rcParams.update({
        "figure.figsize": FIGSIZE,
        "figure.facecolor": "white",
        "savefig.dpi": SAVE_DPI,
        "savefig.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#444444",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.axisbelow": True,  # gridlines stay behind bars/dots
        "axes.labelsize": 10,
        "axes.labelcolor": TEXT_GREY,
        "xtick.color": TEXT_GREY,
        "ytick.color": TEXT_GREY,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "font.size": 10,
        "text.color": TEXT_DARK,
        "legend.frameon": False,
        "legend.fontsize": 10,
    })


def add_title(fig, headline, subtitle, x=0.02, y=0.96, wrap_width=92):
    """
    Add a left-aligned, bold report-style headline with a smaller grey
    subtitle underneath. Uses figure (not axes) coordinates, so it sits
    above every panel even in a multi-panel chart.

    Long headlines are wrapped to `wrap_width` characters (some of this
    report's headlines run over 100 characters, which would otherwise run
    off the side of the figure), and the subtitle shifts down to clear
    however many lines the headline wrapped to.
    """
    wrapped_headline = "\n".join(textwrap.wrap(headline, width=wrap_width))
    fig.text(x, y, wrapped_headline, fontsize=15, fontweight="bold", color=TEXT_DARK, ha="left", va="top")

    headline_lines = wrapped_headline.count("\n") + 1
    subtitle_y = y - 0.045 * headline_lines - 0.015
    wrapped_subtitle = "\n".join(textwrap.wrap(subtitle, width=wrap_width + 15))
    fig.text(x, subtitle_y, wrapped_subtitle, fontsize=11, color=TEXT_GREY, ha="left", va="top")


def add_source(fig, x=0.02, y=0.01):
    """Add the small grey footer every chart in the report shares."""
    fig.text(
        x, y,
        "Source: Yahoo Finance, Screener.in | FY2026 | Analysis: Annapurna Zutshi",
        fontsize=8, color=TEXT_GREY, ha="left", va="bottom",
    )


def add_callout(ax, xy, text, xytext, fontsize=9):
    """
    A short callout label with a thin leader line pointing at one specific
    data point, so the chart reader doesn't have to guess which dot or bar
    a note belongs to. Text is always dark grey, never the series color.
    """
    ax.annotate(
        text,
        xy=xy,
        xytext=xytext,
        textcoords="offset points",
        fontsize=fontsize,
        color=TEXT_DARK,
        arrowprops=dict(arrowstyle="-", color="#999999", linewidth=0.75, shrinkA=0, shrinkB=4),
        zorder=5,
    )


def save_chart(fig, path, pad_inches=0.15):
    """
    Save a figure at the house style's resolution and close it.

    pad_inches adds a small margin around the tight bounding box, so an
    axis label or the source line sitting right at the edge of the content
    never ends up flush against (or clipped by) the saved image's border.
    """
    fig.savefig(path, dpi=SAVE_DPI, bbox_inches="tight", pad_inches=pad_inches, facecolor="white")
    plt.close(fig)
