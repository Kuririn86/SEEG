"""Robust readers for the competition SEEG sample files.

Most supplied sample NPZ files contain a zero-filled prefix before the ZIP
payload. ``numpy.load(path)`` rejects those files, while ``zipfile.ZipFile``
correctly locates the concatenated ZIP archive. The reader below therefore
loads each NPY member explicitly and never enables pickle deserialization.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import zipfile

import numpy as np
import pandas as pd


REQUIRED_MEMBERS = {
    "signal.npy",
    "channel_ids.npy",
    "raw_channel_indices.npy",
    "sampling_rate.npy",
    "valid_samples.npy",
    "sample_id.npy",
}


@dataclass(frozen=True)
class NPZInspection:
    """Container-level information available without loading the signal."""

    path: Path
    members: tuple[str, ...]
    prefix_bytes: int
    standard_numpy_compatible: bool


@dataclass(frozen=True)
class SEEGRecord:
    """One competition recording and its channel metadata."""

    sample_id: str
    signal: np.ndarray
    channel_ids: np.ndarray
    raw_channel_indices: np.ndarray
    sampling_rate: float
    valid_samples: int
    source_path: Path

    @property
    def valid_signal(self) -> np.ndarray:
        """Return only samples declared valid by the file metadata."""

        return self.signal[:, : self.valid_samples]

    @property
    def duration_seconds(self) -> float:
        return self.valid_samples / self.sampling_rate


@dataclass(frozen=True)
class SEEGRecordMetadata:
    """Record metadata loaded without materializing the waveform array."""

    sample_id: str
    channel_ids: np.ndarray
    raw_channel_indices: np.ndarray
    sampling_rate: float
    valid_samples: int
    source_path: Path


def inspect_npz(path: str | Path) -> NPZInspection:
    """Inspect an NPZ container and detect any bytes before its ZIP payload."""

    resolved = Path(path)
    with zipfile.ZipFile(resolved) as archive:
        infos = archive.infolist()
        members = tuple(info.filename for info in infos)
        prefix_bytes = infos[0].header_offset if infos else 0
    with resolved.open("rb") as stream:
        standard_numpy_compatible = stream.read(4) == b"PK\x03\x04"
    return NPZInspection(
        path=resolved,
        members=members,
        prefix_bytes=prefix_bytes,
        standard_numpy_compatible=standard_numpy_compatible,
    )


def _read_member(archive: zipfile.ZipFile, name: str) -> np.ndarray:
    with archive.open(name) as stream:
        return np.lib.format.read_array(stream, allow_pickle=False)


def _read_member_shape(archive: zipfile.ZipFile, name: str) -> tuple[int, ...]:
    """Read an NPY header shape without loading the member payload."""

    with archive.open(name) as stream:
        version = np.lib.format.read_magic(stream)
        if version == (1, 0):
            shape, _, _ = np.lib.format.read_array_header_1_0(stream)
        elif version == (2, 0):
            shape, _, _ = np.lib.format.read_array_header_2_0(stream)
        else:
            raise ValueError(f"Unsupported NPY header version {version} in {name}")
    return tuple(int(dimension) for dimension in shape)


def _validate_metadata(
    *,
    resolved: Path,
    channel_ids: np.ndarray,
    raw_channel_indices: np.ndarray,
    sampling_rate: float,
    valid_samples: int,
    sample_id: str,
    signal_shape: tuple[int, int] | None = None,
) -> None:
    if channel_ids.ndim != 1 or raw_channel_indices.ndim != 1:
        raise ValueError("Channel metadata arrays must be one-dimensional")
    if len(channel_ids) != len(raw_channel_indices):
        raise ValueError("channel_ids and raw_channel_indices lengths differ")
    if signal_shape is not None:
        if len(channel_ids) != signal_shape[0]:
            raise ValueError("Channel metadata length does not match signal channel count")
        if not 0 < valid_samples <= signal_shape[1]:
            raise ValueError(
                f"valid_samples={valid_samples} is outside signal length {signal_shape[1]}"
            )
    elif valid_samples <= 0:
        raise ValueError(f"valid_samples must be positive, got {valid_samples}")
    if not np.isfinite(sampling_rate) or sampling_rate <= 0:
        raise ValueError(f"Invalid sampling rate: {sampling_rate}")
    if sample_id != resolved.stem:
        raise ValueError(f"sample_id={sample_id!r} does not match filename {resolved.stem!r}")


def load_record_metadata(path: str | Path) -> SEEGRecordMetadata:
    """Load channel and timing metadata without reading ``signal.npy``."""

    resolved = Path(path)
    metadata_members = REQUIRED_MEMBERS - {"signal.npy"}
    with zipfile.ZipFile(resolved) as archive:
        members = set(archive.namelist())
        missing = REQUIRED_MEMBERS - members
        if missing:
            raise ValueError(f"Missing NPZ members in {resolved.name}: {sorted(missing)}")
        arrays: dict[str, Any] = {
            name.removesuffix(".npy"): _read_member(archive, name)
            for name in metadata_members
        }
        signal_shape = _read_member_shape(archive, "signal.npy")

    channel_ids = np.asarray(arrays["channel_ids"])
    raw_channel_indices = np.asarray(arrays["raw_channel_indices"])
    sampling_rate = float(np.asarray(arrays["sampling_rate"]).item())
    valid_samples = int(np.asarray(arrays["valid_samples"]).item())
    sample_id = str(np.asarray(arrays["sample_id"]).item())
    if len(signal_shape) != 2:
        raise ValueError(f"signal must be 2-D, got shape {signal_shape}")
    _validate_metadata(
        resolved=resolved,
        channel_ids=channel_ids,
        raw_channel_indices=raw_channel_indices,
        sampling_rate=sampling_rate,
        valid_samples=valid_samples,
        sample_id=sample_id,
        signal_shape=(signal_shape[0], signal_shape[1]),
    )
    return SEEGRecordMetadata(
        sample_id=sample_id,
        channel_ids=channel_ids,
        raw_channel_indices=raw_channel_indices,
        sampling_rate=sampling_rate,
        valid_samples=valid_samples,
        source_path=resolved,
    )


def load_record(path: str | Path) -> SEEGRecord:
    """Load and validate one SEEG record, including prefixed NPZ files."""

    resolved = Path(path)
    with zipfile.ZipFile(resolved) as archive:
        members = set(archive.namelist())
        missing = REQUIRED_MEMBERS - members
        if missing:
            raise ValueError(f"Missing NPZ members in {resolved.name}: {sorted(missing)}")
        arrays: dict[str, Any] = {
            name.removesuffix(".npy"): _read_member(archive, name)
            for name in REQUIRED_MEMBERS
        }

    signal = np.asarray(arrays["signal"])
    channel_ids = np.asarray(arrays["channel_ids"])
    raw_channel_indices = np.asarray(arrays["raw_channel_indices"])
    sampling_rate = float(np.asarray(arrays["sampling_rate"]).item())
    valid_samples = int(np.asarray(arrays["valid_samples"]).item())
    sample_id = str(np.asarray(arrays["sample_id"]).item())

    if signal.ndim != 2:
        raise ValueError(f"signal must be 2-D, got shape {signal.shape}")
    _validate_metadata(
        resolved=resolved,
        channel_ids=channel_ids,
        raw_channel_indices=raw_channel_indices,
        sampling_rate=sampling_rate,
        valid_samples=valid_samples,
        sample_id=sample_id,
        signal_shape=signal.shape,
    )

    return SEEGRecord(
        sample_id=sample_id,
        signal=signal,
        channel_ids=channel_ids,
        raw_channel_indices=raw_channel_indices,
        sampling_rate=sampling_rate,
        valid_samples=valid_samples,
        source_path=resolved,
    )


def read_labels(path: str | Path) -> pd.DataFrame:
    """Read the UTF-8 BOM label table with stable column types."""

    labels = pd.read_csv(path, encoding="utf-8-sig")
    expected = ["sample_id", "label", "onset_time", *[f"ch{i}" for i in range(1, 11)]]
    if labels.columns.tolist() != expected:
        raise ValueError(f"Unexpected label columns: {labels.columns.tolist()}")
    labels["sample_id"] = labels["sample_id"].astype("string")
    labels["label"] = pd.to_numeric(labels["label"], errors="raise").astype("int8")
    labels["onset_time"] = pd.to_numeric(labels["onset_time"], errors="raise")
    return labels
