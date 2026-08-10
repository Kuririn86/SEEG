from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


# Nature-figure contract
# Core conclusion: a compact time/time-frequency backbone produces the four
# competition outputs; graph and spatial modules remain outside the base path.
# Archetype: schematic-led composite (hero workflow + output evidence + scope).
# Integrity: every trace below is a schematic, not patient data.

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().with_name("nature-model-architecture-v1")
FONT_PATH = ROOT / "SimSun.ttf"
if FONT_PATH.exists():
    font_manager.fontManager.addfont(str(FONT_PATH))

# Mandatory editable-SVG and publication settings.
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "SimSun", "DejaVu Sans", "Liberation Sans"],
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "font.size": 7.0,
    "axes.linewidth": 0.7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
})


COL = {
    "ink": "#27323A",
    "muted": "#68747D",
    "line": "#AAB4BA",
    "blue": "#3E6F92",
    "blue_pale": "#EAF1F6",
    "teal": "#4D9A98",
    "teal_pale": "#E9F4F2",
    "orange": "#D28A38",
    "orange_pale": "#FAF0E3",
    "red": "#B75B57",
    "red_pale": "#F8ECEB",
    "grey_pale": "#F3F5F6",
    "white": "#FFFFFF",
}


def clean_ax(ax):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_facecolor("white")


def box(ax, x, y, w, h, *, fc, ec, lw=0.9, radius=0.018, z=2):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.006,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z,
    )
    ax.add_patch(patch)
    return patch


def arrow(ax, start, end, *, color=None, lw=1.15, style="-|>", mutation=8, z=4):
    a = FancyArrowPatch(
        start, end, arrowstyle=style, mutation_scale=mutation,
        linewidth=lw, color=color or COL["ink"],
        shrinkA=1.5, shrinkB=1.5, zorder=z,
    )
    ax.add_patch(a)
    return a


def label(ax, x, y, text, *, size=7, weight="normal", color=None,
          ha="center", va="center", z=6, linespacing=1.25):
    return ax.text(
        x, y, text, fontsize=size, fontweight=weight,
        color=color or COL["ink"], ha=ha, va=va,
        zorder=z, linespacing=linespacing,
    )


def waveform(ax, x, y, w, h, *, seizure=False, color=None, lw=0.9, seed=0):
    t = np.linspace(0, 1, 220)
    base = 0.06 * np.sin(2 * np.pi * (7 * t + 0.3 * np.sin(2 * np.pi * t)))
    # Deterministic schematic texture; this is not sampled or patient-derived data.
    base += 0.009 * np.sin(2 * np.pi * ((23 + seed) * t + 0.17 * seed))
    if seizure:
        env = 1 / (1 + np.exp(-28 * (t - 0.48)))
        base += env * (0.18 * np.sin(2 * np.pi * 18 * t))
    ax.plot(x + w * t, y + h * (0.5 + base), color=color or COL["blue"], lw=lw, zorder=5)


def stage_title(ax, x, y, number, title):
    label(ax, x, y, number, size=6.8, weight="bold", color=COL["white"])
    ax.add_patch(plt.Circle((x, y), 0.018, color=COL["blue"], zorder=5))
    label(ax, x + 0.029, y, title, size=7.2, weight="bold", ha="left")


