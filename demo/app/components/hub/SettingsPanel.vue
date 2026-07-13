<script setup lang="ts">
import { useSpeechInput } from '~/composables/useSpeechInput'
import { useSpeechOutput } from '~/composables/useSpeechOutput'
import { useModelPreload } from '~/composables/useModelPreload'
import { useModelInfo } from '~/composables/useModelInfo'
import { useBackend } from '~/composables/useBackend'

const speech = useSpeechInput()
const voice = useSpeechOutput()
const preload = useModelPreload()
const modelInfo = useModelInfo()
const backend = useBackend()

function toggleGpu() {
  if (backend.webgpuAvailable.value === false) return
  backend.toggle()
}

function formatBytes(bytes: number): string {
  const mb = bytes / (1024 * 1024)
  return mb >= 1024 ? `${(mb / 1024).toFixed(2)} GB` : `${mb.toFixed(1)} MB`
}

onMounted(() => {
  preload.checkCached()
  modelInfo.check()
})

const preloadDisabled = computed(() => preload.status.value === 'downloading' || preload.status.value === 'ready')

const preloadLabel = computed(() => {
  if (preload.status.value === 'ready') return 'Model loaded'
  if (preload.status.value === 'downloading') {
    const p = preload.progress.value
    const pct = p && p.bytesTotal ? Math.round((p.bytesLoaded / p.bytesTotal) * 100) : null
    return pct !== null ? `Loading... ${pct}%` : 'Loading...'
  }
  if (preload.status.value === 'error') return 'Retry preload'
  return preload.cached.value ? 'Preload model (cached)' : 'Preload model'
})

// Split-button dropdown for the two destructive actions - only ever meaningful once there's a
// cached file and/or a loaded engine, so the caret itself disables when neither applies.
const menuOpen = ref(false)
const menuRoot = ref<HTMLElement | null>(null)
const menuDisabled = computed(() => !preload.cached.value && preload.status.value !== 'ready')

function closeMenu() {
  menuOpen.value = false
}

onMounted(() => {
  const onDocClick = (e: MouseEvent) => {
    if (menuOpen.value && menuRoot.value && !menuRoot.value.contains(e.target as Node)) closeMenu()
  }
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') closeMenu()
  }
  document.addEventListener('click', onDocClick)
  window.addEventListener('keydown', onKey)
  onUnmounted(() => {
    document.removeEventListener('click', onDocClick)
    window.removeEventListener('keydown', onKey)
  })
})

async function onPreload() {
  await preload.preload()
  await modelInfo.refresh()
}

async function onClearCache() {
  closeMenu()
  await preload.clearCache()
  await modelInfo.refresh()
}

async function onUnload() {
  closeMenu()
  await preload.unload()
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <h2 class="text-[11px] font-semibold tracking-wide text-[var(--hub-muted)] uppercase">Settings</h2>

    <ClientOnly>
      <div v-if="speech.supported" class="flex items-center justify-between gap-3">
        <span class="text-[12.5px] text-[var(--hub-text)]">Voice input</span>
        <UiToggleSwitch :model-value="speech.enabled.value" @update:model-value="speech.toggleEnabled" />
      </div>
      <div v-if="voice.supported" class="flex items-center justify-between gap-3">
        <span class="text-[12.5px] text-[var(--hub-text)]">Spoken replies</span>
        <UiToggleSwitch :model-value="voice.enabled.value" @update:model-value="voice.toggleEnabled" />
      </div>
    </ClientOnly>

    <div class="flex items-center justify-between gap-3">
      <span class="text-[12.5px] text-[var(--hub-text)]">GPU acceleration</span>
      <UiToggleSwitch
        :model-value="(backend.backend.value ?? (backend.pref.value === 'cpu' ? 'cpu' : 'webgpu')) === 'webgpu'"
        :disabled="backend.webgpuAvailable.value === false || backend.switching.value"
        @update:model-value="toggleGpu"
      />
    </div>

    <div class="flex flex-col gap-1.5">
      <div ref="menuRoot" class="relative flex">
        <button
          type="button"
          class="flex-1 rounded-l-md border px-3 py-2 font-mono text-[11px] font-medium transition-colors disabled:cursor-default"
          :class="preloadDisabled
            ? 'border-[var(--hub-border)] bg-[var(--hub-surface)] text-[var(--hub-muted)]'
            : 'cursor-pointer border-[var(--hub-accent)] bg-[var(--hub-accent)] text-white hover:opacity-90'"
          :disabled="preloadDisabled"
          @click="onPreload"
        >{{ preloadLabel }}<span v-if="preload.status.value === 'ready'" class="text-success"> ✓</span></button>
        <button
          type="button"
          class="flex-none rounded-r-md border border-l-0 px-2 font-mono text-[11px] transition-colors disabled:cursor-default disabled:opacity-40"
          :class="menuDisabled
            ? 'border-[var(--hub-border)] bg-[var(--hub-surface)] text-[var(--hub-muted)]'
            : 'cursor-pointer border-[var(--hub-border)] bg-[var(--hub-surface)] text-[var(--hub-text)] hover:border-[var(--hub-border-hover)]'"
          :disabled="menuDisabled"
          aria-label="Model actions"
          :aria-expanded="menuOpen"
          @click="menuOpen = !menuOpen"
        >▾</button>

        <div
          v-if="menuOpen"
          class="absolute top-[calc(100%+4px)] right-0 z-10 w-48 overflow-hidden rounded-md border border-[var(--hub-border)] bg-[var(--hub-surface)] py-1 shadow-modal"
        >
          <button
            type="button"
            class="block w-full px-3 py-2 text-left text-[11px] text-[var(--hub-text)] disabled:cursor-default disabled:text-[var(--hub-muted)] disabled:opacity-50"
            :class="{ 'cursor-pointer hover:bg-[var(--hub-accent-tint)]': preload.cached.value }"
            :disabled="!preload.cached.value"
            @click="onClearCache"
          >❌ Clear cached model</button>
          <button
            type="button"
            class="block w-full px-3 py-2 text-left text-[11px] text-[var(--hub-text)] disabled:cursor-default disabled:text-[var(--hub-muted)] disabled:opacity-50"
            :class="{ 'cursor-pointer hover:bg-[var(--hub-accent-tint)]': preload.status.value === 'ready' }"
            :disabled="preload.status.value !== 'ready'"
            @click="onUnload"
          >⭕ Unload from memory</button>
        </div>
      </div>
      <p v-if="preload.errorMessage.value" class="m-0 text-[11px] text-error">{{ preload.errorMessage.value }}</p>
      <p v-if="modelInfo.info.value" class="m-0 font-mono text-[10px] leading-[1.5] text-[var(--hub-muted)]">
        Version: {{ modelInfo.info.value.version }}
        <br/>
        Quantization: {{ modelInfo.info.value.quant }}
        <br/>
        <span v-if="modelInfo.info.value.sha256" :title="modelInfo.info.value.sha256">
          Xet hash: {{ modelInfo.info.value.sha256.slice(0, 12) }}...
        </span>
        <span v-else>Hash unavailable</span>
        <br/>
        <span v-if="modelInfo.info.value.diskBytes !== null">On disk: {{ formatBytes(modelInfo.info.value.diskBytes) }}</span>
        <span v-else>Not downloaded</span>
      </p>
    </div>
  </div>
</template>
