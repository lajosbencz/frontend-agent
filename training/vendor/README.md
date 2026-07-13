# vendored llama.cpp

Built for `llama-quantize` (K-quants) and `convert_hf_to_gguf.py`, used by `scripts/export_gguf.py`.
Not a submodule — clone at the pinned commit and build:

```bash
git clone https://github.com/ggml-org/llama.cpp vendor/llama.cpp
git -C vendor/llama.cpp checkout f36e5c348bc8795c34f9a038e58876e7a8423d4d
cmake -S vendor/llama.cpp -B vendor/llama.cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build vendor/llama.cpp/build --target llama-quantize -j
```

Pinned commit: `f36e5c348bc8795c34f9a038e58876e7a8423d4d` (has lfm2/lfm2moe conversion support).
The external training image `ghcr.io/lajosbencz/lfm-train` ships a compatible static `llama-quantize`.
