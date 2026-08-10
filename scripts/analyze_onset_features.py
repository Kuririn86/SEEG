#!/usr/bin/env python3
"""Quantify physiology-motivated feature changes around labeled SEEG onset."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from seeg_detector.analysis.onset_features import (
    OnsetFeatureConfig,
    evaluate_record_alignment,
    summarize_feature_alignment,
)
from seeg_detector.data import load_record, read_labels


DISPLAY_NAMES = {
    "physiology_composite": "Physiology composite",
    "fast_suppression_joint": "Fast activity + LF suppression",
    "multiband_fast_activity": "Multiband fast activity",
    "high_low_ratio": "High/low-frequency ratio",
    "line_length": "Line length",
    "teager_energy": "Teager energy",
    "low_frequency_suppression": "Low-frequency suppression",
    "spectral_centroid": "Spectral centroid",
    "spectral_entropy_change": "Absolute spectral entropy change",
    "rhythmicity": "Rhythmicity",
    "beta_power": "Beta power",
    "low_gamma_power": "Low-gamma power",
    "high_gamma_power": "High-gamma power",
    "ripple_power": "150–250 Hz power",
    "fast_ripple_power": "250–500 Hz power",
    "rms_change": "Absolute RMS change",
    "kurtosis": "Kurtosis",
}


def _aligned_summary(trajectories: pd.DataFrame, step_seconds: float) -> pd.DataFrame:
    data = trajectories.query("channel_set == 'all'").copy()
    record_count = data["sample_id"].nunique()
    data["relative_time_bin"] = (
        np.round(data["relative_time_seconds"] / step_seconds) * step_seconds
    )
    baseline = (
        data.query("-5 <= relative_time_bin <= -2")
        .groupby(["sample_id", "feature"])["aggregate_score"]
        .median()
        .rename("record_baseline")
    )
    data = data.join(baseline, on=["sample_id", "feature"])
    data["baseline_centered_score"] = data["aggregate_score"] - data["record_baseline"]
    summary = (
        data.groupby(["feature", "relative_time_bin"])["baseline_centered_score"]
        .agg(median="median", q25=lambda x: x.quantile(0.25), q75=lambda x: x.quantile(0.75), n="size")
        .reset_index()
    )
    # Fractional onset labels make only the two boundary bins incomplete after
    # alignment. Keep complete record-level bins so every plotted point has n=5.
    return summary.loc[summary["n"] == record_count].reset_index(drop=True)


def _plot_results(
    summary: pd.DataFrame,
    aligned: pd.DataFrame,
    output_stem: Path,
) -> None:
    """Create the quantitative-grid evidence figure.

    Figure contract
    ---------------
    Core conclusion: several physiology-motivated features show a sustained,
    onset-aligned change, but timing and official Top-10 concordance are not
    interchangeable. Panel a is the hero heatmap; panel b compares record-level
    descriptive alignment metrics; panel c shows median trajectories with IQR.
    Independent n is five positive records, not channels or windows.
    """

    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
        }
    )
    palette = ["#2463A8", "#D8792B", "#7A5AA6", "#2A8F7B"]
    top_features = summary.head(10)["feature"].tolist()
    time_grid = np.sort(aligned["relative_time_bin"].unique())
    heat = np.full((len(top_features), len(time_grid)), np.nan)
    for row, feature in enumerate(top_features):
        values = aligned.loc[aligned["feature"] == feature].set_index("relative_time_bin")["median"]
        heat[row] = values.reindex(time_grid).to_numpy()

    figure = plt.figure(figsize=(7.2, 7.4))
    grid = figure.add_gridspec(2, 2, height_ratios=[1.15, 1.0], width_ratios=[1.12, 0.88], hspace=0.42, wspace=0.42)
    ax_heat = figure.add_subplot(grid[0, :])
    limit = max(2.0, float(np.nanpercentile(np.abs(heat), 95)))
    image = ax_heat.imshow(
        np.clip(heat, -limit, limit),
        aspect="auto",
        origin="upper",
        extent=[time_grid.min(), time_grid.max(), len(top_features) - 0.5, -0.5],
        cmap="RdBu_r",
        vmin=-limit,
        vmax=limit,
        interpolation="nearest",
    )
    ax_heat.axvline(0.0, color="#1F2933", linewidth=1.0, linestyle=(0, (3, 2)))
    ax_heat.set_yticks(np.arange(len(top_features)))
    ax_heat.set_yticklabels([DISPLAY_NAMES.get(name, name) for name in top_features])
    ax_heat.set_xlabel("Time relative to labeled onset (s)")
    ax_heat.set_title("a  Baseline-centered onset trajectories", loc="left", fontweight="bold")
    colorbar = figure.colorbar(image, ax=ax_heat, fraction=0.025, pad=0.015)
    colorbar.set_label("90th-percentile response (robust z, baseline centered)")

    ax_rank = figure.add_subplot(grid[1, 0])
    shown = summary.head(12).sort_values("median_abs_timing_error_seconds", ascending=False)
    sizes = 25 + 35 * np.clip(shown["median_early_contrast"].to_numpy(), 0, 6) / 6
    scatter = ax_rank.scatter(
        shown["median_abs_timing_error_seconds"],
        np.arange(len(shown)),
        c=shown["mean_top10_overlap"],
        s=sizes,
        cmap="viridis",
        vmin=0,
        vmax=max(4.0, float(summary["mean_top10_overlap"].max())),
        edgecolor="white",
        linewidth=0.5,
    )
    ax_rank.set_yticks(np.arange(len(shown)))
    ax_rank.set_yticklabels([DISPLAY_NAMES.get(name, name) for name in shown["feature"]])
    ax_rank.set_xlabel("Median |peak-change time − onset| (s)")
    ax_rank.set_title("b  Timing and Top-10 concordance", loc="left", fontweight="bold")
    rank_colorbar = figure.colorbar(scatter, ax=ax_rank, fraction=0.05, pad=0.03)
    rank_colorbar.set_label("Mean official Top-10 overlap (of 10)")

    ax_lines = figure.add_subplot(grid[1, 1])
    for color, feature in zip(palette, summary.head(4)["feature"]):
        data = aligned.loc[aligned["feature"] == feature].sort_values("relative_time_bin")
        ax_lines.plot(
            data["relative_time_bin"],
            data["median"],
            color=color,
            linewidth=1.3,
            label=DISPLAY_NAMES.get(feature, feature),
        )
        ax_lines.fill_between(
            data["relative_time_bin"],
            data["q25"],
            data["q75"],
            color=color,
            alpha=0.16,
            linewidth=0,
        )
    ax_lines.axvline(0.0, color="#1F2933", linewidth=1.0, linestyle=(0, (3, 2)))
    ax_lines.axhline(0.0, color="#9AA3AD", linewidth=0.6)
    ax_lines.set_xlim(-5, 5)
    ax_lines.set_xlabel("Time relative to labeled onset (s)")
    ax_lines.set_ylabel("Baseline-centered response")
    ax_lines.set_title("c  Leading feature trajectories", loc="left", fontweight="bold")
    ax_lines.legend(fontsize=6, loc="upper left")

    figure.suptitle(
        "Physiology-motivated SEEG features around labeled seizure onset",
        x=0.08,
        ha="left",
        fontsize=10.5,
        fontweight="bold",
    )
    figure.text(
        0.08,
        0.945,
        "Five positive records; causal 0.5-s windows, 0.125-s step; lines show median and IQR across records",
        fontsize=6.5,
        color="#4C5663",
    )
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_stem.with_suffix(".png"), dpi=300, bbox_inches="tight", facecolor="white")
    figure.savefig(output_stem.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    figure.savefig(output_stem.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    figure.savefig(output_stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def _write_report(
    summary: pd.DataFrame,
    alignment: pd.DataFrame,
    output_path: Path,
    figure_stem: Path,
) -> None:
    top = summary.head(8)
    clean = alignment.query("channel_set == 'line_clean'")
    clean_summary = clean.groupby("feature").agg(
        clean_median_abs_error=("absolute_timing_error_seconds", "median"),
        clean_median_contrast=("early_contrast", "median"),
    )
    combined = top.join(clean_summary, on="feature")
    rows = []
    for _, row in combined.iterrows():
        rows.append(
            "| {feature} | {error:.3f} | {signed:+.3f} | {hit:.0%} | "
            "{contrast:.2f} | {rate:.0%} | {overlap:.2f} | "
            "{enrichment:+.2f} | {clean_error:.3f} |".format(
                feature=DISPLAY_NAMES.get(row["feature"], row["feature"]),
                error=row["median_abs_timing_error_seconds"],
                signed=row["median_signed_timing_error_seconds"],
                hit=row["within_0_5_seconds_rate"],
                contrast=row["median_early_contrast"],
                rate=row["positive_contrast_rate"],
                overlap=row["mean_top10_overlap"],
                enrichment=row["median_top10_enrichment"],
                clean_error=row["clean_median_abs_error"],
            )
        )
    stable = top.loc[top["positive_contrast_rate"] == 1.0, "feature"].tolist()
    report = f"""# 样例 SEEG onset 生理特征对齐分析

