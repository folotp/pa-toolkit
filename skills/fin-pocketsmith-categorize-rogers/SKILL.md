---
name: fin-pocketsmith-categorize-rogers
description: "Splits uncategorized Rogers wireless transactions in PocketSmith three ways (PA / Élise / Zachary) by reading the per-line totals already printed on the matching monthly Rogers invoice, reviewed with PA one transaction at a time before writing. Trigger on any mention of Rogers transactions/charges in PocketSmith, categorizing or splitting the Rogers phone bill, or cleaning up uncategorized ROGERS entries."
---

# Rogers → PocketSmith categorization

PA's Rogers wireless account bills three lines — his own, Élise's, and Zachary's — as one combined monthly charge. Since the bank feed switched to a TD Visa auto-debit (July 2026), that charge posts to PocketSmith as a single uncategorized transaction (`ROGERS ******0917`), with no per-person breakdown from the bank. Before that, PA imported it (via YNAB) already split into three. This skill restores that three-way split automatically, using the invoice Rogers itself sends — which conveniently already computes a fully-taxed total per line, so there's no proportional allocation to do (unlike Amazon's tax/shipping math): read three numbers off the bill, confirm they add up, confirm with PA, write.

## 1. Find candidate transactions

```
list_transactions(user_id=<id>, uncategorised=true, search="rogers")
```

As of this skill's design, that's the only payee pattern that matches (`ROGERS ******0917` on the TD Visa) — `"wireless"` and `"rci"` both returned zero results when checked directly, so don't assume a second pattern exists the way Amazon has two; but if PA's bank feed or account setup changes, re-check with both of those before trusting a single search again. Drop anything already carrying the `rogers-processed` label.

A transaction with a **positive amount** is a refund/credit — no precedent for this exists yet (unlike Amazon), so don't try to auto-match it to a line; surface it to PA as its own question instead of guessing.

## 2. Match the transaction to its invoice

The auto-debit lags the invoice's own billing date by 2–4 weeks (e.g. an invoice dated July 6 gets debited around July 20) — nothing like Amazon's 0–4 day window, so don't use date proximity as your primary signal. Match on **amount** against the invoice-history list on MonRogers (`"<amount>$ - <day> <mois> <année>"`) or against the archived PDFs' own totals (page 1, "Total dû"). If more than one invoice is a plausible amount match, or none matches, say so to PA rather than picking one.

## 3. Make sure the invoice PDF is on hand

Check `Élise et Pierre-André/Téléphone mobile/Rogers <YYYYMMDD>.pdf` (billing date, not transaction date) via `device_list_dir`. If it's missing, run `fin-rogers-download-invoice`'s steps to fetch it first — don't skip straight to guessing amounts.

## 4. Read the three line totals

Stage the PDF into the cloud workspace and extract its text (`pdftotext`, or read the relevant pages if text extraction is unavailable — page numbers shift between invoices, 13 vs 14 pages seen already, so search by content, not a fixed page number). You're looking for three lines, one per phone number, each reading `Total pour Sans-fil <numéro>` or `Total for Wireless <numéro>` (the language is set per-line on Rogers' side, so the same invoice can mix French and Élise's section with English ones for PA's — match by phone number, never by which language label appears):

| Numéro | Personne | Catégorie PocketSmith |
|---|---|---|
| 819-923-8149 | PA | Téléphonie mobile |
| 819-635-3534 | Zachary | Avances - Zachary |
| 819-230-1324 | Élise | Avances - Élise |

