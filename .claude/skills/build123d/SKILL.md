---
name: build123d
description: Write, fix and verify parametric CAD models in Python with build123d (the OpenCascade-based successor to CadQuery). Use this skill whenever code imports build123d (`import build123d as bd`, `from build123d import *`), or the user wants to model a 3D part, sketch, enclosure, bracket, bin, holder, fixture or other solid in Python, export STL/STEP/3MF for 3D printing or CNC, fillet/chamfer edges, select faces/edges, cut holes, sweep/loft/revolve profiles, or debug a build123d error like "No depth provided", a boolean that silently did nothing, or a part landing in the wrong place. Also use it when the user mentions CadQuery-style modeling but the project already uses build123d.
---

# build123d

build123d is a Python CAD library on top of OpenCascade (OCCT). Parts are exact
B-rep solids, built from primitives, 2D sketches and operations. This skill is
pinned to **build123d 0.13**. The API has changed between minor versions, and
model training data is heavy with CadQuery and older build123d, so the single
biggest source of bugs is confidently writing an API that does not exist here.

## Workflow

1. **Check the installed version and the project's style.** Run
   `python -c "import build123d; print(build123d.__version__)"` in the project's
   environment (`uv run python ...` if there is a `uv.lock`). Read a nearby file
   to see whether the project uses `import build123d as bd` or
   `from build123d import *`, and algebra or builder mode. Match it.
2. **Sketch the dimensions first.** Decide where the origin is and which way is
   up before writing code. Most bugs are a part sitting 5 mm off because a
   primitive was centred when you assumed it sat on the floor.
3. **Write the model**, parameterized: named variables for every dimension,
   derived dimensions computed from them, no magic numbers inside expressions.
4. **Run it and check the geometry numerically** (see "Verify every model"
   below). A script that runs without an exception is not a correct model.
5. **Export** only after the checks pass.

When unsure of a signature, ask the installed library rather than guessing:

```bash
python -c "import build123d as bd, inspect; print(inspect.signature(bd.extrude))"
python -c "import build123d as bd; help(bd.CounterBoreHole)"
```

The installed package source (`site-packages/build123d/`) and the docs at
https://build123d.readthedocs.io are the ground truth. `references/api.md` has
the verified 0.13 signatures of the common objects and operations.

## Two modes: algebra and builder

Both produce the same `Part`/`Sketch`/`Curve` objects and can be mixed.

**Algebra mode** (explicit, functional; good default for library code and tests):

```python
import build123d as bd

plate = bd.Box(80, 60, 10, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
plate -= bd.GridLocations(60, 40, 2, 2) * bd.Cylinder(3, 30)   # 4 through holes
plate = bd.fillet(plate.edges().filter_by(bd.Axis.Z), radius=5)
# volume: 80*60*10 - 4*pi*3^2*10 - 4*(4-pi)*5^2*10 = 46654
```

- `+` fuse, `-` cut, `&` intersect. `*` places: `Plane * Location * shape`.
  `*` binds tighter than `+`/`-`, so no brackets are needed.
- Operations (`extrude`, `fillet`, `revolve`, `offset`, ...) are free functions
  that take the shape and **return a new one**. Nothing is modified in place,
  so `bd.fillet(part.edges(), 1)` on its own line does nothing. Assign it.
- `Locations`-style objects work here too: `bd.GridLocations(...) * shape`
  gives a **list** of placed copies, and `part - [list of shapes]` cuts them
  all. A `GridLocations` can't be multiplied by a `Pos`/`Rot`, so place the
  shape first and bracket it: `bd.GridLocations(...) * (bd.Pos(Z=5) * shape)`.

