import itertools
import math

import build123d as bd
import pytest

from gridfinity_battery_holder.batteries import AA, AAA, NineVolt
from gridfinity_battery_holder.holder import layout, make_holder

PITCH = AA.diameter + 2 * 0.3


class TestLayout:
    def test_square(self):
        result = layout("square", width=3.2 * PITCH, depth=2.5 * PITCH, pitch=PITCH)
        assert result.rows == [3, 3]
        assert result.pocket_width == pytest.approx(3 * PITCH)

    def test_hex_alternates_shorter_rows(self):
        result = layout("hex", width=3.2 * PITCH, depth=3 * PITCH, pitch=PITCH)
        # 1 + floor((3 - 1) / (sqrt(3) / 2)) = 3 rows
        assert result.rows == [3, 2, 3]
        assert result.pocket_width == pytest.approx(3 * PITCH)

    def test_hex_keeps_full_rows_when_there_is_room_to_shift(self):
        result = layout("hex", width=3.5 * PITCH, depth=2 * PITCH, pitch=PITCH)
        assert result.rows == [3, 3]
        assert result.pocket_width == pytest.approx(3.5 * PITCH)

    def test_hex_rows_nest(self):
        result = layout("hex", width=3.2 * PITCH, depth=2 * PITCH, pitch=PITCH)
        (_, z0), *_, (_, z1) = result.centres
        assert z1 - z0 == pytest.approx(PITCH * math.sqrt(3) / 2)

    def test_hex_needs_room_for_a_shifted_row(self):
        assert (
            layout("hex", width=1.4 * PITCH, depth=5 * PITCH, pitch=PITCH).centres == []
        )
        assert (
            layout("square", width=1.4 * PITCH, depth=5 * PITCH, pitch=PITCH).rows
            == [1] * 5
        )

    @pytest.mark.parametrize("packing", ["square", "hex"])
    def test_nothing_fits_in_a_small_pocket(self, packing):
        assert (
            layout(packing, width=0.9 * PITCH, depth=5 * PITCH, pitch=PITCH).centres
            == []
        )
        assert (
            layout(packing, width=5 * PITCH, depth=0.9 * PITCH, pitch=PITCH).centres
            == []
        )

    @pytest.mark.parametrize("packing", ["square", "hex"])
    def test_batteries_stay_in_the_pocket_and_apart(self, packing):
        depth = 4 * PITCH
        result = layout(packing, width=4.7 * PITCH, depth=depth, pitch=PITCH)
        for y, z in result.centres:
            assert abs(y) + PITCH / 2 <= result.pocket_width / 2 + 1e-9
            assert PITCH / 2 - 1e-9 <= z <= depth - PITCH / 2 + 1e-9
        for (y0, z0), (y1, z1) in itertools.combinations(result.centres, 2):
            assert math.hypot(y1 - y0, z1 - z0) >= PITCH - 1e-9


CASES = {
    "8AA-auto": (AA, 8, {}),
    "8AA-square": (AA, 8, {"packing": "square"}),
    "20AA-tall": (AA, 20, {"height_units": 10}),
    "8AA-extend-z": (AA, 8, {"extend": "z", "grid_y": 2}),
    "12AA-extend-z-hex": (AA, 12, {"extend": "z", "grid_y": 3}),
    "6AAA": (AAA, 6, {"extend": "z", "grid_y": 2}),
    "1AA": (AA, 1, {"height_units": 4}),
    "3AAA-single-column": (AAA, 3, {"extend": "z", "grid_y": 1}),
    "4AA-full-cells": (AA, 4, {"height_units": 5, "cell_size": (42, 42)}),
    "8AA-square-overhang": (AA, 8, {"packing": "square", "overhang": True}),
    "8AA-extend-z-overhang": (AA, 8, {"extend": "z", "grid_y": 3, "overhang": True}),
    "12AA-hex-overhang": (
        AA,
        12,
        {"packing": "hex", "height_units": 5, "overhang": True},
    ),
}


@pytest.fixture(scope="module", params=CASES.values(), ids=CASES.keys())
def holder(request):
    battery, count, kwargs = request.param
    return make_holder(battery, count, **kwargs)