def panel_a(ax):
    clean_ax(ax)
    label(ax, -0.015, 1.01, "a", size=10, weight="bold", ha="left", va="bottom")
    label(ax, 0.02, 1.01, "默认推理主干", size=8.4, weight="bold", ha="left", va="bottom")
    label(ax, 0.98, 1.01, "示意波形，非患者数据", size=6.2, color=COL["muted"], ha="right", va="bottom")

    # Stage 1: multichannel input
    box(ax, 0.015, 0.23, 0.135, 0.57, fc=COL["grey_pale"], ec=COL["line"])
    stage_title(ax, 0.039, 0.75, "1", "输入")
    for i, c in enumerate([COL["blue"], COL["teal"], COL["red"]]):
        waveform(ax, 0.032, 0.58 - i * 0.095, 0.10, 0.10, seizure=(i == 2), color=c, seed=i)
    label(ax, 0.083, 0.315, r"$X\in\mathbb{R}^{B\times C\times T}$", size=7.0)
    label(ax, 0.083, 0.265, "通道 ID · 采样信息", size=6.2, color=COL["muted"])

    # Stage 2: preprocessing
    box(ax, 0.18, 0.23, 0.145, 0.57, fc=COL["grey_pale"], ec=COL["line"])
    stage_title(ax, 0.204, 0.75, "2", "预处理")
    waveform(ax, 0.205, 0.62, 0.095, 0.08, color=COL["line"], seed=3)
    arrow(ax, (0.225, 0.565), (0.278, 0.565), color=COL["muted"], lw=0.8, mutation=6)
    waveform(ax, 0.205, 0.49, 0.095, 0.08, color=COL["teal"], seed=4)
    for i, c in enumerate([COL["blue"], COL["teal"], COL["line"], COL["orange"], COL["red"]]):
        ax.add_patch(Rectangle((0.207 + i * 0.018, 0.395), 0.015, 0.035, facecolor=c, edgecolor="none", zorder=5))
    label(ax, 0.252, 0.32, "重采样 · 滤波 · MAD", size=6.3)
    label(ax, 0.252, 0.275, "坏道与时间掩码", size=6.3, color=COL["muted"])

    # Stage 3: dual encoder, hero block
    box(ax, 0.355, 0.13, 0.265, 0.75, fc=COL["blue_pale"], ec=COL["blue"], lw=1.1)
    stage_title(ax, 0.379, 0.83, "3", "双分支共享编码")
    box(ax, 0.375, 0.51, 0.225, 0.245, fc=COL["white"], ec=COL["line"], lw=0.75)
    label(ax, 0.393, 0.716, "时域分支", size=7.2, weight="bold", ha="left")
    for i, (span, c) in enumerate([(0.035, COL["blue"]), (0.07, COL["teal"]), (0.115, COL["red"])]):
        yy = 0.652 - i * 0.055
        ax.plot([0.405, 0.405 + span], [yy, yy], color=c, lw=1.2, zorder=5)
        ax.plot([0.417, 0.417 + span * 0.35], [yy - 0.015, yy + 0.015], color=c, lw=0.8, zorder=5)
    label(ax, 0.485, 0.545, "多尺度一维卷积＋SiLU", size=6.2)

    box(ax, 0.375, 0.19, 0.225, 0.245, fc=COL["white"], ec=COL["line"], lw=0.75)
    label(ax, 0.393, 0.395, "时频分支", size=7.2, weight="bold", ha="left")
    heat = np.array([
        [0.15, 0.18, 0.25, 0.42, 0.68, 0.88, 0.78, 0.55],
        [0.22, 0.28, 0.35, 0.55, 0.82, 0.95, 0.72, 0.40],
        [0.34, 0.38, 0.44, 0.58, 0.72, 0.60, 0.43, 0.30],
    ])
    ax.imshow(heat, extent=(0.405, 0.565, 0.255, 0.345), origin="lower", cmap="Blues", vmin=0, vmax=1, aspect="auto", zorder=5)
    label(ax, 0.485, 0.215, "STFT＋轻量频带映射", size=6.2)

    # Stage 4: fusion
    box(ax, 0.65, 0.23, 0.135, 0.57, fc=COL["teal_pale"], ec=COL["teal"], lw=1.0)
    stage_title(ax, 0.674, 0.75, "4", "门控融合")
    arrow(ax, (0.675, 0.61), (0.716, 0.535), color=COL["blue"], lw=0.9, mutation=6)
    arrow(ax, (0.675, 0.46), (0.716, 0.525), color=COL["teal"], lw=0.9, mutation=6)
    ax.add_patch(plt.Circle((0.727, 0.53), 0.025, facecolor=COL["orange_pale"], edgecolor=COL["orange"], lw=0.9, zorder=5))
    label(ax, 0.727, 0.53, "$G$", size=7.2)
    arrow(ax, (0.752, 0.53), (0.772, 0.53), color=COL["orange"], lw=0.9, mutation=6)
    label(ax, 0.717, 0.39, r"$H=G H_{time}$", size=6.5)
    label(ax, 0.717, 0.335, r"$+(1-G)H_{tf}$", size=6.5)
    label(ax, 0.717, 0.275, "自动权衡证据", size=6.1, color=COL["muted"])

    # Stage 5: temporal model
    box(ax, 0.815, 0.23, 0.17, 0.57, fc=COL["orange_pale"], ec=COL["orange"], lw=1.0)
    stage_title(ax, 0.839, 0.75, "5", "长程 TCN")
    t = np.linspace(0, 1, 120)
    p = 0.08 + 0.84 / (1 + np.exp(-18 * (t - 0.55)))
    ax.plot(0.84 + 0.12 * t, 0.48 + 0.14 * p, color=COL["blue"], lw=1.3, zorder=5)
    ax.axvline(0.84 + 0.12 * 0.55, ymin=0.40, ymax=0.67, color=COL["red"], lw=0.9, ls="--", zorder=4)
    label(ax, 0.906, 0.66, "onset", size=5.8, color=COL["red"])
    label(ax, 0.90, 0.39, "背景 → 起始 → 发作", size=6.2)
    label(ax, 0.90, 0.315, "持续性与状态演化", size=6.1, color=COL["muted"])

    # Main flow arrows
    arrow(ax, (0.15, 0.515), (0.18, 0.515))
    arrow(ax, (0.325, 0.515), (0.355, 0.515))
    arrow(ax, (0.62, 0.515), (0.65, 0.515))
    arrow(ax, (0.785, 0.515), (0.815, 0.515))


