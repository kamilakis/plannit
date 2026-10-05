"""Run a plannit project's design.py WITHOUT Blender: bpy/mathutils mocked, the real engine geometry code records
SHAPES/WALLS/OPENINGS — writes the same JSON as the svg pass (out/renders/model-dump.json), shape for shape (checked
6 Oct 2026 against a Blender dump). For sheets and clash checks when debof is asleep.
usage: python3 tools/nobl.py <project> <out.json> [mode]   (mode: svg | interior | night | cutaway | plan | glb)"""
import sys, os, math, types, json, runpy
from unittest.mock import MagicMock
sys.modules['bpy'] = MagicMock()
class Vector(tuple):
    def __new__(c, v=(0, 0, 0)): return tuple.__new__(c, tuple(float(a) for a in v))
    def __add__(s, o): return Vector(a + b for a, b in zip(s, o))
    def __sub__(s, o): return Vector(a - b for a, b in zip(s, o))
    def __mul__(s, k): return Vector(a * k for a in s) if not isinstance(k, tuple) else sum(a * b for a, b in zip(s, k))
    __rmul__ = __mul__
    def __truediv__(s, k): return Vector(a / k for a in s)
    def __neg__(s): return Vector(-a for a in s)
    @property
    def length(s): return math.sqrt(sum(a * a for a in s))
    def normalized(s): l = s.length or 1; return s / l
    def to_track_quat(s, *a): return MagicMock()
    def cross(s, o): return Vector((s[1]*o[2]-s[2]*o[1], s[2]*o[0]-s[0]*o[2], s[0]*o[1]-s[1]*o[0]))
    def dot(s, o): return sum(a * b for a, b in zip(s, o))
    x = property(lambda s: s[0]); y = property(lambda s: s[1]); z = property(lambda s: s[2])
mu = types.ModuleType('mathutils'); mu.Vector = Vector; mu.Matrix = MagicMock(); mu.Euler = MagicMock(); sys.modules['mathutils'] = mu
PROJECT = os.path.abspath(sys.argv[1]); mode = sys.argv[3] if len(sys.argv) > 3 else 'svg'
sys.path.insert(0, PROJECT); sys.path.append(os.path.join(PROJECT, 'plannit'))
os.chdir(PROJECT)
import existing as X, views
from engine.blender import ctx
ctx.setup([mode], PROJECT, views, X.CEIL)
from engine.blender import materials
materials.library()
runpy.run_path(os.path.join(PROJECT, 'design.py'), run_name='design')
json.dump({'walls': ctx.WALLS, 'openings': ctx.OPENINGS, 'shapes': ctx.SHAPES}, open(sys.argv[2], 'w'))
print('shapes', len(ctx.SHAPES), 'walls', len(ctx.WALLS))
