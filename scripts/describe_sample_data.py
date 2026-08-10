#!/usr/bin/env python3
"""Profile the supplied sample dataset and write reproducible artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from seeg_detector.analysis import build_profile, write_profile_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("Dataset/sampleData"))
    parser.add_argument(
        "--report", type=Path, default=Path("reports/sample_data_description.md")
    )
    parser.add_argument(
        "--file-profile", type=Path, default=Path("reports/sample_file_profile.csv")
    )
    args = parser.parse_args()

    profile = build_profile(args.data_root)
    write_profile_report(profile, args.report)
    args.file_profile.parent.mkdir(parents=True, exist_ok=True)
    profile.files.drop(columns=["channel_schema"]).to_csv(args.file_profile, index=False)
    print(f"Wrote {args.report}")
    print(f"Wrote {args.file_profile}")


if __name__ == "__main__":
    main()

