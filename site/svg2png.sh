#!/bin/bash
# svg2png.sh IN.svg OUT.png [WIDTH,HEIGHT]
# debnuc has no PIL/cairosvg/rsvg, so SVGs are turned into PNGs by screenshotting them in headless
# Firefox — the same trick the scan build.sh uses. The size defaults to the SVG's own
# width/height attributes.
set -euo pipefail
IN="$(realpath "$1")"; OUT="$(realpath -m "$2")"
SIZE="${3:-}"
if [ -z "$SIZE" ]; then
  W=$(grep -om1 'width="[0-9]*"' "$IN" | tr -dc 0-9 || true)
  H=$(grep -om1 'height="[0-9]*"' "$IN" | tr -dc 0-9 || true)
  SIZE="${W:-1200},${H:-900}"
fi
PROF="$(mktemp -d)"; trap 'rm -rf "$PROF"' EXIT
firefox --headless --no-remote --profile "$PROF" --window-size="$SIZE" \
        --screenshot "$OUT" "file://$IN" >/dev/null 2>&1 || true
[ -s "$OUT" ] || { echo "svg2png: firefox produced nothing for $IN" >&2; exit 1; }
echo "wrote $OUT ($SIZE)"
