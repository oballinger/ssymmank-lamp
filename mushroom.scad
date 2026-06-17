// Ssymmank mushroom element -- built up step by step.
//
// STEP 1: a simple shallow funnel.
// STEP 2: add a long stem hanging down from the throat.
// STEP 3: make the stem a hollow cone whose bore continues the funnel's.
// STEP 4: rebuild funnel + stem as ONE continuous revolved shell (no gap).
// STEP 5: add a flat pentagon flange on the funnel's open rim
//         (centre stays open so you can still see into the funnel).
// STEP 6: double the pentagon, and stretch two opposing arms (corners) by 2x.
// STEP 7: flat riblike support struts from each pentagon corner down the
//         BACK of the funnel + shaft (nothing on the front/dish side).
// STEP 8: ribs bounded to the vertex/stem and tapered at the corners;
//         rim made flush so pentagon + funnel + stem are one continuous shell.
// STEP 9: curve the pentagon flange backward onto the lamp's circumsphere so
//         tiled mushrooms form a clean sphere, not a faceted solid.

// ---- parameters -----------------------------------------------------------
LAMP_DIAMETER = 200;  // assembled lamp diameter (mm) -> sets the face curvature

RIM_R    = 40;    // wide rim radius at the top (mm)
THROAT_R = 8;     // narrow throat radius at the bottom (mm)
HEIGHT   = 14;    // funnel height -- shallow (mm)
WALL     = 1.6;   // wall thickness (mm)

STEM_LEN   = 70;  // stem length below the throat (mm) -- long
STEM_TIP_R = 4;   // stem outer radius at the bottom tip (mm)
                  // top radius == THROAT_R so it merges into the funnel

PENT_R   = 68;    // pentagon circumradius, centre -> corner (mm) -- 1.25x of 54
PLATE_T  = 1.6;   // flat pentagon plate thickness (mm)
ARM_STRETCH = 1.25; // radial stretch applied to two opposing arms (corners)
ARM_DROP = 12;    // lower the two long arms by this much in-plane (mm)

RIB_T    = 1.2;   // rib thickness, tangential -- thin, so it reads as 2D
RIB_H    = 4;     // rib depth standing off the back surface (mm)

$fn = 96;

// ---- curvature ------------------------------------------------------------
// The flange is a cap of the circumsphere (radius CIRC_R). The sphere is
// centred on the axis so the flange's inner edge stays at z = HEIGHT (flush
// with the funnel rim); the surface then curves backward toward the arms.
CIRC_R = LAMP_DIAMETER / 2;       // true circumsphere radius (perfect sphere)
CURVE_RELAX = 3.0;                // >1 softens the curve; = 1 is a perfect sphere
CURVE_R = CIRC_R * CURVE_RELAX;   // radius actually used for the flange cap
CAP_ZC = HEIGHT - sqrt(CURVE_R * CURVE_R - (RIM_R - WALL) * (RIM_R - WALL));
function cap_z(rho) = CAP_ZC + sqrt(CURVE_R * CURVE_R - rho * rho);

// ---- body (funnel + stem as one shell) ------------------------------------
// The wall follows one unbroken (radius, z) profile: stem tip -> throat -> rim.
// The inner profile is the same path offset inward by WALL. At the rim the
// inner edge stops at z = HEIGHT (then runs vertically up to clear the cut),
// giving a uniform-thickness rim that opens at exactly RIM_R - WALL -- the
// same radius the pentagon plate's hole uses, so plate + funnel + stem read
// as one continuous shell.
OUTER_PROFILE = [
    [0,          -STEM_LEN],
    [STEM_TIP_R, -STEM_LEN],
    [THROAT_R,   0],
    [RIM_R,      HEIGHT],
    [0,          HEIGHT],
];
INNER_PROFILE = [
    [0,                 -STEM_LEN - 1],
    [STEM_TIP_R - WALL, -STEM_LEN - 1],
    [THROAT_R   - WALL, 0],
    [RIM_R      - WALL, HEIGHT],       // clean uniform rim at z = HEIGHT
    [RIM_R      - WALL, HEIGHT + 1],   // vertical riser to clear the top cut
    [0,                 HEIGHT + 1],
];

module body() {
    rotate_extrude(angle = 360)
        difference() {
            polygon(OUTER_PROFILE);
            polygon(INNER_PROFILE);
        }
}

