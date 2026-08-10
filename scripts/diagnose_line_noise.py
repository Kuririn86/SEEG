#!/usr/bin/env python3
"""Profile 50 Hz line noise and generate reproducible diagnostic artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import welch

from seeg_detector.analysis.line_noise import (
    apply_zero_phase_notches,
    compute_line_noise_metrics,
    summarize_line_noise,
)
from seeg_detector.data import load_record


def _plot_diagnostics(
    metrics: pd.DataFrame,
    data_root: Path,
    output_stem: Path,
    sample_id: str = "train_000211",
) -> None:
    """Create a quantitative-grid figure for distribution and filter response.

    Figure contract: line-noise burden depends on electrode/contact identity,
    not the Ref/POL prefix alone. Panel a compares electrode codes; panel b
    shows contaminated Ref and POL examples plus a clean comparator before and
    after narrow zero-phase notch filtering. Stored units remain unspecified.
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
    figure, axes = plt.subplots(1, 2, figsize=(7.2, 3.5), gridspec_kw={"width_ratios": [1.0, 1.35]})

    code_summary = (
        metrics.groupby("electrode_code")
        .agg(channels=("channel_id", "size"), median=("line50_excess_db", "median"))
        .query("channels >= 10")
        .sort_values("median", ascending=False)
        .head(12)
        .sort_values("median")
    )
    colors = ["#D8792B" if value > 10.0 else "#2463A8" for value in code_summary["median"]]
    axes[0].barh(code_summary.index, code_summary["median"], color=colors, edgecolor="#263442", linewidth=0.4)
    axes[0].axvline(10.0, color="#263442", linestyle=(0, (3, 2)), linewidth=0.8)
    axes[0].set_xlabel("Median 50 Hz peak excess (dB)")
    axes[0].set_title("a  Electrode-code comparison", loc="left", fontweight="bold")
    axes[0].text(10.3, 0.2, "candidate threshold", fontsize=6, color="#4C5663")

    record = load_record(data_root / f"{sample_id}.npz")
    channels = ["EEG PO10-Ref", "POL PO11", "EEG F1-Ref"]
    channel_lookup = {str(name): index for index, name in enumerate(record.channel_ids.tolist())}
    palette = {"EEG PO10-Ref": "#D8792B", "POL PO11": "#B24C63", "EEG F1-Ref": "#2463A8"}
    for channel_id in channels:
        index = channel_lookup[channel_id]
        raw = record.valid_signal[index].astype(np.float64)
        cleaned = apply_zero_phase_notches(raw, record.sampling_rate)
        frequencies, raw_psd = welch(raw, fs=record.sampling_rate, nperseg=4000, noverlap=2000)
        _, clean_psd = welch(cleaned, fs=record.sampling_rate, nperseg=4000, noverlap=2000)
        keep = (frequencies >= 35.0) & (frequencies <= 115.0)
        axes[1].plot(
            frequencies[keep],
            10.0 * np.log10(np.maximum(raw_psd[keep], np.finfo(np.float64).tiny)),
            color=palette[channel_id],
            linewidth=0.8,
            label=f"{channel_id} raw",
        )
        axes[1].plot(
            frequencies[keep],
            10.0 * np.log10(np.maximum(clean_psd[keep], np.finfo(np.float64).tiny)),
            color=palette[channel_id],
            linewidth=0.7,
            linestyle=(0, (3, 2)),
            alpha=0.85,
            label=f"{channel_id} notch",
        )
    axes[1].axvline(50.0, color="#263442", linewidth=0.6, alpha=0.6)
    axes[1].axvline(100.0, color="#263442", linewidth=0.6, alpha=0.6)
    axes[1].set_xlabel("Frequency (Hz)")
    axes[1].set_ylabel("Power spectral density (dB/stored-unit²/Hz)")
    axes[1].set_title("b  Representative spectra before and after notch", loc="left", fontweight="bold")
    axes[1].legend(fontsize=5.7, ncol=2, loc="lower left")

    figure.suptitle("50 Hz line-noise diagnostics in the SEEG sample", x=0.08, ha="left", fontsize=10)
    figure.text(
        0.08,
        0.92,
        "Welch PSD over 60 s; threshold is a diagnostic heuristic, not a clinical exclusion rule",
        fontsize=6.5,
        color="#4C5663",
    )
    figure.subplots_adjust(left=0.10, right=0.99, top=0.82, bottom=0.18, wspace=0.34)
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_stem.with_suffix(".png"), dpi=300, bbox_inches="tight", facecolor="white")
    figure.savefig(output_stem.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    figure.savefig(output_stem.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("Dataset/sampleData"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/line_noise"))
    parser.add_argument(
        "--figure", type=Path, default=Path("assets/figures/line_noise_diagnostic")
    )
    args = parser.parse_args()

    metrics = compute_line_noise_metrics(args.data_root)
    form_summary, code_summary = summarize_line_noise(metrics)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(args.output_dir / "channel_metrics.csv", index=False)
    form_summary.to_csv(args.output_dir / "channel_form_summary.csv", index=False)
    code_summary.to_csv(args.output_dir / "electrode_code_summary.csv", index=False)
    _plot_diagnostics(metrics, args.data_root, args.figure)
    print(f"Analyzed {len(metrics)} record-channel observations")
    print(form_summary.to_string(index=False))
    print(f"Wrote metrics to {args.output_dir}")
    print(f"Wrote figure to {args.figure}.{{png,svg,pdf}}")


if __name__ == "__main__":
    main()
