<script setup lang="ts">
definePageMeta({ layout: 'domain', domain: 'emporium' })
import { emporiumProducts } from '~/data/emporium-products'

const products = emporiumProducts.map((p) => ({
  path: `/emporium/products/${p.slug}`,
  slug: p.slug,
  title: p.name,
  price: p.price,
  summary: p.description,
  category: p.category,
  inStock: p.inStock,
}))

const filters = ['All', ...new Set(products.map((p) => p.category))]
const active = ref('All')

const shown = computed(() =>
  active.value === 'All' ? products : products.filter((p) => p.category === active.value),
)
</script>

<template>
  <div class="wrap pt-9 pb-14">
    <header class="mb-[22px]">
      <span class="mb-4 inline-flex items-center gap-2 rounded-pill border border-accent-tint-border bg-accent-tint px-[9px] py-1 font-mono text-[11px] font-medium tracking-wide text-accent">✦ questionable goods</span>
      <h1 class="font-display text-[22px] font-bold tracking-[-0.03em]">Emporium</h1>
      <p class="mt-2 text-[12.5px] text-text-muted">Perfectly reasonable products, if you squint.</p>
    </header>

    <div class="mb-[22px] flex flex-wrap gap-2">
      <button
        v-for="f in filters"
        :key="f"
        class="cursor-pointer rounded-pill border px-[11px] py-1.5 font-body text-[12px] font-medium transition-colors"
        :class="active === f ? 'border-accent bg-accent text-bg' : 'border-border bg-surface text-text-2 hover:border-border-hover'"
        @click="active = f"
      >
        {{ f }}
      </button>
    </div>

    <div class="grid grid-cols-[repeat(auto-fill,minmax(230px,1fr))] gap-4 max-[480px]:grid-cols-[repeat(auto-fill,minmax(min(100%,160px),1fr))]">
      <ShopProductCard v-for="p in shown" :key="p.path" domain="emporium" :product="p" />
    </div>
  </div>
</template>
