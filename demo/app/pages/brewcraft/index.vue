<script setup lang="ts">
import type { ProductCardItem } from '~/lib/shop'

definePageMeta({ layout: 'domain', domain: 'brewcraft' })
const featuredSlugs = ['duo-machine', 'precision-grinder', 'milk-pitcher', 'tamper-58mm']
const { data: products } = await useAsyncData('home-featured', () =>
  queryCollection('products').all(),
)
const featured = computed<ProductCardItem[]>(() =>
  featuredSlugs
    .map((s) => (products.value ?? []).find((p) => p.slug === s))
    .filter((p): p is NonNullable<typeof p> => p != null)
    .map((p) => ({
      path: `/brewcraft${p.path}`,
      slug: p.slug,
      title: p.title,
      price: p.price,
      summary: p.summary,
      category: p.category,
      inStock: p.inStock,
    })),
)

const homeDocSlugs = ['getting-started', 'dialing-in', 'milk-steaming']
const { data: docs } = await useAsyncData('home-docs', () =>
  queryCollection('docs').all(),
)
const homeDocs = computed(() =>
  homeDocSlugs
    .map((s) => (docs.value ?? []).find((d) => d.path === `/docs/${s}`))
    .filter(Boolean)
    .map((d) => ({ ...d!, path: `/brewcraft${d!.path}` })),
)

const categories = [
  { name: 'Machines', desc: 'Single, dual boiler & lever', to: '/brewcraft/shop' },
  { name: 'Grinders', desc: 'Flat & conical burr grinders', to: '/brewcraft/shop' },
  { name: 'Accessories', desc: 'Tampers, scales & maintenance', to: '/brewcraft/shop' },
]

const tools = [
  { name: 'list_items', args: 'query, filters' },
  { name: 'add_to_cart', args: 'id, quantity' },
  { name: 'search_knowledge', args: 'query' },
  { name: 'navigate', args: 'target, id' },
]
</script>

