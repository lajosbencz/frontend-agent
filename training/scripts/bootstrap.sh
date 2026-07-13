#!/usr/bin/env bash
# Install the repo deps NOT baked into the lfm-train CUDA image (it ships only the heavy ML stack).
# Run once at container start, before the pipeline. Idempotent; all deps are pure-python (seconds).
set -euo pipefail
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"   # writable under rootless podman --userns=keep-id
uv pip install -q -r "$(dirname "$0")/../requirements-image.txt"
echo "[bootstrap] repo deps installed into $(python -c 'import sys; print(sys.prefix)')"
