"""Generate a battery holder bin and export it, or preview it in OCP CAD Viewer."""

import argparse

import build123d as bd

from .batteries import BATTERIES, CylindricalBattery
from .holder import make_holder

CYLINDRICAL = {b.__name__: b for b in BATTERIES if issubclass(b, CylindricalBattery)}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="gridfinity-battery-holder", description=__doc__
    )
    parser.add_argument("battery", choices=CYLINDRICAL)
    parser.add_argument("count", type=int, help="minimum number of batteries to hold")
    parser.add_argument("--extend", choices=["y", "z"], default="y")
    parser.add_argument("--packing", choices=["auto", "square", "hex"], default="auto")
    parser.add_argument("--grid-y", type=int, default=2, help="used with --extend z")
    parser.add_argument(
        "--height-units", type=int, default=7, help="used with --extend y"
    )
    parser.add_argument(
        "--cell-size",
        type=float,
        default=21,
        help="21 for half-size cells, 42 for full",
    )
    parser.add_argument(
        "--clearance", type=float, default=0.3, help="per side, around each battery"
    )
    parser.add_argument(
        "--end-clearance", type=float, default=1.0, help="at each end of the battery"
    )
    parser.add_argument("--min-wall", type=float, default=3.0)
    parser.add_argument(
        "--overhang",
        action="store_true",
        help="let the top row stick out above the rim, up to half a battery",
    )
    parser.add_argument("-o", "--output", help="an .stl or .step path")
    parser.add_argument(
        "--show", action="store_true", help="send the preview to OCP CAD Viewer"
    )
    parser.add_argument(
        "--section", action="store_true", help="with --show, cut the preview in half"
    )
    args = parser.parse_args(argv)

    try:
        holder = make_holder(
            CYLINDRICAL[args.battery],
            args.count,
            extend=args.extend,
            packing=args.packing,
            grid_y=args.grid_y,
            height_units=args.height_units,
            cell_size=(args.cell_size, args.cell_size),
            clearance=args.clearance,
            end_clearance=args.end_clearance,
            min_wall=args.min_wall,
            overhang=args.overhang,
        )
    except ValueError as e:
        parser.error(str(e))
    print(holder)

    if args.output:
        if args.output.lower().endswith((".step", ".stp")):
            bd.export_step(holder.bin, args.output)
        else:
            bd.export_stl(holder.bin, args.output)
        print(f"wrote {args.output}")
    if args.show:
        try:
            from ocp_vscode import show
        except ImportError:
            parser.error("--show needs ocp_vscode: uv add --dev ocp-vscode")

        show(holder.cross_section() if args.section else holder.preview())


if __name__ == "__main__":
    main()
