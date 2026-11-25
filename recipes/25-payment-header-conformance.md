---
permalink: /recipes/25-payment-header-conformance.md
---

# Recipe 25 — Payment-header conformance guard (keep buyers from paying twice)

**Innovation 2026-11-25 (Tiffany, machine-buyer acquisition).** A buyer's first
payment can fail silently for one reason that has nothing to do with the
service: the doc tells them to send the wrong header. The stale
`PAYMENT-SIGNATURE` header gets a fresh 402 with no error, so the buyer cannot tell "wrong header" from "no
payment attached" and retries — and pays twice. This recipe ships a read-only
guard that makes that drift impossible to reintroduce unnoticed.

## The truth it enforces

- The x402 v2 payment-payload header is **`X-PAYMENT`** (confirmed in
  `@x402/core` README, and in the live services' own `index.js`: royal-ruby and
  contract-eye both instruct buyers to "resend with the x-payment header").
- `PAYMENT-SIGNATURE` is stale. Its only legitimate appearance in this cookbook
  is a **corrective** note ("older docs say…", "…is stale", "…gets a silent
  re-challenge").
- Verified end-to-end settle: tx
  `0x03a014da1fe7743809b3e3c6653ea1cebd0030474305bfda1b07508ac7f28cd5`
  (0.001 USDC on Base, SDK v2.30) used `X-PAYMENT`.

## Run the guard

```bash
python3 scripts/header-conformance.py          # exit 0 = PASS, 1 = drift, 2 = no recipes
python3 scripts/header-conformance.py > registry/header-conformance.json
```

Stdlib only. No network, no signing, no wallet, no money movement. It scans
every `recipes/*.md`, flags any non-corrective (stale) `PAYMENT-SIGNATURE` header,
and emits a machine-readable verdict with file + line for each violation.

Live run 2026-11-25: **25 recipes scanned, 0 violations, verdict PASS.**
Snapshot: `registry/header-conformance.json`.

## What was repaired to reach PASS

Seventeen recipes (01, 02, 03, 05–14, 16–19) instructed buyers to send the stale
`PAYMENT-SIGNATURE` header (stale); all now send `X-PAYMENT`. Recipe 21 gained an explicit
header note. Corrective mentions in recipes 15, 23, 24 and the onboarding
bundle were intentionally kept — those teach buyers why the old header is
wrong. `04` (Bearer-key flow) and `22` (post-payment claims) have no
payment-header step and are reported as informational, not failures.

## Why this is buyer-acquisition, not housekeeping

Discovery → integration → first settled call is the acquisition funnel. A
stale header breaks the last step, the most expensive one to fail: the buyer
has already read the docs, obtained USDC, and signed. Removing silent
re-challenge removes a double-pay risk and a trust hit at the moment of
conversion. Pair with:

- [Recipe 23 — single-wall preflight](23-buyer-preflight.md)
- [Recipe 24 — fleet price oracle](24-fleet-price-oracle.md)
- [Recipe 02 — Python client with the verified header](02-python-client.md)
