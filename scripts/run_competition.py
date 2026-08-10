#!/usr/bin/env python3
"""Non-interactive entry point for the staged SEEG competition system."""

from seeg_detector.orchestration.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
