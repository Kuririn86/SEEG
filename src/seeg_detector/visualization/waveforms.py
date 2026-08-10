"""Publication-oriented SEEG waveform previews using matplotlib.

Figure contract
---------------
Core conclusion: the loader preserves channel identity and exposes waveform
structure around a labeled onset while keeping a matched negative example.
Archetype: quantitative grid. Backend: Python/matplotlib. The stored signal
unit is not declared, so panels show median-centered stored amplitude without
assigning a physical unit or clipping observations.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from seeg_detector.data import SEEGRecord


COLORS = {"positive": "#2463A8", "negative": "#687482", "onset": "#D8792B"}


def _channel_indices(record: SEEGRecord, channel_names: list[str]) -> list[int]:
    lookup = {str(name): index for index, name in enumerate(record.channel_ids.tolist())}
    missing = [name for name in channel_names if name not in lookup]
    if missing:
        raise ValueError(f"Channels absent from {record.sample_id}: {missing}")
    return [lookup[name] for name in channel_names]


def plot_onset_comparison(
    positive: SEEGRecord,
    negative: SEEGRecord,
    onset_time: float,
    channel_names: list[str],
    seconds_before: float = 5.0,
    seconds_after: float = 5.0,
) -> plt.Figure:
    """Plot matched raw waveforms around the positive sample's onset time."""

    if not 0 < onset_time < positive.duration_seconds:
        raise ValueError("onset_time must fall inside the positive record")
    positive_indices = _channel_indices(positive, channel_names)
    negative_indices = _channel_indices(negative, channel_names)
    start = max(0.0, onset_time - seconds_before)
    stop = min(positive.duration_seconds, onset_time + seconds_after)
    stop = min(stop, negative.duration_seconds)

    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 8,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.7,
            "axes.grid": False,
        }
    )
    figure, axes = plt.subplots(
        len(channel_names),
        2,
        figsize=(10.0, 8.2),
        sharex=True,
        constrained_layout=False,
    )

    columns = [
        (positive, positive_indices, COLORS["positive"], "Positive sample (label = 1)"),
        (negative, negative_indices, COLORS["negative"], "Negative sample (label = 0)"),
    ]
    for column, (record, indices, color, title) in enumerate(columns):
        sample_start = int(round(start * record.sampling_rate))
        sample_stop = int(round(stop * record.sampling_rate))
        time = np.arange(sample_start, sample_stop) / record.sampling_rate
        for row, (channel_name, channel_index) in enumerate(zip(channel_names, indices)):
            axis = axes[row, column]
            waveform = record.valid_signal[channel_index, sample_start:sample_stop]
            waveform = waveform - np.median(waveform)
            axis.plot(time, waveform, color=color, linewidth=0.45, rasterized=True)
            axis.axhline(0.0, color="#CBD1D8", linewidth=0.45, zorder=0)
            axis.tick_params(axis="both", labelsize=7, width=0.6, length=2.5)
            axis.spines["left"].set_color("#7B8490")
            axis.spines["bottom"].set_color("#7B8490")
            if column == 0:
                axis.set_ylabel(channel_name, rotation=0, ha="right", va="center", labelpad=28)
            if row == 0:
                axis.set_title(f"{title}\n{record.sample_id}", loc="left", fontsize=10, pad=7)
            if row == len(channel_names) - 1:
                axis.set_xlabel("Time from record start (s)")
        for axis in axes[:, column]:
            axis.axvline(
                onset_time,
                color=COLORS["onset"],
                linestyle=(0, (3, 2)),
                linewidth=1.0,
                label="Labeled onset" if column == 0 else "Positive-sample onset reference",
            )

    axes[0, 0].legend(loc="upper right", fontsize=7, handlelength=2.5)
    axes[0, 1].legend(loc="upper right", fontsize=7, handlelength=2.5)
    figure.suptitle("SEEG waveform examples around a labeled seizure onset", fontsize=13, x=0.08, ha="left")
    figure.text(
        0.08,
        0.955,
        "Six labeled Top-10 channels; median-centered stored amplitude; physical unit not provided",
        fontsize=8,
        color="#4C5663",
        ha="left",
    )
    figure.text(
        0.012,
        0.50,
        "Stored amplitude (median-centered)",
        rotation=90,
        va="center",
        fontsize=8,
        color="#4C5663",
    )
    figure.subplots_adjust(left=0.14, right=0.98, top=0.90, bottom=0.07, hspace=0.24, wspace=0.20)
    return figure


def save_waveform_figure(
    figure: plt.Figure, output_stem: str | Path
) -> tuple[Path, Path, Path]:
    stem = Path(output_stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    png_path = stem.with_suffix(".png")
    svg_path = stem.with_suffix(".svg")
    pdf_path = stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=300, bbox_inches="tight", facecolor="white")
    figure.savefig(svg_path, bbox_inches="tight", facecolor="white")
    figure.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    return png_path, svg_path, pdf_path
