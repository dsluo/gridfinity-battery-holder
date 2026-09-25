# gridfinity-battery-holder

Parametric [Gridfinity](https://gridfinity.xyz/) bins for storing batteries,
built with [build123d](https://github.com/gumyr/build123d).

Give it a battery type and the minimum number you want to store, and it makes
the smallest bin that holds them. Batteries lie on their side in one open-top
pocket, packed in rows across the bin and stacked upward. Any room left over
after rounding up to whole grid cells and height units gets filled with
extra batteries.

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
just clean                             # removes build/
just test                              # runs the test suite
```

Anything after the battery and count is passed to the command-line tool:

| Option | Default | Meaning |
|---|---|---|
| `--extend {y,z}` | `y` | `y` keeps the height and makes the bin wider; `z` keeps the width and makes it taller |
| `--height-units N` | `7` | bin height in 7 mm units, used with `--extend y` |
| `--grid-y N` | `2` | bin width in grid cells, used with `--extend z` |
| `--packing {auto,square,hex}` | `auto` | `square` stacks rows straight up; `hex` nests each row in the one below; `auto` picks whichever needs the smaller bin |
| `--cell-size N` | `21` | `21` for half-size grid cells, `42` for full-size |
| `--clearance MM` | `0.3` | gap on each side of every battery |
| `--end-clearance MM` | `1.0` | gap at each end of the batteries |
| `--min-wall MM` | `3.0` | thinnest allowed wall; walls get thicker when there's spare room |
| `--overhang` | off | let the top row stick out above the rim by up to half a battery (bins can't be stacked on top then) |

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
- The pocket starts 7 mm above the bottom of the bin to stay clear of the base.
