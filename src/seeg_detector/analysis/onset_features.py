"""Physiology-motivated feature analysis around labeled SEEG seizure onset."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.fft import rfft, rfftfreq
from scipy.ndimage import median_filter

from seeg_detector.data import SEEGRecord, neural_channel_indices


@dataclass(frozen=True)
class OnsetFeatureConfig:
    """Configuration for causal sliding-window onset feature extraction."""

    window_seconds: float = 0.5
    step_seconds: float = 0.125
    baseline_seconds: float = 10.0
    baseline_guard_seconds: float = 2.0
    early_ictal_seconds: float = 2.0
    derivative_search_before_seconds: float = 1.0
    derivative_search_after_seconds: float = 3.0
    channel_chunk_size: int = 8
    aggregate_quantile: float = 0.90
    include_propagation_features: bool = False
    recruitment_persistence_seconds: float = 1.0
    network_window_seconds: float = 1.5
    network_min_points: int = 6
    connectivity_threshold: float = 0.60


# Features whose clinically meaningful onset response may be bidirectional.
ABSOLUTE_CHANGE_FEATURES = {"rms_change", "spectral_entropy_change"}

CHANNEL_PROPAGATION_FEATURES = {
    "recruitment_consensus",
    "recruitment_persistence",
    "recruitment_change_rate",
    "early_recruitment_lead",
    "propagation_participation",
    "lagged_outflow",
    "net_lagged_outflow",
    "coactivation_strength",
}

GLOBAL_PROPAGATION_FEATURES = {
    "recruited_fraction_2z",
    "recruited_fraction_3z",
    "recruitment_fraction_slope",
    "recruitment_dispersion",
    "propagation_front",
    "network_density",
    "largest_component_fraction",
    "mean_lagged_connectivity",
}

PROPAGATION_FEATURES = CHANNEL_PROPAGATION_FEATURES | GLOBAL_PROPAGATION_FEATURES


def feature_scope(feature_name: str) -> str:
    """Return whether a feature supports channel ranking or only global timing."""

    if feature_name in GLOBAL_PROPAGATION_FEATURES:
        return "global_propagation"
    if feature_name in CHANNEL_PROPAGATION_FEATURES:
        return "channel_propagation"
    return "channel_local"


def _line_clean_mask(frequencies: np.ndarray, maximum: float = 500.0) -> np.ndarray:
    mask = (frequencies >= 1.0) & (frequencies <= maximum)
    for center in np.arange(50.0, maximum + 0.1, 50.0):
        mask &= np.abs(frequencies - center) > 2.0
    return mask


def _band_mask(
    frequencies: np.ndarray,
    low: float,
    high: float,
    *,
    remove_line_harmonics: bool = True,
) -> np.ndarray:
    mask = (frequencies >= low) & (frequencies < high)
    if remove_line_harmonics:
        mask &= _line_clean_mask(frequencies, maximum=max(high, 50.0))
    return mask


def _safe_log(values: np.ndarray) -> np.ndarray:
    return np.log(np.maximum(values, np.finfo(np.float32).tiny))


def extract_priority_features(
    record: SEEGRecord,
    config: OnsetFeatureConfig = OnsetFeatureConfig(),
) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Extract causal channel-by-window features from candidate neural channels.

    Returned timestamps mark the end of each window, so no feature uses samples
    occurring after its reported time. Mains-frequency bins and harmonics are
    removed from spectral summaries rather than applying a time-domain notch.
    """

    indices = np.asarray(neural_channel_indices(record.channel_ids.tolist()), dtype=int)
    if indices.size == 0:
        raise ValueError(f"No candidate neural channels in {record.sample_id}")

    signal = np.asarray(record.valid_signal[indices], dtype=np.float32)
    sampling_rate = float(record.sampling_rate)
    window_samples = int(round(config.window_seconds * sampling_rate))
    step_samples = int(round(config.step_seconds * sampling_rate))
    if window_samples < 8 or step_samples < 1 or signal.shape[1] < window_samples:
        raise ValueError("Window configuration is incompatible with the recording")

    starts = np.arange(0, signal.shape[1] - window_samples + 1, step_samples, dtype=int)
    times = (starts + window_samples) / sampling_rate
    frequencies = rfftfreq(window_samples, d=1.0 / sampling_rate)
    hann = np.hanning(window_samples).astype(np.float32)
    frequency_step = float(frequencies[1] - frequencies[0])

    masks = {
        "low": _band_mask(frequencies, 1.0, 13.0),
        "beta": _band_mask(frequencies, 13.0, 30.0),
        "low_gamma": _band_mask(frequencies, 30.0, 80.0),
        "high_gamma": _band_mask(frequencies, 80.0, 150.0),
        "ripple": _band_mask(frequencies, 150.0, 250.0),
        "fast_ripple": _band_mask(frequencies, 250.0, 500.1),
        "centroid": _line_clean_mask(frequencies, maximum=250.0),
        "rhythmicity": _band_mask(frequencies, 1.0, 45.0),
    }
    for name, mask in masks.items():
        if not np.any(mask):
            raise ValueError(f"No spectral bins for {name} at {sampling_rate} Hz")

    feature_names = [
        "line_length",
        "rms_change",
        "teager_energy",
        "kurtosis",
        "beta_power",
        "low_gamma_power",
        "high_gamma_power",
        "ripple_power",
        "fast_ripple_power",
        "high_low_ratio",
        "low_frequency_suppression",
        "spectral_centroid",
        "spectral_entropy_change",
        "rhythmicity",
    ]
    features = {
        name: np.empty((indices.size, starts.size), dtype=np.float32)
        for name in feature_names
    }

    for batch_start in range(0, indices.size, config.channel_chunk_size):
        batch_stop = min(indices.size, batch_start + config.channel_chunk_size)
        batch = signal[batch_start:batch_stop]
        windows = np.lib.stride_tricks.sliding_window_view(
            batch, window_shape=window_samples, axis=1
        )[:, ::step_samples, :]
        centered = windows - windows.mean(axis=-1, keepdims=True)

        line_length = np.mean(np.abs(np.diff(centered, axis=-1)), axis=-1)
        rms = np.sqrt(np.mean(centered * centered, axis=-1))
        teager = np.mean(
            np.abs(centered[..., 1:-1] ** 2 - centered[..., :-2] * centered[..., 2:]),
            axis=-1,
        )
        second_moment = np.mean(centered * centered, axis=-1)
        fourth_moment = np.mean(centered**4, axis=-1)
        kurtosis = fourth_moment / np.maximum(second_moment**2, np.finfo(np.float32).tiny)

        spectrum = rfft(centered * hann, axis=-1)
        power = (np.abs(spectrum) ** 2).astype(np.float32)

        def band_power(name: str) -> np.ndarray:
            return np.sum(power[..., masks[name]], axis=-1) * frequency_step

        low = band_power("low")
        beta = band_power("beta")
        low_gamma = band_power("low_gamma")
        high_gamma = band_power("high_gamma")
        ripple = band_power("ripple")
        fast_ripple = band_power("fast_ripple")

        centroid_power = power[..., masks["centroid"]]
        centroid_frequency = frequencies[masks["centroid"]]
        centroid_total = np.sum(centroid_power, axis=-1)
        centroid = np.sum(centroid_power * centroid_frequency, axis=-1) / np.maximum(
            centroid_total, np.finfo(np.float32).tiny
        )
        probabilities = centroid_power / np.maximum(
            centroid_total[..., None], np.finfo(np.float32).tiny
        )
        entropy = -np.sum(
            probabilities * np.log(np.maximum(probabilities, np.finfo(np.float32).tiny)),
            axis=-1,
        ) / np.log(centroid_power.shape[-1])
        rhythmic_power = power[..., masks["rhythmicity"]]
        rhythmicity = np.max(rhythmic_power, axis=-1) / np.maximum(
            np.sum(rhythmic_power, axis=-1), np.finfo(np.float32).tiny
        )

        target = slice(batch_start, batch_stop)
        features["line_length"][target] = _safe_log(line_length)
        features["rms_change"][target] = _safe_log(rms)
        features["teager_energy"][target] = _safe_log(teager)
        features["kurtosis"][target] = _safe_log(kurtosis)
        features["beta_power"][target] = _safe_log(beta)
        features["low_gamma_power"][target] = _safe_log(low_gamma)
        features["high_gamma_power"][target] = _safe_log(high_gamma)
        features["ripple_power"][target] = _safe_log(ripple)
        features["fast_ripple_power"][target] = _safe_log(fast_ripple)
        features["high_low_ratio"][target] = _safe_log(
            beta + low_gamma + high_gamma
        ) - _safe_log(low)
        features["low_frequency_suppression"][target] = -_safe_log(low)
        features["spectral_centroid"][target] = centroid
        features["spectral_entropy_change"][target] = entropy
        features["rhythmicity"][target] = _safe_log(rhythmicity)

    return times, indices, features


