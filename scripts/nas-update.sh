#!/bin/sh
# Probe-2-Plot: automatic update on the Synology NAS (DSM Task Scheduler, user root).
#
#   sh /volume1/docker/probe-2-plot/scripts/nas-update.sh     nightly: update if there is a new version
#
# The repository is public, so no key or password is needed: the NAS only reads from GitHub.
#
# What a run does:
#   1. asks GitHub for the newest commit on the "stable" branch
#   2. nothing new: stops ("up to date")
#   3. new version: copies the project library to data/pre-update/ (keeps the last 5), checks out the new
#      files, rebuilds the image and restarts the container
#   4. checks the new version really runs: web server answers, the container reports the new version and
#      can read the library; if not, goes back to the previous version (its image is kept) and remembers
#      the bad commit, so it isn't retried every night
# The data folder is never touched by git (it is in .gitignore). Each run writes to update.log.
# Exit code 1 = failed (DSM can e-mail you: task settings -> "only when the script terminates abnormally").

APP=$(cd "$(dirname "$0")/.." && pwd)
BRANCH=${BRANCH:-stable}
PORT=${PORT:-8522}
REPO=${REPO:-https://github.com/IamRepository/BBQ_temp_dashboard.git}
LOG="$APP/update.log"
WAIT=${WAIT:-30}                     # health checks, 10 s apart

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }
git_() { git -c safe.directory="$APP" -C "$APP" "$@"; }   # files belong to the DSM user, the task runs as root
export GIT_TERMINAL_PROMPT=0         # never wait for a password
export BUILDX_GIT_INFO=false         # the builder's own git call can't read the folder as root: harmless warning

compose() {
    if docker compose version >/dev/null 2>&1; then docker compose -p probe-2-plot "$@"
    else docker-compose -p probe-2-plot "$@"; fi
}

healthy() {
    i=0
    while [ "$i" -lt "$WAIT" ]; do
        curl -fs "http://localhost:$PORT/_stcore/health" >/dev/null 2>&1 && return 0
        i=$((i + 1)); sleep 10
    done
    return 1
}

deploy() {                           # check out commit $1, rebuild, restart
    # quiet build; if it fails (or an old docker-compose doesn't know --quiet), build again with the
    # full output, so the log shows why
    git_ reset -q --hard "$1" && (cd "$APP" && { compose build --quiet || compose build; } && compose up -d) >>"$LOG" 2>&1
}

repo_version() { sed -n "s/^VERSION *= *'\([^']*\)'.*/\1/p" "$APP/version.py" | head -1; }

running_ok() {                       # the new container runs the checked-out version and reads the library
    healthy || return 1
    got=$(docker exec probe-2-plot python -c "import py_compile; py_compile.compile('app.py', cfile='/tmp/app.pyc', doraise=True); \
import pandas, plotly, streamlit; import project_store; from version import VERSION; \
project_store.Library().projects(); print(VERSION)" 2>>"$LOG")
    [ "$got" = "$(repo_version)" ] || { log "check: container reports '${got}', expected $(repo_version)"; return 1; }
}

image_tag() { git_ show "$1:compose.yaml" 2>/dev/null | sed -n 's/^ *image: *probe-2-plot:\([^ ]*\).*/\1/p'; }

cd "$APP" || exit 1

# first run: the folder came from a ZIP, make it a git checkout (data/ stays: it's ignored)
if [ ! -d "$APP/.git" ]; then
    git_ init -q && git_ remote add origin "$REPO" || { log "FAILED: git init"; exit 1; }
    log "first run: folder is now a git checkout of $BRANCH"
fi

git_ fetch -q origin "$BRANCH" || { log "FAILED: can't reach GitHub (network?) or no branch $BRANCH"; exit 1; }
NEW=$(git_ rev-parse "origin/$BRANCH")
OLD=$(git_ rev-parse -q --verify HEAD 2>/dev/null || echo "")
if [ "$OLD" = "$NEW" ]; then
    log "up to date ($(git_ log -1 --format=%h:%s HEAD | cut -c1-70))"
    exit 0
fi
FAILED_FILE="$APP/update.failed"
if [ -f "$FAILED_FILE" ] && [ "$(cat "$FAILED_FILE")" = "$NEW" ]; then
    log "FAILED earlier: $(git_ log -1 --format=%h "$NEW") didn't start, not trying again until stable changes"
    log "  (if it was a passing problem, e.g. no internet during the build: delete update.failed, run again)"
    exit 1
fi

# copy of the library before anything changes (the .p2p files are written atomically, a plain copy is consistent)
STAMP=$(date +%Y%m%d-%H%M)
mkdir -p "$APP/data/pre-update"
if [ -d "$APP/data/projects" ]; then
    cp -a "$APP/data/projects" "$APP/data/pre-update/projects-$STAMP" \
        || { log "FAILED: library copy, nothing changed"; exit 1; }
fi
ls -1dt "$APP"/data/pre-update/projects-* 2>/dev/null | tail -n +6 | while read -r f; do rm -rf "$f"; done
# local edits to compose.yaml would be replaced: keep a copy
[ -f "$APP/compose.yaml" ] && cp "$APP/compose.yaml" "$APP/data/pre-update/compose-$STAMP.yaml"
ls -1t "$APP"/data/pre-update/compose-*.yaml 2>/dev/null | tail -n +6 | while read -r f; do rm -f "$f"; done

log "updating ${OLD:-zip install} -> $(git_ log -1 --format=%h:%s "$NEW" | cut -c1-70)"
if deploy "$NEW" && running_ok; then
    rm -f "$FAILED_FILE"
    log "OK: $(repo_version) is running"
    # old images (tag = version) take space; keep this one and the previous one (for a quick way back)
    TAG=$(image_tag "$NEW"); PREV=$( [ -n "$OLD" ] && image_tag "$OLD" )
    docker images probe-2-plot --format '{{.Tag}}' | grep -vx "$TAG" | grep -vx "${PREV:-$TAG}" |
        while read -r t; do docker rmi "probe-2-plot:$t" >/dev/null 2>&1; done
    exit 0
fi

echo "$NEW" > "$FAILED_FILE"
log "FAILED: new version didn't start properly; going back (library copy: data/pre-update/projects-$STAMP)"
if [ -n "$OLD" ]; then
    if deploy "$OLD" && running_ok; then
        log "back on $(git_ log -1 --format=%h "$OLD") ($(repo_version))"
    else
        log "FAILED: previous version didn't start either: see docs/NAS.md (Updating)"
    fi
else
    # first run (folder came from the ZIP): no previous commit to go back to. The folder now holds the
    # stable files; forget the checkout so the next run treats it as a first run again
    git_ update-ref -d HEAD 2>/dev/null
    log "FAILED on the first run: see the lines above. To get the app back: upload the last ZIP that worked"
    log "  and Build in Container Manager; delete update.failed to try again"
fi
exit 1
