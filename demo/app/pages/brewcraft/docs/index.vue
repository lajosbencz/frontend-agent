<script setup lang="ts">
definePageMeta({ layout: 'domain', domain: 'brewcraft' })
const { data: docs } = await useAsyncData('docs-list', () =>
  queryCollection('docs').order('title', 'ASC').all(),
)
</script>

<template>
  <div class="wrap pt-9 pb-16">
    <header class="mb-6">
      <h1 class="font-display text-[20px] font-bold tracking-[-0.03em]">Guides</h1>
      <p class="mt-2 text-[12.5px] text-text-muted">Dialing in, maintenance, and gear notes - the BrewCraft knowledge base.</p>
    </header>

    <div class="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-4">
      <NuxtLink
        v-for="doc in docs"
        :key="doc.path"
        :to="`/brewcraft${doc.path}`"
        class="flex flex-col gap-2 rounded-lg border border-border bg-surface p-[18px] text-inherit no-underline transition-[border-color,box-shadow] hover:border-border-hover hover:shadow-card hover:no-underline"
      >
        <span class="self-start rounded-[6px] bg-accent-tint px-2 py-[3px] font-mono text-[10px] tracking-wide text-accent">guide</span>
        <span class="font-display text-[13.5px] font-semibold tracking-[-0.01em]">{{ doc.title }}</span>
        <span class="text-[11px] leading-[1.5] text-text-muted">{{ doc.description }}</span>
      </NuxtLink>
    </div>
  </div>
</template>
