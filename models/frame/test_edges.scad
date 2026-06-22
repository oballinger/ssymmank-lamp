// Ssymmank lamp -- TWO CONNECTORS for a test print (check the keyed joint on a
// real star tile).  Both laid flat on the bed, spaced apart.
// Modules/params come from star.scad, so edits there propagate here.

include <star.scad>
SHOW_STAR = false;   // library mode: don't draw the lone star tile

for (i = [0, 1]) translate([0, i * 13, 0]) rotate([90, 0, 0]) connector();