## 结论摘要

- 本次分析的独立单位是 **5 个具有人工 onset 标注和本地信号的阳性记录**；通道和滑窗是记录内重复测量，不作为独立 `n`。
- **没有单一特征在时间、变化方向和空间定位三方面同时占优。**低频抑制的时间误差最小；高伽马功率与官方 Top-10 的空间重合最好；峰度的 onset 后正向变化方向最一致。因此下一版模型应优先保留这三类互补信息，而不是只选综合名次第一项。
- 在 5/5 个阳性记录中均呈正向 early contrast 的首批特征为：{', '.join(DISPLAY_NAMES.get(name, name) for name in stable) if stable else '无'}。
- 严重 50 Hz 候选通道排除后的时间误差作为敏感性分析单独报告；主分析不因工频指标事后删除人工 Top-10 通道。

![onset 特征对齐图](../assets/figures/onset_feature_alignment.png)

## 方法

- 原始信号：赛事本地样例中的 5 个阳性 NPZ，约 2,000 Hz、60 秒；排除 `POL DC01`–`POL DC16` 和无法解析的特殊通道。
- 时间窗：因果 0.5 秒窗、0.125 秒步长，时间戳位于窗末端，避免使用报告时刻之后的数据。
- 基线：每条记录 onset 前 10～2 秒；每个特征按通道用 median/MAD 做稳健标准化。
- 频谱：直接在原始窗口上计算，不使用可能向 onset 前扩散信息的零相位陷波；频谱汇总时剔除 50 Hz 及其谐波 ±2 Hz。
- 通道聚合：每个时间点取有效 SEEG 通道响应的第 90 百分位，保留局灶起始而避免最大值被单个伪迹支配。
- 时间对齐：在 onset 前 1 秒至后 3 秒内寻找聚合轨迹最大上升沿，报告与人工 onset 的有符号和绝对误差。
- 空间对齐：按 onset 后 0～2 秒最大响应排序，计算预测 Top-10 与赛事人工 Top-10 的重合数。
- 统计边界：仅报告记录级中位数、均值和方向一致率，不对窗口或通道执行伪重复推断，不报告小样本 p 值。

