<script setup lang="ts">
const tools = [
  'search_catalog',
  'search_knowledge',
  'add_to_cart',
  'remove_from_cart',
  'view_cart',
  'clear_cart',
  'navigate',
]

const demos = [
  { to: '/brewcraft', name: 'BrewCraft', desc: 'browse, search, and check out' },
  { to: '/emporium', name: 'Emporium', desc: 'same shape, a stranger catalog' },
  { to: '/vendor', name: 'The Vendor', desc: 'no browsing UI - just talk' },
]
</script>

<template>
  <div class="about min-h-dvh bg-[var(--hub-bg)] font-sans text-[var(--hub-text)]">
    <div class="mx-auto max-w-[720px] px-[clamp(1rem,4vw,24px)] pt-10 pb-20">
      <NuxtLink to="/" class="mb-6 inline-block text-[11px] text-[var(--hub-muted)] no-underline hover:text-[var(--hub-accent)]">← Back</NuxtLink>

      <h1 class="m-0 text-[clamp(1.5rem,1.1rem+2vw,2.1rem)] leading-[1.1] font-bold tracking-[-0.03em] text-[var(--hub-text)]">
        How it works
      </h1>

      <p class="mt-[22px] text-[14px] leading-[1.5] text-[var(--hub-text-2)]">
        This site is three demo storefronts sharing one on-device agent: a fine-tuned
        <a class="text-[var(--hub-accent)] no-underline hover:underline" href="https://huggingface.co/LiquidAI/LFM2.5-230M" target="_blank">LFM2.5 - 230M</a> model that runs entirely in your browser and
        drives the interface with tools, rather than just answering in text. Each demo gives it a
        different persona, catalog, and tool set -
        <template v-for="(d, i) in demos" :key="d.to">
          <NuxtLink :to="d.to" class="text-[var(--hub-accent)] no-underline hover:underline">{{ d.name }}</NuxtLink><span v-if="i < demos.length - 1">, </span>
        </template>
        - to show the same core loop adapts to very different UIs.
      </p>

      <div class="mt-[26px] mb-2 flex flex-wrap gap-2">
        <span
          v-for="t in tools"
          :key="t"
          class="rounded-full border border-[var(--hub-accent-tint-border)] bg-[var(--hub-accent-tint)] px-[9px] py-1 font-[ui-monospace,monospace] text-[11px] text-[var(--hub-accent)]"
        >{{ t }}</span>
      </div>

      <section class="mt-[34px]">
        <h2 class="mb-2 text-[16px] font-semibold tracking-[-0.02em] text-[var(--hub-text)]">Runs on-device</h2>
        <p class="text-[13px] leading-[1.5] text-[var(--hub-text-2)]">
          There is no server doing inference. The model loads once and streams tokens right in
          your browser - WebGPU when your machine offers it, otherwise CPU/WASM via
          <span class="font-[ui-monospace,monospace] text-[0.92em]">wllama</span>. 
        </p>
        <p class="mt-2 text-[13px] leading-[1.5] text-[var(--hub-text-2)]">
          Voice input and voice replies are on-device models too
          (Whisper for speech-to-text, a small VITS model for text-to-speech) - nothing is sent
          anywhere for either.
        </p>
      </section>

      <section class="mt-[34px]">
        <h2 class="mb-2 text-[16px] font-semibold tracking-[-0.02em] text-[var(--hub-text)]">Grounded, not improvised</h2>
        <p class="text-[13px] leading-[1.5] text-[var(--hub-text-2)]">
          The live catalog and knowledge is injected as context, so replies stay grounded.
          Tools provide additional interactivity and context retrieval.
        </p>
      </section>

      <section class="mt-[34px]">
        <h2 class="mb-2 text-[16px] font-semibold tracking-[-0.02em] text-[var(--hub-text)]">Same model, different domains</h2>
        <p class="text-[13px] leading-[1.5] text-[var(--hub-text-2)]">
          BrewCraft and Emporium reuse the same catalog/cart tool shape over completely
          different data and persona.
        </p>
        <p class="mt-2 text-[13px] leading-[1.5] text-[var(--hub-text-2)]">
          The Vendor is a different kind of demo entirely: its own grocery inventory and
          knowledge base (haggling, recipes), the same trained tool set as the other two plus
          one bespoke addition (<span class="font-[ui-monospace,monospace] text-[0.92em]">pay</span>,
          to finalize a sale), and no cart page at all - the agent, not a form, is the whole interface.
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
