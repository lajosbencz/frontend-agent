<script setup lang="ts">
definePageMeta({ layout: 'domain', domain: 'vendor' })
import { useAgentRuntime } from '~/composables/useAgentRuntime'
import { useVendorStore } from '~/stores/vendor'

const runtime = useAgentRuntime('vendor')
const vendor = useVendorStore()

const shelfRows = computed(() => [
  vendor.shelves.filter((g) => g.shelf === 1),
  vendor.shelves.filter((g) => g.shelf === 2),
  vendor.shelves.filter((g) => g.shelf === 3),
  vendor.shelves.filter((g) => g.shelf === 4),
])

// This domain has no launcher/⌘K - the whole page IS the conversation, so start loading right away.
onMounted(() => runtime.activate())
</script>

<template>
  <div class="wrap flex h-full min-h-0 max-w-[1080px] flex-col pt-5 pb-5">
    <!-- Illustrated store scene - hand-drawn SVG grocer + bunting, emoji goods. Fills the rest of
         the viewport: shelves on top, then a row with the grocer/counter and the docked chat. -->
    <div class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-border bg-surface-3">
      <!-- Market bunting: alternating pennant flags strung across the shopfront. -->
      <svg viewBox="0 0 400 26" preserveAspectRatio="none" class="block h-[20px] w-full flex-none" aria-hidden="true">
        <path
          v-for="i in 16"
          :key="i"
          :d="`M${(i - 1) * 25} 0 L${(i - 1) * 25 + 25} 0 L${(i - 1) * 25 + 12.5} 22 Z`"
          :fill="i % 2 ? 'var(--accent)' : 'var(--accent-soft)'"
        />
      </svg>

      <!-- Content row: shelves+counter column (left) and the docked chat column (right) - a row
           on wide screens, stacked on narrow ones. -->
      <div class="flex min-h-0 flex-1 flex-col min-[60rem]:flex-row">
        <!-- Shelves and counter are both flex-none: each renders at its natural (content-driven)
             size and never shrinks, so neither can get squeezed into the other. If the window is
             too short to fit both at that size, this column scrolls (overflow-y-auto) instead of
             compressing anything - no pixel heights locked anywhere. -->
        <div class="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-6 pt-3 pb-6">
          <div class="flex flex-none flex-col gap-2.5">
            <div v-for="(row, i) in shelfRows" :key="i" class="flex flex-col gap-1.5">
              <div class="h-2 rounded-[3px] border-b-[3px] border-border-2 bg-surface-4" />
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="g in row"
                  :key="g.id"
                  class="inline-flex items-center gap-[5px] rounded-sm border border-border-2 bg-surface py-1 pr-[9px] pl-1.5 text-[11px] text-text-2"
                  :title="`${g.title} · $${g.price}`"
                >
                  <span class="text-[13.5px] leading-none">{{ g.emoji }}</span>
                  <span>{{ g.title }}</span>
                </span>
              </div>
            </div>
          </div>

          <div class="flex flex-none items-end gap-4">
            <svg viewBox="0 0 120 96" class="h-[88px] w-[110px] flex-none" aria-hidden="true">
              <path d="M20 96 14 74Q18 68 26 70L30 96Z" fill="var(--accent)" />
              <path d="M100 96 106 74Q102 68 94 70L90 96Z" fill="var(--accent)" />
              <path d="M20 96 28 46Q60 34 92 46L100 96Z" fill="var(--accent)" />
              <path d="M46 96 50 58Q60 54 70 58L74 96Z" fill="var(--accent-hover)" opacity=".35" />
              <rect x="52" y="34" width="16" height="16" rx="4" fill="#e3ad82" />
              <circle cx="39" cy="26" r="4" fill="#e8b98a" />
              <circle cx="81" cy="26" r="4" fill="#e8b98a" />
              <circle cx="60" cy="24" r="20" fill="#e8b98a" />
              <circle cx="46" cy="30" r="3" fill="#d98a72" opacity=".5" />
              <circle cx="74" cy="30" r="3" fill="#d98a72" opacity=".5" />
              <path d="M50 32Q60 38 70 32Q65 34.5 60 32Q55 34.5 50 32Z" fill="#6b4a2f" />
              <circle cx="52" cy="23" r="2" fill="#2a1c12" />
              <circle cx="68" cy="23" r="2" fill="#2a1c12" />
              <path d="M37 17Q60 -5 83 17Q77 9 60 8Q43 9 37 17Z" fill="var(--accent-hover)" />
              <rect x="35" y="15" width="50" height="6" rx="3" fill="var(--accent-hover)" />
            </svg>

            <div class="min-w-0 flex-1">
              <!-- Deep oak counter - an actual wood surface, not another card, so it doesn't read
                   as a text input sitting next to the shelves. -->
              <div class="relative flex min-h-16 flex-wrap content-start gap-2 rounded-lg border border-[#33200f] bg-[repeating-linear-gradient(90deg,#5c3a20_0px,#5c3a20_5px,#4c2f19_5px,#4c2f19_10px)] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_8px_24px_-12px_rgba(0,0,0,0.5)]">
                <TransitionGroup name="drop">
                  <div
                    v-for="item in vendor.basket"
                    :key="item.key"
                    class="inline-flex items-center gap-1.5 rounded-pill border border-accent-tint-border bg-accent-tint py-[5px] pr-[11px] pl-[7px] text-[11px] text-text-2"
                  >
                    <span class="text-[12.5px]">{{ item.emoji }}</span>
                    <span>{{ item.title }}</span>
                    <span class="font-mono text-[10px] font-medium text-text-faint">×{{ item.quantity }}</span>
                  </div>
                </TransitionGroup>
                <p v-if="vendor.basket.length === 0" class="m-auto font-mono text-[11px] text-white/45">the counter is empty</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Same shared chat component every domain uses - docked here instead of floating, with
             no launcher/close since the whole page IS the conversation. -->
        <div class="flex h-[280px] min-h-0 flex-none flex-col overflow-hidden border-t border-border-2 bg-surface min-[60rem]:h-auto min-[60rem]:w-[360px] min-[60rem]:border-t-0 min-[60rem]:border-l">
          <AgentPanel
            domain="vendor"
            title="Ask the grocer..."
            placeholder="Say something to the grocer..."
            hint="Try &quot;what do you have?&quot; or &quot;I'll take a dozen eggs.&quot;"
            thinking-label="the grocer is thinking..."
            :closable="false"
          />
        </div>
      </div>
    </div>

    <!-- Mock transaction: a receipt snapshot taken when the agent's `pay` tool finalizes a sale. -->
    <UiModal :model-value="vendor.receipt !== null" @update:model-value="vendor.dismissReceipt">
      <template v-if="vendor.receipt">
        <span class="mb-2 inline-flex items-center gap-1.5 rounded-pill bg-success-bg px-2.5 py-1 font-mono text-[11px] font-medium text-success">✓ sale complete</span>
        <h3 class="m-0 font-display text-[16px] font-bold tracking-[-0.02em]">Receipt</h3>
        <div class="mt-3 flex flex-col gap-1.5">
          <div v-for="item in vendor.receipt.items" :key="item.key" class="flex items-center justify-between gap-3 text-[12.5px]">
            <span class="text-text-2">{{ item.emoji }} {{ item.title }} <span class="text-text-faint">×{{ item.quantity }}</span></span>
            <span class="font-mono text-text-2">${{ (item.price * item.quantity).toFixed(2) }}</span>
          </div>
          <p v-if="vendor.receipt.items.length === 0" class="m-0 font-mono text-[12px] text-text-faint">nothing on the counter</p>
        </div>
        <div class="mt-3 flex items-center justify-between border-t border-border pt-3 text-[13px] font-semibold">
          <span>Total</span>
          <span class="font-mono">${{ vendor.receipt.total.toFixed(2) }}</span>
        </div>
        <button
          type="button"
          class="mt-4 w-full cursor-pointer rounded-md border-none bg-accent px-4 py-2.5 font-body text-[12.5px] font-semibold text-bg transition-colors hover:bg-accent-hover"
          @click="vendor.dismissReceipt"
        >Done</button>
      </template>
    </UiModal>
  </div>
</template>

<style scoped>
/* Vue-transition class hooks (driven by the <TransitionGroup name="drop"> above) - not
   expressible as Tailwind utility classes since Vue applies these class names itself. */
.drop-enter-active { transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.2, 1.4, 0.4, 1); }
.drop-enter-from { opacity: 0; transform: translateY(-14px) scale(0.9); }
</style>
