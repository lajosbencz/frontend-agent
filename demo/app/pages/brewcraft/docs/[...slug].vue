<script setup lang="ts">
definePageMeta({ layout: 'domain', domain: 'brewcraft' })
const route = useRoute()

const contentPath = route.path.replace(/^\/brewcraft/, '')
const { data: page } = await useAsyncData(`doc-${route.path}`, () =>
  queryCollection('docs').path(contentPath).first(),
)

if (!page.value) {
  throw createError({ statusCode: 404, statusMessage: 'Doc not found', fatal: true })
}
</script>

<template>
  <MarkdownArticle v-if="page" :page="page" crumb-to="/brewcraft/docs" crumb-label="Guides" />
</template>
