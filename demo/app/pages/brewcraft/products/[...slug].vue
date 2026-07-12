<script setup lang="ts">
definePageMeta({ layout: 'domain', domain: 'brewcraft' })
import { useCartStore } from '~/stores/cart'

const route = useRoute()
const cart = useCartStore('brewcraft')

const contentPath = route.path.replace(/^\/brewcraft/, '')
const { data: page } = await useAsyncData(`product-${route.path}`, () =>
  queryCollection('products').path(contentPath).first(),
)

if (!page.value) {
  throw createError({ statusCode: 404, statusMessage: 'Product not found', fatal: true })
}

const qty = ref(1)

const compatible = computed(() => {
  const c = page.value?.compatibleWith
  return Array.isArray(c) ? c : []
})

function dec() { if (qty.value > 1) qty.value-- }
function inc() { qty.value++ }

function addToCart() {
  if (!page.value || !page.value.inStock) return
  cart.add({ slug: page.value.slug, title: page.value.title, price: page.value.price }, qty.value)
}
</script>

<template>
  <div v-if="page" class="wrap pt-6 pb-16">
    <nav class="mb-5 font-mono text-[11px] text-text-muted">
      <NuxtLink to="/brewcraft/shop" class="text-text-muted hover:text-accent">Shop</NuxtLink> / <span class="text-text-2">{{ page.title }}</span>
    </nav>

    <div class="grid grid-cols-[repeat(auto-fit,minmax(300px,1fr))] items-start gap-10">
      <div class="flex aspect-square items-center justify-center rounded-xl border border-border bg-[repeating-linear-gradient(45deg,var(--photo-a),var(--photo-a)_12px,var(--photo-b)_12px,var(--photo-b)_24px)]">
        <span class="font-mono text-[10px] font-medium tracking-wide text-text-faint">IMG · {{ page.slug }}</span>
      </div>

      <div class="flex flex-col gap-3.5">
        <span class="self-start rounded-[6px] bg-accent-tint px-2.5 py-1 font-mono text-[10px] font-medium tracking-wide text-accent capitalize">{{ page.category }}</span>
        <h1 class="font-display text-[21px] font-bold tracking-[-0.03em]">{{ page.title }}</h1>

        <div class="flex items-center gap-3">
          <span class="font-display text-[17px] font-semibold">${{ page.price }}</span>
          <span v-if="page.inStock" class="inline-flex items-center gap-1 rounded-[7px] bg-success-bg px-2 py-0.5 font-mono text-[11px] font-medium text-success">✓ in stock</span>
          <span v-else class="font-mono text-[11px] font-medium text-accent">out of stock</span>
        </div>

        <p class="m-0 max-w-[440px] text-[12.5px] leading-[1.5] text-text-2">{{ page.summary }}</p>

        <div class="overflow-hidden rounded-xl border border-border">
          <div class="flex justify-between gap-3 border-b border-surface-4 px-[15px] py-2.5 text-[12px] last:border-b-0"><span class="text-text-muted">Category</span><span class="text-right font-medium">{{ page.category }}</span></div>
          <div class="flex justify-between gap-3 border-b border-surface-4 px-[15px] py-2.5 text-[12px] last:border-b-0"><span class="text-text-muted">Price</span><span class="text-right font-medium">${{ page.price }}</span></div>
          <div class="flex justify-between gap-3 border-b border-surface-4 px-[15px] py-2.5 text-[12px] last:border-b-0"><span class="text-text-muted">In stock</span><span class="text-right font-medium">{{ page.inStock ? 'Yes' : 'No' }}</span></div>
          <div v-if="compatible.length" class="flex justify-between gap-3 border-b border-surface-4 px-[15px] py-2.5 text-[12px] last:border-b-0">
            <span class="text-text-muted">Compatible with</span><span class="text-right font-medium">{{ compatible.join(', ') }}</span>
          </div>
        </div>

        <div class="mt-1 flex flex-wrap items-stretch gap-3">
          <div class="inline-flex items-center overflow-hidden rounded-md border border-border">
            <button class="h-[42px] w-[38px] cursor-pointer border-none bg-surface text-[14.5px] text-text transition-colors hover:bg-surface-2" aria-label="Decrease" @click="dec">−</button>
            <span class="min-w-10 border-x border-border text-center font-display text-[13px] leading-[42px] font-semibold">{{ qty }}</span>
            <button class="h-[42px] w-[38px] cursor-pointer border-none bg-surface text-[14.5px] text-text transition-colors hover:bg-surface-2" aria-label="Increase" @click="inc">+</button>
          </div>
          <button
            class="inline-flex min-w-[200px] flex-1 cursor-pointer items-center justify-center gap-2 rounded-md bg-accent px-4 py-2.5 font-body text-[12.5px] font-semibold text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50 [[data-theme=dark]_&]:text-bg"
            :disabled="!page.inStock"
            @click="addToCart"
          >
            {{ page.inStock ? `Add to cart · $${page.price * qty}` : 'Out of stock' }}
          </button>
        </div>

        <p class="m-0 font-mono text-[11px] text-text-muted">free shipping over $75 · 30-day returns</p>
      </div>
    </div>

    <div class="mt-12">
      <div class="mb-8 h-px bg-border" />
      <article class="prose max-w-[640px]">
        <ContentRenderer :value="page" />
      </article>
    </div>
  </div>
</template>

<style scoped>
/* Markdown body from ContentRenderer - dynamically rendered HTML, not our template, so these
   selectors must stay real CSS (:deep) rather than inline utility classes. */
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
