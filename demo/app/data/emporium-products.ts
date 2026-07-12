import raw from './emporium-products.json'
import { slugify } from '~/lib/slugify'

export interface EmporiumProduct {
  id: number
  slug: string
  name: string
  description: string
  price: number
  category: string
  inStock: boolean
}

type RawProduct = Omit<EmporiumProduct, 'slug' | 'inStock'> & { inStock?: boolean }

export const emporiumProducts: EmporiumProduct[] = (raw as RawProduct[]).map((p) => ({
  ...p,
  slug: slugify(p.name),
  inStock: p.inStock !== false,
}))
