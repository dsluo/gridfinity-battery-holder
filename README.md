# gridfinity-battery-holder

Parametric [Gridfinity](https://gridfinity.xyz/) bins for storing batteries,
built with [build123d](https://github.com/gumyr/build123d).

Give it a battery type and the minimum number you want to store, and it makes
the smallest bin that holds them. Any room left over after rounding up to whole
grid cells and height units gets filled with extra batteries.

- **Holders** (the default for everything but button cells): batteries lie on
  their side in one open-top pocket, packed in rows across the bin and stacked
  upward.
- **Trays** (the default for button cells): cells stand on edge face to face,
  like a roll of coins, each in its own round-bottomed slot with a thin divider
  between neighbours. The slots are staggered like bricks, each half a slot
  along from the ones beside it. There's no rim: the top half of each cell
  sticks up above the bin, clear of its neighbours, so you can pinch it out.
  Bins can't be stacked on top of a tray. The grid is the
  one with the fewest cells, then the squarest.

## Setup

Python, [uv](https://docs.astral.sh/uv/) and the task runner
[just](https://just.systems/) are pinned in `mise.toml`. Install them with
[mise](https://mise.jdx.dev/), then install the Python dependencies:

```sh
mise install
uv sync
```

To preview models, install the
[OCP CAD Viewer](https://marketplace.visualstudio.com/items?itemName=bernhard-42.ocp-cad-viewer)
extension for VS Code and open its panel before running `just show`.

## Usage

```sh
just show AA 8                         # preview in OCP CAD Viewer
just section AA 8                      # preview, cut in half across the batteries
just build stl AA 8                    # writes build/AA-8.stl
just build all AAA 12 --extend z       # writes build/AAA-12.stl and .step
just show CR2032 20                    # a tray of coin cells
just show CR2032 20 --seat 0.7         # sink the coin cells deeper
just clean                             # removes build/
just test                              # runs the test suite
```

Anything after the battery and count is passed to the command-line tool:

| Option | Default | Meaning |
|---|---|---|
| `--style {auto,holder,tray}` | `auto` | `auto` makes a tray for button cells and a holder for everything else |
| `--cell-size N` | `21` | `21` for half-size grid cells, `42` for full-size |
| `--clearance MM` | `0.3` | gap on each side of every battery (around the rim, for trays) |
| `--min-wall MM` | `3.0` holder, `2.0` tray | thinnest allowed outer wall; walls get thicker when there's spare room |

Holders only:

| Option | Default | Meaning |
|---|---|---|
| `--extend {y,z}` | `y` | `y` keeps the height and makes the bin wider; `z` keeps the width and makes it taller |
| `--packing {auto,square,hex}` | `auto` | `square` stacks rows straight up; `hex` nests each row in the one below; `auto` picks whichever needs the smaller bin |
| `--height-units N` | `7` | bin height in 7 mm units, used with `--extend y` |
| `--grid-y N` | `2` | bin width in grid cells, used with `--extend z` |
| `--end-clearance MM` | `1.0` | gap at each end of the batteries |
| `--overhang` | off | let the top row stick out above the rim by up to half a battery (bins can't be stacked on top then) |

Trays only:

| Option | Default | Meaning |
|---|---|---|
| `--grid-x N` | picked | fix the tray's width in grid cells; it then only grows along Y |
| `--no-stagger` | off | straight rows instead of bricklike |
| `--thickness-clearance MM` | `0.15` | gap at each face of a cell, along its thickness |
| `--seat F` | `0.5` | how much of each cell's diameter sits down in its slot; the rest sticks up above the bin |

The tool can also be run directly, e.g.
`uv run gridfinity-battery-holder AA 8 -o aa.stl`.

### From Python

```python
from gridfinity_battery_holder import make_holder
from gridfinity_battery_holder.batteries import AA

holder = make_holder(AA, 8, packing="hex")
print(holder)  # 9 x AA (asked for 8), hex packed in rows of 3/3/3: ...
holder.bin     # the build123d part to export
holder.preview()        # the bin with a battery in every slot
holder.cross_section()  # the preview cut in half
```

Trays work the same way, and take more options than the command line, such as
the divider thickness:

```python
from gridfinity_battery_holder import make_tray
from gridfinity_battery_holder.batteries import CR2032

tray = make_tray(CR2032, 20, divider=1.6)
print(tray)  # 21 x CR2032 (asked for 20), staggered 7 across and 6 deep: ...
tray.cross_section()  # cut along the last row of slots
```

## Batteries

Household cells (AA, AAA, AAAA, C, D, 9V), lithium coin cells (CR1220 to
CR2450), alkaline and silver oxide button cells (LR44, LR41, SR626), zinc-air
hearing aid cells (10, 312, 13, 675), camera and remote cells (CR123A, CR2,
A23) and lithium-ion cells (14500, 16340, 18650, 21700, 26650). See
`src/gridfinity_battery_holder/batteries.py` for the dimensions.

The dimensions are approximate maximums. Measure your own cells before relying
on a tight fit, especially protected or button-top lithium-ion cells, which
are longer. The 9V battery is defined but can't be used for holders yet, since
the holders only support cylindrical batteries.

## Notes

- This project depends on a
  [fork of gridfinity-build123d](https://github.com/dsluo/gridfinity-build123d/tree/build123d-0.13-compat)
  that adds support for build123d 0.13.
- A holder's pocket starts 7 mm above the bottom of the bin to stay clear of
  the base. A tray leaves at least 6 mm under its slots.
