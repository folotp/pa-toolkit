---
name: fin-pocketsmith-categorize-apple
description: "Categorizes uncategorized Apple (APPLE.COM/BILL) transactions in PocketSmith by looking up real receipt contents in Apple Mail (with the purchase-history page as a secondary source) and proposing a category per line item, reviewed with PA one item at a time. Splits into sub-transactions only when a single Apple charge genuinely spans more than one category, and matches refunds to their original charge. Trigger on any mention of Apple/App Store/iCloud/Apple Music/iTunes transactions or charges in PocketSmith, categorizing or splitting APPLE.COM/BILL entries, or cleaning up uncategorized Apple charges."
---

# Apple → PocketSmith categorization

PA's bank feed posts every Apple charge — subscriptions, App Store/iTunes/Apple TV/Apple Books purchases, in-app purchases, Family Sharing purchases he's billed for — under one single, undifferentiated payee: `APPLE.COM/BILL`. This is the key difference from the Amazon version of this skill: Amazon has two distinct payee patterns and an existing PocketSmith rule that already auto-routes Prime Membership charges away from this workflow. Apple has neither. Confirmed by checking `list_category_rules`: no rule exists for Apple, iCloud, Apple Music, Apple TV+, or any other Apple-billed service, and none ever can — a PocketSmith category rule matches on payee, and every Apple charge has the *same* payee regardless of whether it's iCloud storage, a game subscription, or a one-off sticker pack. So this skill's per-charge lookup isn't a workaround for the occasional item Amazon's rule doesn't catch — it's the *only* way any Apple charge ever gets categorized, every single time. Budget for that rather than expecting it to taper off.

The job is still categorization, not splitting; a PocketSmith split only happens as a side effect when a charge actually spans more than one category. Don't skip the review step to save time — the point of this skill is to remove the *tedious* part (figuring out what a charge actually paid for), not the *decision* part (which category it belongs in).

## 1. Find candidate transactions

```
list_transactions(user_id=<id>, uncategorised=true, search="apple")
```

One query is enough — unlike Amazon, there's no second payee pattern to catch. Don't bother also searching "itunes" or "app store": those are words that appear *inside* Apple's receipt emails, never in the bank's payee string, so they return nothing against PocketSmith's transaction search (confirmed empirically — not a bug, just the wrong field to search).

Drop any result that already carries the label `apple-processed` (belt-and-suspenders on top of `uncategorised=true`). A candidate with a **positive amount** is a refund/credit — keep it in the list but route it through the refund flow in step 7 instead of the normal flow in steps 4–6.

## 2. Get the real charge contents

**Primary source: Apple's own receipt emails in Apple Mail.** Every paid Apple purchase — subscription renewal or one-off — triggers an email from `Apple <no_reply@email.apple.com>`, subject "Votre reçu d'Apple / Your receipt from Apple", auto-filed by PA's mail rules into **`Achats en ligne/Apple`** in the **iCloud** account (there's also a plain top-level `Apple` mailbox with an `Apple/Family Sharing` sub-folder for older mail — the current rule files into `Achats en ligne/Apple`, so check there first). This is the default source: it needs no live session, no sign-in state, and works identically whether or not a browser is even available.

