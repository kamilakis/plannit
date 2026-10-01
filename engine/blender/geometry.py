"""Geometry primitives, in plan coordinates (x east, z south, h up; Blender Y = -z). Everything lands in
the 'house' collection; box() also records SHAPES, wall() WALLS and OPENINGS for the technical sheets."""
import bpy, math
from mathutils import Vector
from .ctx import MODE, CUT, CEIL, INTERIOR, SHAPES, WALLS, OPENINGS, SLIDING_OPEN
from .materials import M
S = bpy.context.scene

COL = bpy.data.collections.new('house'); S.collection.children.link(COL)
def link(o): COL.objects.link(o); return o

JIT = 0
def box(x0, x1, z0, z1, h0, h1, m, bevel=0.0, seg=3, name='box'):
    # The 0.2 margin drops things that merely START near the cut, which keeps cutaways clean. Glazing
    # is the exception: a window whose sill sits just under the cut has to survive, or the opening
    # disappears and the wall renders solid — which is exactly how the kitchen window (sill 1.29) went
    # missing from the plan. For glass, drop only if it is genuinely above the cut.
    if MODE in ('cutaway', 'plan', 'glb') and h0 >= (CUT if name == 'glass' else CUT - 0.2): return None
    h1 = min(h1, CUT)
    x0, x1 = sorted((x0, x1)); z0, z1 = sorted((z0, z1))
    SHAPES.append((name, x0, x1, z0, z1, h0, h1, m if isinstance(m, str) else m.name))
    if name == 'wall':               # jitter so butting walls never share a coplanar face (renders as black seams)
        global JIT; JIT = (JIT + 1) % 9; e = 0.0004 * (JIT + 1); x0 -= e; x1 += e; z0 -= e; z1 += e
    me = bpy.data.meshes.new(name)
    X0, X1, Y0, Y1 = x0, x1, -z1, -z0
    v = [(X0, Y0, h0), (X1, Y0, h0), (X1, Y1, h0), (X0, Y1, h0), (X0, Y0, h1), (X1, Y0, h1), (X1, Y1, h1), (X0, Y1, h1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me.from_pydata(v, [], f); me.materials.append(M[m] if isinstance(m, str) else m)
    o = link(bpy.data.objects.new(name, me))
    if bevel > 0:
        b = o.modifiers.new('bev', 'BEVEL'); b.width = bevel; b.segments = seg; b.limit_method = 'NONE'
        o.modifiers.new('ws', 'WEIGHTED_NORMAL')
        for p in me.polygons: p.use_smooth = True
    return o

def cyl(x, z, h0, h1, r, m, verts=32, r2=None, name='cyl'):
    if not INTERIOR and (h0 >= CUT - 0.2 or h1 > CUT + 0.3): return None
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r if r2 is None else r2, depth=h1 - h0,
                                    location=(x, -z, (h0 + h1) / 2))
    o = bpy.context.active_object; o.name = name
    o.data.materials.append(M[m]); bpy.ops.object.shade_smooth()
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def sphere(x, z, h, r, m, sx=1, sy=1, sz=1):
    if not INTERIOR and m == 'bulb': return None
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=r, location=(x, -z, h))
    o = bpy.context.active_object; o.scale = (sx, sy, sz); o.data.materials.append(M[m]); bpy.ops.object.shade_smooth()
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def disc(x, z, h, r, m, axis, t=0.01):
    if not INTERIOR and h - r >= CUT - 0.2: return None
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=r, depth=t, location=(x, -z, h),
                                        rotation=(math.pi / 2, 0, 0) if axis == 'z' else (0, math.pi / 2, 0))
    o = bpy.context.active_object; o.data.materials.append(M[m])
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def wall(x0, x1, z0, z1, openings=(), m='wall', tag='old', new_openings=()):
    """Axis-aligned wall; openings = (along0, along1, sill, head, kind) in plan coords along the long axis.
    tag: 'old' = the scanned envelope and stair core, 'new' = built in the renovation, 'infill' = an
    opening bricked up. new_openings lists the `along0` values cut fresh into an existing wall.
    Only the bookkeeping (WALLS / OPENINGS, the svg mode's model dump) reads the tags: same geometry either way."""
    along_x = (x1 - x0) >= (z1 - z0)
    lo, hi = (x0, x1) if along_x else (z0, z1)
    def piece(a, b, h0, h1):
        if b - a < 1e-4 or h1 - h0 < 1e-4: return
        if along_x: box(a, b, z0, z1, h0, h1, m, name='wall'); WALLS.append((a, b, z0, z1, tag))
        else: box(x0, x1, a, b, h0, h1, m, name='wall'); WALLS.append((x0, x1, a, b, tag))
    u = lo
    for a, b, sill, head, kind in sorted(openings):
        piece(u, a, 0, CEIL)
        piece(a, b, 0, sill); piece(a, b, head, CEIL)
        if kind == 'sliding': sliding_door(along_x, a, b, (z0 + z1) / 2 if along_x else (x0 + x1) / 2, sill, head)
        elif kind in ('window', 'glazed'): window_frame(along_x, a, b, (z0 + z1) / 2 if along_x else (x0 + x1) / 2, sill, head)
        OPENINGS.append((x0, x1, z0, z1, along_x, a, b, sill, head, kind, tag == 'new' or a in new_openings, tag))
        u = b
    piece(u, hi, 0, CEIL)

