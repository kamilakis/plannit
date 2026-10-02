#!/bin/bash
# pack.sh — make a render-farm job directory: the engine plus one project, nothing else.
#
#   farm/pack.sh <project>          a project folder (or a name under projects/) → prints the job directory,
#                                   <project>/build-job/<project name>/  (render-submit <project> does this itself)
#
# render-submit (farm/render-submit) copies one directory to debof and runs
# `blender -b -P scene.py -- …` in it, then ships back <job>/renders/. Until the engine/project split
# that directory was renovation-design/; now it is built here, in the same shape:
#   <job>/scene.py           entry: runs engine/blender/build.py against <job>/project
#   <job>/engine/            the engine, copied
#   <job>/project/           the project's model files (*.py, *.json at its top level, FORCE/HASHDEBUG if
#                            present) and out/render-hashes.json — what build.py reads, and no more
#   <job>/renders/           where the renders land (RENDER_OUT, unless the farm sets its own)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/lib/common.sh"
PROJ="$(project_dir "${1:?usage: farm/pack.sh <project>}")" || exit 1
NAME="$(basename "$PROJ")"                      # the job's name on the farm
JOB="$PROJ/build-job/$NAME"
rm -rf "$JOB"; mkdir -p "$JOB/project/out"

cp -a "$ROOT/engine" "$JOB/engine"
find "$JOB/engine" -name __pycache__ -prune -exec rm -rf {} +
for f in "$PROJ"/*.py "$PROJ"/*.json "$PROJ"/FORCE "$PROJ"/HASHDEBUG; do
  [ -f "$f" ] && cp -a "$f" "$JOB/project/"
done
[ -f "$PROJ/out/render-hashes.json" ] && cp -a "$PROJ/out/render-hashes.json" "$JOB/project/out/"
[ -d "$PROJ/assets" ] && cp -a "$PROJ/assets" "$JOB/project/"   # files the scene loads (images for image_mat)

cat > "$JOB/scene.py" <<'EOF'
# Render-farm entry, written by farm/pack.sh: builds <this dir>/project with <this dir>/engine.
#   blender -b -P scene.py -- MODE CAMS PCT SAMPLES
import os, runpy
H = os.path.dirname(os.path.abspath(__file__))
os.environ['PLANNIT_PROJECT'] = os.path.join(H, 'project')
os.environ.setdefault('RENDER_OUT', os.path.join(H, 'renders'))
runpy.run_path(os.path.join(H, 'engine', 'blender', 'build.py'), run_name='__main__')
EOF
echo "$JOB"
