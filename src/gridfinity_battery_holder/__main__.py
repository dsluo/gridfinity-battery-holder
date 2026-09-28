"""Generate a battery holder bin and export it, or preview it in OCP CAD Viewer.

Button cells stand on edge in a tray of slots; everything else lies on its side
in a holder. Use --style to pick one or the other.
"""

import argparse

import build123d as bd

from .batteries import BATTERIES, CylindricalBattery
from .holder import make_holder
from .tray import make_tray

CYLINDRICAL = {b.__name__: b for b in BATTERIES if issubclass(b, CylindricalBattery)}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="gridfinity-battery-holder", description=__doc__
    )
    parser.add_argument("battery", choices=CYLINDRICAL)
    parser.add_argument("count", type=int, help="minimum number of batteries to hold")
    parser.add_argument(
        "--style",
        choices=["auto", "holder", "tray"],
        default="auto",
        help="auto makes a tray for button cells and a holder for the rest",
    )
    parser.add_argument("--extend", choices=["y", "z"], default="y", help="holder")
    parser.add_argument(
        "--packing", choices=["auto", "square", "hex"], default="auto", help="holder"
    )
    parser.add_argument(
        "--grid-y", type=int, default=2, help="holder, used with --extend z"
    )
    parser.add_argument(
        "--height-units", type=int, default=7, help="holder, used with --extend y"
    )
    parser.add_argument(
        "--grid-x", type=int, help="tray width in cells; picked for you if left out"
    )
    parser.add_argument(
        "--seat",
        type=float,
        default=0.5,
        help="tray, how much of each cell's diameter sits down in its slot",
    )
    parser.add_argument(
        "--thickness-clearance",
        type=float,
        default=0.15,
        help="tray, at each face of a cell",
    )
    parser.add_argument(
        "--no-stagger",
        dest="stagger",
        action="store_false",
        help="tray, straight rows instead of bricklike",
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
        "--end-clearance",
        type=float,
        default=1.0,
        help="holder, at each end of the battery",
    )
    parser.add_argument(
        "--min-wall", type=float, help="defaults to 3 for holders and 2 for trays"
    )
    parser.add_argument(
        "--overhang",
        action="store_true",
        help="holder, let the top row stick out above the rim, up to half a battery",
    )
    parser.add_argument("-o", "--output", help="an .stl or .step path")
    parser.add_argument(
        "--show", action="store_true", help="send the preview to OCP CAD Viewer"
    )
    parser.add_argument(
        "--section", action="store_true", help="with --show, cut the preview in half"
    )
    args = parser.parse_args(argv)

    battery = CYLINDRICAL[args.battery]
    tray = args.style == "tray" or (args.style == "auto" and battery.is_button_cell)
    shared = dict(
        cell_size=(args.cell_size, args.cell_size),
        clearance=args.clearance,
    )
    if args.min_wall is not None:
        shared["min_wall"] = args.min_wall
    try:
        if tray:
            holder = make_tray(
                battery,
                args.count,
                grid_x=args.grid_x,
                seat=args.seat,
                thickness_clearance=args.thickness_clearance,
                stagger=args.stagger,
                **shared,
            )
        else:
            holder = make_holder(
                battery,
                args.count,
                extend=args.extend,
                packing=args.packing,
                grid_y=args.grid_y,
                height_units=args.height_units,
                end_clearance=args.end_clearance,
                overhang=args.overhang,
                **shared,
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
