#!/bin/bash
# render-watch — runs on debof. Polls the job queue on debnuc and renders new jobs on the GPU.
#
# Queue on debnuc (~/render-queue):
#   incoming/<job>/   submitted jobs: a Blender script + job.conf (+ any assets)
#   running/<job>/    claimed by this watcher (moved atomically); while it renders, renders/ and render.log are
#                     copied back here every RENDER_SHIP seconds (default 30), so finished images show up as they land
#   done/<job>/       finished: job files + renders/ + render.log + STATUS
#   failed/<job>/     same layout, STATUS says why
#
# job.conf (bash, sourced):
#   SCENE=scene.py                                     # Blender script, run as: blender -b -P SCENE -- MODE CAMS PCT SPP
#   PRESET=final                                       # draft | final | max   (or set PCT= and SPP= directly)
#   PASSES="interior:all cutaway:all plan:all"         # MODE:CAMS pairs, CAMS = all or comma list
#
# Runs as a systemd --user service (render-watch.service). Logs: journalctl --user -u render-watch -f
set -uo pipefail

# farm.conf from the repo, copied here by install-debof.sh; the environment still overrides it
[ -f "$HOME/.config/render-watch.conf" ] && . "$HOME/.config/render-watch.conf"
REMOTE="${RENDER_REMOTE:-nuc}"                 # ssh alias for debnuc
QUEUE="${RENDER_QUEUE:-render-queue}"          # relative to the remote home
POLL="${RENDER_POLL:-20}"                      # seconds between checks
SHIP="${RENDER_SHIP:-30}"                      # seconds between progress copies of a running job (0 = off)
WORK="${RENDER_WORK:-$HOME/.cache/render-watch}"
BVER=4.5.14; BDIR="$HOME/.cache/blender/blender-$BVER-linux-x64"; B="$BDIR/blender"

SSHO=(-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=30
      -o ControlMaster=auto -o "ControlPath=$HOME/.ssh/cm-render-%r@%h:%p" -o ControlPersist=10m)
rsh(){ ssh "${SSHO[@]}" "$REMOTE" "$@"; }
say(){ echo "[$(date '+%F %T')] $*"; }

ensure_blender(){
  [ -x "$B" ] && return 0
  say "downloading Blender $BVER"
  mkdir -p "$HOME/.cache/blender"
  curl -fsSL "https://download.blender.org/release/Blender4.5/blender-$BVER-linux-x64.tar.xz" | tar xJ -C "$HOME/.cache/blender"
}

pick_device(){
  if command -v nvidia-smi >/dev/null && nvidia-smi -L >/dev/null 2>&1; then echo OPTIX; else echo CPU; fi
}

# render one pass; falls back OptiX -> CUDA -> CPU if a device renders nothing. Returns 0 if anything rendered.
render_pass(){ # jobdir scene mode cams pct spp log
  local jd="$1" scene="$2" mode="$3" cams="$4" pct="$5" spp="$6" log="$7" dev n0 n1
  for dev in $(pick_device) CUDA CPU; do
    n0=$(grep -c '^RENDERED' "$log" 2>/dev/null || true)
    ( cd "$jd" && RENDER_DEVICE=$dev RENDER_OUT="$jd/renders" \
        "$B" -b -P "$scene" -- "$mode" "$cams" "$pct" "$spp" ) 2>&1 \
      | grep --line-buffered -E '^(RENDERED|GPU:)|Error|Traceback|no (OPTIX|CUDA)' | tee -a "$log"
    n1=$(grep -c '^RENDERED' "$log" 2>/dev/null || true)
    [ "$n1" -gt "$n0" ] && return 0
    # a Python error in the scene script fails the same way on every device — don't retry
    if tail -n 20 "$log" | grep -q Traceback && ! tail -n 20 "$log" | grep -qiE 'optix|cuda|device|gpu'; then
      echo "!! $mode: scene script error — not retrying on other devices" | tee -a "$log"; return 1
    fi
    [ "$dev" = CPU ] && break
    echo "!! $mode on $dev rendered nothing — trying next device" | tee -a "$log"
  done
  return 1
}

