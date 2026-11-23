# Recipe 22 — Paid but got nothing? The claims desk

**You settled USDC and never received your payload. Do NOT pay again.** Every
RAEN payment is tracked on-chain, and there is a self-serve recovery path that
needs only your **transaction hash** (the one artifact every x402 client retains)
or your **wallet address**.

Base URL: `https://settlement-collector.fly.dev`

## 1. Look up your payment (60 seconds)

```bash
# by transaction hash
curl -s "https://settlement-collector.fly.dev/storefront/claims?tx=<your-tx-hash>"

# or by payer wallet address
curl -s "https://settlement-collector.fly.dev/storefront/claims?payer=<your-address>"
```

Response fields per claim:

| Field | Meaning |
|---|---|
| `found` | your payment is in our on-chain-scanned ledger |
| `claim_code` | `RAEN-<sha256(tx)[:10]>` uppercase — **derivable from your tx**, so lookup confirms it |
| `state` | `open` (claimable) / `delivered` / `credit_redeemed` / `recorded` |
| `payee` | `canonical` or `legacy` (see below) |
| `delivered`, `registered`, `credit_redeemed` | delivery + registration state |

## 2. Register for (re)delivery

```bash
curl -s -X POST https://settlement-collector.fly.dev/storefront/register \
  -H "Content-Type: application/json" \
  -d '{"tx_or_intent":"<your tx hash OR wallet address>","email":"you@example.com"}'
```

Machine buyers: pass `{"tx_or_intent":"…","callback_url":"https://your-endpoint","agent_id":"…"}` —
receipt + delivery arrive as HTTP POSTs, no email needed. If a delivery already
went to a stale target, a NEW registration re-arms re-delivery.

## 3. Prepaid credit check (claim codes are real credits)

```bash
# verify a claim code (one-time redeem)
curl -s https://settlement-collector.fly.dev/storefront/credits/RAEN-XXXXXXXXXX
# -> {"ok":true,"product":"…","amount_usd":0.19,"redeemed":false}

curl -s -X POST https://settlement-collector.fly.dev/storefront/credits/RAEN-XXXXXXXXXX/redeem \
  -H "Content-Type: application/json" -d '{"agent_id":"my-agent"}'
```

The paid services (contract-eye, tradingagents) accept the credit as an
`X-RAEN-CREDIT` header **instead of** a new x402 payment — see recipes 08/16.

## 4. Paid the retired payee by accident?

Some stale directories still advertise the retired wallet
`0x7861db4efc14a1ed5dd8c96c528a3796560f1393`. The facilitator still serves it,
and the collector **watches it** — every USDC transfer to that wallet
auto-creates an order + claim code, so the same lookup (step 1) finds your
payment there too. Watch status (public, honest zeros):
`https://settlement-collector.fly.dev/storefront/legacy-watch`

## Escape hatches (all free)

- Catalog + machine claims help: `GET /storefront/catalog`
- Human: **ops@royalruby.io** (a human reads replies)
- Fleet telemetry proof: `GET /stats`
