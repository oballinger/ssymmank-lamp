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
WALL     = 0.8;   // shell (funnel + stem) wall thickness (mm) -- 2 perimeters
                  // on a 0.4mm nozzle; as thin as is reliable in PLA

STEM_LEN   = 84;  // default stem length below the throat (mm) -- override per size
STEM_TIP_R = 4;   // stem base (bottom tip) radius (mm)

PENT_R      = 68;    // pentagon circumradius, centre -> corner (mm)
PLATE_T     = 0.8;   // PETAL (pentagon cap) thickness (mm) -- as thin as is
                     // reliable in PLA on a 0.4mm nozzle (2 perimeters). Try
                     // 0.4-0.6 for a single-wall, more translucent petal.
ARM_STRETCH = 1.25;  // radial stretch on two opposing arms
ARM_DROP    = 12;    // drop those two long arms in-plane (mm)

RIB_T = 0.8;      // rib thickness (mm) -- 2 perimeters, thin 2D fin
RIB_H = 4;        // rib depth standing off the back surface (mm)
RIB_BITE = 1.6;   // how far the rib's inner edge sinks INTO the wall so it
                  // always fuses to the shell (> WALL: pokes through into the
                  // bore a little, guaranteeing a solid weld on thin walls)

DISH_DEPTH = 26;  // throat sits this far below the rim -> bowl depth (mm).
                  // shallower than the original 34 so an outer shell's funnel
                  // clears the next-inner shell's caps in the shingled assembly
                  // (deepest depth that stays intersection-free; see assembly.scad)
DN = 16;          // samples along the funnel curve
$fn = 48;         // low: this model is meant to be cheap

// ---- backward curvature (from mushroom.scad, kept cheap) ------------------
// The pentagon cap is curved backward onto the lamp's circumsphere so tiled
// mushrooms approximate a sphere.  Done as a flat pentagon prism intersected
// with a CONCENTRIC spherical shell of uniform thickness PLATE_T -- no render(),
// so it stays a fast OpenCSG preview.  CURVE_FN only needs to be high enough
// that the small cap region of the big sphere reads smooth.
CURVE_CAP    = true;   // false -> flat cap (original simplified behaviour)
LAMP_DIAMETER = 200;   // assembled lamp diameter -> sets the curvature
CURVE_RELAX  = 2.3;    // >1 softens the curve; =1 is a perfect sphere. 2.3 makes
                       // the cap a patch ~CONCENTRIC with the lamp centre, so it
                       // is radially THIN and shingles past other shells' caps
                       // without intersecting (still only a gentle ~10mm dome).
CURVE_FN     = 96;     // facets on the curvature sphere
CURVE_R = LAMP_DIAMETER / 2 * CURVE_RELAX;
CAP_OVERLAP = 3.0;   // cap reaches this far past the funnel inner rim so the
                     // curved cap always fuses to the funnel as ONE solid
                     // (matters most with thin petals, where the curve dips
                     //  below the flat rim and a flush edge would detach).
FLANGE_HOLE = RIM_R - WALL - CAP_OVERLAP;                     // cap inner edge
CAP_ZC = RIM_Z - sqrt(CURVE_R*CURVE_R - FLANGE_HOLE*FLANGE_HOLE);  // hole edge at RIM_Z

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
    if (CURVE_CAP) {
        // curved cap: pentagon prism (with hole) ∩ uniform-thickness shell.
        // The prism spans only the cap's z-range -- a tall (4*CURVE_R) prism
        // made OpenCSG's depth buffer ~1:1000 vs the 0.8 mm shell, so the F5
        // preview dropped the front/middle flange facets (pentagon looked
        // "cut"). A short prism fixes the preview AND removes the need for the
        // upper-half clip: the antipodal bottom cap sits ~600 mm below it.
        FLANGE_Z_LO = -PLATE_T - 4;   // below the lowest (arm-tip) cap point
        FLANGE_Z_HI = RIM_Z + 4;      // above the inner-edge cap point
        intersection() {
            translate([0, 0, (FLANGE_Z_LO + FLANGE_Z_HI) / 2])
            linear_extrude(height = FLANGE_Z_HI - FLANGE_Z_LO, center = true)
                difference() {
                    polygon(pentagon_pts());
                    circle(r = FLANGE_HOLE);    // funnel opening stays open
                }
            translate([0, 0, CAP_ZC])
                difference() {
                    sphere(r = CURVE_R,            $fn = CURVE_FN);
                    sphere(r = CURVE_R - PLATE_T,  $fn = CURVE_FN);
                }
        }
    } else {
        translate([0, 0, RIM_Z - PLATE_T])
            linear_extrude(height = PLATE_T)
                difference() {
                    polygon(pentagon_pts());
                    circle(r = RIM_R - WALL);   // funnel opening stays open
                }
    }
}

// ---- back ribs (one thin extruded fin per corner) -------------------------
// inner spine sunk RIB_BITE into the wall (so the fin overlaps the shell solid
// and fuses); the fin then stands proud by RIB_H beyond that.
function rib_surface(sl) = concat(
    [ for (i = [0:DN]) let (r = RIM_R + (THROAT_R - RIM_R) * i / DN)
        [r - RIB_BITE, funnel_z(r)] ],     // rim -> throat
    [[STEM_TIP_R - RIB_BITE, -sl]]         // -> stem tip
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
module mushroom_shape(stem_len = STEM_LEN) {
    union() {
        body(stem_len);
        pentagon_flange();
        ribs(stem_len);
    }
}
// paint=true -> own Cornsilk colour (standalone). paint=false -> bare geometry,
// so a caller (assembly.scad) can union many and apply ONE transparent colour --
// otherwise overlapping per-mushroom transparent solids cancel to full clear.
module mushroom(stem_len = STEM_LEN, paint = true) {
    if (paint) color("Cornsilk", MUSH_ALPHA) mushroom_shape(stem_len);
    else mushroom_shape(stem_len);
}

mushroom();
