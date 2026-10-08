#!/bin/bash
# site/publish.sh — assemble a project's site and push it to its web server. Host, docroot, URL, Artifacts and
# page settings come from <project>/project.conf; the render queue from the farm config (lib/common.sh).
# <project> is a path to the project folder (or a name under plannit's projects/, e.g. fixture). The site is
# staged in <project>/build-site/; drafts come from <project>/tmp/.
#
#   site/publish.sh <project>                rebuild the playbook page and rsync everything
#   site/publish.sh <project> --collect      first pull the newest finished render job into renders-final/
#   site/publish.sh <project> --collect=JOB  ... or that job exactly (test jobs are named *-final too — be explicit)
#                                            and refresh content/presentation/ with it, then publish
#   site/publish.sh <project> --dry-run      show what would change on the server, send nothing
#   site/publish.sh <project> --local        build into build-site/ and stop (inspect before pushing)
#   (a project's own ./publish.sh is usually just this, for itself)
#
# It also builds a dated, unlisted preview under /preview/ for anything the presentation page marks
# as not-yet-live — nothing is marked at the moment; see site/page-variants.py.
#
# The site is static: the docroot is owned by the ssh user, so no sudo is needed.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"           # plannit
. "$HERE/lib/common.sh"
NAME_ARG="${1:-}"; [ -n "$NAME_ARG" ] && [ "${NAME_ARG#-}" = "$NAME_ARG" ] || { sed -n '2,18p' "$0"; exit 1; }
shift
PROJ="$(project_dir "$NAME_ARG")" || exit 1
. "$PROJ/project.conf"
farm_conf -q; : "${RENDER_QUEUE:=render-queue}"
HOST="$SITE_HOST"
DOCROOT="$SITE_DOCROOT"
STAGE="$PROJ/build-site"
QUEUE="$HOME/$RENDER_QUEUE/done"

COLLECT=0; DRY=0; LOCAL=0
for a in "$@"; do
  case "$a" in
    --collect) COLLECT=1 ;;
    --collect=*) COLLECT=1; CJOB="${a#--collect=}" ;;
    --dry-run) DRY=1 ;;
    --local)   LOCAL=1 ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "unknown option: $a"; exit 1 ;;
  esac
done

RENDERS="$PROJ/out/renders"
FINAL="$PROJ/out/renders-final"
SCANOUT="$PROJ/out/scan"
PRES="$PROJ/content/presentation"
SITE="$HERE/site"

# Everything else in this project works from a copy of the directory, so you can experiment in a
# .bak without touching the real one.  Publishing is the exception: it would push the copy's
# content over the live site.  Building (--local) and --dry-run stay allowed from anywhere.
CANONICAL="$HOME/$PUBLISH_FROM"
if [ -z "$SITE_HOST" ] && [ "$LOCAL" = 0 ]; then echo "!! $NAME_ARG has no web server (project.conf SITE_HOST): use --local"; exit 1; fi
if [ "$PROJ" != "$CANONICAL" ] && [ "$LOCAL" = 0 ] && [ "$DRY" = 0 ] && [ -z "${PUBLISH_FROM_COPY:-}" ]; then
  cat >&2 <<EOF
!! refusing to publish: this is a copy of the project
     here:      $PROJ
     canonical: $CANONICAL
   Pushing from here would replace $SITE_URL with this copy's content.
     site/publish.sh $NAME_ARG --local     build into $PROJ/build-site/ and look at it
     site/publish.sh $NAME_ARG --dry-run   show what would change on the server
     PUBLISH_FROM_COPY=1 site/publish.sh $NAME_ARG   publish anyway (you meant it)
EOF
  exit 1
fi

