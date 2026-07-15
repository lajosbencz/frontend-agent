<script setup lang="ts">
import { useAgentStore, type ToolCallRecord } from '~/stores/agent'
import { useSpeechOutput } from '~/composables/useSpeechOutput'
import { renderMarkdown } from '~/lib/markdown'
import type { DomainKey } from '~/lib/agent/domains'

const props = defineProps<{ domain: DomainKey; hint: string; thinkingLabel?: string }>()

const agent = useAgentStore(props.domain)
const voice = useSpeechOutput()
const bodyEl = ref<HTMLElement | null>(null)

const inspectedTool = ref<ToolCallRecord | null>(null)
const toolModalOpen = computed({
  get: () => inspectedTool.value !== null,
  set: (v) => {
    if (!v) inspectedTool.value = null
  },
})

// Keep the newest reply/tool-call in view as the conversation grows.
function scrollToLatest() {
  nextTick(() => {
    const el = bodyEl.value
    if (el) el.scrollTop = el.scrollHeight
  })
}
watch(() => [agent.transcript.length, agent.status], scrollToLatest)

const pct = computed(() => {
  const d = agent.downloadProgress
  return d && d.bytesTotal ? Math.round((d.bytesLoaded / d.bytesTotal) * 100) : null
})
</script>

<template>
  <div ref="bodyEl" class="flex min-h-[60px] flex-1 flex-col gap-[11px] overflow-y-auto px-[18px] py-4">
    <p v-if="agent.status === 'checking-cache'" class="m-0 font-mono text-[11px] font-medium text-text-faint">Checking for a cached model...</p>
    <p v-else-if="agent.status === 'downloading'" class="m-0 font-mono text-[11px] font-medium text-text-faint">
      Downloading model... <template v-if="pct !== null">{{ pct }}%</template>
    </p>
    <p v-else-if="agent.status === 'loading-into-memory'" class="m-0 font-mono text-[11px] font-medium text-text-faint">Loading model into memory...</p>
    <p v-if="agent.status === 'error' && agent.errorMessage" class="m-0 rounded-lg bg-error-bg px-2.5 py-2 text-[12px] text-error">⚠ {{ agent.errorMessage }}</p>

    <p v-if="agent.transcript.length === 0 && agent.status === 'ready'" class="m-0 text-[12px] text-text-subtle">{{ hint }}</p>

    <template v-for="(e, i) in agent.transcript" :key="i">
      <div v-if="e.role === 'user'" class="max-w-[82%] self-end rounded-[13px_13px_3px_13px] bg-dark px-[13px] py-2.5 text-[12px] leading-[1.4] break-words text-white">{{ e.content }}</div>
      <div v-else class="flex max-w-[88%] flex-col gap-1.5 self-start rounded-[13px_13px_13px_3px] bg-surface-2 px-[13px] py-2.5">
        <div v-if="e.tools?.length" class="flex flex-wrap gap-1.5">
          <button
            v-for="(t, ti) in e.tools"
            :key="ti"
            type="button"
            class="flex h-6 w-6 flex-none cursor-pointer items-center justify-center rounded-sm border border-border-2 bg-surface text-[12px] transition-colors hover:border-border-hover"
            :class="t.done ? 'text-accent' : 'text-text-faint'"
            :title="t.name"
            :aria-label="`Tool call: ${t.name}`"
            @click="inspectedTool = t"
          >🔧</button>
        </div>
        <span v-if="e.content" class="text-[12px] leading-[1.4] break-words text-text-2" v-html="renderMarkdown(e.content)" />
        <div v-if="e.content && voice.enabled.value" class="flex items-center gap-1.5">
          <template v-if="voice.speakingIndex.value === i && (voice.status.value === 'speaking' || voice.status.value === 'paused')">
            <button
              v-if="voice.status.value === 'speaking'"
              type="button"
              class="flex h-6 w-6 cursor-pointer items-center justify-center rounded-sm border border-border-2 bg-surface text-[11px] text-accent transition-colors hover:border-border-hover"
              title="Pause"
              aria-label="Pause spoken reply"
              @click="voice.pause"
            >⏸</button>
            <button
              v-else
              type="button"
              class="flex h-6 w-6 cursor-pointer items-center justify-center rounded-sm border border-border-2 bg-surface text-[11px] text-accent transition-colors hover:border-border-hover"
              title="Resume"
              aria-label="Resume spoken reply"
              @click="voice.resume"
            >▶</button>
            <button
              type="button"
              class="flex h-6 w-6 cursor-pointer items-center justify-center rounded-sm border border-border-2 bg-surface text-[11px] text-text-faint transition-colors hover:border-border-hover hover:text-text"
              title="Stop"
              aria-label="Stop spoken reply"
              @click="voice.stop"
            >⏹</button>
          </template>
          <!-- Not the active track: a persistent replay button. -->
          <button
            v-else
            type="button"
            class="flex h-6 w-6 cursor-pointer items-center justify-center rounded-sm border border-border-2 bg-surface text-[11px] text-text-faint transition-colors hover:border-border-hover hover:text-accent"
            title="Play spoken reply"
            aria-label="Play spoken reply"
            @click="voice.speak(e.content, i)"
          >▶</button>
        </div>
      </div>
    </template>

    <p v-if="agent.status === 'thinking'" class="m-0 font-mono text-[11px] font-medium text-accent">{{ thinkingLabel ?? 'thinking...' }}</p>

    <UiModal v-model="toolModalOpen">
      <template v-if="inspectedTool">
        <h3 class="m-0 font-mono text-[13px] font-semibold text-text">🔧 {{ inspectedTool.name }}</h3>
        <p class="mt-3 mb-1 font-mono text-[10px] font-medium tracking-wide text-text-faint uppercase">Request</p>
        <pre class="m-0 max-h-40 overflow-auto rounded-md bg-surface-2 p-2 font-mono text-[11px] whitespace-pre-wrap break-words text-text-2">{{ JSON.stringify(inspectedTool.args, null, 2) }}</pre>
        <p class="mt-3 mb-1 font-mono text-[10px] font-medium tracking-wide text-text-faint uppercase">Result</p>
        <pre v-if="inspectedTool.done" class="m-0 max-h-40 overflow-auto rounded-md bg-surface-2 p-2 font-mono text-[11px] whitespace-pre-wrap break-words text-text-2">{{ JSON.stringify(inspectedTool.result, null, 2) }}</pre>
        <p v-else class="m-0 font-mono text-[11px] text-text-faint">pending...</p>
      </template>
    </UiModal>
  </div>
</template>
