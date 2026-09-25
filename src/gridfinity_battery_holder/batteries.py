"""Battery sizes as build123d solids."""

import build123d as bd


# Approximate maximum dimensions in mm, based on IEC 60086 and typical
# datasheets (lithium-ion sizes are for unprotected, flat-top cells). Measure
# real cells before relying on a tight fit. Batteries stand upright along Z.
class CylindricalBattery(bd.Cylinder):
    diameter: float
    length: float
    # Button cells are shorter than they are wide (CR2032 is 0.16, AA is 3.5)
    is_button_cell: bool

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.is_button_cell = cls.length / cls.diameter < 1

    def __init__(
        self,
        rotation: bd.RotationLike = (0, 0, 0),
        align: bd.Align | tuple[bd.Align, bd.Align, bd.Align] = (
            bd.Align.CENTER,
            bd.Align.CENTER,
            bd.Align.MIN,
        ),
        mode: bd.Mode = bd.Mode.ADD,
    ):
        super().__init__(
            radius=self.diameter / 2,
            height=self.length,
            rotation=rotation,
            align=align,
            mode=mode,
        )


class RectangularBattery(bd.Box):
    width: float
    depth: float
    length: float

    def __init__(
        self,
        rotation: bd.RotationLike = (0, 0, 0),
        align: bd.Align | tuple[bd.Align, bd.Align, bd.Align] = (
            bd.Align.CENTER,
            bd.Align.CENTER,
            bd.Align.MIN,
        ),
        mode: bd.Mode = bd.Mode.ADD,
    ):
        super().__init__(
            length=self.width,
            width=self.depth,
            height=self.length,
            rotation=rotation,
            align=align,
            mode=mode,
        )


# Household cells
class AA(CylindricalBattery):
    diameter, length = 14.5, 50.5


class AAA(CylindricalBattery):
    diameter, length = 10.5, 44.5


class AAAA(CylindricalBattery):  # styluses, some penlights
    diameter, length = 8.3, 42.5


class C(CylindricalBattery):
    diameter, length = 26.2, 50.0


class D(CylindricalBattery):
    diameter, length = 34.2, 61.5


class NineVolt(RectangularBattery):
    width, depth, length = 26.5, 17.5, 48.5


# Lithium coin cells
class CR1220(CylindricalBattery):
    diameter, length = 12.5, 2.0


class CR1632(CylindricalBattery):
    diameter, length = 16.0, 3.2


class CR2016(CylindricalBattery):
    diameter, length = 20.0, 1.6


class CR2025(CylindricalBattery):
    diameter, length = 20.0, 2.5


class CR2032(CylindricalBattery):
    diameter, length = 20.0, 3.2


class CR2450(CylindricalBattery):
    diameter, length = 24.5, 5.0


# Alkaline and silver oxide button cells
class LR44(CylindricalBattery):  # also AG13, A76, SR44, 357
    diameter, length = 11.6, 5.4


class LR41(CylindricalBattery):  # also AG3, SR41, 392
    diameter, length = 7.9, 3.6


class SR626(CylindricalBattery):  # also AG4, 377, 626
    diameter, length = 6.8, 2.6


# Zinc-air hearing aid cells
class HearingAid10(CylindricalBattery):
    diameter, length = 5.8, 3.6


class HearingAid312(CylindricalBattery):
    diameter, length = 7.9, 3.6


class HearingAid13(CylindricalBattery):
    diameter, length = 7.9, 5.4


class HearingAid675(CylindricalBattery):
    diameter, length = 11.6, 5.4


# Camera, flashlight and remote cells
class CR123A(CylindricalBattery):
    diameter, length = 17.0, 34.5


class CR2(CylindricalBattery):
    diameter, length = 15.6, 27.0


class A23(CylindricalBattery):  # 12 V car and garage remotes, also 23A, MN21
    diameter, length = 10.3, 28.5


# Lithium-ion cells
class Li14500(CylindricalBattery):
    diameter, length = 14.5, 53.0


class Li16340(CylindricalBattery):  # rechargeable CR123A
    diameter, length = 16.6, 34.5


class Li18650(CylindricalBattery):
    diameter, length = 18.5, 65.2


class Li21700(CylindricalBattery):
    diameter, length = 21.2, 70.2


class Li26650(CylindricalBattery):
    diameter, length = 26.5, 65.4


BATTERIES = [
    AA,
    AAA,
    AAAA,
    C,
    D,
    NineVolt,
    CR1220,
    CR1632,
    CR2016,
    CR2025,
    CR2032,
    CR2450,
    LR44,
    LR41,
    SR626,
    HearingAid10,
    HearingAid312,
    HearingAid13,
    HearingAid675,
    CR123A,
    CR2,
    A23,
    Li14500,
    Li16340,
    Li18650,
    Li21700,
    Li26650,
]
