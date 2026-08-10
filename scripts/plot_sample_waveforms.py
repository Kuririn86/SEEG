#!/usr/bin/env python3
"""Generate a deterministic positive/negative SEEG waveform comparison."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from seeg_detector.data import load_record, read_labels
from seeg_detector.visualization.waveforms import plot_onset_comparison, save_waveform_figure


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("Dataset/sampleData"))
    parser.add_argument("--positive", default="train_000027")
    parser.add_argument("--negative", default="train_000057")
    parser.add_argument("--channels", type=int, default=6)
    parser.add_argument(
        "--output", type=Path, default=Path("assets/figures/sample_waveforms_onset")
    )
    args = parser.parse_args()

    labels = read_labels(args.data_root / "label.csv").set_index("sample_id")
    positive_label = labels.loc[args.positive]
    if int(positive_label["label"]) != 1:
        raise ValueError(f"{args.positive} is not labeled positive")
    if int(labels.loc[args.negative, "label"]) != 0:
        raise ValueError(f"{args.negative} is not labeled negative")
    channel_names = [
        str(positive_label[f"ch{i}"]) for i in range(1, min(args.channels, 10) + 1)
    ]
    positive = load_record(args.data_root / f"{args.positive}.npz")
    negative = load_record(args.data_root / f"{args.negative}.npz")
    figure = plot_onset_comparison(
        positive=positive,
        negative=negative,
        onset_time=float(positive_label["onset_time"]),
        channel_names=channel_names,
    )
    paths = save_waveform_figure(figure, args.output)
    plt.close(figure)
    print("Wrote " + " and ".join(map(str, paths)))


if __name__ == "__main__":
    main()

