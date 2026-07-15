<script setup lang="ts">

const demos = [
  { to: '/brewcraft', name: 'BrewCraft', desc: 'browse, search, and check out' },
  { to: '/emporium', name: 'Emporium', desc: 'same shape, a stranger catalog' },
  { to: '/vendor', name: 'The Vendor', desc: 'no browsing UI - just talk' },
]
</script>

<template>
  <div class="about min-h-dvh bg-[var(--hub-bg)] font-sans text-[var(--hub-text)]">
    <div class="mx-auto max-w-[720px] px-[clamp(1rem,4vw,24px)] pt-10 pb-20">
      <NuxtLink to="/" class="hub-link-muted mb-6 inline-block text-[11px]">← Back</NuxtLink>

      <h1 class="m-0 text-[clamp(1.5rem,1.1rem+2vw,2.1rem)] leading-[1.1] font-bold tracking-[-0.03em] text-[var(--hub-text)]">
        Does it work?
      </h1>

      <code><em>Well, yes, but actually no.</em></code>

      <p class="mt-[22px] text-[14px] leading-[1.5] text-[var(--hub-text-2)]">
        <a class="hub-link" href="https://huggingface.co/LiquidAI/LFM2.5-230M" target="_blank">LFM2.5 - 230M</a>
        is truly impressive for it's footprint, and the technical background to deliver and run it embedded in a browser is
        <a class="hub-link" href="https://github.com/ngxson/wllama" target="_blank">trivial</a>.
        The model picked up on training patterns in ~20M tokens, and easily manages structured tool calls.
        <br/><br/>
        <strong>But...</strong>
        <br/>
        230M parameters for diverse domains is not enough.
        During training, the imprinting of different, generalized uses-cases compete for attention.
        The fidelity of interaction is also lacking, and for multi-turn conversations it tends to follow the trainined<!-- sic. --> structure, instead of the actual context.
      </p>

      <section class="mt-[34px]">
        <h2 class="mb-2 text-[16px] font-semibold tracking-[-0.02em] text-[var(--hub-text)]">Forecast: Sunny</h2>
        <p class="text-[13px] leading-[1.5] text-[var(--hub-text-2)]">
          There are no cloud servers doing inference.
        </p>
        <p class="mt-2 text-[13px] leading-[1.5] text-[var(--hub-text-2)]">
          The model loads once and streams tokens right in
          your browser - WebGPU if available, otherwise CPU/WASM via
          <a class="hub-link" href="https://github.com/ngxson/wllama" target="_blank">wllama</a>. 
        </p>
        <p class="mt-2 text-[13px] leading-[1.5] text-[var(--hub-text-2)]">
          Besides the cool factor, running an on-device agent can be useful for:
        </p>
        <ul class="list-disc ml-3 mt-1 text-[12px] text-[var(--hub-text-2)]">
          <li>offline usage</li>
          <li>user privacy</li>
          <li>user accessibility</li>
          <li>hosting cost reduction</li>
        </ul>
        <p class="mt-2 text-[13px] leading-[1.5] text-[var(--hub-text-2)]">
          Combining it with <em>ARIA Roles</em> and <em>Semantic Elements</em> can make navigating a complex UI a breeze.
        </p>
      </section>

      <section class="mt-[34px]">
        <h2 class="mb-2 text-[16px] font-semibold tracking-[-0.02em] text-[var(--hub-text)]">Testbed</h2>
        <p class="text-[14px] leading-[1.5] text-[var(--hub-text-2)]">
          This site is three demo storefronts sharing one on-device agent: a fine-tuned model that runs entirely in your browser and
          drives the interface with tools, rather than just answering in text.
        </p>
        <p class="mt-2 text-[13px] leading-[1.5] text-[var(--hub-text-2)]">
          Each demo gives it a
          different persona, catalog, and tool set -
          <template v-for="(d, i) in demos" :key="d.to">
            <NuxtLink :to="d.to" class="hub-link">{{ d.name }}</NuxtLink><span v-if="i < demos.length - 1">, </span>
          </template>
          - to show the same core loop adapts to very different UIs.
        </p>
        <p class="mt-2 text-[13px] leading-[1.5] text-[var(--hub-text-2)]">
          The live catalog and knowledge is injected as context, so replies stay grounded.
          Tools provide additional interactivity and context retrieval.
        </p>
        <p class="mt-2 text-[13px] leading-[1.5] text-[var(--hub-text-2)]">
          Voice input and voice replies are on-device models too
          (<a class="hub-link" href="https://github.com/openai/whisper" target="_blank">Whisper</a> for speech-to-text,
          a small <a class="hub-link" href="https://huggingface.co/Xenova/mms-tts-eng" target="_blank">VITS model</a> for text-to-speech)
          - nothing is sent anywhere for either.
        </p>
        <p class="mt-2 text-[13px] leading-[1.5] text-[var(--hub-text-2)]">
          Stay tuned for an eval on
          <a class="hub-link" href="https://huggingface.co/LiquidAI/LFM2.5-350M" target="_blank">350M</a>
          at 1.5x the footprint.
        </p>
      </section>

      <p class="mt-11 border-t border-[var(--hub-border)] pt-5 font-[ui-monospace,monospace] text-[11px] tracking-wide text-[var(--hub-muted)]">
        no accounts - no tracking
      </p>
    </div>
  </div>
</template>

<style scoped>
/* Hub-local palette - see index.vue for the rationale (plain CSS vars + prefers-color-scheme,
   everything else above is inlined Tailwind utilities referencing these variables). */
.about {
  --hub-bg: #fafafa;
  --hub-surface: #ffffff;
  --hub-border: #e4e4e7;
  --hub-text: #101114;
  --hub-text-2: #34363d;
  --hub-muted: #6b6d76;
  --hub-accent: #3654ea;
  --hub-accent-tint: #ecf0ff;
  --hub-accent-tint-border: #d6ddff;
}
@media (prefers-color-scheme: dark) {
  .about {
    --hub-bg: #0a0a0c;
    --hub-surface: #131317;
    --hub-border: #24242b;
    --hub-text: #f1f1f4;
    --hub-text-2: #d3d4db;
    --hub-muted: #a4a5b0;
    --hub-accent: #7f97ff;
    --hub-accent-tint: #191c30;
    --hub-accent-tint-border: #262b48;
  }
}
</style>
