---
name: fin-pocketsmith-categorize-amazon
description: "Categorizes uncategorized Amazon transactions in PocketSmith by looking up the real order contents and proposing a category per item, reviewed with PA one item at a time — splitting into sub-transactions only when an order actually spans more than one category, and matching returns to their original charge instead of skipping them. Trigger on any mention of Amazon transactions/charges/refunds in PocketSmith, categorizing or splitting Amazon purchases, or cleaning up uncategorized Amazon.ca* / AMZN Mktp* entries."
---

# Amazon → PocketSmith categorization

PA's bank feed posts Amazon purchases as opaque charges, in one of two payee patterns depending on the account: `Amazon.ca*XXXXXXX` (sometimes garbled by the feed into things like `Amazon.ca*5A2J32HO2NANANANANAAmazon.ca*5A2J32HO2`) and `AMZN Mktp CA*XXXXXXX` (or bare `AMZN Mktp CA`). He's been manually figuring out what each charge actually bought and categorizing it for years — this skill does that lookup and proposal work, but always lets him make the final category call before anything is written to PocketSmith. The job is categorization; a PocketSmith split only happens as a side effect, when a single order genuinely contains items that belong in more than one category. Don't skip the review step to save time; the point of this skill is to remove the *tedious* part (figuring out what was bought), not the *decision* part (which category it belongs in).

## 1. Find candidate transactions

```
list_transactions(user_id=<id>, uncategorised=true, search="amazon")
list_transactions(user_id=<id>, uncategorised=true, search="amzn")
```

Run **both** searches every time. PocketSmith's search matches substrings, and "amazon" doesn't match "AMZN Mktp..." (or vice versa) — these are two distinct bank-feed naming patterns for the same merchant, not a formatting quirk of one, so skipping either query silently misses real transactions.

Before proposing anything, drop any result that already carries the label `amazon-processed` — that's the idempotency marker this skill writes after finishing a transaction (belt-and-suspenders on top of `uncategorised=true`, which already excludes anything this skill previously touched). Also drop `Amazon.ca Prime Member` charges — PA already has a category rule routing those to *Contenu TV & films* automatically; this skill only handles item purchases. A candidate with a **positive amount** is a refund/credit, not a purchase — keep it in the list, but route it through the refund flow in step 7 instead of the normal single-item/split flow in steps 4–6.

## 2. Get the real order contents

Amazon's Data Portability API does **not** cover this — its marketplace transaction scopes are limited to Belgium, France, Germany, Ireland, Italy, Netherlands, Poland, Spain and Sweden, not Canada (checked directly against `developer.amazon.com/docs/amazon-data-portability`). Don't re-investigate this each time; go straight to one of the two working sources below.

**Live browser lookup (primary, proven to work):** use the built-in browser on PA's linked computer.

