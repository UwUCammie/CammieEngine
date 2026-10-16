#!/usr/bin/env python3
"""Regenerate the title screen logo atlas and its shine mask from the source art.

    python tools/generate_title_logo.py [--source art/logoBumpin-source.png]
                                        [--output assets/images/logoBumpin.png]
                                        [--mask-output assets/images/logoBumpinShine.png]
                                        [--crops tmp/logo-crops] [--check]

Needs Pillow and numpy (the bundled .tools/python does not ship them; any
ordinary Python 3 with both installed works). The source art is kept at
art/logoBumpin-source.png and is never modified, so this can be rerun. The
output is a pure function of the source: running it twice gives the same
pixels.

The sheet is the 2048x2048 Sparrow atlas described by assets/images/logoBumpin.xml.
Only four rectangles of it are distinct frames (FRAMES below); the XML is not
touched and every pixel outside the CAMMIE letters is copied through unchanged.

1. The CAMMIE letters. "CAMMIE" used to be filled with trans flag stripes
   inside a thin black outline, inside a pink neon tube. ENGINE has no stripes
   and no black outline: its tube runs straight into a near black interior that
   has a magenta glow just inside the tube. CAMMIE is rebuilt to match, and the
   tube itself is never redrawn:

   - the black outline is the pixels whose brightest channel is below
     DARK_LIMIT. A flood fill (4-connected, so it cannot slip diagonally through
     the outline) from the border of the CAMMIE box cannot cross it, so the
     non black pixels it does not reach are enclosed: each letter's stripe fill
     with its anti-aliased blends (a region that holds light blue stripe
     pixels) and the small counter of the A;
   - what is rebuilt is each letter's fill, the black outline around it
     (OUTLINE_REACH pixels at most) and the one pixel of anti-aliasing between
     the outline and the tube. Tube pixels (tube_mask) are never in it;
   - ENGINE is measured in the same frame: the median colour of its interior
     pixels by distance from the tube's inner edge (the soft edge, the magenta
     glow, the fall to black), where its interior is what its tube ring
     encloses. Every rebuilt pixel of CAMMIE gets the colour ENGINE has at its
     distance from the nearest pixel that is not rebuilt (the tube), so the two
     words have the same tube edge, the same glow brightness, width and falloff,
     and no dark gap. The one contour of CAMMIE that never had a tube, the inner
     edge of the C, gets the same glow from where the outline ended;
   - the counter of the A (found as the small pocket enclosed by an outline of
     its own) would vanish with the rest of the fill. It is redrawn as ENGINE
     draws any contour: a pink tube of ENGINE's tube colour along the hole's
     outline (COUNTER_TUBE pixels thick, the hole is too small for a full tube)
     with the same glow falling away from it, and a dark hole.

   Nothing is blurred. Alpha, the tube, the outer glow and everything outside
   the CAMMIE box are never touched. The generator stops with an error if any
   light blue or pale pink pixel is left inside the CAMMIE box (a gap in the
   outline would show up there).

2. The shine mask (assets/images/logoBumpinShine.png), same size and layout as
   the logo. The title screen shader (source/TitleShineShader.hx) lays a moving
   band of trans flag colours over the neon text. Per pixel:
   R is how much the shine applies: the neon tube, inner glow and outer glow of
     the bottom text line, weighted by how pink the pixel is (cubed, so the
     tube takes the shine and the glow only a hint of it), and 0 on the white
     and pink lettering above, the blue splash and the black fill;
   G is the position of the pixel along the text line, 0 at the left end of the
     tube and 1 at the right end, measured separately in every frame so the
     sweep lines up while the logo bumps (the frames are slightly different
     sizes). The measure is slightly sheared so the band leans like a slash;
   B is 0 and A is 255 (an opaque mask is never touched by premultiplication).
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOURCE = os.path.join(ROOT, "art", "logoBumpin-source.png")
DEFAULT_OUTPUT = os.path.join(ROOT, "assets", "images", "logoBumpin.png")
DEFAULT_MASK_OUTPUT = os.path.join(ROOT, "assets", "images", "logoBumpinShine.png")

# Distinct frame rectangles (x, y, width, height) from logoBumpin.xml.
FRAMES = [
    (0, 0, 922, 670),
    (922, 0, 969, 703),
    (0, 703, 940, 683),
    (940, 703, 933, 679),
]

LIGHT_BLUE = (91, 206, 250)    # #5BCEFA
PALE_PINK = (245, 169, 184)    # #F5A9B8

SEED_TOLERANCE = 25            # per channel distance of a pure light blue stripe pixel
BOX_MARGIN = 14                # pixels added around the light blue pixels: the border lies in the tube or beyond
DARK_LIMIT = 24                # brightest channel below this is black outline (used to find the A's counter)
COUNTER_MIN = 6                # smaller enclosed specks in the outline are anti-aliasing, not a counter
COUNTER_MAX = 80               # an enclosed pocket this small (pixels) is the counter of the A
COUNTER_TUBE = 1.5             # thickness of the tube drawn around the counter
OUTLINE_REACH = 4              # most pixels the black outline can be thick
MIN_STRIPES = 20               # light blue pixels that make an enclosed region a letter
TUBE_BLUE_LEAD = 45            # least blue minus green of a tube pixel
TUBE_RED_FLOOR = 225           # least red of a tube pixel: the tube's soft inner edge (red 200) is interior
PROFILE_REACH = 12             # distance bins measured from ENGINE
MIN_BIN_SAMPLES = 20

# Shine mask.
SHEAR = 0.35                   # sideways pixels per row in the position channel
NEON_FULL = 125.0              # pinkness (see neon_weight) that counts as full neon
NEON_FLOOR = 8.0               # pinkness below this (near white, near black) gets no shine
NEON_GAMMA = 3.0               # cubes the weight: the tube takes the shine, its glow hardly any
GLOW_REACH = 18                # pixels from the tube beyond which the mask is 0


# ---------------------------------------------------------------------------
# image helpers
# ---------------------------------------------------------------------------

def tube_mask(rgb):
    """Bright pink neon tube, including its hotter magenta rim.

    Red high and blue well above green. A pixel of the tube lightened by the
    white glow of the lettering above still has blue well above green, and the
    rim along the tube's edges (green near 20) is red and blue too. The pale
    pink stripe (blue 15 above green), white and the light blue stripe (red
    below 200) are not in it.
    """
    r, g, b = (rgb[..., i].astype(np.int32) for i in range(3))
    return (r > TUBE_RED_FLOOR) & (b - g > TUBE_BLUE_LEAD)


def neon_weight(rgb):
    """0..1 weight of a pixel for the shine: 1 for the neon tube, a small fraction for its glow.

    It is the smaller of red minus green and red minus half the blue, so white
    (no red excess), the blue splash and the purple where glow meets splash all
    stay near 0 while the tube and the magenta glow are positive.
    """
    r, g, b = (rgb[..., i].astype(np.float64) for i in range(3))
    pinkness = np.minimum(r - g, r - 0.5 * b)
    weight = np.clip((pinkness - NEON_FLOOR) / (NEON_FULL - NEON_FLOOR), 0.0, 1.0)
    return weight ** NEON_GAMMA


def floodfill(passable, seeds):
    """4-connected region of `passable` pixels reachable from `seeds`."""
    reached = seeds & passable
    frontier = reached.copy()
    while frontier.any():
        grown = np.zeros_like(reached)
        grown[1:] |= frontier[:-1]
        grown[:-1] |= frontier[1:]
        grown[:, 1:] |= frontier[:, :-1]
        grown[:, :-1] |= frontier[:, 1:]
        grown &= passable & ~reached
        reached |= grown
        frontier = grown
    return reached


def border(shape):
    seeds = np.zeros(shape, dtype=bool)
    seeds[0] = seeds[-1] = True
    seeds[:, 0] = seeds[:, -1] = True
    return seeds


def distance_to(mask, limit=40):
    """Exact Euclidean distance from every pixel to the nearest True pixel, capped.

    The transform is separable: a vertical pass of squared distances, then a
    horizontal pass over its result, each a short loop of whole array shifts.
    """
    height, width = mask.shape
    reach = int(np.ceil(limit))
    inf = float(2 * reach * reach + 4)
    padded = np.pad(mask, ((reach, reach), (0, 0)))
    vertical = np.full(mask.shape, inf)
    for dy in range(-reach, reach + 1):
        vertical = np.minimum(vertical, np.where(padded[reach + dy:reach + dy + height], float(dy * dy), inf))
    padded = np.pad(vertical, ((0, 0), (reach, reach)), constant_values=inf)
    squared = np.full(mask.shape, inf)
    for dx in range(-reach, reach + 1):
        squared = np.minimum(squared, padded[:, reach + dx:reach + dx + width] + dx * dx)
    return np.minimum(np.sqrt(squared), float(limit))


def smoothstep(lo, hi, x):
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------
# CAMMIE
# ---------------------------------------------------------------------------

def locate_cammie(frame):
    """(x0, y0, x1, y1), inclusive, of the CAMMIE box inside one frame.

    The light blue stripes sit only inside the CAMMIE letters, so their bounding
    box plus a small margin is a box whose border runs through the tube.
    """
    rgb = frame[..., :3].astype(np.int32)
    light_blue = (np.abs(rgb - np.array(LIGHT_BLUE)).max(axis=-1) < SEED_TOLERANCE) & (frame[..., 3] > 240)
    ys, xs = np.nonzero(light_blue)
    if len(xs) == 0:
        raise RuntimeError("no light blue stripe found: is this the source art?")
    height, width = frame.shape[:2]
    return (max(xs.min() - BOX_MARGIN, 0), max(ys.min() - BOX_MARGIN, 0),
            min(xs.max() + BOX_MARGIN, width - 1), min(ys.max() + BOX_MARGIN, height - 1))


def dilate4(mask):
    """The mask plus its 4-connected neighbours."""
    grown = mask.copy()
    grown[1:] |= mask[:-1]
    grown[:-1] |= mask[1:]
    grown[:, 1:] |= mask[:, :-1]
    grown[:, :-1] |= mask[:, 1:]
    return grown


def components(mask):
    """4-connected pieces of a mask, one boolean array each."""
    remaining = mask.copy()
    pieces = []
    while remaining.any():
        seed = np.zeros_like(remaining)
        seed.flat[np.argmax(remaining)] = True
        piece = floodfill(remaining, seed)
        pieces.append(piece)
        remaining &= ~piece
    return pieces


def tube_regions(rgb):
    """(ring, outside, interior) masks of a region whose glyphs have a closed tube.

    outside is what a flood fill from the border reaches without crossing a tube
    pixel, ring the tube pixels that touch it, interior everything else: the
    letters' insides from the tube's soft inner edge inwards. Used on ENGINE,
    whose every contour has a tube.
    """
    tube = tube_mask(rgb)
    outside = floodfill(~tube, border(tube.shape))
    ring = floodfill(tube, tube & dilate4(outside))
    return ring, outside, ~ring & ~outside


def enclosed_pockets(region):
    """(dark, pockets): the black outline pixels of a region and what it encloses.

    A flood fill that cannot cross the outline (4-connected, so it cannot slip
    diagonally through it) starts from the border of the region; the non black
    pixels it does not reach are enclosed by an outline.
    """
    dark = region.max(axis=-1) < DARK_LIMIT
    return dark, ~dark & ~floodfill(~dark, border(dark.shape))


def cammie_regions(frame, box):
    """(inside, counters): the pixels to rebuild and the holes in the letters.

    inside is the stripe fill of every letter (an enclosed region that holds
    light blue stripe pixels), the black outline around it, and the one pixel of
    anti-aliasing between the outline and the tube; the tube itself is never in
    it. counters are masks (frame sized) of the small holes inside the letters,
    one per hole: the triangle in the A is a small pocket enclosed by a black
    outline of its own, and the mask is that pocket and its outline.
    """
    x0, y0, x1, y1 = box
    region = frame[y0:y1 + 1, x0:x1 + 1, :3]
    dark, pockets = enclosed_pockets(region)
    stripes = (np.abs(region.astype(np.int32) - np.array(LIGHT_BLUE)).max(axis=-1) < SEED_TOLERANCE) & (frame[y0:y1 + 1, x0:x1 + 1, 3] > 240)
    letters = np.zeros_like(pockets)
    holes = np.zeros_like(pockets)
    counters = []
    small = []
    for pocket in components(pockets):
        if (pocket & stripes).sum() >= MIN_STRIPES:
            letters |= pocket
        elif COUNTER_MIN <= pocket.sum() <= COUNTER_MAX:
            small.append(pocket)
    for pocket in small:
        hole = pocket | floodfill(dark, dilate4(pocket) & dark)
        # a counter sits inside a letter: its outline touches the letter's fill
        if (hole & dilate4(letters)).any() and hole.sum() <= 3 * COUNTER_MAX:
            holes |= hole
            mask = np.zeros(frame.shape[:2], dtype=bool)
            mask[y0:y1 + 1, x0:x1 + 1] = hole
            counters.append(mask)
    # the outline: black pixels reaching out of the fill, a few pixels at most
    reach = letters.copy()
    for _ in range(OUTLINE_REACH):
        reach |= dilate4(reach) & dark
    inside = (dilate4(reach) & ~tube_mask(region)) | holes
    mask = np.zeros(frame.shape[:2], dtype=bool)
    mask[y0:y1 + 1, x0:x1 + 1] = inside
    return mask, counters


def cammie_interior(frame, box):
    """Boolean mask (frame sized) of the pixels of CAMMIE that are rebuilt."""
    return cammie_regions(frame, box)[0]


def find_counters(frame, box):
    """Masks (frame sized) of the holes inside the letters (the triangle of the A)."""
    return cammie_regions(frame, box)[1]


def text_line(frame, box):
    """Extent of the bottom line's neon tube: (x0, y0, x1, y1) and its mask.

    Only rows around the stripes are read, so the pink FRIDAY NIGHT lettering
    above is never mistaken for neon.
    """
    top, bottom = max(box[1] + BOX_MARGIN - 12, 0), min(box[3] - BOX_MARGIN + 12, frame.shape[0] - 1)
    tube = np.zeros(frame.shape[:2], dtype=bool)
    tube[top:bottom + 1] = tube_mask(frame[top:bottom + 1, :, :3])
    ys, xs = np.nonzero(tube)
    return (xs.min(), ys.min(), xs.max(), ys.max()), tube


def widest_gap(columns, start, stop, minimum=8):
    """(first, last) index of the longest run of False columns in [start, stop], or None."""
    best, run_start = None, None
    for x in range(start, stop + 2):
        empty = x <= stop and not columns[x]
        if empty and run_start is None:
            run_start = x
        elif not empty and run_start is not None:
            if x - run_start >= minimum and (best is None or x - run_start > best[1] - best[0] + 1):
                best = (run_start, x - 1)
            run_start = None
    return best


def engine_profile(frame, box):
    """ENGINE's tube colour and interior colour by distance from the tube.

    Returns (distances, colours, tube): distances are the bin centres 0.5, 1.5,
    ... (pixels from the tube's inner edge), colours the median rgb of ENGINE's
    interior pixels in each bin over every stroke of ENGINE in the frame, tube
    the median rgb of the tube's core.
    """
    (_tx0, _ty0, tx1, _ty1), tube = text_line(frame, box)
    # ENGINE starts after the widest tube-free gap right of CAMMIE
    gap = widest_gap(tube.any(axis=0), box[2] - 20, tx1)
    if gap is None:
        raise RuntimeError("could not find the gap between CAMMIE and ENGINE")
    top, bottom = max(box[1] + BOX_MARGIN - 14, 0), min(box[3] - BOX_MARGIN + 14, frame.shape[0] - 1)
    region = frame[top:bottom + 1, gap[1] - 4:tx1 + 15, :3]
    ring, _outside, interior = tube_regions(region)
    distance = distance_to(~interior) - 0.5
    # the counters of ENGINE that show the blue splash are not glyph interior
    red, blue = region[..., 0].astype(np.int32), region[..., 2].astype(np.int32)
    usable = interior & (blue <= red + 8)
    centres = np.arange(0.5, PROFILE_REACH, 1.0)
    colours = []
    for centre in centres:
        selected = usable & (distance >= centre - 0.5) & (distance < centre + 0.5)
        if selected.sum() < MIN_BIN_SAMPLES:
            colours.append(colours[-1] if colours else np.zeros(3))
        else:
            colours.append(np.median(region[selected], axis=0))
    core = ring & (distance_to(~ring) >= 2.5)
    return centres, np.array(colours, dtype=np.float64), np.median(region[core], axis=0)


def rebuild_cammie(frame):
    """Copy of one frame with CAMMIE rebuilt. Returns (frame, interior mask, box)."""
    box = locate_cammie(frame)
    interior = cammie_interior(frame, box)
    centres, colours, tube = engine_profile(frame, box)
    x0, y0, x1, y1 = box
    inside = interior[y0:y1 + 1, x0:x1 + 1]
    # the A's counter: a thin tube along its outline, partial coverage at the inner edge
    coverage = np.zeros(inside.shape)
    for hole in find_counters(frame, box):
        hole = hole[y0:y1 + 1, x0:x1 + 1]
        depth = distance_to(np.pad(~hole, 1, constant_values=True))[1:-1, 1:-1] - 0.5
        coverage = np.maximum(coverage, np.where(hole, np.clip(COUNTER_TUBE + 0.5 - depth, 0.0, 1.0), 0.0))
    glow = inside & (coverage < 0.5)
    distance = distance_to(np.pad(~glow, 1, constant_values=True))[1:-1, 1:-1] - 0.5
    at = np.clip(distance, centres[0], centres[-1])
    colour = np.stack([np.interp(at, centres, colours[:, c]) for c in range(3)], axis=-1)
    colour = colour * (1.0 - coverage[..., None]) + tube * coverage[..., None]
    out = frame.copy()
    region = out[y0:y1 + 1, x0:x1 + 1]
    region[..., :3][inside] = np.clip(np.rint(colour[inside]), 0, 255).astype(np.uint8)
    leftovers = stripe_pixels(out[y0:y1 + 1, x0:x1 + 1])
    if leftovers:
        raise RuntimeError("%d stripe coloured pixels are left in the CAMMIE box: "
                           "the outline has a gap" % leftovers)
    return out, interior, box


def stripe_pixels(region):
    """Count of light blue and pale pink pixels in a region (rgba)."""
    rgb = region[..., :3].astype(np.int32)
    opaque = region[..., 3] > 240
    light_blue = (np.abs(rgb - np.array(LIGHT_BLUE)).max(axis=-1) < 30) & opaque
    pale_pink = (np.abs(rgb - np.array(PALE_PINK)).max(axis=-1) < 10) & opaque
    return int((light_blue | pale_pink).sum())


# ---------------------------------------------------------------------------
# shine mask
# ---------------------------------------------------------------------------

def shine_mask(frame, box):
    """(amount, position) float arrays, frame sized, for the rebuilt frame."""
    (tx0, ty0, tx1, ty1), tube = text_line(frame, box)
    height, width = frame.shape[:2]
    ys, xs = np.mgrid[0:height, 0:width]
    centre = (ty0 + ty1) / 2.0
    sheared = xs + SHEAR * (ys - centre)
    lo, hi = sheared[tube].min(), sheared[tube].max()
    position = np.clip((sheared - lo) / (hi - lo), 0.0, 1.0)
    reach = distance_to(tube, limit=GLOW_REACH + 2)
    amount = neon_weight(frame[..., :3]) * (1.0 - smoothstep(GLOW_REACH * 0.4, GLOW_REACH, reach))
    return amount, position


# ---------------------------------------------------------------------------
# whole sheet
# ---------------------------------------------------------------------------

def load(path):
    return np.array(Image.open(path).convert("RGBA"))


def generate(source_path=DEFAULT_SOURCE):
    """(source, logo, mask) uint8 RGBA arrays for the whole sheet."""
    source = load(source_path)
    logo = source.copy()
    mask = np.zeros_like(source)
    mask[..., 3] = 255
    for (x, y, w, h) in FRAMES:
        frame, _fill, box = rebuild_cammie(source[y:y + h, x:x + w])
        logo[y:y + h, x:x + w] = frame
        amount, position = shine_mask(frame, box)
        mask[y:y + h, x:x + w, 0] = np.rint(amount * 255.0).astype(np.uint8)
        mask[y:y + h, x:x + w, 1] = np.rint(position * 255.0).astype(np.uint8)
    return source, logo, mask


def save_png(array, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    Image.fromarray(array, "RGBA").save(path, optimize=True)


def write_crops(source, logo, folder):
    """Before and after crops of the bottom line of every frame."""
    os.makedirs(folder, exist_ok=True)
    for index, (x, y, w, h) in enumerate(FRAMES):
        box = locate_cammie(source[y:y + h, x:x + w])
        (tx0, ty0, tx1, ty1), _tube = text_line(source[y:y + h, x:x + w], box)
        crop = (max(tx0 - 30, 0), max(ty0 - 30, 0), min(tx1 + 30, w), min(ty1 + 30, h))
        panels = []
        for sheet in (source, logo):
            frame = Image.fromarray(sheet[y:y + h, x:x + w], "RGBA")
            backdrop = Image.new("RGBA", frame.size, (40, 40, 40, 255))
            backdrop.alpha_composite(frame)
            panels.append(backdrop.convert("RGB").crop(crop))
        both = Image.new("RGB", (panels[0].width, panels[0].height * 2))
        both.paste(panels[0], (0, 0))
        both.paste(panels[1], (0, panels[0].height))
        both.save(os.path.join(folder, "frame%d_before_after.png" % index))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--mask-output", default=DEFAULT_MASK_OUTPUT)
    parser.add_argument("--crops", help="folder for before/after crops of every frame")
    parser.add_argument("--check", action="store_true",
                        help="write nothing; exit 1 when the committed pngs are not what this generates")
    args = parser.parse_args(argv)

    source, logo, mask = generate(args.source)
    if args.crops:
        write_crops(source, logo, args.crops)
    if args.check:
        stale = [path for path, array in ((args.output, logo), (args.mask_output, mask))
                 if not os.path.exists(path) or not np.array_equal(load(path), array)]
        for path in stale:
            print("stale: " + path)
        return 1 if stale else 0
    save_png(logo, args.output)
    save_png(mask, args.mask_output)
    changed = int((logo != source).any(axis=-1).sum())
    print("wrote %s (%d pixels changed) and %s" % (args.output, changed, args.mask_output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
