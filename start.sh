#!/usr/bin/env bash
# ============================================================
# PiFeed4 - Production launcher
# ============================================================
# Ensures venv + deps are ready, then runs the app in a
# supervised loop:
#   - Restarts automatically on crash
#   - Force-restarts every 2 hours (guards against hangs)
#   - Ctrl-C exits the loop cleanly
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
RESTART_INTERVAL=7200   # seconds (2 hours)
PAUSE_BEFORE_RESTART=3  # seconds between crash and restart

# ---- colours for log output ----
RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[1;33m'
RST='\033[0m'

log()  { echo -e "${GRN}[PiFeed]${RST} $*"; }
warn() { echo -e "${YEL}[PiFeed]${RST} $*"; }
err()  { echo -e "${RED}[PiFeed]${RST} $*"; }

# ---- Ctrl-C handler ----
STOP=0
trap 'STOP=1; warn "Ctrl-C received, shutting down..."; kill "$APP_PID" 2>/dev/null || true' INT TERM

# ---- ensure venv + deps ----
setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi

    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"

    log "Installing / updating dependencies..."
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
}

# ---- run the app with a timeout ----
run_app() {
    log "Starting PiFeed (will force-restart after ${RESTART_INTERVAL}s)..."

    "$VENV_DIR/bin/python" main.py &
    APP_PID=$!

    # Wait in 1-second ticks so we can check both the timeout
    # and the STOP flag without blocking on a single wait.
    ELAPSED=0
    while [ $ELAPSED -lt $RESTART_INTERVAL ]; do
        # Has the process exited on its own (crash or clean exit)?
        if ! kill -0 "$APP_PID" 2>/dev/null; then
            wait "$APP_PID" 2>/dev/null || true
            return 1  # signal: process exited
        fi
        # Has the user pressed Ctrl-C?
        if [ $STOP -ne 0 ]; then
            wait "$APP_PID" 2>/dev/null || true
            return 0
        fi
        sleep 1
        ELAPSED=$((ELAPSED + 1))
    done

    # Timeout reached — kill and restart
    warn "2-hour limit reached, force-restarting..."
    kill "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
    return 1
}

# ---- main loop ----
main() {
    log "=== PiFeed4 Production Launcher ==="
    log "Press Ctrl-C to exit the loop."
    echo

    setup_venv

    while [ $STOP -eq 0 ]; do
        if run_app; then
            # Clean exit (Ctrl-C)
            break
        fi

        if [ $STOP -ne 0 ]; then
            break
        fi

        warn "Restarting in ${PAUSE_BEFORE_RESTART}s..."
        sleep "$PAUSE_BEFORE_RESTART"
    done

    log "PiFeed stopped."
}

main
