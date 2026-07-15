<script setup lang="ts">
defineProps<{ modelValue: boolean; disabled?: boolean }>()
defineEmits<{ 'update:modelValue': [boolean] }>()

// Colors default to storefront tokens; a container can override --toggle-* for a local palette.
</script>

<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :disabled="disabled"
    class="inline-flex h-5 w-9 flex-none cursor-pointer items-center rounded-pill border p-0.5 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
    :class="modelValue
      ? 'border-[var(--toggle-accent,var(--accent))] bg-[var(--toggle-accent,var(--accent))]'
      : 'border-[var(--toggle-border-color,var(--border))] bg-[var(--toggle-track-off,var(--surface-3))]'"
    @click="$emit('update:modelValue', !modelValue)"
  >
    <span
      class="h-3.5 w-3.5 rounded-pill bg-white shadow-sm transition-transform"
      :class="modelValue ? 'translate-x-[15px]' : 'translate-x-0'"
    />
  </button>
</template>
