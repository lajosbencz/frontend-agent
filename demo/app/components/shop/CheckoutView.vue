<script setup lang="ts">
import { useCartStore } from '~/stores/cart'
import { DOMAINS } from '~/lib/domains'
import type { DomainKey } from '~/lib/agent/domains'

const props = defineProps<{ domain: DomainKey }>()
const config = computed(() => DOMAINS[props.domain]!.commerce!)
const cart = useCartStore(props.domain)
const orderId = ref<string | null>(null)

// Fully client-side mock (no server) - the demo deploys as pure static to GitHub Pages.
function placeOrder() {
  orderId.value = `${config.value.orderPrefix}-${crypto.randomUUID().slice(0, 8).toUpperCase()}`
  cart.clear()
}
</script>

<template>
  <div class="wrap max-w-[720px] pt-9 pb-16">
    <h1 class="mb-[22px] font-display text-[20px] font-bold tracking-[-0.03em]">Checkout</h1>

    <div v-if="orderId" class="flex flex-col items-start gap-3 rounded-xl border border-success bg-success-bg p-[26px] shadow-card">
      <span class="rounded-pill border border-success bg-surface px-2.5 py-[3px] font-mono text-[11px] text-success">✓ order placed</span>
      <p class="m-0 text-text-2">{{ config.successNote }}</p>
      <p class="m-0 font-mono text-[12px] text-text-2">Order ID: <strong class="text-text">{{ orderId }}</strong></p>
      <NuxtLink
        class="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2.5 font-body text-[12.5px] font-semibold text-white no-underline transition-colors hover:bg-accent-hover hover:no-underline [[data-theme=dark]_&]:text-bg"
        :to="config.shopTo"
      >Continue shopping →</NuxtLink>
    </div>

    <template v-else>
      <p v-if="cart.lines.length === 0" class="text-text-muted">Your cart is empty.</p>

      <div v-else class="flex flex-col gap-[18px]">
        <div class="rounded-xl border border-border bg-surface px-[18px] py-1 shadow-card">
          <div v-for="line in cart.lines" :key="line.slug" class="grid grid-cols-[1fr_auto_auto] items-center gap-4 border-b border-surface-4 py-3.5 last:border-b-0">
            <span class="font-display text-[12.5px] font-semibold tracking-[-0.01em]">{{ line.title }}</span>
            <span class="font-mono text-[11px] text-text-muted">×{{ line.quantity }}</span>
            <span class="min-w-14 text-right font-display text-[12.5px] font-semibold">${{ line.price * line.quantity }}</span>
          </div>
          <div class="grid grid-cols-[1fr_auto_auto] items-center gap-4 py-3.5">
            <span class="font-display text-[14px] font-semibold">Total</span>
            <span />
            <span class="min-w-14 text-right font-display text-[14px] font-semibold">${{ cart.total }}</span>
          </div>
        </div>

        <button
          class="inline-flex w-fit cursor-pointer items-center justify-center gap-2 self-start rounded-md bg-accent px-4 py-2.5 font-body text-[12.5px] font-semibold text-white transition-colors hover:bg-accent-hover [[data-theme=dark]_&]:text-bg"
          @click="placeOrder"
        >Place mock order</button>
      </div>
    </template>
  </div>
</template>
