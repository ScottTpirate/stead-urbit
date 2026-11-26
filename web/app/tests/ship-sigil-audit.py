"""Compare Stead marks with the pinned Urbit glyph catalogs, offline.

Run with Python's Cairo and GI/librsvg bindings, Node 24, and a local checkout
of https://github.com/urbit/sigil-js at e86b674a4a3539ddc634351f335ac31d63bf64bd.
All 512 possible syllables are tested in cell one. A differing solid pixel that
no other cell could paint rules out every combination of later syllables.
Pass --display-sizes to compare disjoint regions of every cell at UI sizes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import cairo
import gi
gi.require_version("Rsvg", "2.0")
from gi.repository import Rsvg

SIZE = 256
BLACK = bytes(int(i <= 15) for i in range(256))
WHITE = bytes(int(i >= 240) for i in range(256))
PAINT = bytes(int(i != 0) for i in range(256))
PINS = {
    "core.ts": "5ff0be5772395e335d83faa24d169bdf2c5d88209022dc806d001284181d5f8f",
    "symbols/default.ts": "c41d981eb1d3d80d3679fd7e82212823d821139700489de06dbd637dbb888fd6",
    "symbols/icon.ts": "ca4af5a67a9ff9d56300d076dc1ceec6b40283049db7110994d514cdf5d12275",
}


def render(markup, *, alpha=False, size=SIZE, paper="white"):
    background = "" if alpha else f'<rect width="256" height="256" fill="{paper}"/>'
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 256 256">'
           f'{background}{markup}</svg>')
    image = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    viewport = Rsvg.Rectangle()
    viewport.width = viewport.height = size
    Rsvg.Handle.new_from_data(svg.encode()).render_document(cairo.Context(image), viewport)
    image.flush()
    # Cairo's ARGB32 buffer uses native byte order. All images are grayscale.
    channel = (3 if alpha else 0) if sys.byteorder == "little" else (0 if alpha else 1)
    return bytes(image.get_data())[channel::4]


def mask(pixels, lookup):
    return int.from_bytes(pixels.translate(lookup), "little")


def mark_geometry():
    geometry = Path(__file__).resolve().parents[1] / "src/brandGeometry.ts"
    js = """import {pathToFileURL} from 'node:url';
