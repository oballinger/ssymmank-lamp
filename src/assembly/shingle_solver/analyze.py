"""
Verifier for the two assembly constraints:
  1. mushrooms must never intersect  (assemblable)  -> pairwise surface clearance
  2. centre light never directly visible            -> angular coverage of sphere
     by the mushroom caps (gaps between caps = straight line of sight to centre)

Reuses core geometry/transforms. Replicates the placement so per-size scale can
be varied. Mushroom geometry reconstructed from mushrooms/mushroom_simple.scad.
"""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo src/ -> import core
import numpy as np
from core import geometry
from core.transforms import _unit, _matrix

# ---- mushroom_simple.scad params ----
RIM_R, THROAT_R, RIM_Z, WALL = 40.0, 8.0, 14.0, 0.8
STEM_TIP_R = 4.0
PENT_R, ARM_STRETCH, ARM_DROP = 68.0, 1.25, 12.0
DISH_DEPTH = 34.0
THROAT_Z = RIM_Z - DISH_DEPTH
RIB_T, RIB_H, RIB_BITE = 0.8, 4.0, 1.6
DN = 16
CURVE_R = 200.0 / 2 * 3.0                 # 300
CAP_OVERLAP = 3.0
FLANGE_HOLE = RIM_R - WALL - CAP_OVERLAP  # 36.2
CAP_ZC = RIM_Z - math.sqrt(CURVE_R**2 - FLANGE_HOLE**2)
PENT_ANGLES = [90, 162, 234, 306, 18]
PENT_FACTOR = [1, ARM_STRETCH, 1, 1, ARM_STRETCH]

# ---- assembly params ----
SOCKET_H = 10.0
SMALL, MEDIUM, LARGE, XL = 70.0, 84.0, 100.8, 120.96
CORNER_SEQUENCE = [SMALL, MEDIUM, LARGE, MEDIUM, LARGE]


def funnel_z(r):
    t = (r - THROAT_R) / (RIM_R - THROAT_R)
    return THROAT_Z + DISH_DEPTH * (1 - (1 - t) ** 2)


def pentagon_pts(nsub=4):
    """Cap outline, subdivided, as curved 3D points (on the CURVE_R sphere)."""
    corners = []
    for i in range(5):
        r = PENT_R * PENT_FACTOR[i]
        a = math.radians(PENT_ANGLES[i])
        drop = ARM_DROP if PENT_FACTOR[i] > 1 else 0.0
        corners.append((r * math.cos(a), r * math.sin(a) - drop))
    pts = []
    for i in range(5):
        x0, y0 = corners[i]
        x1, y1 = corners[(i + 1) % 5]
        for k in range(nsub):
            f = k / nsub
            pts.append((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f))
    return pts


def cap_point_z(x, y):
    return CAP_ZC + math.sqrt(CURVE_R**2 - (x*x + y*y))


def cap_mesh():
    """Triangulated solid cap (no hole): fan from centre over subdivided outline.
    Returns (verts Nx3, tris Mx3 int)."""
    outline = pentagon_pts(nsub=5)
    verts = [(0.0, 0.0, cap_point_z(0, 0))]
    for (x, y) in outline:
        verts.append((x, y, cap_point_z(x, y)))
    tris = []
    n = len(outline)
    for i in range(n):
        tris.append((0, 1 + i, 1 + (i + 1) % n))
    return np.array(verts), np.array(tris)


def surface_samples(stem_len):
    """Point cloud over the whole mushroom surface (cap + funnel + stem) in local
    coords, for clearance tests."""
    pts = []
    # cap: dense interior fill (the binding feature) -- radial fan of rings
    for ring in range(1, 13):
        s_in = ring / 12.0
        for (x, y) in pentagon_pts(nsub=14):
            pts.append((x*s_in, y*s_in, cap_point_z(x*s_in, y*s_in)))
    # funnel band
    for ri in range(0, 9):
        r = THROAT_R + (RIM_R - THROAT_R) * ri / 8
        z = funnel_z(r)
        for ai in range(24):
            a = 2*math.pi*ai/24
            pts.append((r*math.cos(a), r*math.sin(a), z))
    # stem
    for si in range(0, 7):
        f = si / 6
        z = THROAT_Z + (-stem_len - THROAT_Z) * f
        r = THROAT_R + (STEM_TIP_R - THROAT_R) * f
        for ai in range(12):
            a = 2*math.pi*ai/12
            pts.append((r*math.cos(a), r*math.sin(a), z))
    # back ribs (the fins that protrude into the inter-mushroom gaps) -- the
    # OUTER edge of each fin is the real collision surface. n = DN+2 points.
    rs = [(RIM_R + (THROAT_R - RIM_R) * i / DN) for i in range(DN + 1)]
    npts = DN + 2
    for az in PENT_ANGLES:
        ca, sa = math.cos(math.radians(az)), math.sin(math.radians(az))
        for i, r in enumerate(rs):
            rho = (r - RIB_BITE) + RIB_H * math.sin(math.pi * i / (npts - 1))
            z = funnel_z(r)
            for ty in (-RIB_T/2, RIB_T/2):     # both faces of the thin fin
                pts.append((rho*ca - ty*sa, rho*sa + ty*ca, z))
        # stem-tip end of the fin
        rho = (STEM_TIP_R - RIB_BITE) + RIB_H * math.sin(math.pi*(npts-1)/(npts-1))
        pts.append((rho*ca, rho*sa, -stem_len))
    return np.array(pts)


def place(socket_pt, top_dir, stem_len, r_floor, scale):
    n = _unit(socket_pt)
    yc = _unit(top_dir - (top_dir @ n) * n)
    xc = _unit(np.cross(yc, n))
    T = n * (r_floor + stem_len * scale)
    return _matrix(xc, yc, n, T)


