"""
Render mockups of the rhombicosidodecahedron lamp geometry.

    images/mockup_faces.png  - coloured pentagon / square / triangle tessellation
    images/mockup_frame.png  - plain wireframe: the 60 vertices + 120 edges

Run:  uv run python src/mockups/build_mockups.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # src/ -> import core

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

from core import geometry

IMAGES = Path(__file__).resolve().parents[2] / "images"

COLORS = {3: "#e8743b", 4: "#7eb6d9", 5: "#f2c14e"}  # triangle / square / pentagon


def _style(ax):
    ax.set_box_aspect((1, 1, 1))
    lim = 1.05
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim, lim)
    ax.set_axis_off()
    ax.view_init(elev=18, azim=32)


def render_faces(V, F):
    counts = {n: sum(len(f) == n for f in F) for n in (3, 4, 5)}
    fig = plt.figure(figsize=(9, 9))
    ax = fig.add_subplot(111, projection="3d")
    pc = Poly3DCollection([V[f] for f in F], alpha=0.92, linewidths=0.6, edgecolor="#333")
    pc.set_facecolor([COLORS[len(f)] for f in F])
    ax.add_collection3d(pc)
    _style(ax)
    ax.set_title("Rhombicosidodecahedron tessellation\n"
                 f"{counts[5]} pentagons (yellow) · {counts[4]} squares (blue) · "
                 f"{counts[3]} triangles (orange)", fontsize=11)
    fig.savefig(IMAGES / "mockup_faces.png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("saved mockup_faces.png")


def render_frame(V, E, stars):
    fig = plt.figure(figsize=(9, 9))
    ax = fig.add_subplot(111, projection="3d")
    segs = [[V[i], V[j]] for i, j in E]
    ax.add_collection3d(Line3DCollection(segs, colors="#5a6b75", linewidths=2.0))
    ax.scatter(V[:, 0], V[:, 1], V[:, 2], s=28, c="#222", depthshade=True)

    # star hub + 5 spokes at the centre of each pentagon
    spokes = [[c, V[vi]] for c, corners in stars for vi in corners]
    ax.add_collection3d(Line3DCollection(spokes, colors=COLORS[5], linewidths=1.6))
    C = np.array([c for c, _ in stars])
    ax.scatter(C[:, 0], C[:, 1], C[:, 2], s=55, c=COLORS[5], edgecolor="#222",
               linewidth=0.5, depthshade=True)

    _style(ax)
    ax.set_title(f"Vertices + edges ({len(V)} verts, {len(E)} edges) "
                 f"+ {len(stars)} pentagon stars", fontsize=11)
    fig.savefig(IMAGES / "mockup_frame.png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("saved mockup_frame.png")


def main():
    V, F, E = geometry.build()
    render_faces(V, F)
    render_frame(V, E, geometry.pentagon_stars(V, F))


if __name__ == "__main__":
    main()
