#!/usr/bin/env bash
# Run the experiment on the Runpod pod that serves the model (vLLM on localhost:8000).
#
#   bash scripts/pod_run.sh setup          # once after cloning: venv, deps, stub dry run
#   bash scripts/pod_run.sh pilot          # first arm-4 game of the real run, to measure time and tokens
#   bash scripts/pod_run.sh full           # all 6 arms x 10 games in tmux session "tattletale" (resumes)
#   bash scripts/pod_run.sh status         # games finished per arm, elapsed time, tokens
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f /etc/rp_environment ] && source /etc/rp_environment

VENV=/workspace/gamevenv
OUT="${OUT:-results/run1}"
export LLM_BASE_URL="${LLM_BASE_URL:-http://localhost:8000/v1}"
export LLM_API_KEY="${LLM_API_KEY:-${VLLM_API_KEY:?VLLM_API_KEY is not set}}"
export LLM_MODEL="${LLM_MODEL:-Qwen/Qwen3.8-27B}"
export LLM_REASONING_EFFORT="${LLM_REASONING_EFFORT:-low}"

case "${1:-}" in
  setup)
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q -r requirements.txt
    "$VENV/bin/python" -m tests.test_stub | tail -1
    ;;
  pilot)
    time "$VENV/bin/python" -m tattletale.run --arms 4 --games 1 --out "$OUT"
    ;;
  full)
    mkdir -p "$OUT"
    tmux new-session -d -s tattletale \
      "$VENV/bin/python -m tattletale.run --arms 1 2 3 4 5 6 --games 10 --out $OUT 2>&1 | tee -a $OUT/run.log; \
       $VENV/bin/python -m tattletale.summarize $OUT 2>&1 | tee -a $OUT/run.log"
    echo "started tmux session 'tattletale' (attach: tmux attach -t tattletale); log: $OUT/run.log"
    ;;
  status)
    cat "$OUT/progress.json" 2>/dev/null || echo "no games finished yet"
    ;;
  *)
    echo "usage: $0 setup | pilot | full | status"; exit 1 ;;
esac