def _robust_z(values: np.ndarray, baseline_mask: np.ndarray) -> np.ndarray:
    baseline = values[:, baseline_mask]
    median = np.median(baseline, axis=1, keepdims=True)
    mad = np.median(np.abs(baseline - median), axis=1, keepdims=True)
    fallback = np.std(baseline, axis=1, keepdims=True)
    scale = np.where(1.4826 * mad > 1e-6, 1.4826 * mad, fallback)
    scale = np.maximum(scale, 1e-6)
    return (values - median) / scale


def _causal_mean(values: np.ndarray, points: int) -> np.ndarray:
    """Causal moving average along the last axis without future samples."""

    points = max(1, int(points))
    cumulative = np.cumsum(values, axis=-1, dtype=np.float64)
    padded = np.concatenate(
        [np.zeros((*values.shape[:-1], 1), dtype=np.float64), cumulative], axis=-1
    )
    ends = np.arange(1, values.shape[-1] + 1)
    starts = np.maximum(0, ends - points)
    counts = ends - starts
    return ((padded[..., ends] - padded[..., starts]) / counts).astype(np.float32)


def _largest_component_fraction(adjacency: np.ndarray) -> float:
    """Return the largest connected-component fraction for a boolean graph."""

    node_count = adjacency.shape[0]
    unseen = set(range(node_count))
    largest = 0
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        size = 1
        while stack:
            node = stack.pop()
            neighbors = set(np.flatnonzero(adjacency[node]).tolist()) & unseen
            unseen.difference_update(neighbors)
            stack.extend(neighbors)
            size += len(neighbors)
        largest = max(largest, size)
    return largest / max(node_count, 1)


