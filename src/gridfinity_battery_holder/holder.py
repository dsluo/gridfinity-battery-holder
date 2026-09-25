"""Gridfinity bins that store cylindrical batteries lying on their side.

Batteries lie along X in a single open-top pocket, stacked in rows up Z. One of
Y or Z is fixed; the other grows until at least `count` batteries fit, and the
pocket then fills whatever room rounding up to whole cells and height units
leaves. X is always the minimum that fits. With `overhang`, the top row may
stick out above the rim as long as each battery's centre is still inside.
"""

import itertools
import math
from dataclasses import dataclass
from typing import Literal

import build123d as bd
import gridfinity as gf

from .batteries import CylindricalBattery

Packing = Literal["square", "hex"]


@dataclass(frozen=True)
class Layout:
    packing: Packing
    # (y, z) of each battery's axis, bottom row first. y is from the pocket's
    # centre line and z from the pocket floor.
    centres: list[tuple[float, float]]
    pocket_width: float

    @property
    def rows(self) -> list[int]:
        """Number of batteries in each row, bottom first."""
        heights = sorted({z for _, z in self.centres})
        return [sum(1 for _, z in self.centres if z == h) for h in heights]


def layout(packing: Packing, width: float, depth: float, pitch: float) -> Layout:
    """Fit as many batteries as possible into a pocket `width` by `depth`.

    `pitch` is the diameter plus clearance on both sides. Square rows stack
    straight up. Hex rows alternate between `n` batteries and `m` batteries
    shifted half a pitch over, each nesting in the row below. If the pocket is
    too narrow for a shifted row, hex fits nothing.
    """
    n = math.floor(width / pitch)
    if n < 1 or depth < pitch:
        return Layout(packing, [], 0.0)
    if packing == "square":
        rise = pitch
        rows = [(0.0, n)] * math.floor(depth / pitch)
    else:
        rise = pitch * math.sqrt(3) / 2
        m = math.floor(width / pitch - 0.5)
        if m < 1:
            return Layout(packing, [], 0.0)
        n_rows = 1 + math.floor((depth - pitch) / rise)
        rows = [(0.0, n) if r % 2 == 0 else (pitch / 2, m) for r in range(n_rows)]
    pocket_width = max(start + k * pitch for start, k in rows)
    centres = [
        (start + (i + 0.5) * pitch - pocket_width / 2, pitch / 2 + r * rise)
        for r, (start, k) in enumerate(rows)
        for i in range(k)
    ]
    return Layout(packing, centres, pocket_width)


@dataclass(frozen=True)
class BatteryHolder:
    bin: bd.Part
    battery: type[CylindricalBattery]
    count: int
    layout: Layout
    grid_x: int
    grid_y: int
    cell_size: tuple[float, float]
    height: float
    floor: float
    overhang: bool
    min_wall: float
    pocket_length: float

    @property
    def capacity(self) -> int:
        return len(self.layout.centres)

    def batteries(self) -> list[CylindricalBattery]:
        """A battery in every slot, positioned to match the bin."""
        return [
            self.battery(rotation=(0, 90, 0), align=bd.Align.CENTER).moved(
                bd.Location((0, y, self.floor + z))
            )
            for y, z in self.layout.centres
        ]

    def preview(self) -> bd.Compound:
        return bd.Compound([self.bin, *self.batteries()])

    def cross_section(self) -> bd.Shape:
        """The preview cut in half across the battery axis."""
        return bd.split(self.preview(), bisect_by=bd.Plane.YZ, keep=bd.Keep.BOTTOM)

    def __str__(self) -> str:
        return (
            f"{self.capacity} x {self.battery.__name__} (asked for {self.count}), "
            f"{self.layout.packing} packed in rows of "
            f"{'/'.join(map(str, self.layout.rows))}: grid {self.grid_x}x{self.grid_y} "
            f"at {self.cell_size[0]} mm, {self.height} mm tall"
        )


