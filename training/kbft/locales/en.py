"""English locale (canonical). Strings are the pre-refactor literals verbatim, so every English pack
generates byte-identical data. The policy KB is generic e-commerce (returns/shipping/warranty/…)."""

from __future__ import annotations

import random

from kbft.locales.base import Locale
from kbft.schema import Doc

_TMPL = {
    "added": "Added {title} to your cart.",
    "added_qty": "Added {n} × {title} to your cart.",
    "added_too": "Added {title} to your cart too.",
    "added_both": "Added both {a} and {b} to your cart.",
    "removed": "Removed {title} from your cart.",
    "cart_now_empty": "Your cart is now empty.",
    "cart_one": "Your cart has 1 item: {title} ({price}). Total {total}.",
    "cart_two": "Your cart has 2 items: {a} ({pa}) and {b} ({pb}). Total {total}.",
    "updated_qty": "Updated — you now have {n} of {title} in your cart.",
    "now_have_two": "You now have 2 × {title} in your cart.",
    "swapped": "Done — swapped {a} for {b}.",
    "self_correct": "Sorry about that — removed {a} and added {b} instead.",
    "options": "Here are some options: {listing}.",
    "found_under": "Here's what I found under {cap}: {listing}.",
    "cheaper_under": "Cheaper options under {cap}: {listing}.",
    "in_stock_under": "In stock under {cap}: {listing}.",
    "pair_well": "These pair well with {title}: {picks}.",
    "most_affordable": "The most affordable is {title} at {price}.",
    "the_second_in": "The second, {title}, is {price}.",
    "the_second_oos": "The second, {title}, is {price} but it's out of stock.",
    "a_few_which": "There are a few {group}: {names}. Which one would you like?",
    "price_added": "The {title} is {price}. Added {n} to your cart.",
    "not_quite": "Not quite — the {title} is listed at {price}.",
    "empty_noremove": "Your cart is empty, so there's no {title} to remove.",
    "dont_have": "You don't have {other} in your cart — it has {a} and {b}.",
    "oos_decline": "Sorry — {title} is currently out of stock, so I can't add it.{tail}",
    "oos_tail": " {alt} is available if you'd like that instead.",
    "not_carry": "Sorry, we don't carry {term}.{tail}",
    "not_carry_tail": " We mainly carry {group}, if that helps.",
    "nav_added_checkout": "Added {title} and took you to checkout.",
    "nav_payment": ("I can't process payment myself, but I've taken you to checkout where you can "
                    "complete the purchase."),
    "ask_search": "Search {query}.",
    "ask_add": "Add {name}.",
    "ask_add_cart": "Add {name} to my cart.",
    "ask_add_checkout": "Add {name} and check out.",
    "ask_add_ordinal": "Add the {ordinal} one.",
    "ask_add_first": "Add the first one.",
    "ask_add_phrase": "Add {phrase} {name}.",
    "ask_add_three": "Add {a}, {b}, and {c}.",
    "added_three": "Added {a}, {b}, and {c} to your cart.",
    "ask_show": "Show me {group}.",
    "ask_show_your": "Show me your {group}.",
    "ask_add_group": "Add the {group}.",
    "good_to_know": "Good to know. What {group} do you have under {cap}?",
    "remove_from_cart_ask": "Remove the {name} from my cart.",
    "remove_ask": "Remove the {name}.",
    "false_premise": "The {name} is {price}, right?",
    "add_word_one": "Add the {word} one.",
    "add_cheapest": "Add the cheapest one.",
    "add_not_expensive": "Not the expensive one — add the cheaper option.",
}
_LISTS = {
    "view_cart_asks": [
        "What's in my cart?", "Show me my cart.", "What do I have so far?",
        "Can you show me my cart contents?", "Let me see what's in my cart.",
        "What have I added so far?", "Pull up my cart, please.",
        "Show me everything in my cart.", "What's currently in my basket?",
        "Give me a look at my cart.", "Remind me what I've got in the cart.",
    ],
    "remove_it_asks": [
        "Actually remove it.", "Take that out.", "Remove that item.",
        "Please take the last thing you mentioned off my cart.",
        "I want to remove whatever I just added before paying.",
        "Don't include the final item we discussed in the total.",
        "Can you subtract what was suggested a moment ago?",
        "No, please leave that new suggestion out of checkout.",
        "Dropping everything you said should be removed first.",
        "Please exclude the most recent product from my list.",
        "I changed my mind about adding that last specific thing.",
        "Don't charge me for the item we just talked about.",
        "Take back whatever came up in your latest reply.",
        "Remove the final suggestion before I finalize this order.",
        "Let's not include what you just offered as an option.",
        "Pull out the product mentioned in our current chat thread.",
    ],
    "clear_asks": [
        "Clear my cart.", "Empty the cart, please.", "Start over.",
        "Empty my cart so I can start fresh.", "Remove everything from my cart.",
        "Wipe the cart clean, please.", "Reset my cart and let's start again.",
        "Delete everything in my cart.", "Just empty the whole thing.",
        "Take everything out and let me restart.",
    ],
    "cheaper_asks": [
        "Anything cheaper?", "Show me the cheaper ones.", "Got something less expensive?",
        "Do you have anything for less?", "Is there a lower-priced option?",
        "Show me more affordable choices.", "Can you find a cheaper version?",
        "What's the less expensive option?", "I'd like something more budget-friendly.",
        "Are there any cheaper alternatives?",
    ],
    "total_asks": [
        "What's my total?", "How much is everything?", "What does my order come to?",
        "Give me the total, please.", "What's the total for these items?",
        "Add up my cart for me.", "How much will this cost altogether?",
        "What's my subtotal?", "Tell me the grand total.", "How much do I owe in total?",
    ],
    "make_it_asks": [
        "Actually, make it {n}.", "Change that to {n}, please.", "I need {n} of those.",
        "Switch the count to {n}.", "Make it {n} instead.", "Can we get {n} instead?",
        "Please adjust the quantity to {n}.", "Update that to {n}.",
        "Let's make it {n}.", "Change the quantity to {n}.",
    ],
    "replace_prefix": [
        "Actually, remove that and add this instead: ", "No wait, I'd rather have ",
        "Okay forget the last one then give me ", "Nevermind just change the end to ",
        "Actually stop removing and replace with ",
    ],
    "also_add_asks": [
        "Also add a {name}.", "And grab me {name} too.", "Add {name} as well.",
        "Could you also throw in {name}?", "I'd like to get {name} added, please.",
        "Don't forget to add {name} either.", "Just tossing {name} into the cart now.",
        "Please include {name} as well today.", "Can we pick up {name} along with that?",
        "Hurry and drop {name} in too then.", "Mind adding {name} alongside those items?",
        "Let's bundle {name} in while you're at it.", "Add {name} to the mix right now.",
        "Please pair {name} with this order.", "Slap some {name} into that basket.",
        "Throwing a second item, just {name}.",
    ],
    "no_i_meant_asks": [
        "No, I meant the {name}.", "That's not it — I wanted {name}.",
        "Oops, remove that and add {name} instead.", "No, please substitute {name}, thanks.",
        "I actually meant {name}.", "Wrong item; I meant {name}.",
        "Not that one — I meant {name}.", "Replace it with {name}, please.",
        "My choice was {name}, not what you added.",
        "Let's go with {name} instead of that.", "That isn't right; swap it for {name}.",
        "Sorry, I meant {name} — swap it in.",
    ],
    "pay_asks": [
        "Place the order and pay.", "Complete my purchase.", "Pay for it now.",
        "Let's checkout right away please.", "I'm ready to place my order.",
        "Please process payment for this item.", "Go ahead and charge me now.",
        "Can we finalize the purchase?", "Send invoice after I pay here.",
        "Checkout with credit card thanks", "Tap to complete my transaction.",
        "Finish paying so i can leave.", "Bill me immediately please.",
        "Swipe card then place order.",
    ],
    "cheapest_asks": [
        "Which is the cheapest?", "What's the most affordable?",
        "Can you tell me which option costs the least?", "How do I pick the cheapest one here?",
        "Is there a cheaper choice available?",
        "I'm looking for the most budget-friendly one.",
        "Which item is priced lowest in this list?", "Which one has the best price?",
        "Which is the least expensive option here?",
        "Point me to the least expensive pick.",
    ],
    "second_asks": [
        "How much is the second one?", "Is the second one in stock?",
        "What's the price on the second one?", "Tell me about the second option.",
        "Is the second item available?", "What does the second one cost?",
        "Can you check stock on the second one?", "How much for the second in the list?",
        "Is the second one still available?", "What's the price of the second item?",
    ],
    "add_another_asks": [
        "Add another {name}.", "One more of those, please.",
        "I'd like to add one more {name}, keeping the current ones.",
        "Can you include an extra {name} along with what I have?",
        "Please give me another {name} but keep my existing order intact.",
        "Just adding a second {name} to save, please!",
        "Could we get one more {name}? Keep the first ones too.",
        "Add another unit of {name} while retaining mine as is.",
        "I want two in total: add one more {name}, keep my other.",
        "Make it a pair; add an extra {name} and don't touch mine.",
        "Please ship me {name} twice, adding to what I already selected.",
        "Keep my items and simply toss another {name} into the order.",
    ],
    # generic-browse reply variants (was a single template; varied to cut assistant monotony since
    # every idiomatic opener funnels here). Picked at random per example.
    "we_carry": [
        "We carry {cats}. A few examples: {listing}. What are you looking for?",
        "We've got {cats} - things like {listing}. Anything in particular?",
        "Sure! We stock {cats}. For instance: {listing}. Want me to narrow it down?",
        "Our range covers {cats} - for example {listing}. What catches your eye?",
    ],
    "browse_openers": [
        "What do you sell?", "What products do you offer?", "What have you got?",
        "What kind of things do you carry?", "Hey, what exactly is your store carrying?",
        "Just curious, can you tell me about your inventory?",
        "I'm looking around, so what kinds of stuff do you have here?",
        "Do you carry any specific items I haven't seen yet?",
        "What sort of goods are available in this shop?",
        "Could you list the main categories of products you stock?",
        "Im interested to know what else besides basics you sell.",
        "What new arrivals or staples would you say define your store?",
        "Are there any particular types of merchandise you specialize in?",
        # idiomatic browse intents: slang openers that are NOT a literal product named
        # "fresh"/"new"; they mean "show me the range". Under-covered before, so the model
        # mis-parsed the leading word as a search term and wrongly declined ("we don't carry Fresh").
        # PURE browse intent only - personal-recommendation phrasings ("what do you recommend?") are
        # left to the recommendation recipe, which answers with grounded picks, not a catalog overview.
        "What's new?", "What's fresh?", "What's good here?", "Anything new?",
        "What's popular?", "What's hot right now?", "What's on offer?",
        "Show me what you've got.", "What's worth a look?",
    ],
    "topic_prefixes": [
        "What about ", "And ", "Ok, now tell me about ", "Switching gears — ",
        "Alright, let's pivot to ", "Changing the subject entirely now ",
        "So then, what else should we look at? ", "That reminds me ",
    ],
    "constrained_asks": [
        "Show me {group} under {cap} that are in stock.",
        "I want {group} under {cap}, in stock only.",
        "Please show {group} under {cap} available now.",
        "Can I see {group} for less than {cap}? In stock please.",
        "Looking for in-stock {group} priced at or below {cap}.",
        "Find me any {group} currently under {cap}, thanks.",
        "I need a quick list of {group} that cost under {cap}.",
        "Show available {group} options with prices not exceeding {cap}.",
        "What are the in-stock {group} choices for {cap}? Show them.",
        "Are there any {group} items in stock costing less than {cap}?",
        "Display {group} selections where price is strictly under {cap}.",
        "I'd like to see stocked {group} that fit a budget of {cap}.",
    ],
    "multi_intent_asks": [
        "How much is the {name}? Add {n} if it's good.",
        "What's the price on {name}, and add {n} to my cart.",
        "Is {name} available? If so, please add {n} units now.",
        "Can you tell me the cost of {name}? Also, I'd like {n} added.",
        "What's the price for {name}? Please ship {n} immediately if okay.",
        "How much does {name} run to buy? Add {n} straight away please.",
        "Tell me {name}'s current rate; want to get {n} in my cart.",
        "Is the cost of {name} set yet? If ready, include {n}.",
        "Could you quote for {name}? Then kindly drop {n} into order.",
        "Please list price on {name}, and then toss {n} in the basket.",
        "How much to take home some {name}? Just add {n}.",
    ],
    "messy_fillers": [
        "um, can you add ", "i wanna get ", "pls add ", "gimme ", "add me ", "so like i need ",
        "hey just throw in some ", "mind if we grab ", "honestly would love to pick up ",
        "let's not forget the ",
    ],
    "bulk_asks": [
        "I'll take {n} of the {name}.", "I want {n} {name}.", "Give me {n} {name}.",
        "Grab me {n} {name}.", "Can I get {n} of the {name}?",
    ],
    "group_listing_asks": [
        "What {group} do you have?", "Show me your {group}.", "What {group} do you carry?",
        "Do you have any {group}?", "Show me the {group} you've got.",
        "How much {group} is available?", "Can I see your {group}?", "Do you stock any {group}?",
        "What variety of {group} exists?", "Please list the {group}.",
        "Are there more {group} options?", "Where can I find {group}?",
        "Tell me about your {group}.", "Do you carry different {group}?",
        "I'd like to see all {group}.", "What's new in {group} today?",
    ],
    # decisive KB Q&A: diverse phrasings that must trigger an immediate search_knowledge (not a hedge).
    # Padded via local ollama qwen3.5:9b (quality-filtered) so the trigger generalizes across wordings.
    "kb_asks": [
        "Tell me about the {title}.", "What can you tell me about the {title}?",
        "Give me the rundown on the {title}.", "How does the {title} work?",
        "What should I know about the {title}?", "Tell me all about the {title}.",
        "Can you explain the {title}?", "I need details on the {title}.",
        "What's up with the {title}?", "Give me info on the {title}.",
        "How does the {title} function?", "Tell more about the {title}.",
        "Why should I care about the {title}?", "Explain this: the {title}.",
        "What's new with the {title}?", "Share everything on the {title}.",
        "Is the {title} any good?", "Break down the {title} for me.",
        "Got time to chat about the {title}?", "Where can I learn about the {title}?",
        "Summarize the key points of the {title}.",
        "Dive into the details of the {title}.", "How much do you know on the {title}?",
        "I'm curious about the {title}.", "Clear up confusion regarding the {title}.",
        "Pitch the benefits of the {title}.", "What makes the {title} special?",
        "Spill the beans on the {title}.", "Give a quick intro to the {title}.",
        "Help me understand the {title} better.", "Is there anything hidden in the {title}?",
        "What is the main point of the {title}?",
        "Could you elaborate on the {title}?", "I want to know about the {title}.",
        "Describe your take on the {title}.", "What's the scoop on the {title}?",
        "Need a primer on the {title}.",
    ],
    # decisive policy Q&A ({topic} = returns/shipping/warranty/payment/cancellation)
    "policy_asks": [
        "What's your {topic} policy?", "How does {topic} work here?",
        "Tell me about your {topic}.", "Do you have a {topic} policy?",
        "Can you tell me your {topic} rules?", "What are the terms for my {topic} request?",
        "Is there anything specific about your {topic}?",
        "What happens if I want a {topic} change?", "How does everything work regarding {topic}?",
        "Can you explain your {topic} policy to me please?",
        "Do you offer any specific policies on {topic}?",
        "Tell me more about your {topic} rules if possible.",
        "Where can I find details about your {topic} terms?",
        "What exactly are the guidelines on {topic}? Thanks!",
        "Do you allow exceptions for specific cases of {topic}?",
        "What is the typical timeline related to my {topic}? Thanks.",
        "Is there a form needed for processing requests on {topic}?",
        "Can you send info regarding any recent changes in {topic}? Thanks.",
    ],
    # short varied leads for grounded replies (avoid a single fixed answer template)
    "grounded_leads": [
        "Here's what we have: ", "From our knowledge base: ", "", "Sure — ",
        "According to our info: ", "",
    ],
}
_PERSONA = (
    "You are the shopping assistant for {store}, an online {vertical} store. Use the tools to search "
    "the catalog and the knowledge base and to manage the cart. Ground every answer ONLY in what the "
    "tools return; if a search returns nothing relevant, say you don't have that information rather "
    "than guessing. Only add items to the cart when the user asks. Use the exact item id from search "
    "results when calling cart tools.")