def _row_standardize(values: np.ndarray) -> np.ndarray:
    centered = values - values.mean(axis=1, keepdims=True)
    norms = np.linalg.norm(centered, axis=1, keepdims=True)
    return centered / np.maximum(norms, 1e-6)


def _top_positive_mean(matrix: np.ndarray, count: int) -> np.ndarray:
    count = min(max(1, count), matrix.shape[1])
    positive = np.maximum(matrix, 0.0)
    return np.mean(np.partition(positive, -count, axis=1)[:, -count:], axis=1)


def _rolling_network_features(
    base: np.ndarray,
    config: OnsetFeatureConfig,
) -> dict[str, np.ndarray]:
    """Compute causal envelope-network features from channel recruitment scores."""

    channel_count, time_count = base.shape
    window_points = max(
        config.network_min_points,
        int(round(config.network_window_seconds / config.step_seconds)),
    )
    top_count = min(max(3, int(round(0.10 * channel_count))), max(channel_count - 1, 1))
    channel_outputs = {
        "lagged_outflow": np.zeros_like(base, dtype=np.float32),
        "net_lagged_outflow": np.zeros_like(base, dtype=np.float32),
        "coactivation_strength": np.zeros_like(base, dtype=np.float32),
    }
    global_outputs = {
        "network_density": np.zeros(time_count, dtype=np.float32),
        "largest_component_fraction": np.zeros(time_count, dtype=np.float32),
        "mean_lagged_connectivity": np.zeros(time_count, dtype=np.float32),
    }
    upper = np.triu_indices(channel_count, k=1)

    for stop in range(config.network_min_points, time_count + 1):
        start = max(0, stop - window_points)
        segment = base[:, start:stop]
        zero_lag = _row_standardize(segment) @ _row_standardize(segment).T
        np.fill_diagonal(zero_lag, 0.0)
        coactivation = _top_positive_mean(zero_lag, top_count)

        past = _row_standardize(segment[:, :-1])
        future = _row_standardize(segment[:, 1:])
        lagged = past @ future.T
        np.fill_diagonal(lagged, 0.0)
        outflow = _top_positive_mean(lagged, top_count)
        inflow = _top_positive_mean(lagged.T, top_count)

        index = stop - 1
        channel_outputs["lagged_outflow"][:, index] = outflow
        channel_outputs["net_lagged_outflow"][:, index] = outflow - inflow
        channel_outputs["coactivation_strength"][:, index] = coactivation
        connections = zero_lag[upper]
        adjacency = zero_lag > config.connectivity_threshold
        global_outputs["network_density"][index] = float(
            np.mean(connections > config.connectivity_threshold)
        )
        global_outputs["largest_component_fraction"][index] = (
            _largest_component_fraction(adjacency)
        )
        global_outputs["mean_lagged_connectivity"][index] = float(np.mean(outflow))

    return {**channel_outputs, **global_outputs}


