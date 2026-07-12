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
  // optional peer deps stay external - pulled only when the consumer uses that subpath
  external: ['@wllama/wllama', 'minisearch', 'stemmer'],
})