const {steadPaths,compactSteadPaths,sectionPaths} = await import(pathToFileURL(process.argv[1]));
console.log(JSON.stringify({master:[1,steadPaths],compact:[16,compactSteadPaths],
  ...Object.fromEntries(Object.entries(sectionPaths).filter(([name]) => name !== 'project').map(([k,v])=>[k,[16,v]]))}));"""
    shapes = json.loads(subprocess.check_output(["node", "--input-type=module", "-e", js, str(geometry)]))
    marks = {}
    for name, (viewbox, paths) in shapes.items():
        assert paths and all(re.fullmatch(r"[\da-zA-Z.,+\-\s]+", p) for p in paths)
        body = "".join(f'<path d="{p}"/>' for p in paths)
        marks[name] = f'<g transform="scale({SIZE / viewbox})">{body}</g>'
    return marks


def group_transform(cells, space):
    # core.ts shifts the same two-cell row vertically only when space is enabled.
    if space == "none":
        if cells == 1:
            return "scale(2)"
        if cells == 2:
            # A tight star has a 2:1 canvas. Also test it centered in a square slot.
            return "translate(0 64)"
        return ""
    scale = 0.5 if space == "large" else 0.75
    width = 128 if cells == 1 else 256
    height = 256 if cells == 4 else 128
    return f"translate({(256 - width * scale) / 2} {(256 - height * scale) / 2}) scale({scale})"


def markup(symbol, position, size=SIZE):
    dx, dy = (position % 2) * 128, (position // 2) * 128
    width = str(256 / size) if size < 64 else "4"
    return symbol.replace("@TR", f"translate({dx} {dy})").replace("@FG", "black").replace("@BG", "white").replace("@SW", width)


def compare(symbols, marks, cells, space):
    group = group_transform(cells, space)
    wrap = lambda body: f'<g transform="{group}">{body}</g>'
    # Every other slot can contribute any glyph (even invalid name combinations).
    # Use alpha, so strokes painted in the background color are also excluded.
    other_cells = "".join(markup(symbol, slot) for slot in range(1, cells) for symbol in symbols)
    blocked = mask(render(wrap(other_cells), alpha=True), PAINT)
    bounds = {name: SIZE * SIZE for name in marks}
    for symbol in symbols:
        pixels = render(wrap(markup(symbol, 0)))
        dark, light = mask(pixels, BLACK), mask(pixels, WHITE)
        for name, (ink, paper) in marks.items():
            positive = ((ink & light) | (paper & dark)) & ~blocked
            reversed_ink = ((ink & dark) | (paper & light)) & ~blocked
            bounds[name] = min(bounds[name], positive.bit_count(), reversed_ink.bit_count())
    return bounds


DISPLAY_SIZES = (12, 14, 16, 28, 34)
CONTRAST = 96
# If one pixel is at most low and the other at least low + 96, they differ by
# at least 96 levels. Sampling cutoffs gives a conservative bound on that count.
CUTOFFS = [(bytes(int(i <= low) for i in range(256)), bytes(int(i >= low + CONTRAST) for i in range(256)))
           for low in range(0, 256 - CONTRAST, 16)]


def levels(pixels):
    return [(mask(pixels, dark), mask(pixels, light)) for dark, light in CUTOFFS]


def differing_pixels(first, second):
    different = 0
    for (first_dark, first_light), (second_dark, second_light) in zip(first, second, strict=True):
        different |= (first_dark & second_light) | (first_light & second_dark)
    return different


def compare_display(symbols, marks, cells, space, size):
    group = group_transform(cells, space)

    def render_cell(body, **options):
        return render(f'<g transform="{group}">{body}</g>', size=size, **options)

    # Exclude pixels on which any syllable in any other cell can draw ink or paper.
    footprints = []
    for slot in range(cells):
        all_syllables = ''.join(markup(symbol, slot, size) for symbol in symbols)
        footprints.append(mask(render_cell(all_syllables, alpha=True), PAINT))

    columns = min(cells, 2)
    rows = cells // columns
    region = [y * rows // size * columns + x * columns // size for y in range(size) for x in range(size)]
    bounds = dict.fromkeys(marks, 0)
    for slot in range(cells):
        isolated = int.from_bytes(bytes(int(owner == slot) for owner in region), 'little')
        for other, footprint in enumerate(footprints):
            if other != slot:
                isolated &= ~footprint
        best = dict.fromkeys(marks, size * size)
        for symbol in symbols:
            glyph = levels(render_cell(markup(symbol, slot, size)))
            for key, mark in marks.items():
                count = (differing_pixels(mark, glyph) & isolated).bit_count()
                best[key] = min(best[key], count)
        # The partitions are disjoint, so each conflicting pixel is counted once.
        for key in bounds:
            bounds[key] += best[key]
    return bounds


def configurations(source):
    for filename, pin in PINS.items():
        if hashlib.sha256((source / filename).read_bytes()).hexdigest() != pin:
            raise ValueError(f"Upstream source mismatch: {filename}")
    for detail, filename in (("default", "default"), ("none", "icon")):
        raw = (source / "symbols" / (filename + ".ts")).read_text()
        catalog = dict(re.findall(r'([a-z]{3}):"([^"]+)"', raw))
        assert len(catalog) == 512
        symbols = sorted(set(catalog.values()))
        for cells in (1, 2, 4):
            for space in ("none", "default", "large"):
                key = f"{cells}-cell/{detail}/{space}"
                yield key, symbols, cells, space


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sigil_js_checkout", type=Path)
    parser.add_argument("--display-sizes", action="store_true", help="compare the five application sizes")
    args = parser.parse_args()
    layouts = list(configurations(args.sigil_js_checkout / "src"))
    geometry = mark_geometry()
    if args.display_sizes:
        report = {}
        for size in DISPLAY_SIZES:
            marks = {(name, paper): levels(render(f'<g fill="{ink}">{body}</g>', size=size, paper=paper))
                     for name, body in geometry.items() for ink, paper in (("black", "white"), ("white", "black"))}
            results = [compare_display(symbols, marks, cells, space, size) for _, symbols, cells, space in layouts]
            report[size] = {name: min(result[name, paper] for result in results for paper in ("white", "black"))
                            for name in geometry}
        print(json.dumps({"layouts": len(layouts), "contrast_of_at_least": CONTRAST, "pixel_lower_bounds": report}, indent=2))
        return 0 if all(all(row.values()) for row in report.values()) else 1

    marks = {}
    for name, body in geometry.items():
        pixels = render(body)
        marks[name] = mask(pixels, BLACK), mask(pixels, WHITE)
    report = {key: compare(symbols, marks, cells, space) for key, symbols, cells, space in layouts}
    smallest = {name: min(case[name] for case in report.values()) for name in marks}
    print(json.dumps({"sample_px": SIZE, "layouts": len(report), "minimum_solid_pixel_differences": smallest}, indent=2))
    return 0 if all(smallest.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
