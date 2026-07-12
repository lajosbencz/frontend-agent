<script setup lang="ts">
import { useCartStore } from '~/stores/cart'
import { DOMAINS } from '~/lib/domains'
import type { DomainKey } from '~/lib/agent/domains'

const props = defineProps<{ domain: DomainKey }>()
const config = computed(() => DOMAINS[props.domain]!.commerce!)
const cart = useCartStore(props.domain)
</script>

<template>
  <div class="wrap pt-9 pb-16">
    <h1 class="mb-[22px] font-display text-[20px] font-bold tracking-[-0.03em]">Cart</h1>

    <div v-if="cart.lines.length === 0" class="flex flex-col items-center gap-4 px-5 py-16 text-center text-text-muted">
      <p class="m-0 text-[13px]">Your cart is empty.</p>
      <NuxtLink
        class="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2.5 font-body text-[12.5px] font-semibold text-white no-underline transition-colors hover:bg-accent-hover hover:no-underline [[data-theme=dark]_&]:text-bg"
        :to="config.shopTo"
      >Browse products →</NuxtLink>
    </div>

    <div v-else class="grid grid-cols-[1fr_300px] items-start gap-6 max-[760px]:grid-cols-1">
      <div class="rounded-xl border border-border bg-surface px-[18px] py-1 shadow-card">
        <div
          v-for="line in cart.lines"
          :key="line.slug"
          class="grid grid-cols-[1fr_auto_auto_auto] items-center gap-4 border-b border-surface-4 py-4 last:border-b-0 max-[460px]:[grid-template-areas:'desc_total'_'step_remove'] max-[460px]:grid-cols-[1fr_auto]"
        >
          <div class="flex min-w-0 flex-col gap-[3px] [grid-area:desc]">
            <span class="font-display text-[13px] font-semibold tracking-[-0.01em]">{{ line.title }}</span>
            <span class="font-mono text-[11px] text-text-muted">${{ line.price }} each</span>
          </div>

          <div class="inline-flex items-center overflow-hidden rounded-md border border-border [grid-area:step]">
            <button class="h-[34px] w-8 cursor-pointer border-none bg-surface text-[13.5px] text-text transition-colors hover:bg-surface-2" aria-label="Decrease" @click="cart.setQuantity(line.slug, Math.max(1, line.quantity - 1))">−</button>
            <span class="min-w-[34px] border-x border-border text-center font-display text-[12.5px] leading-[34px] font-semibold">{{ line.quantity }}</span>
            <button class="h-[34px] w-8 cursor-pointer border-none bg-surface text-[13.5px] text-text transition-colors hover:bg-surface-2" aria-label="Increase" @click="cart.setQuantity(line.slug, line.quantity + 1)">+</button>
          </div>

          <span class="min-w-14 text-right font-display text-[13px] font-semibold [grid-area:total]">${{ line.price * line.quantity }}</span>
          <button class="cursor-pointer border-none bg-transparent p-1 font-mono text-[11px] text-text-subtle [grid-area:remove] justify-self-end hover:text-accent hover:underline" @click="cart.remove(line.slug)">remove</button>
        </div>
      </div>

      <aside class="flex flex-col gap-3.5 rounded-xl border border-border bg-surface p-[18px] shadow-card">
        <div class="flex items-baseline justify-between">
          <span class="font-mono text-[11px] text-text-muted">Subtotal ({{ cart.itemCount }})</span>
          <span class="font-display text-[16px] font-semibold">${{ cart.total }}</span>
        </div>
        <NuxtLink
          class="inline-flex items-center justify-center gap-2 rounded-md bg-accent px-4 py-2.5 font-body text-[12.5px] font-semibold text-white no-underline transition-colors hover:bg-accent-hover hover:no-underline [[data-theme=dark]_&]:text-bg"
          :to="config.checkoutTo"
        >Checkout →</NuxtLink>
        <p class="m-0 text-center text-[11px] text-text-muted">{{ config.checkoutNote }}</p>
      </aside>
    </div>
  </div>
</template>
