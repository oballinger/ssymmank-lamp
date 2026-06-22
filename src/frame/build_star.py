"""
Emit the printable STAR TILE, the CONNECTOR bar, and fit-check views.

    models/frame/star.scad             one pentagon star (12 congruent), print-oriented
    models/frame/connector.scad        one connector bar (60 identical), print-oriented
    models/frame/stars_assembly.scad   all 12 stars + 60 connectors (full-frame fit check)
    models/frame/mate_test.scad        2 neighbouring tiles + their shared connector
    models/frame/test_edges.scad       2 connectors for a quick fit test print
    models/frame/stem_fit.scad         a real stem cone cross-cut in the bores

Decomposition of the frame for 3D printing
------------------------------------------
In the rhombicosidodecahedron every vertex belongs to exactly ONE pentagon, and
the 120 edges split cleanly:
  * 60 pentagon-boundary edges  -> internal to a pentagon
  * 60 inter-pentagon edges     -> the ONLY links between pentagons

So the frame is two part types:
  * STAR TILE  x12 (all congruent): hub socket + 5 spokes + 5 corner sockets
                                    + 5 boundary bars + 10 connector mortises
  * CONNECTOR  x60 (all identical): a flat bar with a keyed tenon at each end,
                                    plugging into two neighbouring tiles' mortises

Joinery: KEYED PEG + SOCKET.  The node wall is thin, so the mortise can't cut
into the node -- instead each corner grows a small rectangular BOSS into the gap,
and the rectangular tenon (which can't spin) plugs into it.  Press-fit, with a
dab of CA for permanence.

This module bakes one canonical star (hub at origin, outward normal = +Z) so a
single printed tile serves all 12 positions, plus world placements for the
fit-check renders.

Run:  uv run python src/frame/build_star.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # src/ -> import core

import numpy as np
from core import geometry
from core.transforms import _unit, _matrix, _fmt_matrix, bar_transforms, node_transforms

MODELS = Path(__file__).resolve().parents[2] / "models" / "frame"

# ---- joint geometry (mm) --------------------------------------------------
# THICKNESS is 1 mm everywhere (fins, socket walls, tenons, boss walls).
THICK = 1.0           # the single 1 mm wall/fin thickness
BORE_R_MOUTH = 5.35   # = STEM_TIP_R(4) + FIT_CLR(0.35) + 1.0  (matches the stem)
NODE_R = BORE_R_MOUTH + THICK   # corner-node outer radius (1 mm wall round the bore)
KEY_T = THICK         # tenon thickness  (tangential) -- matches the 1 mm fin
KEY_H = 6.0           # tenon height     (radial)     -- < EDGE_H, leaves shoulders
KEY_DEPTH = 6.0       # tenon insertion depth (along the edge)
BACK = 1.0            # mortise back wall thickness
NECK = 1.5            # boss overlap back into the node (for a solid weld)


def _orthon(x, y_hint, t):
    """Orthonormal 4x4 from an x-axis, an in-plane hint, and a translation."""
    x = _unit(x)
    z = _unit(y_hint - (y_hint @ x) * x)        # radial-ish, made perpendicular
    y = np.cross(z, x)
    return _matrix(x, y, z, t)


def kink_point(a, b):
    """The point M where the sphere's tangent lines at a and b meet (both on the
    same circumsphere). Each half-edge a->M / M->b then leaves its vertex exactly
    perpendicular to the radial (socket) axis -- (M-a).a == 0 -- and M sits a few
    mm proud of the chord, so the edge kinks outward at its middle."""
    s = a + b
    return s * (2.0 * float(a @ a) / float(s @ s))


def fin_frame(p, q):
    """Radial fin spanning the straight segment p->q: +X along the segment (length
    baked into the x column), +Z radial-outward at the segment midpoint, centred on
    the real midpoint so the fin's ends land exactly on p and q."""
    d = q - p
    L = float(np.linalg.norm(d))
    e = d / L
    mid = (p + q) / 2.0
    radial = _unit(mid)
    tang = _unit(np.cross(radial, e))
    z = _unit(np.cross(e, tang))            # radial-ish, perpendicular to the bar
    return _matrix(e * L, tang, z, mid)


def edge_frame(a, b):
    """Connector frame at the edge midpoint: +X along the edge, +Z radial."""
    mid = (a + b) / 2.0
    return _orthon(b - a, mid, mid)


def receiver_frame(v, w):
    """Mortise-boss frame at vertex v, +X pointing toward neighbour w, +Z radial
    -- the SAME orientation as that edge's connector frame, so the tenon mates."""
    mid = (v + w) / 2.0
    return _orthon(w - v, mid, v)


