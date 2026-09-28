#!/bin/bash
# By-hand renders of a packed job, on the render box itself (no queue) — full quality.
# Run in a job directory made by farm/pack.sh (it has the scene.py entry):
#   bash render-debof.sh [draft|final|max] [camera,camera,...]   (JOB=<dir> to point elsewhere)
#   draft  1280x800,   64 spp  (~seconds per image on the GPU)
#   final  1920x1200, 256 spp  (default)
#   max    2560x1600, 512 spp
# Output: renders-<preset>/ in the job directory.
# Blender 4.5 LTS is fetched into ~/.cache/blender the first time (~350 MB, not backed up).
set -euo pipefail
HERE="$(cd "${JOB:-.}" && pwd)"
[ -f "$HERE/scene.py" ] || { echo "no scene.py in $HERE — make a job with farm/pack.sh"; exit 1; }
PRESET="${1:-final}"; ONLY="${2:-}"
case "$PRESET" in
  draft) PCT=80;  SPP=64  ;;
  final) PCT=120; SPP=256 ;;
  max)   PCT=160; SPP=512 ;;
  *) echo "preset must be draft|final|max"; exit 1 ;;
esac

VER=4.5.14; BDIR="$HOME/.cache/blender/blender-$VER-linux-x64"; B="$BDIR/blender"
if [ ! -x "$B" ]; then
  echo "== downloading Blender $VER"
  mkdir -p "$HOME/.cache/blender"
  curl -fL --progress-bar "https://download.blender.org/release/Blender4.5/blender-$VER-linux-x64.tar.xz" \
    | tar xJ -C "$HOME/.cache/blender"
fi

# GPU: OptiX (RTX) first, then CUDA, else CPU
if command -v nvidia-smi >/dev/null && nvidia-smi -L >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
  export RENDER_DEVICE=OPTIX
else
  echo "!! nvidia-smi not working — rendering on CPU (slow)"; export RENDER_DEVICE=CPU
fi

export RENDER_OUT="$HERE/renders-$PRESET"; mkdir -p "$RENDER_OUT"
LOG="$RENDER_OUT/render.log"; exec > >(tee -a "$LOG") 2>&1
echo "== $(date '+%F %T')  preset=$PRESET (${PCT}% , ${SPP} spp)  device=$RENDER_DEVICE  out=$RENDER_OUT"

pick(){ # $1 = the pass's cameras; honour the optional camera filter
  [ -z "$ONLY" ] && { echo "$1"; return; }
  local out=""; for c in ${1//,/ }; do [[ ",$ONLY," == *",$c,"* ]] && out="$out,$c"; done; echo "${out#,}"
}
run(){ # mode cameras
  local cams; cams="$(pick "$2")"; [ -z "$cams" ] && return 0
  echo "== $1: $cams"; local t0=$SECONDS
  if ! "$B" -b -P "$HERE/scene.py" -- "$1" "$cams" "$PCT" "$SPP" 2>&1 | grep --line-buffered -E "^(RENDERED|GPU:)|Error|Traceback|no OPTIX"; then :; fi
  # OptiX can fail on a driver too old for Blackwell cards; retry once on CUDA
  if [ "$RENDER_DEVICE" = OPTIX ] && ! ls "$RENDER_OUT"/"${cams%%,*}".jpg >/dev/null 2>&1; then
    echo "!! OptiX pass produced nothing — retrying on CUDA"; export RENDER_DEVICE=CUDA
    "$B" -b -P "$HERE/scene.py" -- "$1" "$cams" "$PCT" "$SPP" 2>&1 | grep --line-buffered -E "^(RENDERED|GPU:)|Error|Traceback" || true
  fi
  echo "   $(( SECONDS - t0 )) s"
}
run interior tv,sofa,kitchen,kitchen2,study,entrance,bathroom,bedroom1,bedroom2
run cutaway  axo_sw,axo_ne
run plan     plan
echo "== done $(date '+%F %T')"; ls -la "$RENDER_OUT"
