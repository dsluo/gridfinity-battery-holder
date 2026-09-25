"""Print the numbers that show whether a build123d model is what you meant.

Usage:
    python inspect_shape.py path/to/model.py [name ...]

Runs the module, then reports each named module-level shape (or every
module-level Shape / builder when no names are given): type, bounding box,
size, volume, area, solid/face/edge counts and validity. Builders
(BuildPart etc.) are reported through their .part / .sketch / .line.

Run it with the project's interpreter (e.g. `uv run python ...`) so it sees
the same build123d version.
"""

import runpy
import sys
from pathlib import Path

import build123d as bd


def unwrap(obj):
    for attr, kind in (("part", bd.BuildPart), ("sketch", bd.BuildSketch), ("line", bd.BuildLine)):
        if isinstance(obj, kind):
            return getattr(obj, attr)
    return obj


def fmt(v: bd.Vector) -> str:
    return f"({v.X:.3f}, {v.Y:.3f}, {v.Z:.3f})"


def report(name: str, obj) -> None:
    shape = unwrap(obj)
    print(f"== {name}: {type(obj).__name__}" + (f" -> {type(shape).__name__}" if shape is not obj else ""))
    if not isinstance(shape, bd.Shape) or shape.wrapped is None:
        print("   (empty or not a shape)")
        return
    bb = shape.bounding_box()
    print(f"   bbox min {fmt(bb.min)}  max {fmt(bb.max)}")
    print(f"   size     {fmt(bb.size)}")
    print(f"   volume   {shape.volume:.4f}   area {shape.area:.4f}")
    print(
        f"   solids {len(shape.solids())}  faces {len(shape.faces())}  "
        f"edges {len(shape.edges())}  valid {shape.is_valid}"
    )


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = Path(sys.argv[1])
    sys.path.insert(0, str(path.parent.resolve()))
    namespace = runpy.run_path(str(path), run_name="__inspect__")
    names = sys.argv[2:]
    if names:
        for n in names:
            if n not in namespace:
                sys.exit(f"{n!r} not found in {path}")
            report(n, namespace[n])
        return
    found = False
    for n, obj in namespace.items():
        if n.startswith("_"):
            continue
        if isinstance(obj, (bd.Shape, bd.BuildPart, bd.BuildSketch, bd.BuildLine)):
            report(n, obj)
            found = True
    if not found:
        print("no module-level shapes found; pass a variable name or assign the result")


if __name__ == "__main__":
    main()
