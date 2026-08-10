"""Deterministic discovery and validation of competition dataset resources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .io import read_labels


@dataclass(frozen=True)
class DatasetManifest:
    """Resolved training, test, and label resources for one competition run."""

    root: Path
    train_files: tuple[Path, ...]
    test_files: tuple[Path, ...]
    label_files: tuple[Path, ...]
    labels: pd.DataFrame | None

    @property
    def train_ids(self) -> tuple[str, ...]:
        return tuple(path.stem for path in self.train_files)

    @property
    def test_ids(self) -> tuple[str, ...]:
        return tuple(path.stem for path in self.test_files)


def _index_unique(paths: list[Path], kind: str) -> tuple[Path, ...]:
    indexed: dict[str, Path] = {}
    for path in sorted(paths, key=lambda item: (item.stem, item.as_posix())):
        previous = indexed.get(path.stem)
        if previous is not None:
            raise ValueError(
                f"Duplicate {kind} sample ID {path.stem!r}: {previous} and {path}"
            )
        indexed[path.stem] = path
    return tuple(indexed[sample_id] for sample_id in sorted(indexed))


def _merge_labels(paths: tuple[Path, ...]) -> pd.DataFrame | None:
    if not paths:
        return None
    labels = pd.concat((read_labels(path) for path in paths), ignore_index=True)
    duplicated = labels["sample_id"].duplicated(keep=False)
    if duplicated.any():
        duplicate_ids = sorted(labels.loc[duplicated, "sample_id"].astype(str).unique())
        raise ValueError(f"Duplicate label sample IDs: {duplicate_ids}")
    return labels.sort_values("sample_id", kind="stable").reset_index(drop=True)


def discover_dataset(
    root: str | Path,
    *,
    require_labels: bool = True,
    require_complete_train_labels: bool = False,
) -> DatasetManifest:
    """Discover one-package or multi-package resources below ``root``.

    The local sample bundle contains labels for more training records than are
    physically present, so exact label/file equality is opt-in for production.
    """

    resolved = Path(root).resolve()
    if not resolved.is_dir():
        raise ValueError(f"Dataset root is not a directory: {resolved}")

    train_files = _index_unique(list(resolved.rglob("train_*.npz")), "training")
    test_files = _index_unique(list(resolved.rglob("test_*.npz")), "test")
    label_files = tuple(sorted(resolved.rglob("label.csv")))
    if not train_files:
        raise ValueError(f"No training NPZ files found below {resolved}")
    if not test_files:
        raise ValueError(f"No test NPZ files found below {resolved}")
    if require_labels and not label_files:
        raise ValueError(f"No label.csv files found below {resolved}")

    labels = _merge_labels(label_files)
    if labels is not None:
        known_train = set(path.stem for path in train_files)
        labeled = set(labels["sample_id"].astype(str))
        missing_label_rows = sorted(known_train - labeled)
        if missing_label_rows:
            raise ValueError(f"Training files without labels: {missing_label_rows}")
        if require_complete_train_labels:
            missing_files = sorted(labeled - known_train)
            if missing_files:
                preview = missing_files[:10]
                suffix = "..." if len(missing_files) > len(preview) else ""
                raise ValueError(f"Labels without training files: {preview}{suffix}")

    overlap = sorted(set(path.stem for path in train_files) & set(path.stem for path in test_files))
    if overlap:
        raise ValueError(f"Sample IDs appear in both training and test resources: {overlap}")

    return DatasetManifest(
        root=resolved,
        train_files=train_files,
        test_files=test_files,
        label_files=label_files,
        labels=labels,
    )
