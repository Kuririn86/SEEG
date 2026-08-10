#!/usr/bin/env python3
"""Convert available competition NPZ recordings into EEGLAB .set files."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from seeg_detector.data import load_record, read_labels
from seeg_detector.export.eeglab import export_eeglab_set, onset_to_eeglab_latency


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("Dataset/sampleData"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/eeglab_sample"))
    parser.add_argument("--split", choices=("train", "test", "all"), default="train")
    parser.add_argument(
        "--sample-id",
        action="append",
        help="Export only this sample ID; repeat to export several. Overrides --split.",
    )
    args = parser.parse_args()

    labels = read_labels(args.data_root / "label.csv").set_index("sample_id")
    available = sorted(args.data_root.glob("*.npz"))
    if args.sample_id:
        requested = set(args.sample_id)
        paths = [path for path in available if path.stem in requested]
        missing = requested - {path.stem for path in paths}
        if missing:
            raise FileNotFoundError(f"Sample NPZ not found: {sorted(missing)}")
    else:
        paths = [
            path
            for path in available
            if args.split == "all" or path.stem.startswith(f"{args.split}_")
        ]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, object]] = []
    for path in paths:
        sample_id = path.stem
        record = load_record(path)
        label = None
        onset_seconds = None
        if sample_id in labels.index:
            label = int(labels.loc[sample_id, "label"])
            if label == 1:
                onset_seconds = float(labels.loc[sample_id, "onset_time"])
        output = export_eeglab_set(
            record,
            args.output_dir / f"{sample_id}.set",
            onset_seconds=onset_seconds,
        )
        manifest_rows.append(
            {
                "sample_id": sample_id,
                "split": sample_id.split("_", 1)[0],
                "label": label,
                "channels": record.signal.shape[0],
                "sampling_rate_hz": record.sampling_rate,
                "points": record.valid_samples,
                "duration_seconds": record.duration_seconds,
                "event_type": "seizure_onset" if onset_seconds is not None else "",
                "onset_seconds": onset_seconds,
                "event_latency_samples": (
                    onset_to_eeglab_latency(onset_seconds, record.sampling_rate)
                    if onset_seconds is not None
                    else None
                ),
                "set_file": output.name,
                "set_size_bytes": output.stat().st_size,
            }
        )
        marker = f" onset={onset_seconds:.6f}s" if onset_seconds is not None else ""
        print(f"Wrote {output}{marker}")

    manifest = pd.DataFrame(manifest_rows)
    manifest_path = args.output_dir / "manifest.csv"
    manifest.to_csv(manifest_path, index=False)
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()

