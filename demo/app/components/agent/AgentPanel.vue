<script setup lang="ts">
import { useAgentStore } from '~/stores/agent'
import { useAgentRuntime } from '~/composables/useAgentRuntime'
import { useAgentLoop } from '~/composables/useAgentLoop'
import { useSpeechInput } from '~/composables/useSpeechInput'
import { useSpeechOutput } from '~/composables/useSpeechOutput'
import { useBackend } from '~/composables/useBackend'
import type { DomainKey } from '~/lib/agent/domains'

const props = withDefaults(
  defineProps<{
    domain: DomainKey
    title?: string
    placeholder?: string
    hint: string
    thinkingLabel?: string
    /** Whether this instance owns its own close affordance (docked launcher) or is always-open (vendor). */
    closable?: boolean
  }>(),
  {
    title: 'Ask anything...',
    placeholder: 'Ask about products, compatibility, or your cart...',
    closable: true,
  },
)

const agent = useAgentStore(props.domain)
const runtime = useAgentRuntime(props.domain)
const agentLoop = useAgentLoop(props.domain)
const speech = useSpeechInput()
const voice = useSpeechOutput()
const backend = useBackend()

const input = ref('')
const inputEl = ref<HTMLInputElement | null>(null)

onMounted(() => inputEl.value?.focus())

function close() {
  if (!props.closable) return
  agent.panelOpen = false
}

onMounted(() => {
  const onKey = (e: KeyboardEvent) => {
    if (props.closable && e.key === 'Escape' && agent.panelOpen) close()
  }
  window.addEventListener('keydown', onKey)
  onUnmounted(() => window.removeEventListener('keydown', onKey))
})

function toggleBackend() {
  if (!backend.webgpuAvailable.value) return
  runtime.switchBackend(backend.backend.value === 'webgpu' ? 'cpu' : 'webgpu')
}

// Speak newly-arrived assistant replies when the TTS preference is on.
watch(
  () => agent.transcript.length,
  () => {
    const lastIndex = agent.transcript.length - 1
    const last = agent.transcript[lastIndex]
    if (last?.role === 'assistant') voice.speak(last.content, lastIndex)
  },
)

async function submit() {
  const text = input.value.trim()
  if (!text || agent.status === 'thinking') return
  input.value = ''
  await agentLoop.send(text)
}

function stop() {
  agentLoop.stop()
}

// Optional voice layer: toggle records, then transcribes on the second tap. A completed
// transcript drives the agent through the same submit() path (auto-send), so speaking is
// equivalent to typing + Enter. Errors surface in the status line, never throw.
async function toggleMic() {
  const text = await speech.toggle()
  if (text) {
    input.value = text
    await submit()
  }
}
</script>

