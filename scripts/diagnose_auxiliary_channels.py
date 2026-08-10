#!/usr/bin/env python3
"""Diagnose POL DCxx auxiliary inputs against POL ACxx SEEG candidates."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from seeg_detector.analysis.auxiliary_channels import (
    DC_LSB_STORED_UNIT,
    compute_auxiliary_channel_metrics,
    summarize_auxiliary_channels,
)
from seeg_detector.data import load_record


def _plot_comparison(data_root: Path, metrics, output_stem: Path) -> None:
    """Build a quantitative grid supporting DC-input exclusion.

    Figure contract: DC01--DC16 are fixed, coarsely quantized auxiliary inputs,
    whereas ACxx is a continuous SEEG-like electrode family. Panels a and b
    show representative raw morphology; panel c validates the distinction over
    every available record-channel observation. Stored amplitude units remain
    unspecified, except that DC steps match the documented 366.3-uV LSB.
    """

    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
        }
    )
    record = load_record(data_root / "test_000489.npz")
    lookup = {str(name): index for index, name in enumerate(record.channel_ids.tolist())}
    figure, axes = plt.subplots(1, 3, figsize=(7.2, 3.25), gridspec_kw={"width_ratios": [1, 1, 1.15]})

    dc_channels = [f"POL DC{i:02d}" for i in range(1, 5)]
    dc_samples = int(round(0.1 * record.sampling_rate))
    dc_time = np.arange(dc_samples) / record.sampling_rate * 1000.0
    for offset, channel_id in enumerate(dc_channels):
        signal = record.valid_signal[lookup[channel_id], :dc_samples] / DC_LSB_STORED_UNIT
        axes[0].step(dc_time, signal + offset * 3.0, where="post", linewidth=0.7, color="#D8792B")
    axes[0].set_yticks(np.arange(len(dc_channels)) * 3.0)
    axes[0].set_yticklabels([item.replace("POL ", "") for item in dc_channels])
    axes[0].set_xlabel("Time (ms)")
    axes[0].set_ylabel("ADC levels + offset")
    axes[0].set_title("a  DC inputs: discrete steps", loc="left", fontweight="bold")

    ac_channels = [f"POL AC{i}" for i in range(1, 5)]
    ac_samples = int(round(2.0 * record.sampling_rate))
    ac_time = np.arange(ac_samples) / record.sampling_rate
    for offset, channel_id in enumerate(ac_channels):
        signal = record.valid_signal[lookup[channel_id], :ac_samples].astype(np.float64)
        scale = max(float(signal.std()), np.finfo(np.float64).eps)
        axes[1].plot(ac_time, (signal - signal.mean()) / scale + offset * 5.0, linewidth=0.55, color="#2463A8")
    axes[1].set_yticks(np.arange(len(ac_channels)) * 5.0)
    axes[1].set_yticklabels([item.replace("POL ", "") for item in ac_channels])
    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylabel("Standardized amplitude + offset")
    axes[1].set_title("b  AC contacts: continuous signals", loc="left", fontweight="bold")

    palette = {"auxiliary_dc": "#D8792B", "seeg_ac_candidate": "#2463A8"}
    labels = {"auxiliary_dc": "DC01–DC16", "seeg_ac_candidate": "AC contacts"}
    for role, group in metrics.groupby("channel_role"):
        axes[2].scatter(
            group["unique_value_count"],
            group["transition_rate"],
            s=11,
            alpha=0.55,
            color=palette[role],
            edgecolors="none",
            label=f"{labels[role]} (n={len(group)})",
        )
    axes[2].set_xscale("log")
    axes[2].set_xlabel("Unique values in 60 s (log scale)")
    axes[2].set_ylabel("Sample-to-sample transition rate")
    axes[2].set_title("c  Dataset-wide validation", loc="left", fontweight="bold")
    axes[2].legend(fontsize=6, loc="lower right")

    figure.suptitle("DCxx is an auxiliary-input block, not an SEEG electrode family", x=0.07, ha="left", fontsize=10)
    figure.text(
        0.07,
        0.91,
        "24 records; raw values retained; AC traces standardized only for display",
        fontsize=6.5,
        color="#4C5663",
    )
    figure.subplots_adjust(left=0.10, right=0.99, top=0.80, bottom=0.18, wspace=0.42)
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_stem.with_suffix(".png"), dpi=300, bbox_inches="tight", facecolor="white")
    figure.savefig(output_stem.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    figure.savefig(output_stem.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("Dataset/sampleData"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/auxiliary_channels"))
    parser.add_argument(
        "--figure", type=Path, default=Path("assets/figures/dc_ac_channel_diagnostic")
    )
    args = parser.parse_args()

    metrics = compute_auxiliary_channel_metrics(args.data_root)
    summary = summarize_auxiliary_channels(metrics)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(args.output_dir / "channel_metrics.csv", index=False)
    summary.to_csv(args.output_dir / "role_summary.csv", index=False)
    _plot_comparison(args.data_root, metrics, args.figure)
    print(summary.to_string(index=False))
    print(f"Wrote metrics to {args.output_dir}")
    print(f"Wrote figure to {args.figure}.{{png,svg,pdf}}")


if __name__ == "__main__":
    main()
