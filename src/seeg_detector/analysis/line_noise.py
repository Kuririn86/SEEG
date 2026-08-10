"""Frequency-domain diagnostics for 50 Hz mains interference in SEEG data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import filtfilt, iirnotch, welch

from seeg_detector.data import load_record, parse_channel_id, read_labels


def _median_band(psd: np.ndarray, frequencies: np.ndarray, low: float, high: float) -> np.ndarray:
    return np.median(psd[:, (frequencies >= low) & (frequencies <= high)], axis=1)


def _line_excess_db(
    psd: np.ndarray,
    frequencies: np.ndarray,
    center: float,
) -> np.ndarray:
    line_power = _median_band(psd, frequencies, center - 0.5, center + 0.5)
    flank_bins = np.concatenate(
        [
            psd[:, (frequencies >= center - 5.0) & (frequencies <= center - 2.0)],
            psd[:, (frequencies >= center + 2.0) & (frequencies <= center + 5.0)],
        ],
        axis=1,
    )
    flank_power = np.median(flank_bins, axis=1)
    tiny = np.finfo(np.float64).tiny
    return 10.0 * np.log10(np.maximum(line_power, tiny) / np.maximum(flank_power, tiny))


def compute_line_noise_metrics(
    data_root: str | Path,
    nperseg: int = 4000,
    noverlap: int = 2000,
) -> pd.DataFrame:
    """Compute per-record, per-channel line-peak and basic quality metrics."""

    root = Path(data_root)
    labels = read_labels(root / "label.csv").set_index("sample_id")
    rows: list[dict[str, object]] = []
    for path in sorted(root.glob("*.npz")):
        record = load_record(path)
        signal = np.asarray(record.valid_signal, dtype=np.float64)
        centered = signal - signal.mean(axis=1, keepdims=True)
        frequencies, psd = welch(
            centered,
            fs=record.sampling_rate,
            window="hann",
            nperseg=nperseg,
            noverlap=noverlap,
            detrend="constant",
            axis=1,
            scaling="density",
        )
        line50 = _line_excess_db(psd, frequencies, 50.0)
        line100 = _line_excess_db(psd, frequencies, 100.0)
        line150 = _line_excess_db(psd, frequencies, 150.0)
        label = int(labels.loc[record.sample_id, "label"]) if record.sample_id in labels.index else None

        for channel_index, channel_id in enumerate(record.channel_ids.tolist()):
            parsed = parse_channel_id(str(channel_id))
            source_prefix = parsed.source_prefix if parsed else str(channel_id).split(" ", 1)[0]
            reference_tag = parsed.reference_tag if parsed else None
            rows.append(
                {
                    "sample_id": record.sample_id,
                    "split": record.sample_id.split("_", 1)[0],
                    "label": label,
                    "channel_index": channel_index,
                    "raw_channel_index": int(record.raw_channel_indices[channel_index]),
                    "channel_id": str(channel_id),
                    "source_prefix": source_prefix,
                    "channel_form": "EEG ...-Ref" if reference_tag else source_prefix,
                    "electrode_code": parsed.electrode_code if parsed else "unparsed",
                    "contact_text": parsed.contact_text if parsed else "",
                    "contact_number": parsed.contact_number if parsed else np.nan,
                    "reference_tag": reference_tag or "",
                    "sampling_rate_hz": record.sampling_rate,
                    "duration_seconds": record.duration_seconds,
                    "line50_excess_db": float(line50[channel_index]),
                    "line100_excess_db": float(line100[channel_index]),
                    "line150_excess_db": float(line150[channel_index]),
                    "std_stored_unit": float(centered[channel_index].std()),
                    "peak_to_peak_stored_unit": float(np.ptp(centered[channel_index])),
                    "zero_rate": float((signal[channel_index] == 0).mean()),
                    "repeated_diff_rate": float((np.diff(signal[channel_index]) == 0).mean()),
                }
            )

    metrics = pd.DataFrame(rows)
    metrics["line50_candidate"] = metrics["line50_excess_db"] > 10.0
    metrics["line50_severe"] = metrics["line50_excess_db"] > 20.0
    metrics["line100_candidate"] = metrics["line100_excess_db"] > 10.0
    return metrics


def summarize_line_noise(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return form-level and electrode-code-level summaries."""

    form_summary = (
        metrics.groupby("channel_form", dropna=False)
        .agg(
            channels=("channel_id", "size"),
            median_50hz_excess_db=("line50_excess_db", "median"),
            mean_50hz_excess_db=("line50_excess_db", "mean"),
            candidate_rate=("line50_candidate", "mean"),
            severe_rate=("line50_severe", "mean"),
            harmonic_100hz_rate=("line100_candidate", "mean"),
        )
        .reset_index()
    )
    code_summary = (
        metrics.groupby("electrode_code", dropna=False)
        .agg(
            channels=("channel_id", "size"),
            records=("sample_id", "nunique"),
            median_50hz_excess_db=("line50_excess_db", "median"),
            mean_50hz_excess_db=("line50_excess_db", "mean"),
            candidate_rate=("line50_candidate", "mean"),
            severe_rate=("line50_severe", "mean"),
            harmonic_100hz_rate=("line100_candidate", "mean"),
        )
        .reset_index()
        .sort_values(["median_50hz_excess_db", "channels"], ascending=[False, False])
    )
    return form_summary, code_summary


def apply_zero_phase_notches(
    signal: np.ndarray,
    sampling_rate: float,
    frequencies: tuple[float, ...] = (50.0, 100.0, 150.0),
    quality_factor: float = 50.0,
) -> np.ndarray:
    """Apply narrow zero-phase IIR notches for a diagnostic comparison."""

    filtered = np.asarray(signal, dtype=np.float64).copy()
    for frequency in frequencies:
        numerator, denominator = iirnotch(frequency, quality_factor, fs=sampling_rate)
        filtered = filtfilt(numerator, denominator, filtered, axis=-1)
    return filtered

