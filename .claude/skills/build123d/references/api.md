# build123d 0.13 API quick reference

Signatures below were checked against build123d 0.13.0 with `inspect.signature`.
Every object also accepts `mode=Mode.ADD` (builder mode) and most accept
`rotation=` and `align=`; they're omitted below unless they matter. For
anything not listed, run
`python -c "import build123d as bd, inspect; print(inspect.signature(bd.NAME))"`.

## Contents
- 3D objects
- 2D objects (sketch)
- 1D objects (lines and curves)
- Locations and placement
- Operations
- Selectors and ShapeList
- Shape methods and properties
- Import / export
- Enums

## 3D objects

All centred on the origin unless `align` says otherwise.

```text
Box(length, width, height, rotation=(0,0,0), align=(CENTER,CENTER,CENTER))   # length=X, width=Y, height=Z
Cylinder(radius, height, arc_size=360, ...)                                   # axis along Z
Cone(bottom_radius, top_radius, height, arc_size=360, ...)
Sphere(radius, arc_size1=-90, arc_size2=90, arc_size3=360, ...)
Torus(major_radius, minor_radius, minor_start_angle=0, minor_end_angle=360, major_angle=360, ...)
Wedge(xsize, ysize, zsize, xmin, zmin, xmax, zmax, ...)
Hole(radius, depth=None)                                     # mode=SUBTRACT; depth=None means through (builder only)
CounterBoreHole(radius, counter_bore_radius, counter_bore_depth, depth=None)
CounterSinkHole(radius, counter_sink_radius, depth=None, counter_sink_angle=82)
```

`Hole` and friends drill along -Z of the current workplane, from the
workplane down. In builder mode, put them in `Locations(top_face)` so they
start at the top. In algebra mode they need an explicit `depth`.

## 2D objects (sketch)

Built on local Plane.XY. Place with `Plane * Location * sketch`.

```text
Rectangle(width, height, rotation=0, align=(CENTER,CENTER))
RectangleRounded(width, height, radius, ...)
Circle(radius, arc_size=360, ...)
Ellipse(x_radius, y_radius, ...)
Polygon(*pts, rotation=0, align=(NONE,NONE))                 # closed automatically; NOT centred by default
RegularPolygon(radius, side_count, major_radius=True, ...)   # radius to corners unless major_radius=False
Trapezoid(width, height, left_side_angle, right_side_angle=None, ...)
Triangle(a=, b=, c=, A=, B=, C=)                            # any 3 of sides/angles
SlotCenterToCenter(center_separation, height, rotation=0)
SlotOverall(width, height, ...) / SlotCenterPoint(center, point, height) / SlotArc(arc, height)
Text(txt, font_size, font="Arial", font_path=None, font_style=FontStyle.REGULAR,
     text_align=(TextAlign.CENTER, TextAlign.CENTER), path=None, ...)
make_face(edges)            # closed Curve/wires -> Sketch
make_hull(edges)            # convex hull of edges -> Sketch
```

Sketch booleans work the same as parts: `Rectangle(10, 10) - Circle(2)`.

## 1D objects (lines and curves)

```text
Line(p1, p2)
Polyline(*pts, close=False)
ThreePointArc(p1, p2, p3)
CenterArc(center, radius, start_angle, arc_size)
RadiusArc(start_point, end_point, radius, short_sagitta=True)   # sign of radius picks the side
TangentArc(p1, p2, tangent=(x, y), tangent_from_first=True)
Spline(*pts, tangents=None, periodic=False)
Bezier(*cntl_pnts)
Helix(pitch, height, radius, center=(0,0,0), direction=(0,0,1), cone_angle=0, lefthand=False)
FilletPolyline(*pts, radius=r, close=False)   # radius is keyword-only after *pts
```

In `BuildLine`, `line.line` is the result; wrap in `make_face` (inside a
`BuildSketch`) to get a face. In algebra mode, `Line(...) + Line(...)` gives a
`Curve`; pass it to `make_face`, or as a `path` to `sweep`.

Edge/wire operators: `edge @ 0.5` position at half length, `edge % 0.5`
tangent, `edge ^ 0.5` a Location (for placing a profile at the start of a
sweep path: `path ^ 0`).

## Locations and placement

```text
Pos(x=0, y=0, z=0) / Pos(X=.., Y=.., Z=..)    # translation
Rot(x=0, y=0, z=0) / Rot(X=.., Y=.., Z=..)    # rotation in degrees
Location((x, y, z), (rx, ry, rz))             # both
Plane.XY / .XZ / .YZ / .YX / .ZX / .ZY / .front / .top / .right ...
Plane.XY.offset(d)        # shift along normal
Plane(face)               # plane on a planar face, normal pointing out
Plane(origin, x_dir, z_dir)
plane.reverse()           # flip normal
plane.rotated((rx, ry, rz), ordering=None)
Locations(*pts)                                             # points, Vertex, Location, Face, Plane
GridLocations(x_spacing, y_spacing, x_count, y_count, align=(CENTER,CENTER))
PolarLocations(radius, count, start_angle=0, angular_range=360, rotate=True, endpoint=False)
HexLocations(radius, x_count, y_count, major_radius=False, align=(CENTER,CENTER))
```

Plane normals: XY is +Z, **XZ is -Y**, YZ is +X.

Algebra placement:
- `Pos(1, 2, 3) * Rot(Z=45) * shape`: rotate about the origin, then move.
- `Plane.XZ * Pos(1, 2) * sketch`: the Pos is in the plane's own X/Y.
- `GridLocations(...) * shape` returns a `list` of shapes. `part - that_list`
  or `part + that_list` works. `GridLocations(...) * Pos(...)` is a TypeError;
  write `GridLocations(...) * (Pos(...) * shape)`.