def panel_b(ax):
    clean_ax(ax)
    label(ax, -0.02, 1.02, "b", size=10, weight="bold", ha="left", va="bottom")
    label(ax, 0.03, 1.02, "多任务输出与正式提交结果", size=8.4, weight="bold", ha="left", va="bottom")

    # Four compact evidence cells
    cells = [
        (0.02, 0.56, "片段状态", COL["blue_pale"], COL["blue"]),
        (0.37, 0.56, "帧级状态", COL["blue_pale"], COL["blue"]),
        (0.02, 0.12, "onset 边界", COL["orange_pale"], COL["orange"]),
        (0.37, 0.12, "通道贡献", COL["teal_pale"], COL["teal"]),
    ]
    for x, y, title, fc, ec in cells:
        box(ax, x, y, 0.30, 0.32, fc=fc, ec=ec, lw=0.8)
        label(ax, x + 0.02, y + 0.275, title, size=6.9, weight="bold", ha="left")

    # clip probability
    ax.add_patch(Rectangle((0.05, 0.66), 0.22, 0.055, facecolor=COL["white"], edgecolor=COL["line"], lw=0.6))
    ax.add_patch(Rectangle((0.05, 0.66), 0.18, 0.055, facecolor=COL["blue"], edgecolor="none"))
    label(ax, 0.16, 0.62, r"$p_{clip}$", size=6.2)

    # frame probability
    t = np.linspace(0, 1, 80)
    p = 0.08 + 0.85 / (1 + np.exp(-14 * (t - 0.56)))
    ax.plot(0.40 + 0.23 * t, 0.64 + 0.12 * p, color=COL["blue"], lw=1.2)
    label(ax, 0.515, 0.62, r"$p_{state,k}$", size=6.2)

    # onset peak
    peak = np.exp(-0.5 * ((t - 0.55) / 0.075) ** 2)
    ax.plot(0.05 + 0.22 * t, 0.20 + 0.12 * peak, color=COL["orange"], lw=1.2)
    label(ax, 0.16, 0.16, r"$p_{onset,k}$", size=6.2)

    # channel scores
    vals = np.array([0.92, 0.77, 0.64, 0.52, 0.46, 0.33, 0.24, 0.18])
    colors = mpl.colormaps["Blues"](0.25 + 0.7 * vals)
    for i, (v, c) in enumerate(zip(vals, colors)):
        ax.add_patch(Rectangle((0.40 + i * 0.027, 0.205), 0.022, 0.095 * v, facecolor=c, edgecolor="none"))
    label(ax, 0.51, 0.16, r"$I_c^{model}$", size=6.2)

    # Submission products, visually subordinate but explicit
    box(ax, 0.71, 0.57, 0.27, 0.24, fc=COL["grey_pale"], ec=COL["line"], lw=0.8)
    label(ax, 0.845, 0.72, "概率校准＋阈值", size=6.2)
    label(ax, 0.845, 0.64, "标签＋六位小数概率", size=7.0, weight="bold", color=COL["blue"])
    box(ax, 0.71, 0.32, 0.27, 0.19, fc=COL["grey_pale"], ec=COL["line"], lw=0.8)
    label(ax, 0.845, 0.415, "滑窗融合＋持续性＋延迟校正", size=6.0)
    label(ax, 0.845, 0.355, "onset 时间", size=7.0, weight="bold", color=COL["orange"])
    box(ax, 0.71, 0.07, 0.27, 0.19, fc=COL["grey_pale"], ec=COL["line"], lw=0.8)
    label(ax, 0.845, 0.165, "伪迹惩罚＋遮挡/稳定性验证", size=6.0)
    label(ax, 0.845, 0.105, "官方 Top-10 通道", size=7.0, weight="bold", color=COL["teal"])
    arrow(ax, (0.32, 0.79), (0.71, 0.74), color=COL["line"], lw=0.8, mutation=6)
    arrow(ax, (0.67, 0.63), (0.71, 0.65), color=COL["line"], lw=0.8, mutation=6)
    arrow(ax, (0.32, 0.27), (0.71, 0.415), color=COL["line"], lw=0.8, mutation=6)
    arrow(ax, (0.67, 0.27), (0.71, 0.165), color=COL["line"], lw=0.8, mutation=6)


