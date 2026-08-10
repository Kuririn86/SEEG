#!/usr/bin/env python3
"""Train and evaluate the M0 handcrafted baseline on the local sample bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from seeg_detector.data import load_record_metadata, read_labels
from seeg_detector.evaluation import evaluate_competition_proxy
from seeg_detector.models import (
    HandcraftedRecord,
    extract_handcrafted_record,
    predict_onset,
    rank_channels,
)


def _schema_group(path: Path) -> str:
    metadata = load_record_metadata(path)
    payload = "\0".join(str(item) for item in metadata.channel_ids).encode()
    return hashlib.sha1(payload).hexdigest()[:8]


def _classifier(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    C=0.1,
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=seed,
                ),
            ),
        ]
    )


def _select_onset_threshold(
    records: list[HandcraftedRecord], labels: np.ndarray, onsets: np.ndarray
) -> float:
    positive_indices = np.flatnonzero(labels == 1)
    candidates = np.linspace(0.5, 8.0, 31)
    errors = []
    for threshold in candidates:
        predictions = np.asarray(
            [predict_onset(records[index], threshold) for index in positive_indices]
        )
        errors.append(float(np.mean(np.abs(predictions - onsets[positive_indices]))))
    return float(candidates[int(np.argmin(errors))])


def _extract_all(paths: list[Path]) -> list[HandcraftedRecord]:
    records: list[HandcraftedRecord] = []
    for index, path in enumerate(paths, start=1):
        print(f"[{index:02d}/{len(paths):02d}] extracting {path.name}", flush=True)
        records.append(extract_handcrafted_record(path))
    return records


def _write_report(
    path: Path,
    metrics: dict[str, float],
    fold_rows: list[dict[str, object]],
    train_count: int,
    test_count: int,
    positive_count: int,
    elapsed: float,
    cuda_available: bool,
    cuda_device: str | None,
) -> None:
    lines = [
        "# 样例数据 M0 试训练报告",
        "",
        "## 结论边界",
        "",
        f"本次使用本地 {train_count} 个有标签样例（阳性 {positive_count}、阴性 {train_count - positive_count}）进行按通道布局分组留一折外评估，并对 {test_count} 个无标签 `test_*` 样例生成预测。由于赛事样例测试文件不提供标签，下面分数不是平台测试分，也不能外推到 924 个正式测试样本。",
        "",
        "赛事材料未公布 ChannelScore 的精确排序公式，因此同时报告无序 Top-10 重合率和显式定义的 rank-aware 代理分；其他分量按公开公式计算。",
        "",
        "## 折外指标",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
    ]
    display = (
        ("AUC", "auc"),
        ("F1", "f1"),
        ("Sensitivity", "sensitivity"),
        ("Specificity", "specificity"),
        ("Top-10 overlap proxy", "channel_overlap"),
        ("Top-10 rank-aware proxy", "channel_rank_proxy"),
        ("Onset MAE (s)", "onset_mae"),
        ("Onset score", "onset_score"),
        ("Total score (overlap proxy)", "score_overlap_proxy"),
        ("Total score (rank proxy)", "score_rank_proxy"),
    )
    lines.extend(f"| {label} | {metrics[key]:.6f} |" for label, key in display)
    lines.extend(
        [
            "",
            "## 分组折",
            "",
            "| Fold | 留出布局 | 训练数 | 测试数 | 阳性数 | onset threshold |",
            "|---:|---|---:|---:|---:|---:|",
        ]
    )
    for row in fold_rows:
        lines.append(
            f"| {row['fold']} | `{row['held_out_group']}` | {row['train_size']} | "
            f"{row['test_size']} | {row['test_positives']} | {row['onset_threshold']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## 运行环境",
            "",
            f"- Python：{platform.python_version()}",
            f"- CUDA 可用：{cuda_available}",
            f"- GPU：{cuda_device or '未使用/不可见'}",
            f"- 总耗时：{elapsed:.2f} 秒",
            "- 分类阈值：0.5（预先固定，没有用折外标签调参）",
            "- 分组依据：完全相同的官方通道 ID 序列；它只是患者映射缺失时的保守代理。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("Dataset/sampleData"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/sample_baseline_trial"))
    parser.add_argument("--seed", type=int, default=20260810)
    args = parser.parse_args()

    started = time.perf_counter()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    train_paths = sorted(args.data_root.glob("train_*.npz"))
    test_paths = sorted(args.data_root.glob("test_*.npz"))
    if not train_paths or not test_paths:
        raise ValueError("Both train_*.npz and test_*.npz are required")

    labels_table = read_labels(args.data_root / "label.csv").set_index("sample_id")
    train_ids = [path.stem for path in train_paths]
    sample_labels = labels_table.loc[train_ids]
    labels = sample_labels["label"].to_numpy(dtype=np.int64)
    onsets = sample_labels["onset_time"].to_numpy(dtype=np.float64)
    true_channels = [
        tuple(str(row[f"ch{i}"]) for i in range(1, 11)) if int(row["label"]) == 1 else ()
        for _, row in sample_labels.iterrows()
    ]

    all_paths = train_paths + test_paths
    extracted = _extract_all(all_paths)
    train_records = extracted[: len(train_paths)]
    test_records = extracted[len(train_paths) :]
    feature_names = train_records[0].feature_names
    if any(record.feature_names != feature_names for record in extracted):
        raise RuntimeError("Feature schemas differ between records")
    train_features = np.stack([record.features for record in train_records])
    test_features = np.stack([record.features for record in test_records])
    groups = np.asarray([_schema_group(path) for path in train_paths])

    probabilities = np.zeros(len(train_records), dtype=np.float64)
    predicted_onsets = np.zeros(len(train_records), dtype=np.float64)
    predicted_channels: list[tuple[str, ...]] = [() for _ in train_records]
    fold_assignments = np.zeros(len(train_records), dtype=np.int64)
    fold_rows: list[dict[str, object]] = []
    logo = LeaveOneGroupOut()
    onset_thresholds: list[float] = []
    for fold, (train_index, test_index) in enumerate(
        logo.split(train_features, labels, groups), start=1
    ):
        model = _classifier(args.seed + fold)
        model.fit(train_features[train_index], labels[train_index])
        probabilities[test_index] = model.predict_proba(train_features[test_index])[:, 1]
        onset_threshold = _select_onset_threshold(
            [train_records[index] for index in train_index],
            labels[train_index],
            onsets[train_index],
        )
        onset_thresholds.append(onset_threshold)
        for index in test_index:
            predicted_onsets[index] = predict_onset(train_records[index], onset_threshold)
            predicted_channels[index] = rank_channels(train_records[index], predicted_onsets[index])
            fold_assignments[index] = fold
        fold_rows.append(
            {
                "fold": fold,
                "held_out_group": groups[test_index[0]],
                "train_size": len(train_index),
                "test_size": len(test_index),
                "test_positives": int(labels[test_index].sum()),
                "onset_threshold": onset_threshold,
            }
        )

    decision_threshold = 0.5
    metrics = evaluate_competition_proxy(
        labels,
        probabilities,
        decision_threshold,
        onsets,
        predicted_onsets,
        true_channels,
        predicted_channels,
    )
    metrics_payload = metrics.as_dict()
    metrics_payload.update(
        {
            "evaluation": "leave-one-channel-schema-group-out OOF",
            "channel_score_status": "proxy; official ranking formula unavailable",
            "train_samples": len(train_records),
            "positive_samples": int(labels.sum()),
            "groups": len(np.unique(groups)),
            "decision_threshold": decision_threshold,
            "seed": args.seed,
        }
    )

    oof_rows = []
    for index, record in enumerate(train_records):
        row: dict[str, object] = {
            "sample_id": record.sample_id,
            "fold": int(fold_assignments[index]),
            "schema_group": groups[index],
            "label": int(labels[index]),
            "prob": probabilities[index],
            "predicted_label": int(probabilities[index] >= decision_threshold),
            "true_onset": onsets[index],
            "predicted_onset": predicted_onsets[index],
        }
        for channel_index in range(10):
            row[f"pred_ch{channel_index + 1}"] = predicted_channels[index][channel_index]
        oof_rows.append(row)
    pd.DataFrame(oof_rows).to_csv(args.output_dir / "oof_predictions.csv", index=False)

    final_model = _classifier(args.seed)
    final_model.fit(train_features, labels)
    final_onset_threshold = float(np.median(onset_thresholds))
    test_probabilities = final_model.predict_proba(test_features)[:, 1]
    submission_rows = []
    for record, probability in zip(test_records, test_probabilities, strict=True):
        positive = probability >= decision_threshold
        onset = predict_onset(record, final_onset_threshold) if positive else 0.0
        channels = rank_channels(record, onset) if positive else tuple("" for _ in range(10))
        submission_rows.append(
            {
                "sample_id": record.sample_id,
                "prob": round(float(probability), 6),
                "decision_threshold": decision_threshold,
                "onset_time": round(float(onset), 6),
                **{f"ch{i + 1}": channels[i] for i in range(10)},
            }
        )
    pd.DataFrame(submission_rows).to_csv(args.output_dir / "prediction.csv", index=False)

    joblib.dump(
        {
            "model": final_model,
            "feature_names": feature_names,
            "decision_threshold": decision_threshold,
            "onset_threshold": final_onset_threshold,
            "seed": args.seed,
        },
        args.output_dir / "model.joblib",
    )
    (args.output_dir / "metrics.json").write_text(
        json.dumps(metrics_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    try:
        import torch

        cuda_available = bool(torch.cuda.is_available())
        cuda_device = torch.cuda.get_device_name(0) if cuda_available else None
    except ImportError:
        cuda_available = False
        cuda_device = None
    elapsed = time.perf_counter() - started
    _write_report(
        args.output_dir / "report.md",
        metrics.as_dict(),
        fold_rows,
        len(train_records),
        len(test_records),
        int(labels.sum()),
        elapsed,
        cuda_available,
        cuda_device,
    )
    print(json.dumps(metrics_payload, ensure_ascii=False, indent=2))
    print(f"Wrote artifacts to {args.output_dir}")


if __name__ == "__main__":
    main()