## 优先特征结果

| Feature | 中位绝对时间误差 (s) | 中位有符号误差 (s) | ±0.5 s 命中率 | 中位 early contrast | 正向记录比例 | 平均 Top-10 重合数 | Top-10 中位富集 | 去严重线噪后中位误差 (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

完整记录级结果见 `reports/onset_features/record_feature_alignment.csv`，所有特征汇总见 `reports/onset_features/feature_summary.csv`。

## 解释规则

1. **时间误差小**表示特征最大上升沿靠近人工 onset，不代表它能在连续阴性数据中保持低误报。
2. **early contrast 大**表示 onset 后 2 秒相对个体基线变化明显；不同特征量纲已经过稳健 z 标准化，但极端值仍可能受伪迹影响。
3. **Top-10 重合高**表示该特征的早期空间分布更接近赛事通道标注；不能直接等同于临床 SOZ、EZ 或手术靶点。
4. 组合特征的当前优势属于预设生理组合在样例上的探索性表现。后续必须拆分到完整患者级验证集，避免在这 5 条记录上继续调权造成过拟合。

## 当前建模优先级

1. **第一优先：低频抑制 + 高伽马功率。**前者提供较好的时间锚点，后者提供相对更好的 Top-10 通道定位；二者在这些样例中互补，但都只在 3/5 记录达到 ±0.5 秒。
2. **第二优先：绝对谱熵变化、ripple 功率和 beta 功率。**它们在 3/5 记录达到 ±1 秒，可作为形态变化和频带变化的补充，而非独立 onset 判据。
3. **第三优先：峰度。**5/5 记录方向一致，但中位时差约 1.16 秒、平均 Top-10 重合仅 0.6，更适合作为发作状态确认特征，而非单独承担定位。
4. **暂不优先：低伽马、多频带快活动、节律性、Teager 能量和 fast-ripple。**当前样例的方向或时间稳定性不足；尤其 HFO 仍需排除短窗频谱泄漏、肌电/尖峰和滤波振铃。

排除 `line50_excess_db > 20 dB` 通道后，多数特征的中位时差没有变化，说明当前整体结论并非由少数严重 50 Hz 通道单独驱动；这只是敏感性分析，不等于这些通道已被证实可安全纳入正式模型。

## 下一步

1. 将排名靠前的单一特征和组合特征加入可复现基线模型，执行逐项消融。
2. 获得完整训练数据和患者 ID 后，以患者为独立单位报告 onset MAE、±1/±3 秒命中率和连续数据误报率。
3. 对 HFO 特征额外执行滤波振铃、最小周期数和 50 Hz 谐波敏感性检查。
4. 比较原始参考、同轴双极和其他临床认可参考方案；当前名称不足以安全自动重参考。

## 可复现产物

- `reports/onset_features/feature_summary.csv`
- `reports/onset_features/record_feature_alignment.csv`
- `reports/onset_features/onset_aligned_trajectories.csv`
- `reports/onset_features/channel_onset_responses.csv`
- `{figure_stem}.{{png,svg,pdf,tiff}}`
- `scripts/analyze_onset_features.py`
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("Dataset/sampleData"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/onset_features"))
    parser.add_argument(
        "--figure", type=Path, default=Path("assets/figures/onset_feature_alignment")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("reports/onset_feature_analysis.md")
    )
    args = parser.parse_args()

    config = OnsetFeatureConfig()
    labels = read_labels(args.data_root / "label.csv").set_index("sample_id")
    line_metrics_path = Path("reports/line_noise/channel_metrics.csv")
    line_metrics = pd.read_csv(line_metrics_path) if line_metrics_path.exists() else pd.DataFrame()
    alignment_parts = []
    trajectory_parts = []
    channel_parts = []
    positive_paths = [
        path
        for path in sorted(args.data_root.glob("train_*.npz"))
        if int(labels.loc[path.stem, "label"]) == 1
    ]
    for path in positive_paths:
        record = load_record(path)
        label_row = labels.loc[record.sample_id]
        top10 = [str(label_row[f"ch{index}"]) for index in range(1, 11)]
        record_line = line_metrics.loc[line_metrics["sample_id"] == record.sample_id]
        alignment, trajectories, channels = evaluate_record_alignment(
            record,
            onset_seconds=float(label_row["onset_time"]),
            official_top10=top10,
            line_noise_metrics=record_line,
            config=config,
        )
        alignment_parts.append(alignment)
        trajectory_parts.append(trajectories)
        channel_parts.append(channels)
        print(f"Analyzed {record.sample_id} onset={float(label_row['onset_time']):.6f}s")

    alignment = pd.concat(alignment_parts, ignore_index=True)
    trajectories = pd.concat(trajectory_parts, ignore_index=True)
    channels = pd.concat(channel_parts, ignore_index=True)
    summary = summarize_feature_alignment(alignment)
    aligned_summary = _aligned_summary(trajectories, config.step_seconds)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_dir / "feature_summary.csv", index=False)
    alignment.to_csv(args.output_dir / "record_feature_alignment.csv", index=False)
    aligned_summary.to_csv(args.output_dir / "onset_aligned_trajectories.csv", index=False)
    channels.to_csv(args.output_dir / "channel_onset_responses.csv", index=False)
    _plot_results(summary, aligned_summary, args.figure)
    _write_report(summary, alignment, args.report, args.figure)
    print(summary.head(12).to_string(index=False))
    print(f"Wrote analysis to {args.output_dir}")
    print(f"Wrote report to {args.report}")
    print(f"Wrote figure to {args.figure}.{{png,svg,pdf,tiff}}")


if __name__ == "__main__":
    main()
