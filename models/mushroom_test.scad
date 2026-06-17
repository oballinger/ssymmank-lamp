// Ssymmank mushroom -- SMALL TEST PRINT (PLA / Ultimaker, 0.4mm nozzle).
//
// A shrunk mushroom for validating the thin curved petals before printing the
// real ones.  The overall part is small (~60mm cap, ~35mm tall) so it prints in
// minutes, but PLATE_T / WALL are kept at their REAL printed thickness (0.8mm)
// so the test actually exercises the thin petals -- it is NOT uniformly scaled
// (that would thin the petals too).
//
// Slicing: 0.4mm nozzle, 0.12-0.2mm layers, 2 walls (= 0.8mm, matches the
// petal), 0% infill, no top/bottom layers on the petal if you want it
// translucent.  Print cap-down (petals on the bed) with the stem pointing up;
// add support only under the funnel bowl if your overhang setting needs it.

include <mushroom_simple.scad>;

// thin shells at real printed thickness
PLATE_T = 0.8;     // petal thickness (try 0.4 for a single-wall translucent petal)
WALL    = 0.8;     // funnel / stem wall

// small footprint (kept proportional; PENT_R stays > funnel hole = RIM_R-WALL)
RIM_R      = 18;
THROAT_R   = 5;
RIM_Z      = 7;
DISH_DEPTH = 16;
PENT_R     = 30;
ARM_DROP   = 5;
STEM_LEN   = 18;
STEM_TIP_R = 4;

CURVE_FN = 120;    // a touch smoother for the small cap
