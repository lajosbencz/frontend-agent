<script setup lang="ts">
definePageMeta({ layout: 'domain', domain: 'brewcraft' })
const { data: products } = await useAsyncData('shop-list', () =>
  queryCollection('products').order('category', 'ASC').all(),
)

const filters = ['All', 'Machines', 'Grinders', 'Accessories']
const active = ref('All')

const shown = computed(() => {
  const all = products.value ?? []
  const filtered =
    active.value === 'All' ? all : all.filter((p) => (p.category ?? '').toLowerCase() === active.value.toLowerCase())
  return filtered.map((p) => ({ ...p, path: `/brewcraft${p.path}` }))
})
</script>

<template>
  <div class="wrap pt-9 pb-14">
    <header class="mb-[18px] flex items-baseline gap-3">
      <h1 class="font-display text-[20px] font-bold tracking-[-0.03em]">Shop</h1>
      <span class="text-[12px] text-text-muted">{{ shown.length }} items</span>
    </header>

    <div class="mb-[22px] flex flex-wrap gap-2">
      <button
        v-for="f in filters"
        :key="f"
        class="cursor-pointer rounded-pill border px-[11px] py-1.5 font-body text-[12px] font-medium transition-colors"
        :class="active === f ? 'border-dark bg-dark text-white' : 'border-border bg-surface text-text-2 hover:border-border-hover'"
        @click="active = f"
      >
        {{ f }}
      </button>
    </div>

    <div class="grid grid-cols-[repeat(auto-fill,minmax(230px,1fr))] gap-4 max-[480px]:grid-cols-[repeat(auto-fill,minmax(min(100%,160px),1fr))]">
      <ShopProductCard v-for="p in shown" :key="p.path" domain="brewcraft" :product="p" />
    </div>
  </div>
</template>
