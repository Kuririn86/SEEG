"""Stage-0 competition pipeline used to prove the submission contract."""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

from seeg_detector.data.discovery import DatasetManifest, discover_dataset
from seeg_detector.data.io import load_record_metadata
from seeg_detector.data.naming import infer_channel_role
from seeg_detector.submission import Prediction, write_prediction_csv


def build_eligible_channel_map(
    manifest: DatasetManifest,
) -> dict[str, tuple[str, ...]]:
    """Read only test metadata and retain model-eligible channel IDs."""

    eligible: dict[str, tuple[str, ...]] = {}
    for path in manifest.test_files:
        metadata = load_record_metadata(path)
        labels = tuple(str(item) for item in metadata.channel_ids.tolist())
        candidates = tuple(
            label for label in labels if infer_channel_role(label) == "seeg_candidate"
        )
        eligible[metadata.sample_id] = candidates
    return eligible


def build_negative_smoke_predictions(
    test_ids: Collection[str],
    *,
    probability: float = 0.0,
    decision_threshold: float = 0.5,
) -> list[Prediction]:
    """Return a deterministic all-negative baseline for contract testing only."""

    return [
        Prediction(
            sample_id=sample_id,
            prob=probability,
            decision_threshold=decision_threshold,
            onset_time=0.0,
            channels=(),
        )
        for sample_id in sorted(test_ids)
    ]


def run_smoke_submission(
    data_root: str | Path,
    output_dir: str | Path,
    *,
    require_complete_train_labels: bool = False,
) -> Path:
    """Run stage 0 from resource discovery through an atomically written CSV.

    This deliberately does not claim algorithmic performance. It exists to
    validate runtime discovery, metadata compatibility, output coverage, and
    official serialization before a trained model is connected.
    """

    manifest = discover_dataset(
        data_root,
        require_labels=True,
        require_complete_train_labels=require_complete_train_labels,
    )
    eligible_channels = build_eligible_channel_map(manifest)
    predictions = build_negative_smoke_predictions(manifest.test_ids)
    return write_prediction_csv(
        predictions,
        output_dir,
        expected_test_ids=manifest.test_ids,
        eligible_channels=eligible_channels,
    )
