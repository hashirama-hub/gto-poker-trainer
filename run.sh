#!/usr/bin/env bash
# GTO Poker Trainer - Complete Launch Script
# Usage: ./run.sh [command] [args...]

set -euo pipefail

PROJECT_ROOT="/home/tuanlinh/poker"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
SOLUTIONS_DIR="$PROJECT_ROOT/solutions"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')]${NC} $*"; }
err() { echo -e "${RED}[$(date '+%H:%M:%S')]${NC} $*" >&2; }

# Check venv exists
if [[ ! -x "$VENV_PYTHON" ]]; then
    err "Virtual environment not found at $VENV_PYTHON"
    err "Run: python3 -m venv .venv && .venv/bin/pip install -e ."
    exit 1
fi

# Ensure solutions dir exists
mkdir -p "$SOLUTIONS_DIR"

cd "$PROJECT_ROOT"

# Commands
cmd_train() {
    local mode="${1:-pushfold}"
    shift || true
    log "Starting $mode quiz..."
    exec "$VENV_PYTHON" -m gto.cli "$mode" "$@"
}

cmd_info() {
    log "Querying GTO strategy..."
    exec "$VENV_PYTHON" -m gto.cli info "$@"
}

cmd_solve_pushfold() {
    log "Solving push/fold models (10/15/20bb)..."
    exec "$VENV_PYTHON" -m gto.cli solve-pushfold \
        --depths 10 15 20 \
        --iterations "${1:-60000}" \
        --save-every "${2:-10000}" \
        --report-every "${3:-5000}"
}

cmd_solve_full100() {
    local iterations="${1:-25000}"
    local save_every="${2:-10000}"
    local report_every="${3:-5000}"
    local model_path="${4:-$SOLUTIONS_DIR/full100_sb_bb_50k_checkpoint.pkl}"

    log "Continuing full 100bb solve: $iterations iterations (save every $save_every)"
    log "Model: $model_path"
    log "Speed: ~86 it/s → ~${iterations} it ≈ $((iterations / 86 / 60)) minutes"
    log "Press Ctrl+C to stop (checkpoint auto-saved)"

    exec "$VENV_PYTHON" -m gto.cli solve-full100 \
        --model "$model_path" \
        --iterations "$iterations" \
        --save-every "$save_every" \
        --report-every "$report_every"
}

cmd_solve_full100_bg() {
    local iterations="${1:-50000}"
    local save_every="${2:-10000}"
    local report_every="${3:-5000}"
    local model_path="${4:-$SOLUTIONS_DIR/full100_sb_bb_50k_checkpoint.pkl}"
    local log_file="$PROJECT_ROOT/solve_full100_$(date +%Y%m%d_%H%M%S).log"

    log "Starting background solve: $iterations iterations"
    log "Log: $log_file"
    log "Check progress: tail -f $log_file"

    nohup "$VENV_PYTHON" -u -m gto.cli solve-full100 \
        --model "$model_path" \
        --iterations "$iterations" \
        --save-every "$save_every" \
        --report-every "$report_every" \
        > "$log_file" 2>&1 &

    local pid=$!
    echo $pid > "$PROJECT_ROOT/solve_full100.pid"
    log "Started with PID: $pid"
    log "Stop with: kill $pid"
}

cmd_stop_solve() {
    local pid_file="$PROJECT_ROOT/solve_full100.pid"
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill "$pid" 2>/dev/null; then
            log "Stopped solver (PID: $pid)"
        else
            warn "Process $pid not found"
        fi
        rm -f "$pid_file"
    else
        warn "No PID file found"
    fi
}

cmd_test() {
    log "Running test suite (46 tests)..."
    exec "$VENV_PYTHON" -m pytest -q
}