<template>
  <div class="flex h-full w-full flex-col overflow-hidden bg-surface">
    <div class="flex items-center gap-3 border-b border-surface-4 px-[18px] py-[15px]">
      <span class="h-2 w-2 flex-none rounded-pill bg-accent" />
      <span class="text-[13px] text-text">{{ title }}</span>
      <button
        v-if="backend.backend.value"
        class="ml-auto inline-flex items-center gap-1 font-mono text-[10px] font-medium text-text-faint"
        :class="backend.webgpuAvailable.value
          ? 'cursor-pointer rounded-pill border border-border bg-surface-3 px-2 py-[3px] hover:border-border-hover hover:text-text-2'
          : 'border-none bg-transparent p-0'"
        :title="backend.webgpuAvailable.value ? 'Click to switch GPU / CPU' : ''"
        @click="toggleBackend"
      >
        {{ backend.backend.value === 'webgpu' ? '⚡ GPU' : '🖥 CPU' }}
        <span v-if="backend.webgpuAvailable.value" class="opacity-60">⇄</span>
      </button>
      <ClientOnly>
        <button
          v-if="speech.supported"
          class="flex-none cursor-pointer rounded-pill border px-2 py-[3px] font-mono text-[10px] font-medium transition-colors"
          :class="[
            backend.backend.value ? 'ml-2' : 'ml-auto',
            speech.enabled.value
              ? 'border-accent bg-accent text-white [[data-theme=dark]_&]:text-bg'
              : 'border-border bg-surface-3 text-text-faint hover:border-border-hover hover:text-text-2',
          ]"
          :title="speech.enabled.value ? 'Voice input on - click to disable' : 'Enable voice input'"
          @click="speech.toggleEnabled"
        >
          {{ speech.enabled.value ? '🎙 Voice on' : '🎙 Voice off' }}
        </button>
        <button
          v-if="voice.supported"
          class="flex-none cursor-pointer rounded-pill border px-2 py-[3px] font-mono text-[10px] font-medium transition-colors"
          :class="[
            !speech.supported && !backend.backend.value ? 'ml-auto' : 'ml-2',
            voice.enabled.value
              ? 'border-accent bg-accent text-white [[data-theme=dark]_&]:text-bg'
              : 'border-border bg-surface-3 text-text-faint hover:border-border-hover hover:text-text-2',
          ]"
          :title="voice.enabled.value ? 'Spoken replies on - click to disable' : 'Enable spoken replies'"
          @click="voice.toggleEnabled"
        >
          {{ voice.enabled.value ? '🔊 TTS on' : '🔈 TTS off' }}
        </button>
      </ClientOnly>
      <button
        v-if="closable"
        class="ml-2 flex h-[26px] w-[26px] flex-none cursor-pointer items-center justify-center rounded-sm border border-transparent bg-transparent text-[12px] text-text-faint transition-colors hover:border-border hover:bg-surface-3 hover:text-text"
        title="Close (esc)"
        aria-label="Close assistant"
        @click="close"
      >✕</button>
    </div>

    <AgentTranscriptBody :domain="domain" :hint="hint" :thinking-label="thinkingLabel" />

    <p v-if="speech.status.value === 'recording'" class="m-0 px-[18px] pb-1.5 font-mono text-[11px] font-medium text-accent">
      ● listening... tap the mic to stop
    </p>
    <p v-else-if="speech.status.value === 'transcribing'" class="m-0 px-[18px] pb-1.5 font-mono text-[11px] font-medium text-text-faint">
      transcribing<template v-if="speech.modelProgress.value !== null && speech.modelProgress.value < 100">
        · loading voice model {{ speech.modelProgress.value }}%</template>...
    </p>
    <p v-else-if="speech.status.value === 'error' && speech.errorMessage.value" class="m-0 px-[18px] pb-1.5 font-mono text-[11px] font-medium text-error">
      {{ speech.errorMessage.value }}
    </p>
    <p v-if="voice.status.value === 'loading'" class="m-0 px-[18px] pb-1.5 font-mono text-[11px] font-medium text-text-faint">
      loading voice model<template v-if="voice.modelProgress.value !== null && voice.modelProgress.value < 100">
        · {{ voice.modelProgress.value }}%</template>...
    </p>
    <p v-else-if="voice.status.value === 'error' && voice.errorMessage.value" class="m-0 px-[18px] pb-1.5 font-mono text-[11px] font-medium text-error">
      {{ voice.errorMessage.value }}
    </p>

    <form class="flex gap-2 border-t border-surface-4 px-3.5 py-3" @submit.prevent="submit">
      <button
        v-if="speech.enabled.value"
        type="button"
        class="flex w-[42px] flex-none items-center justify-center rounded-md text-[13px] transition-colors disabled:cursor-default disabled:opacity-50"
        :class="[
          speech.status.value === 'recording'
            ? 'animate-mic-pulse cursor-pointer border border-accent bg-accent text-white'
            : 'cursor-pointer border border-border bg-surface-3 text-text-2 hover:border-border-hover hover:text-text',
          speech.status.value === 'transcribing' ? 'opacity-70' : '',
        ]"
        :title="speech.status.value === 'recording' ? 'Stop and transcribe' : 'Speak to the assistant'"
        aria-label="Voice input"
        :disabled="agent.status !== 'ready' || speech.status.value === 'transcribing'"
        @click="toggleMic"
      >
        {{ speech.status.value === 'recording' ? '■' : '🎤' }}
      </button>
      <input
        ref="inputEl"
        v-model="input"
        class="min-w-0 flex-1 rounded-md border border-border bg-surface px-3 py-2.5 font-body text-[13.5px] text-text outline-none focus:border-border-hover disabled:cursor-not-allowed"
        :placeholder="placeholder"
        :disabled="agent.status !== 'ready' && agent.status !== 'thinking' && agent.status !== 'error'"
      />
      <button
        v-if="agent.status === 'thinking'"
        class="w-[42px] cursor-pointer rounded-md border-none bg-accent text-[13.5px] text-white [[data-theme=dark]_&]:text-bg"
        type="button"
        title="Stop"
        aria-label="Stop"
        @click="stop"
      >■</button>
      <button
        v-else
        class="w-[42px] cursor-pointer rounded-md border-none bg-accent text-[13.5px] text-white disabled:cursor-default disabled:opacity-50 [[data-theme=dark]_&]:text-bg"
        type="submit"
        :disabled="agent.status !== 'ready' && agent.status !== 'error'"
      >↵</button>
    </form>
    <div class="flex items-center gap-3.5 border-t border-surface-4 bg-bg px-[18px] py-2.5 font-mono text-[10px] text-text-faint">
      <span>↵ send</span><span v-if="closable">esc close</span>
      <span class="ml-auto inline-flex items-center gap-1.5"><span class="h-1.5 w-1.5 rounded-pill bg-success" />LFM2.5 · 230M · on-device</span>
    </div>
  </div>
</template>
