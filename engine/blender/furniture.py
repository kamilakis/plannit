"""Parametric furniture: chairs, speakers, framed art, a library bookcase, beds, an outdoor lounge chair."""
import math
import bpy
from .ctx import CEIL, FURNISHED, SHAPES
from .geometry import box, cyl, disc, rbox, link, rod
from .materials import BOOKC, M

# ---- loose furniture (2026-10-08). A design marks what a tenant would bring — beds, sofas, chairs, desks, books,
# appliances, rugs, art, the things on the counters — between loose_start() and loose_end(); what stays is the
# finished flat: walls, built-in joinery, the kitchen, sanitary ware, lights. Furnished (the default) the markers
# do nothing; with UNFURNISHED (ctx.py) everything made in between is deleted again at loose_end(), so the calls
# in between still run in the same order and consume the same random numbers.
_LOOSE = []
def loose_start():
    assert not _LOOSE, 'loose_start() twice without loose_end()'
    _LOOSE.append((set(bpy.data.objects), len(SHAPES)))

def loose_end():
    before, n = _LOOSE.pop()
    if FURNISHED: return
    for o in [o for o in bpy.data.objects if o not in before]: bpy.data.objects.remove(o, do_unlink=True)
    del SHAPES[n:]

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
    loose_start()                                                         # the books are the tenant's
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
    loose_end()

def office_chair(cx, cz, face='N'):     # face: the way the sitter looks — 'N' (-z, the default), 'S', 'W' (-x), 'E'
    for k in range(5):
        a = k * 2 * math.pi / 5
        x1, z1 = cx + 0.30 * math.cos(a), cz + 0.30 * math.sin(a)
        box(min(cx, x1) - 0.015, max(cx, x1) + 0.015, min(cz, z1) - 0.015, max(cz, z1) + 0.015, 0.06, 0.09, 'black', name='chair_star')
        cyl(x1, z1, 0.0, 0.06, 0.025, 'black', 12)
    cyl(cx, cz, 0.09, 0.44, 0.025, 'steel', 16)
    box(cx - 0.25, cx + 0.25, cz - 0.24, cz + 0.24, 0.44, 0.52, 'speaker', 0.03, 4, name='chair_seat')
    # the back sits behind the sitter: on +z for 'N' (as it always was), -z for 'S', +x for 'W', -x for 'E'
    sgn = {'N': 1, 'S': -1, 'W': 1, 'E': -1}[face]
    if face in ('N', 'S'):
        box(cx - 0.23, cx + 0.23, *sorted((cz + sgn * 0.20, cz + sgn * 0.26)), 0.60, 1.10, 'speaker', 0.03, 4, name='chair_back')
        box(cx - 0.02, cx + 0.02, *sorted((cz + sgn * 0.22, cz + sgn * 0.26)), 0.44, 0.62, 'black', name='chair_spine')
    else:
        box(*sorted((cx + sgn * 0.20, cx + sgn * 0.26)), cz - 0.23, cz + 0.23, 0.60, 1.10, 'speaker', 0.03, 4, name='chair_back')
        box(*sorted((cx + sgn * 0.22, cx + sgn * 0.26)), cz - 0.02, cz + 0.02, 0.44, 0.62, 'black', name='chair_spine')

def bed(x0, x1, z0, z1, head, cover):     # head: 'W' (at x0) | 'N' (at z0) | 'S' (at z1)
    box(x0 + 0.05, x1 - 0.05, z0 + 0.05, z1 - 0.05, 0.0, 0.12, 'black', name='bed_base')
    box(x0, x1, z0, z1, 0.12, 0.30, 'oak', 0.01, name='bed_frame')
    box(x0 + 0.03, x1 - 0.03, z0 + 0.03, z1 - 0.03, 0.30, 0.52, 'linen', 0.05, 4, name='mattress')
    if head == 'W':
        box(x0 + 0.55, x1 - 0.02, z0 + 0.01, z1 - 0.01, 0.50, 0.56, cover, 0.04, 4, name='duvet')
        for zz in (z0 + 0.1, (z0 + z1) / 2 + 0.02): box(x0 + 0.08, x0 + 0.45, zz, zz + (z1 - z0) / 2 - 0.12, 0.52, 0.66, 'linen', 0.06, 4, name='pillow')
    elif head == 'S':
        box(x0 + 0.01, x1 - 0.01, z0 + 0.02, z1 - 0.55, 0.50, 0.56, cover, 0.04, 4, name='duvet')
        for xx in (x0 + 0.1, (x0 + x1) / 2 + 0.02): box(xx, xx + (x1 - x0) / 2 - 0.12, z1 - 0.45, z1 - 0.08, 0.52, 0.66, 'linen', 0.06, 4, name='pillow')
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


