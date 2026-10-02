"""Parametric furniture: chairs, speakers, framed art, a library bookcase, beds, an outdoor lounge chair."""
import math
import bpy
from .ctx import CEIL
from .geometry import box, cyl, disc, rbox, link
from .materials import BOOKC, M

def counter_chair(cx, cz, face='S'):     # face: 'S' = faces south (sits on the north side), 'W' = faces west
    box(cx - 0.21, cx + 0.21, cz - 0.21, cz + 0.21, 0.63, 0.67, 'oak', 0.01, name='cseat')
    for dx in (-0.18, 0.18):
        for dz in (-0.18, 0.18): box(cx + dx - 0.012, cx + dx + 0.012, cz + dz - 0.012, cz + dz + 0.012, 0.0, 0.63, 'black', name='leg')
    if face == 'S':
        box(cx - 0.19, cx + 0.19, cz + 0.16, cz + 0.18, 0.25, 0.26, 'black', name='footrest')
        box(cx - 0.20, cx + 0.20, cz - 0.20, cz - 0.17, 0.80, 0.92, 'oak', 0.008, name='cback')
        for dx in (-0.18, 0.18): box(cx + dx - 0.01, cx + dx + 0.01, cz - 0.195, cz - 0.175, 0.67, 0.81, 'black', name='post')
    else:
        box(cx - 0.18, cx - 0.16, cz - 0.19, cz + 0.19, 0.25, 0.26, 'black', name='footrest')
        box(cx + 0.17, cx + 0.20, cz - 0.20, cz + 0.20, 0.80, 0.92, 'oak', 0.008, name='cback')
        for dz in (-0.18, 0.18): box(cx + 0.175, cx + 0.195, cz + dz - 0.01, cz + dz + 0.01, 0.67, 0.81, 'black', name='post')

def chair(cx, cz, face):          # face: +1 = faces south (+z), -1 = faces north
    box(cx - 0.22, cx + 0.22, cz - 0.21, cz + 0.21, 0.43, 0.47, 'oak', 0.01, name='seat')
    for dx in (-0.19, 0.19):
        for dz in (-0.18, 0.18): box(cx + dx - 0.012, cx + dx + 0.012, cz + dz - 0.012, cz + dz + 0.012, 0.0, 0.43, 'black', name='leg')
    bz = cz - face * 0.19
    box(cx - 0.21, cx + 0.21, bz - 0.012, bz + 0.012, 0.62, 0.82, 'oak', 0.008, name='back')
    for dx in (-0.19, 0.19): box(cx + dx - 0.01, cx + dx + 0.01, bz - 0.01, bz + 0.01, 0.47, 0.64, 'black', name='post')

def tower(x, z):
    box(x - 0.15, x + 0.15, z - 0.11, z + 0.11, 0.03, 1.05, 'speaker', 0.012, name='front_speaker')
    box(x - 0.16, x + 0.16, z - 0.12, z + 0.12, 0.0, 0.03, 'black', name='spk_base')
    box(x - 0.151, x + 0.151, z - 0.111, z + 0.111, 1.02, 1.05, 'oak', name='spk_cap')

def artwork(axis, W, f, u0, u1, h0, h1, style, frame='black'):
    """Framed print on a wall. axis 'x': wall plane x=W spanning z u0..u1; 'z': plane z=W spanning x. f = +1/-1 toward the room."""
    w, h = u1 - u0, h1 - h0; uc, hc = (u0 + u1) / 2, (h0 + h1) / 2
    rbox(axis, W, f, u0, u1, 0.0, 0.03, h0, h1, frame, 'art_frame')
    rbox(axis, W, f, u0 + 0.025, u1 - 0.025, 0.03, 0.034, h0 + 0.025, h1 - 0.025, 'art_bg', 'art_canvas')
    def shape(a0, a1, b0, b1, m): rbox(axis, W, f, uc + a0 * w, uc + a1 * w, 0.034, 0.037, hc + b0 * h, hc + b1 * h, m)
    def circ(a, b, r, m):
        d = W + f * 0.036
        if axis == 'x': disc(d, uc + a * w, hc + b * h, r * min(w, h), m, 'x', 0.003)
        else: disc(uc + a * w, d, hc + b * h, r * min(w, h), m, 'z', 0.003)
    if style == 'sun':
        shape(-0.40, 0.40, -0.40, -0.10, 'art_sand'); circ(0.12, 0.10, 0.22, 'art_rust')
    elif style == 'blocks':
        shape(-0.36, 0.02, -0.38, 0.30, 'art_sage'); shape(-0.08, 0.34, -0.10, 0.38, 'art_sand'); shape(-0.08, 0.02, -0.10, 0.30, 'art_navy')
    elif style == 'arch':
        shape(-0.14, 0.14, -0.38, 0.05, 'art_rust'); circ(0.0, 0.05, 0.14 * w / min(w, h), 'art_rust')   # arch = bar + half-width disc
        shape(0.22, 0.36, -0.38, -0.30, 'art_ink')
    elif style == 'line':
        shape(-0.36, 0.36, -0.005, 0.005, 'art_ink'); circ(-0.12, 0.18, 0.12, 'art_navy'); circ(0.20, -0.22, 0.07, 'art_rust')

