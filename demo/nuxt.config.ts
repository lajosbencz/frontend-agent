import tailwindcss from '@tailwindcss/vite'

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: ['@nuxt/content', '@pinia/nuxt'],
  devtools: { enabled: true },
  compatibilityDate: '2024-04-03',
  css: ['~/assets/css/tailwind.css'],

  // Static hosting on GitHub Pages: `npm run generate` prerenders every route to static HTML
  // (no server runtime). Set NUXT_APP_BASE_URL=/<repo>/ for project pages (user.github.io/<repo>).
  ssr: true,
  nitro: {
    preset: 'github_pages', // emits .nojekyll + 404.html and honors app.baseURL
    prerender: { crawlLinks: true, routes: ['/'] },
  },
  app: {
    baseURL: process.env.NUXT_APP_BASE_URL || '/',
    head: {
      // Cross-origin-isolation shim: on a static host (GitHub Pages) this SW re-adds COOP/COEP so
      // SharedArrayBuffer is available and wllama runs multi-threaded. Loaded first (critical) and
      // base-URL aware; on a header-capable host it's a no-op (already isolated).
      script: [
        {
          src: `${process.env.NUXT_APP_BASE_URL || '/'}coi-serviceworker.js`,
          tagPriority: 'critical',
        },
      ],
    },
  },

  runtimeConfig: {
    public: {
      // Empty => client-side RAG over the bundled static index (the zero-infra default).
      // Set NUXT_PUBLIC_RAG_ENDPOINT to a POST /search URL to use your own vector/fulltext DB.
      ragEndpoint: '',
      // Empty => the frontend-agent library's own default (currently lazos/lfm2.5-230m-frontend-agent
      // v1.0.0 Q6_K). Set NUXT_PUBLIC_MODEL_REPO / _VERSION / _QUANT to pin a different release
      // (e.g. a new eval-passed model version) without a library bump or a code change.
      modelRepo: '',
      modelVersion: '',
      modelQuant: '',
    },
  },

  vite: {
    plugins: [tailwindcss()],
    optimizeDeps: {
      include: ['@wllama/wllama'],
      // transformers.js pulls in onnxruntime-web (wasm + workers); let Vite serve it as-is
      // instead of pre-bundling, which mangles its wasm/worker asset resolution.
      exclude: ['@huggingface/transformers'],
    },
  },

  routeRules: {
    // Cross-origin isolation for wllama's multi-threaded WASM (SharedArrayBuffer). These are HTTP
    // headers, so they apply in dev / on a header-capable host; GitHub Pages can't send them, so
    // wllama auto-falls-back to single-thread there (slower but works). A coi-serviceworker shim
    // can re-enable SAB on Pages later if needed.
    '/**': {
      headers: {
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Embedder-Policy': 'require-corp',
      },
    },
  },
})
