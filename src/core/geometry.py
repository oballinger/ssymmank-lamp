"""
Geometry of the Ssymmank lamp.

The lamp is a spherical tessellation of regular pentagons, squares and
triangles -> the RHOMBICOSIDODECAHEDRON (Archimedean solid):
    12 pentagons, 30 squares, 20 triangles, 60 vertices, 120 edges, 62 faces.
    vertex configuration 3.4.5.4 (triangle, square, pentagon, square).

This module is the single source of truth for the vertices, edges and faces.
"""

import numpy as np
from scipy.spatial import ConvexHull

PHI = (1 + 5 ** 0.5) / 2


def _cyclic(t):
    """The 3 even (cyclic) permutations of a 3-tuple."""
    a, b, c = t
    return [(a, b, c), (b, c, a), (c, a, b)]


def _signed(t):
    """All sign combinations of a 3-tuple."""
    out = []
    for sx in (1, -1):
        for sy in (1, -1):
            for sz in (1, -1):
                out.append((sx * t[0], sy * t[1], sz * t[2]))
    return out


def vertices():
    """60 vertices of the rhombicosidodecahedron (edge length 2)."""
    base = [
        (1, 1, PHI ** 3),
        (PHI ** 2, PHI, 2 * PHI),
        (2 + PHI, 0, PHI ** 2),
    ]
    verts = set()
    for b in base:
        for c in _cyclic(b):
            for s in _signed(c):
                verts.add(tuple(round(x, 9) for x in s))
    return np.array(sorted(verts))


def faces(V):
    """Merge ConvexHull triangles into the 62 polygon faces (CCW ordered)."""
    hull = ConvexHull(V)
    planes = {}
    for eq, simplex in zip(hull.equations, hull.simplices):
        key = tuple(np.round(eq, 5))
        planes.setdefault(key, set()).update(simplex.tolist())

    out = []
    for key, idx_set in planes.items():
        idx = list(idx_set)
        pts = V[idx]
        centroid = pts.mean(axis=0)
        normal = np.array(key[:3])
        u = pts[0] - centroid
        u = u / np.linalg.norm(u)
        w = np.cross(normal, u)
        ang = np.arctan2((pts - centroid) @ w, (pts - centroid) @ u)
        order = np.argsort(ang)
        out.append([idx[k] for k in order])
    return out


def edges(face_list):
    """Unique undirected edges (vertex-index pairs) from the face list."""
    e = set()
    for f in face_list:
        n = len(f)
        for k in range(n):
            e.add(tuple(sorted((f[k], f[(k + 1) % n]))))
    return sorted(e)


def pentagon_stars(V, face_list, bulge=1.0):
    """For each pentagon face return (center_point, [5 corner indices]).

    The center is the centroid of the pentagon's 5 vertices, pushed radially
    outward toward the circumsphere to make the structure more spherical:
        bulge=0  -> flat centroid (recessed)
        bulge=1  -> projected onto the circumsphere (level with the corners)
    Values >1 dome the star outward past the corners."""
    R = float(np.linalg.norm(V, axis=1).mean())   # circumradius
    out = []
    for f in face_list:
        if len(f) == 5:
            c = V[f].mean(axis=0)
            cn = np.linalg.norm(c)
            target = cn + bulge * (R - cn)
            out.append((c / cn * target, list(f)))
    return out


def build(normalize=True):
    """Return (V, faces, edges). If normalize, scale to a unit circumsphere."""
    V = vertices()
    if normalize:
        V = V / np.linalg.norm(V, axis=1).mean()
    F = faces(V)
    E = edges(F)
    return V, F, E


if __name__ == "__main__":
    V, F, E = build()
    counts = {}
    for f in F:
        counts[len(f)] = counts.get(len(f), 0) + 1
    print(f"vertices: {len(V)}")
    print(f"edges:    {len(E)}")
    print(f"faces:    {len(F)}  -> "
          f"pentagons {counts.get(5,0)}, squares {counts.get(4,0)}, triangles {counts.get(3,0)}")
