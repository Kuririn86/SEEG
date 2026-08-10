"""Small-data handcrafted baseline for the competition sample bundle."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from seeg_detector.data import load_record, neural_channel_indices

BANDS = (
    ("delta", 1.0, 4.0),
    ("theta", 4.0, 8.0),
    ("alpha", 8.0, 13.0),
    ("beta", 13.0, 30.0),
    ("gamma", 30.0, 70.0),
    ("high", 70.0, 95.0),
)


@dataclass(frozen=True)
class HandcraftedRecord:
    """Fixed record features plus temporal and channel evidence."""

    sample_id: str
    feature_names: tuple[str, ...]
    features: np.ndarray
    frame_times: np.ndarray
    anomaly_trajectory: np.ndarray
    channel_scores: np.ndarray
    channel_ids: tuple[str, ...]


def _summarize_feature(name: str, values: np.ndarray) -> tuple[list[str], list[float]]:
    names: list[str] = []
    result: list[float] = []
    for quantile in (0.1, 0.5, 0.9, 0.99):
        names.append(f"{name}_all_q{int(quantile * 100):02d}")
        result.append(float(np.quantile(values, quantile)))

    per_frame = np.quantile(values, 0.9, axis=0)
    baseline = per_frame[:10]
    late = per_frame[10:]
    for suffix, value in (
        ("frame_max", np.max(per_frame)),
        ("frame_std", np.std(per_frame)),
        ("late_minus_base", np.median(late) - np.median(baseline)),
        ("late_q90_minus_base", np.quantile(late, 0.9) - np.median(baseline)),
    ):
        names.append(f"{name}_{suffix}")
        result.append(float(value))
    return names, result


def extract_handcrafted_record(path: str | Path) -> HandcraftedRecord:
    """Extract layout-invariant one-second time/frequency summaries."""

    record = load_record(path)
    channel_indices = neural_channel_indices([str(item) for item in record.channel_ids])
    if len(channel_indices) < 10:
        raise ValueError(f"{record.sample_id} has fewer than 10 eligible SEEG channels")

    signal = np.asarray(record.valid_signal[channel_indices], dtype=np.float32)
    samples_per_frame = round(record.sampling_rate)
    frame_count = signal.shape[1] // samples_per_frame
    if frame_count < 20:
        raise ValueError(f"{record.sample_id} is too short for the sample baseline")
    signal = signal[:, : frame_count * samples_per_frame]

    center = np.median(signal, axis=1, keepdims=True)
    scale = 1.4826 * np.median(np.abs(signal - center), axis=1, keepdims=True)
    signal = np.clip((signal - center) / np.maximum(scale, 1e-6), -20.0, 20.0)

    # Moving-average decimation is a deterministic, inexpensive anti-aliasing
    # baseline for this M0 experiment.
    decimation = max(1, round(record.sampling_rate / 200.0))
    usable = (signal.shape[1] // decimation) * decimation
    reduced = signal[:, :usable].reshape(signal.shape[0], -1, decimation).mean(axis=2)
    reduced_rate = record.sampling_rate / decimation
    reduced_per_frame = round(reduced_rate)
    reduced = reduced[:, : frame_count * reduced_per_frame]
    frames = reduced.reshape(reduced.shape[0], frame_count, reduced_per_frame)

    rms = np.sqrt(np.mean(np.square(frames), axis=2) + 1e-8)
    line_length = np.mean(np.abs(np.diff(frames, axis=2)), axis=2) + 1e-8
    abs_q95 = np.quantile(np.abs(frames), 0.95, axis=2) + 1e-8
    spectrum = np.fft.rfft(frames, axis=2)
    power = np.square(np.abs(spectrum)) / reduced_per_frame
    frequencies = np.fft.rfftfreq(reduced_per_frame, d=1.0 / reduced_rate)

    feature_maps: dict[str, np.ndarray] = {
        "log_rms": np.log(rms),
        "log_line": np.log(line_length),
        "log_abs95": np.log(abs_q95),
    }
    for band_name, low, high in BANDS:
        mask = (frequencies >= low) & (frequencies < high)
        feature_maps[f"log_bp_{band_name}"] = np.log(np.mean(power[:, :, mask], axis=2) + 1e-10)

    feature_names: list[str] = []
    feature_values: list[float] = []
    for name, values in feature_maps.items():
        names, summaries = _summarize_feature(name, values)
        feature_names.extend(names)
        feature_values.extend(summaries)

    evidence_parts = []
    for name in ("log_rms", "log_line", "log_bp_beta", "log_bp_gamma", "log_bp_high"):
        values = feature_maps[name]
        baseline = values[:, :10]
        base_median = np.median(baseline, axis=1, keepdims=True)
        base_mad = np.median(np.abs(baseline - base_median), axis=1, keepdims=True)
        evidence_parts.append((values - base_median) / np.maximum(1.4826 * base_mad, 0.15))
    evidence = np.maximum(np.mean(np.stack(evidence_parts, axis=0), axis=0), 0.0)

    trajectory = np.quantile(evidence, 0.9, axis=0)
    trajectory = np.convolve(trajectory, np.ones(3) / 3.0, mode="same")
    channel_scores = np.quantile(evidence[:, 10:], 0.9, axis=1)
    for suffix, value in (
        ("anomaly_max", np.max(trajectory)),
        ("anomaly_median", np.median(trajectory[10:])),
        ("anomaly_q90", np.quantile(trajectory[10:], 0.9)),
        ("anomaly_auc", np.mean(trajectory[10:])),
    ):
        feature_names.append(suffix)
        feature_values.append(float(value))

    return HandcraftedRecord(
        sample_id=record.sample_id,
        feature_names=tuple(feature_names),
        features=np.asarray(feature_values, dtype=np.float64),
        frame_times=np.arange(frame_count, dtype=np.float64) + 0.5,
        anomaly_trajectory=np.asarray(trajectory, dtype=np.float64),
        channel_scores=np.asarray(channel_scores, dtype=np.float64),
        channel_ids=tuple(str(record.channel_ids[index]) for index in channel_indices),
    )


def predict_onset(record: HandcraftedRecord, threshold: float) -> float:
    """Return the first sustained anomaly frame after the baseline interval."""

    above = record.anomaly_trajectory >= threshold
    for index in range(10, max(10, len(above) - 2)):
        if bool(np.all(above[index : index + 3])):
            return float(record.frame_times[index])
    return float(record.frame_times[int(np.argmax(record.anomaly_trajectory[10:])) + 10])


def rank_channels(record: HandcraftedRecord, onset_time: float) -> tuple[str, ...]:
    """Rank ten valid channels using post-baseline abnormality evidence."""

    del onset_time
    order = np.argsort(-record.channel_scores, kind="stable")[:10]
    return tuple(record.channel_ids[index] for index in order)
