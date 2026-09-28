#!/bin/bash
# publish-artifact.sh — get the claude.ai viewer Artifact ready to refresh from the page publish.sh just built.
#
#   site/publish-artifact.sh <project> ["label"]   stage + verify the page, print the publish step
#
# IT DOES NOT PUBLISH, and cannot. Until 26 Sep it shelled out to a headless `claude -p` with only the
# Artifact tool allowed, and printed "updated in place" whenever the reply contained the artifact ID.
# It never once worked: the headless session has no Artifact tool, its refusal quoted the ID, so the
# guard matched and the script reported success having published nothing (22 and 26 Sep).
# Even with the tool it could not: the Artifact tool refuses to overwrite a version it has not read in
# full, a read of this multi-MB page comes back truncated, so every refresh needs `force: true` — and
# that needs the owner's explicit OK each time. So the publish itself is an interactive Claude Code step.
#
# What this script does:
#  1. copies build-site/viewer/artifact.html (written by site/publish.sh — models inlined, claude.ai links
#     intact) to the path the viewer was first published from (project.conf ARTIFACT_VIEWER_ROOT);
#  2. checks each inlined model decodes to the GLB in <project>/out/renders/, byte for byte;
#  3. writes the page minus the base64 to viewer-stripped.html, so the publishing session can read
#     the whole page (the tool's rule) without reading 3.6 MB of base64;
#  4. prints the exact Artifact call to make.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/../lib/common.sh"
PROJ="$(project_dir "${1:?usage: site/publish-artifact.sh <project> [label]}")" || exit 1
. "$PROJ/project.conf"
BUILT="$PROJ/build-site/viewer/artifact.html"              # written by site/publish.sh
GLBS="$PROJ/out/renders"
ART_ROOT="$HOME/$ARTIFACT_VIEWER_ROOT"                    # the path the artifact was first published from
SRC="$ART_ROOT/index.html"
URL=$(for a in $ARTIFACTS; do [ "${a#*=}" = viewer/ ] && echo "https://claude.ai/artifact/${a%%=*}"; done)   # viewer artifact the site links to
LABEL="${2:-$(date '+%d %b') refresh}"

[ -f "$BUILT" ] || { echo "!! $BUILT is missing — run ./publish.sh first" >&2; exit 1; }
mkdir -p "$ART_ROOT" && cp -f "$BUILT" "$SRC"

python3 - "$SRC" "$GLBS" "$ART_ROOT/viewer-stripped.html" <<'PY'
import re, sys, base64, hashlib, os
src, glbs, stripped = sys.argv[1:]
s = open(src).read()
pat = r'(<script type="text/plain" id="model-(\w)">)(.*?)(</script>)'
found = re.findall(pat, s, re.S)
if not found: sys.exit('!! no inlined models in the page')
bad = 0
for _, k, b64, _ in found:
    raw = base64.b64decode(re.sub(r'\s', '', b64))
    glb = os.path.join(glbs, 'flat.glb' if k == 'a' else f'flat_{k}.glb')
    ok = os.path.exists(glb) and open(glb, 'rb').read() == raw
    bad += not ok
    print(f'  model-{k}: {len(raw)} bytes, md5 {hashlib.md5(raw).hexdigest()[:8]} — '
          + ('matches ' + os.path.basename(glb) if ok else f'!! does NOT match {glb}'))
if bad: sys.exit('!! inlined models differ from the GLBs — rerun ./publish.sh')
open(stripped, 'w').write(re.sub(pat, r'\1[GLB]\4', s, flags=re.S))
PY

cat <<EOF

staged $SRC ($(du -h "$SRC" | cut -f1), built $(date -r "$BUILT" '+%F %H:%M')) — NOT published yet.

In an interactive Claude Code session (it has the Artifact tool):
  1. read $ART_ROOT/viewer-stripped.html — the whole page minus the verified base64
  2. Artifact publish:
       url:       $URL
       file_path: $SRC
       label:     $LABEL
     (no icon — it is a redeploy)
  3. it will refuse: the live version reads back truncated. Get the owner's explicit OK,
     then repeat with force: true. Pass the URL, not just the path — the URL keeps the link.
EOF
