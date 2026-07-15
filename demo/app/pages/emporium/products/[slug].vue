<script setup lang="ts">
definePageMeta({ layout: 'domain', domain: 'emporium' })
import { emporiumProducts } from '~/data/emporium-products'

const route = useRoute()
const product = emporiumProducts.find((p) => p.slug === route.params.slug)
if (!product) {
  throw createError({ statusCode: 404, statusMessage: 'Product not found', fatal: true })
}
</script>

<template>
  <ShopProductDetail
    domain="emporium"
    :item="{ slug: product.slug, title: product.name, price: product.price, inStock: product.inStock, category: product.category, summary: product.description }"
    crumb-to="/emporium"
    crumb-label="Shop"
    footer-note="no returns · no refunds · no regrets"
  />
</template>
