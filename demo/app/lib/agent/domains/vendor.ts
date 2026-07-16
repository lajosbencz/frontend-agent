// Vendor domain: a neighborhood grocer you talk to - its own inventory (data/vendor-groceries.ts)
// and knowledge base (content/vendor-kb). Frozen roster minus `navigate` (a single counter, nowhere
// to route); `checkout` finalizes the sale and drives the mock transaction modal. The shelf-1
// refusal is context injection in the persona, not a tool.

import { createFrontendAgent } from 'frontend-agent/core'
import { useVendorStore } from '~/stores/vendor'
import { groceries } from '~/data/vendor-groceries'
import { getEngine } from '../engine'
import { createDomain, loadRag, ragTools } from './shared'

const topShelfItems = groceries
  .filter((g) => g.shelf === 1)
  .map((g) => g.title)
  .join(', ')

const PERSONA =
  'You are the grocer behind the counter of a small neighborhood shop, speaking directly to a ' +
  'customer. Stay in character: warm, plainspoken, brief. Ground every answer ONLY in the current ' +
  'view and what the tools return - never invent an item or a price. Add an item to the cart (placing ' +
  'it on the counter) only when the customer clearly asks to buy it; remove it if they change their ' +
  'mind. If they change their mind about everything, clear the cart - this does not charge them. When ' +
  'the customer is ready to buy - "that\'s all", "ring me up", "I\'ll take it" - use checkout to finalize ' +
  'the sale; do not use clear_cart for this. ' +
  `These items sit on the top shelf, out of your reach: ${topShelfItems}. If the customer asks to buy ` +
  'one of them, do not add it to the cart - reply only, in character: ' +
  '"Sorry, that\'s too high for me."'

export const { getSession, resetSession } = createDomain({
  domain: 'vendor',
  errorMessage:
    'The grocer hit a runtime error and needs to reload the model - send your message again. ' +
    'Chrome or Edge are the best-supported browsers for on-device inference.',
  build: async () => {
    const vendor = useVendorStore()
    const rag = await loadRag('/rag/vendor-index.json')
    return createFrontendAgent({
      engine: await getEngine(),
      persona: PERSONA,
      maxViewItems: groceries.length, // show the whole shop; the top-shelf refusal is prompt-driven
      view: () => groceries.map((g) => ({ id: g.id, title: g.title, price: g.price })),
      cart: () => vendor.basket.map((l) => ({ id: l.id, title: l.title, quantity: l.quantity })),
      tools: {
        ...ragTools(rag),
        add_to_cart: (item, quantity) => vendor.sell(item.id, quantity),
        remove_from_cart: (id) => vendor.takeBack(id),
        clear_cart: () => vendor.clear(),
        checkout: () => {
          const receipt = vendor.pay()
          return {
            ok: true,
            receipt: {
              items: receipt.items.map((l) => ({ id: l.id, title: l.title, price: l.price, quantity: l.quantity })),
              total: receipt.total,
            },
          }
        },
      },
    })
  },
})
