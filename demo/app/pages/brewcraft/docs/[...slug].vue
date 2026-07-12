<script setup lang="ts">
definePageMeta({ layout: 'domain', domain: 'brewcraft' })
const route = useRoute()

const contentPath = route.path.replace(/^\/brewcraft/, '')
const { data: page } = await useAsyncData(`doc-${route.path}`, () =>
  queryCollection('docs').path(contentPath).first(),
)

if (!page.value) {
  throw createError({ statusCode: 404, statusMessage: 'Doc not found', fatal: true })
}
</script>

<template>
  <div v-if="page" class="wrap pt-6 pb-[72px]">
    <nav class="mx-auto mb-6 max-w-[700px] font-mono text-[11px] text-text-muted">
      <NuxtLink to="/brewcraft/docs" class="text-text-muted hover:text-accent">Guides</NuxtLink> / <span class="text-text-2">{{ page.title }}</span>
    </nav>

    <article class="prose mx-auto max-w-[700px]">
      <ContentRenderer :value="page" />
    </article>
  </div>
</template>

<style scoped>
/* Markdown body from ContentRenderer - dynamically rendered HTML, not our template, so these
   selectors must stay real CSS (:deep) rather than inline utility classes. */
.prose :deep(h1) { font: 700 24px var(--font-display); letter-spacing: -0.03em; line-height: 1.1; margin: 0 0 0.5em; }
.prose :deep(h2) { font: 600 17px var(--font-display); letter-spacing: -0.02em; margin: 1.8em 0 0.5em; }
.prose :deep(h3) { font: 600 14.5px var(--font-display); letter-spacing: -0.01em; margin: 1.6em 0 0.4em; }
.prose :deep(p) { font-size: 12.5px; line-height: 1.5; color: var(--text-2); margin: 0 0 1.1em; }
.prose :deep(ul), .prose :deep(ol) { font-size: 12.5px; line-height: 1.5; color: var(--text-2); padding-left: 1.3em; margin: 0 0 1.1em; }
.prose :deep(li) { margin: 0.3em 0; }
.prose :deep(a) { color: var(--accent); }
.prose :deep(code) {
  font-family: var(--font-mono); font-size: 0.86em;
  background: var(--surface-2); padding: 1px 5px; border-radius: 5px;
}
.prose :deep(pre) {
  background: var(--surface-2); border: 1px solid var(--border);
  padding: 14px 16px; border-radius: var(--r); overflow-x: auto; margin: 0 0 1.2em;
}
.prose :deep(pre code) { background: none; padding: 0; font-size: 11px; }
.prose :deep(blockquote) {
  border-left: 3px solid var(--accent); margin: 0 0 1.2em; padding: 2px 0 2px 16px;
  color: var(--text-muted);
}
.prose :deep(table) {
  width: 100%; border-collapse: collapse; display: block; overflow-x: auto; margin: 0 0 1.2em; font-size: 12px;
}
.prose :deep(th), .prose :deep(td) {
  border: 1px solid var(--border); padding: 8px 12px; text-align: left;
}
.prose :deep(th) { background: var(--surface-2); font-weight: 600; }
.prose :deep(hr) { border: none; border-top: 1px solid var(--border); margin: 2em 0; }
.prose :deep(img) { border-radius: var(--r); }
</style>