class TestMakeHolder:
    def test_holds_at_least_count(self, holder):
        assert holder.capacity >= holder.count

    def test_is_one_valid_solid(self, holder):
        assert holder.bin.is_valid
        assert len(holder.bin.solids()) == 1

    def test_batteries_do_not_touch_the_bin(self, holder):
        for battery in holder.batteries():
            overlap = holder.bin.intersect(battery)
            assert overlap is None or overlap.volume == pytest.approx(0, abs=1e-6)

    def test_walls_are_thick_enough(self, holder):
        size = holder.bin.bounding_box().size
        assert (size.Y - holder.layout.pocket_width) / 2 >= holder.min_wall - 1e-9
        assert (size.X - holder.pocket_length) / 2 >= holder.min_wall - 1e-9

    def test_end_clearance(self, holder):
        """A battery 1 mm longer at each end just fits; any longer hits the ends."""
        (y, z), *_ = holder.layout.centres

        def touches(length):
            probe = bd.Cylinder(
                holder.battery.diameter / 2, length, rotation=(0, 90, 0)
            )
            overlap = holder.bin.intersect(
                probe.moved(bd.Location((0, y, holder.floor + z)))
            )
            pieces = (
                []
                if overlap is None
                else getattr(overlap, "solids", lambda: [overlap])()
            )
            return sum(piece.volume for piece in pieces) > 1e-6

        assert not touches(holder.battery.length + 2 * 1.0 - 0.01)
        assert touches(holder.battery.length + 2 * 1.0 + 0.2)

    def test_bin_matches_its_grid(self, holder):
        size = holder.bin.bounding_box().size
        cell_x, cell_y = holder.cell_size
        assert size.X == pytest.approx(holder.grid_x * cell_x - 0.5)
        assert size.Y == pytest.approx(holder.grid_y * cell_y - 0.5)
        assert size.Z == pytest.approx(holder.height)

    def test_only_overhang_sticks_out(self, holder):
        top = max(b.bounding_box().max.Z for b in holder.batteries())
        if not holder.overhang:
            assert top <= holder.height + 1e-9

    def test_top_row_centres_stay_below_the_rim(self, holder):
        for battery in holder.batteries():
            assert battery.center().Z <= holder.height + 1e-9

    def test_cross_section_cuts_the_preview_in_half(self, holder):
        box = holder.cross_section().bounding_box()
        assert box.max.X == pytest.approx(0, abs=1e-6)
        assert box.min.X == pytest.approx(-holder.bin.bounding_box().size.X / 2)


@pytest.mark.parametrize("battery, count, kwargs", CASES.values(), ids=CASES.keys())
def test_one_size_smaller_holds_too_few(battery, count, kwargs):
    holder = make_holder(battery, count, **kwargs)
    packing = kwargs.get("packing", "auto")
    packings = ["square", "hex"] if packing == "auto" else [packing]
    pitch = battery.diameter + 2 * 0.3
    headroom = pitch / 2 if kwargs.get("overhang") else 0

    def fits(grid_y, height):
        width = grid_y * holder.cell_size[1] - 0.5 - 2 * holder.min_wall
        depth = height - holder.floor + headroom
        return max(len(layout(p, width, depth, pitch).centres) for p in packings)

    if kwargs.get("extend", "y") == "y":
        assert fits(holder.grid_y - 1, holder.height) < count
    else:
        assert fits(holder.grid_y, holder.height - 7) < count


def test_auto_picks_hex_when_it_needs_a_smaller_bin():
    auto = make_holder(AA, 8)
    square = make_holder(AA, 8, packing="square")
    assert (auto.layout.packing, auto.grid_y, auto.capacity) == ("hex", 3, 9)
    assert (square.layout.packing, square.grid_y, square.capacity) == ("square", 4, 10)


def test_auto_picks_hex_for_a_shorter_bin():
    auto = make_holder(AA, 12, extend="z", grid_y=3)
    square = make_holder(AA, 12, extend="z", grid_y=3, packing="square")
    assert auto.layout.packing == "hex"
    assert auto.height < square.height


def test_overhang_adds_a_row_that_sticks_out():
    flush = make_holder(AA, 8, packing="square")
    overhang = make_holder(AA, 8, packing="square", overhang=True)
    assert (flush.grid_y, flush.layout.rows) == (4, [5, 5])
    assert (overhang.grid_y, overhang.layout.rows) == (3, [3, 3, 3])
    top = max(b.bounding_box().max.Z for b in overhang.batteries())
    assert overhang.height < top <= overhang.height + PITCH / 2
    assert max(b.bounding_box().max.Z for b in flush.batteries()) <= flush.height


def test_overhang_makes_a_shorter_bin():
    flush = make_holder(AA, 8, extend="z", grid_y=3, packing="square")
    overhang = make_holder(AA, 8, extend="z", grid_y=3, packing="square", overhang=True)
    assert overhang.height < flush.height


def test_clearance_around_each_battery():
    holder = make_holder(AA, 8, packing="square", clearance=0.3)
    assert holder.layout.pocket_width == pytest.approx(holder.layout.rows[0] * PITCH)


@pytest.mark.parametrize(
    "battery, count, kwargs, error",
    [
        (AA, 3, {"height_units": 1}, ValueError),
        (AA, 3, {"extend": "z", "grid_y": 1, "packing": "hex"}, ValueError),
        (AA, 0, {}, ValueError),
        (AA, 3, {"packing": "diagonal"}, ValueError),
        (AA, 3, {"extend": "x"}, ValueError),
        (NineVolt, 3, {}, TypeError),
    ],
)
def test_rejects_bad_input(battery, count, kwargs, error):
    with pytest.raises(error):
        make_holder(battery, count, **kwargs)
