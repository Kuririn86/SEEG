"""Typed representation of one official prediction row."""

from __future__ import annotations

from dataclasses import dataclass


CHANNEL_COLUMNS = tuple(f"ch{index}" for index in range(1, 11))
PREDICTION_COLUMNS = (
    "sample_id",
    "prob",
    "decision_threshold",
    "onset_time",
    *CHANNEL_COLUMNS,
)


@dataclass(frozen=True)
class Prediction:
    """One model prediction before CSV serialization."""

    sample_id: str
    prob: float
    decision_threshold: float
    onset_time: float
    channels: tuple[str, ...] = ()

    @property
    def predicted_label(self) -> int:
        return int(self.prob >= self.decision_threshold)
