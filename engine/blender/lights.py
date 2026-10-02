"""Lights: point lights, hidden LED area lights, recessed and surface ceiling luminaires."""
import bpy, math
from .ctx import CEIL, INTERIOR, MODE, NIGHT_LIGHTS
from .geometry import box, link

LIGHTS = []
def pointlight(x, z, h, watts=35, radius=0.05, color=(1.0, 0.86, 0.7), spot=False):
    L = bpy.data.lights.new('l', 'SPOT' if spot else 'POINT'); L.energy = watts; L.shadow_soft_size = radius; L.color = color
    if spot: L.spot_size = math.radians(110); L.spot_blend = 0.6
    o = link(bpy.data.objects.new('l', L)); o.location = (x, -z, h); LIGHTS.append(o); return o

WARM = (1.0, 0.78, 0.55)     # ~2700-3000 K warm white
def lit(night=False):
    """Is a light with this night tag on in this render? night: False = off in a 'tagged' night scene,
    True = on day and night, 'only' = a night light (motion-sensor path lights), off in the day renders."""
    if MODE == 'night': return NIGHT_LIGHTS != 'tagged' or bool(night)
    return night != 'only'

def led(x0, x1, z0, z1, h, watts, dirn='down', thick=0.03, night=False):
    """Hidden LED: an area light whose source is never seen (not visible to camera or reflections).
    dirn: down | up | east | west | north | south (plan: east = +x, south = +z). night: see lit()."""
    if not INTERIOR or not lit(night): return
    # ceiling wall-wash slots stay soft; low accents (under furniture, behind headboards) carry the mood
    watts *= 0.55 if h >= CEIL - 0.05 else (1.5 if dirn == 'up' or h < 1.0 else 1.0)
    L = bpy.data.lights.new('led', 'AREA'); L.shape = 'RECTANGLE'; L.energy = watts; L.color = WARM
    dx, dz = max(x1 - x0, 0.02), max(z1 - z0, 0.02)
    rot, sx, sy = {'down': ((0, 0, 0), dx, dz), 'up': ((math.pi, 0, 0), dx, dz),
                   'east': ((0, -math.pi / 2, 0), thick, dz), 'west': ((0, math.pi / 2, 0), thick, dz),
                   'north': ((math.pi / 2, 0, 0), dx, thick), 'south': ((-math.pi / 2, 0, 0), dx, thick)}[dirn]
    L.size, L.size_y = sx, sy
    o = link(bpy.data.objects.new('led', L)); o.location = ((x0 + x1) / 2, -(z0 + z1) / 2, h); o.rotation_euler = rot
    o.visible_camera = False; o.visible_glossy = False; o.visible_transmission = False
    LIGHTS.append(o); return o

def ceiling_light(x0, x1, z0, z1, watts=45, night=False):
    """A recessed linear ceiling luminaire: a glowing panel set into a plaster reveal, plus a hidden
    area light doing the real work. Bigger and brighter than a spot, so it actually reads in a render —
    the house rule is no pendants and no lamps, not no light."""
    box(x0 - 0.04, x1 + 0.04, z0 - 0.04, z1 + 0.04, CEIL - 0.05, CEIL - 0.001, 'white_matte', name='light_trim')
    box(x0, x1, z0, z1, CEIL - 0.042, CEIL - 0.005, 'downlight' if lit(night) else 'white_matte', name='light_panel')
    led(x0, x1, z0, z1, CEIL - 0.055, watts, 'down', night=night)

def ceiling_fixture(x0, x1, z0, z1, watts=50, night=False):
    """The visible general light the owner asked for in the living room and the study (2026-09-21):
    a slim dark body hung just below the slab with a lit panel let into its underside — the same family
    as the island's ceiling hood, so the two read as one design, instead of a recessed white square
    that disappears into the plaster. One per room, each on its own switch."""
    box(x0 - 0.05, x1 + 0.05, z0 - 0.05, z1 + 0.05, CEIL - 0.10, CEIL, 'black', name='light_body')
    box(x0, x1, z0, z1, CEIL - 0.105, CEIL - 0.098, 'downlight' if lit(night) else 'white_matte', name='light_panel')
    led(x0, x1, z0, z1, CEIL - 0.12, watts, 'down', night=night)