SEED = [7]
def rnd():
    SEED[0] = (SEED[0] * 1103515245 + 12345) % 2147483648; return SEED[0] / 2147483648
def bookcase(x0, x1, z0, z1, along_x, shelves=(0.0, 0.42, 0.80, 1.18, 1.56, 1.94, 2.32), top=CEIL, plinth=True):
    """Full-height oak library unit; open face toward -x (along z) or +z/-z (along x) — books fill each bay."""
    t = 0.025
    if plinth: box(x0, x1, z0, z1, 0.0, 0.08, 'oak', name='bc_plinth')
    length = (x1 - x0) if along_x else (z1 - z0)
    nb = max(1, round(length / 0.8)); bay = length / nb
    for k in range(nb + 1):
        a = min(k * bay, length - t)
        b0 = 0.08 if plinth else shelves[0] + 0.08 - t
        if along_x: box(x0 + a, x0 + a + t, z0, z1, b0, top, 'oak', name='bc_side')
        else: box(x0, x1, z0 + a, z0 + a + t, b0, top, 'oak', name='bc_side')
    for s in (shelves if not plinth else shelves[1:]):
        if along_x: box(x0 + 0.003, x1 - 0.003, z0, z1 - 0.004, s + 0.08 - t, s + 0.08, 'oak', name='bc_shelf')
        else: box(x0, x1 - 0.004, z0 + 0.003, z1 - 0.003, s + 0.08 - t, s + 0.08, 'oak', name='bc_shelf')
    depth0, depth1 = (z0, z1) if along_x else (x0, x1)
    for k in range(nb):
        for si, s in enumerate(shelves[:-1]):
            if si == 3 and k % 2 == 0: continue                          # a few open bays for objects
            u = k * bay + t + 0.01; end = (k + 1) * bay - 0.01
            while u < end - 0.03:
                w = 0.022 + 0.03 * rnd(); h = 0.22 + 0.10 * rnd(); c = f'book{int(rnd() * len(BOOKC))}'
                if rnd() < 0.08: u += 0.06; continue
                w = min(w, end - u)
                if along_x: box(x0 + u, x0 + u + w, depth0 + 0.03, depth1 - 0.03, s + 0.08, s + 0.08 + h, c, name='book')
                else: box(depth0 + 0.03, depth1 - 0.03, z0 + u, z0 + u + w, s + 0.08, s + 0.08 + h, c, name='book')
                u += w + 0.002

def office_chair(cx, cz):     # faces north (toward the desk)
    for k in range(5):
        a = k * 2 * math.pi / 5
        x1, z1 = cx + 0.30 * math.cos(a), cz + 0.30 * math.sin(a)
        box(min(cx, x1) - 0.015, max(cx, x1) + 0.015, min(cz, z1) - 0.015, max(cz, z1) + 0.015, 0.06, 0.09, 'black', name='chair_star')
        cyl(x1, z1, 0.0, 0.06, 0.025, 'black', 12)
    cyl(cx, cz, 0.09, 0.44, 0.025, 'steel', 16)
    box(cx - 0.25, cx + 0.25, cz - 0.24, cz + 0.24, 0.44, 0.52, 'speaker', 0.03, 4, name='chair_seat')
    box(cx - 0.23, cx + 0.23, cz + 0.20, cz + 0.26, 0.60, 1.10, 'speaker', 0.03, 4, name='chair_back')
    box(cx - 0.02, cx + 0.02, cz + 0.22, cz + 0.26, 0.44, 0.62, 'black', name='chair_spine')

