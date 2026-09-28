"""The as-built plan, surveyor style (1:50, A3, DXF + SVG), drawn with sheet.py from the project's existing.py —
the master file: walls, openings with their width/head/sill tags (m measured, ~ estimated, ? unknown),
closet fronts, columns, beams. Everything else on the sheet — overlays, room labels, dimension chains,
title block, legend, notes and the file name — comes from the project's sheets.py (asbuilt()).
Run in <project>/out/scan with PLANNIT_PROJECT set (the project's scan/build.sh does, and prints the SVG to
PDF/PNG). Plan frame: x, z metres."""
import os, sys
PROJECT = os.path.abspath(os.environ.get('PLANNIT_PROJECT') or sys.exit('set PLANNIT_PROJECT to the project folder'))
sys.path.insert(0, PROJECT)
import existing as X
import model
model.defaults(X)
import sheets
from sheet import Sheet, m2
def fmt(v, src): return '?' if v is None else ('' if src == 'm' else '~') + m2(v)
# openings: (kind, a, b, thickness, (width, head, sill)), a/b on the wall's centre line
opens = []
for oid, (wid, u0, u1, kind, sill, head, src, _) in X.OPENINGS.items():
    x0, x1, z0, z1 = X.WALLS[wid][:4]; ax = model.along_x(X, wid)
    c = (z0 + z1) / 2 if ax else (x0 + x1) / 2; t = (z1 - z0) if ax else (x1 - x0)
    a, b = ((u0, c), (u1, c)) if ax else ((c, u0), (c, u1))
    opens.append(('door' if kind == 'glazed' else kind, a, b, t,
                  (fmt(u1 - u0, src[0]), fmt(head, src[2]), fmt(sill, src[2]) if kind == 'window' else None)))
for c, u0, u1, ax in X.CLOSET_FRONTS.values():
    opens.append(('closet', (u0, c) if ax else (c, u0), (u1, c) if ax else (c, u1), 0.10, None))
sh = Sheet(X.ROOMS, sheets.CIRCULATION, sheets.LABELS)
sh.walls([(x0, x1, z0, z1, 'old') for x0, x1, z0, z1, *_ in X.WALLS.values()], opens)
sh.columns([c[:4] for c in X.COLUMNS.values()])
sh.openings(opens)
sh.beams([b[:5] for b in X.BEAMS.values()])
base, finish = sheets.asbuilt(sh)
sh.finish(base, **finish)
print('entities',len(sh.E),'openings',len(opens))
