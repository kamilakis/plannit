"""Scale figures, built from the same primitives as the rest of the flat. The project creates their
materials (skin, skin2, hair, trunks, shirt*, denim, chino, figure) before placing any."""
import bpy, math
from mathutils import Vector
from .ctx import INTERIOR
from .geometry import sphere, link
from .materials import M

FIGURE_DARK = False


def figure_style(dark):
    """dark=True: every figure one matt charcoal silhouette ('figure'), no clothes, no hair."""
    global FIGURE_DARK
    FIGURE_DARK = dark

def bone(p0, p1, r0, r1, m, seg=20):
    """A smooth tapered limb segment between two (x, z, h) points."""
    a = Vector((p0[0], -p0[1], p0[2])); b = Vector((p1[0], -p1[1], p1[2])); d = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=seg, radius1=r0, radius2=r1, depth=d.length, location=(a + b) / 2)
    o = bpy.context.active_object; o.name = 'limb'
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    o.data.materials.append(M[m]); bpy.ops.object.shade_smooth()
    for c in o.users_collection: c.objects.unlink(o)
    link(o)

# joint tables per pose, in the figure's own frame: (right+, forward+, height). 'lean' tips the torso.
POSES = {
    #          hip    knee          ankle         toe           elbow             wrist            lean
    'stand':  (1.00, (0.105, 0.01, 0.54), (0.11, 0.00, 0.09), (0.11, 0.15, 0.035), (0.225, 0.02, 1.16), (0.235, 0.08, 0.88), 0.00),
    'shower': (1.00, (0.105, 0.01, 0.54), (0.11, 0.00, 0.09), (0.11, 0.15, 0.035), (0.320, 0.03, 1.60), (0.140, 0.10, 1.79), 0.00),
    'basin':  (1.00, (0.105, 0.03, 0.54), (0.11, 0.00, 0.09), (0.11, 0.15, 0.035), (0.235, 0.10, 1.18), (0.100, 0.34, 0.95), 0.06),
    'sit':    (0.54, (0.125, 0.44, 0.54), (0.125, 0.50, 0.09), (0.125, 0.64, 0.035), (0.240, 0.10, 0.76), (0.200, 0.38, 0.62), 0.02),
    'stool':  (0.74, (0.125, 0.42, 0.72), (0.125, 0.40, 0.30), (0.125, 0.54, 0.275), (0.240, 0.16, 0.96), (0.160, 0.46, 0.92), 0.03),
}

def person(px, pz, face, pose, skin='skin', top=None, bottom='trunks', legs=None, h=1.78):
    """A figure at (px, pz). `face` in degrees: 0 faces +z, 90 faces +x, 180 faces -z, 270 faces -x.
       `top`/`bottom`/`legs` are material names; None leaves that part bare skin."""
    if not INTERIOR: return
    if FIGURE_DARK: skin, top, bottom, legs = 'figure', None, None, None
    s = h / 1.90
    a = math.radians(face); fx, fz = math.sin(a), math.cos(a); rx, rz = math.cos(a), -math.sin(a)
    hipH, KN, AN, TO, EL, WR, lean = POSES[pose]
    sit = pose in ('sit', 'stool')
    tor = top or skin; leg = legs or skin; hip = bottom or skin
    base = hipH if sit else 0.0      # the height that stays put when the figure is scaled
    def P(lx, ly, lh, fixed=False):  # fixed: keep the height as drawn (seated feet on the floor / footrest)
        return (px + (lx * rx + ly * fx) * s, pz + (lx * rz + ly * fz) * s, lh if fixed else base + (lh - base) * s)
    def blob(p, w, d, hh, m):        # ellipsoid sized in the figure's own frame, mapped to world axes
        sphere(p[0], p[1], p[2], 1.0, m,
               (abs(rx) * w + abs(fx) * d) * s, (abs(rz) * w + abs(fz) * d) * s, hh * s)
    # torso: pelvis, abdomen, chest. `lean` carries the upper body forward.
    blob(P(0, lean * 0.2, hipH + 0.05), 0.19, 0.145, 0.16, hip)
    blob(P(0, lean * 0.5, hipH + 0.20), 0.18, 0.135, 0.15, tor)
    blob(P(0, lean * 1.0, hipH + 0.39), 0.21, 0.140, 0.22, tor)
    # shoulders, neck, head
    shH = hipH + 0.53
    for sgn in (-1, 1): blob(P(sgn * 0.185, lean, shH), 0.070, 0.070, 0.070, tor)
    bone(P(0, lean * 1.1, shH + 0.03), P(0, lean * 1.25, shH + 0.14), 0.064 * s, 0.056 * s, skin)
    blob(P(0, lean * 1.4, shH + 0.24), 0.092, 0.102, 0.122, skin)
    blob(P(0, lean * 1.4 - 0.025, shH + 0.28), 0.096, 0.096, 0.100, skin if FIGURE_DARK else 'hair')
    # arms
    for sgn in (-1, 1):
        sh = P(sgn * 0.185, lean, shH); el = P(sgn * EL[0], EL[1], EL[2]); wr = P(sgn * WR[0], WR[1], WR[2])
        bone(sh, el, 0.062 * s, 0.050 * s, skin); bone(el, wr, 0.050 * s, 0.036 * s, skin)
        if top: blob(P(sgn * 0.215, lean, shH - 0.09), 0.072, 0.072, 0.085, top)   # short sleeve
        hand = P(sgn * WR[0] * 0.92, WR[1] + (0.10 if sit or pose == 'basin' else 0.02), WR[2] - (0.0 if sit or pose == 'basin' else 0.09))
        bone(wr, hand, 0.036 * s, 0.028 * s, skin)
    # legs
    for sgn in (-1, 1):
        hp = P(sgn * 0.10, lean * 0.1, hipH)
        kn = P(sgn * KN[0], KN[1], KN[2], sit); an = P(sgn * AN[0], AN[1], AN[2], sit); to = P(sgn * TO[0], TO[1], TO[2], sit)
        bone(hp, kn, 0.105 * s, 0.072 * s, leg); bone(kn, an, 0.070 * s, 0.050 * s, leg)
        bone(an, to, 0.052 * s, 0.040 * s, skin if leg == skin else skin)
        if bottom and not sit: blob(P(sgn * 0.105, lean * 0.1, hipH - 0.07), 0.105, 0.115, 0.115, bottom)
