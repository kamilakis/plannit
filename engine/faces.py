"""Wall faces: every stretch of wall a room sees, traced from the walls themselves, for drawings that locate
things ON walls (sockets, switches, ...). Stdlib only.

The walls (and anything else solid: columns, wardrobes, closet fronts) are drawn into a 1 cm grid; the floor
is flood-filled from each room's rectangles; the boundary of what was filled is walked clockwise on the paper
(plan +x right, +z down the paper), so the room is always on the walker's right and the wall on the left. A
face is one straight run of that boundary in one room: it starts at the corner on your LEFT as you stand in
the room facing it, and distances along it are measured from there, to the right.

    trace(solids, rooms, entry, bounds) -> {room: [Face, ...]}   in clockwise order, from the face at `entry`
    solids: [(x0, x1, z0, z1, kind)] kind 'wall' (gets a code) | 'front' (joinery: drawn, not numbered).
            Leave columns OUT: a column 10 cm proud of its wall would break the face in three; the wall's face
            runs straight through, and the drawings show the column on it.
    rooms:  {name: [(x0, x1, z0, z1), ...]}  (rough rectangles are fine: they only seed the fill and say which
            room a stretch of boundary belongs to)
    entry:  {name: (x, z)}  a point by the room's door: face 1 is the one nearest it"""
import math

D = 0.01                                            # grid step, m

# a face's direction of travel (room on the right) -> how a viewer in the room looks at it
SEE = {(1, 0): '-z', (-1, 0): '+z', (0, 1): '+x', (0, -1): '-x'}


class Face:
    __slots__ = ('room', 'dir', 'a', 'b', 'kind', 'code', 'n', 'tag')
    def __init__(s, room, d, a, b, kind): s.room, s.dir, s.a, s.b, s.kind, s.code, s.n, s.tag = room, d, a, b, kind, None, None, None   # tag: the project's own mark
    @property
    def length(s): return math.hypot(s.b[0] - s.a[0], s.b[1] - s.a[1])
    @property
    def look(s): return SEE[s.dir]
    @property
    def line(s):
        """('z', c) for a face along x (the wall at z = c), ('x', c) for one along z."""
        return ('z', s.a[1]) if s.dir[1] == 0 else ('x', s.a[0])
    def at(s, u):
        """The plan point u metres along the face from its start."""
        return (s.a[0] + s.dir[0] * u, s.a[1] + s.dir[1] * u)
    def u_of(s, p):
        """How far along the face (from its start) the plan coordinate p lies (x for a face along x, else z)."""
        return (p - s.a[0]) * s.dir[0] if s.dir[1] == 0 else (p - s.a[1]) * s.dir[1]
    @property
    def inward(s):
        """Unit vector from the wall into the room."""
        return (-s.dir[1], s.dir[0])                # the walker's right, paper +z down
    def __repr__(s): return f'Face({s.code or "-"} {s.room} {s.a}->{s.b} {s.length:.2f} {s.kind})'


def _merge_jogs(runs, jog):
    """A step of `jog` cells or less between two runs going the same way (two walls a survey centimetre apart) is
    folded into ONE face, on the line of the longer of the two."""
    L = lambda r: abs(r[4][0] - r[0][0]) + abs(r[4][1] - r[0][1])
    changed = True
    while changed and len(runs) > 3:
        changed = False
        n = len(runs)
        for k in range(n):
            p, j, q = runs[k - 1], runs[k], runs[(k + 1) % n]
            if L(j) > jog or p[1] != q[1] or j[1] in (p[1], (-p[1][0], -p[1][1])): continue
            if p[2] != q[2] or p[3] != q[3]: continue
            main = p if L(p) >= L(q) else q
            if p[1][1] == 0: a, b = (p[0][0], main[0][1]), (q[4][0], main[0][1])
            else: a, b = (main[0][0], p[0][1]), (main[0][0], q[4][1])
            new = [a, p[1], p[2], p[3], b]
            if k == 0: runs = [new] + runs[2:-1]
            elif k == n - 1: runs = [new] + runs[1:k - 1]
            else: runs = runs[:k - 1] + [new] + runs[k + 2:]
            changed = True
            break
    return runs


