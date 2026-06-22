// Ssymmank lamp -- CONNECTOR bar (one of 60, all identical).
// Flat, shallow-V fin with a keyed tenon at each end; plugs into two neighbouring
// tiles' corner mortises.  Lay flat (fin in the XY plane) to print.
// Modules/params come from star.scad, so edits there propagate here.

include <star.scad>
SHOW_STAR = false;   // library mode: don't draw the lone star tile

rotate([90, 0, 0]) connector();   // fin laid flat on the bed