# ------------------------------------------------------------------ collect renders
if [ "$COLLECT" = 1 ]; then
  if [ -n "${CJOB:-}" ]; then JOB="$QUEUE/$CJOB/"; else JOB="$(ls -1dt "$QUEUE"/*-final/ 2>/dev/null | head -1 || true)"; fi
  [ -n "$JOB" ] && [ -d "$JOB/renders" ] || { echo "!! no finished final job in $QUEUE"; exit 1; }
  echo "== collecting $(basename "$JOB")"
  mkdir -p "$FINAL" "$RENDERS"
  cp -f "$JOB"renders/*.jpg "$FINAL/" 2>/dev/null || true
  # GLBs for the web viewer don't live in renders-final (that's jpg-only) — they're read straight out
  # of out/renders/ by publish.sh's viewer step, so a job's .glb output has to land there too.
  cp -f "$JOB"renders/*.glb "$RENDERS/" 2>/dev/null || true
  # the model dump (svg pass) feeds the A.2 proposal sheet's fittings — only palette-A jobs run that pass
  [ -f "$JOB"renders/model-dump.json ] && cp -f "$JOB"renders/model-dump.json "$RENDERS/"
  # which images this job rendered, and from what: merged into the manifest build.py checks next time
  [ -f "$JOB"renders/render-hashes.json ] && python3 - "$JOB"renders/render-hashes.json "$PROJ/out/render-hashes.json" <<'PY'
import json, sys
new = json.load(open(sys.argv[1]))
try: old = json.load(open(sys.argv[2]))
except Exception: old = {}
old.update(new); json.dump(old, open(sys.argv[2], 'w'), indent=0, sort_keys=True)
print(f'   render-hashes: {len(new)} images recorded, {len(old)} in the manifest')
PY
  # The presentation page holds its own copies next to its HTML; keep only the views it uses. The page
  # swaps in "<view>_b" / "<view>_night" by name at runtime, so for every view it shows, bring across
  # whichever variants exist — otherwise a newly-rendered variant (a palette added to a view that never
  # had one) lands in renders-final and 404s on the page, because this loop only saw the old files.
  for f in "$PRES"/*.jpg; do
    n="$(basename "$f" .jpg)"; n="${n%_empty}"; n="${n%_night}"; n="${n%_b}"; n="${n%_d}"
    for v in "$n" "${n}_night" "${n}_b" "${n}_b_night" "${n}_d" "${n}_d_night" "${n}_empty"; do   # palettes A, B, D; the empty flat (8 Oct)
      [ -f "$FINAL/$v.jpg" ] && cp -f "$FINAL/$v.jpg" "$PRES/$v.jpg"
    done
  done
  echo "   renders-final: $(ls -1 "$FINAL"/*.jpg 2>/dev/null | wc -l) images, $(ls -1 "$RENDERS"/*.glb 2>/dev/null | wc -l) GLBs"
fi

# ------------------------------------------------------------------ build
rm -rf "$STAGE"; mkdir -p "$STAGE"/{renders,drawings,cad}
# Every page step below runs only if the project has that page: PLAYBOOK.md, content/presentation,
# content/viewer-3d, content/measure-form, options/. The sheets are named in project.conf.
# project.conf SITE_HOME picks the page served at the site root: 'playbook' (default - the playbook IS the
# root index) or 'presentation' (the root redirects to /presentation/ and the playbook moves to /playbook/).
: "${SITE_HOME:=playbook}"
case "$SITE_HOME" in playbook|presentation) ;; *) echo "!! project.conf SITE_HOME must be playbook or presentation" >&2; exit 1 ;; esac
PB_DIR="$STAGE"; PB_REL=""; [ "$SITE_HOME" = presentation ] && { PB_DIR="$STAGE/playbook"; PB_REL="playbook/"; }

if [ -f "$PROJ/PLAYBOOK.md" ]; then
echo "== playbook${PB_REL:+ (at /$PB_REL)}"
mkdir -p "$PB_DIR"
python3 "$SITE/md2html.py" "$PROJ/PLAYBOOK.md" "$PB_DIR/index.html" "$PLAYBOOK_TITLE"
cp "$PROJ/PLAYBOOK.md" "$PB_DIR/playbook.md"
fi
for f in $SITE_EXTRA; do cp "$PROJ/$f" "$STAGE/" 2>/dev/null || true; done

cat > "$STAGE/robots.txt" <<'EOF'
# unlisted: these pages are not meant to be indexed
User-agent: *
Disallow: /
EOF

# on our own host the pages live next door, not on claude.ai (project.conf ARTIFACTS: id=page)
export PLANNIT_ARTIFACTS="$ARTIFACTS"                # page-variants.py rewrites the same links
artifact_url() { local a; for a in $ARTIFACTS; do [ "${a#*=}" = "$1" ] && echo "https://claude.ai/artifact/${a%%=*}"; done; true; }
linkfix() { local a args=(); for a in $ARTIFACTS; do args+=(-e "s#https://claude.ai/artifact/${a%%=*}#../${a#*=}#g"); done
  [ ${#args[@]} -eq 0 ] || sed -i "${args[@]}" "$1"; }

PREVIEW_REL=""
if [ -d "$PRES" ]; then
echo "== presentation"
mkdir -p "$STAGE/presentation"
cp -a "$PRES/." "$STAGE/presentation/"
# The plan figures are generated into renders/ (and the survey plan in the scan output), but the page
# serves its own copies from its own folder. Until 19 Sep those were copied by hand, so a regenerated
# drawing silently did not reach the page — plan2d.png, stairs2d.png and before.png were all stale.
# (27 Sep: the Drawing tab is gone; Engineer and Contractor show the A.1/A.2/A.3 sheets straight from /cad/.)
for f in $PAGE_FIGURES; do
  [ -f "$RENDERS/$f.png" ] && cp -f "$RENDERS/$f.png" "$STAGE/presentation/$f.png"
done
# «Σήμερα» shows the as-built sheet A.1, drawn from the project's existing.py (was the scan's coloured plan)
A1="${SHEETS_ASBUILT%% *}"
[ -n "$A1" ] && [ -f "$SCANOUT/$A1.png" ] && \
  cp -f "$SCANOUT/$A1.png" "$STAGE/presentation/before.png"
# Staleness is handled per image now: engine/blender/build.py fingerprints every view and render-hashes.json (merged at
# --collect) records what each image in renders-final was rendered from — see "Rendering only what changed".
linkfix "$STAGE/presentation/index.html"
# The Engineer and Contractor tabs are live now; the preview step above only runs when the source
# marks something as not-yet-live.
python3 "$SITE/page-variants.py" live "$STAGE/presentation/index.html" "$STAGE/presentation/index.html"

# The Engineer and Contractor tabs are live now. If a future change needs showing before it goes
# live, mark it in the source (<!-- preview:start label --> … <!-- preview:end -->) and this builds a
# dated, unlisted copy under /preview/ that keeps it, while the live page is built without it. With
# nothing marked there is no preview directory at all — and because rsync deletes what the build no
# longer produces, a preview from an earlier round disappears on the next publish.
if grep -q '<!-- preview:start' "$PRES/index.html"; then
  LABEL=$(grep -o '<!-- preview:start[^>]*-->' "$PRES/index.html" | head -1 | sed -e 's/<!-- *preview:start *//' -e 's/ *-->//')
  PREVIEW_REL="preview/$(date +%Y-%m-%d)${LABEL:+-$LABEL}"
  PREVIEW="$STAGE/$PREVIEW_REL"
  mkdir -p "$PREVIEW"
  python3 "$SITE/page-variants.py" preview "$PRES/index.html" "$PREVIEW/index.html" \
          --prefix ../../ --assets ../../presentation/
