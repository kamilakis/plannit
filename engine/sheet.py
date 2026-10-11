"""Survey-style plan sheets (after the owner's sample αποτύπωση): one entity list per drawing, written both
as a DXF (R12, millimetres, X = x, Y = -z) and as an SVG laid out at 1:50 on A3 — build scripts print the
SVG to PDF with print_pdf.py. Used by the as-built sheet (asbuilt_sheet.py) and the
proposal sheet (proposal_sheet.py), so the two look alike and read the same way.
Plan frame: x, z metres, TRUE NORTH = +x. Text heights are PAPER millimetres. Stdlib only."""
import math
from xml.sax.saxutils import escape

MM = 1000; SCALE = 50; PX = MM / SCALE          # 1 m in the plan = 20 mm on paper
PW, PH, TB = 297, 420, 318                      # A3 portrait; the title/legend band starts at y = TB

def m2(v): return f'{v:.2f}'
def gr(v): return f'{v:.2f}'.replace('.', ',')
def rect(x0, x1, z0, z1): return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]

LAYERS = {  # name: (ACI colour, svg colour, svg stroke mm, flags)
    'FRAME': (7, '#000', 0.35, ''), 'TITLE': (7, '#000', 0.18, ''), 'WALLS': (7, '#000', 0.35, ''),
    'WALL_HATCH': (1, '#8c2d19', 0.09, ''), 'NEW_WALLS': (1, '#d2402a', 0.1, 'fill'),
    'DEMOLISHED': (2, '#b58f00', 0.25, 'dash'), 'DEMOLISHED_FILL': (2, '#f6dc5a', 0.1, 'fill'),
    'CONCRETE': (8, '#333', 0.1, ''), 'WINDOWS': (5, '#000', 0.13, ''), 'DOORS': (30, '#000', 0.18, ''),
    'DOOR_SWING': (8, '#000', 0.09, ''), 'CLOSETS': (4, '#000', 0.13, ''), 'BEAMS': (6, '#000', 0.18, 'dash'),
    'BEAM_TEXT': (6, '#000', 0.1, ''), 'FIXTURES': (8, '#666', 0.1, ''), 'FURNITURE': (9, '#bbb', 0.1, 'frozen'),
    'ROOM_TEXT': (7, '#000', 0.1, ''), 'OPENING_TEXT': (7, '#000', 0.1, ''), 'DIMENSIONS': (7, '#000', 0.09, ''),
    'DIM_TEXT': (7, '#000', 0.1, ''), 'NOTES': (7, '#000', 0.1, '')}