cmd_status() {
    log "=== GTO Poker Trainer Status ==="
    echo
    echo "Models in $SOLUTIONS_DIR:"
    ls -lh "$SOLUTIONS_DIR"/*.pkl 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  (none)"
    echo
    echo "Full 100bb model progress:"
    if [[ -f "$SOLUTIONS_DIR/full100_sb_bb_50k_checkpoint.pkl" ]]; then
        "$VENV_PYTHON" -c "
import pickle
with open('$SOLUTIONS_DIR/full100_sb_bb_50k_checkpoint.pkl', 'rb') as f:
    data = pickle.load(f)
total_regret = sum(abs(r0).sum() + abs(r1).sum() for r0, r1, _, _ in data.values())
total_strat = sum(s0.sum() + s1.sum() for _, _, s0, s1 in data.values())
print(f'  Nodes: {len(data)}')
print(f'  Total regret mass: {total_regret:,.0f}')
print(f'  Total strategy mass: {total_strat:,.0f}')
"
    else
        echo "  Not found"
    fi
    echo
    echo "Background solver:"
    if [[ -f "$PROJECT_ROOT/solve_full100.pid" ]]; then
        pid=$(cat "$PROJECT_ROOT/solve_full100.pid")
        if kill -0 "$pid" 2>/dev/null; then
            echo "  Running (PID: $pid)"
        else
            echo "  Dead (stale PID file)"
        fi
    else
        echo "  Not running"
    fi
}

cmd_help() {
    cat <<EOF
GTO Poker Trainer - Complete Launch Script

Usage: ./run.sh <command> [args...]

TRAINING QUIZZES:
  ./run.sh train pushfold [--hands 10] [--bb 15] [--position sb|bb]
  ./run.sh train icm [--hands 8] [--iterations 60000] [--position sb|bb] [--table "12,15,8,20,10,25,9,14"]
  ./run.sh train preflop [--hands 10] [--position sb|bb]
  ./run.sh train flop [--hands 5] [--fast] [--board "0,15,33"]

LOOKUP GTO STRATEGY:
  ./run.sh info "AA AKs 72o" [--depth 15]        # push/fold model
  ./run.sh info "AA 72o"                         # full 100bb model

SOLVING / TRAINING MODELS:
  ./run.sh solve-pushfold [iterations] [save_every] [report_every]
       Default: 60000 10000 5000

  ./run.sh solve-full100 [iterations] [save_every] [report_every] [model_path]
       Default: 25000 10000 5000 solutions/full100_sb_bb_50k_checkpoint.pkl
       ~86 it/s on CPU. 300-500k iterations needed for convergence.

  ./run.sh solve-full100-bg [iterations] [save_every] [report_every] [model_path]
       Run in background, logs to timestamped file, PID saved.

  ./run.sh stop-solve
       Stop background solver (checkpoint auto-saved).

UTILITIES:
  ./run.sh test          # Run 46 tests
  ./run.sh status        # Show model status & background solver
  ./run.sh help          # This help

EXAMPLES:
  # Quick quiz
  ./run.sh train pushfold --hands 20

  # Full ICM final table quiz
  ./run.sh train icm --hands 10 --iterations 60000

  # Continue training full 100bb tree (foreground)
  ./run.sh solve-full100 50000 10000 5000

  # Continue training full 100bb tree (background)
  ./run.sh solve-full100-bg 100000 10000 5000

  # Check GTO play for specific hands
  ./run.sh info "AA KK QQ AKs AQs" --depth 15
  ./run.sh info "AA 72o A5s KQo"

  # Run tests
  ./run.sh test
EOF
}

# Main
case "${1:-help}" in
    train)     cmd_train "${@:2}" ;;
    info)      cmd_info "${@:2}" ;;
    solve-pushfold) cmd_solve_pushfold "${@:2}" ;;
    solve-full100)  cmd_solve_full100 "${@:2}" ;;
    solve-full100-bg) cmd_solve_full100_bg "${@:2}" ;;
    stop-solve) cmd_stop_solve ;;
    test)      cmd_test ;;
    status)    cmd_status ;;
    help|--help|-h) cmd_help ;;
    *) err "Unknown command: $1"; cmd_help; exit 1 ;;
esac