fi
fi

if [ -d "$PROJ/content/viewer-3d" ]; then
echo "== viewer"
mkdir -p "$STAGE/viewer"
cp -a "$PROJ/content/viewer-3d/." "$STAGE/viewer/"
# Both models are required, not optional: the page parses the copy inlined in its own HTML and never
# fetches the .glb served beside it, so a missing export is a half-broken viewer, not a lost download.
GLBS=""; for g in $VIEWER_GLBS; do GLBS="$GLBS $RENDERS/$g"; done; GLBS="${GLBS# }"   # one per palette on the page
if ! ls $GLBS >/dev/null 2>&1; then
  echo "!! the viewer needs out/renders/: $VIEWER_GLBS. Export them first:" >&2
  echo "     render-submit $NAME_ARG final \"glb:all glb-b:all glb-d:all\"   (or, with Blender here:" >&2
  echo "     PLANNIT_PROJECT=$PROJ blender -b -P engine/blender/build.py -- glb | glb-b | glb-d)" >&2
  exit 1
fi
# no Artifact CSP here, so serve the models as plain files too (the page itself has them inlined)
for g in $GLBS; do cp -f "$g" "$STAGE/viewer/"; done
linkfix "$STAGE/viewer/index.html"
# Fill the models into the page. content/viewer-3d/index.html keeps its <script id="model-*"> blocks EMPTY
# on purpose: they are build output (2.4 MB of base64), and while a filled copy lived in the source
# nothing regenerated it — on 2026-09-19 the live viewer was drawing a 33,298-triangle model with no
# curtains and no frosted shower screen, two exports behind the .glb files on the same URL. This step
# is what makes the page match out/renders/flat*.glb on every build, and it fails loudly if it cannot.
python3 "$SITE/inline-models.py" "$STAGE/viewer/index.html" "$STAGE/viewer/index.html" \
        $GLBS
# …and the same page with its claude.ai links left alone: that is the copy to paste into the viewer
# Artifact, the one place the models genuinely must be inlined (Artifacts block data:/blob: fetches).
python3 "$SITE/inline-models.py" "$PROJ/content/viewer-3d/index.html" "$STAGE/viewer/artifact.html" \
        $GLBS
fi

if [ -d "$PROJ/content/measure-form" ]; then
echo "== measure (read-only copy)"
mkdir -p "$STAGE/measure"
cp -a "$PROJ/content/measure-form/." "$STAGE/measure/"
linkfix "$STAGE/measure/index.html"
cat >> "$STAGE/measure/index.html" <<EOF
<!-- publish.sh: this hosted copy cannot save — the form talks to the Artifact runtime. Reference only:
     2026-09-18, the owner asked for it to be locked so nobody mistakes it for the working copy. -->
