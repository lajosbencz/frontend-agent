<script setup lang="ts">
definePageMeta({ layout: 'domain', domain: 'brewcraft' })

const route = useRoute()
const contentPath = route.path.replace(/^\/brewcraft/, '')
const { data: page } = await useAsyncData(`product-${route.path}`, () =>
  queryCollection('products').path(contentPath).first(),
)

if (!page.value) {
  throw createError({ statusCode: 404, statusMessage: 'Product not found', fatal: true })
}

const compatible = computed(() => {
  const c = page.value?.compatibleWith
  return Array.isArray(c) ? c : []
})
</script>

<template>
  <ShopProductDetail
    v-if="page"
    domain="brewcraft"
    :item="{ slug: page.slug, title: page.title, price: page.price, inStock: page.inStock, category: page.category, summary: page.summary }"
    crumb-to="/brewcraft/shop"
    crumb-label="Shop"
    footer-note="free shipping over $75 · 30-day returns"
  >
    <template #specs>
      <div class="overflow-hidden rounded-xl border border-border">
        <div class="flex justify-between gap-3 border-b border-surface-4 px-[15px] py-2.5 text-[12px] last:border-b-0"><span class="text-text-muted">Category</span><span class="text-right font-medium">{{ page.category }}</span></div>
        <div class="flex justify-between gap-3 border-b border-surface-4 px-[15px] py-2.5 text-[12px] last:border-b-0"><span class="text-text-muted">Price</span><span class="text-right font-medium">${{ page.price }}</span></div>
        <div class="flex justify-between gap-3 border-b border-surface-4 px-[15px] py-2.5 text-[12px] last:border-b-0"><span class="text-text-muted">In stock</span><span class="text-right font-medium">{{ page.inStock ? 'Yes' : 'No' }}</span></div>
        <div v-if="compatible.length" class="flex justify-between gap-3 border-b border-surface-4 px-[15px] py-2.5 text-[12px] last:border-b-0">
          <span class="text-text-muted">Compatible with</span><span class="text-right font-medium">{{ compatible.join(', ') }}</span>
        </div>
      </div>
    </template>
    <template #article>
      <div class="mt-12">
        <div class="mb-8 h-px bg-border" />
        <article class="prose max-w-[640px]">
          <ContentRenderer :value="page" />
        </article>
      </div>
    </template>
  </ShopProductDetail>
</template>

<style scoped>
/* ContentRenderer emits dynamic HTML, not our template, so these must be real :deep CSS. */
.prose :deep(h1), .prose :deep(h2), .prose :deep(h3) {
  font-family: var(--font-display); letter-spacing: -0.02em; margin: 1.6em 0 0.5em;
}
.prose :deep(h2) { font-size: 17px; }
.prose :deep(h3) { font-size: 14.5px; }
.prose :deep(p) { color: var(--text-2); font-size: 12.5px; line-height: 1.5; margin: 0 0 1em; }
.prose :deep(a) { color: var(--accent); }
.prose :deep(code) {
  font-family: var(--font-mono); font-size: 0.88em;
  background: var(--surface-2); padding: 1px 5px; border-radius: 5px;
}
.prose :deep(pre) {
  background: var(--surface-2); padding: 14px 16px; border-radius: var(--r);
  overflow-x: auto; border: 1px solid var(--border);
}
.prose :deep(pre code) { background: none; padding: 0; }
.prose :deep(ul), .prose :deep(ol) { color: var(--text-2); font-size: 12.5px; line-height: 1.5; padding-left: 1.2em; }
.prose :deep(table) { width: 100%; border-collapse: collapse; display: block; overflow-x: auto; }
.prose :deep(th), .prose :deep(td) {
  border: 1px solid var(--border); padding: 8px 12px; text-align: left; font-size: 12px;
}
</style>
