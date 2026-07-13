"""Frozen tool contract for the generic assistant + per-example name aliasing.

The RESULT shape the model grounds on is frozen (docs/base-training-procedure.md §7). Tool NAMES and
arg names may be aliased per training example so the model learns to READ the injected schema rather
than memorize a fixed toolset — the same behaviour must survive any site's naming. `alias_tools`
returns an aliased copy of the schema plus a name map the recipes use to emit matching calls.
"""

from __future__ import annotations

import random

# Canonical generic tool set. search_* return the frozen result shape; cart tools act by id.
GENERIC_TOOLS = [
    {"type": "function", "function": {
        "name": "search_catalog",
        "description": "Full-text search the product catalog, optionally narrowed by category, price "
                       "range, stock, and sort order. Returns matching items with id, title, price "
                       "and a short snippet.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
            "category": {"type": "string"},
            "min_price": {"type": "number"},
            "max_price": {"type": "number"},
            "in_stock": {"type": "boolean"},
            "sort": {"type": "string", "enum": ["price_asc", "price_desc", "rating", "newest"]}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "search_knowledge",
        "description": "Full-text search the knowledge base (product info, guides, policies). "
                       "Returns matching passages.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "add_to_cart",
        "description": "Add a catalog item to the cart by its id.",
        "parameters": {"type": "object", "properties": {
            "id": {"type": "string"}, "quantity": {"type": "integer"}}, "required": ["id"]}}},
    {"type": "function", "function": {
        "name": "remove_from_cart",
        "description": "Remove an item from the cart by its id.",
        "parameters": {"type": "object", "properties": {"id": {"type": "string"}},
                       "required": ["id"]}}},
    {"type": "function", "function": {
        "name": "view_cart", "description": "Show the current cart contents.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "clear_cart", "description": "Empty the cart.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "navigate",
        "description": "Navigate the storefront to a page: the cart, checkout, home, or a specific "
                       "product page (pass its id when target is 'product').",
        "parameters": {"type": "object", "properties": {
            "target": {"type": "string", "enum": ["checkout", "cart", "home", "product"]},
            "id": {"type": "string"}}, "required": ["target"]}}},
    {"type": "function", "function": {
        "name": "submit_form",
        "description": "Submit a site form (contact, newsletter signup, feedback, or support request) "
                       "with the fields the customer actually provided. Extract values from what the "
                       "customer said; never invent a name, email, or message.",
        "parameters": {"type": "object", "properties": {
            "form": {"type": "string", "enum": ["contact", "newsletter", "feedback", "support"]},
            "name": {"type": "string"},
            "email": {"type": "string"},
            "subject": {"type": "string"},
            "message": {"type": "string"}}, "required": ["form"]}}},
]

# Procedural naming: (verb-synonyms, object-synonyms) × a convention → ~100+ names/tool, so the model
# must READ the injected schema, not memorize a fixed set. Result shape stays frozen; only names vary.
_VERBS: dict[str, list[str]] = {
    "search_catalog": ["search", "find", "lookup", "query", "browse"],
    "search_knowledge": ["search", "find", "lookup", "query", "get"],
    "add_to_cart": ["add", "put", "place", "insert"],
    "remove_from_cart": ["remove", "delete", "drop", "discard"],
    "view_cart": ["view", "show", "get", "list"],
    "clear_cart": ["clear", "empty", "reset", "wipe"],
    "navigate": ["navigate", "go", "goto", "open", "take"],
    "submit_form": ["submit", "send", "post", "fill"],
}
_OBJS: dict[str, list[str]] = {
    "search_catalog": ["catalog", "products", "items", "inventory", "store"],
    "search_knowledge": ["knowledge", "docs", "info", "articles", "guides", "kb"],
    "add_to_cart": ["cart", "basket", "bag", "order"],
    "remove_from_cart": ["cart", "basket", "bag", "order"],
    "view_cart": ["cart", "basket", "bag", "order"],
    "clear_cart": ["cart", "basket", "bag", "order"],
    "navigate": ["page", "view", "route", "to", "screen"],
    "submit_form": ["form", "message", "request", "contact"],
}


# Per-argument name variants — same open-space idea applied to arg keys, so the model reads the
# schema's parameter names too rather than memorizing "query"/"id"/"quantity".
_ARGS: dict[str, dict[str, list[str]]] = {
    "search_catalog": {"query": ["query", "q", "search", "term", "text", "keywords"],
                       "category": ["category", "cat", "type", "group", "section"],
                       "min_price": ["min_price", "price_min", "over", "from", "min"],
                       "max_price": ["max_price", "price_max", "under", "budget", "max"],
                       "in_stock": ["in_stock", "available", "stock", "only_available"],
                       "sort": ["sort", "order", "sort_by", "order_by"]},
    "search_knowledge": {"query": ["query", "q", "search", "term", "text", "keywords"]},
    "add_to_cart": {"id": ["id", "item_id", "product_id", "sku", "ref"],
                    "quantity": ["quantity", "qty", "count", "amount", "n"]},
    "remove_from_cart": {"id": ["id", "item_id", "product_id", "sku", "ref"]},
    "navigate": {"target": ["target", "to", "page", "destination", "dest"],
                 "id": ["id", "item_id", "product_id", "sku", "ref"]},
    "submit_form": {"form": ["form", "type", "kind"],
                    "name": ["name", "full_name", "contact_name"],
                    "email": ["email", "email_address", "mail"],
                    "subject": ["subject", "topic", "title"],
                    "message": ["message", "body", "text", "comment"]},
}


