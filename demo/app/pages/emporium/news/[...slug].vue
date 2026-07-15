<script setup lang="ts">
definePageMeta({ layout: 'domain', domain: 'emporium' })
const route = useRoute()

const contentPath = route.path.replace(/^\/emporium/, '')
const { data: page } = await useAsyncData(`emporium-news-${route.path}`, () =>
  queryCollection('emporiumNews').path(contentPath).first(),
)

if (!page.value) {
  throw createError({ statusCode: 404, statusMessage: 'Article not found', fatal: true })
}
</script>

<template>
  <MarkdownArticle v-if="page" :page="page" crumb-to="/emporium/news" crumb-label="News" />
</template>