def panel_c(ax):
    clean_ax(ax)
    label(ax, -0.04, 1.02, "c", size=10, weight="bold", ha="left", va="bottom")
    label(ax, 0.04, 1.02, "模块边界与解释范围", size=8.4, weight="bold", ha="left", va="bottom")

    rows = [
        (0.68, "基础链路", "时域卷积 · STFT · 门控 · TCN · 四个任务头", COL["blue_pale"], COL["blue"]),
        (0.43, "验证后启用", "onset 专项监督 · 动态通道图", COL["teal_pale"], COL["teal"]),
        (0.18, "条件模块", "电极坐标 · 接点—脑区映射", COL["grey_pale"], COL["line"]),
    ]
    for y, title, detail, fc, ec in rows:
        box(ax, 0.03, y, 0.94, 0.17, fc=fc, ec=ec, lw=0.8)
        label(ax, 0.08, y + 0.105, title, size=6.9, weight="bold", ha="left", color=ec if ec != COL["line"] else COL["ink"])
        label(ax, 0.08, y + 0.052, detail, size=6.0, ha="left", color=COL["muted"])
    label(ax, 0.50, 0.075, "Top-10 是模型贡献排序，不是临床 SOZ/EZ 结论", size=6.4, weight="bold", color=COL["red"])
    ax.plot([0.05, 0.95], [0.115, 0.115], color=COL["red"], lw=0.7)


def build_figure():
    # A wide landscape ratio lets the figure fill an A4 landscape page without
    # shrinking the labels to satisfy a height constraint.
    fig = plt.figure(figsize=(7.2, 4.6), facecolor="white")
    gs = fig.add_gridspec(
        2, 5,
        height_ratios=[1.62, 1.0],
        width_ratios=[1, 1, 1, 0.76, 0.76],
        hspace=0.22, wspace=0.28,
        left=0.035, right=0.985, top=0.965, bottom=0.06,
    )
    ax_a = fig.add_subplot(gs[0, :])
    ax_b = fig.add_subplot(gs[1, :3])
    ax_c = fig.add_subplot(gs[1, 3:])
    panel_a(ax_a)
    panel_b(ax_b)
    panel_c(ax_c)
    return fig


def save(fig):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    fig.savefig(OUT.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    fig.savefig(OUT.with_suffix(".png"), dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT.with_suffix(".tiff"), dpi=600, bbox_inches="tight", facecolor="white", pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)


if __name__ == "__main__":
    save(build_figure())