Note: 819-635-3534 shows on the bill under the name "PIERRE-ANDRE FOLOT T" (registered as PA's own tablet/data line) — that's cosmetic, the number is what maps to Zachary. If a line's number on the invoice doesn't match one of these three (a line added, dropped, or renumbered), stop and ask PA rather than guessing which bucket it belongs in — this table is specific to PA's current account and will go stale if his family's lines change.

Also grab the invoice number and billing date from page 1 ("Numéro de facture" and "Date de facturation") — both go into the note.

**Sanity check before proposing anything:** the three totals should sum to exactly the transaction's amount (confirmed on both pilot invoices: 44.31 + 19.55 + 37.41 = 101.27, and 44.31 + 19.55 + 42.01 = 105.87). If they don't reconcile, something's off — a fourth line, a one-time charge billed separately, a misread number — surface the discrepancy to PA instead of writing a split that doesn't add up.

## 5. Review with PA

One `AskUserQuestion` per transaction (not per split — unlike Amazon, there's no item-level category judgment call here; the phone→person→category mapping is fixed, so the only thing to confirm is that the three numbers are right and reconcile). Show: date, amount, account, invoice number and billing date, and the three amounts with their destination categories. Recommended option: proceed as calculated. PA can always type a free-text adjustment — treat it as authoritative.

## 6. Execute the approved split

Two of the three amounts go in `splits`; the third is the remainder PocketSmith computes automatically (Amazon's convention: let the last group absorb it, so pick whichever amount you're least sure of as the remainder if there's ever ambiguity — normally all three are exact so it doesn't matter which one you designate).

```
update_transaction(id,
  category_id=<Avances - Élise>,               # remainder group
  payee="Rogers",
  splits=[
    {amount: <PA's amount>, category_id: <Téléphonie mobile>, payee: "Rogers"},
    {amount: <Zachary's amount>, category_id: <Avances - Zachary>, payee: "Rogers"}
  ],
  note=<Élise's own note — see format below>,
  labels="rogers-processed")
```

This sets the note correctly on the remainder split but copies it onto the two children too (same PocketSmith behavior as the Amazon skill) — fix that with a follow-up `update_transaction(child_id, note=...)` per child, using the IDs returned in `split_transactions`.

**Payee**: `"Rogers"` on the parent and every split — matches PA's own historical practice (his old manually-split entries all used the plain payee `Rogers`, never the raw bank string or a per-line detail). `original_payee` keeps the raw bank string regardless.

**Note format** — the invoice's billing date and number as the first line, common to the parent and all three splits, then which split this is and its own line item only. PA wants the invoice identified by date, not just number, since the number alone doesn't tell him at a glance which month it is:

```
Facture du <YYYY-MM-DD>, no. <numéro de facture>
Split <x>/3:
<numéro de téléphone> (<Prénom>), <montant>$
```

`<YYYY-MM-DD>` is the invoice's billing date (the same date used in the archived PDF's filename, `Rogers <YYYYMMDD>.pdf`), not the transaction date.

Example (July transaction, invoice dated 2026-07-06, order fixed as PA=1, Zachary=2, Élise=3):

```
Facture du 2026-07-06, no. 3202841664
Split 1/3:
819-923-8149 (PA), 44,31$
```
```
Facture du 2026-07-06, no. 3202841664
Split 2/3:
819-635-3534 (Zachary), 19,55$
```
```
Facture du 2026-07-06, no. 3202841664
Split 3/3:
819-230-1324 (Élise), 37,41$
```

Don't resolve category IDs from a prior run's hardcoded numbers — they're account-specific; look them up by title via `list_categories` each time, same discipline as the Amazon skill.

## Out of scope (don't try to solve these here)

- **Refunds/credits** — no observed case yet; a positive-amount Rogers transaction goes to PA as a standalone question, not through the flow above.
- **A second Rogers payee pattern** — only `ROGERS ******0917` exists today; if that ever changes, re-run the search-variant check from step 1 before assuming this skill still covers everything.

## Naming convention

Follows PA's `fin-<outil>-<action>` convention: `pocketsmith` is the system the work lands in, `categorize-rogers` is the action — same pattern as `fin-pocketsmith-categorize-amazon`. Sibling skill `fin-rogers-download-invoice` handles archiving the source PDFs this one reads.

## Reference

Design rationale, the invoice structure findings, and the full pilot (2 real transactions split end-to-end) are documented in the Organon vault at `01 - Finances et patrimoine/Backlog/Items/FIN-BL-0154.md`.