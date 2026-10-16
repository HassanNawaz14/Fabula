"""Phase 2 - EDA: charts of the dataset for the Deliverable 1 report."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "data" / "processed" / "features.csv"
CHARTS = ROOT / "deliv1_docs" / "eda_charts"

DISCLOSURE_COLUMNS = ["n_volunteer", "n_if_asked", "n_hide", "n_lie"]


def chart_class_distribution(frame: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    type_counts = frame.filter(like="mystery_type_").sum()
    type_counts.index = type_counts.index.str.removeprefix("mystery_type_")
    axes[0].bar(type_counts.index, type_counts.values, color="#4C6EF5")
    axes[0].set_title("Mystery type distribution (n=300)")
    axes[0].set_ylabel("scenarios")
    tone_counts = frame.filter(like="tone_").sum()
    tone_counts.index = tone_counts.index.str.removeprefix("tone_")
    axes[1].bar(tone_counts.index, tone_counts.values, color="#F59E0B")
    axes[1].set_title("Tone distribution")
    fig.tight_layout()
    fig.savefig(CHARTS / "class_distribution.png", dpi=150)
    plt.close(fig)


def chart_disclosure_distribution(frame: pd.DataFrame) -> None:
    totals = frame[DISCLOSURE_COLUMNS].sum()
    labels = [column.removeprefix("n_") for column in DISCLOSURE_COLUMNS]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, totals.values, color=["#40C057", "#15AABF", "#FA5252", "#E64980"])
    ax.set_title("Disclosure policies across all NPC facts (n=300 scenarios)")
    ax.set_ylabel("fact count")
    fig.tight_layout()
    fig.savefig(CHARTS / "disclosure_distribution.png", dpi=150)
    plt.close(fig)


def chart_feature_correlations(frame: pd.DataFrame) -> None:
    columns = [
        "n_locations",
        "n_npcs",
        "n_clues",
        "n_facts",
        "n_secret_facts",
        "n_hide",
        "n_lie",
        "n_red_herrings",
        "window_minutes",
        "avg_facts_per_npc",
    ]
    corr = frame[columns].corr()
    fig, ax = plt.subplots(figsize=(8, 6.5))
    image = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(columns)), labels=columns, rotation=45, ha="right")
    ax.set_yticks(range(len(columns)), labels=columns)
    for row in range(len(columns)):
        for col in range(len(columns)):
            value = corr.values[row, col]
            ax.text(col, row, f"{value:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(image, ax=ax, shrink=0.8)
    ax.set_title("Feature correlations (300 generated skeletons)")
    fig.tight_layout()
    fig.savefig(CHARTS / "feature_correlations.png", dpi=150)
    plt.close(fig)


def main() -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(FEATURES)
    chart_class_distribution(frame)
    chart_disclosure_distribution(frame)
    chart_feature_correlations(frame)
    print(f"charts written to {CHARTS}")


if __name__ == "__main__":
    main()
