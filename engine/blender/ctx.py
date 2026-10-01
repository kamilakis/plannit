"""Build state shared by the engine's Blender modules.

build.py calls setup() BEFORE importing any other engine.blender module: they take MODE, CUT, CEIL, …
from here at import time (`from .ctx import MODE, …`), so the values must already be final.
SHAPES / WALLS / OPENINGS are the model's bookkeeping, filled by box() and wall() and read by the
technical sheets (svg / dxf modes)."""
import os

SHAPES = []    # (name, x0, x1, z0, z1, h0, h1, material) — used by MODE 'svg'
WALLS = []     # (x0, x1, z0, z1, tag) per wall piece; tag 'old' (scanned envelope/core) | 'new' | 'infill'
OPENINGS = []  # (x0, x1, z0, z1, along_x, a, b, sill, head, kind, is_new) — read by the technical sheets


def setup(argv, project, views, ceil):
    """argv = the arguments after '--': MODE CAMS PCT SAMPLES. `views` = the project's views module
    (palettes, cut heights); `ceil` = the project's single ceiling height."""
    global MODE, PALETTE, SUFFIX, INTERIOR, CAMS, PCT, SAMPLES, PROJECT, OUT, CEIL, CUT, PAL, PAL_PLANKS, SLIDING_OPEN
    MODE = argv[0] if argv else 'interior'
    # colour scheme: append '-b' to the mode (interior-b, night-b, cutaway-b, plan-b) for palette B; '-c' and
    # '-d' (2026-09-22) are the two stricter candidates C and D. Output files get a matching _b/_c/_d suffix.
    PALETTE = MODE[-1] if MODE[-2:] in ('-b', '-c', '-d') else 'a'
    MODE = MODE[:-2] if PALETTE != 'a' else MODE
    SUFFIX = '' if PALETTE == 'a' else '_' + PALETTE
    INTERIOR = MODE in ('interior', 'night')
    CAMS = argv[1] if len(argv) > 1 else 'all'
    PCT = int(argv[2]) if len(argv) > 2 else 100
    SAMPLES = int(argv[3]) if len(argv) > 3 else 128
    PROJECT = project
    OUT = os.environ.get('RENDER_OUT') or os.path.join(PROJECT, 'out', 'renders')
    CEIL = ceil
    # the section height of the cut-open views: the project's views.CUTS per mode, else the full height
    CUT = views.CUTS.get(MODE, CEIL)
    PAL, PAL_PLANKS = views.PALETTES.get(PALETTE, ({}, {}))
    # how far every 'sliding' opening is slid open: 0 closed .. 1 all panels stacked at its far end (views.SLIDING_OPEN)
    SLIDING_OPEN = float(getattr(views, 'SLIDING_OPEN', 0.0))