1. `Claude_Browser__preview_start` (or `navigate`) to `https://www.amazon.ca/gp/css/order-history` — PA is normally already signed in via the browser's persistent profile.
2. `Claude_Browser__get_page_text` returns the order list with placed-date, total, order number, and item name(s) per order — enough to match single-item orders directly, and enough for a multi-item order's item names, unit prices and tax breakdown by then reading `https://www.amazon.ca/gp/css/summary/print.html?orderID=<order-number>` (the "Printable Order Summary" — a clean, low-clutter page, much easier to parse than the full order-details page).
3. **Quantity, when it isn't obviously 1**: the Printable Order Summary shows a quantity greater than one only as a small circled number floating next to a line item, with no text label and no reliable association to which item it belongs to in a plain-text read — confirmed by testing (order `701-2017002-1439402`: `get_page_text` placed a bare `5` between two item blocks; only a screenshot showed it was actually a badge on the *second* item, and only the subtotal math — `5.99 × 5 + 5.64 + 13.98 = 49.57` — proved which one). Don't guess from position. Two cheap sanity checks first: a single-item order needs no check (quantity is 1 unless the title itself says otherwise, which is packaging, not purchase quantity — e.g. "Two Pack" in the title); for a multi-item order, sum each item's displayed price once — if that sum equals `Item(s) Subtotal` exactly, every quantity is 1 and you're done. Only when it doesn't (a leftover circled number, or the sum comes up short) do you need the real invoice:
   - Open the order's own page, `https://www.amazon.ca/your-orders/order-details?orderID=<order-number>`, and open the "Invoice" dropdown (an `a-popover-trigger`; menu offers three links — "Printable Order Summary" (the page above, not this one), "Invoice", "Request Invoice"). Get the real `invoice.pdf` href — it isn't derivable from the order number, it's a random per-invoice path (`/documents/download/<uuid>/invoice.pdf`) — with `Claude_Browser__javascript_tool`: `[...document.querySelectorAll('a')].find(a => /invoice/i.test(a.textContent) && a.className.includes('popover')).click()`, wait briefly, then read the resulting `<a>` whose `href` contains `/documents/download/`.
   - `navigate` to that PDF URL and read it with `Claude_Browser__computer {action: "screenshot"}` — `get_page_text` returns nothing useful against Chrome's embedded PDF viewer. The invoice is genuinely itemized: a separate 2-page invoice per seller when the order has items from more than one seller, each with an explicit `Quantity`/`Quantité` column per line (confirmed on orders `701-2017002-1439402` and `701-6941889-6212225`) — and the same product can appear as two separate lines whose quantities simply add up (a partial-shipment split), which is exactly what an otherwise-mysterious circled badge turns out to mean. If the invoice runs to several pages, jump straight to the one you need with `#page=N` on the URL rather than trying to click the viewer's page thumbnails — clicks into the embedded PDF viewer land in a cross-origin frame and don't register.
4. If a privacy/re-auth wall appears (e.g. trying to reach Data & Privacy → Request My Data), **stop** — don't enter or guess PA's password. Tell him it needs his sign-in and move on with what's already available.

