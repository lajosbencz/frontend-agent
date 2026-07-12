<script setup lang="ts">
definePageMeta({ layout: 'domain', domain: 'emporium' })
const { data: articles } = await useAsyncData('emporium-news-list', () =>
  queryCollection('emporiumNews').order('date', 'DESC').all(),
)
</script>

<template>
  <div class="wrap pt-9 pb-16">
    <header class="mb-6">
      <h1 class="font-display text-[20px] font-bold tracking-[-0.03em]">News</h1>
      <p class="mt-2 text-[12.5px] text-text-muted">Dispatches from the store - policies, restocks, and things we probably shouldn't have announced.</p>
    </header>

    <div class="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-4">
      <NuxtLink
        v-for="a in articles"
        :key="a.path"
        :to="`/emporium${a.path}`"
        class="flex flex-col gap-2 rounded-lg border border-border bg-surface p-[18px] text-inherit no-underline transition-[border-color,box-shadow] hover:border-border-hover hover:shadow-card hover:no-underline"
      >
        <span class="self-start rounded-[6px] bg-accent-tint px-2 py-[3px] font-mono text-[10px] tracking-wide text-accent">{{ a.date }}</span>
        <span class="font-display text-[13.5px] font-semibold tracking-[-0.01em]">{{ a.title }}</span>
        <span class="text-[11px] leading-[1.5] text-text-muted">{{ a.description }}</span>
      </NuxtLink>
    </div>
  </div>
</template>
