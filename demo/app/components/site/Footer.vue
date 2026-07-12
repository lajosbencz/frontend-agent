<script setup lang="ts">
import { DOMAINS } from '~/lib/domains'
import type { DomainKey } from '~/lib/agent/domains'

const props = defineProps<{ domain: DomainKey }>()
const config = computed(() => DOMAINS[props.domain]!)
</script>

<template>
  <footer class="border-t border-border bg-surface-2">
    <div class="wrap flex flex-wrap justify-between gap-7 py-8">
      <div class="max-w-[280px]">
        <div class="mb-2 flex items-center gap-2">
          <span class="h-[15px] w-[15px] rounded-pill bg-accent shadow-[inset_-4px_-4px_0_rgba(0,0,0,0.14)]" />
          <span class="font-display text-[13px] font-bold tracking-[-0.02em] text-text">{{ config.brand }}</span>
        </div>
        <p class="m-0 text-[11px] leading-[1.5] text-text-subtle">One of three demos showcasing an on-device LLM agent that uses tools to drive the UI.</p>
      </div>
      <div class="flex flex-wrap gap-10">
        <div class="flex flex-col gap-2">
          <div class="mb-0.5 font-mono text-[10px] font-semibold text-text-faint">GO</div>
          <NuxtLink v-for="l in config.links" :key="l.to" :to="l.to" class="text-[12px] text-text-muted no-underline hover:text-text">{{ l.label }}</NuxtLink>
          <NuxtLink v-if="config.commerce" :to="config.commerce.cartTo" class="text-[12px] text-text-muted no-underline hover:text-text">Cart</NuxtLink>
        </div>
        <div class="flex flex-col gap-2">
          <div class="mb-0.5 font-mono text-[10px] font-semibold text-text-faint">DEMO</div>
          <NuxtLink to="/" class="text-[12px] text-text-muted no-underline hover:text-text">All demos</NuxtLink>
          <NuxtLink to="/about" class="text-[12px] text-text-muted no-underline hover:text-text">How it works</NuxtLink>
        </div>
      </div>
    </div>
  </footer>
</template>
