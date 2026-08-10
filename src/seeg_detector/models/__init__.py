"""Model architectures and baselines."""

from .handcrafted import (
    HandcraftedRecord,
    extract_handcrafted_record,
    predict_onset,
    rank_channels,
)

__all__ = [
    "HandcraftedRecord",
    "extract_handcrafted_record",
    "predict_onset",
    "rank_channels",
]
