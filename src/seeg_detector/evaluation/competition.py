"""Known competition metrics with an explicit proxy for the unpublished part."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
from sklearn.metrics import f1_score, roc_auc_score


@dataclass(frozen=True)
class CompetitionMetrics:
    auc: float
    f1: float
    sensitivity: float
    specificity: float
    channel_overlap: float
    channel_rank_proxy: float
    onset_mae: float
    onset_score: float
    score_overlap_proxy: float
    score_rank_proxy: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


def _rank_aware_channel_score(predicted: tuple[str, ...], truth: tuple[str, ...]) -> float:
    true_gain = {channel: 1.0 / math.log2(rank + 2.0) for rank, channel in enumerate(truth)}
    dcg = sum(
        true_gain.get(channel, 0.0) / math.log2(rank + 2.0)
        for rank, channel in enumerate(predicted)
    )
    ideal_gains = sorted(true_gain.values(), reverse=True)
    ideal = sum(gain / math.log2(rank + 2.0) for rank, gain in enumerate(ideal_gains))
    return float(dcg / ideal) if ideal else 0.0


def evaluate_competition_proxy(
    labels: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    true_onsets: np.ndarray,
    predicted_onsets: np.ndarray,
    true_channels: list[tuple[str, ...]],
    predicted_channels: list[tuple[str, ...]],
) -> CompetitionMetrics:
    """Evaluate published terms and two transparent ChannelScore proxies."""

    labels = np.asarray(labels, dtype=np.int64)
    probabilities = np.asarray(probabilities, dtype=np.float64)
    predictions = probabilities >= threshold
    auc = float(roc_auc_score(labels, probabilities))
    f1 = float(f1_score(labels, predictions, zero_division=0))
    positives = labels == 1
    negatives = ~positives
    sensitivity = float(np.mean(predictions[positives]))
    specificity = float(np.mean(~predictions[negatives]))

    onset_errors: list[float] = []
    overlaps: list[float] = []
    rank_scores: list[float] = []
    for index in np.flatnonzero(positives):
        if not predictions[index]:
            onset_errors.append(60.0)
            overlaps.append(0.0)
            rank_scores.append(0.0)
            continue
        onset_errors.append(abs(float(predicted_onsets[index]) - float(true_onsets[index])))
        truth = true_channels[index]
        predicted = predicted_channels[index]
        overlaps.append(len(set(predicted) & set(truth)) / 10.0)
        rank_scores.append(_rank_aware_channel_score(predicted, truth))

    onset_mae = float(np.mean(onset_errors))
    onset_score = max(0.0, 1.0 - onset_mae / 60.0)
    channel_overlap = float(np.mean(overlaps))
    channel_rank_proxy = float(np.mean(rank_scores))
    base = 0.25 * auc + 0.15 * f1 + 0.10 * sensitivity + 0.10 * specificity + 0.15 * onset_score
    return CompetitionMetrics(
        auc=auc,
        f1=f1,
        sensitivity=sensitivity,
        specificity=specificity,
        channel_overlap=channel_overlap,
        channel_rank_proxy=channel_rank_proxy,
        onset_mae=onset_mae,
        onset_score=onset_score,
        score_overlap_proxy=base + 0.25 * channel_overlap,
        score_rank_proxy=base + 0.25 * channel_rank_proxy,
    )
