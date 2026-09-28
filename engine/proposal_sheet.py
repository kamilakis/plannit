"""The PROPOSAL sheets, drawn like the as-built sheet (sheet.py): kept walls hatched, new walls red, demolition
yellow, 1:50 on A3 -> <project>/out/renders/<name>.{dxf,svg} (+ PDF/PNG via print_pdf.py), one per entry in the
project's sheets.PROPOSAL_SHEETS (e.g. the proposal, then the works for the contractor).
Walls and openings come from the project's proposal.py — the same function blender/build.py builds from — and
the fittings from out/renders/model-dump.json, which the Blender 'svg' pass writes (which ones: the project's
sheets.FIXTURES / FURNITURE). Room labels, dimension chains, title block, legend, notes and the file name come
from the project's sheets.py hooks. Stdlib only: runs on debnuc without Blender.
    PLANNIT_PROJECT=<project> python3 engine/proposal_sheet.py"""
import os, sys, json
PROJECT = os.path.abspath(os.environ.get('PLANNIT_PROJECT') or sys.exit('set PLANNIT_PROJECT to the project folder'))
sys.path.insert(0, PROJECT)
import existing as X, proposal as PR
import model
model.defaults(X, PR)
import sheets
from sheet import Sheet, m2, rect
OUT = os.path.join(PROJECT, 'out', 'renders')
def base():
    """The model's part of every proposal sheet: demolition, walls, narrowed openings, columns, openings, beams,
    and the Blender fittings the project lists."""
    walls, opens, cutaways = [], [], []
    for wid, x0, x1, z0, z1, ops, tag, cut in model.walls(X, PR):
        walls.append((x0, x1, z0, z1, 'new' if tag in ('new', 'infill') else 'old'))
        ax = (x1 - x0) >= (z1 - z0); c = (z0 + z1) / 2 if ax else (x0 + x1) / 2; t = (z1 - z0) if ax else (x1 - x0)
        for a, b, sill, head, kind in ops:
            pa, pb = ((a, c), (b, c)) if ax else ((c, a), (c, b))
            oid = next((k for k, v in X.OPENINGS.items() if v[0] == wid and abs(v[1] - a) < 0.02 and abs(v[2] - b) < 0.02), None)
            hd = ('~' if oid in PR.ASSUMED_HEAD else '') + m2(head)
            spec = None if kind == 'closet' else (m2(b - a), hd, m2(sill) if kind == 'window' else None)
            opens.append(('door' if kind == 'glazed' else kind, pa, pb, t, spec))
            if a in cut: cutaways.append(rect(a, b, z0, z1) if ax else rect(x0, x1, a, b))   # masonry removed for it
    for c, u0, u1, ax in PR.CLOSET_FRONTS.values():
        opens.append(('closet', (u0, c) if ax else (c, u0), (u1, c) if ax else (c, u1), 0.02, None))
    sh = Sheet(PR.ROOMS, sheets.CIRCULATION, sheets.LABELS)
    for _w, x0, x1, z0, z1 in model.demolished(X, PR): sh.walls([(x0, x1, z0, z1, 'demolished')], [])
    for q in cutaways: sh.solid('DEMOLISHED_FILL', q); sh.pline('DEMOLISHED', q)
    sh.walls(walls, opens)
    # openings the proposal narrows: the part that is bricked up is new masonry
    for oid, ch in PR.OPENING_CHANGES.items():
        if not ch: continue
        wid, a, b = X.OPENINGS[oid][:3]; x0, x1, z0, z1 = X.WALLS[wid][:4]; ax = model.along_x(X, wid)
        for u0, u1 in ((a, ch[0]), (ch[1], b)):
            if u1 - u0 > 0.01:
                q = rect(u0, u1, z0, z1) if ax else rect(x0, x1, u0, u1); sh.solid('NEW_WALLS', q); sh.pline('WALLS', q); sh.solids.append(q)
    sh.columns([c[:4] for c in X.COLUMNS.values()])
    sh.openings(opens)
    sh.beams([b[:5] for b in X.BEAMS.values()])
    # fittings from the Blender model: what an engineer or a plumber needs to see on the plan
    dump = os.path.join(OUT, 'model-dump.json')
    if os.path.exists(dump):
        seen = set()
        for n, x0, x1, z0, z1, h0, h1, _m in json.load(open(dump))['shapes']:
            key = (n, round(x0, 2), round(x1, 2), round(z0, 2), round(z1, 2))
            if key in seen or not (n in sheets.FIXTURES or n in sheets.FURNITURE): continue
            seen.add(key); sh.pline('FIXTURES' if n in sheets.FIXTURES else 'FURNITURE', rect(x0, x1, z0, z1))
    else:
        print('no renders/model-dump.json — fittings left off; run the Blender svg pass first')
    return sh, opens


# one sheet per entry: A.2 the proposal, A.3 the works, … — each (name, finish) = the project's hook(sheet)
for hook in sheets.PROPOSAL_SHEETS:
    sh, opens = base()
    name, finish = hook(sh)
    sh.finish(os.path.join(OUT, name), **finish)
    print(name, 'entities', len(sh.E), 'openings', len(opens))
