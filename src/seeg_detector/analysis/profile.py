"""Dataset profiling for the supplied competition sample."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from seeg_detector.data import inspect_npz, load_record, parse_channel_id, read_labels


CHANNEL_COLUMNS = [f"ch{i}" for i in range(1, 11)]


@dataclass(frozen=True)
class DatasetProfile:
    labels: pd.DataFrame
    files: pd.DataFrame
    summary: dict[str, object]
    issues: tuple[dict[str, str], ...]


def _profile_record(path: Path, label_lookup: pd.DataFrame) -> dict[str, object]:
    inspection = inspect_npz(path)
    record = load_record(path)
    valid_signal = record.valid_signal
    finite_mask = np.isfinite(valid_signal)
    finite_values = valid_signal[finite_mask]
    label_row = label_lookup.loc[record.sample_id] if record.sample_id in label_lookup.index else None
    return {
        "sample_id": record.sample_id,
        "split": "train" if record.sample_id.startswith("train_") else "test",
        "label": int(label_row["label"]) if label_row is not None else pd.NA,
        "onset_time": float(label_row["onset_time"]) if label_row is not None else np.nan,
        "channels": record.signal.shape[0],
        "allocated_samples": record.signal.shape[1],
        "valid_samples": record.valid_samples,
        "sampling_rate_hz": record.sampling_rate,
        "duration_seconds": record.duration_seconds,
        "dtype": str(record.signal.dtype),
        "finite_rate": float(finite_mask.mean()),
        "zero_rate": float((valid_signal == 0).mean()),
        "minimum": float(finite_values.min()),
        "maximum": float(finite_values.max()),
        "mean": float(finite_values.mean(dtype=np.float64)),
        "std": float(finite_values.std(dtype=np.float64)),
        "channel_ids_unique": bool(len(set(record.channel_ids.tolist())) == len(record.channel_ids)),
        "raw_indices_unique": bool(
            len(set(record.raw_channel_indices.tolist())) == len(record.raw_channel_indices)
        ),
        "channel_schema": "|".join(record.channel_ids.tolist()),
        "prefix_bytes": inspection.prefix_bytes,
        "standard_numpy_compatible": inspection.standard_numpy_compatible,
        "file_size_bytes": path.stat().st_size,
    }


def build_profile(data_root: str | Path) -> DatasetProfile:
    root = Path(data_root)
    labels = read_labels(root / "label.csv")
    label_lookup = labels.set_index("sample_id", drop=False)
    file_rows = [_profile_record(path, label_lookup) for path in sorted(root.glob("*.npz"))]
    files = pd.DataFrame(file_rows)

    channel_occurrences = [
        channel_id
        for schema in files["channel_schema"]
        for channel_id in schema.split("|")
    ]
    parsed_channels = [parse_channel_id(channel_id) for channel_id in channel_occurrences]
    parseable_channels = [item for item in parsed_channels if item is not None]
    unparsed_channel_ids = sorted(
        {channel_id for channel_id, parsed in zip(channel_occurrences, parsed_channels) if parsed is None}
    )

    positives = labels[labels["label"] == 1]
    negatives = labels[labels["label"] == 0]
    available_train_ids = set(files.loc[files["split"] == "train", "sample_id"])
    available_positive_ids = available_train_ids & set(positives["sample_id"])
    top10_membership_checks = []
    for sample_id in sorted(available_positive_ids):
        channel_schema = files.loc[files["sample_id"] == sample_id, "channel_schema"].iloc[0]
        record_channels = set(channel_schema.split("|"))
        top10 = labels.loc[labels["sample_id"] == sample_id, CHANNEL_COLUMNS].iloc[0]
        top10_membership_checks.append(set(top10.tolist()).issubset(record_channels))
    schema_counts = Counter(files["channel_schema"])
    summary: dict[str, object] = {
        "label_rows": len(labels),
        "positive_rows": len(positives),
        "negative_rows": len(negatives),
        "positive_rate": len(positives) / len(labels),
        "onset_min": float(positives["onset_time"].min()),
        "onset_median": float(positives["onset_time"].median()),
        "onset_max": float(positives["onset_time"].max()),
        "sample_npz_files": len(files),
        "train_npz_files": int((files["split"] == "train").sum()),
        "test_npz_files": int((files["split"] == "test").sum()),
        "available_positive_train_files": len(available_positive_ids),
        "train_label_coverage": len(available_train_ids) / len(labels),
        "sampling_rates": sorted(files["sampling_rate_hz"].round(9).unique().tolist()),
        "durations": sorted(files["duration_seconds"].round(9).unique().tolist()),
        "channel_counts": sorted(files["channels"].unique().tolist()),
        "channel_schema_count": len(schema_counts),
        "channel_occurrences": len(channel_occurrences),
        "unique_channel_ids": len(set(channel_occurrences)),
        "pol_channel_occurrences": sum(item.source_prefix == "POL" for item in parseable_channels)
        + sum(channel_id.startswith("POL ") for channel_id in unparsed_channel_ids),
        "eeg_ref_channel_occurrences": sum(
            item.source_prefix == "EEG" and item.reference_tag == "-Ref"
            for item in parseable_channels
        ),
        "parseable_channel_occurrences": len(parseable_channels),
        "electrode_codes": sorted({item.electrode_code for item in parseable_channels}),
        "unparsed_channel_ids": unparsed_channel_ids,
        "prefixed_npz_files": int((files["prefix_bytes"] > 0).sum()),
        "nonfinite_values": int(
            round(((1.0 - files["finite_rate"]) * files["channels"] * files["valid_samples"]).sum())
        ),
        "all_top10_complete_for_positive": bool(positives[CHANNEL_COLUMNS].notna().all().all()),
        "all_top10_empty_for_negative": bool(negatives[CHANNEL_COLUMNS].isna().all().all()),
        "available_positive_top10_in_record": bool(all(top10_membership_checks)),
        "sample_ids_unique": bool(labels["sample_id"].is_unique),
    }

    issues = (
        {
            "severity": "high",
            "finding": "23/24 个 NPZ 文件含前置零字节区域，直接调用 numpy.load(path) 会失败。",
            "impact": "常规训练数据加载器无法读取绝大多数样例。",
            "action": "使用本项目的 ZIP/NPY 兼容读取器，并在完整数据下载后重新验证容器。",
        },
        {
            "severity": "high",
            "finding": "样例只提供 440 条训练标签中的 20 个信号文件。",
            "impact": "样例统计不能估计完整数据分布或模型性能。",
            "action": "仅将样例用于格式、加载器与端到端管线验证。",
        },
        {
            "severity": "high",
            "finding": "label.csv 与 NPZ 元数据均未提供明确患者标识。",
            "impact": "仅凭现有字段不能实施患者级划分和泄漏防护。",
            "action": "定义训练/验证折前先取得官方患者或分组映射。",
        },
        {
            "severity": "medium",
            "finding": "样例文件未声明信号幅值单位和参考电极约定。",
            "impact": "目前不能采用物理幅值阈值，也不能假定记录间绝对幅值可直接比较。",
            "action": "暂按“存储幅值、单位未知”处理，并向赛事组确认采集说明。",
        },
    )
    return DatasetProfile(labels=labels, files=files, summary=summary, issues=issues)


def write_profile_report(profile: DatasetProfile, report_path: str | Path) -> None:
    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = profile.summary
    channel_counts = ", ".join(map(str, summary["channel_counts"]))
    issue_rows = "\n".join(
        f"| {item['severity']} | {item['finding']} | {item['impact']} | {item['action']} |"
        for item in profile.issues
    )
    file_preview_frame = profile.files[
        [
            "sample_id",
            "split",
            "label",
            "channels",
            "duration_seconds",
            "finite_rate",
            "zero_rate",
            "prefix_bytes",
        ]
    ]
    preview_headers = file_preview_frame.columns.tolist()
    preview_lines = [
        "| " + " | ".join(preview_headers) + " |",
        "|" + "|".join(["---"] * len(preview_headers)) + "|",
    ]
    for row in file_preview_frame.itertuples(index=False, name=None):
        formatted = []
        for value in row:
            if isinstance(value, float):
                formatted.append(f"{value:.4f}")
            elif pd.isna(value):
                formatted.append("")
            else:
                formatted.append(str(value))
        preview_lines.append("| " + " | ".join(formatted) + " |")
    file_preview = "\n".join(preview_lines)
    text = f"""# SEEG 样例数据描述

