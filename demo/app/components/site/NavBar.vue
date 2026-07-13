<script setup lang="ts">
import { useCartStore } from '~/stores/cart'
import { useAgentStore } from '~/stores/agent'
import { useAgentRuntime } from '~/composables/useAgentRuntime'
import { DOMAINS } from '~/lib/domains'
import type { DomainKey } from '~/lib/agent/domains'

const props = defineProps<{ domain: DomainKey }>()

const config = computed(() => DOMAINS[props.domain]!)
const cart = computed(() => (config.value.commerce ? useCartStore(props.domain) : null))
const agent = computed(() => (config.value.assistant === 'panel' ? useAgentStore(props.domain) : null))
const runtime = config.value.assistant === 'panel' ? useAgentRuntime(props.domain) : null

function askAgent() {
  runtime?.activate()
}

onMounted(() => {
  const handler = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault()
      askAgent()
    }
  }
  window.addEventListener('keydown', handler)
  onUnmounted(() => window.removeEventListener('keydown', handler))
})
</script>

<template>
  <header class="sticky top-0 z-40 border-b border-border bg-[color-mix(in_srgb,var(--bg)_82%,transparent)] backdrop-blur-md">
    <div class="wrap flex min-h-14 flex-wrap items-center gap-5 py-[9px]">
      <NuxtLink to="/" class="font-mono text-[11px] text-text-faint no-underline max-[30rem]:hidden hover:text-text-muted" title="All demos">← all demos</NuxtLink>
      <NuxtLink :to="config.links[0]?.to ?? '/'" class="flex items-center gap-[9px] no-underline">
        <span class="h-[18px] w-[18px] rounded-pill bg-accent shadow-[inset_-5px_-5px_0_rgba(0,0,0,0.14)]" />
        <span class="font-display text-[14.5px] font-bold tracking-[-0.025em] text-text">{{ config.brand }}</span>
      </NuxtLink>
      <nav class="flex flex-wrap items-center gap-3.5">
        <NuxtLink
          v-for="l in config.links"
          :key="l.to"
          :to="l.to"
          class="px-0.5 py-1 font-body text-[12.5px] font-medium text-text-muted no-underline hover:text-text [&.router-link-exact-active]:font-semibold [&.router-link-exact-active]:text-text"
        >{{ l.label }}</NuxtLink>
      </nav>
      <div class="ml-auto flex items-center gap-2">
        <svg
          v-if="agent"
          class="animate-nudge-x h-[34px] w-5 flex-none text-accent"
          viewBox="0 0 20 24"
          fill="none"
          stroke="currentColor"
          stroke-width="3.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        ><path d="M5 6l8 6-8 6" /></svg>
        <button
          v-if="agent"
          class="flex cursor-pointer items-center gap-[9px] rounded-[9px] border border-border bg-surface py-[7px] pr-2.5 pl-3 text-[12px] text-text-muted transition-colors hover:border-border-hover hover:text-text"
          @click="askAgent"
        >
          <span class="h-1.5 w-1.5 rounded-pill bg-accent" />
          <span class="max-[30rem]:hidden">Ask agent</span>
          <kbd class="rounded-[5px] border border-border bg-surface-3 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-text-subtle max-[30rem]:hidden">⌘K</kbd>
        </button>
        <NuxtLink
          v-if="cart"
          :to="config.commerce!.cartTo"
          class="flex items-center gap-1.5 rounded-[9px] border border-dark bg-dark px-3 py-[7px] text-[12px] font-medium text-white no-underline hover:bg-black"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><path d="M6 8h12l-1.2 11H7.2L6 8z"/><path d="M9 8V6.5a3 3 0 0 1 6 0V8"/></svg>
          <span>{{ cart.itemCount }}</span>
        </NuxtLink>
      </div>
    </div>
  </header>
</template>
