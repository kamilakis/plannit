#!/bin/bash
# proof.sh — prove a refactor changed nothing (engine/project split, ENGINE-SPLIT-PLAN.md).
#
#   tools/proof.sh <project>            print the proof: one "name  hash" line per output
#   tools/proof.sh <project> record     write it to <project>/proof-baseline.txt
#   tools/proof.sh <project> check      compare against it, exit 1 on any difference
# <project>: a project folder, or a name under plannit's projects/.
#
# What it covers:
#   - the sheets named in project.conf (SHEETS_ASBUILT, SHEETS_PROPOSAL): DXF + SVG — stdlib, rebuilt in place
#   - the Blender model: svg pass (model-dump.json), glb per palette
#   - every render's fingerprint (scene.py with RENDER_HASHONLY=1: fingerprints, no render), all
#     modes x palettes A/B/D. Same fingerprint = same image, so no render is needed to prove it.
# Blender: $BLENDER (default "blender"), or $BPY = a python with the bpy 4.5 module (pip install bpy==4.5.*).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
. "$HERE/lib/common.sh"
PROJ="$(project_dir "${1:?usage: tools/proof.sh <project> [record|check]}")" || exit 1; shift
. "$PROJ/project.conf"
ENGINE="$HERE/engine"
BASE="$PROJ/proof-baseline.txt"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
PAR="${PROOF_JOBS:-$(nproc)}"

scene() {   # engine/blender/build.py MODE [CAMS] with output into $TMP/pass-$MODE
  local out="$TMP/pass-$1"; mkdir -p "$out"
  export PLANNIT_PROJECT="$PROJ" RENDER_OUT="$out" RENDER_HASHONLY=1
  if [ -n "${BPY:-}" ]; then "$BPY" "$ENGINE/blender/build.py" -- "$@"
  else "${BLENDER:-blender}" -b -P "$ENGINE/blender/build.py" -- "$@"; fi \
    > "$out.log" 2>&1 || { echo "!! scene.py $* failed, see below" >&2; tail -20 "$out.log" >&2; return 1; }
}
export -f scene; export PROJ ENGINE TMP BPY BLENDER

build() {
  # --- sheets (stdlib)
  ( cd "$PROJ/out/scan" && PLANNIT_PROJECT="$PROJ" python3 "$ENGINE/asbuilt_sheet.py" >/dev/null )
  PLANNIT_PROJECT="$PROJ" python3 "$ENGINE/proposal_sheet.py" >/dev/null
  # --- Blender passes, in parallel
  printf '%s\n' interior night cutaway plan interior-b night-b cutaway-b plan-b \
                interior-d night-d cutaway-d plan-d svg glb glb-b glb-d \
    | xargs -P "$PAR" -I{} bash -c 'scene {}'
}

report() {
  local n f
  for n in $SHEETS_ASBUILT; do for f in "$PROJ/out/scan/$n".{dxf,svg}; do
    echo "sheet/$(basename "$f")  $(sha256sum < "$f" | cut -c1-16)"
  done; done
  for n in $SHEETS_PROPOSAL; do for f in "$PROJ/out/renders/$n".{dxf,svg}; do
    echo "sheet/$(basename "$f")  $(sha256sum < "$f" | cut -c1-16)"
  done; done
  for f in "$TMP"/pass-svg/model-dump.json "$TMP"/pass-glb*/*.glb; do
    echo "model/$(basename "$f")  $(sha256sum < "$f" | cut -c1-16)"
  done
  cat "$TMP"/pass-*.log | awk '/^HASH /{print "render/" $2 "  " $3}' | sort
}

build
report > "$TMP/proof.txt"
n=$(grep -c '^render/' "$TMP/proof.txt"); [ "$n" -gt 0 ] || { echo "!! no fingerprints produced" >&2; exit 1; }
case "${1:-}" in
  record) cp "$TMP/proof.txt" "$BASE"; echo "recorded $(wc -l < "$BASE") proofs ($n render fingerprints) -> $BASE" ;;
  check)  if diff -u "$BASE" "$TMP/proof.txt"; then echo "OK: $(wc -l < "$BASE") proofs identical"; else echo "!! outputs changed" >&2; exit 1; fi ;;
  *)      cat "$TMP/proof.txt" ;;
esac
