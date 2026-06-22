// Ssymmank mushroom -- SMALL stem, fast core + CURVED pentagon flange.
//
// This is mushroom_small.scad (the simplified, fast-loading core) with ONE
// change: the flat pentagon flange is replaced by the curved spherical-cap
// flange from mushroom.scad (STEP 9). The pentagon now curves backward onto
// the lamp's circumsphere so tiled mushrooms form a clean sphere.
//
// Everything else (trumpet funnel, conical stem, back ribs) is the cheap
// version, so this previews/renders fast and is ready to print.

// ---- parameters -----------------------------------------------------------
RIM_R    = 40;    // wide funnel rim radius (mm)
THROAT_R = 8;     // narrow throat radius (mm)
RIM_Z    = 14;    // rim height above the throat plane (mm)
WALL     = 1.6;   // shell wall thickness (mm)

STEM_LEN   = 70;  // SMALL stem length below the throat (mm)
STEM_TIP_R = 4;   // stem base (bottom tip) radius (mm)

PENT_R      = 68;    // pentagon circumradius, centre -> corner (mm)
PLATE_T     = 1.6;   // pentagon plate thickness (mm)
ARM_STRETCH = 1.25;  // radial stretch on two opposing arms
ARM_DROP    = 12;    // drop those two long arms in-plane (mm)

RIB_T = 1.2;      // rib tangential thickness (thin -> reads as a 2D fin)
RIB_H = 4;        // rib depth standing off the back surface (mm)

DISH_DEPTH = 34;  // throat sits this far below the rim -> bowl depth (mm)
DN = 16;          // samples along the funnel curve
$fn = 48;         // low: this model is meant to be cheap

THROAT_Z = RIM_Z - DISH_DEPTH;

// ---- curvature (from mushroom.scad, STEP 9) -------------------------------
// The flange is a cap of the circumsphere (radius CIRC_R). The sphere is
// centred on the axis so the flange's inner edge stays at z = RIM_Z (flush
// with the funnel rim); the surface then curves backward toward the arms.
LAMP_DIAMETER = 200;              // assembled lamp diameter (mm) -> face curvature
CIRC_R   = LAMP_DIAMETER / 2;     // true circumsphere radius (perfect sphere)
CURVE_RELAX = 3.0;                // >1 softens the curve; = 1 is a perfect sphere
CURVE_R  = CIRC_R * CURVE_RELAX;  // radius actually used for the flange cap
SPHERE_FN = 72;                   // facets on the big curvature spheres
CAP_ZC   = RIM_Z - sqrt(CURVE_R * CURVE_R - (RIM_R - WALL) * (RIM_R - WALL));
function cap_z(rho) = CAP_ZC + sqrt(CURVE_R * CURVE_R - rho * rho);
FLANGE_HOLE = RIM_R - WALL - 2;   // overlap the rim so the cap fuses to it

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

// ---- pentagon footprint ---------------------------------------------------
PENT_ANGLES = [90, 162, 234, 306, 18];      // apex up; 162 & 18 are L/R arms
PENT_FACTOR = [1, ARM_STRETCH, 1, 1, ARM_STRETCH];

function pentagon_pts() =
    [ for (i = [0:4])
        let (r = PENT_R * PENT_FACTOR[i], a = PENT_ANGLES[i],
             drop = (PENT_FACTOR[i] > 1) ? ARM_DROP : 0)
        [r * cos(a), r * sin(a) - drop] ];

// ---- CURVED pentagon flange (spherical-cap shell) -------------------------
// The pentagon footprint (prism with a central hole) intersected with a
// concentric spherical shell of uniform thickness PLATE_T. The two same-centre
// spheres never coincide, so the OpenCSG preview is clean with no render().
// Only the TOP cap of the sphere is wanted. The pentagon column must be
// bounded to the rim region (z ~ 0..RIM_Z), otherwise it also slices the
// BOTTOM of the full sphere shell and produces a phantom second pentagon far
// below the stem. EXTRUDE_LO/HI bracket the real cap with margin.
EXTRUDE_LO = -10;
EXTRUDE_HI = RIM_Z + 10;
module pentagon_flange() {
    intersection() {
        translate([0, 0, EXTRUDE_LO])
            linear_extrude(height = EXTRUDE_HI - EXTRUDE_LO)
                difference() {
                    polygon(pentagon_pts());    // pentagon w/ two stretched arms
                    circle(r = FLANGE_HOLE);    // funnel opening stays open
                }
        translate([0, 0, CAP_ZC])           // uniform-thickness spherical shell
            difference() {
                sphere(r = CURVE_R,           $fn = SPHERE_FN);
                sphere(r = CURVE_R - PLATE_T, $fn = SPHERE_FN);
            }
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
MUSH_ALPHA = 0.7;   // 70% opaque (semi-transparent)
module mushroom(stem_len = STEM_LEN) {
    color("Cornsilk", MUSH_ALPHA)
    union() {
        body(stem_len);
        pentagon_flange();
        ribs(stem_len);
    }
}

mushroom();