def hanging_egg_chair(cx, cz, face, shell='rattan', stand='black', cushion='linen'):
    """A hanging egg chair on a C-stand: an open-fronted basket of rattan ribs hung from a hook and spring,
    seat and back cushions inside; the stand's post rises behind it and arcs over, its foot a C on the floor.
    (cx, cz) = the basket's centre in plan; face = the way the opening looks, (fx, fz) along x or z."""
    fx, fz = face; sx, sz = -fz, fx
    A, B, C, H = 0.50, 0.44, 0.62, 0.98                    # half-width, half-depth, half-height, centre height
    def P(u, v, w): return (cx + sx * u + fx * v, cz + sz * u + fz * v, H + w)   # side, forward, up -> plan point
    def egg(t, p): return P(A * math.sin(t) * math.sin(p), B * math.sin(t) * math.cos(p), -C * math.cos(t))
    N = 12                                                  # segments per meridian
    for k in range(16):                                     # meridians; the front ones stop low (the opening)
        p = 2 * math.pi * k / 16
        top = math.pi if math.cos(p) < 0.35 else 1.15
        ts = [top * i / N for i in range(N + 1)]
        for t0, t1 in zip(ts, ts[1:]): rod(egg(t0, p), egg(t1, p), 0.008, shell)
    for t in (0.45, 0.85, 1.15, 1.6, 2.1, 2.6):             # rings: full low down, the back arc higher up
        ps = [2 * math.pi * i / 32 for i in range(33)]
        for p0, p1 in zip(ps, ps[1:]):
            if t > 1.2 and math.cos((p0 + p1) / 2) > 0.35: continue
            rod(egg(t, p0), egg(t, p1), 0.009 if t != 1.15 else 0.014, shell)
    # cushions: a seat in the bowl, a back leaning against the rear ribs
    box(*sorted((P(-0.30, -0.22, 0)[0], P(0.30, 0.20, 0)[0])), *sorted((P(-0.30, -0.22, 0)[1], P(0.30, 0.20, 0)[1])),
        H - 0.42, H - 0.30, cushion, 0.05, 4, name='egg_seat')
    bx, bz, _ = P(0, -0.26, 0)
    _slab(bx, bz, H + 0.02, 0.56, 0.12, 0.62, face, math.radians(12), cushion, 'egg_back')
    # hook, spring, stand: the post behind, an arc over the top, a C-shaped foot on the floor
    rod(P(0, 0, C - 0.02), P(0, 0, C + 0.16), 0.012, stand)
    rod(P(0, 0, C + 0.16), P(0, 0, C + 0.30), 0.02, 'steel' if 'steel' in M else stand)
    post = -0.78
    rod(P(0, post, -H), P(0, post, C + 0.32), 0.03, stand)                       # the post, behind the basket
    pts = [(post * math.cos(a), C + 0.32 + 0.15 * math.sin(a)) for a in [math.pi / 2 * i / 8 for i in range(9)]]
    for (v0, w0), (v1, w1) in zip(pts, pts[1:]): rod(P(0, v0, w0), P(0, v1, w1), 0.03, stand)   # arcs over the top
    rod(P(0, 0, C + 0.47), P(0, 0, C + 0.30), 0.012, stand)                      # down to the spring
    R = 0.55                                                                     # the foot: a C, open to the front
    ring = [(R * math.sin(a), post + R - R * math.cos(a)) for a in [math.radians(-135 + 270 * i / 18) for i in range(19)]]
    for (u0, v0), (u1, v1) in zip(ring, ring[1:]): rod(P(u0, v0, -H + 0.02), P(u1, v1, -H + 0.02), 0.025, stand)
