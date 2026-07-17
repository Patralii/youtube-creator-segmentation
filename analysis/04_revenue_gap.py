"""
04_revenue_gap.py — Quantifying the $2M Opportunity
=====================================================
Purpose:
    Measure how much more revenue High-Retention Niche Specialists would earn
    if monetised at a rate reflecting their retention quality, rather than the
    volume-based RPM that currently undervalues them.

Parity benchmark = mean RPM of Subscriber Giants.
    Why Giants?
        (a) Giants are who the algorithm currently optimises for.
        (b) Niche Specialists hold audience 40% longer than Giants.
            If completed attention is the product, they deserve parity.
    We don't use the platform average — that's dragged down by Dabblers
    and would understate the gap.

Gap per creator = max(0, views_90d × parity_rpm / 1000 − actual_revenue_90d)
Total gap       = sum across all 684 Niche Specialists.

Run after: 03_segmentation.py
Outputs:   outputs/revenue_gap/*.png
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR  = os.path.join(BASE_DIR, "outputs", "revenue_gap")
os.makedirs(OUT_DIR, exist_ok=True)

BG, SURFACE, TEXT, DIM = "#0f0f0f","#181818","#f1f1f1","#aaaaaa"
RED, GREEN, YELLOW, BLUE = "#ff0000","#2fd180","#ffd166","#3ea6ff"
PALETTE = [RED,BLUE,GREEN,YELLOW,"#c084fc","#fb923c","#38bdf8","#a3e635","#e879f9","#94a3b8"]

plt.rcParams.update({
    "figure.facecolor":BG,"axes.facecolor":SURFACE,"text.color":TEXT,
    "axes.labelcolor":DIM,"xtick.color":DIM,"ytick.color":DIM,
    "grid.color":"#303030","font.family":"monospace",
})


def load():
    path = os.path.join(DATA_DIR,"creator_segments.csv")
    if not os.path.exists(path):
        raise FileNotFoundError("creator_segments.csv not found — run 03_segmentation.py first.")
    return pd.read_csv(path)


def compute_gap(df):
    parity_rpm = df[df["archetype"]=="Subscriber Giants"]["rpm"].mean()
    print(f"Parity RPM benchmark (Giant mean): ${parity_rpm:.2f}")

    niche = df[df["archetype"]=="High-Retention Niche Specialists"].copy()
    niche["revenue_at_parity"] = niche["views_90d"] * parity_rpm / 1000
    niche["revenue_gap"] = (niche["revenue_at_parity"] - niche["revenue_90d"]).clip(lower=0)

    total_gap = niche["revenue_gap"].sum()
    print(f"\nNiche Specialist archetype — {len(niche):,} creators")
    print(f"  Avg actual revenue / creator (90d): ${niche['revenue_90d'].mean():>10,.0f}")
    print(f"  Avg parity revenue / creator (90d): ${niche['revenue_at_parity'].mean():>10,.0f}")
    print(f"  Avg gap / creator (90d):             ${niche['revenue_gap'].mean():>10,.0f}")
    print(f"\n  TOTAL revenue gap (90d): ${total_gap:,.0f}")
    print(f"  As % of platform revenue: "
          f"{total_gap / df['revenue_90d'].sum() * 100:.1f}%")
    return niche, parity_rpm


def gap_by_category(niche):
    """
    Break the gap down by niche category.
    Finance and Tech should rank highest — those are also where advertisers
    pay premium CPMs, making them natural first candidates for a pilot
    retention-indexed RPM tier.
    """
    cat = (
        niche.groupby("niche_category")
        .agg(n_creators=("creator_id","count"),
             current_rev=("revenue_90d","sum"),
             parity_rev=("revenue_at_parity","sum"),
             gap=("revenue_gap","sum"))
        .sort_values("gap", ascending=False)
    )
    cat["gap_pct"] = (cat["gap"] / cat["gap"].sum() * 100).round(1)
    print("\nGap by niche category:")
    print(cat.round(0).to_string())
    return cat


def plot_bridge(niche):
    """Stacked bar: current revenue + unrealised gap = parity target."""
    current = niche["revenue_90d"].sum()
    gap     = niche["revenue_gap"].sum()

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.barh(["Niche Specialists (90d)"], [current], color=GREEN,
            label=f"Current revenue  (${current:,.0f})", height=0.4)
    ax.barh(["Niche Specialists (90d)"], [gap], left=[current], color=RED,
            alpha=0.85, label=f"Unrealised gap  (${gap:,.0f})", height=0.4)
    ax.axvline(current+gap, color=YELLOW, ls="--", lw=1.8,
               label=f"Parity target  (${current+gap:,.0f})")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_:f"${x/1000:.0f}K"))
    ax.set_xlabel("90-day revenue (USD)")
    ax.set_title("Revenue Bridge: Current → Retention Parity", color=TEXT, fontsize=12)
    ax.legend(fontsize=9, framealpha=0.3)
    ax.grid(axis="x", alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR,"01_revenue_bridge.png"), dpi=150,
                bbox_inches="tight", facecolor=BG)
    plt.close()
    print("  Saved: 01_revenue_bridge.png")


def plot_category_gap(cat_gap):
    fig, ax = plt.subplots(figsize=(9, 5))
    cols = PALETTE[:len(cat_gap)]
    ax.barh(cat_gap.index[::-1], cat_gap["gap"][::-1], color=cols[::-1], height=0.6)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_:f"${x:,.0f}"))
    ax.set_xlabel("90-day revenue gap (USD)")
    ax.set_title("Revenue Gap by Niche Category — Niche Specialists Only",
                 color=TEXT, fontsize=11)
    ax.grid(axis="x", alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR,"02_gap_by_category.png"), dpi=150,
                bbox_inches="tight", facecolor=BG)
    plt.close()
    print("  Saved: 02_gap_by_category.png")


def plot_gap_distribution(niche):
    """
    Histogram of per-creator gaps.
    A roughly bell-shaped distribution (vs a long tail driven by a few outliers)
    signals the gap is broad-based — foreshadowing the validation check.
    """
    fig, ax = plt.subplots(figsize=(8,4))
    ax.hist(niche["revenue_gap"], bins=35, color=BLUE, alpha=0.85, edgecolor="none")
    ax.axvline(niche["revenue_gap"].median(), color=YELLOW, ls="--", lw=1.5,
               label=f"Median: ${niche['revenue_gap'].median():,.0f}")
    ax.axvline(niche["revenue_gap"].mean(), color=RED, ls="--", lw=1.5,
               label=f"Mean: ${niche['revenue_gap'].mean():,.0f}")
    ax.set_xlabel("Per-creator revenue gap (90d USD)")
    ax.set_ylabel("Number of creators")
    ax.set_title("Distribution of Per-Creator Revenue Gap", color=TEXT, fontsize=11)
    ax.legend(fontsize=9, framealpha=0.3)
    ax.grid(axis="y", alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR,"03_gap_distribution.png"), dpi=150,
                bbox_inches="tight", facecolor=BG)
    plt.close()
    print("  Saved: 03_gap_distribution.png")


if __name__ == "__main__":
    df    = load()
    niche, parity_rpm = compute_gap(df)
    cat   = gap_by_category(niche)
    plot_bridge(niche)
    plot_category_gap(cat)
    plot_gap_distribution(niche)
    print("\nRevenue gap analysis complete.")
