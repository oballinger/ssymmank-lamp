// Ssymmank lamp -- STEM FIT TEST.  Drops real mushroom stems into the hub and a
// corner socket of one tile, then cross-cuts to verify the bore is clear of bar
// material and the conical stem seats with clearance.
// Modules/params come from star.scad, so edits there propagate here.

include <star.scad>
SHOW_STAR = false;   // library mode: don't draw the lone star tile

// The mushroom stem is a straight cone: r=STEM_TIP_R at the tip, widening to
// THROAT_R (8) at the throat (THROAT_Z = -20 in mushroom coords). We model just
// that cone -- the part that enters the bore -- so the cross-section is small
// and the seating/clearance is exact (the full mushroom adds nothing here).
THROAT_R = 8; THROAT_Z = -20;
SEAT = -3.0;   // stem tip lands here (node-local z); bore floor is at -3.5
STUB = 30;     // how much of the stem to draw (mm)

module stem(i, sl) {
    slope = (THROAT_R - STEM_TIP_R) / (sl - THROAT_Z * -1);   // r-gain per mm
    multmatrix(STAR_NODE_M[i]) translate([0, 0, SEAT])
        color("Cornsilk")
        cylinder(h = STUB, r1 = STEM_TIP_R, r2 = STEM_TIP_R + slope * STUB, $fn = 48);
}

module scene() difference() {
    union() {
        color("#9FB6CF") star();
        stem(0, 120.96);   // hub (XL)
        stem(1, 70.0);     // one corner (small)
    }
    translate([-500, 0, -500]) cube([1000, 1000, 1000]);   // cut at y=0
}

VIEW = "socket";   // "socket" -> zoom the hub bore cross-section; "full" -> whole
if (VIEW == "socket")
    intersection() { scene(); translate([0, -7, 2.5]) cube([30, 16, 26], center = true); }
else
    scene();