- `loc1 * loc2` composes Locations.

Builder placement: `with Locations(...):` / `with GridLocations(...):` nest,
and every object created inside is placed at each location.

## Operations

In algebra mode, pass the object first and use the return value. In builder
mode, omit it to act on the builder's pending sketch or current part.

```text
extrude(to_extrude=None, amount=None, dir=None, until=None, target=None, both=False, taper=0.0)
revolve(profiles=None, axis=Axis.Z, revolution_arc=360.0)
loft(sections=None, ruled=False)                         # list of faces/sketches at different heights
sweep(sections=None, path=None, multisection=False, is_frenet=False, transition=Transition.TRANSFORMED)
thicken(to_thicken=None, amount=None, normal_override=None, both=False)
fillet(objects, radius)                                  # edges (3D) or vertices (2D)
chamfer(objects, length, length2=None, angle=None, reference=None)
offset(objects=None, amount=0, openings=None, kind=Kind.ARC, side=Side.BOTH, closed=True)
        # 3D: negative amount + openings=face(s) of the SAME object -> hollow shell
        # 2D: offset a sketch outline, kind=Kind.INTERSECTION keeps sharp corners
mirror(objects=None, about=Plane.XZ)
split(objects=None, bisect_by=Plane.XZ, keep=Keep.TOP)   # Keep.TOP / BOTTOM / BOTH
section(obj=None, section_by=Plane.XZ, height=0.0)       # 2D cross section Sketch
scale(objects=None, by=1, about=None)                    # by can be (sx, sy, sz)
project(objects=None, workplane=None, target=None)
draft(faces, neutral_plane, angle)
make_brake_formed(thickness, station_widths, line=None, side=Side.LEFT, kind=Kind.ARC)
```

`extrude(until=Until.NEXT)` / `Until.LAST` extrude up to the next/last face of
`target` (or the builder's part). `extrude(amount=..., mode=Mode.SUBTRACT)` in
a builder is a pocket.

## Selectors and ShapeList

`shape.vertices() / edges() / wires() / faces() / solids()`, each taking
`Select.ALL` (default), `Select.LAST` or `Select.NEW`. They return a
`ShapeList`:

```text
.sort_by(Axis.Z | SortBy.LENGTH/RADIUS/AREA/VOLUME/DISTANCE, reverse=False)
.group_by(Axis.Z | SortBy..., tol_digits=6)    -> list of ShapeLists
.filter_by(Axis.Z | Plane.XY | GeomType.CIRCLE | Convexity.CONCAVE | lambda s: ..., reverse=False)
.filter_by_position(Axis.Z, minimum, maximum, inclusive=(True, True))
.first / .last        # properties
operators:  > sort_by   < reverse sort_by   >> group_by()[-1]   << group_by()[0]   | filter_by
```

`filter_by(Axis.Z)` on edges keeps edges parallel to Z; on faces it keeps
faces whose **normal** is parallel to Z. `filter_by(Plane.XY)` keeps faces
parallel to the plane.

GeomType: LINE, CIRCLE, ELLIPSE, BSPLINE, BEZIER, PLANE, CYLINDER, CONE,
SPHERE, TORUS, REVOLUTION, EXTRUSION, OFFSET, OTHER.

## Shape methods and properties

```text
.volume  .area                      # properties
.is_valid                           # property, bool
.bounding_box() -> BoundBox         # .min .max .size .center()  (Vectors, .X .Y .Z)
.center(CenterOf.MASS | BOUNDING_BOX | GEOMETRY)
.moved(loc) / .located(loc)         # copies
.move(loc) / .locate(loc)           # in place
.rotate(axis, angle) / .translate(vec) / .mirror(plane) / .scale(factor)
.distance_to(other)
.fuse(*others) / .cut(*others) / .intersect(*others)
.clean() / .fix()
.show_topology()
face.normal_at(), face.center(), face.inner_wires(), face.outer_wire()
edge.length, edge.radius (circles), edge.position_at(t), edge.tangent_at(t)
```

`build123d.Shape` exists but isn't exported by `from build123d import *`.

## Import / export

```text
export_step(shape, path, unit=Unit.MM)
export_stl(shape, path, tolerance=0.001, angular_tolerance=0.1, ascii_format=False)
export_brep(shape, path)
export_gltf(shape, path, ...)
export_obj(shape, path, ...)
Mesher(): .add_shape(shape, ...), .write("x.3mf" | "x.stl"), .read(path)   # 3MF lives here
import_step(path) -> Compound, import_brep(path), import_svg(path), import_dxf(path)
import_stl(path) -> Face   # a mesh surface, not a solid: can't be used in booleans
ExportSVG(...) / ExportDXF(...): .add_layer(name, ...), .add_shape(shapes, layer=...), .write(path)
shape.project_to_viewport(viewport_origin) -> (visible_edges, hidden_edges)
pack(objects, padding, align_z=False)       # lay parts out side by side for a print plate
```

## Enums

```text
Align.MIN / CENTER / MAX / NONE
Mode.ADD / SUBTRACT / INTERSECT / REPLACE / PRIVATE
Keep.TOP / BOTTOM / BOTH / ALL / INSIDE / OUTSIDE
Kind.ARC / INTERSECTION / TANGENT
Until.NEXT / LAST / PREVIOUS / FIRST
Transition.RIGHT / ROUND / TRANSFORMED
Select.ALL / LAST / NEW
Side.LEFT / RIGHT / BOTH
```
