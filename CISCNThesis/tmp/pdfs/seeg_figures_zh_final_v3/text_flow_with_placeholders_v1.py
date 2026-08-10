from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


# Figure contract
# Core conclusion: the complete text workflow remains the primary explanation;
# four empty slots are reserved for user-supplied illustrations.
# Archetype: schematic-led composite, with a single left-to-right hero workflow.
# Integrity: placeholders contain no generated or patient-derived data.

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().with_name("text-flow-with-placeholders-v1")
FONT_PATH = ROOT / "SimSun.ttf"
if FONT_PATH.exists():
    font_manager.fontManager.addfont(str(FONT_PATH))

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "SimSun", "DejaVu Sans", "Liberation Sans"],
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "font.size": 7.0,
    "axes.linewidth": 0.7,
})

COL = {
    "ink": "#243746",
    "muted": "#6F7B84",
    "line": "#AEB8BE",
    "blue": "#315B78",
    "blue_pale": "#F3F7FA",
    "teal": "#2F8F92",
    "teal_pale": "#F2F9F8",
    "orange": "#CC8731",
    "orange_pale": "#FCF7EF",
    "red": "#C45A53",
    "red_pale": "#FCF5F4",
    "slot": "#DCE3E7",
    "white": "#FFFFFF",
}


def clean(ax):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def box(ax, x, y, w, h, *, fc, ec, lw=0.85, radius=0.012, ls="-"):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.004,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=ls,
        zorder=2,
    )
    ax.add_patch(patch)
    return patch


def text(ax, x, y, value, *, size=7, weight="normal", color=None,
         ha="center", va="center", linespacing=1.22, z=5):
    return ax.text(
        x, y, value, fontsize=size, fontweight=weight,
        color=color or COL["ink"], ha=ha, va=va,
        linespacing=linespacing, zorder=z,
    )


def arrow(ax, x1, y1, x2, y2, *, color=None, lw=0.9, dashed=False):
    patch = FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=7,
        linewidth=lw, color=color or COL["ink"],
        linestyle="--" if dashed else "-", shrinkA=1, shrinkB=1, zorder=4,
    )
    ax.add_patch(patch)


def main_stage(ax, x, y, w, h, number, title, body, *, fc=None, ec=None,
               body_size=5.8, title_size=6.6):
    box(ax, x, y, w, h, fc=fc or COL["blue_pale"], ec=ec or COL["blue"], lw=0.9)
    text(ax, x + w / 2, y + h - 0.045, f"{number}  {title}", size=title_size, weight="bold")
    text(ax, x + w / 2, y + h * 0.46, body, size=body_size, linespacing=1.34)


def placeholder(ax, x, y, w, h, letter, title, hint):
    box(ax, x, y, w, h, fc=COL["white"], ec=COL["line"], lw=0.8, ls=(0, (3, 2)))
    text(ax, x + 0.018, y + h - 0.026, letter, size=6.0, weight="bold",
         color=COL["white"])
    ax.add_patch(plt.Circle((x + 0.018, y + h - 0.026), 0.012, color=COL["muted"], zorder=4))
    text(ax, x + 0.036, y + h - 0.026, title, size=6.2, weight="bold", ha="left")
    text(ax, x + w / 2, y + h * 0.42, "图片插入区", size=7.0, weight="bold", color=COL["line"])
    text(ax, x + w / 2, y + 0.025, hint, size=5.2, color=COL["muted"])


