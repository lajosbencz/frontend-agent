import { defineConfig } from 'tsup'

export default defineConfig({
  entry: {
    index: 'src/index.ts',
    core: 'src/core.ts',
    wllama: 'src/wllama.ts',
    rag: 'src/rag/index.ts',
    reference: 'src/reference/index.ts',
  },
  format: ['esm'],
  dts: true,
  clean: true,
  sourcemap: true,
  treeshake: true,
  external: ['@wllama/wllama', 'minisearch', 'stemmer'],
})
