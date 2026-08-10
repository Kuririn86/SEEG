"""Fail-closed validation for official competition predictions."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
import math

from .schema import Prediction


class SubmissionValidationError(ValueError):
    """Raised when predictions would create an invalid official submission."""


def _validate_unit_interval(value: float, field: str, sample_id: str) -> None:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise SubmissionValidationError(
            f"{field} for {sample_id!r} must be finite and in [0, 1], got {value!r}"
        )


def validate_predictions(
    predictions: Sequence[Prediction],
    *,
    expected_test_ids: Collection[str],
    eligible_channels: Mapping[str, Collection[str]],
    onset_upper_bound: float = 60.0,
) -> None:
    """Validate IDs, numeric ranges, global threshold, onset, and Top-10."""

    if not predictions:
        raise SubmissionValidationError("Prediction collection is empty")
    if not math.isfinite(onset_upper_bound) or onset_upper_bound <= 0:
        raise ValueError("onset_upper_bound must be finite and positive")

    sample_ids = [prediction.sample_id for prediction in predictions]
    if len(sample_ids) != len(set(sample_ids)):
        duplicates = sorted({item for item in sample_ids if sample_ids.count(item) > 1})
        raise SubmissionValidationError(f"Duplicate prediction sample IDs: {duplicates}")

    expected = set(expected_test_ids)
    actual = set(sample_ids)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise SubmissionValidationError(
            f"Test ID coverage mismatch: missing={missing[:10]}, extra={extra[:10]}"
        )

    thresholds: set[float] = set()
    for prediction in predictions:
        if not prediction.sample_id:
            raise SubmissionValidationError("sample_id must not be empty")
        _validate_unit_interval(prediction.prob, "prob", prediction.sample_id)
        _validate_unit_interval(
            prediction.decision_threshold,
            "decision_threshold",
            prediction.sample_id,
        )
        thresholds.add(prediction.decision_threshold)
        if not math.isfinite(prediction.onset_time):
            raise SubmissionValidationError(
                f"onset_time for {prediction.sample_id!r} must be finite"
            )
        if not 0.0 <= prediction.onset_time < onset_upper_bound:
            raise SubmissionValidationError(
                f"onset_time for {prediction.sample_id!r} must be in "
                f"[0, {onset_upper_bound}), got {prediction.onset_time!r}"
            )

        channels = prediction.channels
        if prediction.predicted_label:
            if len(channels) != 10:
                raise SubmissionValidationError(
                    f"Positive prediction {prediction.sample_id!r} must contain exactly "
                    f"10 channels, got {len(channels)}"
                )
            if len(set(channels)) != 10 or any(not channel for channel in channels):
                raise SubmissionValidationError(
                    f"Positive prediction {prediction.sample_id!r} has empty or duplicate channels"
                )
            allowed = set(eligible_channels.get(prediction.sample_id, ()))
            invalid = [channel for channel in channels if channel not in allowed]
            if invalid:
                raise SubmissionValidationError(
                    f"Prediction {prediction.sample_id!r} contains ineligible channels: {invalid}"
                )
        elif channels:
            raise SubmissionValidationError(
                f"Negative prediction {prediction.sample_id!r} must leave Top-10 channels empty"
            )

    if len(thresholds) != 1:
        raise SubmissionValidationError(
            f"decision_threshold must be global; found {sorted(thresholds)}"
        )
