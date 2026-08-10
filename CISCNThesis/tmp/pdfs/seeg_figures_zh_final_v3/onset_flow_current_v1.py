from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


# Figure contract
# Core conclusion: onset is selected from continuous state, boundary, duration,
# and artifact evidence, then exception-routed and time-corrected.
# Archetype: text-first schematic-led composite plus one author image slot.
# Integrity: the empty slot contains no generated or patient-derived trace.

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().with_name("onset-flow-current-v1")
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
    "line": "#ADB8BE",
    "blue": "#315B78",
    "blue_pale": "#F2F6F9",
    "teal": "#2F8F92",
    "teal_pale": "#F1F9F8",
    "orange": "#CC8731",
    "orange_pale": "#FCF7EF",
    "red": "#C45A53",
    "red_pale": "#FCF4F3",
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
        facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=ls, zorder=2,
    )
    ax.add_patch(patch)
    return patch


def text(ax, x, y, value, *, size=7.0, weight="normal", color=None,
         ha="center", va="center", linespacing=1.24, z=5):
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


def stage(ax, x, y, w, h, number, title, body, *, accent="blue", body_size=5.9):
    ec = COL[accent]
    fc = COL[f"{accent}_pale"]
    box(ax, x, y, w, h, fc=fc, ec=ec, lw=0.9)
    text(ax, x + w / 2, y + h - 0.042, f"{number}  {title}", size=6.8, weight="bold")
    text(ax, x + w / 2, y + h * 0.43, body, size=body_size, linespacing=1.32)


def route(ax, x, y, w, h, condition, action, *, accent):
    box(ax, x, y, w, h, fc=COL[f"{accent}_pale"], ec=COL[accent], lw=0.72, radius=0.008)
    text(ax, x + 0.012, y + h - 0.030, condition, size=5.9, weight="bold", ha="left", color=COL[accent])
    text(ax, x + w / 2, y + h * 0.40, action, size=5.7, linespacing=1.25)


def build_figure():
    fig, ax = plt.subplots(figsize=(7.2, 4.1), facecolor="white")
    fig.subplots_adjust(left=0.018, right=0.988, top=0.965, bottom=0.035)
    clean(ax)

    text(ax, 0.015, 0.965, "onset 定位：从连续概率到唯一、可校正的时间点",
         size=9.0, weight="bold", ha="left")
    text(ax, 0.985, 0.965, "操作性边界遵循官方标注，不等同于真实 EZ 启动时刻",
         size=5.6, color=COL["muted"], ha="right")
    ax.plot([0.015, 0.985], [0.923, 0.923], color=COL["line"], lw=0.55)

    # Hero inference sequence.
    y, h = 0.655, 0.205
    stage(ax, 0.018, y, 0.142, h, "1", "重叠滑窗推理",
          "每个时间点可能由\n多个窗口重复预测\n保留时间掩码与质量信息")
    stage(ax, 0.183, y, 0.150, h, "2", "Hann 加权融合",
          "重建连续状态概率 $p_k$\n与边界概率 $b_k$\n补齐区域不参与搜索")
    stage(ax, 0.356, y, 0.225, h, "3", "生成并评分候选点",
          "状态持续上升＋边界局部峰值\n最短持续时间 $D_{min}$\n"
          r"$B_k=\rho_1b_k+\rho_2\Delta\mathrm{logit}(p_k)+\rho_3r_k$" "\n"
          r"$-\rho_4Q_k^{artifact}$",
          body_size=5.5)
    stage(ax, 0.604, y, 0.178, h, "4", "获得粗 onset",
          "选择第一个有效候选点\n不是第一次 $p_k>0.5$\n同时识别异常边界情况",
          accent="orange", body_size=5.8)
    stage(ax, 0.812, y, 0.170, h, "6", "时间校正与输出",
          "扣除滤波、重采样与\n滑窗中心偏移\n按有效分辨率输出 onset\n同时记录置信度和异常标记",
          accent="red", body_size=5.6)

    for x1, x2 in [(0.160, 0.183), (0.333, 0.356), (0.581, 0.604)]:
        arrow(ax, x1, y + h / 2, x2, y + h / 2)

    # Explicit exception/refinement routes, missing from the older diagram.
    box(ax, 0.018, 0.355, 0.764, 0.235, fc=COL["white"], ec=COL["line"], lw=0.75)
    text(ax, 0.035, 0.563, "5  根据片段状态与基线质量分流", size=6.2, weight="bold", ha="left")
    routes = [
        (0.035, "左端已处于发作态", "输出 onset=0\n标记为左删失", "red"),
        (0.220, "没有有效候选点", "不强行给高置信起点\n输出低置信或无候选标记", "red"),
        (0.405, "候选有效、基线不足", "保留粗 onset\n不启用相对基线精修", "orange"),
        (0.590, "候选有效、基线合格", "仅在粗 onset 邻域\n按相对基线变化精修", "teal"),
    ]
    for x, condition, action, accent in routes:
        route(ax, x, 0.382, 0.168, 0.145, condition, action, accent=accent)
    arrow(ax, 0.693, y, 0.693, 0.590, color=COL["orange"], dashed=True)
    text(ax, 0.706, 0.615, "分流", size=5.1, color=COL["orange"], ha="left")
    arrow(ax, 0.782, 0.472, 0.812, y + 0.055, color=COL["line"])

    # Empty slot for author-supplied probability curves.
    box(ax, 0.018, 0.075, 0.964, 0.215, fc=COL["white"], ec=COL["line"], lw=0.8, ls=(0, (3, 2)))
    ax.add_patch(plt.Circle((0.041, 0.255), 0.013, color=COL["muted"], zorder=4))
    text(ax, 0.041, 0.255, "A", size=5.8, weight="bold", color=COL["white"])
    text(ax, 0.061, 0.255, "作者图片插入区：状态概率、边界概率与 onset 标记", size=6.1, weight="bold", ha="left")
    text(ax, 0.50, 0.176, "图片插入区", size=8.0, weight="bold", color=COL["line"])
    text(ax, 0.50, 0.107,
         "建议横轴统一为时间；绘制 $p_k$ 与 $b_k$，标出粗 onset、精修 onset、持续时间区间和伪迹区间。",
         size=5.5, color=COL["muted"])

    text(ax, 0.50, 0.022,
         "判定原则：状态明显上升、边界清楚、上升后持续且伪迹风险可接受；最终精度不得超过标注与帧率支持的时间分辨率。",
         size=5.6, weight="bold", color=COL["blue"])
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
