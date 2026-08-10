#!/usr/bin/env python3
"""Sensitivity checks for second-round multichannel propagation features."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from seeg_detector.analysis.onset_features import OnsetFeatureConfig, evaluate_record_alignment
from seeg_detector.data import load_record, read_labels


FEATURES = [
    "lagged_outflow",
    "mean_lagged_connectivity",
    "propagation_participation",
    "network_density",
]


def _remove_severe_line_noise(record, metrics: pd.DataFrame):
    if metrics.empty:
        return record
    lookup = metrics.set_index("channel_id")["line50_excess_db"].to_dict()
    keep = np.asarray(
        [lookup.get(str(channel), 0.0) <= 20.0 for channel in record.channel_ids]
    )
    if keep.sum() < 10:
        return record
    return replace(
        record,
        signal=record.signal[keep],
        channel_ids=record.channel_ids[keep],
        raw_channel_indices=record.raw_channel_indices[keep],
    )


def main() -> None:
    data_root = Path("Dataset/sampleData")
    output_dir = Path("reports/onset_features_round2")
    labels = read_labels(data_root / "label.csv").set_index("sample_id")
    line_metrics = pd.read_csv("reports/line_noise/channel_metrics.csv")
    rows = []
    settings = [
        (1.0, "all_channels"),
        (1.5, "all_channels"),
        (2.0, "all_channels"),
        (1.5, "exclude_line50_gt20db"),
    ]
    paths = [
        path
        for path in sorted(data_root.glob("train_*.npz"))
        if int(labels.loc[path.stem, "label"]) == 1
    ]
    for network_window_seconds, channel_policy in settings:
        config = OnsetFeatureConfig(
            include_propagation_features=True,
            network_window_seconds=network_window_seconds,
        )
        for path in paths:
            record = load_record(path)
            metrics = line_metrics.loc[line_metrics["sample_id"] == record.sample_id]
            if channel_policy == "exclude_line50_gt20db":
                record = _remove_severe_line_noise(record, metrics)
            label = labels.loc[record.sample_id]
            top10 = [str(label[f"ch{index}"]) for index in range(1, 11)]
            alignment, _, _ = evaluate_record_alignment(
                record,
                onset_seconds=float(label["onset_time"]),
                official_top10=top10,
                line_noise_metrics=None,
                config=config,
            )
            selected = alignment.query("channel_set == 'all' and feature in @FEATURES")
            for _, row in selected.iterrows():
                rows.append(
                    {
                        "network_window_seconds": network_window_seconds,
                        "channel_policy": channel_policy,
                        "sample_id": record.sample_id,
                        "feature": row["feature"],
                        "signed_timing_error_seconds": row[
                            "signed_timing_error_seconds"
                        ],
                        "absolute_timing_error_seconds": row[
                            "absolute_timing_error_seconds"
                        ],
                        "early_contrast": row["early_contrast"],
                        "channels_used": row["channels_used"],
                    }
                )
            print(
                f"Checked {record.sample_id} window={network_window_seconds:.1f}s "
                f"policy={channel_policy}"
            )

    per_record = pd.DataFrame(rows)
    summary = (
        per_record.groupby(["network_window_seconds", "channel_policy", "feature"])
        .agg(
            records=("sample_id", "nunique"),
            median_abs_timing_error_seconds=("absolute_timing_error_seconds", "median"),
            mean_abs_timing_error_seconds=("absolute_timing_error_seconds", "mean"),
            within_0_5_seconds_rate=(
                "absolute_timing_error_seconds",
                lambda values: float((values <= 0.5).mean()),
            ),
            within_1_second_rate=(
                "absolute_timing_error_seconds",
                lambda values: float((values <= 1.0).mean()),
            ),
            positive_contrast_rate=("early_contrast", lambda values: float((values > 0).mean())),
            median_channels_used=("channels_used", "median"),
        )
        .reset_index()
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    per_record.to_csv(output_dir / "propagation_sensitivity_per_record.csv", index=False)
    summary.to_csv(output_dir / "propagation_sensitivity_summary.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