def bed(x0, x1, z0, z1, head, cover):     # head: 'W' | 'N'
    box(x0 + 0.05, x1 - 0.05, z0 + 0.05, z1 - 0.05, 0.0, 0.12, 'black', name='bed_base')
    box(x0, x1, z0, z1, 0.12, 0.30, 'oak', 0.01, name='bed_frame')
    box(x0 + 0.03, x1 - 0.03, z0 + 0.03, z1 - 0.03, 0.30, 0.52, 'linen', 0.05, 4, name='mattress')
    if head == 'W':
        box(x0 + 0.55, x1 - 0.02, z0 + 0.01, z1 - 0.01, 0.50, 0.56, cover, 0.04, 4, name='duvet')
        for zz in (z0 + 0.1, (z0 + z1) / 2 + 0.02): box(x0 + 0.08, x0 + 0.45, zz, zz + (z1 - z0) / 2 - 0.12, 0.52, 0.66, 'linen', 0.06, 4, name='pillow')
    else:
        box(x0 + 0.01, x1 - 0.01, z0 + 0.55, z1 - 0.02, 0.50, 0.56, cover, 0.04, 4, name='duvet')
        for xx in (x0 + 0.1, (x0 + x1) / 2 + 0.02): box(xx, xx + (x1 - x0) / 2 - 0.12, z0 + 0.08, z0 + 0.45, 0.52, 0.66, 'linen', 0.06, 4, name='pillow')


def _slab(cx, cz, h, w, t, l, face, tilt, m, name):
    """A w x t x l slab (side x forward x up) centred at plan (cx, cz, h), leaned back by `tilt` radians and
    turned to face plan direction `face` = (fx, fz)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, -cz, h))
    o = bpy.context.active_object; o.name = name; o.scale = (w, t, l)
    o.rotation_euler = (tilt, 0, math.atan2(-face[0], -face[1]))
    for c in o.users_collection: c.objects.unlink(o)
    o.data.materials.append(M[m]); link(o)
    b = o.modifiers.new('bev', 'BEVEL'); b.width = min(0.02, t / 3); b.segments = 3
    return o

def lounge_chair(cx, cz, face, frame='oak_dark', cushion='linen', w=0.66, d=0.82):
    """A low, laid-back veranda chair: slatted frame, seat cushion, arms, a back reclined ~28 deg.
    (cx, cz) = the seat's centre; face = the direction the sitter looks, (fx, fz) along x or z."""
    # low enough (back top ~0.88) to survive every section cut, so no cut test here
    fx, fz = face; sx, sz = -fz, fx                                  # the sitter's left-right axis
    def bx(f0, f1, s0, s1, h0, h1, m, bev=0.0, name='lounge'):
        xs = sorted((cx + fx * f0 + sx * s0, cx + fx * f1 + sx * s1)); zs = sorted((cz + fz * f0 + sz * s0, cz + fz * f1 + sz * s1))
        box(xs[0], xs[1], zs[0], zs[1], h0, h1, m, bev, name=name)
    for f0 in (-d / 2 + 0.02, d / 2 - 0.06):                          # legs
        for s0 in (-w / 2 + 0.02, w / 2 - 0.06): bx(f0, f0 + 0.04, s0, s0 + 0.04, 0.0, 0.20, frame)
    bx(-d / 2, d / 2, -w / 2, w / 2, 0.20, 0.26, frame, 0.01, 'lounge_frame')
    bx(-d / 2 + 0.06, d / 2 - 0.02, -w / 2 + 0.06, w / 2 - 0.06, 0.26, 0.36, cushion, 0.03, 'lounge_seat')
    for s0 in (-w / 2, w / 2 - 0.05): bx(-d / 2, d / 2 - 0.10, s0, s0 + 0.05, 0.26, 0.52, frame, 0.01, 'lounge_arm')
    tilt, bl = math.radians(28), 0.66                                 # the back: leaned back, its foot at the rear
    rx, rz = cx - fx * (d / 2 - 0.04), cz - fz * (d / 2 - 0.04)
    off = math.sin(tilt) * bl / 2
    _slab(rx - fx * off, rz - fz * off, 0.30 + math.cos(tilt) * bl / 2, w, 0.05, bl, face, tilt, frame, 'lounge_back')
    _slab(rx - fx * (off - 0.06), rz - fz * (off - 0.06), 0.34 + math.cos(tilt) * (bl - 0.06) / 2, w - 0.12, 0.09, bl - 0.08, face, tilt, cushion, 'lounge_cushion')
