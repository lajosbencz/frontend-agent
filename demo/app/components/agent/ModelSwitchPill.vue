<script setup lang="ts">
import { shortQuant } from 'frontend-agent'
import { useModelSwitcher } from '~/composables/useModelSwitcher'

// Compact chat-header pill opening the shared matrix modal. `beforeSwitch` aborts any in-flight turn
// before teardown, so switching mid-conversation is safe. Hidden in self-host mode.
const props = defineProps<{ beforeSwitch?: () => void | Promise<void> }>()

const model = useModelSwitcher()
onMounted(() => model.init())

const open = ref(false)
const shortLabel = computed(() => `${model.current.value.size} ${shortQuant(model.current.value.ref.quant)}`)
</script>

<template>
  <div v-if="!model.selfHosted.value" class="flex-none">
    <button
      type="button"
      class="inline-flex items-center gap-1 rounded-pill border border-border bg-surface-3 px-2 py-[3px] font-mono text-[10px] font-medium text-text-faint transition-colors hover:border-border-hover hover:text-text-2 disabled:cursor-default disabled:opacity-60"
      :disabled="model.switching.value"
      :title="model.switching.value ? 'Switching model...' : 'Switch model'"
      @click="open = true"
    >
      <span v-if="model.switching.value">🧠 ...</span>
      <span v-else>🧠 {{ shortLabel }} <span class="opacity-60">▾</span></span>
    </button>

    <UiModelMatrixModal v-model:open="open" :before-switch="props.beforeSwitch" />
  </div>
</template>