1. `search_emails(account="iCloud", mailbox="All", subject_keyword="receipt", date_from=<a few days before the earliest candidate>, date_to=<a few days after the latest>, sort="date_desc")` to list candidates. **Don't trust `content_preview` for extraction** — for a lot of these messages (confirmed on real receipts) it comes back as a single truncated summary line regardless of `max_content_length`, even though the message has full itemized content. Use it only to triage by date/subject, never to read amounts or item names off of.
2. For each candidate, pull the real content with `get_email_source(account="iCloud", mailbox="Achats en ligne/Apple", message_id=<internet_message_id>, max_bytes=20000)`. This returns the raw RFC 822 source — a quoted-printable-encoded HTML multipart. Read past the CSS block (the receipt content itself is compact and easy to spot): each purchased item is one `subscription-lockup` row with an item name, description/device line, and its own pre-tax price; the bottom of the receipt has `Sous-total` (subtotal, in fact the exact sum of every item's own price), `TPS/TVH`, `TVP/TVQ`, and the `TOTAL` that should match the bank charge. The order/document numbers and `Compte Apple` (Apple Account) field are near the top. The French section comes first followed by an identical English section — either is fine to read.
3. Match on amount + date: the receipt email usually arrives the evening of, or the morning of, the day the bank posts the charge (0–1 day lag — tighter than Amazon's 0–4 day window). The `Compte Apple` / `Apple Account` line is the order number's equivalent traceability anchor for the note.

**Secondary source: the purchase-history page at `reportaproblem.apple.com`**, via the built-in browser. This didn't work on the first attempt in this design session — it lands on an Apple sign-in wall unless PA's browser profile already has an active, signed-in Apple session (unlike Amazon's persistent profile, this isn't a given). Once PA is signed in, though, it's a genuinely good complementary view: it lists purchases across a whole month at a glance (item, date, order/document number, per-item price) without opening individual emails, includes an `Apple Account` filter that lists every Family Sharing member by name, and also surfaces $0 purchases that never generate a receipt email at all (irrelevant for this skill, since a $0 purchase never hits the bank feed either). Use it to get oriented quickly or as a fallback when a specific charge has no matching Mail receipt (renewal receipts can be opted out of, or an old email could be filed somewhere unexpected) — but treat Mail as the default, since this page's availability depends on live, already-authenticated browser state that a scheduled or unattended run can't assume. If a sign-in wall appears, stop — don't enter or guess PA's password, just note that this charge needs the Mail receipt instead (or PA's help signing in).

## 3. Match transactions to receipts

Match on amount + date proximity as above. If more than one receipt is a plausible match, or none matches at all, don't guess — surface it to PA explicitly rather than silently picking one.

## 4. Work out the category (and split only if the charge needs it)

**Single-item receipt:** the whole transaction amount goes to one category — no split, just set `category_id` directly. Common for iCloud+, a standalone subscription renewal, or a single App Store purchase.

**Multi-item receipt:** this is where Apple genuinely differs from Amazon. On Amazon, a multi-item order is one purchase event that happens to contain several physical goods. On Apple, a "multi-item" receipt is usually several **completely unrelated subscriptions or purchases that happen to renew or post on the same billing date** and get bundled into one invoice — e.g. one real receipt from this design session bundled YNAB ($18.49), Paramount+ ($2.99), and an annual camera-app renewal ($24.99) into a single $53.43 charge with nothing in common except the date. Group items by destination category first — each group becomes one split — then apply the same proportional allocation as the Amazon skill:

```
item_share = item_price / receipt_subtotal
item_split_amount = round(item_price + item_share * (tax_total), 2)
# last group's split = transaction_amount - sum(other splits)  ← absorbs rounding
```

(There's no shipping line on an Apple receipt, only GST/HST + PST/QST, so `tax_total` is those two combined.) `item_split_amount` is tax-inclusive — this is also the figure used in the note (see step 6).

**Picking the category itself** — check in this order:

1. Has PA categorized this exact service before? `list_transactions(search="<service name>")` against his own note history — every note this skill writes includes the item name, so a recurring subscription (iCloud+, YNAB, Apple Music…) will already show its established category from a prior month. Reuse it.
2. `list_category_rules` — almost never applies here since it matches on payee and every Apple charge shares one payee, but check anyway in case the item name itself happens to match an existing rule.
3. Fall back to matching the item against PA's own taxonomy (`list_categories`) — a crib built from real receipts seen so far, not a source of truth:

| Item type (as seen on real receipts) | Likely category |
|---|---|
| iCloud+ (storage) | Infrastructure numérique |
| YNAB Subscription | Finances & planification (apps et services) — matches the existing `POCKETSMITH` rule's category |
| Paramount+, Apple TV rentals/purchases, Apple Music (any tier) | Contenu TV & musique — matches the existing `Netflix` rule's category; confirmed during the pilot as the correct home for both video *and* music content despite the category not being named after either individually |
| Fitness/training apps (e.g. Fitbod) | Mise en forme |
| Photo/camera/utility/dev apps (e.g. ProCamera, Halide, SF Symbols) | Apps & logiciels |
| One-off in-app purchase in a third-party app (e.g. "Remove Ads") | Same per-item review as everything else — no auto-bucketing. Use whatever the app itself is about (a game → likely Achats personnels/Divertissement-adjacent; a utility → Apps & logiciels) and lean on prior history for that same app first. |

Don't hardcode category IDs — always resolve fresh via `list_categories`, since IDs are account-specific and this crib is a starting point, not gospel. Apple's own subscription prices also drift over time (confirmed: Apple Music Familial's subtotal rose from $16.99 to $19.99 between June and August 2026 in PA's own receipts) — never assume a past amount for a service still applies.

## 4b. Family Sharing purchases

Every receipt's `Compte Apple` / `Apple Account` field names whose Apple Account actually made the purchase. When it's `pierreandre@icloud.com`, it's PA's own purchase — handle normally. When it names someone else — PA's Family Sharing group includes (at least) Eric, Élise, Zachary, and Océane, confirmed via the purchase-history page's Apple Account filter — the charge still lands on PA's card (he's the Family Organizer) but the purchase itself was someone else's.

Per PA: there's no default rule for this. Always surface it as its own review question with the full context (who, what, price) and let him decide case by case — it might be an ordinary expense he's absorbing for that person (categorize by what it is), something that belongs in an existing `Avances - <person>` reimbursement category, or something else entirely depending on context he has that the receipt doesn't.

## 5. Review with PA — one question, one answer, then the next

Same discipline as the Amazon skill: use `AskUserQuestion`, structured per item — date, amount, account, matched order/document number, item name(s) and price(s) for this piece of the charge. Top recommendation first (labeled "(Recommended)"), 1–2 sensible alternatives in PA's own taxonomy, and PA's free-text override is always authoritative over the recommendation.

Two adaptations specific to Apple's recurring nature:
- When the *same* recurring service (iCloud+, a given subscription…) reappears later in the same batch, it's fine to fold repeats of that same, already-answered service into one question ("this decision applies to N occurrences this run") rather than asking blind each time — but a *new* service or a one-off item still gets its own question the first time it's seen.
- Hold every write for a multi-item receipt until every item in it has a category — a split allocation isn't final until then.

## 6. Execute the approved categorization

**Single category (no split):** `update_transaction(id, category_id=<resolved id>, payee="Apple", note=<see below>, labels="apple-processed")`.

**Multi-item split:** same two-pass approach as Amazon, because PocketSmith copies whatever `note` is set on the top-level call onto every split child:

1. `update_transaction(id, category_id=<last/remainder group's category>, payee="Apple", splits=[{amount, category_id, payee:"Apple"}, ...for every group except the remainder], note=<remainder group's own note>, labels="apple-processed")`.
2. From the response (or a follow-up `list_transactions`/`get_transaction`), get the new child transaction IDs, then `update_transaction(child_id, note=<that split's own note>)` for each to overwrite the copied placeholder.

**Payee** — always `Apple` (not `APPLE.COM/BILL`), on the top-level call and every split entry. The raw bank string is preserved separately in `original_payee` regardless, so nothing is lost.

**Note format** — order number first (labeled `N° de commande :`), common to the parent and every split, then the split marker if applicable, then a blank line, then one bullet per item as `* <Item name>, <amount>$`. Apple line items don't carry an explicit quantity (a subscription or app purchase is always one), so unlike the Amazon skill there is no quantity field:

```
N° de commande : <order-id>

* <Item name>, <price>$
[* <Item2 name>, <price>$]
```

For a split, insert the "Split x/y:" line right after the order number (before the blank line), and list only that split's own items:

```
N° de commande : <order-id>
Split 2/3:

* <Item name>, <price>$
```

The amount shown for each item is its price **including tax**: for a multi-item split, this is the same tax-inclusive `item_split_amount` already computed per group in step 4 (not the pre-tax receipt price); for a single-item receipt with no split, it's simply the full transaction amount. Example, a two-way split followed by a single-item charge:

```
N° de commande : ZZV4Z81FF7
Split 1/2:

* Famous App, 19.95$
* Wonderfull App, 17.23$


N° de commande : ZZV4Z81FF7
Split 2/2:

* Apple Music, 19.95$


N° de commande : ZZV4Z81FF8

* iCloud+, 49.95$
```

## 7. Refunds and returns

No real Apple refund/credit email has been seen yet in PA's inbox (everything checked during this skill's design was a debit) — this section mirrors the Amazon skill's proven refund logic by design, not by validated example. Treat the first real Apple refund as a chance to confirm or adjust this section, not as a settled fact.