<script>
(function(){
  document.querySelectorAll('#cards input, #cards textarea').forEach(function(el){
    el.disabled = true; el.style.cursor = 'not-allowed';
  });
  document.querySelectorAll('.photo-btn').forEach(function(el){ el.remove(); });
})();
</script>
<div style="position:fixed;left:0;right:0;bottom:0;z-index:9999;background:#7a2e2e;color:#fff;
            font:500 13px/1.5 ui-monospace,Menlo,monospace;padding:9px 14px;text-align:center">
  Reference copy, read-only — for the working form,
  <a href="$(artifact_url measure/)" style="color:#fff">use the Artifact version</a>.
</div>
EOF
fi

if [ -d "$PROJ/options" ]; then
echo "== options (design alternatives: sketches + INDEX.md)"
mkdir -p "$STAGE/options"
cp -a "$PROJ/options/." "$STAGE/options/"
[ -f "$PROJ/options/INDEX.md" ] && python3 "$SITE/md2html.py" "$PROJ/options/INDEX.md" "$STAGE/options/index.html" "${NAME:-} - options"
fi
if [ "$SITE_HOME" = presentation ] && [ -d "$PRES" ]; then
cat > "$STAGE/index.html" <<EOF
<!doctype html><meta charset="utf-8"><title>${NAME:-site}</title>
<meta http-equiv="refresh" content="0; url=presentation/">
<link rel="canonical" href="presentation/">
<p><a href="presentation/">${NAME:-site}</a> &middot; <a href="playbook/">playbook</a></p>
EOF
fi
echo "== renders / drawings / cad"
cp -f "$FINAL"/*.jpg "$STAGE/renders/" 2>/dev/null || true
for f in "$RENDERS"/*.png "$RENDERS"/*.svg; do
  [ -f "$f" ] && cp -f "$f" "$STAGE/drawings/"
done
for n in $SHEETS_ASBUILT; do for f in "$SCANOUT/$n".{dxf,pdf,png,svg}; do   # sheet A.1
  [ -f "$f" ] && cp -f "$f" "$STAGE/cad/"
done; done
# the PROPOSAL sheets (A.2 proposal, A.3 works): rebuilt here from the project's model files — stdlib, seconds —
# then printed like the as-built
( cd "$RENDERS" && PLANNIT_PROJECT="$PROJ" python3 "$HERE/engine/proposal_sheet.py" >/dev/null \
  && for n in $SHEETS_PROPOSAL; do
       python3 "$HERE/engine/print_pdf.py" $n.svg $n.pdf && pdftoppm -png -r 110 -singlefile $n.pdf $n || exit 1
     done ) || echo "!! proposal sheets failed"
# their CAD, same frame as A.1 so they overlay
for n in $SHEETS_PROPOSAL; do for f in "$RENDERS/$n".{dxf,pdf,png,svg}; do
  [ -f "$f" ] && cp -f "$f" "$STAGE/cad/"
done
done

echo "== drafts (tmp/ — throwaway previews, deleted by the next publish)"
# Drafts live in tmp/ as dated folders, each with its own index.html. They are staged under /drafts/
# so the owner can look at a proposal in a browser instead of hunting through the repo — and because
# the push runs with --delete, they vanish automatically as soon as tmp/ no longer holds them.
if [ -d "$PROJ/tmp" ]; then
  mkdir -p "$STAGE/drafts"
  for d in "$PROJ"/tmp/*/; do
    [ -d "$d" ] || continue
    cp -a "$d" "$STAGE/drafts/"
    echo "   /drafts/$(basename "$d")/"
  done
fi

echo "== built $(du -sh "$STAGE" | cut -f1) in $STAGE"
[ "$LOCAL" = 1 ] && { echo "(--local: not pushing)"; exit 0; }

# ------------------------------------------------------------------ push
RSYNC=(rsync -rlt --delete --human-readable)
[ "$DRY" = 1 ] && RSYNC+=(--dry-run --itemize-changes)
"${RSYNC[@]}" "$STAGE/" "$HOST:$DOCROOT/"
[ "$DRY" = 1 ] && { echo "(--dry-run: nothing sent)"; exit 0; }

echo
echo "published:"
if [ "$SITE_HOME" = presentation ]; then
echo "  $SITE_URL/                -> presentation/ (the site's home page)"
echo "  $SITE_URL/playbook/       playbook"
else
echo "  $SITE_URL/                playbook"
fi
echo "  $SITE_URL/presentation/   renders page"
[ -d "$STAGE/options" ] && echo "  $SITE_URL/options/        design alternatives (sketches)"
[ -n "$PREVIEW_REL" ] && echo "  $SITE_URL/$PREVIEW_REL/   preview: not live on the presentation page yet"
echo "  $SITE_URL/viewer/         3D viewer"
echo "  $SITE_URL/viewer/artifact.html   the filled page to paste into the Artifact"
echo "  $SITE_URL/renders/  /drawings/  /cad/"
[ -d "$STAGE/drafts" ] && echo "  $SITE_URL/drafts/   drafts of work in progress (throwaway)"
