<script setup lang="ts">
const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [boolean] }>()

function close() {
  emit('update:modelValue', false)
}

onMounted(() => {
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && props.modelValue) close()
  }
  window.addEventListener('keydown', onKey)
  onUnmounted(() => window.removeEventListener('keydown', onKey))
})
</script>

<template>
  <!-- Not teleported: position:fixed already escapes clipping/z-index without needing <body>, and
       staying in-tree keeps CSS custom-property inheritance intact for callers with a local
       palette (e.g. the hub pages' independent --hub-* tokens, via the --toggle-* bridge below). -->
  <Transition name="ui-modal">
    <div v-if="modelValue" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="close" />
      <div class="relative w-full max-w-sm rounded-xl border border-[var(--toggle-border-color,var(--border))] bg-[var(--toggle-surface,var(--surface))] p-5 shadow-modal">
        <button
          class="absolute top-3 right-3 flex h-7 w-7 cursor-pointer items-center justify-center rounded-sm border-none bg-transparent text-[13px] text-[var(--toggle-muted,var(--text-faint))] transition-colors hover:text-[var(--toggle-text,var(--text))]"
          aria-label="Close"
          title="Close (esc)"
          @click="close"
        >✕</button>
        <slot />
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.ui-modal-enter-active,
.ui-modal-leave-active {
  transition: opacity 0.15s ease;
}
.ui-modal-enter-from,
.ui-modal-leave-to {
  opacity: 0;
}
</style>