def _propagation_scores(
    z_values: dict[str, np.ndarray],
    baseline_mask: np.ndarray,
    config: OnsetFeatureConfig,
) -> dict[str, np.ndarray]:
    """Build channel-recruitment and dynamic-network propagation features."""

    consensus = np.median(
        np.stack(
            [
                np.maximum(z_values["high_gamma_power"], 0.0),
                np.maximum(z_values["low_frequency_suppression"], 0.0),
                np.abs(z_values["spectral_entropy_change"]),
                np.maximum(z_values["kurtosis"], 0.0),
                np.maximum(z_values["line_length"], 0.0),
            ],
            axis=0,
        ),
        axis=0,
    ).astype(np.float32)
    channel_count, time_count = consensus.shape
    persistence_points = max(
        1, int(round(config.recruitment_persistence_seconds / config.step_seconds))
    )
    persistence = _causal_mean(consensus, persistence_points)
    change_rate = np.zeros_like(consensus)
    change_rate[:, 1:] = np.maximum(
        np.diff(consensus, axis=1) / config.step_seconds, 0.0
    )
    change_rate = _causal_mean(change_rate, 3)
    lead = np.maximum(consensus - np.median(consensus, axis=0, keepdims=True), 0.0)

    recruited_2z = np.mean(consensus > 2.0, axis=0).astype(np.float32)
    recruited_3z = np.mean(consensus > 3.0, axis=0).astype(np.float32)
    fraction_slope = np.zeros(time_count, dtype=np.float32)
    fraction_slope[1:] = np.maximum(
        np.diff(recruited_2z) / config.step_seconds, 0.0
    )
    fraction_slope = _causal_mean(fraction_slope[None, :], 3)[0]
    dispersion = (
        np.quantile(consensus, 0.90, axis=0) - np.quantile(consensus, 0.50, axis=0)
    ).astype(np.float32)
    propagation_front = (
        recruited_2z * (1.0 - recruited_2z) * fraction_slope
    ).astype(np.float32)
    participation = consensus * fraction_slope[None, :]

    network = _rolling_network_features(consensus, config)
    channel_raw = {
        "recruitment_consensus": consensus,
        "recruitment_persistence": persistence,
        "recruitment_change_rate": change_rate,
        "early_recruitment_lead": lead,
        "propagation_participation": participation,
        "lagged_outflow": network["lagged_outflow"],
        "net_lagged_outflow": network["net_lagged_outflow"],
        "coactivation_strength": network["coactivation_strength"],
    }
    global_raw = {
        "recruited_fraction_2z": recruited_2z,
        "recruited_fraction_3z": recruited_3z,
        "recruitment_fraction_slope": fraction_slope,
        "recruitment_dispersion": dispersion,
        "propagation_front": propagation_front,
        "network_density": network["network_density"],
        "largest_component_fraction": network["largest_component_fraction"],
        "mean_lagged_connectivity": network["mean_lagged_connectivity"],
    }

    outputs = {
        name: _robust_z(values, baseline_mask)
        for name, values in channel_raw.items()
    }
    for name, values in global_raw.items():
        standardized = _robust_z(values[None, :], baseline_mask)
        outputs[name] = np.repeat(standardized, channel_count, axis=0)
    return outputs


