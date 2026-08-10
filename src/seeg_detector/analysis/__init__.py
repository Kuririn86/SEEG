"""Exploratory analysis and data-quality profiling."""

from .profile import build_profile, write_profile_report
from .line_noise import (
    apply_zero_phase_notches,
    compute_line_noise_metrics,
    summarize_line_noise,
)
from .auxiliary_channels import (
    DC_LSB_STORED_UNIT,
    compute_auxiliary_channel_metrics,
    summarize_auxiliary_channels,
)

__all__ = [
    "apply_zero_phase_notches",
    "build_profile",
    "compute_auxiliary_channel_metrics",
    "compute_line_noise_metrics",
    "DC_LSB_STORED_UNIT",
    "summarize_line_noise",
    "summarize_auxiliary_channels",
    "write_profile_report",
]
