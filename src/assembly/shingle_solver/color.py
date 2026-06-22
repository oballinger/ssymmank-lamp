import math
import numpy as np
from scipy.spatial import cKDTree
import analyze, opt
from core import geometry
from core.transforms import _unit, _matrix

STEMS = [analyze.SMALL, analyze.MEDIUM, analyze.LARGE, analyze.XL]  # 4 shells


def sockets():
    """Return list of (kind, dir_unit, socket_pt, top_dir) for all 72 sockets,
    plus the pentagon-grouping needed to orient +Y. kind: 'C'entre/'corner'."""
    V, F, E = geometry.build()
    radius = 100.0
    V = V * radius
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
            return (-math.degrees(math.atan2(d @ b, d @ t0))) % 360.0
        order = sorted(range(5), key=cw_key)
        out.append(('C', centre, corners[start] - centre))
        for k in order:
            out.append(('v', corners[k], corners[k] - centre))
    return out  # 72 entries


def placements(stem_of, scale):
    """stem_of: list len72 of stem length. scale uniform. -> list (M,stem,scale)."""
    socks = sockets()
    r_floor = 100.0 - analyze.SOCKET_H / 2.0 + 1.0
    out = []
    for (kind, pt, top), sl in zip(socks, stem_of):
        out.append((analyze.place(pt, top, sl, r_floor, scale), sl, scale))
    return out


def adjacency(scale):
    """Edge between two sockets if their caps OVERLAP when placed at a COMMON
    radius (worst case = same shell). This is the graph that must be coloured."""
    socks = sockets()
    n = len(socks)
    # place every cap at the SAME stem (common radius) and scale
    common = analyze.MEDIUM
    r_floor = 100.0 - analyze.SOCKET_H / 2.0 + 1.0
    NCAP = 12 * 5 * 14                   # dense cap-fill points in _CLOUD ordering
    capw = []
    cdirs = []
    for (kind, pt, top) in socks:
        M = analyze.place(pt, top, common, r_floor, scale)
        R = M[:3, :3]; T = M[:3, 3]
        cap = opt._CLOUD[common][:NCAP]
        capw.append((R @ (scale * cap).T).T + T)
        cdirs.append(_unit(T))
    cdirs = np.array(cdirs)
    trees = [cKDTree(c) for c in capw]
    adj = [[] for _ in range(n)]
    for a in range(n):
        for b in range(a + 1, n):
            if cdirs[a] @ cdirs[b] < math.cos(math.radians(60)):
                continue
            d, _ = trees[b].query(capw[a], k=1)
            if d.min() < 1.0:            # overlap/touch at common radius => must differ
                adj[a].append(b); adj[b].append(a)
    return adj, n


def dsatur(adj, n, K):
    color = [-1] * n
    sat = [set() for _ in range(n)]
    deg = [len(adj[i]) for i in range(n)]
    for _ in range(n):
        u = max((i for i in range(n) if color[i] == -1),
                key=lambda i: (len(sat[i]), deg[i]))
        for c in range(K):
            if c not in sat[u]:
                color[u] = c; break
        if color[u] == -1:
            color[u] = K  # overflow marker (needs > K)
        for v in adj[u]:
            sat[v].add(color[u])
    conflicts = sum(1 for a in range(n) for b in adj[a] if a < b and color[a] == color[b])
    return color, conflicts


def measure(stem_of, scale):
    pl = placements(stem_of, scale)
    # coverage
    capw = []
    clouds = []
    for (M, sl, sc) in pl:
        R = M[:3, :3]; T = M[:3, 3]
        capw.append((R @ (sc * opt._CV).T).T + T)
        clouds.append((R @ (sc * opt._CLOUD[sl]).T).T + T)
    covered = np.zeros(opt._NDIR, dtype=bool); eps = 1e-9; D = opt._D
    for w in capw:
        cen = w.mean(0); cdr = cen / np.linalg.norm(cen)
        wn = w / np.linalg.norm(w, axis=1, keepdims=True)
        cand = (D @ cdr) >= (wn @ cdr).min() - 0.02
        if not cand.any(): continue
        Dc = D[cand]; hit = np.zeros(len(Dc), dtype=bool)
        for tri in opt._CT:
            v0, v1, v2 = w[tri[0]], w[tri[1]], w[tri[2]]; e1 = v1 - v0; e2 = v2 - v0
            pv = np.cross(Dc, e2); det = pv @ e1; ok = np.abs(det) > eps
            inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
            tv = -v0; u = (pv @ tv) * inv; qv = np.cross(tv, e1)
            v = (Dc @ qv) * inv; t = (e2 @ qv) * inv
            hit |= ok & (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6) & (t > 0)
        idx = np.where(cand)[0]; covered[idx[hit]] = True
    leak = (~covered).sum() / opt._NDIR
    # clearance
    cc = np.array([c.mean(0) for c in clouds]); cd = cc / np.linalg.norm(cc, axis=1, keepdims=True)
    trees = [cKDTree(c) for c in clouds]; best = 1e9; bp = None
    n = len(clouds)
    for a in range(n):
        for b in range(a + 1, n):
            if cd[a] @ cd[b] < math.cos(math.radians(75)): continue
            d, _ = trees[b].query(clouds[a], k=1); m = d.min()
            if m < best: best = m; bp = (int(pl[a][1]), int(pl[b][1]))
    return leak, best, bp


def backtrack_color(adj, n, K, node_limit=2_000_000):
    """Exact K-colouring via backtracking with DSATUR-style ordering. Returns
    colour list or None (None also if node_limit hit -> treat as infeasible)."""
    order = sorted(range(n), key=lambda i: -len(adj[i]))
    color = [-1] * n
    cnt = [0]

    def solve(idx):
        if idx == n:
            return True
        cnt[0] += 1
        if cnt[0] > node_limit:
            return False
        u = order[idx]
        used = {color[v] for v in adj[u] if color[v] != -1}
        for c in range(K):
            if c in used:
                continue
            color[u] = c
            if solve(idx + 1):
                return True
            color[u] = -1
        return False
    return color if solve(0) else None


if __name__ == "__main__":
    from collections import Counter
    for SCALE in [0.72, 0.74, 0.75, 0.76, 0.78, 0.80]:
        adj, n = adjacency(SCALE)
        degs = [len(a) for a in adj]
        col = backtrack_color(adj, n, 4)
        ok = col is not None
        tag = "4-colourable" if ok else "NOT 4-colourable"
        line = f"scale {SCALE}: maxdeg {max(degs)}, edges {sum(degs)//2}, {tag}"
        if ok:
            # assign stems to colours; try to give most-overlapping edges the
            # widest radial gap by ordering colours by frequency -> stems
            stem_of = [STEMS[c] for c in col]
            leak, clr, bp = measure(stem_of, SCALE)
            line += f"  -> leak={leak*100:.2f}%  clearance={clr:.2f}mm  binding={bp}  sizes={dict(Counter(col))}"
        print(line)
