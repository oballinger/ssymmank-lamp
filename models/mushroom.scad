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
// STEP 10: smooth outer surface -- funnel dish meets the cap tangentially (no
//          hard rim) and the ribs are clipped just under the surface.
// STEP 11: restore a clearly-visible trumpet funnel bowl + conical stem (the
//          tangent dish had flattened them away), keeping the smooth rim/cap.

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

$fn = 64;          // revolve / circle facets (96 was overkill; identical look)
SPHERE_FN = 72;    // facets on the big r=CURVE_R curvature spheres. The cap is a
                   // tiny, nearly-flat slice of a 300 mm sphere, so 72 is smooth
                   // here yet ~8x cheaper than 200 in the CGAL/CSG booleans --
                   // this is what makes preview AND render fast.

// ---- curvature ------------------------------------------------------------
// The flange is a cap of the circumsphere (radius CIRC_R). The sphere is
// centred on the axis so the flange's inner edge stays at z = HEIGHT (flush
// with the funnel rim); the surface then curves backward toward the arms.
CIRC_R = LAMP_DIAMETER / 2;       // true circumsphere radius (perfect sphere)
CURVE_RELAX = 3.0;                // >1 softens the curve; = 1 is a perfect sphere
CURVE_R = CIRC_R * CURVE_RELAX;   // radius actually used for the flange cap
CAP_ZC = HEIGHT - sqrt(CURVE_R * CURVE_R - (RIM_R - WALL) * (RIM_R - WALL));
function cap_z(rho)     = CAP_ZC + sqrt(CURVE_R * CURVE_R - rho * rho);
function cap_slope(rho) = -rho / sqrt(CURVE_R * CURVE_R - rho * rho);

// ---- funnel dish ----------------------------------------------------------
// A concave trumpet bowl from the throat up to the rim. The rim sits at the
// cap's inner edge height so the funnel and the curved pentagon flange join as
// one continuous shell. The bowl is a smooth circular-arc concave so it reads
// clearly as a funnel and there is no hard crease leaving the throat.
RIM_Z   = cap_z(RIM_R);            // rim height = cap edge (funnel meets flange)
DISH_DEPTH = 34;                   // throat sits this far below the rim (mm)
THROAT_Z   = RIM_Z - DISH_DEPTH;   // throat height
DISH_N  = 28;                      // samples along the dish
// concave arc: quadratic blend giving a steep wall at the throat easing to a
// gentle (near-flat) lip at the rim -- a trumpet, not a straight cone.
function funnel_z(r) =
    let (t = (r - THROAT_R) / (RIM_R - THROAT_R))
        THROAT_Z + DISH_DEPTH * (1 - (1 - t) * (1 - t));
// dish curve sampled (r,z), with the radius pulled in by `off` (0 outer, WALL inner)
function dish_sample(off) =
    [ for (i = [0 : DISH_N])
        let (r = THROAT_R + (RIM_R - THROAT_R) * i / DISH_N)
        [r - off, funnel_z(r)] ];

// ---- body (funnel + stem as one shell) ------------------------------------
// One unbroken (radius, z) profile: stem tip -> throat -> trumpet dish -> rim.
OUTER_PROFILE = concat(
    [[0, -STEM_LEN], [STEM_TIP_R, -STEM_LEN]],
    dish_sample(0),                                  // throat -> rim
    [[0, RIM_Z]]
);
INNER_PROFILE = concat(
    [[0, -STEM_LEN - 1], [STEM_TIP_R - WALL, -STEM_LEN - 1]],
    dish_sample(WALL),                               // inner wall
    [[RIM_R - WALL, RIM_Z + 1], [0, RIM_Z + 1]]
);

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

// The flange is a curved cap of the circumsphere: the pentagon footprint
// (prism with a central hole) intersected with a CONCENTRIC spherical shell of
// uniform thickness PLATE_T. Two same-centre spheres a fixed PLATE_T apart never
// have coinciding surfaces, so the OpenCSG preview is clean with NO render() --
// forcing render() here is what made every preview load take minutes. The hole
// is slightly smaller than the funnel opening so the cap overlaps and fuses to
// the funnel rim (one solid, not two).
FLANGE_HOLE = RIM_R - WALL - 2;   // overlap the rim so the cap fuses to it

module pentagon_flange() {
    intersection() {
        linear_extrude(height = 4 * CURVE_R, center = true)
            difference() {
                polygon(pentagon_pts());    // pentagon w/ two stretched arms
                circle(r = FLANGE_HOLE);    // funnel opening stays open
            }
        translate([0, 0, CAP_ZC])           // uniform-thickness spherical shell
            difference() {
                sphere(r = CURVE_R,            $fn = SPHERE_FN);
                sphere(r = CURVE_R - PLATE_T,  $fn = SPHERE_FN);
            }
        // upper-half clip: keep only the top cap (the full shell would also
        // give the antipodal bottom cap through the tall prism).
        translate([0, 0, CAP_ZC + CURVE_R])
            cube([4 * CURVE_R, 4 * CURVE_R, 2 * CURVE_R], center = true);
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
    // Spine runs along the inner (back) surface: pentagon vertex -> curved cap
    // underside -> smooth dish underside -> down the shaft. Ends taper to a
    // point at the vertex and the stem tip. The whole rib is intersected with
    // the outer envelope below, so it can never break the smooth outer face.
    fs = 4;
    flange = [ for (k = [0 : fs])
                 let (rho = cr + (RIM_R - cr) * k / fs)
                 [rho, cap_z(rho) - PLATE_T, (k == 0) ? TIP : RIB_H] ];
    ds = 6;
    dish = [ for (k = [1 : ds])
               let (r = RIM_R + (THROAT_R - RIM_R) * k / ds)
               [r - WALL - o, funnel_z(r) - WALL, RIB_H] ];
    shaft = [
        [STEM_TIP_R + o, -STEM_LEN + o, RIB_H],   // shaft, above the tip
        [STEM_TIP_R,     -STEM_LEN,     TIP],     // stem tip (point, flush)
    ];
    N = concat(flange, dish, shaft);
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

// open interior (dish + bore): trims rib material off the FRONT / out of dish.
module cavity_solid() {
    rotate_extrude(angle = 360) polygon(INNER_PROFILE);
}

// filled outer envelope (the smooth outer surface as a solid). Intersecting
// the ribs with this guarantees nothing pokes through the outer face.
module outer_envelope() {
    union() {
        rotate_extrude(angle = 360) polygon(OUTER_PROFILE);
        translate([0, 0, CAP_ZC]) sphere(r = CURVE_R, $fn = SPHERE_FN);
    }
}

// No render() here: forcing CGAL at the top level made F5 preview take minutes.
// Preview now uses fast OpenCSG; full CGAL runs only on F6 / STL export.
color("Cornsilk")
union() {
    body();
    pentagon_flange();
    intersection() {
        difference() {
            ribs();
            cavity_solid();      // keep ribs off the front / out of the dish
        }
        outer_envelope();        // and never poking through the outer surface
    }
}