def make_holder(
    battery: type[CylindricalBattery],
    count: int,
    *,
    extend: Literal["y", "z"] = "y",
    packing: Packing | Literal["auto"] = "auto",
    grid_y: int = 2,
    height_units: int = 7,
    cell_size: tuple[float, float] = (21, 21),
    height_unit: float = 7,
    clearance: float = 0.3,
    end_clearance: float = 1.0,
    min_wall: float = 3.0,
    floor: float = 7,
    overhang: bool = False,
) -> BatteryHolder:
    """Build the smallest bin that holds at least `count` batteries.

    extend: "y" keeps `height_units` and makes the bin wider; "z" keeps
        `grid_y` and makes it taller. The other of the two is ignored.
    packing: "square" stacks rows straight up; "hex" nests each row in the one
        below; "auto" uses whichever needs the smaller bin, then whichever
        holds more (square on a tie).
    cell_size: (21, 21) for half-size cells, (42, 42) for full-size.
    clearance: per side, around each battery.
    end_clearance: at each end, along the battery's length. Real cells often
        run a little over their nominal length.
    min_wall: walls only get thicker than this when rounding up to whole cells
        leaves spare room. Under ~1.95 mm, the sharp pocket corners get too
        close to the bin's 3.75 mm corner fillet.
    floor: keeps the pocket out of the base.
    overhang: let the top row stick out above the rim, up to half a battery,
        so the walls still hold each battery at its widest point. Bins with
        overhanging batteries can't have another bin stacked on them.
    """
    if not (isinstance(battery, type) and issubclass(battery, CylindricalBattery)):
        raise TypeError(f"only cylindrical batteries are supported, not {battery!r}")
    if count < 1:
        raise ValueError(f"count must be at least 1, not {count}")
    if packing not in ("square", "hex", "auto"):
        raise ValueError(f"packing must be 'square', 'hex' or 'auto', not {packing!r}")

    pitch = battery.diameter + 2 * clearance
    pocket_x = battery.length + 2 * end_clearance
    grid_x = math.ceil((pocket_x + 2 * min_wall + 0.5) / cell_size[0])
    candidates: list[Packing] = ["square", "hex"] if packing == "auto" else [packing]
    headroom = pitch / 2 if overhang else 0.0

    def best_layout(grid_y: int, height: float) -> Layout:
        width = grid_y * cell_size[1] - 0.5 - 2 * min_wall
        return max(
            (layout(p, width, height - floor + headroom, pitch) for p in candidates),
            key=lambda option: len(option.centres),
        )

    if extend == "y":
        height = height_units * height_unit
        if not best_layout(1000, height).centres:
            raise ValueError(
                f"height_units={height_units} is too short for {battery.__name__}"
            )
        grid_y = next(
            g
            for g in itertools.count(1)
            if len(best_layout(g, height).centres) >= count
        )
    elif extend == "z":
        if not best_layout(grid_y, 1000).centres:
            raise ValueError(f"grid_y={grid_y} is too narrow for {battery.__name__}")
        height_units = next(
            h
            for h in itertools.count(1)
            if len(best_layout(grid_y, h * height_unit).centres) >= count
        )
        height = height_units * height_unit
    else:
        raise ValueError(f"extend must be 'y' or 'z', not {extend!r}")

    chosen = best_layout(grid_y, height)
    pocket = bd.Box(
        pocket_x,
        chosen.pocket_width,
        height - floor,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
    )
    grid = gf.Grid.filled(grid_x, grid_y, cell_size=cell_size)
    part = gf.Bin(grid=grid, height=height, compartment=pocket, stacking_lip=None)
    return BatteryHolder(
        bin=part,
        battery=battery,
        count=count,
        layout=chosen,
        grid_x=grid_x,
        grid_y=grid_y,
        cell_size=cell_size,
        height=height,
        floor=floor,
        overhang=overhang,
        min_wall=min_wall,
        pocket_length=pocket_x,
    )