**Builder mode** (context managers; the docs' main style):

```python
from build123d import *

with BuildPart() as plate:
    Box(80, 60, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    with Locations(plate.faces().sort_by(Axis.Z)[-1]):   # sketch on the top face
        with GridLocations(60, 40, 2, 2):
            Hole(radius=3)                               # cuts through by default
    fillet(plate.edges().filter_by(Axis.Z), radius=5)
result = plate.part
```

- Objects created inside a builder are added automatically. Pass
  `mode=Mode.SUBTRACT` (or `INTERSECT`, `REPLACE`, `PRIVATE`) to change that.
  `Hole`, `CounterBoreHole` and `CounterSinkHole` subtract by default.
- The builder object (`plate`) is **not** a shape. Use `plate.part`,
  `sketch.sketch`, `line.line` to get geometry out, especially before using
  it with algebra operators.
- Nested builders do not inherit placements; each builds on its own local
  `Plane.XY` and is placed when it exits. `BuildSketch(Plane.XZ)` draws on a
  local XY, so selectors inside the sketch (e.g. `sort_by(Axis.Z)`) see flat
  2D geometry, not the final placement.
- Operations with no object argument act on the builder's pending geometry,
  e.g. `extrude(amount=5)` after a `BuildSketch` block.

Pick algebra mode unless the project already uses builder mode or the user asks
for it. It is easier to test, compose in functions, and reason about.

## Coordinates, alignment and placement

- **Primitives are centred on the origin by default** in all three axes.
  `Box(10, 20, 30)` spans Z from -15 to 15. Use
  `align=(Align.CENTER, Align.CENTER, Align.MIN)` to sit it on Z=0, or
  `Align.MIN` for all axes to put the corner at the origin.
- `Cylinder(radius, height)` and `Circle(radius)`, `Hole(radius)`: **radius,
  not diameter**. Convert with `d / 2` explicitly.
- `Pos(x, y, z)` / `Pos(Z=5)` translate; `Rot(X=90)` rotates (degrees);
  `Location((x, y, z), (rx, ry, rz))` is both. Compose right to left:
  `Pos(...) * Rot(...) * shape` rotates about the origin first, then moves.
- `Plane.XY`, `Plane.XZ`, `Plane.YZ`, and `Plane.XZ` has its normal along
  **-Y**. So `extrude(Plane.XZ * Rectangle(4, 4), 3)` grows toward -Y (Y from
  -3 to 0). Pass `dir=` or a negative amount, or use `Plane.XZ.reverse()`, if you
  need +Y. Planes can be offset: `Plane.XY.offset(10)`, or built from a face:
  `Plane(face)`.
- `shape.moved(loc)` returns a moved copy; `shape.move(loc)` mutates.
  `shape.rotate(Axis.Z, 90)` rotates about an axis.
- Revolve profiles must sit on one side of the axis. Draw them on a plane that
  contains the axis, e.g. `revolve(Plane.XZ * Pos(5, 0) * Rectangle(2, 4), Axis.Z)`.

## Selecting faces and edges

Selectors replace clicking. They return a `ShapeList` (a `list` subclass):

```python
part.faces().sort_by(Axis.Z)[-1]          # top face       (same as (part.faces() > Axis.Z)[-1])
part.faces().sort_by(Axis.Z)[0]           # bottom face
part.edges().filter_by(Axis.Z)            # edges parallel to Z (vertical edges)
part.faces().filter_by(Plane.XY)          # faces parallel to XY
part.edges().group_by(Axis.Z)[-1]         # all edges at the highest Z level
part.edges().filter_by(GeomType.CIRCLE)   # circular edges (holes, bosses)
part.faces().filter_by(GeomType.CYLINDER)
part.edges().filter_by_position(Axis.Z, 0, 5)
part.faces().filter_by(lambda f: f.inner_wires())   # faces with holes
part.edges(Select.LAST)                   # edges from the last operation
part.edges(Select.NEW)                    # edges created by the last operation (e.g. a cut's rim)
```

- `sort_by(...)[-1]` picks one item even when several share the extreme value.
  When the top has several coplanar faces or edges, use `group_by(...)[-1]`.
- Select from a face down when it's easier: `top.edges().filter_by(GeomType.CIRCLE)`.
- In builder mode, call selectors on the builder (`plate.edges()`), and inside a
  `BuildSketch` they return the sketch's local 2D geometry.
- `offset(part, amount=-2, openings=face)` needs `face` to come from **that
  same** `part` object. A face from another `Box(...)` call, even an identical
  one, is silently ignored and you get a shrunken solid instead of a shell.

## Verify every model

Run the model and print numbers that would be wrong if the model were wrong:

```python
bb = part.bounding_box()
print(bb.min, bb.max, bb.size)       # where it is, and how big
print(part.volume)                   # compare against a hand estimate
print(len(part.solids()), part.is_valid)
```

- **Bounding box** catches alignment and sign errors (the part is centred, not
  on the floor; the XZ extrusion went -Y).
- **Volume** catches booleans that did nothing (a cutter that misses the part,
  a cutter placed at the wrong height, a `fillet` result that was never
  assigned). Work out the expected volume by hand, at least roughly.
- **Solid count** catches features that don't touch: fusing two
  non-overlapping shapes gives a `Part` with 2 solids, not an error. A
  printable part usually has exactly 1.
- `is_valid` is a property (not a method). `True` is necessary, not sufficient.

`scripts/inspect_shape.py` prints all of this for a shape in a module:

```bash
python .claude/skills/build123d/scripts/inspect_shape.py path/to/model.py [variable_name]
```

With no variable name it reports every module-level shape. For projects with a
test suite, turn these checks into pytest assertions (volume within a tolerance
of the hand calculation, bounding box size, one solid).

For visual checks, `ocp_vscode` (`from ocp_vscode import show; show(part)`)
displays in the OCP CAD Viewer VS Code extension. Don't rely on it in
automated runs: it needs the viewer to be open. A cross-section is a cheap
way to inspect internal features:
`bd.split(part, bisect_by=bd.Plane.YZ, keep=bd.Keep.BOTTOM)` or
`bd.section(part, bd.Plane.XZ)`.

## Exporting

```python
bd.export_stl(part, "out.stl")                       # tolerance=0.001, angular_tolerance=0.1 by default
bd.export_step(part, "out.step")
mesher = bd.Mesher(); mesher.add_shape(part); mesher.write("out.3mf")   # 3MF (and STL) via Mesher
```

There is no `export_3mf`. STEP keeps exact geometry and is the right format to
hand to another CAD tool; STL/3MF are meshes for slicers. Export functions take
a `Shape` (a `Part` is one); in builder mode pass `builder.part`.

## Common failures and fixes

| Symptom | Likely cause |
| --- | --- |
| `AttributeError` on `Workplane`, `.box()`, `.faces(">Z")`, `.cutBlind` | That's CadQuery. build123d has no string selectors or method chaining on a workplane. Translate: `.faces(">Z")` becomes `.faces().sort_by(Axis.Z)[-1]`. |
| `ValueError: No depth provided` from `Hole` | In algebra mode `Hole` has no builder part to measure; pass `depth=`, or cut a `Cylinder` instead. |
| Fillet or chamfer raises `StdFail_NotDone` / "failed" | Radius is too big for an adjacent face or edge, or edges meet at a tangent. Reduce the radius, fillet fewer edges at a time, or do the rounding in 2D (`fillet` on sketch vertices, `RectangleRounded`) before extruding. Fillet late in the design. |
| Boolean runs but volume is unchanged | Cutter doesn't overlap the part: check its bounding box. Often a centred primitive where an aligned one was intended. |
| Result has more solids than expected | Fused pieces only touch or are separated; overlap them slightly (0.01 mm) or check positions. |
| Sweep/loft fails | Profile not perpendicular to the path start, self-intersecting path, or incompatible sections. Try `Transition.RIGHT`/`ROUND`, split the sweep, or use `loft` instead. |
| `NameError: Shape` after `from build123d import *` | `Shape` isn't in `__all__`. Use `build123d.Shape` or `from build123d.topology import Shape`. |
| `Text` fails | Font not found. Pass `font_path=` to a .ttf that exists. |

## Style

- Keep dimensions as named parameters (function arguments or a dataclass) so
  the part regenerates when they change.
- Prefer 2D then 3D: build profiles as sketches (with 2D fillets) and
  extrude/revolve them. 2D operations are faster and fail far less often.
- Do fillets and chamfers last; they turn simple edges into complex faces
  that later operations struggle with.
- For 3D printing, model the fit clearances explicitly as parameters
  (typically 0.1 to 0.3 mm per side for FDM) rather than baking them into
  nominal dimensions.

See `references/api.md` for signatures of the common objects and operations.
