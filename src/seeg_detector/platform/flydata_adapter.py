"""Thin, lazily imported adapter around the competition ``flydata`` package."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FlyDataResources:
    source_id: str
    source_root: Path
    output_dir: Path
    resource_tree: Any


def load_flydata_resources(source_id: str) -> FlyDataResources:
    """Load one platform resource without making core modules depend on FlyData."""

    if not source_id.strip():
        raise ValueError("source_id must not be empty")
    try:
        from flydata import FlyData
    except ImportError as error:
        raise RuntimeError(
            "flydata is available only in the competition environment; use --data-root locally"
        ) from error

    handler = FlyData()
    resource_tree = handler.load_file(source_id)
    source_root = Path("data_source") / source_id
    output_dir = Path(handler.output_path())
    if not source_root.is_dir():
        raise RuntimeError(f"FlyData did not materialize the expected source root: {source_root}")
    return FlyDataResources(
        source_id=source_id,
        source_root=source_root.resolve(),
        output_dir=output_dir.resolve(),
        resource_tree=resource_tree,
    )
