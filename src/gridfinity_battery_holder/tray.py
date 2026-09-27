"""Gridfinity trays that store button cells on edge, like a roll of coins.

Cells stand on edge face to face along X, each in its own slot. A slot is
round at the bottom to match the cell and holds its lower `seat` fraction;
thin dividers separate neighbouring slots. With `stagger`, the slots are laid
like bricks: each is shifted half a slot along Y from the ones beside it, so
the top of every cell has only the low shoulders of its neighbours beside it,
leaving room for fingers. The top of the bin is the top of the dividers, with
no rim around the cells, so the rest of each cell sticks up above the bin to be
pinched out. Bins can't be stacked on top of a tray.

The grid is the one with the fewest cells that fits at least `count`, then the
squarest, or with `grid_x`, the shortest along Y at that width. Rounding up to
whole grid cells fills in extra slots, and rounding up to whole height units
goes into the floor.
"""

import itertools
import math
from dataclasses import dataclass

import build123d as bd
import gridfinity as gf

from .batteries import CylindricalBattery


@dataclass(frozen=True)
class BatteryTray:
    bin: bd.Part
    battery: type[CylindricalBattery]
    count: int
    # Positions along X, and along Y, which are half a slot apart when staggered
    columns: int
    rows: int
    stagger: bool
    grid_x: int
    grid_y: int
    cell_size: tuple[float, float]
    height: float
    # Along X, the cell's thickness plus clearance, and across the slot in Y,
    # its diameter plus clearance.
    slot_width: float
    slot_diameter: float
    divider: float
    # Of the slots' bottoms, down from the top of the bin
    slot_depth: float
    min_wall: float

    @property
    def capacity(self) -> int:
        return len(self.slots)

    @property
    def slots(self) -> list[tuple[float, float]]:
        """(x, y) of each slot's centre, row by row from the lowest y."""
        return _slots(
            self.columns,
            self.rows,
            self.stagger,
            self.slot_width + self.divider,
            self.slot_diameter + self.divider,
        )

    def batteries(self) -> list[CylindricalBattery]:
        """A cell in every slot, centred in it."""
        z = self.height - self.slot_depth + self.slot_diameter / 2
        return [
            self.battery(rotation=(0, 90, 0), align=bd.Align.CENTER).moved(
                bd.Location((x, y, z))
            )
            for x, y in self.slots
        ]

    def preview(self) -> bd.Compound:
        return bd.Compound([self.bin, *self.batteries()])

    def cross_section(self) -> bd.Compound:
        """The preview cut along the middle of the last row."""
        y = self.slots[-1][1]
        plane = bd.Plane(origin=(0, y, 0), z_dir=(0, 1, 0))
        return bd.split(self.preview().solids(), bisect_by=plane, keep=bd.Keep.BOTTOM)

    def __str__(self) -> str:
        across = len({x for x, _ in self.slots})
        deep = len({y for _, y in self.slots})
        pattern = "staggered" if self.stagger else "in rows"
        return (
            f"{self.capacity} x {self.battery.__name__} (asked for {self.count}), "
            f"{pattern} {across} across and {deep} deep: "
            f"grid {self.grid_x}x{self.grid_y} "
            f"at {self.cell_size[0]} mm, {self.height} mm tall"
        )


def _slots(
    columns: int, rows: int, stagger: bool, pitch_x: float, pitch_y: float
) -> list[tuple[float, float]]:
    """Slot centres, centred on 0, row by row from the lowest y.

    Staggered rows are half a pitch apart, and each column only uses every other
    row, alternating between neighbouring columns.
    """
    step_y = pitch_y / 2 if stagger else pitch_y
    grid = [
        (k * pitch_x, r * step_y)
        for r in range(rows)
        for k in range(columns)
        if not stagger or (k + r) % 2 == 0
    ]
    if not grid:
        return []
    mid_x = (min(x for x, _ in grid) + max(x for x, _ in grid)) / 2
    mid_y = (min(y for _, y in grid) + max(y for _, y in grid)) / 2
    return [(x - mid_x, y - mid_y) for x, y in grid]


