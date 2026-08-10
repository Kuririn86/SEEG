from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from seeg_detector.data import (
    infer_channel_role,
    inspect_npz,
    is_auxiliary_dc_channel,
    load_record,
    neural_channel_indices,
    parse_channel_id,
)
from seeg_detector.export.eeglab import build_eeglab_struct, onset_to_eeglab_latency
from seeg_detector.analysis.line_noise import apply_zero_phase_notches


class DataIOTests(unittest.TestCase):
    def _make_record(self, directory: Path, prefixed: bool) -> Path:
        clean_path = directory / "sample_000001_clean.npz"
        np.savez(
            clean_path,
            signal=np.arange(24, dtype=np.float32).reshape(2, 12),
            channel_ids=np.array(["A1", "A2"]),
            raw_channel_indices=np.array([0, 1], dtype=np.int32),
            sampling_rate=np.array(4.0),
            valid_samples=np.array(8),
            sample_id=np.array("sample_000001"),
        )
        target = directory / "sample_000001.npz"
        payload = clean_path.read_bytes()
        target.write_bytes((b"\x00" * 64 if prefixed else b"") + payload)
        return target

    def test_loads_standard_npz_and_honors_valid_samples(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._make_record(Path(directory), prefixed=False)
            record = load_record(path)
            self.assertEqual(record.valid_signal.shape, (2, 8))
            self.assertEqual(record.duration_seconds, 2.0)
            self.assertTrue(inspect_npz(path).standard_numpy_compatible)

    def test_loads_zero_prefixed_npz(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._make_record(Path(directory), prefixed=True)
            record = load_record(path)
            inspection = inspect_npz(path)
            self.assertEqual(record.sample_id, "sample_000001")
            self.assertEqual(inspection.prefix_bytes, 64)
            self.assertFalse(inspection.standard_numpy_compatible)

    def test_eeglab_onset_latency_is_one_based(self) -> None:
        self.assertAlmostEqual(onset_to_eeglab_latency(13.843409, 2000.0), 27687.818)

    def test_builds_eeglab_event_and_empty_negative_event_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._make_record(Path(directory), prefixed=True)
            record = load_record(path)
            positive = build_eeglab_struct(record, Path(directory) / "positive.set", 1.25)
            negative = build_eeglab_struct(record, Path(directory) / "negative.set", None)
            self.assertEqual(positive["event"][0, 0]["type"], "seizure_onset")
            self.assertEqual(positive["event"][0, 0]["latency"], 6.0)
            self.assertEqual(negative["event"].size, 0)

    def test_parses_channel_id_without_losing_case_or_leading_zeros(self) -> None:
        parsed = parse_channel_id("POL pMC12")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.electrode_code, "pMC")
        self.assertEqual(parsed.contact_number, 12)

        dc = parse_channel_id("POL DC01")
        self.assertEqual(dc.contact_text, "01")
        self.assertEqual(dc.contact_number, 1)

        referenced = parse_channel_id("EEG F3-Ref")
        self.assertEqual(referenced.source_prefix, "EEG")
        self.assertEqual(referenced.reference_tag, "-Ref")
        self.assertIsNone(parse_channel_id("POL E"))

    def test_zero_phase_notch_reduces_50_hz_without_shifting_signal(self) -> None:
        sampling_rate = 2000.0
        time = np.arange(0.0, 4.0, 1.0 / sampling_rate)
        clean_component = np.sin(2 * np.pi * 12.0 * time)
        contaminated = clean_component + 3.0 * np.sin(2 * np.pi * 50.0 * time)
        filtered = apply_zero_phase_notches(
            contaminated,
            sampling_rate,
            frequencies=(50.0,),
            quality_factor=50.0,
        )
        projection_before = abs(np.vdot(contaminated, np.exp(2j * np.pi * 50.0 * time)))
        projection_after = abs(np.vdot(filtered, np.exp(2j * np.pi * 50.0 * time)))
        self.assertLess(projection_after, projection_before * 0.05)
        # Ignore IIR settling at the record edges when checking waveform fidelity.
        central = slice(int(sampling_rate), -int(sampling_rate))
        self.assertGreater(
            np.corrcoef(clean_component[central], filtered[central])[0, 1],
            0.99,
        )

    def test_dc_inputs_are_separated_from_seeg_candidate_channels(self) -> None:
        self.assertTrue(is_auxiliary_dc_channel("POL DC01"))
        self.assertTrue(is_auxiliary_dc_channel("POL DC16"))
        self.assertFalse(is_auxiliary_dc_channel("POL DC17"))
        self.assertEqual(infer_channel_role("POL DC08"), "auxiliary_dc")
        self.assertEqual(infer_channel_role("POL AC08"), "seeg_candidate")
        self.assertEqual(infer_channel_role("POL E"), "unknown")
        self.assertEqual(
            neural_channel_indices(["POL AC08", "POL DC08", "EEG F3-Ref", "POL E"]),
            [0, 2],
        )


if __name__ == "__main__":
    unittest.main()