// ---- pentagon flange on the rim -------------------------------------------
// A flat pentagon at the funnel's open end. A circular hole the size of the
// funnel opening keeps the centre open. Two opposing arms (the left & right
// corners) are stretched radially outward by ARM_STRETCH.
PENT_ANGLES = [90, 162, 234, 306, 18];      // apex up; 162 & 18 are L/R arms
PENT_FACTOR = [1, ARM_STRETCH, 1, 1, ARM_STRETCH];

function pentagon_pts() =
    [ for (i = [0:4])
        let (r = PENT_R * PENT_FACTOR[i], a = PENT_ANGLES[i],
             drop = (PENT_FACTOR[i] > 1) ? ARM_DROP : 0)
        [r * cos(a), r * sin(a) - drop] ];

// The flange is a curved cap of the circumsphere. Built as the top PLATE_T
// slice of a domed solid: take the pentagon prism intersected with a solid
// sphere, then subtract a copy shifted down by PLATE_T. This leaves only the
// top curved slab (no second/bottom cap) and is robust in preview. The hole
// is slightly smaller than the funnel opening so the cap overlaps and fuses
// to the funnel rim (one solid, not two).
FLANGE_HOLE = RIM_R - WALL - 3;   // overlap the rim so the cap fuses to it

module cap_solid() {
    intersection() {
        translate([0, 0, CAP_ZC]) sphere(r = CURVE_R, $fn = 200);
        linear_extrude(height = 4 * CURVE_R, center = true)
            difference() {
                polygon(pentagon_pts());    // pentagon w/ two stretched arms
                circle(r = FLANGE_HOLE);    // funnel opening stays open
            }
    }
}

module pentagon_flange() {
    render()   // force exact (CGAL) eval so the preview shows the whole cap
    difference() {
        cap_solid();
        translate([0, 0, -PLATE_T]) cap_solid();
    }
}

// ---- support struts (flat ribs, back only) --------------------------------
// One thin rib per pentagon corner. It sits entirely on the BACK of the part:
// under the plate, then proud of the funnel's outer surface, then down the
// outside of the shaft. Each rib is thin tangentially (RIB_T) so it reads as
// a flat 2D fin rather than a round rod. Worked out in a meridian frame
// (u = radius, v = height; thin direction = Y) then rotated to the corner's
// azimuth.
// rib tile: flat tangential plate of size s (s -> 0 tapers the rib to a point)
module rib_tile(u, v, s) {
    translate([u, 0, v]) cube([s, RIB_T, s], center = true);
}

module rib(vx, vy) {
    th = atan2(vy, vx);
    cr = sqrt(vx * vx + vy * vy);   // corner radial distance
    o  = RIB_H / 2;                 // push onto the back surface
    TIP = 0.1;                      // taper-to-point size
    // Flange portion follows the curved underside (cap_z) from the pentagon
    // vertex inward to the rim; then proud of the funnel + shaft. Ends sit
    // exactly at the vertex and the stem tip and taper to a point.
    fs = 3;
    flange = [ for (k = [0 : fs])
                 let (rho = cr + (RIM_R - cr) * k / fs)
                 [rho, cap_z(rho) - PLATE_T, (k == 0) ? TIP : RIB_H] ];
    rest = [
        [RIM_R + o,      HEIGHT - o,        RIB_H],   // funnel back, below rim
        [THROAT_R + o,   0,                 RIB_H],   // throat
        [STEM_TIP_R + o, -STEM_LEN + o,     RIB_H],   // shaft, above the tip
        [STEM_TIP_R,     -STEM_LEN,         TIP],     // stem tip (point, flush)
    ];
    N = concat(flange, rest);
    rotate([0, 0, th])
        for (i = [0 : len(N) - 2])
            hull() {
                rib_tile(N[i][0],     N[i][1],     N[i][2]);
                rib_tile(N[i + 1][0], N[i + 1][1], N[i + 1][2]);
            }
}

module ribs() {
    for (p = pentagon_pts()) rib(p[0], p[1]);
}

// solid of the open interior (dish + bore); used to trim any rib material that
// would intrude onto the front so the ribs live strictly on the back.
module cavity_solid() {
    rotate_extrude(angle = 360) polygon(INNER_PROFILE);
}

color("Cornsilk") union() {
    body();
    pentagon_flange();
    difference() {
        ribs();
        cavity_solid();   // keep ribs off the front / out of the dish
    }
}