def onset_feature_scores(
    times: np.ndarray,
    features: dict[str, np.ndarray],
    onset_seconds: float,
    config: OnsetFeatureConfig = OnsetFeatureConfig(),
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Convert raw features to baseline-standardized onset-response scores."""

    baseline_mask = (
        (times >= max(config.window_seconds, onset_seconds - config.baseline_seconds))
        & (times <= onset_seconds - config.baseline_guard_seconds)
    )
    if baseline_mask.sum() < 8:
        raise ValueError(f"Insufficient pre-onset baseline for onset={onset_seconds}")

    z_values = {name: _robust_z(values, baseline_mask) for name, values in features.items()}
    scores = {
        name: np.abs(values) if name in ABSOLUTE_CHANGE_FEATURES else values
        for name, values in z_values.items()
    }
    multiband = np.median(
        np.stack(
            [
                z_values["beta_power"],
                z_values["low_gamma_power"],
                z_values["high_gamma_power"],
            ],
            axis=0,
        ),
        axis=0,
    )
    scores["multiband_fast_activity"] = multiband
    scores["fast_suppression_joint"] = np.sqrt(
        np.maximum(multiband, 0.0) * np.maximum(z_values["low_frequency_suppression"], 0.0)
    )
    scores["physiology_composite"] = np.median(
        np.stack(
            [
                np.maximum(z_values["line_length"], 0.0),
                np.maximum(z_values["high_low_ratio"], 0.0),
                np.maximum(multiband, 0.0),
                np.maximum(z_values["low_frequency_suppression"], 0.0),
            ],
            axis=0,
        ),
        axis=0,
    )
    if config.include_propagation_features:
        scores.update(_propagation_scores(z_values, baseline_mask, config))
    return baseline_mask, scores


def evaluate_record_alignment(
    record: SEEGRecord,
    onset_seconds: float,
    official_top10: list[str],
    line_noise_metrics: pd.DataFrame | None = None,
    config: OnsetFeatureConfig = OnsetFeatureConfig(),
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Evaluate temporal and channel-ranking alignment for one positive record."""

    times, indices, raw_features = extract_priority_features(record, config=config)
    baseline_mask, scores = onset_feature_scores(
        times, raw_features, onset_seconds, config=config
    )
    channel_ids = np.asarray(record.channel_ids[indices], dtype=str)
    early_mask = (times >= onset_seconds) & (
        times <= onset_seconds + config.early_ictal_seconds
    )
    derivative_mask = (times[1:] >= onset_seconds - config.derivative_search_before_seconds) & (
        times[1:] <= onset_seconds + config.derivative_search_after_seconds
    )

    clean_mask = np.ones(channel_ids.size, dtype=bool)
    if line_noise_metrics is not None and not line_noise_metrics.empty:
        lookup = line_noise_metrics.set_index("channel_id")["line50_excess_db"].to_dict()
        clean_mask = np.asarray([lookup.get(name, 0.0) <= 20.0 for name in channel_ids])
        if clean_mask.sum() < 10:
            clean_mask[:] = True

    alignment_rows: list[dict[str, object]] = []
    trajectory_rows: list[dict[str, object]] = []
    channel_rows: list[dict[str, object]] = []

    for feature_name, channel_scores in scores.items():
        scope = feature_scope(feature_name)
        early_response = np.max(channel_scores[:, early_mask], axis=1)
        overlap = np.nan
        enrichment = np.nan
        if scope != "global_propagation":
            order = np.argsort(-early_response, kind="stable")
            predicted_top10 = set(channel_ids[order[:10]].tolist())
            official_set = set(official_top10)
            overlap = len(predicted_top10 & official_set)
            official_mask = np.asarray([name in official_set for name in channel_ids])
            other_mask = ~official_mask
            enrichment = float(np.median(early_response[official_mask])) - float(
                np.median(early_response[other_mask])
            )

            for channel_index, channel_id in enumerate(channel_ids):
                channel_rows.append(
                    {
                        "sample_id": record.sample_id,
                        "feature": feature_name,
                        "feature_scope": scope,
                        "channel_id": channel_id,
                        "early_response": float(early_response[channel_index]),
                        "official_top10": bool(official_mask[channel_index]),
                        "response_rank": int(np.flatnonzero(order == channel_index)[0] + 1),
                    }
                )

        channel_sets = [("all", np.ones(channel_ids.size, dtype=bool))]
        if feature_name not in PROPAGATION_FEATURES:
            channel_sets.append(("line_clean", clean_mask))
        for channel_set, mask in channel_sets:
            aggregate = np.quantile(
                channel_scores[mask], config.aggregate_quantile, axis=0
            )
            aggregate = median_filter(aggregate, size=3, mode="nearest")
            derivative = np.diff(aggregate) / np.diff(times)
            candidate_indices = np.flatnonzero(derivative_mask)
            peak_index = candidate_indices[np.argmax(derivative[candidate_indices])]
            peak_time = float(times[peak_index + 1])
            baseline_level = float(np.median(aggregate[baseline_mask]))
            early_level = float(np.median(aggregate[early_mask]))
            alignment_rows.append(
                {
                    "sample_id": record.sample_id,
                    "feature": feature_name,
                    "feature_scope": scope,
                    "channel_set": channel_set,
                    "onset_seconds": onset_seconds,
                    "peak_change_seconds": peak_time,
                    "signed_timing_error_seconds": peak_time - onset_seconds,
                    "absolute_timing_error_seconds": abs(peak_time - onset_seconds),
                    "baseline_level": baseline_level,
                    "early_ictal_level": early_level,
                    "early_contrast": early_level - baseline_level,
                    "top10_overlap": overlap if channel_set == "all" else np.nan,
                    "top10_enrichment": enrichment if channel_set == "all" else np.nan,
                    "channels_used": int(mask.sum()),
                }
            )
            relative_time = times - onset_seconds
            keep = (relative_time >= -5.0) & (relative_time <= 5.0)
            for time_value, score_value in zip(relative_time[keep], aggregate[keep]):
                trajectory_rows.append(
                    {
                        "sample_id": record.sample_id,
                        "feature": feature_name,
                        "feature_scope": scope,
                        "channel_set": channel_set,
                        "relative_time_seconds": float(time_value),
                        "aggregate_score": float(score_value),
                    }
                )

    return (
        pd.DataFrame(alignment_rows),
        pd.DataFrame(trajectory_rows),
        pd.DataFrame(channel_rows),
    )


def summarize_feature_alignment(alignment: pd.DataFrame) -> pd.DataFrame:
    """Summarize record-level results without treating windows as replicates."""

    all_channels = alignment.query("channel_set == 'all'").copy()
    summary = (
        all_channels.groupby(["feature", "feature_scope"])
        .agg(
            positive_records=("sample_id", "nunique"),
            median_abs_timing_error_seconds=("absolute_timing_error_seconds", "median"),
            mean_abs_timing_error_seconds=("absolute_timing_error_seconds", "mean"),
            median_signed_timing_error_seconds=("signed_timing_error_seconds", "median"),
            within_0_5_seconds_rate=(
                "absolute_timing_error_seconds",
                lambda values: float((values <= 0.5).mean()),
            ),
            within_1_second_rate=(
                "absolute_timing_error_seconds",
                lambda values: float((values <= 1.0).mean()),
            ),
            median_early_contrast=("early_contrast", "median"),
            min_early_contrast=("early_contrast", "min"),
            positive_contrast_rate=("early_contrast", lambda values: float((values > 0).mean())),
            mean_top10_overlap=("top10_overlap", "mean"),
            median_top10_overlap=("top10_overlap", "median"),
            median_top10_enrichment=("top10_enrichment", "median"),
        )
        .reset_index()
    )
    # Rank-based exploratory score gives equal weight to timing, temporal contrast,
    # and spatial Top-10 concordance. It is descriptive and not fitted to a test set.
    summary["timing_rank"] = summary["median_abs_timing_error_seconds"].rank(
        method="average", ascending=True
    )
    summary["contrast_rank"] = summary["median_early_contrast"].rank(
        method="average", ascending=False
    )
    summary["top10_rank"] = summary["mean_top10_overlap"].rank(
        method="average", ascending=False
    )
    summary["exploratory_rank_score"] = (
        summary[["timing_rank", "contrast_rank", "top10_rank"]].mean(axis=1)
    )
    summary["hit_rank"] = summary["within_0_5_seconds_rate"].rank(
        method="average", ascending=False
    )
    summary["within_1_second_rank"] = summary["within_1_second_rate"].rank(
        method="average", ascending=False
    )
    summary["mean_timing_rank"] = summary["mean_abs_timing_error_seconds"].rank(
        method="average", ascending=True
    )
    summary["direction_rank"] = summary["positive_contrast_rate"].rank(
        method="average", ascending=False
    )
    summary["onset_alignment_rank_score"] = summary[
        [
            "timing_rank",
            "mean_timing_rank",
            "hit_rank",
            "within_1_second_rank",
            "direction_rank",
        ]
    ].mean(axis=1)
    return summary.sort_values(
        ["exploratory_rank_score", "median_abs_timing_error_seconds", "feature"]
    ).reset_index(drop=True)