# Distractor tools: plausible-but-irrelevant tools injected alongside the canonical set (recipes never
# call them) so the model must SELECT the right tool from an arbitrary, variable-size list.
# Each: (verb-pool, object-pool, params, description); names alias like the canonical ones.
_DISTRACTORS: list[tuple[list[str], list[str], dict, str]] = [
    (["track", "check", "get"], ["order", "shipment", "delivery"], {"order_id": {"type": "string"}},
     "Track an existing order's delivery status."),
    (["apply", "redeem", "use"], ["coupon", "code", "promo"], {"code": {"type": "string"}},
     "Apply a discount code to the order."),
    (["get", "fetch", "load"], ["reviews", "ratings"], {"id": {"type": "string"}},
     "Get customer reviews for an item."),
    (["suggest", "recommend", "get"], ["recommendations", "picks", "similar"], {"id": {"type": "string"}},
     "Get items recommended for the customer."),
    (["notify", "watch", "subscribe"], ["restock", "availability"], {"id": {"type": "string"}},
     "Notify the customer when an item is back in stock."),
    (["estimate", "check", "get"], ["shipping", "delivery"], {"zip": {"type": "string"}},
     "Estimate shipping cost and time to a location."),
    (["apply", "set"], ["filter", "sort"], {"field": {"type": "string"}, "order": {"type": "string"}},
     "Sort or filter the current result list."),
    (["pay", "charge", "settle"], ["order", "balance", "invoice"], {"amount": {"type": "number"}},
     "Charge the customer's saved payment method."),
    (["make", "propose", "offer"], ["offer", "bid", "counter"], {"id": {"type": "string"}, "price": {"type": "number"}},
     "Propose a counter-offer price on an item."),
    (["save", "add", "bookmark"], ["wishlist", "favorites", "saved"], {"id": {"type": "string"}},
     "Save an item to the wishlist for later."),
    (["add", "set"], ["giftwrap", "wrapping", "gift"], {"id": {"type": "string"}, "message": {"type": "string"}},
     "Add gift wrapping and a note to an item."),
    (["get", "check", "view"], ["loyalty", "points", "rewards"], {},
     "Check the customer's loyalty points balance."),
    (["book", "schedule", "reserve"], ["pickup", "appointment", "slot"], {"slot": {"type": "string"}},
     "Book a pickup or appointment slot."),
    (["set", "change"], ["language", "locale", "currency"], {"value": {"type": "string"}},
     "Change the storefront language or currency."),
]


def _compose(rng: random.Random, verb: str, obj: str) -> str:
    """Join a verb + object under a random naming convention."""
    style = rng.choice(["snake", "snake", "camel", "dotted", "flat"])
    if style == "snake":
        return f"{verb}_{obj}"
    if style == "camel":
        return verb + obj.capitalize()
    if style == "dotted":
        return f"{obj}.{verb}"
    return verb + obj  # flat


def canonical_names() -> dict[str, str]:
    """Identity name map (no aliasing) — for callers that want the frozen names."""
    return {t["function"]["name"]: t["function"]["name"] for t in GENERIC_TOOLS}


def _identity_arg_map() -> dict[str, dict[str, str]]:
    return {t["function"]["name"]: {k: k for k in t["function"]["parameters"].get("properties", {})}
            for t in GENERIC_TOOLS}


def alias_tools(rng: random.Random,
                enable: bool = True) -> tuple[list[dict], dict[str, str], dict[str, dict[str, str]]]:
    """Return (tools_schema, name_map, arg_map). With aliasing on, each canonical tool gets a
    PROCEDURALLY generated name (verb×object×convention) AND procedurally renamed arguments; the
    schema is rewritten to match. Recipes emit calls via ctx.call(canonical, **canonical_kwargs),
    which maps both the tool name and the arg keys — so calls always agree with the injected schema.
    The open name/arg space forces schema-reading (arbitrary tool + arg names). Off -> canonical."""
    if not enable:
        return GENERIC_TOOLS, canonical_names(), _identity_arg_map()
    name_map: dict[str, str] = {}
    arg_map: dict[str, dict[str, str]] = {}
    used: set[str] = set()
    tools: list[dict] = []
    for t in GENERIC_TOOLS:
        canon = t["function"]["name"]
        for _ in range(8):  # retry to avoid collisions between tools in the same set
            name = _compose(rng, rng.choice(_VERBS[canon]), rng.choice(_OBJS[canon]))
            if name not in used:
                break
        used.add(name)
        name_map[canon] = name
        params = t["function"]["parameters"]
        props = params.get("properties", {})
        amap = {arg: rng.choice(_ARGS.get(canon, {}).get(arg, [arg])) for arg in props}
        arg_map[canon] = amap
        new_params = {**params, "properties": {amap[k]: v for k, v in props.items()}}
        if "required" in params:
            new_params["required"] = [amap.get(r, r) for r in params["required"]]
        tools.append({"type": "function",
                      "function": {**t["function"], "name": name, "parameters": new_params}})
    # Inject 0-3 aliased DISTRACTOR tools (recipes never call them) + shuffle the whole list, so the
    # injected schema varies in SIZE and ORDER too — the model must read it and pick, not memorize a
    # fixed seven in a fixed order. Deterministic (rng-driven). Canonical path (enable=False) is untouched.
    for verbs, objs, params, desc in rng.sample(_DISTRACTORS, rng.randint(2, 5)):
        for _ in range(8):
            name = _compose(rng, rng.choice(verbs), rng.choice(objs))
            if name not in used:
                break
        used.add(name)
        tools.append({"type": "function", "function": {
            "name": name, "description": desc,
            "parameters": {"type": "object", "properties": params, "required": list(params)}}})
    rng.shuffle(tools)
    return tools, name_map, arg_map
