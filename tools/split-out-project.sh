#!/bin/bash
# split-out-project.sh — turn a checkout that holds the tool AND a project (projects/<name>/, the layout before
# plannit had its own repository) into the project's own repository, with plannit as a submodule.
#
#   cd <that checkout> && <plannit>/tools/split-out-project.sh <name> <plannit git URL> [<plannit ref>]
#
# In one commit: the project's files move to the root; the tool's (engine/ farm/ site/ tools/ lib/ projects/…)
# are removed and plannit is added as the submodule plannit/ at <ref> (default: its default branch);
# farm/farm.conf, if the checkout has one, is kept as ./farm.conf (your machines: install it as
# ~/.config/plannit/farm.conf; PLANNIT_DIR=<path under home> sets where plannit will be, default: here);
# ./publish.sh becomes a wrapper for plannit/site/publish.sh. History is kept.
set -euo pipefail
NAME="${1:?usage: split-out-project.sh <name> <plannit git URL> [<plannit ref>]}"; URL="${2:?plannit git URL}"; REF="${3:-}"
[ -f "projects/$NAME/project.conf" ] || { echo "!! no projects/$NAME/project.conf here — run at the checkout's root"; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "!! the working tree is not clean — commit or stash first"; git status --short; exit 1; }

# 1. keep what belongs to the project from the tool's side of the old layout
[ -f farm/farm.conf ] && { cp farm/farm.conf farm.conf.keep; echo '
# where plannit is on this box, relative to home (for install-debof.sh): the submodule in this checkout
: "${PLANNIT_DIR:='"${PLANNIT_DIR:-$(realpath --relative-to="$HOME" "$PWD" 2>/dev/null || echo "$PWD")/plannit}"'}"' >> farm.conf.keep; }

# 2. the tool's files go (they come back as the submodule); tool-level files at the root that the project replaces
for p in engine farm site tools lib README.md .gitignore publish.sh; do
  [ -e "$p" ] && git rm -rq "$p"
done
for p in projects/*; do [ "$p" = "projects/$NAME" ] || git rm -rq "$p"; done

# 3. the project to the root
( shopt -s dotglob; for f in "projects/$NAME"/*; do git mv "$f" .; done )
rmdir "projects/$NAME" projects 2>/dev/null || true
[ -f farm.conf.keep ] && mv farm.conf.keep farm.conf && git add farm.conf

# 4. paths that pointed across the old layout
[ -f scan/build.sh ] && sed -i 's#^ENGINE="\$HERE/\.\./\.\./\.\./engine"$#for c in "$HERE/../plannit" "$HERE/../../.."; do [ -f "$c/engine/sheet.py" ] \&\& ENGINE="$(cd "$c/engine" \&\& pwd)" \&\& break; done#' scan/build.sh
cat > publish.sh <<'EOF'
#!/bin/bash
# publish.sh — this project's site: plannit/site/publish.sh for this folder (--collect, --dry-run, --local).
HERE="$(cd "$(dirname "$0")" && pwd)"
exec "$HERE/plannit/site/publish.sh" "$HERE" "$@"
EOF
chmod +x publish.sh
cat > .gitignore <<'EOF'
# generated, never committed: the site's staging tree, render-farm jobs, drafts, interpreter caches
build-site/
build-job/
tmp/
__pycache__/
*.pyc
EOF
git add publish.sh .gitignore scan/build.sh 2>/dev/null || git add publish.sh .gitignore

# 5. the tool, as a submodule
git submodule add -q "$URL" plannit
[ -n "$REF" ] && git -C plannit checkout -q "$REF" && git add plannit
git commit -qm "Split out: this repository is the project $NAME; plannit is the submodule plannit/

The project's files moved from projects/$NAME/ to the root; the tool's files were removed and plannit
is now a submodule$( [ -n "$REF" ] && echo " (at $REF)" ). farm/farm.conf kept as ./farm.conf. ./publish.sh calls
plannit/site/publish.sh for this folder."
echo "done: $(git log --oneline -1)"
echo "next: git submodule update --init   (in other clones)   ·   farm.conf -> ~/.config/plannit/farm.conf"