class Sheet:
    def __init__(self, rooms, circulation=(), labels=None):
        """rooms: {name: (rects, label point)}. circulation: rooms doors open away from (halls, corridors) —
        a door's swing and its tag go into the other room. labels: {name: (text, vertical)} to print a room
        under another text and/or turned 90° (narrow closets); anything else prints its name, level."""
        self.E = []; self.rooms = rooms; self.circulation = set(circulation); self.labels = labels or {}; self.solids = []
        self.own = {}                                 # text index -> the indices of its own dimension's lines (check())
        self.movable = []                             # label groups resolve() may move: (entity indices, [(dx, dz) offsets to try], rank)
    # ---- primitives
    def line(s, l, a, b): s.E.append(('line', l, a, b))
    def pline(s, l, pts, closed=True): s.E.append(('pline', l, list(pts), closed))
    def solid(s, l, q): s.E.append(('solid', l, list(q)))
    def text(s, l, p, t, h, rot=0, align='c'): s.E.append(('text', l, p, t, h, rot, align))
    def hatch(s, poly, layer='WALL_HATCH', step=0.08, sign=1):
        """45° hatch clipped to a convex polygon."""
        cx = sum(p[0] for p in poly) / len(poly); cz = sum(p[1] for p in poly) / len(poly)
        cs = [p[0] + sign * p[1] for p in poly]; c = math.floor(min(cs) / step) * step
        while c < max(cs):
            c += step; lo, hi = -1e9, 1e9
            for i in range(len(poly)):
                p, q = poly[i], poly[(i + 1) % len(poly)]; ex, ez = q[0] - p[0], q[1] - p[1]; N = (-ez, ex)
                if N[0] * (cx - p[0]) + N[1] * (cz - p[1]) < 0: N = (ez, -ex)
                A = N[0] - N[1] * sign; B = N[1] * sign * c - N[0] * p[0] - N[1] * p[1]
                if abs(A) < 1e-12:
                    if B < 0: lo, hi = 1, 0
                elif A > 0: lo = max(lo, -B / A)
                else: hi = min(hi, -B / A)
            if hi - lo > 0.005: s.line(layer, (lo, sign * (c - lo)), (hi, sign * (c - hi)))
    # ---- rooms
    def room_at(s, x, z):
        for name, (rs, _) in s.rooms.items():
            if any(x0 <= x <= x1 and z0 <= z <= z1 for x0, x1, z0, z1 in rs): return name
        return None
    def score(s, r): return -1 if r is None else (0 if r in s.circulation else 1)
    def area(s, name): return sum((x1 - x0) * (z1 - z0) for x0, x1, z0, z1 in s.rooms[name][0])
    def room_labels(s, extra=()):
        total = 0
        for name, (rs, p) in s.rooms.items():
            ar = s.area(name); total += ar; nm, vert = s.labels.get(name, (name, False))
            i0 = len(s.E)
            s.text('ROOM_TEXT', p, nm, 2.2 if vert else 2.8, 90 if vert else 0)
            s.text('ROOM_TEXT', (p[0] + 0.16, p[1]) if vert else (p[0], p[1] + 0.2), f'Ε={gr(ar)}τ.μ.', 1.7, 90 if vert else 0)
            # the name and its area move together, to spots still inside the room (a grid, nearest first)
            offs = sorted(((dx * 0.15, dz * 0.15) for dx in range(-8, 9) for dz in range(-8, 9)), key=lambda o: math.hypot(*o))
            def inside(o, m=0.08):                    # both lines' boxes, with a margin, wholly inside the room
                for e in s.E[i0:i0 + 2]:
                    bx = s.text_box(('text', e[1], (e[2][0] + o[0], e[2][1] + o[1])) + e[3:])
                    if not all(s.room_at(x, z) == name for x in (bx[0] - m, bx[1] + m) for z in (bx[2] - m, bx[3] + m)): return False
                return True
            offs = [o for o in offs if inside(o)] or [(0, 0)]
            s.movable.append(([i0, i0 + 1], offs, 3))
        for p, t in extra: s.text('ROOM_TEXT', p, t, 2.4)
        return total
    # ---- walls: [(x0, x1, z0, z1, style)] style 'old' | 'new' | 'demolished'; opens: see openings()
    def walls(s, walls, opens):
        for x0, x1, z0, z1, style in walls:
            ax = (x1 - x0) >= (z1 - z0); lo, hi = (x0, x1) if ax else (z0, z1); c0, c1 = (z0, z1) if ax else (x0, x1)
            cuts = sorted((min(a[0 if ax else 1], b[0 if ax else 1]), max(a[0 if ax else 1], b[0 if ax else 1]))
                          for k, a, b, *_ in opens if style != 'demolished' and
                          abs(a[1 if ax else 0] - b[1 if ax else 0]) < 0.02 and c0 - 0.01 <= a[1 if ax else 0] <= c1 + 0.01)
            pieces, u = [], lo
            for a, b in cuts:
                if b <= lo or a >= hi: continue
                if a > u: pieces.append((u, a))
                u = max(u, b)
            if u < hi: pieces.append((u, hi))
            for a, b in pieces:
                if b - a < 0.004: continue
                q = rect(a, b, z0, z1) if ax else rect(x0, x1, a, b)
                if style == 'demolished':
                    s.solid('DEMOLISHED_FILL', q); s.pline('DEMOLISHED', q); continue
                s.solids.append(q); s.pline('WALLS', q)
                if style == 'new': s.solid('NEW_WALLS', q)
                else: s.hatch(q)
    def removed(s, pts):
        """A fitting that is taken out (not a wall): its outline, filled and dashed like demolished masonry."""
        pts = list(pts)
        for i in range(1, len(pts) - 1): s.solid('DEMOLISHED_FILL', [pts[0], pts[i], pts[i + 1]])
        s.pline('DEMOLISHED', pts)
    def columns(s, cols):
        for x0, x1, z0, z1 in cols:
            q = rect(x0, x1, z0, z1); s.solid('CONCRETE', q); s.pline('WALLS', q); s.solids.append(q)
    def beams(s, beams):
        for x0, x1, z0, z1, soffit in beams:
            s.pline('BEAMS', rect(x0, x1, z0, z1))
            horiz = (x1 - x0) > (z1 - z0); m = ((x0 + x1) / 2, (z0 + z1) / 2)
            s.text('BEAM_TEXT', (m[0], z1 + 0.12) if horiz else (x1 + 0.12, m[1]),
                   f'ΔΟΚΟΣ {gr(min(x1 - x0, z1 - z0))} · κ.π. +{gr(soffit)}', 1.6, 0 if horiz else 90)
            # along the beam, either side of it
            L = (x1 - x0) if horiz else (z1 - z0); across = -((z1 - z0) if horiz else (x1 - x0)) - 0.24
            half = s.text_box(s.E[-1]); half = ((half[1] - half[0]) if horiz else (half[3] - half[2])) / 2
            offs = [(0, 0)] + [(u, v) if horiz else (v, u) for k in range(1, int(max(0, L / 2 - half) / 0.25) + 1)
                               for u in (k * 0.25, -k * 0.25) for v in (0, across)] + [(0, across) if horiz else (across, 0)]
            s.movable.append(([len(s.E) - 1], offs, 1))
    # ---- openings: (kind, a, b, thickness, (width, head, sill) strings or None); a/b on the wall centre line
    @staticmethod
    def reading(a, b):
        th = math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))
        while th > 90.01: th -= 180
        while th <= -89.99: th += 180
        t = math.radians(th); return th, (math.cos(t), -math.sin(t)), (-math.sin(t), -math.cos(t))
    def tag(s, c, a, b, w, head, sill, layer='OPENING_TEXT'):
        th, rd, up = s.reading(a, b); P = lambda p, k, v: (p[0] + k[0] * v, p[1] + k[1] * v)
        i0 = len(s.E)
        s.text(layer, P(c, up, 0.075), w, 1.8, th); s.text(layer, P(c, up, -0.075), head, 1.8, th)
        s.line(layer, P(c, rd, -0.17), P(c, rd, 0.17))
        if sill: s.text(layer, P(c, rd, 0.21), sill, 1.8, th, 'l')
        # further from the wall (the side it is on: away from the opening's centre line), or along it
        L = math.hypot(b[0] - a[0], b[1] - a[1]); mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        nrm = (c[0] - mid[0], c[1] - mid[1]); nl = math.hypot(*nrm) or 1; nrm = (nrm[0] / nl, nrm[1] / nl)
        along = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        offs = [(0, 0)]
        for d in (0.15, 0.3, 0.45, 0.6, 0.75):
            for t in (0, 0.25, -0.25, 0.5, -0.5):
                if abs(t) <= L / 2 + 0.25: offs.append((nrm[0] * d + along[0] * t, nrm[1] * d + along[1] * t))
        for t in (0.25, -0.25, 0.5, -0.5): offs.append((along[0] * t, along[1] * t))
        s.movable.append((list(range(i0, len(s.E))), offs, 2))
    def openings(s, opens):
        for kind, a, b, t, spec in opens:
            dx, dz = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dz); u = (dx / L, dz / L); n = (-u[1], u[0])
            off = lambda p, d, k=n: (p[0] + k[0] * d, p[1] + k[1] * d)
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2); h2 = t / 2
            sp, sm = s.score(s.room_at(*off(mid, 0.35))), s.score(s.room_at(*off(mid, -0.35)))
            nin = n if sp >= sm else (-n[0], -n[1]); nout = (-nin[0], -nin[1])
            outer_room = s.room_at(*off(mid, 0.35, nout))
            w, head, sill = spec if spec else (None, None, None)
            if kind == 'window':
                for d in (-h2, -0.017, 0.017, h2): s.line('WINDOWS', off(a, d), off(b, d))
                s.line('WINDOWS', off(a, -h2), off(a, h2)); s.line('WINDOWS', off(b, -h2), off(b, h2))
                s.tag(off(mid, h2 + 0.31, nin), a, b, w, head, sill)
            elif kind == 'door':
                s.line('DOORS', off(a, -h2), off(a, h2)); s.line('DOORS', off(b, -h2), off(b, h2))
                leaves = [(a, b, L)] if L <= 1.0 else [(a, mid, L / 2), (b, mid, L / 2)]
                for h, far, r in leaves:
                    h0 = off(h, h2, nin); tip = (h0[0] + nin[0] * r, h0[1] + nin[1] * r)
                    s.line('DOORS', h0, tip)
                    a0 = math.atan2(nin[1], nin[0]); a1 = math.atan2(far[1] - h[1], far[0] - h[0])
                    d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
                    s.pline('DOOR_SWING', [(h0[0] + r * math.cos(a0 + d * i / 16), h0[1] + r * math.sin(a0 + d * i / 16)) for i in range(17)], False)
                if spec:
                    if outer_room is not None: s.tag(off(mid, h2 + 0.28, nout), a, b, w, head, None)
                    else: s.tag(off(mid, max(r for *_, r in leaves) + h2 + 0.23, nin), a, b, w, head, None)
            elif kind == 'sliding':  # glazed sliding door: jambs, two overlapping glass leaves, tagged like a door
                ext = lambda p, q, f: (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f)
                s.line('DOORS', off(a, -h2), off(a, h2)); s.line('DOORS', off(b, -h2), off(b, h2))
                for p0, p1, d in ((a, ext(a, b, 0.55), -0.03), (ext(a, b, 0.45), b, 0.03)):
                    s.line('DOORS', off(p0, d - 0.012), off(p1, d - 0.012)); s.line('DOORS', off(p0, d + 0.012), off(p1, d + 0.012))
                    s.line('DOORS', off(p0, d - 0.012), off(p0, d + 0.012)); s.line('DOORS', off(p1, d - 0.012), off(p1, d + 0.012))
                if spec: s.tag(off(mid, h2 + 0.28, nout if outer_room is not None else nin), a, b, w, head, None)
            else:  # closet opening / sliding fronts: two overlapping leaves
                ext = lambda p, q, f: (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f)
                s.line('CLOSETS', off(a, -0.02), off(ext(a, b, 0.55), -0.02)); s.line('CLOSETS', off(ext(a, b, 0.45), 0.02), off(b, 0.02))
                s.line('CLOSETS', off(a, -h2), off(a, h2)); s.line('CLOSETS', off(b, -h2), off(b, h2))
                s.solids.append(rect(min(a[0], b[0]) - 0.01, max(a[0], b[0]) + 0.01, min(a[1], b[1]) - 0.01, max(a[1], b[1]) + 0.01))
    # ---- dimensions (metres, two decimals, as a surveyor writes them)
    def tick(s, p): s.line('DIMENSIONS', (p[0] - 0.05, p[1] + 0.05), (p[0] + 0.05, p[1] - 0.05))
    def dim(s, a, b, at, horiz, ext_from=None, label=True):
        if abs(b - a) < 0.02: return
        first = len(s.E)
        P = (lambda u: (u, at)) if horiz else (lambda u: (at, u))
        s.line('DIMENSIONS', P(a), P(b)); s.tick(P(a)); s.tick(P(b))
        if ext_from is not None:
            for u in (a, b):
                sg = 0.06 if at > ext_from else -0.06
                s.line('DIMENSIONS', (u, ext_from + sg) if horiz else (ext_from + sg, u), (u, at + sg) if horiz else (at + sg, u))
        if label:
            m = (a + b) / 2
            if horiz: s.text('DIM_TEXT', (m, at - 0.09), m2(abs(b - a)), 1.8)
            else: s.text('DIM_TEXT', (at - 0.09, m), m2(abs(b - a)), 1.8, 90)
            s.own[len(s.E) - 1] = set(range(first, len(s.E) - 1))
            # slide along its line (staying inside its span), or flip to the other side of it
            room = abs(b - a) / 2 - len(m2(abs(b - a))) * 0.6 * 1.8 * 1.38 / PX / 2 - 0.03
            offs = [(0, 0), (0.18, 0) if not horiz else (0, 0.18)]
            k = 1
            while k * 0.15 <= room:
                for u in (k * 0.15, -k * 0.15):
                    for v in (0, 0.18): offs.append((u, v) if horiz else (v, u))
                k += 1
            s.movable.append(([len(s.E) - 1], offs, 0))
    def chain(s, pts, at, horiz, ext_from, total=0.45):
        pts = sorted(set(round(p, 3) for p in pts))
        for a, b in zip(pts, pts[1:]): s.dim(a, b, at, horiz, ext_from)
        if len(pts) > 2 and total:
            s.dim(pts[0], pts[-1], at + (-total if ext_from is not None and at < ext_from else total), horiz, None)
    def cut(s, horiz, at):
        iv = []
        for q in s.solids:
            xs = []
            for i in range(len(q)):
                p, r = q[i], q[(i + 1) % len(q)]
                pa, ra = (p[1], r[1]) if horiz else (p[0], r[0])
                if (pa - at) * (ra - at) <= 0 and pa != ra:
                    t = (at - pa) / (ra - pa); xs.append((p[0] + t * (r[0] - p[0])) if horiz else (p[1] + t * (r[1] - p[1])))
            if len(xs) >= 2: iv.append((min(xs), max(xs)))
        iv.sort(); merged = []
        for lo, hi in iv:
            if merged and lo <= merged[-1][1] + 0.005: merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
            else: merged.append((lo, hi))
        return merged
    def room_dim(s, horiz, at, u):
        """Clear dimension, face to face, of the space containing coordinate u on the cut line `at`."""
        m = s.cut(horiz, at)
        for (a0, a1), (b0, b1) in zip(m, m[1:]):
            if a1 <= u <= b0: s.dim(a1, b0, at, horiz); return
        raise SystemExit(f'room_dim: no space around {u} on cut {at}')
    # ---- legibility check: every label's box against the other labels, the dimension, door, beam and fixture
    # lines, and the walls. PLANNIT_SHEET_CHECK=1 prints what collides; the sheet is only right when it prints nothing.
    @staticmethod
    def text_box(e, pad=0.0):
        """A text entity's box in plan metres (x0, x1, z0, z1): DejaVu Sans Condensed at h * 1.38 mm, centred
        vertically (the SVG's dominant-baseline), ~0.60 em a character (capitals and digits), 0.92 em tall (accents
        included): generous on purpose, a label that only just clears is still hard to read. pad widens every side."""
        _, _, p, t, h, rot, al = e
        w = len(t) * 0.60 * h * 1.38 / PX; ht = 0.92 * h * 1.38 / PX
        a0 = {'l': 0, 'c': -w / 2, 'r': -w}[al]
        if abs(rot) < 1: return (p[0] + a0 - pad, p[0] + a0 + w + pad, p[1] - ht / 2 - pad, p[1] + ht / 2 + pad)
        if abs(abs(rot) - 90) < 1:                    # turned 90° (reads upward): the run goes along -z
            sg = 1 if rot > 0 else -1
            u0, u1 = sorted((p[1] - sg * a0, p[1] - sg * (a0 + w)))
            return (p[0] - ht / 2 - pad, p[0] + ht / 2 + pad, u0 - pad, u1 + pad)
        return None                                   # slanted (tags on slanted walls): not checked
    @staticmethod
    def _seg_hits_box(a, b, bx):
        x0, x1, z0, z1 = bx; t0, t1 = 0.0, 1.0; dx, dz = b[0] - a[0], b[1] - a[1]
        for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dz, a[1] - z0), (dz, z1 - a[1])):
            if abs(p) < 1e-12:
                if q < 0: return False
            else:
                r = q / p
                if p < 0: t0 = max(t0, r)
                else: t1 = min(t1, r)
                if t0 > t1: return False
        return True
    def _shift(s, i, dx, dz):
        e = s.E[i]
        if e[0] == 'text': s.E[i] = (e[0], e[1], (e[2][0] + dx, e[2][1] + dz)) + e[3:]
        elif e[0] == 'line': s.E[i] = (e[0], e[1], (e[2][0] + dx, e[2][1] + dz), (e[3][0] + dx, e[3][1] + dz))
    def _hits(s, group, upto):
        """How many things the texts of one label group collide with (other labels, lines, walls)."""
        own = set(group)
        for i in group: own |= s.own.get(i, set())
        n = 0
        ov = lambda a, b: a[0] < b[1] and b[0] < a[1] and a[2] < b[3] and b[2] < a[3]
        for i in group:
            e = s.E[i]
            if e[0] != 'text': continue
            bi = s.text_box(e, 0.015)
            if not bi: continue
            for k in range(upto):
                if k in own: continue
                f = s.E[k]
                if f[0] == 'text':
                    bk = s.text_box(f)
                    if bk and ov(bi, bk): n += 3                      # text on text: worst
                elif f[0] == 'line' and f[1] in ('DIMENSIONS', 'DOORS', 'BEAMS', 'FIXTURES', 'WINDOWS') or \
                     f[0] == 'pline' and f[1] in ('DOOR_SWING', 'BEAMS', 'FIXTURES', 'WALLS', 'DEMOLISHED', 'CLOSETS'):
                    pts = [f[2], f[3]] if f[0] == 'line' else f[2] + ([f[2][0]] if f[3] else [])
                    if any(s._seg_hits_box(pts[m], pts[m + 1], bi) for m in range(len(pts) - 1)): n += 1
        return n
    def resolve(s, upto, passes=3):
        """Move each colliding label group to the first of its offsets where it collides with nothing (else to
        the one with the fewest hits). Dimension figures go first, then opening tags, beam notes, room names."""
        for _ in range(passes):
            moved = False
            for group, offs, _rank in sorted(s.movable, key=lambda g: g[2]):
                if not s._hits(group, upto): continue
                best, here = None, (0, 0)
                for dx, dz in offs:
                    for i in group: s._shift(i, dx - here[0], dz - here[1])
                    here = (dx, dz); h = s._hits(group, upto)
                    if best is None or h < best[0]: best = (h, dx, dz)
                    if h == 0: break
                for i in group: s._shift(i, best[1] - here[0], best[2] - here[1])
                moved = moved or (best[1], best[2]) != (0, 0)
            if not moved: break
    def check(s, upto=None):
        E = s.E[:upto] if upto else s.E
        texts = [(i, e) for i, e in enumerate(E) if e[0] == 'text']
        boxes = {i: s.text_box(e) for i, e in texts}
        out = []
        ov = lambda a, b: a[0] < b[1] and b[0] < a[1] and a[2] < b[3] and b[2] < a[3]
        for n, (i, e) in enumerate(texts):
            bi = boxes[i]
            if not bi: continue
            for j, f in texts[n + 1:]:
                bj = boxes[j]
                if bj and ov(bi, bj): out.append(f'text/text  "{e[3]}" ({e[1]})  x  "{f[3]}" ({f[1]})')
            inner = (bi[0] + 0.002, bi[1] - 0.002, bi[2] + 0.002, bi[3] - 0.002)
            for k, f in enumerate(E):
                if f[0] == 'line' and f[1] in ('DIMENSIONS', 'DOORS', 'BEAMS', 'FIXTURES', 'WINDOWS') or \
                   f[0] == 'pline' and f[1] in ('DOOR_SWING', 'BEAMS', 'FIXTURES', 'WALLS', 'DEMOLISHED', 'CLOSETS'):
                    if k in s.own.get(i, ()): continue                               # its own dimension line sits right under it
                    pts = [f[2], f[3]] if f[0] == 'line' else f[2] + ([f[2][0]] if f[3] else [])
                    if any(s._seg_hits_box(pts[m], pts[m + 1], inner) for m in range(len(pts) - 1)):
                        out.append(f'text/{f[1].lower():<11} "{e[3]}" ({e[1]})'); break
        return out
    # ---- the A3 sheet, then both files
    def finish(s, base, rows, legend, notes):
        """rows: [(label, value)] for the title block; legend: [(kind, text)] with kind in
        'hatch' 'new' 'demolished' 'concrete' 'beam' 'fraction'; notes: lines of text."""
        draw_end = len(s.E)
        s.resolve(draw_end)
        import os
        if os.environ.get('PLANNIT_SHEET_CHECK'):
            found = s.check(draw_end)
            print(f'{os.path.basename(base)}: {len(found)} legibility problem(s)')
            for f in found: print('   ' + f)
        def pts_of(e): return [e[2], e[3]] if e[0] == 'line' else (e[2] if e[0] in ('pline', 'solid') else [e[2]])
        allp = [p for e in s.E[:draw_end] for p in pts_of(e)]
        x0, x1 = min(p[0] for p in allp), max(p[0] for p in allp); z0, z1 = min(p[1] for p in allp), max(p[1] for p in allp)
        W, H = (x1 - x0) * PX, (z1 - z0) * PX
        assert W <= PW - 30 and H <= TB - 18, f'plan does not fit A3 at 1:{SCALE}: {W:.0f} x {H:.0f} mm'
        OX = 20 + (PW - 30 - W) / 2 - x0 * PX; OY = 12 + (TB - 18 - H) / 2 - z0 * PX
        M = lambda px, py: ((px - OX) / PX, (py - OY) / PX)
        box = lambda l, a, b, c, d: s.pline(l, [M(a, b), M(c, b), M(c, d), M(a, d)])
        T = lambda px, py, t, h, align='l', l='TITLE': s.text(l, M(px, py), t, h, 0, align)
        box('FRAME', 20, 10, PW - 10, PH - 10)
        nx, ny = PW - 32, 26                                   # north arrow: TRUE north = plan +x = paper right
        s.pline('FRAME', [M(nx + 9, ny), M(nx - 7, ny - 4.5), M(nx - 4, ny), M(nx - 7, ny + 4.5)])
        s.solid('FRAME', [M(nx + 9, ny), M(nx - 7, ny - 4.5), M(nx - 4, ny)]); T(nx + 12, ny, 'Β', 4)
        for i in range(5):
            q = [M(26 + i * 20, TB - 8), M(46 + i * 20, TB - 8), M(46 + i * 20, TB - 6), M(26 + i * 20, TB - 6)]
            s.pline('FRAME', q)
            if i % 2 == 0: s.solid('FRAME', q)
            T(26 + i * 20, TB - 3.2, str(i), 1.8, 'c')
        T(126, TB - 3.2, '5 m', 1.8, 'c'); T(136, TB - 7, 'ΚΛΙΜΑΚΑ 1:50', 2)
        LX = 26; y = TB + 8; T(LX, y, 'ΥΠΟΜΝΗΜΑ', 2.6); y += 7
        for kind, label in legend:
            q = [M(LX, y - 2), M(LX + 12, y - 2), M(LX + 12, y + 2), M(LX, y + 2)]
            if kind == 'hatch': s.pline('WALLS', q); s.hatch(q)
            elif kind == 'new': s.solid('NEW_WALLS', q); s.pline('WALLS', q)
            elif kind == 'demolished': s.solid('DEMOLISHED_FILL', q); s.pline('DEMOLISHED', q)
            elif kind == 'concrete': s.solid('CONCRETE', q); s.pline('WALLS', q)
            elif kind == 'beam': s.pline('BEAMS', [M(LX, y - 1.5), M(LX + 12, y - 1.5), M(LX + 12, y + 1.5), M(LX, y + 1.5)])
            if kind == 'fraction':
                y += 1.5
                T(LX + 6, y - 2, 'Πλάτος', 1.7, 'c'); s.line('TITLE', M(LX + 1, y), M(LX + 11, y)); T(LX + 6, y + 2, 'Πρέκι', 1.7, 'c')
                T(LX + 12.5, y, 'Ποδιά', 1.7); T(LX + 26, y, 'Παράθυρα', 1.9)
                T(LX + 56, y - 2, 'Πλάτος', 1.7, 'c'); s.line('TITLE', M(LX + 51, y), M(LX + 61, y)); T(LX + 56, y + 2, 'Πρέκι', 1.7, 'c')
                T(LX + 65, y, 'Πόρτες', 1.9); y += 7.5; continue
            T(LX + 16, y, label, 1.9); y += 6
        y += 1
        for t in notes: T(LX, y, t, 1.75); y += 4.3
        BX0, BX1 = 190, PW - 14; y = TB + 4; RH = (PH - 14 - y) / len(rows)
        for k, v in rows:
            box('TITLE', BX0, y, BX1, y + RH); T((BX0 + BX1) / 2, y + RH * 0.27, k, 1.6, 'c')
            T((BX0 + BX1) / 2, y + RH * 0.67, v, 2.3 if len(v) < 30 else 2.0, 'c'); y += RH
        s._dxf(base + '.dxf', M); s._svg(base + '.svg', OX, OY)
    def _dxf(s, path, M):
        X = lambda x: round(x * MM, 1); Y = lambda z: round(-z * MM, 1)
        esc = lambda t: ''.join(c if ord(c) < 128 else f'\\U+{ord(c):04X}' for c in t)
        w = []; P = lambda c, v: w.append(f'{c:>3}\n{v}')
        P(0, 'SECTION'); P(2, 'HEADER'); P(9, '$ACADVER'); P(1, 'AC1009')
        P(9, '$EXTMIN'); P(10, X(M(0, 0)[0])); P(20, Y(M(0, PH)[1])); P(30, 0)
        P(9, '$EXTMAX'); P(10, X(M(PW, 0)[0])); P(20, Y(M(0, 0)[1])); P(30, 0)
        P(9, '$DIMSCALE'); P(40, SCALE); P(9, '$LTSCALE'); P(40, SCALE)
        P(0, 'ENDSEC'); P(0, 'SECTION'); P(2, 'TABLES')
        P(0, 'TABLE'); P(2, 'LTYPE'); P(70, 2); P(0, 'LTYPE'); P(2, 'CONTINUOUS'); P(70, 0); P(3, 'Solid line'); P(72, 65); P(73, 0); P(40, 0.0)
        P(0, 'LTYPE'); P(2, 'DASHED'); P(70, 0); P(3, '__ __ __'); P(72, 65); P(73, 2); P(40, 3.0); P(49, 2.0); P(49, -1.0); P(0, 'ENDTAB')
        P(0, 'TABLE'); P(2, 'STYLE'); P(70, 1); P(0, 'STYLE'); P(2, 'STANDARD'); P(70, 0); P(40, 0); P(41, 1); P(50, 0); P(71, 0); P(42, 2.5); P(3, 'arial.ttf'); P(4, ''); P(0, 'ENDTAB')
        P(0, 'TABLE'); P(2, 'LAYER'); P(70, len(LAYERS))
        for n, (c, _, _, f) in LAYERS.items(): P(0, 'LAYER'); P(2, n); P(70, 1 if f == 'frozen' else 0); P(62, c); P(6, 'DASHED' if f == 'dash' else 'CONTINUOUS')
        P(0, 'ENDTAB'); P(0, 'ENDSEC'); P(0, 'SECTION'); P(2, 'ENTITIES')
        AL = {'l': 0, 'c': 1, 'r': 2}
        for e in s.E:
            k, l = e[0], e[1]
            if k == 'line': a, b = e[2], e[3]; P(0, 'LINE'); P(8, l); P(10, X(a[0])); P(20, Y(a[1])); P(30, 0); P(11, X(b[0])); P(21, Y(b[1])); P(31, 0)
            elif k == 'pline':
                P(0, 'POLYLINE'); P(8, l); P(66, 1); P(10, 0); P(20, 0); P(30, 0); P(70, 1 if e[3] else 0)
                for p in e[2]: P(0, 'VERTEX'); P(8, l); P(10, X(p[0])); P(20, Y(p[1])); P(30, 0)
                P(0, 'SEQEND'); P(8, l)
            elif k == 'solid':
                q = e[2] + [e[2][-1]] * (4 - len(e[2])); a, b, c, d = q        # DXF SOLID vertex order is 1,2,4,3
                P(0, 'SOLID'); P(8, l)
                for g, p in ((0, a), (1, b), (2, d), (3, c)): P(10 + g, X(p[0])); P(20 + g, Y(p[1])); P(30 + g, 0)
            elif k == 'text':
                _, _, p, t, h, rot, al = e; P(0, 'TEXT'); P(8, l); P(10, X(p[0])); P(20, Y(p[1])); P(30, 0); P(40, round(h * SCALE, 1)); P(1, esc(t))
                P(50, round(rot, 2)); P(72, AL[al]); P(11, X(p[0])); P(21, Y(p[1])); P(31, 0); P(73, 2)
        P(0, 'ENDSEC'); P(0, 'EOF')
        open(path, 'w', newline='\r\n').write('\n'.join(w) + '\n')
    def _svg(s, path, OX, OY):
        S = lambda p: f'{OX + p[0] * PX:.2f},{OY + p[1] * PX:.2f}'
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}mm" height="{PH}mm" viewBox="0 0 {PW} {PH}">',
               '<rect width="100%" height="100%" fill="#fff"/>',
               '<style>text{font-family:"DejaVu Sans Condensed","DejaVu Sans",sans-serif;dominant-baseline:central}</style>']
        for e in s.E:
            k, l = e[0], e[1]; col, sw, fl = LAYERS[l][1], LAYERS[l][2], LAYERS[l][3]
            if fl == 'frozen': continue
            dash = ' stroke-dasharray="1.6 0.8"' if fl == 'dash' else ''
            if k == 'line': out.append(f'<polyline points="{S(e[2])} {S(e[3])}" fill="none" stroke="{col}" stroke-width="{sw}"/>')
            elif k == 'pline':
                tg = 'polygon' if e[3] else 'polyline'
                out.append(f'<{tg} points="{" ".join(S(p) for p in e[2])}" fill="none" stroke="{col}" stroke-width="{sw}"{dash} stroke-linejoin="round"/>')
            elif k == 'solid': out.append(f'<polygon points="{" ".join(S(p) for p in e[2])}" fill="{col}" stroke="none"/>')
            elif k == 'text':
                _, _, p, t, h, rot, al = e; x, y = S(p).split(',')
                anc = {'l': 'start', 'c': 'middle', 'r': 'end'}[al]
                out.append(f'<text x="{x}" y="{y}" font-size="{h * 1.38:.2f}" text-anchor="{anc}" fill="{col}" transform="rotate({-rot:.2f} {x} {y})">{escape(t)}</text>')
        out.append('</svg>'); open(path, 'w').write('\n'.join(out))
