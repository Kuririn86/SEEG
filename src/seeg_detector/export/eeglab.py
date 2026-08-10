"""Export competition recordings as one-file EEGLAB ``.set`` datasets."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import savemat

from seeg_detector.data import SEEGRecord, infer_channel_role


EVENT_DTYPE = np.dtype(
    [
        ("type", object),
        ("latency", object),
        ("duration", object),
        ("urevent", object),
        ("code", object),
        ("value", object),
        ("onset_seconds", object),
        ("source", object),
    ]
)
UREVENT_DTYPE = np.dtype(
    [
        ("type", object),
        ("latency", object),
        ("duration", object),
        ("code", object),
        ("value", object),
        ("onset_seconds", object),
        ("source", object),
    ]
)
CHANLOC_DTYPE = np.dtype(
    [
        ("labels", object),
        ("original_label", object),
        ("raw_index", object),
        ("urchan", object),
        ("type", object),
    ]
)


def onset_to_eeglab_latency(onset_seconds: float, sampling_rate: float) -> float:
    """Convert seconds from record start to EEGLAB's one-based sample latency."""

    return float(onset_seconds * sampling_rate + 1.0)


def _event_struct(onset_seconds: float | None, sampling_rate: float) -> tuple[np.ndarray, np.ndarray]:
    if onset_seconds is None:
        return np.empty((0, 0), dtype=EVENT_DTYPE), np.empty((0, 0), dtype=UREVENT_DTYPE)

    latency = onset_to_eeglab_latency(onset_seconds, sampling_rate)
    event = np.empty((1, 1), dtype=EVENT_DTYPE)
    event[0, 0] = (
        "seizure_onset",
        latency,
        0.0,
        1.0,
        "S1",
        1.0,
        float(onset_seconds),
        "label.csv",
    )
    urevent = np.empty((1, 1), dtype=UREVENT_DTYPE)
    urevent[0, 0] = (
        "seizure_onset",
        latency,
        0.0,
        "S1",
        1.0,
        float(onset_seconds),
        "label.csv",
    )
    return event, urevent


def _channel_locations(record: SEEGRecord) -> np.ndarray:
    chanlocs = np.empty((1, len(record.channel_ids)), dtype=CHANLOC_DTYPE)
    for index, (label, raw_index) in enumerate(
        zip(record.channel_ids.tolist(), record.raw_channel_indices.tolist())
    ):
        role = infer_channel_role(str(label))
        chanlocs[0, index] = (
            str(label),
            str(label),
            float(raw_index),
            float(index + 1),
            "SEEG" if role == "seeg_candidate" else "MISC",
        )
    return chanlocs


def build_eeglab_struct(
    record: SEEGRecord,
    output_path: str | Path,
    onset_seconds: float | None,
) -> dict[str, object]:
    """Build the MATLAB ``EEG`` structure expected by EEGLAB."""

    output = Path(output_path).resolve()
    signal = np.ascontiguousarray(record.valid_signal, dtype=np.float32)
    pnts = signal.shape[1]
    event, urevent = _event_struct(onset_seconds, record.sampling_rate)
    xmax = (pnts - 1) / record.sampling_rate
    return {
        "setname": record.sample_id,
        "filename": output.name,
        "filepath": str(output.parent),
        "subject": "",
        "group": "",
        "condition": "",
        "session": [],
        "comments": (
            "Converted from competition NPZ. Signal amplitude units, electrode coordinates, "
            "patient identity, and reference convention were not provided. POL DC01-DC16 are "
            "marked MISC because they are auxiliary DC inputs rather than implanted contacts."
        ),
        "nbchan": float(signal.shape[0]),
        "trials": 1.0,
        "pnts": float(pnts),
        "srate": float(record.sampling_rate),
        "xmin": 0.0,
        "xmax": float(xmax),
        "times": np.arange(pnts, dtype=np.float64) / record.sampling_rate * 1000.0,
        "data": signal,
        "icaact": np.empty((0, 0)),
        "icawinv": np.empty((0, 0)),
        "icasphere": np.empty((0, 0)),
        "icaweights": np.empty((0, 0)),
        "icachansind": np.empty((0, 0)),
        "chanlocs": _channel_locations(record),
        "urchanlocs": np.empty((0, 0)),
        "chaninfo": {},
        "ref": "unknown",
        "event": event,
        "urevent": urevent,
        "eventdescription": np.empty((0, 0), dtype=object),
        "epoch": np.empty((0, 0)),
        "epochdescription": np.empty((0, 0), dtype=object),
        "reject": {},
        "stats": {},
        "specdata": np.empty((0, 0)),
        "specicaact": np.empty((0, 0)),
        "splinefile": "",
        "icasplinefile": "",
        "dipfit": {},
        "history": "",
        "saved": "yes",
        "etc": {
            "source_format": "competition_npz",
            "source_sample_id": record.sample_id,
            "original_channel_ids": np.asarray(record.channel_ids, dtype=object),
            "channel_roles": np.asarray(
                [infer_channel_role(str(label)) for label in record.channel_ids.tolist()],
                dtype=object,
            ),
            "raw_channel_indices": np.asarray(record.raw_channel_indices, dtype=np.int32),
            "valid_samples": float(record.valid_samples),
            "onset_seconds": float(onset_seconds) if onset_seconds is not None else np.nan,
        },
        "run": [],
        "datfile": "",
    }


def export_eeglab_set(
    record: SEEGRecord,
    output_path: str | Path,
    onset_seconds: float | None = None,
) -> Path:
    """Write an EEGLAB-compatible MATLAB v5 ``.set`` file."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    eeg = build_eeglab_struct(record, output, onset_seconds)
    savemat(
        output,
        {"EEG": eeg},
        appendmat=False,
        do_compression=False,
        long_field_names=True,
        oned_as="row",
    )
    return output
