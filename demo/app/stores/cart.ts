import { defineStore } from 'pinia'

export interface CartLine {
  slug: string
  title: string
  price: number
  quantity: number
}

const stores = new Map<string, ReturnType<typeof defineCartStore>>()

function defineCartStore(domain: string) {
  return defineStore(`cart:${domain}`, {
    state: () => ({
      lines: [] as CartLine[],
    }),
    getters: {
      itemCount: (state) => state.lines.reduce((sum, l) => sum + l.quantity, 0),
      total: (state) => state.lines.reduce((sum, l) => sum + l.quantity * l.price, 0),
    },
    actions: {
      add(line: { slug: string; title: string; price: number }, quantity = 1) {
        const existing = this.lines.find((l) => l.slug === line.slug)
        if (existing) {
          existing.quantity += quantity
        } else {
          this.lines.push({ ...line, quantity })
        }
      },
      remove(slug: string) {
        this.lines = this.lines.filter((l) => l.slug !== slug)
      },
      setQuantity(slug: string, quantity: number) {
        const existing = this.lines.find((l) => l.slug === slug)
        if (existing) existing.quantity = quantity
      },
      clear() {
        this.lines = []
      },
    },
  })
}

export function useCartStore(domain: string) {
  let define = stores.get(domain)
  if (!define) {
    define = defineCartStore(domain)
    stores.set(domain, define)
  }
  return define()
}
