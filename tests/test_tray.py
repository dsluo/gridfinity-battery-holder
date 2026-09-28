import itertools
import math

import build123d as bd
import pytest

from gridfinity_battery_holder.batteries import CR2032, CR2450, LR44, SR626, NineVolt
from gridfinity_battery_holder.tray import make_tray

CASES = {
    "10CR2032": (CR2032, 10, {}),
    "20CR2032": (CR2032, 20, {}),
    "20LR44": (LR44, 20, {}),
    "30SR626": (SR626, 30, {}),
    "10CR2032-2-wide": (CR2032, 10, {"grid_x": 2}),
    "1CR2450": (CR2450, 1, {}),
    "5CR2032-full-cells": (CR2032, 5, {"cell_size": (42, 42)}),
    "10CR2032-deep-seat": (CR2032, 10, {"seat": 0.7}),
    "20CR2032-rows": (CR2032, 20, {"stagger": False}),
}


@pytest.fixture(scope="module", params=CASES.values(), ids=CASES.keys())
def tray(request):
    battery, count, kwargs = request.param
    return make_tray(battery, count, **kwargs)


def volume(shape):
    if shape is None:
        return 0.0
    return sum(s.volume for s in getattr(shape, "solids", lambda: [shape])())


class TestMakeTray:
    def test_holds_at_least_count(self, tray):
        assert tray.capacity >= tray.count
        assert len(tray.batteries()) == tray.capacity

    def test_is_one_valid_solid(self, tray):
        assert tray.bin.is_valid
        assert len(tray.bin.solids()) == 1

    def test_bin_matches_its_grid(self, tray):
        size = tray.bin.bounding_box().size
        cell_x, cell_y = tray.cell_size
        assert size.X == pytest.approx(tray.grid_x * cell_x - 0.5)
        assert size.Y == pytest.approx(tray.grid_y * cell_y - 0.5)
        assert size.Z == pytest.approx(tray.height)

    def test_is_as_short_as_the_slots_allow(self, tray):
        assert tray.height - 7 < 6.0 + tray.slot_depth <= tray.height

    def test_cells_stand_on_edge(self, tray):
        size = tray.batteries()[0].bounding_box().size
        assert size.X == pytest.approx(tray.battery.length)
        assert size.Z == pytest.approx(tray.battery.diameter)

    def test_cells_do_not_poke_into_the_bin(self, tray):
        for battery in tray.batteries():
            assert volume(tray.bin.intersect(battery)) == pytest.approx(0, abs=1e-6)

    def test_cells_sit_in_their_slots(self, tray):
        """Nudged a little further than the clearance, every cell hits a wall."""
        for battery in tray.batteries():
            for nudge in [bd.Pos(Z=-0.4), bd.Pos(X=0.4), bd.Pos(X=-0.4)]:
                assert volume(tray.bin.intersect(nudge * battery)) > 1e-4

    def test_cells_stick_up_above_the_bin(self, tray):
        for battery in tray.batteries():
            assert battery.bounding_box().max.Z > tray.height + 1

    def test_no_rim_around_the_cells(self, tray):
        """Nothing of the bin is higher than the dividers between the slots."""
        top = tray.bin.bounding_box().max.Z
        assert top == pytest.approx(tray.height)
        assert max(v.Z for v in tray.bin.vertices()) == pytest.approx(tray.height)

    def test_dividers_between_slots(self, tray):
        dividers = tray.height
        pitch = tray.slot_width + tray.divider
        for x, y in tray.slots:
            if x + pitch > max(sx for sx, _ in tray.slots) + 1e-9:
                continue
            between = x + pitch / 2
            assert tray.bin.is_inside((between, y, dividers - 0.5))

    def test_slots_stay_inside_the_walls(self, tray):
        size = tray.bin.bounding_box().size
        for x, y in tray.slots:
            assert abs(x) + tray.slot_width / 2 <= size.X / 2 - tray.min_wall + 1e-9
            assert abs(y) + tray.slot_diameter / 2 <= size.Y / 2 - tray.min_wall + 1e-9
        for (x0, y0), (x1, y1) in itertools.combinations(tray.slots, 2):
            assert (
                abs(x1 - x0) >= tray.slot_width + tray.divider - 1e-9
                or abs(y1 - y0) >= tray.slot_diameter + tray.divider - 1e-9
            )

    def test_neighbours_are_staggered(self, tray):
        pitch_x = tray.slot_width + tray.divider
        pitch_y = tray.slot_diameter + tray.divider
        offset = pitch_y / 2 if tray.stagger else 0
        for (x0, y0), (x1, y1) in itertools.combinations(tray.slots, 2):
            if abs(x1 - x0) == pytest.approx(pitch_x):
                assert abs(y1 - y0) % pitch_y == pytest.approx(offset, abs=1e-6)

    def test_cross_section_cuts_along_the_last_row(self, tray):
        box = tray.cross_section().bounding_box()
        assert box.max.Y == pytest.approx(tray.slots[-1][1], abs=1e-6)


