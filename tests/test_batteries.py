import pytest

from gridfinity_battery_holder import batteries
from gridfinity_battery_holder.batteries import (
    BATTERIES,
    CylindricalBattery,
    RectangularBattery,
)


def all_subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from all_subclasses(sub)


def test_every_battery_is_listed_once():
    defined = set(all_subclasses(CylindricalBattery)) | set(
        all_subclasses(RectangularBattery)
    )
    assert set(BATTERIES) == defined
    assert len(BATTERIES) == len(defined)


@pytest.mark.parametrize("battery", BATTERIES, ids=lambda b: b.__name__)
def test_battery_builds_at_its_size(battery):
    solid = battery()
    size = solid.bounding_box().size
    assert solid.is_valid
    if issubclass(battery, CylindricalBattery):
        assert tuple(size) == pytest.approx(
            (battery.diameter, battery.diameter, battery.length)
        )
    else:
        assert tuple(size) == pytest.approx(
            (battery.width, battery.depth, battery.length)
        )


@pytest.mark.parametrize("battery", BATTERIES, ids=lambda b: b.__name__)
def test_battery_stands_on_the_xy_plane(battery):
    box = battery().bounding_box()
    assert box.min.Z == pytest.approx(0)
    assert box.center().X == pytest.approx(0)
    assert box.center().Y == pytest.approx(0)


def test_button_cells():
    buttons = {
        b.__name__
        for b in BATTERIES
        if issubclass(b, CylindricalBattery) and b.is_button_cell
    }
    assert buttons == {
        "CR1220",
        "CR1632",
        "CR2016",
        "CR2025",
        "CR2032",
        "CR2450",
        "LR44",
        "LR41",
        "SR626",
        "HearingAid10",
        "HearingAid312",
        "HearingAid13",
        "HearingAid675",
    }


def test_button_cell_flag_on_instances():
    assert batteries.CR2032().is_button_cell
    assert not batteries.AA().is_button_cell