class EnLocale(Locale):
    def money(self, v: float) -> str:
        return f"${v}"

    def policy_docs(self, slug: str, store: str, rng: random.Random) -> list[Doc]:
        s0, s1 = rng.choice([(2, 4), (3, 5), (4, 7), (5, 8)])
        exp = rng.choice([1, 2])
        free_over = rng.choice([35, 49, 50, 75, 99])
        ret_days = rng.choice([14, 30, 45, 60, 90])
        restock = rng.choice(["no restocking fee", "a 10% restocking fee on opened items",
                              "free return shipping", "return shipping paid by the customer"])
        warranty = rng.choice(["90 days", "6 months", "1 year", "2 years"])
        cancel_h = rng.choice([1, 2, 6, 12, 24])
        pays = rng.choice(["major credit cards, PayPal, and Apple Pay",
                           "Visa, Mastercard, and store credit",
                           "all major cards and Google Pay", "credit cards and bank transfer"])
        entries = [
            ("shipping", "Shipping & Delivery",
             f"Standard shipping takes {s0}-{s1} business days. Express delivery arrives within {exp} "
             f"business day(s) for an added fee. Orders over ${free_over} qualify for free standard "
             f"shipping. Delivery times may be longer for remote areas."),
            ("returns", "Returns & Refunds",
             f"Items can be returned within {ret_days} days of delivery for a refund, provided they are "
             f"in original condition. There is {restock}. Refunds are issued to the original payment "
             f"method within 5-7 business days of receiving the return."),
            ("warranty", "Warranty",
             f"Eligible products carry a {warranty} manufacturer warranty covering defects in materials "
             f"and workmanship. Damage from misuse is not covered. Contact support with your order "
             f"number to start a warranty claim."),
            ("tracking", "Order Tracking",
             "Once an order ships, a tracking number is emailed to you. You can track your package "
             "status using that number on the carrier's site. Tracking updates can take up to 24 hours "
             "to appear after dispatch."),
            ("payment", "Payment Methods",
             f"{store} accepts {pays}. Payment is charged when the order is placed. All transactions are "
             f"processed over a secure encrypted connection."),
            ("cancellation", "Order Cancellation",
             f"Orders can be cancelled within {cancel_h} hour(s) of being placed, before they enter "
             f"fulfillment. After that, you can return the item once it arrives under the returns policy."),
        ]
        return [Doc(id=f"{slug}-policy-{key}", title=title, description=body[:120], body=body)
                for key, title, body in entries]


EN = EnLocale(
    lang="en", persona=_PERSONA, sys_suffix="", hint_label="Example catalog items",
    tmpl=_TMPL, lists=_LISTS, ordinals=["first", "second"],
    vague={"a couple of": 2, "a pair of": 2, "a few": 3, "half a dozen": 6, "a dozen": 12},
    messy={"a couple of ": 2, "a few ": 3, "a dozen ": 12, "": 1})
