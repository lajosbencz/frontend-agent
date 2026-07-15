import tailwindcss from '@tailwindcss/vite'

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: ['@nuxt/content', '@pinia/nuxt'],
  compatibilityDate: '2024-04-03',
  css: ['~/assets/css/tailwind.css'],

  ssr: true,
  nitro: {
    // Static export for GitHub Pages (`npm run generate`); set NUXT_APP_BASE_URL=/<repo>/ for project pages.
    preset: 'github_pages',
    prerender: { crawlLinks: true, routes: ['/'] },
  },
  app: {
    baseURL: process.env.NUXT_APP_BASE_URL || '/',
    head: {
      // Restores cross-origin isolation on static hosts that can't send the headers below.
      script: [
        { src: `${process.env.NUXT_APP_BASE_URL || '/'}coi-serviceworker.js`, tagPriority: 'critical' },
      ],
    },
  },

  runtimeConfig: {
    public: {
      modelRepo: '',
      modelVersion: '',
      modelQuant: '',
      modelUrl: '',
    },
  },

  vite: {
    plugins: [tailwindcss()],
    optimizeDeps: {
      // frontend-agent's transitive deps are pre-bundled here (the lib itself is excluded below, so
      // Vite can't discover them from it) to avoid first-load page reloads.
      include: ['@wllama/wllama', 'minisearch', 'stemmer', 'marked'],
      // Don't pre-bundle the local workspace lib: Vite would cache a stale copy of dist/ and 404 after
      // a lib rebuild. Excluded -> it resolves fresh from dist each time (rebuild the lib to update).
      exclude: ['@huggingface/transformers', 'frontend-agent'],
    },
  },

  routeRules: {
    // Cross-origin isolation for wllama's SharedArrayBuffer. `credentialless` keeps isolation while
    // still allowing cross-origin (Hugging Face) model downloads; `require-corp` blocks them.
    '/**': {
      headers: {
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Embedder-Policy': 'credentialless',
      },
    },
  },
})
