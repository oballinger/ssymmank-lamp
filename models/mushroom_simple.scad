// Ssymmank mushroom -- SIMPLIFIED, fast-loading core.
//
// A lightweight version of mushroom.scad meant to open and preview instantly:
//   * flat pentagon flange (no curved spherical cap -> no big r=300 spheres)
//   * thin back ribs built from ONE extruded polygon each (no hull stacks, no
//     intersection with an envelope solid, no CGAL-heavy clipping)
//   * low $fn
// It keeps the recognisable shape -- trumpet funnel, conical stem, stretched
// pentagon, back fins -- but evaluates in a fraction of a second.
//
// ORIENTATION: the funnel/stem axis is +Z (stem at -Z, cap at +Z). The pentagon
// "top" (its single un-stretched apex) is +Y; the two long arms are the lower
// corners at 162 deg and 18 deg.
//
// The small / medium / large files `include` this core and override STEM_LEN.
// `mushroom(stem_len)` is also exposed as a module so other files can `use`
// this and place oriented copies.

// ---- parameters -----------------------------------------------------------
RIM_R    = 40;    // wide funnel rim radius (mm)
THROAT_R = 8;     // narrow throat radius (mm)
RIM_Z    = 14;    // rim height above the throat plane (mm)
WALL     = 1.6;   // shell wall thickness (mm)

STEM_LEN   = 84;  // default stem length below the throat (mm) -- override per size
STEM_TIP_R = 4;   // stem base (bottom tip) radius (mm)

PENT_R      = 68;    // pentagon circumradius, centre -> corner (mm)
PLATE_T     = 1.6;   // flat pentagon plate thickness (mm)
ARM_STRETCH = 1.25;  // radial stretch on two opposing arms
ARM_DROP    = 12;    // drop those two long arms in-plane (mm)

RIB_T = 1.2;      // rib tangential thickness (thin -> reads as a 2D fin)
RIB_H = 4;        // rib depth standing off the back surface (mm)

DISH_DEPTH = 34;  // throat sits this far below the rim -> bowl depth (mm)
DN = 16;          // samples along the funnel curve
$fn = 48;         // low: this model is meant to be cheap

THROAT_Z = RIM_Z - DISH_DEPTH;

// concave trumpet bowl: steep at the throat, easing to a gentle lip at the rim
function funnel_z(r) =
    let (t = (r - THROAT_R) / (RIM_R - THROAT_R))
        THROAT_Z + DISH_DEPTH * (1 - (1 - t) * (1 - t));

// ---- body (funnel + stem as one revolved shell) ---------------------------
function outer_profile(sl) = concat(
    [[0, -sl], [STEM_TIP_R, -sl]],
    [ for (i = [0:DN]) let (r = THROAT_R + (RIM_R - THROAT_R) * i / DN)
        [r, funnel_z(r)] ],
    [[0, RIM_Z]]
);
function inner_profile(sl) = concat(
    [[0, -sl - 1], [STEM_TIP_R - WALL, -sl - 1]],
    [ for (i = [0:DN]) let (r = THROAT_R + (RIM_R - THROAT_R) * i / DN)
        [r - WALL, funnel_z(r)] ],
    [[RIM_R - WALL, RIM_Z + 1], [0, RIM_Z + 1]]
);

module body(sl) {
    rotate_extrude(angle = 360)
        difference() {
            polygon(outer_profile(sl));
            polygon(inner_profile(sl));
        }
}

// ---- flat pentagon flange on the rim --------------------------------------
PENT_ANGLES = [90, 162, 234, 306, 18];      // apex up; 162 & 18 are L/R arms
PENT_FACTOR = [1, ARM_STRETCH, 1, 1, ARM_STRETCH];

function pentagon_pts() =
    [ for (i = [0:4])
        let (r = PENT_R * PENT_FACTOR[i], a = PENT_ANGLES[i],
             drop = (PENT_FACTOR[i] > 1) ? ARM_DROP : 0)
        [r * cos(a), r * sin(a) - drop] ];

module pentagon_flange() {
    translate([0, 0, RIM_Z - PLATE_T])
        linear_extrude(height = PLATE_T)
            difference() {
                polygon(pentagon_pts());
                circle(r = RIM_R - WALL);   // funnel opening stays open
            }
}

// ---- back ribs (one thin extruded fin per corner) -------------------------
function rib_surface(sl) = concat(
    [ for (i = [0:DN]) let (r = RIM_R + (THROAT_R - RIM_R) * i / DN)
        [r, funnel_z(r)] ],          // rim -> throat
    [[STEM_TIP_R, -sl]]              // -> stem tip
);

module rib(az, sl) {
    s = rib_surface(sl);
    n = len(s);
    outer = [ for (i = [n - 1 : -1 : 0])
                let (d = RIB_H * sin(180 * i / (n - 1)))   // 0 at ends, max mid
                [s[i][0] + d, s[i][1]] ];
    rotate([0, 0, az])
        rotate([90, 0, 0])
            linear_extrude(height = RIB_T, center = true)
                polygon(concat(s, outer));
}

module ribs(sl) { for (a = PENT_ANGLES) rib(a, sl); }

// ---- the whole element ----------------------------------------------------
module mushroom(stem_len = STEM_LEN) {
    color("Cornsilk")
    union() {
        body(stem_len);
        pentagon_flange();
        ribs(stem_len);
    }
}

mushroom();
