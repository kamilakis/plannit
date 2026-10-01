"""The model's logic, shared by every project: a project's existing.py / proposal.py are data only.

existing.py (the flat today), required: CEIL, WALLS {id: (x0, x1, z0, z1, …)}, OPENINGS {id: (wall id, a, b, kind,
  sill, head, src, note)} with head None = unmeasured, ROOMS {name: (rects, label point)}.
  Optional (empty if absent): CLOSET_FRONTS, BEAMS, COLUMNS, FITTINGS.
proposal.py (the renovation as changes), required: ROOMS. Optional: DEMOLISH, RESIZE, OPENING_CHANGES
  (id -> new (a, b, sill, head, kind) | None = bricked up | 'merged' = swallowed by a neighbour widened over it),
  NEW_OPENINGS, NEW_WALLS, ASSUMED_HEAD (a head for each unmeasured opening that stays), CLOSET_FRONTS,
  REMOVE_FITTINGS.
Frame: x, z metres; walls are axis-aligned rectangles; openings run along a wall's long axis.
Stdlib only: imported as `model` by the sheet scripts, as `engine.model` in Blender."""


def defaults(X, P=None):
    """Fill the optional tables with empty ones, in place, so every caller can rely on them."""
    for k in ('CLOSET_FRONTS', 'BEAMS', 'COLUMNS', 'FITTINGS'):
        if not hasattr(X, k): setattr(X, k, {})
    if P is not None:
        for k in ('RESIZE', 'OPENING_CHANGES', 'NEW_OPENINGS', 'NEW_WALLS', 'ASSUMED_HEAD', 'CLOSET_FRONTS'):
            if not hasattr(P, k): setattr(P, k, {})
        for k in ('DEMOLISH', 'REMOVE_FITTINGS'):
            if not hasattr(P, k): setattr(P, k, set())


def along_x(X, wid):
    """True if wall `wid` of the flat today runs along x (its openings are measured in x)."""
    x0, x1, z0, z1 = X.WALLS[wid][:4]
    return (x1 - x0) >= (z1 - z0)


def area(rooms, name):
    """Clear floor area of a room: the sum of its rectangles."""
    return sum((x1 - x0) * (z1 - z0) for x0, x1, z0, z1 in rooms[name][0])


def walls(X, P):
    """Every wall of the renovated flat: (id, x0, x1, z0, z1, openings, tag, new_opening_starts).
    tag 'old' kept, 'new' built, 'infill' an opening bricked up."""
    for wid, (x0, x1, z0, z1, *_r) in X.WALLS.items():
        if wid in P.DEMOLISH: continue
        x0, x1, z0, z1 = P.RESIZE.get(wid, (x0, x1, z0, z1))
        ops, cut, infill = [], [], []
        for oid, (on, a, b, k, sill, head, *_o) in X.OPENINGS.items():
            if on != wid: continue
            if oid in P.OPENING_CHANGES:
                ch = P.OPENING_CHANGES[oid]
                if ch is None: infill.append((a, b)); continue
                if ch == 'merged': continue                           # absorbed by a neighbour's widened opening
                ops.append(ch)
                if ch[1] - ch[0] > b - a + 0.01: cut.append(ch[0])    # widened = cut into the wall
                continue
            ops.append((a, b, sill, head if head is not None else P.ASSUMED_HEAD[oid], k))
        for o in P.NEW_OPENINGS.get(wid, []): ops.append(o); cut.append(o[0])
        if not infill:
            yield wid, x0, x1, z0, z1, ops, 'old', tuple(cut)
            continue
        # a bricked-up opening: the wall in pieces, the old opening as 'infill'
        ax = along_x(X, wid); lo = x0 if ax else z0; hi = x1 if ax else z1
        edges = sorted([lo, hi] + [u for ab in infill for u in ab])
        for u0, u1 in zip(edges, edges[1:]):
            if u1 - u0 < 1e-4: continue
            tag = 'infill' if any(abs(u0 - a) < 1e-6 for a, _ in infill) else 'old'
            box = (u0, u1, z0, z1) if ax else (x0, x1, u0, u1)
            yield wid, *box, [o for o in ops if u0 <= o[0] < u1], tag, tuple(c for c in cut if u0 <= c < u1)
    for wid, (x0, x1, z0, z1, ops, _n) in P.NEW_WALLS.items():
        yield wid, x0, x1, z0, z1, ops, 'new', ()

def demolished(X, P):
    """Existing wall pieces that come down: (id, x0, x1, z0, z1)."""
    for wid, (x0, x1, z0, z1, *_r) in X.WALLS.items():
        if wid in P.DEMOLISH: yield wid, x0, x1, z0, z1; continue
        if wid in P.RESIZE:
            r = P.RESIZE[wid]
            if along_x(X, wid):
                for a, b in ((x0, r[0]), (r[1], x1)):
                    if b - a > 1e-4: yield wid, a, b, z0, z1
            else:
                for a, b in ((z0, r[2]), (r[3], z1)):
                    if b - a > 1e-4: yield wid, x0, x1, a, b
