<script setup lang="ts">
import { shortQuant } from 'frontend-agent/wllama'
import { useModelSwitcher } from '~/composables/useModelSwitcher'

// Split read-only button [params | quant | version | v] opening the size x quant matrix modal.
const emit = defineEmits<{ switched: [] }>()

const model = useModelSwitcher()
onMounted(() => model.init())

const open = ref(false)
const cur = computed(() => model.current.value)
</script>

<template>
  <div class="flex flex-col gap-1">
    <div class="flex items-center justify-between gap-2">
      <span class="text-[12.5px] text-[var(--hub-text)]">Model</span>
      <span
        class="min-h-[14px] truncate font-mono text-[10px]"
        :class="model.errorMessage.value ? 'text-error' : 'text-[var(--hub-muted)]'"
      >{{ model.statusText.value }}</span>
    </div>

    <button
      type="button"
      class="flex w-full items-stretch overflow-hidden rounded-md border border-[var(--hub-border)] bg-[var(--hub-surface)] font-mono text-[11px] text-[var(--hub-text)] transition-colors hover:border-[var(--hub-border-hover)] disabled:cursor-default disabled:opacity-50"
      :disabled="model.switching.value"
      aria-label="Select model"
      @click="open = true"
    >
      <span class="flex-1 px-2.5 py-2 text-left font-semibold">{{ cur.size }}</span>
      <span class="border-l border-[var(--hub-border)] px-2.5 py-2">{{ shortQuant(cur.ref.quant) }}</span>
      <span class="border-l border-[var(--hub-border)] px-2.5 py-2 text-[var(--hub-muted)]">{{ model.currentVersion.value }}</span>
      <span class="flex items-center border-l border-[var(--hub-accent)] bg-[var(--hub-accent)] px-2 text-white">&#9662;</span>
    </button>

    <UiModelMatrixModal v-model:open="open" @switched="emit('switched')" />
  </div>
</template>
