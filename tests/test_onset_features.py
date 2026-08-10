from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from seeg_detector.analysis.onset_features import (
    GLOBAL_PROPAGATION_FEATURES,
    OnsetFeatureConfig,
    evaluate_record_alignment,
    extract_priority_features,
)
from seeg_detector.data import SEEGRecord


class OnsetFeatureTests(unittest.TestCase):
    def _synthetic_record(self) -> SEEGRecord:
        sampling_rate = 2000.0
        duration_seconds = 8.0
        onset_seconds = 5.0
        time = np.arange(int(duration_seconds * sampling_rate)) / sampling_rate
        generator = np.random.default_rng(20260810)
        signal = generator.normal(0.0, 0.15, size=(13, time.size)).astype(np.float32)
        ictal = time >= onset_seconds
        for channel in range(10):
            signal[channel, ~ictal] += (
                1.0 * np.sin(2 * np.pi * 5.0 * time[~ictal])
            ).astype(np.float32)
            signal[channel, ictal] += (
                2.0 * np.sin(2 * np.pi * 100.0 * time[ictal])
            ).astype(np.float32)
        signal[-1] = (time >= onset_seconds).astype(np.float32)
        channel_ids = np.asarray(
            [f"POL A{index:02d}" for index in range(1, 13)] + ["POL DC01"]
        )
        return SEEGRecord(
            sample_id="synthetic",
            signal=signal,
            channel_ids=channel_ids,
            raw_channel_indices=np.arange(channel_ids.size),
            sampling_rate=sampling_rate,
            valid_samples=time.size,
            source_path=Path("synthetic.npz"),
        )

    def test_extracts_causal_features_and_excludes_dc_input(self) -> None:
        record = self._synthetic_record()
        times, indices, features = extract_priority_features(record)
        self.assertEqual(indices.size, 12)
        self.assertNotIn(12, indices.tolist())
        self.assertAlmostEqual(times[0], 0.5)
        self.assertTrue(np.all(np.diff(times) > 0))
        self.assertEqual(features["high_gamma_power"].shape, (12, times.size))

    def test_high_gamma_step_aligns_with_synthetic_onset_and_top10(self) -> None:
        record = self._synthetic_record()
        official = record.channel_ids[:10].tolist()
        alignment, _, channels = evaluate_record_alignment(
            record,
            onset_seconds=5.0,
            official_top10=official,
            config=OnsetFeatureConfig(channel_chunk_size=4),
        )
        result = alignment.query(
            "feature == 'high_gamma_power' and channel_set == 'all'"
        ).iloc[0]
        self.assertLessEqual(result["absolute_timing_error_seconds"], 0.5)
        self.assertGreater(result["early_contrast"], 0.25)
        self.assertEqual(result["top10_overlap"], 10)
        selected = channels.query("feature == 'high_gamma_power'").nsmallest(
            10, "response_rank"
        )
        self.assertTrue(selected["official_top10"].all())

    def test_propagation_features_are_scoped_and_align_with_recruitment(self) -> None:
        record = self._synthetic_record()
        alignment, _, channels = evaluate_record_alignment(
            record,
            onset_seconds=5.0,
            official_top10=record.channel_ids[:10].tolist(),
            config=OnsetFeatureConfig(
                channel_chunk_size=4,
                include_propagation_features=True,
            ),
        )
        all_features = alignment.query("channel_set == 'all'")
        self.assertEqual(all_features["feature"].nunique(), 33)
        global_rows = all_features[
            all_features["feature"].isin(GLOBAL_PROPAGATION_FEATURES)
        ]
        self.assertTrue(global_rows["top10_overlap"].isna().all())
        self.assertTrue(global_rows["feature_scope"].eq("global_propagation").all())
        slope = global_rows.query("feature == 'recruitment_fraction_slope'").iloc[0]
        self.assertLessEqual(slope["absolute_timing_error_seconds"], 0.5)
        self.assertNotIn(
            "recruitment_fraction_slope", set(channels["feature"].unique())
        )


if __name__ == "__main__":
    unittest.main()
