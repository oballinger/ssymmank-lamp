"""Per-mushroom azimuthal orientation optimiser, stretched arms MANDATORY.
Caps keep ARM_STRETCH=1.25; each mushroom may spin about its radial axis so its
arms reach into coverage gaps (square/triangle centres -> empty, no neighbour
stem) rather than skewering neighbours. Intersection measured EXACTLY by OpenSCAD;
leak by rays. Greedy coordinate descent over a discrete angle set."""
import os, math, subprocess
import numpy as np
from scipy.spatial import cKDTree
import analyze, color, color3
from core.transforms import _unit, _matrix

SCALE, BASE, DELTA, DISH, RELAX, ARM = 0.85, 70.0, 14.0, 6.0, 2.3, 1.25
ANGLES = [i*30.0 for i in range(12)]

col, K = color3.proper_coloring(SCALE)
STEMS = [BASE + i*DELTA for i in range(K)]
RPLACE = [color3.R_FLOOR + SCALE*(s+color3.RIM_Z) for s in STEMS]
STLS = [color3.variant_stl(RELAX, DISH, STEMS[i], ARM) for i in range(K)]
SOCKS = color.sockets()


def place_az(pt, top, stem, theta_deg):
    n = _unit(np.asarray(pt, float))
    yc0 = _unit(top - (top @ n) * n); xc0 = _unit(np.cross(yc0, n))
    th = math.radians(theta_deg)
    xc = math.cos(th)*xc0 + math.sin(th)*yc0
    yc = -math.sin(th)*xc0 + math.cos(th)*yc0
    T = n * (color3.R_FLOOR + stem*SCALE)
    return _matrix(xc, yc, n, T)


def matstr(M):
    return "[" + ",".join("["+",".join("%.6f" % x for x in row)+"]" for row in M) + "]"

def piece(M, shell):
    return f'multmatrix({matstr(M)}) scale({SCALE}) import(S{shell})'


# clouds for adjacency (orientation-independent enough at prune=8)
def close_pairs():
    clouds = []
    for (kind, pt, top), c in zip(SOCKS, col):
        M = place_az(pt, top, STEMS[c], 0.0); R = M[:3, :3]; T = M[:3, 3]
        clouds.append((R@(SCALE*analyze.surface_samples(STEMS[c])).T).T + T)
    cents = np.array([c.mean(0) for c in clouds]); cd = cents/np.linalg.norm(cents, axis=1, keepdims=True)
    trees = [cKDTree(c) for c in clouds]; n = len(clouds); nb = [[] for _ in range(n)]
    for a in range(n):
        for b in range(a+1, n):
            if cd[a]@cd[b] < math.cos(math.radians(75)): continue
            if trees[b].query(clouds[a], k=1)[0].min() < 10: nb[a].append(b); nb[b].append(a)
    return nb

NB = close_pairs()
HDR = "\n".join(f'S{i}="{STLS[i]}";' for i in range(K))


def facets_pairs(pairs, theta):
    """render intersection of given (i,j) pairs at current theta; return facets."""
    if not pairs: return 0
    Ms = {}
    body = []
    for (a, b) in pairs:
        Ma = place_az(*SOCKS[a][1:], STEMS[col[a]], theta[a])
        Mb = place_az(*SOCKS[b][1:], STEMS[col[b]], theta[b])
        body.append(f'intersection(){{{piece(Ma, col[a])};{piece(Mb, col[b])};}}')
    open(os.path.join(color3.SCRATCH,"_o.scad"), "w").write(HDR+"\n"+"\n".join(body)+"\n")
    if os.path.exists(os.path.join(color3.SCRATCH,"_o.stl")): os.remove(os.path.join(color3.SCRATCH,"_o.stl"))
    subprocess.run([color3.OSC, "-o", os.path.join(color3.SCRATCH,"_o.stl"), os.path.join(color3.SCRATCH,"_o.scad")], capture_output=True)
    return open(os.path.join(color3.SCRATCH,"_o.stl"), "rb").read().count(b"facet normal") if os.path.exists(os.path.join(color3.SCRATCH,"_o.stl")) else 0


def total_facets(theta):
    allpairs = list({tuple(sorted((a, b))) for a in range(len(SOCKS)) for b in NB[a]})
    return facets_pairs(allpairs, theta), len(allpairs)


def optimize(passes=3):
    n = len(SOCKS); theta = [0.0]*n
    f0, npair = total_facets(theta)
    print(f"start: {f0} facets over {npair} pairs")
    for p in range(passes):
        improved = 0
        # only touch mushrooms currently involved in an intersecting pair
        for i in range(n):
            mypairs = [(i, j) for j in NB[i]]
            cur = facets_pairs(mypairs, theta)
            if cur == 0:
                continue
            best_t, best_f = theta[i], cur
            for t in ANGLES:
                if t == theta[i]: continue
                theta[i] = t; fv = facets_pairs(mypairs, theta)
                if fv < best_f: best_f, best_t = fv, t
            theta[i] = best_t
            if best_f < cur: improved += 1
        tf, _ = total_facets(theta)
        print(f"pass {p+1}: total facets {tf}, improved {improved} mushrooms")
        if tf == 0: break
    for f in ("_o.scad", "_o.stl"):
        p = os.path.join(color3.SCRATCH, f)
        if os.path.exists(p): os.remove(p)
    return theta


def leak_for(theta, ndir=60000):
    capmeshes = []
    for idx, ((kind, pt, top), c) in enumerate(zip(SOCKS, col)):
        M = place_az(pt, top, STEMS[c], theta[idx]); R = M[:3, :3]; T = M[:3, 3]
        cv, ct = color3.cap_mesh_cr(RELAX*100.0, ARM)
        capmeshes.append(((R@(SCALE*cv).T).T+T, ct))
    return color3.coverage(capmeshes, ndir=ndir)*100


if __name__ == "__main__":
    import json
    theta = optimize(5)
    lk = leak_for(theta)
    json.dump(theta, open("theta.json", "w"))
    print(f"FINAL leak with optimised orientation: {lk:.3f}%")
    print("theta sample:", [round(t) for t in theta][:12], "...")
