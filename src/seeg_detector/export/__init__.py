"""Exports to external EEG analysis formats."""

from .eeglab import build_eeglab_struct, export_eeglab_set

__all__ = ["build_eeglab_struct", "export_eeglab_set"]