def make_tray(
    battery: type[CylindricalBattery],
    count: int,
    *,
    grid_x: int | None = None,
    cell_size: tuple[float, float] = (21, 21),
    height_unit: float = 7,
    clearance: float = 0.3,
    divider: float = 1.2,
    seat: float = 0.5,
    stagger: bool = True,
    min_wall: float = 2.0,
    floor: float = 6.0,
) -> BatteryTray:
    """Build the smallest tray that holds at least `count` cells.

    grid_x: fixes the tray's width in cells, and it gets deeper along Y as
        needed. By default, the grid with the fewest cells, then the squarest.
    cell_size: (21, 21) for half-size cells, (42, 42) for full-size.
    clearance: per side, around each cell.
    divider: the wall between neighbouring slots and between rows.
    seat: how much of each cell's diameter sits down in its slot. The rest
        sticks up above the bin to grab. Under 0.5, the slots stop holding
        the cells at their widest.
    stagger: lay the slots like bricks, each half a slot along Y from the ones
        beside it, rather than in straight rows. It holds about as many and
        leaves room to grab each cell.
    min_wall: between the slots and the outside of the bin.
    floor: the least material under the slots. The Gridfinity base itself is
        4.75 mm.
    """
    if not (isinstance(battery, type) and issubclass(battery, CylindricalBattery)):
        raise TypeError(f"only cylindrical batteries are supported, not {battery!r}")
    if count < 1:
        raise ValueError(f"count must be at least 1, not {count}")
    if not 0 < seat < 1:
        raise ValueError(f"seat must be between 0 and 1, not {seat}")

    slot_width = battery.length + 2 * clearance
    slot_diameter = battery.diameter + 2 * clearance

    pitch_x = slot_width + divider
    pitch_y = slot_diameter + divider
    step_y = pitch_y / 2 if stagger else pitch_y

    def fits(gx: int, gy: int) -> tuple[int, int]:
        """(columns, rows) in a gx by gy grid."""
        inside_x = gx * cell_size[0] - 0.5 - 2 * min_wall
        inside_y = gy * cell_size[1] - 0.5 - 2 * min_wall
        if inside_x < slot_width or inside_y < slot_diameter:
            return 0, 0
        return (
            1 + math.floor((inside_x - slot_width) / pitch_x),
            1 + math.floor((inside_y - slot_diameter) / step_y),
        )

    def capacity(gx: int, gy: int) -> int:
        return len(_slots(*fits(gx, gy), stagger, pitch_x, pitch_y))

    def shortest_y(gx: int) -> int | None:
        """The fewest cells along Y that fit `count`, if any do at this width."""
        if fits(gx, 1000)[0] == 0:
            return None
        return next(g for g in itertools.count(1) if capacity(gx, g) >= count)

    if grid_x is not None:
        grid_y = shortest_y(grid_x)
        if grid_y is None:
            raise ValueError(f"grid_x={grid_x} is too narrow for {battery.__name__}")
    else:
        # Once Y is as short as it can be, wider grids only get bigger.
        min_y = next(g for g in itertools.count(1) if fits(1000, g)[1])
        options = []
        for gx in itertools.count(1):
            gy = shortest_y(gx)
            if gy is not None:
                options.append((gx * gy, abs(gx - gy), gx, gy))
                if gy == min_y:
                    break
        *_, grid_x, grid_y = min(options)
    columns, rows = fits(grid_x, grid_y)

    slot_depth = seat * slot_diameter
    height = math.ceil((floor + slot_depth) / height_unit) * height_unit

    tray = BatteryTray(
        bin=bd.Part(),
        battery=battery,
        count=count,
        columns=columns,
        rows=rows,
        stagger=stagger,
        grid_x=grid_x,
        grid_y=grid_y,
        cell_size=cell_size,
        height=height,
        slot_width=slot_width,
        slot_diameter=slot_diameter,
        divider=divider,
        slot_depth=slot_depth,
        min_wall=min_wall,
    )

    # The compartment is cut down from the bin's top face, at z = 0. Each slot
    # is a cylinder along X, with straight sides running up from its middle
    # when that's below the top.
    centre_z = -slot_depth + slot_diameter / 2
    slot = bd.Pos(Z=centre_z) * bd.Cylinder(
        slot_diameter / 2, slot_width, rotation=(0, 90, 0)
    )
    if centre_z < 0:
        down = (bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX)
        slot += bd.Box(slot_width, slot_diameter, -centre_z, align=down)
    compartment = bd.Part() + [bd.Pos(x, y) * slot for x, y in tray.slots]

    grid = gf.Grid.filled(grid_x, grid_y, cell_size=cell_size)
    part = gf.Bin(grid=grid, height=height, compartment=compartment, stacking_lip=None)
    return BatteryTray(**{**tray.__dict__, "bin": part})
