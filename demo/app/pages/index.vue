<script setup lang="ts">
const settingsOpen = ref(false)

const demos = [
  {
    to: '/brewcraft',
    name: 'BrewCraft',
    desc: 'Shop machines, beans and accessories; the agent searches the catalog and manages the cart for you.',
    icon: '☕',
  },
  {
    to: '/emporium',
    name: 'Emporium',
    desc: 'A shop of paradoxical goods. Same agent shape, a stranger catalog.',
    icon: '🧪',
  },
  {
    to: '/vendor',
    name: 'The Vendor',
    desc: 'Unconventional UI. Ask for something and watch it land on the counter.',
    icon: '🍎',
  },
]
</script>

<template>
  <div class="home min-h-dvh bg-[var(--hub-bg)] font-sans text-[var(--hub-text)]">
    <div class="mx-auto max-w-[860px] px-[clamp(1rem,4vw,24px)] pt-[clamp(40px,7vw,80px)] pb-16">
      <div class="flex flex-wrap items-start justify-between gap-6">
        <div class="min-w-[240px] flex-1">
          <span class="font-[ui-monospace,monospace] text-[11px] font-semibold tracking-wider text-[var(--hub-accent)] uppercase">
            <span
              class="inline-block rounded-full bg-[var(--hub-accent-tint)] px-[9px] py-1 mx-1"
            >language model</span>
            <span
              class="inline-block rounded-full bg-[var(--hub-accent-tint)] px-[9px] py-1 mx-1"
            >frontend agent</span>
            <span
              class="inline-block rounded-full bg-[var(--hub-accent-tint)] px-[9px] py-1 mx-1"
            >tech demo</span>
          </span>

          <h1 class="mt-5 text-[clamp(1.5rem,1rem+2vw,2.1rem)] leading-[1.1] font-bold tracking-[-0.03em] text-[var(--hub-text)]">
            Generalist agent, on Your device
          </h1>
          <p class="mt-4 max-w-[420px] text-[13px] leading-[1.5] text-[var(--hub-muted)]">
            A tiny language model running entirely in your browser, driving various UIs with tools.
            <ul class="pt-3">
              <li>
                <NuxtLink
                  to="/about"
                  class="mt-1 inline-block text-[12px] text-[var(--hub-muted)] no-underline hover:text-[var(--hub-accent)]"
                >→ How this works</NuxtLink>
              </li>
              <li>
                <a
                  href="https://github.com/lajosbencz/frontend-agent"
                  target="_blank"
                  class="mt-1 inline-block text-[12px] text-[var(--hub-muted)] no-underline hover:text-[var(--hub-accent)]"
                >→ Github Source</a>
              </li>
            </ul>
          </p>
        </div>

        <div class="hidden w-full shrink-0 rounded-lg border border-[var(--hub-border)] bg-[var(--hub-surface)] p-4 sm:block sm:w-[240px]">
          <HubSettingsPanel />
        </div>
        <button
          type="button"
          class="flex h-9 w-9 flex-none cursor-pointer items-center justify-center rounded-md border border-[var(--hub-border)] bg-[var(--hub-surface)] text-[15px] text-[var(--hub-text)] sm:hidden"
          aria-label="Open settings"
          title="Settings"
          @click="settingsOpen = true"
        >⚙</button>
      </div>

      <h3 class="mt-9 text-[clamp(1.2rem,0.9rem+1.5vw,1.5rem)] leading-none font-bold tracking-[-0.03em] text-[var(--hub-text)]">
        Examples
      </h3>

      <div class="mt-3 grid grid-cols-[repeat(auto-fit,minmax(230px,1fr))] gap-4">
        <NuxtLink
          v-for="d in demos"
          :key="d.to"
          :to="d.to"
          class="flex flex-col gap-2 rounded border border-[var(--hub-border)] bg-[var(--hub-surface)] p-4 text-inherit no-underline transition-[border-color,transform] hover:-translate-y-0.5 hover:border-[var(--hub-border-hover)] hover:no-underline"
        >
          <span class="mt-1 text-[15px] font-bold tracking-[-0.02em]">
            <span>{{ d.icon }}</span>
            {{ d.name }}
          </span>
          <span class="flex-1 text-[12px] leading-[1.5] text-[var(--hub-muted)]">{{ d.desc }}</span>
          <span class="mt-2 self-end font-[ui-monospace,monospace] text-[11px] font-medium text-[var(--hub-accent)]">Open →</span>
        </NuxtLink>
      </div>
    </div>

    <UiModal v-model="settingsOpen">
      <HubSettingsPanel />
    </UiModal>
  </div>
</template>

<style scoped>
/* Hub-local palette (own identity, independent of the storefront's --bg/--accent/etc tokens) -
   plain CSS custom properties + a prefers-color-scheme media query is the only way to express
   this; everything else above is inlined Tailwind utilities referencing these variables. The
   --toggle-* bridge lets the generic UiToggleSwitch/UiModal primitives pick up this palette
   instead of the storefront's, purely via CSS inheritance (no JS/props needed). */
.home {
  --hub-bg: #fafafa;
  --hub-surface: #ffffff;
  --hub-border: #e4e4e7;
  --hub-border-hover: #c9c9d0;
  --hub-text: #101114;
  --hub-muted: #6b6d76;
  --hub-accent: #3654ea;
  --hub-accent-tint: #ecf0ff;

  --toggle-accent: var(--hub-accent);
  --toggle-track-off: var(--hub-border);
  --toggle-border-color: var(--hub-border);
  --toggle-surface: var(--hub-surface);
  --toggle-muted: var(--hub-muted);
  --toggle-text: var(--hub-text);
}
@media (prefers-color-scheme: dark) {
  .home {
    --hub-bg: #0a0a0c;
    --hub-surface: #131317;
    --hub-border: #24242b;
    --hub-border-hover: #34343e;
    --hub-text: #f1f1f4;
    --hub-muted: #a4a5b0;
    --hub-accent: #335ccc;
    --hub-accent-tint: #191c30;
  }
}
</style>
