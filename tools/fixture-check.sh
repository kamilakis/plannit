#!/bin/bash
# fixture-check.sh — run projects/fixture (two rooms, one door, one window) through the whole pipeline:
# sheets F.1 / F.2, the Blender model dump, one real render (tiny: 20 %, 4 samples), the viewer GLB, a render-farm
# job (packed, fingerprinted through its scene.py entry) and a local site build. It must pass without touching
# engine/ or site/: if it needs a change there, something project-specific is still hard-coded.
#   tools/fixture-check.sh          Blender: $BLENDER (default blender) or $BPY (a python with bpy 4.5)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; P="$ROOT/projects/fixture"; export PLANNIT_PROJECT="$P"
blend() { if [ -n "${BPY:-}" ]; then "$BPY" "$@"; else "${BLENDER:-blender}" -b -P "$@"; fi; }
ok() { echo "  ok  $*"; }; die() { echo "  !!  $*" >&2; exit 1; }
rm -rf "$P/out" "$P/build-site" "$P/build-job"; mkdir -p "$P/out/scan" "$P/out/renders"
( cd "$P/out/scan" && python3 "$ROOT/engine/asbuilt_sheet.py" >/dev/null ) && [ -s "$P/out/scan/fixture-asbuilt.dxf" ] && ok "sheet F.1 (as built)"
blend "$ROOT/engine/blender/build.py" -- svg 2>&1 | grep -q '^RENDERED svg' && [ -s "$P/out/renders/model-dump.json" ] && ok "model dump" || die "svg pass"
python3 "$ROOT/engine/proposal_sheet.py" >/dev/null && [ -s "$P/out/renders/fixture-proposal.dxf" ] && ok "sheet F.2 (proposal, with the fittings)"
blend "$ROOT/engine/blender/build.py" -- interior all 20 4 2>&1 | grep -q '^RENDERED room' && [ -s "$P/out/renders/room.jpg" ] && ok "render room.jpg" || die "render"
blend "$ROOT/engine/blender/build.py" -- glb 2>&1 | grep -q '^RENDERED glb' && [ -s "$P/out/renders/flat.glb" ] && ok "viewer GLB" || die "glb"
J=$("$ROOT/farm/pack.sh" "$P")
( cd /tmp && RENDER_HASHONLY=1 blend "$J/scene.py" -- interior all ) 2>&1 | grep -q '^HASH room.jpg' && ok "farm job: packed, fingerprinted via its scene.py" || die "farm job"
"$ROOT/site/publish.sh" "$P" --local >/dev/null 2>&1 && [ -s "$P/build-site/cad/fixture-proposal.dxf" ] && ok "site (local build)" || die "site"
echo "fixture: the whole pipeline ran without project-specific code in engine/, farm/ or site/"
