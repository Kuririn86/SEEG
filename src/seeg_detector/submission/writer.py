"""Atomic serialization of a validated official prediction file."""

from __future__ import annotations

import csv
import os
from pathlib import Path
import tempfile
from collections.abc import Collection, Mapping, Sequence

from .schema import PREDICTION_COLUMNS, Prediction
from .validator import validate_predictions


def _prediction_row(prediction: Prediction) -> dict[str, str]:
    padded_channels = (*prediction.channels, *("" for _ in range(10 - len(prediction.channels))))
    row = {
        "sample_id": prediction.sample_id,
        "prob": f"{prediction.prob:.6f}",
        "decision_threshold": f"{prediction.decision_threshold:.6f}",
        "onset_time": f"{prediction.onset_time:.6f}",
    }
    row.update({f"ch{index}": value for index, value in enumerate(padded_channels, start=1)})
    return row


def _prediction_from_row(row: dict[str, str]) -> Prediction:
    channels = tuple(row[f"ch{index}"] for index in range(1, 11) if row[f"ch{index}"])
    return Prediction(
        sample_id=row["sample_id"],
        prob=float(row["prob"]),
        decision_threshold=float(row["decision_threshold"]),
        onset_time=float(row["onset_time"]),
        channels=channels,
    )


def write_prediction_csv(
    predictions: Sequence[Prediction],
    output_dir: str | Path,
    *,
    expected_test_ids: Collection[str],
    eligible_channels: Mapping[str, Collection[str]],
    onset_upper_bound: float = 60.0,
) -> Path:
    """Validate, write to a temporary file, reread, and atomically replace."""

    validate_predictions(
        predictions,
        expected_test_ids=expected_test_ids,
        eligible_channels=eligible_channels,
        onset_upper_bound=onset_upper_bound,
    )
    resolved_output = Path(output_dir).resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)
    target = resolved_output / "prediction.csv"

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=".prediction.", suffix=".csv.tmp", dir=resolved_output
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=PREDICTION_COLUMNS, lineterminator="\n")
            writer.writeheader()
            for prediction in predictions:
                writer.writerow(_prediction_row(prediction))
            stream.flush()
            os.fsync(stream.fileno())

        with temporary.open("r", newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
            if stream.seekable():
                stream.seek(0)
            fieldnames = tuple(rows[0].keys()) if rows else ()
        if fieldnames != PREDICTION_COLUMNS:
            raise RuntimeError(f"Serialized prediction columns changed: {fieldnames}")
        if len(rows) != len(predictions):
            raise RuntimeError("Serialized prediction row count changed")
        if [row["sample_id"] for row in rows] != [item.sample_id for item in predictions]:
            raise RuntimeError("Serialized prediction sample order changed")
        round_tripped = [_prediction_from_row(row) for row in rows]
        validate_predictions(
            round_tripped,
            expected_test_ids=expected_test_ids,
            eligible_channels=eligible_channels,
            onset_upper_bound=onset_upper_bound,
        )

        os.replace(temporary, target)
        return target
    finally:
        if temporary.exists():
            temporary.unlink()
