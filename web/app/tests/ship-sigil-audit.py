"""Compare Stead marks with the pinned Urbit glyph catalogs, offline.

Run with Python's Cairo and GI/librsvg bindings, Node 24, and a local checkout
of https://github.com/urbit/sigil-js at e86b674a4a3539ddc634351f335ac31d63bf64bd.
All 512 possible syllables are tested in cell one. A differing solid pixel that
no other cell could paint rules out every combination of later syllables.
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


def render(markup, *, alpha=False):
    background = "" if alpha else '<rect width="256" height="256" fill="white"/>'
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256">{background}{markup}</svg>'
    image = cairo.ImageSurface(cairo.FORMAT_ARGB32, SIZE, SIZE)
    viewport = Rsvg.Rectangle()
    viewport.width = viewport.height = SIZE
    Rsvg.Handle.new_from_data(svg.encode()).render_document(cairo.Context(image), viewport)
    image.flush()
    # Cairo's ARGB32 buffer uses native byte order. All images are grayscale.
    channel = (3 if alpha else 0) if sys.byteorder == "little" else (0 if alpha else 1)
    return bytes(image.get_data())[channel::4]


def mask(pixels, lookup):
    return int.from_bytes(pixels.translate(lookup), "little")


def mark_masks():
    geometry = Path(__file__).resolve().parents[1] / "src/brandGeometry.ts"
    js = """import {pathToFileURL} from 'node:url';
const {steadPaths,compactSteadPaths,sectionPaths} = await import(pathToFileURL(process.argv[1]));
console.log(JSON.stringify({master:[1,steadPaths],compact:[16,compactSteadPaths],
  ...Object.fromEntries(Object.entries(sectionPaths).filter(([name]) => name !== 'project').map(([k,v])=>[k,[16,v]]))}));"""
    shapes = json.loads(subprocess.check_output(["node", "--input-type=module", "-e", js, str(geometry)]))
    masks = {}
    for name, (viewbox, paths) in shapes.items():
        assert paths and all(re.fullmatch(r"[\da-zA-Z.,+\-\s]+", p) for p in paths)
        body = "".join(f'<path d="{p}"/>' for p in paths)
        image = render(f'<g transform="scale({SIZE / viewbox})">{body}</g>')
        masks[name] = mask(image, BLACK), mask(image, WHITE)
    return masks


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


def markup(symbol, position):
    dx, dy = (position % 2) * 128, (position // 2) * 128
    return symbol.replace("@TR", f"translate({dx} {dy})").replace("@FG", "black").replace("@BG", "white").replace("@SW", "4")


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sigil_js_checkout", type=Path)
    source = parser.parse_args().sigil_js_checkout / "src"
    for filename, pin in PINS.items():
        if hashlib.sha256((source / filename).read_bytes()).hexdigest() != pin:
            raise ValueError(f"Upstream source mismatch: {filename}")
    marks = mark_masks()
    report = {}
    for detail, filename in (("default", "default"), ("none", "icon")):
        raw = (source / "symbols" / (filename + ".ts")).read_text()
        catalog = dict(re.findall(r'([a-z]{3}):"([^"]+)"', raw))
        assert len(catalog) == 512
        symbols = sorted(set(catalog.values()))
        for cells in (1, 2, 4):
            for space in ("none", "default", "large"):
                key = f"{cells}-cell/{detail}/{space}"
                report[key] = compare(symbols, marks, cells, space)
    smallest = {name: min(case[name] for case in report.values()) for name in marks}
    print(json.dumps({"sample_px": SIZE, "layouts": len(report), "minimum_solid_pixel_differences": smallest}, indent=2))
    return 0 if all(smallest.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
