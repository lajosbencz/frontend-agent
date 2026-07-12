<script setup lang="ts">
import { useCartStore } from '~/stores/cart'

const props = defineProps<{
  domain: string
  product: {
    path: string
    slug: string
    title: string
    price: number
    summary: string
    category: string
    inStock: boolean
  }
}>()

const cart = useCartStore(props.domain)

function add(e: Event) {
  e.preventDefault()
  e.stopPropagation()
  if (!props.product.inStock) return
  cart.add({ slug: props.product.slug, title: props.product.title, price: props.product.price }, 1)
}
</script>

<template>
  <NuxtLink
    :to="product.path"
    class="flex cursor-pointer flex-col overflow-hidden rounded-lg border border-border bg-surface text-left text-inherit no-underline transition-[border-color,box-shadow] hover:border-border-hover hover:shadow-card hover:no-underline"
    :data-agent-target="`product-card-${product.slug}`"
  >
    <div class="flex aspect-[4/3] items-center justify-center bg-[repeating-linear-gradient(45deg,var(--photo-a),var(--photo-a)_9px,var(--photo-b)_9px,var(--photo-b)_18px)]">
      <span class="font-mono text-[10px] font-medium tracking-wide text-text-faint">IMG · {{ product.slug }}</span>
    </div>
    <div class="flex flex-1 flex-col gap-[5px] px-3.5 pt-[13px] pb-3.5">
      <div class="flex items-baseline justify-between gap-2">
        <span class="font-display text-[12.5px] font-semibold tracking-[-0.01em]">{{ product.title }}</span>
        <span class="font-display text-[12.5px] font-semibold">${{ product.price }}</span>
      </div>
      <span class="text-[11px] text-text-subtle capitalize">{{ product.category }}</span>
      <span class="flex-1 text-[11px] leading-[1.4] text-text-muted">{{ product.summary }}</span>
      <div class="mt-1.5 flex items-center justify-between gap-2">
        <span v-if="product.inStock" class="inline-flex items-center gap-1 rounded-[7px] bg-success-bg px-2 py-0.5 font-mono text-[11px] font-medium text-success">✓ in stock</span>
        <span v-else class="font-mono text-[11px] font-medium text-accent">out of stock</span>
        <button
          class="rounded-sm border border-accent-tint-border bg-accent-tint px-2.5 py-[5px] font-body text-[11px] font-semibold text-accent hover:bg-accent-tint-border disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="!product.inStock"
          @click="add"
        >Add +</button>
      </div>
    </div>
  </NuxtLink>
</template>