run_job(){ # job name
  local job="$1" jd="$WORK/$1" log status=ok t0=$SECONDS
  rm -rf "$jd"; mkdir -p "$jd"
  if ! rsync -a -e "ssh ${SSHO[*]}" "$REMOTE:$QUEUE/running/$job/" "$jd/"; then
    say "$job: fetch failed"; return 1
  fi
  log="$jd/render.log"; : > "$log"; mkdir -p "$jd/renders"
  echo "job $job  started $(date '+%F %T') on $(hostname)" >> "$log"

  local SCENE=scene.py PRESET=final PASSES="interior:all" PCT="" SPP=""
  if [ -f "$jd/job.conf" ]; then source "$jd/job.conf"; fi
  case "$PRESET" in
    draft) : "${PCT:=80}"  "${SPP:=64}" ;;
    final) : "${PCT:=120}" "${SPP:=256}" ;;
    max)   : "${PCT:=160}" "${SPP:=512}" ;;
  esac
  : "${PCT:=100}" "${SPP:=128}"
  echo "scene=$SCENE preset=$PRESET pct=$PCT spp=$SPP passes=[$PASSES]" >> "$log"
  nvidia-smi --query-gpu=name,driver_version --format=csv,noheader >> "$log" 2>/dev/null || true

  if [ ! -f "$jd/$SCENE" ]; then
    echo "!! $SCENE not found in job" >> "$log"; status="failed: no $SCENE"
  elif ! ensure_blender >> "$log" 2>&1; then
    status="failed: blender download"
  else
    # progress copies: every finished image (and the log) goes back to running/<job>/ while the job runs. Stopped
    # by a flag and WAITED for before the job is moved to done/ — an rsync still in flight after the mv would
    # recreate running/<job>/, and the next watcher start would queue that leftover again.
    local shipper=""
    if [ "$SHIP" -gt 0 ] 2>/dev/null; then
      rm -f "$jd/.ship-stop"
      ( while [ ! -f "$jd/.ship-stop" ]; do
          rsync -a --exclude '*.tmp' -e "ssh ${SSHO[*]}" "$jd/renders" "$jd/render.log" "$REMOTE:$QUEUE/running/$job/" >/dev/null 2>&1
          for _ in $(seq "$SHIP"); do [ -f "$jd/.ship-stop" ] && break; sleep 1; done
        done ) &
      shipper=$!
    fi
    local p
    for p in $PASSES; do
      say "$job: ${p%%:*} ${p#*:}"
      render_pass "$jd" "$SCENE" "${p%%:*}" "${p#*:}" "$PCT" "$SPP" "$log" || status="failed: pass $p"
    done
    if [ -n "$shipper" ]; then touch "$jd/.ship-stop"; wait "$shipper" 2>/dev/null; rm -f "$jd/.ship-stop"; fi
  fi
  echo "finished $(date '+%F %T') in $(( SECONDS - t0 )) s — $status" >> "$log"
  echo "$status" > "$jd/STATUS"

  local dest=done; [ "$status" = ok ] || dest=failed
  if rsync -a -e "ssh ${SSHO[*]}" "$jd/renders" "$jd/render.log" "$jd/STATUS" "$REMOTE:$QUEUE/running/$job/" \
     && rsh "mkdir -p $QUEUE/$dest && mv $QUEUE/running/$job $QUEUE/$dest/$job"; then
    say "$job: $status ($(( SECONDS - t0 )) s) -> $dest"
    rm -rf "$jd"
  else
    say "$job: rendered but could not ship results back; kept in $jd"
  fi
}

if [ "${1:-}" = --job ]; then run_job "$2"; exit $?; fi

say "render-watch up: polling $REMOTE:~/$QUEUE every ${POLL}s, work dir $WORK"
mkdir -p "$WORK"
# Jobs left in running/ by a crash or reboot go back to incoming
rsh "mkdir -p $QUEUE/incoming $QUEUE/running $QUEUE/done $QUEUE/failed && for j in $QUEUE/running/*/; do [ -d \"\$j\" ] && mv \"\$j\" $QUEUE/incoming/; done; true" 2>/dev/null \
  || say "debnuc not reachable yet"

# keep debof awake while a job runs, if polkit lets a service inhibit sleep
INHIBIT=()
if systemd-inhibit --what=sleep:idle --who=render-watch --why=probe true 2>/dev/null; then
  INHIBIT=(systemd-inhibit --what=sleep:idle --who=render-watch)
else
  say "note: systemd-inhibit not permitted — a job will not block suspend"
fi

while true; do
  # oldest first; claim by atomic mv on debnuc
  job=$(rsh "cd $QUEUE/incoming 2>/dev/null && ls -1tr | head -1" 2>/dev/null)
  if [ -n "$job" ] && rsh "mv $QUEUE/incoming/$job $QUEUE/running/" 2>/dev/null; then
    say "$job: claimed"
    cmd=("$0" --job "$job")
    [ ${#INHIBIT[@]} -gt 0 ] && cmd=("${INHIBIT[@]}" --why="rendering $job" "${cmd[@]}")
    "${cmd[@]}" || say "$job: runner exited non-zero"
    continue
  fi
  sleep "$POLL"
done
