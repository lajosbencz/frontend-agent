<script setup lang="ts">
definePageMeta({ layout: 'domain', domain: 'emporium' })
import { emporiumProducts } from '~/data/emporium-products'
import { useCartStore } from '~/stores/cart'

const route = useRoute()
const cart = useCartStore('emporium')

const product = emporiumProducts.find((p) => p.slug === route.params.slug)
if (!product) {
  throw createError({ statusCode: 404, statusMessage: 'Product not found', fatal: true })
}

const qty = ref(1)
function dec() { if (qty.value > 1) qty.value-- }
function inc() { qty.value++ }
function addToCart() {
  if (!product.inStock) return
  cart.add({ slug: product.slug, title: product.name, price: product.price }, qty.value)
}
</script>

<template>
  <div class="wrap pt-6 pb-16">
    <nav class="mb-5 font-mono text-[11px] text-text-muted">
      <NuxtLink to="/emporium" class="text-text-muted hover:text-accent">Shop</NuxtLink> / <span class="text-text-2">{{ product.name }}</span>
    </nav>

    <div class="grid grid-cols-[repeat(auto-fit,minmax(300px,1fr))] items-start gap-10">
      <div class="flex aspect-square items-center justify-center rounded-xl border border-border bg-[repeating-linear-gradient(45deg,var(--photo-a),var(--photo-a)_12px,var(--photo-b)_12px,var(--photo-b)_24px)]">
        <span class="font-mono text-[10px] font-medium tracking-wide text-text-faint">IMG · {{ product.slug }}</span>
      </div>

      <div class="flex flex-col gap-3.5">
        <span class="self-start rounded-[6px] bg-accent-tint px-2.5 py-1 font-mono text-[10px] font-medium tracking-wide text-accent">{{ product.category }}</span>
        <h1 class="font-display text-[21px] font-bold tracking-[-0.03em]">{{ product.name }}</h1>

        <div class="flex items-center gap-3">
          <span class="font-display text-[17px] font-semibold">${{ product.price }}</span>
          <span v-if="product.inStock" class="inline-flex items-center gap-1 rounded-[7px] bg-success-bg px-2 py-0.5 font-mono text-[11px] font-medium text-success">✓ in stock</span>
          <span v-else class="font-mono text-[11px] font-medium text-accent">out of stock</span>
        </div>

        <p class="m-0 max-w-[440px] text-[12.5px] leading-[1.5] text-text-2">{{ product.description }}</p>

        <div class="mt-1 flex flex-wrap items-stretch gap-3">
          <div class="inline-flex items-center overflow-hidden rounded-md border border-border">
            <button class="h-[42px] w-[38px] cursor-pointer border-none bg-surface text-[14.5px] text-text transition-colors hover:bg-surface-2" aria-label="Decrease" @click="dec">−</button>
            <span class="min-w-10 border-x border-border text-center font-display text-[13px] leading-[42px] font-semibold">{{ qty }}</span>
            <button class="h-[42px] w-[38px] cursor-pointer border-none bg-surface text-[14.5px] text-text transition-colors hover:bg-surface-2" aria-label="Increase" @click="inc">+</button>
          </div>
          <button
            class="inline-flex min-w-[200px] flex-1 cursor-pointer items-center justify-center gap-2 rounded-md bg-accent px-4 py-2.5 font-body text-[12.5px] font-semibold text-bg transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="!product.inStock"
            @click="addToCart"
          >{{ product.inStock ? `Add to cart · $${product.price * qty}` : 'Out of stock' }}</button>
        </div>

        <p class="m-0 font-mono text-[11px] text-text-muted">no returns · no refunds · no regrets</p>
      </div>
    </div>
  </div>
</template>
