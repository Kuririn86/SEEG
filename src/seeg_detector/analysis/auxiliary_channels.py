"""Diagnostics for the fixed POL DC01--DC16 auxiliary input block."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from seeg_detector.data import infer_channel_role, load_record


DC_LSB_STORED_UNIT = 366.3


def _median_run_length(signal: np.ndarray) -> float:
    changes = np.flatnonzero(np.diff(signal) != 0) + 1
    runs = np.diff(np.r_[0, changes, signal.size])
    return float(np.median(runs))


def compute_auxiliary_channel_metrics(data_root: str | Path) -> pd.DataFrame:
    """Compare DC auxiliary inputs with the AC electrode-code family."""

    rows: list[dict[str, object]] = []
    for path in sorted(Path(data_root).glob("*.npz")):
        record = load_record(path)
        for channel_index, channel_id in enumerate(map(str, record.channel_ids.tolist())):
            role = infer_channel_role(channel_id)
            is_ac = channel_id.startswith("POL AC") and channel_id[6:].isdigit()
            if role != "auxiliary_dc" and not is_ac:
                continue
            signal = np.asarray(record.valid_signal[channel_index], dtype=np.float64)
            levels = np.unique(signal)
            scaled = levels / DC_LSB_STORED_UNIT
            rows.append(
                {
                    "sample_id": record.sample_id,
                    "channel_id": channel_id,
                    "channel_index": channel_index,
                    "raw_channel_index": int(record.raw_channel_indices[channel_index]),
                    "channel_role": "auxiliary_dc" if role == "auxiliary_dc" else "seeg_ac_candidate",
                    "sampling_rate_hz": record.sampling_rate,
                    "duration_seconds": record.duration_seconds,
                    "unique_value_count": int(levels.size),
                    "minimum_stored_unit": float(signal.min()),
                    "maximum_stored_unit": float(signal.max()),
                    "standard_deviation_stored_unit": float(signal.std()),
                    "transition_rate": float(np.mean(np.diff(signal) != 0)),
                    "median_run_samples": _median_run_length(signal),
                    "dc_lsb_multiple_rate": float(
                        np.mean(np.isclose(scaled, np.rint(scaled), atol=2e-3))
                    ),
                }
            )
    return pd.DataFrame(rows)


def summarize_auxiliary_channels(metrics: pd.DataFrame) -> pd.DataFrame:
    """Return role-level descriptive statistics."""

    return (
        metrics.groupby("channel_role")
        .agg(
            record_channels=("channel_id", "size"),
            records=("sample_id", "nunique"),
            unique_values_median=("unique_value_count", "median"),
            unique_values_min=("unique_value_count", "min"),
            unique_values_max=("unique_value_count", "max"),
            transition_rate_median=("transition_rate", "median"),
            median_run_samples=("median_run_samples", "median"),
            dc_lsb_multiple_rate=("dc_lsb_multiple_rate", "mean"),
        )
        .reset_index()
    )
