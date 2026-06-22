"""Real solver: shingled shells with concentric (radially-thin) caps.
Intersections measured EXACTLY by OpenSCAD on the real mushroom solids.

Per shell i: stem s_i = base + i*delta ; the cap curvature is set so the cap is
concentric with the lamp centre (radially thin) -> CURVE_RELAX_i = R_place/(scale*100).
Sockets are properly k-coloured at the coverage scale (same-shell caps never
overlap). Cross-shell caps are thin concentric patches -> clear with small gap.
Funnel depth (dish) is a knob for cross-shell funnel clearance.
"""
import os, math, subprocess, hashlib, tempfile
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import analyze, color, opt
from core.transforms import _fmt_matrix

OSC = os.environ.get("OPENSCAD", "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
SRC_MUSH = str(Path(__file__).resolve().parents[3] / "models" / "mushrooms" / "mushroom_simple.scad")
SCRATCH = os.path.join(tempfile.gettempdir(), "shingle_solver"); os.makedirs(SCRATCH, exist_ok=True)
R_FLOOR = 100.0 - analyze.SOCKET_H/2.0 + 1.0
RIM_Z = analyze.RIM_Z
_SRC = open(SRC_MUSH).read()

import re
def variant_stl(curve_relax, dish, stem, arm=1.25):
    """Render one mushroom variant (given curvature, funnel depth, stem, arm
    stretch) to STL at origin, true (unscaled) size. Cached by params."""
    key = hashlib.md5(f"{curve_relax:.4f}_{dish:.3f}_{stem:.3f}_{arm:.3f}".encode()).hexdigest()[:10]
    stl = os.path.join(SCRATCH, f"_v_{key}.stl")
    if os.path.exists(stl):
        return stl
    t = _SRC
    t = re.sub(r"CURVE_RELAX\s*=\s*[0-9.]+;", f"CURVE_RELAX  = {curve_relax:.5f};", t)
    t = re.sub(r"DISH_DEPTH\s*=\s*[0-9.]+;", f"DISH_DEPTH = {dish:.3f};", t)
    t = re.sub(r"STEM_LEN\s*=\s*[0-9.]+;", f"STEM_LEN   = {stem:.3f};", t)
    t = re.sub(r"ARM_STRETCH\s*=\s*[0-9.]+;", f"ARM_STRETCH = {arm:.4f};", t)
    sp = os.path.join(SCRATCH, f"_v_{key}.scad"); open(sp, "w").write(t)
    subprocess.run([OSC, "-o", stl, sp], capture_output=True)
    return stl


def pentagon_pts_arm(arm, nsub=5):
    """Cap outline (2D) with arbitrary arm stretch (arm=1.0 -> regular)."""
    fac = [1, arm, 1, 1, arm]; drop = analyze.ARM_DROP
    corners = []
    for i in range(5):
        r = analyze.PENT_R*fac[i]; a = math.radians(analyze.PENT_ANGLES[i])
        d = drop if fac[i] > 1 else 0.0
        corners.append((r*math.cos(a), r*math.sin(a)-d))
    pts = []
    for i in range(5):
        x0, y0 = corners[i]; x1, y1 = corners[(i+1) % 5]
        for kk in range(nsub):
            f = kk/nsub; pts.append((x0+(x1-x0)*f, y0+(y1-y0)*f))
    return pts


def cap_mesh_cr(curve_r, arm=1.25):
    """cap triangulation for leak rays, with given curvature radius + arm stretch."""
    FH = analyze.FLANGE_HOLE
    CAP_ZC = RIM_Z - math.sqrt(curve_r**2 - FH**2)
    def z(x, y): return CAP_ZC + math.sqrt(curve_r**2 - (x*x+y*y))
    outline = pentagon_pts_arm(arm, nsub=5)
    verts = [(0.0, 0.0, z(0, 0))] + [(x, y, z(x, y)) for (x, y) in outline]
    n = len(outline)
    tris = [(0, 1+i, 1+(i+1) % n) for i in range(n)]
    return np.array(verts), np.array(tris)


def coverage(capmeshes, ndir=24000):
    i = np.arange(ndir)+0.5; phi = np.arccos(1-2*i/ndir); g = math.pi*(1+5**0.5); th = g*i
    D = np.column_stack((np.sin(phi)*np.cos(th), np.sin(phi)*np.sin(th), np.cos(phi)))
    covered = np.zeros(ndir, bool); eps = 1e-9
    for (w, tris) in capmeshes:
        cen = w.mean(0); cdr = cen/np.linalg.norm(cen)
        wn = w/np.linalg.norm(w, axis=1, keepdims=True)
        cand = (D@cdr) >= (wn@cdr).min()-0.02
        if not cand.any(): continue
        Dc = D[cand]; hit = np.zeros(len(Dc), bool)
        for tri in tris:
            v0, v1, v2 = w[tri[0]], w[tri[1]], w[tri[2]]; e1 = v1-v0; e2 = v2-v0
            pv = np.cross(Dc, e2); det = pv@e1; ok = np.abs(det) > eps
            inv = np.where(ok, 1/np.where(ok, det, 1), 0); tv = -v0
            u = (pv@tv)*inv; qv = np.cross(tv, e1); v = (Dc@qv)*inv; t = (e2@qv)*inv
            hit |= ok & (u >= -1e-6) & (v >= -1e-6) & (u+v <= 1+1e-6) & (t > 0)
        idx = np.where(cand)[0]; covered[idx[hit]] = True
    return (~covered).sum()/ndir


# proper colouring at coverage scale (computed once per scale)
_color_cache = {}
def proper_coloring(scale):
    # colour at max(scale, 0.85): denser graph => colouring stays proper at the
    # coverage scale. min 5 colours (4 was an under-connected artifact at 0.95).
    sc = max(scale, 0.85)
    if sc in _color_cache: return _color_cache[sc]
    adj, n = color.adjacency(sc)
    for k in [5, 6, 7]:
        col = color.backtrack_color(adj, n, k, node_limit=800000)
        if col is not None:
            _color_cache[sc] = (col, k); return col, k
    raise RuntimeError("no colouring")


def evaluate(scale, base, delta, dish, arm=1.25, concentric=True, fixed_relax=None,
             prune=8.0, verbose=False, ndir=24000):
    col, k = proper_coloring(scale)
    stems = [base + i*delta for i in range(k)]
    Rplace = [R_FLOOR + scale*(s + RIM_Z) for s in stems]
    if fixed_relax is not None:
        relax = [fixed_relax]*k
    else:
        relax = [(Rplace[i]/(scale*100.0)) if concentric else 3.0 for i in range(k)]
    curve_r = [relax[i]*100.0 for i in range(k)]
    stls = [variant_stl(relax[i], dish, stems[i], arm) for i in range(k)]
    socks = color.sockets()
    # placements + clouds + caps
    Ms = []; clouds = []; capmeshes = []; shell = []
    for (kind, pt, top), c in zip(socks, col):
        M = analyze.place(pt, top, stems[c], R_FLOOR, scale); Ms.append(M); shell.append(c)
        R = M[:3, :3]; T = M[:3, 3]
        clouds.append((R@(scale*analyze.surface_samples(stems[c])).T).T + T)
        cv, ct = cap_mesh_cr(curve_r[c], arm); capmeshes.append(((R@(scale*cv).T).T+T, ct))
    leak = coverage(capmeshes, ndir=ndir)
    # close pairs
    cents = np.array([c.mean(0) for c in clouds]); cd = cents/np.linalg.norm(cents, axis=1, keepdims=True)
    trees = [cKDTree(c) for c in clouds]; n = len(clouds); pairs = []
    for a in range(n):
        for b in range(a+1, n):
            if cd[a]@cd[b] < math.cos(math.radians(75)): continue
            if trees[b].query(clouds[a], k=1)[0].min() < prune: pairs.append((a, b))
    # oracle: import per-shell STL, place, intersect
    lines = [f'S{i}="{stls[i]}";' for i in range(k)]
    def place_str(idx):
        m = "[" + ",".join("["+",".join("%.6f" % x for x in row)+"]" for row in Ms[idx]) + "]"
        return f'multmatrix({m}) scale({scale}) import(S{shell[idx]})'
    body = "\n".join(f"intersection(){{{place_str(a)};{place_str(b)};}}" for a, b in pairs)
    oscad = "\n".join(lines) + "\n" + body + "\n"
    op = os.path.join(SCRATCH, "_oracle.scad"); ostl = os.path.join(SCRATCH, "_oracle.stl")
    open(op, "w").write(oscad)
    if os.path.exists(ostl): os.remove(ostl)
    subprocess.run([OSC, "-o", ostl, op], capture_output=True)
    facets = open(ostl, "rb").read().count(b"facet normal") if os.path.exists(ostl) else -1
    if verbose:
        print(f"  k={k} stems={[round(s) for s in stems]} relax={[round(r,2) for r in relax]} "
              f"Rplace={[round(r) for r in Rplace]}")
    return facets, leak*100, k, len(pairs)


if __name__ == "__main__":
    print("concentric caps + proper k-colour shells | OpenSCAD-exact intersection")
    print("scale base delta dish |  facets  leak%  (k, pairs)")
    for scale in [0.80, 0.85]:
        for delta in [10, 16, 24]:
            for dish in [34, 22]:
                f, leak, k, npairs = evaluate(scale, 70, delta, dish)
                flag = "  <== CLEAN" if (f == 0 and leak < 0.05) else ""
                print(f" {scale:.2f}  70   {delta:2d}   {dish:2d}  | {f:6d}  {leak:5.2f}  (k={k},{npairs}p){flag}")
