# Ssymmank lamp

Geometry mockup of the Günter Ssymmank Philharmonie lamp.

The lamp is a **spherical tessellation of regular pentagons, squares and
triangles** — i.e. the **rhombicosidodecahedron** (an Archimedean solid):

| | count |
|---|---|
| pentagons | 12 |
| squares | 30 |
| triangles | 20 |
| vertices | 60 |
| edges | 120 |
| faces | 62 |

Vertex configuration is `3.4.5.4` (triangle, square, pentagon, square meet at
every vertex).

Source / reference exhibition:
https://blog.sbb.berlin/darunter-sieht-man-gut-aus-ausstellung-zu-den-leuchten-guenter-ssymmanks-eroeffnet/

## Files

| file | what |
|---|---|
| `geometry.py` | single source of truth — vertices, edges, faces of the solid |
| `mockup.py` | renders `mockup_faces.png` and `mockup_frame.png` |
| `make_scad.py` | emits `lamp_frame.scad` with coordinates baked in |
| `lamp_frame.scad` | OpenSCAD model of the frame (vertices + edges) |
| `mockup_faces.png` | coloured pentagon / square / triangle tessellation |
| `mockup_frame.png` | plain wireframe: 60 vertices + 120 edges |

## Usage

```bash
uv run python mockup.py      # regenerate the PNG mockups
uv run python make_scad.py   # regenerate lamp_frame.scad
```

Open `lamp_frame.scad` in OpenSCAD and press **F5** (preview) or **F6**
(render). Strut radius, node radius and overall diameter are parameters at the
top of the file.
