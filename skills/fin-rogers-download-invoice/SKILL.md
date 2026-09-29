---
name: fin-rogers-download-invoice
description: "Downloads Rogers wireless invoice PDFs from MonRogers and archives them locally as 'Rogers YYYYMMDD.pdf' in PA's Téléphone mobile folder, using the billing date printed on the invoice. Trigger on any mention of downloading, saving, or archiving Rogers bills/invoices, checking for missing Rogers invoices, or preparing invoices for fin-pocketsmith-categorize-rogers."
---

# Rogers invoice download & archive

PA's Rogers account (`503410917`) issues one PDF invoice a month, covering three lines (his own, Élise's, Zachary's) under one bill. He archives each one locally as `Rogers YYYYMMDD.pdf` (the `YYYYMMDD` is the invoice's own billing date, not the download date) in `Élise et Pierre-André/Téléphone mobile/`. This skill does that download and filing — it does not touch PocketSmith or decide any categorization; that's `fin-pocketsmith-categorize-rogers`'s job, and it depends on this skill's output.

## Before anything: two things that will bite you if skipped

**MonRogers requires PA to sign in himself, every time a fresh session is needed.** Unlike Amazon, there's no persistent login you can rely on by default. Never enter his password. Navigate to `https://www.rogers.com/consumer/self-serve/view-bill` and check whether the account overview loads or a "Ouvrir une session" screen appears. If it's the login screen, tell PA and wait — don't guess or retry the same thing hoping it changes.

**The signed download URL only works from PA's own machine, and never retype an accented folder name in `device_bash`.** Two hard-won facts from the pilot:

1. The cloud container has no network path to rogers.com (a valid signed URL returns 401 there but 200 from `device_bash`). Every fetch of an actual PDF must run through `device_bash`, never the container's own `Bash`.
2. Typing `Élise et Pierre-André` literally inside a `device_bash` command is a trap: the accented characters can arrive pre-composed (NFC) while the real folder on PA's Mac is decomposed (NFD, macOS's norm) — or vice versa. The two look byte-identical when printed but are different filesystem entries. Doing this once during design silently created a second, empty-looking "Élise et Pierre-André" folder in his Documents that shadowed the real one. **Never type the accented folder name as a literal in a `device_bash` command.** Always discover it programmatically first:

```python
import os
base = os.path.join(os.environ['HOME'], 'mnt')
folder_name = next(n for n in os.listdir(base) if '.DS_Store' in os.listdir(os.path.join(base, n)) or 'Téléphone mobile' in os.listdir(os.path.join(base, n)))
```

(or simpler: `os.listdir(base)` returns whatever the mount actually calls it — index into that, don't reconstruct the string yourself.) Same caution applies to `Téléphone mobile` one level down, though in practice it hasn't shown the same split — still, prefer `os.listdir()` over retyping. After any write, sanity-check with `device_list_dir` (which talks to the real disk, not `device_bash`'s view) that nothing duplicated.

## 1. See what's already archived vs. what Rogers has

`device_list_dir` on `Élise et Pierre-André/Téléphone mobile/` to see which `Rogers YYYYMMDD.pdf` files already exist. Then on the MonRogers account overview page, read the invoice history list (`get_page_text` after the page loads) — it shows every available bill as `"<amount>$ - <day> <mois FR> <année>"`, e.g. `"105,87 $ - 6 août 2026"`. Convert each to `YYYYMMDD` (day is always the account's billing day, currently the 6th) and diff against what's already archived. Download whatever's missing — by default the most recent one or two months, or a specific range if PA asks for it (e.g. backfilling older bills).

## 2. Get the signed PDF URL for each missing month

The invoice list is a `<select>`/combobox; each `<option>` carries a `value` like `documents/390901609230-03217401886` — that trailing number pair encodes the account and a per-invoice document ID (the second half, e.g. `03217401886`, is what you'll see again in the PDF's own filename on Rogers' server).

1. `form_input` the combobox to the target option's value.
2. Click "Enregistrer ou télécharger la facture" — a modal opens with one checkbox per month.
3. Check the box matching your target month, click "Télécharger les factures".
4. This may pop a native macOS "Save As" dialog on PA's screen (the browser pane's own download behavior, triggered by Rogers' page navigating to the PDF). **This is harmless — tell PA once that he can cancel it, you're getting the file a different way.** Don't wait for it and don't try to interact with it (it's outside the page DOM, not reachable by the browser tools anyway).
5. Immediately call `read_network_requests` filtered on the document ID from step 1's option value. Look for the completed `GET .../rogers_rest/rogers/documents/<id>.pdf?download=true&EncryptedToken=...` request (status 200). Copy that full URL, token included — it's single-purpose and won't be there if you wait too long or navigate away first.

## 3. Fetch and file it — via `device_bash`, with the discovered folder path

Get the exact billing date from the account page's invoice-history label for this document (or from the combobox option text you selected) to build `YYYYMMDD`. Then, in one `device_bash` Python call: resolve the real folder name (per the warning above), `curl` the captured URL straight to `<real folder>/Téléphone mobile/Rogers <YYYYMMDD>.pdf`, and print the resulting file size so you can sanity-check it's a real PDF (a few hundred KB, not a small JSON error body — Rogers returns a short JSON payload with a 401 on auth failures, which is easy to mistake for a truncated PDF if you don't check).

```python
import os, subprocess
base = os.path.join(os.environ['HOME'], 'mnt')
real = next(n for n in os.listdir(base) if '.DS_Store' in os.listdir(os.path.join(base, n)))
tm = os.path.join(base, real, 'Téléphone mobile')
dest = os.path.join(tm, f'Rogers {yyyymmdd}.pdf')
r = subprocess.run(['curl', '-sS', '-o', dest, '-w', '%{http_code} %{size_download}', url], capture_output=True, text=True)
print(r.stdout, os.path.getsize(dest))
```

Verify afterward with `device_list_dir` (the real-disk API) that the file landed where expected and nothing else changed — this is your check against the NFC/NFD trap recurring.

## 4. Report back

Tell PA which invoice(s) were saved (billing date, invoice number if you read it from page 1, amount) and where. If `fin-pocketsmith-categorize-rogers` is what triggered this download (an invoice was missing mid-categorization), hand back the file path so that skill can continue.

## Out of scope

- Any PocketSmith interaction — this skill only produces the archived PDF.
- Downloading "toutes les factures" in bulk isn't tested; do individual months unless PA explicitly asks for a backfill, and if so, still go one at a time so a single failed fetch doesn't silently skip others.

## Naming convention

Follows PA's `fin-<outil>-<action>` convention: `fin-` scopes it to a financial workflow, `rogers` is the source system, `download-invoice` is the action. Sibling skill: `fin-pocketsmith-categorize-rogers` (the system the *output* lands in, since that one's action is categorization, not download).

## Reference

Design rationale and the full pilot (2 invoices downloaded and archived, NFC/NFD incident and fix) are documented in the Organon vault at `01 - Finances et patrimoine/Backlog/Items/FIN-BL-0154.md`.