@pytest.mark.parametrize("battery, count, kwargs", CASES.values(), ids=CASES.keys())
def test_no_smaller_grid_fits(battery, count, kwargs):
    tray = make_tray(battery, count, **kwargs)
    cell_x, cell_y = tray.cell_size

    def fits(gx, gy):
        inside_x = gx * cell_x - 0.5 - 2 * tray.min_wall
        inside_y = gy * cell_y - 0.5 - 2 * tray.min_wall
        if inside_x < tray.slot_width or inside_y < tray.slot_diameter:
            return 0
        step_y = (tray.slot_diameter + 1.2) / (2 if tray.stagger else 1)
        columns = 1 + math.floor((inside_x - tray.slot_width) / (tray.slot_width + 1.2))
        rows = 1 + math.floor((inside_y - tray.slot_diameter) / step_y)
        if not tray.stagger:
            return columns * rows
        # Even columns use the even rows, odd columns the odd ones.
        return sum((k + r) % 2 == 0 for k in range(columns) for r in range(rows))

    assert fits(tray.grid_x, tray.grid_y) == tray.capacity
    if "grid_x" in kwargs:
        assert fits(tray.grid_x, tray.grid_y - 1) < count
        return
    area = tray.grid_x * tray.grid_y
    for gx, gy in itertools.product(range(1, area + 1), repeat=2):
        smaller = gx * gy < area or (
            gx * gy == area and abs(gx - gy) < abs(tray.grid_x - tray.grid_y)
        )
        if smaller:
            assert fits(gx, gy) < count, (gx, gy)


def test_stagger_holds_about_as_many():
    for battery in [CR2032, LR44, SR626]:
        staggered = make_tray(battery, 20, grid_x=3)
        rows = make_tray(battery, 20, grid_x=3, stagger=False)
        assert staggered.grid_y <= rows.grid_y + 1


def test_seat_sets_how_far_cells_stick_up():
    for seat in [0.3, 0.5, 0.7]:
        tray = make_tray(CR2032, 10, seat=seat)
        top = tray.batteries()[0].bounding_box().max.Z
        assert top - tray.height == pytest.approx(
            (1 - seat) * tray.slot_diameter - 0.3
        )


@pytest.mark.parametrize(
    "battery, count, kwargs, error",
    [
        (CR2032, 0, {}, ValueError),
        (CR2032, 3, {"seat": 0}, ValueError),
        (CR2032, 3, {"seat": 1}, ValueError),
        (CR2450, 3, {"grid_x": 1, "cell_size": (4, 4)}, ValueError),
        (NineVolt, 3, {}, TypeError),
    ],
)
def test_rejects_bad_input(battery, count, kwargs, error):
    with pytest.raises(error):
        make_tray(battery, count, **kwargs)


def test_thickness_has_its_own_clearance():
    tray = make_tray(CR2032, 10, clearance=0.3, thickness_clearance=0.15)
    assert tray.slot_width == pytest.approx(CR2032.length + 0.3)
    assert tray.slot_diameter == pytest.approx(CR2032.diameter + 0.6)