def build_figure():
    fig, ax = plt.subplots(figsize=(7.2, 4.35), facecolor="white")
    fig.subplots_adjust(left=0.018, right=0.988, top=0.965, bottom=0.035)
    clean(ax)

    text(ax, 0.015, 0.965, "SEEG 发作检测模型：基础推理链路与四项比赛输出",
         size=9.0, weight="bold", ha="left")
    text(ax, 0.985, 0.965, "全文本流程为主；虚线框由作者自行插图",
         size=5.8, color=COL["muted"], ha="right")
    ax.plot([0.015, 0.985], [0.925, 0.925], color=COL["line"], lw=0.55)

    # Complete text-first inference chain.
    y, h = 0.505, 0.355
    main_stage(ax, 0.012, y, 0.102, h, "1", "原始输入",
               "多通道 SEEG\n$X\in\mathbb{R}^{B\\times C\\times T}$\n通道 ID\n采样率与有效长度")
    main_stage(ax, 0.132, y, 0.115, h, "2", "预处理与切窗",
               "重采样、滤波\n坏道与伪迹标记\nMAD 稳健标准化\n输出窗口 $X$\n＋通道/时间掩码")

    box(ax, 0.267, y - 0.012, 0.192, h + 0.024, fc=COL["blue_pale"], ec=COL["blue"], lw=0.9)
    text(ax, 0.363, y + h - 0.035, "3  双分支共享编码", size=6.6, weight="bold")
    box(ax, 0.279, y + 0.185, 0.168, 0.115, fc=COL["white"], ec=COL["blue"], lw=0.7)
    text(ax, 0.363, y + 0.265, "时域分支", size=6.1, weight="bold")
    text(ax, 0.363, y + 0.215, "共享多尺度一维卷积＋SiLU\n识别尖波、节律和波形演化", size=5.5)
    box(ax, 0.279, y + 0.035, 0.168, 0.115, fc=COL["white"], ec=COL["blue"], lw=0.7)
    text(ax, 0.363, y + 0.115, "时频分支", size=6.1, weight="bold")
    text(ax, 0.363, y + 0.065, "STFT＋轻量频带映射\n识别频带能量和频率迁移", size=5.5)

    main_stage(ax, 0.480, y, 0.125, h, "4", "帧率对齐与门控融合",
               "$H=G\odot H_{time}$\n$+(1-G)\odot H_{tf}$\n自动权衡两类证据",
               body_size=5.7, title_size=5.7)
    main_stage(ax, 0.625, y, 0.125, h, "5", "长程 TCN",
               "观察异常是否持续\n建模背景→起始\n→发作演化\n排除孤立尖波", body_size=5.7)

    # Four task heads and official products.
    box(ax, 0.770, y - 0.012, 0.105, h + 0.024, fc=COL["red_pale"], ec=COL["red"], lw=0.8)
    text(ax, 0.8225, y + h + 0.035, "6  四个任务头", size=6.4, weight="bold")
    heads = [
        ("片段状态头", "$p_{clip}$"),
        ("帧级状态头", "$p_{state,k}$"),
        ("onset 边界头", "$p_{onset,k}$"),
        ("通道贡献头", "$I_c^{model}$"),
    ]
    for i, (title, symbol) in enumerate(heads):
        yy = y + 0.270 - i * 0.082
        box(ax, 0.781, yy, 0.083, 0.066, fc=COL["white"], ec=COL["red"], lw=0.65, radius=0.007)
        text(ax, 0.8225, yy + 0.043, title, size=5.3, weight="bold")
        text(ax, 0.8225, yy + 0.018, symbol, size=5.1)

    products = [
        (y + 0.278, "概率校准＋阈值\n标签＋六位小数概率", COL["orange"]),
        (y + 0.155, "滑窗融合＋持续性判定\n边界峰值＋延迟校正\nonset 时间", COL["orange"]),
        (y + 0.025, "伪迹惩罚＋稳定性验证\n贡献度排序\n官方 Top-10 通道", COL["orange"]),
    ]
    for yy, value, ec in products:
        hh = 0.08 if yy > y + 0.2 else 0.105
        box(ax, 0.895, yy, 0.098, hh, fc=COL["orange_pale"], ec=ec, lw=0.75, radius=0.007)
        text(ax, 0.944, yy + hh / 2, value, size=5.2, weight="bold" if "标签" in value or "Top-10" in value else "normal")

    # Main arrows.
    for x1, x2 in [(0.114, 0.132), (0.247, 0.267), (0.459, 0.480), (0.605, 0.625), (0.750, 0.770)]:
        arrow(ax, x1, y + h / 2, x2, y + h / 2)
    arrow(ax, 0.875, y + 0.305, 0.895, y + 0.318)
    arrow(ax, 0.875, y + 0.215, 0.895, y + 0.208)
    arrow(ax, 0.875, y + 0.075, 0.895, y + 0.075)

    # Optional research modules remain outside the base chain.
    optional = [
        (0.280, "研究性消融", "Morlet 对照 STFT\nSwiGLU 对照 SiLU"),
        (0.455, "动态通道图（可选）", "只做患者级验证\n稳定改善时启用"),
        (0.630, "空间解释（条件模块）", "需坐标与脑区映射\n不参与基础提交"),
    ]
    for x, title_value, body in optional:
        box(ax, x, 0.335, 0.155, 0.115, fc=COL["teal_pale"], ec=COL["teal"], lw=0.75, ls=(0, (3, 2)))
        text(ax, x + 0.0775, 0.415, title_value, size=5.6, weight="bold")
        text(ax, x + 0.0775, 0.365, body, size=5.2)
    arrow(ax, 0.357, 0.450, 0.350, y - 0.012, color=COL["teal"], lw=0.75, dashed=True)
    arrow(ax, 0.532, 0.450, 0.542, y, color=COL["teal"], lw=0.75, dashed=True)
    arrow(ax, 0.707, 0.450, 0.688, y, color=COL["teal"], lw=0.75, dashed=True)

    # Empty author-editable visual slots.
    placeholder(ax, 0.012, 0.055, 0.225, 0.205, "A", "输入示意", "建议：真实或脱敏后的多通道 SEEG 波形")
    placeholder(ax, 0.262, 0.055, 0.225, 0.205, "B", "时频特征示意", "建议：同一时间窗对应的 STFT 图")
    placeholder(ax, 0.512, 0.055, 0.225, 0.205, "C", "状态与 onset 示意", "建议：状态概率曲线＋专家 onset 标记")
    placeholder(ax, 0.762, 0.055, 0.225, 0.205, "D", "通道贡献示意", "建议：Top-10 条形图或电极位置图")

    text(ax, 0.50, 0.012,
         "解释边界：Top-10 表示模型贡献排序；不得直接写成临床 SOZ、EZ 或手术靶点。",
         size=5.6, weight="bold", color=COL["red"])
    return fig


def save(fig):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    fig.savefig(OUT.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    fig.savefig(OUT.with_suffix(".png"), dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(
        OUT.with_suffix(".tiff"), dpi=600, bbox_inches="tight", facecolor="white",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)


if __name__ == "__main__":
    save(build_figure())
