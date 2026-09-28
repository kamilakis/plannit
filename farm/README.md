# farm/: one box queues, a GPU box renders

The render box cannot be reached from the queueing box, so **the render box polls a job queue on the
queueing box**: a job is claimed by moving it there, rendered on the GPU, and the results are shipped back
into the same queue. In the scripts the two are called *debnuc* (queues; ssh alias `nuc` from the render
box) and *debof* (renders) — the names of the first farm this ran on.

    ~/render-queue/                 on the queueing box
      incoming/<job>/   ← render-submit puts jobs here (copied in via .staging, then mv, so jobs are never half-written)
      running/<job>/    ← claimed by the render box
      done/<job>/       ← job files + renders/ + render.log + STATUS ("ok")
      failed/<job>/     ← same, STATUS says why

| file | runs on | |
|---|---|---|
| `farm.conf.example` | — | your machines: render box IP/MAC, broadcast address, ssh alias, queue path, where plannit is. Copy to `~/.config/plannit/farm.conf` (or set `$PLANNIT_FARM_CONF`) |
| `pack.sh` | queueing box | engine + one project → `<project>/build-job/<name>/`, a job directory with a `scene.py` entry |
| `render-submit` | queueing box | queues a job (a project folder, a directory or a script), wakes the render box |
| `render-watch.sh` · `render-watch.service` | render box | polls the queue over ssh, renders, ships results back |
| `install-debof.sh` | render box | installs the two above plus the farm config as `~/.config/render-watch.conf` |
| `render-debof.sh` · `render-local-cpu.sh` | a job dir | by-hand renders without the queue |

## Submit (on the queueing box)

    render-submit ~/work/myflat                           # packs the project, final, all passes
    render-submit ~/work/myflat draft "interior:tv,study"
    render-submit --status
    render-submit --wake

A project is packed first (`farm/pack.sh`); a plain directory is copied whole, minus
renders*/web/scene-history/logs. The render box gets a wake-on-LAN packet if it doesn't answer ping.
Put `render-submit` on your PATH as a symlink to `<plannit>/farm/render-submit`.

## Job format

`job.conf` (sourced by bash) next to the Blender script:

    SCENE=scene.py
    PRESET=final                          # draft 80%/64spp · final 120%/256spp · max 160%/512spp (or PCT=, SPP=)
    PASSES="interior:all cutaway:all plan:all"

Each pass runs `blender -b -P $SCENE -- MODE CAMS PCT SPP` with env `RENDER_DEVICE` (OPTIX,
falling back to CUDA and then CPU if a device renders nothing) and `RENDER_OUT=<job>/renders`.
The script must print `RENDERED <name>` per image, which is how success is counted.
Blender 4.5.14 is fetched to the render box's `~/.cache/blender` on first use.

## Install on the render box

With `~/.config/plannit/farm.conf` in place on the queueing box (its `PLANNIT_DIR` says where plannit is),
on the render box: `ssh nuc 'cat <plannit>/farm/install-debof.sh' > /tmp/t && bash /tmp/t`.
It installs `~/.local/bin/render-watch`, the `render-watch.service` user unit and `~/.config/render-watch.conf`,
enables linger (sudo), and ships its log to the queueing box's `~/from-debof/render-watch-install.log`.

On the render box: `journalctl --user -u render-watch -f` · `systemctl --user restart render-watch`.
Update the watcher: rerun the installer. A crash or reboot moves `running/` jobs back to `incoming/` at startup.

⚠ Jobs are code: `job.conf` and the scene script run on the render box. Only the queueing box can queue
jobs (the render box trusts it).
