// Vendor domain: a neighborhood grocer you talk to - its own inventory (data/vendor-groceries.ts)
// and knowledge base (content/vendor-kb: haggling rules, recipes), unrelated to Emporium's catalog.
// Uses the same 7 trained reference tools as BrewCraft/Emporium (minus navigate - there's nowhere
// else to go) rather than bespoke schemas, for the same tool-calling reliability the model was
// actually trained on, plus one bespoke addition: `pay`, which finalizes the sale and drives the
// mock transaction modal - a genuinely new capability with no trained equivalent, kept distinct
// from clear_cart (which just empties the counter with no sale). The shelf-1 refusal is plain
// context injection, not a tool.

import {
  createAgent,
  buildRegistry,
  buildSystemPrompt,
  type ToolDefinition,
  type Session,
} from 'frontend-agent'
import { referenceTools } from 'frontend-agent/reference'
import { LocalMiniSearchRAG } from 'frontend-agent/rag'
import { useAgentStore } from '~/stores/agent'
import { useVendorStore } from '~/stores/vendor'
import { groceries } from '~/data/vendor-groceries'
import { getEngine } from '../engine'
import { memoizedSession } from '../sessionCache'
import { attachSessionEvents, buildRecovery } from './shared'

const DOMAIN = 'vendor'

const topShelfItems = groceries
  .filter((g) => g.shelf === 1)
  .map((g) => g.title)
  .join(', ')

const PERSONA =
  'You are the grocer behind the counter of a small neighborhood shop, speaking directly to a ' +
  'customer. Stay in character: warm, plainspoken, brief. Use the catalog search for prices and ' +
  'what is in stock - never invent an item or a price. Use the knowledge base search for haggling ' +
  "questions and recipe ideas. Ground every answer ONLY in what the tools return; if a search " +
  "returns nothing relevant, say you don't have that rather than guessing. Add an item to the cart " +
  '(placing it on the counter) only when the customer clearly asks to buy it, using the exact id ' +
  'from a catalog search; remove it from the cart if they change their mind about that item. If the ' +
  'customer changes their mind about everything, clear the cart - this does not charge them. When ' +
  'the customer is ready to buy - "that\'s all", "ring me up", "I\'ll take it" - use pay to finalize ' +
  'the sale; do not use clear_cart for this. ' +
  `The following items sit on the top shelf, out of your reach: ${topShelfItems}. If the customer ` +
  'asks for one of those, do not add it to the cart - reply only: "Sorry, that\'s way too high for me."'

async function buildSession(): Promise<Session> {
  const agent = useAgentStore(DOMAIN)
  const vendor = useVendorStore()

  const base = (useRuntimeConfig().app.baseURL || '/').replace(/\/$/, '')
  const rag = await LocalMiniSearchRAG.fromUrl(`${base}/rag/vendor-index.json`)

  const payTool: ToolDefinition = {
    schema: {
      name: 'pay',
      description:
        'Finalize the sale: ring up everything currently on the counter, charge the customer, and ' +
        'produce a receipt. Use this when the customer is ready to buy, instead of clear_cart.',
      parameters: { type: 'object', properties: {} },
    },
    handler: () => {
      const receipt = vendor.pay()
      return {
        ok: true,
        receipt: {
          items: receipt.items.map((l) => ({ id: l.id, title: l.title, price: l.price, quantity: l.quantity })),
          total: receipt.total,
        },
      }
    },
  }

  const tools: ToolDefinition[] = [
    ...referenceTools({
      rag,
      cart: {
        add: (item, quantity) => vendor.sell(item.id, quantity),
        remove: (id) => vendor.takeBack(id),
        view: () => ({
          cart: vendor.basket.map((l) => ({ id: l.id, title: l.title, price: l.price, quantity: l.quantity })),
          total: vendor.total,
        }),
        clear: () => vendor.clear(),
      },
      navigate: () => {},
    }).filter((t) => t.schema.name !== 'navigate'),
    payTool,
  ]
  const registry = buildRegistry(tools)

  const session = createAgent({
    engine: await getEngine(),
    tools: registry,
    systemPrompt: () =>
      buildSystemPrompt({ persona: PERSONA, catalogHint: () => rag.hint(6), toolSchemas: registry.schemas }),
  })

  attachSessionEvents(session, agent, {
    label: DOMAIN,
    errorMessage:
      'The grocer hit a runtime error and needs to reload the model - send your message again. ' +
      'Chrome or Edge are the best-supported browsers for on-device inference.',
    onError: buildRecovery(cache),
  })
  return session
}

const cache = memoizedSession(buildSession)
export const getSession = cache.get
export const resetSession = cache.reset
