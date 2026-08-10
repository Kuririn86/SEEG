from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Arc, Circle, PathPatch, Polygon
from matplotlib.path import Path as MplPath


# Figure contract
# Core conclusion: line width and w_ij(t) encode illustrative, time-varying
# channel association strength; they do not represent anatomical or causal links.
# Archetype: schematic-led topographic network.
# Integrity: all positions and weights are illustrative, not patient data.

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().with_name("dynamic-channel-graph-topview-v1")
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

INK = "#253744"
MUTED = "#6F7B84"
HEAD = "#D7DEE2"
NODE = "#36779A"
NODE_EDGE = "#234F69"
EDGE = "#2F8F92"
ACCENT = "#D18935"


NODES = {
    "F3": (-0.38, 0.53),
    "F4": (0.38, 0.53),
    "C3": (-0.52, 0.06),
    "Cz": (0.00, 0.13),
    "C4": (0.52, 0.06),
    "P3": (-0.38, -0.40),
    "P4": (0.38, -0.40),
    "Oz": (0.00, -0.70),
}

# Illustrative dynamic weights only.
EDGES = [
    ("F3", "C3", 0.82, (-0.51, 0.30)),
    ("F3", "Cz", 0.56, (-0.18, 0.35)),
    ("F4", "Cz", 0.71, (0.18, 0.35)),
    ("F4", "C4", 0.91, (0.51, 0.30)),
    ("C3", "Cz", 0.64, (-0.26, 0.14)),
    ("Cz", "C4", 0.77, (0.26, 0.14)),
    ("C3", "P3", 0.88, (-0.51, -0.18)),
    ("C4", "P4", 0.59, (0.51, -0.18)),
    ("Cz", "P4", 0.68, (0.23, -0.17)),
    ("P3", "Oz", 0.74, (-0.20, -0.57)),
    ("P4", "Oz", 0.52, (0.20, -0.57)),
]


def head_outline(ax):
    # Smooth top-down head silhouette with a subtle central sagittal guide.
    verts = [
        (0.00, 0.92),
        (-0.52, 0.90), (-0.77, 0.50), (-0.74, 0.00),
        (-0.72, -0.46), (-0.42, -0.86), (0.00, -0.88),
        (0.42, -0.86), (0.72, -0.46), (0.74, 0.00),
        (0.77, 0.50), (0.52, 0.90), (0.00, 0.92),
    ]
    codes = [MplPath.MOVETO] + [MplPath.CURVE4] * 12
    patch = PathPatch(MplPath(verts, codes), facecolor="#F7F9FA", edgecolor=HEAD, lw=1.5, zorder=0)
    ax.add_patch(patch)
    # Nose and ears retain the familiar topograph orientation cues.
    ax.add_patch(Polygon([(-0.09, 0.90), (0.00, 1.03), (0.09, 0.90)], closed=False,
                         fill=False, edgecolor=HEAD, lw=1.5, zorder=1))
    ax.add_patch(Arc((-0.76, 0.02), 0.18, 0.35, theta1=75, theta2=285, color=HEAD, lw=1.4, zorder=1))
    ax.add_patch(Arc((0.76, 0.02), 0.18, 0.35, theta1=-105, theta2=105, color=HEAD, lw=1.4, zorder=1))
    ax.plot([0, 0], [0.84, -0.82], color=HEAD, lw=0.55, ls=(0, (2, 3)), zorder=0)


def edge_width(weight):
    return 0.5 + 4.2 * weight


def build_figure():
    fig, ax = plt.subplots(figsize=(3.5, 4.0), facecolor="white")
    fig.subplots_adjust(left=0.04, right=0.96, top=0.91, bottom=0.10)
    ax.set_aspect("equal")
    ax.set_xlim(-1.02, 1.02)
    ax.set_ylim(-1.05, 1.10)
    ax.axis("off")

    ax.text(0.0, 1.085, "动态通道图示意（俯视）", ha="center", va="bottom",
            fontsize=9.0, fontweight="bold", color=INK)
    head_outline(ax)

    # Draw edges before nodes so all nodes remain visually foregrounded.
    for a, b, weight, label_xy in EDGES:
        xa, ya = NODES[a]
        xb, yb = NODES[b]
        ax.plot([xa, xb], [ya, yb], color=EDGE, lw=edge_width(weight),
                alpha=0.30 + 0.62 * weight, solid_capstyle="round", zorder=2)
        ax.text(*label_xy, f"w={weight:.2f}", ha="center", va="center",
                fontsize=5.2, color=INK, fontfamily="DejaVu Sans", zorder=5,
                bbox={"boxstyle": "round,pad=0.10", "fc": "white", "ec": "none", "alpha": 0.88})

    for name, (x, y) in NODES.items():
        ax.add_patch(Circle((x, y), 0.085, facecolor=NODE, edgecolor=NODE_EDGE, lw=1.0, zorder=6))
        ax.text(x, y, name, ha="center", va="center", fontsize=6.2,
                fontweight="bold", fontfamily="DejaVu Sans", color="white", zorder=7)

    # Compact encoding key.
    y0 = -0.94
    ax.text(-0.73, y0, "连接强度", ha="left", va="center", fontsize=5.8, color=MUTED)
    for x, weight in [(-0.38, 0.25), (-0.05, 0.55), (0.30, 0.90)]:
        ax.plot([x, x + 0.18], [y0, y0], color=EDGE, lw=edge_width(weight), alpha=0.72,
                solid_capstyle="round")
        ax.text(x + 0.09, y0 - 0.065, f"w={weight:.2f}", ha="center", va="top",
                fontsize=5.0, fontfamily="DejaVu Sans", color=MUTED)

    ax.text(0.0, -1.035, r"边权 $w_{ij}(t)$ 随时间窗更新；示意值，非患者数据",
            ha="center", va="top", fontsize=5.6, color=ACCENT, fontweight="bold")
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
    fig.savefig(OUT.with_name(OUT.name + "-transparent").with_suffix(".png"),
                dpi=600, bbox_inches="tight", transparent=True)
    plt.close(fig)


if __name__ == "__main__":
    save(build_figure())