def window_frame(along_x, a, b, c, sill, head, t=0.05, d=0.06):
    def fb(a0, a1, h0, h1, m='frame'):
        if along_x: box(a0, a1, c - d / 2, c + d / 2, h0, h1, m, name='frame')
        else: box(c - d / 2, c + d / 2, a0, a1, h0, h1, m, name='frame')
    fb(a, a + t, sill, head); fb(b - t, b, sill, head); fb(a, b, sill, sill + t); fb(a, b, head - t, head)
    if b - a > 1.2: fb((a + b) / 2 - t / 2, (a + b) / 2 + t / 2, sill, head)
    if along_x: box(a, b, c - 0.004, c + 0.004, sill, head, 'glass', name='glass')
    else: box(c - 0.004, c + 0.004, a, b, sill, head, 'glass', name='glass')

def sliding_door(along_x, a, b, c, sill, head, t=0.05, track=0.07):
    """Glazed sliding door: a perimeter frame and one framed glass panel per track (~1.2 m each), slid
    SLIDING_OPEN of the way to the far end `b` (0 = closed across the opening, 1 = stacked at b)."""
    def fb(a0, a1, d0, d1, h0, h1, m='frame', name='frame'):
        if along_x: box(a0, a1, d0, d1, h0, h1, m, name=name)
        else: box(d0, d1, a0, a1, h0, h1, m, name=name)
    n = max(2, math.ceil((b - a) / 1.2)); w = (b - a) / n + t        # panels overlap by one stile
    depth = n * track
    fb(a, a + t, c - depth / 2, c + depth / 2, sill, head); fb(b - t, b, c - depth / 2, c + depth / 2, sill, head)
    fb(a, b, c - depth / 2, c + depth / 2, sill, sill + 0.02); fb(a, b, c - depth / 2, c + depth / 2, head - t, head)
    for i in range(n):
        p0 = a + i * (b - a) / n - (t / 2 if i else 0)
        p0 += SLIDING_OPEN * ((b - w) - p0)
        d = c + (i - (n - 1) / 2) * track
        fb(p0, p0 + t, d - 0.02, d + 0.02, sill + 0.02, head - t); fb(p0 + w - t, p0 + w, d - 0.02, d + 0.02, sill + 0.02, head - t)
        fb(p0, p0 + w, d - 0.02, d + 0.02, sill + 0.02, sill + 0.02 + t); fb(p0, p0 + w, d - 0.02, d + 0.02, head - 2 * t, head - t)
        fb(p0 + t, p0 + w - t, d - 0.004, d + 0.004, sill + 0.02 + t, head - 2 * t, 'glass', 'glass')

def rod(p0, p1, r=0.02, m='black'):
    a = Vector((p0[0], -p0[1], p0[2])); b = Vector((p1[0], -p1[1], p1[2])); d = b - a
    if MODE in ('cutaway', 'plan', 'glb') and min(a.z, b.z) >= CUT - 0.2: return
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=r, depth=d.length, location=(a + b) / 2)
    o = bpy.context.active_object; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); o.data.materials.append(M[m])
    for c in o.users_collection: c.objects.unlink(o)
    link(o)

def floor(x0, x1, z0, z1, m='floor_oak', h=0.0):
    me = bpy.data.meshes.new('floor'); X0, X1, Y0, Y1 = x0, x1, -z1, -z0
    me.from_pydata([(X0, Y0, h), (X1, Y0, h), (X1, Y1, h), (X0, Y1, h)], [], [(0, 1, 2, 3)])
    me.materials.append(M[m]); link(bpy.data.objects.new('floor', me))
    if abs(h) < 0.1 and x1 - x0 < 20: SHAPES.append(('floor', x0, x1, z0, z1, h, h, m))

def ceiling(x0, x1, z0, z1, h=None, m='ceiling'):
    """A ceiling plane at h (default the ceiling height), facing down. (A flipped floor() needs its object back,
    and floor() does not return it — and bpy.data.objects[-1] is the last object by NAME, not the newest.)"""
    h = CEIL if h is None else h
    me = bpy.data.meshes.new('ceiling'); X0, X1, Y0, Y1 = x0, x1, -z1, -z0
    me.from_pydata([(X0, Y0, h), (X0, Y1, h), (X1, Y1, h), (X1, Y0, h)], [], [(0, 1, 2, 3)])   # clockwise from above: normal -Z
    me.materials.append(M[m]); return link(bpy.data.objects.new('ceiling', me))

def rbox(axis, W, f, u0, u1, d0, d1, h0, h1, m, name='art'):
    if axis == 'x': return box(W + f * d0, W + f * d1, u0, u1, h0, h1, m, name=name)
    return box(u0, u1, W + f * d0, W + f * d1, h0, h1, m, name=name)