def star_frame(hub, corners):
    """World<->local 4x4 for a pentagon: hub at origin, +Z outward, +X to the
    top (highest-z) corner. Returns (W2L, L2W)."""
    z = _unit(hub)
    top = max(range(5), key=lambda k: corners[k][2])
    d = corners[top] - hub
    x = _unit(d - (d @ z) * z)
    y = np.cross(z, x)
    L2W = _matrix(x, y, z, hub)
    W2L = np.eye(4)
    W2L[:3, :3] = np.array([x, y, z])
    W2L[:3, 3] = -W2L[:3, :3] @ hub
    return W2L, L2W


def canonical_star(V, F, E, owner, hub, corners, idxs):
    """Local-space transforms for one star: nodes, bars, and connector mortises."""
    W2L, _ = star_frame(hub, corners)

    nodes = [hub] + [corners[k] for k in range(5)]
    spokes = [(hub, corners[k]) for k in range(5)]
    boundary = [(corners[k], corners[(k + 1) % 5]) for k in range(5)]

    node_w = node_transforms(nodes)
    # every fused edge kinks at its middle: two fins, a->M and M->b, each leaving
    # its vertex perpendicular to the socket axis.
    bar_w = []
    for a, b in spokes + boundary:
        m = kink_point(a, b)
        bar_w.append(fin_frame(a, m))
        bar_w.append(fin_frame(m, b))

    # the 2 inter-pentagon edges at each of the 5 corners -> 10 mortises
    p = owner[idxs[0]]
    recv_w = []
    for (a, b) in E:
        if owner[a] != owner[b]:
            if owner[a] == p:
                recv_w.append(receiver_frame(V[a], V[b]))
            elif owner[b] == p:
                recv_w.append(receiver_frame(V[b], V[a]))

    node_l = [W2L @ m for m in node_w]
    bar_l = [W2L @ m for m in bar_w]
    recv_l = [W2L @ m for m in recv_w]
    return node_l, bar_l, recv_l


def _modules(edge_len):
    """Shared SCAD: parameters + edge_bar/node/receiver/connector modules."""
    return f"""DIAMETER = 200.0;
EDGE_LEN = {edge_len:.4f};          // every edge/connector is this long (Archimedean)

EDGE_H = 10; EDGE_T = {THICK};          // bar height (radial) x thickness (1 mm)
STEM_TIP_R = 4; FIT_CLR = 0.35; SOCKET_WALL = {THICK};
SOCKET_H = EDGE_H; SOCKET_DEPTH = SOCKET_H - 1;
$fn = 32;
BORE_R_TIP = STEM_TIP_R + FIT_CLR;
BORE_R_MOUTH = STEM_TIP_R + FIT_CLR + 1.0;
NODE_R = {NODE_R};

// ---- keyed joint -----------------------------------------------------------
KEY_T = {KEY_T}; KEY_H = {KEY_H}; KEY_DEPTH = {KEY_DEPTH};
BACK = {BACK}; NECK = {NECK}; KEY_CLR = 0.30;

// ---- edge kink -------------------------------------------------------------
// Every edge bends at its middle so each half leaves its vertex perpendicular to
// the socket axis (tangent to the sphere). The kink point M is where the sphere's
// tangent lines at the two vertices meet, a few mm proud of the chord.
RAD     = DIAMETER / 2;
HALF    = EDGE_LEN / 2;                       // half a chord
MIDR    = sqrt(RAD * RAD - HALF * HALF);      // radius of the chord midpoint
KINK_H  = HALF * HALF / MIDR;                 // outward rise of M above that mid
ARM_LEN = sqrt(HALF * HALF + KINK_H * KINK_H);// vertex -> M, straight
PHI     = atan2(KINK_H, HALF);                // tangent angle above the chord (deg)
GAP_OFF = NODE_R + BACK;                      // vertex -> mortise mouth, along the arm

module edge_bar() cube([1, EDGE_T, EDGE_H], center = true);   // x scaled by matrix

// A node is built in two halves so the bore can be subtracted from the WHOLE
// tile last (after the bars union on) -- otherwise the bars, which run the full
// edge length, drive through the node centre and refill the socket bore.
module node_solid() {{
    translate([0, 0, -SOCKET_H / 2]) cylinder(h = SOCKET_H, r = NODE_R);
}}
module bore() {{
    // conical bore matched to the tapered stem ...
    translate([0, 0, -SOCKET_H / 2 + SOCKET_H - SOCKET_DEPTH + 0.5])
        cylinder(h = SOCKET_DEPTH + 0.5, r1 = BORE_R_TIP, r2 = BORE_R_MOUTH);
    // ... then a straight clearance column continuing OUT past the fin height,
    // so no leaning bar (its tall axis is radial at the edge mid, not at the
    // vertex) can overhang the socket opening. Radius = mouth, so the 1 mm node
    // wall survives.
    translate([0, 0, SOCKET_H / 2 - 1.5])
        cylinder(h = EDGE_H + 2, r = BORE_R_MOUTH);
}}

// mortise boss at a corner: tilted UP by PHI so it aims along the kinked edge's
// tangent (perpendicular to the socket), grows into the gap so it never breaches
// the bore. Tenon plugs in from the gap face.
module receiver() {{
    bw = KEY_T + 2 * SOCKET_WALL; bh = KEY_H + 2 * SOCKET_WALL;
    x0 = NODE_R - NECK;  xlen = NECK + BACK + KEY_DEPTH;
    rotate([0, -PHI, 0])
    difference() {{
        translate([x0, -bw / 2, -bh / 2]) cube([xlen, bw, bh]);
        translate([NODE_R + BACK, -(KEY_T + KEY_CLR) / 2, -(KEY_H + KEY_CLR) / 2])
            cube([KEY_DEPTH + 0.2, KEY_T + KEY_CLR, KEY_H + KEY_CLR]);
    }}
}}

// one connector: a shallow V (kink at the centre, apex M raised by KINK_H), with a
// keyed tenon near each vertex that plugs into that corner's tilted boss. Planar
// (lies in the XZ plane), so it prints flat. All 60 are identical.
module conn_half() {{
    fin0 = GAP_OFF + KEY_DEPTH;                 // where the visible fin starts
    translate([-HALF, 0, 0]) rotate([0, -PHI, 0]) {{
        translate([GAP_OFF, -KEY_T / 2, -KEY_H / 2])
            cube([KEY_DEPTH, KEY_T, KEY_H]);     // tenon (into the tilted boss)
        translate([fin0, -EDGE_T / 2, -EDGE_H / 2])
            cube([ARM_LEN - fin0, EDGE_T, EDGE_H]);   // arm up to the kink at M
    }}
}}
module connector() {{ conn_half(); mirror([1, 0, 0]) conn_half(); }}"""