## 结论摘要

- `label.csv` 含 {summary['label_rows']} 条训练标签：阳性 {summary['positive_rows']} 条、阴性 {summary['negative_rows']} 条，标签表阳性率为 {summary['positive_rate']:.2%}。该比例只描述标签表，不能代替患者级分布。
- 本地解压样例含 {summary['train_npz_files']} 个训练 NPZ 和 {summary['test_npz_files']} 个测试 NPZ；训练文件仅覆盖标签表的 {summary['train_label_coverage']:.2%}。
- 所有样例记录均为 60 秒、约 2,000 Hz、`float32`，每通道 120,000 个有效采样点；通道数随记录变化，为 {channel_counts}。
- 阳性 onset 范围为 {summary['onset_min']:.3f}–{summary['onset_max']:.3f} 秒，中位数 {summary['onset_median']:.3f} 秒。阳性行 Top-10 通道完整，阴性行 Top-10 通道为空。
- 所有已读有效信号均为有限数值；但 {summary['prefixed_npz_files']}/{summary['sample_npz_files']} 个 NPZ 存在前置零字节，不能直接用标准 `numpy.load(path)`。

## 数据粒度与字段

- 一行标签对应一个 `sample_id`，每个 NPZ 对应一段多通道 SEEG 记录。
- `signal` 形状为 `(通道数, 120000)`；实际读取必须截取 `signal[:, :valid_samples]`。
- `channel_ids` 是记录内通道名，`raw_channel_indices` 是原始通道索引。
- `sampling_rate` 为约 2,000 Hz，`valid_samples` 为 120,000，对应 60 秒。
- `label=1` 行给出 `onset_time` 和 `ch1`–`ch10`；`label=0` 的 onset 为 0、Top-10 为空。
- 本地 5 个阳性训练文件的 Top-10 名称均能在各自 `channel_ids` 中找到，且每行 10 个名称不重复。

