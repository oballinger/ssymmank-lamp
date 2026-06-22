// Ssymmank lamp -- MATE TEST: two neighbouring star tiles and the single
// connector that bridges them, to verify the keyed joint seats.
// Modules/params come from star.scad, so edits there propagate here.

include <star.scad>
SHOW_STAR = false;   // library mode: don't draw the lone star tile

color("#4F86C6") multmatrix([[0.16246, -0.50000, -0.85065, -85.06508], [-0.26287, 0.80902, -0.52573, -52.57311], [0.95106, 0.30902, 0.00000, 0.00000], [0.00000, 0.00000, 0.00000, 1.00000]]) star();
color("#C64F4F") multmatrix([[0.16246, 0.50000, -0.85065, -85.06508], [0.26287, 0.80902, 0.52573, 52.57311], [0.95106, -0.30902, 0.00000, 0.00000], [0.00000, 0.00000, 0.00000, 1.00000]]) star();
color("#DDAA33") multmatrix([[0.00000, 0.22975, -0.97325, -94.85360], [1.00000, 0.00000, 0.00000, 0.00000], [0.00000, -0.97325, -0.22975, -22.39190], [0.00000, 0.00000, 0.00000, 1.00000]]) connector();
