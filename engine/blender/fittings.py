"""Fittings built from the model: curtains and blinds, the shell (walls, beams, columns) from the
master file, floors from the proposal's rooms, stair flights."""
import math
from mathutils import Vector
from .ctx import MODE, CEIL
from .geometry import box, wall, rod, floor
from .. import model

# Curtains. Depths are measured from the wall CENTRELINE, so everything must clear E/2 = 0.125 or it
# ends up buried in the wall. The light sheer is drawn across the glass; the dark blackout is what
# actually blocks the light — gathered into pleats at a jamb where there is floor to stack it, or
# rolled up at the head where furniture (counter, fridge, headboard, speaker) leaves no room.
SHEER_D, DRAPE_D = 0.155, 0.30
# 2026-09-19: at night the curtains are OPEN. A sheer drawn across the glass catches the interior
# light and renders as a flat glowing panel, so every window read as a blank white rectangle instead
# of as a window. By day it stays drawn (that is what softens the sun); at night it is pulled aside
# into its own small stack, or rolled up next to the blackout on the blind windows.
CURTAINS_OPEN = (MODE == 'night')

def _span(f, c, d0, d1):
    a, b = c + f * d0, c + f * d1
    return (a, b) if a < b else (b, a)

def curtain(along_x, a, b, c, f, sides='both', bot=0.0, drawn_open=None):
    """Floor-length drapes: sheer across the glass, blackout gathered in pleats at `sides` ('a','b','both').
    drawn_open: True/False forces this one open or closed; None follows the mode (open at night)."""
    CURTAINS_OPEN = globals()['CURTAINS_OPEN'] if drawn_open is None else drawn_open
    top = CEIL - 0.10
    s0, s1 = _span(f, c, SHEER_D - 0.012, SHEER_D + 0.012)
    t0, t1 = _span(f, c, 0.13, 0.42)
    ta = a - (0.34 if sides in ('both', 'a') else 0.05)
    tb = b + (0.34 if sides in ('both', 'b') else 0.05)
    if along_x: box(ta, tb, t0, t1, top + 0.02, top + 0.07, 'black', name='curtain_track')
    else: box(t0, t1, ta, tb, top + 0.02, top + 0.07, 'black', name='curtain_track')
    if not CURTAINS_OPEN:                                   # sheer drawn across the glass (daytime)
        if along_x: box(a - 0.03, b + 0.03, s0, s1, bot, top, 'curtain_light', 0.012, 2, name='curtain')
        else: box(s0, s1, a - 0.03, b + 0.03, bot, top, 'curtain_light', 0.012, 2, name='curtain')
    jambs = ([(a, -1)] if sides in ('both', 'a') else []) + ([(b, 1)] if sides in ('both', 'b') else [])
    for jamb, away in jambs:
        if CURTAINS_OPEN:                                   # ...otherwise gathered beside the blackout
            for i in range(2):
                u0 = jamb + away * (0.03 + i * 0.062); u1 = u0 + away * 0.055
                lo, hi = min(u0, u1), max(u0, u1)
                d0, d1 = _span(f, c, 0.145, 0.205)
                if along_x: box(lo, hi, d0, d1, 0.0, top, 'curtain_light', 0.014, 3, name='curtain')
                else: box(d0, d1, lo, hi, 0.0, top, 'curtain_light', 0.014, 3, name='curtain')
        for i in range(4):
            # Pleats read as cloth only if their section stays roughly square: a deep, narrow box with a
            # big bevel just turns into a cylinder and the whole stack looks like a bundle of pipes.
            u0 = jamb + away * (0.02 + i * 0.075); u1 = u0 + away * 0.068
            lo, hi = min(u0, u1), max(u0, u1)
            d = DRAPE_D + (0.03 if i % 2 == 0 else -0.03)   # alternating in/out gives the gathered wave
            d0, d1 = _span(f, c, d - 0.038, d + 0.038)
            if along_x: box(lo, hi, d0, d1, 0.0, top, 'curtain_dark', 0.015, 3, name='curtain')
            else: box(d0, d1, lo, hi, 0.0, top, 'curtain_dark', 0.015, 3, name='curtain')

