// Single-thread f32 GEMM microbenchmark kernel (source of truth for the hardware probe).
// Compiled to WASM by AssemblyScript via `npm run build:wasm` (see scripts/build-wasm.mjs), which
// embeds the result into src/engine/mm.generated.ts. Do not hand-edit the generated file.

const CAP: i32 = 64 * 64;
const A = new StaticArray<f32>(CAP);
const B = new StaticArray<f32>(CAP);
const C = new StaticArray<f32>(CAP);

export function mm(n: i32, iters: i32): f32 {
  const cells = n * n;
  for (let i = 0; i < cells; i++) {
    unchecked((A[i] = <f32>(i % 7) * 0.1));
    unchecked((B[i] = <f32>(i % 5) * 0.2));
  }
  let s: f32 = 0;
  for (let t = 0; t < iters; t++) {
    for (let i = 0; i < n; i++) {
      const ai = i * n;
      for (let j = 0; j < n; j++) {
        let acc: f32 = 0;
        for (let k = 0; k < n; k++) {
          acc += unchecked(A[ai + k]) * unchecked(B[k * n + j]);
        }
        unchecked((C[ai + j] = acc));
      }
    }
    const d = t % n;
    s += unchecked(C[d * n + d]);
  }
  return s;
}
