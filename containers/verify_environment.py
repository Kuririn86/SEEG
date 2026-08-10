"""Fail-fast verification for the SEEG Apptainer environment."""

from __future__ import annotations

import argparse
import importlib
import json
import platform


EXPECTED_VERSIONS = {
    "numpy": "1.26.4",
    "pandas": "2.3.3",
    "scipy": "1.15.3",
    "sklearn": "1.7.2",
    "torch": "2.7.1+cu118",
    "torchvision": "0.22.1+cu118",
    "torchaudio": "2.7.1+cu118",
    "pytorch_lightning": "2.6.5",
    "torch_geometric": "2.8.0.post1",
    "mne": "1.12.1",
    "pywt": "1.8.0",
    "h5py": "3.16.0",
    "joblib": "1.5.3",
    "lightgbm": "4.7.0",
    "xgboost": "3.2.0",
    "catboost": "1.2.10",
    "optuna": "4.9.0",
    "matplotlib": "3.10.9",
    "seaborn": "0.13.2",
    "numba": "0.66.0",
}

EXTRA_MODULES = (
    "jupyterlab",
    "ipykernel",
    "nbclient",
    "nbformat",
    "pytest",
    "ruff",
    "tensorboard",
    "captum",
    "onnx",
    "onnxruntime",
    "psutil",
    "yaml",
)


def normalized_version(module_name: str, module: object) -> str:
    version = str(getattr(module, "__version__", "unknown"))
    if module_name == "catboost":
        return version
    return version


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-cuda",
        action="store_true",
        help="Fail unless Apptainer was started with working NVIDIA passthrough",
    )
    args = parser.parse_args()

    versions: dict[str, str] = {}
    mismatches: dict[str, dict[str, str]] = {}
    for module_name, expected in EXPECTED_VERSIONS.items():
        module = importlib.import_module(module_name)
        actual = normalized_version(module_name, module)
        versions[module_name] = actual
        if actual != expected:
            mismatches[module_name] = {"expected": expected, "actual": actual}

    for module_name in EXTRA_MODULES:
        module = importlib.import_module(module_name)
        versions[module_name] = normalized_version(module_name, module)

    torch = importlib.import_module("torch")
    cuda_available = bool(torch.cuda.is_available())
    report = {
        "python": platform.python_version(),
        "versions": versions,
        "torch_cuda_build": torch.version.cuda,
        "cuda_available": cuda_available,
        "cuda_device": torch.cuda.get_device_name(0) if cuda_available else None,
        "mismatches": mismatches,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if mismatches:
        raise SystemExit(f"Version mismatches: {mismatches}")
    if args.require_cuda and not cuda_available:
        raise SystemExit("CUDA is unavailable; run the image with apptainer exec --nv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
