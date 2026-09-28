# lib/common.sh — sourced by plannit's shell tools.
PLANNIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# A project: a path to a folder with project.conf (a real project, usually its own repo with plannit as a
# submodule), or a name under plannit's projects/ (the fixture). Prints the absolute path.
project_dir() {
  local p="${1:?project}"
  if [ -f "$p/project.conf" ]; then (cd "$p" && pwd)
  elif [ -f "$PLANNIT_ROOT/projects/$p/project.conf" ]; then echo "$PLANNIT_ROOT/projects/$p"
  else echo "!! $p is not a project (a folder with a project.conf)" >&2; return 1; fi
}

# The render farm's machines are not part of the tool: $PLANNIT_FARM_CONF, or ~/.config/plannit/farm.conf.
# farm_conf        load it or fail;  farm_conf -q   load it if it exists
farm_conf() {
  local f="${PLANNIT_FARM_CONF:-$HOME/.config/plannit/farm.conf}"
  if [ -f "$f" ]; then . "$f"; return 0; fi
  [ "${1:-}" = -q ] && return 0
  echo "!! no farm config at $f — copy $PLANNIT_ROOT/farm/farm.conf.example there and fill it in" >&2; return 1
}
