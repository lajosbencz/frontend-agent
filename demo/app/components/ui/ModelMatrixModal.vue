<script setup lang="ts">
import { MODEL_SIZES, MODEL_QUANTS, modelOptionAt, DEFAULT_MODEL_ID } from 'frontend-agent/wllama'
import { useModelSwitcher } from '~/composables/useModelSwitcher'

// Shared pick surface: size x quant matrix + HF-git-tag version selector, in a modal. Uses the
// --toggle-* bridge tokens (--hub-* on Settings, storefront base in chat) so it stays legible in dark.
const open = defineModel<boolean>('open', { required: true })
const props = defineProps<{ beforeSwitch?: () => void | Promise<void> }>()
const emit = defineEmits<{ switched: [] }>()

const model = useModelSwitcher()
const selectedVersion = ref(model.currentVersion.value)

watch(open, (isOpen) => {
  if (isOpen) {
    selectedVersion.value = model.currentVersion.value
    model.loadVersions()
  }
})

// Always include current + selected so the <select> is never empty before the HF fetch resolves.
const versionOptions = computed(() =>
  Array.from(new Set([...model.versions.value, model.currentVersion.value, selectedVersion.value])),
)

async function pick(id: string | undefined) {
  if (!id) return
  if (id === model.currentId.value && selectedVersion.value === model.currentVersion.value) {
    open.value = false
    return
  }
  await props.beforeSwitch?.()
  await model.select(id, selectedVersion.value)
  if (!model.errorMessage.value) {
    open.value = false
    emit('switched')
  }
}

async function pickRecommended() {
  await props.beforeSwitch?.()
  await model.resetToRecommended()
  if (!model.errorMessage.value) {
    open.value = false
    emit('switched')
  }
}
</script>

<template>
  <UiModal v-model="open" size="md">
    <div
      class="flex flex-col gap-4 text-[var(--m-text)]"
      style="--m-text: var(--toggle-text, var(--text)); --m-border: var(--toggle-border-color, var(--border)); --m-muted: var(--toggle-muted, var(--text-faint)); --m-accent: var(--toggle-accent, var(--accent))"
    >
      <!-- Explicit color: the global h1..h4 { color: var(--text) } rule hits this element directly;
           on the hub (no [data-theme] attr) --text stays light = dark-on-dark without this. -->
      <h3 class="pr-8 text-[13px] font-semibold text-[var(--m-text)]">Select model</h3>

      <!-- Matrix: quant rows x parameter columns; each cell is a build showing its download size. -->
      <div class="grid gap-1.5" style="grid-template-columns: auto repeat(2, minmax(0, 1fr))">
        <div />
        <div
          v-for="size in MODEL_SIZES"
          :key="size"
          class="pb-1 text-center font-mono text-[11px] font-semibold"
        >{{ size }}</div>

        <template v-for="q in MODEL_QUANTS" :key="q.quant">
          <div class="flex flex-col justify-center pr-2 text-right leading-tight">
            <span class="font-mono text-[11px] font-semibold">{{ q.short }}</span>
            <span class="text-[9px] text-[var(--m-muted)]">{{ q.note }}</span>
          </div>
          <button
            v-for="size in MODEL_SIZES"
            :key="size + q.quant"
            type="button"
            class="flex flex-col items-center justify-center gap-0.5 rounded-md border px-2 py-2.5 transition-colors disabled:cursor-default disabled:opacity-50"
            :style="modelOptionAt(size, q.quant)?.id === model.currentId.value
              ? 'border-color: var(--m-accent)'
              : 'border-color: var(--m-border)'"
            :class="modelOptionAt(size, q.quant)?.id === model.currentId.value
              ? 'text-[var(--m-accent)]'
              : 'cursor-pointer hover:border-[var(--m-accent)]'"
            :disabled="model.switching.value || !modelOptionAt(size, q.quant)"
            @click="pick(modelOptionAt(size, q.quant)?.id)"
          >
            <span class="font-mono text-[11px]">~{{ modelOptionAt(size, q.quant)?.approxMB }} MB</span>
            <span
              v-if="modelOptionAt(size, q.quant)?.id === model.currentId.value"
              class="text-[9px] font-semibold"
            >current</span>
            <span
              v-else-if="modelOptionAt(size, q.quant)?.id === DEFAULT_MODEL_ID"
              class="text-[9px] text-[var(--m-muted)]"
            >default</span>
          </button>
        </template>
      </div>

      <!-- Version (git tag on the HF repo), listed from Hugging Face -->
      <label class="flex items-center justify-between gap-3">
        <span class="text-[12px]">Version</span>
        <select
          v-model="selectedVersion"
          :disabled="model.switching.value"
          class="min-w-[7rem] cursor-pointer rounded-md border border-[var(--m-border)] bg-[var(--toggle-surface,var(--surface))] px-2 py-1.5 font-mono text-[11px] transition-colors hover:border-[var(--m-accent)] focus:border-[var(--m-accent)] focus:outline-none disabled:cursor-default disabled:opacity-50"
        >
          <option v-for="v in versionOptions" :key="v" :value="v">{{ v }}</option>
        </select>
      </label>

      <button
        v-if="!model.isRecommended.value"
        type="button"
        class="self-start text-[11px] text-[var(--m-accent)] underline-offset-2 hover:underline disabled:cursor-default disabled:opacity-50"
        :disabled="model.switching.value"
        @click="pickRecommended"
      >Switch back to recommended</button>

      <p class="text-[10px] leading-relaxed text-[var(--m-muted)]">
        More parameters = smarter; higher quant = more faithful but a larger download. Pick a version,
        then a build - this only sets your choice. Use Preload (or just start chatting) to download and
        load it; an already-cached pick loads instantly.
      </p>
      <p
        v-if="model.statusText.value"
        class="min-h-[14px] font-mono text-[10px]"
        :class="model.errorMessage.value ? 'text-error' : 'text-[var(--m-muted)]'"
      >{{ model.statusText.value }}</p>
    </div>
  </UiModal>
</template>