<template>
  <div class="animate-fade-in">
    <!-- HERO -->
    <section class="wrap grid grid-cols-[repeat(auto-fit,minmax(320px,1fr))] items-center gap-11 pt-14 pb-10">
      <div>
        <span class="inline-flex items-center gap-2 rounded-pill border border-accent-tint-border bg-accent-tint px-[9px] py-1 font-mono text-[11px] font-medium tracking-wide text-accent">◑ ESPRESSO, DIALED IN</span>
        <h1 class="mt-5 text-[clamp(28px,3.6vw,38px)] leading-[1.1] font-bold tracking-[-0.035em] text-text-strong">Better espresso starts<br>at your counter.</h1>
        <p class="mt-[18px] mb-7 max-w-[440px] text-[13.5px] leading-[1.5] text-text-muted">
          Espresso machines, precision grinders, and step-by-step guides - everything you need to
          pull a café-grade shot at home.
        </p>
        <div class="flex flex-wrap gap-3">
          <NuxtLink to="/brewcraft/shop" class="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2.5 font-body text-[12.5px] font-semibold text-white no-underline transition-colors hover:bg-accent-hover hover:no-underline [[data-theme=dark]_&]:text-bg">Shop the collection →</NuxtLink>
          <NuxtLink to="/brewcraft/docs" class="inline-flex items-center gap-2 rounded-md border border-border bg-surface px-4 py-2.5 font-body text-[12.5px] font-semibold text-text no-underline transition-colors hover:border-border-hover hover:no-underline">Explore brewing guides</NuxtLink>
        </div>
      </div>

      <!-- agent demo card -->
      <div class="rounded-xl border border-border bg-surface p-[18px] shadow-float">
        <div class="flex items-center gap-[9px] border-b border-surface-4 px-1 pt-0.5 pb-3">
          <span class="h-[7px] w-[7px] rounded-pill bg-accent" />
          <span class="font-mono text-[11px] font-semibold text-text-2">brewcraft agent</span>
          <span class="ml-auto font-mono text-[10px] font-medium text-text-faint">on-device</span>
        </div>
        <div class="flex flex-col gap-[11px] px-1 pt-3.5 pb-1.5">
          <div class="max-w-[82%] self-end rounded-[13px_13px_3px_13px] bg-dark px-[13px] py-2.5 text-[12px] leading-[1.4] text-white">Find a grinder under $300 and add it to my cart</div>
          <div class="inline-flex items-center gap-2 self-start rounded-sm border border-border bg-surface-3 px-2.5 py-1.5 font-mono text-[11px] font-medium text-text-2"><span class="text-accent">→</span> list_items<span class="text-text-faint">{ query:"grinder", max_price:300 }</span></div>
          <div class="inline-flex items-center gap-2 self-start rounded-sm border border-border bg-surface-3 px-2.5 py-1.5 font-mono text-[11px] font-medium text-text-2"><span class="text-success">✓</span> add_to_cart<span class="text-text-faint">{ id:"compact-grinder" }</span></div>
          <div class="max-w-[86%] self-start rounded-[13px_13px_13px_3px] bg-surface-2 px-[13px] py-2.5 text-[12px] leading-[1.4] text-[#3a352e]">Added the <b class="font-semibold">Compact Grinder ($219)</b>. It pairs with any BrewCraft machine - want a tamper too?</div>
        </div>
      </div>
    </section>

    <!-- CATEGORY CARDS -->
    <section class="wrap grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4 pt-3 pb-2">
      <NuxtLink
        v-for="c in categories"
        :key="c.name"
        :to="c.to"
        class="flex cursor-pointer flex-col gap-[5px] rounded-lg border border-border-2 bg-surface-3 p-5 text-left text-inherit no-underline transition-colors hover:border-border-hover hover:bg-surface-4 hover:no-underline"
      >
        <span class="font-display text-[14px] font-semibold tracking-[-0.02em]">{{ c.name }}</span>
        <span class="text-[12px] text-text-muted">{{ c.desc }}</span>
        <span class="mt-2 font-mono text-[11px] font-medium text-accent">Browse →</span>
      </NuxtLink>
    </section>

    <!-- POPULAR -->
    <section class="wrap pt-10 pb-2">
      <div class="mb-[18px] flex items-baseline justify-between">
        <h2 class="font-display text-[17px] font-semibold tracking-[-0.02em]">Popular right now</h2>
        <NuxtLink to="/brewcraft/shop" class="font-body text-[12px] font-medium text-accent no-underline">View all →</NuxtLink>
      </div>
      <div class="grid grid-cols-[repeat(auto-fill,minmax(230px,1fr))] gap-4">
        <ShopProductCard v-for="p in featured" :key="p.path" domain="brewcraft" :product="p" />
      </div>
    </section>

    <!-- LEARN -->
    <section class="wrap pt-10 pb-2">
      <div class="mb-[18px] flex items-baseline justify-between">
        <h2 class="font-display text-[17px] font-semibold tracking-[-0.02em]">Learn to brew</h2>
        <NuxtLink to="/brewcraft/docs" class="font-body text-[12px] font-medium text-accent no-underline">All guides →</NuxtLink>
      </div>
      <div class="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-4">
        <NuxtLink
          v-for="d in homeDocs"
          :key="d!.path"
          :to="d!.path"
          class="flex cursor-pointer flex-col gap-2 rounded-lg border border-border bg-surface p-[18px] text-left text-inherit no-underline transition-colors hover:border-border-hover hover:no-underline"
        >
          <div><span class="rounded-[6px] bg-accent-tint px-2 py-[3px] font-mono text-[10px] font-medium text-accent">guide</span></div>
          <span class="font-display text-[13.5px] font-semibold tracking-[-0.01em]">{{ d!.title }}</span>
          <span class="text-[11px] leading-[1.4] text-text-muted">{{ d!.description }}</span>
        </NuxtLink>
      </div>
    </section>

    <!-- SHOWCASE -->
    <section class="wrap pb-14">
      <div class="grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] items-center gap-7 rounded-[20px] bg-dark p-[clamp(28px,4vw,48px)] text-white">
        <div>
          <span class="font-mono text-[11px] font-medium tracking-wide text-accent-soft">THE SHOWCASE</span>
          <h2 class="my-3 text-[clamp(20px,2.6vw,26px)] leading-[1.1] font-semibold tracking-[-0.025em] text-white">A tiny LLM agent, running in your browser.</h2>
          <p class="mb-[22px] max-w-[460px] text-[12.5px] leading-[1.5] text-[#b8b0a5]">
            BrewCraft ships a fine-tuned <b class="font-semibold text-white">LFM2.5 · 230M</b> model trained on our knowledge base.
            It answers espresso questions and drives the interface with tools - search, add to cart,
            open guides - all on-device.
          </p>
          <NuxtLink to="/about" class="inline-flex items-center gap-2 rounded-md bg-white px-4 py-2.5 font-body text-[12.5px] font-semibold text-dark no-underline transition-colors hover:bg-[#f0ede8] hover:no-underline">How it works →</NuxtLink>
        </div>
        <div class="flex flex-col gap-[9px] font-mono text-[11px] font-medium">
          <div v-for="t in tools" :key="t.name" class="flex items-center gap-2.5 rounded-md border border-[#3a342c] bg-[#2b2620] px-3.5 py-[11px]">
            <span class="text-accent-soft">→</span> {{ t.name }}<span class="ml-auto text-[#7d766c]">{{ t.args }}</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
