#!/bin/bash
# Pod bootstrap: install vLLM into /workspace, cache the model weights there, serve on :8000.
# Everything lives on the persistent /workspace disk, so a stop/start skips straight to serving.
set -uo pipefail
export HF_HOME=/workspace/hf HF_HUB_ENABLE_HF_TRANSFER=1
echo "[bootstrap] $(date -u +%FT%TZ) start"
if [ ! -x /workspace/venv/bin/vllm ]; then
  python3 -m venv /workspace/venv || { echo "[bootstrap] venv FAILED"; exit 1; }
  /workspace/venv/bin/pip install -q -U pip uv
  /workspace/venv/bin/uv pip install --python /workspace/venv/bin/python vllm hf_transfer \
    || { echo "[bootstrap] vllm install FAILED"; exit 1; }
fi
echo "[bootstrap] vllm $(/workspace/venv/bin/python -c 'import vllm; print(vllm.__version__)')"
/workspace/venv/bin/python -c "from huggingface_hub import snapshot_download as s; print('[bootstrap] weights at', s('$MODEL_ID'))" \
  || { echo "[bootstrap] weight download FAILED"; exit 1; }
echo "[bootstrap] $(date -u +%FT%TZ) weights ready, starting vLLM"
# DeepGEMM JIT-compiles its FP8 kernels and fails on this image (needs nvcc >= 12.9; the image has 12.8,
# and the CUDA 13 nvcc in the venv can't find its headers). vLLM's precompiled FP8 kernels work.
export VLLM_USE_DEEP_GEMM=0
# FlashInfer's top-k/top-p sampler is also JIT-compiled at warm-up; PyTorch sampling is used instead.
export VLLM_USE_FLASHINFER_SAMPLER=0
export PATH="/workspace/venv/bin:$PATH"                 # ninja, for any remaining JIT builds
exec /workspace/venv/bin/vllm serve "$MODEL_ID" --served-model-name "$SERVED_NAME" \
  --host 0.0.0.0 --port 8000 --api-key "$VLLM_API_KEY" \
  --max-model-len 32768 --max-num-seqs 128 --gpu-memory-utilization 0.92 \
  --enable-prefix-caching --reasoning-parser qwen3 \
  --limit-mm-per-prompt '{"image":0,"video":0}'
