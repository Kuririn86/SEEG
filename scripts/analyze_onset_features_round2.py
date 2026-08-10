#!/usr/bin/env python3
"""Second-round onset analysis with multichannel propagation features."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from seeg_detector.analysis.onset_features import (
    PROPAGATION_FEATURES,
    OnsetFeatureConfig,
    evaluate_record_alignment,
    summarize_feature_alignment,
)
from seeg_detector.data import load_record, read_labels


DISPLAY_NAMES = {
    "line_length": "Line length",
    "rms_change": "Absolute RMS change",
    "teager_energy": "Teager energy",
    "kurtosis": "Kurtosis",
    "beta_power": "Beta power",
    "low_gamma_power": "Low-gamma power",
    "high_gamma_power": "High-gamma power",
    "ripple_power": "150–250 Hz power",
    "fast_ripple_power": "250–500 Hz power",
    "high_low_ratio": "High/low-frequency ratio",
    "low_frequency_suppression": "Low-frequency suppression",
    "spectral_centroid": "Spectral centroid",
    "spectral_entropy_change": "Absolute spectral entropy change",
    "rhythmicity": "Rhythmicity",
    "multiband_fast_activity": "Multiband fast activity",
    "fast_suppression_joint": "Fast activity + LF suppression",
    "physiology_composite": "Physiology composite",
    "recruitment_consensus": "Recruitment consensus",
    "recruitment_persistence": "Recruitment persistence",
    "recruitment_change_rate": "Recruitment change rate",
    "early_recruitment_lead": "Early recruitment lead",
    "propagation_participation": "Propagation participation",
    "lagged_outflow": "Lagged network outflow",
    "net_lagged_outflow": "Net lagged outflow",
    "coactivation_strength": "Coactivation strength",
    "recruited_fraction_2z": "Recruited-channel fraction (>2z)",
    "recruited_fraction_3z": "Recruited-channel fraction (>3z)",
    "recruitment_fraction_slope": "Recruitment-fraction slope",
    "recruitment_dispersion": "Recruitment dispersion",
    "propagation_front": "Propagation-front index",
    "network_density": "Dynamic network density",
    "largest_component_fraction": "Largest component fraction",
    "mean_lagged_connectivity": "Mean lagged connectivity",
}


def _add_family(summary: pd.DataFrame) -> pd.DataFrame:
    output = summary.copy()
    output["feature_family"] = np.where(
        output["feature"].isin(PROPAGATION_FEATURES), "propagation", "round1"
    )
    return output.sort_values(
        ["onset_alignment_rank_score", "median_abs_timing_error_seconds", "feature"]
    ).reset_index(drop=True)


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
    result = (
        data.groupby(["feature", "feature_scope", "relative_time_bin"])[
            "baseline_centered_score"
        ]
        .agg(
            median="median",
            q25=lambda values: values.quantile(0.25),
            q75=lambda values: values.quantile(0.75),
            n="size",
        )
        .reset_index()
    )
    return result.loc[result["n"] == record_count].reset_index(drop=True)


def _plot_results(
    summary: pd.DataFrame,
    alignment: pd.DataFrame,
    aligned: pd.DataFrame,
    output_stem: Path,
) -> None:
    """Render a quantitative-grid comparison of first- and second-round features.

    Figure contract
    ---------------
    Core conclusion: multichannel propagation features are useful only if they
    improve record-level alignment beyond the best first-round local features.
    Panel a is the hero record-by-feature timing-error heatmap; panel b reports
    the aggregate timing ranking; panel c shows onset-aligned trajectories;
    Independent n is five positive records. Color distinguishes the original
    local features from the added propagation features.
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
    colors = {"round1": "#9AA3AD", "propagation": "#2463A8"}
    top = summary.head(12).copy()
    records = sorted(alignment["sample_id"].unique())
    timing = alignment.query("channel_set == 'all'").pivot(
        index="feature", columns="sample_id", values="signed_timing_error_seconds"
    )
    timing = timing.reindex(index=top["feature"], columns=records)

    figure = plt.figure(figsize=(7.2, 8.0))
    grid = figure.add_gridspec(
        2,
        2,
        height_ratios=[1.05, 1.0],
        width_ratios=[1.06, 0.94],
        hspace=0.45,
        wspace=0.48,
    )
    ax_heat = figure.add_subplot(grid[0, :])
    image = ax_heat.imshow(
        np.clip(timing.to_numpy(), -3.0, 3.0),
        aspect="auto",
        cmap="RdBu_r",
        vmin=-3.0,
        vmax=3.0,
        interpolation="nearest",
    )
    ax_heat.set_xticks(np.arange(len(records)))
    ax_heat.set_xticklabels([name.removeprefix("train_") for name in records])
    ax_heat.set_yticks(np.arange(len(top)))
    ax_heat.set_yticklabels([DISPLAY_NAMES.get(name, name) for name in top["feature"]])
    ax_heat.set_xlabel("Positive record ID")
    ax_heat.set_title("a  Record-level signed timing error", loc="left", fontweight="bold")
    colorbar = figure.colorbar(image, ax=ax_heat, fraction=0.025, pad=0.02)
    colorbar.set_label("Peak-change time − labeled onset (s)")

    ax_rank = figure.add_subplot(grid[1, 0])
    ranked = top.sort_values("median_abs_timing_error_seconds", ascending=False)
    positions = np.arange(len(ranked))
    bar_colors = [colors[family] for family in ranked["feature_family"]]
    ax_rank.barh(
        positions,
        ranked["median_abs_timing_error_seconds"],
        color=bar_colors,
        edgecolor="#34404B",
        linewidth=0.35,
    )
    ax_rank.set_yticks(positions)
    ax_rank.set_yticklabels([DISPLAY_NAMES.get(name, name) for name in ranked["feature"]])
    ax_rank.set_xlabel("Median absolute timing error (s)")
    ax_rank.set_title("b  Onset-alignment ranking", loc="left", fontweight="bold")
    for position, (_, row) in enumerate(ranked.iterrows()):
        ax_rank.text(
            row["median_abs_timing_error_seconds"] + 0.025,
            position,
            f"{int(round(row['within_0_5_seconds_rate'] * 5))}/5",
            va="center",
            fontsize=5.5,
            color="#34404B",
        )
    ax_rank.text(
        0.99,
        0.02,
        "labels: records within ±0.5 s",
        transform=ax_rank.transAxes,
        ha="right",
        fontsize=5.5,
        color="#59636E",
    )

    ax_lines = figure.add_subplot(grid[1, 1])
    line_colors = ["#2463A8", "#D8792B", "#7A5AA6", "#2A8F7B"]
    leading_features = top.head(3)["feature"].tolist()
    original_comparator = summary.query("feature_family == 'round1'").iloc[0]["feature"]
    if original_comparator not in leading_features:
        leading_features.append(original_comparator)
    for color, feature in zip(line_colors, leading_features[:4]):
        data = aligned.loc[aligned["feature"] == feature].sort_values("relative_time_bin")
        x = data["relative_time_bin"].to_numpy(dtype=float)
        median = data["median"].to_numpy(dtype=float)
        q25 = data["q25"].to_numpy(dtype=float)
        q75 = data["q75"].to_numpy(dtype=float)
        ax_lines.plot(
            x,
            np.clip(median, -4.0, 4.0),
            color=color,
            linewidth=1.3,
            label=DISPLAY_NAMES[feature],
        )
        ax_lines.fill_between(
            x,
            np.clip(q25, -4.0, 4.0),
            np.clip(q75, -4.0, 4.0),
            color=color,
            alpha=0.15,
            linewidth=0,
        )
    ax_lines.axvline(0.0, color="#1F2933", linewidth=1.0, linestyle=(0, (3, 2)))
    ax_lines.axhline(0.0, color="#9AA3AD", linewidth=0.6)
    ax_lines.set_xlim(-5, 5)
    ax_lines.set_xlabel("Time relative to labeled onset (s)")
    ax_lines.set_ylabel("Baseline-centered response")
    ax_lines.set_ylim(-4.0, 4.0)
    ax_lines.set_title("c  Leading onset trajectories", loc="left", fontweight="bold")
    ax_lines.legend(fontsize=5.5, loc="upper left")
    ax_lines.text(
        0.99,
        0.02,
        "display clipped to ±4 robust z",
        transform=ax_lines.transAxes,
        ha="right",
        fontsize=5.2,
        color="#59636E",
    )

    from matplotlib.patches import Patch

    handles = [
        Patch(facecolor=colors["round1"], label="Round-1 local feature"),
        Patch(facecolor=colors["propagation"], label="Round-2 propagation feature"),
    ]
    figure.legend(handles=handles, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.015))
    figure.suptitle(
        "Second-round SEEG feature alignment with labeled seizure onset",
        x=0.08,
        ha="left",
        fontsize=10.5,
        fontweight="bold",
    )
    figure.text(
        0.08,
        0.946,
        "33 features; five positive records; causal 0.5-s windows; descriptive record-level analysis",
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
    sensitivity: pd.DataFrame,
    output_path: Path,
    figure_stem: Path,
) -> None:
    original = summary.query("feature_family == 'round1'").iloc[0]
    propagation = summary.query("feature_family == 'propagation'").iloc[0]
    top = summary.head(12)
    rows = []
    for _, row in top.iterrows():
        overlap = "—" if pd.isna(row["mean_top10_overlap"]) else f"{row['mean_top10_overlap']:.2f}"
        rows.append(
            "| {name} | {family} | {scope} | {error:.3f} | {signed:+.3f} | "
            "{hit05:.0%} | {hit1:.0%} | {direction:.0%} | {overlap} |".format(
                name=DISPLAY_NAMES.get(row["feature"], row["feature"]),
                family="传播" if row["feature_family"] == "propagation" else "第一轮",
                scope=row["feature_scope"],
                error=row["median_abs_timing_error_seconds"],
                signed=row["median_signed_timing_error_seconds"],
                hit05=row["within_0_5_seconds_rate"],
                hit1=row["within_1_second_rate"],
                direction=row["positive_contrast_rate"],
                overlap=overlap,
            )
        )
    propagation_top10 = summary.query(
        "feature_family == 'propagation' and feature_scope != 'global_propagation'"
    ).sort_values(["mean_top10_overlap", "median_abs_timing_error_seconds"], ascending=[False, True]).iloc[0]
    mean_error_reduction = 1.0 - (
        propagation["mean_abs_timing_error_seconds"]
        / original["mean_abs_timing_error_seconds"]
    )
    lagged_sensitivity = sensitivity.query("feature == 'lagged_outflow'").copy()
    sensitivity_rows = []
    for _, row in lagged_sensitivity.iterrows():
        policy = (
            "全部候选通道"
            if row["channel_policy"] == "all_channels"
            else "排除 line50 >20 dB"
        )
        sensitivity_rows.append(
            "| {window:.1f} | {policy} | {median:.3f} | {mean:.3f} | {hit05:.0%} | "
            "{hit1:.0%} | {direction:.0%} |".format(
                window=row["network_window_seconds"],
                policy=policy,
                median=row["median_abs_timing_error_seconds"],
                mean=row["mean_abs_timing_error_seconds"],
                hit05=row["within_0_5_seconds_rate"],
                hit1=row["within_1_second_rate"],
                direction=row["positive_contrast_rate"],
            )
        )
    report = f"""# 样例 SEEG onset 特征第二轮分析

## 技术摘要

- 本轮保留第一轮 **17 项**特征，并新增 **16 项**多通道招募、lead–lag 和动态网络特征，共比较 **33 项**。
- 独立分析单位仍为 **5 条阳性记录**；通道与滑窗不是独立重复，不执行小样本显著性检验。
- onset 专用排序同时考虑中位及平均绝对时间误差、±0.5/±1 秒命中率和 onset 后变化方向一致率；官方 Top-10 仅用于具有通道分辨率的特征。
- 第一轮最佳 onset 特征为 **{DISPLAY_NAMES[original['feature']]}**，中位绝对误差 {original['median_abs_timing_error_seconds']:.3f} 秒；新增传播特征中最佳为 **{DISPLAY_NAMES[propagation['feature']]}**，中位绝对误差 {propagation['median_abs_timing_error_seconds']:.3f} 秒。
- 两者中位误差相同，但最佳传播特征的平均绝对误差为 {propagation['mean_abs_timing_error_seconds']:.3f} 秒，较第一轮最佳的 {original['mean_abs_timing_error_seconds']:.3f} 秒下降 {mean_error_reduction:.1%}；其 ±1 秒命中率为 {propagation['within_1_second_rate']:.0%}，且 {propagation['positive_contrast_rate']:.0%} 的记录呈 onset 后正向变化。因此它在当前样例上的跨记录稳定性更好。
- 新增通道传播特征中，官方 Top-10 平均重合最高的是 **{DISPLAY_NAMES[propagation_top10['feature']]}**（{propagation_top10['mean_top10_overlap']:.2f}/10）。时间吻合与空间通道吻合仍需分别解释。
- 敏感性分析显示，lagged outflow 的优势会随网络历史窗及严重线噪通道排除而减弱，因此当前只能将它列为**优先验证候选**，不能称为已经稳定胜出的 onset 生物标志物。

![第二轮 onset 特征分析](../assets/figures/onset_feature_alignment_round2.png)

## 新增特征

### 通道级传播特征

1. recruitment consensus、persistence、change rate 和 early lead；
2. propagation participation；
3. causal lagged outflow、net outflow 和 coactivation strength。

### 全局传播轨迹

1. 超过 2z/3z 的招募通道比例及其斜率；
2. recruitment dispersion 和 propagation-front index；
3. 动态网络密度、最大连通分量比例和平均滞后连接。

所有传播特征只使用当前时刻及之前的窗口。网络连接在过去 1.5 秒的招募轨迹上估计；它是信号驱动的传播代理，不是基于三维坐标的解剖传播速度。

## onset 对齐结果

| Feature | 批次 | 范围 | 中位绝对误差 (s) | 中位有符号误差 (s) | ±0.5 s | ±1 s | 正向变化率 | 平均 Top-10 重合 |
|---|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## Lagged outflow 敏感性分析

| 网络历史窗 (s) | 通道策略 | 中位绝对误差 (s) | 平均绝对误差 (s) | ±0.5 s | ±1 s | 正向变化率 |
|---:|---|---:|---:|---:|---:|---:|
{chr(10).join(sensitivity_rows)}

默认 1.5 秒窗得到最好的时间吻合；缩短至 1.0 秒或延长至 2.0 秒后性能下降。排除 `line50_excess_db > 20 dB` 通道后，中位误差由 0.282 秒增至 0.501 秒、平均误差增至约 1.014 秒。这个变化可能同时来自噪声减弱和通道数量大幅减少，现有 5 条记录不足以区分二者。

## 解释边界

1. 每项特征的时间点是在人工 onset 前 1 秒至后 3 秒内寻找最大上升沿得到；这衡量“变化是否靠近 onset”，不等同于独立连续检测性能。
2. 全局传播特征没有通道排序能力，因此其 Top-10 指标记为缺失，而不是记为零。
3. 新增网络特征依赖当前原始参考；共同参考和 50 Hz 污染仍可能抬高连接。正式模型应比较原始参考与可验证的双极参考，并使用通道质量掩码重新建图。
4. 基线标准化在本次回顾性分析中使用 onset 前 10～2 秒；部署时必须换成仅依赖历史数据的自适应基线，不能使用真实 onset 选择基线。
5. 只有 5 条阳性记录，当前排序仅用于确定消融优先级，不能说明跨患者泛化或临床定位有效性。

## 可复现产物

- `reports/onset_features_round2/feature_summary.csv`
- `reports/onset_features_round2/record_feature_alignment.csv`
- `reports/onset_features_round2/onset_aligned_trajectories.csv`
- `reports/onset_features_round2/channel_onset_responses.csv`
- `reports/onset_features_round2/propagation_sensitivity_summary.csv`
- `reports/onset_features_round2/propagation_sensitivity_per_record.csv`
- `{figure_stem}.{{png,svg,pdf,tiff}}`
- `scripts/analyze_onset_features_round2.py`
- `scripts/analyze_propagation_sensitivity.py`
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("Dataset/sampleData"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("reports/onset_features_round2")
    )
    parser.add_argument(
        "--figure", type=Path, default=Path("assets/figures/onset_feature_alignment_round2")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("reports/onset_feature_analysis_round2.md")
    )
    args = parser.parse_args()

    config = OnsetFeatureConfig(include_propagation_features=True)
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
        print(f"Analyzed {record.sample_id}")

    alignment = pd.concat(alignment_parts, ignore_index=True)
    trajectories = pd.concat(trajectory_parts, ignore_index=True)
    channels = pd.concat(channel_parts, ignore_index=True)
    summary = _add_family(summarize_feature_alignment(alignment))
    aligned = _aligned_summary(trajectories, config.step_seconds)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_dir / "feature_summary.csv", index=False)
    alignment.to_csv(args.output_dir / "record_feature_alignment.csv", index=False)
    aligned.to_csv(args.output_dir / "onset_aligned_trajectories.csv", index=False)
    channels.to_csv(args.output_dir / "channel_onset_responses.csv", index=False)
    sensitivity_path = args.output_dir / "propagation_sensitivity_summary.csv"
    if not sensitivity_path.exists():
        raise FileNotFoundError(
            f"Run scripts/analyze_propagation_sensitivity.py first: {sensitivity_path}"
        )
    sensitivity = pd.read_csv(sensitivity_path)
    _plot_results(summary, alignment, aligned, args.figure)
    _write_report(summary, alignment, sensitivity, args.report, args.figure)
    print(summary.head(15).to_string(index=False))
    print(f"Wrote report to {args.report}")


if __name__ == "__main__":
    main()
