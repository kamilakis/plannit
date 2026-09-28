"""Build one project's model in Blender 4.5 and render it, or export it. Knows no facts about any flat.
PLANNIT_PROJECT=<project> blender -b -P engine/blender/build.py -- MODE CAMS PCT SAMPLES
  MODE  interior | night | cutaway | plan | glb   (+ -b / -c / -d for palette B, C, D) | svg (the model dump)
  CAMS  comma list (or 'all')
(was renovation-design/scene.py; the render farm runs it through farm/pack.sh's scene.py entry)

The project folder supplies:
  existing.py   the flat today (master file; CEIL, EXT, WALLS, OPENINGS, BEAMS, COLUMNS, FITTINGS, STAIR, ROOMS, …)
  proposal.py   the renovation as changes: DEMOLISH, NEW_WALLS, ROOMS, … (engine/model.py makes the walls)
  views.py      palettes, section heights (CUTS), SKY, SUN, CAMERAS — data only
  design.py     furniture, fittings, lights, people: calls into engine.blender.api, in build order
Plan coords: x east, z south, metres, h = height above floor. Blender: X = x, Y = -z, Z = h.
Env: RENDER_OUT (default <project>/out/renders), RENDER_DEVICE=OPTIX|CUDA|CPU, NIGHT_EV, RENDER_FORCE=1,
RENDER_HASHONLY=1 (fingerprints only, no render — tools/proof.sh)."""
import bpy, os, sys, runpy

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
# the project this builds: its model files (existing.py, proposal.py), views.py, design.py and out/ (renders, manifest)
PROJECT = os.environ.get('PLANNIT_PROJECT') or sys.exit('set PLANNIT_PROJECT to the project folder')
PROJECT = os.path.abspath(PROJECT)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # holds engine/
sys.path.insert(0, PROJECT)
if ROOT not in sys.path: sys.path.append(ROOT)

import existing as X                     # plain data: the single ceiling height lives here
import views                             # plain data: palettes and cut heights are needed before any geometry
from engine.blender import ctx
ctx.setup(argv, PROJECT, views, X.CEIL)

# Order from here on is the order the objects are made in; the render fingerprints depend on it.
bpy.ops.wm.read_factory_settings(use_empty=True)
from engine.blender import materials
materials.library()
runpy.run_path(os.path.join(PROJECT, 'design.py'), run_name='design')
from engine.blender import render
render.run(views)
