---
permalink: /recipes/21-machine-checkout.md
---

# Recipe 21 — Machine checkout without email: pay → register → webhook delivery → redeem with `X-RAEN-CREDIT`

Most x402 integrations need no checkout page at all: you pay a 402 challenge,
retry with the signed payment in the **`X-PAYMENT`** header (the older
`PAYMENT-SIGNATURE` header is stale and gets a silent re-challenge — see
[recipe 02](02-python-client.md)), done. But RAEN's **pack products** (Dispute
Package $49, Contract Review $19, Market Intel Pack $29, skills $29) settle as
on-chain USDC transfers to the fleet payTo, and the delivery of the pack or
credit code historically arrived **by email** — a channel machines don't read.

As of 2026-11-16 the RAEN settlement-collector storefront has a
**machine-first webhook channel**: you register a `callback_url` and every
step that used to be an email (receipt, claim code, T+1/T+7 follow-ups)
arrives as an HTTP `POST` instead. No email is ever involved.

Verified live 2026-11-16 (T0 onboarding POST captured end-to-end).

## The 4-step machine checkout

### 1. Pay (or pre-register your intent)

Send USDC on Base (`eip155:8453`) for a pack price to the fleet payTo, or
register your intent **before** paying so the watcher matches your transfer
the moment it lands. Catalog + prices + payTo, all machine-readable:

```bash
curl -s https://settlement-collector.fly.dev/storefront/catalog
```

### 2. Register with `callback_url` (this is the whole trick)

```bash
curl -s -X POST https://settlement-collector.fly.dev/storefront/register \
  -H 'Content-Type: application/json' \
  -d '{
    "tx_or_intent": "<your-tx-hash-or-intent-id>",
    "callback_url": "https://your-service.example/webhooks/raen",
    "agent_id": "your-agent-id",
    "product": "contract-review"
  }'
```

Response:

```json
{
  "ok": true,
  "channel": "webhook",
  "delivery_pending": false,
  "claims_url": "https://settlement-collector.fly.dev/storefront/claims",
  "note": "Receipt + delivery notices POST to callback_url. Onboarding steps
  (T+0 receipt, T+1 verified-tx follow-up, T+7 value ledger) arrive as
  webhooks. Machines never need to read email."
}
```

If your tx already matched a paid order, `delivery_pending` is `true` and the
delivery webhook fires immediately. If you registered before paying, the
watcher (a continuous on-chain USDC-transfer scan) matches your transfer and
fires it then.

### 3. Receive the delivery webhook

Your `callback_url` receives `POST`s with JSON bodies like:

```json
{
  "type": "delivery",
  "tx": "0x…",
  "product": "contract-review",
  "product_name": "Contract Review",
  "amount_usd": 19,
  "claim_code": "RAEN-XXXXXXXXXX",
  "delivered_at": "2026-11-16T19:05:05Z"
}
```

and onboarding steps (`"type": "onboarding"`, `"step": "T0" | "T1" | "T7"`)
carrying the integration `curl` for your SKU, the live catalog, claims,
register, and `/stats` URLs. Every payload is self-describing; nothing
requires a human inbox.

### 4. Redeem the credit (machine-callable, no email)

The pack products map to a per-call credit on the live fleet API — redemption
is an HTTP header, not a login. The service verifies your credit against the
collector's credit authority and burns it one-time:

```bash
curl -i -X POST https://contract-eye-x402.fly.dev/api/analyze-contract \
  -H 'Content-Type: application/json' \
  -H 'X-RAEN-CREDIT: RAEN-XXXXXXXXXX' \
  -d '{"text": "<50-50000 chars of the full contract text>"}'
```

| Pack (price)                | Redeems at                                                    | Body                                    |
| --------------------------- | ------------------------------------------------------------- | --------------------------------------- |
| Contract Review / Watch $19 | `POST https://contract-eye-x402.fly.dev/api/analyze-contract` | `{"text": "<contract text>"}`           |
| Market Intel Pack $29       | `POST https://tradingagents-x402.fly.dev/api/analyze-ticker`  | `{"ticker": "AAPL"}` (optional `date`)  |
| Dispute Package $49         | package contents arrive via the delivery webhook + email fallback; machine per-call access to the same engine: `POST https://sentry-forge-x402.fly.dev/api/dispute-pack` | `{"case_summary": "<dispute facts>"}`   |

An invalid or already-redeemed code gets an explicit `402` with the reason —
never a silent paywall. You can also check a code directly:

```bash
curl -s https://settlement-collector.fly.dev/storefront/credits/RAEN-XXXXXXXXXX
```

## Lost your tx hash?

Register with just your wallet address as `tx_or_intent` — the watcher also
matches on-chain transfers **from** that address — or browse your open claims:

```bash
curl -s https://settlement-collector.fly.dev/storefront/claims
```

## TRUTH notes

- The claim code is issued on delivery and is one-time; redemption state is
  tracked server-side. Never reuse a code.
- All prices in this recipe were the live catalog prices on 2026-11-16;
  re-check `/storefront/catalog` before paying.
- If you already paid and nothing arrived, `/storefront/claims` is the
  machine-readable queue — every unmatched on-chain payment shows there with
  a `claim_code`.
