import { defineStore } from 'pinia'
import { groceries, type GroceryItem } from '~/data/vendor-groceries'

export interface BasketEntry {
  key: string
  id: string
  title: string
  price: number
  quantity: number
  emoji: string
}

export interface Receipt {
  items: BasketEntry[]
  total: number
}

// The Vendor's own grocery inventory (see data/vendor-groceries.ts) - sold in-character over
// conversation only, no cart page. `basket` drives the counter animation; `receipt` is a snapshot
// taken by the agent's `pay` tool, shown as a mock transaction modal. `clear` (the trained
// clear_cart tool) just empties the counter with no sale/receipt - a distinct action from paying.
// Items stay on the shelf regardless of sales (a demo, not a real stock system).
export const useVendorStore = defineStore('vendor', {
  state: () => ({
    basket: [] as BasketEntry[],
    receipt: null as Receipt | null,
  }),
  getters: {
    shelves(): GroceryItem[] {
      return groceries
    },
    total(): number {
      return this.basket.reduce((sum, l) => sum + l.price * l.quantity, 0)
    },
  },
  actions: {
    sell(id: string, quantity: number): GroceryItem | null {
      const item = groceries.find((g) => g.id === id)
      if (!item) return null
      this.basket.push({
        key: `${id}:${this.basket.length}`,
        id: item.id,
        title: item.title,
        price: item.price,
        quantity,
        emoji: item.emoji,
      })
      return item
    },
    takeBack(id: string): boolean {
      const idx = this.basket.findIndex((l) => l.id === id)
      if (idx === -1) return false
      this.basket.splice(idx, 1)
      return true
    },
    /** clear_cart: empty the counter, no sale. */
    clear() {
      this.basket = []
    },
    /** pay: snapshot the counter into a receipt (drives the transaction modal), then clear it. */
    pay(): Receipt {
      const receipt: Receipt = { items: this.basket, total: this.total }
      this.receipt = receipt
      this.basket = []
      return receipt
    },
    dismissReceipt() {
      this.receipt = null
    },
  },
})
