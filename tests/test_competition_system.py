from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from seeg_detector.data import discover_dataset, load_record_metadata
from seeg_detector.orchestration.competition import run_smoke_submission
from seeg_detector.submission import (
    PREDICTION_COLUMNS,
    Prediction,
    SubmissionValidationError,
    validate_predictions,
    write_prediction_csv,
)


class CompetitionSystemTests(unittest.TestCase):
    def _write_record(self, root: Path, sample_id: str, *, prefixed: bool = False) -> Path:
        clean = root / f"{sample_id}_clean.npz"
        np.savez(
            clean,
            signal=np.arange(48, dtype=np.float32).reshape(4, 12),
            channel_ids=np.array(["POL A1", "POL A2", "POL DC01", "EEG F3-Ref"]),
            raw_channel_indices=np.arange(4, dtype=np.int32),
            sampling_rate=np.array(4.0),
            valid_samples=np.array(8),
            sample_id=np.array(sample_id),
        )
        target = root / f"{sample_id}.npz"
        payload = clean.read_bytes()
        target.write_bytes((b"\x00" * 32 if prefixed else b"") + payload)
        clean.unlink()
        return target

    def _write_labels(self, root: Path, sample_ids: list[str]) -> None:
        columns = ["sample_id", "label", "onset_time", *[f"ch{i}" for i in range(1, 11)]]
        rows = [[sample_id, 0, 0.0, *("" for _ in range(10))] for sample_id in sample_ids]
        with (root / "label.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(columns)
            writer.writerows(rows)

    def test_metadata_reader_does_not_materialize_signal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_record(Path(directory), "test_000001", prefixed=True)
            import seeg_detector.data.io as io_module

            original = io_module._read_member

            def guarded_read(archive, name):
                if name == "signal.npy":
                    raise AssertionError("signal.npy should not be read by the metadata loader")
                return original(archive, name)

            with patch.object(io_module, "_read_member", side_effect=guarded_read):
                metadata = load_record_metadata(path)
            self.assertEqual(metadata.sample_id, "test_000001")
            self.assertEqual(metadata.channel_ids.tolist()[2], "POL DC01")
            self.assertEqual(metadata.valid_samples, 8)

    def test_discovers_resources_and_allows_partial_local_label_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_record(root, "train_000001")
            self._write_record(root, "test_000001")
            self._write_labels(root, ["train_000001", "train_000999"])
            manifest = discover_dataset(root, require_complete_train_labels=False)
            self.assertEqual(manifest.train_ids, ("train_000001",))
            self.assertEqual(manifest.test_ids, ("test_000001",))
            with self.assertRaisesRegex(ValueError, "Labels without training files"):
                discover_dataset(root, require_complete_train_labels=True)

    def test_submission_rejects_threshold_and_top10_contract_violations(self) -> None:
        eligible = {"test_000001": tuple(f"POL A{i}" for i in range(1, 12))}
        legal = Prediction(
            sample_id="test_000001",
            prob=0.9,
            decision_threshold=0.5,
            onset_time=12.25,
            channels=tuple(f"POL A{i}" for i in range(1, 11)),
        )
        validate_predictions(
            [legal],
            expected_test_ids={"test_000001"},
            eligible_channels=eligible,
        )

        illegal = Prediction(
            sample_id="test_000001",
            prob=0.9,
            decision_threshold=0.5,
            onset_time=12.25,
            channels=(*tuple(f"POL A{i}" for i in range(1, 10)), "POL DC01"),
        )
        with self.assertRaisesRegex(SubmissionValidationError, "ineligible channels"):
            validate_predictions(
                [illegal],
                expected_test_ids={"test_000001"},
                eligible_channels=eligible,
            )

    def test_writer_serializes_exact_schema_and_six_decimal_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            prediction = Prediction(
                sample_id="test_000001",
                prob=0.12345678,
                decision_threshold=0.5,
                onset_time=0.0,
            )
            path = write_prediction_csv(
                [prediction],
                directory,
                expected_test_ids={"test_000001"},
                eligible_channels={"test_000001": ()},
            )
            with path.open(newline="", encoding="utf-8") as stream:
                reader = csv.DictReader(stream)
                row = next(reader)
                self.assertEqual(tuple(reader.fieldnames or ()), PREDICTION_COLUMNS)
            self.assertEqual(row["prob"], "0.123457")
            self.assertEqual(row["decision_threshold"], "0.500000")
            self.assertTrue(all(row[f"ch{i}"] == "" for i in range(1, 11)))

    def test_writer_rejects_probability_that_flips_label_after_rounding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            prediction = Prediction(
                sample_id="test_000001",
                prob=0.4999996,
                decision_threshold=0.5,
                onset_time=0.0,
            )
            with self.assertRaisesRegex(
                SubmissionValidationError,
                "must contain exactly 10 channels",
            ):
                write_prediction_csv(
                    [prediction],
                    directory,
                    expected_test_ids={"test_000001"},
                    eligible_channels={"test_000001": ()},
                )
            self.assertFalse((Path(directory) / "prediction.csv").exists())

    def test_stage0_smoke_pipeline_runs_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_root = root / "data"
            output_root = root / "output"
            data_root.mkdir()
            self._write_record(data_root, "train_000001", prefixed=True)
            self._write_record(data_root, "test_000001", prefixed=True)
            self._write_labels(data_root, ["train_000001"])

            result = run_smoke_submission(data_root, output_root)
            self.assertEqual(result, output_root / "prediction.csv")
            with result.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([row["sample_id"] for row in rows], ["test_000001"])
            self.assertEqual(rows[0]["prob"], "0.000000")


if __name__ == "__main__":
    unittest.main()
