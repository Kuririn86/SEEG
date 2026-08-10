"""Command-line interface for the staged competition system."""

from __future__ import annotations

import argparse
from pathlib import Path

from seeg_detector.platform import load_flydata_resources

from .competition import run_smoke_submission


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the SEEG competition pipeline. The current stage-0 command "
            "only creates a deterministic contract-testing submission."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--data-root", type=Path, help="Local dataset root")
    source.add_argument("--source-id", help="FlyData resource ID in the competition platform")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Local output directory; omit when --source-id supplies FlyData.output_path()",
    )
    parser.add_argument(
        "--smoke-baseline",
        action="store_true",
        help="Explicitly enable the all-negative stage-0 contract baseline",
    )
    parser.add_argument(
        "--strict-full-data",
        action="store_true",
        help="Require every label row to have a corresponding training NPZ",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.smoke_baseline:
        raise SystemExit(
            "No trained model is connected yet. Pass --smoke-baseline only for contract testing."
        )

    if args.source_id:
        if args.output_dir is not None:
            raise SystemExit("--output-dir must be omitted when --source-id is used")
        resources = load_flydata_resources(args.source_id)
        data_root = resources.source_root
        output_dir = resources.output_dir
    else:
        if args.output_dir is None:
            raise SystemExit("--output-dir is required with --data-root")
        data_root = args.data_root
        output_dir = args.output_dir

    prediction_path = run_smoke_submission(
        data_root,
        output_dir,
        require_complete_train_labels=args.strict_full_data,
    )
    print(f"Stage-0 smoke submission written to {prediction_path}")
    return 0
