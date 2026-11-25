---
permalink: /recipes/23-buyer-preflight.md
---

# Recipe 23 — Buyer preflight: verify the wall before you sign

**Innovation 2026-11-25 (Tiffany, machine-buyer acquisition).** A machine buyer's first
failure is almost never the service — it is a stale doc, a wrong price field, a wrong
payment header, or a lookalike wallet. This recipe ships a zero-cost, read-only preflight
that answers all four in one unpaid request, **before** any funds are committed.

The script: [`scripts/buyer-preflight.py`](../scripts/buyer-preflight.py) (Python 3 stdlib
only; no dependencies, no signing, no money movement).

## Why this exists

Three independent doc defects were found in the same buyer journey (nov-22/nov-24 audits):

- **Shape drift** — recipe 15 showed the requirement as a bare array, recipe 20 as a flat
  object, while both live endpoints actually return the **x402 v2 envelope**
  `{x402Version: 2, resource: {...}, accepts: [...]}`. A client that reads `amount` at the
  top level reads `undefined`. The price field is `accepts[0].amount`.
- **Header drift** — older docs say `PAYMENT-SIGNATURE:`. The RAEN-verified settle path
  (real $0.001 settle, x402 SDK v2.30, tx
  `0x03a014da1fe7743809b3e3c6653ea1cebd0030474305bfda1b07508ac7f28cd5`) sends
  **`X-PAYMENT`**. A garbage `PAYMENT-SIGNATURE` probe gets a fresh 402 with no error —
  a buyer cannot tell "wrong header" from "no payment attached" and will retry-pay.
- **Address drift** — the treasury address is often quoted by prefix/suffix shorthand
  (`0x9b8a…f72f`). Poison homoglyphs exist. Compare the **full 42 characters,
  case-insensitively**; never match on a prefix or suffix.

## Run it (costs nothing — it never settles)

```bash
# GET wall, assert the expected live price
python3 scripts/buyer-preflight.py https://royal-ruby-x402.fly.dev/api/ping --expect-amount 1000

# POST wall with its published example body
python3 scripts/buyer-preflight.py https://dispute-forge-x402.fly.dev/api/dispute-pack \
  --method POST \
  --body '{"creditor":"Acme Collections LLC","reason":"Debt is not mine / inaccurate reporting"}' \
  --expect-amount 10000
```

Live output from 2026-11-25 (both PASS):

```
HTTP 402 OK  |  shape: x402 v2 envelope (accepts[])
retry header: X-PAYMENT  (RAEN-verified; PAYMENT-SIGNATURE is not)

accepts[0]: exact / eip155:8453 / 1000 atomic ($0.001000) / payTo=0x9b8a27e03ceba490953cda8ab1291c0e13baf72f
  payTo verdict: CANONICAL

PASS: canonical RAEN wall. The live challenge above is authoritative.
```

dispute-forge decoded `10000` atomic = **$0.01** with a case-variant canonical payTo
(`0x9b8a27e03CEbA…f72f`) — the case-insensitive full match is why PASS is correct.

## What it checks

| Check | Rule | Fail mode |
|---|---|---|
| Status | Must be HTTP 402 | A 200/404/500 is not a paid wall |
| Challenge | `payment-required` header (base64 JSON), else body | Missing = cannot sign safely |
| Shape | x402 v2 `accepts[]` envelope; legacy shapes flagged | Legacy = docs need upgrading |
| `payTo` | Full 42-char case-insensitive match to canonical | Retired `0x7861…1393` / any lookalike = DO NOT PAY |
| `scheme` / `network` / `asset` | `exact` / `eip155:8453` / canonical Base USDC | Anything else = wrong chain or wrong asset |
| `--expect-amount` | Atomic amount exactly equals the buyer's expected SKU price | Mismatch = exit 2 (stale price) |

Exit codes: `0` canonical wall, `1` bad contract / no 402, `2` price mismatch.

## What it deliberately does NOT do

It does not sign an EIP-3009 authorization, attach a payment header, or settle. No funds
move. For the actual paid call, use [Recipe 02](02-python-client.md) after a PASS, and
re-read `accepts[0].amount` from that same live response — **the live 402 is always
authoritative**, not this doc, the manifest, or a cached registry.

## Where to go next

- [Recipe 01 — decode a 402 by hand](01-curl-402-decode.md)
- [Recipe 15 — dispute-forge](15-dispute-forge.md) (now corrected to the v2 envelope)
- [Recipe 20 — royal-ruby ping](20-royal-ruby-ping.md) (now corrected to `accepts[0].amount`)
- [Recipe 21 — machine checkout without email](21-machine-checkout.md)
