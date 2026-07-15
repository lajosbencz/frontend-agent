<script setup lang="ts">
import { useCartStore } from '~/stores/cart'

const props = defineProps<{
  domain: string
  item: { slug: string; title: string; price: number; inStock: boolean; category: string; summary: string }
  crumbTo: string
  crumbLabel: string
  footerNote: string
}>()

const cart = useCartStore(props.domain)
const qty = ref(1)
function dec() { if (qty.value > 1) qty.value-- }
function inc() { qty.value++ }
function addToCart() {
  if (!props.item.inStock) return
  cart.add({ slug: props.item.slug, title: props.item.title, price: props.item.price }, qty.value)
}
</script>

<template>
  <div class="wrap pt-6 pb-16">
    <nav class="mb-5 font-mono text-[11px] text-text-muted">
      <NuxtLink :to="crumbTo" class="text-text-muted hover:text-accent">{{ crumbLabel }}</NuxtLink> / <span class="text-text-2">{{ item.title }}</span>
    </nav>

    <div class="grid grid-cols-[repeat(auto-fit,minmax(300px,1fr))] items-start gap-10">
      <div class="flex aspect-square items-center justify-center rounded-xl border border-border bg-[repeating-linear-gradient(45deg,var(--photo-a),var(--photo-a)_12px,var(--photo-b)_12px,var(--photo-b)_24px)]">
        <span class="font-mono text-[10px] font-medium tracking-wide text-text-faint">IMG · {{ item.slug }}</span>
      </div>

      <div class="flex flex-col gap-3.5">
        <span class="self-start rounded-[6px] bg-accent-tint px-2.5 py-1 font-mono text-[10px] font-medium tracking-wide text-accent capitalize">{{ item.category }}</span>
        <h1 class="font-display text-[21px] font-bold tracking-[-0.03em]">{{ item.title }}</h1>

        <div class="flex items-center gap-3">
          <span class="font-display text-[17px] font-semibold">${{ item.price }}</span>
          <span v-if="item.inStock" class="inline-flex items-center gap-1 rounded-[7px] bg-success-bg px-2 py-0.5 font-mono text-[11px] font-medium text-success">✓ in stock</span>
          <span v-else class="font-mono text-[11px] font-medium text-accent">out of stock</span>
        </div>

        <p class="m-0 max-w-[440px] text-[12.5px] leading-[1.5] text-text-2">{{ item.summary }}</p>

        <slot name="specs" />

        <div class="mt-1 flex flex-wrap items-stretch gap-3">
          <div class="inline-flex items-center overflow-hidden rounded-md border border-border">
            <button class="h-[42px] w-[38px] cursor-pointer border-none bg-surface text-[14.5px] text-text transition-colors hover:bg-surface-2" aria-label="Decrease" @click="dec">−</button>
            <span class="min-w-10 border-x border-border text-center font-display text-[13px] leading-[42px] font-semibold">{{ qty }}</span>
            <button class="h-[42px] w-[38px] cursor-pointer border-none bg-surface text-[14.5px] text-text transition-colors hover:bg-surface-2" aria-label="Increase" @click="inc">+</button>
          </div>
          <button
            class="inline-flex min-w-[200px] flex-1 cursor-pointer items-center justify-center gap-2 rounded-md bg-accent px-4 py-2.5 font-body text-[12.5px] font-semibold text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50 [[data-theme=dark]_&]:text-bg"
            :disabled="!item.inStock"
            @click="addToCart"
          >
            {{ item.inStock ? `Add to cart · $${item.price * qty}` : 'Out of stock' }}
          </button>
        </div>

        <p class="m-0 font-mono text-[11px] text-text-muted">{{ footerNote }}</p>
      </div>
    </div>

    <slot name="article" />
  </div>
</template>
