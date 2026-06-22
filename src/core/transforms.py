"""Transform math shared by every model generator.

All orientation maths is done here in numpy and baked into the .scad files as
4x4 multmatrix transforms, so the .scad itself is just data + tiny modules.
Both the frame builders (frame/) and the assembly builder (assembly/) import
from here, so it lives in the shared `core` package rather than in any one
component.
"""

import numpy as np


def _unit(v):
    return v / np.linalg.norm(v)


def _matrix(col0, col1, col2, translate):
    """Row-major 4x4 mapping local x,y,z axes onto col0,col1,col2 (+translate)."""
    m = np.eye(4)
    m[:3, 0] = col0
    m[:3, 1] = col1
    m[:3, 2] = col2
    m[:3, 3] = translate
    return m


def _fmt_matrix(m):
    return "[" + ", ".join("[%.5f, %.5f, %.5f, %.5f]" % tuple(row) for row in m) + "]"


def bar_transforms(pairs, radius):
    """One transform per (a, b) bar: x-axis along the bar (length baked into its
    magnitude), z-axis radial, y-axis tangential. The bar stands as a radial fin
    centred on the sphere at `radius` so it runs the full height of the sockets.
    Length is folded into the x column so a single unit cube serves every bar,
    whatever its length (polyhedron edges and pentagon spokes differ)."""
    mats = []
    for a, b in pairs:
        d = b - a
        L = float(np.linalg.norm(d))
        e = d / L
        mid = (a + b) / 2.0
        radial = _unit(mid)                 # outward at the bar midpoint
        tang = _unit(np.cross(radial, e))   # tangential, perpendicular to bar
        z = _unit(np.cross(e, tang))        # radial -> the bar's tall (height) axis
        centre = radial * radius            # sit on the sphere, level with sockets
        mats.append(_matrix(e * L, tang, z, centre))   # |x column| = bar length
    return mats


def node_transforms(verts):
    """One transform per vertex: z-axis points radially outward (socket axis)."""
    mats = []
    for v in verts:
        n = _unit(v)
        ref = np.array([0.0, 0.0, 1.0])
        if abs(float(n @ ref)) > 0.9:
            ref = np.array([1.0, 0.0, 0.0])
        u = _unit(np.cross(n, ref))
        w = np.cross(n, u)
        mats.append(_matrix(u, w, n, v))
    return mats
