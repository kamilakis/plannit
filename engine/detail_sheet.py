"""The DETAIL sheets (a kitchen's plan and elevations, a window schedule, …): one per entry in the project's
details.DETAIL_SHEETS, each a hook that returns (file name, detail.Paper) -> <project>/out/renders/<name>.{dxf,svg}
(PDF via print_pdf.py in.svg out.pdf 420 297). The hooks read the model (existing.py, proposal.py) and the
Blender boxes in out/renders/model-dump.json (the Blender 'svg' pass, or tools/nobl.py). Stdlib only.
    PLANNIT_PROJECT=<project> python3 engine/detail_sheet.py [sheet name or hook name …]
(A hook may return a list of (name, Paper): a set of sheets, as many as its contents need.)"""
import os, sys
PROJECT = os.path.abspath(os.environ.get('PLANNIT_PROJECT') or sys.exit('set PLANNIT_PROJECT to the project folder'))
sys.path.insert(0, PROJECT)
import existing as X, proposal as PR
import model
model.defaults(X, PR)
import details
OUT = os.path.join(PROJECT, 'out', 'renders')
want = sys.argv[1:]
for hook in details.DETAIL_SHEETS:
    got = hook()
    for name, paper in (got if isinstance(got, list) else [got]):        # a hook returns one sheet or a list of them
        if want and name not in want and hook.__name__ not in want: continue
        paper.write(os.path.join(OUT, name))
        print(name, 'entities', len(paper.E))
