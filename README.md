# plannit

From a surveyed flat to a renovation proposal: 1:50 survey sheets (DXF / SVG / PDF), photoreal Blender renders
(with a GPU render farm that only re-renders what changed), a 3D web viewer, and a static site to show it all.
The tool knows no facts about any flat. Each flat is a **project**: a folder of data plus a few scripts that
call the tool, usually its own git repository with plannit as a submodule.

```
plannit/
├── engine/              model logic, the survey sheets, Blender (build.py + helpers), scan intake
├── farm/                render farm: pack a job, submit it, the watcher on the GPU box (farm/README.md)
├── site/                the site publisher and page tools
├── tools/               proof.sh (prove a refactor changed nothing), fixture-check.sh, split-out-project.sh
├── lib/common.sh        shared shell: find a project, load the farm config
└── projects/fixture/    the smallest complete project (two rooms, one door, one window) — the test
```

## A project

A folder with these files (see `projects/fixture/` for the minimum, and `engine/model.py` for the model's fields):

| file | what | read by |
|---|---|---|
| `existing.py` | the flat today, data only: `CEIL`, `WALLS`, `OPENINGS`, `ROOMS` (+ optional `CLOSET_FRONTS`, `BEAMS`, `COLUMNS`, `FITTINGS`) | everything |
| `proposal.py` | the renovation as changes, data only: `ROOMS` (+ optional `DEMOLISH`, `RESIZE`, `OPENING_CHANGES`, `NEW_OPENINGS`, `NEW_WALLS`, `ASSUMED_HEAD`, `CLOSET_FRONTS`, `REMOVE_FITTINGS`) | everything |
| `views.py` | data: `PALETTES`, `CUTS`, `SKY`, `SUN`, `CAMERAS` (`interior`, `cutaway`, `plan`) | Blender |
| `design.py` | furniture, fittings, lights, people — calls into `engine.blender.api`, in build order | Blender |
| `sheets.py` | what the sheets say: `CIRCULATION`, `LABELS`, `FIXTURES`, `FURNITURE`, `asbuilt(sh)`, `PROPOSAL_SHEETS` | the sheets |
| `project.conf` | where the site goes, sheet file names, Artifacts, viewer models (`KEY="value"` lines) | site, proof |

Generated into the project: `out/` (renders, sheets, `render-hashes.json`), `build-site/`, `build-job/`, and
`proof-baseline.txt` (`tools/proof.sh <project> record`).

## Use

```bash
# sheets (stdlib Python)
cd <project>/out/scan && PLANNIT_PROJECT=<project> python3 <plannit>/engine/asbuilt_sheet.py
PLANNIT_PROJECT=<project> python3 <plannit>/engine/proposal_sheet.py
# Blender 4.5: MODE interior | night | cutaway | plan | glb (+ -b/-c/-d palettes) | svg (the model dump)
PLANNIT_PROJECT=<project> blender -b -P <plannit>/engine/blender/build.py -- interior all 100 128
# the render farm (config: farm/farm.conf.example -> ~/.config/plannit/farm.conf)
render-submit <project> draft "interior:tv"
# the site
<plannit>/site/publish.sh <project> --local | --dry-run | --collect
# proofs
<plannit>/tools/proof.sh <project> record | check      # sheets, model, every render's fingerprint
<plannit>/tools/fixture-check.sh                       # the fixture through everything
```

Blender for the proofs without a Blender install: `pip install bpy==4.5.*` in a Python 3.11 venv, then `BPY=<its python>`.

## Limits

Walls are axis-aligned rectangles; one floor, one ceiling height. The sheets' fixed text is Greek and their
north arrow points to plan +x. Page prose is written per project. `site/publish.sh` builds the pages a project
has (`PLAYBOOK.md`, `content/presentation`, `content/viewer-3d`, `content/measure-form`).