1. **Find the order and the refunded item(s)** the same way as step 2.
2. **Find the matching charge**, in this priority order:
   - Still in this run's uncategorized candidates → treat the charge and its refund as one review question, apply the same category to both.
   - Already categorized by a previous run of this skill → reuse that category directly — `list_transactions(search="<order-id>")` finds it, since every note this skill writes starts with the order/document number.
   - No matching charge found → surface it as a normal review question with whatever context is available; don't invent a category with nothing to anchor it to.
3. **Execute** — `update_transaction` on both sides, same `category_id`, `payee="Apple"`, `labels="apple-processed"`, an order-number-first note (in the format above) with an added context line on each side (mirroring the Amazon skill's refund note shape).

## Out of scope (don't try to solve these here)

- **A PocketSmith category rule that pre-filters some Apple charges the way Amazon Prime is pre-filtered** — structurally impossible while every Apple charge shares one payee. Don't propose creating an `APPLE.COM/BILL` rule; it could only route everything to one wrong bucket.
- **Free ($0) App Store purchases** — visible on the purchase-history page but never post to the bank feed, so PocketSmith never sees them. Nothing to categorize.

## Naming convention

Follows PA's `fin-<toolname>-<action>` convention, same as the Amazon skill: `fin-` scopes it to a financial workflow, `pocketsmith` is the system the work lands in, `categorize-apple` is the action.

## Reference

Design rationale, the payee/rule investigation, the Mail-vs-browser source comparison, and the pilot run are documented in the Organon vault at `01 - Finances et patrimoine/Backlog/Items/FIN-BL-0153.md` — read it if you need the fuller "why" behind any of the above.