def trace(solids, rooms, entry, bounds, min_len=0.30, jog=0.02):
    x0b, x1b, z0b, z1b = bounds
    nx = int(round((x1b - x0b) / D)) + 2; nz = int(round((z1b - z0b) / D)) + 2
    I = lambda x: int(round((x - x0b) / D)) + 1
    J = lambda z: int(round((z - z0b) / D)) + 1
    grid = bytearray(nx * nz)                       # 0 floor, 1 wall, 2 front
    for x0, x1, z0, z1, kind in solids:
        v = 1 if kind == 'wall' else 2
        for i in range(max(I(x0), 0), min(I(x1), nx)):
            row = i * nz
            for j in range(max(J(z0), 0), min(J(z1), nz)):
                if grid[row + j] != 1: grid[row + j] = v
    # flood fill, every room seeded from its rectangles' centres; regions may merge (open plans)
    region = {}                                     # cell -> region id
    def fill(seed, rid):
        st = [seed]; region[seed] = rid
        while st:
            c = st.pop(); i, j = divmod(c, nz)
            if i in (0, nx - 1) or j in (0, nz - 1): raise ValueError(f'room fill leaked out of the plan at {i}, {j}')
            for n in (c - nz, c + nz, c - 1, c + 1):
                if not grid[n] and n not in region: region[n] = rid; st.append(n)
    members = {}                                    # region id -> the rooms seeded in it
    for name, rects in rooms.items():
        for x0, x1, z0, z1 in rects:
            c = I((x0 + x1) / 2) * nz + J((z0 + z1) / 2)
            if grid[c]: continue
            if c not in region: fill(c, len(members) + 1); members[len(members) + 1] = set()
            members[region[c]].add(name)
    # which room a floor cell belongs to: the rectangle that holds it, else the nearest one
    def room_of(i, j):
        x = x0b + (i - 1 + 0.5) * D; z = z0b + (j - 1 + 0.5) * D; best = None
        for name in members[region[i * nz + j]]:
            rects = rooms[name]
            for a, b, c, d in rects:
                dx = max(a - x, 0, x - b); dz = max(c - z, 0, z - d); dd = dx * dx + dz * dz
                if best is None or dd < best[0]: best = (dd, name)
        return best[1]
    # boundary edges, room on the right: (start vertex, dir) -> (room, kind); vertices are grid corners (i, j)
    edges = {}
    for c in region:
        i, j = divmod(c, nz)
        for n, (si, sj), d in ((c - 1, (i, j), (1, 0)),           # solid above (-z): top side, travel +x
                               (c + nz, (i + 1, j), (0, 1)),       # solid right (+x): right side, travel +z
                               (c + 1, (i + 1, j + 1), (-1, 0)),   # solid below: bottom side, travel -x
                               (c - nz, (i, j + 1), (0, -1))):     # solid left: left side, travel -z
            if grid[n]: edges[(si, sj)] = edges.get((si, sj), []) + [(d, room_of(i, j), 'wall' if grid[n] == 1 else 'front')]
    # walk the loops
    P = lambda v: (round(x0b + (v[0] - 1) * D, 3), round(z0b + (v[1] - 1) * D, 3))
    loops = []
    while edges:
        v0 = next(iter(edges)); v = v0; loop = []; d_prev = None
        while True:
            outs = edges[v]
            if len(outs) > 1 and d_prev:            # a pinch: take the sharpest right turn
                rt = (-d_prev[1], d_prev[0])
                outs.sort(key=lambda e: 0 if e[0] == rt else (1 if e[0] == d_prev else 2))
            d, rm, kd = outs.pop(0)
            if not outs: del edges[v]
            loop.append((v, d, rm, kd)); d_prev = d
            v = (v[0] + d[0], v[1] + d[1])
            if v == v0 and v not in edges: break
            if v not in edges: raise ValueError('open boundary loop')
        loops.append(loop)
    # runs: same direction, room and kind
    out = {name: [] for name in rooms}
    for loop in loops:
        runs = []
        for v, d, rm, kd in loop:
            if runs and runs[-1][1] == d and runs[-1][2] == rm and runs[-1][3] == kd: runs[-1][4] = (v[0] + d[0], v[1] + d[1])
            else: runs.append([v, d, rm, kd, (v[0] + d[0], v[1] + d[1])])
        if len(runs) > 1 and runs[0][1:4] == runs[-1][1:4]:      # the loop started mid-run
            runs[0][0] = runs[-1][0]; runs.pop()
        runs = _merge_jogs(runs, int(round(jog / D)))
        for a, d, rm, kd, b in runs: out[rm].append(Face(rm, d, P(a), P(b), kd))
    # order each room's faces from the one at its entry (clockwise = loop order within each loop)
    for name, fs in out.items():
        if not fs or name not in entry: continue
        ex, ez = entry[name]
        def dist(f):
            (ax, az), (bx, bz) = f.a, f.b
            px = min(max(ex, min(ax, bx)), max(ax, bx)); pz = min(max(ez, min(az, bz)), max(az, bz))
            return math.hypot(ex - px, ez - pz) + (0 if f.kind == 'wall' and f.length >= min_len else 100)
        k = fs.index(min(fs, key=dist))
        out[name] = fs[k:] + fs[:k]
    return out


def number(faces, prefix, min_len=0.30):
    """Give each wall face of min_len or more a code '<prefix>.<n>', clockwise."""
    for name, fs in faces.items():
        n = 0
        for f in fs:
            if f.kind == 'wall' and f.length >= min_len - 1e-6:
                n += 1; f.n = n; f.code = f'{prefix[name]}.{n}'
    return faces
