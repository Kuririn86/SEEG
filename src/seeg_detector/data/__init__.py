"""Dataset loading and validation utilities."""

from .discovery import DatasetManifest, discover_dataset
from .io import (
    NPZInspection,
    SEEGRecord,
    SEEGRecordMetadata,
    inspect_npz,
    load_record,
    load_record_metadata,
    read_labels,
)
from .naming import (
    ParsedChannelId,
    infer_channel_role,
    is_auxiliary_dc_channel,
    neural_channel_indices,
    parse_channel_id,
)

__all__ = [
    "NPZInspection",
    "DatasetManifest",
    "ParsedChannelId",
    "SEEGRecord",
    "SEEGRecordMetadata",
    "inspect_npz",
    "discover_dataset",
    "infer_channel_role",
    "is_auxiliary_dc_channel",
    "neural_channel_indices",
    "load_record",
    "load_record_metadata",
    "parse_channel_id",
    "read_labels",
]
