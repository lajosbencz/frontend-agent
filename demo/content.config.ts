import { defineContentConfig, defineCollection, z } from '@nuxt/content'

export default defineContentConfig({
  collections: {
    docs: defineCollection({
      type: 'page',
      source: 'docs/**',
      schema: z.object({
        title: z.string(),
        description: z.string(),
      }),
    }),
    products: defineCollection({
      type: 'page',
      source: 'products/**',
      schema: z.object({
        title: z.string(),
        slug: z.string(),
        category: z.enum(['machines', 'grinders', 'accessories']),
        price: z.number(),
        summary: z.string(),
        compatibleWith: z.array(z.string()).default([]),
        inStock: z.boolean().default(true),
      }),
    }),
    emporiumNews: defineCollection({
      type: 'page',
      source: 'news/**',
      schema: z.object({
        title: z.string(),
        description: z.string(),
        date: z.string(),
      }),
    }),
  },
})