## 数据质量风险

| 严重度 | 发现 | 影响 | 建议 |
|---|---|---|---|
{issue_rows}

## 通道与电极命名规范

样例共出现 {summary['channel_occurrences']} 次通道记录、{summary['unique_channel_ids']} 个不同的完整通道 ID，可归纳为：

```text
<来源前缀> <电极/轨迹代码><接触点编号><可选参考标记>
```

例如：

| 原始名称 | 来源前缀 | 电极/轨迹代码 | 接触点 | 参考标记 |
|---|---|---|---:|---|
| `POL pMC12` | `POL` | `pMC` | 12 | 无 |
| `EEG F3-Ref` | `EEG` | `F` | 3 | `-Ref` |
| `POL DC01` | `POL` | `DC` | 01 | 无 |

解释边界如下：

- **代码 + 数字**：`A`、`F`、`PO`、`pMC` 等代码在同一记录内通常对应一组连续编号接触点，数字是该组内的接触点序号。这是由命名连续性得到的结构性解释；样例没有植入计划、坐标、左右侧或脑区映射，因此不能把代码直接解释成固定解剖区域。
- **大小写与前导零必须保留**：`PO`、`mPO`、`pMC`、`aMC` 是不同代码；`DC01`–`DC16` 的两位编号属于原始 ID。算法内部可以另存整数 `contact_number=1`，但提交、Top-10 和审计输出必须保留原字符串 `DC01`。
- **`POL DC01`–`POL DC16` 是辅助输入，不是植入电极组**：该固定 16 通道块应标记为 `auxiliary_dc` 并默认从 SEEG 模型、重参考和 Top-10 排名中排除；原始数据和索引仍需保留以供审计。
- **`POL ACxx` 仍是普通 SEEG 候选**：样例中 `AC` 通道呈连续脑电样波形，更符合电极/轨迹代码，不应按字面理解为与 DC 辅助输入相对的“交流通道”。
- **`EEG ...-Ref`**：`EEG` 是 EDF/EDF+ 常用的信号类型前缀；`-Ref` 表明标签采用“该接触点相对某个参考”的形式，但文件未给出参考电极身份。因此不能仅凭名称恢复参考导联，也不能假定所有 `-Ref` 通道使用同一参考。
- **`POL ...`**：`POL` 占样例通道记录的 {summary['pol_channel_occurrences'] / summary['channel_occurrences']:.2%}，但它不是 EDF+ 标准信号类型。现有材料不足以把它可靠展开为某个设备或医学术语，应作为采集/导出系统保留的来源前缀，不应据此排除通道或判断是否为 SEEG。
- **同组混合前缀**：同一代码内可同时出现 `EEG A1-Ref`、`EEG A2-Ref` 与 `POL A3`–`POL A16`。做电极组聚合时可使用解析后的代码 `A`，但模型输入、Top-10 和回写结果仍须使用完整原始 `channel_ids`。
- **异常名称**：{', '.join(f'`{item}`' for item in summary['unparsed_channel_ids'])} 是唯一不符合“代码 + 数字”形式的名称，应作为辅助/特殊通道候选单独审查，不能自动当作普通接触点。

建议的数据字段为 `raw_channel_id`、`source_prefix`、`electrode_code`、`contact_text`、`contact_number` 和 `reference_tag`。其中 `raw_channel_id` 是提交和跨文件匹配的唯一权威字段，其他字段只用于分组、排序和质量检查。

命名解释参考 [EDF+ 标准标签结构](https://www.edfplus.info/specs/edftexts.html) 与 [MNE EDF 类型推断说明](https://mne.tools/stable/generated/mne.io.read_raw_edf.html)；赛事样例自身未附设备命名手册，故 `POL` 和字母代码的含义保持未判定。

## 文件级概览

{file_preview}

## 使用边界

本报告只描述赛事组提供的样例文件，不推断完整数据集规模、患者数量、类别比例、临床 SOZ/EZ、模型精度或推理时延。通道命名模式可用于检查记录间结构差异，但在缺少官方患者映射时不能把相同通道表直接等同为同一患者。
"""
    output.write_text(text, encoding="utf-8")