def blind(along_x, a, b, c, f, sill, head, bot=None):
    """Where drapes have nowhere to stack: sheer over the glass, blackout roller rolled up at the head."""
    bot = sill if bot is None else bot
    s0, s1 = _span(f, c, 0.133, 0.157)
    r0, r1 = _span(f, c, 0.16, 0.30)
    # Open at night: the sheer rolls up too, into a second lighter bundle under the blackout roller.
    sh0, sh1 = (head + 0.02, head + 0.12) if CURTAINS_OPEN else (bot, head + 0.14)
    sm = 0.06 if CURTAINS_OPEN else 0.012          # rolled: chunkier and rounded; drawn: a flat panel
    if along_x:
        box(a - 0.02, b + 0.02, s0, s1 if not CURTAINS_OPEN else s1 + 0.05, sh0, sh1, 'curtain_light', sm, 4, name='curtain')
        box(a - 0.06, b + 0.06, r0, r1, head + 0.16, head + 0.30, 'curtain_dark', 0.055, 4, name='blind_roll')
    else:
        box(s0, s1 if not CURTAINS_OPEN else s1 + 0.05, a - 0.02, b + 0.02, sh0, sh1, 'curtain_light', sm, 4, name='curtain')
        box(r0, r1, a - 0.06, b + 0.06, head + 0.16, head + 0.30, 'curtain_dark', 0.055, 4, name='blind_roll')


def shell(X, PR):
    """Every wall, existing or new, from model.walls(X, PR); the concrete frame (beams, columns) from X."""
    model.defaults(X, PR)
    # Every wall, existing or new, comes from model.walls(): kept walls cut short or re-opened as the proposal
    # says, bricked-up openings as 'infill', the new partitions as 'new'. Nothing about a wall is typed here.
    for _wid, x0, x1, z0, z1, _ops, _tag, _cut in model.walls(X, PR):
        wall(x0, x1, z0, z1, [(a, b, sl, hd, 'door' if k == 'closet' else k) for a, b, sl, hd, k in _ops],
             tag=_tag, new_openings=_cut)
    # the concrete frame (measured 23 Sep): downstand beams and columns. Unsurveyed rooms may have more.
    for x0, x1, z0, z1, soffit, _src in X.BEAMS.values(): box(x0, x1, z0, z1, soffit, CEIL, 'wall', name='beam')
    for x0, x1, z0, z1, _src in X.COLUMNS.values(): box(x0, x1, z0, z1, 0.0, CEIL, 'wall', name='column')


def room_floors(rooms, walls, wet, wet_mat='microcement', wet_h=0.002):
    """A floor per room rectangle (`wet` rooms in `wet_mat`, a little proud), plus a threshold under every door."""
    for _name, (_rects, _lbl) in rooms.items():
        for _r in _rects:
            if _name in wet: floor(*_r, wet_mat, wet_h)
            else: floor(*_r)
    for _wid, x0, x1, z0, z1, _ops, _tag, _cut in walls:        # thresholds through the wall at each door
        for a, b, sl, hd, k in _ops:
            if k != 'window' and sl == 0:
                floor(a, b, z0, z1) if (x1 - x0) >= (z1 - z0) else floor(x0, x1, a, b)


def tread(x0, x1, z0, z1, top, kind):
    box(x0, x1, z0, z1, top - 0.03, top, 'marble', name='stair_' + kind)
    box(x0, x1, z0, z1, top - 0.30, top - 0.03, 'plaster', name='stairbody_' + kind)
def flight(x0, x1, z_start, north, h_start, up, kind, rail_x, rise, run, steps=7):
    """One straight flight of `steps` treads with balusters and a handrail."""
    RISE, RUN = rise, run
    sgn = 1 if up else -1
    for i in range(steps):
        zz0 = z_start - RUN * (i + 1) if north else z_start + RUN * i
        zz1 = zz0 + RUN
        top = h_start + sgn * RISE * (i + 1)
        tread(x0, x1, zz0, zz1, top, kind)
        zb = (zz0 + zz1) / 2
        rod((rail_x, zb, top), (rail_x, zb, top + 0.90), 0.008)                     # baluster
    z_end = z_start - RUN * steps if north else z_start + RUN * steps
    rod((rail_x, z_start, h_start + 0.90), (rail_x, z_end, h_start + sgn * RISE * (steps + 1) + 0.90), 0.022)   # handrail
