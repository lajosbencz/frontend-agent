"""Run a GGUF through the vendored llama-server for evaluation/benchmarking.

Why llama-server (not transformers): we must score the ACTUAL quantized weights the browser ships,
and reproduce the browser's runtime (llama.cpp + the GGUF's embedded chat template). We drive the
raw /completion endpoint with a prompt string rendered by the SAME training tokenizer
(apply_chat_template), so the model sees exactly the training/inference distribution — no jinja
template drift between HF and llama.cpp to muddy the comparison.

Backend is selectable via n_gpu_layers: 0 = pure CPU (matches the WASM browser target), 99 = offload
all layers to the GPU (Vulkan build) — eval scores are backend-independent (greedy quant math) so we
run the sweep on GPU for speed.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SERVER = REPO / "vendor" / "llama.cpp" / "build" / "bin" / "llama-server"


def model_quant_label(name: str) -> str:
    """A matrix key from a GGUF filename: '{params}-{version}-{quant}' (e.g. '230m-v6-Q8_0') so
    results across param sizes, versions, AND quants never collide. Missing parts are dropped;
    falls back to the stem."""
    base = Path(name).name
    params = re.search(r"(\d+)\s*m\b", base, re.I)
    ver = re.search(r"\b(v\d+(?:\.\d+)*)", base, re.I)  # v6 or dotted semver v0.7.0
    quant = re.search(r"(Q\d[A-Za-z0-9_]*)", base)
    parts = []
    if params:
        parts.append(f"{params.group(1)}m")
    if ver:
        parts.append(ver.group(1).lower())
    if quant:
        parts.append(quant.group(1))
    return "-".join(parts) if parts else Path(base).stem


class LlamaServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8891):
        self.base = f"http://{host}:{port}"

    def _post(self, path: str, payload: dict, timeout: float = 120.0) -> dict:
        req = urllib.request.Request(
            self.base + path, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())

    def _health_ok(self) -> bool:
        try:
            with urllib.request.urlopen(self.base + "/health", timeout=2) as r:
                return json.loads(r.read().decode()).get("status") == "ok"
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            return False

    def complete(self, prompt: str, n_predict: int = 220, temperature: float = 0.0,
                 stop: list[str] | None = None, grammar: str | None = None) -> str:
        """Greedy raw completion. Returns generated text (special tokens preserved for tool parsing).
        `grammar` (GBNF) constrains decoding to valid tool-call structure when provided."""
        payload = {
            "prompt": prompt, "n_predict": n_predict, "temperature": temperature,
            "cache_prompt": True, "stop": stop or [], "top_k": 1,
        }
        if grammar:
            payload["grammar"] = grammar
        try:
            return self._post("/completion", payload).get("content", "")
        except urllib.error.HTTPError as e:
            if e.code == 400:  # prompt exceeds n_ctx — score as empty, don't abort the sweep
                return ""
            raise


@contextmanager
def serve(model_path: str | Path, n_ctx: int = 8192, port: int = 8891, threads: int | None = None,
          n_gpu_layers: int = 99, health_timeout: float = 120.0, parallel: int = 1):
    """Start llama-server on a GGUF, yield a LlamaServer, tear down on exit.

    n_gpu_layers: 99 offloads all layers to the GPU (Vulkan); 0 stays on CPU.
    parallel: number of concurrent decode slots (--parallel). llama-server SPLITS the -c context
    across slots, so n_ctx is auto-scaled to keep >=4096 tokens per slot for multi-turn scenarios.
    Raises TimeoutError if the server isn't healthy within health_timeout (a shorter value lets a
    caller probe the GPU path and fall back to CPU without a long hang)."""
    if not SERVER.exists():
        raise FileNotFoundError(f"llama-server not built at {SERVER}")
    if parallel > 1:
        n_ctx = max(n_ctx, parallel * 4096)  # keep per-slot ctx adequate for multi-turn prompts
    cmd = [str(SERVER), "-m", str(model_path), "--host", "127.0.0.1", "--port", str(port),
           "-c", str(n_ctx), "-ngl", str(n_gpu_layers), "--no-webui", "--parallel", str(parallel)]
    if threads:
        cmd += ["-t", str(threads)]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    client = LlamaServer(port=port)
    try:
        deadline = time.monotonic() + health_timeout
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"llama-server exited early (code {proc.returncode})")
            if client._health_ok():
                break
            time.sleep(0.5)
        else:
            raise TimeoutError(f"llama-server not healthy within {health_timeout}s")
        yield client
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def pick_backend(model_path: str | Path, prefer_gpu: bool = True, probe_timeout: float = 45.0) -> int:
    """Return a working n_gpu_layers: try GPU (99) with a short health probe, fall back to CPU (0).
    Prevents a Vulkan hang from stalling an autonomous run."""
    if not prefer_gpu:
        return 0
    try:
        with serve(model_path, n_gpu_layers=99, health_timeout=probe_timeout) as srv:
            srv.complete("hi", n_predict=1)
        return 99
    except (TimeoutError, RuntimeError, OSError) as e:
        print(f"[gguf_runtime] GPU probe failed ({e}); falling back to CPU (-ngl 0)")
        return 0
