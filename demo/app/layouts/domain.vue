<script setup lang="ts">
import { DOMAINS } from '~/lib/domains'
import { useAgentStore } from '~/stores/agent'
import type { DomainKey } from '~/lib/agent/domains'

const route = useRoute()
const domain = computed(() => (route.meta.domain as DomainKey) ?? 'brewcraft')
const config = computed(() => DOMAINS[domain.value]!)
const agent = computed(() => (config.value.assistant === 'panel' ? useAgentStore(domain.value) : null))
</script>

<template>
  <div class="flex min-h-dvh flex-col bg-bg text-text" :data-theme="config.theme">
    <SiteNavBar :domain="domain" />
    <div class="flex flex-1 items-start" :class="{ 'overflow-hidden': config.fullHeight }">
      <div
        class="flex min-w-0 flex-1 flex-col"
        :style="config.fullHeight ? 'height: calc(100dvh - var(--nav-h))' : 'min-height: calc(100dvh - var(--nav-h))'"
        :class="{ 'max-[60rem]:pb-[55dvh]': agent?.panelOpen }"
      >
        <main class="flex flex-1 flex-col" :class="{ 'min-h-0': config.fullHeight }">
          <slot />
        </main>
        <SiteFooter v-if="!config.fullHeight" :domain="domain" />
      </div>
      <AgentLauncher v-if="config.assistant === 'panel'" :domain="domain" />
    </div>
  </div>
</template>
