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
# 24 Nov: an evening render lights only what the design marks between evening_on() and evening_on(False) — the
# owner's own list of lights, not every lamp the design has gathered
_EV = [False]
def evening_on(on=True): _EV[0] = on
def lit(night=False):
    """Is a light with this night tag on in this render? night: False = off in a 'tagged' night scene,
    True = on day and night, 'only' = a night light (motion-sensor path lights), off in the day renders."""
    if MODE == 'night' and NIGHT_LIGHTS == 'evening': return _EV[0] and night != 'only'   # ~22:00: the marked ones, full
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


def portals(walls, openings, inset=0.01):
    """Cycles light portals (17 Nov) in every window and glazed door of the envelope (walls tagged 'old', kinds window /
    sliding / glazed), facing into the flat: they tell the renderer where the sky comes in, so day interiors clear
    their noise in fewer samples. They add no light and are invisible. 'In' = toward the centre of the envelope's
    walls. Off in the night scene (no sky to guide). Returns how many were made."""
    if not INTERIOR or MODE == 'night': return 0
    old = [w for w in walls if w[4] == 'old']
    if not old: return 0
    cx = (min(w[0] for w in old) + max(w[1] for w in old)) / 2; cz = (min(w[2] for w in old) + max(w[3] for w in old)) / 2
    k = 0
    for x0, x1, z0, z1, along_x, a, b, sill, head, kind, _new, tag in openings:
        if tag != 'old' or kind not in ('window', 'sliding', 'glazed'): continue
        L = bpy.data.lights.new('portal', 'AREA'); L.shape = 'RECTANGLE'
        try: L.cycles.is_portal = True
        except AttributeError: bpy.data.lights.remove(L); return k      # a Blender without portals: nothing lost
        h = (sill + head) / 2
        if along_x:                                   # the wall runs along x: the portal faces +z or -z (plan)
            south = cz > (z0 + z1) / 2
            z = (z1 + inset) if south else (z0 - inset)
            loc, rot = ((a + b) / 2, -z, h), ((-math.pi / 2, 0, 0) if south else (math.pi / 2, 0, 0))
            L.size, L.size_y = b - a, head - sill
        else:                                         # the wall runs along z: the portal faces +x or -x
            east = cx > (x0 + x1) / 2
            x = (x1 + inset) if east else (x0 - inset)
            loc, rot = (x, -(a + b) / 2, h), ((0, -math.pi / 2, 0) if east else (0, math.pi / 2, 0))
            L.size, L.size_y = head - sill, b - a
        o = link(bpy.data.objects.new('portal', L)); o.location = loc; o.rotation_euler = rot; k += 1
    return k