def build_placements(scale_for):
    """scale_for: fn(stem_len)->scale. Returns list of (M 4x4, stem_len, scale)."""
    V, F, E = geometry.build()
    radius = 100.0
    V = V * radius
    r_floor = radius - SOCKET_H / 2.0 + 1.0
    out = []
    for f in F:
        if len(f) != 5:
            continue
        corners = V[f]
        centre = corners.mean(axis=0)
        n_c = _unit(centre)
        start = max(range(5), key=lambda k: corners[k][2])
        d0 = corners[start] - centre
        t0 = _unit(d0 - (d0 @ n_c) * n_c)
        b = np.cross(n_c, t0)
        def cw_key(k):
            d = corners[k] - centre
            d = d - (d @ n_c) * n_c
            ang = math.degrees(math.atan2(d @ b, d @ t0))
            return (-ang) % 360.0
        order = sorted(range(5), key=cw_key)
        sc = scale_for(XL)
        out.append((place(centre, corners[start]-centre, XL, r_floor, sc), XL, sc))
        for seq_i, k in enumerate(order):
            sl = CORNER_SEQUENCE[seq_i]
            sc = scale_for(sl)
            out.append((place(corners[k], corners[k]-centre, sl, r_floor, sc), sl, sc))
    return out


def world_mesh(M, scale, verts, tris):
    R = M[:3, :3]; T = M[:3, 3]
    w = (R @ (scale * verts).T).T + T
    return w, tris


def coverage(placements, ndir=40000):
    """Fraction of directions from origin NOT blocked by any cap (= light leak)."""
    cv, ct = cap_mesh()
    meshes = [world_mesh(M, sc, cv, ct) for (M, sl, sc) in placements]
    # fibonacci sphere directions
    i = np.arange(ndir) + 0.5
    phi = np.arccos(1 - 2*i/ndir)
    gold = math.pi * (1 + 5**0.5)
    theta = gold * i
    D = np.column_stack((np.sin(phi)*np.cos(theta),
                         np.sin(phi)*np.sin(theta),
                         np.cos(phi)))
    covered = np.zeros(ndir, dtype=bool)
    eps = 1e-9
    for (w, tris) in meshes:
        # bounding cone prune: cap centroid dir + max angular radius
        cen = w.mean(axis=0); cdir = cen/np.linalg.norm(cen)
        wn = w/np.linalg.norm(w, axis=1, keepdims=True)
        cosr = (wn @ cdir).min() - 0.02
        cand = (D @ cdir) >= cosr
        if not cand.any():
            continue
        Dc = D[cand]
        hit = np.zeros(len(Dc), dtype=bool)
        for tri in tris:
            v0, v1, v2 = w[tri[0]], w[tri[1]], w[tri[2]]
            e1 = v1 - v0; e2 = v2 - v0
            pvec = np.cross(Dc, e2)
            det = pvec @ e1
            ok = np.abs(det) > eps
            invdet = np.where(ok, 1.0/np.where(ok, det, 1), 0.0)
            tvec = -v0
            u = (pvec @ tvec) * invdet
            qvec = np.cross(tvec, e1)
            v = (Dc @ qvec) * invdet
            t = (e2 @ qvec) * invdet
            hit |= ok & (u >= -1e-6) & (v >= -1e-6) & (u+v <= 1+1e-6) & (t > 0)
        idx = np.where(cand)[0]
        covered[idx[hit]] = True
    leak = (~covered).sum()
    return leak / ndir, covered, D


def clearance(placements):
    """Min surface-to-surface distance over all near pairs. <~0.3 => touching."""
    clouds = []
    cents = []
    for (M, sl, sc) in placements:
        pts = surface_samples(sl)
        R = M[:3, :3]; T = M[:3, 3]
        w = (R @ (sc * pts).T).T + T
        clouds.append(w)
        cents.append(w.mean(axis=0))
    cents = np.array(cents)
    n = len(clouds)
    # angular adjacency: only test pairs whose centroids are within 70 deg
    cdir = cents/np.linalg.norm(cents, axis=1, keepdims=True)
    best = 1e9; worst_pair = None
    for a in range(n):
        for bdy in range(a+1, n):
            if cdir[a] @ cdir[bdy] < math.cos(math.radians(75)):
                continue
            A = clouds[a]; B = clouds[bdy]
            # min pairwise distance (subsample for speed)
            d2 = ((A[:, None, :] - B[None, :, :])**2).sum(-1)
            m = math.sqrt(d2.min())
            if m < best:
                best = m; worst_pair = (a, bdy)
    return best, worst_pair


def report(label, scale_for):
    pl = build_placements(scale_for)
    leak, covered, D = coverage(pl)
    clr, pair = clearance(pl)
    print(f"\n=== {label} ===")
    print(f"  scales: " + ", ".join(f"{int(s)}:{scale_for(s):.3f}" for s in (SMALL,MEDIUM,LARGE,XL)))
    print(f"  light leak (sphere fraction with line-of-sight to centre): {leak*100:.2f}%")
    ptxt = ""
    if pair:
        a, bdy = pair
        ptxt = f"  [closest pair: {int(pl[a][1])}mm & {int(pl[bdy][1])}mm stems]"
    print(f"  min surface clearance between any two mushrooms: {clr:.2f} mm" +
          ("  *** CONTACT/OVERLAP ***" if clr < 0.3 else "  (ok)") + ptxt)
    return leak, clr


if __name__ == "__main__":
    report("current  (uniform 0.52)", lambda sl: 0.52)
