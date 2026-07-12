<script setup lang="ts">
import { useAgentStore } from '~/stores/agent'
import type { DomainKey } from '~/lib/agent/domains'

const props = defineProps<{ domain: DomainKey }>()
const agent = useAgentStore(props.domain)
// (Esc-to-close is handled in AgentPanel.)
</script>

<template>
  <!-- Docked assistant. Sticky right column on wide screens; fixed bottom sheet on narrow.
       Renders nothing when closed, so the content column is full-width. -->
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
/* Vue-transition class hooks (driven by the <Transition name="dock"> above) - not expressible as
   Tailwind utility classes since Vue applies these class names itself based on the `name` prop. */
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
