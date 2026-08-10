"""End-to-end training and competition orchestration."""

from .competition import build_eligible_channel_map, run_smoke_submission

__all__ = ["build_eligible_channel_map", "run_smoke_submission"]
