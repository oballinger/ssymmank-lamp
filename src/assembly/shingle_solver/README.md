# shingle_solver

Derives the **shingled** mushroom layout in `models/assembly/assembly.scad`:
**zero mushroom-mushroom intersection AND zero light leak** (no straight
line-of-sight from the centre escapes between caps). Intersections are measured
*exactly* on the real OpenSCAD solids (`intersection()` → non-empty STL = overlap);
light leak by ray-casting from the origin against the cap surfaces.

## The idea

The two goals fight: full angular coverage forces caps to overlap, and rigid
overlapping caps intersect. The resolution is **radial shingling** plus three
shape tweaks (all kept "pentagonal, slightly curved", stretched arms retained):

1. **Concentric caps** — `CURVE_RELAX=2.3` makes each cap a patch ~concentric
   with the lamp centre, so it is *radially thin* and slides past other shells'
   caps instead of doming into them.
2. **5 radial shells** (stems 70/84/98/112/126) assigned by a **proper
   5-colouring of the cap-overlap graph at the coverage scale** — so no two
   *touching* caps share a shell. Same-shell caps never overlap; cross-shell
   pairs are at different radii and shingle. (Colouring at a *sparse* scale was
   the original bug — it isn't proper once caps grow to cover.)
3. **Shallow funnel** (`DISH_DEPTH=26`) so an outer shell's funnel clears the
   next-inner shell's caps.
4. **Per-mushroom azimuth** — 5 mushrooms spun about their radial axis so their
   stretched arms reach into the square/triangle gaps (empty) instead of
   skewering a neighbour's stem. Stored in `theta_d26.json`.

Stem tips all seat at the same bore floor, so the **frame is unchanged**.

## Files

| file | what |
|---|---|
| `analyze.py` | mushroom geometry reconstruction + ray-cast light-leak (coverage) |
| `opt.py` | fast evaluator (KD-tree clearance, fibonacci-sphere leak) used by `color` |
| `color.py` | cap-overlap adjacency graph + backtracking k-colouring |
| `color3.py` | per-variant mushroom STL render + **OpenSCAD intersection oracle** + leak |
| `orient.py` | per-mushroom azimuth optimiser (greedy, oracle-driven) → `theta_d26.json` |
| `build.py` | **regenerates** `models/assembly/assembly.scad` + `_overlap_check.scad` |
| `theta_d26.json` | the solved per-mushroom azimuths (5 non-zero) |

## Run

```bash
# regenerate the assembly from the solved orientations
python3 src/assembly/shingle_solver/build.py

# re-solve the orientations from scratch (overwrites theta on disk if you wire it)
python3 src/assembly/shingle_solver/orient.py
```

Needs `numpy`, `scipy`, and OpenSCAD (set `$OPENSCAD` if not at the macOS
default `/Applications/OpenSCAD.app/...`). The leak metric (rays) is reliable; a
point-cloud nearest-distance metric is NOT (it can't see one shell poking
*through* another) — only the OpenSCAD `intersection()` oracle is trusted for
collisions.
