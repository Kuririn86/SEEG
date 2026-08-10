from __future__ import annotations

import unittest

import numpy as np

from seeg_detector.evaluation import evaluate_competition_proxy


class CompetitionMetricTests(unittest.TestCase):
    def test_perfect_predictions_have_unit_proxy_score(self) -> None:
        truth = tuple(f"C{index}" for index in range(10))
        metrics = evaluate_competition_proxy(
            labels=np.asarray([0, 1]),
            probabilities=np.asarray([0.1, 0.9]),
            threshold=0.5,
            true_onsets=np.asarray([0.0, 12.0]),
            predicted_onsets=np.asarray([0.0, 12.0]),
            true_channels=[(), truth],
            predicted_channels=[(), truth],
        )
        self.assertAlmostEqual(metrics.score_overlap_proxy, 1.0)
        self.assertAlmostEqual(metrics.score_rank_proxy, 1.0)

    def test_missed_positive_gets_sixty_second_onset_error(self) -> None:
        truth = tuple(f"C{index}" for index in range(10))
        metrics = evaluate_competition_proxy(
            labels=np.asarray([0, 1]),
            probabilities=np.asarray([0.1, 0.2]),
            threshold=0.5,
            true_onsets=np.asarray([0.0, 12.0]),
            predicted_onsets=np.asarray([0.0, 12.0]),
            true_channels=[(), truth],
            predicted_channels=[(), truth],
        )
        self.assertEqual(metrics.onset_mae, 60.0)
        self.assertEqual(metrics.onset_score, 0.0)
        self.assertEqual(metrics.channel_overlap, 0.0)