**Amazon "Request My Data" export (secondary, covers older orders the live lookup won't easily scroll to):** if PA has a recent export of the "Your Orders" category downloaded, read it directly for order/item/amount/quantity data instead of the browser. Ask him for the file (or its location in a connected folder) if the live lookup doesn't cover a transaction's date.

## 3. Match transactions to orders

Match on amount + date proximity (a transaction usually posts 0–4 days after the order's ship/delivery date). Amazon sometimes charges one order in multiple shipments — match at the charge level, not the order level, if the order list shows a different total than the transaction.

If more than one order is a plausible match for a transaction, or no order matches at all, don't guess — surface it to PA explicitly (as one of the review questions, or as a separate note) rather than silently picking one.

## 4. Work out the category (and split only if the order needs it)

**Single-item order, or a multi-item order where everything belongs in the same category:** the whole transaction amount goes to one category — no PocketSmith split needed, just set `category_id` directly. This is the common case; treat it as the default, not the exception.

**Multi-item order that genuinely spans categories:** only now does a PocketSmith split come into play. Group items by destination category first — each group becomes one split. Allocate tax and shipping proportionally across items so each item's split reflects its true landed cost — taxes included — and let the *last* group absorb the rounding remainder so the splits sum exactly to the transaction amount (PocketSmith requires that):

```
item_share = item_subtotal / order_item_subtotal
item_split_amount = round(item_subtotal + item_share * (tax + shipping), 2)  # taxes included
# last group's split = transaction_amount - sum(other splits)  ← absorbs rounding
```

**Picking the category itself** — check these in order, and lean on whichever gives the most confident answer:

1. Has PA categorized a similar Amazon item before? `list_transactions(search="<keyword from item name>")` against his own history is the strongest signal — reuse whatever category he used last time (e.g. "créatine" and "K2" supplements → *Suppléments alimentaires*, both confirmed by direct precedent in his history).
2. `list_category_rules` — an existing payee rule might already apply.
3. Fall back to matching the item's product type against PA's own taxonomy (`list_categories`) — a rough crib, subject to what actually exists in his account:

| Item type | Likely category |
|---|---|
| Electronics, cables, gadgets | Électronique et informatique / Accessoires électroniques et domotique |
| Household supplies, cleaning, tools | Fournitures et entretien ménager |
| Kitchen items | Articles et accessoires de cuisine |
| Supplements, vitamins | Suppléments alimentaires |
| Health/medical | Soins de santé et médicaments |
| Spa/hot-tub related (test strips, chemicals) | Entretien du spa |
| Sport/outdoor gear | Équipement sport et plein air |
| Kids' items (Zachary specifically) | Dépenses Zachary assumées seul, or Avances - Zachary if it's something to be reimbursed |
| Gifts | Cadeaux offerts |
| Genuinely unclear | Autres achats personnels discrétionnaires — flag it as low-confidence in the review question |

Don't hardcode category IDs from a past run — always resolve the category by name via `list_categories` for the current call, since IDs are account-specific and this crib is only a starting point, not a source of truth.

## 5. Review with PA — one question, one answer, then the next

This is the part PA explicitly asked to keep interactive: use `AskUserQuestion`, one transaction (or one item, for a multi-item order) per question, not a big batch dump. Structure each question as:

- The question text: date, amount, account, matched Amazon order number, item name(s)/quantity/price(s) for this piece of the transaction.
- Options: your top recommendation first (labeled "(Recommended)"), then 1–2 sensible alternative categories, in PA's own taxonomy.
- PA can always type a free-text override (e.g. "Avances - Zachary" when an item turns out to be something bought *for* someone else, to be reimbursed rather than expensed) — treat that as authoritative over your recommendation.

Move to the next question as soon as PA answers this one, and hold every write until you've gotten through every item for that transaction — a multi-item order's split allocation isn't final until every item has a category, so writing early risks executing an incomplete split. A refund/charge pair (step 7) only needs a question when the matching charge isn't already categorized — see step 7 for when to ask and when to just reuse.

## 6. Execute the approved categorization

**Single category (no split):** `update_transaction(id, category_id=<resolved id>, payee=<see Payee below>, note=<see Note format below>, labels="amazon-processed")`.

**Multi-item split:** this needs two passes, because each split's note must list only *that split's own* items — PocketSmith copies whatever `note` you set on the top-level call onto every split child it creates, so a single call can't give each one distinct content.

1. `update_transaction(id, category_id=<category for the last/remainder group>, payee=<see Payee below>, splits=[{amount, category_id, payee: <see Payee below>}, ...for every group except the remainder one], note=<remainder group's own note — see below>, labels="amazon-processed")`. This sets the correct note for the remainder split (it's split y/y, or whichever number you assign it) and, as a side effect, copies that same note onto every child split too — expected, corrected next.
2. The call's response (or a follow-up `list_transactions`/`get_transaction` against the parent) gives you the new child transaction IDs. For each child, `update_transaction(child_id, note=<that split's own note>)` to overwrite the copied placeholder with its correct item-specific content.

**Payee** — set `payee` to a clean, standardized merchant name on the top-level call *and* on every entry in `splits`: `Amazon.ca` (or `Amazon.com` if `original_payee` indicates the US marketplace — check the domain in the raw bank string; default to `.ca` since that's what PA actually shops from). Don't put the order ID or a split index in the payee field — that traceability already lives in the note, and PocketSmith preserves the raw bank string separately in `original_payee` regardless of what `payee` is set to, so nothing is lost by cleaning it up. This matches PA's own historical practice: every one of his manually-processed Amazon splits used a plain, consistent payee rather than embedding the order details in it.

**Note format** — every note (split or not) starts with `N° de commande : <order-number>` as a first line, common to the parent and every one of its splits so all pieces of one order are traceable back to it at a glance, then a blank line, then one bulleted line per item. **The amount on each item line includes taxes** — its own share of the order's tax when the order is split (per the proportional allocation in step 4), or the item's full tax-included line price when it isn't — never the pre-tax subtotal:

```
N° de commande : <order-number>

* <quantity>x <Item name>, <price incl. tax>$
* <quantity>x <Item2 name>, <price incl. tax>$
```

For a split (one category out of several the order spans), insert a second line naming which split this is — right under the order number, still before the blank line — then list **only the items belonging to this split** — each split's note should stand alone as a record of what that split covers, so no one has to cross-reference the siblings to know what it's for:

```
N° de commande : <order-number>
Split <x>/<y>:

* <quantity>x <Item name>, <price incl. tax>$
* <quantity>x <Item2 name>, <price incl. tax>$
```

Example — order `702-8910940-6806607` split 2 ways, this note going on the split holding the spa-supply item (its own share of the order's tax already folded into the `22.37$`):

```
N° de commande : 702-8910940-6806607
Split 2/2:

* 1x SenSafe Ozone Check Test Strips, 22.37$
```

...and the sibling split (the household-cleaner item) gets:

```
N° de commande : 702-8910940-6806607
Split 1/2:

* 1x Affresh Washing Machine Cleaner, 19.73$
```

No "Traité par Claude le..." processing line and no order-total/date needed in the note — the `amazon-processed` label plus PocketSmith's own transaction date already cover that, and keeping the note to the order number + bulleted item lines is what keeps it scannable across many transactions. Write item names as given by Amazon (French/English as they appear). A refund/charge pair (step 7) uses this same order-number-first, bulleted-item, tax-included shape with one extra context line — see there for the exact format.

## 7. Refunds and returns

A refund posts as its own credit transaction, days after the original charge, same order, usually the same or a smaller amount. These are in scope — don't leave a flagged credit sitting uncategorized forever.

1. **Find the order and the returned item(s)** the same way as step 2 — the order-history/order-details page shows a "Return received" note on the specific item, and (for a partial return, i.e. the refund is less than the full order) the order's own per-item subtotal math from the Invoice tells you which item and how much, the same way it tells you quantity.
2. **Find the matching charge, in this priority order:**
   - Still in this run's uncategorized candidate list → treat the charge and its refund as one review question: ask PA once for the category, then apply it to both (step 6, same `category_id` on each). This is what nets the pair to zero within that category rather than leaving either side uncategorized.
   - Already categorized by a previous run of this skill → reuse that category for the refund directly, no new question. Find it with `list_transactions(search="<order-number>")` — every note this skill writes starts with the order number, so this finds the original charge even months later, however it was categorized.
   - No matching charge found at all (order predates this skill, or the charge was categorized by hand under different terms) → surface it to PA as a normal review question with whatever order/item context is available; don't invent a category with nothing to anchor it to.
3. **Execute** — `update_transaction` on both the charge and the credit, same `category_id`, `payee="Amazon.ca"`, `labels="amazon-processed"`. Note format keeps the order number common (per step 6 — same `N° de commande :` + blank line + bulleted, tax-included item shape) with one added context line on each side:

```
N° de commande : <order-number>

* <quantity>x <Item name>, <price incl. tax>$
Retourné — remboursé intégralement (voir transaction #<other transaction's PocketSmith id>)
```

```
N° de commande : <order-number>

* <quantity>x <Item name>, <price incl. tax>$
Remboursement (voir transaction #<original transaction's PocketSmith id>)
```

## Out of scope (don't try to solve these here)

- **Amazon Prime / subscriptions** — already handled by an existing category rule; this skill only touches item purchases that show up uncategorized.
- **The Data Portability API** — confirmed not to cover Canadian marketplace transactions; don't spend time re-checking this.

## Naming convention

This skill follows PA's `fin-<toolname>-<action>` convention for finance-domain skills: `fin-` marks it as scoped to a financial workflow (as opposed to a general-purpose tool skill like the `organon-*` skills, which aren't finance-specific even though finance work leans on them), `pocketsmith` is the system the work lands in, and `categorize-amazon` is the action. Apply the same pattern to future finance skills (e.g. a rebuilt `Registre des transactions.xlsx` export per FIN-BL-0144 would be `fin-xlsx-export-registre`).

## Reference

Design rationale, matching logic, and the full pilot run (4 real transactions processed end-to-end) are documented in the Organon vault at `01 - Finances et patrimoine/Backlog/Items/FIN-BL-0152.md` — read it if you need the fuller "why" behind any of the above.