def main(diameter=200.0):
    V, F, E = geometry.build()
    radius = diameter / 2.0
    V = V * radius

    pents_idx = [f for f in F if len(f) == 5]
    owner = {}
    for pi, f in enumerate(pents_idx):
        for v in f:
            owner[v] = pi
    edge_len = float(np.linalg.norm(V[E[0][0]] - V[E[0][1]]))

    stars = geometry.pentagon_stars(V, F, bulge=1.0)
    pents = [(c, np.array([V[i] for i in corners]), corners)
             for c, corners in stars]

    # ---- canonical (print) star, from pentagon 0 --------------------------
    hub0, corners0, idxs0 = pents[0]
    node_l, bar_l, recv_l = canonical_star(V, F, E, owner, hub0, corners0, idxs0)

    # ---- 12 placements (local -> world) -----------------------------------
    placements = [star_frame(c, cs)[1] for c, cs, _ in pents]

    # ---- 60 connectors, world space ---------------------------------------
    inter = [(a, b) for (a, b) in E if owner[a] != owner[b]]
    conn_w = [edge_frame(V[a], V[b]) for a, b in inter]

    node_block = ",\n        ".join(_fmt_matrix(m) for m in node_l)
    bar_block = ",\n        ".join(_fmt_matrix(m) for m in bar_l)
    recv_block = ",\n        ".join(_fmt_matrix(m) for m in recv_l)
    place_block = ",\n    ".join(_fmt_matrix(m) for m in placements)
    conn_block = ",\n    ".join(_fmt_matrix(m) for m in conn_w)

    common = _modules(edge_len)

    star_def = f"""STAR_NODE_M = [
        {node_block}
];
STAR_BAR_M = [
        {bar_block}
];
STAR_RECV_M = [
        {recv_block}
];
module star() {{
    difference() {{
        union() {{
            for (m = STAR_BAR_M)  multmatrix(m) edge_bar();
            for (m = STAR_NODE_M) multmatrix(m) node_solid();
            for (m = STAR_RECV_M) multmatrix(m) receiver();
        }}
        for (m = STAR_NODE_M) multmatrix(m) bore();   // clear every socket last
    }}
}}"""

    # ---- star.scad --------------------------------------------------------
    (MODELS / "star.scad").write_text(f"""// Ssymmank lamp -- STAR TILE (one of 12, all congruent).
// Hub socket + 5 spokes + 5 corner sockets + 5 boundary bars + 10 connector
// mortises, fused as one printable pentagonal wheel.  Hub at origin, +Z out.
// Auto-generated by build_star.py.

{common}

{star_def}

star();   // hub at origin, sockets up; each edge kinks out to leave perpendicular
""")

    # ---- connector.scad ---------------------------------------------------
    (MODELS / "connector.scad").write_text(f"""// Ssymmank lamp -- CONNECTOR bar (one of 60, all identical).
// Flat fin with a keyed tenon at each end; plugs into two neighbouring tiles'
// corner mortises.  Lay flat (fin in the XY plane) to print.
// Auto-generated by build_star.py.

{common}

rotate([90, 0, 0]) connector();   // fin laid flat on the bed
""")

    # ---- test_edges.scad : two connectors, flat, for a test print ----------
    (MODELS / "test_edges.scad").write_text(f"""// Ssymmank lamp -- TWO CONNECTORS for a test print (check the keyed joint on a
// real star tile).  Both laid flat on the bed, spaced apart.
// Auto-generated by build_star.py.

{common}

for (i = [0, 1]) translate([0, i * 13, 0]) rotate([90, 0, 0]) connector();
""")

    # ---- stars_assembly.scad (full fit check) -----------------------------
    PALETTE = ["#4F86C6", "#C64F4F", "#4FC686", "#C6A14F", "#864FC6", "#4FC6C6",
               "#C64F86", "#86C64F", "#C6864F", "#4F4FC6", "#C6C64F", "#9C9C9C"]
    color_lines = "\n".join(
        f'    color("{PALETTE[i]}") multmatrix(PLACE_M[{i}]) star();'
        for i in range(12))
    (MODELS / "stars_assembly.scad").write_text(f"""// Ssymmank lamp -- FIT CHECK: 12 star tiles + 60 connectors = full frame.
// Auto-generated by build_star.py.

{common}

{star_def}

PLACE_M = [
    {place_block}
];
CONN_M = [
    {conn_block}
];

{color_lines}
color("#BBBBBB") for (m = CONN_M) multmatrix(m) connector();
""")

    # ---- mate_test.scad : 2 neighbouring tiles + their shared connector ----
    a0, b0 = next((a, b) for a, b in inter)         # first inter edge
    pa, pb = owner[a0], owner[b0]
    place_a = _fmt_matrix(placements[pa])
    place_b = _fmt_matrix(placements[pb])
    conn_ab = _fmt_matrix(edge_frame(V[a0], V[b0]))
    (MODELS / "mate_test.scad").write_text(f"""// Ssymmank lamp -- MATE TEST: two neighbouring star tiles and the single
// connector that bridges them, to verify the keyed joint seats.
// Auto-generated by build_star.py.

{common}

{star_def}

color("#4F86C6") multmatrix({place_a}) star();
color("#C64F4F") multmatrix({place_b}) star();
color("#DDAA33") multmatrix({conn_ab}) connector();
""")

    # ---- stem_fit.scad : mushrooms seated in the hub + a corner, cross-cut ----
    (MODELS / "stem_fit.scad").write_text(f"""// Ssymmank lamp -- STEM FIT TEST.  Drops real mushroom stems into the hub and a
// corner socket of one tile, then cross-cuts (CUT=true) to verify the bore is
// clear of bar material and the conical stem seats with clearance.
// Auto-generated by build_star.py.

{common}

{star_def}

// The mushroom stem is a straight cone: r=STEM_TIP_R at the tip, widening to
// THROAT_R (8) at the throat (THROAT_Z = -20 in mushroom coords). We model just
// that cone -- the part that enters the bore -- so the cross-section is small
// and the seating/clearance is exact (the full mushroom adds nothing here).
THROAT_R = 8; THROAT_Z = -20;
SEAT = -3.0;   // stem tip lands here (node-local z); bore floor is at -3.5
STUB = 30;     // how much of the stem to draw (mm)

module stem(i, sl) {{
    slope = (THROAT_R - STEM_TIP_R) / (sl - THROAT_Z * -1);   // r-gain per mm
    multmatrix(STAR_NODE_M[i]) translate([0, 0, SEAT])
        color("Cornsilk")
        cylinder(h = STUB, r1 = STEM_TIP_R, r2 = STEM_TIP_R + slope * STUB, $fn = 48);
}}

module scene() difference() {{
    union() {{
        color("#9FB6CF") star();
        stem(0, 120.96);   // hub (XL)
        stem(1, 70.0);     // one corner (small)
    }}
    translate([-500, 0, -500]) cube([1000, 1000, 1000]);   // cut at y=0
}}

VIEW = "socket";   // "socket" -> zoom the hub bore cross-section; "full" -> whole
if (VIEW == "socket")
    intersection() {{ scene(); translate([0, -7, 2.5]) cube([30, 16, 26], center = true); }}
else
    scene();
""")

    print(f"edge length {edge_len:.2f} mm")
    print(f"saved star.scad ({len(node_l)} sockets, {len(bar_l)} bars, "
          f"{len(recv_l)} mortises)")
    print(f"saved connector.scad, stars_assembly.scad (60 connectors), mate_test.scad, "
          f"test_edges.scad, stem_fit.scad")


if __name__ == "__main__":
    main()
