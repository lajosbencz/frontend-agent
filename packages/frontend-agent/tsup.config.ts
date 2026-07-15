import { defineConfig } from 'tsup'

export default defineConfig({
  entry: {
    index: 'src/index.ts',
    rag: 'src/rag/index.ts',
    reference: 'src/reference/index.ts',
  },
  format: ['esm'],
  dts: true,
  clean: true,
  sourcemap: true,
  treeshake: true,
  // wllama is a hard dep; minisearch/stemmer are optional peers (only the ./rag subpath imports them)
  external: ['@wllama/wllama', 'minisearch', 'stemmer'],
})
