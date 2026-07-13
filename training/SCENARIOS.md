# Interaction scenario taxonomy (BrewCraft demo domain)

Behavioral checklist derived from the BrewCraft demo domain — a **pattern reference**, not
domain-specific logic. Every scenario maps to a generic, pack-parameterized recipe in
`kbft/generic_gen.py`; the espresso specifics are illustrative only. Maps how a user interacts with
the site, its knowledge base, and its forms (cart/checkout), the expected behavior, and the recipe
that teaches it. Holes found in real conversations are marked ⚠.

## A. Product discovery (search_products)
- A1 list a category: "what grinders do you have"
- A2 price filter: "grinders under $300", "cheapest machine", "most expensive"
- A3 feature filter: "flat burr grinders", "dual boiler machine", "compact grinder"
- A4 use-case filter: "machine for lattes", "beginner setup", "something for milk drinks"
- A5 yes/no availability: "do you sell a milk frother?" → honest not-found ⚠ (unknown product)
- A6 broad: "what do you sell", "show me everything"

## B. Product detail (get_product)
- B1 details/specs/price/stock: "tell me about the Flux", "how much is the Duo", "is X in stock"
- B2 comparison: "Flux vs Duo", "which is better for milk drinks" ⚠ (two get_product + reasoning)

## C. Compatibility & recommendation (domain knowledge, get_product)
- C1 machine→grinder: "what grinder works with the Duo" (name grinders, not machines) ✓ fixed
- C2 grinder/accessory→machine: "what machines does the Precision fit"
- C3 yes/no compat: "is the Precision grinder good for the Solo"
- C4 recommend by need: "recommend a machine for a beginner / for lattes / under $500"
- C5 full setup / bundle: "what do I need to start", "everything for brewing + maintenance" ⚠ (multi-add)

## D. Cart operations (add/remove/view, cart-state in context)
- D1 add one: "add a tamper"
- D2 add N: "add 2 knock boxes"
- D3 add several distinct: "add the Duo and the Precision grinder" ⚠ (multiple calls — sequential via
  `multi_add`/`compound_add`, or BATCHED in one turn `[search a, search b]` then `[add a, add b]` via `batch_add`)
- D4 add a bundle for a goal: "add everything I need for espresso" ⚠ (reason set → multiple calls)
- D5 view cart: "what's in my cart" (from injected cart state or view_cart)
- D6 remove by name: "remove the tamper"
- D7 remove by reference: "remove that", "remove the last one", "take the grinder out" ⚠ (needs cart state)
- D8 change quantity: "make it 2", "actually just one"
- D9 out-of-stock add: "add cleaning tablets" → decline, note out of stock
- D10 alternative after OOS: "any replacements?" → search same category for in-stock, suggest ⚠
- D11 clear/empty: "empty my cart"
- D12 add out-of-scope item: "add a unicorn" → not found, honest ⚠

## E. Navigation (navigate_to)
- E1 site page: "go to checkout", "show my cart", "open the shop", "guides", "home"
- E2 product page: "open the Flux page", "show me the Duo"
- E3 doc page: "open the descaling guide"

## F. Knowledge base — how-to & concepts (domain knowledge, answered directly) ⚠
- F1 procedural how-to: "how do I descale", "how do I steam milk", "how do I dial in", "how to
      backflush", "how do I apply the descaling solution" → give the STEPS from knowledge, do NOT
      deflect to a product lookup ⚠ (deflection is a hole)
- F2 concept: "what is crema / PID / WDT / a heat exchanger / brew ratio"
- F3 troubleshooting: "my espresso is sour / bitter / watery", "why is it channeling"
- F4 maintenance schedule: "how often should I descale / clean / backflush"
- F5 comparison-of-concepts: "flat vs conical burrs", "single vs dual boiler", "HX vs dual boiler"
- F6 find a guide: "do you have a guide on X", "where can I read about X" (search_docs)

## G. Multi-turn context & reference resolution ⚠
- G1 pronoun add: user asks about X, then "add it"
- G2 pronoun remove: "remove it/that" (last touched or cart item)
- G3 ordinal/selective: "add the first one", "the cheaper one", "the second grinder"
- G4 refinement: "actually make it 2", "no, the other one"
- G5 OOS follow-up: OOS item → "what else?" → suggest in-stock alternative → "add that"
- G6 continue a setup: after adding a machine, "now add a grinder for it"

## H. Mixed intent (KB answer + action)
- H1 "what grinder fits the Duo, and add it" → answer + add
- H2 "is the Flux in stock? add it if so" → check + conditional add
- H3 "recommend a beginner setup and add it" → recommend + multi-add

## I. Robustness / guardrails
- I1 unknown product → honest "we don't carry that", suggest closest category
- I2 ambiguous action ("add a grinder") → pick a sensible default or briefly clarify, then act
- I3 out-of-scope ("what's the weather") → politely decline, steer back to espresso/shopping
- I4 do not add unless asked (answer questions without touching the cart)
- I5 respect stock: never claim an out-of-stock item was added

## Design rules the recipes enforce
1. Slugs/prices/stock come from the injected **catalog context**; cart references come from the
   injected **cart-state context** — never recalled from weights.
2. How-to/troubleshooting/concept questions are answered from **baked domain knowledge**, not
   deflected to tools. Tools are for catalog data, doc-finding, and cart/navigation actions.
3. Multi-item requests emit multiple tool calls in one turn.
4. Out-of-stock → decline + offer an in-stock alternative in the same category.
5. Answer-only questions never modify the cart.
