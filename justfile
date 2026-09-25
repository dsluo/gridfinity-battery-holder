out := "build"

# List recipes
default:
    @just --list

# Preview a holder in OCP CAD Viewer, e.g. `just show AA 8 --packing square`
show battery="AA" count="8" *args:
    uv run gridfinity-battery-holder {{ battery }} {{ count }} --show {{ args }}

# Preview a holder cut in half across the batteries
section battery="AA" count="8" *args:
    uv run gridfinity-battery-holder {{ battery }} {{ count }} --show --section {{ args }}

# Export build/<battery>-<count>.<format>, where format is stl, step or all
build format battery="AA" count="8" *args:
    @mkdir -p {{ out }}
    for ext in {{ if format == "all" { "stl step" } else if format =~ '^(stl|step)$' { format } else { error("format must be stl, step or all, not " + format) } }}; do \
        uv run gridfinity-battery-holder {{ battery }} {{ count }} -o {{ out }}/{{ battery }}-{{ count }}.$ext {{ args }}; \
    done

# Remove everything in build/
clean:
    rm -rf {{ out }}

# Run the test suite, e.g. `just test -k hex`
test *args:
    uv run pytest {{ args }}
