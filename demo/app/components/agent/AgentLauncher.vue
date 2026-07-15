<script setup lang="ts">
import { useAgentStore } from '~/stores/agent'
import type { DomainKey } from '~/lib/agent/domains'

const props = defineProps<{ domain: DomainKey }>()
const agent = useAgentStore(props.domain)
</script>

<template>
  <!-- Docked assistant: sticky right column on wide screens, fixed bottom sheet on narrow. -->
  <Transition name="dock">
    <aside
      v-if="agent.panelOpen"
      class="sticky top-[var(--nav-h)] z-30 h-[calc(100dvh-var(--nav-h))] flex-[0_0_var(--dock-w)] self-stretch border-l border-border bg-surface max-[60rem]:fixed max-[60rem]:inset-x-0 max-[60rem]:top-auto max-[60rem]:bottom-0 max-[60rem]:h-[55dvh] max-[60rem]:flex-none max-[60rem]:border-l-0 max-[60rem]:border-t max-[60rem]:shadow-float"
    >
      <AgentPanel :domain="domain" />
    </aside>
  </Transition>
</template>

<style scoped>
/* Vue-transition class hooks (name="dock") - Vue applies these itself, not Tailwind utilities. */
.dock-enter-active,
.dock-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.dock-enter-from,
.dock-leave-to {
  opacity: 0;
  transform: translateX(12px);
}
@media (max-width: 60rem) {
  .dock-enter-from,
  .dock-leave-to {
    opacity: 0;
    transform: translateY(16px);
  }
}
</style>
